$ErrorActionPreference = 'Stop'

$script:EzpHarnessCommonRoot = if ($PSCommandPath) {
    Split-Path -Parent $PSCommandPath
}
else {
    $PSScriptRoot
}

function Get-EzpTail {
    param(
        [AllowNull()][string] $Text,
        [int] $MaxLength = 2000
    )

    if ($null -eq $Text) {
        return ''
    }
    if ($Text.Length -gt $MaxLength) {
        return $Text.Substring($Text.Length - $MaxLength)
    }
    return $Text
}

function Save-EzpJson {
    param(
        $Value,
        [string] $Path,
        [int] $Depth = 20
    )

    $Value | ConvertTo-Json -Depth $Depth | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-EzpConfigValue {
    param(
        $Object,
        [string] $Name,
        $Default = $null
    )

    if ($null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name) {
        return $Object.$Name
    }
    return $Default
}

function Get-EzpHarnessConfig {
    param([string] $ProjectRoot)

    $ConfigPath = Join-Path $ProjectRoot '.harness/config.json'
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        return $null
    }
    return Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Join-EzpProcessArguments {
    param([string[]] $Arguments)

    return (($Arguments | ForEach-Object {
        if ($_ -match '[\s"]') {
            '"' + ($_ -replace '"', '\"') + '"'
        }
        else {
            $_
        }
    }) -join ' ')
}

function Invoke-EzpExternalProcess {
    param(
        [string] $ProjectRoot,
        [string] $FilePath,
        [string[]] $Arguments = @(),
        [int] $TimeoutSeconds = 30,
        [string] $TimeoutMessage = 'process timed out'
    )

    $Psi = [System.Diagnostics.ProcessStartInfo]::new()
    $Psi.FileName = $FilePath
    $Psi.Arguments = Join-EzpProcessArguments $Arguments
    $Psi.WorkingDirectory = $ProjectRoot
    $Psi.UseShellExecute = $false
    $Psi.RedirectStandardOutput = $true
    $Psi.RedirectStandardError = $true
    $Psi.CreateNoWindow = $true

    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $Psi
    [void]$Process.Start()
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()

    $TimedOut = -not $Process.WaitForExit([Math]::Max(1, $TimeoutSeconds) * 1000)
    if ($TimedOut) {
        try {
            $Process.Kill()
        }
        catch {
            Write-Output "Failed to kill timed-out process: $($_.Exception.Message)"
        }
    }
    try {
        $Process.WaitForExit()
    }
    catch {
    }

    return [pscustomobject]@{
        exit_code = if ($TimedOut) { 124 } else { [int]$Process.ExitCode }
        timed_out = $TimedOut
        stdout = $StdoutTask.Result
        stderr = if ($TimedOut -and [string]::IsNullOrWhiteSpace($StderrTask.Result)) { $TimeoutMessage } else { $StderrTask.Result }
    }
}

function Invoke-EzpPowershellCommand {
    param(
        [string] $ProjectRoot,
        [string] $Command,
        [int] $TimeoutSeconds = 30
    )

    $EncodedCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
    return Invoke-EzpExternalProcess `
        -ProjectRoot $ProjectRoot `
        -FilePath 'powershell.exe' `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', $EncodedCommand) `
        -TimeoutSeconds $TimeoutSeconds `
        -TimeoutMessage "PowerShell command timed out after ${TimeoutSeconds}s"
}

function Test-EzpTrivialCommand {
    param([string] $Command)

    $Text = $Command.Trim()
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $true
    }

    $Lower = $Text.ToLowerInvariant()
    $Lower = $Lower -replace '^(powershell|powershell\.exe|pwsh|pwsh\.exe)\s+(-noprofile\s+)?(-executionpolicy\s+\w+\s+)?(-command\s+)?', ''
    $Lower = $Lower.Trim().Trim('"').Trim("'").Trim()

    if ($Lower -match '^(true|:|exit\s+0)$') {
        return $true
    }
    if ($Lower -match '^(echo|write-output)\b') {
        return $true
    }
    return $false
}

function Get-EzpSmokeTimeout {
    param($Smoke)

    $Timeout = 30
    foreach ($Name in @('timeout_sec', 'timeout_seconds', 'startup_timeout_seconds')) {
        if ($null -ne $Smoke -and $Smoke.PSObject.Properties.Name -contains $Name) {
            $Value = [int]$Smoke.$Name
            if ($Value -gt 0) {
                $Timeout = $Value
                break
            }
        }
    }
    return $Timeout
}

function Write-EzpRuntimeProbe {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [int] $StepNumber,
        [string] $Command,
        $Result
    )

    $PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
    $Status = if ($Result.exit_code -eq 0 -and -not $Result.timed_out) { 'completed' } else { 'smoke_failed' }
    [pscustomobject]@{
        status = $Status
        step = $StepNumber
        command = $Command
        exit_code = $Result.exit_code
        timed_out = $Result.timed_out
        stdout_tail = Get-EzpTail $Result.stdout
        stderr_tail = Get-EzpTail $Result.stderr
        timestamp = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json') -Encoding UTF8
}

function Invoke-EzpRuntimeSmokeIfConfigured {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [int] $StepNumber
    )

    $Config = Get-EzpHarnessConfig -ProjectRoot $ProjectRoot
    if ($null -eq $Config -or -not ($Config.PSObject.Properties.Name -contains 'smoke')) {
        return $null
    }

    $Required = [bool](Get-EzpConfigValue $Config.smoke 'required' $false)
    if (-not $Required) {
        return $null
    }

    $Command = [string](Get-EzpConfigValue $Config.smoke 'command' '')
    if ([string]::IsNullOrWhiteSpace($Command)) {
        return [pscustomobject]@{
            exit_code = 10
            timed_out = $false
            stdout = ''
            stderr = 'required smoke.command is empty'
            command = ''
        }
    }

    $Timeout = Get-EzpSmokeTimeout $Config.smoke
    $Result = Invoke-EzpPowershellCommand -ProjectRoot $ProjectRoot -Command $Command -TimeoutSeconds $Timeout
    $Result | Add-Member -NotePropertyName command -NotePropertyValue $Command -Force
    Write-EzpRuntimeProbe -ProjectRoot $ProjectRoot -Phase $Phase -StepNumber $StepNumber -Command $Command -Result $Result
    return $Result
}

function Test-EzpRuntimeEvidence {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        $Config
    )

    $Smoke = Get-EzpConfigValue $Config 'smoke' $null
    $Required = [bool](Get-EzpConfigValue $Smoke 'required' $false)
    $Kind = [string](Get-EzpConfigValue $Smoke 'artifact_kind' '')
    if (-not $Required -or $Kind -notin @('cli', 'server', 'desktop')) {
        return [pscustomobject]@{ ok = $true; artifacts = @(); message = 'runtime smoke not required' }
    }

    $PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
    $Artifacts = @()
    foreach ($Name in @('runtime-probe.json', 'smoke-output.json')) {
        $Path = Join-Path $PhaseDir $Name
        if (Test-Path -LiteralPath $Path) {
            $Artifacts += $Name
        }
    }

    if ($Artifacts.Count -eq 0) {
        return [pscustomobject]@{ ok = $false; artifacts = @(); message = 'missing runtime-probe.json or smoke-output.json' }
    }

    $ProbePath = Join-Path $PhaseDir 'runtime-probe.json'
    if (Test-Path -LiteralPath $ProbePath) {
        try {
            $Probe = Get-Content -LiteralPath $ProbePath -Raw -Encoding UTF8 | ConvertFrom-Json
            $Status = [string](Get-EzpConfigValue $Probe 'status' '')
            if ($Status -and $Status -ne 'completed') {
                return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe status is $Status" }
            }
            $ExitCode = Get-EzpConfigValue $Probe 'exit_code' 0
            if ([int]$ExitCode -ne 0) {
                return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe exit code is $ExitCode" }
            }
        }
        catch {
            return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe.json is invalid: $($_.Exception.Message)" }
        }
    }

    return [pscustomobject]@{ ok = $true; artifacts = $Artifacts; message = 'runtime evidence present' }
}

function Get-EzpPhaseIndex {
    param(
        [string] $ProjectRoot,
        [string] $Phase
    )

    $IndexPath = Join-Path $ProjectRoot "phases/$Phase/index.json"
    if (-not (Test-Path -LiteralPath $IndexPath)) {
        throw "Harness phase index not found: $IndexPath"
    }
    return Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Save-EzpPhaseIndex {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        $Index
    )

    Save-EzpJson $Index (Join-Path $ProjectRoot "phases/$Phase/index.json") 20
}

function Get-EzpStepFileHash {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return ''
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-EzpTaskGateDir {
    param(
        [string] $ProjectRoot,
        [string] $Phase
    )

    return Join-Path $ProjectRoot "phases/$Phase/task-gates"
}

function Get-EzpTaskGatePath {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [int] $TaskNumber
    )

    return Join-Path (Get-EzpTaskGateDir -ProjectRoot $ProjectRoot -Phase $Phase) "task-$TaskNumber.json"
}

function Get-EzpVerifyCommandsFromResult {
    param($VerifyResult)

    $Commands = @()
    if ($null -eq $VerifyResult) {
        return $Commands
    }

    if ($VerifyResult.PSObject.Properties.Name -contains 'verify_commands') {
        foreach ($Command in @($VerifyResult.verify_commands)) {
            if (-not [string]::IsNullOrWhiteSpace([string]$Command) -and $Commands -notcontains [string]$Command) {
                $Commands += [string]$Command
            }
        }
    }

    if ($Commands.Count -eq 0 -and $VerifyResult.PSObject.Properties.Name -contains 'dimensions') {
        $CommandDimension = Get-EzpConfigValue $VerifyResult.dimensions 'command' $null
        $Checks = Get-EzpConfigValue $CommandDimension 'checks' @()
        foreach ($Check in @($Checks)) {
            $Command = [string](Get-EzpConfigValue $Check 'command' '')
            if (-not [string]::IsNullOrWhiteSpace($Command) -and $Commands -notcontains $Command) {
                $Commands += $Command
            }
        }
    }

    return $Commands
}

function Save-EzpTaskGateEvidence {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [int] $TaskNumber,
        [int] $StepNumber,
        [string] $StepMdName,
        [string] $StepMdPath,
        $Verify,
        [AllowNull()] $SmokeResult = $null,
        [string] $Status,
        [string] $EvidenceStatus,
        [string] $Message,
        [int] $VerifyTimeoutSeconds = 120
    )

    $GateDir = Get-EzpTaskGateDir -ProjectRoot $ProjectRoot -Phase $Phase
    if (-not (Test-Path -LiteralPath $GateDir)) {
        New-Item -ItemType Directory -Force -Path $GateDir | Out-Null
    }

    $VerifyResult = if ($null -ne $Verify) { $Verify.result } else { $null }
    $VerifyCommands = @(Get-EzpVerifyCommandsFromResult $VerifyResult)
    $VerifyType = [string](Get-EzpConfigValue $VerifyResult 'verify_type' '')

    $Gate = [pscustomobject]@{
        schema_version = 1
        phase = $Phase
        task_number = $TaskNumber
        step = $StepNumber
        step_md = $StepMdName
        step_sha256 = Get-EzpStepFileHash $StepMdPath
        status = $Status
        evidence_status = $EvidenceStatus
        message = $Message
        verify_type = $VerifyType
        verify_commands = $VerifyCommands
        verify_commands_count = $VerifyCommands.Count
        verify_timeout_seconds = $VerifyTimeoutSeconds
        verify_exit_code = if ($null -ne $Verify) { [int]$Verify.exit_code } else { $null }
        verify_timed_out = if ($null -ne $Verify) { [bool]$Verify.timed_out } else { $null }
        verify_result = $VerifyResult
        smoke_command = if ($null -ne $SmokeResult) { [string](Get-EzpConfigValue $SmokeResult 'command' '') } else { $null }
        smoke_exit_code = if ($null -ne $SmokeResult) { [int]$SmokeResult.exit_code } else { $null }
        smoke_timed_out = if ($null -ne $SmokeResult) { [bool]$SmokeResult.timed_out } else { $null }
        updated_at = (Get-Date).ToUniversalTime().ToString('o')
    }

    $Path = Get-EzpTaskGatePath -ProjectRoot $ProjectRoot -Phase $Phase -TaskNumber $TaskNumber
    Save-EzpJson $Gate $Path 40
    return $Gate
}

function Set-EzpStepStatus {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [int] $StepNumber,
        [string] $Status
    )

    $Index = Get-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase
    $Step = $Index.steps |
        Where-Object { [int]$_.step -eq $StepNumber } |
        Select-Object -First 1
    if ($Step) {
        $Step.status = $Status
        Save-EzpPhaseIndex -ProjectRoot $ProjectRoot -Phase $Phase -Index $Index
    }
}

function Invoke-EzpVerifyStep {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        [string] $StepMdPath,
        [int] $TimeoutSeconds = 30
    )

    $VerifyScript = Join-Path $script:EzpHarnessCommonRoot 'verify-step.py'
    if (-not (Test-Path -LiteralPath $StepMdPath)) {
        return [pscustomobject]@{
            exit_code = 1
            timed_out = $false
            stdout = ''
            stderr = "step file not found: $StepMdPath"
            result = [pscustomobject]@{
                pass = $false
                error = "step file not found: $StepMdPath"
            }
        }
    }
    if (-not (Test-Path -LiteralPath $VerifyScript)) {
        return [pscustomobject]@{
            exit_code = 1
            timed_out = $false
            stdout = ''
            stderr = "verify-step.py not found: $VerifyScript"
            result = [pscustomobject]@{
                pass = $false
                error = "verify-step.py not found: $VerifyScript"
            }
        }
    }

    $ProcessTimeout = [Math]::Max(1, $TimeoutSeconds + 10)
    $Result = Invoke-EzpExternalProcess `
        -ProjectRoot $ProjectRoot `
        -FilePath 'python' `
        -Arguments @($VerifyScript, '--step-md', $StepMdPath, '--project-root', $ProjectRoot, '--phase', $Phase, '--timeout', ([string]$TimeoutSeconds)) `
        -TimeoutSeconds $ProcessTimeout `
        -TimeoutMessage "verify-step.py timed out after ${ProcessTimeout}s"

    $Parsed = $null
    if (-not [string]::IsNullOrWhiteSpace($Result.stdout)) {
        try {
            $Parsed = $Result.stdout | ConvertFrom-Json
        }
        catch {
            $Parsed = $Result.stdout
        }
    }

    return [pscustomobject]@{
        exit_code = $Result.exit_code
        timed_out = $Result.timed_out
        stdout = $Result.stdout
        stderr = $Result.stderr
        result = $Parsed
    }
}

function Invoke-EzpModelRouter {
    param(
        [string] $ProjectRoot,
        [string] $Backend,
        [string] $Profile = 'balanced',
        [string] $ExplicitModel = ''
    )

    $RouterScript = Join-Path $script:EzpHarnessCommonRoot 'model-router.py'
    if (-not (Test-Path -LiteralPath $RouterScript)) {
        return [pscustomobject]@{
            exit_code = 1
            timed_out = $false
            stdout = ''
            stderr = "model-router.py not found: $RouterScript"
            result = [pscustomobject]@{
                enabled = $false
                profile = $Profile
                backend = $Backend
                selected = $null
                status = 'error'
                reason = "model-router.py not found: $RouterScript"
            }
        }
    }

    $Arguments = @(
        $RouterScript,
        '--project-root', $ProjectRoot,
        '--backend', $Backend,
        '--profile', $Profile,
        '--json'
    )
    if (-not [string]::IsNullOrWhiteSpace($ExplicitModel)) {
        $Arguments += @('--explicit-model', $ExplicitModel)
    }

    $Result = Invoke-EzpExternalProcess `
        -ProjectRoot $ProjectRoot `
        -FilePath 'python' `
        -Arguments $Arguments `
        -TimeoutSeconds 15 `
        -TimeoutMessage 'model-router.py timed out after 15s'

    $Parsed = $null
    if (-not [string]::IsNullOrWhiteSpace($Result.stdout)) {
        try {
            $Parsed = $Result.stdout | ConvertFrom-Json
        }
        catch {
            $Parsed = [pscustomobject]@{
                enabled = $false
                profile = $Profile
                backend = $Backend
                selected = $null
                status = 'error'
                reason = "failed to parse model-router output: $($_.Exception.Message)"
            }
        }
    }

    return [pscustomobject]@{
        exit_code = $Result.exit_code
        timed_out = $Result.timed_out
        stdout = $Result.stdout
        stderr = $Result.stderr
        result = $Parsed
    }
}

function Set-EzpModelRoutingEnvironment {
    param($Resolution)

    $Names = @(
        'EZPOWERS_MODEL_PROFILE',
        'EZPOWERS_MODEL',
        'EZPOWERS_MODEL_VARIANT',
        'EZPOWERS_REASONING_EFFORT',
        'EZPOWERS_MODEL_ROUTING_JSON'
    )
    $Previous = @{}
    foreach ($Name in $Names) {
        $Previous[$Name] = [Environment]::GetEnvironmentVariable($Name, 'Process')
    }

    $Selected = [string](Get-EzpConfigValue $Resolution 'selected' '')
    $Profile = [string](Get-EzpConfigValue $Resolution 'profile' '')
    $Variant = [string](Get-EzpConfigValue $Resolution 'variant' '')
    $Reasoning = [string](Get-EzpConfigValue $Resolution 'reasoning_effort' '')

    if (-not [string]::IsNullOrWhiteSpace($Profile)) {
        [Environment]::SetEnvironmentVariable('EZPOWERS_MODEL_PROFILE', $Profile, 'Process')
    }
    if (-not [string]::IsNullOrWhiteSpace($Selected)) {
        [Environment]::SetEnvironmentVariable('EZPOWERS_MODEL', $Selected, 'Process')
    }
    if (-not [string]::IsNullOrWhiteSpace($Variant)) {
        [Environment]::SetEnvironmentVariable('EZPOWERS_MODEL_VARIANT', $Variant, 'Process')
    }
    if (-not [string]::IsNullOrWhiteSpace($Reasoning)) {
        [Environment]::SetEnvironmentVariable('EZPOWERS_REASONING_EFFORT', $Reasoning, 'Process')
    }
    if ($null -ne $Resolution) {
        [Environment]::SetEnvironmentVariable('EZPOWERS_MODEL_ROUTING_JSON', ($Resolution | ConvertTo-Json -Depth 20 -Compress), 'Process')
    }

    return $Previous
}

function Restore-EzpEnvironment {
    param($Previous)

    foreach ($Name in $Previous.Keys) {
        [Environment]::SetEnvironmentVariable($Name, $Previous[$Name], 'Process')
    }
}

function Get-EzpGateExitCode {
    param([string] $Status)

    switch ($Status) {
        'pass' { return 0 }
        'fail' { return 1 }
        'spec_gap' { return 2 }
        'test_gap' { return 3 }
        'code_gap' { return 4 }
        'review_pending' { return 5 }
        default { return 3 }
    }
}
