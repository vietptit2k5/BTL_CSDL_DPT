import html
import time
from pathlib import Path
from uuid import uuid4
import numpy as np
from ..core import ContractError, file_hash
from ..video_search import FEATURES, frame_similarities, pair_score, search_video
from .data import guard_live, load_matrices, load_snapshot
from .files import read_csv, read_json, seal, verify, write_csv, write_json

NAMES={'clip':'CLIP — nội dung cảnh','hsv':'HSV — màu sắc','lbp':'LBP — kết cấu','motion':'Optical Flow — chuyển động'}


def label_table(run):
    for step in ('b0','b0_diagnostic'):
        folder=Path(run)/step
        if (folder/'files.json').exists():
            verify(folder)
            return {r['video_id']:r for r in read_csv(folder/'nhan_nd1.csv')},read_json(folder/'result.json')['status']
    return {},'not_measured'


def export_query(run,spec,cfg,video_id,baseline=False,live=True):
    started=time.perf_counter()
    info,arrays,videos,frames=load_snapshot(run);matrices=load_matrices(run)
    from .stages import require_b3
    require_b3(run)
    if live:guard_live(run,spec,cfg)
    if baseline:
        weights=dict(clip=1.0,hsv=0.0,lbp=0.0,motion=0.0);mode='CLIP baseline — không phải hệ số đã chọn'
    else:
        from .stages import locked_weights
        lock=locked_weights(run);weights=lock['weights'];mode='Hệ số video đã khóa trên nửa phát triển'
    hits=search_video(video_id,info['ids'],matrices,weights)
    labels,status=label_table(run)
    if status!='passed':mode+='; nhãn ND1 chưa được chứng nhận'
    folder=run/'b4'/f'{video_id}-{uuid4().hex[:10]}';folder.mkdir(parents=True)
    from ..result_export import export_videos
    for hit in hits:
        hit['video_path']=str(Path(cfg['dataset_root'])/videos[hit['video_id']]['relative_path'])
    export_started=time.perf_counter()
    export_videos(folder,hits,{v:r['sha256'] for v,r in videos.items()})
    export_seconds=time.perf_counter()-export_started
    ids=info['ids'];qi=ids.index(video_id)
    by_frame={(f['video_id'],f['index']):f for f in frames}
    correspondences=[]
    for hit in hits:
        j=ids.index(hit['video_id']);hit['labels']={f:labels.get(hit['video_id'],{}).get(f,'chưa có') for f in ('d1','d2','d5')}
        hit['examples']={}
        for f in FEATURES[:-1]:
            s=frame_similarities(f,arrays[f][qi],arrays[f][j])
            a,b=np.unravel_index(np.argmax(s),s.shape)
            hit['examples'][f]=dict(query_frame=int(a),result_frame=int(b),
                                   query_image=by_frame[(video_id,int(a))]['image_path'],
                                   result_image=by_frame[(hit['video_id'],int(b))]['image_path'])
            for direction,matrix in [('query_to_result',s),('result_to_query',s.T)]:
                for k,row in enumerate(matrix):
                    best=int(np.argmax(row));correspondences.append(dict(result_video=hit['video_id'],feature=f,
                            direction=direction,frame=k,nearest_frame=best,similarity=float(row[best])))
    write_csv(folder/'frame_matches.csv',correspondences)
    ranking=search_video(video_id,ids,matrices,weights)
    write_csv(folder/'top5.csv',[dict(rank=i+1,video_id=h['video_id'],score=h['score'],
                 **{f's_{f}':h['similarities'][f] for f in FEATURES},**{f'w_{f}':weights[f] for f in FEATURES},
                 **{f'contribution_{f}':h['contributions'][f] for f in FEATURES},**hits[i]['labels']) for i,h in enumerate(ranking)])
    # All candidate scores remain available for explaining exactly why these five won.
    qscore=sum(weights[f]*matrices[f][qi] for f in FEATURES)
    order=sorted([i for i in range(len(ids)) if i!=qi],key=lambda i:(-qscore[i],ids[i]))
    write_csv(folder/'all_candidates.csv',[dict(rank=r+1,video_id=ids[i],score=float(qscore[i]),
                  **{f's_{f}':float(matrices[f][qi,i]) for f in FEATURES}) for r,i in enumerate(order)])
    trace=dict(video_id=video_id,mode=mode,weights=weights,label_status=status,hits=hits,
               snapshot_hash=verify(run/'snapshot'),matrix_hash=verify(run/'b2'),
               elapsed_seconds=time.perf_counter()-started,
               export_seconds=export_seconds,
               score_meaning='relative ranking score, not probability; frame examples are individual-descriptor illustrations')
    write_json(folder/'trace.json',trace)
    # A static contact sheet is portable evidence even when the HTML is not open.
    from PIL import Image, ImageDraw
    tile_w,tile_h=180,135
    sheet=Image.new('RGB',(tile_w*6,tile_h*5+30),'white');draw=ImageDraw.Draw(sheet)
    draw.text((8,7),f'{video_id} -> 5 other videos; per-descriptor best pairs (illustrations only)',fill='black')
    for row,hit in enumerate(hits):
        for col,f in enumerate(FEATURES[:-1]):
            for side,key in enumerate(('query_image','result_image')):
                with Image.open(hit['examples'][f][key]) as original:
                    picture=original.convert('RGB');picture.thumbnail((tile_w-6,tile_h-27))
                x=(col*2+side)*tile_w;y=row*tile_h+30
                sheet.paste(picture,(x+3,y+24));draw.text((x+3,y+4),f'{f} {video_id if side==0 else hit["video_id"]}',fill='black')
    sheet.save(folder/'bang_khung.jpg',quality=90)
    def esc(value):return html.escape(str(value),quote=True)
    def media(vid):return (Path(cfg['dataset_root'])/videos[vid]['relative_path']).resolve().as_uri()
    body=[f'<h1>Tìm video tương đồng ND3: {esc(video_id)}</h1><p>{esc(mode)}</p>',
          '<p>Điểm dùng xếp hạng, không phải xác suất. Mỗi đặc trưng có phép ghép khung riêng; không so thứ tự thời gian.</p>',
          f'<video controls preload="metadata" src="{esc(media(video_id))}"></video>',
          '<p><a href="bang_khung.jpg">Ảnh ghép</a> · <a href="top5.csv">Top 5 và điểm</a> · <a href="all_candidates.csv">Tất cả ứng viên</a> · '
          '<a href="frame_matches.csv">Ghép khung hai chiều</a> · <a href="trace.json">Trace</a></p>']
    body.append('<p><a href="results.zip" download>Tải đủ 5 file MP4 (ZIP)</a> · <a href="result-manifest.json">SHA256 các file</a></p>')
    for rank,hit in enumerate(hits,1):
        body.extend([f'<article><h2>#{rank} {esc(hit["video_id"])} — {hit["score"]:.6f}</h2>',
                     f'<p>Nhãn ND1: {esc(hit["labels"])}</p><video controls preload="metadata" src="{esc(hit["exported_video"])}"></video>',
                     f'<p><a href="{esc(hit["exported_video"])}" download>Tải file MP4</a></p>',
                     '<table><tr><th>Đặc trưng</th><th>Tương đồng</th><th>Hệ số</th><th>Đóng góp</th></tr>'])
        for f in FEATURES:
            body.append(f'<tr><td>{esc(NAMES[f])}</td><td>{hit["similarities"][f]:.6f}</td><td>{weights[f]:.2f}</td><td>{hit["contributions"][f]:.6f}</td></tr>')
        body.append('</table><p>Cặp khung có điểm cao nhất của từng đặc trưng, chỉ để minh họa. Điểm video dùng trung bình ghép hai chiều.</p>')
        for f,e in hit['examples'].items():
            body.append(f'<p>{f.upper()}: khung truy vấn {e["query_frame"]} / khung kết quả {e["result_frame"]}</p>'+
                        ''.join(f'<img alt="{esc(f)} {esc(k)}" src="{esc(Path(e[k]).resolve().as_uri())}">' for k in ('query_image','result_image')))
        body.append('</article>')
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Tìm video tương đồng ND3</title><style>body{font:16px/1.6 Segoe UI,sans-serif;max-width:1000px;margin:32px auto;padding:16px;background:#f5f7f3;color:#203b2e}video{width:100%;max-height:400px}img{width:44%;margin:1%}article{background:white;padding:22px;margin:28px 0;border:1px solid #ccd8ce}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:8px;text-align:left}</style>'+''.join(body)+'</html>'
    (folder/'ket_qua.html').write_text(page,encoding='utf-8');seal(folder)
    if live:guard_live(run,spec,cfg)
    return dict(page=str(folder/'ket_qua.html'),trace=str(folder/'trace.json'),mode=mode,top5=ranking)


def replay(run,trace_path):
    trace_path=Path(trace_path).resolve()
    if not trace_path.is_relative_to(run.resolve()):raise ContractError('Trace must belong to this run')
    verify(trace_path.parent);trace=read_json(trace_path)
    info,arrays,_,_=load_snapshot(run);matrices=load_matrices(run)
    if trace['snapshot_hash']!=verify(run/'snapshot') or trace['matrix_hash']!=verify(run/'b2'):
        raise ContractError('Trace snapshot differs')
    hits=search_video(trace['video_id'],info['ids'],matrices,trace['weights'])
    if [h['video_id'] for h in hits]!=[h['video_id'] for h in trace['hits']]:raise ContractError('Top5 replay differs')
    errors=[];qi=info['ids'].index(trace['video_id'])
    for old,new in zip(trace['hits'],hits,strict=True):
        if abs(old['score']-new['score'])>1e-10:raise ContractError('Recorded score differs')
        computed=pair_score(arrays,qi,info['ids'].index(old['video_id']))
        errors.extend(abs(computed[f]-old['similarities'][f]) for f in FEATURES)
    if max(errors)>1e-6:raise ContractError('Vector replay differs from matrices')
    return dict(status='passed',top5=[h['video_id'] for h in hits],max_vector_score_error=max(errors),
                scope='offline sealed snapshot and vectors; no live MySQL or relevance assertion')
