param(
    [string] $HarnessRoot = ''
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$TempRoot = Join-Path $env:TEMP ("ezpowers-harness-smoke-" + [guid]::NewGuid().ToString("N"))
$PlanDir = Join-Path $TempRoot 'docs/plans'

New-Item -ItemType Directory -Force -Path $PlanDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $TempRoot '.harness') | Out-Null

try {
    if ([string]::IsNullOrWhiteSpace($HarnessRoot)) {
        $HarnessRoot = Join-Path $TempRoot 'fake-harness'
        New-Item -ItemType Directory -Force -Path (Join-Path $HarnessRoot 'scripts') | Out-Null
        '' | Set-Content -LiteralPath (Join-Path $HarnessRoot 'scripts/execute.py') -Encoding UTF8
    }

    $HarnessScripts = Join-Path $HarnessRoot 'scripts'
    $ExecutePath = Join-Path $HarnessScripts 'execute.py'
    if (-not (Test-Path -LiteralPath $ExecutePath)) {
        throw "Smoke failed: missing harness execute.py at $ExecutePath"
    }

    @"
{
  "project": "smoke",
  "harness": { "root": "$($HarnessRoot.Replace('\', '\\'))" },
  "smoke": { "required": true, "artifact_kind": "cli", "command": "Write-Output ok" },
  "executor": { "reviewer_backend": "claude-code" }
}
"@ | Set-Content -LiteralPath (Join-Path $TempRoot '.harness/config.json') -Encoding UTF8

    @'
# Plan: Smoke Feature

## Goal
Prove the lightweight harness helpers work together.

## Architecture
One deep module behind a CLI-like interface.

## Tech Stack
PowerShell.

## Full-Feature Wiring Gate
Verify: `Write-Output gate-ok`

### Task 1: Implement smoke command [R1]

**Files:**
- Modify: `src/smoke.ps1`
- Test: `tests/smoke.Tests.ps1`

**Completion criteria (from spec):**
- [ ] Given: smoke input / When: command runs / Then: output appears / Verify: `Write-Output ok`

**Verification method:** Run spec Verify commands.
'@ | Set-Content -LiteralPath (Join-Path $PlanDir '2026-05-13-smoke-feature.md') -Encoding UTF8

    & (Join-Path $RepoRoot 'scripts/harness-convert.ps1') -ProjectRoot $TempRoot -PlanPath 'docs/plans/2026-05-13-smoke-feature.md' | Out-Null
    & (Join-Path $RepoRoot 'scripts/harness-doctor.ps1') -ProjectRoot $TempRoot -Phase 'smoke-feature' | Out-Null
    & (Join-Path $RepoRoot 'scripts/harness-phase.ps1') -ProjectRoot $TempRoot -Phase 'smoke-feature' | Out-Null
    & (Join-Path $RepoRoot 'scripts/harness-phase.ps1') -ProjectRoot $TempRoot -Phase 'smoke-feature' -ResetStep 0 | Out-Null
    & (Join-Path $RepoRoot 'scripts/harness-gate.ps1') -ProjectRoot $TempRoot -Phase 'smoke-feature' | Out-Null

    $PhaseDir = Join-Path $TempRoot 'phases/smoke-feature'
    $Index = Get-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $Gate = Get-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Raw -Encoding UTF8 | ConvertFrom-Json

    if (@($Index.steps).Count -ne 1) {
        throw 'Smoke failed: expected one converted step'
    }
    if ($Gate.status -ne 'pass') {
        throw "Smoke failed: expected wiring gate pass, got $($Gate.status)"
    }

    Write-Output 'Harness smoke passed.'
}
finally {
    if (Test-Path -LiteralPath $TempRoot) {
        Remove-Item -LiteralPath $TempRoot -Recurse -Force
    }
}
