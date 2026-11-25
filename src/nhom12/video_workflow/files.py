import csv
import json
from pathlib import Path
from ..core import ContractError, PROJECT, digest, file_hash


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value, exclusive=False):
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if exclusive:
        with path.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2)
    else:
        temporary = path.with_suffix(path.suffix+'.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(path)


def write_csv(path, records):
    records = list(records)
    if not records:
        raise ContractError('Cannot export an empty table without columns')
    path = Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def code_identity():
    folder = Path(__file__).parent
    return digest({str(p.relative_to(PROJECT)):file_hash(p) for p in
                   [*sorted(folder.glob('*.py')),folder.parent/'video_search.py']})


def seal(folder, manifest='files.json'):
    folder = Path(folder)
    entries = {p.relative_to(folder).as_posix():file_hash(p) for p in sorted(folder.rglob('*'))
               if p.is_file() and p.name != manifest and '__pycache__' not in p.parts}
    write_json(folder/manifest,entries)
    return digest(entries)


def verify(folder, manifest='files.json'):
    folder = Path(folder)
    entries = read_json(folder/manifest)
    for relative, sha in entries.items():
        path = folder/relative
        if not path.resolve().is_relative_to(folder.resolve()) or not path.is_file() or file_hash(path) != sha:
            raise ContractError(f'Workflow artifact changed: {path}')
    return digest(entries)


def run_path(path):
    result = Path(path).resolve()
    if not result.is_relative_to((PROJECT/'var').resolve()):
        raise ContractError('Workflow run must be inside project var/; use another run name to reproduce')
    result.mkdir(parents=True,exist_ok=True)
    return result
