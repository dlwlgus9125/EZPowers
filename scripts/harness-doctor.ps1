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
    $ArtifactKind = ''
    if ($Config.smoke.PSObject.Properties.Name -contains 'artifact_kind') {
        $ArtifactKind = [string]$Config.smoke.artifact_kind
    }
    $GuiStrategy = ''
    if ($Config.smoke.PSObject.Properties.Name -contains 'gui_strategy') {
        $GuiStrategy = [string]$Config.smoke.gui_strategy
    }
    if ($ArtifactKind -in @('cli', 'server', 'desktop') -and -not $Required) {
        Write-Check 'FAIL' 'smoke' "artifact_kind=$ArtifactKind requires smoke.required=true"
        $Failures++
    }
    elseif ($Required -and [string]::IsNullOrWhiteSpace($Command)) {
        Write-Check 'FAIL' 'smoke' 'required=true but command is empty'
        $Failures++
    }
    elseif ($ArtifactKind -eq 'desktop' -and $GuiStrategy -eq 'skip') {
        Write-Check 'FAIL' 'smoke' 'desktop artifact cannot use gui_strategy=skip'
        $Failures++
    }
    else {
        Write-Check 'PASS' 'smoke' "required=$Required"
    }

    $BuildCommand = ''
    if ($Config.PSObject.Properties.Name -contains 'build' -and $Config.build.PSObject.Properties.Name -contains 'command') {
        $BuildCommand = [string]$Config.build.command
    }
    $TestCommand = ''
    if ($Config.PSObject.Properties.Name -contains 'test' -and $Config.test.PSObject.Properties.Name -contains 'command') {
        $TestCommand = [string]$Config.test.command
    }
    if ($Required -and -not [string]::IsNullOrWhiteSpace($Command)) {
        foreach ($Pair in @(@('build.command', $BuildCommand), @('test.command', $TestCommand))) {
            if (-not [string]::IsNullOrWhiteSpace($Pair[1]) -and $Command.Trim() -eq $Pair[1].Trim()) {
                Write-Check 'FAIL' 'smoke parity' "smoke.command matches $($Pair[0]); use the real app entry point"
                $Failures++
            }
        }
    }
}
else {
    Write-Check 'FAIL' 'smoke' 'missing smoke config'
    $Failures++
}

if ($Config.PSObject.Properties.Name -contains 'wiring') {
    $Wiring = $Config.wiring
    $Enabled = $false
    if ($Wiring.PSObject.Properties.Name -contains 'enabled') {
        $Enabled = [bool]$Wiring.enabled
    }
    $ExemptReason = ''
    if ($Wiring.PSObject.Properties.Name -contains 'exempt_reason') {
        $ExemptReason = [string]$Wiring.exempt_reason
    }
    $Kind = ''
    if ($Config.PSObject.Properties.Name -contains 'smoke' -and $Config.smoke.PSObject.Properties.Name -contains 'artifact_kind') {
        $Kind = [string]$Config.smoke.artifact_kind
    }
    if (-not $Enabled -and [string]::IsNullOrWhiteSpace($ExemptReason)) {
        Write-Check 'FAIL' 'wiring' 'wiring disabled without exempt_reason'
        $Failures++
    }
    elseif (-not $Enabled -and $Kind -notin @('docs', 'library')) {
        Write-Check 'FAIL' 'wiring' "wiring exemption not allowed for artifact_kind: $Kind"
        $Failures++
    }
    else {
        Write-Check 'PASS' 'wiring' "enabled=$Enabled"
    }
}
else {
    Write-Check 'FAIL' 'wiring' 'missing wiring config'
    $Failures++
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
