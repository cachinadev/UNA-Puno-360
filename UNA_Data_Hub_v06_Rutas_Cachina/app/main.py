"""UNA Data Hub 0.2: public read-only geospatial API."""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI,Query,HTTPException
from fastapi.responses import HTMLResponse
from .db import connection,list_places,nearby,get_place
from .geo import feature,validate_bbox,CATEGORIES

from .services import router as services_router
from .community import router as community_router
from .accounts import router as accounts_router
from .accounts_admin import router as admin_router
from .transport import router as transport_router

app=FastAPI(title='UNA Data Hub — GeoAPI',version='0.6.0',description='Puno pilot: public OSM geographic data. Not an official UNA service.')

app.include_router(services_router)
app.include_router(community_router)
app.include_router(accounts_router)
app.include_router(admin_router)
app.include_router(transport_router)

@app.get('/health')
def health():
    try:
        with connection() as conn:
            result=conn.execute('SELECT PostGIS_Version() AS version, (SELECT COUNT(*) FROM geo_places) AS count').fetchone()
        return {'status':'ok','database':'postgresql/postgis','postgis':result['version'],'geo_places':result['count']}
    except Exception:
        raise HTTPException(status_code=503,detail='Database unavailable')

@app.get('/sources')
def sources():
    return [{'id':'osm','name':'OpenStreetMap','url':'https://www.openstreetmap.org/copyright',
            'license':'ODbL; attribution required','data':'geographic points'},
           {'id':'dspace','name':'UNA DSpace (legacy connector)',
            'url':'https://repositorio.unap.edu.pe/server/api','status':'operator import supported'}]

@app.get('/geo/categories')
def categories():
    return {'categories':list(CATEGORIES)}

def parse_query_bbox(south,west,north,east):
    coords=(south,west,north,east)
    if all(v is None for v in coords): return None
    if any(v is None for v in coords):
        raise HTTPException(422,'Specify all of south,west,north,east')
    try: return validate_bbox(*coords,max_area=10.0)
    except ValueError as err: raise HTTPException(422,str(err))

@app.get('/geo/places')
def places(category:str|None=None,q:str|None=Query(None,max_length=100),
    south:float|None=None,west:float|None=None,north:float|None=None,east:float|None=None,
    reviewed:bool|None=None,limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0)):
    bbox=parse_query_bbox(south,west,north,east)
    if category and category not in CATEGORIES: raise HTTPException(422,'Unknown category')
    return {'data':list_places(category,bbox,q,limit,offset,reviewed),
            'limit':limit,'offset':offset,'attribution':'© OpenStreetMap contributors (ODbL)'}

@app.get('/geo/geojson')
def geojson(category:str|None=None,
    south:float|None=None,west:float|None=None,north:float|None=None,east:float|None=None,
    limit:int=Query(200,ge=1,le=1000)):
    bbox=parse_query_bbox(south,west,north,east)
    if category and category not in CATEGORIES: raise HTTPException(422,'Unknown category')
    data=list_places(category,bbox,limit=limit)
    return {'type':'FeatureCollection','features':[feature(p) for p in data],
            'attribution':'© OpenStreetMap contributors (ODbL)'}

@app.get('/geo/nearby')
def near(lat:float=Query(...,ge=-90,le=90),lon:float=Query(...,ge=-180,le=180),
        radius_m:int=Query(500,ge=1,le=5000),category:str|None=None,limit:int=Query(50,ge=1,le=100)):
    if category and category not in CATEGORIES: raise HTTPException(422,'Unknown category')
    return {'data':nearby(lat,lon,radius_m,category,limit),'units':'metres',
            'attribution':'© OpenStreetMap contributors (ODbL)'}

@app.get('/geo/places/{place_id}')
def detail(place_id:int):
    row=get_place(place_id)
    if not row: raise HTTPException(404,'Place not found')
    return row

@app.get('/map',response_class=HTMLResponse,include_in_schema=False)
def map_page():
    return (Path(__file__).resolve().parent.parent/'web'/'map.html').read_text(encoding='utf-8')

@app.get('/records')
def records(q:str|None=Query(None,max_length=120),source:str|None=None,
  limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
    from .academic import get_records
    if source and source not in ('dspace','oai'):
        raise HTTPException(422,'Unknown academic source')
    return {'data':get_records(q,source,limit,offset),'limit':limit,'offset':offset}
