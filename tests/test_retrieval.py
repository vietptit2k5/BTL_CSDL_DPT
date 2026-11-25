import unittest
import numpy as np
from nhom12.core import ContractError
from nhom12.retrieval import ExactFrameIndex
from nhom12.search import rank


class MatrixRetrieval(unittest.TestCase):
    def test_matches_scalar_for_random_queries_all_weights_and_ties(self):
        rng = np.random.default_rng(1204)
        def vector():
            clip = rng.normal(size=512).astype(np.float32); clip /= np.linalg.norm(clip)
            return dict(hsv=rng.dirichlet(np.ones(128)).astype(np.float32),
                        lbp=rng.dirichlet(np.ones(10)).astype(np.float32), clip=clip)
        frames = [dict(video_id=f'V{v:02}', index=i, time=float(i), image_path='fixture', features=vector())
                  for v in range(12) for i in range(16)]
        # Exact duplicate vectors and video ties must retain ID and frame-index ordering.
        for f in frames[:20]: f['features'] = frames[25]['features']
        index = ExactFrameIndex(frames)
        for weights in [dict(clip=.9,hsv=.1,lbp=0),dict(clip=0,hsv=1,lbp=0),
                        dict(clip=0,hsv=0,lbp=1),dict(clip=.3,hsv=.3,lbp=.4)]:
            for q in [vector(), frames[25]['features']]:
                self.assertEqual(index.rank(q, weights), rank(q, frames, weights))
                self.assertEqual(index.last_statistics['scanned_frames'], len(frames))

    def test_rejects_bad_vector_and_duplicate_frame(self):
        feature={n:np.eye(1,d,dtype=np.float32).ravel() for n,d in [('hsv',128),('lbp',10),('clip',512)]}
        frames=[dict(video_id=f'V{i}',index=0,time=0,image_path='fixture',features=feature) for i in range(6)]
        with self.assertRaises(ContractError): ExactFrameIndex(frames+[frames[0]])
        bad={**feature,'clip':np.zeros(512)}
        with self.assertRaises(ContractError): ExactFrameIndex(frames).rank(bad,dict(clip=.9,hsv=.1,lbp=0))

    def test_common_frame_fusion(self):
        def one(index, dim): return np.eye(1,dim,index,dtype=np.float32).ravel()
        query=dict(hsv=one(0,128),lbp=one(0,10),clip=one(0,512))
        frames=[]
        for v in range(6):
            for i in range(2):
                f=dict(query)
                if v==0: f['hsv' if i==0 else 'clip']=one(1,128 if i==0 else 512)
                frames.append(dict(video_id=f'V{v}',index=i,time=float(i),image_path='fixture',features=f))
        self.assertEqual(ExactFrameIndex(frames).rank(query,dict(clip=.5,hsv=.5,lbp=0)),
                         rank(query,frames,dict(clip=.5,hsv=.5,lbp=0)))
