"""Integration with synthetic media adapters; does not claim real CLIP inference."""
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nhom12.core import ContractError,inventory,load_settings
from nhom12.pipeline import build,query_image

class FakeMedia:
    def probe(self,path):
        return dict(duration=10,width=100,height=100,fps=30,codec='h264')
    def sample(self,path,times,short_side,gray=False):
        return [(t,Image.new('L' if gray else 'RGB',(short_side,short_side),128)) for t in times]

class FakeExtractor:
    def __init__(self,*a,**kw): pass
    def extract(self,images):
        return [{f:np.eye(1,n,dtype=np.float32).ravel() for f,n in [('hsv',128),('lbp',10),('clip',512)]} for _ in images]

class PipelineTest(unittest.TestCase):
    def test_build_query_trace_and_invalidate(self):
        spec,cfg=load_settings()
        cfg['database']={'backend':'sqlite'}
        # Small synthetic fixture only; real contract still enforces >=500.
        spec['dataset']['minimum_videos']=6
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'sources';root.mkdir()
            for folder,code in spec['classes'].items():
                (root/folder).mkdir();(root/folder/f'{code}001.mp4').write_bytes(b'fixture')
            model=Path(tmp)/'model';model.mkdir();(model/'config.json').write_text('{}')
            cfg.update(dataset_root=str(root),artifacts=str(Path(tmp)/'artifacts'),model_path=str(model))
            rows=inventory(root,spec)
            reviews={r['video_id']:dict(sha256=r['sha256'],single_scene=True,not_duplicate=True,no_large_logo=True) for r in rows}
            review_path=Path(tmp)/'reviews.json';review_path.write_text(json.dumps(reviews))
            image=Path(tmp)/'image.png';Image.new('RGB',(80,120),128).save(image)
            with patch('nhom12.media.OpenCVBackend',FakeMedia),patch('nhom12.features.FrameExtractor',FakeExtractor),\
                 patch('nhom12.features.motion_feature',return_value=np.full(24,1/8)),\
                 patch('nhom12.pipeline.runtime_identity',return_value={'fixture':'1'}):
                index=build(spec,cfg,review_path)
                self.assertTrue(Path(index).is_file())
                output=query_image(spec,cfg,index,image)
                self.assertTrue(Path(output).is_file())
                trace=json.loads(Path(output).with_name('trace.json').read_text(encoding='utf-8'))
                self.assertEqual(len({r['video_id'] for r in trace['hits']}),5)
                self.assertEqual(len(trace['query_features']['clip']),512)
                p=root/rows[0]['relative_path'];p.write_bytes(b'changed')
                with self.assertRaises(ContractError): query_image(spec,cfg,index,image)

if __name__=='__main__': unittest.main()
