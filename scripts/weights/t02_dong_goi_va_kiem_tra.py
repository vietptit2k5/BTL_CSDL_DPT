"""Tập test ảnh Internet – bước T2: ghi quyết định sàng lọc, đóng gói 60 ảnh, kiểm tra rò rỉ (E6).

Quyết định sàng lọc (người duyệt xem lần lượt theo thứ tự xét, áp dụng tiêu chí E1–E5 trong data/test_internet/README.md)
được ghi ngay trong file này để có thể kiểm tra lại. Ứng viên không có trong bảng là chưa được xét (đã đủ 10 ảnh trước đó).

Kiểm tra rò rỉ: độ giống CLIP (cos) giữa mỗi ảnh nhận và 8.976 khung trong CSDL, và giữa các ảnh nhận với nhau.
Cặp có cos >= 0,95 được ghi ra để xem bằng mắt. Bước này chỉ xét độ trùng, không xét lớp của kết quả tìm kiếm.
"""
import csv
import hashlib
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import common_w as W

ROOT = W.PROJECT / 'data' / 'test_internet'
N = 'nhận'
D = {  # lớp -> {thứ tự xét: (quyết định/tiêu chí, lý do, nhãn phụ hoặc ghi chú)}
    'SEA': {1: ('E3', 'tàu thả phao chiếm phần nổi bật'), 2: (N, '', 'vách đá, cột đá ven biển'),
            3: ('E3', 'thuyền chiếm phần lớn khung, bãi cát'), 4: (N, '', 'bờ đá, bãi cát; ảnh dọc'),
            5: ('E5', 'cùng địa điểm Twelve Apostles với #2'), 6: ('E3', 'thuyền là chủ thể'),
            7: (N, '', 'hoàng hôn trên biển, cọc gỗ nhỏ'), 8: ('E5', 'tác giả Dietmar Rabich đã có 2 ảnh trong lớp'),
            9: ('E3', 'ghế bãi biển phủ kín khung'), 10: (N, '', 'sóng vỗ bờ đá'), 11: ('E5', 'tác giả đã đủ 2 ảnh; đá chiếm phần lớn'),
            12: ('E1', 'không có biển (cỏ lúc hoàng hôn)'), 13: ('E5', 'tác giả đã đủ 2 ảnh'),
            14: ('E1', 'bãi cát chiếm phần lớn, mặt biển chỉ là dải hẹp'), 15: ('E1', 'bến thuyền và biển hiệu; Salton Sea là hồ'),
            16: (N, '', 'cột đá giữa vịnh, phơi sáng lâu'), 17: ('E3', 'người câu cá nổi bật'), 18: ('E3', 'dù che nắng phủ bãi cát'),
            19: ('E5', 'tác giả đã đủ 2 ảnh'), 20: (N, '', 'hoàng hôn trên biển; ảnh dọc'), 21: ('E3', 'thuyền là chủ thể'),
            22: ('E2', 'ảnh đen trắng'), 23: ('E3', 'thuyền và chim là chủ thể'), 24: (N, '', 'bọt sóng trên bãi biển'),
            25: ('E1', 'không thấy biển'), 26: ('E5', 'tác giả đã đủ 2 ảnh'), 27: ('E1', 'chân dung người'), 28: ('E1', 'ô tô'),
            29: ('E5', 'tác giả đã đủ 2 ảnh'), 30: ('E5', 'tác giả đã đủ 2 ảnh'), 31: ('E5', 'tác giả đã đủ 2 ảnh'),
            32: ('E5', 'tác giả đã đủ 2 ảnh'), 33: ('E1', 'núi Uluru, không có biển'), 34: ('E5', 'tác giả đã đủ 2 ảnh; cầu gỗ'),
            35: ('E5', 'tác giả đã đủ 2 ảnh; đen trắng'), 36: ('E1', 'ô tô'), 37: ('E3', 'thuyền là chủ thể'),
            38: (N, '', 'vòm đá ven biển, vách đá chiếm nửa trái'), 39: ('E5', 'tác giả đã đủ 2 ảnh'),
            40: (N, '', 'bờ đá, phơi sáng lâu'), 41: ('E5', 'tác giả đã đủ 2 ảnh'), 42: ('E1', 'ô tô'),
            43: ('E3', 'xe và thuyền trên bãi'), 44: ('E3', 'thuyền và người kéo thuyền'), 45: ('E5', 'tác giả đã đủ 2 ảnh'),
            46: ('E5', 'tác giả đã đủ 2 ảnh'), 47: ('E3', 'cột, mái che, cây cảnh trên bãi'), 48: ('E3', 'thuyền là chủ thể'),
            49: (N, '', 'bờ biển có mỏm đá nhọn')},
    'WAT': {1: (N, '', 'ảnh dọc'), 2: ('E1', 'ghềnh rộng lẫn với sông, không có dòng đổ rõ'), 3: ('E1', 'thác đóng băng'),
            4: (N, '', 'thác giữa đồng cỏ'), 5: (N, '', 'thác bậc giữa rừng'), 6: (N, '', 'thác nhỏ, hồ phía dưới'),
            7: ('E3', 'cầu gỗ chiếm nửa dưới khung'), 8: ('E1', 'suối chảy qua đá, không có dòng đổ từ độ cao rõ'),
            9: (N, '', 'thác mảnh trên vách cỏ; ảnh dọc'), 10: ('E1', 'thác ở xa, hẻm đá và sông chiếm phần lớn'),
            11: ('E1', 'ảnh flycam: rừng phủ kín, không thấy thác'), 12: (N, '', 'thác cao, mảnh; ảnh dọc'),
            13: (N, '', 'ảnh dọc'), 14: (N, '', 'thác trên vách đá rêu'), 15: (N, '', 'thác giữa cột đá bazan'),
            16: ('E1', 'dương xỉ và rừng chiếm phần lớn, thác nhỏ'), 17: ('E5', 'tác giả King of Hearts đã có 2 ảnh'),
            18: (N, '', 'thác Horseshoe (Niagara), thuyền du lịch nhỏ, cầu vồng')},
    'FOR': {1: (N, '', 'nhìn ngược lên tán rừng'), 2: ('E1', 'mẫu côn trùng'), 3: ('E1', 'hồ và núi'), 4: (N, '', 'đường mòn trong rừng'),
            5: ('E3', 'ghế băng và lối gỗ là chủ thể'), 6: (N, '', 'đường mòn, hoa dưới tán'), 7: ('E2', 'hiệu ứng lia máy nhoè, không phải ảnh thông thường'),
            8: ('E1', 'cây trong công viên, có ghế'), 9: ('E1', 'chim'), 10: ('E1', 'đồng cỏ chiếm phần lớn, rừng ở xa'),
            11: (N, '', 'đường rừng mùa thu'), 12: ('E1', 'gốc cây cụt là chủ thể'), 13: ('E5', 'tác giả Dietmar Rabich đã có 2 ảnh'),
            14: ('E1', 'cận cảnh thân cây'), 15: ('E5', 'tác giả đã đủ 2 ảnh; cùng địa điểm với #1'), 16: ('E5', 'tác giả đã đủ 2 ảnh'),
            17: (N, '', 'rừng nguyên sinh, lối đi có lan can'), 18: (N, '', 'rừng trong sương'), 19: ('E3', 'toà nhà và ô tô'),
            20: ('E1', 'hồ và đồi rừng, không rõ lớp'), 21: ('E1', 'đồi núi phủ cây, lẫn với núi'), 22: ('E5', 'tác giả đã đủ 2 ảnh'),
            23: ('E1', 'rắn'), 24: ('E5', 'tác giả đã đủ 2 ảnh'), 25: ('E1', 'chim'), 26: ('E1', 'chim'), 27: ('E1', 'hoa'),
            28: ('E3', 'đàn ngựa'), 29: (N, '', 'rừng dẻ trong khe'), 30: ('E1', 'thác nước'),
            31: ('E1', 'bãi cây bụi, rừng thưa'), 32: ('E1', 'nấm'), 33: ('E5', 'tác giả đã đủ 2 ảnh; bò'), 34: ('E1', 'một cây đơn lẻ'),
            35: ('E5', 'tác giả đã đủ 2 ảnh'), 36: ('E3', 'nhà nguyện'), 37: ('E3', 'lâu đài'), 38: ('E1', 'chim'),
            39: ('E1', 'thung lũng cây bụi, hoa ở tiền cảnh'), 40: ('E1', 'thung lũng núi'), 41: ('E3', 'tường thành và lối đi'),
            42: ('E5', 'tác giả đã đủ 2 ảnh'), 43: ('E1', 'quả trứng'), 44: ('E1', 'hoa'), 45: ('E5', 'tác giả đã đủ 2 ảnh'),
            46: ('E1', 'hồ và núi'), 47: ('E1', 'vân gỗ'), 48: ('E5', 'cùng địa điểm Mount Seymour với #4'),
            49: ('E4', 'bảng thông tin có chữ lớn'), 50: ('E1', 'cây ở tiền cảnh, núi và biển phía xa'), 51: ('E3', 'nhà gỗ phủ tuyết'),
            52: (N, '', 'rừng dẻ dày'), 53: (N, '', 'đường rừng có tia nắng'), 54: ('E5', 'tác giả đã đủ 2 ảnh'), 55: ('E1', 'hoa'),
            56: ('E1', 'đỉnh đồi trống, hai cây'), 57: ('E1', 'đồng trống, cây thưa'), 58: (N, '', 'rừng phủ vách hẻm núi')},
    'MOU': {1: (N, '', 'sống núi cỏ, đường mòn'), 2: ('E3', 'thánh giá đỉnh núi nổi bật giữa khung'), 3: (N, '', 'thung lũng sông băng'),
            4: (N, '', 'núi tuyết, hồ nhỏ dưới thung lũng'), 5: ('E1', 'cây thông phủ tuyết là chủ thể'),
            6: (N, '', 'biển mây, hồ nhỏ phía dưới'), 7: ('E2', 'ảnh đen trắng; thánh giá'), 8: (N, '', 'đỉnh núi hình tháp'),
            9: (N, '', 'thung lũng khô cằn'), 10: (N, '', 'thung lũng núi đá'), 11: ('E3', 'thánh giá đỉnh núi nổi bật'),
            12: ('E1', 'cỏ chiếm phần lớn, núi ở xa'), 13: ('E1', 'rừng thông ở tiền cảnh chiếm phần lớn'), 14: (N, '', 'dãy núi tuyết'),
            15: ('E1', 'sườn tuyết, không thấy hình dạng núi'), 16: (N, '', 'dãy núi nhìn từ máy bay lúc hoàng hôn'),
            17: (N, '', 'núi đá Dolomites')},
    'RIV': {1: (N, '', 'hồ Baikal: hồ lớn, trông giống biển'), 2: (N, '', 'hồ giữa rừng, phản chiếu'),
            3: ('E1', 'núi chiếm phần lớn, hồ nhỏ (theo quy tắc Bảng 1.1 là MOU)'), 4: (N, '', 'kênh suối giữa cây phủ sương giá'),
            5: (N, '', 'suối giữa đồng cỏ'), 6: ('E3', 'thuyền thúng và cầu tàu'), 7: (N, '', 'hồ, đá ở tiền cảnh; ảnh dọc'),
            8: (N, '', 'hồ phản chiếu đồi'), 9: ('E3', 'tháp quan sát'), 10: ('E1', 'thác nước'), 11: (N, '', 'sông mùa thu, thuyền nhỏ bên bờ'),
            12: ('E1', 'cây cỏ che gần hết mặt nước'), 13: (N, '', 'hồ, sậy, đồi rừng'), 14: ('E5', 'tác giả Dietmar Rabich đã có 2 ảnh'),
            15: (N, '', 'sông giữa rừng, nhìn từ trên cao'), 16: (N, '', 'hồ núi, đá ven bờ; núi phía sau')},
    'FLO': {1: ('E3', 'đài phun nước và nhà cửa'), 2: (N, '', 'hoa kế cận cảnh'), 3: ('E1', 'sậy và ao, hoa không phải chủ thể'),
            4: (N, '', 'hoa táo cận cảnh'), 5: (N, '', 'lan đất; ảnh dọc'), 6: ('E1', 'rùa'), 7: (N, '', 'đồng hoa cúc'),
            8: (N, '', 'hoa chuông trắng; ảnh dọc'), 9: (N, '', 'hoa trà đỏ'), 10: ('E3', 'ong là chủ thể'), 11: (N, '', 'hoa cẩm chướng'),
            12: ('E5', 'tác giả Uoaei1 đã có 2 ảnh'), 13: (N, '', 'hoa vạn thọ'), 14: ('E2', 'chụp trong studio, nền nhân tạo'),
            15: ('E3', 'tháp cổng và toà nhà'), 16: (N, '', 'cánh đồng hoa dại, biển và hải đăng phía xa'),
            17: ('E3', 'bướm là chủ thể'), 18: ('E2', 'nền đen nhân tạo'), 19: (N, '', 'hoa lưu ly; ảnh dọc')},
}

cand = {(r['lop'], int(r['thu_tu_xet'])): r for r in csv.DictReader(open(ROOT / 'ung_vien.csv', encoding='utf-8-sig')) if r['thu_tu_xet']}
screen, accepted = [], []
for cls in W.CLASSES:
    dec = D[cls]
    if sorted(dec) != list(range(1, max(dec) + 1)):
        raise SystemExit(f'{cls}: phải xét liên tục từ #1, không được bỏ qua ứng viên')
    if sum(v[0] == N for v in dec.values()) != 10 or dec[max(dec)][0] != N:
        raise SystemExit(f'{cls}: phải dừng đúng lúc nhận đủ 10 ảnh')
    for n in sorted(dec):
        r = cand[(cls, n)]; code, why = dec[n][0], dec[n][1]
        screen.append([cls, n, r['tieu_de'][5:], r['tac_gia'], code, why, r['trang']])
        if code == N:
            accepted.append((cls, n, r, dec[n][2]))
titles = [a[2]['tieu_de'] for a in accepted]
if len(set(titles)) != len(titles):
    raise SystemExit('Một ảnh được nhận ở hai lớp')
for cls in W.CLASSES:
    authors = [a[2]['tac_gia'] for a in accepted if a[0] == cls]
    if max(authors.count(x) for x in authors) > 2:
        raise SystemExit(f'{cls}: một tác giả có hơn 2 ảnh')
W.write_csv(ROOT / 'sang_loc.csv', screen, ['lop', 'thu_tu_xet', 'tieu_de', 'tac_gia', 'quyet_dinh', 'ly_do', 'trang_commons'])

# ---- đóng gói
out = ROOT / 'anh'; out.mkdir(exist_ok=True)
labels, sources = [], []
for k, (cls, n, r, note) in enumerate(accepted):
    name = f'T{cls}{sum(1 for a in accepted[:k + 1] if a[0] == cls):02d}.jpg'
    shutil.copyfile(ROOT / r['file_ung_vien'], out / name)
    sha = hashlib.sha256((out / name).read_bytes()).hexdigest()
    labels.append([name, cls, r['trang'], ''])
    sources.append([name, cls, n, r['tieu_de'][5:], r['trang'], r['tac_gia'], r['giay_phep'], f'{r["rong"]}x{r["cao"]}',
                    sha, note, r['mo_ta'][:200]])
W.write_csv(ROOT / 'nhan.csv', labels, ['file', 'lop', 'nguon', 'nhom'])
W.write_csv(ROOT / 'nguon_chi_tiet.csv', sources, ['file', 'lop', 'thu_tu_xet', 'tieu_de', 'trang_commons', 'tac_gia', 'giay_phep',
                                                  'kich_thuoc_goc', 'sha256_ban_luu', 'ghi_chu_noi_dung', 'mo_ta_commons'])

# ---- kiểm tra rò rỉ E6 (chỉ độ trùng)
spec, cfg = W.settings()
db = W.load_database(spec, cfg); enc = W.encoder(spec, cfg)
feats = enc.extract([W.prepare_query(out / l[0], spec) for l in labels])
Q = np.stack([f['clip'] for f in feats]).astype(np.float64)
X = db['X']['clip'] / np.linalg.norm(db['X']['clip'], axis=1, keepdims=True)
cos_db = Q @ X.T; cos_tt = Q @ Q.T; np.fill_diagonal(cos_tt, -1)
flags, rep = [], []
for i, l in enumerate(labels):
    j = int(cos_db[i].argmax()); fr = db['frames'][j]
    rep.append([l[0], f'{cos_db[i, j]:.4f}', fr['video_id'], fr['index']])
    if cos_db[i, j] >= 0.95: flags.append((l[0], fr['video_id'], fr['image_path'], cos_db[i, j]))
pairs = [(labels[i][0], labels[j][0], cos_tt[i, j]) for i in range(len(labels)) for j in range(i + 1, len(labels)) if cos_tt[i, j] >= 0.95]
W.write_csv(ROOT / 'kiem_tra_trung.csv', rep, ['anh', 'cos_cao_nhat_voi_khung_CSDL', 'video', 'khung'])
mx = np.array([float(r[1]) for r in rep])
print(f'Đã nhận {len(labels)} ảnh. cos cao nhất với khung CSDL: trung vị {np.median(mx):.3f}, lớn nhất {mx.max():.3f}')
print('Cặp ảnh test – khung CSDL có cos >= 0,95:', flags or 'không có')
print('Cặp ảnh test – ảnh test có cos >= 0,95:', pairs or 'không có')
if flags:     # ghép để xem bằng mắt
    sheet = Image.new('RGB', (640, 250 * len(flags)), 'white'); dr = ImageDraw.Draw(sheet)
    for k, (a, v, p, c) in enumerate(flags):
        for x, path in ((0, out / a), (320, p)):
            im = Image.open(path).convert('RGB'); im.thumbnail((310, 220)); sheet.paste(im, (x + 5, 250 * k + 25))
        dr.text((5, 250 * k + 5), f'{a} vs {v} cos={c:.3f}', fill='black')
    sheet.save(ROOT / 'kiem_tra_trung.jpg', quality=90)

# ---- ảnh tổng quan để thành viên khác xác nhận nhãn (không kèm kết quả tìm kiếm)
tile = 210; sheet = Image.new('RGB', (10 * tile, 6 * (tile + 20)), 'white'); dr = ImageDraw.Draw(sheet)
for k, l in enumerate(labels):
    im = Image.open(out / l[0]).convert('RGB'); im.thumbnail((tile - 6, tile - 6))
    x, y = (k % 10) * tile, (k // 10) * (tile + 20)
    sheet.paste(im, (x + 3, y + 20)); dr.text((x + 3, y + 4), l[0], fill='black')
sheet.save(ROOT / 'tong_quan.jpg', quality=90)
W.write_csv(ROOT / 'nhan_xac_nhan.csv', [[l[0], l[1], '', '', ''] for l in labels],
            ['file', 'lop_de_xuat', 'xac_nhan_TV2 (dong y / lop khac)', 'xac_nhan_TV3 (dong y / lop khac)', 'ghi_chu'])
