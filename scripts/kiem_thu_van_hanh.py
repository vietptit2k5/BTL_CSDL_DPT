"""Real MySQL/GPU + local HTTP functional validation; NO relevance evaluation.

python scripts/kiem_thu_van_hanh.py --port 8766 --keep-alive 180
"""
import argparse
import hashlib
import http.client
import json
import sys
import threading
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import load_settings,file_hash
from nhom12.environment import configure_runtime
from nhom12.webapp.server import Application,LocalServer
from nhom12.result_export import verify_export
from nhom12.query_evidence import verify_trace


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=0);ap.add_argument('--keep-alive',type=int,default=0)
    args=ap.parse_args();configure_runtime();spec,cfg=load_settings();out=ROOT/'var/completion';out.mkdir(exist_ok=True)
    app=Application(spec,cfg);server=LocalServer(args.port,app)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    port=server.server_port;print(f'Functional test server: http://127.0.0.1:{port}',flush=True)
    def request(method,path,body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',port,timeout=60)
        con.request(method,path,body,headers or {});r=con.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),data);con.close();return result
    def get(path):
        code,_,raw=request('GET',path);assert code==200,(path,code);return json.loads(raw)
    results=[]
    try:
        assert request('GET','/')[0]==200
        assert request('POST','/api/search',b'broken',{'X-Nhom12-Request':'1'})[0]==400
        frames=json.loads((ROOT/'var/video_similarity/run01/snapshot/frames.json').read_text(encoding='utf-8'))
        indexed=next(Path(r['image_path']) for r in frames if r['video_id']=='WAT028' and r['index']==0)
        external=ROOT/'var/search_phases/04_query/inputs/external-coffee.png'
        cases=[('indexed_functional',indexed),('outside_topic_functional',external),('repeat_functional',indexed)]
        for name,path in cases:
            started=time.perf_counter();code,_,raw=request('POST','/api/search',path.read_bytes(),{'X-Nhom12-Request':'1','Content-Type':'application/octet-stream'})
            assert code==202,(name,code);job=json.loads(raw)['job_id']
            while True:
                state=get('/api/jobs/'+job)
                if state['status']!='running':break
                if time.perf_counter()-started>600:raise RuntimeError('Functional query timeout')
                time.sleep(.5)
            assert state['status']=='done',state
            result=state['result'];hits=result['hits'];assert len({h['video_id'] for h in hits})==5
            assert [h['score'] for h in hits]==sorted((h['score'] for h in hits),reverse=True)
            folder=app.jobs[job]['folder'];export=verify_export(folder);replay=verify_trace(folder/'trace.json')
            code,headers,raw=request('GET',hits[0]['video_url'],headers={'Range':'bytes=0-511'})
            assert code==206 and len(raw)==512 and headers['Accept-Ranges']=='bytes'
            code,headers,raw=request('GET',hits[0]['download_url'])
            assert code==200 and 'attachment' in headers['Content-Disposition']
            manifest=json.loads((folder/'result-manifest.json').read_text(encoding='utf-8'))
            assert hashlib.sha256(raw).hexdigest()==manifest['files'][0]['sha256']
            code,headers,raw=request('GET',result['archive_url'])
            assert code==200 and hashlib.sha256(raw).hexdigest()==file_hash(folder/'results.zip')
            row=dict(case=name,trace=str(folder/'trace.json'),demo=str(folder/'demo.html'),
                     cold=result['session']['cold'],wall_seconds=time.perf_counter()-started,
                     server_job_seconds=state['elapsed_seconds'],timings=result['timings_seconds'],
                     export=export,replay=replay,top5=[h['video_id'] for h in hits])
            results.append(row);print(f'PASS {name}: cold={row["cold"]}, job={row["server_job_seconds"]:.2f}s, export exact',flush=True)
            (out/'functional_progress.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        assert get('/api/status')['completed_queries']==3
        report=dict(status='passed',backend='mysql',queries=results,port=port,
                    cold_job_seconds=results[0]['server_job_seconds'],warm_job_seconds=[r['server_job_seconds'] for r in results[1:]],
                    image_relevance_evaluation='deferred_by_user',browser_playback_verified=False,
                    scope='functional HTTP, GPU, source-index integrity, five MP4 copies/ZIP and byte-range delivery only')
        (out/'functional_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Functional validation saved. Independent image evaluation was NOT run.',flush=True)
        deadline=time.monotonic()+args.keep_alive
        while time.monotonic()<deadline and not (out/'stop_test_server').exists():time.sleep(1)
    finally:server.shutdown();server.server_close();thread.join();app.close()


if __name__=='__main__':main()
