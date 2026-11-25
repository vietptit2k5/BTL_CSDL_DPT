import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nhom12.core import load_settings
from nhom12.preprocess import content_box,prepare_image,square_for_clip

class PreprocessTests(unittest.TestCase):
    def setUp(self): self.spec,_=load_settings()

    def test_shared_crop_and_preserved_aspect(self):
        frame=np.zeros((100,200,3),dtype=np.uint8)
        frame[10:90]=180
        image=Image.fromarray(frame)
        self.assertEqual(content_box([image,image],self.spec),(0,10,200,90))
        result=prepare_image(image,self.spec)
        self.assertEqual(min(result.size),256)
        # Resampling blends the border by about one pixel before thresholding.
        self.assertAlmostEqual(result.width/result.height,2.5,delta=.02)

    def test_brightest_composite_preserves_dark_natural_region(self):
        dark=Image.new('RGB',(100,100),0)
        bright=Image.new('RGB',(100,100),128)
        self.assertEqual(content_box([dark,bright],self.spec),(0,0,100,100))
        self.assertEqual(content_box([dark],self.spec),(0,0,100,100))

    def test_letterbox_retains_portrait_content(self):
        result=square_for_clip(Image.new('RGB',(40,100),'red'))
        self.assertEqual(result.size,(100,100))
        self.assertEqual(result.getpixel((0,50)),(0,0,0))
        self.assertEqual(result.getpixel((50,0)),(255,0,0))

if __name__=='__main__': unittest.main()
