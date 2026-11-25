"""Application flows ND3/ND4. Output is isolated by generation; sources stay read-only."""
import json
import platform
import sys
import re
from datetime import datetime,timezone
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4
from .core import (ContractError,assert_snapshot,digest,file_hash,inventory,sample_times)
from . import repository as db

def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

def model_identity(cfg):
    if cfg['model_path']:
        p=Path(cfg['model_path']).resolve()
        if not p.is_dir():
            raise ContractError('model_path must point to a local checkpoint directory')
        identity={str(f.relative_to(p)):file_hash(f) for f in sorted(p.rglob('*')) if f.is_file()}
        if not identity:
            raise ContractError('Empty model checkpoint')
        return digest(identity)
    if not cfg['model_revision'] or not re.fullmatch(r'[0-9a-fA-F]{40}',cfg['model_revision']):
        raise ContractError('Pin model_revision or configure a local checkpoint before build')
    return cfg['model_revision']

def runtime_identity():
    from importlib.metadata import PackageNotFoundError
    packages={name:version(name) for name in ('numpy','Pillow','scikit-image','torch','transformers')}
    for name in ('opencv-python-headless','opencv-python'):
        try:
            packages[name]=version(name)
            break
        except PackageNotFoundError:
            continue
    else:
        raise ContractError('No installed OpenCV distribution')
    return packages

def build(spec,cfg,reviews_path=None,resume=None,stop_after=None):
    """Full, resumable ND3 extraction. Content reviews may remain pending."""
    from .building import build_index
    index=build_index(spec,cfg,reviews_path=reviews_path,resume=resume,stop_after=stop_after)
    if Path(index).name=='index.sqlite':
        from .provenance import archive_sources
        archive_sources(Path(index).parent)
        if cfg.get('database',{}).get('backend')=='mysql':
            from .storage_mysql.migrate import migrate
            migrate(index,spec,cfg)
            return str(Path(cfg['artifacts'])/'current_mysql_index.json')
    return index

def _sqlite_query_data(spec,cfg,index_path):
    con=db.connect(index_path,readonly=True)
    try:
        stamp=con.execute('SELECT status,spec_hash,model_identity,snapshot_json,implementation_version FROM build WHERE id=1').fetchone()
        if not stamp or stamp[0]!='ready' or stamp[1]!=digest(spec):
            raise ContractError('Index is incomplete or built under a different report spec')
        if stamp[2]!=model_identity(cfg):
            raise ContractError('Query model differs from indexed model')
        if stamp[4]!=db.IMPLEMENTATION_VERSION:
            raise ContractError('Unsupported index implementation version')
        recorded_code=con.execute('SELECT implementation_hash FROM build WHERE id=1').fetchone()[0]
        from .provenance import check_extraction
        check_extraction(Path(index_path).parent,recorded_code)
        recorded=json.loads(Path(index_path).with_name('environment.json').read_text(encoding='utf-8'))
        if recorded['packages']!=runtime_identity():
            raise ContractError('Extraction dependencies changed; rebuild or restore recorded versions')
        if recorded['device']!=cfg['device']:
            raise ContractError('Query execution device differs from the indexed extraction profile')
        snapshot=json.loads(stamp[3])
        assert_snapshot(snapshot,inventory(cfg['dataset_root'],spec))
        db.validate_complete(con,snapshot,spec['sampling']['k'])
        frames=db.read_frames(con)
        paths=dict(con.execute('SELECT video_id,relative_path FROM videos'))
    finally:
        con.close()
    return frames,paths,stamp[2],str(Path(index_path).resolve())

def query_image(spec,cfg,index_path,image_path):
    if cfg.get('database',{}).get('backend')=='mysql':
        from .querying import SearchSession
        with SearchSession(spec,cfg,index_path) as session:
            return session.query(image_path)
    from PIL import Image,ImageOps
    from .features import FrameExtractor
    from .preprocess import prepare_image
    from .search import rank
    if index_path is None: raise ContractError('SQLite query requires --index')
    frames,paths,index_model,index_label=_sqlite_query_data(spec,cfg,index_path)
    extractor=FrameExtractor(spec,model_path=cfg['model_path'],revision=cfg['model_revision'],
                            device=cfg['device'],local_files_only=cfg['local_files_only'])
    with Image.open(image_path) as source:
        original=ImageOps.exif_transpose(source).convert('RGB')
    prepared=prepare_image(original,spec)
    vectors=extractor.extract([prepared])[0]
    hits=rank(vectors,frames,cfg['search']['weights'])
    for hit in hits:
        hit['video_path']=str(Path(cfg['dataset_root'])/paths[hit['video_id']])
    output=Path(cfg['artifacts'])/('query-'+uuid4().hex);output.mkdir(parents=True)
    original.save(output/'input.png');prepared.save(output/'preprocessed.png')
    trace=dict(query_sha256=file_hash(image_path),spec_hash=digest(spec),index=index_label,
               model_identity=index_model,search_policy=cfg['search'],
               query_features={f:x.tolist() for f,x in vectors.items()},hits=hits)
    write_json(output/'trace.json',trace)
    from .demo import render
    render(output,trace)
    return str(output/'demo.html')
