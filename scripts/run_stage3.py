"""Full real ND3 build, controlled recovery check, audit, and direct spot checks."""
import json
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from nhom12.environment import configure_runtime
configure_runtime()
from nhom12.core import load_settings,file_hash
from nhom12.pipeline import build
from nhom12.building import audit_index,extract_video,write_json
from nhom12 import repository as db

class Tee:
    def __init__(self,original,log): self.original=original;self.log=log
    def write(self,text):
        self.original.write(text);self.original.flush();self.log.write(text);self.log.flush()
    def flush(self): self.original.flush();self.log.flush()
    def __getattr__(self,name): return getattr(self.original,name)

def main():
    import numpy as np
    from nhom12.features import FrameExtractor
    from nhom12.media import OpenCVBackend
    spec,cfg=load_settings();output=root/'var/search_phases/03_database';output.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter();state_path=output/'state.json'
    with (output/'execution.log').open('a',encoding='utf-8') as log:
        previous_stdout=sys.stdout;sys.stdout=Tee(previous_stdout,log)
        try:
            if state_path.exists():
                state=json.loads(state_path.read_text(encoding='utf-8'));generation=Path(state['generation'])
            else:
                partial=build(spec,cfg,stop_after=3)
                generation=Path(partial).parent
                write_json(state_path,dict(generation=str(generation),status='paused_after_3_real_videos'))
            index=build(spec,cfg,resume=generation)
            write_json(state_path,dict(generation=str(generation),index=index,status='ready'))
            audit=audit_index(index,spec,cfg)
            write_json(output/'audit.json',audit)
            con=db.connect(index,readonly=True)
            try:
                encoder=FrameExtractor(spec,model_path=cfg['model_path'],device=cfg['device'],local_files_only=True)
                backend=OpenCVBackend();checks=[]
                for vid in ('SEA005','MOU023','FLO114'):
                    relative,meta,sha=con.execute('SELECT relative_path,metadata_json,sha256 FROM videos WHERE video_id=?',(vid,)).fetchone()
                    assert file_hash(Path(cfg['dataset_root'])/relative)==sha
                    folder=output/'direct_checks'/vid
                    if folder.exists():
                        from uuid import uuid4
                        folder=folder/uuid4().hex[:8]
                    box,frames,motion,artifacts=extract_video(Path(cfg['dataset_root'])/relative,json.loads(meta),backend,encoder,spec,folder)
                    differences={}
                    for f in ('hsv','lbp','clip'):
                        max_delta=0.0
                        for frame in frames:
                            blob=con.execute('SELECT vector FROM frame_features WHERE video_id=? AND frame_index=? AND feature=?',(vid,frame['index'],f)).fetchone()[0]
                            stored=np.frombuffer(blob,dtype='<f4');direct=frame['features'][f]
                            np.testing.assert_allclose(stored,direct,atol=1e-5,rtol=1e-5)
                            max_delta=max(max_delta,float(np.max(abs(stored-direct))))
                        differences[f]=max_delta
                    stored=np.frombuffer(con.execute('SELECT vector FROM video_features WHERE video_id=?',(vid,)).fetchone()[0],dtype='<f4')
                    np.testing.assert_allclose(stored,motion,atol=1e-5,rtol=1e-5)
                    differences['motion']=float(np.max(abs(stored-motion)))
                    checks.append(dict(video_id=vid,status='passed',max_abs_differences=differences))
                write_json(output/'direct_checks.json',checks)
            finally: con.close()
            events=[json.loads(line) for line in (generation/'events.jsonl').read_text(encoding='utf-8').splitlines()]
            result=dict(status='passed',index=index,audit=audit,direct_checks=checks,
                        controlled_pause_events=sum(e['event']=='controlled_pause' for e in events),
                        reused_video_events=sum(e['event']=='video_reused' for e in events),
                        elapsed_seconds_this_execution=time.perf_counter()-started)
            write_json(output/'validation.json',result)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        finally: sys.stdout=previous_stdout

if __name__=='__main__': main()
