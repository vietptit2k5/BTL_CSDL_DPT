"""HTTP contracts use an explicit fake retrieval service; real browser/GPU evidence is separate."""
import hashlib
import http.client
import io
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from nhom12.core import load_settings
from nhom12.search import rank
from nhom12.webapp.server import Application,LocalServer,byte_range


class FakeSession:
    constructions=0
    release=None
    def __init__(self,spec,cfg):
        type(self).constructions+=1
        self.cfg=cfg;self.started=False;self.closed=False;self.queries=0
        self.index_report={'counts':dict(videos=5,keyframes=5,frame_features=15,video_features=5)}
    def close(self):self.closed=True
    def query(self,path):
        if type(self).release:type(self).release.wait(3)
        self.started=True;self.queries+=1
        folder=Path(self.cfg['artifacts'])/f'query-test-{self.queries}';folder.mkdir(exist_ok=True)
        raw=Path(path).read_bytes();(folder/'source-image.bin').write_bytes(raw)
        features={n:np.eye(1,d,dtype=np.float32).ravel() for n,d in [('hsv',128),('lbp',10),('clip',512)]}
        frames=[]
        for i in range(5):
            video=Path(self.cfg['dataset_root'])/f'V{i}.mp4';video.write_bytes(bytes(range(256))*4)
            frame=folder/f'frame{i}.png';Image.new('RGB',(10,10)).save(frame)
            frames.append(dict(video_id=f'V{i}',index=0,time=1.,image_path=str(frame),features=features))
        hits=rank(features,frames,dict(clip=.9,hsv=.1,lbp=0))
        for hit in hits:hit['video_path']=str(Path(self.cfg['dataset_root'])/(hit['video_id']+'.mp4'))
        from nhom12.result_export import export_videos
        export_videos(folder,hits,{h['video_id']:hashlib.sha256(Path(h['video_path']).read_bytes()).hexdigest() for h in hits})
        trace=dict(trace_version='nd4-v2',query_sha256=hashlib.sha256(raw).hexdigest(),artifact_sha256={},
            query_features={k:v.tolist() for k,v in features.items()},
            matched_features={f'{h["video_id"]}/0':{k:v.tolist() for k,v in features.items()} for h in hits},
            hits=hits,index='mysql:fixture/fixture',preprocess={'crop_box':[0,0,10,10]},timings_seconds={'total':.01},
            session={'cold':self.queries==1},search_policy={'weights':dict(clip=.9,hsv=.1,lbp=0)},dataset_quality_status='pending')
        (folder/'trace.json').write_text(json.dumps(trace),encoding='utf-8')
        Image.new('RGB',(10,10)).save(folder/'input.png')
        return str(folder/'demo.html')


class WebHTTP(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        spec,cfg=load_settings();cfg.update(artifacts=str(Path(self.tmp.name)/'artifacts'),dataset_root=self.tmp.name)
        FakeSession.constructions=0;FakeSession.release=None
        self.app=Application(spec,cfg,FakeSession);self.server=LocalServer(0,self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        image=io.BytesIO();Image.new('RGB',(30,40),128).save(image,format='PNG');self.image=image.getvalue()
    def stop(self):
        if FakeSession.release:FakeSession.release.set()
        self.server.shutdown();self.server.server_close();self.thread.join();self.app.close()
    def request(self,method,path,body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        con.request(method,path,body,headers or {})
        response=con.getresponse();data=response.read();result=(response.status,dict(response.getheaders()),data);con.close();return result
    def submit(self):
        code,headers,data=self.request('POST','/api/search',self.image,{'X-Nhom12-Request':'1'})
        self.assertEqual(code,202);return json.loads(data)['job_id']
    def wait(self,job):
        for _ in range(100):
            code,_,data=self.request('GET','/api/jobs/'+job);value=json.loads(data)
            if value['status']!='running':self.assertEqual(value['status'],'done',value);return value
            time.sleep(.02)
        self.fail('HTTP fixture job did not finish')
    def test_range_full_open_suffix_head_and_416(self):
        job=self.submit();result=self.wait(job);media=result['result']['hits'][0]['video_url']
        for value,expected in [('bytes=100-199',bytes(range(100,200))),('bytes=1000-',bytes(range(232,256))),('bytes=-8',bytes(range(248,256)))]:
            code,headers,data=self.request('GET',media,headers={'Range':value})
            self.assertEqual(code,206);self.assertEqual(data,expected);self.assertEqual(headers['Accept-Ranges'],'bytes');self.assertIn('/1024',headers['Content-Range'])
        code,headers,data=self.request('HEAD',media,headers={'Range':'bytes=0-1'})
        self.assertEqual(code,200);self.assertEqual(data,b'');self.assertEqual(headers['Content-Length'],'1024')
        for value in ('bytes=1024-','bytes=1-0','bytes=-0','bytes=0-1,3-5'):
            code,headers,data=self.request('GET',media,headers={'Range':value})
            self.assertEqual(code,416);self.assertEqual(headers['Content-Range'],'bytes */1024')
    def test_one_worker_busy_and_session_reused_then_reset(self):
        FakeSession.release=threading.Event();first=self.submit()
        self.assertEqual(self.request('POST','/api/search',self.image,{'X-Nhom12-Request':'1'})[0],409)
        self.assertEqual(self.request('POST','/api/reset',b'',{'X-Nhom12-Request':'1'})[0],409)
        FakeSession.release.set();self.wait(first)
        second=self.submit();self.wait(second);self.assertEqual(FakeSession.constructions,1)
        self.assertEqual(self.request('POST','/api/reset',b'',{'X-Nhom12-Request':'1'})[0],200)
        self.assertIsNone(self.app.session)
    def test_bad_input_oversize_and_cross_origin_rejected(self):
        self.assertEqual(self.request('POST','/api/search',b'broken',{'X-Nhom12-Request':'1'})[0],400)
        self.assertEqual(FakeSession.constructions,0)
        self.assertEqual(self.request('POST','/api/search',b'',{'Content-Length':str(65*1024*1024),'X-Nhom12-Request':'1'})[0],413)
        self.assertEqual(self.request('POST','/api/search',self.image,{'X-Nhom12-Request':'1','Origin':'https://example.org'})[0],403)
        self.assertEqual(self.request('POST','/api/search',self.image)[0],403)
        self.assertEqual(self.request('GET','/api/status',headers={'Host':'evil.example'})[0],403)
    def test_file_allowlist_and_download_headers(self):
        job=self.submit();result=self.wait(job)
        for path in ('/.mysql.local.json','/../config.json',f'/artifacts/{job}/source-image.bin',f'/media/{job}/NONEXISTENT.mp4',f'/artifacts/{job}/../../config.json'):
            self.assertEqual(self.request('GET',path)[0],404,path)
        code,headers,data=self.request('GET',result['result']['trace_url'])
        self.assertEqual(code,200);self.assertIn('attachment',headers['Content-Disposition'])
        self.assertNotIn('video_path',result['result']['hits'][0])
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])

    def test_result_video_and_zip_download_are_scoped_to_five_hits(self):
        job=self.submit();result=self.wait(job)['result']
        code,headers,data=self.request('GET',result['hits'][0]['download_url'])
        self.assertEqual(code,200);self.assertIn('attachment',headers['Content-Disposition'])
        self.assertEqual(data,bytes(range(256))*4)
        code,headers,data=self.request('GET',result['archive_url'])
        self.assertEqual(code,200);self.assertEqual(headers['Content-Type'],'application/zip')
        import zipfile
        with zipfile.ZipFile(io.BytesIO(data)) as archive:self.assertEqual(len(archive.namelist()),6)
        self.assertEqual(self.request('GET',f'/exports/{job}/source-image.bin')[0],404)
