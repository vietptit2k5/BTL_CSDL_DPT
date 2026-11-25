"""Real MySQL/GPU validation with independent photos, variants, and scalar replay."""
import json
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageEnhance
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from nhom12.core import load_settings,file_hash,ContractError
from nhom12.environment import configure_runtime
from nhom12.querying import SearchSession
from nhom12.query_evidence import verify_trace
from nhom12.search import rank
from nhom12.storage_mysql.connection import connect
from nhom12.storage_mysql.repository import rows
from nhom12.building import write_json

def main():
    configure_runtime();spec,cfg=load_settings()
    out=root/'var/search_phases/04_query';inputs=out/'inputs';inputs.mkdir(parents=True,exist_ok=True)
    pointer=json.loads((root/'var/current_mysql_index.json').read_text(encoding='utf-8'));generation=pointer['generation']
    with connect(cfg) as con:
        keyframes=rows(con,'keyframes',generation)
        source_hashes={p:s for vid,manifest in rows(con,'video_artifacts',generation) for p,s in json.loads(manifest).items()}
    cases=[]
    for code in ('SEA','WAT','FOR','MOU','RIV','FLO'):
        row=next(r for r in keyframes if r[0].startswith(code) and r[1]==0)
        path=inputs/f'indexed-{row[0]}.png';shutil.copyfile(row[4],path)
        cases.append(dict(id=path.stem,path=str(path),kind='indexed_keyframe_functional_smoke'))
    external=[]
    for name in ('astronaut','coffee','chelsea','rocket'):
        path=inputs/f'external-{name}.png'
        if not path.is_file():raise RuntimeError('Prepare independent scikit-image photos first')
        if file_hash(path) in source_hashes.values():raise AssertionError('External image duplicates an indexed artifact')
        item=dict(id=path.stem,path=str(path),kind='independent_photo_outside_six_scene_classes',
                  source=f'https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.{name}')
        cases.append(item);external.append(item)
    original=Image.open(inputs/'external-coffee.png')
    portrait=original.crop((180,0,380,400));portrait.save(inputs/'portrait.png')
    ImageEnhance.Brightness(original).enhance(.1).save(inputs/'dark.png')
    cases.extend([dict(id='portrait',path=str(inputs/'portrait.png'),kind='derived_independent_photo_portrait'),
                  dict(id='dark',path=str(inputs/'dark.png'),kind='derived_independent_photo_dark')])
    (inputs/'broken.jpg').write_bytes(b'not an image')
    results=[];reference_checks=[];failures=[]
    start=time.perf_counter()
    with patch('nhom12.repository.connect',side_effect=AssertionError('Online phase4 must never use SQLite')):
        with SearchSession(spec,cfg) as session:
            for bad in (inputs/'broken.jpg',inputs/'missing.png'):
                try:session.query(bad)
                except ContractError as exc:failures.append(dict(input=bad.name,error=str(exc)))
                else:raise AssertionError('Invalid image accepted')
            assert not session.started
            for i,case in enumerate(cases):
                print(f'QUERY {i+1}/{len(cases)} {case["id"]}',flush=True)
                request_start=time.perf_counter()
                demo=session.query(case['path'])
                wall_seconds=time.perf_counter()-request_start
                trace_path=Path(demo).with_name('trace.json');trace=json.loads(trace_path.read_text(encoding='utf-8'))
                replay=verify_trace(trace_path)
                assert trace['retrieval']['scanned_frames']==8976
                assert len({h['video_id'] for h in trace['hits']})==5
                assert all(Path(h[k]).is_file() for h in trace['hits'] for k in ('video_path','image_path'))
                result=dict(**case,query_sha256=trace['query_sha256'],demo=demo,trace=str(trace_path),
                            timings=trace['timings_seconds'],wall_seconds=wall_seconds,cold=trace['session']['cold'],replay=replay,
                            top5=[h['video_id'] for h in trace['hits']],scores=[h['score'] for h in trace['hits']])
                results.append(result)
                # Full baseline comparison includes in-dataset, outside-topic, portrait and dark.
                if i in (0,6,10,11):
                    ref_start=time.perf_counter()
                    query={k:np.asarray(v,dtype='<f4') for k,v in trace['query_features'].items()}
                    expected=rank(query,session.frames,cfg['search']['weights'])
                    for actual,reference in zip(trace['hits'],expected,strict=True):
                        for key,value in reference.items():assert actual[key]==value,(case['id'],key)
                    reference_checks.append(dict(case=case['id'],passed=True,scalar_seconds=time.perf_counter()-ref_start,
                                                 matrix_seconds=trace['timings_seconds']['search']))
                print(f'PASS {case["id"]}: {result["top5"]}; query={trace["timings_seconds"]["total"]:.3f}s; search={trace["timings_seconds"]["search"]:.3f}s',flush=True)
                write_json(out/'progress.json',dict(completed=len(results),total=len(cases),results=results))
            initialization=session.initialization
    warm=[r['wall_seconds'] for r in results if not r['cold']]
    report=dict(status='passed',backend='mysql',generation=generation,device=cfg['device'],cases=results,
                initialization=initialization,independent_sources=external,full_scalar_comparisons=reference_checks,
                invalid_inputs=failures,warm_median_seconds=float(np.median(warm)),warm_max_seconds=max(warm),
                elapsed_seconds=time.perf_counter()-start,quality_review='pending',
                academic_effectiveness='not_evaluated_no_independent_relevance_labels')
    write_json(out/'validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cases','independent_sources')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr=sys.stdout
    main()
