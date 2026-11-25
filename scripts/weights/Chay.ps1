# Run one step of the weight-selection procedure (see README.md in this folder).
#   ./scripts/weights/Chay.ps1 chon                                   -> step 4: select and lock the weights
#   ./scripts/weights/Chay.ps1 test -Anh D:\test\anh -Nhan D:\test\nhan.csv   -> step 5: evaluate once on test images
#   ./scripts/weights/Chay.ps1 lai                                    -> rebuild steps 1-3 (validation set + survey)
param([Parameter(Mandatory=$true)][ValidateSet('chon','test','lai')][string]$Buoc, [string]$Anh, [string]$Nhan)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$here = $PSScriptRoot
$py = Join-Path $here '..\..\.venv\Scripts\python.exe'
switch ($Buoc) {
  'chon' { & $py (Join-Path $here 'w03_chon_he_so.py') }
  'test' {
    if (-not $Anh -or -not $Nhan) { throw 'Step test needs -Anh <image folder> -Nhan <labels.csv>' }
    & $py (Join-Path $here 'w04_danh_gia_test.py') --anh $Anh --nhan $Nhan
  }
  'lai'  { & $py (Join-Path $here 'w01_tao_tap_validation.py'); if ($LASTEXITCODE -eq 0) { & $py (Join-Path $here 'w02_khao_sat.py') } }
}
exit $LASTEXITCODE
