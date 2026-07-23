<#
.SYNOPSIS
    PowerShell wrapper for the cross-platform EZPowers repository gate.

.DESCRIPTION
    Delegates whole-repository structural validation to scripts/check_repo.py
    and preserves its exit code.

.PARAMETER WithTests
    Also run `python -m unittest discover -s tests` through the Python gate.
#>
param(
    [switch] $WithTests
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = if ($env:EZP_PYTHON) { $env:EZP_PYTHON } else { 'python' }
$GateArgs = @(
    (Join-Path $PSScriptRoot 'check_repo.py'),
    '--repo-root',
    $RepoRoot
)

if ($WithTests) {
    $GateArgs += '--with-tests'
}

& $Python @GateArgs
exit $LASTEXITCODE
