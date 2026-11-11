"""Development-only JWT signer, never an institutionally verified login."""
import os
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import Depends,HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .db import connection

bearer=HTTPBearer(auto_error=False)
ISSUER='una-data-hub-local-dev'
AUDIENCE='una-community-dev'

def configured():
    secret=os.getenv('COMMUNITY_JWT_SECRET','')
    return os.getenv('APP_ENV')=='development' and len(secret)>=32 and secret!='replace_me_with_at_least_32_random_characters'

def make_dev_token(user_id:str,minutes:int=60):
    if not configured(): raise RuntimeError('Local JWT demo is disabled; configure APP_ENV and a strong secret')
    if not 1<=minutes<=120: raise ValueError('minutes must be between 1 and 120')
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':user_id,'iss':ISSUER,'aud':AUDIENCE,'iat':now,'exp':now+timedelta(minutes=minutes)},os.environ['COMMUNITY_JWT_SECRET'],algorithm='HS256')

def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    if not configured(): raise HTTPException(503,'Demo authentication disabled. Institutional OIDC integration required for production.')
    if credentials is None: raise HTTPException(401,'Bearer token required',headers={'WWW-Authenticate':'Bearer'})
    try:
        claims=jwt.decode(credentials.credentials,os.environ['COMMUNITY_JWT_SECRET'],algorithms=['HS256'],issuer=ISSUER,audience=AUDIENCE,options={'require':['exp','iat','sub','aud','iss']})
    except jwt.PyJWTError:
        raise HTTPException(401,'Invalid or expired token',headers={'WWW-Authenticate':'Bearer'})
    with connection() as conn:
        user=conn.execute('SELECT id,display_name,faculty,bio,role FROM community_users WHERE id=%s AND is_active=true',(claims['sub'],)).fetchone()
    if not user: raise HTTPException(403,'Account not active')
    return user
