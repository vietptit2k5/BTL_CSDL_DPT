param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'Run.ps1') serve --port $Port
exit $LASTEXITCODE
