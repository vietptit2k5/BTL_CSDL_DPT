from .connection import doctor, connect
from .migrate import migrate, verify
from .service import select_generation


def execute(args, spec, cfg):
    if args.mysql_command=='setup':
        from .administration import install
        return install(cfg)
    if args.mysql_command=='metadata':
        from .administration import metadata
        return metadata(cfg,select_generation(cfg),args.class_code,args.min_duration,args.max_duration,args.portrait)
    if args.mysql_command == 'doctor':
        return doctor(cfg)
    if args.mysql_command == 'migrate':
        return migrate(args.source, spec, cfg)
    if args.mysql_command == 'verify':
        return verify(select_generation(cfg, args.index), spec, cfg, args.source)
    with connect(cfg) as con:
        cur = con.cursor()
        cur.execute('SELECT generation_id,status,source_sha256,imported_at FROM generations ORDER BY imported_at')
        result = [dict(generation=r[0], status=r[1], source_sha256=r[2], imported_at=r[3].isoformat()) for r in cur.fetchall()]
        cur.close()
        return result
