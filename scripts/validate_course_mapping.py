"""Verify source coverage/page references/module links without modifying slides."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
mapping=json.loads((root/'docs/course_mapping.json').read_text(encoding='utf-8'))
chapters=mapping['chapters']
assert [c['chapter'] for c in chapters]==list(range(1,13))
assert sum(c['page_count'] for c in chapters)==386
for chapter in chapters:
    source=(root/'docs'/chapter['source']).resolve()
    assert source.is_file()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==chapter['sha256']
    extracted=json.loads((root/f'var/course_slides/{chapter["chapter"]:02}.json').read_text(encoding='utf-8'))
    assert len(extracted['pages'])==chapter['page_count']
    assert [p['page'] for p in extracted['pages']]==list(range(1,chapter['page_count']+1))
    for topic in chapter['topics']:
        lo,hi=topic['pdf_pages']
        assert 1<=lo<=hi<=chapter['page_count']
        for module in topic['code']:
            assert (root/module).is_file(),module
report=dict(status='passed',chapters=len(chapters),pdf_pages=386,
            mapped_topics=sum(len(c['topics']) for c in chapters),
            source_files_unchanged=True,page_numbers='1-based PDF order, not printed slide labels')
out=root/'var/course_slides/mapping_validation.json';out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
