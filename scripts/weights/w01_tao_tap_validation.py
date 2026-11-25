"""Bước 1–2: tạo tập validation truy vấn giả lập và xuất bảng độ tương đồng.

- Mặc định dùng TẤT CẢ 561 video, mỗi video một truy vấn (--per-class N để chỉ lấy N video mỗi lớp, chọn ngẫu nhiên
  với seed cố định). Tập test là ảnh Internet, không lấy từ kho video, nên dùng toàn bộ kho làm validation không rò rỉ.
- Mỗi video lấy MỘT khung (số 7) – các khung cùng video gần như giống nhau, lấy nhiều khung không thêm thông tin.
- Biến đổi như ảnh người dùng (giống ND2), rồi đi qua đúng đường xử lý truy vấn của hệ thống.
- Nhãn tự động: lớp của video nguồn và mã video nguồn.
- Kiểm tra: điểm do script tính phải trùng điểm do hệ thống (ExactFrameIndex) tính.

Đầu ra (var/weights/validation/): anh/*.jpg, nhan.csv, dac_trung.npz, tuong_dong.npz, bang_tuong_dong.csv
"""
import argparse
import time

import numpy as np
from PIL import Image

import common_w as W

ap = argparse.ArgumentParser()
ap.add_argument('--per-class', type=int, default=0, help='0 = mọi video')
ap.add_argument('--frame', type=int, default=7)
ap.add_argument('--seed', type=int, default=2026)
a = ap.parse_args()

spec, cfg = W.settings()
out = W.OUT / 'validation'; (out / 'anh').mkdir(parents=True, exist_ok=True)
t0 = time.time()
db = W.load_database(spec, cfg)
vids, cls, frames = db['vids'], db['cls'], db['frames']
print(f'CSDL {db["label"]}: {len(vids)} video, {len(frames)} khung ({time.time()-t0:.0f}s)', flush=True)

rng = np.random.default_rng(a.seed)
chosen = []
for c in W.CLASSES:
    pool = [i for i, v in enumerate(vids) if v[:3] == c]
    chosen += pool if a.per_class <= 0 else sorted(rng.choice(pool, a.per_class, replace=False).tolist())

rows, prepared = [], []
for n, vi in enumerate(chosen):
    v = vids[vi]; fr = frames[vi * W.K + a.frame]
    src = Image.open(fr['image_path']).convert('RGB')
    qid = f'Q{n+1:03d}_{v}'
    path = out / 'anh' / f'{qid}.jpg'
    path.write_bytes(W.augment(src, rng))
    prepared.append(W.prepare_query(path, spec))
    rows.append([qid, v[:3], v, a.frame, vi * W.K + a.frame, path.name])
W.write_csv(out / 'nhan.csv', rows, ['ma_truy_van', 'lop', 'video_nguon', 'khung_nguon', 'vi_tri_khung', 'file'])

enc = W.encoder(spec, cfg)
t = time.time(); feats = enc.extract(prepared); print(f'mã hoá {len(feats)} ảnh: {time.time()-t:.1f}s', flush=True)
Q = {f: np.stack([x[f] for x in feats]) for f in W.FEATS}
np.savez(out / 'dac_trung.npz', **Q)
S = W.similarities(Q, db['X'])
np.savez(out / 'tuong_dong.npz', **S, video_ids=np.array(vids))

# ---- kiểm tra khớp với hệ thống: cùng vector truy vấn, cùng trọng số hiện tại -> cùng top-5 và cùng điểm
from nhom12.retrieval import ExactFrameIndex
index = ExactFrameIndex(frames)
w_now = cfg['search']['weights']
V = W.video_scores(S, w_now, len(vids))
bad = 0
for i in range(0, len(feats), max(1, len(feats) // 6)):
    hits = index.rank(feats[i], w_now)
    mine = W.top_k(V[i:i+1])[0]
    same = [h['video_id'] for h in hits] == [vids[j] for j in mine]
    gap = max(abs(h['score'] - float(V[i, vids.index(h['video_id'])])) for h in hits)
    bad += (not same) or gap > 1e-5
    print(f'  kiểm tra {rows[i][0]}: top-5 {"trùng" if same else "KHÁC"} hệ thống, lệch điểm tối đa {gap:.1e}')
if bad:
    raise SystemExit('Cách tính trong script không khớp hệ thống – dừng lại')

# ---- bảng để xem bằng Excel: mỗi truy vấn giữ top-20 video theo CLIP ∪ top-5 theo HSV ∪ top-5 theo LBP
table = []
for i, r in enumerate(rows):
    cand = set()
    for f, k in (('clip', 20), ('hsv', 5), ('lbp', 5)):
        cand |= set(W.top_k(S[f][i:i+1].reshape(1, len(vids), W.K).max(2), k)[0].tolist())
    for vi in sorted(cand):
        for k in range(W.K):
            j = vi * W.K + k
            table.append([r[0], r[1], r[2], vids[vi], k, f'{S["clip"][i, j]:.6f}', f'{S["hsv"][i, j]:.6f}', f'{S["lbp"][i, j]:.6f}'])
W.write_csv(out / 'bang_tuong_dong.csv', table,
            ['ma_truy_van', 'lop_truy_van', 'video_nguon', 'video', 'khung', 's_clip', 's_hsv', 's_lbp'])
W.dump_json(out / 'thong_tin.json', dict(seed=a.seed, per_class=a.per_class, frame=a.frame, index=db['label'],
                                          queries=len(rows), rows_excel=len(table), seconds=round(time.time() - t0, 1)))
print(f'Xong: {len(rows)} truy vấn, bảng Excel {len(table)} dòng -> {out}')
