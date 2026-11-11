"""Destructive-light native API smoke test. Creates clearly marked dev records."""
import argparse
import time
import uuid
import httpx

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:8000')
args=parser.parse_args()
base=args.base_url.rstrip('/')
suffix=uuid.uuid4().hex[:10]
email=f'native-test-{suffix}@example.com'
password=f'NativeTest{suffix.upper()}2026!'

def expect(response,status=200):
    if response.status_code!=status:
        raise RuntimeError(f'{response.request.method} {response.request.url}: expected {status}, got {response.status_code}: {response.text[:500]}')
    return response.json()

with httpx.Client(base_url=base,timeout=15) as client:
    expect(client.get('/health'))
    registered=expect(client.post('/auth/register',json={'email':email,'display_name':f'Prueba nativa {suffix}','password':password}),201)
    token=registered.get('dev_verification_token')
    if not token: raise RuntimeError('AUTH_DEV_EXPOSE_TOKENS=true is required for native smoke testing')
    expect(client.post('/auth/verify-email',json={'token':token}))
    session=expect(client.post('/auth/login',json={'email':email,'password':password}))
    headers={'Authorization':f"Bearer {session['access_token']}"}
    expect(client.get('/auth/me',headers=headers))
    expect(client.put('/profile',headers=headers,json={'display_name':f'Prueba nativa {suffix}','faculty':'Ingeniería de prueba',
      'semester':'MVP','interests':['pruebas','mapas'],'theme':'light','language':'es','profile_public':False,
      'transport_alerts':True,'reservation_alerts':True,'community_alerts':True}))
    expect(client.get('/profile',headers=headers))
    post=expect(client.post('/community/posts',headers=headers,json={'body':f'Publicación de prueba nativa {suffix}'}),201)
    expect(client.get('/community/feed',headers=headers))
    start=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+3600))
    end=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time()+7200))
    event=expect(client.post('/community/events',headers=headers,json={'title':f'Evento nativo {suffix}','description':'Dato de prueba automatizada','starts_at':start,'ends_at':end}),201)
    expect(client.post(f"/community/events/{event['id']}/attend",headers=headers))
    expect(client.post('/community/reports',headers=headers,json={'target_type':'post','target_id':post['id'],'reason':'Reporte automatizado de prueba'}),201)
    expect(client.get('/transport/routes'))
    simulation=expect(client.get('/transport/demo/snapshot'))
    if not simulation['data'] or not simulation['data'][0]['vehicles']:
        raise RuntimeError('Demo transport seed did not expose vehicles')
    expect(client.get('/geo/places',params={'limit':1}))
    books=expect(client.get('/library/books',params={'limit':100}))['data']
    demo_book=next((item for item in books if item.get('demo_record') and item.get('available_copies',0)>0),None)
    if not demo_book: raise RuntimeError('No reservable demo book found')
    reservation=expect(client.post(f"/library/books/{demo_book['external_id']}/reservations",headers=headers),201)
    if client.post(f"/library/books/{demo_book['external_id']}/reservations",headers=headers).status_code!=409:
        raise RuntimeError('Duplicate book reservation was not rejected')
    expect(client.get('/library/reservations/me',headers=headers))
    expect(client.post(f"/library/reservations/{reservation['id']}/cancel",headers=headers))
    menus=expect(client.get('/dining/menus',params={'limit':100}))['data']
    demo_menu=next((item for item in menus if item.get('demo_record')),None)
    if not demo_menu: raise RuntimeError('No reservable demo menu found')
    expect(client.post(f"/dining/menus/{demo_menu['id']}/reservations",headers=headers),201)
    if client.post(f"/dining/menus/{demo_menu['id']}/reservations",headers=headers).status_code!=409:
        raise RuntimeError('Duplicate meal reservation was not rejected')
    notifications=expect(client.get('/notifications',headers=headers))
    if notifications['unread']<2: raise RuntimeError('Reservation notifications were not created')
    expect(client.post('/notifications/read-all',headers=headers))
    expect(client.get('/facilities/search',params={'limit':1}))
    admin=client.get('/admin/overview',headers=headers)
    if admin.status_code!=403: raise RuntimeError(f'Admin authorization expected 403, got {admin.status_code}')
    expect(client.post('/auth/logout',headers=headers))
    if client.get('/auth/me',headers=headers).status_code!=401: raise RuntimeError('Logout did not revoke the session')
print('PASS: auth, profile, community, events, reports, deterministic transport, geo, book and meal reservations, notifications, facilities, authorization and logout')
