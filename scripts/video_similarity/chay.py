"""Standalone replay entry point: python scripts/video_similarity/chay.py b2.

This is exactly the main CLI's video-workflow path, without PowerShell policy changes.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from nhom12.environment import configure_runtime
configure_runtime()
from nhom12.cli import main
if __name__=='__main__':
    if '--config' in sys.argv:
        raise SystemExit('For a custom config use run.py --config CONFIG video-workflow STEP')
    sys.argv.insert(1,'video-workflow')
    raise SystemExit(main())
