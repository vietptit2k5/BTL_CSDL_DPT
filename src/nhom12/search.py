"""ND4: one image -> exactly five unique videos, with a common evidence frame.

Implementation decision for ND3/4, NOT a claim made in report ND1/2:
bounded feature scores; fuse on EACH frame first; then max over frames.
"""
import math
import numpy as np
from .core import ContractError, validate_vector

def distance(name,a,b):
    a,b=validate_vector(name,a),validate_vector(name,b)
    # Accumulate in float64: stored float32 L1 histograms can sum to
    # 0.99999994, which otherwise makes d(x,x) spuriously about 0.00024.
    a,b=a.astype(np.float64),b.astype(np.float64)
    if name=='clip':
        return float(np.clip(1-np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)),0,2))
    if name=='hsv':
        coefficient=np.sqrt(a*b).sum()/np.sqrt(a.sum()*b.sum())
        return float(np.sqrt(np.clip(1-coefficient,0,1)))
    return float(.5*np.sum((a-b)**2/(a+b+1e-12)))

def rank(query, frames, weights, top_k=5):
    if top_k!=5:
        raise ContractError('XLSX ND4 fixes top_k=5')
    if set(weights)!={'hsv','lbp','clip'} or not all(math.isfinite(w) and w>=0 for w in weights.values()) or not math.isclose(sum(weights.values()),1):
        raise ContractError('Invalid image weights')
    for f in weights:
        validate_vector(f,query[f])
    best={}
    for frame in frames:
        distances={f:distance(f,query[f],frame['features'][f]) for f in weights}
        similarities={f:1-d/(2 if f=='clip' else 1) for f,d in distances.items()}
        score=sum(weights[f]*similarities[f] for f in weights)
        hit=dict(video_id=frame['video_id'],frame_index=frame['index'],time_sec=frame['time'],
                 image_path=frame['image_path'],score=score,distances=distances,
                 similarities=similarities,contributions={f:weights[f]*similarities[f] for f in weights})
        previous=best.get(hit['video_id'])
        if previous is None or (-score,hit['frame_index'])<(-previous['score'],previous['frame_index']):
            best[hit['video_id']]=hit
    if len(best)<5:
        raise ContractError('Need at least five indexed videos; no duplicate/fake padding')
    return sorted(best.values(),key=lambda h:(-h['score'],h['video_id']))[:5]
