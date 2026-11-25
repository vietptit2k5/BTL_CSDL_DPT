"""Tập test ảnh Internet – bước T1: thu ứng viên từ Wikimedia Commons (chỉ danh mục "Quality images").

Vì sao Commons/Quality images: ảnh chụp thật đã được cộng đồng thẩm định chất lượng kỹ thuật; giấy phép rõ (CC/PD);
có API ghi lại tác giả, giấy phép, mô tả -> lặp lại được. Không dùng Pexels/Pixabay vì đó là nguồn video của bộ dữ liệu.

Lọc tự động (khai báo trước): JPEG; giấy phép CC0 / CC BY / CC BY-SA / Public domain; cạnh ngắn >= 1000 px;
tỉ lệ khung 1:2 – 2,5:1 (loại ảnh panorama rất dài); tiêu đề không chứa từ chỉ tranh vẽ/bản đồ/ảnh ghép.
Thứ tự xét: xáo ngẫu nhiên seed 2026 trong từng lớp -> người duyệt xét lần lượt, nhận 10 ảnh đủ điều kiện đầu tiên.

Đầu ra: data/test_internet/ung_vien/<LOP>/<stt>.jpg (cạnh dài 1280), ung_vien.csv, bang_duyet_<LOP>.jpg
"""
import argparse
import csv
import html
import json
import random
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2] / 'data' / 'test_internet'
UA = {'User-Agent': 'D23-Nhom12-CSDLDPT/1.0 (student coursework; image test set; contact via course)'}
API = 'https://commons.wikimedia.org/w/api.php'
QUERIES = {
    'SEA': ['sea coast waves', 'ocean seascape', 'sea beach', 'sea cliffs', 'sea sunset horizon'],
    'WAT': ['waterfall', 'waterfalls cascade', 'falls river gorge'],
    'FOR': ['forest', 'forest trees woodland', 'forest path', 'rainforest', 'beech forest', 'coniferous forest'],
    'MOU': ['mountain', 'mountain peak', 'mountain range', 'alps summit', 'mountains valley'],
    'RIV': ['river', 'lake', 'lake reflection', 'river landscape', 'lake shore'],
    'FLO': ['flower', 'flowers field', 'wildflowers', 'blossom close-up', 'flower meadow'],
}
BAD_TITLE = re.compile(r'map|drawing|painting|illustration|poster|stamp|postcard|diagram|logo|collage|montage|stitch|hdr|'
                       r'infrared|aquarium|museum|stained|mosaic|sculpture|statue|coat of arms', re.I)
OK_LICENSE = re.compile(r'^(CC0|CC BY(-SA)? \d|Public domain|PD)', re.I)
ap = argparse.ArgumentParser()
ap.add_argument('--den', default='', help='tải thêm tới thứ tự này cho các lớp, ví dụ SEA=60,FOR=60 (mặc định 30)')
args = ap.parse_args()
LIMIT = {c: 30 for c in QUERIES} | {k: int(v) for k, v in (p.split('=') for p in args.den.split(',') if p)}


def call(params):
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': 2})
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as exc:
            print(f'  lỗi API ({exc.__class__.__name__}: {exc}); thử lại sau {5 * (attempt + 1)}s', flush=True)
            time.sleep(5 * (attempt + 1))
    raise SystemExit('Không gọi được Commons API')


def text(meta, key):
    v = meta.get(key, {}).get('value', '')
    return html.unescape(re.sub(r'<[^>]+>', ' ', str(v))).strip()


ROOT.mkdir(parents=True, exist_ok=True)
cache = ROOT / 'ket_qua_tim_kiem.json'              # lưu kết quả tìm kiếm: chạy lại không gọi API lần nữa
pool = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
for cls, qs in QUERIES.items():
    if cls in pool: continue
    titles = []
    for q in qs:
        r = call(dict(action='query', list='search', srsearch=f'{q} incategory:Quality_images filetype:bitmap',
                      srnamespace=6, srlimit=50))
        titles += [s['title'] for s in r['query']['search']]
        time.sleep(1.0)
    pool[cls] = list(dict.fromkeys(titles))
    cache.write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding='utf-8')
    print(cls, 'kết quả tìm kiếm:', len(pool[cls]), flush=True)

info_cache = ROOT / 'thong_tin_ung_vien.json'
cached = json.loads(info_cache.read_text(encoding='utf-8')) if info_cache.exists() else None
rows, kept = [], {}
for cls, titles in ({} if cached else pool).items():
    kept[cls] = []
    for i in range(0, len(titles), 40):
        r = call(dict(action='query', titles='|'.join(titles[i:i + 40]), prop='imageinfo',
                      iiprop='url|size|mime|extmetadata|sha1', iiurlwidth=1280))
        for p in r['query']['pages']:
            ii = (p.get('imageinfo') or [{}])[0]
            if not ii: continue
            m = ii.get('extmetadata', {}); lic = text(m, 'LicenseShortName'); w, h = ii.get('width', 0), ii.get('height', 0)
            reason = ''
            if ii.get('mime') != 'image/jpeg': reason = 'không phải JPEG'
            elif not OK_LICENSE.match(lic): reason = f'giấy phép {lic}'
            elif min(w, h) < 1000: reason = 'ảnh nhỏ'
            elif not 0.5 <= w / h <= 2.5: reason = 'tỉ lệ khung quá dài'
            elif BAD_TITLE.search(p['title']): reason = 'tiêu đề chỉ ảnh không phải ảnh chụp cảnh'
            row = dict(lop=cls, tieu_de=p['title'], trang=ii.get('descriptionurl', ''), url_anh=ii.get('thumburl') or ii.get('url'),
                       rong=w, cao=h, giay_phep=lic, tac_gia=text(m, 'Artist')[:120], mo_ta=text(m, 'ImageDescription')[:300],
                       ngay_chup=text(m, 'DateTimeOriginal')[:40], sha1_goc=ii.get('sha1', ''), loai_tu_dong=reason)
            rows.append(row)
            if not reason: kept[cls].append(row)
        time.sleep(1.0)
    random.Random(2026).shuffle(kept[cls])
    for n, row in enumerate(kept[cls], 1): row['thu_tu_xet'] = n
    print(cls, 'qua lọc tự động:', len(kept[cls]), flush=True)
if cached:
    rows, kept = cached['rows'], cached['kept']
else:
    info_cache.write_text(json.dumps(dict(rows=rows, kept=kept), ensure_ascii=False), encoding='utf-8')


def download(url, path):
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                path.write_bytes(r.read())
            return True
        except Exception as exc:
            print(f'  lỗi tải {path.name} ({exc}); thử lại sau {5 * (attempt + 1)}s', flush=True)
            time.sleep(5 * (attempt + 1))
    return False


# tải ảnh theo thứ tự xét (cạnh dài 1280) và làm bảng duyệt có đánh số.
# Một ảnh có thể là ứng viên ở hai lớp (từ khoá chồng nhau): mỗi lớp giữ bản ghi riêng, không tra theo tiêu đề.
for cls, items in kept.items():
    d = ROOT / 'ung_vien' / cls; d.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for n, row in enumerate(items, 1):
        if row['thu_tu_xet'] != n:
            raise SystemExit(f'Thứ tự xét của {cls} bị lệch tại vị trí {n}')
    first = LIMIT[cls] - 29 if LIMIT[cls] > 30 else 1          # bảng duyệt chỉ gồm 30 ứng viên của lượt này
    for row in items[:LIMIT[cls]]:
        f = d / f'{row["thu_tu_xet"]:03d}.jpg'
        if not f.exists():
            ok = download(row['url_anh'], f); time.sleep(1.5)
            if not ok:
                row['loi_tai'] = 'không tải được (lỗi mạng)'; continue
        im = Image.open(f)                     # kiểm tra file khớp bản ghi: cùng hướng và gần cùng tỉ lệ khung với ảnh gốc
        if abs(im.width / im.height - row['rong'] / row['cao']) > 0.02:
            raise SystemExit(f'{f} không khớp bản ghi {row["tieu_de"]}')
        row['file_ung_vien'] = f'ung_vien/{cls}/{f.name}'
        if row['thu_tu_xet'] >= first:
            im = Image.open(f).convert('RGB'); im.thumbnail((300, 220)); thumbs.append((row['thu_tu_xet'], im))
    sheet = Image.new('RGB', (6 * 304, ((len(thumbs) + 5) // 6) * 244), 'white'); dr = ImageDraw.Draw(sheet)
    for k, (n, im) in enumerate(thumbs):
        x, y = (k % 6) * 304, (k // 6) * 244
        sheet.paste(im, (x + 2, y + 20)); dr.text((x + 4, y + 4), f'{cls} #{n}', fill='black')
    sheet.save(ROOT / (f'bang_duyet_{cls}.jpg' if first == 1 else f'bang_duyet_{cls}_{first}-{LIMIT[cls]}.jpg'), quality=88)
    print(cls, 'đã tải', len(thumbs), flush=True)

keys = ['lop', 'thu_tu_xet', 'file_ung_vien', 'tieu_de', 'trang', 'url_anh', 'rong', 'cao', 'giay_phep', 'tac_gia', 'mo_ta',
        'ngay_chup', 'sha1_goc', 'loai_tu_dong', 'loi_tai']
out_rows = [r for items in kept.values() for r in items] + [r for r in rows if r['loai_tu_dong']]
with open(ROOT / 'ung_vien.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, keys, extrasaction='ignore'); w.writeheader()
    w.writerows(sorted(out_rows, key=lambda r: (r['lop'], r.get('thu_tu_xet', 10**6))))
print('Xong ->', ROOT)
