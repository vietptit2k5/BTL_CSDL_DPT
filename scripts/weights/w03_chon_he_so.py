"""Bước 4: CHỌN HỆ SỐ – tìm kiếm lưới một chiều trên tập validation, theo đúng file muc_tieu.json.

Với w_lbp = 0 (căn cứ ở khảo sát B2), chỉ còn một tham số: w_clip = 1 − w_hsv.
  1. Với mỗi w_hsv trong lưới: tính P@5 (TB theo lớp) kèm sai số chuẩn SE, và R@1.
  2. Giữ các cấu hình đạt ràng buộc R@1 >= ngưỡng.
  3. Quy tắc 1-SE: lấy P@5 cao nhất P*; chọn w_hsv nhỏ nhất có P@5 >= P* − SE (đơn giản nhất trong vùng nhiễu).
  4. Kiểm tra LBP: thử w_lbp nhỏ tại cấu hình đã chọn; chỉ nhận nếu P@5 tăng hơn 1 SE và vẫn đạt ràng buộc.
  5. Ghi var/weights/trong_so_chot.json (KHOÁ – không ghi đè nếu đã có) và báo cáo kèm biểu đồ.

Chạy:  python w03_chon_he_so.py            (chạy chính thức, khoá kết quả)
       python w03_chon_he_so.py --thu DIR   (chạy thử, ghi vào DIR, không khoá)
"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

import common_w as W

ap = argparse.ArgumentParser()
ap.add_argument('--thu', help='thư mục ghi kết quả chạy thử (không khoá)')
a = ap.parse_args()
HERE = Path(__file__).parent
goal_path = HERE / 'muc_tieu.json'; goal = json.loads(goal_path.read_text(encoding='utf-8'))
inp = W.OUT / 'validation'
out = Path(a.thu) if a.thu else W.OUT / 'chon_he_so'; out.mkdir(parents=True, exist_ok=True)
lock = (out if a.thu else W.OUT) / 'trong_so_chot.json'
if lock.exists() and not a.thu:
    raise SystemExit(f'Đã khoá trọng số ở {lock}. Không chọn lại sau khi đã khoá (nếu thật sự cần, đổi tên file cũ và ghi lý do).')

z = np.load(inp / 'tuong_dong.npz'); S = {f: z[f] for f in W.FEATS}; vids = list(z['video_ids']); NV = len(vids)
lab = list(csv.DictReader(open(inp / 'nhan.csv', encoding='utf-8-sig')))
qcls = np.array([r['lop'] for r in lab]); src_v = np.array([vids.index(r['video_nguon']) for r in lab])
src_f = np.array([int(r['vi_tri_khung']) for r in lab]); vcls = np.array([v[:3] for v in vids])
thr = goal['rang_buoc']['nguong']


def evaluate(w):
    top = W.top_k(W.video_scores(S, w, NV, exclude_video=src_v))
    p5 = (vcls[top] == qcls[:, None]).mean(1)
    r1 = (W.top_k(W.video_scores(S, w, NV, exclude_frame=src_f), 1)[:, 0] == src_v).astype(float)
    m, se, per = W.macro(p5, qcls)
    return dict(w=w, P5=m, SE=se, R1=float(r1.mean()), per=per, misses=[lab[i]['ma_truy_van'] for i in np.where(r1 == 0)[0]])


fmt = lambda w: f'{w["clip"]:.2f}/{w["hsv"]:.2f}/{w["lbp"]:.2f}'
# 1. lưới một chiều
grid = [evaluate(dict(clip=round(1 - h - goal['w_lbp_mac_dinh'], 4), hsv=h, lbp=goal['w_lbp_mac_dinh'])) for h in goal['luoi_w_hsv']]
# 2–3. ràng buộc + quy tắc 1-SE
ok = [g for g in grid if g['R1'] >= thr]
if ok:
    best = max(ok, key=lambda g: g['P5'])
    zone = [g for g in ok if g['P5'] >= best['P5'] - best['SE']]
    chosen = min(zone, key=lambda g: g['w']['hsv'])
    why = (f'{len(ok)}/{len(grid)} cấu hình đạt R@1 >= {thr}. P@5 cao nhất P* = {best["P5"]:.4f} tại {fmt(best["w"])} (SE = {best["SE"]:.4f}). '
           f'Vùng 1-SE (P@5 >= {best["P5"] - best["SE"]:.4f}) gồm w_hsv = {[g["w"]["hsv"] for g in zone]}; chọn w_hsv nhỏ nhất = {chosen["w"]["hsv"]}.')
else:
    chosen = max(grid, key=lambda g: (g['R1'], g['P5'])); best = chosen; zone = [chosen]
    why = f'Không cấu hình nào đạt R@1 >= {thr}; theo quy tắc dự phòng chọn R@1 cao nhất: {fmt(chosen["w"])}.'
# 4. kiểm tra LBP
checks = []
for l in goal['kiem_tra_lbp']:
    w = dict(clip=round(chosen['w']['clip'] - l, 4), hsv=chosen['w']['hsv'], lbp=l)
    if w['clip'] < 0: continue
    g = evaluate(w); g['nhan'] = g['R1'] >= thr and g['P5'] > chosen['P5'] + chosen['SE']; checks.append(g)
accepted = [g for g in checks if g['nhan']]
final = max(accepted, key=lambda g: g['P5']) if accepted else chosen
lbp_note = ('Thêm LBP vì P@5 tăng hơn 1 SE: ' + fmt(final['w'])) if accepted else \
    'Không thêm LBP: không mức w_lbp nào làm P@5 tăng quá 1 SE (khác biệt nằm trong nhiễu) → giữ w_lbp = 0.'

# 5. ghi kết quả
rows = [[fmt(g['w']), f'{g["P5"]:.4f}', f'{g["SE"]:.4f}', f'{g["R1"]:.4f}', 'đạt' if g['R1'] >= thr else 'không'] +
        [f'{g["per"][c]:.3f}' for c in W.CLASSES] for g in grid + checks]
W.write_csv(out / 'bang_luoi.csv', rows, ['clip/hsv/lbp', 'P@5_theo_lop', 'SE', 'R@1', f'R@1>={thr}'] + [f'P@5_{c}' for c in W.CLASSES])
xs = [g['w']['hsv'] for g in grid]
W.line_chart_svg(out / 'duong_P5_R1.svg', xs,
                 [('P@5 (TB lớp)', '#1f5fa8', [g['P5'] for g in grid], [g['SE'] for g in grid]),
                  ('R@1', '#c26a00', [g['R1'] for g in grid], None)],
                 'P@5 và R@1 theo trọng số HSV (w_clip = 1 − w_hsv, w_lbp = 0)', 'w_hsv', 'giá trị', hline=thr)
result = dict(trong_so=final['w'], P5_validation=round(final['P5'], 4), SE=round(final['SE'], 4), R1_validation=round(final['R1'], 4),
              ly_do=why, kiem_tra_lbp=lbp_note, so_truy_van=len(lab),
              chuan_hoa='bounded_distances', gop_khung='best_joint_frame',
              muc_tieu_sha256=W.file_sha(goal_path), du_lieu_sha256=W.file_sha(inp / 'tuong_dong.npz'),
              thoi_diem=datetime.now().isoformat(timespec='seconds'), che_do='thu' if a.thu else 'chinh_thuc')
W.dump_json(lock, result)
md = ['# Kết quả chọn hệ số tính điểm (tập validation)', '',
      f'Mục tiêu khai báo trước (`muc_tieu.json`): {goal["muc_tieu_chinh"]}; ràng buộc R@1 >= {thr}; {goal["quy_tac_chon"]}.', '',
      '| clip/hsv/lbp | P@5 (TB lớp) | SE | R@1 | Đạt ràng buộc | ' + ' | '.join(W.CLASSES) + ' |', '|---|---|---|---|---|' + '---|' * 6]
md += [f'| {" | ".join(r)} |' for r in rows]
md += ['', f'**Lựa chọn:** {why}', '', f'**Kiểm tra LBP:** {lbp_note}', '',
       f'**Hệ số chốt: CLIP {final["w"]["clip"]} / HSV {final["w"]["hsv"]} / LBP {final["w"]["lbp"]}** '
       f'(P@5 = {final["P5"]:.4f} ± {final["SE"]:.4f}, R@1 = {final["R1"]:.4f} trên {len(lab)} truy vấn validation).', '',
       f'Truy vấn không tìm ra video nguồn ở cấu hình chốt: {", ".join(final["misses"]) or "không có"}.', '',
       '![P@5 và R@1 theo w_hsv](duong_P5_R1.svg)']
(out / 'ket_qua_chon_he_so.md').write_text('\n'.join(md), encoding='utf-8')
print('\n'.join(md[4:]))
print(f'\nĐã ghi {lock}' + (' (CHẠY THỬ – chưa khoá)' if a.thu else ' – TRỌNG SỐ ĐÃ KHOÁ'))
