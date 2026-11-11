"""Account governance and moderation. Authorization checked server-side on every call."""
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from .accounts import current_account
from .db import connection
import json
router=APIRouter(prefix='/admin',tags=['Administración y moderación'])

def require_role(user,roles):
    if user['role'] not in roles: raise HTTPException(403,'No autorizado')

def audit(conn,actor,target,action,details=None):
    conn.execute('INSERT INTO admin_audit(actor_id,target_id,action,details) VALUES (%s,%s,%s,%s::jsonb)',
      (actor,target,action,json.dumps(details or {},ensure_ascii=False)))

class StatusIn(BaseModel):
    status:str=Field(pattern='^(active|suspended|banned)$')
    reason:str=Field(min_length=8,max_length=500)
class RoleIn(BaseModel):
    role:str=Field(pattern='^(student|moderator|librarian|transport_operator|admin)$')
    reason:str=Field(min_length=8,max_length=500)
class ActionIn(BaseModel):
    action:str=Field(pattern='^(hide|dismiss)$')
    note:str=Field(min_length=5,max_length=500)

@router.get('/users')
def users(q:str|None=Query(None,max_length=100),limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        data=conn.execute('''SELECT id,display_name,email,faculty,role,account_status,verified_at,created_at
          FROM community_users WHERE (%s IS NULL OR display_name ILIKE %s OR email ILIKE %s)
          ORDER BY created_at DESC LIMIT %s OFFSET %s''',(q,'%'+(q or '').replace('%','\\%').replace('_','\\_')+'%','%'+(q or '').replace('%','\\%').replace('_','\\_')+'%',limit,offset)).fetchall()
    return {'data':data}

@router.patch('/users/{uid}/status')
def status(uid:str,data:StatusIn,user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    if uid==user['id']:raise HTTPException(403,'No puedes modificar tu propio estado')
    with connection() as conn:
        target=conn.execute('SELECT id,role,account_status FROM community_users WHERE id=%s FOR UPDATE',(uid,)).fetchone()
        if not target:raise HTTPException(404,'Cuenta inexistente')
        if target['role'] in ('admin','superadmin'):raise HTTPException(403,'No se permite suspender a otro administrador mediante esta API')
        conn.execute('''UPDATE community_users SET account_status=%s,is_active=%s,
             auth_version=auth_version+1,updated_at=now() WHERE id=%s''',(data.status,data.status=='active',uid))
        conn.execute('UPDATE auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
        audit(conn,user['id'],uid,'account.status',{'status':data.status,'reason':data.reason})
    return {'id':uid,'status':data.status,'sessions_revoked':True}

@router.patch('/users/{uid}/role')
def role(uid:str,data:RoleIn,user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    if uid==user['id']:raise HTTPException(403,'No puedes modificar tu propio rol')
    with connection() as conn:
        target=conn.execute('SELECT id,role,account_status,verified_at FROM community_users WHERE id=%s FOR UPDATE',(uid,)).fetchone()
        if not target:raise HTTPException(404,'Cuenta inexistente')
        if target['role'] in ('admin','superadmin') or (data.role=='admin' and user['role']!='superadmin'):raise HTTPException(403,'La promoción o eliminación del rol admin requiere superadministrador o procedimiento fuera de banda')
        if target['account_status']!='active' or not target['verified_at']:
            raise HTTPException(409,'Solo se asignan roles a cuentas activas verificadas')
        conn.execute('UPDATE community_users SET role=%s,auth_version=auth_version+1,updated_at=now() WHERE id=%s',(data.role,uid))
        conn.execute('UPDATE auth_sessions SET revoked_at=now() WHERE user_id=%s',(uid,))
        audit(conn,user['id'],uid,'account.role',{'role':data.role,'reason':data.reason})
    return {'id':uid,'role':data.role,'sessions_revoked':True}

@router.get('/reports')
def reports(status:str=Query('open',pattern='^(open|reviewed|dismissed)$'),limit:int=Query(50,ge=1,le=100),user=Depends(current_account)):
    require_role(user,('moderator','admin','superadmin'))
    with connection() as conn:
        data=conn.execute('''SELECT id,reporter_id,target_type,target_id,reason,status,created_at,handled_by
            FROM community_reports WHERE status=%s ORDER BY created_at LIMIT %s''',(status,limit)).fetchall()
    return {'data':data}

@router.post('/reports/{report_id}/resolve')
def resolve(report_id:int,data:ActionIn,user=Depends(current_account)):
    require_role(user,('moderator','admin','superadmin'))
    with connection() as conn:
        report=conn.execute('SELECT * FROM community_reports WHERE id=%s FOR UPDATE',(report_id,)).fetchone()
        if not report: raise HTTPException(404,'Denuncia inexistente')
        if report['status']!='open': raise HTTPException(409,'Denuncia ya resuelta')
        if data.action=='hide':
            table={'post':'community_posts','comment':'community_comments','event':'community_events'}[report['target_type']]
            conn.execute(f"UPDATE {table} SET status='hidden' WHERE id=%s",(report['target_id'],))
        conn.execute('UPDATE community_reports SET status=%s,handled_by=%s,handled_at=now() WHERE id=%s',
            ('reviewed' if data.action=='hide' else 'dismissed',user['id'],report_id))
        audit(conn,user['id'],str(report['target_id']),'moderation.'+data.action,{'report_id':report_id,'type':report['target_type'],'note':data.note})
    return {'resolved':True,'action':data.action}

@router.get('/audit')
def audits(limit:int=Query(50,ge=1,le=100),user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        data=conn.execute('SELECT id,actor_id,target_id,action,details,created_at FROM admin_audit ORDER BY id DESC LIMIT %s',(limit,)).fetchall()
    return {'data':data}

@router.get('/overview')
def overview(user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        counts=conn.execute('''SELECT
          (SELECT count(*) FROM community_users) AS total_accounts,
          (SELECT count(*) FROM community_users WHERE account_status='active') AS active_users,
          (SELECT count(*) FROM community_reports WHERE status='open') AS pending_reports,
          (SELECT count(*) FROM community_groups) AS published_groups,
          (SELECT count(*) FROM community_events WHERE status='published') AS registered_events,
          (SELECT count(*) FROM campus_facilities WHERE public_enabled=true) AS campus_facilities,
          (SELECT count(*) FROM transport_routes WHERE public_enabled=true) AS transport_routes''').fetchone()
    return counts

@router.get('/events')
def events(limit:int=Query(100,ge=1,le=200),user=Depends(current_account)):
    require_role(user,('admin','superadmin'))
    with connection() as conn:
        data=conn.execute('''SELECT e.id,e.title,e.location_name,e.starts_at,e.ends_at,e.status,e.capacity,e.demo_record,
          (SELECT count(*) FROM community_event_attendees a WHERE a.event_id=e.id) AS registered
          FROM community_events e ORDER BY e.starts_at DESC LIMIT %s''',(limit,)).fetchall()
    return {'data':data}
