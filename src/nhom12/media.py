"""Report §2.1.3: sequential decode, nearest actual presentation timestamp."""
import math
import json
import shutil
import subprocess
from pathlib import Path
from .core import ContractError

class OpenCVBackend:
    def __init__(self):
        import cv2
        self.cv2=cv2

    def probe(self,path):
        """FFprobe metadata avoids estimating VFR duration from frame count/FPS."""
        executable=shutil.which('ffprobe')
        if not executable:
            raise ContractError('FFprobe not on PATH; install FFmpeg before a production build')
        completed=subprocess.run([executable,'-v','error','-show_format','-show_streams','-of','json',str(path)],
                                 capture_output=True,text=True,encoding='utf-8',check=False)
        if completed.returncode:
            raise ContractError(f'FFprobe failed: {completed.stderr.strip()}')
        data=json.loads(completed.stdout)
        video=next((s for s in data['streams'] if s['codec_type']=='video'),None)
        if video is None: raise ContractError('No video stream')
        numerator,denominator=map(int,video['avg_frame_rate'].split('/'))
        duration=float(data['format']['duration'])
        if duration<=0 or not math.isfinite(duration): raise ContractError('Invalid video duration')
        rotations=[s.get('rotation') for s in video.get('side_data_list',[]) if 'rotation' in s]
        coded_w,coded_h=int(video['width']),int(video['height'])
        rotated=bool(rotations) and abs(float(rotations[0]))%180==90
        return dict(duration=duration,width=coded_h if rotated else coded_w,height=coded_w if rotated else coded_h,
                    coded_width=coded_w,coded_height=coded_h,
                    fps=numerator/denominator if denominator else None,codec=video['codec_name'],
                    duration_method='ffprobe_format',rotation=rotations,container=data['format'].get('format_name',''))

    def probe_estimate(self,path):
        """Diagnostic only; production pipeline never uses this estimate."""
        cv=self.cv2;cap=cv.VideoCapture(str(path))
        try:
            if not cap.isOpened(): raise ContractError(f'Cannot open video: {path}')
            fps=cap.get(cv.CAP_PROP_FPS);count=cap.get(cv.CAP_PROP_FRAME_COUNT)
            if not math.isfinite(fps) or fps<=0 or count<=0:
                raise ContractError('Missing metadata; use an FFprobe backend for this file')
            fourcc=int(cap.get(cv.CAP_PROP_FOURCC))
            codec=''.join(chr((fourcc>>(8*i))&255) for i in range(4)).rstrip('\x00')
            return dict(duration=count/fps,width=int(cap.get(cv.CAP_PROP_FRAME_WIDTH)),
                        height=int(cap.get(cv.CAP_PROP_FRAME_HEIGHT)),fps=fps,codec=codec,
                        duration_method='frame_count/average_fps')
        finally:
            cap.release()

    def sample(self,path,times,short_side,gray=False):
        return self.sample_many(path,[(t,short_side,gray) for t in times])

    def sample_many(self,path,requests):
        """One decode pass for mixed keyframe/motion requests, nearest real PTS.

        Convert/resize only selected frames; retain two native frames to bracket
        each target. No change to sampling times or per-request preprocessing.
        """
        from PIL import Image
        from .preprocess import resize_short
        if not requests or any(not math.isfinite(t) or t<0 or side<=0 for t,side,gray in requests):
            raise ContractError('Invalid sample times')
        cv=self.cv2;cap=cv.VideoCapture(str(path))
        targets=sorted(enumerate(requests),key=lambda p:p[1][0]);out=[None]*len(requests)
        previous=None;pending=0;last_ts=-1;last_interval=None
        def convert(chosen,request):
            ts,frame=chosen;t,side,gray=request
            pixels=cv.cvtColor(frame,cv.COLOR_BGR2GRAY if gray else cv.COLOR_BGR2RGB)
            return ts,resize_short(Image.fromarray(pixels),side)
        try:
            if not cap.isOpened(): raise ContractError(f'Cannot open video: {path}')
            while pending<len(targets):
                ok,frame=cap.read()
                if not ok: break
                ts=cap.get(cv.CAP_PROP_POS_MSEC)/1000
                if not math.isfinite(ts) or ts<0 or ts<=last_ts:
                    raise ContractError('Missing/nonmonotonic PTS; requires another decoder backend')
                if last_ts>=0: last_interval=ts-last_ts
                last_ts=ts
                current=(ts,frame)
                while pending<len(targets) and ts>=targets[pending][1][0]:
                    index,request=targets[pending];target=request[0]
                    chosen=previous if previous is not None and abs(previous[0]-target)<=abs(ts-target) else current
                    out[index]=convert(chosen,request);pending+=1
                previous=current
            # Targets beyond the last PTS use the last decoded frame, only within one frame interval.
            while pending<len(targets) and previous:
                index,request=targets[pending];target=request[0]
                if last_interval is None or target-previous[0]>last_interval+1e-7:
                    raise ContractError('Requested timestamp beyond decoded video')
                out[index]=convert(previous,request);pending+=1
            if any(x is None for x in out): raise ContractError('Incomplete video decode')
            return out
        finally:
            cap.release()
