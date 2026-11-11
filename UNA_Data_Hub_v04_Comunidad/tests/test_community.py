import os
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.community import router,GroupIn,PostIn,EventIn
from app.community_auth import make_dev_token,configured

def test_schemas():
    assert GroupIn(slug='club-robotica',name='Club de Robótica').visibility=='public'
    assert PostIn(body='Publicación').group_id is None

def test_dates():
    from pydantic import ValidationError
    now=datetime.now(timezone.utc)
    try:
        EventIn(title='Evento piloto',starts_at=now,ends_at=now-timedelta(minutes=1))
        assert False
    except ValidationError: pass

def test_auth_rejects_missing_credentials():
    app=FastAPI();app.include_router(router)
    with patch.dict(os.environ,{'APP_ENV':'development','COMMUNITY_JWT_SECRET':'x'*40}):
        r=TestClient(app).get('/community/me')
        assert r.status_code==401

def test_dev_token_guard():
    with patch.dict(os.environ,{'APP_ENV':'production','COMMUNITY_JWT_SECRET':'x'*40}):
        assert not configured()
        try:make_dev_token('demo-estudiante');assert False
        except RuntimeError:pass

def test_dev_token_has_signature():
    with patch.dict(os.environ,{'APP_ENV':'development','COMMUNITY_JWT_SECRET':'x'*40}):
        token=make_dev_token('demo-estudiante')
        assert len(token.split('.'))==3
