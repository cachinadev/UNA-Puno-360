"""UNA Conecta Campus Finder: public curated search and admin-reviewed facilities."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from .db import connection
from .accounts import current_account
from .accounts_admin import require_role

router=APIRouter(prefix='/facilities',tags=['Campus Services Finder'])
CATEGORIES=('food','cafe','printing','copies','bathroom','medical','medical_tests','pharmacy','water','wifi','atm','other')
CATEGORY_LABELS={
 'food':'Comida y menús','cafe':'Cafeterías','printing':'Impresiones',
 'copies':'Fotocopias','bathroom':'Baños','medical':'Centro médico',
 'medical_tests':'Análisis clínicos','pharmacy':'Farmacias',
 'water':'Agua potable','wifi':'Wi-Fi','atm':'Cajeros','other':'Otros servicios'}
SELECT_COLUMNS='''id,source,source_id,name,category,description,address,location_hint,
 opening_hours,contact_public,accessibility,cost_info,tags,reviewed,verified_at,
 updated_at,ST_Y(geom) AS lat,ST_X(geom) AS lon'''

def as_feature(item):
    properties={k:v for k,v in item.items() if k not in ('lat','lon','id')}
    return {'type':'Feature','id':item['id'],
      'geometry':{'type':'Point','coordinates':[item['lon'],item['lat']]},
      'properties':properties}

def public_facility_query(category=None,q=None,accessible=None,only_reviewed=True,
                          lat=None,lon=None,radius_m=None,limit=50,offset=0):
    filters=['public_enabled=true','source<>\'demo\''];params=[]
    if only_reviewed: filters.append('reviewed=true')
    if category:
        filters.append('category=%s');params.append(category)
    if q:
        filters.append('(name ILIKE %s OR coalesce(description,\'\') ILIKE %s)')
        escaped=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
        params.extend(['%'+escaped+'%']*2)
    if accessible:
        filters.append('accessibility=%s');params.append(accessible)
    pos=None
    if lat is not None and lon is not None:
        pos='ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography'
        if radius_m is not None:
            filters.append(f'ST_DWithin(geom::geography,{pos},%s)')
            params.extend([lon,lat,radius_m])
    cols=SELECT_COLUMNS
    if pos:
        cols+=f',ROUND(ST_Distance(geom::geography,{pos})::numeric,1) AS distance_m'
        # SELECT's placeholders come before WHERE placeholders.
        params=[lon,lat]+params
    query=f"SELECT {cols} FROM campus_facilities WHERE {' AND '.join(filters)}"
    query+=' ORDER BY '+('distance_m ASC,id ASC' if pos else 'name ASC,id ASC')+' LIMIT %s OFFSET %s'
    params.extend([limit,offset])
    with connection() as conn:
        return conn.execute(query,params).fetchall()

@router.get('/categories')
def categories():
    return {'categories':[{'id':key,'label':CATEGORY_LABELS[key]} for key in CATEGORIES]}

@router.get('/search')
def search(category:str|None=None,q:str|None=Query(default=None,max_length=100),
          accessible:Literal['yes','limited','no','unknown']|None=None,
          lat:float|None=Query(default=None,ge=-90,le=90),
          lon:float|None=Query(default=None,ge=-180,le=180),
          radius_m:int|None=Query(default=None,ge=10,le=5000),
          limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):
    if category and category not in CATEGORIES:raise HTTPException(422,'Unknown category')
    if (lat is None)!=(lon is None) or (radius_m is not None and lat is None):
        raise HTTPException(422,'lat and lon required together for proximity queries')
    rows=public_facility_query(category,q,accessible,True,lat,lon,radius_m,limit,offset)
    return {'data':rows,'limit':limit,'offset':offset,'distance_unit':'metres',
      'note':'Only operator-approved facilities; opening_hours may be unverified or outdated',
      'attribution':'© OpenStreetMap contributors (ODbL) where applicable'}

@router.get('/geojson')
def geojson(category:str|None=None,
            lat:float|None=Query(default=None,ge=-90,le=90),
            lon:float|None=Query(default=None,ge=-180,le=180),
            radius_m:int|None=Query(default=None,ge=10,le=5000),
            limit:int=Query(200,ge=1,le=500)):
    if category and category not in CATEGORIES:raise HTTPException(422,'Unknown category')
    if (lat is None)!=(lon is None) or (radius_m is not None and lat is None):
        raise HTTPException(422,'lat and lon required together')
    rows=public_facility_query(category=category,lat=lat,lon=lon,radius_m=radius_m,limit=limit)
    return {'type':'FeatureCollection','features':[as_feature(x) for x in rows],
       'attribution':'© OpenStreetMap contributors (ODbL) where applicable'}


class FacilityIn(BaseModel):
    name:str=Field(min_length=2,max_length=180)
    category:str
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    description:str|None=Field(default=None,max_length=1200)
    address:str|None=Field(default=None,max_length=300)
    location_hint:str|None=Field(default=None,max_length=200)
    opening_hours:str|None=Field(default=None,max_length=160)
    contact_public:str|None=Field(default=None,max_length=180)
    accessibility:Literal['yes','limited','no','unknown']='unknown'
    cost_info:str|None=Field(default=None,max_length=180)

class PublishIn(BaseModel):
    publish:bool
    reason:str=Field(min_length=5,max_length=500)

@router.post('/admin',status_code=201)
def create_facility(data:FacilityIn,user=Depends(current_account)):
    require_role(user,('admin',))
    if data.category not in CATEGORIES:raise HTTPException(422,'Unknown category')
    import uuid
    sid=str(uuid.uuid4())
    with connection() as conn:
        row=conn.execute('''INSERT INTO campus_facilities
          (source,source_id,name,category,description,address,location_hint,opening_hours,
           contact_public,accessibility,cost_info,geom,reviewed,public_enabled)
          VALUES ('operator',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
              ST_SetSRID(ST_MakePoint(%s,%s),4326),false,false)
          RETURNING id''',
          (sid,data.name,data.category,data.description,data.address,data.location_hint,
           data.opening_hours,data.contact_public,data.accessibility,data.cost_info,data.lon,data.lat)).fetchone()
        conn.execute('INSERT INTO campus_facility_audit(actor_id,facility_id,action) VALUES (%s,%s,%s)',
                (user['id'],row['id'],'create'))
    return {'id':row['id'],'published':False}

@router.put('/admin/{facility_id}')
def edit_facility(facility_id:int,data:FacilityIn,user=Depends(current_account)):
    require_role(user,('admin',))
    if data.category not in CATEGORIES:raise HTTPException(422,'Unknown category')
    with connection() as conn:
        row=conn.execute('SELECT id,source FROM campus_facilities WHERE id=%s FOR UPDATE',(facility_id,)).fetchone()
        if not row:raise HTTPException(404,'Facility not found')
        if row['source']=='demo':raise HTTPException(403,'Demo facilities cannot be edited for publishing')
        conn.execute('''UPDATE campus_facilities SET name=%s,category=%s,description=%s,address=%s,
            location_hint=%s,opening_hours=%s,contact_public=%s,accessibility=%s,cost_info=%s,
            geom=ST_SetSRID(ST_MakePoint(%s,%s),4326),reviewed=false,public_enabled=false,
            verified_at=NULL,updated_at=now() WHERE id=%s''',
            (data.name,data.category,data.description,data.address,data.location_hint,
             data.opening_hours,data.contact_public,data.accessibility,data.cost_info,
             data.lon,data.lat,facility_id))
        conn.execute('INSERT INTO campus_facility_audit(actor_id,facility_id,action) VALUES (%s,%s,%s)',
                     (user['id'],facility_id,'edit_requires_review'))
    return {'id':facility_id,'published':False,'requires_review':True}

@router.get('/admin/pending')
def pending(limit:int=Query(50,ge=1,le=100),user=Depends(current_account)):
    require_role(user,('admin','moderator'))
    with connection() as conn:
        data=conn.execute(f'''SELECT {SELECT_COLUMNS} FROM campus_facilities
          WHERE reviewed=false OR public_enabled=false ORDER BY updated_at DESC LIMIT %s''',(limit,)).fetchall()
    return {'data':data}

@router.post('/admin/{facility_id}/review')
def review(facility_id:int,body:PublishIn,user=Depends(current_account)):
    require_role(user,('admin','moderator'))
    with connection() as conn:
        facility=conn.execute('SELECT id,source FROM campus_facilities WHERE id=%s FOR UPDATE',(facility_id,)).fetchone()
        if not facility:raise HTTPException(404,'Facility not found')
        if facility['source']=='demo' and body.publish:
            raise HTTPException(403,'Demo records cannot be published')
        conn.execute('''UPDATE campus_facilities SET reviewed=%s,public_enabled=%s,
          verified_at=CASE WHEN %s THEN now() ELSE NULL END,updated_at=now() WHERE id=%s''',
             (body.publish,body.publish,body.publish,facility_id))
        conn.execute('''INSERT INTO campus_facility_audit(actor_id,facility_id,action,details)
          VALUES (%s,%s,%s,%s::jsonb)''',(user['id'],facility_id,
           'publish' if body.publish else 'unpublish',json.dumps({'reason':body.reason})))
    return {'id':facility_id,'published':body.publish}

@router.get('/{facility_id}')
def detail(facility_id:int):
    with connection() as conn:
        row=conn.execute(f'''SELECT {SELECT_COLUMNS} FROM campus_facilities
           WHERE id=%s AND reviewed=true AND public_enabled=true AND source<>'demo' ''',(facility_id,)).fetchone()
    if not row:raise HTTPException(404,'Facility unavailable')
    return row

