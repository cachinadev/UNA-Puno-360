"""Pure transformation functions, without DB/network dependencies."""
from __future__ import annotations
from math import isfinite

CATEGORIES = {
    "library": [("amenity", "library")],
    "university": [("amenity", "university")],
    "college": [("amenity", "college")],
    "bus_stop": [("highway", "bus_stop")],
    "bus_station": [("amenity", "bus_station")],
    "hospital": [("amenity", "hospital")],
    "clinic": [("amenity", "clinic")],
    "pharmacy": [("amenity", "pharmacy")],
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "sports": [("leisure", "sports_centre")],
}
# Puno pilot bounds; configurable using CLI arguments; NOT a campus polygon.
PUNO_BBOX = (-15.86, -70.05, -15.78, -69.98) # S,W,N,E

def validate_bbox(south:float,west:float,north:float,east:float,max_area:float=0.06):
    vals=(south,west,north,east)
    if not all(isfinite(x) for x in vals):
        raise ValueError("Coordinates must be finite")
    if not (-90<=south<north<=90 and -180<=west<east<=180):
        raise ValueError("Invalid bbox: require south<north and west<east")
    if (north-south)*(east-west)>max_area:
        raise ValueError("Bounding box too large for public Overpass pilot")
    return vals

def classify(tags:dict):
    for category,pairs in CATEGORIES.items():
        if any(tags.get(k)==v for k,v in pairs):
            return category
    return "other"

def make_overpass_query(south,west,north,east):
    validate_bbox(south,west,north,east)
    # Fixed, audited tag whitelist. Never interpolate user-supplied Overpass syntax.
    options='|'.join(sorted(set(value for pairs in CATEGORIES.values() for _,value in pairs)))
    return (f'[out:json][timeout:25];('
        f'nwr["amenity"~"^(university|college|library|bus_station|hospital|clinic|pharmacy|restaurant|cafe)$"]({south},{west},{north},{east});'
        f'nwr["highway"="bus_stop"]({south},{west},{north},{east});'
        f'nwr["leisure"="sports_centre"]({south},{west},{north},{east});'
        f');out center tags;')

def parse_overpass(payload:dict):
    out=[]
    for item in payload.get('elements',[]):
        if not isinstance(item,dict) or item.get('type') not in ('node','way','relation'):
            continue
        tags=item.get('tags') or {}
        if not isinstance(tags,dict):
            continue
        location=item if item['type']=='node' else item.get('center') or {}
        lat,lon=location.get('lat'),location.get('lon')
        if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)) or not isfinite(lat) or not isfinite(lon):
            continue
        if not (-90<=lat<=90 and -180<=lon<=180):
            continue
        sid=item.get('id')
        if not isinstance(sid,int):
            continue
        category=classify(tags)
        if category=='other':
            continue
        name=(tags.get('name') or tags.get('name:es') or f'{category} OSM {sid}')
        out.append({'source':'osm','source_id':f'{item["type"]}/{sid}',
            'name':str(name)[:250],'category':category,'tags':tags,
            'lat':float(lat),'lon':float(lon)})
    return out

def feature(row:dict):
    return {'type':'Feature','id':row['id'],
            'geometry':{'type':'Point','coordinates':[row['longitude'],row['latitude']]},
            'properties':{'name':row['name'],'category':row['category'],
                'source':row['source'],'source_id':row['source_id'],
                'reviewed':row['reviewed'], 'tags':row['tags']}}
