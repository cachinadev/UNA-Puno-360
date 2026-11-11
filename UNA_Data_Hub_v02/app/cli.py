"""Operator commands; imports are intentionally NOT web API endpoints."""
from __future__ import annotations
import argparse
import asyncio
from .academic import sync_dspace,sync_oai
from .db import connection,upsert_places
from .osm import synchronize
from .geo import PUNO_BBOX,validate_bbox

# Clearly fictional data: not actual campus infrastructure or bus stops.
SAMPLES=[
  dict(source='demo',source_id='demo-1',name='Punto ilustrativo A (NO verificado)', category='university',lat=-15.827,lon=-70.019,tags={'demo':'true'}),
  dict(source='demo',source_id='demo-2',name='Punto ilustrativo B (NO verificado)', category='library',lat=-15.826,lon=-70.016,tags={'demo':'true'}),
  dict(source='demo',source_id='demo-3',name='Punto ilustrativo C (NO verificado)',category='bus_stop',lat=-15.830,lon=-70.020,tags={'demo':'true'}),
]

def main():
    parser=argparse.ArgumentParser(description='UNA GeoData administrative commands')
    sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status');sub.add_parser('seed-demo');imp=sub.add_parser('import-osm')
    ds=sub.add_parser('sync-dspace');ds.add_argument('--query',default='quinua');ds.add_argument('--size',type=int,default=10)
    sub.add_parser('sync-oai')
    imp.add_argument('--bbox',nargs=4,type=float,metavar=('SOUTH','WEST','NORTH','EAST'),default=PUNO_BBOX)
    args=parser.parse_args()
    if args.cmd=='status':
        with connection() as conn:
            print(conn.execute('SELECT PostGIS_Version() AS version').fetchone())
    elif args.cmd=='seed-demo':
        print({'inserted_or_updated':upsert_places(SAMPLES),'note':'DEMO only, not verified landmarks'})
    elif args.cmd=='sync-dspace':
        print({'saved':asyncio.run(sync_dspace(args.query,min(25,max(1,args.size))))})
    elif args.cmd=='sync-oai':
        print({'saved':asyncio.run(sync_oai())})
    elif args.cmd=='import-osm':
        validate_bbox(*args.bbox)
        print(asyncio.run(synchronize(tuple(args.bbox))))

if __name__=='__main__':main()
