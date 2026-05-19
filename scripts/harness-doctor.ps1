param(
    [string] $ProjectRoot = (Get-Location).Path,
    [string] $Phase = '',
    [switch] $Json,
    [switch] $Status,
    [switch] $Verbose
)

$ErrorActionPreference = 'Stop'

$script:Config = $null
$script:ConfigPath = Join-Path $ProjectRoot '.harness/config.json'

function New-DoctorResult {
    param(
        [string] $Id,
        [string] $Name,
        [string] $Status,
        [string] $Message,
        [string[]] $Details = @(),
        [object[]] $Issues = @(),
        [double] $Duration = 0
    )

    [pscustomobject]@{
        id = $Id
        name = $Name
        status = $Status
        message = $Message
        details = @($Details)
        issues = @($Issues)
        duration = [math]::Round($Duration, 3)
    }
}

function Invoke-DoctorCheck {
    param(
        [string] $Id,
        [string] $Name,
        [scriptblock] $Check
    )

    $Watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $Result = & $Check
        $Watch.Stop()
        $Result.duration = [math]::Round($Watch.Elapsed.TotalMilliseconds, 3)
        return $Result
    }
    catch {
        $Watch.Stop()
        return New-DoctorResult `
            -Id $Id `
            -Name $Name `
            -Status 'fail' `
            -Message $_.Exception.Message `
            -Duration $Watch.Elapsed.TotalMilliseconds
    }
}

function Get-ConfigValue {
    param($Object, [string] $Name, $Default = $null)
    if ($null -ne $Object -and $Object.PSObject.Properties.Name -contains $Name) {
        return $Object.$Name
    }
    return $Default
}

function Test-TrivialCommand {
    param([string] $Command)
    $Text = $Command.Trim()
    if ([string]::IsNullOrWhiteSpace($Text)) { return $true }
    $Lower = $Text.ToLowerInvariant()
    $Lower = $Lower -replace '^(powershell|powershell\.exe|pwsh|pwsh\.exe)\s+(-noprofile\s+)?(-executionpolicy\s+\w+\s+)?(-command\s+)?', ''
    $Lower = $Lower.Trim().Trim('"').Trim("'").Trim()
    return $Lower -match '^(true|:|exit\s+0)$' -or $Lower -match '^(echo|write-output)\b'
}

function Check-Config {
    if (-not (Test-Path -LiteralPath $script:ConfigPath)) {
        return New-DoctorResult 'config' 'config' 'fail' "missing $script:ConfigPath"
    }
    try {
        $script:Config = Get-Content -LiteralPath $script:ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
        return New-DoctorResult 'config' 'config' 'pass' $script:ConfigPath
    }
    catch {
        return New-DoctorResult 'config' 'config' 'fail' "invalid JSON: $($_.Exception.Message)"
    }
}

function Check-HarnessRoot {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'harness.root' 'harness.root' 'skip' 'config unavailable'
    }
    $Harness = Get-ConfigValue $script:Config 'harness' $null
    $HarnessRoot = [string](Get-ConfigValue $Harness 'root' '')
    if ([string]::IsNullOrWhiteSpace($HarnessRoot)) {
        return New-DoctorResult 'harness.root' 'harness.root' 'fail' 'empty; /executeharness is disabled'
    }
    $ExecutePath = Join-Path $HarnessRoot 'scripts/execute.py'
    if (Test-Path -LiteralPath $ExecutePath) {
        return New-DoctorResult 'execute.py' 'execute.py' 'pass' $ExecutePath
    }
    return New-DoctorResult 'execute.py' 'execute.py' 'fail' "missing $ExecutePath"
}

function Check-IndexBackup {
    $BackupIndex = Join-Path $ProjectRoot 'phases/index.ezpowers.json'
    if (Test-Path -LiteralPath $BackupIndex) {
        return New-DoctorResult 'index backup' 'index backup' 'warn' 'phases/index.ezpowers.json exists; restore or discard before continuing'
    }
    return New-DoctorResult 'index backup' 'index backup' 'pass' 'no stale phases/index.ezpowers.json'
}

function Check-PhaseIndex {
    if ([string]::IsNullOrWhiteSpace($Phase)) {
        return New-DoctorResult 'phase index' 'phase index' 'skip' 'phase not supplied'
    }
    $PhaseIndex = Join-Path $ProjectRoot "phases/$Phase/index.json"
    if (Test-Path -LiteralPath $PhaseIndex) {
        $PhaseData = Get-Content -LiteralPath $PhaseIndex -Raw -Encoding UTF8 | ConvertFrom-Json
        $Pending = @($PhaseData.steps | Where-Object { $_.status -eq 'pending' }).Count
        return New-DoctorResult 'phase index' 'phase index' 'pass' "$PhaseIndex ($Pending pending)"
    }
    return New-DoctorResult 'phase index' 'phase index' 'warn' "missing $PhaseIndex; conversion required"
}

function Check-Smoke {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'smoke' 'smoke' 'skip' 'config unavailable'
    }
    $Smoke = Get-ConfigValue $script:Config 'smoke' $null
    if ($null -eq $Smoke) {
        return New-DoctorResult 'smoke' 'smoke' 'fail' 'missing smoke config'
    }
    $Required = [bool](Get-ConfigValue $Smoke 'required' $false)
    $Command = [string](Get-ConfigValue $Smoke 'command' '')
    $ArtifactKind = [string](Get-ConfigValue $Smoke 'artifact_kind' '')
    $GuiStrategy = [string](Get-ConfigValue $Smoke 'gui_strategy' '')

    if ($ArtifactKind -in @('cli', 'server', 'desktop') -and -not $Required) {
        return New-DoctorResult 'smoke' 'smoke' 'fail' "artifact_kind=$ArtifactKind requires smoke.required=true"
    }
    if ($Required -and [string]::IsNullOrWhiteSpace($Command)) {
        return New-DoctorResult 'smoke' 'smoke' 'fail' 'required=true but command is empty'
    }
    if ($ArtifactKind -eq 'desktop' -and $GuiStrategy -eq 'skip') {
        return New-DoctorResult 'smoke' 'smoke' 'fail' 'desktop artifact cannot use gui_strategy=skip'
    }

    $Build = Get-ConfigValue $script:Config 'build' $null
    $Test = Get-ConfigValue $script:Config 'test' $null
    $BuildCommand = [string](Get-ConfigValue $Build 'command' '')
    $TestCommand = [string](Get-ConfigValue $Test 'command' '')
    if ($Required -and -not [string]::IsNullOrWhiteSpace($Command)) {
        foreach ($Pair in @(@('build.command', $BuildCommand), @('test.command', $TestCommand))) {
            if (-not [string]::IsNullOrWhiteSpace($Pair[1]) -and $Command.Trim() -eq $Pair[1].Trim()) {
                return New-DoctorResult 'smoke parity' 'smoke parity' 'fail' "smoke.command matches $($Pair[0]); use the real app entry point"
            }
        }
    }
    return New-DoctorResult 'smoke' 'smoke' 'pass' "required=$Required"
}

function Check-Wiring {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'wiring' 'wiring' 'skip' 'config unavailable'
    }
    $Wiring = Get-ConfigValue $script:Config 'wiring' $null
    if ($null -eq $Wiring) {
        return New-DoctorResult 'wiring' 'wiring' 'fail' 'missing wiring config'
    }
    $Enabled = [bool](Get-ConfigValue $Wiring 'enabled' $false)
    $ExemptReason = [string](Get-ConfigValue $Wiring 'exempt_reason' '')
    $Smoke = Get-ConfigValue $script:Config 'smoke' $null
    $Kind = [string](Get-ConfigValue $Smoke 'artifact_kind' '')
    if (-not $Enabled -and [string]::IsNullOrWhiteSpace($ExemptReason)) {
        return New-DoctorResult 'wiring' 'wiring' 'fail' 'wiring disabled without exempt_reason'
    }
    if (-not $Enabled -and $Kind -notin @('docs', 'library')) {
        return New-DoctorResult 'wiring' 'wiring' 'fail' "wiring exemption not allowed for artifact_kind: $Kind"
    }
    return New-DoctorResult 'wiring' 'wiring' 'pass' "enabled=$Enabled"
}

function Check-ReviewerBackend {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'reviewer_backend' 'reviewer_backend' 'skip' 'config unavailable'
    }
    $Executor = Get-ConfigValue $script:Config 'executor' $null
    $Backend = [string](Get-ConfigValue $Executor 'reviewer_backend' 'claude-code')
    return New-DoctorResult 'reviewer_backend' 'reviewer_backend' 'pass' $(if ($Backend) { $Backend } else { 'claude-code default' })
}

function Check-ModelRouting {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'model routing' 'model routing' 'skip' 'config unavailable'
    }
    $Executor = Get-ConfigValue $script:Config 'executor' $null
    $Routing = Get-ConfigValue $Executor 'model_routing' $null
    if ($null -eq $Routing -or -not [bool](Get-ConfigValue $Routing 'enabled' $false)) {
        return New-DoctorResult 'model routing' 'model routing' 'pass' 'disabled; current defaults apply'
    }
    $Profile = [string](Get-ConfigValue $Routing 'default_profile' 'balanced')
    $Router = Join-Path $PSScriptRoot 'model-router.py'
    if (-not (Test-Path -LiteralPath $Router)) {
        return New-DoctorResult 'model routing' 'model routing' 'fail' "missing $Router"
    }
    $Output = & python $Router --project-root $ProjectRoot --backend harness-env --profile $Profile --json
    $Exit = $LASTEXITCODE
    $Parsed = $null
    try { $Parsed = ($Output -join "`n") | ConvertFrom-Json } catch { }
    if ($Exit -ne 0) {
        return New-DoctorResult 'model routing' 'model routing' 'fail' "profile=$Profile could not resolve" @($Output)
    }
    $Status = [string](Get-ConfigValue $Parsed 'status' '')
    $Selected = [string](Get-ConfigValue $Parsed 'selected' '')
    if ($Status -in @('unresolved', 'error')) {
        return New-DoctorResult 'model routing' 'model routing' 'warn' "profile=$Profile unresolved" @($Output)
    }
    if ($Status -eq 'unverified') {
        return New-DoctorResult 'model routing' 'model routing' 'warn' "profile=$Profile selected=$Selected without availability cache" @($Output)
    }
    return New-DoctorResult 'model routing' 'model routing' 'pass' "profile=$Profile selected=$Selected"
}

function Check-HookPolicy {
    $HooksPath = Join-Path $ProjectRoot 'hooks/hooks.json'
    $PolicyPath = Join-Path $ProjectRoot 'hooks/hook-policy.json'
    if (-not (Test-Path -LiteralPath $HooksPath) -and -not (Test-Path -LiteralPath $PolicyPath)) {
        return New-DoctorResult 'hook policy' 'hook policy' 'pass' 'not configured'
    }
    if ((Test-Path -LiteralPath $HooksPath) -and -not (Test-Path -LiteralPath $PolicyPath)) {
        return New-DoctorResult 'hook policy' 'hook policy' 'warn' 'hooks.json exists without hook-policy.json'
    }
    try {
        $Policy = Get-Content -LiteralPath $PolicyPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $Count = @($Policy.hooks).Count
        return New-DoctorResult 'hook policy' 'hook policy' 'pass' "$Count hook policy entries"
    }
    catch {
        return New-DoctorResult 'hook policy' 'hook policy' 'fail' "invalid hook-policy.json: $($_.Exception.Message)"
    }
}

function Check-AnchorSidecars {
    if ([string]::IsNullOrWhiteSpace($Phase)) {
        return New-DoctorResult 'hashline anchors' 'hashline anchors' 'skip' 'phase not supplied'
    }
    $PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
    $AnchorDir = Join-Path $PhaseDir 'anchors'
    if (-not (Test-Path -LiteralPath $AnchorDir)) {
        return New-DoctorResult 'hashline anchors' 'hashline anchors' 'pass' 'no anchor sidecars configured'
    }
    $Failures = @()
    foreach ($Anchor in Get-ChildItem -LiteralPath $AnchorDir -Filter '*.hashline.json') {
        $StepName = $Anchor.BaseName -replace '\.hashline$', ''
        $StepPath = Join-Path $PhaseDir "$StepName.md"
        if (-not (Test-Path -LiteralPath $StepPath)) {
            $Failures += "missing source for $($Anchor.Name)"
            continue
        }
        & python (Join-Path $PSScriptRoot 'hashline-anchor.py') verify --source $StepPath --anchor $Anchor.FullName --json *> $null
        if ($LASTEXITCODE -ne 0) {
            $Failures += "anchor mismatch: $($Anchor.Name)"
        }
    }
    if ($Failures.Count -gt 0) {
        return New-DoctorResult 'hashline anchors' 'hashline anchors' 'fail' 'anchor verification failed' $Failures
    }
    return New-DoctorResult 'hashline anchors' 'hashline anchors' 'pass' 'anchors verified'
}

function Check-StaticTools {
    if ($null -eq $script:Config) {
        return New-DoctorResult 'static verification' 'static verification' 'skip' 'config unavailable'
    }
    $Verification = Get-ConfigValue $script:Config 'verification' $null
    $Required = [bool](Get-ConfigValue $Verification 'static_required' $false)
    if (-not $Required) {
        return New-DoctorResult 'static verification' 'static verification' 'pass' 'optional'
    }
    $AstGrep = Get-Command 'ast-grep' -ErrorAction SilentlyContinue
    $Sg = Get-Command 'sg' -ErrorAction SilentlyContinue
    if ($AstGrep -or $Sg) {
        return New-DoctorResult 'static verification' 'static verification' 'pass' 'static tool available'
    }
    return New-DoctorResult 'static verification' 'static verification' 'fail' 'verification.static_required=true but ast-grep/sg is not available'
}

$CheckDefinitions = @(
    @{ Id = 'config'; Name = 'config'; Check = ${function:Check-Config} },
    @{ Id = 'harness.root'; Name = 'harness.root'; Check = ${function:Check-HarnessRoot} },
    @{ Id = 'index backup'; Name = 'index backup'; Check = ${function:Check-IndexBackup} },
    @{ Id = 'phase index'; Name = 'phase index'; Check = ${function:Check-PhaseIndex} },
    @{ Id = 'smoke'; Name = 'smoke'; Check = ${function:Check-Smoke} },
    @{ Id = 'wiring'; Name = 'wiring'; Check = ${function:Check-Wiring} },
    @{ Id = 'reviewer_backend'; Name = 'reviewer_backend'; Check = ${function:Check-ReviewerBackend} },
    @{ Id = 'model routing'; Name = 'model routing'; Check = ${function:Check-ModelRouting} },
    @{ Id = 'hook policy'; Name = 'hook policy'; Check = ${function:Check-HookPolicy} },
    @{ Id = 'hashline anchors'; Name = 'hashline anchors'; Check = ${function:Check-AnchorSidecars} },
    @{ Id = 'static verification'; Name = 'static verification'; Check = ${function:Check-StaticTools} }
)

$Results = @()
foreach ($Definition in $CheckDefinitions) {
    $Results += Invoke-DoctorCheck -Id $Definition.Id -Name $Definition.Name -Check $Definition.Check
}

$Failures = @($Results | Where-Object { $_.status -eq 'fail' }).Count
$Warnings = @($Results | Where-Object { $_.status -eq 'warn' }).Count
$Skipped = @($Results | Where-Object { $_.status -eq 'skip' }).Count
$Passed = @($Results | Where-Object { $_.status -eq 'pass' }).Count
$ExitCode = if ($Failures -gt 0) { 1 } elseif ($Warnings -gt 0) { 2 } else { 0 }

$Report = [pscustomobject]@{
    results = $Results
    summary = [pscustomobject]@{
        total = @($Results).Count
        passed = $Passed
        failed = $Failures
        warnings = $Warnings
        skipped = $Skipped
    }
    exitCode = $ExitCode
}

if ($Json) {
    $Report | ConvertTo-Json -Depth 20
    exit $ExitCode
}

if ($Status) {
    $Verdict = if ($Failures -gt 0) { 'FAIL' } elseif ($Warnings -gt 0) { 'WARN' } else { 'PASS' }
    Write-Output "$Verdict $Passed/$(@($Results).Count) passed, $Warnings warning(s), $Failures failure(s), $Skipped skipped"
    exit $ExitCode
}

foreach ($Result in $Results) {
    $DisplayStatus = $Result.status.ToUpperInvariant()
    Write-Output "[$DisplayStatus] $($Result.name) - $($Result.message)"
    if ($Verbose -and $Result.details.Count -gt 0) {
        foreach ($Detail in $Result.details) {
            Write-Output "  $Detail"
        }
    }
}

if ($Failures -gt 0) {
    Write-Output "Harness doctor verdict: FAIL ($Failures failure(s), $Warnings warning(s))"
    exit 1
}

Write-Output "Harness doctor verdict: PASS ($Warnings warning(s))"
exit $ExitCode
