param([Parameter(ValueFromRemainingArguments=$true)][string[]]$TaskArgs)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Project Python is missing. See docs/HUONG_DAN_MOI_TRUONG.md.' }
$env:PATH = (Join-Path $projectRoot 'tools/ffmpeg/bin') + [IO.Path]::PathSeparator + $env:PATH
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_HOME = Join-Path $projectRoot 'var/hf'
$env:PYTHONPYCACHEPREFIX = Join-Path $projectRoot 'var/pycache'
& $pythonPath (Join-Path $projectRoot 'run.py') @TaskArgs
exit $LASTEXITCODE
