param(
    [string] $ProjectRoot = (Get-Location).Path,
    [string] $Phase = ''
)

$ErrorActionPreference = 'Stop'

function Write-Check {
    param(
        [string] $Status,
        [string] $Name,
        [string] $Detail
    )
    Write-Output "[$Status] $Name - $Detail"
}

$Failures = 0
$Warnings = 0
$ConfigPath = Join-Path $ProjectRoot '.harness/config.json'

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    Write-Check 'FAIL' 'config' "missing $ConfigPath"
    exit 1
}

$Config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Check 'PASS' 'config' $ConfigPath

$HarnessRoot = ''
if ($Config.PSObject.Properties.Name -contains 'harness' -and $Config.harness.PSObject.Properties.Name -contains 'root') {
    $HarnessRoot = [string]$Config.harness.root
}

if ([string]::IsNullOrWhiteSpace($HarnessRoot)) {
    Write-Check 'FAIL' 'harness.root' 'empty; /executeharness is disabled'
    $Failures++
}
else {
    $ExecutePath = Join-Path $HarnessRoot 'scripts/execute.py'
    if (Test-Path -LiteralPath $ExecutePath) {
        Write-Check 'PASS' 'execute.py' $ExecutePath
    }
    else {
        Write-Check 'FAIL' 'execute.py' "missing $ExecutePath"
        $Failures++
    }
}

$BackupIndex = Join-Path $ProjectRoot 'phases/index.ezpowers.json'
if (Test-Path -LiteralPath $BackupIndex) {
    Write-Check 'WARN' 'index backup' 'phases/index.ezpowers.json exists; restore or discard before continuing'
    $Warnings++
}
else {
    Write-Check 'PASS' 'index backup' 'no stale phases/index.ezpowers.json'
}

if (-not [string]::IsNullOrWhiteSpace($Phase)) {
    $PhaseIndex = Join-Path $ProjectRoot "phases/$Phase/index.json"
    if (Test-Path -LiteralPath $PhaseIndex) {
        $PhaseData = Get-Content -LiteralPath $PhaseIndex -Raw -Encoding UTF8 | ConvertFrom-Json
        $Pending = @($PhaseData.steps | Where-Object { $_.status -eq 'pending' }).Count
        Write-Check 'PASS' 'phase index' "$PhaseIndex ($Pending pending)"
    }
    else {
        Write-Check 'WARN' 'phase index' "missing $PhaseIndex; conversion required"
        $Warnings++
    }
}

if ($Config.PSObject.Properties.Name -contains 'smoke') {
    $Required = $false
    if ($Config.smoke.PSObject.Properties.Name -contains 'required') {
        $Required = [bool]$Config.smoke.required
    }
    $Command = ''
    if ($Config.smoke.PSObject.Properties.Name -contains 'command') {
        $Command = [string]$Config.smoke.command
    }
    if ($Required -and [string]::IsNullOrWhiteSpace($Command)) {
        Write-Check 'WARN' 'smoke' 'required=true but command is empty'
        $Warnings++
    }
    else {
        Write-Check 'PASS' 'smoke' "required=$Required"
    }
}
else {
    Write-Check 'WARN' 'smoke' 'missing smoke config'
    $Warnings++
}

if ($Config.PSObject.Properties.Name -contains 'executor' -and $Config.executor.PSObject.Properties.Name -contains 'reviewer_backend') {
    Write-Check 'PASS' 'reviewer_backend' ([string]$Config.executor.reviewer_backend)
}
else {
    Write-Check 'PASS' 'reviewer_backend' 'claude-code default'
}

if ($Failures -gt 0) {
    Write-Output "Harness doctor verdict: FAIL ($Failures failure(s), $Warnings warning(s))"
    exit 1
}

Write-Output "Harness doctor verdict: PASS ($Warnings warning(s))"
