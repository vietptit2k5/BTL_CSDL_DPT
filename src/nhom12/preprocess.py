"""Report §2.1.3: shared preprocessing for video keyframes and query images."""
import numpy as np
from PIL import Image
from .core import ContractError

def resize_short(image, side):
    w,h=image.size
    if min(w,h)<=0 or side<=0:
        raise ContractError('Invalid image dimensions')
    size=(round(w*side/min(w,h)),round(h*side/min(w,h)))
    method=Image.Resampling.BOX if min(w,h)>side else Image.Resampling.BICUBIC
    return image.resize(size,method)

def content_box(images,spec):
    if not images or len({im.size for im in images})!=1:
        raise ContractError('Crop requires nonempty, equally sized frames')
    p=spec['preprocess']
    g=np.max(np.stack([np.asarray(im.convert('L'),dtype=np.float32) for im in images]),axis=0)
    h,w=g.shape
    row=(np.percentile(g,p['percentile'],axis=1)>=p['border_threshold']) & (g.mean(axis=1)>=p['mean_threshold'])
    col=(np.percentile(g,p['percentile'],axis=0)>=p['border_threshold']) & (g.mean(axis=0)>=p['mean_threshold'])
    if not row.any() or not col.any():
        return (0,0,w,h)
    y0,y1=int(np.argmax(row)),int(h-np.argmax(row[::-1]))
    x0,x1=int(np.argmax(col)),int(w-np.argmax(col[::-1]))
    if y0<h*p['min_border_fraction']: y0=0
    if h-y1<h*p['min_border_fraction']: y1=h
    if x0<w*p['min_border_fraction']: x0=0
    if w-x1<w*p['min_border_fraction']: x1=w
    if (x1-x0)*(y1-y0)<w*h*p['min_keep_area']:
        return (0,0,w,h)
    return (x0,y0,x1,y1)

def prepare_image(image,spec,box=None):
    image=resize_short(image.convert('RGB'),spec['sampling']['decode_short_side'])
    box=box or content_box([image],spec)
    return resize_short(image.crop(box),spec['preprocess']['feature_short_side'])

def square_for_clip(image):
    image=image.convert('RGB')
    w,h=image.size;s=max(w,h)
    square=Image.new('RGB',(s,s),(0,0,0))
    square.paste(image,((s-w)//2,(s-h)//2))
    return square
