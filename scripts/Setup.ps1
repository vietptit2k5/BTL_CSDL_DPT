param(
    [Parameter(Mandatory=$true)][string]$SourcePython,
    [Parameter(Mandatory=$true)][string]$SourceModel,
    [Parameter(Mandatory=$true)][string]$SourceFFmpegBin
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$venvRoot = Join-Path $projectRoot '.venv'
$pythonPath = Join-Path $venvRoot 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & $SourcePython -m venv --without-pip $venvRoot
    if($LASTEXITCODE -ne 0){throw 'Failed to create project venv'}
}
& $SourcePython (Join-Path $PSScriptRoot 'bootstrap_from_local.py') --target $venvRoot
if($LASTEXITCODE -ne 0){throw 'Dependency copy failed'}

function Copy-VerifiedFile([string]$From,[string]$To) {
    if(Test-Path -LiteralPath $To){
        if((Get-FileHash -LiteralPath $From -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $To -Algorithm SHA256).Hash){return}
    }
    Copy-Item -LiteralPath $From -Destination $To
}
$modelTarget=Join-Path $projectRoot 'models/clip-vit-base-patch32'
$binaryTarget=Join-Path $projectRoot 'tools/ffmpeg/bin'
New-Item -ItemType Directory -Force -Path $modelTarget,$binaryTarget | Out-Null
Get-ChildItem -LiteralPath $SourceModel -File | ForEach-Object { Copy-VerifiedFile $_.FullName (Join-Path $modelTarget $_.Name) }
foreach($name in @('ffmpeg.exe','ffprobe.exe')) { Copy-VerifiedFile (Join-Path $SourceFFmpegBin $name) (Join-Path $binaryTarget $name) }
& $pythonPath -m pip check
if($LASTEXITCODE -ne 0){throw 'Dependency consistency check failed'}
Write-Output 'Project environment copied independently. Run scripts/Run.ps1 doctor --deep next.'
