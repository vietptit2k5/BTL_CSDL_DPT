"""Bước 5: đánh giá MỘT LẦN trên tập test ảnh Internet, sau khi trọng số đã khoá (trong_so_chot.json).

Đầu vào: thư mục ảnh + file nhãn CSV (UTF-8) với các cột:
  file   – tên file ảnh trong thư mục
  lop    – SEA / WAT / FOR / MOU / RIV / FLO
  nguon  – đường dẫn web hoặc ghi chú nguồn ảnh
  nhom   – (không bắt buộc) mã nhóm cho các ảnh cùng một địa điểm/cảnh; ảnh cùng nhóm được tính như một đơn vị khi tính SE
Liên quan = video cùng lớp với ảnh. Ảnh Internet không thuộc video nào nên không có R@1.

So sánh: hệ số đã chốt, cấu hình cũ 0.9/0.1/0, chỉ CLIP. KHÔNG chỉnh trọng số ở bước này.
Đầu ra (var/weights/test/): ket_qua_test.md, bang_ket_qua.csv, top5_tung_anh.csv, anh_kem_nhat.jpg
"""
import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import common_w as W

ap = argparse.ArgumentParser()
ap.add_argument('--anh', required=True, help='thư mục ảnh test')
ap.add_argument('--nhan', required=True, help='file CSV nhãn')
ap.add_argument('--trong-so', default=str(W.OUT / 'trong_so_chot.json'))
ap.add_argument('--out', default=str(W.OUT / 'test'))
a = ap.parse_args()
lock = Path(a.trong_so)
if not lock.exists():
    raise SystemExit('Chưa có trọng số đã khoá – chạy w03_chon_he_so.py trước. Tập test chỉ được mở sau khi đã khoá.')
chosen = json.loads(lock.read_text(encoding='utf-8'))
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader(open(a.nhan, encoding='utf-8-sig')))
for r in rows:
    if r['lop'] not in W.CLASSES or not (Path(a.anh) / r['file']).is_file():
        raise SystemExit(f'Dòng nhãn không hợp lệ hoặc thiếu ảnh: {r}')
qcls = np.array([r['lop'] for r in rows])
group = np.array([r.get('nhom') or r['file'] for r in rows])

spec, cfg = W.settings()
db = W.load_database(spec, cfg); vids, frames = db['vids'], db['frames']; vcls = db['cls']; NV = len(vids)
enc = W.encoder(spec, cfg)
enc.extract([W.prepare_query(Path(a.anh) / rows[0]['file'], spec)])          # làm nóng GPU, không tính giờ
feats, t_enc = [], []
for r in rows:
    t = time.perf_counter(); feats.append(enc.extract([W.prepare_query(Path(a.anh) / r['file'], spec)])[0])
    t_enc.append(time.perf_counter() - t)
Q = {f: np.stack([x[f] for x in feats]) for f in W.FEATS}
S = W.similarities(Q, db['X'])
CONFIGS = {'Hệ số đã chốt': chosen['trong_so'], 'Cấu hình cũ 0.9/0.1/0': dict(clip=0.9, hsv=0.1, lbp=0.0),
           'Chỉ CLIP': dict(clip=1.0, hsv=0.0, lbp=0.0)}


def p_at_5(w):
    V = W.video_scores(S, w, NV); top = W.top_k(V)
    return (vcls[top] == qcls[:, None]).mean(1), top, V


def macro_grouped(x):
    """TB theo lớp; SE tính trên đơn vị 'nhóm' (ảnh cùng địa điểm gộp thành một)."""
    per, var = {}, 0.0
    for c in W.CLASSES:
        m = qcls == c
        if not m.any(): continue
        units = np.array([x[m & (group == g)].mean() for g in np.unique(group[m])])
        per[c] = float(units.mean())
        if len(units) > 1: var += units.var(ddof=1) / len(units)
    return float(np.mean(list(per.values()))), float(np.sqrt(var) / len(per)), per


res = {}
for name, w in CONFIGS.items():
    p5, top, V = p_at_5(w); m, se, per = macro_grouped(p5); res[name] = dict(w=w, p5=p5, top=top, V=V, m=m, se=se, per=per)
base = res['Cấu hình cũ 0.9/0.1/0']['p5']
diff = res['Hệ số đã chốt']['p5'] - base
dm, dse, _ = macro_grouped(diff)
t0 = time.perf_counter()
for i in range(len(rows)):                      # tính độ tương đồng với 8.976 khung + gộp điểm, cho từng ảnh
    W.video_scores(W.similarities({f: Q[f][i:i+1] for f in W.FEATS}, db['X']), chosen['trong_so'], NV)
t_search = (time.perf_counter() - t0) / len(rows)

fmt = lambda w: f'{w["clip"]}/{w["hsv"]}/{w["lbp"]}'
table = [[k, fmt(r['w']), f'{r["m"]:.4f}', f'{r["se"]:.4f}'] + [f'{r["per"].get(c, float("nan")):.3f}' for c in W.CLASSES] for k, r in res.items()]
W.write_csv(out / 'bang_ket_qua.csv', table, ['cau_hinh', 'clip/hsv/lbp', 'P@5_theo_lop', 'SE'] + [f'P@5_{c}' for c in W.CLASSES])
r = res['Hệ số đã chốt']; detail = []
for i, row in enumerate(rows):
    for k, j in enumerate(r['top'][i]):
        T = sum(r['w'][f] * S[f][i, j * W.K:(j + 1) * W.K] for f in W.FEATS); b = int(np.argmax(T)); fi = j * W.K + b
        detail.append([row['file'], row['lop'], k + 1, vids[j], vids[j][:3], f'{r["V"][i, j]:.4f}',
                       f'{S["clip"][i, fi]:.4f}', f'{S["hsv"][i, fi]:.4f}', f'{S["lbp"][i, fi]:.4f}', b, frames[fi]['image_path']])
W.write_csv(out / 'top5_tung_anh.csv', detail, ['anh', 'lop', 'hang', 'video', 'lop_video', 'diem', 's_clip', 's_hsv', 's_lbp', 'khung', 'anh_khung'])

# ảnh kém nhất: ghép ảnh truy vấn + 5 khung bằng chứng để phân tích lỗi
worst = np.argsort(r['p5'], kind='stable')[:10]
tile = 150; sheet = Image.new('RGB', (tile * 6, tile * len(worst) + 4), 'white'); dr = ImageDraw.Draw(sheet)
for n, i in enumerate(worst):
    q = Image.open(Path(a.anh) / rows[i]['file']).convert('RGB'); q.thumbnail((tile - 4, tile - 22))
    sheet.paste(q, (2, n * tile + 20)); dr.text((2, n * tile + 4), f'{rows[i]["lop"]} P@5={r["p5"][i]:.1f}', fill='black')
    for k in range(5):
        d = detail[i * 5 + k]; im = Image.open(d[10]).convert('RGB'); im.thumbnail((tile - 4, tile - 22))
        sheet.paste(im, ((k + 1) * tile + 2, n * tile + 20))
        dr.text(((k + 1) * tile + 2, n * tile + 4), f'#{k+1} {d[3]} {d[5]}', fill='black' if d[4] == rows[i]['lop'] else 'red')
sheet.save(out / 'anh_kem_nhat.jpg', quality=90)

md = ['# Đánh giá trên tập test ảnh Internet', '',
      f'{len(rows)} ảnh, {len(np.unique(group))} nhóm địa điểm; liên quan = cùng lớp. Trọng số lấy từ `{lock.name}` '
      f'(khoá lúc {chosen.get("thoi_diem")}, chế độ {chosen.get("che_do")}); không chỉnh trọng số ở bước này.', '',
      '| Cấu hình | clip/hsv/lbp | P@5 (TB lớp) | SE | ' + ' | '.join(W.CLASSES) + ' |', '|---|---|---|---|' + '---|' * 6]
md += [f'| {" | ".join(t)} |' for t in table]
md += ['', f'Chênh lệch "đã chốt − cấu hình cũ": {dm:+.4f} (SE {dse:.4f}; khoảng ±2SE: [{dm - 2*dse:+.4f}, {dm + 2*dse:+.4f}]). '
       + ('Khoảng này chứa 0 → chưa đủ bằng chứng khác biệt trên tập test.' if dm - 2 * dse <= 0 <= dm + 2 * dse else 'Khoảng này không chứa 0.'), '',
       f'Thời gian: mã hoá ảnh trung vị {1000*np.median(t_enc):.0f} ms; so khớp 8.976 khung {1000*t_search:.1f} ms/ảnh '
       f'(thiết bị {cfg["device"]}, chưa tính các bước kiểm tra của phiên).', '',
       'Mười ảnh kém nhất (chữ đỏ = khác lớp): `anh_kem_nhat.jpg`. Chi tiết từng kết quả và khung bằng chứng: `top5_tung_anh.csv`.']
(out / 'ket_qua_test.md').write_text('\n'.join(md), encoding='utf-8')
print('\n'.join(md))
