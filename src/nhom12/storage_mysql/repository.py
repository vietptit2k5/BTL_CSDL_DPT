"""Generation-scoped readers; all query vectors come from MySQL."""
import json
import math
from pathlib import Path
import numpy as np
from ..core import ContractError, validate_vector, digest, file_hash

TABLES = {
    'feature_catalog': ('feature', 'dimension', 'normalization', 'distance'),
    'videos': ('video_id', 'class_code', 'relative_path', 'sha256', 'size_bytes', 'metadata_json', 'crop_json', 'quality_json'),
    'keyframes': ('video_id', 'frame_index', 'target_time', 'actual_time', 'image_path'),
    'frame_features': ('video_id', 'frame_index', 'feature', 'vector'),
    'video_features': ('video_id', 'feature', 'vector'),
    'video_artifacts': ('video_id', 'manifest_json'),
}
ORDER = {'feature_catalog': 'feature', 'videos': 'video_id', 'keyframes': 'video_id,frame_index',
         'frame_features': 'video_id,frame_index,feature', 'video_features': 'video_id,feature',
         'video_artifacts': 'video_id'}


def rows(con, table, generation):
    columns = TABLES[table]
    cur = con.cursor()
    try:
        cur.execute(f'SELECT {",".join(columns)} FROM {table} WHERE generation_id=%s ORDER BY {ORDER[table]}', (generation,))
        return cur.fetchall()
    finally:
        cur.close()


def generation_info(con, generation, ready=True):
    cur = con.cursor()
    try:
        cur.execute('SELECT status,source_sha256,context_json FROM generations WHERE generation_id=%s', (generation,))
        row = cur.fetchone()
    finally:
        cur.close()
    if row is None or (ready and row[0] != 'ready'):
        raise ContractError('MySQL generation is missing or incomplete')
    return dict(status=row[0], source_sha256=row[1], context=json.loads(row[2]))


def canonical(table, row):
    return tuple(json.loads(x) if name.endswith('_json') else bytes(x) if name == 'vector' else x
                 for name, x in zip(TABLES[table], row, strict=True))


def validate(con, generation, spec, verify_artifacts=False):
    info = generation_info(con, generation, ready=False)
    context = info['context']
    if context['build']['spec_hash'] != digest(spec):
        raise ContractError('MySQL report spec differs')
    snapshot = json.loads(context['build']['snapshot_json'])
    videos = rows(con, 'videos', generation)
    expected = {r['video_id']: (r['class_code'], r['relative_path'], r['sha256'], r['size_bytes']) for r in snapshot}
    if {v[0]: v[1:5] for v in videos} != expected:
        raise ContractError('MySQL video snapshot differs')
    catalog = {r[0]: r[1:] for r in rows(con, 'feature_catalog', generation)}
    wanted = {'hsv': (128, 'L1', 'Bhattacharyya'), 'lbp': (10, 'L1', 'Chi-square'),
              'clip': (512, 'L2', 'cosine'), 'motion': (24, 'L1_each_block', 'Chi-square')}
    if catalog != wanted:
        raise ContractError('MySQL feature catalog differs')
    frame_rows = rows(con, 'keyframes', generation)
    frames = {}
    times = {}
    for vid, i, target, actual, path in frame_rows:
        if vid not in expected or not all(math.isfinite(t) and t >= 0 for t in (target, actual)):
            raise ContractError('MySQL keyframe metadata is invalid')
        frames[(vid, i)] = dict(video_id=vid, index=i, time=actual, image_path=path, features={})
        times.setdefault(vid, []).append((i, target, actual))
    for vid in expected:
        entries = times.get(vid, [])
        if [t[0] for t in entries] != list(range(spec['sampling']['k'])):
            raise ContractError(f'MySQL {vid}: incomplete keyframes')
        if any(a[1] >= b[1] or a[2] >= b[2] for a, b in zip(entries, entries[1:])):
            raise ContractError('MySQL timestamps must increase')
    vector_rows = rows(con, 'frame_features', generation)
    for vid, i, feature, blob in vector_rows:
        if (vid, i) not in frames or feature not in ('hsv', 'lbp', 'clip'):
            raise ContractError('Unexpected MySQL frame feature')
        frames[(vid, i)]['features'][feature] = validate_vector(feature, np.frombuffer(blob, dtype='<f4'))
    if any(set(f['features']) != {'hsv', 'lbp', 'clip'} for f in frames.values()):
        raise ContractError('MySQL frame features are incomplete')
    motions = rows(con, 'video_features', generation)
    if {r[0] for r in motions} != set(expected) or len(motions) != len(expected):
        raise ContractError('MySQL motion vectors are incomplete')
    for vid, feature, blob in motions:
        if feature != 'motion':
            raise ContractError('Unexpected video feature')
        validate_vector('motion', np.frombuffer(blob, dtype='<f4'))
    artifacts = rows(con, 'video_artifacts', generation)
    if {r[0] for r in artifacts} != set(expected):
        raise ContractError('MySQL artifact manifests incomplete')
    if verify_artifacts:
        for vid, manifest in artifacts:
            manifest = json.loads(manifest)
            paths = {f['image_path'] for (v, i), f in frames.items() if v == vid}
            if not paths.issubset(manifest):
                raise ContractError('MySQL keyframe paths missing from artifact manifest')
            for path, sha in manifest.items():
                if not Path(path).is_file() or file_hash(path) != sha:
                    raise ContractError(f'MySQL artifact changed: {vid}')
    counts = dict(videos=len(videos), keyframes=len(frames), frame_features=len(vector_rows),
                  video_features=len(motions), video_artifacts=len(artifacts))
    return dict(counts=counts, dataset_quality_status=context['build']['quality_status']), list(frames.values()), {v[0]: v[2] for v in videos}
