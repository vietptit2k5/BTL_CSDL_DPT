"""Phần dùng chung cho quy trình chọn trọng số (bản rút gọn): đọc CSDL MySQL, mã hoá ảnh truy vấn, tính độ tương đồng.

Công thức độ tương đồng và cách gộp khung giống hệt hệ thống (src/nhom12/search.py, retrieval.py):
  s_clip = 1 − d_cos/2 = (1+cos)/2,  s_hsv = 1 − d_Bhattacharyya,  s_lbp = 1 − χ²
  điểm khung = Σ w_f·s_f ; điểm video = max theo 16 khung ; hoà điểm -> mã video nhỏ hơn đứng trước.
"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'src'))
from nhom12.core import load_settings  # noqa: E402

OUT = PROJECT / 'var' / 'weights'
CLASSES = ['SEA', 'WAT', 'FOR', 'MOU', 'RIV', 'FLO']
FEATS = ('clip', 'hsv', 'lbp')
K = 16


def settings():
    return load_settings()


def load_database(spec, cfg):
    """Đọc toàn bộ vector khung từ MySQL (có kiểm tra toàn vẹn của hệ thống) -> ma trận theo thứ tự (video, khung)."""
    from nhom12.storage_mysql.service import load_index
    frames, paths, _, label = load_index(spec, cfg)
    frames = sorted(frames, key=lambda f: (f['video_id'], f['index']))
    vids = sorted({f['video_id'] for f in frames})
    if len(frames) != len(vids) * K or any(f['index'] != i % K for i, f in enumerate(frames)):
        raise SystemExit('CSDL không có đúng 16 khung liên tiếp cho mỗi video')
    X = {f: np.stack([fr['features'][f] for fr in frames]).astype(np.float64) for f in FEATS}
    return dict(frames=frames, vids=vids, cls=np.array([v[:3] for v in vids]), X=X, paths=paths, label=label)


def encoder(spec, cfg):
    from nhom12.features import FrameExtractor
    return FrameExtractor(spec, model_path=cfg['model_path'], revision=cfg['model_revision'],
                          device=cfg['device'], local_files_only=cfg['local_files_only'])


def prepare_query(path, spec):
    """Đúng đường xử lý ảnh truy vấn của hệ thống (querying.SearchSession.query)."""
    from nhom12.querying import read_query
    from nhom12.preprocess import content_box, prepare_image, resize_short
    _, original, _ = read_query(path)
    decoded = resize_short(original, spec['sampling']['decode_short_side'])
    box = content_box([decoded], spec)
    return prepare_image(original, spec, box=box)


def similarities(Q, X):
    """Q: dict đặc trưng của n truy vấn; X: dict ma trận khung. Trả về s_f (n × số khung), float32."""
    q = {f: np.asarray(Q[f], np.float64) for f in FEATS}
    cos = (q['clip'] @ X['clip'].T) / (np.linalg.norm(q['clip'], axis=1)[:, None] * np.linalg.norm(X['clip'], axis=1)[None])
    s = {'clip': 1 - np.clip(1 - cos, 0, 2) / 2}
    coef = (np.sqrt(q['hsv']) @ np.sqrt(X['hsv']).T) / np.sqrt(q['hsv'].sum(1)[:, None] * X['hsv'].sum(1)[None])
    s['hsv'] = 1 - np.sqrt(np.clip(1 - coef, 0, 1))
    s['lbp'] = 1 - np.stack([.5 * (((X['lbp'] - v) ** 2) / (X['lbp'] + v + 1e-12)).sum(1) for v in q['lbp']])
    return {f: s[f].astype(np.float32) for f in FEATS}


def video_scores(S, w, n_videos, exclude_frame=None, exclude_video=None):
    """Điểm video (n × số video). exclude_frame: khung bị bỏ khỏi CSDL; exclude_video: video bị bỏ khỏi kết quả."""
    T = sum(np.float32(w[f]) * S[f] for f in FEATS if w.get(f, 0) > 0)
    n = T.shape[0]
    if exclude_frame is not None:
        T = T.copy(); T[np.arange(n), exclude_frame] = -np.inf
    V = T.reshape(n, n_videos, K).max(2)
    if exclude_video is not None:
        V = V.copy(); V[np.arange(n), exclude_video] = -np.inf
    return V


def top_k(V, k=5):
    return np.argsort(-V, axis=1, kind='stable')[:, :k]


def macro(values, classes):
    """Trung bình theo lớp và sai số chuẩn của trung bình đó (mỗi truy vấn độc lập)."""
    per = {c: values[classes == c] for c in CLASSES if (classes == c).any()}
    mean = float(np.mean([v.mean() for v in per.values()]))
    se = float(np.sqrt(sum(v.var(ddof=1) / len(v) for v in per.values() if len(v) > 1)) / len(per))
    return mean, se, {c: float(v.mean()) for c, v in per.items()}


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_csv(path, rows, header):
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:       # utf-8-sig: Excel đọc đúng tiếng Việt
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def line_chart_svg(path, xs, series, title, xlabel, ylabel, hline=None):
    """Biểu đồ đường SVG đơn giản. series: [(tên, màu, ys, sai_số hoặc None)]."""
    W, H, L, R, T, B = 640, 380, 64, 150, 40, 56
    allv = [y + (e or 0) for _, _, ys, es in series for y, e in zip(ys, es or [0] * len(ys))]
    allv += [y - (e or 0) for _, _, ys, es in series for y, e in zip(ys, es or [0] * len(ys))]
    if hline is not None: allv.append(hline)
    lo, hi = min(allv), max(allv); pad = (hi - lo) * .08 or .01; lo, hi = lo - pad, hi + pad
    px = lambda x: L + (x - min(xs)) / ((max(xs) - min(xs)) or 1) * (W - L - R)
    py = lambda y: T + (hi - y) / (hi - lo) * (H - T - B)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Times New Roman" font-size="13">',
           f'<rect width="{W}" height="{H}" fill="white"/>', f'<text x="{W/2}" y="22" text-anchor="middle" font-size="15">{title}</text>',
           f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="black"/><line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="black"/>']
    for i in range(6):
        y = lo + (hi - lo) * i / 5
        out.append(f'<line x1="{L-4}" y1="{py(y):.1f}" x2="{W-R}" y2="{py(y):.1f}" stroke="#ddd"/>'
                   f'<text x="{L-8}" y="{py(y)+4:.1f}" text-anchor="end">{y:.3f}</text>')
    for x in xs:
        out.append(f'<text x="{px(x):.1f}" y="{H-B+18}" text-anchor="middle">{x:g}</text>')
    out.append(f'<text x="{(L+W-R)/2}" y="{H-12}" text-anchor="middle">{xlabel}</text>')
    out.append(f'<text transform="translate(16,{(T+H-B)/2}) rotate(-90)" text-anchor="middle">{ylabel}</text>')
    if hline is not None:
        out.append(f'<line x1="{L}" y1="{py(hline):.1f}" x2="{W-R}" y2="{py(hline):.1f}" stroke="#c00" stroke-dasharray="6 4"/>'
                   f'<text x="{W-R+6}" y="{py(hline)+4:.1f}" fill="#c00">ngưỡng {hline:g}</text>')
    for k, (name, color, ys, es) in enumerate(series):
        pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in zip(xs, ys))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y, e in zip(xs, ys, es or [None] * len(ys)):
            out.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="3.5" fill="{color}"/>')
            if e:
                out.append(f'<line x1="{px(x):.1f}" y1="{py(y-e):.1f}" x2="{px(x):.1f}" y2="{py(y+e):.1f}" stroke="{color}"/>')
        out.append(f'<rect x="{W-R+10}" y="{T+10+k*22}" width="14" height="4" fill="{color}"/>'
                   f'<text x="{W-R+30}" y="{T+16+k*22}">{name}</text>')
    out.append('</svg>')
    Path(path).write_text('\n'.join(out), encoding='utf-8')


def augment(img, rng):
    """Biến đổi giả lập ảnh người dùng – giống thí nghiệm ND2 (cắt, sáng, tương phản, đổi kích thước, JPEG q=80)."""
    from PIL import Image, ImageEnhance
    w, h = img.size
    fw, fh = rng.uniform(.75, .9), rng.uniform(.75, .9); cw, ch = int(w * fw), int(h * fh)
    x, y = rng.integers(0, w - cw + 1), rng.integers(0, h - ch + 1)
    img = img.crop((x, y, x + cw, y + ch))
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(.85, 1.15))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(.85, 1.15))
    s = rng.uniform(.6, 1.8)
    img = img.resize((max(32, int(img.width * s)), max(32, int(img.height * s))), Image.Resampling.BICUBIC)
    buf = io.BytesIO(); img.save(buf, 'JPEG', quality=80)
    return buf.getvalue()


def dump_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
