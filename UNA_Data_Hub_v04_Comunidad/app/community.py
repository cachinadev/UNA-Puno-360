# UNA Comunidad: bounded, moderated, parameterized SQL API.
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,model_validator
from .db import connection
from .community_auth import current_user

router=APIRouter(prefix='/community',tags=['UNA Comunidad (piloto)'])

def missing(message='No encontrado'): raise HTTPException(404,message)
def forbidden(message='Sin permisos'): raise HTTPException(403,message)
def get_group(conn,gid):
    g=conn.execute('SELECT id,slug,name,description,faculty,visibility,created_by,created_at FROM community_groups WHERE id=%s',(gid,)).fetchone()
    if not g: missing('Grupo inexistente')
    return g

def member(conn,gid,uid):
    return conn.execute('SELECT role FROM community_memberships WHERE group_id=%s AND user_id=%s',(gid,uid)).fetchone()

def allowed_group(conn,gid,user,write=False):
    g=get_group(conn,gid)
    m=member(conn,gid,user['id'])
    if write and not m: forbidden('Debes unirte al grupo')
    if g['visibility']=='private' and not m and user['role'] not in ('moderator','admin'): forbidden('Grupo privado')
    return g

def can_read_post(conn,p,user):
    if not p or p['status']!='published': missing('Publicación no disponible')
    if p['group_id'] is not None: allowed_group(conn,p['group_id'],user)

class GroupIn(BaseModel):
    slug:str=Field(min_length=3,max_length=60,pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    name:str=Field(min_length=3,max_length=120)
    description:str=Field(default='',max_length=1000)
    faculty:str|None=Field(default=None,max_length=120)
    visibility:str=Field(default='public',pattern='^(public|private)$')
class PostIn(BaseModel):
    body:str=Field(min_length=1,max_length=3000)
    group_id:int|None=Field(default=None,gt=0)
class CommentIn(BaseModel):
    body:str=Field(min_length=1,max_length=1000)
class ReactionIn(BaseModel):
    kind:str=Field(pattern='^(like|celebrate|support)$')
class EventIn(BaseModel):
    title:str=Field(min_length=3,max_length=150)
    description:str=Field(default='',max_length=2000)
    location_name:str|None=Field(default=None,max_length=200)
    starts_at:datetime
    ends_at:datetime
    group_id:int|None=Field(default=None,gt=0)
    @model_validator(mode='after')
    def valid_dates(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None or self.ends_at<=self.starts_at:
            raise ValueError('Fechas con zona horaria y fin posterior al inicio requeridas')
        return self
class ReportIn(BaseModel):
    target_type:str=Field(pattern='^(post|comment|event)$')
    target_id:int=Field(gt=0)
    reason:str=Field(min_length=5,max_length=500)
class ModerateIn(BaseModel):
    action:str=Field(pattern='^(hide|dismiss)$')

@router.get('/me')
def me(user=Depends(current_user)): return user

@router.get('/groups')
def groups(limit:int=Query(30,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current_user)):
    with connection() as conn:
        data=conn.execute('''SELECT g.id,g.slug,g.name,g.description,g.faculty,g.visibility,g.created_at,
              EXISTS(SELECT 1 FROM community_memberships m WHERE m.group_id=g.id AND m.user_id=%s) AS joined
              FROM community_groups g WHERE g.visibility='public'
              OR EXISTS(SELECT 1 FROM community_memberships m WHERE m.group_id=g.id AND m.user_id=%s)
              ORDER BY g.created_at DESC,g.id DESC LIMIT %s OFFSET %s''',(user['id'],user['id'],limit,offset)).fetchall()
    return {'data':data,'limit':limit,'offset':offset}

@router.post('/groups',status_code=201)
def create_group(payload:GroupIn,user=Depends(current_user)):
    with connection() as conn:
        if conn.execute('SELECT 1 FROM community_groups WHERE slug=%s',(payload.slug,)).fetchone(): raise HTTPException(409,'Identificador ya utilizado')
        g=conn.execute('''INSERT INTO community_groups(slug,name,description,faculty,visibility,created_by)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING id,slug,name,visibility''',(payload.slug,payload.name,payload.description,payload.faculty,payload.visibility,user['id'])).fetchone()
        conn.execute('INSERT INTO community_memberships(group_id,user_id,role) VALUES (%s,%s,%s)',(g['id'],user['id'],'owner'))
    return g

@router.post('/groups/{group_id}/join')
def join_group(group_id:int,user=Depends(current_user)):
    with connection() as conn:
        g=get_group(conn,group_id)
        if g['visibility']!='public': forbidden('Los grupos privados requieren invitación')
        conn.execute('INSERT INTO community_memberships(group_id,user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(group_id,user['id']))
    return {'joined':True}

@router.get('/feed')
def feed(group_id:int|None=Query(None,gt=0),limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0),user=Depends(current_user)):
    with connection() as conn:
        if group_id: allowed_group(conn,group_id,user)
        where='AND p.group_id=%s' if group_id else ''
        params=[]
        if group_id: params.append(group_id)
        params.extend([user['id'],limit,offset])
        data=conn.execute(f'''SELECT p.id,p.author_id,u.display_name,p.group_id,p.body,p.created_at,
              (SELECT count(*) FROM community_reactions r WHERE r.post_id=p.id) AS reactions,
              (SELECT count(*) FROM community_comments c WHERE c.post_id=p.id AND c.status='published') AS comments
              FROM community_posts p JOIN community_users u ON u.id=p.author_id
              WHERE p.status='published' {where} AND (p.group_id IS NULL OR EXISTS
               (SELECT 1 FROM community_groups g WHERE g.id=p.group_id AND (g.visibility='public'
                OR EXISTS(SELECT 1 FROM community_memberships m WHERE m.group_id=g.id AND m.user_id=%s))))
              AND u.is_active=true
              ORDER BY p.created_at DESC,p.id DESC LIMIT %s OFFSET %s''',params).fetchall()
    return {'data':data,'limit':limit,'offset':offset}

@router.post('/posts',status_code=201)
def create_post(payload:PostIn,user=Depends(current_user)):
    if not payload.body.strip(): raise HTTPException(422,'Texto vacío')
    with connection() as conn:
        if payload.group_id: allowed_group(conn,payload.group_id,user,write=True)
        return conn.execute('''INSERT INTO community_posts(author_id,group_id,body) VALUES (%s,%s,%s)
             RETURNING id,author_id,group_id,body,status,created_at''',(user['id'],payload.group_id,payload.body.strip())).fetchone()

@router.delete('/posts/{post_id}')
def delete_post(post_id:int,user=Depends(current_user)):
    with connection() as conn:
        p=conn.execute('SELECT id,author_id,status FROM community_posts WHERE id=%s',(post_id,)).fetchone()
        if not p: missing()
        if p['author_id']!=user['id'] and user['role'] not in ('moderator','admin'): forbidden()
        conn.execute("UPDATE community_posts SET status='deleted',updated_at=now() WHERE id=%s",(post_id,))
    return {'deleted':True}

@router.get('/posts/{post_id}/comments')
def comments(post_id:int,limit:int=Query(30,ge=1,le=100),user=Depends(current_user)):
    with connection() as conn:
        p=conn.execute('SELECT group_id,status FROM community_posts WHERE id=%s',(post_id,)).fetchone();can_read_post(conn,p,user)
        data=conn.execute('''SELECT c.id,c.body,c.created_at,c.author_id,u.display_name FROM community_comments c
          JOIN community_users u ON u.id=c.author_id WHERE c.post_id=%s AND c.status='published' AND u.is_active=true
          ORDER BY c.created_at LIMIT %s''',(post_id,limit)).fetchall()
    return {'data':data}

@router.post('/posts/{post_id}/comments',status_code=201)
def add_comment(post_id:int,payload:CommentIn,user=Depends(current_user)):
    if not payload.body.strip(): raise HTTPException(422,'Texto vacío')
    with connection() as conn:
        p=conn.execute('SELECT group_id,status FROM community_posts WHERE id=%s FOR UPDATE',(post_id,)).fetchone();can_read_post(conn,p,user)
        if p['group_id']:allowed_group(conn,p['group_id'],user,write=True)
        return conn.execute('''INSERT INTO community_comments(post_id,author_id,body) VALUES (%s,%s,%s)
          RETURNING id,post_id,author_id,body,created_at''',(post_id,user['id'],payload.body.strip())).fetchone()

@router.put('/posts/{post_id}/reaction')
def react(post_id:int,payload:ReactionIn,user=Depends(current_user)):
    with connection() as conn:
        p=conn.execute('SELECT group_id,status FROM community_posts WHERE id=%s',(post_id,)).fetchone();can_read_post(conn,p,user)
        conn.execute('''INSERT INTO community_reactions(post_id,user_id,kind) VALUES (%s,%s,%s)
          ON CONFLICT(post_id,user_id) DO UPDATE SET kind=excluded.kind''',(post_id,user['id'],payload.kind))
    return {'kind':payload.kind}

@router.get('/events')
def events(limit:int=Query(30,ge=1,le=100),user=Depends(current_user)):
    with connection() as conn:
        data=conn.execute('''SELECT e.id,e.title,e.description,e.location_name,e.starts_at,e.ends_at,e.group_id,
           e.organizer_id FROM community_events e WHERE e.status='published' AND (e.group_id IS NULL OR EXISTS
           (SELECT 1 FROM community_groups g WHERE g.id=e.group_id AND (g.visibility='public' OR
           EXISTS(SELECT 1 FROM community_memberships m WHERE m.group_id=g.id AND m.user_id=%s))))
           ORDER BY e.starts_at LIMIT %s''',(user['id'],limit)).fetchall()
    return {'data':data}

@router.post('/events',status_code=201)
def create_event(payload:EventIn,user=Depends(current_user)):
    with connection() as conn:
        if payload.group_id:allowed_group(conn,payload.group_id,user,write=True)
        return conn.execute('''INSERT INTO community_events(organizer_id,group_id,title,description,location_name,starts_at,ends_at)
         VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id,title,starts_at,ends_at''',
         (user['id'],payload.group_id,payload.title,payload.description,payload.location_name,payload.starts_at,payload.ends_at)).fetchone()

@router.post('/events/{event_id}/attend')
def attend(event_id:int,user=Depends(current_user)):
    with connection() as conn:
        e=conn.execute('SELECT group_id,status FROM community_events WHERE id=%s',(event_id,)).fetchone()
        if not e or e['status']!='published': missing('Evento no disponible')
        if e['group_id']:allowed_group(conn,e['group_id'],user)
        conn.execute('INSERT INTO community_event_attendees(event_id,user_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(event_id,user['id']))
    return {'attending':True}

@router.post('/reports',status_code=201)
def report(payload:ReportIn,user=Depends(current_user)):
    with connection() as conn:
        table={'post':'community_posts','comment':'community_comments','event':'community_events'}[payload.target_type]
        if not conn.execute(f'SELECT 1 FROM {table} WHERE id=%s',(payload.target_id,)).fetchone(): missing('Contenido inexistente')
        try:
            return conn.execute('''INSERT INTO community_reports(reporter_id,target_type,target_id,reason)
                VALUES(%s,%s,%s,%s) RETURNING id,status''',(user['id'],payload.target_type,payload.target_id,payload.reason)).fetchone()
        except Exception as exc:
            if getattr(exc,'sqlstate',None)=='23505': raise HTTPException(409,'Denuncia ya registrada')
            raise

@router.get('/moderation/reports')
def reports(user=Depends(current_user)):
    if user['role'] not in ('moderator','admin'): forbidden()
    with connection() as conn:
        data=conn.execute("SELECT id,target_type,target_id,reason,status,created_at FROM community_reports WHERE status='open' ORDER BY created_at LIMIT 100").fetchall()
    return {'data':data}

@router.post('/moderation/reports/{report_id}')
def moderate(report_id:int,payload:ModerateIn,user=Depends(current_user)):
    if user['role'] not in ('moderator','admin'): forbidden()
    with connection() as conn:
        r=conn.execute('SELECT * FROM community_reports WHERE id=%s FOR UPDATE',(report_id,)).fetchone()
        if not r:missing('Denuncia inexistente')
        if r['status']!='open': raise HTTPException(409,'Denuncia cerrada')
        if payload.action=='hide':
            table={'post':'community_posts','comment':'community_comments','event':'community_events'}[r['target_type']]
            conn.execute(f"UPDATE {table} SET status='hidden' WHERE id=%s",(r['target_id'],))
        conn.execute('''UPDATE community_reports SET status=%s,handled_by=%s,handled_at=now() WHERE id=%s''',
                     ('reviewed' if payload.action=='hide' else 'dismissed',user['id'],report_id))
    return {'resolved':True,'action':payload.action}
