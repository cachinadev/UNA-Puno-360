"""Optional live PostGIS tests: run after 'docker compose up -d'."""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import upsert_places

@pytest.mark.skipif(not os.environ.get('RUN_DB_TESTS'),reason='Requires running PostGIS and RUN_DB_TESTS=1')
def test_database_geo_endpoints():
    rows=[dict(source='test',source_id='abc',name='Test geo point',category='library',lat=-15.82,lon=-70.02,tags={'test':'yes'})]
    assert upsert_places(rows)==1
    c=TestClient(app)
    r=c.get('/geo/nearby?lat=-15.82&lon=-70.02&radius_m=50&category=library')
    assert r.status_code==200
    assert any(v['source_id']=='abc' for v in r.json()['data'])
    r=c.get('/geo/geojson?category=library&south=-15.83&west=-70.03&north=-15.81&east=-70.01')
    assert r.status_code==200 and r.json()['type']=='FeatureCollection'
