"""Read-only import and faithful replay of s01/s04 of the original ND1 system.

Eight pixel color groups -> argmax -> original five dominant_group values.
The ND1 decoder and CV2 resizing are deliberately separate from the ND2 index.
"""
import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image
from ..core import ContractError, digest, file_hash, sample_times
from ..preprocess import content_box, resize_short
from .data import load_snapshot
from .files import read_csv, read_json, seal, verify, write_csv, write_json
from .nd1 import categorize, color_fractions

COLORS=('do_cam','vang','xanh_luc','xanh_duong','tim_hong','trang','xam','toi')
GROUP5=dict(do_cam='mau_am',vang='mau_am',xanh_luc='xanh_luc',xanh_duong='xanh_duong',
            tim_hong='mau_am',trang='trang_xam',xam='trang_xam',toi='toi')
SOURCE_FILES=('scripts/s01_cache_frames.py','scripts/s04_ch1_stats.py','src/common.py','config.yaml',
              'outputs/ch1_stats.json','outputs/metadata.csv','outputs/manifest.csv')


def archive_original(run,legacy_root):
    source=Path(legacy_root);folder=run/'nd1_sources'
    if (folder/'files.json').exists():
        verify(folder)
        expected=read_json(folder/'origin.json')
        for name,sha in expected['hashes'].items():
            if file_hash(source/name)!=sha:raise ContractError('Original ND1 source changed since import')
        return folder
    folder.mkdir(exist_ok=True)
    hashes={}
    for name in SOURCE_FILES:
        sha=file_hash(source/name);dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,dest);hashes[name]=sha
    write_json(folder/'origin.json',dict(legacy_root=str(source),hashes=hashes,
               source_identity='Original manifest has sizes, not historical video SHA256. Cached-frame hashes are separately compared.'))
    seal(folder);return folder


def pixel_hash(array):
    array=np.ascontiguousarray(array)
    return hashlib.sha256(str(array.shape).encode()+array.tobytes()).hexdigest()


def decode_original(path,duration):
    """Port of original s01 process/save; strict '<' tie and CV2 INTER_AREA retained."""
    import cv2
    targets=[(t,f'f{i:02d}',360,False) for i,t in enumerate(sample_times(duration))]
    starts=sample_times(duration-.25,8)
    targets += [(t,f'm{i:02d}a',180,True) for i,t in enumerate(starts)]
    targets += [(t+.25,f'm{i:02d}b',180,True) for i,t in enumerate(starts)]
    targets.sort();cap=cv2.VideoCapture(str(path));previous=None;ti=0;images={};pts={}
    def save(target,frame,timestamp):
        t,name,side,gray=target
        source=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY) if gray else frame
        h,w=source.shape[:2];size=(side,round(h*side/w)) if w<=h else (round(w*side/h),side)
        image=cv2.resize(source,size,interpolation=cv2.INTER_AREA)
        images[name]=image if gray else cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
        pts[name]=float(timestamp)
    try:
        if not cap.isOpened():raise ContractError(f'Cannot decode ND1 video: {path}')
        while ti<len(targets):
            if not cap.grab():break
            ts=cap.get(cv2.CAP_PROP_POS_MSEC)/1000
            while ti<len(targets) and ts>=targets[ti][0]:
                ok,frame=cap.retrieve()
                if not ok:raise ContractError('ND1 frame retrieve failed')
                use=(ts,frame)
                if previous is not None and abs(previous[0]-targets[ti][0])<abs(ts-targets[ti][0]):use=previous
                save(targets[ti],use[1],use[0]);ti+=1
            if ti<len(targets) and targets[ti][0]-ts<.2:
                ok,frame=cap.retrieve()
                if not ok:raise ContractError('ND1 previous-frame retrieve failed')
                previous=(ts,frame)
        if ti<len(targets) and previous is not None:
            for target in targets[ti:]:save(target,previous[1],previous[0])
            ti=len(targets)
    finally:cap.release()
    if ti!=len(targets) or len(images)!=32:raise ContractError('ND1 decoder did not produce all 32 frames')
    return images,pts


def measure(images,spec,thresholds):
    import cv2
    keyframes=[Image.fromarray(images[f'f{i:02d}']).convert('RGB') for i in range(16)]
    box=content_box(keyframes,spec)
    prepared=[resize_short(im.crop(box),256) for im in keyframes]
    # Original s04 order matters for exact argmax ties.
    shares=np.mean([color_fractions(im)[[3,2,1,0,4,5,6,7]] for im in prepared],axis=0)
    dominant=COLORS[int(np.argmax(shares))]
    gray=[cv2.cvtColor(np.asarray(im),cv2.COLOR_RGB2GRAY) for im in prepared]
    edges=[float((cv2.Canny(g,100,200)>0).mean()) for g in gray]
    motion_box=tuple(int(round(c*.5)) for c in box)
    diffs=[]
    for i in range(8):
        a=np.asarray(Image.fromarray(images[f'm{i:02d}a']).crop(motion_box),dtype=np.float32)
        b=np.asarray(Image.fromarray(images[f'm{i:02d}b']).crop(motion_box),dtype=np.float32)
        diffs.append(np.abs(a-b).mean())
    edge=float(np.mean(edges));motion=float(np.mean(diffs))
    return dict(d1=GROUP5[dominant],dominant_color=dominant,dominant_group=GROUP5[dominant],
                d2=categorize(edge,*thresholds['edge'],('min','trung_binh','day')),
                d5=categorize(motion,*thresholds['motion'],('tinh','nhe','manh')),
                edge_density=edge,motion_index=motion,brightness=float(np.mean([g.mean() for g in gray])),
                crop=list(box),per_frame_edge=edges,per_pair_difference=[float(v) for v in diffs],
                **{f'fraction_{c}':float(v) for c,v in zip(COLORS,shares,strict=True)})


def load_old_images(root,vid):
    images={}
    for name in [*[f'f{i:02d}' for i in range(16)],*[f'm{i:02d}{end}' for i in range(8) for end in ('a','b')]]:
        with Image.open(Path(root)/'cache/frames'/vid/(name+'.png')) as image:
            images[name]=np.asarray(image.convert('RGB') if name.startswith('f') else image).copy()
    return images


def run_original(run,spec,cfg,legacy_root,workers=3):
    import cv2
    cv2.setNumThreads(1)
    info,_,videos,_=load_snapshot(run);source=archive_original(run,legacy_root)
    folder=run/'b0'
    if (folder/'files.json').exists():verify(folder);return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True);raw=folder/'raw';raw.mkdir(exist_ok=True)
    thresholds=read_json(source/'outputs/ch1_stats.json')['thresholds']
    old_rows=read_csv(source/'outputs/metadata.csv');old={r['vid']:r for r in old_rows}
    manifest={r['vid']:r for r in read_csv(source/'outputs/manifest.csv')}
    if set(old)!=set(info['ids']) or set(manifest)!=set(info['ids']):raise ContractError('Original ND1 video IDs differ')
    unchanged=[v for v in info['ids'] if int(manifest[v]['size_bytes'])==videos[v]['size_bytes']]
    method_hash=digest(dict(sources=verify(source),thresholds=thresholds,policy='faithful_s01_s04_v1'))
    def process(vid):
        json_path=raw/(vid+'.json');npz_path=raw/(vid+'.npz')
        if json_path.exists() and npz_path.exists():
            row=read_json(json_path)
            if row['source_sha256']!=videos[vid]['sha256'] or row['method_hash']!=method_hash or row['frames_sha256']!=file_hash(npz_path):
                raise ContractError('ND1 resume artifacts changed')
            return row
        cached=load_old_images(legacy_root,vid)
        original=measure(cached,spec,thresholds)
        expected=old[vid]
        old_errors=[f for f,a,b in [('dominant_color',original['dominant_color'],expected['dominant_color']),
                    ('dominant_group',original['d1'],expected['dominant_group']),('texture',original['d2'],expected['texture']),
                    ('motion',original['d5'],expected['motion']),('edge_density',round(original['edge_density'],4),float(expected['edge_density'])),
                    ('motion_index',round(original['motion_index'],2),float(expected['motion_index']))] if a!=b]
        # Recompute all CURRENT videos, including the 511 expected unchanged videos.
        images,pts=decode_original(Path(cfg['dataset_root'])/videos[vid]['relative_path'],videos[vid]['metadata']['duration'])
        current=measure(images,spec,thresholds)
        np.savez_compressed(npz_path,**images)
        pixel_matches={k:pixel_hash(images[k])==pixel_hash(cached[k]) for k in images}
        label_errors=[f for f,key in [('d1','dominant_group'),('d2','texture'),('d5','motion')]
                      if current[f]!=expected[key]]
        row=dict(video_id=vid,class_code=videos[vid]['class_code'],source_sha256=videos[vid]['sha256'],
                 method_hash=method_hash,frames_sha256=file_hash(npz_path),actual_pts=pts,
                 old_cache_errors=old_errors,candidate_unchanged=vid in unchanged,
                 old_cached_frames_matching=sum(pixel_matches.values()),old_cached_frame_matches=pixel_matches,
                 current_vs_old_label_errors=label_errors,**current)
        write_json(json_path,row);return row
    records=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(process,info['ids']):
            records.append(row)
            if len(records)%20==0 or len(records)==1 or len(records)==len(info['ids']):
                print(f'B0 original ND1 {len(records)}/{len(info["ids"])} {row["video_id"]}',flush=True)
                write_json(folder/'progress.json',dict(completed=len(records),total=len(info['ids'])))
    label_rows=[{k:v for k,v in r.items() if k not in ('actual_pts','old_cache_errors','old_cached_frame_matches',
                        'current_vs_old_label_errors','per_frame_edge','per_pair_difference','crop')} for r in records]
    write_csv(folder/'nhan_nd1.csv',label_rows)
    mismatches=[dict(video_id=r['video_id'],errors=r['current_vs_old_label_errors']) for r in records
                if r['candidate_unchanged'] and r['current_vs_old_label_errors']]
    old_errors=[dict(video_id=r['video_id'],errors=r['old_cache_errors']) for r in records if r['old_cache_errors']]
    image_changes=[r['video_id'] for r in records if r['candidate_unchanged'] and r['old_cached_frames_matching']!=32]
    passed=len(unchanged)==511 and not mismatches and not old_errors
    write_json(folder/'baseline_check.json',dict(expected_unchanged=511,manifest_same_size=len(unchanged),
               unchanged_label_mismatches=mismatches,original_cache_replay_errors=old_errors,
               sampled_pixel_differences_for_same_size=image_changes,
               historical_source_sha256_available=False,
               identity_limit='Historical video SHA256 unavailable; size membership is corroborated by cached-frame comparison, not asserted as byte identity'))
    result=dict(status='passed' if passed else 'failed_baseline',verified=passed,rows=len(records),
                thresholds=thresholds,snapshot_hash=verify(run/'snapshot'),method_hash=method_hash,
                original_sources_hash=verify(source),reference_sha256=file_hash(source/'outputs/ch1_stats.json'),
                unchanged_count=len(unchanged),unchanged_label_mismatches=len(mismatches),
                original_cache_replay_errors=len(old_errors),same_size_sampled_pixel_differences=len(image_changes),
                d1_definition='argmax of eight pixel shares, then original GROUP5 -> five dominant groups; eight-color detail retained',
                d5_definition='original cropped grayscale short180, float32 mean absolute difference; not Flow',
                limitation='automatic ND1 proxy labels; historical video SHA256 unavailable; sampled pixel checks reported separately')
    write_json(folder/'method.json',dict(method='faithful_s01_s04_v1',thresholds=thresholds,source_hash=verify(source),
               color_order=COLORS,group5=GROUP5,motion_short_side=180,decode_resize='cv2.INTER_AREA',
               mapping='D1 HSV; D2 LBP via Canny proxy; D4 CLIP via scene class; D5 Flow via grayscale-change proxy'))
    write_json(folder/'result.json',result);seal(folder)
    if not passed:raise ContractError('B0 original ND1 replay mismatch; see baseline_check.json; B5/test remain blocked')
    return result
