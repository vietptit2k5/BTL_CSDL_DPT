"""Reproduce the known ND2 border-crop limitation without changing preprocessing."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import load_settings
from nhom12.preprocess import content_box,resize_short,prepare_image
spec,cfg=load_settings();out=ROOT/'var/completion/crop';out.mkdir(parents=True,exist_ok=True)
report=[]
for level in (8,15,30):
    pixels=np.full((720,1280,3),128,dtype=np.uint8);pixels[:302]=level
    image=Image.fromarray(pixels);decoded=resize_short(image,360);box=content_box([decoded],spec)
    image.save(out/f'before_{level}.png');prepare_image(image,spec,box).save(out/f'after_{level}.png')
    report.append(dict(top_gray=level,top_fraction=302/720,crop_box=box,decoded_size=decoded.size,
                       removed_top_pixels=box[1],kind='synthetic technical limitation, not a relevance test'))
(out/'report.json').write_text(json.dumps(dict(cases=report,preprocessing_changed=False),indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
