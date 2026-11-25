"""ND4b: self-contained evidence and independent score replay (course 1/11/12)."""
import html
import json
import math
from pathlib import Path
import numpy as np
from .core import ContractError, file_hash, validate_vector
from .search import distance


def histogram_svg(vectors):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 420" role="img" aria-label="HSV and LBP normalized histograms"><rect width="1000" height="420" fill="white"/>']
    for name, y in [('hsv', 35), ('lbp', 240)]:
        values = vectors[name]; maximum = float(values.max()) or 1
        parts.append(f'<text x="35" y="{y}" font-family="sans-serif" font-size="18">{name.upper()} — {len(values)} bins, L1 normalized</text>')
        width = 930/len(values)
        for i, value in enumerate(values):
            height = float(value)/maximum*135
            parts.append(f'<rect x="{35+i*width:.3f}" y="{y+150-height:.3f}" width="{max(.5,width-.5):.3f}" height="{height:.3f}" fill="#117a65"><title>bin {i}: {float(value):.9g}</title></rect>')
        parts.append(f'<path d="M35 {y+150} H965" stroke="#333"/>')
        parts.append(f'<text x="2" y="{y+22}" font-family="sans-serif" font-size="11">{maximum:.3f}</text><text x="15" y="{y+151}" font-family="sans-serif" font-size="11">0</text>')
        ticks=range(len(values)) if len(values)<=10 else (0,32,64,96,127)
        for i in ticks:
            parts.append(f'<text x="{35+(i+.5)*width:.3f}" y="{y+168}" text-anchor="middle" font-family="sans-serif" font-size="11">{i}</text>')
    return ''.join(parts)+'</svg>'


def verify_trace(path):
    path = Path(path).resolve()
    try:
        trace = json.loads(path.read_text(encoding='utf-8'))
        if trace.get('trace_version') != 'nd4-v2':
            raise ContractError('Unsupported trace; score replay requires nd4-v2 evidence')
        root = path.parent
        for name, expected in trace['artifact_sha256'].items():
            artifact = (root/name).resolve()
            if not artifact.is_relative_to(root) or not artifact.is_file() or file_hash(artifact) != expected:
                raise ContractError('Trace evidence is missing, changed, or outside its folder')
        if file_hash(root/'source-image.bin') != trace['query_sha256']:
            raise ContractError('Trace query bytes differ')
        query = {k: validate_vector(k, np.asarray(v, dtype='<f4')) for k, v in trace['query_features'].items()}
        weights = trace['search_policy']['weights']
        if set(weights) != {'hsv', 'lbp', 'clip'} or not all(math.isfinite(w) and w >= 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1):
            raise ContractError('Trace has invalid weights')
        hits = trace['hits']
        if len(hits) != 5 or len({h['video_id'] for h in hits}) != 5 or hits != sorted(hits, key=lambda h: (-h['score'], h['video_id'])):
            raise ContractError('Trace must contain five unique sorted videos')
        for hit in hits:
            key = f'{hit["video_id"]}/{hit["frame_index"]}'
            stored = trace['matched_features'][key]
            score = 0
            for name in weights:
                measured = distance(name, query[name], np.asarray(stored[name], dtype='<f4'))
                similarity = 1-measured/(2 if name == 'clip' else 1)
                contribution = weights[name]*similarity
                for actual, expected in [(hit['distances'][name], measured), (hit['similarities'][name], similarity), (hit['contributions'][name], contribution)]:
                    if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-12):
                        raise ContractError('Trace distance/similarity/contribution is not reproducible')
                score += contribution
            if not math.isclose(hit['score'], score, rel_tol=0, abs_tol=1e-12):
                raise ContractError('Trace score is not reproducible')
        return dict(status='passed', checked_hits=5, scope='score_replay_for_returned_hits',
                    query_sha256=trace['query_sha256'], index=trace['index'])
    except (KeyError, TypeError, ValueError, OSError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError('Malformed or incomplete trace evidence') from None
