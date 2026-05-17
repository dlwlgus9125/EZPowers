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
            -TimeoutSeconds 10 | Out-Null

        $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        $Pending = @($Index.steps | Where-Object { $_.status -eq 'pending' }).Count
        if ($Pending -ne 0) {
            throw "[FAIL] harness run: expected all steps completed"
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

function Assert-HarnessSmoke {
    $SmokeOutput = & (Join-Path $RepoRoot 'scripts/harness-smoke.ps1')
    if (($SmokeOutput -join "`n") -notlike '*Harness smoke passed.*') {
        throw '[FAIL] harness smoke: expected pass output'
    }

    Write-Output '[PASS] harness smoke end-to-end'
}

Assert-Contains 'commands/choiceexecutor.md' 'Harness is the external executor/recovery path, not the only strict verification path.' 'choiceexecutor keeps all paths strict'
Assert-Contains 'commands/choiceexecutor.md' 'scripts/lightpath-gate.ps1 -Scope task' 'choiceexecutor uses lightpath task gate'
Assert-Contains 'commands/choiceexecutor.md' 'scripts/lightpath-gate.ps1 -Scope final' 'choiceexecutor uses lightpath final gate'
Assert-Contains 'agents/wiring-reviewer.md' 'missing generated gate evidence' 'wiring reviewer fails missing lightpath evidence'
Assert-ControllerPrompt 'commands/setup.md' 'setup prompt is diet controller'
Assert-ControllerPrompt 'commands/brainstorm.md' 'brainstorm prompt is diet controller'
Assert-ControllerPrompt 'commands/plan.md' 'plan prompt is diet controller'
Assert-ControllerPrompt 'commands/executeharness.md' 'executeharness prompt is diet controller'
Assert-Contains 'commands/setup.md' 'docs/reference/setup-contract.md' 'setup reads setup contract'
Assert-Contains 'commands/brainstorm.md' 'docs/reference/spec-contract.md' 'brainstorm reads spec contract'
Assert-Contains 'commands/plan.md' 'docs/reference/plan-contract.md' 'plan reads plan contract'
Assert-Contains 'commands/executeharness.md' 'docs/reference/harness-execution-contract.md' 'executeharness reads harness execution contract'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Avoid conversion work when a usable phase already exists' 'harness contract skips needless conversion'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'scripts/harness-convert.ps1 -ProjectRoot <project-root> -PlanPath <plan-path>' 'harness contract uses conversion helper'
Assert-Contains 'commands/executeharness.md' 'scripts/harness-doctor.ps1 -ProjectRoot <project-root> -Phase <phase>' 'executeharness runs doctor first'
Assert-Contains 'commands/executeharness.md' 'scripts/harness-gate.ps1 -ProjectRoot <project-root> -Phase <phase>' 'executeharness uses gate helper'
Assert-Contains 'commands/executeharness.md' 'scripts/harness-phase.ps1' 'executeharness uses phase helper for status'
Assert-Contains 'commands/executeharness.md' 'scripts/harness-run.ps1 -ProjectRoot <project-root> -Phase <phase>' 'executeharness uses run helper'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Do not reset a step without a concrete pass/fail signal' 'harness contract recovery requires signal'
Assert-Contains 'commands/executeharness.md' 'mattpocock-harness-adapter.md' 'executeharness reads Matt adapter'
Assert-Contains 'commands/plan.md' 'vertical red-green slice' 'plan enforces vertical TDD slices'
Assert-Contains 'commands/plan.md' 'mattpocock-harness-adapter.md' 'plan reads Matt adapter'
Assert-Contains 'commands/setup.md' 'mattpocock-harness-adapter.md' 'setup reads Matt adapter'
Assert-Contains 'commands/brainstorm.md' 'mattpocock-harness-adapter.md' 'brainstorm reads Matt adapter'
Assert-Contains 'docs/reference/setup-contract.md' 'Config Schema' 'setup contract owns config schema'
Assert-Contains 'docs/reference/spec-contract.md' 'Requirement Section Template' 'spec contract owns requirement template'
Assert-Contains 'docs/reference/plan-contract.md' 'Task Shape' 'plan contract owns task template'
Assert-Contains 'docs/reference/harness-execution-contract.md' 'Wiring Gate File' 'harness contract owns wiring schema'
Assert-Contains 'docs/reference/architecture-readiness-contract.md' 'Deletion test' 'architecture contract has deletion test'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'EZPowers automation wins' 'Matt adapter preserves EZPowers automation'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'commands/setup.md' 'Matt adapter covers setup command'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'commands/brainstorm.md' 'Matt adapter covers brainstorm command'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/tdd' 'Matt adapter maps TDD skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/diagnose' 'Matt adapter maps diagnose skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'harness-run.ps1' 'Matt adapter maps run helper'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/improve-codebase-architecture' 'Matt adapter maps architecture skill'
Assert-Contains 'docs/reference/mattpocock-harness-adapter.md' 'engineering/to-issues' 'Matt adapter maps issue slicing skill'
Assert-Contains 'docs/INDEX.md' 'Matt Pocock Harness Adapter' 'docs index links Matt adapter'
Assert-Contains 'docs/INDEX.md' 'Setup Contract' 'docs index links setup contract'
Assert-Contains 'docs/INDEX.md' 'Spec Contract' 'docs index links spec contract'
Assert-Contains 'docs/INDEX.md' 'Plan Contract' 'docs index links plan contract'
Assert-Contains 'docs/INDEX.md' 'Harness Execution Contract' 'docs index links harness execution contract'
Assert-Contains 'docs/reference/verification-contract.md' 'The rules in this English subsection are canonical' 'view wiring canonical section present'
Assert-Contains 'docs/reference/verification-contract.md' 'W5 | Template resolution' 'view wiring W1-W5 taxonomy present'
Assert-Contains 'docs/reference/domain-language.md' 'Light Path' 'domain language defines light path'
Assert-Contains 'docs/reference/domain-language.md' 'Strict Path' 'domain language defines strict path'
Assert-Contains 'docs/reference/verification-contract.md' 'scripts/lightpath-gate.ps1' 'verification contract defines lightpath gate'
Assert-Contains '.githooks/pre-commit' 'check-harness-docs.ps1' 'pre-commit runs harness docs gate'
Assert-Contains '.githooks/pre-commit' '.claude-plugin/(plugin|marketplace)' 'pre-commit watches Claude plugin metadata'
Assert-Contains '.githooks/pre-commit' 'agents/wiring-reviewer' 'pre-commit watches wiring reviewer'
Assert-Contains '.githooks/pre-commit' 'commands/(setup|brainstorm|choiceexecutor|executeharness|plan)' 'pre-commit watches prompt diet commands'
Assert-Contains '.githooks/pre-commit' 'CLAUDE\.md' 'pre-commit watches root guide'
Assert-Contains '.githooks/pre-commit' 'docs/INDEX\.md' 'pre-commit watches docs index'
Assert-Contains '.githooks/pre-commit' 'domain-language' 'pre-commit watches domain language'
Assert-Contains '.githooks/pre-commit' 'mattpocock-harness-adapter' 'pre-commit watches Matt adapter'
Assert-Contains '.githooks/pre-commit' 'setup-contract' 'pre-commit watches setup contract'
Assert-Contains '.githooks/pre-commit' 'spec-contract' 'pre-commit watches spec contract'
Assert-Contains '.githooks/pre-commit' 'plan-contract' 'pre-commit watches plan contract'
Assert-Contains '.githooks/pre-commit' 'harness-execution-contract' 'pre-commit watches harness execution contract'
Assert-Contains '.githooks/pre-commit' 'harness_versions/changelog' 'pre-commit watches harness changelog'
Assert-Contains '.githooks/pre-commit' 'harness-convert' 'pre-commit watches harness convert helper'
Assert-Contains '.githooks/pre-commit' 'harness-common' 'pre-commit watches harness common helper'
Assert-Contains '.githooks/pre-commit' 'harness-doctor' 'pre-commit watches harness doctor'
Assert-Contains '.githooks/pre-commit' 'harness-gate' 'pre-commit watches harness gate helper'
Assert-Contains '.githooks/pre-commit' 'harness-phase' 'pre-commit watches harness phase helper'
Assert-Contains '.githooks/pre-commit' 'harness-run' 'pre-commit watches harness run helper'
Assert-Contains '.githooks/pre-commit' 'harness-smoke' 'pre-commit watches harness smoke helper'
Assert-Contains '.githooks/pre-commit' 'lightpath-gate' 'pre-commit watches lightpath gate helper'
Assert-Contains '.githooks/pre-commit' 'non-harness command, agent, skill, or skill-gate files' 'pre-commit keeps python gate scoped'
Assert-Contains 'CLAUDE.md' 'runs harness docs gate or validate.py by changed path' 'root guide documents split gate'
Assert-Contains 'CLAUDE.md' 'mattpocock-harness-adapter.md' 'root guide documents Matt adapter'
Assert-Contains 'harness_versions/changelog.jsonl' 'harness_light_path_refactor' 'harness changelog records refactor'
Assert-Contains '.githooks/pre-commit' 'smoke-plugin' 'pre-commit watches smoke-plugin helper'
Assert-Contains '.githooks/pre-commit' 'verify-step' 'pre-commit watches verify-step script'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/verify-step.py'))) {
    throw '[FAIL] verify-step.py: missing scripts/verify-step.py'
}
Write-Output '[PASS] verify-step.py exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/smoke-plugin.ps1'))) {
    throw '[FAIL] smoke-plugin.ps1: missing scripts/smoke-plugin.ps1'
}
Write-Output '[PASS] smoke-plugin.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/harness-common.ps1'))) {
    throw '[FAIL] harness-common.ps1: missing scripts/harness-common.ps1'
}
Write-Output '[PASS] harness-common.ps1 exists'

if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot 'scripts/lightpath-gate.ps1'))) {
    throw '[FAIL] lightpath-gate.ps1: missing scripts/lightpath-gate.ps1'
}
Write-Output '[PASS] lightpath-gate.ps1 exists'

Assert-HarnessPhaseHelper
Assert-HarnessDoctor
Assert-HarnessConvert
Assert-HarnessGate
Assert-HarnessRun
Assert-LightpathGate
Assert-HarnessSmoke

Write-Output 'Harness doc checks passed.'
