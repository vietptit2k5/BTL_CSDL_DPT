"""ND4b and ND5: portable local HTML evidence. No hosted website or server."""
import html
import json
from pathlib import Path

def render(output,trace):
    esc=lambda x:html.escape(str(x),quote=True)
    cards=[]
    for i,hit in enumerate(trace['hits'],1):
        uri=hit.get('exported_video') or Path(hit['video_path']).resolve().as_uri()
        frame=Path(hit['image_path']).resolve().as_uri()
        cards.append(f'<article><h2>{i}. {esc(hit["video_id"])}</h2><p>Điểm {hit["score"]:.4f} · khung {hit["frame_index"]} · {hit["time_sec"]:.3f}s</p>'
          f'<video controls preload="metadata" src="{esc(uri)}#t={hit["time_sec"]}"></video>'
          f'<img alt="Khung dùng tính điểm" src="{esc(frame)}"><pre>{esc(json.dumps(hit["contributions"],indent=2))}</pre></article>')
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><title>Nhóm 12 tìm kiếm video</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:16px}article{border-top:1px solid #bbb;padding:20px 0}img,video{width:45%;max-height:320px;object-fit:contain}pre{white-space:pre-wrap}</style>'
    page+='<h1>Ảnh truy vấn và 5 video tương đồng</h1><p>Điểm xếp hạng tương đối; không phải xác suất đúng.</p><img alt="Ảnh truy vấn" src="input.png"><img alt="Sau tiền xử lý" src="preprocessed.png">'+''.join(cards)
    page+='<p><a href="trace.json">Vector và phép tính trung gian</a></p>'
    if all(h.get('exported_video') for h in trace['hits']):
        page+='<p><a href="results.zip">Tải 5 file MP4 và manifest</a> · <a href="result-manifest.json">SHA256 các file kết quả</a></p>'
    page+='</html>'
    if trace.get('trace_version')=='nd4-v2':
        timing=trace['timings_seconds']
        details=f'<section><h2>Dữ liệu trung gian</h2><p>Crop: {esc(trace["preprocess"]["crop_box"])} trên ảnh decode {esc(trace["preprocess"]["decoded_size"])}. Điểm tương đồng không phải xác suất.</p><img alt="Histogram HSV và LBP" src="histograms.svg" style="width:100%;max-height:none"><p>Encode: {timing["encode"]:.3f}s · so khớp: {timing["search"]:.3f}s. Chi tiết thời gian từng bước nằm trong trace.</p><p><a href="query-features.npz">Vector truy vấn NPZ</a> · <a href="trace.json">Trace có vector khung khớp để tái tính điểm</a></p></section>'
        page=page.replace('</html>',details+'</html>')
    (Path(output)/'demo.html').write_text(page,encoding='utf-8')
