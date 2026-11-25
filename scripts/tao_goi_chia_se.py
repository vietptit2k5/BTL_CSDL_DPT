"""Create an explicit source ZIP; local credentials, caches and machine venv are excluded."""
import argparse
import json
import sys
import zipfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOP=('README.md','pyproject.toml','requirements.lock.txt','run.py','report_spec.json','config.json','mysql.local.example.json')
DIRECTORIES=('src','scripts','tests','sql','docs','prompts','specs')


def create_package(output,full_run=None):
    output=Path(output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    selected=[ROOT/p for p in TOP if (ROOT/p).is_file()]
    selected += [p for name in DIRECTORIES for p in (ROOT/name).rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.log')]
    if full_run:
        run=Path(full_run).resolve()
        if not run.is_relative_to(ROOT/'var/video_similarity'):raise ValueError('Full run must be under var/video_similarity')
        selected += [p for p in run.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    secrets=[]
    for path in ROOT.glob('.mysql*.json'):
        value=json.loads(path.read_text(encoding='utf-8-sig')).get('password','')
        if value:secrets.append(value.encode('utf-8'))
    manifest=[]
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as archive:
        for p in sorted(set(selected)):
            relative=p.relative_to(ROOT).as_posix()
            if p.name.startswith(('.mysql','.env','.db_accounts')):raise ValueError('Secret file in package selection')
            # Small text files are checked against actual local passwords without printing them.
            if p.stat().st_size<8*1024*1024 and p.suffix in ('.py','.json','.md','.txt','.sql','.csv','.yaml'):
                raw=p.read_bytes()
                if any(secret in raw for secret in secrets):raise ValueError('Local credential found in package payload')
            archive.write(p,relative);manifest.append(relative)
        readme='Gói mã nguồn. Không chứa mật khẩu, model, Python venv hoặc video nguồn. Demo hiện tại dùng máy đã kiểm chứng. Xem docs/HOAN_THIEN_VAN_HANH.md và scripts/video_similarity/README.md. Nếu không chọn --full-run thì kết quả ND3 đầy đủ vẫn được giữ trên máy nguồn trong var/video_similarity/run01.\n'
        archive.writestr('HUONG_DAN_GOI.txt',readme)
        archive.writestr('package-manifest.json',json.dumps(dict(files=manifest,credentials_included=False,full_run=bool(full_run)),ensure_ascii=False,indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP integrity failed')
        if any(Path(n).name.startswith(('.mysql','.env','.db_accounts')) for n in archive.namelist()):raise ValueError('Credential filename in ZIP')
    return dict(zip=str(output),files=len(manifest),bytes=output.stat().st_size,credentials_included=False,full_run=bool(full_run))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path)
    ap.add_argument('--full-run',type=Path,help='Optional full ND3 run, including large raw evidence')
    a=ap.parse_args();out=a.out or ROOT/'var/releases'/('nhom12-source-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip')
    print(json.dumps(create_package(out,a.full_run),ensure_ascii=False,indent=2))
