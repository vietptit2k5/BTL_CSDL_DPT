"""Export/review/update safety contracts. Synthetic files do not measure retrieval quality."""
import copy
import csv
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from nhom12.core import ContractError,file_hash,load_settings
from nhom12.result_export import export_videos,verify_export
from nhom12.quality_registry import initialize,import_reviews,summary
from nhom12.incremental import change_plan


class Completion(unittest.TestCase):
    def test_five_video_copies_and_zip_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'result';folder.mkdir();hits=[];hashes={}
            for i in range(5):
                vid=f'SEA{i:03d}';path=root/(vid+'.mp4');path.write_bytes(bytes([i])*2048)
                hits.append(dict(video_id=vid,video_path=str(path),score=1-i*.1));hashes[vid]=file_hash(path)
            export_videos(folder,hits,hashes)
            self.assertEqual(verify_export(folder)['videos'],5)
            self.assertTrue(all(h['exported_video'].startswith('videos/') for h in hits))
            (folder/hits[0]['exported_video']).write_bytes(b'changed')
            with self.assertRaises(ContractError):verify_export(folder)

    def test_export_rejects_wrong_source_hash_and_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'SEA001.mp4';src.write_bytes(b'fixture')
            hits=[dict(video_id='SEA001',video_path=str(src),score=1)]*5
            with self.assertRaises(ContractError):export_videos(root,hits,{'SEA001':file_hash(src)})
            hits=[dict(video_id=f'SEA{i:03d}',video_path=str(src),score=1) for i in range(5)]
            with self.assertRaises(ContractError):export_videos(root,hits,{h['video_id']:'wrong' for h in hits})
            self.assertFalse((root/'results.zip').exists())

    def test_review_never_invents_approval_and_rejects_stale_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg={'quality_registry':str(root/'registry.json')}
            snapshot=[dict(video_id='SEA001',sha256='abc')]
            self.assertEqual(initialize(cfg,snapshot)['status'],'pending')
            row=dict(video_id='SEA001',sha256='abc',single_scene='true',not_duplicate='true',no_large_logo='true',reviewer='fixture reviewer',reviewed_at='2026-11-25T00:00:00+07:00',notes='fixture only')
            path=root/'review.csv'
            def save(r):
                with path.open('w',newline='',encoding='utf-8-sig') as f:
                    w=csv.DictWriter(f,fieldnames=list(r));w.writeheader();w.writerow(r)
            save(row);self.assertEqual(import_reviews(cfg,snapshot,path)['status'],'reviewed')
            save({**row,'single_scene':'','not_duplicate':'','no_large_logo':'','reviewer':'','reviewed_at':''})
            self.assertEqual(import_reviews(cfg,snapshot,path)['status'],'reviewed')
            self.assertEqual(summary(cfg,[dict(video_id='SEA001',sha256='new')])['stale'],1)
            save({**row,'sha256':'other'})
            with self.assertRaises(ContractError):import_reviews(cfg,snapshot,path)
            save({**row,'reviewer':''})
            with self.assertRaises(ContractError):import_reviews(cfg,snapshot,path)

    def test_incremental_plan_reuses_and_requires_explicit_replace(self):
        spec,_=load_settings();spec=copy.deepcopy(spec);spec['dataset']['minimum_videos']=6
        old=[dict(video_id=f'SEA{i:03d}',sha256='old',size_bytes=3,relative_path=f'Sea/SEA{i:03d}.mp4') for i in range(1,8)]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'SEA008.mp4';path.write_bytes(b'new')
            plan=change_plan(old,spec,[path],['SEA001'])
            self.assertEqual(plan['final_count'],7);self.assertEqual(len(plan['reused']),6);self.assertEqual(plan['extract'],['SEA008'])
            self.assertFalse(plan['active_dataset_changed'])
            existing=Path(tmp)/'SEA002.mp4';existing.write_bytes(b'replacement')
            with self.assertRaises(ContractError):change_plan(old,spec,[existing],[])
            with self.assertRaises(ContractError):change_plan(old,spec,[],['SEA001','SEA002'])

    def test_share_package_excludes_local_secrets(self):
        import importlib.util
        from unittest.mock import patch
        project=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('share_builder',project/'scripts/tao_goi_chia_se.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir();(root/'src/code.py').write_text('x=1')
            (root/'.mysql.local.json').write_text(json.dumps(dict(password='not-to-be-shared')))
            (root/'.mysql.admin.local.json').write_text(json.dumps(dict(password='admin-secret-value')))
            (root/'.env').write_text('SECRET=hidden')
            with patch.object(module,'ROOT',root):result=module.create_package(root/'package.zip')
            self.assertFalse(result['credentials_included'])
            with zipfile.ZipFile(root/'package.zip') as archive:
                self.assertIn('src/code.py',archive.namelist())
                self.assertFalse(any(n.startswith('.mysql') or n=='.env' for n in archive.namelist()))


if __name__=='__main__':unittest.main()
