"""Human review is independent of feature extraction and keyed by source SHA256."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from .core import PROJECT, ContractError, file_hash

FLAGS=('single_scene','not_duplicate','no_large_logo')


def registry_path(cfg):
    path=Path(cfg.get('quality_registry') or PROJECT/'data/reviews/registry.json')
    return path if path.is_absolute() else PROJECT/path


def summary(cfg,snapshot,fallback='pending'):
    path=registry_path(cfg)
    if not path.is_file():
        return dict(status=fallback,reviewed=0,total=len(snapshot),issues=0,stale=0,registry_sha256=None)
    raw=path.read_bytes();data=json.loads(raw);records=data['records'];approved=issues=stale=0
    for source in snapshot:
        r=records.get(source['video_id'],{})
        if r and r.get('sha256')!=source['sha256']:stale+=1;continue
        if any(r.get(f) is False for f in FLAGS):issues+=1
        elif all(r.get(f) is True for f in FLAGS) and r.get('reviewer','').strip() and r.get('reviewed_at'):
            approved+=1
    status='issues' if issues else 'reviewed' if approved==len(snapshot) else 'pending'
    import hashlib
    return dict(status=status,reviewed=approved,total=len(snapshot),issues=issues,stale=stale,registry_sha256=hashlib.sha256(raw).hexdigest())


def initialize(cfg,snapshot):
    folder=registry_path(cfg).parent;folder.mkdir(parents=True,exist_ok=True)
    path=registry_path(cfg)
    if path.exists():return summary(cfg,snapshot)
    records={r['video_id']:dict(sha256=r['sha256'],**{f:None for f in FLAGS},reviewer='',reviewed_at='',notes='') for r in snapshot}
    path.write_text(json.dumps(dict(version='sha256-human-review-v1',records=records),ensure_ascii=False,indent=2),encoding='utf-8')
    with (folder/'review_template.csv').open('x',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['video_id','sha256',*FLAGS,'reviewer','reviewed_at','notes'])
        writer.writeheader()
        writer.writerows(dict(video_id=vid,**r) for vid,r in records.items())
    return summary(cfg,snapshot)


def prepare_page(cfg,snapshot,frames):
    import html
    initialize(cfg,snapshot)
    path=registry_path(cfg);folder=path.parent
    records=json.loads(path.read_text(encoding='utf-8'))['records'];by_video={r['video_id']:[] for r in snapshot}
    for f in frames:
        if f['index'] in (0,5,10,15):by_video[f['video_id']].append(f)
    body=['<h1>Rà soát nội dung theo SHA256</h1><p>Xem video đầy đủ và các khung minh họa. '
          'Khung minh họa không chứng minh video chỉ có một cảnh. Không chắc thì để Chưa xác nhận.</p>',
          '<label>Người rà soát: <input id="reviewer" placeholder="Tên hoặc mã thành viên"></label> '
          '<button id="save">Tải phiếu CSV đã điền</button><p>Tiến trình được lưu trên trình duyệt này; nhập CSV vào hệ thống để xác nhận.</p>']
    data=[]
    for source in snapshot:
        vid=source['video_id'];r=records.get(vid,{})
        valid=r.get('sha256')==source['sha256']
        row=dict(video_id=vid,sha256=source['sha256'],**{f:r.get(f) if valid else None for f in FLAGS},
                 notes=r.get('notes','') if valid else '',reviewer=r.get('reviewer','') if valid else '',reviewed_at=r.get('reviewed_at','') if valid else '')
        data.append(row)
        uri=(Path(cfg['dataset_root'])/source['relative_path']).resolve().as_uri()
        body.append(f'<article data-id="{vid}"><h2>{vid}</h2><small>SHA256: {source["sha256"]}</small><p>'+
                    f'<video controls preload="none" src="{html.escape(uri,quote=True)}"></video></p>')
        for fr in sorted(by_video[vid],key=lambda f:f['index']):
            body.append(f'<img alt="Khung {fr["index"]}" loading="lazy" src="{html.escape(Path(fr["image_path"]).resolve().as_uri(),quote=True)}">')
        for key,title in [('single_scene','Chỉ một cảnh liên tục'),('not_duplicate','Không trùng hoặc gần trùng cảnh với video khác'),('no_large_logo','Không có logo/chữ lớn nổi bật')]:
            body.append(f'<label>{title}: <select data-field="{key}"><option value="">Chưa xác nhận</option><option value="true">Đạt</option><option value="false">Có vấn đề</option></select></label> ')
        body.append('<p>Ghi chú / ID video bị trùng: <input data-field="notes"></p></article>')
    from .core import digest
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    script="""const initial=PAYLOAD;const key=KEY;let records=JSON.parse(localStorage.getItem(key)||'null')||initial;
const byId=Object.fromEntries(records.map(r=>[r.video_id,r]));
document.querySelectorAll('article').forEach(card=>{let r=byId[card.dataset.id];card.querySelectorAll('[data-field]').forEach(el=>{el.value=r[el.dataset.field]===null?'':String(r[el.dataset.field]);el.onchange=()=>{r[el.dataset.field]=el.dataset.field==='notes'?el.value:(el.value===''?null:el.value==='true');r.reviewed_at=new Date().toISOString();r.reviewer=document.querySelector('#reviewer').value.trim();localStorage.setItem(key,JSON.stringify(records));};});});
document.querySelector('#save').onclick=()=>{let who=document.querySelector('#reviewer').value.trim();if(!who){alert('Điền tên hoặc mã người rà soát');return;}const cols=['video_id','sha256','single_scene','not_duplicate','no_large_logo','reviewer','reviewed_at','notes'];
const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';let rows=[cols.join(',')];for(const r of records){let touched=['single_scene','not_duplicate','no_large_logo'].some(k=>r[k]!==null);if(touched&&!r.reviewer)r.reviewer=who;rows.push(cols.map(k=>quote(r[k])).join(','));}
let a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\\ufeff'+rows.join('\\r\\n')],{type:'text/csv;charset=utf-8'}));a.download='review_completed.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};"""
    script=script.replace('PAYLOAD',payload).replace('KEY',json.dumps('nh12-review-'+digest(snapshot)))
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Rà soát nội dung video</title><style>body{font:16px/1.5 Segoe UI;max-width:1150px;margin:auto;padding:24px}article{border-top:1px solid #ccc;padding:20px 0}video{width:70%;max-height:350px}img{width:23%;margin:0.5%}label{display:inline-block;margin:8px}small{overflow-wrap:anywhere}input{min-width:240px;padding:6px}</style>'+''.join(body)+'<script>'+script+'</script></html>'
    (folder/'review.html').write_text(page,encoding='utf-8')
    return dict(page=str(folder/'review.html'),template=str(folder/'review_template.csv'),**summary(cfg,snapshot))


def collect_legacy(cfg,snapshot,backup_root):
    import hashlib
    root=Path(backup_root);index={r['video_id']:r for r in snapshot};out=[]
    for journal in sorted(root.rglob('nhat_ky_thay_the.csv')):
        with journal.open(encoding='utf-8-sig') as stream:journal_rows=list(csv.DictReader(stream))
        for r in journal_rows:
            vid=r.get('video') or r.get('vid')
            if vid not in index or not r.get('md5_moi'):continue
            source=index[vid];h=hashlib.md5()
            with (Path(cfg['dataset_root'])/source['relative_path']).open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            out.append(dict(video_id=vid,current_sha256=source['sha256'],journal=str(journal),
                     journal_sha256=file_hash(journal),old_recorded_new_md5=r['md5_moi'],current_md5=h.hexdigest(),
                     matches_current_bytes=h.hexdigest().lower()==r['md5_moi'].lower(),
                     historical_check=r.get('kiem_tra',''),notes=r.get('ly_do',''),
                     authority='historical replacement evidence only; not full single-scene/duplicate/logo review'))
    target=registry_path(cfg).parent/'legacy_evidence.csv';target.parent.mkdir(exist_ok=True,parents=True)
    if out:
        with target.open('w',encoding='utf-8-sig',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    return dict(records=len(out),matching=sum(r['matches_current_bytes'] for r in out),output=str(target),human_flags_changed=False)


def execute(args,spec,cfg):
    from .storage_mysql.service import load_index
    frames,paths,model,label,context,report=load_index(spec,cfg,metadata=True)
    snapshot=json.loads(context['build']['snapshot_json'])
    if args.action=='init':return initialize(cfg,snapshot)
    if args.action=='prepare':return prepare_page(cfg,snapshot,frames)
    if args.action=='status':return summary(cfg,snapshot)
    if args.action=='legacy':return collect_legacy(cfg,snapshot,args.backup_root)
    if not args.csv:raise ContractError('reviews import needs --csv')
    return import_reviews(cfg,snapshot,args.csv)


def import_reviews(cfg,snapshot,csv_path):
    path=registry_path(cfg);expected={r['video_id']:r['sha256'] for r in snapshot}
    with Path(csv_path).open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    if len({r['video_id'] for r in rows})!=len(rows):raise ContractError('Duplicate IDs in review CSV')
    existing=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(version='sha256-human-review-v1',records={})
    for raw in rows:
        vid=raw['video_id']
        if vid not in expected or raw['sha256']!=expected[vid]:raise ContractError('Review SHA256 does not match current video')
        r={k:raw.get(k,'').strip() for k in ('reviewer','reviewed_at','notes')};r['sha256']=raw['sha256']
        for f in FLAGS:
            v=raw.get(f,'').strip().lower()
            if v not in ('','true','false'):raise ContractError('Review flags must be blank, true or false')
            r[f]=None if not v else v=='true'
        # A full template contains untouched rows for the other team members.
        # Import only completed/partial reviews, so their work is not cleared.
        if all(r[f] is None for f in FLAGS):continue
        if any(r[f] is not None for f in FLAGS):
            if not r['reviewer'] or not r['reviewed_at']:raise ContractError('Completed review flags require reviewer and ISO date/time')
            try:datetime.fromisoformat(r['reviewed_at'].replace('Z','+00:00'))
            except ValueError:raise ContractError('Review date must be ISO format') from None
        existing['records'][vid]=r
    path.parent.mkdir(parents=True,exist_ok=True)
    history=path.parent/'history';history.mkdir(exist_ok=True)
    if path.exists():
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        (history/(stamp+'.json')).write_bytes(path.read_bytes())
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(path)
    return summary(cfg,snapshot)
