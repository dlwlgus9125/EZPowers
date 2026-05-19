param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'harness-common.ps1')

$PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
$CertificatePath = Join-Path $PhaseDir 'completion-certificate.json'
$Failures = New-Object System.Collections.ArrayList
$TaskGatePaths = New-Object System.Collections.ArrayList
$RuntimeArtifacts = @()

function Add-CertFailure {
    param(
        [string] $Status,
        [string] $EvidenceStatus,
        [string] $Message,
        [AllowNull()] $Step = $null,
        [AllowNull()] $TaskNumber = $null
    )

    [void]$Failures.Add([pscustomobject]@{
        status = $Status
        evidence_status = $EvidenceStatus
        message = $Message
        step = $Step
        task_number = $TaskNumber
    })
}

function Resolve-CertStatus {
    param($Items)

    foreach ($Status in @('code_gap', 'spec_gap', 'fail', 'test_gap', 'review_pending')) {
        if (@($Items | Where-Object { $_.status -eq $Status }).Count -gt 0) {
            return $Status
        }
    }
    return 'test_gap'
}

function Save-Certificate {
    param(
        [string] $Status,
        [string] $EvidenceStatus,
        [string] $Message,
        [AllowNull()] $Index = $null,
        [AllowNull()] $WiringGate = $null
    )

    if (-not (Test-Path -LiteralPath $PhaseDir)) {
        New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null
    }

    $Certificate = [pscustomobject]@{
        schema_version = 1
        phase = $Phase
        status = $Status
        evidence_status = $EvidenceStatus
        message = $Message
        steps_total = if ($null -ne $Index) { @($Index.steps).Count } else { 0 }
        task_gate_paths = @($TaskGatePaths)
        wiring_gate_path = Join-Path $PhaseDir 'wiring-gate.json'
        wiring_gate = $WiringGate
        runtime_artifacts = @($RuntimeArtifacts)
        failures = @($Failures)
        checked_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    Save-EzpJson $Certificate $CertificatePath 50
    return $Certificate
}

if (-not (Test-Path -LiteralPath $PhaseDir)) {
    Add-CertFailure 'test_gap' 'missing_phase' "phase directory not found: $PhaseDir"
    $Status = Resolve-CertStatus $Failures
    $Certificate = Save-Certificate -Status $Status -EvidenceStatus 'certification_failed' -Message 'phase directory missing'
    Write-Output "Harness certificate status: $($Certificate.status) ($($Certificate.message))"
    exit (Get-EzpGateExitCode $Certificate.status)
}

$Index = $null
try {
    $Index = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
}
catch {
    Add-CertFailure 'test_gap' 'missing_phase_index' $_.Exception.Message
}

if ($null -ne $Index) {
    $Steps = @($Index.steps)
    if ($Steps.Count -eq 0) {
        Add-CertFailure 'spec_gap' 'missing_steps' 'phase index has no steps'
    }

    foreach ($Step in $Steps) {
        $StepNumber = [int](Get-EzpConfigValue $Step 'step' -1)
        $TaskNumber = $StepNumber + 1
        $StepStatus = [string](Get-EzpConfigValue $Step 'status' '')
        $StepMdName = [string](Get-EzpConfigValue $Step 'step_md' "step$StepNumber.md")
        $StepMdPath = Join-Path $PhaseDir $StepMdName
        $GatePath = Get-EzpTaskGatePath -ProjectRoot $ProjectRoot -Phase $Phase -TaskNumber $TaskNumber
        [void]$TaskGatePaths.Add((Join-Path 'task-gates' "task-$TaskNumber.json"))

        if ($StepStatus -ne 'completed') {
            Add-CertFailure 'test_gap' 'step_not_completed' "step $StepNumber status is $StepStatus" $StepNumber $TaskNumber
            continue
        }

        if (-not (Test-Path -LiteralPath $GatePath)) {
            Add-CertFailure 'test_gap' 'missing_task_gate' "missing task gate evidence: $GatePath" $StepNumber $TaskNumber
            continue
        }

        $Gate = $null
        try {
            $Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            Add-CertFailure 'test_gap' 'invalid_task_gate' "invalid task gate evidence: $($_.Exception.Message)" $StepNumber $TaskNumber
            continue
        }

        if ([string](Get-EzpConfigValue $Gate 'status' '') -ne 'pass') {
            Add-CertFailure 'fail' 'task_gate_not_pass' "task $TaskNumber gate status is $($Gate.status)" $StepNumber $TaskNumber
        }
        if ([int](Get-EzpConfigValue $Gate 'verify_exit_code' -1) -ne 0) {
            Add-CertFailure 'fail' 'verify_exit_nonzero' "task $TaskNumber verify exit code is $($Gate.verify_exit_code)" $StepNumber $TaskNumber
        }
        if ([bool](Get-EzpConfigValue $Gate 'verify_timed_out' $false)) {
            Add-CertFailure 'fail' 'verify_timeout' "task $TaskNumber verify timed out" $StepNumber $TaskNumber
        }
        if (-not [bool](Get-EzpConfigValue (Get-EzpConfigValue $Gate 'verify_result' $null) 'pass' $false)) {
            Add-CertFailure 'fail' 'verify_result_not_pass' "task $TaskNumber verify result is not pass" $StepNumber $TaskNumber
        }

        $CommandCount = [int](Get-EzpConfigValue $Gate 'verify_commands_count' 0)
        if ($CommandCount -lt 1) {
            $CommandCount = @((Get-EzpConfigValue $Gate 'verify_commands' @())).Count
        }
        if ($CommandCount -lt 1) {
            Add-CertFailure 'test_gap' 'missing_verify_command_evidence' "task $TaskNumber has no recorded Verify command" $StepNumber $TaskNumber
        }

        $RecordedHash = [string](Get-EzpConfigValue $Gate 'step_sha256' '')
        $CurrentHash = Get-EzpStepFileHash $StepMdPath
        if ([string]::IsNullOrWhiteSpace($CurrentHash)) {
            Add-CertFailure 'test_gap' 'missing_step_file' "step file missing: $StepMdPath" $StepNumber $TaskNumber
        }
        elseif ([string]::IsNullOrWhiteSpace($RecordedHash) -or $RecordedHash -ne $CurrentHash) {
            Add-CertFailure 'test_gap' 'stale_task_gate' "task $TaskNumber gate does not match current step file" $StepNumber $TaskNumber
        }

        $VerifyType = [string](Get-EzpConfigValue $Gate 'verify_type' '')
        if ($VerifyType -eq 'e2e') {
            if ($CommandCount -lt 1) {
                Add-CertFailure 'test_gap' 'missing_e2e_command' "task $TaskNumber e2e proof has no command evidence" $StepNumber $TaskNumber
            }
            if ([int](Get-EzpConfigValue $Gate 'verify_timeout_seconds' 0) -lt 120) {
                Add-CertFailure 'test_gap' 'e2e_timeout_too_short' "task $TaskNumber e2e proof used less than 120s timeout" $StepNumber $TaskNumber
            }
        }
    }
}

$WiringGate = $null
$WiringPath = Join-Path $PhaseDir 'wiring-gate.json'
if (-not (Test-Path -LiteralPath $WiringPath)) {
    Add-CertFailure 'test_gap' 'missing_wiring_gate' "missing wiring gate: $WiringPath"
}
else {
    try {
        $WiringGate = Get-Content -LiteralPath $WiringPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $Required = [bool](Get-EzpConfigValue $WiringGate 'required' $false)
        $WiringStatus = [string](Get-EzpConfigValue $WiringGate 'status' '')
        if ($Required -and $WiringStatus -ne 'pass') {
            $Status = if ($WiringStatus -in @('fail', 'spec_gap', 'test_gap', 'code_gap', 'review_pending')) { $WiringStatus } else { 'test_gap' }
            Add-CertFailure $Status 'wiring_gate_not_pass' "wiring gate status is $WiringStatus"
        }
    }
    catch {
        Add-CertFailure 'test_gap' 'invalid_wiring_gate' "invalid wiring gate: $($_.Exception.Message)"
    }
}

$Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
if ($null -eq $Config) {
    Add-CertFailure 'test_gap' 'missing_config' 'missing .harness/config.json'
}
else {
    $RuntimeEvidence = Test-EzpRuntimeEvidence -ProjectRoot $ProjectRoot -Phase $Phase -Config $Config
    $RuntimeArtifacts = @($RuntimeEvidence.artifacts)
    if (-not [bool]$RuntimeEvidence.ok) {
        Add-CertFailure 'test_gap' 'runtime_evidence_missing' $RuntimeEvidence.message
    }
}

if ($Failures.Count -gt 0) {
    $Status = Resolve-CertStatus $Failures
    $First = @($Failures)[0]
    $Certificate = Save-Certificate -Status $Status -EvidenceStatus 'certification_failed' -Message $First.message -Index $Index -WiringGate $WiringGate
    Write-Output "Harness certificate status: $($Certificate.status) ($($Certificate.message))"
    exit (Get-EzpGateExitCode $Certificate.status)
}

$Certificate = Save-Certificate -Status 'pass' -EvidenceStatus 'certified' -Message 'all task gates and final gates are verified' -Index $Index -WiringGate $WiringGate
Write-Output "Harness certificate status: $($Certificate.status) ($($Certificate.message))"
exit 0
