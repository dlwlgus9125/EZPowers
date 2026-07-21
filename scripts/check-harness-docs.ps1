$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Assert-Contains {
    param(
        [string] $Path,
        [string] $Needle,
        [string] $Label
    )

    $FullPath = Join-Path $RepoRoot $Path
    if (-not (Test-Path -LiteralPath $FullPath)) {
        throw "[FAIL] ${Label}: missing file $Path"
    }

    $Text = Get-Content -LiteralPath $FullPath -Raw -Encoding UTF8
    if (-not $Text.Contains($Needle)) {
        throw "[FAIL] ${Label}: missing text '$Needle' in $Path"
    }

    Write-Output "[PASS] $Label"
}

function Assert-NotContains {
    param(
        [string] $Path,
        [string] $Needle,
        [string] $Label
    )

    $FullPath = Join-Path $RepoRoot $Path
    if (-not (Test-Path -LiteralPath $FullPath)) {
        throw "[FAIL] ${Label}: missing file $Path"
    }

    $Text = Get-Content -LiteralPath $FullPath -Raw -Encoding UTF8
    if ($Text.Contains($Needle)) {
        throw "[FAIL] ${Label}: forbidden text '$Needle' remains in $Path"
    }

    Write-Output "[PASS] $Label"
}

function Assert-DeepInterviewUtf8 {
    $Path = Join-Path $RepoRoot 'skills/deep-interview/SKILL.md'
    if (-not (Test-Path -LiteralPath $Path)) {
        throw '[FAIL] deep-interview UTF-8: missing skills/deep-interview/SKILL.md'
    }

    $Text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    function ConvertFrom-CodePoints {
        param([int[]] $CodePoints)
        return -join ($CodePoints | ForEach-Object { [char]$_ })
    }

    $RequiredPhrases = @(
        (ConvertFrom-CodePoints @(0xBAA8, 0xD638, 0xD55C, 0x20, 0xC694, 0xCCAD)),
        (ConvertFrom-CodePoints @(0xD55C, 0x20, 0xBC88, 0xC5D0, 0x20, 0xD558, 0xB098)),
        (ConvertFrom-CodePoints @(0xC644, 0xB8CC, 0x20, 0xAE30, 0xC900))
    )
    foreach ($Needle in $RequiredPhrases) {
        if (-not $Text.Contains($Needle)) {
            throw "[FAIL] deep-interview UTF-8: missing Korean phrase $Needle"
        }
    }
    foreach ($Needle in @([char]0xfffd, [char]0x5360, [char]0x7652, [char]0xf9cf)) {
        if ($Text.Contains([string]$Needle)) {
            throw "[FAIL] deep-interview UTF-8: mojibake marker remains: $Needle"
        }
    }

    Write-Output '[PASS] deep-interview UTF-8/mojibake guard'
}

function Assert-ControllerPrompt {
    param(
        [string] $Path,
        [string] $Label
    )

    $FullPath = Join-Path $RepoRoot $Path
    if (-not (Test-Path -LiteralPath $FullPath)) {
        throw "[FAIL] ${Label}: missing file $Path"
    }

    $Text = Get-Content -LiteralPath $FullPath -Raw -Encoding UTF8
    foreach ($Heading in @('## Purpose', '## Read', '## Rules', '## Stop conditions', '## Outputs')) {
        if (-not $Text.Contains($Heading)) {
            throw "[FAIL] ${Label}: missing controller heading $Heading"
        }
    }

    $LineCount = @($Text -split "\r?\n").Count
    if ($LineCount -gt 85) {
        throw "[FAIL] ${Label}: controller prompt is too long ($LineCount lines)"
    }

    foreach ($Needle in @('```', '## Phase ', '### ', 'config.json Schema', 'Task Structure', 'wiring-gate.json Generation', 'Per-Requirement Structure')) {
        if ($Text.Contains($Needle)) {
            throw "[FAIL] ${Label}: long template/schema marker remains in controller prompt: $Needle"
        }
    }

    if (-not $Text.Contains('docs/reference/mattpocock-harness-adapter.md')) {
        throw "[FAIL] ${Label}: controller does not read Matt Pocock adapter"
    }

    Write-Output "[PASS] $Label"
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
  "reviewer_verdict": "PASS",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
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
  "reviewer_verdict": "PASS",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
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
  "reviewer_verdict": "CODE_GAP",
  "status": "pending",
  "attempts": []
}
'@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8
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

Assert-Contains 'commands/choice_execute.md' 'Harness is the external executor/recovery path, not the only strict verification path.' 'choice_execute keeps all paths strict'
Assert-Contains 'commands/choice_execute.md' 'scripts/lightpath-gate.ps1 -Scope task' 'choice_execute uses lightpath task gate'
Assert-Contains 'commands/choice_execute.md' 'scripts/lightpath-gate.ps1 -Scope final' 'choice_execute uses lightpath final gate'
Assert-Contains 'commands/choice_execute.md' 'scripts/harness-certify.ps1' 'choice_execute uses completion certificate gate'
Assert-Contains 'commands/choice_execute.md' 'scripts/harness-resume-proof.ps1' 'choice_execute uses resume proof gate'
Assert-Contains 'commands/choice_execute.md' 'Checkboxes are progress hints, not PASS evidence.' 'choice_execute treats checkboxes as hints'
Assert-NotContains 'commands/choice_execute.md' 'Treat `- [x]` tasks as PASS' 'choice_execute removed checkbox PASS resume rule'
Assert-NotContains 'commands/choice_execute.md' 'Tasks checked `- [x]` are treated as PASS' 'choice_execute removed checked-task skip rule'
Assert-Contains 'docs/reference/setup-contract.md' '"lifecycle_stage": "undecided"' 'setup lifecycle default is undecided'
Assert-NotContains 'docs/reference/setup-contract.md' '"lifecycle_stage": "mvp"' 'setup lifecycle does not silently default to MVP'
Assert-Contains 'docs/reference/verification-contract.md' 'scripts/harness-resume-proof.ps1' 'verification contract defines resume proof'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Resume Proof' 'harness execution contract defines resume proof'
Assert-Contains 'evals/optimization/choiceexecutor/resume-mid-task.yaml' 'resume_proof_required' 'resume eval tracks proof requirement'
Assert-NotContains 'evals/optimization/choiceexecutor/resume-mid-task.yaml' 'Task 1 skipped as already complete (- [x] markers)' 'resume eval no longer rewards checkbox skip'
Assert-NotContains 'evals/optimization/choiceexecutor/resume-mid-task.yaml' 'tasks_skipped' 'resume eval no longer tracks skipped checkbox metric'
Assert-Contains 'agents/wiring-reviewer.md' 'missing generated gate evidence' 'wiring reviewer fails missing lightpath evidence'
Assert-ControllerPrompt 'commands/setup.md' 'setup prompt is diet controller'
Assert-ControllerPrompt 'commands/design_architecture.md' 'design_architecture prompt is diet controller'
Assert-ControllerPrompt 'commands/spec.md' 'spec prompt is diet controller'
Assert-ControllerPrompt 'commands/prepare_execute.md' 'prepare_execute prompt is diet controller'
Assert-ControllerPrompt 'commands/maintain.md' 'maintain prompt is diet controller'
Assert-ControllerPrompt 'commands/deploy.md' 'deploy prompt is diet controller'
Assert-ControllerPrompt 'commands/reset_setup.md' 'reset_setup prompt is diet controller'
Assert-ControllerPrompt 'docs/reference/strict-execution-adapter.md' 'strict execution adapter is diet controller'
Assert-Contains 'commands/setup.md' 'docs/reference/setup-contract.md' 'setup reads setup contract'
Assert-Contains 'commands/setup.md' 'docs/reference/harness-kit-contract.md' 'setup reads harness kit contract'
Assert-Contains 'commands/design_architecture.md' 'docs/reference/design-architecture-contract.md' 'design_architecture reads architecture contract'
Assert-Contains 'commands/design_architecture.md' 'docs/reference/ui-verification-adapter-contract.md' 'design_architecture reads UI adapter contract'
Assert-Contains 'commands/spec.md' 'docs/reference/spec-contract.md' 'spec reads spec contract'
Assert-Contains 'commands/prepare_execute.md' 'docs/reference/plan-contract.md' 'prepare_execute reads plan contract'
Assert-Contains 'commands/prepare_execute.md' 'docs/reference/ui-verification-adapter-contract.md' 'prepare_execute reads UI adapter contract'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'docs/reference/harness-execution-contract.md' 'strict adapter reads harness execution contract'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Avoid conversion work when a usable phase already exists' 'harness contract skips needless conversion'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'scripts/harness-convert.ps1 -ProjectRoot <project-root> -PlanPath <plan-path>' 'harness contract uses conversion helper'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>' 'strict adapter runs doctor first'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>' 'strict adapter uses gate helper'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'scripts/harness-phase.ps1' 'strict adapter uses phase helper for status'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase>' 'strict adapter uses run helper'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'scripts/harness-certify.ps1 -ProjectRoot <project-root> -Phase <phase>' 'strict adapter uses certify helper'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Do not reset a step without a concrete pass/fail signal' 'harness contract recovery requires signal'
Assert-Contains 'docs/reference/strict-execution-adapter.md' 'mattpocock-harness-adapter.md' 'strict adapter reads Matt adapter'
Assert-Contains 'commands/choice_execute.md' 'docs/reference/inline-execution-adapter.md' 'choice_execute delegates Path 3 to inline adapter'
Assert-Contains 'docs/reference/inline-execution-adapter.md' 'scripts/lightpath-gate.ps1 -Scope prepare' 'inline adapter prepares lightpath artifacts'
Assert-Contains 'docs/reference/inline-execution-adapter.md' 'scripts/lightpath-gate.ps1 -Scope task' 'inline adapter runs lightpath task gate'
Assert-Contains 'docs/reference/inline-execution-adapter.md' 'do not weaken or replace the Verify command' 'inline adapter forbids oracle weakening'
Assert-Contains 'docs/reference/inline-execution-adapter.md' 'fix-in-place' 'inline adapter uses fix-in-place loops'
Assert-Contains 'commands/prepare_execute.md' 'vertical red-green slice' 'prepare_execute enforces vertical TDD slices'
Assert-Contains 'commands/prepare_execute.md' 'mattpocock-harness-adapter.md' 'prepare_execute reads Matt adapter'
Assert-Contains 'commands/setup.md' 'mattpocock-harness-adapter.md' 'setup reads Matt adapter'
Assert-Contains 'commands/spec.md' 'mattpocock-harness-adapter.md' 'spec reads Matt adapter'
Assert-Contains 'docs/reference/setup-contract.md' 'Config Schema' 'setup contract owns config schema'
Assert-Contains 'docs/reference/model-routing-contract.md' 'Model Routing Contract' 'model routing contract exists'
Assert-Contains 'docs/reference/dispatch-protocol.md' 'scripts/model-router.py' 'dispatch protocol uses model router'
Assert-Contains 'docs/reference/dispatch-protocol.md' 'workflow-contract-reviewer' 'dispatch protocol registers workflow contract reviewer'
Assert-Contains 'docs/reference/reviewer-placement-contract.md' 'REVIEWER-MATRIX-COMMANDS-BEGIN' 'reviewer placement command matrix exists'
Assert-Contains 'agents/workflow-contract-reviewer.md' 'Review Packet' 'workflow contract reviewer uses review packet'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'EZPOWERS_MODEL' 'harness contract passes model environment'
Assert-Contains 'docs/reference/harness-execution-contract.md' '-ExplicitModel <model>' 'harness contract documents explicit model override'
Assert-Contains 'scripts/harness-run.ps1' 'ExplicitModel' 'harness run exposes explicit model override'
Assert-Contains 'scripts/harness-run.ps1' '-ExplicitModel $ExplicitModel' 'harness run passes explicit model to router'
Assert-Contains 'commands/choice_execute.md' 'model-routing-contract.md' 'choice_execute reads model routing contract'
Assert-Contains 'commands/choice_execute.md' 'context-injector.py verify' 'choice_execute verifies context injection sentinels'
Assert-Contains 'docs/reference/spec-contract.md' 'Requirement Section Template' 'spec contract owns requirement template'
Assert-Contains 'docs/reference/plan-contract.md' 'Task Shape' 'plan contract owns task template'
Assert-Contains 'docs/reference/harness-kit-contract.md' 'No Synthesis Rule' 'harness kit contract forbids setup synthesis'
Assert-Contains 'docs/reference/ui-verification-adapter-contract.md' 'Capability Matrix' 'UI verification contract defines capability matrix'
Assert-Contains 'commands/prepare_execute.md' 'select the strongest available adapter' 'prepare_execute selects strongest UI adapter'
Assert-Contains 'commands/prepare_execute.md' 'user-observable oracle' 'prepare_execute preserves UI oracle'
Assert-Contains 'commands/prepare_execute.md' 'insert a prerequisite' 'prepare_execute inserts adapter prerequisite'
Assert-Contains 'docs/reference/ui-verification-adapter-contract.md' 'Playwright is the preferred browser e2e' 'UI contract keeps Playwright preferred not mandatory'
Assert-Contains 'docs/reference/ui-verification-adapter-contract.md' 'Equivalent means the replacement verifies the same observable claim' 'UI contract defines adapter equivalence'
Assert-Contains 'docs/reference/ui-verification-adapter-contract.md' 'adapter_fallback_task_required' 'UI contract requires fallback task'
Assert-Contains 'docs/reference/plan-contract.md' 'Task 0: Install UI Verification Adapter' 'plan contract defines UI adapter prerequisite task'
Assert-Contains 'docs/reference/plan-contract.md' 'Do not replace a UI acceptance criterion' 'plan contract forbids UI oracle downgrade'
Assert-Contains 'docs/reference/pipeline-audit-contract.md' 'UI verification adapter availability' 'pipeline audit checks UI adapter availability'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Wiring Gate File' 'harness contract owns wiring schema'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Completion Certificate' 'harness contract owns completion certificate'
Assert-Contains 'docs/reference/architecture-readiness-contract.md' 'Deletion test' 'architecture contract has deletion test'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'EZPowers automation wins' 'Matt adapter preserves EZPowers automation'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'commands/setup.md' 'Matt adapter covers setup command'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'commands/spec.md' 'Matt adapter covers spec command'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'commands/prepare_execute.md' 'Matt adapter covers prepare_execute command'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/tdd' 'Matt adapter maps TDD skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/diagnose' 'Matt adapter maps diagnose skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'harness-run.ps1' 'Matt adapter maps run helper'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/improve-codebase-architecture' 'Matt adapter maps architecture skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/to-issues' 'Matt adapter maps issue slicing skill'
Assert-Contains 'docs/INDEX.md' 'Matt Pocock Harness Adapter' 'docs index links Matt adapter'
Assert-Contains 'docs/INDEX.md' 'Setup Contract' 'docs index links setup contract'
Assert-Contains 'docs/INDEX.md' 'Spec Contract' 'docs index links spec contract'
Assert-Contains 'docs/INDEX.md' 'Plan Contract' 'docs index links plan contract'
Assert-Contains 'docs/INDEX.md' 'Harness Kit Contract' 'docs index links harness kit contract'
Assert-Contains 'docs/INDEX.md' 'UI Verification Adapter Contract' 'docs index links UI adapter contract'
Assert-Contains 'docs/INDEX.md' 'Design Architecture Contract' 'docs index links design architecture contract'
Assert-Contains 'docs/INDEX.md' 'Harness Execution Contract' 'docs index links harness execution contract'
Assert-Contains 'docs/INDEX.md' 'Model Routing Contract' 'docs index links model routing contract'
Assert-Contains 'docs/INDEX.md' 'Reviewer Placement Contract' 'docs index links reviewer placement contract'
Assert-Contains 'docs/reference/verification-contract.md' 'The rules in this English subsection are canonical' 'view wiring canonical section present'
Assert-Contains 'docs/reference/verification-contract.md' 'W5 | Template resolution' 'view wiring W1-W5 taxonomy present'
Assert-Contains 'docs/reference/domain-language.md' 'Light Path' 'domain language defines light path'
Assert-Contains 'docs/reference/domain-language.md' 'Strict Path' 'domain language defines strict path'
Assert-Contains 'docs/reference/verification-contract.md' 'scripts/lightpath-gate.ps1' 'verification contract defines lightpath gate'
Assert-Contains '.githooks/pre-commit' 'check-harness-docs.ps1' 'pre-commit runs harness docs gate'
Assert-Contains '.githooks/pre-commit' '.agents/plugins/marketplace' 'pre-commit watches agents marketplace'
Assert-Contains '.githooks/pre-commit' '.claude-plugin/(plugin|marketplace)' 'pre-commit watches Claude plugin metadata'
Assert-Contains '.githooks/pre-commit' 'architecture-reviewer' 'pre-commit watches architecture reviewer'
Assert-Contains '.githooks/pre-commit' 'wiring-reviewer' 'pre-commit watches wiring reviewer'
Assert-Contains '.githooks/pre-commit' 'workflow-contract-reviewer' 'pre-commit watches workflow contract reviewer'
Assert-Contains '.githooks/pre-commit' 'frontend-experience-reviewer' 'pre-commit watches frontend experience reviewer'
Assert-Contains '.githooks/pre-commit' 'commands/(setup|design_architecture|spec|prepare_execute|choice_execute|maintain|deploy|reset_setup|review|sync-docs|set-rules|eval|feedback)' 'pre-commit watches prompt diet commands'
Assert-Contains '.githooks/pre-commit' 'CLAUDE\.md' 'pre-commit watches root guide'
Assert-Contains '.githooks/pre-commit' 'docs/INDEX\.md' 'pre-commit watches docs index'
Assert-Contains '.githooks/pre-commit' 'domain-language' 'pre-commit watches domain language'
Assert-Contains '.githooks/pre-commit' 'app-delivery-contract' 'pre-commit watches app delivery contract'
Assert-Contains '.githooks/pre-commit' 'mattpocock-harness-adapter' 'pre-commit watches Matt adapter'
Assert-Contains '.githooks/pre-commit' 'setup-contract' 'pre-commit watches setup contract'
Assert-Contains '.githooks/pre-commit' 'spec-contract' 'pre-commit watches spec contract'
Assert-Contains '.githooks/pre-commit' 'plan-contract' 'pre-commit watches plan contract'
Assert-Contains '.githooks/pre-commit' 'harness-kit-contract' 'pre-commit watches harness kit contract'
Assert-Contains '.githooks/pre-commit' 'ui-verification-adapter-contract' 'pre-commit watches UI adapter contract'
Assert-Contains '.githooks/pre-commit' 'frontend-design-contract' 'pre-commit watches frontend design contract'
Assert-Contains '.githooks/pre-commit' 'design-architecture-contract' 'pre-commit watches design architecture contract'
Assert-Contains '.githooks/pre-commit' 'harness-execution-contract' 'pre-commit watches harness execution contract'
Assert-Contains '.githooks/pre-commit' 'harness_versions/changelog' 'pre-commit watches harness changelog'
Assert-Contains '.githooks/pre-commit' 'harness-convert' 'pre-commit watches harness convert helper'
Assert-Contains '.githooks/pre-commit' 'harness-common' 'pre-commit watches harness common helper'
Assert-Contains '.githooks/pre-commit' 'harness-certify' 'pre-commit watches harness certify helper'
Assert-Contains '.githooks/pre-commit' 'harness-resume-proof' 'pre-commit watches harness resume proof helper'
Assert-Contains '.githooks/pre-commit' 'harness-doctor' 'pre-commit watches harness doctor'
Assert-Contains '.githooks/pre-commit' 'harness-gate' 'pre-commit watches harness gate helper'
Assert-Contains '.githooks/pre-commit' 'harness-phase' 'pre-commit watches harness phase helper'
Assert-Contains '.githooks/pre-commit' 'harness-run' 'pre-commit watches harness run helper'
Assert-Contains '.githooks/pre-commit' 'harness-smoke' 'pre-commit watches harness smoke helper'
Assert-Contains '.githooks/pre-commit' 'lightpath-gate' 'pre-commit watches lightpath gate helper'
Assert-Contains '.githooks/pre-commit' 'non-harness agent, skill, or skill-gate files' 'pre-commit keeps python gate scoped'
Assert-Contains 'CLAUDE.md' 'runs harness docs gate or validate.py by changed path' 'root guide documents split gate'
Assert-Contains 'CLAUDE.md' 'mattpocock-harness-adapter.md' 'root guide documents Matt adapter'
Assert-Contains 'harness_versions/changelog.jsonl' 'harness_light_path_refactor' 'harness changelog records refactor'
Assert-Contains 'harness_versions/changelog.jsonl' 'command_chain_v2_release' 'harness changelog records v2 command chain'
Assert-Contains '.githooks/pre-commit' 'smoke-plugin' 'pre-commit watches smoke-plugin helper'
Assert-Contains '.githooks/pre-commit' 'verify-step' 'pre-commit watches verify-step script'
Assert-Contains '.githooks/pre-commit' 'frontend-visual-readiness' 'pre-commit watches frontend visual readiness script'
Assert-Contains '.githooks/pre-commit' 'model-routing-contract' 'pre-commit watches model routing contract'
Assert-Contains '.githooks/pre-commit' 'reviewer-placement-contract' 'pre-commit watches reviewer placement contract'
Assert-Contains '.githooks/pre-commit' 'model-router' 'pre-commit watches model router'
Assert-Contains '.githooks/pre-commit' 'hashline-anchor' 'pre-commit watches hashline anchor'
Assert-Contains '.githooks/pre-commit' 'context-injector' 'pre-commit watches context injector'
Assert-Contains '.githooks/pre-commit' 'hook-policy' 'pre-commit watches hook policy'
Assert-Contains '.agents/plugins/marketplace.json' '"path": "./plugins/ezpowers"' 'agents marketplace uses packaged plugin mirror'
Assert-Contains 'commands/reset_setup.md' 'does not update installed Codex or Claude plugin command caches' 'reset_setup documents plugin cache boundary'
Assert-Contains 'plugins/ezpowers/commands/reset_setup.md' 'does not update installed Codex or Claude plugin command caches' 'packaged reset_setup documents plugin cache boundary'
Assert-Contains 'harness-kit/v2.0.0/manifest.json' '"target": "scripts/lightpath-gate.ps1"' 'harness kit installs lightpath gate helper'
Assert-Contains 'harness-kit/v2.0.0/manifest.json' '"target": "scripts/harness-resume-proof.ps1"' 'harness kit installs resume proof helper'
Assert-Contains 'harness-kit/v2.0.0/manifest.json' '"target": "scripts/verify-step.py"' 'harness kit installs verify step helper'
Assert-Contains 'commands/choice_execute.md' 'replace a missing gate script with inline verification' 'choice_execute forbids inline gate substitution'
Assert-Contains 'docs/reference/verification-contract.md' 'inline verification is not an acceptable replacement' 'verification contract forbids inline gate substitution'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'plugins/ezpowers/.codex-plugin/plugin.json'))) {
    throw '[FAIL] packaged plugin mirror: missing plugins/ezpowers/.codex-plugin/plugin.json'
}
Write-Output '[PASS] packaged plugin mirror codex manifest exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'plugins/ezpowers/commands/choice_execute.md'))) {
    throw '[FAIL] packaged plugin mirror: missing plugins/ezpowers/commands/choice_execute.md'
}
Write-Output '[PASS] packaged plugin mirror choice_execute exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'plugins/ezpowers/scripts/harness-resume-proof.ps1'))) {
    throw '[FAIL] packaged plugin mirror: missing plugins/ezpowers/scripts/harness-resume-proof.ps1'
}
Write-Output '[PASS] packaged plugin mirror harness resume proof exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/verify-step.py'))) {
    throw '[FAIL] verify-step.py: missing scripts/verify-step.py'
}
Write-Output '[PASS] verify-step.py exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/frontend-visual-readiness.py'))) {
    throw '[FAIL] frontend-visual-readiness.py: missing scripts/frontend-visual-readiness.py'
}
Write-Output '[PASS] frontend-visual-readiness.py exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/smoke-plugin.ps1'))) {
    throw '[FAIL] smoke-plugin.ps1: missing scripts/smoke-plugin.ps1'
}
Write-Output '[PASS] smoke-plugin.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/harness-common.ps1'))) {
    throw '[FAIL] harness-common.ps1: missing scripts/harness-common.ps1'
}
Write-Output '[PASS] harness-common.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/harness-certify.ps1'))) {
    throw '[FAIL] harness-certify.ps1: missing scripts/harness-certify.ps1'
}
Write-Output '[PASS] harness-certify.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/harness-resume-proof.ps1'))) {
    throw '[FAIL] harness-resume-proof.ps1: missing scripts/harness-resume-proof.ps1'
}
Write-Output '[PASS] harness-resume-proof.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1'))) {
    throw '[FAIL] lightpath-gate.ps1: missing scripts/lightpath-gate.ps1'
}
Write-Output '[PASS] lightpath-gate.ps1 exists'

foreach ($ScriptName in @('model-router.py', 'hashline-anchor.py', 'context-injector.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot "scripts/$ScriptName"))) {
        throw "[FAIL] ${ScriptName}: missing scripts/$ScriptName"
    }
    Write-Output "[PASS] $ScriptName exists"
}

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/verify-harness-kit.py'))) {
    throw '[FAIL] verify-harness-kit.py: missing scripts/verify-harness-kit.py'
}
Write-Output '[PASS] verify-harness-kit.py exists'

& python (Join-Path $RepoRoot 'scripts/verify-harness-kit.py') --repo-root $RepoRoot | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw '[FAIL] verify-harness-kit.py: manifest validation failed'
}
Write-Output '[PASS] verify-harness-kit manifest'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'hooks/hook-policy.json'))) {
    throw '[FAIL] hook-policy.json: missing hooks/hook-policy.json'
}
Write-Output '[PASS] hook-policy.json exists'

Assert-HarnessPhaseHelper
Assert-HarnessDoctor
Assert-HarnessConvert
Assert-HarnessGate
Assert-HarnessRun
Assert-LightpathGate
Assert-HarnessCertify
Assert-HarnessResumeProof
Assert-HarnessSmoke
Assert-ModelRouter
Assert-HashlineAnchor
Assert-ContextInjector
Assert-VerifyStepStatic
Assert-FrontendVisualReadiness
Assert-DeepInterviewUtf8

Write-Output 'Harness doc checks passed.'
