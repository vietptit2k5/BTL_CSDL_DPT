import json
import time
from contextlib import closing
from pathlib import Path
import numpy as np
from ..core import ContractError, assert_snapshot, digest, file_hash, inventory
from ..file_snapshot import FrozenFiles, input_files
from ..storage_mysql.connection import connect
from ..storage_mysql.repository import rows
from ..storage_mysql.revisions import stamp
from ..storage_mysql.service import load_index, select_generation
from ..video_search import POLICY, validate_arrays
from .files import code_identity, read_json, seal, verify, write_json


def capture(run, spec, cfg):
    folder=run/'snapshot'
    if folder.exists():
        load_snapshot(run); guard_live(run,spec,cfg)
        return dict(status='reused',folder=str(folder))
    if cfg.get('database',{}).get('backend')!='mysql':
        raise ContractError('ND3 workflow reads the configured MySQL generation only')
    started=time.perf_counter(); generation=select_generation(cfg)
    with closing(FrozenFiles(input_files(spec,cfg))):
        before=stamp(cfg,generation)
        frames,paths,model,label,context,report=load_index(spec,cfg,generation,metadata=True)
        frames=sorted(frames,key=lambda f:(f['video_id'],f['index']))
        ids=sorted(paths)
        with connect(cfg) as con:
            videos=rows(con,'videos',generation)
            motions=rows(con,'video_features',generation)
            artifact_rows=rows(con,'video_artifacts',generation)
        artifact_count=0
        for vid,raw in artifact_rows:
            for path,sha in json.loads(raw).items():
                if not Path(path).is_file() or file_hash(path)!=sha:
                    raise ContractError(f'MySQL artifact changed: {vid}: {path}')
                artifact_count+=1
        after=stamp(cfg,generation)
        if before!=after:
            raise ContractError('MySQL changed during snapshot; no snapshot published')
        arrays={f:np.stack([fr['features'][f] for fr in frames]).reshape(len(ids),16,-1)
                for f in ('clip','hsv','lbp')}
        motion={vid:np.frombuffer(blob,dtype='<f4').copy() for vid,f,blob in motions}
        arrays['motion']=np.stack([motion[v] for v in ids])
        validate_arrays(arrays,ids)
        metadata={v[0]:dict(video_id=v[0],class_code=v[1],relative_path=v[2],sha256=v[3],size_bytes=v[4],
                            metadata=json.loads(v[5]),crop=json.loads(v[6]),quality=json.loads(v[7])) for v in videos}
        frame_meta=[{k:fr[k] for k in ('video_id','index','time','image_path')} for fr in frames]
        folder.mkdir()
        np.savez_compressed(folder/'vectors.npz',**arrays)
        write_json(folder/'videos.json',metadata);write_json(folder/'frames.json',frame_meta)
        write_json(folder/'info.json',dict(ids=ids,index=label,generation=generation,revision=before,
                   source_snapshot=json.loads(context['build']['snapshot_json']),model_identity=model,
                   dataset_root=cfg['dataset_root'],spec_hash=digest(spec),policy=POLICY,code_identity=code_identity(),
                   dataset_quality_status=report['dataset_quality_status'],verified_artifacts=artifact_count,
                   seconds=time.perf_counter()-started))
        fingerprint=seal(folder)
    return dict(status='captured',videos=len(ids),frames=len(frames),fingerprint=fingerprint)


def load_snapshot(run):
    folder=Path(run)/'snapshot';verify(folder)
    info=read_json(folder/'info.json')
    if info['policy']!=POLICY:
        raise ContractError('ND3 snapshot policy differs; reproduce in a NEW run folder')
    with np.load(folder/'vectors.npz',allow_pickle=False) as z:
        arrays={f:z[f] for f in ('clip','hsv','lbp','motion')}
    return info,arrays,read_json(folder/'videos.json'),read_json(folder/'frames.json')


def guard_live(run,spec,cfg):
    info=read_json(Path(run)/'snapshot/info.json')
    if digest(spec)!=info['spec_hash'] or select_generation(cfg)!=info['generation']:
        raise ContractError('Active MySQL generation/report spec differs from the run')
    if json.loads(json.dumps(stamp(cfg,info['generation'])))!=info['revision']:
        raise ContractError('MySQL revision differs; create a new run from the current index')
    assert_snapshot(info['source_snapshot'],inventory(cfg['dataset_root'],spec))


def load_matrices(run):
    folder=Path(run)/'b2';verify(folder)
    info=read_json(folder/'result.json')
    if info['snapshot_hash']!=verify(Path(run)/'snapshot'):
        raise ContractError('Similarity matrices belong to another snapshot')
    if info['algorithm_hash']!=file_hash(Path(__file__).parent.parent/'video_search.py'):
        raise ContractError('Similarity algorithm changed; rebuild derived artifacts in a new run')
    with np.load(folder/'matrices.npz',allow_pickle=False) as z:
        return {f:z[f] for f in ('clip','hsv','lbp','motion')}
