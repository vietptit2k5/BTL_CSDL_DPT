"""Coordinator: publish existing blind IDs without regenerating or revealing their mapping.

Only Python's standard library is needed. Original proposed labels remain ignored locally.
"""
import csv
import hashlib
import html
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'data/test_internet'
KIT=SOURCE/'xac_nhan_mu'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    with (KIT/'_doi_chieu_KHONG_MO.csv').open(encoding='utf-8-sig',newline='') as f:mapping=list(csv.DictReader(f))
    with (SOURCE/'nguon_chi_tiet.csv').open(encoding='utf-8-sig',newline='') as f:credits={r['file']:r for r in csv.DictReader(f)}
    manifest=dict(version='blind-label-kit-v1',schema=['anh','lop','muc_do','ghi_chu'],raters={})
    template=(Path(__file__).with_name('template.html')).read_text(encoding='utf-8')
    for who in ('TV2','TV3'):
        group=[r for r in mapping if r['nguoi']==who]
        names=sorted(r['ten_mu'] for r in group)
        if len(names)!=60 or len(set(names))!=60:raise ValueError('Expected 60 unique blind IDs')
        images={name:sha(KIT/f'anh_{who}'/name) for name in names}
        with (KIT/f'phieu_{who}.csv').open(encoding='utf-8-sig',newline='') as f:form=list(csv.DictReader(f))
        if [r['anh'] for r in form]!=names:raise ValueError('Existing form IDs changed; do not regenerate blindly')
        manifest['raters'][who]=dict(images=images,form=f'phieu_{who}.csv',page=f'{who}.html')
        payload=json.dumps(dict(rater=who,ids=names,snapshot=hashlib.sha256(json.dumps(images,sort_keys=True).encode()).hexdigest()))
        page=template.replace('__RATER__',who).replace('__PAYLOAD__',payload.replace('<','\\u003c'))
        (KIT/f'{who}.html').write_text(page,encoding='utf-8')
        with (KIT/f'credits_{who}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['anh','tac_gia','giay_phep','nguon','thay_doi']);w.writeheader()
            for r in sorted(group,key=lambda r:r['ten_mu']):
                c=credits[r['file_that']]
                w.writerow(dict(anh=r['ten_mu'],tac_gia=html.unescape(c['tac_gia']),giay_phep=c['giay_phep'],
                                nguon=c['trang_commons'],thay_doi='Resized to long side 1280 and renamed; image content not altered'))
    (KIT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared TV2.html, TV3.html, safe manifest and source credits; existing images/forms unchanged.')


if __name__=='__main__':main()
