"""Copy installed dependency RECORD files into a distinct venv, offline.

Run using the source interpreter. Source installation is read-only. No links back
to source site-packages are created; console entry points are not copied.
"""
import argparse
import importlib.metadata as md
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--target',type=Path,required=True)
    args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    target=args.target.resolve()
    if not target.is_relative_to(root) or target==root:
        raise ValueError('Target must be a dedicated venv within this project')
    dest=target/'Lib/site-packages';dest.mkdir(parents=True,exist_ok=True)
    distributions={canonicalize_name(d.metadata['Name']):d for d in md.distributions()}
    seeds=['numpy','pillow','opencv-python-headless','scikit-image','torch','transformers','safetensors','pip','setuptools','psutil']
    pending=list(seeds);selected={}
    while pending:
        name=canonicalize_name(pending.pop())
        if name in selected: continue
        d=distributions[name];selected[name]=d
        for text in d.requires or []:
            req=Requirement(text)
            if req.marker is None or req.marker.evaluate({'extra':''}):
                pending.append(req.name)
    records=[];copied=0;total=0
    def copy_one(args):
        src,out=args
        stat=src.stat()
        if out.exists():
            old=out.stat()
            if old.st_size==stat.st_size and old.st_mtime_ns==stat.st_mtime_ns:
                return stat.st_size
        out.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,out)
        return stat.st_size
    for name,d in sorted(selected.items()):
        source=Path(d.locate_file('')).resolve()
        if source==dest.resolve(): raise ValueError('Source and target must differ')
        jobs=[]
        for item in d.files or []:
            src=Path(d.locate_file(item)).resolve()
            if not src.is_relative_to(source) or not src.is_file() or src.suffix=='.pyc': continue
            relative=src.relative_to(source);out=dest/relative
            jobs.append((src,out))
        with ThreadPoolExecutor(max_workers=16) as pool:
            size=sum(pool.map(copy_one,jobs))
        count=len(jobs)
        records.append(dict(name=d.metadata['Name'],version=d.version,source=str(source),files=count,bytes=size))
        copied+=count;total+=size
        print(f'{name}=={d.version}: {count} files, {size/1e6:.1f} MB',flush=True)
    audit=root/'var/search_phases/01_environment';audit.mkdir(parents=True,exist_ok=True)
    (audit/'bootstrap.json').write_text(json.dumps(dict(source_python=sys.executable,target=str(target),packages=records,files=copied,bytes=total),indent=2),encoding='utf-8')
    (root/'requirements.lock.txt').write_text('\n'.join(f'{r["name"]}=={r["version"]}' for r in records)+'\n',encoding='utf-8')

if __name__=='__main__': main()
