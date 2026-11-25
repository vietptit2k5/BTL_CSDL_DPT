"""Validate a blind annotation form using Python's standard library only."""
import argparse
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
KIT=ROOT/'data/test_internet/xac_nhan_mu'
CLASSES=('SEA','WAT','FOR','MOU','RIV','FLO','KHONG_RO')
FIELDS=('anh','lop','muc_do','ghi_chu')


def validate(path,expected,partial=False):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=list(FIELDS):raise ValueError('Cột phải là: anh,lop,muc_do,ghi_chu')
        rows=list(reader)
    ids=[r['anh'] for r in rows]
    if len(ids)!=len(set(ids)) or set(ids)!=set(expected):
        raise ValueError('Phiếu phải chứa đủ mỗi mã ảnh đúng một lần; không đổi tên ảnh')
    errors=[];completed=0
    for row in rows:
        if None in row or any(row.get(k) is None for k in FIELDS):
            errors.append(f'{row.get("anh")}: dòng CSV thừa/thiếu cột');continue
        label=row['lop'].strip();certainty=row['muc_do'].strip();notes=row['ghi_chu'].strip()
        if partial and not label and not certainty and not notes:continue
        if label not in CLASSES:errors.append(f'{row["anh"]}: lớp phải thuộc '+', '.join(CLASSES));continue
        if certainty not in ('chac','phan_van'):errors.append(f'{row["anh"]}: muc_do phải là chac hoặc phan_van');continue
        if (label=='KHONG_RO' or certainty=='phan_van') and not notes:
            errors.append(f'{row["anh"]}: cần ghi lý do khi không rõ/phân vân');continue
        completed+=1
    if errors:raise ValueError('\n'.join(errors))
    return dict(status='valid_partial' if partial else 'valid_complete',completed=completed,total=len(expected),
                notice='Kiểm tra định dạng và độ đầy đủ; không phán xét nhãn đúng hay sai')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rater',required=True,choices=('TV2','TV3'));ap.add_argument('--csv',type=Path)
    ap.add_argument('--partial',action='store_true',help='Allow completely blank, untouched rows')
    args=ap.parse_args();manifest=json.loads((KIT/'manifest.json').read_text(encoding='utf-8'))
    try:result=validate(args.csv or KIT/f'phieu_{args.rater}.csv',manifest['raters'][args.rater]['images'],args.partial)
    except (ValueError,OSError) as exc:ap.exit(2,str(exc)+'\n')
    print(json.dumps(dict(rater=args.rater,**result),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
