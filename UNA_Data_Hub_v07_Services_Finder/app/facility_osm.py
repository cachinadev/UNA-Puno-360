"""Operator-only OpenStreetMap importer for public facilities (never a public Overpass proxy)."""
from __future__ import annotations
import os
import httpx
from .geo import validate_bbox

# Meaningful classification from standardized OSM tags, conservative for medical testing.
def classify(tags: dict) -> str | None:
    amenity = tags.get('amenity', '')
    shop = tags.get('shop', '')
    healthcare = tags.get('healthcare', '')
    if amenity == 'toilets': return 'bathroom'
    if amenity == 'drinking_water': return 'water'
    if amenity == 'pharmacy' or shop == 'chemist' or healthcare == 'pharmacy': return 'pharmacy'
    if amenity in ('clinic', 'hospital', 'doctors', 'dentist') or healthcare in ('clinic','doctor','hospital','dentist'): return 'medical'
    if healthcare == 'laboratory': return 'medical_tests'
    if shop in ('copyshop', 'printshop') or amenity == 'copyshop': return 'printing'
    if amenity in ('restaurant', 'fast_food', 'food_court') or shop in ('bakery','convenience'): return 'food'
    if amenity in ('cafe', 'ice_cream'): return 'cafe'
    if amenity == 'atm': return 'atm'
    if tags.get('internet_access') == 'wlan' and amenity in ('internet_cafe','library'): return 'wifi'
    return None

def import_name(tags: dict, category: str) -> str:
    return (tags.get('name') or {
        'bathroom':'Baño público','water':'Agua potable','medical':'Centro de salud',
        'medical_tests':'Laboratorio clínico','printing':'Impresiones y copias',
        'pharmacy':'Farmacia','food':'Alimentos','cafe':'Cafetería','atm':'Cajero automático','wifi':'Zona Wi-Fi'
    }.get(category,'Servicio'))[:180]

def normalize(elements: list[dict]) -> list[dict]:
    out=[]
    for e in elements:
        tags=e.get('tags') or {}
        category=classify(tags)
        center=e.get('center') or e
        lat,lon=center.get('lat'),center.get('lon')
        if category is None or not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)):
            continue
        if not (-90<=lat<=90 and -180<=lon<=180): continue
        if e.get('type') not in ('node','way','relation') or not isinstance(e.get('id'),int): continue
        out.append({'source':'osm','source_id':f"{e['type']}/{e['id']}",
             'name':import_name(tags,category),'category':category,
             'lat':lat,'lon':lon,'tags':tags,
             'opening_hours':tags.get('opening_hours'),
             'accessibility':{'yes':'yes','limited':'limited','no':'no'}.get(tags.get('wheelchair'),'unknown'),
             'address':tags.get('addr:full') or ' '.join(filter(None,[tags.get('addr:street'),tags.get('addr:housenumber')])) or None})
    return out

def query_bbox(south:float,west:float,north:float,east:float)->str:
    validate_bbox(south,west,north,east,max_area=0.15)
    bbox=f'({south},{west},{north},{east})'
    clauses=[
      '["amenity"~"^(toilets|drinking_water|pharmacy|clinic|hospital|doctors|dentist|restaurant|fast_food|food_court|cafe|ice_cream|atm|copyshop)$"]',
      '["shop"~"^(copyshop|printshop|chemist|bakery|convenience)$"]',
      '["healthcare"~"^(laboratory|clinic|doctor|hospital|dentist|pharmacy)$"]'
    ]
    return '[out:json][timeout:25];('+''.join(f'nwr{c}{bbox};' for c in clauses)+');out center tags;'

async def fetch_facilities(bbox:tuple[float,float,float,float]):
    url=os.getenv('OVERPASS_URL','https://overpass-api.de/api/interpreter')
    if url!='https://overpass-api.de/api/interpreter':
        raise ValueError('Overpass URL not approved in this pilot')
    headers={'User-Agent':os.environ.get('OVERPASS_USER_AGENT','UNADataHubResearch/0.7 (configure an operator contact)')}
    async with httpx.AsyncClient(timeout=50,headers=headers,follow_redirects=False) as client:
        r=await client.post(url,data={'data':query_bbox(*bbox)})
        r.raise_for_status()
        if len(r.content)>5_000_000: raise ValueError('Overpass response too large')
        return normalize(r.json().get('elements',[]))
