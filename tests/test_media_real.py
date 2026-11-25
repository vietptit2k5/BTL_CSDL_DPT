"""Opt-in integration tests with actual FFmpeg/OpenCV, not mocked PTS."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'));sys.path.insert(0,str(root/'scripts'))

@unittest.skipUnless(os.environ.get('NHOM12_RUN_MEDIA_TESTS')=='1','Requires real extraction environment')
class RealMedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from nhom12.environment import configure_runtime
        configure_runtime()
        from create_media_fixtures import create_fixtures
        from nhom12.media import OpenCVBackend
        cls.files=create_fixtures(root/'var/search_phases/02_features/fixtures')
        cls.backend=OpenCVBackend()

    def test_vfr_uses_nearest_actual_pts(self):
        import numpy as np
        p=self.files['vfr']
        output=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(p)],capture_output=True,text=True,check=True)
        pts=np.array([float(f['best_effort_timestamp_time']) for f in json.loads(output.stdout)['frames']])
        self.assertGreater(np.ptp(np.diff(pts)),.01)
        targets=[.05,.15,.91,1.02,1.53,2.89]
        samples=self.backend.sample(p,targets,180)
        for target,(actual,im) in zip(targets,samples,strict=True):
            self.assertAlmostEqual(abs(actual-target),float(np.min(abs(pts-target))),places=5)

    def test_rotation_decodes_as_portrait(self):
        meta=self.backend.probe(self.files['rotated'])
        self.assertTrue(meta['rotation'])
        _,im=self.backend.sample(self.files['rotated'],[1],180)[0]
        self.assertEqual(im.size,(180,320))

    def test_mixed_one_pass_matches_individual_requests(self):
        import numpy as np
        p=self.files['vfr']
        requests=[(.31,360,False),(1.08,180,True),(1.31,180,True),(2.43,360,False)]
        together=self.backend.sample_many(p,requests)
        for (target,side,gray),(pts,image) in zip(requests,together,strict=True):
            separate=self.backend.sample(p,[target],side,gray)[0]
            self.assertEqual(pts,separate[0])
            np.testing.assert_array_equal(np.asarray(image),np.asarray(separate[1]))

    def test_invalid_timestamps_rejected(self):
        from nhom12.core import ContractError
        with self.assertRaises(ContractError): self.backend.sample(self.files['landscape'],[float('nan')],180)

if __name__=='__main__': unittest.main()
