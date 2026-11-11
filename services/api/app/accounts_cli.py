"""Offline operator tools: issue one-time verification/reset token; bootstrap first admin.
Run only from trusted local terminal. Never expose these commands as HTTP APIs.
"""
import argparse, getpass, uuid
from .accounts import ph, one_time, strong
from .db import connection

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    for name in ('verify-token','reset-token'):
        c=sub.add_parser(name);c.add_argument('email')
    c=sub.add_parser('bootstrap-admin');c.add_argument('email');c.add_argument('name')
    args=p.parse_args()
    with connection() as conn:
        if args.command=='bootstrap-admin':
            total=conn.execute("SELECT COUNT(*) AS n FROM community_users WHERE role IN ('admin','superadmin')").fetchone()['n']
            if total:raise SystemExit('An administrator already exists. Bootstrap disabled.')
            password=getpass.getpass('Administrator password: ');strong(password)
            uid=str(uuid.uuid4())
            conn.execute('''INSERT INTO community_users(id,email,display_name,password_hash,role,account_status,is_active,verified_at)
                 VALUES (%s,%s,%s,%s,'superadmin','active',true,now())''',
                 (uid,args.email.lower(),args.name,ph.hash(password)))
            print('Admin created:',uid)
        else:
            user=conn.execute('SELECT id FROM community_users WHERE lower(email)=%s',(args.email.lower(),)).fetchone()
            if not user:raise SystemExit('Email not found')
            purpose='verify' if args.command=='verify-token' else 'reset'
            token=one_time(conn,user['id'],purpose,60 if purpose=='verify' else 15)
            print(f'ONE-TIME {purpose.upper()} TOKEN (share securely): {token}')
if __name__=='__main__':main()
