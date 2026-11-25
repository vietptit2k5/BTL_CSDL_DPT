"""ND3: symmetric matching of the ND2 frame sets, plus normalized Flow distance.

Each descriptor has its own frame matching. Temporal ordering is not compared.
No ND1 label is used to filter or rank candidates.
"""
import math
import numpy as np
from .core import ContractError, validate_vector

FEATURES = ('clip', 'hsv', 'lbp', 'motion')
POLICY = 'nd3_symmetric_mean_best_per_descriptor_flow_chi_over_3_v1'


def validate_weights(weights):
    if set(weights) != set(FEATURES) or not all(
        isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in weights.values()
    ) or not math.isclose(sum(weights.values()), 1, abs_tol=1e-10):
        raise ContractError('Video weights must cover CLIP/HSV/LBP/motion, be nonnegative and sum to 1')


def frame_similarities(name, left, right):
    a, b = np.asarray(left, np.float64), np.asarray(right, np.float64)
    if name == 'clip':
        cosine = (a @ b.T) / (np.linalg.norm(a, axis=1)[:, None] * np.linalg.norm(b, axis=1)[None])
        return (1 + np.clip(cosine, -1, 1)) / 2
    if name == 'hsv':
        coefficient = np.sqrt(a) @ np.sqrt(b).T / np.sqrt(a.sum(1)[:, None] * b.sum(1)[None])
        return 1 - np.sqrt(np.clip(1-coefficient, 0, 1))
    if name != 'lbp':
        raise ContractError('Frame descriptor must be CLIP, HSV or LBP')
    return 1 - .5 * np.sum((a[:, None]-b[None])**2 / (a[:, None]+b[None]+1e-12), axis=2)


def symmetric_match(similarity):
    s = np.asarray(similarity, np.float64)
    return float((s.max(axis=1).mean() + s.max(axis=0).mean()) / 2)


def motion_similarity(left, right):
    a, b = np.asarray(left, np.float64), np.asarray(right, np.float64)
    distance = .5 * np.sum((a-b)**2 / (a+b+1e-12))
    return float(np.clip(1-distance/3, 0, 1))


def validate_arrays(arrays, video_ids):
    n = len(video_ids)
    if n < 6 or list(video_ids) != sorted(set(video_ids)):
        raise ContractError('Need at least six unique, sorted video IDs')
    for f, dim in [('clip',512), ('hsv',128), ('lbp',10), ('motion',24)]:
        expected = (n, dim) if f == 'motion' else (n,16,dim)
        x = np.asarray(arrays[f])
        if x.shape != expected:
            raise ContractError(f'Video array shape differs: {f}: {x.shape}, expected {expected}')
        for row in x.reshape(-1,dim):
            validate_vector(f, row)


def pair_score(arrays, i, j):
    scores = {f:symmetric_match(frame_similarities(f, arrays[f][i], arrays[f][j]))
              for f in FEATURES if f != 'motion'}
    scores['motion'] = motion_similarity(arrays['motion'][i], arrays['motion'][j])
    return scores


def build_matrices(arrays, video_ids, progress=None):
    validate_arrays(arrays, video_ids)
    n = len(video_ids)
    result = {f:np.empty((n,n),np.float64) for f in FEATURES}
    flat = {f:np.asarray(arrays[f],np.float64).reshape(n*16,-1) for f in FEATURES if f != 'motion'}
    # Evaluate all 16x16 frame pairs. Reduction is mean(best) in BOTH directions.
    for i in range(n):
        for f in flat:
            s = frame_similarities(f, arrays[f][i], flat[f]).reshape(16,n,16)
            result[f][i] = (s.max(axis=2).mean(axis=0) + s.max(axis=0).mean(axis=1))/2
        a = np.asarray(arrays['motion'][i],np.float64)
        b = np.asarray(arrays['motion'],np.float64)
        result['motion'][i] = np.clip(1-(.5*np.sum((a-b)**2/(a+b+1e-12),axis=1))/3,0,1)
        if progress:
            progress(i+1,n)
    return result


def search_video(video_id, video_ids, matrices, weights, top_k=5):
    validate_weights(weights)
    if top_k != 5:
        raise ContractError('ND3 demonstration returns five distinct other videos')
    try:
        q = video_ids.index(video_id)
    except ValueError:
        raise ContractError(f'Video ID not in indexed MySQL generation: {video_id}') from None
    scores = sum(weights[f]*np.asarray(matrices[f][q],np.float64) for f in FEATURES)
    candidates = [i for i in range(len(video_ids)) if i != q]
    selected = sorted(candidates,key=lambda i:(-scores[i],video_ids[i]))[:top_k]
    return [dict(video_id=video_ids[i],score=float(scores[i]),
                 similarities={f:float(matrices[f][q,i]) for f in FEATURES},
                 contributions={f:float(weights[f]*matrices[f][q,i]) for f in FEATURES}) for i in selected]


def reference_pair(arrays, i, j):
    """Independent scalar oracle; intentionally does not call matrix helpers."""
    result = {}
    for f in FEATURES[:-1]:
        s = np.empty((16,16),np.float64)
        for k in range(16):
            for l in range(16):
                a, b = arrays[f][i,k].astype(np.float64), arrays[f][j,l].astype(np.float64)
                if f == 'clip':
                    value = (1+np.clip(sum(a*b)/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))/2
                elif f == 'hsv':
                    value = 1-np.sqrt(np.clip(1-sum(np.sqrt(a*b))/np.sqrt(sum(a)*sum(b)),0,1))
                else:
                    value = 1-.5*sum((a-b)**2/(a+b+1e-12))
                s[k,l] = value
        result[f] = float((sum(max(row) for row in s)/16 + sum(max(col) for col in s.T)/16)/2)
    a,b = arrays['motion'][i].astype(np.float64), arrays['motion'][j].astype(np.float64)
    result['motion'] = float(1-(.5*sum((a-b)**2/(a+b+1e-12)))/3)
    return result
