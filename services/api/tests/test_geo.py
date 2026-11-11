import pytest
from fastapi.testclient import TestClient
from app.geo import parse_overpass,validate_bbox,feature,make_overpass_query
from app.main import app

def test_overpass_node_way_and_filter():
    data={'elements':[
      {'type':'node','id':1,'lat':-15.82,'lon':-70.02,'tags':{'amenity':'library','name':'Prueba biblioteca'}},
      {'type':'way','id':2,'center':{'lat':-15.83,'lon':-70.03},'tags':{'amenity':'university'}},
      {'type':'node','id':3,'lat':-15.82,'lon':-70.01,'tags':{'shop':'clothes'}},
    ]}
    r=parse_overpass(data)
    assert len(r)==2
    assert r[0]['category']=='library' and r[0]['source_id']=='node/1'
    assert r[1]['category']=='university' and r[1]['lon']==-70.03

def test_reject_big_bbox():
    with pytest.raises(ValueError): validate_bbox(-90,-180,90,180)
    with pytest.raises(ValueError): validate_bbox(-15,-70,-16,-69)

def test_safe_overpass_query():
    q=make_overpass_query(-15.86,-70.05,-15.78,-69.98)
    assert '[out:json]' in q and 'bus_stop' in q

def test_geojson_coordinates_order():
    row={'id':9,'latitude':-15.82,'longitude':-70.02,'name':'Example','category':'library','source':'demo','source_id':'a','reviewed':False,'tags':{}}
    assert feature(row)['geometry']['coordinates']==[-70.02,-15.82]

def test_categories_and_validation_without_database():
    c=TestClient(app)
    assert c.get('/geo/categories').status_code==200
    assert c.get('/geo/geojson?south=-15.9').status_code==422
    assert c.get('/geo/nearby?lat=91&lon=-70').status_code==422
    assert c.get('/sources').status_code==200

def test_academic_normalization():
    from app.academic import normalize_dspace
    data={'_embedded':{'searchResult':{'_embedded':{'objects':[{'_embedded':{'indexableObject':{'uuid':'abc','metadata':{'dc.title':[{'value':'Tesis de prueba'}],'dc.contributor.author':[{'value':'Autor'}]}}}}]}}}}
    row=normalize_dspace(data)[0]
    assert row['title']=='Tesis de prueba' and row['authors']==['Autor']
