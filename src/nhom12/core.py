"""Contracts ND1/ND2; provenance guard for ND3 and ND4. No media imports."""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
FEATURES = {"hsv":128, "lbp":10, "clip":512, "motion":24}

class ContractError(ValueError):
    pass

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def load_settings(config=None):
    spec = json.loads((PROJECT / 'report_spec.json').read_text(encoding='utf-8'))
    cfg = json.loads(Path(config or PROJECT / 'config.json').read_text(encoding='utf-8'))
    for name, dim in FEATURES.items():
        if spec['features'][name + '_dim'] != dim:
            raise ContractError('Feature dimensions disagree with report Table 2.8')
    fixed_sampling=dict(k=16,margin=.05,decode_short_side=360,motion_pairs=8,motion_dt=.25,motion_short_side=180)
    fixed_preprocess=dict(percentile=98,border_threshold=24,mean_threshold=12,min_border_fraction=.01,min_keep_area=.4,feature_short_side=256)
    if spec['sampling']!=fixed_sampling or spec['preprocess']!=fixed_preprocess:
        raise ContractError('Sampling/preprocessing changed from report Table 2.8; revise contract explicitly')
    if spec['features']['clip_checkpoint']!='openai/clip-vit-base-patch32' or spec['flow_normalization']!='L1_each_of_3_blocks_without_global_division':
        raise ContractError('Model/flow normalization differs from report')
    search = cfg['search']
    if search['top_k'] != 5 or set(search['weights']) != {'hsv','lbp','clip'}:
        raise ContractError('XLSX ND4 requires top5; image weights must cover HSV/LBP/CLIP only')
    weights = list(search['weights'].values())
    if not all(math.isfinite(w) and w >= 0 for w in weights) or not math.isclose(sum(weights),1):
        raise ContractError('Weights must be finite, nonnegative and sum to one')
    if search['aggregation'] != 'best_joint_frame' or search['normalization'] != 'bounded_distances':
        raise ContractError('Unsupported scoring policy')
    for key in ('dataset_root','artifacts'):
        cfg[key] = str((PROJECT / cfg[key]).resolve())
    if cfg.get('model_path'):
        cfg['model_path']=str((PROJECT/cfg['model_path']).resolve())
    return spec, cfg

def sample_times(duration, k=16, margin=.05):
    if duration <= 0 or k <= 0:
        raise ContractError('Invalid duration or K')
    return [duration * (margin + (1-2*margin)*(i+.5)/k) for i in range(k)]

def inventory(root, spec):
    """Hash source bytes; never infer that one scene/nonduplicate was verified."""
    root = Path(root)
    rows = []
    for folder, code in spec['classes'].items():
        directory = root / folder
        if not directory.is_dir():
            raise ContractError(f'Missing class folder: {directory}')
        for p in sorted(directory.iterdir()):
            if not p.is_file() or p.suffix.lower() != '.mp4':
                continue
            if not re.fullmatch(code + r'\d{3}', p.stem):
                raise ContractError(f'Unexpected video ID: {p}')
            rows.append(dict(video_id=p.stem, class_code=code, relative_path=p.relative_to(root).as_posix(),
                             size_bytes=p.stat().st_size, sha256=file_hash(p)))
    if len({r['video_id'] for r in rows}) != len(rows):
        raise ContractError('Duplicate video IDs')
    return rows

def assert_snapshot(expected, current):
    if digest(expected) != digest(current):
        raise ContractError('Dataset changed: rebuild index; never use stale vectors')

def validate_vector(name, value):
    import numpy as np
    x = np.asarray(value, dtype='<f4')
    if x.shape != (FEATURES[name],) or not np.isfinite(x).all():
        raise ContractError(f'Invalid {name} vector: {x.shape}')
    if name == 'clip':
        good = np.isclose(np.linalg.norm(x),1,atol=1e-4)
    else:
        good = (x >= 0).all() and (all(np.isclose(p.sum(),1,atol=1e-4) for p in x.reshape(3,8))
                                  if name == 'motion' else np.isclose(x.sum(),1,atol=1e-4))
    if not good:
        raise ContractError(f'Invalid {name} normalization')
    return x
