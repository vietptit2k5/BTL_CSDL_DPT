"""Real GPU smoke query; assert the online path never opens the SQLite backup."""
import json
import shutil
import sys
import time
from pathlib import Path
from unittest.mock import patch
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from nhom12.core import load_settings, file_hash
from nhom12.environment import configure_runtime
from nhom12.pipeline import query_image
from nhom12 import repository
from nhom12.search import rank
from nhom12.building import write_json

configure_runtime()
spec, cfg = load_settings()
source = json.loads((root / 'var/current_index.json').read_text(encoding='utf-8'))['index']
con = repository.connect(source, readonly=True)
try:
    image = con.execute("SELECT image_path FROM keyframes WHERE video_id='SEA005' AND frame_index=0").fetchone()[0]
finally:
    con.close()
output = root / 'var/search_phases/03_mysql'
image_copy = output / 'query-input.png'; shutil.copyfile(image, image_copy)
start = time.perf_counter()
with patch('nhom12.repository.connect', side_effect=AssertionError('Online MySQL query must not open SQLite')):
    demo = query_image(spec, cfg, None, image_copy)
elapsed = time.perf_counter() - start
trace = json.loads(Path(demo).with_name('trace.json').read_text(encoding='utf-8'))
con = repository.connect(source, readonly=True)
try:
    frames = repository.read_frames(con)
finally:
    con.close()
reference = rank({k: np.asarray(v, dtype='<f4') for k, v in trace['query_features'].items()}, frames, cfg['search']['weights'])
for hit, expected in zip(trace['hits'], reference, strict=True):
    for key in expected:
        if hit[key] != expected[key]:
            raise AssertionError(f'MySQL/SQLite ranking differs: {key}')
assert len({h['video_id'] for h in trace['hits']}) == 5
assert all(a['score'] >= b['score'] for a, b in zip(trace['hits'], trace['hits'][1:]))
assert trace['index'].startswith('mysql:d23_nhom12/')
result = dict(status='passed', input_kind='indexed_keyframe_smoke_only_not_independent_evaluation',
              query_image=str(image_copy), query_sha256=file_hash(image_copy), demo=demo,
              trace=str(Path(demo).with_name('trace.json')), index=trace['index'],
              online_sqlite_access='forbidden_by_test_guard', ranking_equal_to_sqlite=True,
              elapsed_seconds=elapsed, hits=trace['hits'])
write_json(output / 'query_validation.json', result)
print(json.dumps(result, ensure_ascii=False, indent=2))
