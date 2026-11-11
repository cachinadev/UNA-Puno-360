"""Explicit, operator-run Overpass import. No public untrusted query proxy."""
from __future__ import annotations
import os
import httpx
from .geo import parse_overpass,make_overpass_query,validate_bbox
from .db import upsert_places

async def fetch_osm(bbox:tuple[float,float,float,float]):
    validate_bbox(*bbox)
    url=os.getenv('OVERPASS_URL','https://overpass-api.de/api/interpreter')
    if url != 'https://overpass-api.de/api/interpreter':
        raise ValueError('Only approved Overpass endpoint is permitted in pilot')
    headers={'User-Agent':os.environ.get('OVERPASS_USER_AGENT','UNADataHubResearch/0.2 (pilot; configure contact)')}
    async with httpx.AsyncClient(timeout=httpx.Timeout(45.0), follow_redirects=False, headers=headers) as client:
        response=await client.post(url,data={'data':make_overpass_query(*bbox)})
        response.raise_for_status()
        if len(response.content)>8_000_000:
            raise ValueError('Response too large; use a smaller bbox')
        return parse_overpass(response.json())

async def synchronize(bbox):
    features=await fetch_osm(bbox)
    return {'downloaded':len(features),'upserted':upsert_places(features),'bbox':bbox}
