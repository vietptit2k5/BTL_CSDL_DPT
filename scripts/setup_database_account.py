"""Set up a scoped runtime account. Passwords are generated/stored locally, never printed.

python scripts/setup_database_account.py
Keeps the original admin connection in ignored .mysql.admin.local.json.
"""
import copy
import json
import secrets
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import load_settings,ContractError
from nhom12.storage_mysql.administration import install
from nhom12.storage_mysql.connection import connect,settings
from nhom12.storage_mysql.revisions import stamp
from nhom12.storage_mysql.service import select_generation
from nhom12.environment import configure_runtime


def main():
    configure_runtime();spec,cfg=load_settings();current=ROOT/'.mysql.local.json';admin=ROOT/'.mysql.admin.local.json'
    marker=ROOT/'.db_accounts.local.json'
    if not admin.exists():shutil.copyfile(current,admin)
    admin_cfg=copy.deepcopy(cfg);admin_cfg['database'].update(connection_file=str(admin),tracking_mode='direct')
    generation=select_generation(admin_cfg);before=stamp(admin_cfg,generation)
    install(admin_cfg)
    value=settings(admin_cfg);database=value['database']
    if marker.exists():
        account=json.loads(marker.read_text(encoding='utf-8'));runtime=json.loads(current.read_text(encoding='utf-8'))
        if runtime['user']!=account['user']:raise ContractError('Managed account marker and runtime connection differ')
    else:
        runtime={**value,'user':'nh12_app_'+uuid4().hex[:8],'password':secrets.token_urlsafe(32)}
        with connect(admin_cfg,server_only=True) as con:
            cur=con.cursor()
            cur.execute('CREATE USER %s@%s IDENTIFIED BY %s',(runtime['user'],'127.0.0.1',runtime['password']))
            cur.execute(f'GRANT SELECT ON `{database}`.* TO %s@%s',(runtime['user'],'127.0.0.1'))
            cur.execute(f'GRANT EXECUTE ON PROCEDURE `{database}`.nh12_retrieval_stamp TO %s@%s',(runtime['user'],'127.0.0.1'))
            cur.close()
        probe=ROOT/'var/runtime-account-probe.json';probe.write_text(json.dumps(runtime),encoding='utf-8')
        test_cfg=copy.deepcopy(cfg);test_cfg['database'].update(connection_file=str(probe),tracking_mode='procedure')
        try:
            if stamp(test_cfg,generation)!=before:raise ContractError('Scoped account stamp differs from administrator stamp')
            with connect(test_cfg) as con:
                cur=con.cursor();cur.execute('SELECT COUNT(*) FROM v_video_metadata WHERE generation_id=%s',(generation,))
                count=cur.fetchone()[0];cur.close()
            if count<500:raise ContractError('Unexpected runtime metadata count')
            temporary=current.with_suffix('.tmp');temporary.write_text(json.dumps(runtime,indent=2),encoding='utf-8');temporary.replace(current)
            marker.write_text(json.dumps(dict(user=runtime['user'],host='127.0.0.1',database=database,
                   created_at=datetime.now(timezone.utc).isoformat(),privileges=['SELECT database.*','EXECUTE nh12_retrieval_stamp']),indent=2),encoding='utf-8')
        finally:
            if probe.exists():probe.unlink()
    raw=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    raw['database']['tracking_mode']='procedure'
    (ROOT/'config.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
    admin_profile={**raw,'database':{**raw['database'],'connection_file':str(admin),'tracking_mode':'direct'}}
    (ROOT/'var/admin.config.json').write_text(json.dumps(admin_profile,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='configured',runtime_user=runtime['user'],database=database,
          runtime_privileges=['SELECT','EXECUTE tracking reader'],feature_rows_changed=False,password_printed=False),ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except ContractError as exc:raise SystemExit(str(exc))
