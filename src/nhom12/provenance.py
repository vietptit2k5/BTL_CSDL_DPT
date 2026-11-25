"""Verify extraction provenance when only storage or presentation code changes."""
import ast
import json
from pathlib import Path
from .core import ContractError, digest, file_hash


def _function(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(matches) != 1:
        raise ContractError(f'Missing provenance function: {name}')
    return ast.dump(matches[0], include_attributes=False)


def check_extraction(generation, recorded_hash):
    from .building import implementation_hash
    current = implementation_hash()
    if current == recorded_hash:
        return dict(mode='exact', recorded_hash=recorded_hash, current_hash=current)
    generation = Path(generation)
    archive = generation / 'implementation_sources'
    manifest_path = generation / 'implementation_sources.json'
    if not manifest_path.is_file():
        raise ContractError('Changed implementation without a certified source archive')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if digest(manifest) != recorded_hash:
        raise ContractError('Source archive does not match indexed implementation hash')
    for name, sha in manifest.items():
        if Path(name).name != name or file_hash(archive / name) != sha:
            raise ContractError('Source archive is damaged')
    current_dir = Path(__file__).parent
    critical = ('core.py', 'media.py', 'preprocess.py', 'features.py', 'repository.py', 'schema.sql')
    for name in critical:
        if file_hash(current_dir / name) != manifest.get(name):
            raise ContractError(f'Extraction implementation changed: {name}')
    functions = {'building.py': ('extract_video', 'quality_review', 'build_index'),
                 'pipeline.py': ('model_identity', 'runtime_identity')}
    for module, names in functions.items():
        for name in names:
            if _function(archive / module, name) != _function(current_dir / module, name):
                raise ContractError(f'Extraction function changed: {module}/{name}')
    return dict(mode='verified_extraction_archive', recorded_hash=recorded_hash,
                current_hash=current, unchanged_modules=list(critical), unchanged_functions=functions)


def archive_sources(generation):
    """Archive a just-built runtime; never overwrite the certified original archive."""
    generation = Path(generation)
    if (generation / 'implementation_sources.json').exists():
        return
    folder = Path(__file__).parent
    files = [p for p in sorted(folder.iterdir()) if p.suffix in ('.py', '.sql')]
    archive = generation / 'implementation_sources'
    archive.mkdir(exist_ok=True)
    for p in files:
        (archive / p.name).write_bytes(p.read_bytes())
    (generation / 'implementation_sources.json').write_text(
        json.dumps({p.name: file_hash(p) for p in files}, indent=2), encoding='utf-8')
