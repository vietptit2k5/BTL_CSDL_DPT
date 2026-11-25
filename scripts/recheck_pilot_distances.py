"""Revalidate saved pilot vectors after numeric distance fixes, no extraction."""
import sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
import numpy as np
from nhom12.search import distance
folder=root/'var/search_phases/02_features'
summary=json.loads((folder/'validation.json').read_text(encoding='utf-8'))
arrays={v['video_id']:np.load(folder/v['video_id']/'features.npz') for v in summary['videos']}
for row in summary['videos']:
    row['self_distances']={f:distance(f,arrays[row['video_id']][f][7],arrays[row['video_id']][f][7]) for f in ('hsv','lbp','clip')}
    (folder/row['video_id']/'validation.json').write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf-8')
for row in summary['pair_comparisons']:
    a,b=arrays[row['a']],arrays[row['b']]
    row['distances']={f:distance(f,a[f][7],b[f][7]) for f in ('hsv','lbp','clip')}
    row['motion_chi_square']=distance('motion',a['motion'],b['motion'])
summary['distance_validation']='float64 accumulators; histogram coefficient normalized like OpenCV; vectors not re-extracted'
(folder/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print({f:max(v['self_distances'][f] for v in summary['videos']) for f in ('hsv','lbp','clip')})
