"""Offline operator CLI. Import a bounded OSM area; DO NOT publish until verified."""
import argparse,asyncio,json
from .db import connection
from .facility_osm import fetch_facilities

def upsert(items):
    with connection() as conn:
        for p in items:
            conn.execute('''INSERT INTO campus_facilities
              (source,source_id,name,category,address,opening_hours,accessibility,tags,geom)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,ST_SetSRID(ST_MakePoint(%s,%s),4326))
              ON CONFLICT(source,source_id) DO UPDATE SET
               name=EXCLUDED.name,category=EXCLUDED.category,
               tags=EXCLUDED.tags,geom=EXCLUDED.geom,fetched_at=now(),
               updated_at=now(),
               -- Changed data must be re-reviewed; unchanged data retains approval.
               reviewed=false,public_enabled=false,verified_at=NULL
              WHERE (campus_facilities.name,campus_facilities.category,campus_facilities.tags,
                     campus_facilities.geom) IS DISTINCT FROM
                    (EXCLUDED.name,EXCLUDED.category,EXCLUDED.tags,EXCLUDED.geom)''',
              (p['source'],p['source_id'],p['name'],p['category'],p.get('address'),
               p.get('opening_hours'),p.get('accessibility','unknown'),
               json.dumps(p['tags'],ensure_ascii=False),p['lon'],p['lat']))
    return len(items)

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    imp=sub.add_parser('import-osm')
    imp.add_argument('--bbox',nargs=4,type=float,metavar=('S','W','N','E'),required=True)
    demo=sub.add_parser('seed-demo')
    args=parser.parse_args()
    if args.action=='import-osm':
        items=asyncio.run(fetch_facilities(tuple(args.bbox)))
        print(json.dumps({'fetched':len(items),'saved_unreviewed':upsert(items)}))
    else:
        items=[{'source':'demo','source_id':'fake-001','name':'Cafetería DEMO (no existe)',
                'category':'cafe','lat':-15.827,'lon':-70.019,'tags':{},'opening_hours':None},
               {'source':'demo','source_id':'fake-002','name':'Baño DEMO (no existe)',
                'category':'bathroom','lat':-15.828,'lon':-70.018,'tags':{},'opening_hours':None},
               {'source':'demo','source_id':'fake-003','name':'Copias DEMO (no existe)',
                'category':'copies','lat':-15.826,'lon':-70.017,'tags':{},'opening_hours':None}]
        print(json.dumps({'saved_unreviewed':upsert(items)}))
if __name__=='__main__': main()
