"""Local account pilot for UNA Data Hub. No affiliation/identity proof from UNA.
Never enable in production without verified email delivery, abuse throttling and institutional approval.
"""
from __future__ import annotations
import hashlib, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
import jwt
from .db import connection

router = APIRouter(prefix='/auth', tags=['Autenticación local — piloto'])
bearer=HTTPBearer(auto_error=False)
ph=PasswordHasher(time_cost=3,memory_cost=65536,parallelism=2)
DUMMY_HASH=ph.hash('not-a-real-user-password')
ISSUER='una-data-hub-local'; AUDIENCE='una-conecta'

def enabled():
    secret=os.getenv('AUTH_JWT_SECRET','')
    return os.getenv('AUTH_LOCAL_ENABLED','false').lower()=='true' and len(secret)>=48 and not secret.startswith('replace_')

def require_enabled():
    if not enabled(): raise HTTPException(503,'Autenticación local deshabilitada')

def hash_token(token): return hashlib.sha256(token.encode()).hexdigest()

def utcnow(): return datetime.now(timezone.utc)

def create_access(user, sid):
    now=utcnow()
    return jwt.encode({'sub':user['id'],'sid':str(sid),'ver':user['auth_version'],'iss':ISSUER,'aud':AUDIENCE,'iat':now,'exp':now+timedelta(minutes=15)},os.environ['AUTH_JWT_SECRET'],algorithm='HS256')

def issue_refresh(conn,user_id,agent=None):
    token=secrets.token_urlsafe(48)
    row=conn.execute('''INSERT INTO auth_sessions(user_id,refresh_hash,expires_at,user_agent)
        VALUES (%s,%s,now()+interval '7 days',%s) RETURNING id''',(user_id,hash_token(token),(agent or '')[:250])).fetchone()
    return row['id'],token

def current_account(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    require_enabled()
    if not credentials: raise HTTPException(401,'Token de acceso requerido',headers={'WWW-Authenticate':'Bearer'})
    try:
        c=jwt.decode(credentials.credentials,os.environ['AUTH_JWT_SECRET'],algorithms=['HS256'],issuer=ISSUER,audience=AUDIENCE,options={'require':['sub','sid','ver','iat','exp','iss','aud']})
        uuid.UUID(c['sid'])
    except (jwt.PyJWTError,ValueError,KeyError,TypeError):
        raise HTTPException(401,'Token inválido o expirado')
    with connection() as conn:
        row=conn.execute('''SELECT u.id,u.display_name,u.faculty,u.bio,u.role,u.email,u.account_status,u.auth_version,
            u.is_active FROM community_users u JOIN auth_sessions s ON s.user_id=u.id
            WHERE u.id=%s AND s.id=%s AND s.revoked_at IS NULL AND s.expires_at>now()''',(c['sub'],c['sid'])).fetchone()
    if not row or row['account_status']!='active' or not row['is_active'] or c['ver']!=row['auth_version']:
        raise HTTPException(401,'Sesión revocada o cuenta inactiva')
    return row

class RegisterIn(BaseModel):
    email:EmailStr
    display_name:str=Field(min_length=2,max_length=90)
    password:str=Field(min_length=12,max_length=128)
    faculty:str|None=Field(default=None,max_length=120)
class LoginIn(BaseModel):
    email:EmailStr
    password:str
class TokenIn(BaseModel):
    token:str=Field(min_length=20,max_length=300)
class RefreshIn(BaseModel):
    refresh_token:str=Field(min_length=30,max_length=300)
class PasswordIn(BaseModel):
    current_password:str
    new_password:str=Field(min_length=12,max_length=128)
class ResetIn(BaseModel):
    email:EmailStr
class ResetConfirmIn(BaseModel):
    token:str
    new_password:str=Field(min_length=12,max_length=128)

def strong(password):
    if not (any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password)):
        raise HTTPException(422,'Contraseña: 12+ caracteres, mayúscula, minúscula y número')

def one_time(conn,uid,purpose,minutes):
    token=secrets.token_urlsafe(36)
    conn.execute('DELETE FROM auth_one_time_tokens WHERE user_id=%s AND purpose=%s',(uid,purpose))
    conn.execute('''INSERT INTO auth_one_time_tokens(user_id,purpose,token_hash,expires_at)
       VALUES (%s,%s,%s,now()+(%s * interval '1 minute'))''',(uid,purpose,hash_token(token),minutes))
    return token

def dev_tokens_allowed():
    return os.getenv('APP_ENV')=='development' and os.getenv('AUTH_DEV_EXPOSE_TOKENS')=='true'

@router.post('/register',status_code=201)
def register(data:RegisterIn):
    require_enabled()
    if os.getenv('AUTH_ALLOW_REGISTRATION','false').lower()!='true': raise HTTPException(403,'Registro público deshabilitado')
    strong(data.password)
    mail=str(data.email).lower(); uid=str(uuid.uuid4())
    with connection() as conn:
        if conn.execute('SELECT 1 FROM community_users WHERE lower(email)=%s',(mail,)).fetchone():
            raise HTTPException(409,'No se pudo crear la cuenta con este correo')
        conn.execute('''INSERT INTO community_users(id,email,display_name,password_hash,faculty,role,account_status,is_active)
            VALUES (%s,%s,%s,%s,%s,'student','pending',false)''',(uid,mail,data.display_name.strip(),ph.hash(data.password),data.faculty))
        token=one_time(conn,uid,'verify',60)
    result={'message':'Cuenta registrada. Requiere verificación de correo.','user_id':uid}
    if dev_tokens_allowed(): result['dev_verification_token']=token
    return result

@router.post('/verify-email')
def verify_email(data:TokenIn):
    require_enabled()
    with connection() as conn:
        row=conn.execute('''SELECT id,user_id FROM auth_one_time_tokens WHERE token_hash=%s
          AND purpose='verify' AND consumed_at IS NULL AND expires_at>now() FOR UPDATE''',(hash_token(data.token),)).fetchone()
        if not row: raise HTTPException(400,'Token inválido o caducado')
        conn.execute("UPDATE community_users SET verified_at=now(),account_status='active',is_active=true,updated_at=now() WHERE id=%s AND account_status='pending'",(row['user_id'],))
        conn.execute('UPDATE auth_one_time_tokens SET consumed_at=now() WHERE id=%s',(row['id'],))
    return {'verified':True}

@router.post('/login')
def login(data:LoginIn,user_agent:str|None=Header(default=None)):
    require_enabled()
    access=None; refresh=None; error=None
    with connection() as conn:
        u=conn.execute('''SELECT id,email,password_hash,role,auth_version,account_status,is_active,
         failed_logins,locked_until FROM community_users WHERE lower(email)=%s FOR UPDATE''',(str(data.email).lower(),)).fetchone()
        # Always do a password KDF for nonexistent users to reduce timing enumeration.
        try: valid=ph.verify(u['password_hash'] if u and u['password_hash'] else DUMMY_HASH,data.password)
        except (VerifyMismatchError,VerificationError,ValueError): valid=False
        if not u or not valid:
            if u:
                conn.execute('''UPDATE community_users SET failed_logins=failed_logins+1,
                   locked_until=CASE WHEN failed_logins+1>=5 THEN now()+interval '15 minutes' ELSE locked_until END
                   WHERE id=%s''',(u['id'],))
            error=(401,'Credenciales incorrectas')
        elif u['locked_until'] and u['locked_until']>utcnow():
            error=(429,'Cuenta temporalmente bloqueada')
        elif u['account_status']!='active' or not u['is_active']:
            error=(403,'Cuenta no habilitada')
        else:
            conn.execute('UPDATE community_users SET failed_logins=0,locked_until=NULL WHERE id=%s',(u['id'],))
            sid,refresh=issue_refresh(conn,u['id'],user_agent)
            access=create_access(u,sid)
    if error: raise HTTPException(*error)
    return {'access_token':access,'refresh_token':refresh,'token_type':'bearer','expires_in':900}

@router.post('/refresh')
def refresh(data:RefreshIn):
    require_enabled()
    with connection() as conn:
        session=conn.execute('''SELECT s.id,s.user_id,s.expires_at,s.revoked_at,u.auth_version,u.account_status,u.is_active
           FROM auth_sessions s JOIN community_users u ON u.id=s.user_id
           WHERE s.refresh_hash=%s FOR UPDATE OF s''',(hash_token(data.refresh_token),)).fetchone()
        if not session or session['revoked_at'] or session['expires_at']<=utcnow() or session['account_status']!='active' or not session['is_active']:
            raise HTTPException(401,'Sesión inválida')
        new=secrets.token_urlsafe(48)
        conn.execute('UPDATE auth_sessions SET refresh_hash=%s,last_used=now() WHERE id=%s',(hash_token(new),session['id']))
    return {'access_token':create_access({'id':session['user_id'],'auth_version':session['auth_version']},session['id']),'refresh_token':new,'token_type':'bearer','expires_in':900}

@router.get('/me')
def me(user=Depends(current_account)):
    return {k:user[k] for k in ('id','display_name','email','faculty','role','bio','account_status')}

@router.post('/logout')
def logout(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),user=Depends(current_account)):
    claims=jwt.decode(credentials.credentials,os.environ['AUTH_JWT_SECRET'],algorithms=['HS256'],audience=AUDIENCE,issuer=ISSUER)
    with connection() as conn: conn.execute('UPDATE auth_sessions SET revoked_at=now() WHERE id=%s AND user_id=%s',(claims['sid'],user['id']))
    return {'logged_out':True}

@router.post('/password/change')
def change_password(data:PasswordIn,user=Depends(current_account)):
    strong(data.new_password)
    with connection() as conn:
        row=conn.execute('SELECT password_hash FROM community_users WHERE id=%s FOR UPDATE',(user['id'],)).fetchone()
        try: valid=ph.verify(row['password_hash'],data.current_password)
        except (VerifyMismatchError,VerificationError): valid=False
        if not valid: raise HTTPException(401,'Contraseña actual incorrecta')
        conn.execute('UPDATE community_users SET password_hash=%s,auth_version=auth_version+1,updated_at=now() WHERE id=%s',(ph.hash(data.new_password),user['id']))
        conn.execute('UPDATE auth_sessions SET revoked_at=now() WHERE user_id=%s',(user['id'],))
    return {'changed':True,'login_required':True}

@router.post('/password/request-reset')
def request_reset(data:ResetIn):
    require_enabled()
    with connection() as conn:
        u=conn.execute('SELECT id FROM community_users WHERE lower(email)=%s AND account_status=%s',(str(data.email).lower(),'active')).fetchone()
        if u:
            token=one_time(conn,u['id'],'reset',15)
            # Real deployment MUST send token via verified email delivery service.
    result={'message':'Si la cuenta existe, se enviarán instrucciones por un canal verificado.'}
    if u and dev_tokens_allowed(): result['dev_reset_token']=token
    return result

@router.post('/password/confirm-reset')
def confirm_reset(data:ResetConfirmIn):
    require_enabled();strong(data.new_password)
    with connection() as conn:
        row=conn.execute('''SELECT id,user_id FROM auth_one_time_tokens WHERE token_hash=%s
            AND purpose='reset' AND consumed_at IS NULL AND expires_at>now() FOR UPDATE''',(hash_token(data.token),)).fetchone()
        if not row: raise HTTPException(400,'Token inválido o caducado')
        conn.execute('UPDATE community_users SET password_hash=%s,auth_version=auth_version+1,failed_logins=0,locked_until=NULL WHERE id=%s',(ph.hash(data.new_password),row['user_id']))
        conn.execute('UPDATE auth_sessions SET revoked_at=now() WHERE user_id=%s',(row['user_id'],))
        conn.execute('UPDATE auth_one_time_tokens SET consumed_at=now() WHERE id=%s',(row['id'],))
    return {'reset':True,'login_required':True}
