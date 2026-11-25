"""Opt-in actual OpenCV/scikit-image feature tests, no CLIP downloads."""
import os
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from PIL import Image

@unittest.skipUnless(os.environ.get('NHOM12_RUN_MEDIA_TESTS')=='1','Requires real extraction environment')
class RealFeatures(unittest.TestCase):
    def test_rgb_channel_order_and_hsv_bins(self):
        from nhom12.features import hsv_hist
        for rgb,bin_index in [((255,0,0),15),((0,255,0),47),((0,0,255),95),((0,0,0),0)]:
            x=hsv_hist(Image.new('RGB',(256,256),rgb))
            self.assertEqual(int(np.argmax(x)),bin_index)
            self.assertAlmostEqual(float(x[bin_index]),1)

    def test_uniform_lbp_flat_image(self):
        from nhom12.features import lbp_hist
        x=lbp_hist(Image.new('RGB',(256,256),(128,128,128)))
        self.assertEqual(x.shape,(10,))
        self.assertEqual(int(np.argmax(x)),8)

    def test_distance_matches_opencv_without_float32_self_error(self):
        import cv2
        from nhom12.search import distance
        rng=np.random.default_rng(42)
        a=rng.random(128).astype(np.float32);a/=a.sum()
        b=rng.random(128).astype(np.float32);b/=b.sum()
        self.assertLess(distance('hsv',a,a),1e-7)
        self.assertAlmostEqual(distance('hsv',a,b),cv2.compareHist(a,b,cv2.HISTCMP_BHATTACHARYYA),places=7)

    def test_no_motion_block_norms_and_direction_convention(self):
        from nhom12.features import motion_feature
        gray=np.full((180,320),128,dtype=np.uint8)
        x=motion_feature([(gray,gray,.25)]*8)
        np.testing.assert_allclose(x.reshape(3,8).sum(1),np.ones(3))
        self.assertEqual(float(x[0]),1)
        self.assertEqual(float(x[8]),1)
        np.testing.assert_allclose(x[16:],np.full(8,1/8))

if __name__=='__main__': unittest.main()
