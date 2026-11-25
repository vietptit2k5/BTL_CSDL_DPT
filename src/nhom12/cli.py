import argparse
import importlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from .core import ContractError,load_settings,inventory,digest

def main():
    from .environment import configure_runtime
    configure_runtime()
    ap=argparse.ArgumentParser(description='D23 nhóm 12: scaffold ND1 đến ND5')
    ap.add_argument('--config',type=Path)
    sub=ap.add_subparsers(dest='command',required=True)
    doctor=sub.add_parser('doctor',help='Inspect dependencies without loading models')
    doctor.add_argument('--deep',action='store_true',help='Import actual native libraries and inspect CUDA')
    sub.add_parser('plan',help='Hash dataset and emit extraction plan; no inference')
    b=sub.add_parser('build');b.add_argument('--reviews',type=Path)
    b.add_argument('--resume',type=Path,help='Existing generation folder or database')
    b.add_argument('--stop-after',type=int,help='Controlled pause after N new videos, for recovery checks')
    verify=sub.add_parser('verify');verify.add_argument('--index',required=True,type=Path)
    q=sub.add_parser('query');q.add_argument('--index',help='MySQL generation/pointer; SQLite path with SQLite config');q.add_argument('--image',required=True,type=Path)
    batch=sub.add_parser('query-batch',help='Reuse the verified MySQL index and GPU model for several images')
    batch.add_argument('--index');batch.add_argument('--images',nargs='+',required=True,type=Path)
    replay=sub.add_parser('replay',help='Recompute all returned-hit scores without MySQL or a GPU')
    replay.add_argument('--trace',required=True,type=Path)
    web=sub.add_parser('serve',help='Run the local image-search UI and byte-range media server')
    web.add_argument('--port',type=int,default=8765)
    review=sub.add_parser('reviews',help='SHA256-bound content review, separate from features')
    review.add_argument('action',choices=['init','prepare','import','status','legacy'])
    review.add_argument('--csv',type=Path);review.add_argument('--backup-root',type=Path,default=Path('D:/csdldpt_backup'))
    update=sub.add_parser('dataset-update',help='Plan or build a separate dataset generation; active index stays unchanged')
    update.add_argument('--add',nargs='*',type=Path,default=[]);update.add_argument('--remove',nargs='*',default=[])
    update.add_argument('--replace',action='store_true');update.add_argument('--apply',action='store_true')
    update.add_argument('--admin-connection',type=Path)
    mysql=sub.add_parser('mysql',help='Manage the project MySQL database')
    mysql_sub=mysql.add_subparsers(dest='mysql_command',required=True)
    mysql_sub.add_parser('doctor')
    mysql_sub.add_parser('list')
    mysql_sub.add_parser('setup',help='Administrator: install tracking reader and metadata view')
    metadata=mysql_sub.add_parser('metadata',help='Filter typed metadata in MySQL')
    metadata.add_argument('--class-code',choices=['SEA','WAT','FOR','MOU','RIV','FLO'])
    metadata.add_argument('--min-duration',type=float);metadata.add_argument('--max-duration',type=float)
    metadata.add_argument('--portrait',action='store_true')
    migration=mysql_sub.add_parser('migrate');migration.add_argument('--source',required=True,type=Path)
    mv=mysql_sub.add_parser('verify');mv.add_argument('--index');mv.add_argument('--source',type=Path)
    from .video_workflow.cli import add_arguments as add_video_arguments
    add_video_arguments(sub)
    args=ap.parse_args()
    try:
        spec,cfg=load_settings(args.config)
        if args.command in ('query-video','video-workflow'):
            from .video_workflow.cli import execute as execute_video
            print(json.dumps(execute_video(args,spec,cfg),ensure_ascii=False,indent=2))
        elif args.command=='dataset-update':
            from .incremental import execute as execute_update
            print(json.dumps(execute_update(args,spec,cfg),ensure_ascii=False,indent=2))
        elif args.command=='reviews':
            from .quality_registry import execute as execute_review
            print(json.dumps(execute_review(args,spec,cfg),ensure_ascii=False,indent=2))
        elif args.command=='serve':
            from .webapp.server import serve
            serve(spec,cfg,args.port)
        elif args.command=='query-batch':
            from .querying import SearchSession
            results=[]
            with SearchSession(spec,cfg,args.index) as session:
                for image in args.images:
                    try: results.append(dict(image=str(image),demo=session.query(image),status='passed'))
                    except ContractError as exc: results.append(dict(image=str(image),status='error',error=str(exc)))
            print(json.dumps(results,ensure_ascii=False,indent=2))
            if any(r['status']=='error' for r in results): return 2
        elif args.command=='replay':
            from .query_evidence import verify_trace
            print(json.dumps(verify_trace(args.trace),ensure_ascii=False,indent=2))
        elif args.command=='mysql':
            from .storage_mysql.cli import execute
            print(json.dumps(execute(args,spec,cfg),indent=2,ensure_ascii=False))
        elif args.command=='doctor':
            report=dict(python=sys.version,executable=sys.executable,spec_hash=digest(spec),modules={m:bool(importlib.util.find_spec(m)) for m in
               ('numpy','PIL','cv2','skimage','torch','transformers')},model_path=cfg['model_path'],
               model_revision=cfg['model_revision'],ffprobe=shutil.which('ffprobe'),ffmpeg=shutil.which('ffmpeg'))
            if args.deep:
                report['imports']={}
                for name in report['modules']:
                    try:
                        module=importlib.import_module(name)
                        report['imports'][name]=dict(version=getattr(module,'__version__','unknown'),path=module.__file__)
                    except Exception as exc:
                        report['imports'][name]=dict(error=f'{type(exc).__name__}: {exc}')
                try:
                    import torch
                    report['cuda']=dict(available=torch.cuda.is_available(),device=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
                except ImportError: pass
            print(json.dumps(report,indent=2))
        elif args.command=='plan':
            rows=inventory(cfg['dataset_root'],spec)
            folder=Path(cfg['artifacts']);folder.mkdir(parents=True,exist_ok=True)
            report=dict(spec_hash=digest(spec),snapshot_hash=digest(rows),video_count=len(rows),
                        expected_keyframes=len(rows)*16,expected_frame_vectors=len(rows)*16*3,
                        expected_motion_vectors=len(rows),meets_minimum=len(rows)>=500,
                        quality_review='pending',snapshot=rows)
            (folder/'plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            reviews={r['video_id']:dict(sha256=r['sha256'],single_scene=None,not_duplicate=None,no_large_logo=None,reviewer='',notes='') for r in rows}
            target=folder/'reviews.template.json'
            if not target.exists():
                target.write_text(json.dumps(reviews,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in report.items() if k!='snapshot'},indent=2))
        elif args.command=='verify':
            from .building import audit_index
            print(json.dumps(audit_index(args.index,spec,cfg),indent=2))
        else:
            from .pipeline import build,query_image
            print(build(spec,cfg,args.reviews,resume=args.resume,stop_after=args.stop_after) if args.command=='build' else query_image(spec,cfg,args.index,args.image))
    except (ContractError,ImportError,FileNotFoundError) as exc:
        ap.exit(2,f'{type(exc).__name__}: {exc}\n')
