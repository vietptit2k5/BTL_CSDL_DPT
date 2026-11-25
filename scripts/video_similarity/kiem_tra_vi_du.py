"""Verify frozen B8 outputs and create a local entry page from actual results."""
import html
import argparse
import sys
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import file_hash
from nhom12.video_workflow.files import read_csv,read_json,verify,write_json
from nhom12.video_workflow.presentation import replay

parser=argparse.ArgumentParser(description='Kiểm tra trace B8 và tạo trang tổng hợp từ kết quả đã lưu')
parser.add_argument('--run',type=Path,default=ROOT/'var/video_similarity/run01')
run=parser.parse_args().run.resolve()
verify(run/'b8');examples=read_json(run/'b8/result.json')['examples']
class MediaParser(HTMLParser):
    def __init__(self):super().__init__();self.videos=[]
    def handle_starttag(self,tag,attrs):
        if tag=='video':self.videos.append(dict(attrs).get('src'))
results=[]
for item in examples:
    path=Path(item['page']);trace=read_json(item['trace'])
    parser=MediaParser();parser.feed(path.read_text(encoding='utf-8'))
    assert len(parser.videos)==6 and len(set(parser.videos))==6
    assert trace['label_status']=='passed'
    assert len({h['video_id'] for h in trace['hits']})==5
    assert trace['video_id'] not in {h['video_id'] for h in trace['hits']}
    assert [h['score'] for h in trace['hits']]==sorted((h['score'] for h in trace['hits']),reverse=True)
    assert all(abs(sum(h['contributions'].values())-h['score'])<1e-12 for h in trace['hits'])
    results.append(dict(kind=item['kind'],video_id=trace['video_id'],page=str(path),
                        replay=replay(run,Path(item['trace'])),html_video_elements=len(parser.videos),
                        contact_sheet=str(path.with_name('bang_khung.jpg'))))
if len(examples)==3:assert len(read_csv(run/'b8/flow_change.csv'))==10
chosen=read_json(run/'b6/result.json')['results']['chosen']['metrics']
snapshot=read_json(run/'snapshot/info.json')
split=read_json(run/'b1/result.json')
weights=read_json(run/'trong_so_video.json')['weights']
weight_text=' · '.join(f'{name.upper()} {weights[name]:.2f}'.replace('.',',') for name in ('clip','hsv','lbp','motion'))
labels={'good':'Ca có điểm tổng hợp cao nhất','class_error_or_lowest_class_precision':'Ca có P@5 lớp thấp nhất',
        'largest_observed_motion_D5_gain':'Ca tăng D5 nhiều nhất khi có Flow'}
def esc(x):return html.escape(str(x),quote=True)
body=['<h1>Cơ chế tìm video tương đồng ND3</h1>',
      f'<p>Lần chạy {esc(run.name)}: {len(snapshot["ids"])} video; nhãn ND1 tính lại từ code và ngưỡng gốc; đặc trưng ND2 đọc từ MySQL.</p>',
      f'<p><strong>Hệ số khóa:</strong> {esc(weight_text)}. Chọn trên {split["development"]} truy vấn phát triển, kiểm tra trên {split["test"]} truy vấn giữ riêng.</p>',
      '<p>Điểm tương đồng dùng xếp hạng, không phải xác suất. D1/D2/D5 là các nhãn tự động của ND1; không dùng nhãn để lọc ứng viên.</p>',
      '<h2>Tài liệu và cách tự chạy</h2><ul>',
      '<li><a href="../../../scripts/video_similarity/README.md">Lệnh chạy B0–B8 không cần AI</a></li>',
      '<li><a href="../../../docs/ND3_CO_CHE_TIM_VIDEO_TUONG_DONG.md">Thiết kế và mapping ND1–ND2</a></li>',
      '<li><a href="explanations/SEA001.txt">Giải thích cách tính nhãn SEA001</a></li></ul>',
      '<h2>Kết quả kiểm tra giữ riêng</h2><table><tr><th>Cùng lớp</th><th>D1</th><th>D2</th><th>D5</th><th>Tổng hợp</th></tr>',
      '<tr>'+''.join(f'<td>{chosen[k]["mean"]:.4f}</td>' for k in ('class','d1','d2','d5','objective'))+'</tr></table>',
      '<p><a href="b6/bang_dong_gop.csv">9 cấu hình và mức ngẫu nhiên</a> · <a href="b6/per_class.csv">Theo lớp</a> · '
      '<a href="b6/result.json">Sai số và chênh lệch ghép cặp</a></p>',
      '<h2>Các bước và dữ liệu trung gian</h2><ul>']
for title,target in [('B0 Nhãn ND1 và đối chiếu','b0/nhan_nd1.csv'),('B0 Danh sách đối chiếu','b0/baseline_check.json'),
                     ('B1 Mục tiêu','b1/muc_tieu_video.json'),('B1 Chia truy vấn','b1/split.csv'),
                     ('B2 Thứ tự video trong ma trận','b2/video_order.csv'),('B3 Tính từng cặp độc lập','b3/scalar_pairs.csv'),
                     ('B5 Toàn bộ lưới hệ số','b5/bang_luoi.csv'),('B5 Hệ số khóa','trong_so_video.json'),
                     ('B6 Chi tiết từng truy vấn','b6/per_query.csv'),('B7 Báo cáo','b7/ket_qua.md'),
                     ('B8 Thứ hạng có và không có Flow','b8/flow_change.csv'),('Log các lệnh','logs/'),
                     ('Kiểm tra bảo toàn nguồn','verification/preservation.json')]:
    body.append(f'<li><a href="{esc(target)}">{esc(title)}</a></li>')
body.append('</ul><h2>Ví dụ thực tế</h2>')
for item in results:
    path=Path(item['page']).relative_to(run).as_posix();sheet=Path(item['contact_sheet']).relative_to(run).as_posix()
    body.append(f'<article><h3>{esc(labels[item["kind"]])}: {esc(item["video_id"])}</h3><a href="{esc(path)}">Mở trang phát 5 video và điểm từng đặc trưng</a><p><a href="{esc(sheet)}"><img alt="Các cặp khung minh họa" src="{esc(sheet)}"></a></p></article>')
body.append('<p>Trace của các ví dụ được tính lại từ vector và ma trận. Kiểm thử mã nguồn được chạy riêng theo README. Chưa xác nhận phát media trực tiếp trên trình duyệt trong phiên kiểm tra.</p>')
page='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Cơ chế tìm video tương đồng ND3</title><style>body{font:16px/1.65 Segoe UI,sans-serif;max-width:1050px;margin:32px auto;padding:20px;color:#203c2c;background:#f4f7f2}article{padding:18px;background:white;margin:20px 0;border:1px solid #cdd9cc}img{max-width:100%;height:auto}a{color:#175b37}td,th{border:1px solid #aebdae;padding:10px}table{border-collapse:collapse}li{margin:6px 0}</style>'+''.join(body)+'</html>'
(run/'index.html').write_text(page,encoding='utf-8')
out=run/'verification';out.mkdir(exist_ok=True)
write_json(out/'final_examples.json',dict(status='passed',examples=results,entry_page=str(run/'index.html'),entry_sha256=file_hash(run/'index.html'),
          browser_playback_verified=False))
print('\n'.join(f'{r["kind"]}: {r["video_id"]}, replay PASS' for r in results))
print(run/'index.html')
