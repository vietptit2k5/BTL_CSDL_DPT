import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nhom12.core import ContractError,assert_snapshot,sample_times,validate_vector
from nhom12.search import rank
from nhom12.evaluation import evaluate
from nhom12 import repository as db

def ff(which=0):
    return {name:np.eye(1,dim,which,dtype=np.float32).ravel() for name,dim in [('hsv',128),('lbp',10),('clip',512)]}

class Contracts(unittest.TestCase):
    def test_stale_same_size_changed_content(self):
        with self.assertRaises(ContractError):
            assert_snapshot([{'video_id':'SEA001','size':10,'sha256':'a'}],[{'video_id':'SEA001','size':10,'sha256':'b'}])

    def test_timing_and_motion_normalization(self):
        ts=sample_times(4)
        self.assertEqual(len(ts),16)
        self.assertAlmostEqual(ts[0],.3125)
        validate_vector('motion',np.full(24,1/8))
        with self.assertRaises(ContractError):
            validate_vector('motion',np.full(24,1/24))

    def test_top5_common_frame_unique_and_descending(self):
        frames=[dict(video_id=f'V{i}',index=0,time=.5,image_path='f.png',features=ff(0 if i==0 else 1)) for i in range(6)]
        frames.append(dict(video_id='V0',index=1,time=1,image_path='g.png',features=ff(1)))
        hits=rank(ff(),frames,dict(clip=.9,hsv=.1,lbp=0))
        self.assertEqual(len({h['video_id'] for h in hits}),5)
        self.assertEqual(hits[0]['video_id'],'V0')
        self.assertEqual(hits[0]['frame_index'],0)
        self.assertEqual([h['score'] for h in hits],sorted((h['score'] for h in hits),reverse=True))
        self.assertAlmostEqual(sum(hits[0]['contributions'].values()),hits[0]['score'])

    def test_missing_vector_is_not_zero_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            row=dict(video_id='SEA001',class_code='SEA',relative_path='Sea/SEA001.mp4',sha256='x',size_bytes=1)
            con=db.create(Path(tmp)/'test.sqlite',dict(spec_hash='s',snapshot=[row],model_identity='m',created_at='now'))
            frames=[dict(index=i,target=i,actual=i,image_path='x',features=ff()) for i in range(16)]
            db.add_video(con,row,{},[0,0,1,1],{},frames,np.full(24,1/8))
            db.validate_complete(con,[row])
            con.execute("DELETE FROM frame_features WHERE frame_index=0 AND feature='clip'")
            with self.assertRaises(ContractError):
                db.validate_complete(con,[row])
            con.close()

    def test_test_split_and_empty_relevance(self):
        ranks={'q':['a','b','c','d','e']}
        result=evaluate(ranks,{'q':['a','z']},{'q':'test'})[0]
        self.assertEqual(result['precision_at_5'],.2)
        self.assertEqual(result['recall_at_5'],.5)
        with self.assertRaises(ContractError):
            evaluate(ranks,{'q':['a']},{'q':'validation'})

if __name__=='__main__':
    unittest.main()
