param(
    [Parameter(Mandatory = $true)]
    [string] $PlanPath,

    [string] $ProjectRoot = (Get-Location).Path,

    [string] $Phase = ''
)

$ErrorActionPreference = 'Stop'

function Get-Slug {
    param([string] $Name)
    $Slug = [IO.Path]::GetFileNameWithoutExtension($Name)
    $Slug = $Slug -replace '^\d{4}-\d{2}-\d{2}-', ''
    $Slug = $Slug.ToLowerInvariant() -replace '[^a-z0-9]+', '-'
    $Slug = $Slug.Trim('-')
    if ([string]::IsNullOrWhiteSpace($Slug)) { return 'phase' }
    return $Slug
}

function Get-Section {
    param([string] $Text, [string] $Name)
    $Pattern = "(?ms)^##\s+$([regex]::Escape($Name))\s*\r?\n(.*?)(?=^##\s+|\z)"
    $Match = [regex]::Match($Text, $Pattern)
    if ($Match.Success) { return $Match.Groups[1].Value.Trim() }
    return ''
}

function Get-WiringGateSection {
    param([string] $Text)
    $Pattern = "(?ms)^##\s+Full-Feature Wiring Gate\s*\r?\n(.*?)(?=^###\s+Task\s+\d+:|^##\s+|\z)"
    $Match = [regex]::Match($Text, $Pattern)
    if ($Match.Success) { return $Match.Groups[1].Value.Trim() }
    return ''
}

function Get-TaskField {
    param([string] $TaskText, [string] $Label)
    $Pattern = "(?ms)^\*\*$([regex]::Escape($Label))[^*]*:\*\*\s*\r?\n(.*?)(?=^\*\*|^### |\z)"
    $Match = [regex]::Match($TaskText, $Pattern)
    if ($Match.Success) { return $Match.Groups[1].Value.Trim() }
    return ''
}

function Get-InlineField {
    param([string] $Text, [string] $Label)
    $Pattern = "(?m)^\*\*$([regex]::Escape($Label)):\*\*\s*(.+)$"
    $Match = [regex]::Match($Text, $Pattern)
    if ($Match.Success) { return $Match.Groups[1].Value.Trim() }
    return ''
}

function Get-BacktickCommands {
    param([string] $Text)
    $Commands = @()
    foreach ($Match in [regex]::Matches($Text, '`([^`]+)`')) {
        $Command = $Match.Groups[1].Value.Trim()
        if ($Command -and $Command -notmatch '^(path|file|Task|T\d+)$') {
            $Commands += $Command
        }
    }
    return $Commands
}

function Get-VerifyCommands {
    param([string] $Text)
    $Commands = @()
    foreach ($Match in [regex]::Matches($Text, '(?m)^\*\*Verify:\*\*\s*`([^`]+)`')) {
        $Commands += $Match.Groups[1].Value.Trim()
    }
    if ($Commands.Count -eq 0) {
        foreach ($Match in [regex]::Matches($Text, '(?m)^Verify:\s*`([^`]+)`')) {
            $Commands += $Match.Groups[1].Value.Trim()
        }
    }
    if ($Commands.Count -eq 0) {
        $Commands = @(Get-BacktickCommands $Text)
    }
    return $Commands
}

function Get-CoveredTasks {
    param([string] $Covers)
    $Tasks = @()
    foreach ($Match in [regex]::Matches($Covers, '\bT\d+\b')) {
        $Task = $Match.Value
        if ($Tasks -notcontains $Task) {
            $Tasks += $Task
        }
    }
    return $Tasks
}

function Get-CoveredEdges {
    param([string] $Covers)
    $Edges = @()
    foreach ($ChainMatch in [regex]::Matches($Covers, 'T\d+(?:\s*->\s*T\d+)+')) {
        $Tasks = @([regex]::Matches($ChainMatch.Value, 'T\d+') | ForEach-Object { $_.Value })
        for ($i = 0; $i -lt $Tasks.Count - 1; $i++) {
            $Edge = "$($Tasks[$i])->$($Tasks[$i + 1])"
            if ($Edges -notcontains $Edge) {
                $Edges += $Edge
            }
        }
    }
    return $Edges
}

$PlanFullPath = if ([IO.Path]::IsPathRooted($PlanPath)) { $PlanPath } else { Join-Path $ProjectRoot $PlanPath }
if (-not (Test-Path -LiteralPath $PlanFullPath)) {
    throw "Plan not found: $PlanFullPath"
}

$PlanText = Get-Content -LiteralPath $PlanFullPath -Raw -Encoding UTF8
if ([string]::IsNullOrWhiteSpace($Phase)) {
    $Phase = Get-Slug $PlanFullPath
}

$PhaseDir = Join-Path $ProjectRoot "phases/$Phase"
New-Item -ItemType Directory -Force -Path $PhaseDir | Out-Null

$Goal = Get-Section $PlanText 'Goal'
if ([string]::IsNullOrWhiteSpace($Goal)) {
    $Title = [regex]::Match($PlanText, '(?m)^#\s+(.+)$')
    $Goal = if ($Title.Success) { $Title.Groups[1].Value.Trim() } else { $Phase }
}

$Architecture = Get-Section $PlanText 'Architecture'
$TechStack = Get-Section $PlanText 'Tech Stack'

@"
# $Phase

## Goal
$Goal

## Architecture
$Architecture

## Tech Stack
$TechStack

## Plan
$PlanFullPath
"@ | Set-Content -LiteralPath (Join-Path $PhaseDir 'phase-context.md') -Encoding UTF8

$TaskMatches = [regex]::Matches($PlanText, '(?m)^### Task\s+(\d+):\s*(.+)$')
if ($TaskMatches.Count -eq 0) {
    throw "No tasks found in plan: $PlanFullPath"
}

$Steps = @()
for ($i = 0; $i -lt $TaskMatches.Count; $i++) {
    $Match = $TaskMatches[$i]
    $TaskNumber = [int]$Match.Groups[1].Value
    $TaskName = $Match.Groups[2].Value.Trim()
    $Category = 'feature'
    if ($TaskName -match '\{([^}]+)\}') {
        $Category = $Matches[1].Trim()
    }
    $TaskStart = $Match.Index
    $TaskEnd = if ($i + 1 -lt $TaskMatches.Count) { $TaskMatches[$i + 1].Index } else { $PlanText.Length }
    $TaskText = $PlanText.Substring($TaskStart, $TaskEnd - $TaskStart).Trim()
    $StepNumber = $TaskNumber - 1
    $StepFile = "step$StepNumber.md"

    $Files = @()
    foreach ($Line in ($TaskText -split "`r?`n")) {
        if ($Line -match '^\s*-\s*(Create|Modify|Test|Read):\s*`?([^`]+)`?') {
            $Files += $Matches[2].Trim()
        }
    }

    $Completion = Get-TaskField $TaskText 'Completion criteria'
    $Verification = Get-TaskField $TaskText 'Verification method'
    $WiringHandoff = Get-TaskField $TaskText 'Wiring handoff'
    if ([string]::IsNullOrWhiteSpace($Verification)) {
        $Verification = ($TaskText -split "`r?`n" | Where-Object { $_ -match 'Verify:' }) -join "`n"
    }

    $FilesBlock = if ($Files.Count -gt 0) {
        ($Files | ForEach-Object { "- `$_" }) -join "`n"
    }
    else {
        "- $PlanFullPath"
    }

    @"
# Step $StepNumber (Task $TaskNumber): $TaskName

## Files to Read
$FilesBlock

## Task
$TaskText

## Acceptance Criteria
$Completion

## Verification
$Verification

## tools
- $PlanFullPath
"@ | Set-Content -LiteralPath (Join-Path $PhaseDir $StepFile) -Encoding UTF8

    $Steps += [pscustomobject]@{
        step = $StepNumber
        name = $TaskName
        status = 'pending'
        step_md = $StepFile
        category = $Category
        wiring_handoff = $WiringHandoff
    }
}

$ProjectName = Split-Path -Leaf $ProjectRoot
$ConfigPath = Join-Path $ProjectRoot '.harness/config.json'
if (Test-Path -LiteralPath $ConfigPath) {
    $Config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Config.PSObject.Properties.Name -contains 'project') {
        $ProjectName = [string]$Config.project
    }
}

[pscustomobject]@{
    project = $ProjectName
    phase = $Phase
    created_at = (Get-Date).ToUniversalTime().ToString('o')
    steps = $Steps
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PhaseDir 'index.json') -Encoding UTF8

$GateText = Get-WiringGateSection $PlanText
$Commands = @(Get-VerifyCommands $GateText)
$RequiredField = Get-InlineField $GateText 'Required'
$Required = -not [string]::IsNullOrWhiteSpace($GateText)
if (-not [string]::IsNullOrWhiteSpace($RequiredField)) {
    $Required = $RequiredField -match '^(yes|true|required)$'
}
$VerifyType = Get-InlineField $GateText 'Verify-type'
if ([string]::IsNullOrWhiteSpace($VerifyType)) {
    $VerifyType = if ($Required) { 'e2e' } else { 'none' }
}
$Covers = Get-InlineField $GateText 'Covers'
$ExpectedObservation = Get-InlineField $GateText 'Expected observation'
$GateStatus = if ($Required -and $Commands.Count -eq 0) { 'spec_gap' } elseif ($Required) { 'pending' } else { 'pass' }

[pscustomobject]@{
    phase = $Phase
    required = $Required
    verify_type = $VerifyType
    commands = $Commands
    covered_tasks = @(Get-CoveredTasks $Covers)
    covered_edges = @(Get-CoveredEdges $Covers)
    expected_observation = $ExpectedObservation
    status = $GateStatus
    attempts = @()
    reason = if ($Required) { '' } else { 'single-task library-only or no executable artifact' }
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PhaseDir 'wiring-gate.json') -Encoding UTF8

Write-Output "Converted plan to phase: $PhaseDir"
