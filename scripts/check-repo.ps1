<#
.SYNOPSIS
    Structural commit gate for the EZPowers plugin repository.

.DESCRIPTION
    A fast, mechanical gate — not a regression suite. It verifies:
      1. Skill frontmatter validity (name/description; workflow skills carry
         disable-model-invocation and an agents/openai.yaml).
      2. No dead repo-relative path references to docs/reference, scripts, or
         agents files inside skills, agents, docs/INDEX.md, or docs/reference.
      3. Version parity across .claude-plugin/plugin.json,
         .claude-plugin/marketplace.json, and .codex-plugin/plugin.json
         (the codex build-metadata suffix +codex.* is stripped before compare).
      4. Conditional: harness-kit changes revalidate the kit; -WithTests runs the
         Python unittest suite.

    The banned-vague-expression rule is enforced on generated /spec output by the
    spec contract, not on the harness's own documentation (which legitimately
    quotes and discusses those words). scripts/shared.py provides that scan.

.PARAMETER ChangedFiles
    Repo-relative paths of the files under consideration (pre-commit passes the
    staged set). When empty the gate scans the whole tree and revalidates the kit.

.PARAMETER WithTests
    Also run `python -m unittest discover -s tests` (slow; off by default so the
    pre-commit stays fast).

.OUTPUTS
    One line per failure; exit code is the number of failures (0 when clean).
#>
param(
    [string[]] $ChangedFiles = @(),
    [switch] $WithTests
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Failures = New-Object System.Collections.ArrayList

# The pre-commit hook passes the staged set as one comma-joined string (bash
# cannot hand PowerShell a native array); normalize to a real string[].
$ChangedFiles = @(
    $ChangedFiles |
        ForEach-Object { $_ -split ',' } |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -ne '' }
)

function Add-Failure {
    param([string] $Message)
    [void]$Failures.Add($Message)
    Write-Output "[FAIL] $Message"
}

$WorkflowSkills = @(
    'setup', 'design-architecture', 'spec', 'prepare-execute', 'choice-execute',
    'maintain', 'deploy', 'reset-setup', 'review', 'sync-docs', 'set-rules'
)

function Get-Frontmatter {
    param([string] $Text)
    if ($Text -notmatch '(?s)^﻿?---\r?\n(.*?)\r?\n---') {
        return $null
    }
    return $Matches[1]
}

# ---- Check 1: skill frontmatter ----
$SkillDirs = Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'skills') -Directory -ErrorAction SilentlyContinue
foreach ($Dir in $SkillDirs) {
    $SkillPath = Join-Path $Dir.FullName 'SKILL.md'
    if (-not (Test-Path -LiteralPath $SkillPath)) {
        Add-Failure "skills/$($Dir.Name): missing SKILL.md"
        continue
    }
    $Text = Get-Content -LiteralPath $SkillPath -Raw -Encoding UTF8
    $Front = Get-Frontmatter $Text
    if ($null -eq $Front) {
        Add-Failure "skills/$($Dir.Name)/SKILL.md: missing or malformed YAML frontmatter"
        continue
    }
    if ($Front -notmatch '(?m)^name:\s*\S') {
        Add-Failure "skills/$($Dir.Name)/SKILL.md: frontmatter missing name"
    }
    if ($Front -notmatch '(?m)^description:\s*\S') {
        Add-Failure "skills/$($Dir.Name)/SKILL.md: frontmatter missing description"
    }
    if ($WorkflowSkills -contains $Dir.Name) {
        if ($Front -notmatch '(?m)^disable-model-invocation:\s*true') {
            Add-Failure "skills/$($Dir.Name)/SKILL.md: workflow skill must set disable-model-invocation: true"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $Dir.FullName 'agents/openai.yaml'))) {
            Add-Failure "skills/$($Dir.Name): workflow skill must ship agents/openai.yaml"
        }
    }
}

# ---- Check 2: dead-path scan ----
$ScanTargets = New-Object System.Collections.ArrayList
foreach ($rel in @('docs/INDEX.md')) {
    $p = Join-Path $RepoRoot $rel
    if (Test-Path -LiteralPath $p) { [void]$ScanTargets.Add($p) }
}
foreach ($sub in @('skills', 'agents', 'docs/reference')) {
    $base = Join-Path $RepoRoot $sub
    if (Test-Path -LiteralPath $base) {
        Get-ChildItem -LiteralPath $base -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue |
            ForEach-Object { [void]$ScanTargets.Add($_.FullName) }
    }
}
# Repo-owned reference paths. Excludes:
#  - placeholders containing * < > (charset), and paths that are a suffix of a
#    longer path such as {harness.root}/scripts/execute.py (negative lookbehind),
#  - skills/README.md and other single-segment skills paths (require skills/<name>/<file>),
#  - anything inside a fenced code block (illustrative examples, stripped first).
$PathPattern = '(?<![/\w.}\-])(?<p>docs/reference/[A-Za-z0-9._-]+\.md|agents/[A-Za-z0-9._-]+\.md|skills/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+\.md|scripts/[A-Za-z0-9._-]+\.(?:ps1|py))'
$DeadSeen = @{}
foreach ($File in $ScanTargets) {
    $Content = Get-Content -LiteralPath $File -Raw -Encoding UTF8
    # Drop fenced code blocks so example paths do not count as references.
    $Content = [regex]::Replace($Content, '(?s)```.*?```', '')
    foreach ($m in [regex]::Matches($Content, $PathPattern)) {
        $Ref = $m.Groups['p'].Value
        if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot $Ref))) {
            $Key = "$File|$Ref"
            if (-not $DeadSeen.ContainsKey($Key)) {
                $DeadSeen[$Key] = $true
                $RelFile = $File.Substring($RepoRoot.Length + 1) -replace '\\', '/'
                Add-Failure "dead path reference in ${RelFile}: $Ref"
            }
        }
    }
}

# ---- Check 2b: docs/INDEX.md links (resolved relative to docs/) ----
$IndexPath = Join-Path $RepoRoot 'docs/INDEX.md'
if (Test-Path -LiteralPath $IndexPath) {
    $IndexText = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8
    foreach ($m in [regex]::Matches($IndexText, '\]\((?<t>[^)]+\.md)\)')) {
        $Target = $m.Groups['t'].Value
        if ($Target -match '^[A-Za-z]+://' -or $Target -match '[*<>]') { continue }
        if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $RepoRoot 'docs') $Target))) {
            Add-Failure "dead link in docs/INDEX.md: $Target"
        }
    }
}

# ---- Check 3: version sync ----
function Get-JsonVersion {
    param([string] $Rel)
    $p = Join-Path $RepoRoot $Rel
    if (-not (Test-Path -LiteralPath $p)) {
        Add-Failure "version sync: missing $Rel"
        return $null
    }
    $obj = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($obj.PSObject.Properties.Name -contains 'version' -and $obj.version) {
        return [string]$obj.version
    }
    # marketplace.json nests the version under plugins[].version
    if ($obj.PSObject.Properties.Name -contains 'plugins' -and @($obj.plugins).Count -gt 0) {
        return [string]$obj.plugins[0].version
    }
    Add-Failure "version sync: no version field in $Rel"
    return $null
}
$PluginVer = Get-JsonVersion '.claude-plugin/plugin.json'
$MarketVer = Get-JsonVersion '.claude-plugin/marketplace.json'
$CodexVerRaw = Get-JsonVersion '.codex-plugin/plugin.json'
$CodexVer = if ($null -ne $CodexVerRaw) { $CodexVerRaw -replace '\+codex\..*$', '' } else { $null }
if ($null -ne $PluginVer -and $null -ne $MarketVer -and $PluginVer -ne $MarketVer) {
    Add-Failure "version mismatch: plugin.json=$PluginVer marketplace.json=$MarketVer"
}
if ($null -ne $PluginVer -and $null -ne $CodexVer -and $PluginVer -ne $CodexVer) {
    Add-Failure "version mismatch: plugin.json=$PluginVer codex-plugin.json(base)=$CodexVer"
}

# ---- Check 4: conditional kit + tests ----
$Python = if ($env:EZP_PYTHON) { $env:EZP_PYTHON } else { 'python' }
$KitTouched = ($ChangedFiles.Count -eq 0) -or (@($ChangedFiles | Where-Object { $_ -like 'harness-kit/*' }).Count -gt 0)
if ($KitTouched) {
    $KitOut = & $Python (Join-Path $RepoRoot 'scripts/verify-harness-kit.py') 2>&1
    if ($LASTEXITCODE -ne 0) {
        Add-Failure "harness kit verification failed: $($KitOut -join ' ')"
    }
}
if ($WithTests) {
    Push-Location $RepoRoot
    try {
        & $Python -m unittest discover -s tests | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Add-Failure 'python unittest suite failed (run: python -m unittest discover -s tests)'
        }
    }
    finally {
        Pop-Location
    }
}

if ($Failures.Count -gt 0) {
    Write-Output "check-repo: FAIL ($($Failures.Count) issue(s))"
    exit $Failures.Count
}
Write-Output 'check-repo: PASS'
exit 0
