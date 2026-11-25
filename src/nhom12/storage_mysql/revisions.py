"""Transactional invalidation of in-memory retrieval snapshots (course metadata manager)."""
import hashlib
from ..core import ContractError
from .connection import connect
from .repository import TABLES

TRACKED = (*TABLES, 'generations')


def trigger_definitions():
    for table in TRACKED:
        for event, short, values in [('INSERT', 'i', '(NEW.generation_id,1)'),
                                      ('UPDATE', 'u', '(OLD.generation_id,1),(NEW.generation_id,1)'),
                                      ('DELETE', 'd', '(OLD.generation_id,1)')]:
            name = f'nh12_rev_{table}_{short}'
            body = ('INSERT INTO retrieval_revisions(generation_id,revision) VALUES ' + values +
                    ' ON DUPLICATE KEY UPDATE revision=revision+1')
            yield name, table, event, body


def ensure_tracking(cfg):
    """Add tracking to this project's schema, preserving all certified feature rows."""
    if cfg.get('database',{}).get('tracking_mode')=='procedure':
        # Runtime account is SELECT + EXECUTE only. DDL is an administrator task.
        from .service import select_generation
        stamp(cfg,select_generation(cfg))
        return
    with connect(cfg) as con:
        cur = con.cursor()
        cur.execute("SELECT GET_LOCK(CONCAT('nh12-revisions-',LEFT(SHA2(DATABASE(),256),32)),10)")
        if cur.fetchone()[0] != 1:
            raise ContractError('MySQL revision setup is busy')
        try:
            cur.execute('CREATE TABLE IF NOT EXISTS retrieval_revisions ('
                        'generation_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,'
                        'revision BIGINT UNSIGNED NOT NULL) ENGINE=InnoDB')
            cur.execute('INSERT IGNORE INTO retrieval_revisions SELECT generation_id,0 FROM generations')
            con.commit()
            cur.execute('SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()')
            existing = {r[0] for r in cur.fetchall()}
            for name, table, event, body in trigger_definitions():
                if name not in existing:
                    cur.execute(f'CREATE TRIGGER {name} AFTER {event} ON {table} FOR EACH ROW {body}')
            con.commit()
        finally:
            cur.execute("SELECT RELEASE_LOCK(CONCAT('nh12-revisions-',LEFT(SHA2(DATABASE(),256),32)))"); cur.fetchone(); cur.close()


def stamp(cfg, generation):
    with connect(cfg) as con:
        cur = con.cursor()
        if cfg.get('database',{}).get('tracking_mode')=='procedure':
            cur.execute('CALL nh12_retrieval_stamp(%s)',(generation,))
            first=cur.fetchall();row=first[0] if first else None
            cur.nextset();counts=cur.fetchone();cur.fetchall()
            cur.nextset();definitions=cur.fetchall()
            while cur.nextset():cur.fetchall()
            cur.close()
            if row is None or row[1]!='ready' or counts is None:
                raise ContractError('MySQL retrieval snapshot is not ready')
            if {r[0] for r in definitions}!={d[0] for d in trigger_definitions()}:
                raise ContractError('MySQL retrieval revision triggers are incomplete')
            return (row,tuple(counts),hashlib.sha256(repr(definitions).encode()).hexdigest())
        cur.execute('SELECT r.revision,g.status,SHA2(CAST(g.context_json AS CHAR),256) '
                    'FROM retrieval_revisions r JOIN generations g USING(generation_id) WHERE generation_id=%s', (generation,))
        row = cur.fetchone()
        if row is None or row[1] != 'ready':
            raise ContractError('MySQL retrieval snapshot is not ready')
        # DDL such as TRUNCATE bypasses DML triggers: also verify counts and trigger definitions.
        counts = []
        for table in TABLES:
            cur.execute(f'SELECT COUNT(*) FROM {table} WHERE generation_id=%s', (generation,))
            counts.append(cur.fetchone()[0])
        cur.execute('SELECT TRIGGER_NAME,EVENT_OBJECT_TABLE,EVENT_MANIPULATION,ACTION_STATEMENT '
                    'FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE() AND TRIGGER_NAME LIKE %s '
                    'ORDER BY TRIGGER_NAME', ('nh12_rev_%',))
        definitions = cur.fetchall(); cur.close()
        if {r[0] for r in definitions} != {d[0] for d in trigger_definitions()}:
            raise ContractError('MySQL retrieval revision triggers are incomplete')
        return (row, tuple(counts), hashlib.sha256(repr(definitions).encode()).hexdigest())
