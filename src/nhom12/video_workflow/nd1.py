"""ND1 Table 1.5 labels. Diagnostic transcriptions never certify old ND1 data."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from ..core import ContractError, PROJECT, digest, file_hash, sample_times
from ..media import OpenCVBackend
from ..preprocess import resize_short
from .data import load_snapshot
from .files import read_csv, read_json, seal, verify, write_csv, write_json

COLORS=('blue','green','yellow','red_orange','purple_pink','white','gray','dark')


def color_fractions(image):
    import cv2
    hsv=cv2.cvtColor(np.asarray(image.convert('RGB')),cv2.COLOR_RGB2HSV)
    h=hsv[...,0].astype(np.float64)*2; s=hsv[...,1]; v=hsv[...,2]
    dark=v<50; white=(s<40)&(v>=190); gray=(s<40)&(v>=50)&(v<190)
    chromatic=~(dark|white|gray)
    masks=[chromatic&(h>=165)&(h<255), chromatic&(h>=70)&(h<165),
           chromatic&(h>=40)&(h<70),chromatic&((h<40)|(h>=345)),
           chromatic&(h>=255)&(h<345),white,gray,dark]
    return np.array([m.mean() for m in masks])


def measured_appearance(images):
    import cv2
    fractions=np.mean([color_fractions(im) for im in images],axis=0)
    edge=float(np.mean([(cv2.Canny(cv2.cvtColor(np.asarray(im.convert('RGB')),cv2.COLOR_RGB2GRAY),100,200)>0).mean()
                        for im in images]))
    return dict(d1=COLORS[int(np.argmax(fractions))],edge_density=edge,
                **{f'fraction_{c}':float(v) for c,v in zip(COLORS,fractions,strict=True)})


def categorize(value,low,high,names):
    if not np.isfinite(value) or low>=high:
        raise ContractError('Invalid ND1 measurement/thresholds')
    return names[0] if value<low else names[2] if value>high else names[1]


def resolve_thresholds(reference):
    """Read exact numbers at explicitly mapped paths in the ORIGINAL statistics JSON."""
    stats_path=Path(reference['stats_file'])
    if file_hash(stats_path)!=reference['stats_sha256']:
        raise ContractError('Original ND1 statistics hash differs')
    stats=read_json(stats_path); result={}
    for key in ('edge_low','edge_high','motion_low','motion_high'):
        value=stats
        for part in reference['threshold_paths'][key]:
            value=value[int(part)] if isinstance(value,list) else value[part]
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value):
            raise ContractError(f'ND1 threshold is not a finite number: {key}')
        result[key]=float(value)
    return result


def verify_baseline(records,baseline,expected_unchanged):
    old={r['video_id']:r for r in baseline}; matched=[];changed=[];missing=[];mismatches=[]
    if len(old)!=len(baseline):
        raise ContractError('Duplicate IDs in original ND1 baseline')
    for r in records:
        prev=old.get(r['video_id'])
        if not prev: missing.append(r['video_id']);continue
        if prev['sha256']!=r['sha256']:changed.append(r['video_id']);continue
        matched.append(r['video_id'])
        for field in ('d1','d2','d5'):
            if prev[field]!=r[field]:
                mismatches.append(dict(video_id=r['video_id'],field=field,old=prev[field],new=r[field]))
    return dict(passed=len(matched)==expected_unchanged and not mismatches,
                expected_unchanged=expected_unchanged,unchanged_count=len(matched),
                changed=changed,missing_from_baseline=missing,mismatches=mismatches)


def run_labels(run,spec,cfg,reference_path=None,diagnostic=False):
    info,arrays,videos,frames=load_snapshot(run)
    if reference_path is None and not diagnostic:
        raise ContractError('B0 needs --reference ORIGINAL_REFERENCE.json; use --diagnostic only to inspect, not tune')
    reference=read_json(reference_path) if reference_path else None
    if reference:
        thresholds=resolve_thresholds(reference)
        if reference.get('method')!=read_json(PROJECT/'specs/nd1_method_report.json')['method']:
            raise ContractError('Original ND1 method differs from implemented report transcription; adapt/review first')
    else:
        thresholds=dict(edge_low=.067,edge_high=.133,motion_low=3.9,motion_high=9.6)
    folder=run/('b0_diagnostic' if diagnostic else 'b0')
    if (folder/'files.json').exists():
        verify(folder)
        if read_json(folder/'result.json')['reference_sha256']!=(file_hash(reference_path) if reference_path else None):
            raise ContractError('Reference changed; use a new run folder')
        return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True);raw_folder=folder/'raw';raw_folder.mkdir(exist_ok=True)
    method=read_json(PROJECT/'specs/nd1_method_report.json')
    write_json(folder/'method.json',method)
    by_frame={v:[] for v in info['ids']}
    for fr in frames:by_frame[fr['video_id']].append(fr)
    backend=OpenCVBackend();records=[]
    for pos,vid in enumerate(info['ids']):
        raw_path=raw_folder/f'{vid}.json';pairs_path=raw_folder/f'{vid}_pairs.npz'
        if raw_path.exists() and pairs_path.exists():
            raw=read_json(raw_path)
            if raw['sha256']!=videos[vid]['sha256'] or raw['pairs_sha256']!=file_hash(pairs_path):
                raise ContractError('Interrupted ND1 raw cache changed')
        else:
            images=[]
            for fr in by_frame[vid]:
                with Image.open(fr['image_path']) as image:images.append(resize_short(image.convert('RGB'),256))
            raw=measured_appearance(images)
            meta=videos[vid];duration=meta['metadata']['duration']
            starts=sample_times(duration-.25,8,.05)
            decoded=backend.sample_many(Path(cfg['dataset_root'])/meta['relative_path'],
                                        [(t,360,False) for t in starts+[t+.25 for t in starts]])
            import cv2
            gray=[cv2.cvtColor(np.asarray(resize_short(im.crop(tuple(meta['crop'])),256)),cv2.COLOR_RGB2GRAY)
                  for t,im in decoded]
            diffs=[float(np.abs(a.astype(np.float64)-b.astype(np.float64)).mean()) for a,b in zip(gray[:8],gray[8:],strict=True)]
            np.savez_compressed(pairs_path,start_gray=np.stack(gray[:8]),end_gray=np.stack(gray[8:]),
                                actual_pts=np.array([t for t,im in decoded]),target_pts=np.array(starts+[t+.25 for t in starts]))
            raw.update(video_id=vid,sha256=meta['sha256'],motion_difference=float(np.mean(diffs)),
                       per_pair_differences=diffs,pairs_sha256=file_hash(pairs_path))
            write_json(raw_path,raw)
        row={k:v for k,v in raw.items() if k not in ('per_pair_differences','pairs_sha256')}
        row.update(class_code=videos[vid]['class_code'],
                   d2=categorize(raw['edge_density'],thresholds['edge_low'],thresholds['edge_high'],('smooth','medium','dense')),
                   d5=categorize(raw['motion_difference'],thresholds['motion_low'],thresholds['motion_high'],('static','light','strong')))
        records.append(row)
        if (pos+1)%20==0 or pos==0 or pos+1==len(info['ids']):
            write_json(folder/'progress.json',dict(completed=pos+1,total=len(info['ids'])))
            print(f'B0 {pos+1}/{len(info["ids"])} {vid}',flush=True)
    write_csv(folder/'nhan_nd1.csv',records)
    baseline_report=None
    if reference:
        if file_hash(reference['baseline_csv'])!=reference['baseline_sha256']:
            raise ContractError('Original ND1 baseline hash differs')
        baseline_report=verify_baseline(records,read_csv(reference['baseline_csv']),reference['expected_unchanged'])
        write_json(folder/'baseline_check.json',baseline_report)
        write_json(folder/'reference.json',reference)
    passed=bool(reference and not diagnostic and baseline_report['passed'])
    result=dict(status='passed' if passed else 'diagnostic_only' if diagnostic else 'failed_baseline',
                verified=passed,rows=len(records),thresholds=thresholds,
                reference_sha256=file_hash(reference_path) if reference_path else None,
                method_hash=digest(method),snapshot_hash=verify(run/'snapshot'),baseline=baseline_report,
                limitation='D5 is grayscale change, not optical flow; diagnostic report thresholds are rounded and unverified')
    write_json(folder/'result.json',result);seal(folder)
    if reference and not diagnostic and not passed:
        raise ContractError('B0 baseline does not match; tuning/test stopped. See baseline_check.json')
    return result


def certified_labels(run):
    folder=Path(run)/'b0'
    if not (folder/'files.json').is_file():
        raise ContractError('B0 original ND1 verification missing. Diagnostic labels cannot authorize B5-B8')
    verify(folder);result=read_json(folder/'result.json')
    if not result['verified'] or result['snapshot_hash']!=verify(Path(run)/'snapshot'):
        raise ContractError('B0 not verified for this snapshot; do not tune or evaluate test')
    if result.get('original_sources_hash') and verify(Path(run)/'nd1_sources')!=result['original_sources_hash']:
        raise ContractError('Archived original ND1 sources changed')
    return read_csv(folder/'nhan_nd1.csv')
