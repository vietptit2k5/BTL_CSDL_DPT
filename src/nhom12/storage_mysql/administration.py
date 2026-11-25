"""Administrator-only setup; never changes the certified generation feature rows."""
from .connection import connect,settings
from .repository import TABLES
from .revisions import ensure_tracking


def install(cfg):
    direct={**cfg,'database':{**cfg['database'],'tracking_mode':'direct'}}
    ensure_tracking(direct)
    counts=','.join(f'(SELECT COUNT(*) FROM `{t}` WHERE generation_id=requested)' for t in TABLES)
    procedure=f"""CREATE PROCEDURE nh12_retrieval_stamp(IN requested CHAR(32))
    SQL SECURITY DEFINER READS SQL DATA
    BEGIN
      SELECT r.revision,g.status,SHA2(CAST(g.context_json AS CHAR),256)
        FROM retrieval_revisions r JOIN generations g USING(generation_id)
        WHERE r.generation_id=requested;
      SELECT {counts};
      SELECT TRIGGER_NAME,EVENT_OBJECT_TABLE,EVENT_MANIPULATION,ACTION_STATEMENT
        FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()
          AND TRIGGER_NAME LIKE 'nh12_rev_%' ORDER BY TRIGGER_NAME;
    END"""
    view="""CREATE OR REPLACE SQL SECURITY INVOKER VIEW v_video_metadata AS
      SELECT generation_id,video_id,class_code,relative_path,size_bytes,sha256,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.duration')) AS DECIMAL(12,4)) AS duration_seconds,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.fps')) AS DECIMAL(12,4)) AS fps,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.width')) AS UNSIGNED) AS width,
        CAST(JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.height')) AS UNSIGNED) AS height,
        JSON_UNQUOTE(JSON_EXTRACT(metadata_json,'$.codec')) AS codec,
        JSON_UNQUOTE(JSON_EXTRACT(quality_json,'$.status')) AS indexed_review_status
      FROM videos"""
    with connect(cfg) as con:
        cur=con.cursor()
        cur.execute("SELECT ROUTINE_NAME FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=DATABASE() AND ROUTINE_NAME='nh12_retrieval_stamp'")
        if cur.fetchone() is None:cur.execute(procedure)
        cur.execute(view);con.commit();cur.close()
    return dict(status='installed',database=settings(cfg)['database'],procedure='nh12_retrieval_stamp',view='v_video_metadata')


def metadata(cfg,generation,class_code=None,min_duration=None,max_duration=None,portrait=False):
    clauses=['generation_id=%s'];params=[generation]
    for field,op,value in [('class_code','=',class_code),('duration_seconds','>=',min_duration),('duration_seconds','<=',max_duration)]:
        if value is not None:clauses.append(f'{field}{op}%s');params.append(value)
    if portrait:clauses.append('height>width')
    with connect(cfg) as con:
        cur=con.cursor(dictionary=True)
        cur.execute('SELECT video_id,class_code,duration_seconds,fps,width,height,codec,size_bytes '
                    'FROM v_video_metadata WHERE '+' AND '.join(clauses)+' ORDER BY video_id',tuple(params))
        rows=cur.fetchall();cur.close()
    for row in rows:
        for field in ('duration_seconds','fps'):
            if row[field] is not None:row[field]=float(row[field])
    return dict(generation=generation,count=len(rows),videos=rows)
