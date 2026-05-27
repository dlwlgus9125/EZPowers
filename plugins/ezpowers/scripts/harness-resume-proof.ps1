param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path,

    [string] $PlanPath = '',

    [int] $CompletedTaskCount = 0,

    [string] $ResumeHash = ''
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'harness-common.ps1')

$PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
$ProofPath = Join-Path $PhaseDir 'resume-proof.json'
$Failures = New-Object System.Collections.ArrayList
$VerifiedGatePaths = New-Object System.Collections.ArrayList
$RuntimeArtifacts = @()

function Add-ResumeFailure {
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

function Resolve-ResumeStatus {
    param($Items)

    foreach ($Status in @('code_gap', 'spec_gap', 'fail', 'test_gap', 'review_pending')) {
        if (@($Items | Where-Object { $_.status -eq $Status }).Count -gt 0) {
            return $Status
        }
    }
    return 'test_gap'
}

function Save-ResumeProof {
    param(
        [string] $Status,
        [string] $EvidenceStatus,
        [string] $Message,
        [AllowNull()] $Index = $null
    )

    if (-not (Test-Path -LiteralPath $PhaseDir)) {
        New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null
    }

    $Proof = [pscustomobject]@{
        schema_version = 1
        phase = $Phase
        plan_path = $PlanPath
        completed_task_count = $CompletedTaskCount
        resume_hash = $ResumeHash
        status = $Status
        evidence_status = $EvidenceStatus
        message = $Message
        steps_total = if ($null -ne $Index) { @($Index.steps).Count } else { 0 }
        verified_task_gate_paths = @($VerifiedGatePaths)
        runtime_artifacts = @($RuntimeArtifacts)
        failures = @($Failures)
        checked_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    Save-EzpJson $Proof $ProofPath 50
    return $Proof
}

if ($CompletedTaskCount -lt 0) {
    Add-ResumeFailure 'spec_gap' 'invalid_completed_task_count' '-CompletedTaskCount must be zero or greater'
    $Proof = Save-ResumeProof -Status 'spec_gap' -EvidenceStatus 'resume_proof_failed' -Message '-CompletedTaskCount must be zero or greater'
    Write-Output "Harness resume proof status: $($Proof.status) ($($Proof.message))"
    exit (Get-EzpGateExitCode $Proof.status)
}

if (-not (Test-Path -LiteralPath $PhaseDir)) {
    Add-ResumeFailure 'test_gap' 'missing_phase' "phase directory not found: $PhaseDir"
    $Proof = Save-ResumeProof -Status 'test_gap' -EvidenceStatus 'resume_proof_failed' -Message 'phase directory missing'
    Write-Output "Harness resume proof status: $($Proof.status) ($($Proof.message))"
    exit (Get-EzpGateExitCode $Proof.status)
}

$Index = $null
try {
    $Index = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
}
catch {
    Add-ResumeFailure 'test_gap' 'missing_phase_index' $_.Exception.Message
}

if ($null -ne $Index) {
    $Steps = @($Index.steps)
    if ($CompletedTaskCount -gt $Steps.Count) {
        Add-ResumeFailure 'spec_gap' 'completed_prefix_exceeds_steps' "requested $CompletedTaskCount completed tasks but phase has $($Steps.Count) steps"
    }

    $Limit = [Math]::Min($CompletedTaskCount, $Steps.Count)
    for ($TaskNumber = 1; $TaskNumber -le $Limit; $TaskNumber++) {
        $StepNumber = $TaskNumber - 1
        $Step = $Steps |
            Where-Object { [int](Get-EzpConfigValue $_ 'step' -1) -eq $StepNumber } |
            Select-Object -First 1

        if (-not $Step) {
            Add-ResumeFailure 'test_gap' 'missing_step' "missing step $StepNumber for Task $TaskNumber" $StepNumber $TaskNumber
            continue
        }

        $StepStatus = [string](Get-EzpConfigValue $Step 'status' '')
        $StepMdName = [string](Get-EzpConfigValue $Step 'step_md' "step$StepNumber.md")
        $StepMdPath = Join-Path $PhaseDir $StepMdName
        $GatePath = Get-EzpTaskGatePath -ProjectRoot $ProjectRoot -Phase $Phase -TaskNumber $TaskNumber
        [void]$VerifiedGatePaths.Add((Join-Path 'task-gates' "task-$TaskNumber.json"))

        if ($StepStatus -ne 'completed') {
            Add-ResumeFailure 'test_gap' 'step_not_completed' "step $StepNumber status is $StepStatus" $StepNumber $TaskNumber
            continue
        }

        if (-not (Test-Path -LiteralPath $GatePath)) {
            Add-ResumeFailure 'test_gap' 'missing_task_gate' "missing task gate evidence: $GatePath" $StepNumber $TaskNumber
            continue
        }

        $Gate = $null
        try {
            $Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json
        }
        catch {
            Add-ResumeFailure 'test_gap' 'invalid_task_gate' "invalid task gate evidence: $($_.Exception.Message)" $StepNumber $TaskNumber
            continue
        }

        if ([int](Get-EzpConfigValue $Gate 'schema_version' 0) -ne 1) {
            Add-ResumeFailure 'test_gap' 'invalid_task_gate_schema' "task $TaskNumber gate schema_version is $($Gate.schema_version)" $StepNumber $TaskNumber
        }
        if ([string](Get-EzpConfigValue $Gate 'status' '') -ne 'pass') {
            Add-ResumeFailure 'fail' 'task_gate_not_pass' "task $TaskNumber gate status is $($Gate.status)" $StepNumber $TaskNumber
        }
        if ([int](Get-EzpConfigValue $Gate 'verify_exit_code' -1) -ne 0) {
            Add-ResumeFailure 'fail' 'verify_exit_nonzero' "task $TaskNumber verify exit code is $($Gate.verify_exit_code)" $StepNumber $TaskNumber
        }
        if ([bool](Get-EzpConfigValue $Gate 'verify_timed_out' $false)) {
            Add-ResumeFailure 'fail' 'verify_timeout' "task $TaskNumber verify timed out" $StepNumber $TaskNumber
        }
        if (-not [bool](Get-EzpConfigValue (Get-EzpConfigValue $Gate 'verify_result' $null) 'pass' $false)) {
            Add-ResumeFailure 'fail' 'verify_result_not_pass' "task $TaskNumber verify result is not pass" $StepNumber $TaskNumber
        }

        $CommandCount = [int](Get-EzpConfigValue $Gate 'verify_commands_count' 0)
        if ($CommandCount -lt 1) {
            $CommandCount = @((Get-EzpConfigValue $Gate 'verify_commands' @())).Count
        }
        if ($CommandCount -lt 1) {
            Add-ResumeFailure 'test_gap' 'missing_verify_command_evidence' "task $TaskNumber has no recorded Verify command" $StepNumber $TaskNumber
        }

        $RecordedHash = [string](Get-EzpConfigValue $Gate 'step_sha256' '')
        $CurrentHash = Get-EzpStepFileHash $StepMdPath
        if ([string]::IsNullOrWhiteSpace($CurrentHash)) {
            Add-ResumeFailure 'test_gap' 'missing_step_file' "step file missing: $StepMdPath" $StepNumber $TaskNumber
        }
        elseif ([string]::IsNullOrWhiteSpace($RecordedHash) -or $RecordedHash -ne $CurrentHash) {
            Add-ResumeFailure 'test_gap' 'stale_task_gate' "task $TaskNumber gate does not match current step file" $StepNumber $TaskNumber
        }

        $VerifyType = [string](Get-EzpConfigValue $Gate 'verify_type' '')
        if ($VerifyType -eq 'e2e') {
            if ($CommandCount -lt 1) {
                Add-ResumeFailure 'test_gap' 'missing_e2e_command' "task $TaskNumber e2e proof has no command evidence" $StepNumber $TaskNumber
            }
            if ([int](Get-EzpConfigValue $Gate 'verify_timeout_seconds' 0) -lt 120) {
                Add-ResumeFailure 'test_gap' 'e2e_timeout_too_short' "task $TaskNumber e2e proof used less than 120s timeout" $StepNumber $TaskNumber
            }
        }
    }
}

if ($CompletedTaskCount -gt 0) {
    $Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
    if ($null -eq $Config) {
        Add-ResumeFailure 'test_gap' 'missing_config' 'missing .harness/config.json'
    }
    else {
        $RuntimeEvidence = Test-EzpRuntimeEvidence -ProjectRoot $ProjectRoot -Phase $Phase -Config $Config
        $RuntimeArtifacts = @($RuntimeEvidence.artifacts)
        if (-not [bool]$RuntimeEvidence.ok) {
            Add-ResumeFailure 'test_gap' 'runtime_evidence_missing' $RuntimeEvidence.message
        }
    }
}

if ($Failures.Count -gt 0) {
    $Status = Resolve-ResumeStatus $Failures
    $First = @($Failures)[0]
    $Proof = Save-ResumeProof -Status $Status -EvidenceStatus 'resume_proof_failed' -Message $First.message -Index $Index
    Write-Output "Harness resume proof status: $($Proof.status) ($($Proof.message))"
    exit (Get-EzpGateExitCode $Proof.status)
}

$Message = if ($CompletedTaskCount -gt 0) {
    "completed task prefix 1-$CompletedTaskCount is verified"
}
else {
    'no completed task prefix requested'
}
$Proof = Save-ResumeProof -Status 'pass' -EvidenceStatus 'resume_prefix_verified' -Message $Message -Index $Index
Write-Output "Harness resume proof status: $($Proof.status) ($($Proof.message))"
exit 0
