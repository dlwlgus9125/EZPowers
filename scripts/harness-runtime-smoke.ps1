$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = if ($env:EZP_PYTHON) { $env:EZP_PYTHON } else { 'python' }

Push-Location $RepoRoot
try {
    & $Python (Join-Path $RepoRoot 'scripts/runtime_smoke.py')
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
