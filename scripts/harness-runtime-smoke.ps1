<#
.SYNOPSIS
    End-to-end runtime smoke suite for the PowerShell harness helpers.

.DESCRIPTION
    Exercises each harness runtime script (phase/doctor/convert/gate/run,
    lightpath gate, certify, resume proof, smoke, model router, hashline anchor,
    context injector, verify-step static, frontend visual readiness) against
    disposable fixtures under $env:TEMP. Each smoke throws on failure and cleans
    up its own temp tree in a finally block.

.PARAMETER Only
    Run only the smokes whose name matches this pattern. Substring match by
    default; PowerShell wildcards (* ? [ ]) are honored if present.

.PARAMETER List
    Print the smoke names that would run (respecting -Only) and exit without
    executing them.

.OUTPUTS
    Per-smoke [PASS]/[FAIL] lines plus a summary. Exit code is the number of
    failing smokes (0 when all pass).
#>
param(
    [string] $Only,
    [switch] $List
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Set-SmokeBoundVerdict {
    # Mirrors lightpath-gate.ps1 Set-LightpathReviewerVerdict: a reviewer verdict
    # is only accepted when bound to the evidence_fingerprint the gate stamped
    # during its mechanical evidence run (harness-gate.ps1 fingerprint binding).
    param(
        [string] $GatePath,
        [string] $Verdict
    )
    $Gate = Get-Content -LiteralPath $GatePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Gate.status -ne 'review_pending') {
        throw "[FAIL] harness gate: expected review_pending before verdict binding, got $($Gate.status)"
    }
    $Fingerprint = [string]$Gate.evidence_fingerprint
    if ([string]::IsNullOrWhiteSpace($Fingerprint)) {
        throw '[FAIL] harness gate: evidence_fingerprint missing after gate run'
    }
    if (-not ($Gate.PSObject.Properties.Name -contains 'reviewer_verdict')) {
        $Gate | Add-Member -NotePropertyName reviewer_verdict -NotePropertyValue '' -Force
    }
    $Gate.reviewer_verdict = $Verdict
    if (-not ($Gate.PSObject.Properties.Name -contains 'verdict_fingerprint')) {
        $Gate | Add-Member -NotePropertyName verdict_fingerprint -NotePropertyValue '' -Force
    }
    $Gate.verdict_fingerprint = $Fingerprint
    $Gate | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $GatePath -Encoding UTF8
}

function Assert-HarnessPhaseHelper {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-docs-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null

    try {
        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "first", "status": "completed", "step_md": "step0.md" },
    { "step": 1, "name": "second", "status": "completed", "step_md": "step1.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8

        & (Join-Path $RepoRoot 'scripts/harness-phase.ps1') -ProjectRoot $TempRoot -Phase 'sample' -ResetStep 1 | Out-Null
        $Updated = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $Step = $Updated.steps | Where-Object { [int]$_.step -eq 1 } | Select-Object -First 1
        if ($Step.status -ne 'pending') {
            throw "[FAIL] harness phase helper: reset-step did not set pending"
        }

        $StatusOutput = & (Join-Path $RepoRoot 'scripts/harness-phase.ps1') -ProjectRoot $TempRoot -Phase 'sample' -Status
        if (($StatusOutput -join "`n") -notlike '*pending*') {
            throw "[FAIL] harness phase helper: status output did not include pending"
        }

        $DefaultOutput = & (Join-Path $RepoRoot 'scripts/harness-phase.ps1') -ProjectRoot $TempRoot -Phase 'sample'
        if (($DefaultOutput -join "`n") -notlike '*pending*') {
            throw "[FAIL] harness phase helper: default output did not include status"
        }

        Write-Output "[PASS] harness phase helper status/reset"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessDoctor {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-doctor-" + [guid]::NewGuid().ToString("N"))
    $HarnessRoot = Join-Path $TempRoot 'harness'
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $HarnessRoot 'scripts') | Out-Null
    New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null

    try {
        '' | Set-Content -LiteralPath (Join-Path $HarnessRoot 'scripts/execute.py') -Encoding UTF8
        @"
{
  "harness": { "root": "$($HarnessRoot.Replace('\', '\\'))" },
  "smoke": { "required": true, "artifact_kind": "cli", "command": "echo ok" },
  "wiring": { "enabled": true, "exempt_reason": "", "view_extensions": [] },
  "executor": { "reviewer_backend": "claude-code" }
}
"@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "first", "status": "pending", "step_md": "step0.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8

        $DoctorOutput = & (Join-Path $RepoRoot 'scripts/harness-doctor.ps1') -ProjectRoot $TempRoot -Phase 'sample'
        if (($DoctorOutput -join "`n") -notlike '*Harness doctor verdict: PASS*') {
            throw "[FAIL] harness doctor: expected PASS"
        }

        Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8 -Value '{"harness":{"root":""}}'
        & (Join-Path $RepoRoot 'scripts/harness-doctor.ps1') -ProjectRoot $TempRoot *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness doctor: empty harness.root should fail"
        }

        Write-Output "[PASS] harness doctor preflight"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessConvert {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-convert-" + [guid]::NewGuid().ToString("N"))
    $PlanDir = Join-Path $TempRoot 'docs/plans'
    New-Item -ItemType Directory -Force -Path $PlanDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

    try {
        '{"project":"fixture"}' | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
# Plan: Sample Feature

## Goal
Ship a tiny feature.

## Architecture
One deep module with a public CLI interface.

## Tech Stack
PowerShell fixture.

## Full-Feature Wiring Gate
**Required:** yes
**Verify-type:** cli
**Covers:** T1 -> T2
**Expected observation:** CLI entry point routes the command
**Verify:** `if (-not (Test-Path gate-target.txt)) { exit 1 }`

### Task 1: Add command [R1]

**Files:**
- Modify: `src/app.ps1`
- Test: `tests/app.Tests.ps1`

**Completion criteria (from spec):**
- [ ] Given: CLI input / When: command runs / Then: output appears / Verify: `pwsh -NoProfile -Command "exit 0"`

**Verification method:** Run spec Verify commands.

### Task 2: Wire command [R1]

**Files:**
- Modify: `src/main.ps1`

**Completion criteria (from spec):**
- [ ] Given: entry point / When: command runs / Then: command is routed / Verify: `pwsh -NoProfile -Command "exit 0"`

**Verification method:** Run spec Verify commands.
'@ | Set-Content -LiteralPath (Join-Path $PlanDir '2026-05-13-sample-feature.md') -Encoding UTF8

        & (Join-Path $RepoRoot 'scripts/harness-convert.ps1') -ProjectRoot $TempRoot -PlanPath 'docs/plans/2026-05-13-sample-feature.md' | Out-Null
        $PhaseDir = Join-Path $TempRoot 'phases/sample-feature'
        foreach ($Path in @('phase-context.md', 'step0.md', 'step1.md', 'index.json', 'wiring-gate.json')) {
            if (-not (Test-Path -LiteralPath (Join-Path $PhaseDir $Path))) {
                throw "[FAIL] harness convert: missing $Path"
            }
        }

        $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($Index.steps).Count -ne 2) {
            throw "[FAIL] harness convert: expected 2 steps"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $Gate.required -or @($Gate.commands).Count -lt 1) {
            throw "[FAIL] harness convert: expected required wiring gate with command"
        }
        if (@($Gate.commands).Count -ne 1 -or @($Gate.commands)[0] -ne 'if (-not (Test-Path gate-target.txt)) { exit 1 }') {
            throw "[FAIL] harness convert: wiring gate captured task-local backticks"
        }
        if ($Gate.verify_type -ne 'cli') {
            throw "[FAIL] harness convert: expected Verify-type to be preserved"
        }
        if (@($Gate.covered_tasks).Count -ne 2 -or @($Gate.covered_tasks)[0] -ne 'T1' -or @($Gate.covered_tasks)[1] -ne 'T2') {
            throw "[FAIL] harness convert: expected Covers tasks to be preserved"
        }
        if ($Gate.expected_observation -ne 'CLI entry point routes the command') {
            throw "[FAIL] harness convert: expected observation was not preserved"
        }

        Write-Output "[PASS] harness convert plan-to-phase"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessGate {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-gate-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

    try {
        '{"smoke":{"required":false,"artifact_kind":"library"},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "cli",
  "commands": ["if (-not (Test-Path gate-target.txt)) { exit 1 }"],
  "covered_tasks": ["T1"],
  "covered_edges": [],
  "expected_observation": "gate ok",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        'ok' | Set-Content -LiteralPath (Join-Path $TempRoot 'gate-target.txt') -Encoding UTF8

        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 5) {
            throw "[FAIL] harness gate: review_pending should exit 5"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'review_pending' -or @($Gate.attempts).Count -lt 1) {
            throw "[FAIL] harness gate: pass command did not record pass attempt"
        }
        if ($Gate.evidence_status -ne 'command_passed') {
            throw "[FAIL] harness gate: passing command should wait for reviewer evidence"
        }

        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "cli",
  "commands": ["true"],
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: no-op command should fail"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'spec_gap') {
            throw "[FAIL] harness gate: no-op command did not set spec_gap"
        }

        '{"smoke":{"required":true,"artifact_kind":"cli","command":"pwsh -NoProfile -Command \"Write-Output smoke\""},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "cli",
  "commands": ["if (-not (Test-Path gate-target.txt)) { exit 1 }"],
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: missing runtime evidence should fail for executable artifact"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'test_gap') {
            throw "[FAIL] harness gate: missing runtime evidence did not set test_gap"
        }

        '{"smoke":{"required":true,"artifact_kind":"desktop","command":"pwsh -NoProfile -Command \"Write-Output smoke\"","screenshot_path":".harness/artifacts/gui-smoke.png","min_pixel_variance":12.0},"server":{"health_check_url":"http://localhost:3000/health"},"wiring":{"enabled":true,"view_extensions":[".tsx"]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "e2e",
  "commands": ["if (1 -eq 1) { Write-Output gate } else { exit 1 }"],
  "expected_observation": "desktop UI shows server API data",
  "reviewer_verdict": "PASS",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        @'
{
  "status": "completed",
  "step": 0,
  "command": "smoke",
  "exit_code": 0,
  "timed_out": false
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: reviewer PASS must not pass missing desktop evidence"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'test_gap' -or $Gate.message -notmatch 'desktop evidence') {
            throw "[FAIL] harness gate: missing desktop evidence did not set runtime test_gap"
        }

        New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness/artifacts') | Out-Null
        'fake screenshot' | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/artifacts/gui-smoke.png') -Encoding UTF8
        @'
{
  "status": "completed",
  "step": 0,
  "command": "smoke",
  "exit_code": 0,
  "timed_out": false,
  "desktop_evidence": {
    "window_found": true,
    "screenshot_path": ".harness/artifacts/gui-smoke.png",
    "pixel_variance": 18.5,
    "ui_text": "Dashboard loaded",
    "automation_names": ["DashboardWindow"],
    "api_observation": "GET /api/dashboard returned 200"
  }
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "e2e",
  "commands": ["if (1 -eq 1) { Write-Output gate } else { exit 1 }"],
  "expected_observation": "desktop UI shows server API data",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 5) {
            throw "[FAIL] harness gate: desktop evidence fixture should reach review_pending first"
        }
        Set-SmokeBoundVerdict -GatePath (Join-Path $PhaseDir 'wiring-gate.json') -Verdict 'PASS'
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "[FAIL] harness gate: desktop evidence fixture should pass"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'pass' -or @($Gate.runtime_artifacts) -notcontains '.harness/artifacts/gui-smoke.png') {
            throw "[FAIL] harness gate: desktop evidence pass did not record screenshot artifact"
        }

        '{"smoke":{"required":true,"artifact_kind":"web","command":"pwsh -NoProfile -Command \"Write-Output smoke\""},"app_delivery":{"surface_kind":"web","frontend":{"present":true},"backend":{"present":true}},"server":{"health_check_url":"http://localhost:3000/health"},"ui_verification":{"required":true,"capability":"browser-e2e"},"wiring":{"enabled":true,"view_extensions":[".tsx"]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "e2e",
  "commands": ["if (1 -eq 1) { Write-Output gate } else { exit 1 }"],
  "expected_observation": "web client renders API endpoint data",
  "reviewer_verdict": "PASS",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        @'
{
  "status": "completed",
  "step": 0,
  "command": "smoke",
  "exit_code": 0,
  "timed_out": false
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: reviewer PASS must not pass missing client-server evidence"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'test_gap' -or $Gate.message -notmatch 'client-server evidence') {
            throw "[FAIL] harness gate: missing client-server evidence did not set runtime test_gap"
        }

        @'
{
  "status": "completed",
  "step": 0,
  "command": "smoke",
  "exit_code": 0,
  "timed_out": false,
  "client_server_evidence": {
    "api_observation": "GET /api/dashboard returned 200 and rendered Dashboard",
    "endpoint": "/api/dashboard",
    "status_code": 200
  }
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "e2e",
  "commands": ["if (1 -eq 1) { Write-Output gate } else { exit 1 }"],
  "expected_observation": "web client renders API endpoint data",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 5) {
            throw "[FAIL] harness gate: client-server evidence fixture should reach review_pending first"
        }
        Set-SmokeBoundVerdict -GatePath (Join-Path $PhaseDir 'wiring-gate.json') -Verdict 'PASS'
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "[FAIL] harness gate: client-server evidence fixture should pass"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'pass' -or @($Gate.runtime_artifacts) -notcontains 'runtime-probe.json') {
            throw "[FAIL] harness gate: client-server evidence pass did not record runtime artifact"
        }

        '{"smoke":{"required":false,"artifact_kind":"library"},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "phase": "sample",
  "required": true,
  "verify_type": "cli",
  "commands": ["if (-not (Test-Path gate-target.txt)) { exit 1 }"],
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -ne 5) {
            throw "[FAIL] harness gate: CODE_GAP fixture should reach review_pending first"
        }
        Set-SmokeBoundVerdict -GatePath (Join-Path $PhaseDir 'wiring-gate.json') -Verdict 'CODE_GAP'
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: CODE_GAP reviewer verdict should fail"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'code_gap') {
            throw "[FAIL] harness gate: CODE_GAP reviewer verdict did not set code_gap"
        }

        @'
{
  "phase": "sample",
  "required": true,
  "commands": ["exit 7"],
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: failing command should fail"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'fail') {
            throw "[FAIL] harness gate: failing command did not set fail status"
        }

        @'
{
  "phase": "sample",
  "required": true,
  "commands": [],
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness gate: empty required commands should fail"
        }
        $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Gate.status -ne 'spec_gap') {
            throw "[FAIL] harness gate: empty commands did not set spec_gap"
        }

        Write-Output "[PASS] harness gate execution"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessRun {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-run-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    $FakeExecutor = Join-Path $TempRoot 'fake-executor.ps1'
    New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null

    try {
        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "first", "status": "pending", "step_md": "step0.md" },
    { "step": 1, "name": "second", "status": "pending", "step_md": "step1.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8

        @'
param(
    [string] $ProjectRoot,
    [string] $Phase
)

if (-not [string]::IsNullOrWhiteSpace($env:EZPOWERS_MODEL)) {
    $env:EZPOWERS_MODEL | Set-Content -LiteralPath (Join-Path $ProjectRoot 'selected-model.txt') -Encoding UTF8
}

$IndexPath = Join-Path $ProjectRoot "phases/$Phase/index.json"
$Index = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8 | ConvertFrom-Json
$Step = $Index.steps | Where-Object { $_.status -eq 'pending' } | Sort-Object { [int]$_.step } | Select-Object -First 1
if (-not $Step) {
    Write-Output 'no pending step'
    exit 0
}
$Step.status = 'completed'
$Index | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $IndexPath -Encoding UTF8
Write-Output "completed step $($Step.step)"
'@ | Set-Content -LiteralPath $FakeExecutor -Encoding UTF8
        @'
# Step 0

## Files to Read
- `step0.txt`

## Task
Done.

## Acceptance Criteria
- [ ] Given: step 0 / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

## Verification
Verify: `python -c "raise SystemExit(0)"`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        'step0' | Set-Content -LiteralPath (Join-Path $TempRoot 'step0.txt') -Encoding UTF8
        @'
# Step 1

## Files to Read
- `step1.txt`

## Task
Done.

## Acceptance Criteria
- [ ] Given: step 1 / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

## Verification
Verify: `python -c "raise SystemExit(0)"`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step1.md') -Encoding UTF8
        'step1' | Set-Content -LiteralPath (Join-Path $TempRoot 'step1.txt') -Encoding UTF8

        & (Join-Path $RepoRoot 'scripts/harness-run.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'sample' `
            -ExecutorCommand "& '$FakeExecutor' -ProjectRoot '$TempRoot' -Phase 'sample'" `
            -ExplicitModel 'gpt-explicit-test' `
            -TimeoutSeconds 10 | Out-Null

        $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $Pending = @($Index.steps | Where-Object { $_.status -eq 'pending' }).Count
        if ($Pending -ne 0) {
            throw "[FAIL] harness run: expected all steps completed"
        }
        $SelectedModel = Get-Content -LiteralPath (Join-Path $TempRoot 'selected-model.txt') -Raw -Encoding UTF8
        if ($SelectedModel.Trim() -ne 'gpt-explicit-test') {
            throw "[FAIL] harness run: explicit model override was not passed to executor"
        }

        $RunLog = Get-Content -LiteralPath (Join-Path $PhaseDir 'harness-run.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($RunLog.attempts).Count -ne 2) {
            throw "[FAIL] harness run: expected two recorded attempts"
        }
        if (@($RunLog.attempts | Where-Object { $_.exit_code -eq 0 }).Count -ne 2) {
            throw "[FAIL] harness run: expected successful attempt exit codes"
        }

        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "bad verify", "status": "pending", "step_md": "step0.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8
        @'
# Step 0

## Files to Read
- `missing-file.txt`

## Task
Done.

## Acceptance Criteria
- [ ] Given: app / When: action / Then: result / Verify: `exit 9`

## Verification
Verify: `exit 9`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/harness-run.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'sample' `
            -ExecutorCommand "& '$FakeExecutor' -ProjectRoot '$TempRoot' -Phase 'sample'" `
            -TimeoutSeconds 10 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness run: verify-step failure should fail the run"
        }
        $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($Index.steps)[0].status -ne 'rejected') {
            throw "[FAIL] harness run: verify-step failure should reject the step"
        }

        Write-Output "[PASS] harness run controlled execution"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-LightpathGate {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-lightpath-gate-" + [guid]::NewGuid().ToString("N"))
    $PlanDir = Join-Path $TempRoot 'docs/plans'
    New-Item -ItemType Directory -Force -Path $PlanDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

    try {
        @'
{
  "smoke": {
    "required": true,
    "artifact_kind": "cli",
    "command": "python -c \"print('smoke')\"",
    "timeout_sec": 10
  },
  "wiring": {
    "enabled": true,
    "view_extensions": []
  }
}
'@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        'ok' | Set-Content -LiteralPath (Join-Path $TempRoot 'app.txt') -Encoding UTF8
        'ok' | Set-Content -LiteralPath (Join-Path $TempRoot 'gate-target.txt') -Encoding UTF8
        @'
# Plan: Lightpath Sample

## Goal
Ship a lightpath feature.

## Full-Feature Wiring Gate
**Required:** yes
**Verify-type:** cli
**Covers:** T1
**Expected observation:** CLI entry point routes the command
**Verify:** `python -c "from pathlib import Path; raise SystemExit(0 if Path('gate-target.txt').exists() else 1)"`

### Task 1: Add behavior [R1]

**Files:**
- Modify: `app.txt`

**Completion criteria (from spec):**
- [ ] Given: CLI input / When: command runs / Then: output appears / Verify: `python -c "raise SystemExit(0)"`

**Verification method:** Run spec Verify commands.
'@ | Set-Content -LiteralPath (Join-Path $PlanDir '2026-05-13-lightpath-sample.md') -Encoding UTF8

        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -PlanPath 'docs/plans/2026-05-13-lightpath-sample.md' `
            -Phase 'lightpath-sample' `
            -Scope prepare | Out-Null
        $PhaseDir = Join-Path $TempRoot 'phases/lightpath-sample'
        foreach ($Path in @('step0.md', 'index.json', 'wiring-gate.json', 'lightpath-gate.json')) {
            if (-not (Test-Path -LiteralPath (Join-Path $PhaseDir $Path))) {
                throw "[FAIL] lightpath gate: prepare missing $Path"
            }
        }

        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'lightpath-sample' `
            -TaskNumber 1 `
            -Scope task | Out-Null
        $State = Get-Content -LiteralPath (Join-Path $PhaseDir 'lightpath-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($State.status -ne 'pass' -or $State.evidence_status -ne 'task_verified') {
            throw "[FAIL] lightpath gate: task gate did not pass"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $PhaseDir 'runtime-probe.json'))) {
            throw "[FAIL] lightpath gate: task gate did not write runtime-probe.json"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $PhaseDir 'task-gates/task-1.json'))) {
            throw "[FAIL] lightpath gate: task gate did not write task proof"
        }

        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'lightpath-sample' `
            -DiffRange 'HEAD~1..HEAD' `
            -Scope final *> $null
        if ($LASTEXITCODE -ne 5) {
            throw "[FAIL] lightpath gate: final gate without reviewer should exit review_pending"
        }
        $State = Get-Content -LiteralPath (Join-Path $PhaseDir 'lightpath-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($State.status -ne 'review_pending') {
            throw "[FAIL] lightpath gate: final gate did not record review_pending"
        }

        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'lightpath-sample' `
            -DiffRange 'HEAD~1..HEAD' `
            -ReviewerVerdict 'CODE_GAP' `
            -Scope final *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] lightpath gate: CODE_GAP reviewer verdict should fail"
        }
        $State = Get-Content -LiteralPath (Join-Path $PhaseDir 'lightpath-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($State.status -ne 'code_gap') {
            throw "[FAIL] lightpath gate: CODE_GAP did not set code_gap"
        }

        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'lightpath-sample' `
            -DiffRange 'HEAD~1..HEAD' `
            -ReviewerVerdict 'PASS' `
            -Scope final | Out-Null
        $State = Get-Content -LiteralPath (Join-Path $PhaseDir 'lightpath-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($State.status -ne 'pass') {
            throw "[FAIL] lightpath gate: PASS reviewer verdict did not pass"
        }
        $Certificate = Get-Content -LiteralPath (Join-Path $PhaseDir 'completion-certificate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Certificate.status -ne 'pass') {
            throw "[FAIL] lightpath gate: final pass did not certify completion"
        }

        @'
# Step 0

## Files to Read
- `missing-file.txt`

## Task
Bad task.

## Acceptance Criteria
- [ ] Given: app / When: action / Then: result / Verify: `exit 9`

## Verification
Verify: `exit 9`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        & (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1') `
            -ProjectRoot $TempRoot `
            -Phase 'lightpath-sample' `
            -TaskNumber 1 `
            -Scope task *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] lightpath gate: failing task Verify should fail"
        }
        $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (@($Index.steps)[0].status -ne 'rejected') {
            throw "[FAIL] lightpath gate: failing task Verify should reject the step"
        }

        Write-Output "[PASS] lightpath gate execution"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessCertify {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-certify-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    $TaskGateDir = Join-Path $PhaseDir 'task-gates'
    New-Item -ItemType Directory -Force -Path $TaskGateDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

    function Write-CertifyProof {
        param(
            [string] $Hash,
            [string] $VerifyType = 'cli',
            [int] $VerifyTimeoutSeconds = 120
        )

        [pscustomobject]@{
            schema_version = 1
            phase = 'sample'
            task_number = 1
            step = 0
            step_md = 'step0.md'
            step_sha256 = $Hash
            status = 'pass'
            evidence_status = 'task_verified'
            message = 'task verified'
            verify_type = $VerifyType
            verify_commands = @('python -c "raise SystemExit(0)"')
            verify_commands_count = 1
            verify_timeout_seconds = $VerifyTimeoutSeconds
            verify_exit_code = 0
            verify_timed_out = $false
            verify_result = [pscustomobject]@{ pass = $true }
        } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $TaskGateDir 'task-1.json') -Encoding UTF8
    }

    try {
        '{"smoke":{"required":false,"artifact_kind":"library"},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "first", "status": "completed", "step_md": "step0.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8
        @'
# Step 0

## Acceptance Criteria
- [ ] Given: app / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

## Verification
Verify: `python -c "raise SystemExit(0)"`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        '{"phase":"sample","required":false,"status":"pass","commands":[],"attempts":[]}' |
            Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8

        $Hash = (Get-FileHash -LiteralPath (Join-Path $PhaseDir 'step0.md') -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-CertifyProof -Hash $Hash
        & (Join-Path $RepoRoot 'scripts/harness-certify.ps1') -ProjectRoot $TempRoot -Phase 'sample' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "[FAIL] harness certify: expected valid proof to pass"
        }
        $Certificate = Get-Content -LiteralPath (Join-Path $PhaseDir 'completion-certificate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Certificate.status -ne 'pass') {
            throw "[FAIL] harness certify: certificate did not pass"
        }

        Remove-Item -LiteralPath (Join-Path $TaskGateDir 'task-1.json') -Force
        & (Join-Path $RepoRoot 'scripts/harness-certify.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness certify: missing task proof should fail"
        }
        $Certificate = Get-Content -LiteralPath (Join-Path $PhaseDir 'completion-certificate.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Certificate.status -ne 'test_gap') {
            throw "[FAIL] harness certify: missing proof did not set test_gap"
        }

        Write-CertifyProof -Hash 'stale'
        & (Join-Path $RepoRoot 'scripts/harness-certify.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness certify: stale proof should fail"
        }

        Write-CertifyProof -Hash $Hash -VerifyType 'e2e' -VerifyTimeoutSeconds 30
        & (Join-Path $RepoRoot 'scripts/harness-certify.ps1') -ProjectRoot $TempRoot -Phase 'sample' *> $null
        if ($LASTEXITCODE -eq 0) {
            throw "[FAIL] harness certify: e2e proof with short timeout should fail"
        }

        Write-Output "[PASS] harness certify completion proof"
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessResumeProof {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-harness-resume-proof-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    $TaskGateDir = Join-Path $PhaseDir 'task-gates'
    New-Item -ItemType Directory -Force -Path $TaskGateDir | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

    function Write-ResumeTaskGate {
        param(
            [string] $Hash,
            [string] $Status = 'pass',
            [int] $ExitCode = 0,
            [bool] $TimedOut = $false,
            [bool] $VerifyPass = $true,
            [string] $VerifyType = 'cli',
            [int] $VerifyTimeoutSeconds = 120
        )

        [pscustomobject]@{
            schema_version = 1
            phase = 'sample'
            task_number = 1
            step = 0
            step_md = 'step0.md'
            step_sha256 = $Hash
            status = $Status
            evidence_status = 'task_verified'
            message = 'task verified'
            verify_type = $VerifyType
            verify_commands = @('python -c "raise SystemExit(0)"')
            verify_commands_count = 1
            verify_timeout_seconds = $VerifyTimeoutSeconds
            verify_exit_code = $ExitCode
            verify_timed_out = $TimedOut
            verify_result = [pscustomobject]@{ pass = $VerifyPass }
        } | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $TaskGateDir 'task-1.json') -Encoding UTF8
    }

    try {
        '{"smoke":{"required":false,"artifact_kind":"library"},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "project": "sample",
  "phase": "sample",
  "steps": [
    { "step": 0, "name": "first", "status": "completed", "step_md": "step0.md" },
    { "step": 1, "name": "second", "status": "pending", "step_md": "step1.md" }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8
        @'
# Step 0

## Acceptance Criteria
- [ ] Given: app / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

## Verification
Verify: `python -c "raise SystemExit(0)"`
Verify-type: cli
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        @'
# Step 1

## Acceptance Criteria
- [ ] Given: app / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step1.md') -Encoding UTF8

        $Hash = (Get-FileHash -LiteralPath (Join-Path $PhaseDir 'step0.md') -Algorithm SHA256).Hash.ToLowerInvariant()
        Write-ResumeTaskGate -Hash $Hash
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 -PlanPath 'docs/plans/sample.md' -ResumeHash 'abc123' | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw '[FAIL] harness resume proof: expected fresh task proof to pass'
        }
        $Proof = Get-Content -LiteralPath (Join-Path $PhaseDir 'resume-proof.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($Proof.status -ne 'pass' -or @($Proof.verified_task_gate_paths).Count -ne 1) {
            throw '[FAIL] harness resume proof: pass proof did not record verified prefix'
        }

        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 2 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: pending checked task should fail'
        }

        Remove-Item -LiteralPath (Join-Path $TaskGateDir 'task-1.json') -Force
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: missing task proof should fail'
        }

        Write-ResumeTaskGate -Hash 'stale'
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: stale task proof should fail'
        }

        Write-ResumeTaskGate -Hash $Hash -VerifyType 'e2e' -VerifyTimeoutSeconds 30
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: e2e proof with short timeout should fail'
        }

        Write-ResumeTaskGate -Hash $Hash -ExitCode 1 -VerifyPass $false
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: failing Verify evidence should fail'
        }

        '{"smoke":{"required":true,"artifact_kind":"cli","command":"python -c \"print(''smoke'')\""},"wiring":{"enabled":true,"view_extensions":[]}}' |
            Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        Write-ResumeTaskGate -Hash $Hash
        & (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1') -ProjectRoot $TempRoot -Phase 'sample' -CompletedTaskCount 1 *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] harness resume proof: missing required runtime evidence should fail'
        }

        Write-Output '[PASS] harness resume proof prefix validation'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HarnessSmoke {
    $SmokeOutput = & (Join-Path $RepoRoot 'scripts/harness-smoke.ps1')
    if (($SmokeOutput -join "`n") -notlike '*Harness smoke passed.*') {
        throw '[FAIL] harness smoke: expected pass output'
    }

    Write-Output '[PASS] harness smoke end-to-end'
}

function Assert-ModelRouter {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-model-router-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null
    try {
        @'
{
  "executor": {
    "model_routing": {
      "enabled": true,
      "default_profile": "deep-analysis",
      "availability_cache": ".harness/model-availability.json"
    }
  }
}
'@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
{
  "models": {
    "harness-env": ["gpt-5.5"]
  }
}
'@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/model-availability.json') -Encoding UTF8

        $Output = & python (Join-Path $RepoRoot 'scripts/model-router.py') --project-root $TempRoot --backend harness-env --profile deep-analysis --json
        if ($LASTEXITCODE -ne 0) {
            throw "[FAIL] model router: expected successful resolution"
        }
        $Result = ($Output -join "`n") | ConvertFrom-Json
        if ($Result.selected -ne 'gpt-5.5' -or $Result.status -ne 'resolved') {
            throw "[FAIL] model router: expected gpt-5.5 resolved from availability cache"
        }
        Write-Output '[PASS] model router resolution'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-HashlineAnchor {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-hashline-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
    try {
        $Source = Join-Path $TempRoot 'step0.md'
        $Anchor = Join-Path $TempRoot 'anchors/step0.hashline.json'
        "alpha`n베타`n" | Set-Content -LiteralPath $Source -Encoding UTF8
        & python (Join-Path $RepoRoot 'scripts/hashline-anchor.py') stamp --source $Source --anchor $Anchor | Out-Null
        & python (Join-Path $RepoRoot 'scripts/hashline-anchor.py') verify --source $Source --anchor $Anchor --json | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw '[FAIL] hashline anchor: expected clean verify'
        }
        "alpha changed`n베타`n" | Set-Content -LiteralPath $Source -Encoding UTF8
        & python (Join-Path $RepoRoot 'scripts/hashline-anchor.py') verify --source $Source --anchor $Anchor --json *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] hashline anchor: drift should fail verify'
        }
        Write-Output '[PASS] hashline anchor drift detection'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-ContextInjector {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-context-injector-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
    try {
        $Block = & python (Join-Path $RepoRoot 'scripts/context-injector.py') build --kind contract --content 'docs/reference/model-routing-contract.md'
        $Prompt = Join-Path $TempRoot 'prompt.md'
        (($Block -join "`n") + "`n" + ($Block -join "`n")) | Set-Content -LiteralPath $Prompt -Encoding UTF8
        & python (Join-Path $RepoRoot 'scripts/context-injector.py') verify --file $Prompt --json *> $null
        if ($LASTEXITCODE -eq 0) {
            throw '[FAIL] context injector: duplicate sentinel should fail'
        }
        Write-Output '[PASS] context injector duplicate detection'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-VerifyStepStatic {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-verify-static-" + [guid]::NewGuid().ToString("N"))
    $PhaseDir = Join-Path $TempRoot 'phases/sample'
    New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null
    try {
        'ok' | Set-Content -LiteralPath (Join-Path $TempRoot 'app.txt') -Encoding UTF8
        @'
# Step 0

## Files to Read
- `app.txt`

## Task
Done.

## Acceptance Criteria
- [ ] Given: app / When: command runs / Then: command passes / Verify: `python -c "raise SystemExit(0)"`

## Verification
Verify: `python -c "raise SystemExit(0)"`
Verify-type: cli
Static-verify: `python -c "raise SystemExit(0)"`
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'step0.md') -Encoding UTF8
        $Output = & python (Join-Path $RepoRoot 'scripts/verify-step.py') --step-md (Join-Path $PhaseDir 'step0.md') --project-root $TempRoot --phase sample
        if ($LASTEXITCODE -ne 0) {
            throw '[FAIL] verify-step static: expected pass'
        }
        $Result = ($Output -join "`n") | ConvertFrom-Json
        if (-not ($Result.dimensions.PSObject.Properties.Name -contains 'static')) {
            throw '[FAIL] verify-step static: missing static dimension'
        }
        Write-Output '[PASS] verify-step static dimension'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

function Assert-FrontendVisualReadiness {
    $TempRoot = Join-Path $env:TEMP ("ezpowers-frontend-visual-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot 'docs/ux') | Out-Null
    try {
        @'
{
  "app_delivery": {
    "frontend": {
      "design_artifact": "docs/ux/frontend-design.md"
    }
  }
}
'@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8
        @'
# Frontend Design

Visual QA strategy: component DOM fallback.
'@ | Set-Content -LiteralPath (Join-Path $TempRoot 'docs/ux/frontend-design.md') -Encoding UTF8

        $Output = & python (Join-Path $RepoRoot 'scripts/frontend-visual-readiness.py') --project-root $TempRoot --json
        if ($LASTEXITCODE -ne 0) {
            throw '[FAIL] frontend visual readiness: no-tool advisory path should pass'
        }
        $Result = ($Output -join "`n") | ConvertFrom-Json
        if ($Result.lanes.storybook_component_states.required) {
            throw '[FAIL] frontend visual readiness: Storybook should not be required without project-local evidence'
        }

        'export default {}' | Set-Content -LiteralPath (Join-Path $TempRoot 'playwright.config.ts') -Encoding UTF8
        $Output = & python (Join-Path $RepoRoot 'scripts/frontend-visual-readiness.py') --project-root $TempRoot --json
        if ($LASTEXITCODE -ne 0) {
            throw '[FAIL] frontend visual readiness: Playwright e2e-only path should pass'
        }
        $Result = ($Output -join "`n") | ConvertFrom-Json
        if ($Result.lanes.screenshot_visual_baseline.required) {
            throw '[FAIL] frontend visual readiness: Playwright e2e-only should not require screenshot visual baseline lane'
        }

        New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot 'tests') | Out-Null
        "import { expect } from '@playwright/test';`nawait expect(page).toHaveScreenshot();`n" |
            Set-Content -LiteralPath (Join-Path $TempRoot 'tests/visual.spec.ts') -Encoding UTF8
        $Output = & python (Join-Path $RepoRoot 'scripts/frontend-visual-readiness.py') --project-root $TempRoot --json
        if ($LASTEXITCODE -ne 1) {
            throw '[FAIL] frontend visual readiness: Playwright screenshots without visual baseline should fail'
        }
        $Result = ($Output -join "`n") | ConvertFrom-Json
        if (-not $Result.lanes.screenshot_visual_baseline.required) {
            throw '[FAIL] frontend visual readiness: Playwright screenshots should require screenshot visual baseline lane'
        }
        Write-Output '[PASS] frontend visual readiness runner'
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

$Smokes = @(
    [pscustomobject]@{ Name = 'HarnessPhaseHelper';      Fn = 'Assert-HarnessPhaseHelper' }
    [pscustomobject]@{ Name = 'HarnessDoctor';           Fn = 'Assert-HarnessDoctor' }
    [pscustomobject]@{ Name = 'HarnessConvert';          Fn = 'Assert-HarnessConvert' }
    [pscustomobject]@{ Name = 'HarnessGate';             Fn = 'Assert-HarnessGate' }
    [pscustomobject]@{ Name = 'HarnessRun';              Fn = 'Assert-HarnessRun' }
    [pscustomobject]@{ Name = 'LightpathGate';           Fn = 'Assert-LightpathGate' }
    [pscustomobject]@{ Name = 'HarnessCertify';          Fn = 'Assert-HarnessCertify' }
    [pscustomobject]@{ Name = 'HarnessResumeProof';      Fn = 'Assert-HarnessResumeProof' }
    [pscustomobject]@{ Name = 'HarnessSmoke';            Fn = 'Assert-HarnessSmoke' }
    [pscustomobject]@{ Name = 'ModelRouter';             Fn = 'Assert-ModelRouter' }
    [pscustomobject]@{ Name = 'HashlineAnchor';          Fn = 'Assert-HashlineAnchor' }
    [pscustomobject]@{ Name = 'ContextInjector';         Fn = 'Assert-ContextInjector' }
    [pscustomobject]@{ Name = 'VerifyStepStatic';        Fn = 'Assert-VerifyStepStatic' }
    [pscustomobject]@{ Name = 'FrontendVisualReadiness'; Fn = 'Assert-FrontendVisualReadiness' }
)

$Selected = $Smokes
if (-not [string]::IsNullOrWhiteSpace($Only)) {
    $Pattern = $Only
    if ($Pattern -notmatch '[\*\?\[\]]') {
        $Pattern = "*$Pattern*"
    }
    $Selected = @($Smokes | Where-Object { $_.Name -like $Pattern })
    if ($Selected.Count -eq 0) {
        Write-Output "No smokes match -Only '$Only'. Use -List to see available names."
        exit 2
    }
}

if ($List) {
    foreach ($S in $Selected) {
        Write-Output $S.Name
    }
    exit 0
}

$Failures = @()
foreach ($S in $Selected) {
    try {
        & $S.Fn | Out-Null
        Write-Output ("[PASS] {0}" -f $S.Name)
    }
    catch {
        $Failures += [pscustomobject]@{ Name = $S.Name; Message = $_.Exception.Message }
        Write-Output ("[FAIL] {0}: {1}" -f $S.Name, $_.Exception.Message)
    }
}

$Passed = $Selected.Count - $Failures.Count
Write-Output ''
Write-Output ("Ran {0} smoke(s): {1} passed, {2} failed." -f $Selected.Count, $Passed, $Failures.Count)
foreach ($F in $Failures) {
    Write-Output ("  FAIL {0}: {1}" -f $F.Name, $F.Message)
}

exit $Failures.Count
