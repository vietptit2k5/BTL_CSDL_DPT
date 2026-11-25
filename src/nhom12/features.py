"""Report §§2.3–2.6. Real extractors, imported lazily; no placeholder vectors."""
import numpy as np
from .core import ContractError,validate_vector
from .preprocess import square_for_clip

def hsv_hist(image):
    import cv2
    hsv=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2HSV).astype(np.int32)
    bins=(hsv[...,0]*8//180)*16+(hsv[...,1]*4//256)*4+hsv[...,2]*4//256
    hist=np.bincount(bins.ravel(),minlength=128).astype(np.float32)
    return validate_vector('hsv',hist/hist.sum())

def lbp_hist(image):
    import cv2
    from skimage.feature import local_binary_pattern
    gray=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2GRAY)
    codes=local_binary_pattern(gray,8,1,method='uniform')[1:-1,1:-1].astype(np.int32)
    if not codes.size:
        raise ContractError('Image too small for LBP')
    hist=np.bincount(codes.ravel(),minlength=10).astype(np.float32)
    return validate_vector('lbp',hist/hist.sum())

class FrameExtractor:
    def __init__(self,spec,model_path=None,revision=None,device='cpu',local_files_only=True):
        import torch
        from transformers import CLIPModel,CLIPProcessor
        self.torch=torch;self.device=device
        checkpoint=model_path or spec['features']['clip_checkpoint']
        kwargs=dict(local_files_only=local_files_only)
        if revision and not model_path: kwargs['revision']=revision
        self.model=CLIPModel.from_pretrained(checkpoint,**kwargs).to(device).eval()
        vision=self.model.config.vision_config
        if (self.model.config.projection_dim,vision.patch_size,vision.hidden_size,vision.num_hidden_layers)!=(512,32,768,12):
            raise ContractError('Local checkpoint is not the reported CLIP ViT-B/32 architecture')
        self.processor=CLIPProcessor.from_pretrained(checkpoint,**kwargs)
        if device.startswith('cuda'): self.model=self.model.half()

    def extract(self,images):
        """Input already cropped and short256. CLIP processor resizes square to224."""
        if not images: return []
        result=[]
        for start in range(0,len(images),32):
            group=images[start:start+32]
            pixels=self.processor(images=[square_for_clip(im) for im in group],return_tensors='pt')['pixel_values'].to(self.device)
            if self.device.startswith('cuda'): pixels=pixels.half()
            with self.torch.no_grad():
                # Explicit projection is consistent across Transformers 4/5:
                # get_image_features changed its return container in version 5.
                vision_output=self.model.vision_model(pixel_values=pixels,return_dict=True)
                vectors=self.model.visual_projection(vision_output.pooler_output)
            if not isinstance(vectors,self.torch.Tensor) or vectors.shape!=(len(group),512):
                raise ContractError('CLIP must return projected 512-dimensional image features')
            vectors=vectors.float().cpu().numpy()
            for im,vector in zip(group,vectors,strict=True):
                norm=np.linalg.norm(vector)
                if norm<=0: raise ContractError('Zero CLIP vector')
                result.append(dict(hsv=hsv_hist(im),lbp=lbp_hist(im),clip=validate_vector('clip',vector/norm)))
        return result

def motion_feature(pairs):
    """Table2.7: each block sum1. Uniform direction if no moving pixels (decision)."""
    import cv2
    if len(pairs)!=8: raise ContractError('Report requires exactly eight motion pairs')
    edges=np.array([0,.01,.02,.04,.08,.16,.32,.64,np.inf])
    a,b,c=(np.zeros(8,dtype=np.float64) for _ in range(3))
    for ga,gb,dt in pairs:
        if ga.ndim!=2 or ga.shape!=gb.shape or min(ga.shape)<=1 or not np.isfinite(dt) or dt<=0:
            raise ContractError('Motion requires equally sized grayscale frames and positive dt')
        flow=cv2.calcOpticalFlowFarneback(ga,gb,None,.5,3,15,3,5,1.2,0)
        scale=min(ga.shape)*dt
        mag=np.linalg.norm(flow,axis=2)/scale
        residual=flow-np.median(flow.reshape(-1,2),axis=0)
        rmag=np.linalg.norm(residual,axis=2)/scale
        a+=np.histogram(mag,edges)[0];b+=np.histogram(rmag,edges)[0]
        angle=(np.arctan2(-residual[...,1],residual[...,0])%(2*np.pi))*8/(2*np.pi)
        keep=rmag>=.01
        c+=np.bincount(angle[keep].astype(int)%8,weights=rmag[keep],minlength=8)
    parts=[part/part.sum() if part.sum()>0 else np.full(8,1/8) for part in (a,b,c)]
    return validate_vector('motion',np.concatenate(parts))
