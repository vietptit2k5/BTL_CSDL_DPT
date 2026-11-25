import itertools
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from ..core import ContractError, PROJECT, digest, file_hash
from ..video_search import FEATURES, POLICY, build_matrices, reference_pair
from .data import load_matrices, load_snapshot
from .files import read_csv, read_json, seal, verify, write_csv, write_json
from .metrics import METRICS, joint_values, macro, random_expectation, split_queries, summarize, top_five, values
from .nd1 import certified_labels


def b1(run,goal_path=None,groups_path=None):
    info,_,videos,_=load_snapshot(run)
    folder=run/'b1'
    if (folder/'files.json').exists():
        verify(folder)
        if goal_path and file_hash(goal_path)!=read_json(folder/'result.json')['goal_source_sha256']:
            raise ContractError('Goals already frozen; changed goals require a new run')
        if groups_path and file_hash(groups_path)!=read_json(folder/'result.json')['groups_source_sha256']:
            raise ContractError('Query groups already frozen')
        return read_json(folder/'result.json')
    goal_path=Path(goal_path or PROJECT/'specs/video_goal.json');goal=read_json(goal_path)
    expected=read_json(PROJECT/'specs/video_goal.json')
    if goal['objective']!=expected['objective'] or goal['metrics']!=list(METRICS):
        raise ContractError('Unsupported objective/metrics; explicitly implement a new policy before running')
    grid=goal['weight_grid']
    if not grid or any(not isinstance(x,(int,float)) or not np.isfinite(x) or x<0 or x>1 for x in grid):
        raise ContractError('Invalid declared weight grid')
    ids=info['ids'];classes=np.array([videos[v]['class_code'] for v in ids])
    if groups_path:
        rows=read_csv(groups_path);lookup={r['video_id']:r['group'] for r in rows}
        if len(lookup)!=len(rows) or set(lookup)!=set(ids) or any(not g.strip() for g in lookup.values()):
            raise ContractError('Groups CSV must cover each indexed video once, with nonempty group')
        groups=[lookup[v] for v in ids]
    else:groups=ids
    split=split_queries(ids,classes,groups,goal['seed'])
    folder.mkdir(exist_ok=True)
    write_json(folder/'muc_tieu_video.json',goal);write_csv(folder/'split.csv',split)
    mapping={
        'D1':dict(report='ND1 Table 1.5 p13 and original s04 GROUP5; ND2 2.3 pp28-29',descriptor='HSV128',metric='same original five dominant_group labels; argmax eight pixel groups first, then GROUP5; retain eight-color detail'),
        'D2':dict(report='ND1 Table 1.5 p13; ND2 2.4 pp30-31',descriptor='LBP10',metric='same ND1 Canny-density level; proxy differs from LBP'),
        'D4':dict(report='ND1 Table 1.1 and 1.5; ND2 2.5 pp31-33',descriptor='CLIP512',metric='same six-class scene label; does not separately test D3 layout'),
        'D5':dict(report='ND1 Table 1.5 pp13-14; ND2 2.6 pp33-35',descriptor='Flow24',metric='same grayscale-difference level, not optical-flow magnitude itself'),
        'aggregation':dict(report='ND3 implementation choice',policy=POLICY,loss='frame temporal order not compared; each descriptor matches independently'),
        'fusion':dict(report='ND2 2.7.3 pp36-37 prioritizes CLIP; exact weights left to ND3-4',policy='nonnegative weights sum1; CLIP minimum declared; Flow chi-square divided by3')}
    write_json(folder/'mapping_nd1_nd2.json',mapping)
    report=PROJECT.parent/'[D23-lớp 04] - Nhóm 12.pdf'
    result=dict(status='frozen',goal_source_sha256=file_hash(goal_path),
                groups_source_sha256=file_hash(groups_path) if groups_path else None,
                grouping='supplied' if groups_path else 'one video per group; duplicate independence unverified',
                development=sum(r['split']=='development' for r in split),test=sum(r['split']=='test' for r in split),
                snapshot_hash=verify(run/'snapshot'),report_sha256=file_hash(report),
                split_scope='held-out queries within the same fixed gallery, not unseen-gallery generalization')
    write_json(folder/'result.json',result);seal(folder)
    return result


def b2(run):
    info,arrays,_,_=load_snapshot(run);folder=run/'b2'
    if (folder/'files.json').exists():
        load_matrices(run);return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True);started=time.perf_counter()
    def progress(done,total):
        if done%20==0 or done==1 or done==total:
            print(f'B2 {done}/{total} videos',flush=True)
            write_json(folder/'progress.json',dict(completed=done,total=total,seconds=time.perf_counter()-started))
    matrices=build_matrices(arrays,info['ids'],progress)
    np.savez_compressed(folder/'matrices.npz',**matrices)
    write_csv(folder/'video_order.csv',[dict(position=i,video_id=v) for i,v in enumerate(info['ids'])])
    result=dict(status='built',videos=len(info['ids']),policy=POLICY,seconds=time.perf_counter()-started,
                snapshot_hash=verify(run/'snapshot'),algorithm_hash=file_hash(PROJECT/'src/nhom12/video_search.py'),
                dtype='float64',requires_b3_before_query=True)
    write_json(folder/'result.json',result);seal(folder);return result


def b3(run):
    info,arrays,_,_=load_snapshot(run);matrices=load_matrices(run);folder=run/'b3'
    if (folder/'files.json').exists():
        verify(folder)
        if read_json(folder/'result.json')['matrix_hash']!=verify(run/'b2'):raise ContractError('B3 cache differs')
        return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True);tol=1e-6;checks=[]
    for f,m in matrices.items():
        error=float(np.max(np.abs(m-m.T)))
        self_gap=float(np.max(m.max(1)-np.diag(m)))
        checks.append(dict(feature=f,symmetry_error=error,self_score_gap=self_gap,
                           minimum=float(m.min()),maximum=float(m.max()),
                           passed=bool(np.isfinite(m).all() and error<tol and self_gap<tol and m.min()>=-tol and m.max()<=1+tol)))
    rng=np.random.default_rng(2026);n=len(info['ids'])
    pairs=sorted({(0,0),(0,n-1),(n-1,0),(n//2,n//2),*[(int(i),int(j)) for i,j in rng.integers(0,n,(20,2))]})
    errors=[]
    for i,j in pairs:
        expected=reference_pair(arrays,i,j)
        for f in FEATURES:
            errors.append(dict(left=info['ids'][i],right=info['ids'][j],feature=f,
                               matrix=float(matrices[f][i,j]),scalar=expected[f],error=abs(float(matrices[f][i,j])-expected[f])))
    write_csv(folder/'matrix_checks.csv',checks);write_csv(folder/'scalar_pairs.csv',errors)
    passed=all(c['passed'] for c in checks) and max(r['error'] for r in errors)<tol
    result=dict(status='passed' if passed else 'failed',tolerance=tol,independent_scalar_pairs=len(pairs),
                max_scalar_error=max(r['error'] for r in errors),matrix_hash=verify(run/'b2'),
                scope='arithmetic, symmetry, bounds, self can tie; no effectiveness claim')
    write_json(folder/'result.json',result);seal(folder)
    if not passed:raise ContractError('B3 failed; query/tuning stopped')
    return result


def require_b3(run):
    verify(run/'b3');result=read_json(run/'b3/result.json')
    if result['status']!='passed' or result['matrix_hash']!=verify(run/'b2'):
        raise ContractError('B3 must pass against current matrices')


def experiment_inputs(run):
    load_snapshot(run);certified_labels(run);require_b3(run);verify(run/'b1')
    result={step:verify(run/step) for step in ('snapshot','b0','b1','b2','b3')}
    result['experiment_code']=digest({name:file_hash(Path(__file__).parent/name) for name in
                                    ('stages.py','metrics.py','nd1.py','nd1_original.py')})
    return result


def dataset(run,split):
    info,_,_,_=load_snapshot(run);ids=info['ids'];rows=certified_labels(run)
    labels_by_id={r['video_id']:r for r in rows}
    if set(labels_by_id)!=set(ids) or len(labels_by_id)!=len(rows):raise ContractError('ND1 label IDs differ')
    labels={f:np.array([labels_by_id[v]['class_code' if f=='class' else f] for v in ids]) for f in METRICS}
    assignments=read_csv(run/'b1/split.csv')
    if [r['video_id'] for r in assignments]!=ids:raise ContractError('Frozen split order differs')
    queries=np.array([i for i,r in enumerate(assignments) if r['split']==split],dtype=int)
    groups=np.array([assignments[i]['group'] for i in queries]);classes=labels['class'][queries]
    if len(set(classes))!=6:raise ContractError('Evaluation split must cover all six classes')
    return info,labels,queries,classes,groups


def locked_weights(run):
    lock=read_json(run/'trong_so_video.json')
    if lock['mode']!='official' or lock['inputs']!=experiment_inputs(run) or lock['selection_hash']!=verify(run/'b5'):
        raise ContractError('Locked video weights differ from original inputs; use a new run')
    return lock


def b5(run):
    inputs=experiment_inputs(run)
    if (run/'trong_so_video.json').exists():return locked_weights(run)
    goal=read_json(run/'b1/muc_tieu_video.json')
    info,labels,queries,classes,groups=dataset(run,'development');matrices=load_matrices(run)
    candidates=[]
    for h,l,m in itertools.product(goal['weight_grid'],repeat=3):
        c=round(1-h-l-m,10)
        if c<goal['clip_minimum']-1e-10:continue
        weights=dict(clip=c,hsv=h,lbp=l,motion=m)
        v=values(labels,queries,top_five(matrices,weights,queries))
        candidates.append(dict(weights=weights,metrics=summarize(v,classes,groups)))
    if not candidates:raise ContractError('Declared grid has no valid configuration')
    reference=max(candidates,key=lambda x:x['metrics']['class']['mean'])
    limit=reference['metrics']['class']['mean']-reference['metrics']['class']['se']
    valid=[x for x in candidates if x['metrics']['class']['mean']>=limit]
    best=max(valid,key=lambda x:x['metrics']['objective']['mean'])
    objective_limit=best['metrics']['objective']['mean']-best['metrics']['objective']['se']
    zone=[x for x in valid if x['metrics']['objective']['mean']>=objective_limit]
    chosen=min(zone,key=lambda x:(sum(v>0 for v in x['weights'].values()),-x['weights']['clip'],
                                 x['weights']['hsv'],x['weights']['lbp'],x['weights']['motion']))
    folder=run/'b5';folder.mkdir(exist_ok=True)
    records=[]
    for candidate in candidates:
        metrics=candidate['metrics'];records.append(dict(**candidate['weights'],
                 **{f'{f}_mean':metrics[f]['mean'] for f in (*METRICS,'objective')},
                 **{f'{f}_se':metrics[f]['se'] for f in (*METRICS,'objective')},
                 eligible=metrics['class']['mean']>=limit,
                 within_1se=metrics['class']['mean']>=limit and metrics['objective']['mean']>=objective_limit))
    write_csv(folder/'bang_luoi.csv',records)
    result=dict(status='selected_on_development',queries=len(queries),grid_size=len(candidates),
                class_reference=reference,class_minimum=limit,objective_reference=best,
                objective_minimum=objective_limit,one_se_zone=len(zone),chosen=chosen,
                notice='1-SE is a selection heuristic, not a significance test; positive weights are not required')
    write_json(folder/'result.json',result);selection_hash=seal(folder)
    lock=dict(mode='official',weights=chosen['weights'],development_metrics=chosen['metrics'],inputs=inputs,
              selection_hash=selection_hash,locked_at=datetime.now(timezone.utc).isoformat(),policy=POLICY)
    write_json(run/'trong_so_video.json',lock,exclusive=True)
    return lock


def ablations(weights):
    configs=[(f'only_{f}',{k:float(k==f) for k in FEATURES}) for f in FEATURES]
    configs.append(('chosen',weights))
    for f in FEATURES:
        remaining=1-weights[f]
        configs.append((f'without_{f}',None if remaining<=1e-12 else
                        {k:0.0 if k==f else weights[k]/remaining for k in FEATURES}))
    return configs


def b6(run):
    lock=locked_weights(run);info,labels,queries,classes,groups=dataset(run,'test');matrices=load_matrices(run)
    folder=run/'b6'
    if (folder/'files.json').exists():
        verify(folder)
        if read_json(folder/'result.json')['lock_sha256']!=file_hash(run/'trong_so_video.json'):raise ContractError('Test lock changed')
        return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True)
    plan=dict(lock_sha256=file_hash(run/'trong_so_video.json'),inputs=lock['inputs'],
              configs=ablations(lock['weights']),query_ids=[info['ids'][q] for q in queries])
    if (folder/'test_plan.json').exists():
        if read_json(folder/'test_plan.json')!=json_safe(plan):raise ContractError('Test plan changed after first execution')
    else:write_json(folder/'test_plan.json',plan,exclusive=True)
    result={};per_query=[];top_rows=[];per_class=[];times=[]
    chosen_top=top_five(matrices,lock['weights'],queries)
    chosen_values=values(labels,queries,chosen_top)
    for name,weights in ablations(lock['weights']):
        if weights is None:
            result[name]=dict(status='undefined_empty_ablation');continue
        top=top_five(matrices,weights,queries);v=values(labels,queries,top)
        summary=summarize(v,classes,groups)
        paired={f:macro(chosen_values[:,i]-v[:,i],classes,groups) for i,f in enumerate(METRICS)}
        joint={f:macro(x,classes,groups) for f,x in joint_values(labels,queries,top).items()}
        result[name]=dict(status='evaluated',weights=weights,metrics=summary,chosen_minus_this=paired,joint_same_class_and_attribute=joint)
        for row,q in enumerate(queries):
            per_query.append(dict(configuration=name,video_id=info['ids'][q],class_code=str(classes[row]),group=str(groups[row]),
                                  **{f:float(v[row,i]) for i,f in enumerate(METRICS)},objective=float(v[row].mean())))
            for rank,j in enumerate(top[row],1):
                top_rows.append(dict(configuration=name,query_id=info['ids'][q],rank=rank,result_id=info['ids'][j]))
        for f,metric in summary.items():
            per_class.extend(dict(configuration=name,metric=f,class_code=c,value=x) for c,x in metric['per_class'].items())
    for q in queries:
        t=time.perf_counter();top_five(matrices,lock['weights'],np.array([q]));times.append(time.perf_counter()-t)
    baseline=summarize(random_expectation(labels,queries),classes,groups)
    confusion=[]
    for c in sorted(set(labels['class'])):
        for d in sorted(set(labels['class'])):
            mask=classes==c;count=int((labels['class'][chosen_top[mask]]==d).sum())
            confusion.append(dict(query_class=c,result_class=d,count=count,fraction=count/(int(mask.sum())*5)))
    write_csv(folder/'per_query.csv',per_query);write_csv(folder/'top5_all_configurations.csv',top_rows)
    write_csv(folder/'per_class.csv',per_class);write_csv(folder/'confusion_chosen.csv',confusion)
    table=[]
    for name,r in result.items():
        table.append(dict(configuration=name,status=r['status'],
                     **{f:r.get('metrics',{}).get(f,{}).get('mean','NA') for f in (*METRICS,'objective')},
                     **{f'{f}_se':r.get('metrics',{}).get(f,{}).get('se','NA') for f in (*METRICS,'objective')}))
    table.append(dict(configuration='exact_random_expectation',status='analytical_expectation',
                      **{f:baseline[f]['mean'] for f in (*METRICS,'objective')},
                      **{f'{f}_se':'not_a_random_simulation' for f in (*METRICS,'objective')}))
    write_csv(folder/'bang_dong_gop.csv',table)
    report=dict(status='completed_frozen_test',queries=len(queries),lock_sha256=plan['lock_sha256'],results=result,
                exact_random_expectation=baseline,
                cached_ranking_median_ms=float(np.median(times)*1000),cached_ranking_p95_ms=float(np.percentile(times,95)*1000),
                timing_scope='cached 561-video score lookup, fusion and top5 only; excludes MySQL validation, matrix build, media and UI',
                limitation='ND1 automatic labels are proxies; fixed-gallery held-out queries; D3 not separately evaluated')
    write_json(folder/'result.json',report);seal(folder);return report


def json_safe(value):
    import json
    return json.loads(json.dumps(value))


def b7(run):
    locked_weights(run);verify(run/'b6');r=read_json(run/'b6/result.json');folder=run/'b7'
    if (folder/'files.json').exists():
        verify(folder);return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True);records=read_csv(run/'b6/bang_dong_gop.csv')
    lines=['# Kết quả tìm video tương đồng ND3','',
           'Các hệ số được chọn trên nửa phát triển; các số dưới đây chỉ từ nửa kiểm tra. Kho tìm kiếm giữ nguyên toàn bộ video, loại video truy vấn.',
           '', '| Cấu hình | P@5 lớp | D1@5 | D2@5 | D5@5 | Tổng hợp |','|---|---:|---:|---:|---:|---:|']
    for row in records:
        vals=[f'{float(row[f]):.4f}' if row[f]!='NA' else 'NA' for f in (*METRICS,'objective')]
        lines.append('| '+row['configuration']+' | '+' | '.join(vals)+' |')
    lines+=['','SE từng độ đo: `../b6/bang_dong_gop.csv`; theo lớp: `../b6/per_class.csv`; '
            'chênh lệch ghép cặp và chỉ số cùng lớp đồng thời cùng thuộc tính: `../b6/result.json`.',
            '',f'Thời gian xếp hạng từ ma trận đã nạp: trung vị {r["cached_ranking_median_ms"]:.3f} ms; p95 {r["cached_ranking_p95_ms"]:.3f} ms. Đây không phải thời gian đầu cuối.',
            '', 'D1 dùng dominant_group 5 nhóm đúng s04: chọn màu chủ đạo trong 8 nhóm rồi ánh xạ GROUP5; không cộng tỷ lệ trước argmax. D2 dựa trên Canny, D5 dựa trên hiệu mức xám; các nhãn này liên quan nhưng không đồng nhất với LBP/Flow. '
            'Một SE không phải khoảng tin cậy 95%. Kết quả trên kho cố định không chứng minh tổng quát sang video mới.']
    (folder/'ket_qua.md').write_text('\n'.join(lines),encoding='utf-8')
    result=dict(status='reported',test_hash=verify(run/'b6'),report=str(folder/'ket_qua.md'))
    write_json(folder/'result.json',result);seal(folder);return result


def b8(run,spec,cfg):
    from .presentation import export_query
    locked_weights(run);verify(run/'b6');rows=read_csv(run/'b6/per_query.csv')
    chosen={r['video_id']:r for r in rows if r['configuration']=='chosen'}
    no_flow={r['video_id']:r for r in rows if r['configuration']=='without_motion'}
    best=max(chosen,key=lambda v:(float(chosen[v]['objective']),v))
    worst=min(chosen,key=lambda v:(float(chosen[v]['class']),v))
    ids=[('good',best),('class_error_or_lowest_class_precision',worst)]
    lock=locked_weights(run)
    if lock['weights']['motion']>0 and no_flow:
        changed=max(no_flow,key=lambda v:(float(chosen[v]['d5'])-float(no_flow[v]['d5']),v))
        delta=float(chosen[changed]['d5'])-float(no_flow[changed]['d5'])
        if delta>0:ids.append(('largest_observed_motion_D5_gain',changed))
    folder=run/'b8'
    if (folder/'files.json').exists():verify(folder);return read_json(folder/'result.json')
    folder.mkdir(exist_ok=True)
    results=[dict(kind=kind,**export_query(run,spec,cfg,vid)) for kind,vid in ids]
    if len(ids)==3:
        info,_,_,_=load_snapshot(run);matrices=load_matrices(run);vid=ids[2][1];q=info['ids'].index(vid)
        w_without=dict(ablations(lock['weights']))['without_motion']
        rows=[]
        for name,w in [('chosen',lock['weights']),('without_motion',w_without)]:
            from ..video_search import search_video
            for rank,hit in enumerate(search_video(vid,info['ids'],matrices,w),1):
                rows.append(dict(configuration=name,query_id=vid,rank=rank,video_id=hit['video_id'],
                                 score=hit['score'],motion_similarity=hit['similarities']['motion']))
        write_csv(folder/'flow_change.csv',rows)
    result=dict(status='exported',examples=results,
                motion_note='Flow example exists only for an observed positive D5 difference; weight zero/no gain is reported as such',
                selection_rule='deterministic best objective, lowest class precision, largest positive D5 gain; not hand-picked claims')
    write_json(folder/'result.json',result);seal(folder);return result


def status(run):
    states={}
    for step in ('snapshot','b0_diagnostic','b0','b1','b2','b3','b5','b6','b7','b8'):
        path=run/step/'result.json'
        if step=='snapshot':path=run/step/'info.json'
        if path.exists():
            result=read_json(path)
            if step=='snapshot':result={k:result[k] for k in ('index','generation','policy','dataset_quality_status')}
            states[step]=dict(sealed=(run/step/'files.json').exists(),result=result)
        else:states[step]=dict(status='not_run')
    return states
