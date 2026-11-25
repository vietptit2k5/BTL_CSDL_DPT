import json
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
from ..core import PROJECT, ContractError
from . import stages
from .data import capture, guard_live
from .files import run_path

DEFAULT_RUN = PROJECT/'var/video_similarity/run01'


def add_arguments(subparsers):
    video=subparsers.add_parser('query-video',help='ND3: indexed video ID -> five other videos')
    video.add_argument('--video',required=True)
    video.add_argument('--run',type=Path,default=DEFAULT_RUN)
    video.add_argument('--baseline',action='store_true',help='Explicit CLIP-only demonstration; not selected weights')
    workflow=subparsers.add_parser('video-workflow',help='Replay ND3 steps B0-B8 with saved intermediate artifacts')
    workflow.add_argument('step',choices=['snapshot','b0','b1','b2','b3','b5','b6','b7','b8','status','replay'])
    workflow.add_argument('--run',type=Path,default=DEFAULT_RUN)
    workflow.add_argument('--diagnostic',action='store_true')
    workflow.add_argument('--legacy-root',type=Path,help='Original ND1 system; imported read-only, s01/s04 faithfully replayed')
    workflow.add_argument('--goal',type=Path)
    workflow.add_argument('--groups',type=Path)
    workflow.add_argument('--trace',type=Path)


def _execute(args,spec,cfg):
    from .nd1 import run_labels
    from .presentation import export_query,replay
    run=run_path(args.run)
    if args.command=='query-video':
        stages.require_b3(run)
        return export_query(run,spec,cfg,args.video,args.baseline)
    step=args.step
    if step=='status':return stages.status(run)
    if step=='replay':
        if not args.trace:raise ContractError('replay needs --trace')
        return replay(run,args.trace)
    if step=='snapshot':return capture(run,spec,cfg)
    if not (run/'snapshot/files.json').exists():capture(run,spec,cfg)
    guard_live(run,spec,cfg)
    if step=='b0':
        if args.legacy_root:
            from .nd1_original import run_original
            result=run_original(run,spec,cfg,args.legacy_root)
        elif args.diagnostic:result=run_labels(run,spec,cfg,diagnostic=True)
        else:raise ContractError('Official B0 requires --legacy-root pointing to the original ND1 system')
    elif step=='b1':result=stages.b1(run,args.goal,args.groups)
    elif step=='b2':result=stages.b2(run)
    elif step=='b3':result=stages.b3(run)
    elif step=='b5':result=stages.b5(run)
    elif step=='b6':result=stages.b6(run)
    elif step=='b7':result=stages.b7(run)
    else:result=stages.b8(run,spec,cfg)
    guard_live(run,spec,cfg)
    return result


def execute(args,spec,cfg):
    """Keep a terminal transcript for every manual command, including failures."""
    run=run_path(args.run);folder=run/'logs';folder.mkdir(exist_ok=True)
    name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid4().hex[:6]
    class Tee:
        def __init__(self,console,log):self.console=console;self.log=log
        def write(self,value):self.console.write(value);self.log.write(value);return len(value)
        def flush(self):self.console.flush();self.log.flush()
    with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
        log.write('COMMAND: '+json.dumps(sys.argv,ensure_ascii=False)+'\n')
        stream=Tee(sys.stdout,log)
        try:
            with redirect_stdout(stream),redirect_stderr(stream):result=_execute(args,spec,cfg)
            log.write('\nRESULT:\n'+json.dumps(result,ensure_ascii=False,indent=2)+'\n')
            return result
        except BaseException:
            traceback.print_exc(file=log);raise
