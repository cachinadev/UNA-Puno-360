"""UNA Rutas public read-only API and signed ingestion bridge for CACHINA fleet feeds.
Provider integration contracts are configurable; no undocumented KUNTUR/Rutas endpoints assumed.
"""
from __future__ import annotations
import hashlib,hmac,json,os
from datetime import datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter, HTTPException, Header, Request, Query
from pydantic import BaseModel,Field,field_validator
from .db import connection
router=APIRouter(prefix='/transport',tags=['UNA Rutas'])

def utcnow():return datetime.now(timezone.utc)

def require_bridge_token(authorization:str|None):
    expected=os.environ.get('TRANSPORT_BRIDGE_TOKEN','')
    if len(expected)<32 or not authorization or not authorization.startswith('Bearer ') or not hmac.compare_digest(authorization[7:],expected):
        raise HTTPException(401,'Bridge authorization required')

def verify_signature(body:bytes,timestamp:str|None,signature:str|None):
    secret=os.environ.get('TRANSPORT_WEBHOOK_SECRET','')
    if len(secret)<32 or not timestamp or not signature:
        raise HTTPException(401,'Signed webhook required')
    try:
        ts=int(timestamp)
    except (ValueError,TypeError):raise HTTPException(401,'Invalid timestamp')
    if abs(int(utcnow().timestamp())-ts)>300:raise HTTPException(401,'Timestamp outside permitted window')
    digest=hmac.new(secret.encode(),f'{timestamp}.'.encode()+body,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature.removeprefix('sha256='),digest):
        raise HTTPException(401,'Signature mismatch')

class Position(BaseModel):
    vehicle_id:str=Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_\-:.]+$')
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    speed_kph:float|None=Field(default=None,ge=0,le=180)
    heading:float|None=Field(default=None,ge=0,lt=360)
    observed_at:datetime
    @field_validator('observed_at')
    @classmethod
    def tz_required(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('Timezone required')
        if v>utcnow()+timedelta(minutes=2):raise ValueError('Future timestamp')
        return v
class Batch(BaseModel):
    provider:Literal['kuntur','rutas','demo']
    tenant:str=Field(min_length=1,max_length=60)
    positions:list[Position]=Field(min_length=1,max_length=200)

def persist(batch:Batch):
    accepted=ignored=0
    with connection() as conn:
        for p in batch.positions:
            # Whitelist provisioned vehicle mapping; unknown vehicles NEVER auto-enrolled.
            row=conn.execute("""SELECT id FROM transport_vehicles WHERE provider=%s AND tenant=%s AND provider_vehicle_id=%s AND active=true""",
                    (batch.provider,batch.tenant,p.vehicle_id)).fetchone()
            if not row:
                ignored+=1;continue
            # Upsert only newer observations; drop out-of-order packets; cap stale data (24 h).
            if p.observed_at<utcnow()-timedelta(hours=24):ignored+=1;continue
            result=conn.execute("""INSERT INTO transport_positions(vehicle_id,position,speed_kph,heading,observed_at,received_at)
             VALUES (%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s,%s,now())
             ON CONFLICT(vehicle_id) DO UPDATE SET position=EXCLUDED.position,speed_kph=EXCLUDED.speed_kph,
               heading=EXCLUDED.heading,observed_at=EXCLUDED.observed_at,received_at=now()
             WHERE transport_positions.observed_at < EXCLUDED.observed_at RETURNING vehicle_id""",
             (row['id'],p.lon,p.lat,p.speed_kph,p.heading,p.observed_at)).fetchone()
            if result:accepted+=1
            else:ignored+=1
        conn.execute('INSERT INTO transport_ingest_audit(provider,tenant,accepted_count,ignored_count) VALUES (%s,%s,%s,%s)',(batch.provider,batch.tenant,accepted,ignored))
    return {'accepted':accepted,'ignored':ignored}

@router.post('/internal/ingest')
def ingest(batch:Batch,authorization:str|None=Header(default=None)):
    require_bridge_token(authorization)
    return persist(batch)

@router.post('/internal/webhook')
async def webhook(request:Request,x_transport_timestamp:str|None=Header(default=None),x_transport_signature:str|None=Header(default=None)):
    body=await request.body()
    if len(body)>256_000:raise HTTPException(413,'Payload too large')
    verify_signature(body,x_transport_timestamp,x_transport_signature)
    try: batch=Batch.model_validate_json(body)
    except Exception:raise HTTPException(422,'Invalid payload')
    return persist(batch)

@router.get('/routes')
def routes(limit:int=Query(100,ge=1,le=200)):
    with connection() as conn:
        rows=conn.execute("""SELECT id,name,service_type,description,official_verified,
          ST_AsGeoJSON(shape)::json AS geometry FROM transport_routes
          WHERE tenant='una' AND public_enabled=true ORDER BY name LIMIT %s""",(limit,)).fetchall()
    return {'data':rows,'note':'Only routes explicitly approved for publication'}

@router.get('/routes/{route_id}/stops')
def stops(route_id:str):
    with connection() as conn:
        rows=conn.execute("""SELECT s.id,s.name,s.stop_order,ST_Y(s.position) AS lat,ST_X(s.position) AS lon,
          s.official_verified FROM transport_stops s JOIN transport_routes r ON r.id=s.route_id
          WHERE s.route_id=%s AND r.public_enabled=true AND r.tenant='una' ORDER BY s.stop_order""",(route_id,)).fetchall()
    return {'data':rows}

@router.get('/vehicles')
def vehicles(route_id:str|None=None):
    with connection() as conn:
        rows=conn.execute("""SELECT v.id,v.public_label,v.route_id,v.provider,
          ST_Y(p.position) AS lat,ST_X(p.position) AS lon,p.speed_kph,p.heading,p.observed_at,
          EXTRACT(EPOCH FROM now()-p.observed_at)::int AS age_seconds
          FROM transport_vehicles v JOIN transport_routes r ON r.id=v.route_id
          JOIN transport_positions p ON p.vehicle_id=v.id
          WHERE v.tenant='una' AND v.active AND v.public_enabled AND r.public_enabled
            AND p.observed_at>now()-interval '5 minutes' AND (%s::text IS NULL OR v.route_id=%s)
          ORDER BY v.public_label LIMIT 200""",(route_id,route_id)).fetchall()
    return {'data':rows,'stale_after_seconds':300}

@router.get('/vehicles/geojson')
def vehicles_geojson():
    data=vehicles()['data']
    return {'type':'FeatureCollection','features':[
        {'type':'Feature','id':v['id'],'geometry':{'type':'Point','coordinates':[v['lon'],v['lat']]},
         'properties':{k:v[k] for k in ('public_label','route_id','provider','speed_kph','heading','observed_at','age_seconds')}} for v in data]}
