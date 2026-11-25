"""Tập test – bước T3: xác nhận nhãn MÙ bởi hai thành viên, rồi tổng hợp.

  python t03_xac_nhan_nhan.py tao       -> tạo gói gán nhãn mù cho TV2 và TV3
  python t03_xac_nhan_nhan.py tong_hop  -> đọc hai phiếu đã điền, tính độ đồng thuận, liệt kê ảnh bất đồng

Gán nhãn mù: ảnh được đổi tên ngẫu nhiên (X01…X60, thứ tự khác nhau cho mỗi người) để tên file không lộ lớp;
phiếu không có lớp đề xuất, không có ghi chú "ca biên". Bảng đối chiếu tên nằm ở _doi_chieu_KHONG_MO.csv.
Độ đồng thuận: tỉ lệ trùng và hệ số Cohen's kappa (đã trừ phần trùng do ngẫu nhiên).
"""
import csv
import random
import shutil
import sys
from collections import Counter

from PIL import Image, ImageDraw

import common_w as W

ROOT = W.PROJECT / 'data' / 'test_internet'
BLIND = ROOT / 'xac_nhan_mu'
RATERS = {'TV2': 11, 'TV3': 23}            # seed xáo thứ tự riêng cho từng người
CLASSES = W.CLASSES
HUONG_DAN = """# Hướng dẫn gán nhãn (làm một mình, không trao đổi với người khác cho tới khi nộp phiếu)

Mở thư mục `anh_<TÊN>/`, xem từng ảnh ở kích thước đầy đủ, điền vào `phieu_<TÊN>.csv` (mở bằng Excel):
- cột `lop`: một trong SEA, WAT, FOR, MOU, RIV, FLO, hoặc KHONG_RO nếu không xác định được một lớp
- cột `muc_do`: `chac` hoặc `phan_van`
- cột `ghi_chu`: lý do khi chọn KHONG_RO hoặc phan_van (ví dụ: "hồ chiếm nửa dưới, núi nửa trên")

Quy tắc (Bảng 1.1 báo cáo ND1): gán theo **chủ thể chính – đối tượng chiếm diện tích lớn nhất và là trọng tâm của ảnh**.
| Mã | Lớp | Chủ thể |
|---|---|---|
| SEA | Biển | mặt biển, sóng, bờ biển, bãi cát giáp biển, hoàng hôn trên biển |
| WAT | Thác nước | dòng nước đổ từ trên cao xuống, kèm bọt và sương |
| FOR | Rừng | tán lá, thân cây, đường mòn trong rừng, rừng phủ kín sườn đồi |
| MOU | Núi | đỉnh núi, dãy núi, sườn núi, thung lũng (hình dạng núi là chủ thể) |
| RIV | Sông/Hồ | mặt nước tương đối phẳng có bờ bao quanh, có thể phản chiếu; không có sóng lớn, không có thác |
| FLO | Hoa | một bông hoa cận cảnh, bụi hoa, cánh đồng hoa |
Ví dụ: hồ có núi phía sau → RIV nếu mặt nước là phần lớn khung hình, MOU nếu núi là điểm nhấn; thác giữa rừng → WAT.

Không mở các file khác trong thư mục `test_internet` (nhãn đề xuất, bảng sàng lọc, bảng đối chiếu tên).
"""


def create():
    labels = list(csv.DictReader(open(ROOT / 'nhan.csv', encoding='utf-8-sig')))
    BLIND.mkdir(exist_ok=True)
    mapping = []
    for who, seed in RATERS.items():
        order = labels[:]; random.Random(seed).shuffle(order)
        d = BLIND / f'anh_{who}'; d.mkdir(exist_ok=True)
        sheet = Image.new('RGB', (10 * 210, 6 * 230), 'white'); dr = ImageDraw.Draw(sheet); rows = []
        for k, r in enumerate(order, 1):
            name = f'X{k:02d}.jpg'
            shutil.copyfile(ROOT / 'anh' / r['file'], d / name)
            mapping.append([who, name, r['file']]); rows.append([name, '', '', ''])
            im = Image.open(d / name).convert('RGB'); im.thumbnail((204, 204))
            x, y = ((k - 1) % 10) * 210, ((k - 1) // 10) * 230
            sheet.paste(im, (x + 3, y + 22)); dr.text((x + 3, y + 5), name, fill='black')
        sheet.save(BLIND / f'tong_quan_{who}.jpg', quality=90)
        W.write_csv(BLIND / f'phieu_{who}.csv', rows, ['anh', 'lop', 'muc_do', 'ghi_chu'])
    W.write_csv(BLIND / '_doi_chieu_KHONG_MO.csv', mapping, ['nguoi', 'ten_mu', 'file_that'])
    (BLIND / 'HUONG_DAN.md').write_text(HUONG_DAN, encoding='utf-8')
    print('Đã tạo gói gán nhãn mù tại', BLIND)


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n / n
    return po, (po - pe) / (1 - pe) if pe < 1 else 1.0


def summarize():
    prop = {r['file']: r['lop'] for r in csv.DictReader(open(ROOT / 'nhan.csv', encoding='utf-8-sig'))}
    back = {(r['nguoi'], r['ten_mu']): r['file_that'] for r in csv.DictReader(open(BLIND / '_doi_chieu_KHONG_MO.csv', encoding='utf-8-sig'))}
    got = {}
    for who in RATERS:
        rows = list(csv.DictReader(open(BLIND / f'phieu_{who}.csv', encoding='utf-8-sig')))
        bad = [r['anh'] for r in rows if r['lop'].strip().upper() not in CLASSES + ['KHONG_RO']]
        if bad:
            raise SystemExit(f'Phiếu {who} chưa điền đủ hoặc sai mã lớp ở: {", ".join(bad)}')
        got[who] = {back[(who, r['anh'])]: (r['lop'].strip().upper(), r['muc_do'].strip(), r['ghi_chu'].strip()) for r in rows}
    files = sorted(prop)
    a = [got['TV2'][f][0] for f in files]; b = [got['TV3'][f][0] for f in files]; p = [prop[f] for f in files]
    out = ['# Tổng hợp xác nhận nhãn tập test', '', '| So sánh | Tỉ lệ trùng | Cohen\'s kappa |', '|---|---|---|']
    for name, x, y in (('TV2 – TV3', a, b), ('TV2 – đề xuất', a, p), ('TV3 – đề xuất', b, p)):
        po, k = kappa(x, y); out.append(f'| {name} | {po:.3f} | {k:.3f} |')
    out += ['', 'Thang đọc kappa (Landis & Koch 1977): 0,61–0,80 khá tốt; 0,81–1,00 gần như hoàn toàn.', '']
    dis = [[f, prop[f], *got['TV2'][f], *got['TV3'][f]] for f in files if not (got['TV2'][f][0] == got['TV3'][f][0] == prop[f])]
    W.write_csv(ROOT / 'bat_dong.csv', dis, ['file', 'de_xuat', 'TV2_lop', 'TV2_muc_do', 'TV2_ghi_chu', 'TV3_lop', 'TV3_muc_do', 'TV3_ghi_chu'])
    out += [f'Ảnh cả ba thống nhất: {len(files) - len(dis)}/{len(files)}. Ảnh cần thảo luận: {len(dis)} (bat_dong.csv).', '',
            'Xử lý ảnh bất đồng: cả nhóm xem lại theo Bảng 1.1. Thống nhất được thì ghi lớp cuối cùng vào nhan.csv kèm lý do; '
            'không thống nhất được thì loại ảnh và lấy ứng viên kế tiếp theo thứ tự xét (README mục 6).']
    (ROOT / 'tong_hop_xac_nhan.md').write_text('\n'.join(out), encoding='utf-8')
    print('\n'.join(out))
    for row in dis:
        print(' ', row[0], 'đề xuất', row[1], '| TV2', row[2], row[3], row[4], '| TV3', row[5], row[6], row[7])


if __name__ == '__main__':
    {'tao': create, 'tong_hop': summarize}[sys.argv[1] if len(sys.argv) > 1 else 'tao']()
