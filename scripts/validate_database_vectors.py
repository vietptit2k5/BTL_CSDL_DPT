"""Compare EVERY DB feature against its checksummed extraction archive."""
import json
import sqlite3
import sys
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from nhom12.core import file_hash

def main():
    out=root/'var/search_phases/03_database'
    result=json.loads((out/'validation.json').read_text(encoding='utf-8'))
    assert result['status']=='passed'
    index=Path(result['index']);con=sqlite3.connect(index.as_uri()+'?mode=ro',uri=True)
    archive_count=frame_vectors=motion_vectors=images=0
    try:
        for vid,manifest_text,crop_text in con.execute('SELECT v.video_id,a.manifest_json,v.crop_json FROM videos v JOIN video_artifacts a USING(video_id) ORDER BY v.video_id'):
            manifest=json.loads(manifest_text);archives=[p for p in manifest if p.endswith('/features.npz') or p.endswith('\\features.npz')]
            assert len(archives)==1,vid
            archive=Path(archives[0]);assert file_hash(archive)==manifest[str(archive)],vid
            crop=json.loads(crop_text);expected_size=(crop[2]-crop[0],crop[3]-crop[1])
            with np.load(archive,allow_pickle=False) as data:
                for i,target,actual,path in con.execute('SELECT frame_index,target_time,actual_time,image_path FROM keyframes WHERE video_id=? ORDER BY frame_index',(vid,)):
                    assert abs(float(data['target_times'][i])-target)<1e-12,(vid,i,'target')
                    assert abs(float(data['actual_times'][i])-actual)<1e-12,(vid,i,'actual')
                    assert file_hash(path)==manifest[path],(vid,i,'image checksum')
                    with Image.open(path) as im:
                        assert im.format=='PNG' and im.mode=='RGB' and im.size==expected_size,(vid,i,'image dimensions')
                        im.verify()
                    images+=1
                    rows=con.execute('SELECT feature,vector FROM frame_features WHERE video_id=? AND frame_index=?',(vid,i)).fetchall()
                    assert {f for f,b in rows}=={'hsv','lbp','clip'},(vid,i)
                    for f,blob in rows:
                        stored=np.frombuffer(blob,dtype='<f4')
                        assert np.array_equal(stored,data[f][i]),(vid,i,f)
                        frame_vectors+=1
                motion=np.frombuffer(con.execute('SELECT vector FROM video_features WHERE video_id=?',(vid,)).fetchone()[0],dtype='<f4')
                assert np.array_equal(motion,data['motion']),(vid,'motion')
                assert np.all(data['motion_end_pts']>data['motion_start_pts']),vid
                motion_vectors+=1
            archive_count+=1
    finally: con.close()
    report=dict(status='passed',archives=archive_count,pngs=images,frame_vectors=frame_vectors,motion_vectors=motion_vectors,
                index_sha256=file_hash(index),checks=['all DB BLOBs exactly equal extraction NPZ','target and actual PTS equal NPZ','PNG checksum/CRC/mode/crop dimensions','positive actual motion dt'])
    (out/'deep_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
