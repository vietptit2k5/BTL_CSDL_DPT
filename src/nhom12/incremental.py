"""Build a new dataset/index generation, reusing certified unchanged descriptors.

Never edits the active dataset, active pointer, protected extraction functions or old runs.
Without --apply, only a change plan is returned.
"""
import copy
import json
import re
import shutil
import time
from pathlib import Path
from uuid import uuid4
import numpy as np
from .core import PROJECT,ContractError,digest,file_hash,inventory
from .file_snapshot import FrozenFiles,input_files
from .building import extract_video,implementation_hash,now,write_json
from .provenance import archive_sources
from .pipeline import model_identity,runtime_identity
from . import repository as db
from .storage_mysql.connection import connect
from .storage_mysql.repository import rows
from .storage_mysql.service import load_index,select_generation
from .storage_mysql.revisions import stamp


def change_plan(snapshot,spec,additions,removals,replace=False):
    current={r['video_id']:r for r in snapshot};removed=set(removals);added={}
    if not additions and not removals:raise ContractError('Specify --add and/or --remove')
    if len(removed)!=len(removals) or not removed<=current.keys():raise ContractError('Unknown or duplicate removal ID')
    code_folder={v:k for k,v in spec['classes'].items()}
    for raw in additions:
        path=Path(raw).resolve();vid=path.stem
        if not path.is_file() or path.suffix.lower()!='.mp4' or not re.fullmatch(r'[A-Z]{3}\d{3}',vid) or vid[:3] not in code_folder:
            raise ContractError('Added MP4 must have an ND1 ID, e.g. SEA087.mp4')
        if vid in added or vid in removed:raise ContractError('Duplicate or conflicting addition/removal')
        if vid in current and not replace:raise ContractError('Existing ID needs --replace')
        added[vid]=dict(video_id=vid,path=str(path),sha256=file_hash(path),size_bytes=path.stat().st_size,
                        relative_path=f'{code_folder[vid[:3]]}/{vid}.mp4',class_code=vid[:3])
    wanted=(current.keys()-removed)|added.keys()
    if len(wanted)<spec['dataset']['minimum_videos']:raise ContractError('Change would violate minimum video count')
    reused=sorted(v for v in wanted if v in current and (v not in added or added[v]['sha256']==current[v]['sha256']))
    extracted=sorted(wanted-set(reused))
    return dict(added=added,removed=sorted(removed),reused=reused,extract=extracted,
                final_count=len(wanted),active_dataset_changed=False)


def load_source(spec,cfg):
    generation=select_generation(cfg);before=stamp(cfg,generation)
    frames,paths,model,label,context,report=load_index(spec,cfg,generation,metadata=True)
    with connect(cfg) as con:
        data={table:rows(con,table,generation) for table in ('videos','keyframes','video_features','video_artifacts')}
    if stamp(cfg,generation)!=before:raise ContractError('Source MySQL generation changed during planning')
    return dict(generation=generation,frames=frames,context=context,data=data)


def build_generation(spec,cfg,source,plan,admin_connection):
    from .media import OpenCVBackend
    from .features import FrameExtractor
    from .storage_mysql.migrate import migrate
    started=time.perf_counter();version=Path(cfg['artifacts'])/'dataset_versions'/uuid4().hex
    root=version/'dataset';artifacts=version/'artifacts';run=artifacts/('build-'+uuid4().hex)
    run.mkdir(parents=True);old=json.loads(source['context']['build']['snapshot_json'])
    old_by={r['video_id']:r for r in old};ids=sorted((old_by.keys()-set(plan['removed']))|plan['added'].keys())
    lease=FrozenFiles(input_files(spec,cfg))
    try:
        for folder in spec['classes']:(root/folder).mkdir(parents=True,exist_ok=True)
        for vid in ids:
            r=plan['added'].get(vid) or old_by[vid]
            src=Path(r['path']) if 'path' in r else Path(cfg['dataset_root'])/r['relative_path']
            dest=root/r['relative_path'];shutil.copyfile(src,dest)
            if file_hash(dest)!=r['sha256']:raise ContractError('Versioned source copy differs')
        new_cfg=copy.deepcopy(cfg);new_cfg.update(dataset_root=str(root.resolve()),artifacts=str(artifacts.resolve()))
        new_cfg['database']['backend']='mysql'
        snapshot=inventory(root,spec);by_id={r['video_id']:r for r in snapshot}
        packages=runtime_identity();model=model_identity(cfg);code_hash=implementation_hash()
        context=dict(spec_hash=digest(spec),snapshot_hash=digest(snapshot),model_identity=model,
                     implementation_version=db.IMPLEMENTATION_VERSION,implementation_hash=code_hash,
                     dataset_root=str(root.resolve()),device=cfg['device'],packages=packages)
        write_json(run/'context.json',context);write_json(run/'snapshot.json',snapshot);write_json(run/'spec.json',spec)
        write_json(run/'environment.json',dict(packages=packages,device=cfg['device']))
        con=db.create(run/'index.building.sqlite',dict(**context,snapshot=snapshot,created_at=now()))
        frame_features={(r['video_id'],r['index']):r['features'] for r in source['frames']}
        old_videos={r[0]:r for r in source['data']['videos']}
        old_frames={vid:[] for vid in ids}
        for vid,i,target,actual,path in source['data']['keyframes']:
            if vid in old_frames:old_frames[vid].append(dict(index=i,target=target,actual=actual,image_path=path,features=frame_features[(vid,i)]))
        motions={r[0]:np.frombuffer(r[2],dtype='<f4') for r in source['data']['video_features']}
        manifests={r[0]:json.loads(r[1]) for r in source['data']['video_artifacts']}
        backend=OpenCVBackend();encoder=None;qualities=[]
        try:
            for n,vid in enumerate(ids,1):
                if vid in plan['reused']:
                    row=old_videos[vid];meta,crop,quality=(json.loads(row[i]) for i in (5,6,7))
                    db.add_video(con,by_id[vid],meta,crop,quality,old_frames[vid],motions[vid],manifests[vid])
                else:
                    path=root/by_id[vid]['relative_path'];meta=backend.probe(path)
                    if meta['codec'].lower() not in ('h264','avc1') or not spec['dataset']['duration_rounded_min']<=round(meta['duration'],1)<=spec['dataset']['duration_rounded_max']:
                        raise ContractError('Added video violates ND1 codec/duration contract')
                    if encoder is None:encoder=FrameExtractor(spec,model_path=cfg['model_path'],revision=cfg['model_revision'],device=cfg['device'],local_files_only=cfg['local_files_only'])
                    crop,frames,motion,files=extract_video(path,meta,backend,encoder,spec,run/vid)
                    quality=dict(sha256=by_id[vid]['sha256'],status='pending',single_scene=None,not_duplicate=None,no_large_logo=None,reviewer='',notes='new or replaced video; human review required')
                    db.add_video(con,by_id[vid],meta,crop,quality,frames,motion,files)
                qualities.append(quality.get('status','pending'))
                if n%50==0 or n==len(ids):print(f'Incremental {n}/{len(ids)}; extraction required {len(plan["extract"])}',flush=True)
            db.validate_complete(con,snapshot,16,verify_artifacts=True)
            state='issues' if 'issues' in qualities else 'reviewed' if set(qualities)=={'reviewed'} else 'pending'
            con.execute("UPDATE build SET status='ready',quality_status=? WHERE id=1",(state,));con.commit()
        finally:con.close();encoder=None
        (run/'index.building.sqlite').replace(run/'index.sqlite');archive_sources(run)
        admin_cfg=copy.deepcopy(new_cfg);admin_cfg['database'].update(connection_file=str(admin_connection),tracking_mode='direct')
        migration=migrate(run/'index.sqlite',spec,admin_cfg)
        # Runtime profile uses the scoped connection. Its artifacts pointer is isolated.
        config_path=version/'config.json';write_json(config_path,new_cfg)
        result=dict(status='ready_separate_version',source_generation=source['generation'],new_generation=migration['generation'],
                    reused=len(plan['reused']),extracted=len(plan['extract']),removed=plan['removed'],
                    config=str(config_path),seconds=time.perf_counter()-started,
                    active_config_changed=False,active_pointer_changed=False)
        write_json(version/'change-plan.json',plan);write_json(version/'result.json',result)
        return result
    except BaseException as exc:
        write_json(version/'failure.json',dict(error_type=type(exc).__name__,active_index_unchanged=True))
        raise
    finally:lease.close()


def execute(args,spec,cfg):
    source=load_source(spec,cfg);snapshot=json.loads(source['context']['build']['snapshot_json'])
    plan=change_plan(snapshot,spec,args.add,args.remove,args.replace)
    if not args.apply:
        target=Path(cfg['artifacts'])/'dataset_plans'/(uuid4().hex+'.json')
        target.parent.mkdir(parents=True,exist_ok=True)
        write_json(target,dict(source_generation=source['generation'],**plan))
        return dict(status='plan_only',plan=str(target),source_generation=source['generation'],
                    reused=len(plan['reused']),extract=plan['extract'],removed=plan['removed'],
                    final_count=plan['final_count'],active_dataset_changed=False)
    admin=args.admin_connection or PROJECT/'.mysql.admin.local.json'
    if not admin.is_file():raise ContractError('Incremental import needs a local administrator connection file')
    return build_generation(spec,cfg,source,plan,admin)
