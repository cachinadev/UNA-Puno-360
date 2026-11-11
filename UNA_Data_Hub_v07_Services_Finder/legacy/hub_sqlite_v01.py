"""UNA Data Hub: public academic metadata only. Python 3.10+."""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query

BASE = 'https://repositorio.unap.edu.pe'
DB = Path(os.environ.get('UNA_DB', str(Path(__file__).with_name('una_hub.sqlite3'))))
USER_AGENT = 'UNADataHubResearchPrototype/0.1 (public metadata; contact administrator before bulk harvesting)'
app = FastAPI(title='UNA Data Hub — piloto', version='0.1.0', docs_url='/docs')


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS records (
        source TEXT NOT NULL, identifier TEXT NOT NULL, title TEXT NOT NULL,
        authors TEXT NOT NULL, published TEXT, url TEXT, raw TEXT NOT NULL,
        updated_at TEXT NOT NULL, PRIMARY KEY(source, identifier))''')
    c.commit()
    return c


def store(items):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        for r in items:
            c.execute('''INSERT INTO records (source, identifier, title, authors, published, url, raw, updated_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              ON CONFLICT(source,identifier) DO UPDATE SET title=excluded.title,
              authors=excluded.authors,published=excluded.published,url=excluded.url,
              raw=excluded.raw,updated_at=excluded.updated_at''',
              (r['source'], r['identifier'], r['title'], json.dumps(r['authors'], ensure_ascii=False),
               r.get('published'), r.get('url'), json.dumps(r.get('raw',{}), ensure_ascii=False), now))
        c.commit()
    return len(items)


def values(meta, key):
    return [x.get('value', '') for x in meta.get(key, []) if isinstance(x, dict) and x.get('value')]


def normalize_dspace(data):
    items = data.get('_embedded', {}).get('searchResult', {}).get('_embedded', {}).get('objects', [])
    normalized = []
    for wrapper in items:
        obj = wrapper.get('_embedded', {}).get('indexableObject') or wrapper.get('indexableObject') or wrapper
        meta = obj.get('metadata') or {}
        uid = str(obj.get('uuid') or obj.get('id') or '')
        titles = values(meta, 'dc.title')
        if not uid or not titles:
            continue
        uri = (values(meta, 'dc.identifier.uri') or [None])[0]
        if uri and urlparse(uri).scheme not in ('https', 'http'):
            uri = None
        normalized.append({'source':'dspace', 'identifier':uid, 'title':titles[0],
          'authors':values(meta, 'dc.contributor.author'),
          'published':(values(meta, 'dc.date.issued') or [None])[0],
          'url':uri or f'{BASE}/items/{uid}', 'raw':{'uuid':uid,'metadata':meta}})
    return normalized


def normalize_oai(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ns={'o':'http://www.openarchives.org/OAI/2.0/', 'dc':'http://purl.org/dc/elements/1.1/'}
    error = root.find('o:error',ns)
    if error is not None:
        raise ValueError(f'OAI error: {error.attrib.get("code")}: {error.text}')
    result=[]
    for record in root.findall('.//o:ListRecords/o:record', ns):
        header=record.find('o:header',ns)
        if header is None or header.get('status')=='deleted':
            continue
        ident=header.findtext('o:identifier',default='',namespaces=ns)
        title=record.findtext('.//dc:title',default='',namespaces=ns)
        if not ident or not title:
            continue
        authors=[x.text for x in record.findall('.//dc:creator',ns) if x.text]
        dates=[x.text for x in record.findall('.//dc:date',ns) if x.text]
        ids=[x.text for x in record.findall('.//dc:identifier',ns) if x.text and x.text.startswith(('http://','https://'))]
        result.append({'source':'oai','identifier':ident,'title':title,
          'authors':authors,'published':dates[0] if dates else None,
          'url':ids[0] if ids else None,'raw':{'oai_identifier':ident}})
    token = root.findtext('.//o:ListRecords/o:resumptionToken', default=None,namespaces=ns)
    return result,token or None


def fetch_dspace(term='quinua',size=10):
    with httpx.Client(timeout=15, headers={'User-Agent':USER_AGENT},follow_redirects=True) as client:
        res=client.get(f'{BASE}/server/api/discover/search/objects', params={'query':term,'size':size,'page':0})
        res.raise_for_status()
        return normalize_dspace(res.json())


def fetch_oai():
    with httpx.Client(timeout=20, headers={'User-Agent':USER_AGENT},follow_redirects=True) as client:
        res=client.get(f'{BASE}/server/oai/request',params={'verb':'ListRecords','metadataPrefix':'oai_dc'})
        res.raise_for_status()
        return normalize_oai(res.content)

@app.get('/health')
def health():
    with connect() as c:
        count=c.execute('SELECT COUNT(*) FROM records').fetchone()[0]
    return {'status':'ok','records':count, 'database':str(DB)}

@app.get('/sources')
def sources():
    return [
       {'id':'dspace','url':f'{BASE}/server/api/discover/search/objects','access':'public metadata; verify response'},
       {'id':'oai','url':f'{BASE}/server/oai/request','access':'public metadata; verify response'}]

@app.get('/records')
def records(source: str | None=None,q: str | None=None,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
    sql='SELECT source,identifier,title,authors,published,url,updated_at FROM records WHERE 1=1'
    params=[]
    if source:
        sql+=' AND source=?';params.append(source)
    if q:
        sql+=' AND (title LIKE ? OR authors LIKE ?)';params.extend([f'%{q}%',f'%{q}%'])
    sql+=' ORDER BY updated_at DESC LIMIT ? OFFSET ?';params.extend([limit,offset])
    with connect() as c:
        rows=c.execute(sql,params).fetchall()
    return [{'source':r['source'],'identifier':r['identifier'],'title':r['title'],
       'authors':json.loads(r['authors']), 'published':r['published'],'url':r['url'],
       'updated_at':r['updated_at']} for r in rows]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('command',choices=['init','sync-dspace','sync-oai'])
    p.add_argument('--query',default='quinua')
    p.add_argument('--size',type=int,default=10)
    args=p.parse_args()
    if args.command=='init':
        connect().close();print('Base SQLite inicializada:', DB);return
    try:
        if args.command=='sync-dspace':
            items=fetch_dspace(args.query,min(max(args.size,1),25))
            print('Registros recibidos:',len(items),'guardados:',store(items))
        else:
            items,token=fetch_oai()
            print('Primera página OAI:',len(items),'guardados:',store(items), 'paginación disponible:',bool(token))
    except (httpx.HTTPError,ValueError,ET.ParseError,KeyError) as exc:
        print('Error de sincronización:',str(exc))
        raise SystemExit(1)

if __name__=='__main__':
    main()
