'Public read-only library and dining endpoints. No personal student data.'
from __future__ import annotations
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from .db import connection

router=APIRouter(tags=['Servicios estudiantiles'])
LIBRARY_URL='https://biblioteca.unap.edu.pe/opac_css/'
DINING_URL='https://comedor.unap.edu.pe/'

def rows(sql: str, params=()):
    with connection() as conn:
        return conn.execute(sql, params).fetchall()

def one(sql: str, params=()):
    with connection() as conn:
        return conn.execute(sql, params).fetchone()

@router.get('/library/info')
def library_info():
    return {'official_url': LIBRARY_URL,'catalog_provider':'PMB',
      'api_catalog_confirmed':False,'availability_policy':'not_verified_by_default',
      'note':'Datos locales importados con trazabilidad; no representa inventario en vivo.'}

@router.get('/library/branches')
def branches():
    return {'data':rows('''SELECT code,name,address,opening_hours,source_url,verified,
        ST_Y(geom) AS latitude,ST_X(geom) AS longitude FROM library_branches ORDER BY name''')}

@router.get('/library/books')
def books(q:str|None=Query(None,max_length=100),branch:str|None=Query(None,max_length=40),
          limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
    filters=[];args=[]
    if q:
        filters.append('(title ILIKE %s OR array_to_string(authors, %s) ILIKE %s OR subject ILIKE %s)')
        term='%'+q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        args.extend((term,' ',term,term))
    if branch: filters.append('branch_code=%s');args.append(branch)
    sql='''SELECT external_id,title,authors,publication_year,isbn,subject,branch_code,
              catalog_url,availability,verified,updated_at FROM library_books'''
    if filters:sql+=' WHERE '+' AND '.join(filters)
    sql+=' ORDER BY title LIMIT %s OFFSET %s';args.extend((limit,offset))
    return {'data':rows(sql,args),'limit':limit,'offset':offset,'source':LIBRARY_URL,
            'warning':'Disponibilidad no verificada salvo integración oficial.'}

@router.get('/library/books/{external_id}')
def book(external_id:str):
    item=one('''SELECT external_id,title,authors,publication_year,isbn,subject,
       branch_code,catalog_url,availability,verified,updated_at FROM library_books WHERE external_id=%s''',(external_id,))
    if not item:raise HTTPException(404,'Registro no encontrado')
    return item

@router.get('/dining/info')
def dining_info():
    return {'official_url':DINING_URL,'student_login_required_for_private_services':True,
            'menus_official_api_confirmed':False,
            'warning':'No se recopilan padrones, evaluaciones socioeconómicas o resultados personales.'}

@router.get('/dining/locations')
def locations():
    return {'data':rows('''SELECT code,name,address,source_url,verified,
         ST_Y(geom) AS latitude,ST_X(geom) AS longitude FROM dining_locations ORDER BY name''')}

@router.get('/dining/menus')
def menus(day:date|None=None,location:str|None=Query(None,max_length=40),
          limit:int=Query(30,ge=1,le=100)):
    conditions=[];args=[]
    if day:conditions.append('service_date=%s');args.append(day)
    if location:conditions.append('location_code=%s');args.append(location)
    sql='''SELECT location_code,service_date,meal_type,description,allergens,source_url,
         verified,updated_at FROM dining_menus'''
    if conditions:sql+=' WHERE '+' AND '.join(conditions)
    sql+=' ORDER BY service_date DESC,meal_type LIMIT %s';args.append(limit)
    return {'data':rows(sql,args),'warning':'No publicar menús como oficiales sin verificación.'}

@router.get('/dining/announcements')
def announcements(limit:int=Query(20,ge=1,le=100)):
    return {'data':rows('''SELECT external_id,title,body,published_on,deadline,url,verified
            FROM dining_announcements ORDER BY published_on DESC NULLS LAST LIMIT %s''',(limit,)),
            'official_url':DINING_URL}
