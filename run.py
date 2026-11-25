"""Source checkout entry point; no dependency installation is performed here."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from nhom12.environment import configure_runtime
configure_runtime()
from nhom12.cli import main
if __name__=='__main__':
    # PowerShell 5 treats native stderr progress as a terminating error under
    # ErrorActionPreference=Stop. Preserve CLI diagnostics on the stdout stream.
    if sys.platform=='win32':
        sys.stderr=sys.stdout
    raise SystemExit(main())
