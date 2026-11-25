"""Bước 3: khảo sát điểm số TRƯỚC khi chọn trọng số (không chọn gì ở bước này).

B1. Phạm vi và độ phân tán của s_clip, s_hsv, s_lbp  -> vì sao trọng số không phải "tầm quan trọng"
B2. Từng đặc trưng dùng riêng: P@5 (trung bình theo lớp) và R@1  -> căn cứ đặt w_lbp = 0
B3. Ma trận nhầm lẫn của top-5 (chỉ CLIP và cấu hình hiện tại)  -> đối chiếu các cặp lớp gần nhau ở ND1 (Bảng 1.9)

Giao thức đo (dùng chung cho mọi bước sau):
  P@5: bỏ video nguồn khỏi kết quả; đúng = cùng lớp với truy vấn.
  R@1: giữ video nguồn nhưng bỏ khung gốc của truy vấn khỏi CSDL; đúng = video nguồn đứng đầu.
"""
import csv

import numpy as np

import common_w as W

inp = W.OUT / 'validation'; out = W.OUT / 'khao_sat'; out.mkdir(parents=True, exist_ok=True)
z = np.load(inp / 'tuong_dong.npz'); S = {f: z[f] for f in W.FEATS}; vids = list(z['video_ids'])
lab = list(csv.DictReader(open(inp / 'nhan.csv', encoding='utf-8-sig')))
qcls = np.array([r['lop'] for r in lab]); src_v = np.array([vids.index(r['video_nguon']) for r in lab])
src_f = np.array([int(r['vi_tri_khung']) for r in lab]); vcls = np.array([v[:3] for v in vids]); NV = len(vids)
spec, cfg = W.settings()


def evaluate(w):
    top = W.top_k(W.video_scores(S, w, NV, exclude_video=src_v))
    p5 = (vcls[top] == qcls[:, None]).mean(1)
    r1 = (W.top_k(W.video_scores(S, w, NV, exclude_frame=src_f), 1)[:, 0] == src_v).astype(float)
    return p5, r1, top


md = [f'# Khảo sát điểm số trên tập validation ({len(lab)} truy vấn, mỗi video một truy vấn)', '']
# ---------------- B1
rows = []
for f in W.FEATS:
    x = S[f]; within = x.std(1)
    rows.append([f, f'{x.min():.4f}', f'{np.percentile(x, 5):.4f}', f'{np.median(x):.4f}', f'{np.percentile(x, 95):.4f}',
                 f'{x.max():.4f}', f'{within.mean():.4f}'])
W.write_csv(out / 'B1_pham_vi_diem.csv', rows, ['dac_trung', 'min', 'p5', 'trung_vi', 'p95', 'max', 'do_lech_chuan_trong_1_truy_van'])
sd = {r[0]: float(r[6]) for r in rows}
md += ['## B1. Phạm vi điểm (trên mọi cặp truy vấn × khung)', '', '| Đặc trưng | min | p5 | trung vị | p95 | max | độ lệch chuẩn trong 1 truy vấn |',
       '|---|---|---|---|---|---|---|'] + [f'| {" | ".join(r)} |' for r in rows] + ['',
       f'Độ lệch chuẩn của s_hsv gấp **{sd["hsv"]/sd["clip"]:.1f} lần** s_clip. Ảnh hưởng thực của một đặc trưng tỉ lệ với '
       f'w × độ lệch chuẩn: ví dụ với 0,9/0,1/0, HSV có ảnh hưởng bằng {0.1*sd["hsv"]/(0.9*sd["clip"]):.2f} lần CLIP dù trọng số chỉ 0,1.', '']
# ---------------- B2
singles = {'Chỉ CLIP': dict(clip=1, hsv=0, lbp=0), 'Chỉ HSV': dict(clip=0, hsv=1, lbp=0), 'Chỉ LBP': dict(clip=0, hsv=0, lbp=1),
           f'Hiện tại {cfg["search"]["weights"]["clip"]}/{cfg["search"]["weights"]["hsv"]}/{cfg["search"]["weights"]["lbp"]}': cfg['search']['weights']}
rows, tops = [], {}
for name, w in singles.items():
    p5, r1, top = evaluate(w); tops[name] = top
    m, se, per = W.macro(p5, qcls)
    rows.append([name, f'{m:.4f}', f'{se:.4f}', f'{r1.mean():.4f}'] + [f'{per[c]:.3f}' for c in W.CLASSES])
rand = np.mean([((vcls == c).sum() - 1) / (NV - 1) for c in W.CLASSES])
W.write_csv(out / 'B2_tung_dac_trung.csv', rows, ['cau_hinh', 'P@5_theo_lop', 'SE', 'R@1'] + [f'P@5_{c}' for c in W.CLASSES])
md += ['## B2. Từng đặc trưng dùng riêng', '', '| Cấu hình | P@5 (TB theo lớp) | SE | R@1 | ' + ' | '.join(W.CLASSES) + ' |',
       '|---|---|---|---|' + '---|' * 6] + [f'| {" | ".join(r)} |' for r in rows] + ['',
       f'Mức ngẫu nhiên của P@5 (TB theo lớp) ≈ {rand:.3f}; theo lớp: ' +
       ', '.join(f'{c} {((vcls == c).sum() - 1) / (NV - 1):.3f}' for c in W.CLASSES) + '.', '']
# ---------------- B3
for name in ('Chỉ CLIP', [k for k in singles if k.startswith('Hiện tại')][0]):
    top = tops[name]; M = np.zeros((6, 6))
    for i, c in enumerate(qcls):
        for j in top[i]:
            M[W.CLASSES.index(c), W.CLASSES.index(vcls[j])] += 1
    M = 100 * M / M.sum(1, keepdims=True)
    tag = 'B3_nham_lan_' + ('clip' if name == 'Chỉ CLIP' else 'hien_tai') + '.csv'
    W.write_csv(out / tag, [[c] + [f'{x:.1f}' for x in M[i]] for i, c in enumerate(W.CLASSES)], ['lop_truy_van \\ lop_ket_qua (%)'] + W.CLASSES)
    off = sorted(((M[i, j], W.CLASSES[i], W.CLASSES[j]) for i in range(6) for j in range(6) if i != j), reverse=True)[:4]
    md += [f'## B3. Ma trận nhầm lẫn top-5 – {name} (% kết quả theo lớp)', '', '| Truy vấn \\ kết quả | ' + ' | '.join(W.CLASSES) + ' |',
           '|---|' + '---|' * 6] + [f'| {c} | ' + ' | '.join(f'{x:.1f}' for x in M[i]) + ' |' for i, c in enumerate(W.CLASSES)] + ['',
           'Bốn ô nhầm lớn nhất: ' + '; '.join(f'{a}→{b} {v:.1f}%' for v, a, b in off) + '.', '']
(out / 'khao_sat.md').write_text('\n'.join(md), encoding='utf-8')
print('\n'.join(md))
