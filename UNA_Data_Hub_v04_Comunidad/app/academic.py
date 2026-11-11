"""Import-only public academic metadata; no authentication or personal records."""
from __future__ import annotations
import httpx
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
from .db import connection

DS_BASE='https://repositorio.unap.edu.pe'
AGENT='UNADataHubResearch/0.2 public academic metadata research pilot'

def meta_values(meta,key):
    return [x['value'] for x in meta.get(key,[]) if isinstance(x,dict) and x.get('value')]

def normalize_dspace(data):
    items=data.get('_embedded',{}).get('searchResult',{}).get('_embedded',{}).get('objects',[])
    result=[]
    for wrapper in items:
        obj=wrapper.get('_embedded',{}).get('indexableObject') or wrapper.get('indexableObject') or wrapper
        m=obj.get('metadata') or {};uid=obj.get('uuid') or obj.get('id')
        title=meta_values(m,'dc.title')
        if not uid or not title:continue
        urls=meta_values(m,'dc.identifier.uri')
        link=next((url for url in urls if urlparse(url).scheme=='https' and urlparse(url).netloc in ('repositorio.unap.edu.pe','hdl.handle.net')),None)
        result.append({'source':'dspace','identifier':str(uid),'title':title[0],
          'authors':meta_values(m,'dc.contributor.author'),'published':(meta_values(m,'dc.date.issued') or [None])[0],
          'url':link or f'{DS_BASE}/items/{uid}'})
    return result

def normalize_oai(content):
    if len(content)>8_000_000:raise ValueError('OAI response too large')
    root=ET.fromstring(content)
    ns={'o':'http://www.openarchives.org/OAI/2.0/','dc':'http://purl.org/dc/elements/1.1/'}
    error=root.find('o:error',ns)
    if error is not None:raise ValueError('OAI protocol error: '+str(error.get('code')))
    records=[]
    for x in root.findall('.//o:ListRecords/o:record',ns):
        header=x.find('o:header',ns)
        if header is None or header.get('status')=='deleted':continue
        uid=header.findtext('o:identifier','',ns)
        title=x.findtext('.//dc:title','',ns)
        if not uid or not title:continue
        urls=[t.text for t in x.findall('.//dc:identifier',ns) if t.text and t.text.startswith('https://')]
        records.append({'source':'oai','identifier':uid,'title':title,
           'authors':[t.text for t in x.findall('.//dc:creator',ns) if t.text],
           'published':x.findtext('.//dc:date',None,ns),
           'url':next((u for u in urls if urlparse(u).netloc in ('repositorio.unap.edu.pe','hdl.handle.net')),None)})
    return records

def save_records(items):
    import json
    statement='''INSERT INTO academic_records(source,identifier,title,authors,published,url)
       VALUES (%s,%s,%s,%s::jsonb,%s,%s)
       ON CONFLICT(source,identifier) DO UPDATE SET title=excluded.title,
       authors=excluded.authors,published=excluded.published,url=excluded.url,updated_at=now()'''
    with connection() as conn:
        with conn.cursor() as cur:
            for x in items:
                cur.execute(statement,(x['source'],x['identifier'],x['title'],json.dumps(x['authors'],ensure_ascii=False),x['published'],x['url']))
    return len(items)

def get_records(query=None,source=None,limit=20,offset=0):
    sql='SELECT source,identifier,title,authors,published,url,updated_at FROM academic_records WHERE true'
    params=[]
    if source:sql+=' AND source=%s';params.append(source)
    if query:sql+=' AND title ILIKE %s';params.append('%'+query.replace('%','\\%').replace('_','\\_')+'%')
    sql+=' ORDER BY updated_at DESC LIMIT %s OFFSET %s';params.extend([limit,offset])
    with connection() as conn:return conn.execute(sql,params).fetchall()

async def sync_dspace(query='quinua',size=10):
    async with httpx.AsyncClient(timeout=25,headers={'User-Agent':AGENT},follow_redirects=False) as cli:
        response=await cli.get(f'{DS_BASE}/server/api/discover/search/objects',params={'query':query,'size':size,'page':0})
        response.raise_for_status()
        if len(response.content)>8_000_000:raise ValueError('DSpace response too large')
        return save_records(normalize_dspace(response.json()))

async def sync_oai():
    async with httpx.AsyncClient(timeout=30,headers={'User-Agent':AGENT},follow_redirects=False) as cli:
        response=await cli.get(f'{DS_BASE}/server/oai/request',params={'verb':'ListRecords','metadataPrefix':'oai_dc'})
        response.raise_for_status()
        return save_records(normalize_oai(response.content))
