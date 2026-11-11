from fastapi.testclient import TestClient
from app.main import app
from app.facility_osm import classify,normalize,query_bbox
from app.facilities import as_feature

client=TestClient(app)

def test_classification():
    assert classify({'amenity':'toilets'})=='bathroom'
    assert classify({'shop':'copyshop'})=='printing'
    assert classify({'healthcare':'laboratory'})=='medical_tests'
    assert classify({'amenity':'clinic'})=='medical'
    assert classify({'amenity':'restaurant'})=='food'
    assert classify({'shop':'supermarket'}) is None

def test_normalize_excludes_missing_coordinates_and_unknown():
    data=[{'type':'node','id':10,'lat':-15.8,'lon':-70,'tags':{'amenity':'toilets'}},
          {'type':'way','id':20,'tags':{'amenity':'cafe'}}]
    out=normalize(data)
    assert len(out)==1 and out[0]['source_id']=='node/10'

def test_bbox_validation():
    assert 'nwr' in query_bbox(-15.84,-70.03,-15.81,-70.00)

def test_invalid_bbox():
    import pytest
    with pytest.raises(ValueError):query_bbox(-15.9,-70.1,-15.0,-69.0)

def test_geojson_feature():
    feat=as_feature({'id':2,'name':'Prueba','lat':-15.8,'lon':-70.01,'category':'copies'})
    assert feat['geometry']['coordinates']==[-70.01,-15.8]
    assert 'lat' not in feat['properties']

def test_category_api():
    response=client.get('/facilities/categories')
    assert response.status_code==200
    assert any(e['id']=='bathroom' for e in response.json()['categories'])

def test_validations_without_database():
    for path in ['/facilities/search?category=not-real', '/facilities/search?lat=-15.8',
                 '/facilities/search?radius_m=1000', '/facilities/geojson?lat=-15.8']:
        assert client.get(path).status_code==422

def test_admin_requires_auth():
    # With secure default disabled, endpoint cannot be accessed anonymously.
    assert client.get('/facilities/admin/pending').status_code in (401,503)

def test_map_route():
    r=client.get('/services-map')
    assert r.status_code==200 and 'UNA Conecta' in r.text
