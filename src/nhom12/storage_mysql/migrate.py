"""Non-destructive, transactional migration; certified SQLite remains untouched."""
import hashlib
import json
from pathlib import Path
from ..core import ContractError, file_hash
from .. import repository as sqlite
from ..building import audit_index, write_json
from .connection import connect, settings
from .repository import TABLES, ORDER, rows, canonical, generation_info, validate


def initialize(cfg):
    name = settings(cfg)['database']
    with connect(cfg, server_only=True) as con:
        cur = con.cursor()
        cur.execute(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci')
        cur.close()
    with connect(cfg) as con:
        cur = con.cursor()
        cur.execute('SHOW FULL TABLES')
        existing = {r[0] for r in cur.fetchall()}
        if existing:
            if 'schema_metadata' not in existing:
                raise ContractError('Target database contains unrelated tables; choose an empty project database')
            cur.execute('SELECT version FROM schema_metadata WHERE id=1')
            if cur.fetchone() != ('nhom12-mysql-v1',):
                raise ContractError('Unsupported MySQL schema')
            if not set(TABLES).union({'schema_metadata', 'generations', 'v_video_overview'}).issubset(existing):
                raise ContractError('MySQL schema is incomplete; use a new empty database')
        else:
            # DDL is deliberately separate: MySQL DDL performs implicit commits.
            source = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
            for statement in source.split(';'):
                if statement.strip():
                    cur.execute(statement)
            con.commit()
        cur.close()


def compare_source(con, generation, source):
    proof = {}
    for table, columns in TABLES.items():
        before = source.execute(f'SELECT {",".join(columns)} FROM {table} ORDER BY {ORDER[table]}').fetchall()
        after = rows(con, table, generation)
        if len(before) != len(after):
            raise ContractError(f'Migration row count differs: {table}')
        checksum = hashlib.sha256()
        for a, b in zip(before, after, strict=True):
            a, b = canonical(table, a), canonical(table, b)
            if a != b:
                raise ContractError(f'Migration changed a value: {table}')
            for value in b:
                raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')
                checksum.update(len(raw).to_bytes(8, 'little')); checksum.update(raw)
        proof[table] = dict(rows=len(after), canonical_sha256=checksum.hexdigest(), equal=True)
    return proof


def migrate(source_path, spec, cfg):
    source_path = Path(source_path).resolve()
    print('Validating certified source and local artifacts...', flush=True)
    source_audit = audit_index(source_path, spec, cfg)
    sha = file_hash(source_path)
    generation = sha[:32]
    initialize(cfg)
    source = sqlite.connect(source_path, readonly=True)
    try:
        source.row_factory = __import__('sqlite3').Row
        build = dict(source.execute('SELECT * FROM build WHERE id=1').fetchone())
        source.row_factory = None
        context = dict(build=build, source_path=str(source_path), artifact_root=str(source_path.parent),
                       environment=json.loads(source_path.with_name('environment.json').read_text(encoding='utf-8')),
                       source_audit=source_audit)
        with connect(cfg) as con:
            cur = con.cursor()
            lock = 'nhom12-migrate-' + hashlib.sha256(settings(cfg)['database'].encode()).hexdigest()[:32]
            cur.execute('SELECT GET_LOCK(%s,10)', (lock,))
            if cur.fetchone()[0] != 1:
                raise ContractError('Another MySQL migration is running')
            try:
                cur.execute('SELECT status,source_sha256 FROM generations WHERE generation_id=%s', (generation,))
                previous = cur.fetchone()
                if previous and previous[1] != sha:
                    raise ContractError('MySQL generation collision')
                if not previous:
                    cur.execute('INSERT INTO generations(generation_id,status,source_sha256,context_json) VALUES (%s,%s,%s,%s)',
                                (generation, 'importing', sha, json.dumps(context)))
                    con.commit()
                if not previous or previous[0] != 'ready':
                    for table in TABLES:
                        if rows(con, table, generation):
                            raise ContractError('Partial generation contains committed data; inspect before retry')
                    for table, columns in TABLES.items():
                        data = source.execute(f'SELECT {",".join(columns)} FROM {table} ORDER BY {ORDER[table]}').fetchall()
                        placeholders = ','.join(['%s'] * (len(columns) + 1))
                        sql = f'INSERT INTO {table}(generation_id,{",".join(columns)}) VALUES ({placeholders})'
                        for offset in range(0, len(data), 500):
                            cur.executemany(sql, [(generation,) + tuple(row) for row in data[offset:offset+500]])
                        print(f'MySQL {table}: {len(data)}', flush=True)
                    report, _, _ = validate(con, generation, spec)
                    proof = compare_source(con, generation, source)
                    if file_hash(source_path) != sha:
                        raise ContractError('SQLite source changed during migration')
                    cur.execute("UPDATE generations SET status='ready' WHERE generation_id=%s", (generation,))
                    con.commit()
                else:
                    report, _, _ = validate(con, generation, spec)
                    proof = compare_source(con, generation, source)
                result = dict(backend='mysql', database=settings(cfg)['database'], generation=generation,
                              source_sha256=sha, technical_status='ready', source_audit=source_audit,
                              **report, exact_copy=proof)
            except BaseException:
                con.rollback()
                # Only the empty import marker survives a failure; retry never duplicates vectors.
                if not previous or previous[0] != 'ready':
                    cur.execute("UPDATE generations SET status='failed' WHERE generation_id=%s AND status<>'ready'", (generation,))
                    con.commit()
                raise
            finally:
                cur.execute('SELECT RELEASE_LOCK(%s)', (lock,)); cur.fetchone(); cur.close()
        output = Path(cfg['artifacts']) / 'search_phases' / '03_mysql'
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / 'migration.json', result)
        pointer = dict(backend='mysql', database=result['database'], generation=generation)
        write_json(Path(cfg['artifacts']) / 'current_mysql_index.json', pointer)
        return result
    finally:
        source.close()


def verify(generation, spec, cfg, source_path=None):
    with connect(cfg) as con:
        info = generation_info(con, generation)
        report, _, _ = validate(con, generation, spec, verify_artifacts=True)
        if source_path:
            if file_hash(source_path) != info['source_sha256']:
                raise ContractError('Verification SQLite SHA256 differs')
            source = sqlite.connect(source_path, readonly=True)
            try:
                report['exact_copy'] = compare_source(con, generation, source)
            finally:
                source.close()
        return dict(backend='mysql', generation=generation, technical_status='ready', **report)
