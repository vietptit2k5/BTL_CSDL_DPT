"""Real feature pilot: two nature videos per class, no database/full build."""
import json
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'src'))
from nhom12.environment import configure_runtime
configure_runtime()
import numpy as np
from PIL import Image,ImageDraw
from nhom12.core import load_settings,sample_times,file_hash,digest,validate_vector
from nhom12.media import OpenCVBackend
from nhom12.features import FrameExtractor,motion_feature
from nhom12.preprocess import resize_short,content_box,square_for_clip
from nhom12.pipeline import model_identity,runtime_identity
from nhom12.search import distance

SAMPLES={'Sea':['SEA005','SEA016'],'Waterfall':['WAT001','WAT008'],
         'Forest':['FOR018','FOR015'],'Mountain':['MOU046','MOU023'],
         'River-Lake':['RIV001','RIV003'],'Flower':['FLO097','FLO114']}

def write_json(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def fit(image,size):
    im=image.copy().convert('RGB');im.thumbnail(size)
    panel=Image.new('RGB',size,'#eeeeee');panel.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2))
    return panel

def bars(vector,path,label):
    im=Image.new('RGB',(640,200),'white');d=ImageDraw.Draw(im);d.text((8,5),label,fill='black')
    maxv=max(float(max(vector)),1e-12);n=len(vector)
    for i,v in enumerate(vector):
        x0=10+i*620/n;x1=10+(i+1)*620/n
        d.rectangle((x0,185-float(v)/maxv*150,max(x0,x1-1),185),fill='#2469a0')
    im.save(path)

def main():
    spec,cfg=load_settings();sp=spec['sampling'];pre=spec['preprocess']
    output=root/'var/search_phases/02_features';output.mkdir(parents=True,exist_ok=True)
    backend=OpenCVBackend();encoder=FrameExtractor(spec,model_path=cfg['model_path'],device=cfg['device'],local_files_only=True)
    reports=[];arrays={};overview=Image.new('RGB',(1000,12*180),'white');draw=ImageDraw.Draw(overview)
    start=time.perf_counter()
    for folder,ids in SAMPLES.items():
        for vid in ids:
            t0=time.perf_counter();source=Path(cfg['dataset_root'])/folder/(vid+'.mp4');sha=file_hash(source)
            meta=backend.probe(source);targets=sample_times(meta['duration'],sp['k'],sp['margin'])
            decoded=backend.sample(source,targets,sp['decode_short_side'])
            box=content_box([im for pts,im in decoded],spec)
            prepared=[resize_short(im.crop(box),pre['feature_short_side']) for pts,im in decoded]
            vectors=encoder.extract(prepared)
            values={name:np.stack([r[name] for r in vectors]) for name in ('hsv','lbp','clip')}
            starts=sample_times(meta['duration']-sp['motion_dt'],sp['motion_pairs'],sp['margin'])
            a=backend.sample(source,starts,sp['motion_short_side'],gray=True)
            b=backend.sample(source,[t+sp['motion_dt'] for t in starts],sp['motion_short_side'],gray=True)
            ow,oh=decoded[0][1].size;mw,mh=a[0][1].size
            mb=tuple(round(v*s) for v,s in zip(box,(mw/ow,mh/oh,mw/ow,mh/oh)))
            pairs=[]
            for (ta,ia),(tb,ib) in zip(a,b,strict=True):
                pairs.append((np.asarray(ia.crop(mb)),np.asarray(ib.crop(mb)),tb-ta))
            values['motion']=motion_feature(pairs)
            values['target_times']=np.array(targets);values['actual_times']=np.array([p for p,im in decoded])
            values['motion_actual_dt']=np.array([dt for ga,gb,dt in pairs])
            for f in ('hsv','lbp','clip'):
                for x in values[f]: validate_vector(f,x)
            validate_vector('motion',values['motion'])
            assert sha==file_hash(source),'Source changed during pilot'
            directory=output/vid;directory.mkdir(exist_ok=True)
            np.savez_compressed(directory/'features.npz',**values)
            decoded[7][1].save(directory/'before.png');prepared[7].save(directory/'after.png')
            square_for_clip(prepared[7]).resize((224,224)).save(directory/'clip_letterbox.png')
            contact=Image.new('RGB',(4*240,4*160),'white');cd=ImageDraw.Draw(contact)
            for i,((pts,raw),im) in enumerate(zip(decoded,prepared,strict=True)):
                contact.paste(fit(im,(240,135)),((i%4)*240,(i//4)*160+25))
                cd.text(((i%4)*240+3,(i//4)*160+5),f'{i:02d}: target {targets[i]:.3f}s / PTS {pts:.3f}s',fill='black')
            contact.save(directory/'contact_sheet.jpg',quality=90)
            bars(values['hsv'][7],directory/'hsv.png',f'{vid}: HSV128 L1')
            bars(values['lbp'][7],directory/'lbp.png',f'{vid}: LBP10 L1')
            bars(values['motion'],directory/'motion.png',f'{vid}: flow 3 x 8; each block sum = 1')
            original_area=decoded[0][1].width*decoded[0][1].height
            report=dict(video_id=vid,class_folder=folder,path=str(source),sha256=sha,metadata=meta,
              crop=list(box),decode_size=list(decoded[0][1].size),feature_size=list(prepared[0].size),
              crop_removed_fraction=1-(box[2]-box[0])*(box[3]-box[1])/original_area,
              grayscale_mean=float(np.asarray(prepared[7].convert('L')).mean()),
              max_target_error=float(np.max(abs(values['target_times']-values['actual_times']))),
              motion_dt_range=[float(values['motion_actual_dt'].min()),float(values['motion_actual_dt'].max())],
              motion_blocks=values['motion'].reshape(3,8).sum(1).tolist(),
              dimensions={f:list(values[f].shape) for f in ('hsv','lbp','clip','motion')},
              norms={f:dict(min=float(np.linalg.norm(values[f],axis=1).min()) if f=='clip' else float(values[f].sum(1).min()),
                           max=float(np.linalg.norm(values[f],axis=1).max()) if f=='clip' else float(values[f].sum(1).max())) for f in ('hsv','lbp','clip')},
              self_distances={f:distance(f,values[f][7],values[f][7]) for f in ('hsv','lbp','clip')},
              seconds=time.perf_counter()-t0)
            write_json(directory/'validation.json',report)
            row=len(reports);draw.text((5,row*180+5),f'{vid} | {meta["fps"]:.3f} fps | crop {report["crop_removed_fraction"]:.1%}',fill='black')
            overview.paste(fit(decoded[7][1],(330,150)),(0,row*180+25))
            overview.paste(fit(prepared[7],(330,150)),(335,row*180+25))
            overview.paste(fit(square_for_clip(prepared[7]),(330,150)),(670,row*180+25))
            reports.append(report);arrays[vid]=values
            print(f'{vid} passed: {meta["fps"]:.3f}fps, crop={report["crop_removed_fraction"]:.1%}, {report["seconds"]:.1f}s',flush=True)
    overview.save(output/'overview.jpg',quality=92)
    pairs=[('SEA005','SEA016'),('SEA005','FLO097'),('FOR018','FOR015'),('RIV001','RIV003')]
    comparison=[dict(a=a,b=b,distances={f:distance(f,arrays[a][f][7],arrays[b][f][7]) for f in ('hsv','lbp','clip')},
                     motion_chi_square=distance('motion',arrays[a]['motion'],arrays[b]['motion'])) for a,b in pairs]
    summary=dict(status='passed',sample_count=len(reports),keyframe_count=len(reports)*16,
       frame_vector_count=len(reports)*16*3,motion_vector_count=len(reports),spec_hash=digest(spec),
       model_identity=model_identity(cfg),device=cfg['device'],packages=runtime_identity(),
       elapsed_seconds=time.perf_counter()-start,videos=reports,pair_comparisons=comparison,
       limitations=['Pilot only, not a full dataset index or retrieval-quality evaluation','Scene/duplicate/logo judgments not inferred from feature validity'])
    write_json(output/'validation.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('videos','pair_comparisons')},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
