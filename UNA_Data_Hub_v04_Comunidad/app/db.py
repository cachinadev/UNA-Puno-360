"""Simple synchronous psycopg PostGIS gateway with bound parameters."""
from __future__ import annotations
import os
from contextlib import contextmanager

@contextmanager
def connection():
    from psycopg import connect
    from psycopg.rows import dict_row
    url=os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError('DATABASE_URL not configured')
    with connect(url, row_factory=dict_row, connect_timeout=5) as conn:
        yield conn

ROW_SQL = "id,source,source_id,name,category,tags,reviewed, ST_Y(geom) AS latitude, ST_X(geom) AS longitude"

def upsert_places(items:list[dict]):
    sql="""INSERT INTO geo_places(source,source_id,name,category,tags,geom,reviewed,fetched_at)
        VALUES (%s,%s,%s,%s,%s::jsonb,ST_SetSRID(ST_MakePoint(%s,%s),4326),false,now())
        ON CONFLICT(source,source_id) DO UPDATE SET
          name=excluded.name,category=excluded.category,tags=excluded.tags,
          geom=excluded.geom,fetched_at=now()
        RETURNING id"""
    import json
    with connection() as conn:
        with conn.cursor() as cur:
            for x in items:
                cur.execute(sql,(x['source'],x['source_id'],x['name'],x['category'],
                   json.dumps(x['tags'],ensure_ascii=False),x['lon'],x['lat']))
    return len(items)

def list_places(category=None,bbox=None,q=None,limit=100,offset=0,reviewed=None):
    where=[];params=[]
    if category:
        where.append('category=%s');params.append(category)
    if q:
        where.append('name ILIKE %s');params.append('%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
    if bbox:
        south,west,north,east=bbox
        where.append('geom && ST_MakeEnvelope(%s,%s,%s,%s,4326)')
        params.extend((west,south,east,north))
    if reviewed is not None:
        where.append('reviewed=%s');params.append(reviewed)
    sql=f'SELECT {ROW_SQL} FROM geo_places'
    if where: sql+=' WHERE '+' AND '.join(where)
    sql+=' ORDER BY id DESC LIMIT %s OFFSET %s';params.extend((limit,offset))
    with connection() as conn:
        return conn.execute(sql,params).fetchall()

def nearby(lat,lon,radius_m,category=None,limit=50):
    # geography gives distances in metres (WGS84 spheroid)
    where=['ST_DWithin(geom::geography,ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography,%s)']
    params=[lon,lat,radius_m]
    if category:
        where.append('category=%s');params.append(category)
    sql=f'''SELECT {ROW_SQL},ROUND(ST_Distance(geom::geography,
        ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography)::numeric,1) AS distance_m
        FROM geo_places WHERE {' AND '.join(where)} ORDER BY distance_m LIMIT %s'''
    with connection() as conn:
        return conn.execute(sql,[lon,lat,*params,limit]).fetchall()

def get_place(place_id:int):
    with connection() as conn:
        return conn.execute(f'SELECT {ROW_SQL} FROM geo_places WHERE id=%s',(place_id,)).fetchone()
