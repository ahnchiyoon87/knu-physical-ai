"""Apply service schema and configure the dedicated read-only login explicitly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from backend.common.config import ROOT, env
from backend.common.gateway import database
from backend.common.log import span

def main():
    readonly = conninfo_to_dict(env('READONLY_DATABASE_URL'))
    if readonly.get('user') != 'lab_reader' or not readonly.get('password'):
        raise ValueError('READONLY_DATABASE_URL은 별도 암호를 설정한 lab_reader 계정이어야 합니다')
    with span('data', 'data.bootstrap', 'scripts/bootstrap.py:main'), database() as db:
        db.execute("SELECT pg_advisory_xact_lock(hashtext('equipment-assistant-schema'))")
        for path in sorted((ROOT / 'supabase/migrations').glob('*.sql')):
            db.execute(path.read_text(encoding='utf-8'))
        if not db.execute("SELECT 1 FROM pg_roles WHERE rolname='lab_reader'").fetchone():
            db.execute('CREATE ROLE lab_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT')
        db.execute(sql.SQL('ALTER ROLE lab_reader PASSWORD {}').format(sql.Literal(readonly['password'])))
        db.execute('ALTER ROLE lab_reader SET default_transaction_read_only=on')
        db.execute('GRANT USAGE ON SCHEMA lab TO lab_reader')
        db.execute('GRANT SELECT ON ALL TABLES IN SCHEMA lab TO lab_reader')
        db.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA lab GRANT SELECT ON TABLES TO lab_reader')
        db.execute('GRANT USAGE ON SCHEMA extensions TO lab_reader')
    sys.stdout.write('스키마와 읽기 전용 계정 설정 완료. 모델은 호출하지 않았습니다.\n')
if __name__ == '__main__':
    main()
