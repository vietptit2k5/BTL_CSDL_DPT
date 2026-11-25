"""Recovery tests use explicit synthetic adapters; full-build evidence is separate."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nhom12.core import ContractError,load_settings
from nhom12.pipeline import build,query_image
from nhom12 import repository as db
from test_pipeline import FakeMedia,FakeExtractor

class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);sources=root/'sources';sources.mkdir()
        self.spec,self.cfg=load_settings();self.spec['dataset']['minimum_videos']=6
        self.cfg['database']={'backend':'sqlite'}
        for folder,code in self.spec['classes'].items():
            (sources/folder).mkdir();(sources/folder/f'{code}001.mp4').write_bytes(b'fixture')
        model=root/'model';model.mkdir();(model/'config.json').write_text('{}')
        self.cfg.update(dataset_root=str(sources),artifacts=str(root/'artifacts'),model_path=str(model))
        for target,value in [('nhom12.media.OpenCVBackend',FakeMedia),('nhom12.features.FrameExtractor',FakeExtractor),
                             ('nhom12.features.motion_feature',lambda pairs:np.full(24,1/8)),('nhom12.pipeline.runtime_identity',lambda:{'fixture':'1'})]:
            p=patch(target,value);p.start();self.addCleanup(p.stop)

    def test_pause_resume_and_pending_reviews(self):
        partial=build(self.spec,self.cfg,stop_after=2)
        con=db.connect(partial,readonly=True)
        self.assertEqual(con.execute('SELECT count(*) FROM videos').fetchone()[0],2)
        self.assertEqual(con.execute('SELECT status FROM build').fetchone()[0],'building');con.close()
        index=build(self.spec,self.cfg,resume=partial)
        con=db.connect(index,readonly=True)
        self.assertEqual(con.execute('SELECT count(*) FROM videos').fetchone()[0],6)
        self.assertEqual(con.execute('SELECT quality_status FROM build').fetchone()[0],'pending')
        flags=json.loads(con.execute('SELECT quality_json FROM videos LIMIT 1').fetchone()[0])
        self.assertIsNone(flags['single_scene']);con.close()
        progress=json.loads(Path(index).with_name('progress.json').read_text())
        self.assertEqual(progress['reused'],2)

    def test_vector_error_rolls_back_every_table(self):
        from nhom12.core import inventory
        row=inventory(self.cfg['dataset_root'],self.spec)[0]
        con=db.create(Path(self.tmp.name)/'rollback.sqlite',dict(spec_hash='fixture',snapshot=[row],model_identity='fixture',created_at='test'))
        features=FakeExtractor().extract([None]*16)
        features[5]['clip']=np.zeros(512,dtype=np.float32)
        frames=[dict(index=i,target=float(i),actual=float(i),image_path='fixture.png',features=f) for i,f in enumerate(features)]
        with self.assertRaises(ContractError):
            db.add_video(con,row,{},[0,0,1,1],{},frames,np.full(24,1/8),{})
        for table in ('videos','keyframes','frame_features','video_features','video_artifacts'):
            self.assertEqual(con.execute(f'SELECT count(*) FROM {table}').fetchone()[0],0)
        con.close()

    def test_changed_source_rejects_resume_even_same_byte_count(self):
        partial=build(self.spec,self.cfg,stop_after=1)
        source=Path(self.cfg['dataset_root'])/'Sea/SEA001.mp4';source.write_bytes(b'changed')
        with self.assertRaisesRegex(ContractError,'Resume rejected'):
            build(self.spec,self.cfg,resume=partial)

    def test_failed_video_transaction_can_resume(self):
        calls=[]
        class FailOnce(FakeExtractor):
            def extract(self,images):
                calls.append(1)
                if len(calls)==3: raise RuntimeError('simulated interruption')
                return super().extract(images)
        with patch('nhom12.features.FrameExtractor',FailOnce):
            with self.assertRaisesRegex(RuntimeError,'simulated interruption'): build(self.spec,self.cfg)
            run=next(Path(self.cfg['artifacts']).glob('build-*'))
            con=db.connect(run/'index.building.sqlite',readonly=True)
            self.assertEqual(con.execute('SELECT status FROM build').fetchone()[0],'failed')
            self.assertEqual(con.execute('SELECT count(*) FROM videos').fetchone()[0],2);con.close()
            index=build(self.spec,self.cfg,resume=run)
            self.assertTrue(Path(index).is_file())
            self.assertEqual(json.loads((run/'progress.json').read_text())['reused'],2)

    def test_corrupted_artifact_is_rebuilt(self):
        partial=build(self.spec,self.cfg,stop_after=1)
        con=db.connect(partial,readonly=True)
        frame=con.execute('SELECT image_path FROM keyframes LIMIT 1').fetchone()[0];con.close()
        Path(frame).write_bytes(b'corrupt')
        index=build(self.spec,self.cfg,resume=partial)
        con=db.connect(index,readonly=True)
        frame2=con.execute('SELECT image_path FROM keyframes ORDER BY video_id,frame_index LIMIT 1').fetchone()[0];con.close()
        self.assertNotEqual(frame,frame2)
        self.assertEqual(json.loads(Path(index).with_name('progress.json').read_text())['reused'],0)
