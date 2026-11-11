import os,hashlib,hmac,time
from datetime import datetime,timezone,timedelta
import pytest
from fastapi import HTTPException
from app.transport import Batch,verify_signature,require_bridge_token
from app.transport_bridge import normalize,safe_url

def test_valid_batch():
 b=Batch(provider='kuntur',tenant='una',positions=[dict(vehicle_id='fleet-1',lat=-15.82,lon=-70.01,observed_at=datetime.now(timezone.utc))]);assert b.positions[0].lat==-15.82

def test_naive_time_rejected():
 with pytest.raises(ValueError):Batch(provider='kuntur',tenant='una',positions=[dict(vehicle_id='x',lat=1,lon=2,observed_at='2026-11-10T10:00:00')])

def test_future_rejected():
 with pytest.raises(ValueError):Batch(provider='kuntur',tenant='una',positions=[dict(vehicle_id='x',lat=1,lon=2,observed_at=datetime.now(timezone.utc)+timedelta(hours=1))])

def test_bad_coordinate_rejected():
 with pytest.raises(ValueError):Batch(provider='kuntur',tenant='una',positions=[dict(vehicle_id='x',lat=-150,lon=2,observed_at=datetime.now(timezone.utc))])

def test_bridge_secret(monkeypatch):
 monkeypatch.setenv('TRANSPORT_BRIDGE_TOKEN','a'*64)
 require_bridge_token('Bearer '+'a'*64)
 with pytest.raises(HTTPException):require_bridge_token('Bearer '+'b'*64)

def test_hmac(monkeypatch):
 monkeypatch.setenv('TRANSPORT_WEBHOOK_SECRET','c'*64)
 ts=str(int(time.time()));body=b'{}';signature=hmac.new(('c'*64).encode(),(ts+'.').encode()+body,hashlib.sha256).hexdigest()
 verify_signature(body,ts,'sha256='+signature)
 with pytest.raises(HTTPException):verify_signature(body,ts,'sha256='+'0'*64)

def test_url_allowlist(monkeypatch):
 monkeypatch.setenv('TRANSPORT_ALLOWED_HOSTS','api.example.org')
 with pytest.raises(ValueError):safe_url('http://api.example.org')
 with pytest.raises(ValueError):safe_url('https://localhost/')
 with pytest.raises(ValueError):safe_url('https://evil.example.org/')

def test_normalize():
 out=normalize({'vehicles':[{'id':'test','lat':1,'lon':2,'observed_at':'2026-11-10T10:00:00Z'}]},'kuntur','una')
 assert out['positions'][0]['vehicle_id']=='test'
