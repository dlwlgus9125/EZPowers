param(
    [Parameter(Mandatory = $true)]
    [string] $Phase,

    [string] $ProjectRoot = (Get-Location).Path,

    [string] $HarnessRoot = '',

    [int] $TimeoutSeconds = 600,

    [int] $MaxSteps = 0,

    [string] $ExecutorCommand = ''
)

$ErrorActionPreference = 'Stop'

function Get-PhaseIndex {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Harness phase index not found: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

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
        stdout_tail = if ($Stdout.Length -gt 2000) { $Stdout.Substring($Stdout.Length - 2000) } else { $Stdout }
        stderr_tail = if ($Stderr.Length -gt 2000) { $Stderr.Substring($Stderr.Length - 2000) } else { $Stderr }
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    }
}

function Read-ConfigHarnessRoot {
    $ConfigPath = Join-Path $ProjectRoot '.harness/config.json'
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        throw "Missing harness config: $ConfigPath"
    }

    $Config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Config.PSObject.Properties.Name -contains 'harness' -and $Config.harness.PSObject.Properties.Name -contains 'root') {
        return [string]$Config.harness.root
    }
    return ''
}

function Invoke-HarnessExecutor {
    param([string] $Command, [string] $ExecutePath)

    $OutFile = Join-Path $env:TEMP ("ezpowers-run-out-" + [guid]::NewGuid().ToString("N") + ".txt")
    $ErrFile = Join-Path $env:TEMP ("ezpowers-run-err-" + [guid]::NewGuid().ToString("N") + ".txt")

    try {
        if ([string]::IsNullOrWhiteSpace($Command)) {
            $Process = Start-Process -FilePath 'python' `
                -ArgumentList @($ExecutePath, $Phase) `
                -WorkingDirectory $ProjectRoot `
                -PassThru `
                -WindowStyle Hidden `
                -RedirectStandardOutput $OutFile `
                -RedirectStandardError $ErrFile
        }
        else {
            $Process = Start-Process -FilePath 'powershell.exe' `
                -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $Command) `
                -WorkingDirectory $ProjectRoot `
                -PassThru `
                -WindowStyle Hidden `
                -RedirectStandardOutput $OutFile `
                -RedirectStandardError $ErrFile
        }

        $TimedOut = -not $Process.WaitForExit([Math]::Max(1, $TimeoutSeconds) * 1000)
        if ($TimedOut) {
            try {
                $Process.Kill()
            }
            catch {
                Write-Output "Failed to kill timed-out harness process: $($_.Exception.Message)"
            }
        }

        $Stdout = if (Test-Path -LiteralPath $OutFile) { Get-Content -LiteralPath $OutFile -Raw -Encoding UTF8 } else { '' }
        $Stderr = if (Test-Path -LiteralPath $ErrFile) { Get-Content -LiteralPath $ErrFile -Raw -Encoding UTF8 } else { '' }
        $ExitCode = if ($TimedOut) { 124 } else { [int]$Process.ExitCode }

        return [pscustomobject]@{
            exit_code = $ExitCode
            timed_out = $TimedOut
            stdout = $Stdout
            stderr = $Stderr
        }
    }
    finally {
        Remove-Item -LiteralPath $OutFile, $ErrFile -ErrorAction SilentlyContinue
    }
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
    $Index = Get-PhaseIndex $IndexPath
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
    Write-Output "Running harness step $StepNumber with timeout ${TimeoutSeconds}s"

    $Result = Invoke-HarnessExecutor $ExecutorCommand $ExecutePath

    $AfterIndex = Get-PhaseIndex $IndexPath
    $AfterStep = $AfterIndex.steps |
        Where-Object { [int]$_.step -eq $StepNumber } |
        Select-Object -First 1
    $AfterStatus = if ($AfterStep) { [string]$AfterStep.status } else { 'missing' }

    $AttemptRecord = New-Attempt $StepNumber $DisplayCommand $Result.exit_code $Result.timed_out $BeforeStatus $AfterStatus $Result.stdout $Result.stderr

    # Multi-dimensional verify-step.py integration (optional, backwards-compatible)
    # Use index step_md field if available, fall back to convention
    $StepMdName = if ($AfterStep -and $AfterStep.PSObject.Properties.Name -contains 'step_md' -and -not [string]::IsNullOrWhiteSpace([string]$AfterStep.step_md)) {
        [string]$AfterStep.step_md
    } else {
        "step${StepNumber}.md"
    }
    $StepMdPath = Join-Path $ProjectRoot "phases/$Phase/$StepMdName"
    if ($AfterStatus -eq 'completed' -and (Test-Path -LiteralPath $StepMdPath)) {
        $VerifyScript = Join-Path $PSScriptRoot 'verify-step.py'
        if (Test-Path -LiteralPath $VerifyScript) {
            $VerifyId = [guid]::NewGuid().ToString("N")
            $VerifyOutFile = Join-Path $env:TEMP ("ezpowers-verify-out-$VerifyId.txt")
            $VerifyErrFile = Join-Path $env:TEMP ("ezpowers-verify-err-$VerifyId.txt")
            try {
                $VerifyProc = Start-Process -FilePath 'python' `
                    -ArgumentList @($VerifyScript, '--step-md', $StepMdPath, '--project-root', $ProjectRoot, '--phase', $Phase, '--timeout', '30') `
                    -WorkingDirectory $ProjectRoot `
                    -PassThru -Wait -WindowStyle Hidden `
                    -RedirectStandardOutput $VerifyOutFile `
                    -RedirectStandardError $VerifyErrFile
                $VerifyOut = if (Test-Path -LiteralPath $VerifyOutFile) { Get-Content -LiteralPath $VerifyOutFile -Raw -Encoding UTF8 } else { '' }
                $VerifyErr = if (Test-Path -LiteralPath $VerifyErrFile) { Get-Content -LiteralPath $VerifyErrFile -Raw -Encoding UTF8 } else { '' }
                if ($VerifyOut) {
                    try {
                        $AttemptRecord | Add-Member -NotePropertyName verify_result -NotePropertyValue ($VerifyOut | ConvertFrom-Json) -Force
                    } catch {
                        $AttemptRecord | Add-Member -NotePropertyName verify_result -NotePropertyValue $VerifyOut -Force
                    }
                }
                $AttemptRecord | Add-Member -NotePropertyName verify_exit_code -NotePropertyValue ([int]$VerifyProc.ExitCode) -Force
                if ($VerifyProc.ExitCode -ne 0) {
                    Write-Output "verify-step.py reported issues for step $StepNumber (exit $($VerifyProc.ExitCode)) -- see verify_result in harness-run.json"
                }
            } catch {
                Write-Output "verify-step.py skipped: $($_.Exception.Message)"
            } finally {
                Remove-Item -LiteralPath $VerifyOutFile, $VerifyErrFile -ErrorAction SilentlyContinue
            }
        }
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
