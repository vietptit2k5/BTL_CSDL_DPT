"""Course 7/8: exhaustive vector comparison; reference formulas remain authoritative."""
import math
import numpy as np
from .core import ContractError, validate_vector
from .search import rank as reference_rank


class ExactFrameIndex:
    """Scan every frame in float64, then refine all videos near the top-five boundary.

    The 1e-5 safety band covers roundoff including sqrt at HSV distance zero.
    No approximate-neighbour index, semantic class filter, or feature omission.
    The final scores/evidence use the original scalar formulas on every frame of
    every candidate video; ties therefore preserve the original ID/frame policy.
    """
    def __init__(self, frames):
        self.frames = frames
        self.ids = sorted({f['video_id'] for f in frames})
        if len(self.ids) < 5:
            raise ContractError('Need at least five indexed videos')
        if len({(f['video_id'], f['index']) for f in frames}) != len(frames):
            raise ContractError('Duplicate indexed frame')
        self.positions = {vid: [] for vid in self.ids}
        for i, frame in enumerate(frames):
            self.positions[frame['video_id']].append(i)
        self.matrix = {name: np.stack([validate_vector(name, f['features'][name]) for f in frames]).astype(np.float64)
                       for name in ('hsv', 'lbp', 'clip')}
        self.hsv_sqrt = np.sqrt(self.matrix['hsv'])
        self.hsv_sums = self.matrix['hsv'].sum(axis=1)
        self.clip_norms = np.linalg.norm(self.matrix['clip'], axis=1)
        for value in (*self.matrix.values(), self.hsv_sqrt, self.hsv_sums, self.clip_norms):
            value.flags.writeable = False
        self.last_statistics = {}

    def rank(self, query, weights, top_k=5):
        if top_k != 5 or set(weights) != {'hsv', 'lbp', 'clip'} or not all(math.isfinite(w) and w >= 0 for w in weights.values()) or not math.isclose(sum(weights.values()), 1):
            raise ContractError('Invalid top5 search policy')
        q = {name: validate_vector(name, query[name]).astype(np.float64) for name in self.matrix}
        cosine = (self.matrix['clip'] @ q['clip']) / (self.clip_norms * np.linalg.norm(q['clip']))
        clip_distance = np.clip(1-cosine, 0, 2)
        coefficient = (self.hsv_sqrt @ np.sqrt(q['hsv'])) / np.sqrt(self.hsv_sums * q['hsv'].sum())
        hsv_distance = np.sqrt(np.clip(1-coefficient, 0, 1))
        lbp_distance = .5 * np.sum((self.matrix['lbp']-q['lbp'])**2 / (self.matrix['lbp']+q['lbp']+1e-12), axis=1)
        scores = weights['clip']*(1-clip_distance/2) + weights['hsv']*(1-hsv_distance) + weights['lbp']*(1-lbp_distance)
        video_scores = {vid: float(scores[indexes].max()) for vid, indexes in self.positions.items()}
        boundary = sorted(video_scores.values(), reverse=True)[4]
        candidates = {vid for vid, score in video_scores.items() if score >= boundary-1e-5}
        selected = [frame for frame in self.frames if frame['video_id'] in candidates]
        self.last_statistics = dict(algorithm='exhaustive_float64_matrix_then_scalar_refinement',
                                    scanned_frames=len(self.frames), indexed_videos=len(self.ids),
                                    refinement_videos=len(candidates), refinement_frames=len(selected),
                                    roundoff_safety_band=1e-5, approximate_nearest_neighbor=False)
        return reference_rank(query, selected, weights, top_k)
