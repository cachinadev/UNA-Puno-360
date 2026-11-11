import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.import_services import validate_row,import_csv
from pathlib import Path

def test_library_info():
    r=TestClient(app).get('/library/info')
    assert r.status_code==200 and r.json()['api_catalog_confirmed'] is False

def test_dining_info():
    r=TestClient(app).get('/dining/info')
    assert r.status_code==200 and r.json()['student_login_required_for_private_services'] is True

def test_query_validation():
    c=TestClient(app)
    assert c.get('/library/books?limit=999').status_code==422
    assert c.get('/dining/menus?day=bad').status_code==422

def test_no_fake_book_availability():
    with pytest.raises(ValueError):
        validate_row('books',dict(external_id='T1',title='Libro',catalog_url='https://example.org',availability='available',verified='false'))

def test_menu_dates():
    row=validate_row('menus',dict(location_code='L',service_date='2026-11-10',meal_type='lunch',description='Demo',source_url='https://example.org',verified='false'))
    assert row['service_date'].isoformat()=='2026-11-10'

def test_https_required():
    with pytest.raises(ValueError):
        validate_row('locations',dict(code='D',name='Demo',source_url='http://example.com'))

def test_demo_csv_dry_run():
    assert import_csv('branches',Path(__file__).parents[1]/'examples'/'branches.demo.csv',dry_run=True)==1
