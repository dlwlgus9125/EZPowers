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

function Resolve-EzpProjectPath {
    param(
        [string] $ProjectRoot,
        [string] $Path
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return ''
    }
    if ([IO.Path]::IsPathRooted($Path)) {
        return $Path
    }
    return Join-Path $ProjectRoot $Path
}

function Test-EzpNonEmptyEvidenceValue {
    param($Value)

    if ($null -eq $Value) {
        return $false
    }
    if ($Value -is [string]) {
        return -not [string]::IsNullOrWhiteSpace($Value)
    }
    if ($Value -is [System.Array]) {
        foreach ($Item in @($Value)) {
            if (Test-EzpNonEmptyEvidenceValue $Item) {
                return $true
            }
        }
        return $false
    }
    return $true
}

function Get-EzpDesktopEvidenceFromArtifact {
    param($Artifact)

    if ($null -eq $Artifact) {
        return $null
    }

    foreach ($Name in @('desktop_evidence', 'gui_evidence')) {
        $Evidence = Get-EzpConfigValue $Artifact $Name $null
        if ($null -ne $Evidence) {
            return $Evidence
        }
    }

    $Nested = Get-EzpConfigValue $Artifact 'evidence' $null
    if ($null -ne $Nested) {
        foreach ($Name in @('desktop', 'desktop_evidence', 'gui')) {
            $Evidence = Get-EzpConfigValue $Nested $Name $null
            if ($null -ne $Evidence) {
                return $Evidence
            }
        }
    }

    return $null
}

function Get-EzpClientServerEvidenceFromArtifact {
    param($Artifact)

    if ($null -eq $Artifact) {
        return $null
    }

    $Evidence = Get-EzpConfigValue $Artifact 'client_server_evidence' $null
    if ($null -ne $Evidence) {
        return $Evidence
    }

    $Nested = Get-EzpConfigValue $Artifact 'evidence' $null
    if ($null -ne $Nested) {
        foreach ($Name in @('client_server', 'client_server_evidence')) {
            $Evidence = Get-EzpConfigValue $Nested $Name $null
            if ($null -ne $Evidence) {
                return $Evidence
            }
        }
    }

    return $null
}

function Get-EzpApiObservationFromArtifact {
    param($Artifact)

    $ClientServerEvidence = Get-EzpClientServerEvidenceFromArtifact $Artifact
    $ApiObservation = Get-EzpConfigValue $ClientServerEvidence 'api_observation' ''
    if (Test-EzpNonEmptyEvidenceValue $ApiObservation) {
        return [string]$ApiObservation
    }

    $DesktopEvidence = Get-EzpDesktopEvidenceFromArtifact $Artifact
    $ApiObservation = Get-EzpConfigValue $DesktopEvidence 'api_observation' ''
    if (Test-EzpNonEmptyEvidenceValue $ApiObservation) {
        return [string]$ApiObservation
    }

    return ''
}

function Get-EzpApiObservationFromParsedArtifacts {
    param([object[]] $ParsedArtifacts)

    foreach ($Item in @($ParsedArtifacts)) {
        $Observation = Get-EzpApiObservationFromArtifact (Get-EzpConfigValue $Item 'value' $null)
        if (Test-EzpNonEmptyEvidenceValue $Observation) {
            return [string]$Observation
        }
    }

    return ''
}

function Test-EzpServerApiDependency {
    param(
        $Config,
        [AllowNull()] $Gate = $null
    )

    $Server = Get-EzpConfigValue $Config 'server' $null
    foreach ($Name in @('start_command', 'health_check_url')) {
        if (-not [string]::IsNullOrWhiteSpace([string](Get-EzpConfigValue $Server $Name ''))) {
            return $true
        }
    }

    $AppDelivery = Get-EzpConfigValue $Config 'app_delivery' $null
    $Backend = Get-EzpConfigValue $AppDelivery 'backend' $null
    if ([bool](Get-EzpConfigValue $Backend 'present' $false)) {
        return $true
    }
    foreach ($Name in @('api_style', 'auth_session', 'persistence', 'background_jobs')) {
        if (-not [string]::IsNullOrWhiteSpace([string](Get-EzpConfigValue $Backend $Name ''))) {
            return $true
        }
    }

    $ExpectedObservation = [string](Get-EzpConfigValue $Gate 'expected_observation' '')
    if ($ExpectedObservation -match '(?i)\b(api|server|http|route|endpoint)\b') {
        return $true
    }

    $VerifyType = [string](Get-EzpConfigValue $Gate 'verify_type' '')
    if ($VerifyType -eq 'api') {
        return $true
    }

    return $false
}

function Test-EzpClientSurface {
    param(
        $Config,
        [AllowNull()] $Gate = $null,
        [string] $ArtifactKind = ''
    )

    if ($ArtifactKind -in @('web', 'mobile', 'desktop', 'gui')) {
        return $true
    }

    $AppDelivery = Get-EzpConfigValue $Config 'app_delivery' $null
    $SurfaceKind = [string](Get-EzpConfigValue $AppDelivery 'surface_kind' '')
    if ($SurfaceKind -in @('web', 'mobile', 'desktop', 'gui')) {
        return $true
    }

    $Frontend = Get-EzpConfigValue $AppDelivery 'frontend' $null
    if ([bool](Get-EzpConfigValue $Frontend 'present' $false)) {
        return $true
    }

    $UiVerification = Get-EzpConfigValue $Config 'ui_verification' $null
    if ([bool](Get-EzpConfigValue $UiVerification 'required' $false)) {
        return $true
    }

    $ExpectedObservation = [string](Get-EzpConfigValue $Gate 'expected_observation' '')
    if ($ExpectedObservation -match '(?i)\b(client|frontend|browser|screen|ui|mobile|desktop|page|render|rendered|renders)\b') {
        return $true
    }

    return $false
}

function Test-EzpClientServerEvidenceRequired {
    param(
        $Config,
        [AllowNull()] $Gate = $null,
        [string] $ArtifactKind = ''
    )

    return (Test-EzpClientSurface -Config $Config -Gate $Gate -ArtifactKind $ArtifactKind) -and
        (Test-EzpServerApiDependency -Config $Config -Gate $Gate)
}

function Test-EzpClientServerRuntimeEvidence {
    param(
        $Config,
        $Gate,
        [string] $ArtifactKind,
        [object[]] $Artifacts,
        [object[]] $ParsedArtifacts
    )

    if (-not (Test-EzpClientServerEvidenceRequired -Config $Config -Gate $Gate -ArtifactKind $ArtifactKind)) {
        return [pscustomobject]@{ ok = $true; artifacts = $Artifacts; message = 'client-server evidence not required' }
    }

    $ApiObservation = Get-EzpApiObservationFromParsedArtifacts $ParsedArtifacts
    if (-not (Test-EzpNonEmptyEvidenceValue $ApiObservation)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'client-server evidence missing API observation for server/API wiring' }
    }

    return [pscustomobject]@{ ok = $true; artifacts = $Artifacts; message = 'client-server runtime evidence present' }
}

function Test-EzpNonZeroHandle {
    param($Handle)

    if ($null -eq $Handle) {
        return $false
    }

    $Text = ([string]$Handle).Trim()
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $false
    }
    if ($Text -in @('0', '0x0')) {
        return $false
    }

    $Number = 0L
    if ([long]::TryParse($Text, [ref]$Number)) {
        return $Number -ne 0
    }
    return $true
}

function Test-EzpAnyRegexMatch {
    param(
        $Values,
        [string] $Pattern
    )

    if ([string]::IsNullOrWhiteSpace($Pattern)) {
        return [pscustomobject]@{ ok = $true; message = '' }
    }

    try {
        foreach ($Value in @($Values)) {
            $Text = [string]$Value
            if (-not [string]::IsNullOrWhiteSpace($Text) -and $Text -match $Pattern) {
                return [pscustomobject]@{ ok = $true; message = '' }
            }
        }
    }
    catch {
        return [pscustomobject]@{ ok = $false; message = "invalid desktop evidence regex '$Pattern': $($_.Exception.Message)" }
    }

    return [pscustomobject]@{ ok = $false; message = "desktop evidence did not match expected regex '$Pattern'" }
}

function Test-EzpDesktopRuntimeEvidence {
    param(
        [string] $ProjectRoot,
        $Config,
        $Gate,
        [object[]] $Artifacts,
        [object[]] $ParsedArtifacts
    )

    $Evidence = $null
    foreach ($Item in @($ParsedArtifacts)) {
        $Candidate = Get-EzpDesktopEvidenceFromArtifact (Get-EzpConfigValue $Item 'value' $null)
        if ($null -ne $Candidate) {
            $Evidence = $Candidate
            break
        }
    }

    if ($null -eq $Evidence) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'missing desktop evidence in runtime-probe.json or smoke-output.json' }
    }

    $WindowFound = [bool](Get-EzpConfigValue $Evidence 'window_found' $false)
    $MainWindowHandle = Get-EzpConfigValue $Evidence 'main_window_handle' (Get-EzpConfigValue $Evidence 'window_handle' $null)
    if (-not $WindowFound -and -not (Test-EzpNonZeroHandle $MainWindowHandle)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'desktop evidence missing window_found=true or nonzero main_window_handle' }
    }

    $Smoke = Get-EzpConfigValue $Config 'smoke' $null
    $ScreenshotPath = [string](Get-EzpConfigValue $Evidence 'screenshot_path' '')
    if ([string]::IsNullOrWhiteSpace($ScreenshotPath)) {
        $ScreenshotPath = [string](Get-EzpConfigValue $Smoke 'screenshot_path' '')
    }
    if ([string]::IsNullOrWhiteSpace($ScreenshotPath)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'desktop evidence missing screenshot_path' }
    }

    $ResolvedScreenshotPath = Resolve-EzpProjectPath -ProjectRoot $ProjectRoot -Path $ScreenshotPath
    if (-not (Test-Path -LiteralPath $ResolvedScreenshotPath)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "desktop screenshot does not exist: $ScreenshotPath" }
    }

    $PixelVarianceRaw = Get-EzpConfigValue $Evidence 'pixel_variance' $null
    if ($null -eq $PixelVarianceRaw) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'desktop evidence missing pixel_variance' }
    }
    $PixelVariance = 0.0
    if (-not [double]::TryParse(([string]$PixelVarianceRaw), [ref]$PixelVariance)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "desktop evidence has invalid pixel_variance: $PixelVarianceRaw" }
    }
    $MinPixelVariance = [double](Get-EzpConfigValue $Smoke 'min_pixel_variance' 12.0)
    if ($PixelVariance -lt $MinPixelVariance) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "desktop screenshot pixel variance $PixelVariance is below $MinPixelVariance" }
    }

    $UiText = [string](Get-EzpConfigValue $Evidence 'ui_text' '')
    $AutomationNames = @(Get-EzpConfigValue $Evidence 'automation_names' @())
    $ApiObservation = Get-EzpApiObservationFromParsedArtifacts $ParsedArtifacts
    if (-not (Test-EzpNonEmptyEvidenceValue $UiText) -and -not (Test-EzpNonEmptyEvidenceValue $AutomationNames) -and -not (Test-EzpNonEmptyEvidenceValue $ApiObservation)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'desktop evidence missing UI text, automation name, or API observation' }
    }

    $ExpectedTextRegex = [string](Get-EzpConfigValue $Smoke 'expected_text_regex' '')
    if (-not [string]::IsNullOrWhiteSpace($ExpectedTextRegex) -and -not [bool](Get-EzpConfigValue $Evidence 'expected_text_matched' $false)) {
        $TextMatch = Test-EzpAnyRegexMatch -Values @($UiText) -Pattern $ExpectedTextRegex
        if (-not $TextMatch.ok) {
            return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = $TextMatch.message }
        }
    }

    $ExpectedNameRegex = [string](Get-EzpConfigValue $Smoke 'expected_automation_name_regex' '')
    if (-not [string]::IsNullOrWhiteSpace($ExpectedNameRegex) -and -not [bool](Get-EzpConfigValue $Evidence 'expected_automation_name_matched' $false)) {
        $NameMatch = Test-EzpAnyRegexMatch -Values $AutomationNames -Pattern $ExpectedNameRegex
        if (-not $NameMatch.ok) {
            return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = $NameMatch.message }
        }
    }

    if ((Test-EzpClientServerEvidenceRequired -Config $Config -Gate $Gate -ArtifactKind 'desktop') -and -not (Test-EzpNonEmptyEvidenceValue $ApiObservation)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'client-server evidence missing API observation for server/API wiring' }
    }

    $ResultArtifacts = @($Artifacts)
    if ($ResultArtifacts -notcontains $ScreenshotPath) {
        $ResultArtifacts += $ScreenshotPath
    }
    return [pscustomobject]@{ ok = $true; artifacts = $ResultArtifacts; message = 'desktop runtime evidence present' }
}

function Test-EzpRuntimeEvidence {
    param(
        [string] $ProjectRoot,
        [string] $Phase,
        $Config,
        [AllowNull()] $Gate = $null
    )

    $Smoke = Get-EzpConfigValue $Config 'smoke' $null
    $Required = [bool](Get-EzpConfigValue $Smoke 'required' $false)
    $Kind = [string](Get-EzpConfigValue $Smoke 'artifact_kind' '')
    if (-not $Required -and $Kind -notin @('docs', 'library')) {
        return [pscustomobject]@{ ok = $false; artifacts = @(); message = "runtime smoke required: smoke.required=false not allowed for artifact_kind: $Kind" }
    }
    $ClientServerEvidenceRequired = Test-EzpClientServerEvidenceRequired -Config $Config -Gate $Gate -ArtifactKind $Kind
    $RuntimeKinds = @('cli', 'server', 'desktop', 'web', 'mobile', 'gui')
    if ((-not $Required -and -not $ClientServerEvidenceRequired) -or
        ($Required -and $Kind -notin $RuntimeKinds -and -not $ClientServerEvidenceRequired)) {
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
    $ParsedArtifacts = @()
    if (-not (Test-Path -LiteralPath $ProbePath)) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'missing runtime-probe.json' }
    }
    try {
        $Probe = Get-Content -LiteralPath $ProbePath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe.json is invalid: $($_.Exception.Message)" }
    }
    if ($null -eq $Probe) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'runtime-probe.json is empty' }
    }
    $ParsedArtifacts += [pscustomobject]@{ name = 'runtime-probe.json'; value = $Probe }
    if ($Probe.PSObject.Properties.Name -notcontains 'status') {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'runtime-probe.json missing status' }
    }
    $Status = [string](Get-EzpConfigValue $Probe 'status' '')
    if ($Status -ne 'completed') {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe status is $Status" }
    }
    if ($Probe.PSObject.Properties.Name -notcontains 'exit_code') {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = 'runtime-probe.json missing exit_code' }
    }
    $ExitCode = Get-EzpConfigValue $Probe 'exit_code' 0
    if ([int]$ExitCode -ne 0) {
        return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "runtime-probe exit code is $ExitCode" }
    }

    $SmokeOutputPath = Join-Path $PhaseDir 'smoke-output.json'
    if (Test-Path -LiteralPath $SmokeOutputPath) {
        try {
            $SmokeOutput = Get-Content -LiteralPath $SmokeOutputPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $ParsedArtifacts += [pscustomobject]@{ name = 'smoke-output.json'; value = $SmokeOutput }
        }
        catch {
            if ($Kind -eq 'desktop') {
                return [pscustomobject]@{ ok = $false; artifacts = $Artifacts; message = "smoke-output.json is invalid: $($_.Exception.Message)" }
            }
        }
    }

    $ResultArtifacts = @($Artifacts)
    $ResultMessage = 'runtime evidence present'
    if ($Kind -eq 'desktop') {
        $DesktopRuntimeEvidence = Test-EzpDesktopRuntimeEvidence `
            -ProjectRoot $ProjectRoot `
            -Config $Config `
            -Gate $Gate `
            -Artifacts $Artifacts `
            -ParsedArtifacts $ParsedArtifacts
        if (-not $DesktopRuntimeEvidence.ok) {
            return $DesktopRuntimeEvidence
        }
        $ResultArtifacts = @($DesktopRuntimeEvidence.artifacts)
        $ResultMessage = 'desktop runtime evidence present'
    }

    $ClientServerRuntimeEvidence = Test-EzpClientServerRuntimeEvidence `
        -Config $Config `
        -Gate $Gate `
        -ArtifactKind $Kind `
        -Artifacts $ResultArtifacts `
        -ParsedArtifacts $ParsedArtifacts
    if (-not $ClientServerRuntimeEvidence.ok) {
        return $ClientServerRuntimeEvidence
    }
    if ($ClientServerEvidenceRequired -and $Kind -ne 'desktop') {
        $ResultMessage = 'client-server runtime evidence present'
    }

    return [pscustomobject]@{ ok = $true; artifacts = $ResultArtifacts; message = $ResultMessage }
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
