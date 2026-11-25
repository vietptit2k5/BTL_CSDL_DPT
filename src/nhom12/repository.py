"""ND3: typed feature persistence; missing vectors are errors, never zero padding."""
import json
import sqlite3
from pathlib import Path
from .core import ContractError, FEATURES, validate_vector, file_hash

IMPLEMENTATION_VERSION='nd3-v2'

def connect(path, readonly=False):
    p = Path(path).resolve()
    con = sqlite3.connect(p.as_uri() + '?mode=ro', uri=True) if readonly else sqlite3.connect(p)
    con.execute('PRAGMA foreign_keys=ON')
    return con

def create(path, build):
    if Path(path).exists():
        raise ContractError(f'Refusing overwrite: {path}')
    con = connect(path)
    con.executescript(Path(__file__).with_name('schema.sql').read_text())
    con.execute('INSERT INTO build(id,status,spec_hash,implementation_version,model_identity,snapshot_json,created_at,implementation_hash,dataset_root) VALUES (1,?,?,?,?,?,?,?,?)',
                ('building',build['spec_hash'],IMPLEMENTATION_VERSION,build['model_identity'],
                 json.dumps(build['snapshot'],sort_keys=True),build['created_at'],build.get('implementation_hash',''),build.get('dataset_root','')))
    for f,dim in FEATURES.items():
        con.execute('INSERT INTO feature_catalog VALUES (?,?,?,?)',
                    (f,dim,'L2' if f=='clip' else 'L1_each_block' if f=='motion' else 'L1',
                     'cosine' if f=='clip' else 'Bhattacharyya' if f=='hsv' else 'Chi-square'))
    con.commit()
    return con

def add_video(con, record, metadata, crop, quality, frames, motion, artifacts=None):
    with con:
        con.execute('INSERT INTO videos VALUES (?,?,?,?,?,?,?,?)',
          (record['video_id'],record['class_code'],record['relative_path'],record['sha256'],
           record['size_bytes'],json.dumps(metadata),json.dumps(crop),json.dumps(quality)))
        for frame in frames:
            i = frame['index']
            con.execute('INSERT INTO keyframes VALUES (?,?,?,?,?)',
              (record['video_id'],i,frame['target'],frame['actual'],frame['image_path']))
            for name in ('hsv','lbp','clip'):
                x = validate_vector(name,frame['features'][name])
                con.execute('INSERT INTO frame_features VALUES (?,?,?,?)',(record['video_id'],i,name,x.tobytes()))
        x = validate_vector('motion',motion)
        con.execute('INSERT INTO video_features VALUES (?,?,?)',(record['video_id'],'motion',x.tobytes()))
        if artifacts is not None:
            con.execute('INSERT INTO video_artifacts VALUES (?,?)',(record['video_id'],json.dumps(artifacts,sort_keys=True)))

def delete_video(con,vid):
    with con:
        for table in ('video_artifacts','frame_features','video_features','keyframes','videos'):
            con.execute(f'DELETE FROM {table} WHERE video_id=?',(vid,))

def validate_artifacts(con,vid):
    rows=con.execute('SELECT manifest_json FROM video_artifacts WHERE video_id=?',(vid,)).fetchall()
    if len(rows)!=1:
        raise ContractError(f'{vid}: missing artifact manifest')
    manifest=json.loads(rows[0][0])
    expected_paths={r[0] for r in con.execute('SELECT image_path FROM keyframes WHERE video_id=?',(vid,))}
    if not expected_paths.issubset(manifest):
        raise ContractError(f'{vid}: keyframes missing from artifact manifest')
    for path,sha in manifest.items():
        if not Path(path).is_file() or file_hash(path)!=sha:
            raise ContractError(f'{vid}: artifact changed or missing: {path}')

def validate_complete(con, expected, k=16, verify_artifacts=False, subset=False):
    import numpy as np
    ids = {r[0] for r in con.execute('SELECT video_id FROM videos')}
    expected_ids={r['video_id'] for r in expected}
    mismatch=(not expected_ids.issubset(ids)) if subset else (ids!=expected_ids)
    if mismatch:
        raise ContractError('Database video inventory incomplete')
    if subset: ids=expected_ids
    stored={r[0]:r[1:] for r in con.execute('SELECT video_id,class_code,relative_path,sha256,size_bytes FROM videos')}
    for record in expected:
        if stored[record['video_id']]!=(record['class_code'],record['relative_path'],record['sha256'],record['size_bytes']):
            raise ContractError('Stored video metadata does not match indexed snapshot')
    for vid in ids:
        import math
        timing=con.execute('SELECT target_time,actual_time FROM keyframes WHERE video_id=? ORDER BY frame_index',(vid,)).fetchall()
        if any(not math.isfinite(x) or x<0 for pair in timing for x in pair):
            raise ContractError(f'{vid}: invalid keyframe timestamp')
        if any(a[0]>=b[0] or a[1]>=b[1] for a,b in zip(timing,timing[1:])):
            raise ContractError(f'{vid}: keyframe timestamps must increase')
        indexes = [r[0] for r in con.execute('SELECT frame_index FROM keyframes WHERE video_id=? ORDER BY frame_index',(vid,))]
        if indexes != list(range(k)):
            raise ContractError(f'{vid}: need exactly K distinct keyframes')
        for i in indexes:
            rows = con.execute('SELECT feature,vector FROM frame_features WHERE video_id=? AND frame_index=?',(vid,i)).fetchall()
            if {r[0] for r in rows} != {'hsv','lbp','clip'}:
                raise ContractError(f'{vid}/{i}: missing reported feature')
            for f,blob in rows:
                validate_vector(f,np.frombuffer(blob,dtype='<f4'))
        rows = con.execute('SELECT vector FROM video_features WHERE video_id=?',(vid,)).fetchall()
        if len(rows)!=1:
            raise ContractError(f'{vid}: missing motion feature')
        validate_vector('motion',np.frombuffer(rows[0][0],dtype='<f4'))
        if verify_artifacts:
            validate_artifacts(con,vid)
    if con.execute('PRAGMA foreign_key_check').fetchall():
        raise ContractError('Broken foreign keys')

def read_frames(con):
    import numpy as np
    frames=[]
    for vid,i,t,path in con.execute('SELECT video_id,frame_index,actual_time,image_path FROM keyframes ORDER BY video_id,frame_index'):
        ff={f:np.frombuffer(blob,dtype='<f4') for f,blob in con.execute(
          'SELECT feature,vector FROM frame_features WHERE video_id=? AND frame_index=?',(vid,i))}
        frames.append(dict(video_id=vid,index=i,time=t,image_path=path,features=ff))
    return frames
