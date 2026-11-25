"""Real FFprobe/OpenCV/CLIP smoke test, with reproducible offline evidence."""
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from nhom12.environment import configure_runtime
configure_runtime()
import numpy as np
import torch
from nhom12.core import load_settings,digest,file_hash
from nhom12.pipeline import model_identity,runtime_identity
from nhom12.media import OpenCVBackend
from nhom12.features import FrameExtractor
from nhom12.preprocess import prepare_image

spec,cfg=load_settings()
out=root/'var/search_phases/01_environment';out.mkdir(parents=True,exist_ok=True)
backend=OpenCVBackend();source=Path(cfg['dataset_root'])/'Sea/SEA005.mp4'
started=time.perf_counter();meta=backend.probe(source)
pts,image=backend.sample(source,[meta['duration']/2],360)[0]
pre=prepare_image(image,spec)
image.save(out/'source_frame.png');pre.save(out/'preprocessed.png')
extractor=FrameExtractor(spec,model_path=cfg['model_path'],device=cfg['device'],local_files_only=True)
features=extractor.extract([pre])[0]
np.savez_compressed(out/'real_image_features.npz',**features)
result=dict(status='passed',python=sys.version,executable=sys.executable,platform=platform.platform(),
            packages=runtime_identity(),cuda_available=torch.cuda.is_available(),
            gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            device=cfg['device'],model_identity=model_identity(cfg),spec_hash=digest(spec),
            video=str(source),source_sha256=file_hash(source),metadata=meta,actual_pts=pts,
            elapsed_seconds=time.perf_counter()-started,
            features={f:dict(shape=list(x.shape),dtype=str(x.dtype),finite=bool(np.isfinite(x).all()),
                          l2=float(np.linalg.norm(x)),sum=float(x.sum())) for f,x in features.items()},
            binaries={name:subprocess.run([name,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0] for name in ('ffmpeg','ffprobe')},
            report_sources={p.name:file_hash(p) for p in Path(cfg['dataset_root']).iterdir() if p.suffix in ('.docx','.xlsx') or p.name=='[D23-lớp 04] - Nhóm 12.pdf'})
(out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
