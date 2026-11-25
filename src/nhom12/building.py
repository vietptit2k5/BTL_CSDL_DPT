"""ND3 full indexing with resumable generations and honest content-review state."""
import json
import platform
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
from .core import ContractError,digest,file_hash,inventory,assert_snapshot,sample_times
from . import repository as db

def now(): return datetime.now(timezone.utc).isoformat()

def write_json(path,value):
    path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

def implementation_hash():
    folder=Path(__file__).parent
    return digest({p.name:file_hash(p) for p in sorted(folder.iterdir()) if p.suffix in ('.py','.sql')})

def quality_review(record,reviews):
    r=reviews.get(record['video_id'],{})
    matched=r.get('sha256')==record['sha256']
    flags={k:r.get(k) if matched else None for k in ('single_scene','not_duplicate','no_large_logo')}
    state='issues' if any(v is False for v in flags.values()) else 'reviewed' if all(v is True for v in flags.values()) else 'pending'
    return dict(sha256=record['sha256'],status=state,**flags,
                reviewer=r.get('reviewer','') if matched else '',notes=r.get('notes','') if matched else '',
                stale_review=bool(r) and not matched)

def extract_video(source,meta,backend,encoder,spec,folder):
    import numpy as np
    from .features import motion_feature
    from .preprocess import content_box,resize_short
    sp=spec['sampling'];targets=sample_times(meta['duration'],sp['k'],sp['margin'])
    starts=sample_times(meta['duration']-sp['motion_dt'],sp['motion_pairs'],sp['margin'])
    ends=[t+sp['motion_dt'] for t in starts]
    if hasattr(backend,'sample_many'):
        requests=[(t,sp['decode_short_side'],False) for t in targets]
        requests += [(t,sp['motion_short_side'],True) for t in starts+ends]
        decoded_all=backend.sample_many(source,requests)
        decoded=decoded_all[:sp['k']]
        a=decoded_all[sp['k']:sp['k']+sp['motion_pairs']]
        b=decoded_all[sp['k']+sp['motion_pairs']:]
    else:
        decoded=backend.sample(source,targets,sp['decode_short_side'])
        a=backend.sample(source,starts,sp['motion_short_side'],gray=True)
        b=backend.sample(source,ends,sp['motion_short_side'],gray=True)
    if (len(decoded),len(a),len(b))!=(sp['k'],sp['motion_pairs'],sp['motion_pairs']):
        raise ContractError('Incomplete decoder output')
    box=content_box([im for t,im in decoded],spec)
    prepared=[resize_short(im.crop(box),spec['preprocess']['feature_short_side']) for t,im in decoded]
    features=encoder.extract(prepared)
    folder.mkdir(parents=True,exist_ok=False)
    frames=[];artifacts={}
    for i,((actual,image),vectors) in enumerate(zip(decoded,features,strict=True)):
        path=folder/f'f{i:02}.png';image.crop(box).save(path,compress_level=1)
        artifacts[str(path)]=file_hash(path)
        frames.append(dict(index=i,target=targets[i],actual=actual,image_path=str(path),features=vectors))
    ow,oh=decoded[0][1].size;mw,mh=a[0][1].size
    motion_box=tuple(round(v*s) for v,s in zip(box,(mw/ow,mh/oh,mw/ow,mh/oh)))
    pairs=[]
    for (ta,ia),(tb,ib) in zip(a,b,strict=True):
        if tb<=ta: raise ContractError('Invalid actual motion timestamps')
        pairs.append((np.asarray(ia.crop(motion_box)),np.asarray(ib.crop(motion_box)),tb-ta))
    motion=motion_feature(pairs)
    arrays={f:np.stack([v[f] for v in features]) for f in ('hsv','lbp','clip')}
    arrays.update(motion=motion,target_times=np.array(targets),actual_times=np.array([t for t,im in decoded]),
                  motion_start_pts=np.array([t for t,im in a]),motion_end_pts=np.array([t for t,im in b]))
    archive=folder/'features.npz';np.savez_compressed(archive,**arrays)
    artifacts[str(archive)]=file_hash(archive)
    return box,frames,motion,artifacts

def audit_index(index,spec,cfg,check_sources=True):
    from .pipeline import model_identity,runtime_identity
    con=db.connect(index,readonly=True)
    try:
        stamp=con.execute('SELECT status,spec_hash,model_identity,snapshot_json,implementation_version,implementation_hash,dataset_root,quality_status FROM build WHERE id=1').fetchone()
        if stamp[0]!='ready': raise ContractError('Index is not technically ready')
        if stamp[1]!=digest(spec) or stamp[2]!=model_identity(cfg) or stamp[4]!=db.IMPLEMENTATION_VERSION:
            raise ContractError('Index spec/model/implementation differs from current runtime')
        from .provenance import check_extraction
        provenance=check_extraction(Path(index).parent,stamp[5])
        if Path(stamp[6]).resolve()!=Path(cfg['dataset_root']).resolve():
            raise ContractError('Dataset root changed')
        environment=json.loads(Path(index).with_name('environment.json').read_text(encoding='utf-8'))
        if environment['packages']!=runtime_identity() or environment['device']!=cfg['device']:
            raise ContractError('Environment differs from extraction profile')
        snapshot=json.loads(stamp[3])
        if check_sources: assert_snapshot(snapshot,inventory(cfg['dataset_root'],spec))
        db.validate_complete(con,snapshot,spec['sampling']['k'],verify_artifacts=True)
        integrity=con.execute('PRAGMA integrity_check').fetchall()
        if integrity!=[('ok',)]: raise ContractError(f'SQLite integrity error: {integrity}')
        counts={t:con.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('videos','keyframes','frame_features','video_features','video_artifacts')}
        return dict(technical_status='ready',dataset_quality_status=stamp[7],integrity='ok',counts=counts,
                    by_class=dict(con.execute('SELECT class_code,count(*) FROM videos GROUP BY class_code')),
                    snapshot_hash=digest(snapshot),spec_hash=stamp[1],model_identity=stamp[2],implementation_hash=stamp[5],provenance=provenance)
    finally: con.close()

def build_index(spec,cfg,reviews_path=None,resume=None,stop_after=None):
    from .pipeline import model_identity,runtime_identity
    from .media import OpenCVBackend
    from .features import FrameExtractor
    if stop_after is not None and stop_after<=0: raise ContractError('stop_after must be positive')
    started=time.perf_counter();rows=inventory(cfg['dataset_root'],spec)
    if len(rows)<spec['dataset']['minimum_videos']: raise ContractError('XLSX requires >=500 videos')
    packages=runtime_identity();code_hash=implementation_hash()
    context=dict(spec_hash=digest(spec),snapshot_hash=digest(rows),model_identity=model_identity(cfg),
      implementation_version=db.IMPLEMENTATION_VERSION,implementation_hash=code_hash,
      dataset_root=str(Path(cfg['dataset_root']).resolve()),device=cfg['device'],packages=packages)
    reviews=json.loads(Path(reviews_path).read_text(encoding='utf-8')) if reviews_path else {}
    quality={r['video_id']:quality_review(r,reviews) for r in rows}
    quality_states=Counter(q['status'] for q in quality.values())
    quality_status='issues' if quality_states['issues'] else 'reviewed' if quality_states['reviewed']==len(rows) else 'pending'
    root=Path(cfg['artifacts']).resolve()
    if resume:
        run=Path(resume).resolve();run=run.parent if run.is_file() else run
        if not run.is_relative_to(root): raise ContractError('Resume must refer to a generation under project artifacts')
        if json.loads((run/'context.json').read_text(encoding='utf-8'))!=context:
            raise ContractError('Resume rejected: dataset/spec/model/code/environment changed')
        if (run/'index.sqlite').exists():
            audit_index(run/'index.sqlite',spec,cfg)
            print(f'Already ready: {run}',flush=True)
            return str(run/'index.sqlite')
        if not (run/'index.building.sqlite').is_file(): raise ContractError('No partial database to resume')
        con=db.connect(run/'index.building.sqlite')
    else:
        run=root/('build-'+uuid4().hex);run.mkdir(parents=True)
        write_json(run/'context.json',context);write_json(run/'spec.json',spec)
        write_json(run/'environment.json',dict(packages=packages,python=sys.version,platform=platform.platform(),device=cfg['device']))
        write_json(run/'snapshot.json',rows)
        con=db.create(run/'index.building.sqlite',dict(**context,snapshot=rows,created_at=now()))
    print(f'GENERATION {run}',flush=True)
    log=run/'events.jsonl';active=None;reused=0;processed=0
    def event(kind,**values):
        with log.open('a',encoding='utf-8') as f: f.write(json.dumps(dict(at=now(),event=kind,**values),ensure_ascii=False)+'\n')
    def progress(status):
        count=con.execute('SELECT count(*) FROM videos').fetchone()[0]
        value=dict(status=status,total=len(rows),completed=count,reused=reused,processed_this_session=processed,
                   current_video=active,elapsed_seconds=time.perf_counter()-started,quality_counts=dict(quality_states),dataset_quality_status=quality_status)
        write_json(run/'progress.json',value)
        return value
    try:
        con.execute("UPDATE build SET status='building',quality_status=? WHERE id=1",(quality_status,));con.commit()
        event('session_start',resume=bool(resume),context=context)
        metadata={};problems=[];backend=OpenCVBackend()
        saved=json.loads((run/'manifest.json').read_text(encoding='utf-8')) if (run/'manifest.json').exists() else None
        if saved and saved['snapshot_hash']==context['snapshot_hash'] and not saved['errors']:
            metadata=saved['metadata']
        else:
            def probe(record):
                try:
                    meta=backend.probe(Path(cfg['dataset_root'])/record['relative_path'])
                    if meta['codec'].lower() not in ('h264','avc1'): raise ContractError('Codec must be H.264')
                    if meta.get('container') and 'mp4' not in meta['container'].split(','):
                        raise ContractError('Container must be MP4')
                    duration=round(meta['duration'],1)
                    if not spec['dataset']['duration_rounded_min']<=duration<=spec['dataset']['duration_rounded_max']:
                        raise ContractError('Duration outside rounded report range')
                    return record['video_id'],meta,None
                except Exception as exc: return record['video_id'],None,f'{type(exc).__name__}: {exc}'
            with ThreadPoolExecutor(max_workers=6) as pool:
                for vid,meta,error in pool.map(probe,rows):
                    if error: problems.append(dict(video_id=vid,error=error))
                    else: metadata[vid]=meta
            write_json(run/'manifest.json',dict(snapshot_hash=context['snapshot_hash'],records=rows,metadata=metadata,errors=problems))
        if problems: raise ContractError(f'{len(problems)} metadata errors; see manifest.json; no files silently excluded')
        print(f'PREFLIGHT {len(metadata)}/{len(rows)} metadata passed; quality={quality_status}',flush=True)
        encoder=None
        for i,record in enumerate(rows):
            active=record['video_id'];t0=time.perf_counter()
            exists=con.execute('SELECT 1 FROM videos WHERE video_id=?',(active,)).fetchone()
            if exists:
                try:
                    db.validate_complete(con,[record],spec['sampling']['k'],verify_artifacts=True,subset=True)
                    reused+=1;event('video_reused',video_id=active)
                    continue
                except (ContractError,ValueError) as exc:
                    event('video_invalidated',video_id=active,error=str(exc));db.delete_video(con,active)
            if encoder is None:
                encoder=FrameExtractor(spec,model_path=cfg['model_path'],revision=cfg['model_revision'],device=cfg['device'],local_files_only=cfg['local_files_only'])
            source=Path(cfg['dataset_root'])/record['relative_path']
            if file_hash(source)!=record['sha256']: raise ContractError(f'{active}: source changed before extraction')
            folder=run/'frames'/active/uuid4().hex[:12]
            box,frames,motion,artifacts=extract_video(source,metadata[active],backend,encoder,spec,folder)
            if file_hash(source)!=record['sha256']: raise ContractError(f'{active}: source changed during extraction')
            db.add_video(con,record,metadata[active],box,quality[active],frames,motion,artifacts)
            db.validate_complete(con,[record],spec['sampling']['k'],verify_artifacts=True,subset=True)
            processed+=1;event('video_complete',video_id=active,seconds=time.perf_counter()-t0)
            state=progress('building')
            print(f'{state["completed"]}/{len(rows)} {active} {time.perf_counter()-t0:.2f}s (reused {reused})',flush=True)
            if stop_after and processed>=stop_after and state['completed']<len(rows):
                event('controlled_pause',completed=state['completed']);progress('paused')
                print('PAUSED: index is NOT ready; resume this generation to finish.',flush=True)
                return str(run/'index.building.sqlite')
        assert_snapshot(rows,inventory(cfg['dataset_root'],spec))
        if implementation_hash()!=code_hash: raise ContractError('Implementation changed while building')
        db.validate_complete(con,rows,spec['sampling']['k'],verify_artifacts=True)
        if con.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]: raise ContractError('SQLite integrity failed')
        con.execute("UPDATE build SET status='ready',completed_at=? WHERE id=1",(now(),));con.commit()
        summary=progress('ready');summary.update(context=context,technical_status='ready',quality_counts=dict(quality_states),
          counts={t:con.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('videos','keyframes','frame_features','video_features','video_artifacts')},
          by_class=dict(con.execute('SELECT class_code,count(*) FROM videos GROUP BY class_code')),
          metadata_seconds=sum(m['duration'] for m in metadata.values()))
        write_json(run/'summary.json',summary);event('build_ready',counts=summary['counts'])
    except BaseException as exc:
        if isinstance(exc,(SystemExit,KeyboardInterrupt)): kind=type(exc).__name__
        else: kind=f'{type(exc).__name__}: {exc}'
        con.rollback();con.execute("UPDATE build SET status='failed' WHERE id=1");con.commit()
        event('session_failed',video_id=active,error=kind);progress('failed')
        write_json(run/'failure.json',dict(video_id=active,error=kind,at=now()))
        raise
    finally: con.close()
    final=run/'index.sqlite';(run/'index.building.sqlite').rename(final)
    return str(final)
