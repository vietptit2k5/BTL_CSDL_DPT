"""Small synthetic decoder tests; never mixed into the nature dataset."""
import subprocess
from pathlib import Path

def create_fixtures(directory,ffmpeg='ffmpeg'):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    base=directory/'landscape.mp4';vfr=directory/'vfr.mp4';rotated=directory/'rotation90.mp4'
    commands=[
      ['-f','lavfi','-i','testsrc2=size=320x180:rate=30:duration=3','-c:v','libx264','-pix_fmt','yuv420p',str(base)],
      ['-f','lavfi','-i','testsrc2=size=320x180:rate=30:duration=3','-vf',r"select=if(lt(t\,1)\,not(mod(n\,3))\,not(mod(n\,2)))",'-fps_mode','vfr','-c:v','libx264','-pix_fmt','yuv420p',str(vfr)],
      ['-display_rotation:v:0','90','-i',str(base),'-c','copy',str(rotated)]]
    for command,path in zip(commands,(base,vfr,rotated)):
        if path.exists(): continue
        result=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-n',*command],capture_output=True,text=True)
        if result.returncode: raise RuntimeError(result.stderr)
    return dict(landscape=base,vfr=vfr,rotated=rotated)

if __name__=='__main__':
    import sys
    root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
    from nhom12.environment import configure_runtime
    configure_runtime()
    print(create_fixtures(root/'var/search_phases/02_features/fixtures'))
