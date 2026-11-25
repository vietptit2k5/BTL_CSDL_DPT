"""Read every course PDF page; retain source hashes and PDF page references."""
import hashlib
import json
import re
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'var/devtools'))
import pymupdf

output = root / 'var/course_slides'
output.mkdir(parents=True, exist_ok=True)
manifest = []
def order(p):
    match = re.search(r'\d+', p.stem)
    return int(match.group()) if match else 1
for path in sorted((root.parent / 'HeCSDL_DPT_slides').glob('*.pdf'), key=order):
    number = order(path)
    doc = pymupdf.open(path)
    pages = [dict(page=i+1, text=p.get_text(sort=True)) for i, p in enumerate(doc)]
    item = dict(chapter=number, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                page_count=len(pages), pages=pages)
    (output / f'{number:02}.json').write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / f'{number:02}.txt').write_text('\n\n'.join(f'--- PDF PAGE {p["page"]} ---\n{p["text"]}' for p in pages), encoding='utf-8')
    manifest.append({k: v for k, v in item.items() if k != 'pages'})
    print(f'{number}: {path.name}: {len(pages)} pages; {sum(len(p["text"]) for p in pages)} characters')
(output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
