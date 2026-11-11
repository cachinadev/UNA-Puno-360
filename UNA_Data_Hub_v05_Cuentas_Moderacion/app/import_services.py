'Manual, reviewable CSV imports; no unauthenticated write API.'
from __future__ import annotations
import csv
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
from .db import connection

TABLES={
 'branches':('library_branches',('code','name','address','opening_hours','source_url','verified')),
 'books':('library_books',('external_id','title','authors','publication_year','isbn','subject','branch_code','catalog_url','availability','verified')),
 'locations':('dining_locations',('code','name','address','source_url','verified')),
 'menus':('dining_menus',('location_code','service_date','meal_type','description','allergens','source_url','verified')),
 'announcements':('dining_announcements',('external_id','title','body','published_on','deadline','url','verified')),
}
REQUIRED={
 'branches':('code','name','source_url'), 'books':('external_id','title','catalog_url'),
 'locations':('code','name','source_url'),
 'menus':('location_code','service_date','meal_type','description','source_url'),
 'announcements':('external_id','title','url')}
ARRAYS={'authors','allergens'}
DATES={'service_date','published_on','deadline'}
BOOLS={'verified'}

def validate_row(kind,row):
    if kind not in TABLES:raise ValueError('Tipo de importación inválido')
    for name in REQUIRED[kind]:
        if not (row.get(name) or '').strip():raise ValueError(f'Falta {name}')
    cols=TABLES[kind][1]
    out={}
    for c in cols:
        v=(row.get(c) or '').strip()
        if c in ('source_url','catalog_url','url') and v:
            parsed=urlparse(v)
            if parsed.scheme!='https' or not parsed.hostname:raise ValueError(f'{c}: solo HTTPS')
        if c in BOOLS:out[c]=v.lower() in ('true','1','yes','si','sí')
        elif c in ARRAYS:out[c]=[x.strip() for x in v.split('|') if x.strip()]
        elif c in DATES:out[c]=date.fromisoformat(v) if v else None
        elif c=='publication_year':out[c]=int(v) if v else None
        else:out[c]=v or None
    if kind=='books':
        out['availability']=out['availability'] or 'not_verified'
        if out['availability'] not in ('available','unavailable','unknown','not_verified'):
            raise ValueError('availability inválido')
        if not out['verified'] and out['availability'] in ('available','unavailable'):
            raise ValueError('No declarar disponibilidad sin verificación')
    if kind=='menus' and out['meal_type'] not in ('breakfast','lunch','dinner'):
        raise ValueError('meal_type inválido')
    return out

def import_csv(kind,path,dry_run=False):
    if kind not in TABLES: raise ValueError('Tipo inválido')
    file=Path(path)
    if file.stat().st_size>2_000_000:raise ValueError('CSV demasiado grande (>2MB)')
    with file.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames:raise ValueError('CSV sin cabeceras')
        parsed=[validate_row(kind,r) for r in reader]
    if len(parsed)>10000:raise ValueError('Límite 10000 filas')
    if dry_run:return len(parsed)
    table,cols=TABLES[kind]
    # Table and column identifiers are whitelisted constants; values are bound.
    conflict={'branches':'code','books':'external_id','locations':'code',
              'menus':'location_code,service_date,meal_type','announcements':'external_id'}[kind]
    update=','.join(f'{c}=excluded.{c}' for c in cols if c not in conflict.split(','))
    sql=f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['%s']*len(cols))}) ON CONFLICT ({conflict}) DO UPDATE SET {update},updated_at=now()"
    with connection() as conn:
        with conn.cursor() as cur:
            for row in parsed:cur.execute(sql,[row[c] for c in cols])
    return len(parsed)
