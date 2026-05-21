param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path,

    [string] $HarnessRoot = '',

    [int] $TimeoutSeconds = 600,

    [int] $MaxSteps = 0,

    [string] $ExecutorCommand = '',

    [string] $ExplicitModel = ''
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'harness-common.ps1')

function Save-RunLog {
    param($Entries, [string] $Path)

    [pscustomobject]@{
        phase = $Phase
        updated_at = (Get-Date).ToUniversalTime().ToString('o')
        attempts = $Entries
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function New-Attempt {
    param(
        [int] $Step,
        [string] $Command,
        [int] $ExitCode,
        [bool] $TimedOut,
        [string] $BeforeStatus,
        [string] $AfterStatus,
        [string] $Stdout,
        [string] $Stderr
    )

    [pscustomobject]@{
        step = $Step
        command = $Command
        exit_code = $ExitCode
        timed_out = $TimedOut
        before_status = $BeforeStatus
        after_status = $AfterStatus
        stdout_tail = Get-EzpTail $Stdout
        stderr_tail = Get-EzpTail $Stderr
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }
}

function Read-ConfigHarnessRoot {
    $Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
    if ($null -eq $Config) {
        throw "Missing harness config: $(Join-Path $ProjectRoot '.harness/config.json')"
    }

    if ($Config.PSObject.Properties.Name -contains 'harness' -and $Config.harness.PSObject.Properties.Name -contains 'root') {
        return [string]$Config.harness.root
    }
    return ''
}

function Invoke-HarnessExecutor {
    param([string] $Command, [string] $ExecutePath)

    if ([string]::IsNullOrWhiteSpace($Command)) {
        return Invoke-EzpExternalProcess `
            -ProjectRoot $ProjectRoot `
            -FilePath 'python' `
            -Arguments @($ExecutePath, $Phase) `
            -TimeoutSeconds $TimeoutSeconds `
            -TimeoutMessage "Harness executor timed out after ${TimeoutSeconds}s"
    }

    return Invoke-EzpPowershellCommand -ProjectRoot $ProjectRoot -Command $Command -TimeoutSeconds $TimeoutSeconds
}

if ($TimeoutSeconds -lt 1) {
    throw 'TimeoutSeconds must be >= 1'
}

$IndexPath = Join-Path $ProjectRoot "phases/$Phase/index.json"
$RunLogPath = Join-Path $ProjectRoot "phases/$Phase/harness-run.json"
$RunAttempts = @()

$ExecutePath = ''
if ([string]::IsNullOrWhiteSpace($ExecutorCommand)) {
    if ([string]::IsNullOrWhiteSpace($HarnessRoot)) {
        $HarnessRoot = Read-ConfigHarnessRoot
    }
    if ([string]::IsNullOrWhiteSpace($HarnessRoot)) {
        throw 'harness.root is empty and ExecutorCommand was not supplied'
    }

    $ExecutePath = Join-Path $HarnessRoot 'scripts/execute.py'
    if (-not (Test-Path -LiteralPath $ExecutePath)) {
        throw "EasyPowersHarness executor not found: $ExecutePath"
    }
}

$StepsRun = 0
while ($true) {
    $Index = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
    $Pending = $Index.steps |
        Where-Object { $_.status -eq 'pending' } |
        Sort-Object { [int]$_.step } |
        Select-Object -First 1

    if (-not $Pending) {
        Write-Output "Harness run complete: no pending steps in $IndexPath"
        Save-RunLog $RunAttempts $RunLogPath
        exit 0
    }

    if ($MaxSteps -gt 0 -and $StepsRun -ge $MaxSteps) {
        Write-Output "Harness run paused: MaxSteps=$MaxSteps reached"
        Save-RunLog $RunAttempts $RunLogPath
        exit 0
    }

    $StepNumber = [int]$Pending.step
    $BeforeStatus = [string]$Pending.status
    $DisplayCommand = if ([string]::IsNullOrWhiteSpace($ExecutorCommand)) { "python $ExecutePath $Phase" } else { $ExecutorCommand }
    $ModelProfile = 'balanced'
    if ($Pending.PSObject.Properties.Name -contains 'model_profile' -and -not [string]::IsNullOrWhiteSpace([string]$Pending.model_profile)) {
        $ModelProfile = [string]$Pending.model_profile
    }
    Write-Output "Running harness step $StepNumber with timeout ${TimeoutSeconds}s"

    $ModelRoute = Invoke-EzpModelRouter -ProjectRoot $ProjectRoot -Backend 'harness-env' -Profile $ModelProfile -ExplicitModel $ExplicitModel
    if ($null -ne $ModelRoute.result -and [string](Get-EzpConfigValue $ModelRoute.result 'status' '') -ne 'disabled') {
        Write-Output "Model route for step ${StepNumber}: profile=$ModelProfile selected=$([string](Get-EzpConfigValue $ModelRoute.result 'selected' '')) status=$([string](Get-EzpConfigValue $ModelRoute.result 'status' ''))"
    }
    if ($ModelRoute.exit_code -ne 0 -or $ModelRoute.timed_out) {
        $AttemptRecord = New-Attempt $StepNumber 'python scripts/model-router.py' $ModelRoute.exit_code $ModelRoute.timed_out $BeforeStatus $BeforeStatus $ModelRoute.stdout $ModelRoute.stderr
        if ($null -ne $ModelRoute.result) {
            $AttemptRecord | Add-Member -NotePropertyName model_resolution -NotePropertyValue $ModelRoute.result -Force
        }
        $RunAttempts += $AttemptRecord
        Save-RunLog $RunAttempts $RunLogPath
        Write-Output "Model routing failed at step $StepNumber"
        exit 1
    }

    $PreviousEnv = Set-EzpModelRoutingEnvironment $ModelRoute.result
    try {
        $Result = Invoke-HarnessExecutor $ExecutorCommand $ExecutePath
    }
    finally {
        Restore-EzpEnvironment $PreviousEnv
    }

    $AfterIndex = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
    $AfterStep = $AfterIndex.steps |
        Where-Object { [int]$_.step -eq $StepNumber } |
        Select-Object -First 1
    $AfterStatus = if ($AfterStep) { [string]$AfterStep.status } else { 'missing' }

    $AttemptRecord = New-Attempt $StepNumber $DisplayCommand $Result.exit_code $Result.timed_out $BeforeStatus $AfterStatus $Result.stdout $Result.stderr
    if ($null -ne $ModelRoute.result) {
        $AttemptRecord | Add-Member -NotePropertyName model_resolution -NotePropertyValue $ModelRoute.result -Force
    }

    $StepMdName = if ($AfterStep -and $AfterStep.PSObject.Properties.Name -contains 'step_md' -and -not [string]::IsNullOrWhiteSpace([string]$AfterStep.step_md)) {
        [string]$AfterStep.step_md
    }
    else {
        "step${StepNumber}.md"
    }
    $StepMdPath = Join-Path $ProjectRoot "phases/$Phase/$StepMdName"
    $TaskNumber = $StepNumber + 1
    $Verify = $null
    $SmokeResult = $null

    if ($AfterStatus -eq 'completed') {
        $VerifyTimeout = 120
        $Verify = Invoke-EzpVerifyStep -ProjectRoot $ProjectRoot -Phase $Phase -StepMdPath $StepMdPath -TimeoutSeconds $VerifyTimeout
        $AttemptRecord | Add-Member -NotePropertyName verify_exit_code -NotePropertyValue ([int]$Verify.exit_code) -Force
        if ($null -ne $Verify.result) {
            $AttemptRecord | Add-Member -NotePropertyName verify_result -NotePropertyValue $Verify.result -Force
        }
        if ($Verify.exit_code -ne 0 -or $Verify.timed_out) {
            Save-EzpTaskGateEvidence `
                -ProjectRoot $ProjectRoot `
                -Phase $Phase `
                -TaskNumber $TaskNumber `
                -StepNumber $StepNumber `
                -StepMdName $StepMdName `
                -StepMdPath $StepMdPath `
                -Verify $Verify `
                -Status 'fail' `
                -EvidenceStatus 'verify_failed' `
                -Message "verify-step.py rejected step $StepNumber" `
                -VerifyTimeoutSeconds $VerifyTimeout | Out-Null
            $RunAttempts += $AttemptRecord
            Save-RunLog $RunAttempts $RunLogPath
            Set-EzpStepStatus -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Status 'rejected'
            Write-Output "verify-step.py rejected step $StepNumber (exit $($Verify.exit_code))"
            exit 1
        }
    }

    if ($AfterStatus -eq 'completed') {
        $SmokeResult = Invoke-EzpRuntimeSmokeIfConfigured -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber
        if ($null -ne $SmokeResult) {
            $AttemptRecord | Add-Member -NotePropertyName smoke_command -NotePropertyValue $SmokeResult.command -Force
            $AttemptRecord | Add-Member -NotePropertyName smoke_exit_code -NotePropertyValue ([int]$SmokeResult.exit_code) -Force
            if ($SmokeResult.exit_code -ne 0 -or $SmokeResult.timed_out) {
                Save-EzpTaskGateEvidence `
                    -ProjectRoot $ProjectRoot `
                    -Phase $Phase `
                    -TaskNumber $TaskNumber `
                    -StepNumber $StepNumber `
                    -StepMdName $StepMdName `
                    -StepMdPath $StepMdPath `
                    -Verify $Verify `
                    -SmokeResult $SmokeResult `
                    -Status 'fail' `
                    -EvidenceStatus 'smoke_failed' `
                    -Message "runtime smoke failed at step $StepNumber" `
                    -VerifyTimeoutSeconds $VerifyTimeout | Out-Null
                $RunAttempts += $AttemptRecord
                Save-RunLog $RunAttempts $RunLogPath
                Set-EzpStepStatus -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Status 'error'
                Write-Output "Runtime smoke failed at step $StepNumber"
                exit 1
            }
        }
        Save-EzpTaskGateEvidence `
            -ProjectRoot $ProjectRoot `
            -Phase $Phase `
            -TaskNumber $TaskNumber `
            -StepNumber $StepNumber `
            -StepMdName $StepMdName `
            -StepMdPath $StepMdPath `
            -Verify $Verify `
            -SmokeResult $SmokeResult `
            -Status 'pass' `
            -EvidenceStatus 'task_verified' `
            -Message "step $StepNumber verified" `
            -VerifyTimeoutSeconds $VerifyTimeout | Out-Null
    }

    $RunAttempts += $AttemptRecord
    Save-RunLog $RunAttempts $RunLogPath

    if ($Result.timed_out) {
        Write-Output "Harness run timed out at step $StepNumber"
        exit 124
    }
    if ($Result.exit_code -ne 0) {
        Write-Output "Harness executor failed at step $StepNumber with exit code $($Result.exit_code)"
        exit 1
    }
    if ($AfterStatus -eq 'pending') {
        Write-Output "Harness executor made no progress at step $StepNumber"
        exit 2
    }
    if ($AfterStatus -in @('error', 'blocked', 'rejected')) {
        Write-Output "Harness step $StepNumber ended with status $AfterStatus"
        exit 1
    }

    Write-Output "Harness step $StepNumber status: $AfterStatus"
    $StepsRun++
}
