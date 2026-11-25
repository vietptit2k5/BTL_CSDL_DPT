"""Project-local runtime tools, without changing machine-wide configuration."""
import os
from pathlib import Path

def configure_runtime():
    root=Path(__file__).resolve().parents[2]
    binaries=root/'tools/ffmpeg/bin'
    if binaries.is_dir():
        os.environ['PATH']=str(binaries)+os.pathsep+os.environ.get('PATH','')
    os.environ.setdefault('HF_HOME',str(root/'var/hf'))
    # Every current project configuration uses a local or pinned checkpoint.
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
