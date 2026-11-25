"""Read-only final audit; does not run the independent ND4 image evaluation."""
import csv
import json
import re
import socket
import sqlite3
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from nhom12.core import file_hash,load_settings
from nhom12.environment import configure_runtime
from nhom12.provenance import check_extraction
from nhom12.storage_mysql.connection import connect
from nhom12.storage_mysql.revisions import stamp
from nhom12.storage_mysql.service import select_generation
from nhom12.video_workflow.data import guard_live,load_matrices
from nhom12.video_workflow.files import read_json,verify
from nhom12.video_workflow.stages import locked_weights
from nhom12.result_export import verify_export


def main():
    configure_runtime();spec,cfg=load_settings();run=ROOT/'var/video_similarity/run01'
    guard_live(run,spec,cfg);load_matrices(run);weights=locked_weights(run)
    archive=Path(read_json(ROOT/'var/current_index.json')['index'])
    with sqlite3.connect(archive.as_uri()+'?mode=ro',uri=True) as con:
        recorded=con.execute('SELECT implementation_hash FROM build WHERE id=1').fetchone()[0]
    extraction=check_extraction(archive.parent,recorded)
    generation=select_generation(cfg);runtime_stamp=stamp(cfg,generation)
    admin={**cfg,'database':{**cfg['database'],'connection_file':'.mysql.admin.local.json','tracking_mode':'direct'}}
    equal_stamp=runtime_stamp==stamp(admin,generation)
    with connect(cfg) as con:
        cur=con.cursor();cur.execute('SHOW GRANTS FOR CURRENT_USER');grants=[r[0] for r in cur.fetchall()];cur.close()
    privilege_text='\n'.join(grants).upper()
    scoped='SELECT ON' in privilege_text and 'EXECUTE ON PROCEDURE' in privilege_text and not any(
        p in privilege_text for p in ('ALL PRIVILEGES','INSERT,','UPDATE,','DELETE,','CREATE,','GRANT OPTION'))
    origin=read_json(run/'nd1_sources/origin.json')
    originals={n:file_hash(Path(origin['legacy_root'])/n)==sha for n,sha in origin['hashes'].items()}
    raw=(ROOT/'var/completion/tests.log').read_bytes()
    log=raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig')
    counts=re.findall(r'Ran (\d+) tests',log)
    tests_ok=bool(counts and int(counts[-1])==56 and re.search(r'^OK\s*$',log,re.M) and 'FAILED (' not in log and 'skipped=' not in log)
    labels={}
    for who in ('TV2','TV3'):
        path=ROOT/f'data/test_internet/xac_nhan_mu/phieu_{who}.csv'
        with path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
        labels[who]=dict(rows=len(rows),labels_filled=sum(bool(r['lop'].strip()) for r in rows),sha256=file_hash(path))
    functional=read_json(ROOT/'var/completion/functional_validation.json')
    browser_path=ROOT/'var/completion/browser_validation.json'
    browser=read_json(browser_path) if browser_path.exists() else {}
    exports=[verify_export(Path(r['trace']).parent) for r in functional['queries']]
    ports={}
    for port in (3306,3307):
        with socket.socket() as sock:
            sock.settimeout(1);ports[str(port)]=sock.connect_ex(('127.0.0.1',port))==0
    checks=dict(certified_archive_unchanged=file_hash(archive)=='7cf27d6f707c0bf2276cdf84e1e270b85cd8ff9e308d96bd8fc2f8a667c9842a',
                original_nd1_inputs_preserved=all(originals.values()),
                active_generation_unchanged=generation=='7cf27d6f707c0bf2276cdf84e1e270b8',
                runtime_scoped_account=scoped,stamp_matches_admin=equal_stamp,
                all_56_tests_passed_without_skips=tests_ok,
                image_weights_unchanged=cfg['search']['weights']==dict(clip=.95,hsv=.05,lbp=0.),
                video_weights_unchanged=weights['weights']==dict(clip=.90,hsv=.05,lbp=0.,motion=.05),
                independent_nd4_deferred=not (ROOT/'var/weights/test/ket_qua_test.md').exists() and all(
                    r['rows']==60 and r['labels_filled']==0 for r in labels.values()),
                functional_http_passed=functional['status']=='passed',
                browser_playback_verified=browser.get('status')=='passed' and browser.get('matching_frame_seek_verified') is True,
                production_mysql_running=ports['3306'],owned_test_mysql_stopped=not ports['3307'])
    result=dict(checks=checks,extraction=extraction,source_checks=originals,
                stage_fingerprints={s:verify(run/s) for s in ('snapshot','b0','b1','b2','b3','b5','b6','b7','b8')},
                active_revision=runtime_stamp,image_test_labels=labels,exports=exports,
                tests_log_sha256=file_hash(ROOT/'var/completion/tests.log'),
                browser_playback_verified=checks['browser_playback_verified'],
                browser_validation_sha256=file_hash(browser_path) if browser_path.exists() else None,
                scope='integrity and functionality; no image relevance evaluation')
    (ROOT/'var/completion/preservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    if not all(checks.values()):raise SystemExit(1)


if __name__=='__main__':main()
