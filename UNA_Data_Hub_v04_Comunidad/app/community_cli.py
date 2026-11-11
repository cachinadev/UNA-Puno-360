# Local-only demo seed and tokens. No public token issuance endpoint.
import argparse
from .db import connection
from .community_auth import make_dev_token,configured

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('seed-demo')
    t=sub.add_parser('token');t.add_argument('user_id',choices=['demo-estudiante','demo-moderador'])
    a=p.parse_args()
    if not configured(): raise SystemExit('Configura APP_ENV=development y COMMUNITY_JWT_SECRET seguro (>=32 caracteres)')
    if a.command=='seed-demo':
        with connection() as conn:
            conn.execute('''INSERT INTO community_users(id,display_name,faculty,role) VALUES
                 ('demo-estudiante','Estudiante Demo','Ingeniería Electrónica','student'),
                 ('demo-moderador','Moderación Demo',NULL,'moderator')
                 ON CONFLICT (id) DO NOTHING''')
        print('Cuentas de DEMOSTRACIÓN creadas')
    else:
        with connection() as conn:
            exists=conn.execute('SELECT 1 FROM community_users WHERE id=%s AND is_active=true',(a.user_id,)).fetchone()
        if not exists:raise SystemExit('Primero ejecuta seed-demo')
        print(make_dev_token(a.user_id))
if __name__=='__main__':main()
