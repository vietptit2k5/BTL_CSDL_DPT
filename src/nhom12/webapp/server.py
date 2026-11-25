"""Loopback UI, one GPU worker, explicit media allowlists and RFC9110 byte ranges."""
import copy
import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
from ..core import ContractError
from ..querying import SearchSession, read_query
from ..query_evidence import verify_trace

STATIC = Path(__file__).with_name('static')
ASSETS = {'/':'index.html','/app.css':'app.css','/app.js':'app.js','/favicon.svg':'favicon.svg'}
ARTIFACTS = {'input.png','preprocessed.png','clip-input-preview.png','histograms.svg','query-features.npz','trace.json',
             'result-manifest.json','results.zip','quality-review.json'}
TYPES = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
         '.svg':'image/svg+xml','.png':'image/png','.mp4':'video/mp4','.json':'application/json; charset=utf-8','.npz':'application/octet-stream','.zip':'application/zip'}
ID = r'[0-9a-f]{32}'


def byte_range(value, size):
    """One byte range, inclusive end. Multiple/unsatisfiable ranges are rejected."""
    match = re.fullmatch(r'bytes=(\d*)-(\d*)', value or '')
    if not match or size <= 0 or not any(match.groups()):
        raise ValueError('Unsatisfiable byte range')
    first, last = match.groups()
    if not first:
        length = int(last)
        if length <= 0: raise ValueError('Unsatisfiable byte range')
        return max(0, size-length), size-1
    start = int(first); end = min(int(last), size-1) if last else size-1
    if start >= size or end < start: raise ValueError('Unsatisfiable byte range')
    return start, end


def public_error(exc):
    detail = str(exc)
    if 'decode query' in detail or 'too small' in detail:
        return 'Không đọc được ảnh. Hãy chọn một ảnh hợp lệ có kích thước tối thiểu 3 × 3 pixel.'
    if '64 MiB' in detail:
        return 'Ảnh không tồn tại hoặc vượt quá giới hạn 64 MB.'
    if 'MySQL error' in detail:
        return 'Chưa kết nối được MySQL. Kiểm tra dịch vụ và cấu hình kết nối rồi thử lại.'
    if any(word in detail for word in ('changed','differs','different','closed','snapshot')):
        return 'Dữ liệu hoặc phiên làm việc đã thay đổi. Bấm “Phiên mới” rồi thử lại sau khi kiểm tra dữ liệu.'
    if any(word in detail.lower() for word in ('model','checkpoint','cuda')):
        return 'Chưa nạp được mô hình tìm kiếm. Kiểm tra model và thiết bị trong cấu hình dự án.'
    return 'Chưa thể tìm kiếm với dữ liệu hiện tại. Kiểm tra cấu hình và nhật ký ứng dụng rồi thử lại.'


class Application:
    def __init__(self, spec, cfg, session_factory=SearchSession):
        self.spec=copy.deepcopy(spec); self.cfg=copy.deepcopy(cfg)
        self.session_factory=session_factory; self.session=None
        self.lock=threading.RLock(); self.jobs={}; self.active=None
        self.uploads=Path(cfg['artifacts'])/'web/uploads';self.uploads.mkdir(parents=True,exist_ok=True)
        self.log_path=Path(cfg['artifacts'])/'web/events.jsonl';self.log_path.parent.mkdir(parents=True,exist_ok=True)

    def event(self, kind, **values):
        with self.lock:
            with self.log_path.open('a',encoding='utf-8') as log:
                log.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),event=kind,**values),ensure_ascii=False)+'\n')

    def status(self):
        with self.lock:
            started=bool(self.session and self.session.started and not self.session.closed)
            return dict(busy=self.active is not None,session_ready=started,
                        needs_reset=bool(self.session and self.session.closed),
                        completed_queries=self.session.queries if self.session else 0,
                        backend='mysql',classes=len(self.spec['classes']),
                        counts=self.session.index_report['counts'] if started else None)

    def submit(self, raw):
        with self.lock:
            if self.active: raise BlockingIOError('A search is already running')
            job_id=uuid4().hex; folder=self.uploads/job_id; folder.mkdir()
            image=folder/'image.bin';image.write_bytes(raw)
            # Decode before loading MySQL/model. Untrusted filenames never become paths.
            read_query(image)
            cold=not self.session or not self.session.started
            self.jobs[job_id]=dict(id=job_id,status='running',cold=cold,created=time.time(),result=None,error=None)
            self.active=job_id
            threading.Thread(target=self._search,args=(job_id,image),daemon=True,name='nhom12-query').start()
            return job_id

    def _search(self, job_id, image):
        start=time.perf_counter()
        self.event('search_started',job_id=job_id)
        try:
            if self.session is None:
                self.session=self.session_factory(self.spec,self.cfg)
            demo=self.session.query(image)
            folder=Path(demo).resolve().parent
            if not folder.is_relative_to(Path(self.cfg['artifacts']).resolve()):
                raise ContractError('Unexpected query result folder')
            trace=json.loads((folder/'trace.json').read_text(encoding='utf-8'))
            verify_trace(folder/'trace.json')
            with self.lock:
                self.jobs[job_id].update(status='done',folder=folder,trace=trace,
                                         elapsed_seconds=time.perf_counter()-start)
            self.event('search_done',job_id=job_id,elapsed_seconds=time.perf_counter()-start,
                       video_ids=[h['video_id'] for h in trace['hits']],cold=trace['session']['cold'])
        except Exception as exc:
            logging.exception('Local search failed')
            with self.lock:
                self.jobs[job_id].update(status='error',error=public_error(exc))
            self.event('search_error',job_id=job_id,error_type=type(exc).__name__,message=public_error(exc))
        finally:
            with self.lock: self.active=None

    def job(self, job_id):
        with self.lock:
            job=self.jobs.get(job_id)
            if job is None: raise KeyError('Unknown query')
            result={key:job.get(key) for key in ('id','status','cold','created','error','elapsed_seconds')}
            if job['status']=='done':
                trace=job['trace'];base=f'/artifacts/{job_id}/'
                hits=[]
                for h in trace['hits']:
                    hit={k:v for k,v in h.items() if k not in ('video_path','image_path')}
                    hit.update(video_url=f'/media/{job_id}/{h["video_id"]}.mp4',frame_url=f'/frames/{job_id}/{h["video_id"]}.png')
                    if h.get('exported_video'):
                        hit['download_url']=f'/exports/{job_id}/{Path(h["exported_video"]).name}?download=1'
                    hits.append(hit)
                result['result']=dict(hits=hits,preprocess=trace['preprocess'],timings_seconds=trace['timings_seconds'],
                    elapsed_seconds=job['elapsed_seconds'],session=trace['session'],search_policy=trace['search_policy'],
                    dataset_quality_status=trace['dataset_quality_status'],
                    images={name:base+name for name in ('input.png','preprocessed.png','clip-input-preview.png','histograms.svg')},
                    trace_url=base+'trace.json?download=1',vectors_url=base+'query-features.npz?download=1',
                    archive_url=base+'results.zip?download=1' if (job['folder']/'results.zip').is_file() else None,
                    export_manifest_url=base+'result-manifest.json?download=1' if (job['folder']/'result-manifest.json').is_file() else None,
                    quality_review=trace.get('quality_review'),
                    feature_summary={name:dict(dimension=len(values)) for name,values in trace['query_features'].items()})
            return result

    def file(self, job_id, kind, name):
        with self.lock:
            job=self.jobs.get(job_id)
            if not job or job['status']!='done': raise KeyError('No completed result')
            if kind=='artifacts':
                if name not in ARTIFACTS: raise KeyError('Artifact not allowed')
                return job['folder']/name
            if kind=='exports':
                names={Path(h['exported_video']).name for h in job['trace']['hits'] if h.get('exported_video')}
                if name not in names:raise KeyError('Export not part of this result')
                path=(job['folder']/'videos'/name).resolve()
                if not path.is_relative_to(job['folder']/'videos'):raise KeyError('Export outside scope')
                return path
            vid=name.rsplit('.',1)[0]
            hit=next((h for h in job['trace']['hits'] if h['video_id']==vid),None)
            if hit is None: raise KeyError('Video not part of this result')
            path=Path(hit['video_path'] if kind=='media' else hit['image_path']).resolve()
            allowed=Path(self.cfg['dataset_root'] if kind=='media' else self.cfg['artifacts']).resolve()
            if not path.is_relative_to(allowed): raise KeyError('Path outside media scope')
            return path

    def reset(self):
        with self.lock:
            if self.active: raise BlockingIOError('A search is already running')
            if self.session: self.session.close()
            self.session=None
            self.event('session_reset')

    def close(self):
        if self.session: self.session.close()


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, port, application):
        self.application=application
        super().__init__(('127.0.0.1',port),Handler)


class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    server_version='Nhom12Local/1.0'
    def log_message(self, format, *args):
        # Avoid logging query filenames or untrusted URL payloads.
        pass

    def setup(self):
        super().setup(); self.connection.settimeout(60)

    def _host_ok(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob: data:; media-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        super().end_headers()

    def _json(self, value, code=200):
        raw=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers()
        if self.command!='HEAD': self.wfile.write(raw)

    def _file(self, path, download=False):
        try:
            with path.open('rb') as stream:
                import os
                size=os.fstat(stream.fileno()).st_size
                start,end,status=0,size-1,200
                if self.command=='GET' and self.headers.get('Range'):
                    try: start,end=byte_range(self.headers['Range'],size);status=206
                    except ValueError:
                        self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
                self.send_response(status);self.send_header('Content-Type',TYPES.get(path.suffix,'application/octet-stream'))
                self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(max(0,end-start+1)))
                self.send_header('Cache-Control','no-store')
                if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                if download:self.send_header('Content-Disposition',f'attachment; filename="{path.name}"')
                self.end_headers()
                if self.command=='HEAD':return
                stream.seek(start);remaining=end-start+1
                while remaining>0:
                    chunk=stream.read(min(128*1024,remaining))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
                if path.suffix=='.mp4':self.server.application.event('media_served',status=status,start=start,end=end,bytes=end-start+1)
        except (BrokenPipeError,ConnectionResetError,TimeoutError):
            return
        except FileNotFoundError:
            self._json(dict(error='Không tìm thấy tệp kết quả.'),404)

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        if not self._host_ok():self._json(dict(error='Host không hợp lệ.'),403);return
        url=urlsplit(self.path);path=url.path
        if path in ASSETS:self._file(STATIC/ASSETS[path]);return
        if path=='/api/status':self._json(self.server.application.status());return
        match=re.fullmatch(r'/api/jobs/('+ID+r')',path)
        try:
            if match:self._json(self.server.application.job(match[1]));return
            match=re.fullmatch(r'/(artifacts|media|frames|exports)/('+ID+r')/([A-Za-z0-9_.-]+)',path)
            if match:
                file=self.server.application.file(match[2],match[1],match[3])
                self._file(file,parse_qs(url.query).get('download')==['1']);return
        except KeyError:
            pass
        self._json(dict(error='Không tìm thấy tài nguyên được phép.'),404)

    def do_POST(self):
        origin=self.headers.get('Origin')
        allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
        if not self._host_ok() or self.headers.get('X-Nhom12-Request')!='1' or (origin and origin not in allowed):
            self.close_connection=True;self._json(dict(error='Yêu cầu không hợp lệ.'),403);return
        try:
            length=int(self.headers.get('Content-Length','-1'))
            if length<0 or length>64*1024*1024:
                self.close_connection=True;self._json(dict(error='Ảnh vượt quá giới hạn 64 MB.'),413);return
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ContractError('Cannot decode query image')
            path=urlsplit(self.path).path
            if path=='/api/search':
                job_id=self.server.application.submit(raw)
                self._json(dict(job_id=job_id),202);return
            if path=='/api/reset':
                self.server.application.reset();self._json(dict(status='reset'));return
        except BlockingIOError:
            self._json(dict(error='Đang xử lý một ảnh. Vui lòng chờ kết quả hiện tại.'),409);return
        except ContractError as exc:
            self._json(dict(error=public_error(exc)),400);return
        except (ValueError,TimeoutError):
            self.close_connection=True;self._json(dict(error='Không đọc được yêu cầu.'),400);return
        self._json(dict(error='Không tìm thấy thao tác.'),404)


def serve(spec,cfg,port=8765):
    app=Application(spec,cfg);server=LocalServer(port,app)
    print(f'Local application: http://127.0.0.1:{server.server_port}',flush=True)
    print('Keep this process running. Ctrl+C stops the application and releases the model/source snapshot.',flush=True)
    try:server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:pass
    finally:server.server_close();app.close()
