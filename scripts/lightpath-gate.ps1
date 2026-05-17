param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('prepare', 'task', 'final')]
    [string] $Scope,

    [string] $ProjectRoot = (Get-Location).Path,

    [string] $PlanPath = '',

    [string] $Phase = '',

    [int] $TaskNumber = 0,

    [string] $DiffRange = '',

    [ValidateSet('', 'PASS', 'TEST_GAP', 'CODE_GAP', 'SPEC_GAP')]
    [string] $ReviewerVerdict = '',

    [int] $TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'harness-common.ps1')

function Get-LightpathSlug {
    param([string] $Name)

    $Slug = [IO.Path]::GetFileNameWithoutExtension($Name)
    $Slug = $Slug -replace '^\d{4}-\d{2}-\d{2}-', ''
    $Slug = $Slug.ToLowerInvariant() -replace '[^a-z0-9]+', '-'
    $Slug = $Slug.Trim('-')
    if ([string]::IsNullOrWhiteSpace($Slug)) {
        return 'phase'
    }
    return $Slug
}

function Get-LightpathPhaseDir {
    return Join-Path $ProjectRoot "phases/$Phase"
}

function Get-LightpathStatePath {
    return Join-Path (Get-LightpathPhaseDir) 'lightpath-gate.json'
}

function Get-LightpathRuntimeArtifacts {
    $PhaseDir = Get-LightpathPhaseDir
    $Artifacts = @()
    foreach ($Name in @('runtime-probe.json', 'smoke-output.json')) {
        if (Test-Path -LiteralPath (Join-Path $PhaseDir $Name)) {
            $Artifacts += $Name
        }
    }
    return $Artifacts
}

function Save-LightpathState {
    param(
        [string] $Status,
        [string] $EvidenceStatus = '',
        [string] $Message = '',
        $TaskResult = $null,
        $Gate = $null,
        [int] $GateExitCode = 0
    )

    $PhaseDir = Get-LightpathPhaseDir
    if (-not (Test-Path -LiteralPath $PhaseDir)) {
        New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null
    }

    $State = [pscustomobject]@{
        mode = 'lightpath'
        scope = $Scope
        phase = $Phase
        plan_path = $PlanPath
        diff_range = $DiffRange
        task_number = if ($TaskNumber -gt 0) { $TaskNumber } else { $null }
        status = $Status
        evidence_status = $EvidenceStatus
        message = $Message
        wiring_gate_path = Join-Path $PhaseDir 'wiring-gate.json'
        runtime_artifacts = @(Get-LightpathRuntimeArtifacts)
        gate_exit_code = $GateExitCode
        task_result = $TaskResult
        wiring_gate = $Gate
        updated_at = (Get-Date).ToUniversalTime().ToString('o')
    }
    Save-EzpJson $State (Get-LightpathStatePath) 30
    return $State
}

function Require-Phase {
    if ([string]::IsNullOrWhiteSpace($Phase)) {
        throw '-Phase is required for this lightpath gate scope'
    }
}

function Get-LightpathStep {
    param([int] $Task)

    $Index = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
    $StepNumber = $Task - 1
    return $Index.steps |
        Where-Object { [int]$_.step -eq $StepNumber } |
        Select-Object -First 1
}

function Set-LightpathReviewerVerdict {
    param([string] $Verdict)

    if ([string]::IsNullOrWhiteSpace($Verdict)) {
        return
    }

    $GatePath = Join-Path (Get-LightpathPhaseDir) 'wiring-gate.json'
    if (-not (Test-Path -LiteralPath $GatePath)) {
        throw "Wiring gate not found: $GatePath"
    }
    $Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not ($Gate.PSObject.Properties.Name -contains 'reviewer_verdict')) {
        $Gate | Add-Member -NotePropertyName reviewer_verdict -NotePropertyValue '' -Force
    }
    $Gate.reviewer_verdict = $Verdict
    if (-not [string]::IsNullOrWhiteSpace($DiffRange)) {
        if (-not ($Gate.PSObject.Properties.Name -contains 'diff_range')) {
            $Gate | Add-Member -NotePropertyName diff_range -NotePropertyValue '' -Force
        }
        $Gate.diff_range = $DiffRange
    }
    Save-EzpJson $Gate $GatePath 20
}

if ($Scope -eq 'prepare') {
    if ([string]::IsNullOrWhiteSpace($PlanPath)) {
        throw '-PlanPath is required for lightpath prepare'
    }

    $PlanFullPath = if ([IO.Path]::IsPathRooted($PlanPath)) { $PlanPath } else { Join-Path $ProjectRoot $PlanPath }
    if (-not (Test-Path -LiteralPath $PlanFullPath)) {
        throw "Plan not found: $PlanFullPath"
    }
    if ([string]::IsNullOrWhiteSpace($Phase)) {
        $Phase = Get-LightpathSlug $PlanFullPath
    }

    & (Join-Path $PSScriptRoot 'harness-convert.ps1') -ProjectRoot $ProjectRoot -PlanPath $PlanFullPath -Phase $Phase | Out-Null
    $State = Save-LightpathState -Status 'prepared' -EvidenceStatus 'phase_prepared' -Message 'lightpath phase artifacts prepared'
    Write-Output "Lightpath gate prepared: $($State.phase)"
    exit 0
}

Require-Phase

if ($Scope -eq 'task') {
    if ($TaskNumber -lt 1) {
        throw '-TaskNumber must be the one-indexed plan task number'
    }

    $Step = Get-LightpathStep -Task $TaskNumber
    if (-not $Step) {
        $State = Save-LightpathState `
            -Status 'spec_gap' `
            -EvidenceStatus 'missing_step' `
            -Message "Task $TaskNumber has no converted step"
        Write-Output "Lightpath task gate status: $($State.status) ($($State.message))"
        exit 2
    }

    $StepNumber = [int]$Step.step
    $StepMdName = if ($Step.PSObject.Properties.Name -contains 'step_md' -and -not [string]::IsNullOrWhiteSpace([string]$Step.step_md)) {
        [string]$Step.step_md
    }
    else {
        "step${StepNumber}.md"
    }
    $StepMdPath = Join-Path $ProjectRoot "phases/$Phase/$StepMdName"
    $Verify = Invoke-EzpVerifyStep -ProjectRoot $ProjectRoot -Phase $Phase -StepMdPath $StepMdPath -TimeoutSeconds 30

    $TaskResult = [pscustomobject]@{
        task_number = $TaskNumber
        step = $StepNumber
        step_md = $StepMdName
        verify_exit_code = [int]$Verify.exit_code
        verify_timed_out = [bool]$Verify.timed_out
        verify_result = $Verify.result
        smoke_exit_code = $null
        smoke_timed_out = $null
    }

    if ($Verify.exit_code -ne 0 -or $Verify.timed_out) {
        Set-EzpStepStatus -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Status 'rejected'
        $State = Save-LightpathState `
            -Status 'fail' `
            -EvidenceStatus 'verify_failed' `
            -Message "verify-step.py rejected Task $TaskNumber" `
            -TaskResult $TaskResult
        Write-Output "Lightpath task gate status: $($State.status) ($($State.message))"
        exit 1
    }

    $SmokeResult = Invoke-EzpRuntimeSmokeIfConfigured -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber
    if ($null -ne $SmokeResult) {
        $TaskResult.smoke_exit_code = [int]$SmokeResult.exit_code
        $TaskResult.smoke_timed_out = [bool]$SmokeResult.timed_out
        if ($SmokeResult.exit_code -ne 0 -or $SmokeResult.timed_out) {
            Set-EzpStepStatus -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Status 'error'
            $State = Save-LightpathState `
                -Status 'fail' `
                -EvidenceStatus 'smoke_failed' `
                -Message "runtime smoke failed for Task $TaskNumber" `
                -TaskResult $TaskResult
            Write-Output "Lightpath task gate status: $($State.status) ($($State.message))"
            exit 1
        }
    }

    Set-EzpStepStatus -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Status 'completed'
    $State = Save-LightpathState `
        -Status 'pass' `
        -EvidenceStatus 'task_verified' `
        -Message "Task $TaskNumber verified" `
        -TaskResult $TaskResult
    Write-Output "Lightpath task gate status: $($State.status) ($($State.message))"
    exit 0
}

if ($Scope -eq 'final') {
    Set-LightpathReviewerVerdict -Verdict $ReviewerVerdict

    $GateScript = Join-Path $PSScriptRoot 'harness-gate.ps1'
    $GateResult = Invoke-EzpExternalProcess `
        -ProjectRoot $ProjectRoot `
        -FilePath 'powershell.exe' `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $GateScript, '-ProjectRoot', $ProjectRoot, '-Phase', $Phase, '-TimeoutSeconds', ([string]$TimeoutSeconds)) `
        -TimeoutSeconds ([Math]::Max(1, $TimeoutSeconds + 10)) `
        -TimeoutMessage "harness-gate.ps1 timed out after $([Math]::Max(1, $TimeoutSeconds + 10))s"

    $GatePath = Join-Path (Get-LightpathPhaseDir) 'wiring-gate.json'
    $Gate = if (Test-Path -LiteralPath $GatePath) {
        Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    else {
        $null
    }
    $Status = if ($null -ne $Gate -and $Gate.PSObject.Properties.Name -contains 'status') {
        [string]$Gate.status
    }
    else {
        'test_gap'
    }

    if ($GateResult.timed_out) {
        $Status = 'fail'
    }

    $Message = if ($Status -eq 'review_pending') {
        'wiring reviewer verdict required'
    }
    elseif ($GateResult.exit_code -ne 0) {
        Get-EzpTail ($GateResult.stderr + $GateResult.stdout)
    }
    else {
        'final wiring gate evaluated'
    }

    $State = Save-LightpathState `
        -Status $Status `
        -EvidenceStatus 'final_gate' `
        -Message $Message `
        -Gate $Gate `
        -GateExitCode ([int]$GateResult.exit_code)
    Write-Output "Lightpath final gate status: $($State.status) ($($State.message))"
    exit (Get-EzpGateExitCode $Status)
}
