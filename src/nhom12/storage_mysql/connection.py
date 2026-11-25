import json
import re
from contextlib import contextmanager
from pathlib import Path
from ..core import PROJECT, ContractError


def settings(cfg):
    path = PROJECT / cfg.get('database', {}).get('connection_file', '.mysql.local.json')
    try:
        value = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as exc:
        raise ContractError('Cannot read MySQL connection file; see mysql.local.example.json') from exc
    allowed = {'host', 'port', 'user', 'password', 'database'}
    if set(value) - allowed or not allowed.issubset(value):
        raise ContractError('MySQL connection file requires host, port, user, password, database only')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', value['database']):
        raise ContractError('Unsafe MySQL database name')
    value['port'] = int(value['port'])
    return value


@contextmanager
def connect(cfg, server_only=False):
    import mysql.connector
    args = settings(cfg)
    if server_only:
        args.pop('database')
    con = None
    try:
        con = mysql.connector.connect(**args, charset='utf8mb4', use_unicode=True,
                                      connection_timeout=10, autocommit=False)
        yield con
    except mysql.connector.Error as exc:
        # Connector messages may contain user names, query text, or credentials.
        raise ContractError(f'MySQL error {exc.errno} (SQLSTATE {exc.sqlstate}); check connection/permissions/server log') from None
    finally:
        if con is not None:
            con.close()


def doctor(cfg):
    value = settings(cfg)
    with connect(cfg, server_only=True) as con:
        cur = con.cursor()
        cur.execute('SELECT VERSION()')
        server = cur.fetchone()[0]
        cur.execute('SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s', (value['database'],))
        exists = cur.fetchone() is not None
        cur.close()
    return dict(connected=True, server=server, host=value['host'], port=value['port'],
                database=value['database'], database_exists=exists)
