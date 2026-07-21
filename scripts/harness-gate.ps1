param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path,

    [int] $TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'harness-common.ps1')

$GatePath = Join-Path $ProjectRoot "phases/$Phase/wiring-gate.json"
if (-not (Test-Path -LiteralPath $GatePath)) {
    throw "Wiring gate not found: $GatePath"
}

function Save-Gate {
    param($Gate, [string] $Path)
    Save-EzpJson $Gate $Path 20
}

function Set-GateStatus {
    param(
        $Gate,
        [string] $Status,
        [string] $EvidenceStatus,
        [string] $Message,
        [int] $ExitCode
    )

    $Gate.status = $Status
    if (-not ($Gate.PSObject.Properties.Name -contains 'evidence_status')) {
        $Gate | Add-Member -NotePropertyName evidence_status -NotePropertyValue '' -Force
    }
    $Gate.evidence_status = $EvidenceStatus
    if (-not ($Gate.PSObject.Properties.Name -contains 'message')) {
        $Gate | Add-Member -NotePropertyName message -NotePropertyValue '' -Force
    }
    $Gate.message = $Message
    Save-Gate $Gate $GatePath
    Write-Output "Wiring gate status: $Status ($Message)"
    exit $ExitCode
}

function New-Attempt {
    param(
        [string] $Command,
        [int] $ExitCode,
        [string] $Stdout,
        [string] $Stderr
    )

    [pscustomobject]@{
        command = $Command
        exit_code = $ExitCode
        stdout_tail = Get-EzpTail $Stdout
        stderr_tail = Get-EzpTail $Stderr
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }
}

function Get-EvidenceFingerprint {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [object[]] $Commands,
        [object[]] $Artifacts
    )

    $PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
    $Parts = @()
    foreach ($Command in @($Commands)) {
        $Parts += "cmd:$([string]$Command)"
    }
    foreach ($Artifact in @($Artifacts)) {
        $Name = [string]$Artifact
        $Candidates = @()
        if ([IO.Path]::IsPathRooted($Name)) {
            $Candidates += $Name
        }
        else {
            $Candidates += (Join-Path $ProjectRoot $Name)
            $Candidates += (Join-Path $PhaseDir $Name)
        }
        $Hash = 'missing'
        foreach ($Candidate in $Candidates) {
            if (Test-Path -LiteralPath $Candidate) {
                $Hash = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash.ToLowerInvariant()
                break
            }
        }
        $Parts += "art:${Name}:$Hash"
    }

    $Bytes = [Text.Encoding]::UTF8.GetBytes(($Parts -join "`n"))
    $Sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $HashBytes = $Sha.ComputeHash($Bytes)
    }
    finally {
        $Sha.Dispose()
    }
    return ([BitConverter]::ToString($HashBytes) -replace '-', '').ToLowerInvariant()
}

$Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not [bool]$Gate.required) {
    $Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
    $Smoke = Get-EzpConfigValue $Config 'smoke' $null
    $ArtifactKind = [string](Get-EzpConfigValue $Smoke 'artifact_kind' '')
    if ($ArtifactKind -notin @('docs', 'library')) {
        Set-GateStatus $Gate 'fail' 'invalid_wiring_config' "wiring gate required=false not allowed for artifact_kind: $ArtifactKind" 1
    }
    $Gate.status = 'pass'
    Save-Gate $Gate $GatePath
    Write-Output "Wiring gate skipped: required=false (artifact_kind=$ArtifactKind)"
    exit 0
}

$Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
if ($null -eq $Config) {
    Set-GateStatus $Gate 'test_gap' 'missing_config' 'missing .harness/config.json' 3
}

$Smoke = Get-EzpConfigValue $Config 'smoke' $null
$ArtifactKind = [string](Get-EzpConfigValue $Smoke 'artifact_kind' '')
$Wiring = Get-EzpConfigValue $Config 'wiring' $null
if ($null -eq $Wiring) {
    Set-GateStatus $Gate 'test_gap' 'missing_wiring_config' 'config.json has no wiring block' 3
}

$WiringEnabled = [bool](Get-EzpConfigValue $Wiring 'enabled' $false)
$ExemptReason = [string](Get-EzpConfigValue $Wiring 'exempt_reason' '')
if (-not $WiringEnabled) {
    if ([string]::IsNullOrWhiteSpace($ExemptReason)) {
        Set-GateStatus $Gate 'test_gap' 'invalid_wiring_config' 'wiring disabled without exempt_reason' 3
    }
    if ($ArtifactKind -notin @('docs', 'library')) {
        Set-GateStatus $Gate 'fail' 'invalid_wiring_config' "wiring exemption not allowed for artifact_kind: $ArtifactKind" 1
    }
}

$Commands = @($Gate.commands)
if ($Commands.Count -eq 0) {
    Set-GateStatus $Gate 'spec_gap' 'missing_command' 'no commands' 2
}
foreach ($Command in $Commands) {
    if (Test-EzpTrivialCommand $Command) {
        Set-GateStatus $Gate 'spec_gap' 'trivial_command' "trivial wiring gate command: $Command" 2
    }
}

if (-not ($Gate.PSObject.Properties.Name -contains 'attempts') -or $null -eq $Gate.attempts) {
    $Gate | Add-Member -NotePropertyName attempts -NotePropertyValue @() -Force
}

$Attempts = @($Gate.attempts)
foreach ($Command in $Commands) {
    $Result = Invoke-EzpPowershellCommand -ProjectRoot $ProjectRoot -Command $Command -TimeoutSeconds $TimeoutSeconds
    $Attempts += New-Attempt $Command $Result.exit_code $Result.stdout $Result.stderr

    if ($Result.exit_code -ne 0 -or $Result.timed_out) {
        $Gate.attempts = $Attempts
        $Gate.status = 'fail'
        Save-Gate $Gate $GatePath
        Write-Output "Wiring gate status: fail ($Command)"
        exit 1
    }
}

$Gate.attempts = $Attempts
$RuntimeEvidence = Test-EzpRuntimeEvidence -ProjectRoot $ProjectRoot -Phase $Phase -Config $Config -Gate $Gate
if (-not ($Gate.PSObject.Properties.Name -contains 'runtime_artifacts')) {
    $Gate | Add-Member -NotePropertyName runtime_artifacts -NotePropertyValue @() -Force
}
$Gate.runtime_artifacts = @($RuntimeEvidence.artifacts)
if (-not $RuntimeEvidence.ok) {
    $Gate.status = 'test_gap'
    if (-not ($Gate.PSObject.Properties.Name -contains 'evidence_status')) {
        $Gate | Add-Member -NotePropertyName evidence_status -NotePropertyValue '' -Force
    }
    $Gate.evidence_status = 'runtime_gap'
    if (-not ($Gate.PSObject.Properties.Name -contains 'message')) {
        $Gate | Add-Member -NotePropertyName message -NotePropertyValue '' -Force
    }
    $Gate.message = $RuntimeEvidence.message
    Save-Gate $Gate $GatePath
    Write-Output "Wiring gate status: test_gap ($($RuntimeEvidence.message))"
    exit 3
}

$EvidenceFingerprint = Get-EvidenceFingerprint -ProjectRoot $ProjectRoot -Phase $Phase -Commands $Commands -Artifacts $Gate.runtime_artifacts
if (-not ($Gate.PSObject.Properties.Name -contains 'evidence_fingerprint')) {
    $Gate | Add-Member -NotePropertyName evidence_fingerprint -NotePropertyValue '' -Force
}
$Gate.evidence_fingerprint = $EvidenceFingerprint
if (-not ($Gate.PSObject.Properties.Name -contains 'message')) {
    $Gate | Add-Member -NotePropertyName message -NotePropertyValue '' -Force
}

$Verdict = [string](Get-EzpConfigValue $Gate 'reviewer_verdict' '')
$VerdictFingerprint = [string](Get-EzpConfigValue $Gate 'verdict_fingerprint' '')
if ($Verdict) {
    if ([string]::IsNullOrWhiteSpace($VerdictFingerprint)) {
        $Gate.status = 'review_pending'
        $Gate.message = 'reviewer_verdict is not bound to current evidence (missing verdict_fingerprint)'
    }
    elseif ($VerdictFingerprint -ne $EvidenceFingerprint) {
        $Gate.status = 'review_pending'
        $Gate.message = "reviewer_verdict fingerprint does not match current evidence (verdict=$VerdictFingerprint evidence=$EvidenceFingerprint)"
    }
    else {
        switch ($Verdict) {
            'PASS' { $Gate.status = 'pass' }
            'TEST_GAP' { $Gate.status = 'test_gap' }
            'CODE_GAP' { $Gate.status = 'code_gap' }
            'SPEC_GAP' { $Gate.status = 'spec_gap' }
            default { $Gate.status = 'test_gap' }
        }
        $Gate.message = "reviewer_verdict $Verdict accepted for bound evidence"
    }
}
else {
    $Gate.status = 'review_pending'
    $Gate.message = 'reviewer verdict required'
}
if (-not ($Gate.PSObject.Properties.Name -contains 'evidence_status')) {
    $Gate | Add-Member -NotePropertyName evidence_status -NotePropertyValue '' -Force
}
$Gate.evidence_status = 'command_passed'
Save-Gate $Gate $GatePath
Write-Output "Wiring gate status: $($Gate.status)"
switch ($Gate.status) {
    'pass' { exit 0 }
    'review_pending' { exit 5 }
    'fail' { exit 1 }
    'spec_gap' { exit 2 }
    'test_gap' { exit 3 }
    'code_gap' { exit 4 }
    default { exit 3 }
}
