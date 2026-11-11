"""Authenticated, transactional MVP interactions for demonstration services."""
from __future__ import annotations
import secrets
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .accounts import current_account
from .accounts_admin import require_role
from .db import connection

router=APIRouter(tags=['Interacciones persistentes del MVP'])
ACTIVE_RESERVATIONS=('requested','confirmed','ready','collected')

def conflict(message): raise HTTPException(409,message)
def code(prefix): return f'{prefix}-{secrets.token_hex(4).upper()}'

@router.post('/library/books/{external_id}/reservations',status_code=201)
def reserve_book(external_id:str,user=Depends(current_account)):
    with connection() as conn:
        book=conn.execute('''SELECT id,title,available_copies,demo_record FROM library_books
          WHERE external_id=%s FOR UPDATE''',(external_id,)).fetchone()
        if not book: raise HTTPException(404,'Libro no encontrado')
        if not book['demo_record']: conflict('La reserva solo está habilitada para el catálogo de demostración')
        if book['available_copies']<1: conflict('No quedan copias demostrativas disponibles')
        try:
            reservation=conn.execute('''INSERT INTO library_reservations(reservation_number,user_id,book_id)
              VALUES (%s,%s,%s) RETURNING id,reservation_number,status,created_at''',(code('LIB'),user['id'],book['id'])).fetchone()
        except Exception as exc:
            if getattr(exc,'sqlstate',None)=='23505': conflict('Ya tienes una reserva activa para este libro')
            raise
        conn.execute('UPDATE library_books SET available_copies=available_copies-1 WHERE id=%s',(book['id'],))
        conn.execute('''INSERT INTO user_notifications(user_id,kind,title,body,target_url)
          VALUES (%s,'library','Reserva solicitada',%s,'/biblioteca/reservas')''',(user['id'],f"Solicitud registrada para {book['title']}"))
    return {**reservation,'demonstration':True}

@router.get('/library/reservations/me')
def my_book_reservations(user=Depends(current_account)):
    with connection() as conn:
        data=conn.execute('''SELECT r.id,r.reservation_number,r.status,r.pickup_deadline,r.created_at,
          b.external_id,b.title,b.authors,b.branch_code FROM library_reservations r JOIN library_books b ON b.id=r.book_id
          WHERE r.user_id=%s ORDER BY r.created_at DESC''',(user['id'],)).fetchall()
    return {'data':data,'warning':'Reservas demostrativas; no tienen validez en la biblioteca institucional.'}

@router.post('/library/reservations/{reservation_id}/cancel')
def cancel_book_reservation(reservation_id:str,user=Depends(current_account)):
    with connection() as conn:
        item=conn.execute('''SELECT id,book_id,status FROM library_reservations
          WHERE id=%s AND user_id=%s FOR UPDATE''',(reservation_id,user['id'])).fetchone()
        if not item: raise HTTPException(404,'Reserva no encontrada')
        if item['status'] not in ACTIVE_RESERVATIONS: conflict('La reserva ya está cerrada')
        conn.execute("UPDATE library_reservations SET status='cancelled',updated_at=now() WHERE id=%s",(reservation_id,))
        conn.execute('UPDATE library_books SET available_copies=LEAST(total_copies,available_copies+1) WHERE id=%s',(item['book_id'],))
    return {'cancelled':True}

class ReservationStatusIn(BaseModel):
    status:str=Field(pattern='^(confirmed|ready|collected|expired|cancelled)$')

@router.get('/admin/library/reservations')
def admin_book_reservations(user=Depends(current_account)):
    require_role(user,('librarian','admin','superadmin'))
    with connection() as conn:
        data=conn.execute('''SELECT r.id,r.reservation_number,r.status,r.pickup_deadline,r.created_at,
          b.title,b.external_id,u.display_name,u.email FROM library_reservations r
          JOIN library_books b ON b.id=r.book_id JOIN community_users u ON u.id=r.user_id
          ORDER BY r.created_at DESC LIMIT 100''').fetchall()
    return {'data':data}

@router.patch('/admin/library/reservations/{reservation_id}')
def update_book_reservation(reservation_id:str,payload:ReservationStatusIn,user=Depends(current_account)):
    require_role(user,('librarian','admin','superadmin'))
    with connection() as conn:
        item=conn.execute('SELECT id,user_id,book_id,status FROM library_reservations WHERE id=%s FOR UPDATE',(reservation_id,)).fetchone()
        if not item: raise HTTPException(404,'Reserva no encontrada')
        allowed={'requested':{'confirmed','cancelled'},'confirmed':{'ready','cancelled'},'ready':{'collected','expired','cancelled'},'collected':set(),'expired':set(),'cancelled':set()}
        if payload.status not in allowed[item['status']]: conflict('Transición de estado no permitida')
        deadline="now()+interval '2 days'" if payload.status=='ready' else 'pickup_deadline'
        conn.execute(f'UPDATE library_reservations SET status=%s,pickup_deadline={deadline},updated_at=now() WHERE id=%s',(payload.status,reservation_id))
        if payload.status in ('expired','cancelled'):
            conn.execute('UPDATE library_books SET available_copies=LEAST(total_copies,available_copies+1) WHERE id=%s',(item['book_id'],))
        conn.execute('''INSERT INTO user_notifications(user_id,kind,title,body,target_url)
          VALUES (%s,'library','Estado de reserva actualizado',%s,'/biblioteca/reservas')''',(item['user_id'],f'Nuevo estado: {payload.status}'))
    return {'id':reservation_id,'status':payload.status}

@router.post('/dining/menus/{menu_id}/reservations',status_code=201)
def reserve_meal(menu_id:int,user=Depends(current_account)):
    with connection() as conn:
        menu=conn.execute('''SELECT id,description,quota,demo_record,
          (SELECT count(*) FROM meal_reservations r WHERE r.menu_id=dining_menus.id AND r.status<>'cancelled') AS reserved
          FROM dining_menus WHERE id=%s FOR UPDATE''',(menu_id,)).fetchone()
        if not menu: raise HTTPException(404,'Menú no encontrado')
        if not menu['demo_record']: conflict('Las reservas solo están habilitadas para menús demostrativos')
        if menu['reserved']>=menu['quota']: conflict('Se agotó la cuota demostrativa')
        try:
            item=conn.execute('''INSERT INTO meal_reservations(confirmation_code,user_id,menu_id)
              VALUES (%s,%s,%s) RETURNING id,confirmation_code,status,created_at''',(code('COM'),user['id'],menu_id)).fetchone()
        except Exception as exc:
            if getattr(exc,'sqlstate',None)=='23505': conflict('Ya registraste este menú')
            raise
        conn.execute('''INSERT INTO user_notifications(user_id,kind,title,body,target_url)
          VALUES (%s,'dining','Reserva de comida confirmada',%s,'/comedor')''',(user['id'],menu['description']))
    return {**item,'demonstration':True,'warning':'Este código no permite acceso al comedor real.'}

class MealReservationStatusIn(BaseModel):
    status:str=Field(pattern='^(confirmed|checked_in|cancelled)$')

@router.get('/admin/dining/reservations')
def admin_meal_reservations(user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        data=conn.execute('''SELECT r.id,r.confirmation_code,r.status,r.created_at,
          m.meal_date,m.meal_type,m.description,u.display_name,u.email
          FROM meal_reservations r JOIN dining_menus m ON m.id=r.menu_id
          JOIN community_users u ON u.id=r.user_id ORDER BY r.created_at DESC LIMIT 100''').fetchall()
    return {'data':data}

@router.patch('/admin/dining/reservations/{reservation_id}')
def update_meal_reservation(reservation_id:str,payload:MealReservationStatusIn,user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        item=conn.execute('SELECT id,user_id,status FROM meal_reservations WHERE id=%s FOR UPDATE',(reservation_id,)).fetchone()
        if not item: raise HTTPException(404,'Reserva no encontrada')
        allowed={'confirmed':{'checked_in','cancelled'},'checked_in':set(),'cancelled':set()}
        if payload.status not in allowed[item['status']]: conflict('Transición de estado no permitida')
        conn.execute('UPDATE meal_reservations SET status=%s,updated_at=now() WHERE id=%s',(payload.status,reservation_id))
        conn.execute('''INSERT INTO user_notifications(user_id,kind,title,body,target_url)
          VALUES (%s,'dining','Estado de reserva de comedor',%s,'/comedor')''',(item['user_id'],f'Nuevo estado: {payload.status}'))
    return {'id':reservation_id,'status':payload.status}

@router.get('/notifications')
def notifications(user=Depends(current_account)):
    with connection() as conn:
        data=conn.execute('''SELECT id,kind,title,body,target_url,read_at,created_at FROM user_notifications
          WHERE user_id=%s ORDER BY created_at DESC LIMIT 100''',(user['id'],)).fetchall()
    return {'data':data,'unread':sum(1 for item in data if item['read_at'] is None)}

@router.post('/notifications/read-all')
def read_all_notifications(user=Depends(current_account)):
    with connection() as conn:
        conn.execute('UPDATE user_notifications SET read_at=now() WHERE user_id=%s AND read_at IS NULL',(user['id'],))
    return {'read':True}

class ProfileIn(BaseModel):
    display_name:str=Field(min_length=2,max_length=90)
    faculty:str|None=Field(default=None,max_length=120)
    semester:str|None=Field(default=None,max_length=40)
    interests:list[str]=Field(default_factory=list,max_length=20)
    theme:str=Field(default='system',pattern='^(light|dark|system)$')
    language:str=Field(default='es',pattern='^(es|en|qu|ay)$')
    profile_public:bool=False
    transport_alerts:bool=True
    reservation_alerts:bool=True
    community_alerts:bool=True

@router.get('/profile')
def profile(user=Depends(current_account)):
    with connection() as conn:
        preferences=conn.execute('SELECT * FROM user_preferences WHERE user_id=%s',(user['id'],)).fetchone()
    return {'user':user,'preferences':preferences or {'theme':'system','language':'es','semester':None,'interests':[],
      'profile_public':False,'transport_alerts':True,'reservation_alerts':True,'community_alerts':True}}

@router.put('/profile')
def update_profile(payload:ProfileIn,user=Depends(current_account)):
    interests=[value.strip()[:80] for value in payload.interests if value.strip()][:20]
    with connection() as conn:
        conn.execute('UPDATE community_users SET display_name=%s,faculty=%s,updated_at=now() WHERE id=%s',
          (payload.display_name.strip(),payload.faculty,user['id']))
        conn.execute('''INSERT INTO user_preferences(user_id,theme,language,semester,interests,profile_public,
          transport_alerts,reservation_alerts,community_alerts) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
          ON CONFLICT(user_id) DO UPDATE SET theme=excluded.theme,language=excluded.language,semester=excluded.semester,
          interests=excluded.interests,profile_public=excluded.profile_public,transport_alerts=excluded.transport_alerts,
          reservation_alerts=excluded.reservation_alerts,community_alerts=excluded.community_alerts,updated_at=now()''',
          (user['id'],payload.theme,payload.language,payload.semester,interests,payload.profile_public,
           payload.transport_alerts,payload.reservation_alerts,payload.community_alerts))
    return {'updated':True}
