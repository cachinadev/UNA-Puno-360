import os
os.environ['UNA_DB']='/tmp/una_hub_test.sqlite3'
import hub
from fastapi.testclient import TestClient


def test_dspace_normalization():
    sample={'_embedded':{'searchResult':{'_embedded':{'objects':[
      {'_embedded':{'indexableObject':{'uuid':'abc','metadata':{
      'dc.title':[{'value':'Quinua en Puno'}],
      'dc.contributor.author':[{'value':'Autora Uno'}],
      'dc.identifier.uri':[{'value':'https://hdl.handle.net/123/456'}]}}}}]}}}}
    r=hub.normalize_dspace(sample)
    assert len(r)==1 and r[0]['authors']==['Autora Uno']


def test_oai_normalization():
    xml=b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
    <ListRecords><record><header><identifier>oai:unap:1</identifier></header>
    <metadata><oai_dc xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Tesis de prueba</dc:title><dc:creator>Investigador</dc:creator>
    </oai_dc></metadata></record></ListRecords></OAI-PMH>'''
    items,token=hub.normalize_oai(xml)
    assert len(items)==1 and token is None


def test_local_api(tmp_path,monkeypatch):
    monkeypatch.setattr(hub,'DB',tmp_path/'test.sqlite3')
    hub.store([{'source':'oai','identifier':'one','title':'Energía solar',
                'authors':['Alumno'], 'published':'2025','url':'https://example.org'}])
    client=TestClient(hub.app)
    assert client.get('/health').json()['records']==1
    assert len(client.get('/records',params={'q':'solar'}).json())==1
    assert client.get('/records',params={'limit':999}).status_code==422
