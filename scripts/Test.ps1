param([switch]$RealAdapters)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
if($RealAdapters) { $env:NHOM12_RUN_MEDIA_TESTS = '1' } else { $env:NHOM12_RUN_MEDIA_TESTS = '0' }
& (Join-Path $projectRoot '.venv/Scripts/python.exe') (Join-Path $projectRoot 'scripts/run_tests.py')
exit $LASTEXITCODE
