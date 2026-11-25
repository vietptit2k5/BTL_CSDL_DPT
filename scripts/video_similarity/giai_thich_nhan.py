"""Explain one saved B0 result without AI, MySQL or a GPU.

python scripts/video_similarity/giai_thich_nhan.py --video SEA001
"""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import digest, file_hash, load_settings
from nhom12.video_workflow.files import read_json
from nhom12.video_workflow.nd1_original import COLORS, measure

ap=argparse.ArgumentParser();ap.add_argument('--video',required=True)
ap.add_argument('--run',type=Path,default=ROOT/'var/video_similarity/run01');args=ap.parse_args()
info=read_json(args.run/'snapshot/info.json')
if args.video not in info['ids']:raise SystemExit('Video ID không có trong snapshot')
raw=read_json(args.run/'b0/raw'/(args.video+'.json'));npz=args.run/'b0/raw'/(args.video+'.npz')
if file_hash(npz)!=raw['frames_sha256']:raise SystemExit('File khung đã thay đổi')
spec,cfg=load_settings()
if digest(spec)!=info['spec_hash']:raise SystemExit('Đặc tả hiện tại khác lần chạy')
thresholds=read_json(args.run/'nd1_sources/outputs/ch1_stats.json')['thresholds']
with np.load(npz,allow_pickle=False) as z:recomputed=measure(dict(z),spec,thresholds)
for key in ('d1','d2','d5'):
    if raw[key]!=recomputed[key]:raise SystemExit('Nhãn tính lại khác dữ liệu đã lưu')
lines=[f'Video: {args.video}',f'SHA256 video hiện tại: {raw["source_sha256"]}',
       '', 'D1: tỷ lệ tám nhóm màu trên 16 khung:']
lines += [f'  {c}: {100*raw["fraction_"+c]:.6f}%' for c in COLORS]
lines += [f'Màu lớn nhất: {raw["dominant_color"]}; ánh xạ GROUP5 -> {raw["d1"]}',
          '', 'D2: mật độ Canny từng khung:',str(raw['per_frame_edge']),
          f'Trung bình: {raw["edge_density"]:.10f}; ngưỡng gốc: {thresholds["edge"]}; nhãn: {raw["d2"]}',
          '', 'D5: trung bình hiệu tuyệt đối mức xám của từng cặp:',str(raw['per_pair_difference']),
          f'Trung bình float32: {raw["motion_index"]:.10f}; ngưỡng gốc: {thresholds["motion"]}; nhãn: {raw["d5"]}',
          '', 'Tính lại từ 32 khung NPZ: cả ba nhãn khớp.',
          'D1/D2/D5 là nhãn đánh giá ND1; không phải đầu vào lọc hoặc xếp hạng của bộ tìm video.']
out=args.run/'explanations';out.mkdir(exist_ok=True)
text='\n'.join(lines);(out/(args.video+'.txt')).write_text(text,encoding='utf-8');print(text)
