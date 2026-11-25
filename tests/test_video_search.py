import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from nhom12.core import ContractError, file_hash
from nhom12.video_search import (FEATURES, build_matrices, motion_similarity, pair_score,
                                 reference_pair, search_video, symmetric_match, validate_weights)
from nhom12.video_workflow.files import read_csv, seal, verify, write_json
from nhom12.video_workflow.metrics import macro, random_expectation, split_queries
from nhom12.video_workflow.nd1 import categorize, color_fractions, certified_labels, verify_baseline
from nhom12.video_workflow.nd1_original import GROUP5, measure
from nhom12.video_workflow.stages import ablations, b1, b2, b3, b5, b6, b7


def fixture(n=6):
    rng=np.random.default_rng(12)
    clip=rng.normal(size=(n,16,512));clip/=np.linalg.norm(clip,axis=2,keepdims=True)
    return dict(clip=clip.astype('f4'),hsv=rng.dirichlet(np.ones(128),size=(n,16)).astype('f4'),
                lbp=rng.dirichlet(np.ones(10),size=(n,16)).astype('f4'),
                motion=rng.dirichlet(np.ones(8),size=(n,3)).reshape(n,24).astype('f4'))


class VideoSearch(unittest.TestCase):
    def test_matrix_scalar_symmetry_self_and_frame_permutation(self):
        x=fixture();ids=[f'V{i}' for i in range(6)];m=build_matrices(x,ids)
        for f in FEATURES:
            np.testing.assert_allclose(m[f],m[f].T,atol=1e-6)
            self.assertTrue((np.diag(m[f])>=m[f].max(1)-1e-6).all())
        for i,j in [(0,0),(0,1),(2,5)]:
            oracle=reference_pair(x,i,j)
            for f in FEATURES:self.assertAlmostEqual(m[f][i,j],oracle[f],places=6)
        perm=copy.deepcopy(x)
        for f in FEATURES[:-1]:perm[f][1]=perm[f][1,::-1]
        for f,value in pair_score(perm,0,1).items():self.assertAlmostEqual(value,m[f][0,1],places=6)

    def test_flow_three_blocks_range_and_zero_distance(self):
        a=np.tile(np.eye(1,8,0).ravel(),3);b=np.tile(np.eye(1,8,1).ravel(),3)
        self.assertAlmostEqual(motion_similarity(a,a),1)
        self.assertAlmostEqual(motion_similarity(a,b),0,places=10)
        self.assertAlmostEqual(motion_similarity(a,b),motion_similarity(b,a))

    def test_five_unique_no_self_ties_and_weight_contract(self):
        ids=[f'V{i}' for i in range(6)];m={f:np.ones((6,6)) for f in FEATURES}
        w=dict(clip=.4,hsv=.2,lbp=.2,motion=.2)
        hits=search_video('V0',ids,m,w)
        self.assertEqual([h['video_id'] for h in hits],ids[1:])
        self.assertTrue(all(abs(sum(h['contributions'].values())-h['score'])<1e-12 for h in hits))
        with self.assertRaises(ContractError):search_video('MISSING',ids,m,w)
        with self.assertRaises(ContractError):validate_weights({**w,'motion':-.2})
        with self.assertRaises(ContractError):validate_weights({**w,'motion':float('nan')})

    def test_symmetric_coverage_not_single_max(self):
        self.assertLess(symmetric_match(np.array([[1,0],[0,0.]])),1)
        self.assertEqual(symmetric_match(np.eye(2)),1)


class ND3Workflow(unittest.TestCase):
    def test_original_nd1_color_groups_and_threshold_boundaries(self):
        tests=[((0,0,255),'blue'),((0,255,0),'green'),((255,255,0),'yellow'),
               ((255,0,0),'red_orange'),((255,0,255),'purple_pink'),
               ((255,255,255),'white'),((120,120,120),'gray'),((0,0,0),'dark')]
        names=('blue','green','yellow','red_orange','purple_pink','white','gray','dark')
        for rgb,name in tests:
            fractions=color_fractions(Image.new('RGB',(8,8),rgb))
            self.assertEqual(names[int(np.argmax(fractions))],name)
            self.assertAlmostEqual(fractions.sum(),1)
        self.assertEqual(categorize(.067,.067,.133,('s','m','d')),'m')
        self.assertEqual(categorize(.133,.067,.133,('s','m','d')),'m')

    def test_baseline_requires_same_source_bytes_and_exact_labels(self):
        rows=[dict(video_id='V0',sha256='old',d1='blue',d2='smooth',d5='static')]
        self.assertTrue(verify_baseline(rows,rows,1)['passed'])
        self.assertFalse(verify_baseline([{**rows[0],'sha256':'new'}],rows,1)['passed'])
        self.assertFalse(verify_baseline([{**rows[0],'d5':'strong'}],rows,1)['passed'])
        self.assertFalse(verify_baseline(rows,rows,511)['passed'])

    def test_original_s04_argmax_then_group_and_motion_float32(self):
        from nhom12.core import load_settings
        spec,_=load_settings()
        # Red is the strongest individual color; green+blue combined is irrelevant.
        images={f'f{i:02d}':np.full((360,360,3),(255,0,0),dtype=np.uint8) for i in range(16)}
        images.update({f'm{i:02d}{end}':np.full((180,180),5 if end=='a' else 9,dtype=np.uint8)
                       for i in range(8) for end in ('a','b')})
        result=measure(images,spec,dict(edge=[.067,.133],motion=[3.9,9.6]))
        self.assertEqual(result['dominant_color'],'do_cam')
        self.assertEqual(result['d1'],'mau_am')
        self.assertEqual(result['d2'],'min')
        self.assertEqual(result['d5'],'nhe')
        self.assertEqual(result['motion_index'],4)
        self.assertEqual(GROUP5['trang'],GROUP5['xam'])

    def test_group_split_deterministic_disjoint_and_macro(self):
        ids=[f'{c}{i}' for c in range(6) for i in range(8)]
        cls=np.array([str(c) for c in range(6) for i in range(8)])
        groups=[f'{c}-{i//2}' for c in range(6) for i in range(8)]
        a=split_queries(ids,cls,groups);self.assertEqual(a,split_queries(ids,cls,groups))
        dev={r['group'] for r in a if r['split']=='development'}
        test={r['group'] for r in a if r['split']=='test'};self.assertFalse(dev&test)
        v=np.arange(48)/48
        stats=macro(v,cls,np.array(ids));self.assertAlmostEqual(stats['mean'],v.mean())
        expected=np.sqrt(sum(v[cls==c].var(ddof=1)/8 for c in set(cls)))/6
        self.assertAlmostEqual(stats['se'],expected)

    def test_random_baseline_accounts_for_actual_label_imbalance(self):
        labels={f:np.array(['a','a','a','a','b','b']) for f in ('class','d1','d2','d5')}
        result=random_expectation(labels,np.array([0,4]))
        np.testing.assert_allclose(result,[[.6]*4,[.2]*4])

    def test_diagnostic_labels_never_authorize_tuning(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);write_json(run/'b0_diagnostic/result.json',dict(verified=False));seal(run/'b0_diagnostic')
            with self.assertRaises(ContractError):certified_labels(run)
            with patch('nhom12.video_workflow.stages.load_snapshot',return_value=None):
                with self.assertRaises(ContractError):b5(run)

    def test_artifact_seal_detects_tampering_and_ablations(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);write_json(folder/'value.json',dict(x=1));seal(folder);verify(folder)
            write_json(folder/'value.json',dict(x=2))
            with self.assertRaises(ContractError):verify(folder)
        rows=dict(ablations(dict(clip=.4,hsv=.2,lbp=.2,motion=.2)))
        self.assertEqual(len(rows),9)
        self.assertEqual(rows['without_motion']['motion'],0)
        self.assertAlmostEqual(sum(rows['without_motion'].values()),1)
        self.assertIsNone(dict(ablations(dict(clip=1.,hsv=0.,lbp=0.,motion=0.)))['without_clip'])

    def test_complete_frozen_selection_test_and_replay_on_explicit_fixture(self):
        # Synthetic labels here test workflow mechanics only, never real retrieval quality.
        from nhom12.video_search import POLICY
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);ids=sorted(f'{c}{i:03d}' for c in ('SEA','WAT','FOR','MOU','RIV','FLO') for i in range(1,5))
            folder=run/'snapshot';folder.mkdir()
            np.savez_compressed(folder/'vectors.npz',**fixture(24))
            write_json(folder/'info.json',dict(ids=ids,policy=POLICY))
            write_json(folder/'videos.json',{v:dict(class_code=v[:3]) for v in ids})
            write_json(folder/'frames.json',[]);seal(folder)
            labels=[dict(video_id=v,class_code=v[:3],d1='xanh_duong' if i%2 else 'toi',
                         d2='min' if i%2 else 'day',d5='tinh' if i%2 else 'manh') for i,v in enumerate(ids)]
            from nhom12.video_workflow.files import write_csv
            write_csv(run/'b0/nhan_nd1.csv',labels)
            write_json(run/'b0/result.json',dict(verified=True,snapshot_hash=verify(folder),scope='synthetic test fixture'))
            seal(run/'b0')
            self.assertEqual(b1(run)['development'],12)
            b2(run);self.assertEqual(b3(run)['status'],'passed')
            lock=b5(run);self.assertEqual(b5(run),lock)
            self.assertEqual(len(read_csv(run/'b5/bang_luoi.csv')),125)
            result=b6(run);self.assertEqual(result['queries'],12)
            self.assertEqual(len(result['results']),9)
            self.assertEqual(b6(run),result)
            self.assertEqual(b7(run)['status'],'reported')
            self.assertEqual(file_hash(run/'trong_so_video.json'),result['lock_sha256'])


if __name__=='__main__':unittest.main()
