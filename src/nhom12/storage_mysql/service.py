import json
import re
from pathlib import Path
from ..core import ContractError, digest, assert_snapshot, inventory
from ..provenance import check_extraction
from .. import repository as sqlite
from .connection import connect, settings
from .repository import generation_info, validate


def select_generation(cfg, index=None):
    if index and re.fullmatch(r'[0-9a-f]{32}', str(index)):
        return str(index)
    path = Path(index) if index else Path(cfg['artifacts']) / 'current_mysql_index.json'
    try:
        pointer = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise ContractError('Use current_mysql_index.json or a MySQL generation ID') from None
    if pointer.get('backend') != 'mysql' or pointer.get('database') != settings(cfg)['database']:
        raise ContractError('MySQL pointer targets a different database')
    generation = pointer.get('generation', '')
    if not re.fullmatch(r'[0-9a-f]{32}', generation):
        raise ContractError('Invalid MySQL generation ID')
    return generation


def load_index(spec, cfg, index=None, metadata=False):
    from ..pipeline import model_identity, runtime_identity
    generation = select_generation(cfg, index)
    with connect(cfg) as con:
        info = generation_info(con, generation)
        context = info['context']; stamp = context['build']
        if stamp['spec_hash'] != digest(spec) or stamp['implementation_version'] != sqlite.IMPLEMENTATION_VERSION:
            raise ContractError('MySQL spec or implementation version differs')
        if stamp['model_identity'] != model_identity(cfg):
            raise ContractError('MySQL query model differs from indexed model')
        check_extraction(context['artifact_root'], stamp['implementation_hash'])
        if context['environment']['packages'] != runtime_identity() or context['environment']['device'] != cfg['device']:
            raise ContractError('MySQL extraction environment differs')
        if Path(stamp['dataset_root']).resolve() != Path(cfg['dataset_root']).resolve():
            raise ContractError('MySQL dataset root differs')
        assert_snapshot(json.loads(stamp['snapshot_json']), inventory(cfg['dataset_root'], spec))
        report, frames, paths = validate(con, generation, spec)
    result=(frames, paths, stamp['model_identity'], f'mysql:{settings(cfg)["database"]}/{generation}')
    return (*result, context, report) if metadata else result
