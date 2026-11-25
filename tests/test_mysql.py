"""Real MySQL tests run only against an explicitly supplied, isolated test database."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from nhom12.core import ContractError, load_settings
from nhom12.pipeline import build, query_image
from nhom12.storage_mysql.connection import connect
from nhom12.storage_mysql.migrate import migrate, verify
from nhom12.storage_mysql.repository import generation_info
from test_pipeline import FakeMedia, FakeExtractor


@unittest.skipUnless(os.environ.get('NHOM12_MYSQL_TEST_CONFIG'), 'requires isolated MySQL test config')
class MySQLIntegration(unittest.TestCase):
    def setUp(self):
        self.spec, self.cfg = load_settings()
        self.cfg['database'] = dict(backend='sqlite', connection_file=os.environ['NHOM12_MYSQL_TEST_CONFIG'])
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name); sources = root / 'sources'; sources.mkdir()
        self.spec['dataset']['minimum_videos'] = 6
        for folder, code in self.spec['classes'].items():
            (sources / folder).mkdir(); (sources / folder / f'{code}001.mp4').write_bytes(b'fixture')
        model = root / 'model'; model.mkdir(); (model / 'config.json').write_text('{}')
        self.cfg.update(dataset_root=str(sources), artifacts=str(root / 'artifacts'), model_path=str(model))
        for target, value in [('nhom12.media.OpenCVBackend', FakeMedia),
                              ('nhom12.features.FrameExtractor', FakeExtractor),
                              ('nhom12.features.motion_feature', lambda pairs: np.full(24, 1/8)),
                              ('nhom12.pipeline.runtime_identity', lambda: {'fixture': '1'})]:
            p = patch(target, value); p.start(); self.addCleanup(p.stop)
        self.index = build(self.spec, self.cfg)

    def test_scoped_reader_and_incremental_generation_preserve_active_index(self):
        import secrets
        from uuid import uuid4
        import mysql.connector
        from nhom12.storage_mysql.administration import install
        from nhom12.storage_mysql.connection import settings
        from nhom12.storage_mysql.revisions import stamp
        from nhom12.incremental import load_source,change_plan,build_generation
        result=migrate(self.index,self.spec,self.cfg);generation=result['generation'];install(self.cfg)
        before=stamp(self.cfg,generation);account=settings(self.cfg);user='test_reader_'+uuid4().hex[:8]
        password=secrets.token_urlsafe(24)
        with connect(self.cfg,server_only=True) as con:
            cur=con.cursor();cur.execute('CREATE USER %s@%s IDENTIFIED BY %s',(user,'127.0.0.1',password))
            cur.execute(f'GRANT SELECT ON `{account["database"]}`.* TO %s@%s',(user,'127.0.0.1'))
            cur.execute(f'GRANT EXECUTE ON PROCEDURE `{account["database"]}`.nh12_retrieval_stamp TO %s@%s',(user,'127.0.0.1'));cur.close()
        try:
            path=Path(self.tmp.name)/'runtime.json';path.write_text(json.dumps({**account,'user':user,'password':password}))
            runtime=copy.deepcopy(self.cfg);runtime['database'].update(connection_file=str(path),tracking_mode='procedure')
            self.assertEqual(stamp(runtime,generation),before)
            with connect(runtime) as con:
                cur=con.cursor()
                with self.assertRaises(mysql.connector.Error):cur.execute('UPDATE schema_metadata SET version=version')
                cur.close()
            active=(Path(runtime['artifacts'])/'current_mysql_index.json').read_bytes()
            source=load_source(self.spec,runtime)
            extra=Path(self.tmp.name)/'SEA002.mp4';extra.write_bytes(b'new fixture')
            old=json.loads(source['context']['build']['snapshot_json']);plan=change_plan(old,self.spec,[extra],[])
            with patch('nhom12.incremental.runtime_identity',lambda:{'fixture':'1'}):
                changed=build_generation(self.spec,runtime,source,plan,Path(os.environ['NHOM12_MYSQL_TEST_CONFIG']))
            self.assertEqual(changed['reused'],6);self.assertEqual(changed['extracted'],1)
            self.assertEqual((Path(runtime['artifacts'])/'current_mysql_index.json').read_bytes(),active)
            self.assertEqual(stamp(runtime,generation),before)
            new_cfg=json.loads(Path(changed['config']).read_text(encoding='utf-8'))
            from nhom12.storage_mysql.service import load_index
            frames,_,_,_=load_index(self.spec,new_cfg)
            self.assertEqual(len(frames),7*16)
        finally:
            with connect(self.cfg,server_only=True) as con:
                cur=con.cursor();cur.execute('DROP USER %s@%s',(user,'127.0.0.1'));cur.close()

    def test_exact_copy_idempotency_and_mysql_query(self):
        from nhom12.core import file_hash
        before = file_hash(self.index)
        result = migrate(self.index, self.spec, self.cfg)
        generation = result['generation']
        self.assertEqual(result['counts']['frame_features'], 288)
        self.assertTrue(all(r['equal'] for r in result['exact_copy'].values()))
        again = migrate(self.index, self.spec, self.cfg)
        self.assertEqual(generation, again['generation'])
        self.assertEqual(file_hash(self.index), before)
        verify(generation, self.spec, self.cfg, self.index)
        image = Path(self.tmp.name) / 'query.png'; Image.new('RGB', (80, 100), 128).save(image)
        self.cfg['database']['backend'] = 'mysql'
        # The online query must work even when the SQLite backup cannot be opened.
        with patch('nhom12.repository.connect', side_effect=AssertionError('SQLite query forbidden')):
            output = query_image(self.spec, self.cfg, generation, image)
        trace = json.loads(Path(output).with_name('trace.json').read_text(encoding='utf-8'))
        self.assertTrue(trace['index'].startswith('mysql:'))
        self.assertEqual(len({h['video_id'] for h in trace['hits']}), 5)
        # Actual server constraints reject malformed BLOBs and missing frame parents.
        import mysql.connector
        with connect(self.cfg) as con:
            cur = con.cursor()
            for sql, args in [
                ('UPDATE frame_features SET vector=%s WHERE generation_id=%s AND feature=%s LIMIT 1', (b'bad', generation, 'clip')),
                ('INSERT INTO frame_features VALUES (%s,%s,%s,%s,%s)', (generation, 'SEA001', 99, 'clip', bytes(2048))),
            ]:
                with self.assertRaises(mysql.connector.Error): cur.execute(sql, args)
                con.rollback()
            cur.close()
        verify(generation, self.spec, self.cfg, self.index)

    def test_failed_import_rolls_back_and_can_retry(self):
        with patch('nhom12.storage_mysql.migrate.compare_source', side_effect=ContractError('simulated comparison failure')):
            with self.assertRaisesRegex(ContractError, 'simulated'):
                migrate(self.index, self.spec, self.cfg)
        from nhom12.core import file_hash
        generation = file_hash(self.index)[:32]
        with connect(self.cfg) as con:
            self.assertEqual(generation_info(con, generation, ready=False)['status'], 'failed')
            cur = con.cursor()
            cur.execute('SELECT count(*) FROM frame_features WHERE generation_id=%s', (generation,))
            self.assertEqual(cur.fetchone()[0], 0); cur.close()
        self.assertEqual(migrate(self.index, self.spec, self.cfg)['technical_status'], 'ready')

    def test_reusable_session_replay_and_committed_update_invalidation(self):
        from nhom12.querying import SearchSession
        from nhom12.query_evidence import verify_trace
        from nhom12.storage_mysql import revisions
        generation=migrate(self.index,self.spec,self.cfg)['generation']
        self.cfg['database']['backend']='mysql'
        image=Path(self.tmp.name)/'query.png';Image.new('RGB',(80,100),128).save(image)
        calls=[]
        class CountedExtractor(FakeExtractor):
            def __init__(self,*a,**kw):calls.append(1)
        with patch('nhom12.features.FrameExtractor',CountedExtractor):
            with SearchSession(self.spec,self.cfg,generation) as session:
                first=session.query(image);second=session.query(image)
                self.assertEqual(len(calls),1)
                verify_trace(Path(second).with_name('trace.json'))
                trace=json.loads(Path(second).with_name('trace.json').read_text(encoding='utf-8'))
                self.assertFalse(trace['session']['cold'])
                before=revisions.stamp(self.cfg,generation)
                with connect(self.cfg) as con:
                    cur=con.cursor();cur.execute('UPDATE videos SET size_bytes=size_bytes+1 WHERE generation_id=%s',(generation,));con.rollback();cur.close()
                self.assertEqual(revisions.stamp(self.cfg,generation),before)
                with connect(self.cfg) as con:
                    cur=con.cursor();cur.execute('UPDATE videos SET size_bytes=size_bytes+1 WHERE generation_id=%s',(generation,));con.commit();cur.close()
                with self.assertRaisesRegex(ContractError,'MySQL index changed'):session.query(image)
                self.assertTrue(session.closed)
        # Replay must detect altered evidence or component scores.
        trace_path=Path(first).with_name('trace.json')
        trace=json.loads(trace_path.read_text(encoding='utf-8'));trace['hits'][0]['contributions']['hsv']+=.01
        trace_path.write_text(json.dumps(trace),encoding='utf-8')
        with self.assertRaises(ContractError):verify_trace(trace_path)
