"""Optional polling bridge: map an authorized provider JSON endpoint to UNA ingestion.
Set a documented HTTPS URL supplied by the provider administrator; no endpoint discovery or scraping.
"""
from __future__ import annotations
import os,sys,json,ipaddress,socket
from urllib.parse import urlparse
from datetime import datetime,timezone
import httpx

def safe_url(url):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError('A valid HTTPS provider URL is required')
    allowed=[x.strip().lower() for x in os.getenv('TRANSPORT_ALLOWED_HOSTS','').split(',') if x.strip()]
    if p.hostname.lower() not in allowed:
        raise ValueError('Provider host not allowlisted')
    # Domain resolution is verified here, but pinning/network policy is needed against DNS rebinding.
    for entry in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
        addr=ipaddress.ip_address(entry[4][0])
        if not addr.is_global:raise ValueError('Provider resolves to private/non-public address')
    return url

def normalize(payload,provider,tenant):
    # Expects explicit adapter contract: {vehicles:[{id,lat,lon,observed_at,speed_kph?,heading?}]}
    raw=payload.get('vehicles',[])
    if not isinstance(raw,list):raise ValueError('Expected vehicles array')
    items=[]
    for x in raw[:200]:
        items.append({'vehicle_id':str(x['id']),'lat':x['lat'],'lon':x['lon'],
        'observed_at':x['observed_at'],'speed_kph':x.get('speed_kph'),'heading':x.get('heading')})
    return {'provider':provider,'tenant':tenant,'positions':items}

def run():
    provider=os.environ.get('TRANSPORT_PROVIDER','')
    if provider not in ('kuntur','rutas'):raise ValueError('Provider must be kuntur or rutas')
    url=safe_url(os.environ.get('TRANSPORT_PROVIDER_URL',''))
    api_key=os.environ.get('TRANSPORT_PROVIDER_TOKEN','')
    bridge=os.environ.get('TRANSPORT_BRIDGE_TOKEN','')
    if not api_key or len(bridge)<32:raise ValueError('Missing provider/bridge token')
    # Explicit trust of provider schema; customize normalize() when actual API contract is known.
    with httpx.Client(timeout=10,follow_redirects=False,trust_env=False) as client:
        res=client.get(url,headers={'Authorization':f'Bearer {api_key}','Accept':'application/json'})
        res.raise_for_status()
        normalized=normalize(res.json(),provider,os.environ.get('TRANSPORT_TENANT','una'))
        if not normalized['positions']:return {'accepted':0,'ignored':0,'note':'No positions'}
        local=os.environ.get('TRANSPORT_HUB_URL','http://127.0.0.1:8000/transport/internal/ingest')
        # Intentionally allow HTTP only to local loopback; use HTTPS for remote ingress.
        dest=urlparse(local)
        if dest.scheme!='https' and not (dest.scheme=='http' and dest.hostname in ('127.0.0.1','localhost','api')):
            raise ValueError('Hub must use HTTPS unless local/Docker network')
        resp=client.post(local,json=normalized,headers={'Authorization':f'Bearer {bridge}'})
        resp.raise_for_status()
        return resp.json()
if __name__=='__main__':
    try:print(json.dumps(run(),ensure_ascii=False))
    except Exception as e:
        print(f'Bridge failed: {type(e).__name__}: {e}',file=sys.stderr);sys.exit(1)
