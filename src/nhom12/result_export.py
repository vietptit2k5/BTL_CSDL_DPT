"""Copy the five result MP4s, verify bytes, and make a portable ZIP."""
import json
import shutil
import zipfile
from pathlib import Path
from .core import ContractError, file_hash


def export_videos(folder,hits,expected_hashes):
    folder=Path(folder).resolve()
    if len(hits)!=5 or len({h['video_id'] for h in hits})!=5:
        raise ContractError('Export requires exactly five distinct videos')
    target=folder/'videos';target.mkdir(exist_ok=False)
    records=[]
    for rank,hit in enumerate(hits,1):
        vid=hit['video_id'];source=Path(hit['video_path'])
        if not vid.replace('_','').isalnum() or vid not in expected_hashes:
            raise ContractError('Unverified video ID in export')
        expected=expected_hashes[vid]
        if file_hash(source)!=expected:raise ContractError('Result source bytes changed before export')
        name=f'videos/{rank:02d}_{vid}.mp4';dest=folder/name
        shutil.copyfile(source,dest)
        if file_hash(dest)!=expected:raise ContractError('Exported video differs from indexed source')
        hit['exported_video']=name
        records.append(dict(rank=rank,video_id=vid,file=name,sha256=expected,bytes=dest.stat().st_size,score=hit['score']))
    manifest=dict(version='nh12-export-v1',files=records,scope='five exact copies; ranking scores are not probabilities')
    (folder/'result-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(folder/'results.zip','x',compression=zipfile.ZIP_STORED) as archive:
        archive.write(folder/'result-manifest.json','result-manifest.json')
        for r in records:archive.write(folder/r['file'],r['file'])
    return manifest


def verify_export(folder):
    folder=Path(folder).resolve()
    manifest=json.loads((folder/'result-manifest.json').read_text(encoding='utf-8'))
    rows=manifest['files']
    if len(rows)!=5 or len({r['video_id'] for r in rows})!=5:raise ContractError('Invalid export manifest')
    expected={'result-manifest.json',*(r['file'] for r in rows)}
    with zipfile.ZipFile(folder/'results.zip') as archive:
        if set(archive.namelist())!=expected or len(archive.namelist())!=6:raise ContractError('ZIP entries differ')
        import hashlib
        for r in rows:
            path=(folder/r['file']).resolve()
            if not path.is_relative_to(folder/'videos') or file_hash(path)!=r['sha256']:
                raise ContractError('Export copy missing or changed')
            h=hashlib.sha256()
            with archive.open(r['file']) as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
            if h.hexdigest()!=r['sha256']:raise ContractError('ZIP video differs')
    return dict(status='passed',videos=5,zip_entries=6)
