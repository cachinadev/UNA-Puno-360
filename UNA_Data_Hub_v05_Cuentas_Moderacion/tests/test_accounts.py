import os
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.accounts import enabled, strong, hash_token, create_access, RegisterIn, current_account
from app.accounts_admin import require_role, StatusIn, RoleIn, ActionIn
from app.main import app
import jwt

def test_disabled_by_default():
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'false','AUTH_JWT_SECRET':'x'*64}):
        assert not enabled()
        assert TestClient(app).post('/auth/register',json={'email':'test@example.org','display_name':'Test User','password':'ExamplePassword2026'}).status_code==503

def test_enabled_requires_strong_secret():
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'true','AUTH_JWT_SECRET':'short'}): assert not enabled()
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'true','AUTH_JWT_SECRET':'x'*64}): assert enabled()

def test_password_rules():
    from fastapi import HTTPException
    strong('LongEnoughPassword123')
    try:strong('onlylowercase12345');assert False
    except HTTPException as e:assert e.status_code==422

def test_token_hash():
    assert hash_token('secret')!= 'secret'
    assert hash_token('secret')==hash_token('secret')

def test_login_access_requires_auth():
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'true','AUTH_JWT_SECRET':'x'*64}):
        assert TestClient(app).get('/auth/me').status_code==401
        assert TestClient(app).get('/community/feed').status_code==401

def test_jwt_has_exp_and_session():
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'true','AUTH_JWT_SECRET':'x'*64}):
        import uuid
        uid=str(uuid.uuid4());sid=uuid.uuid4()
        tok=create_access({'id':uid,'auth_version':2},sid)
        claims=jwt.decode(tok,'x'*64,algorithms=['HS256'],audience='una-conecta',issuer='una-data-hub-local')
        assert claims['sub']==uid and claims['sid']==str(sid) and claims['ver']==2

def test_roles():
    from fastapi import HTTPException
    require_role({'role':'admin'},('admin',))
    try:require_role({'role':'student'},('admin',));assert False
    except HTTPException as e:assert e.status_code==403

def test_validation():
    assert StatusIn(status='suspended',reason='Repeated abusive behavior').status=='suspended'
    assert RoleIn(role='moderator',reason='Training completed').role=='moderator'
    assert ActionIn(action='hide',note='Confirmed violation').action=='hide'

def test_no_open_registration_without_opt_in():
    with patch.dict(os.environ,{'AUTH_LOCAL_ENABLED':'true','AUTH_JWT_SECRET':'x'*64,'AUTH_ALLOW_REGISTRATION':'false'}):
        r=TestClient(app).post('/auth/register',json={'email':'student@example.org','display_name':'Student One','password':'VeryStrongPassword123'})
        assert r.status_code==403
