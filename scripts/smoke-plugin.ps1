$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot

function Write-Check {
    param(
        [string] $Status,
        [string] $Name,
        [string] $Detail
    )
    Write-Output "[$Status] $Name - $Detail"
}

$Failures = 0
$Warnings = 0

# ---------------------------------------------------------------------------
# 1. Assert-PluginJson
# ---------------------------------------------------------------------------
$PluginPath = Join-Path $RepoRoot '.claude-plugin/plugin.json'
if (-not (Test-Path -LiteralPath $PluginPath)) {
    Write-Check 'FAIL' 'plugin.json' 'missing .claude-plugin/plugin.json'
    $Failures++
}
else {
    try {
        $Plugin = Get-Content -LiteralPath $PluginPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $Missing = @()
        foreach ($Field in @('name', 'version')) {
            if (-not ($Plugin.PSObject.Properties.Name -contains $Field) -or [string]::IsNullOrWhiteSpace([string]$Plugin.$Field)) {
                $Missing += $Field
            }
        }
        if ($Missing.Count -gt 0) {
            Write-Check 'FAIL' 'plugin.json' "missing fields: $($Missing -join ', ')"
            $Failures++
        }
        else {
            Write-Check 'PASS' 'plugin.json' "$($Plugin.name) v$($Plugin.version)"
        }
    }
    catch {
        Write-Check 'FAIL' 'plugin.json' "invalid JSON: $($_.Exception.Message)"
        $Failures++
    }
}

# ---------------------------------------------------------------------------
# 1b. Assert-CodexPluginJson
# ---------------------------------------------------------------------------
$CodexPluginPath = Join-Path $RepoRoot '.codex-plugin/plugin.json'
if (-not (Test-Path -LiteralPath $CodexPluginPath)) {
    Write-Check 'FAIL' 'codex-plugin.json' 'missing .codex-plugin/plugin.json'
    $Failures++
}
else {
    try {
        $CodexPlugin = Get-Content -LiteralPath $CodexPluginPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $SkillsPath = Join-Path $RepoRoot 'skills'
        $ActiveCodexHooksPath = Join-Path $RepoRoot 'hooks/hooks.json'
        $PackagedActiveCodexHooksPath = Join-Path $RepoRoot 'plugins/ezpowers/hooks/hooks.json'
        $TraceHookTemplatePath = Join-Path $RepoRoot 'docs/reference/trace-hooks-template.json'
        if ($CodexPlugin.PSObject.Properties.Name -contains 'commands') {
            Write-Check 'FAIL' 'codex-plugin.json' 'unsupported commands field present; Codex exposes EZPowers through skills'
            $Failures++
        }
        elseif (Test-Path -LiteralPath $ActiveCodexHooksPath) {
            Write-Check 'FAIL' 'codex-plugin.json' 'active hooks/hooks.json must not ship in the Codex plugin root'
            $Failures++
        }
        elseif (Test-Path -LiteralPath $PackagedActiveCodexHooksPath) {
            Write-Check 'FAIL' 'codex-plugin.json' 'packaged mirror must not ship active hooks/hooks.json'
            $Failures++
        }
        elseif (-not (Test-Path -LiteralPath $TraceHookTemplatePath)) {
            Write-Check 'FAIL' 'codex-plugin.json' 'missing docs/reference/trace-hooks-template.json'
            $Failures++
        }
        elseif ($CodexPlugin.skills -ne './skills/') {
            Write-Check 'FAIL' 'codex-plugin.json' "skills path must be ./skills/, found '$($CodexPlugin.skills)'"
            $Failures++
        }
        elseif (-not (Test-Path -LiteralPath $SkillsPath)) {
            Write-Check 'FAIL' 'codex-plugin.json' 'skills path does not exist'
            $Failures++
        }
        else {
            $Prompts = @($CodexPlugin.interface.defaultPrompt)
            $PromptText = $Prompts -join "`n"
            $SlashOnlyPrompt = $false
            foreach ($Prompt in $Prompts) {
                if ([string]$Prompt -match '^\s*/') {
                    $SlashOnlyPrompt = $true
                }
            }

            if ($SlashOnlyPrompt -or $PromptText -match '/setup') {
                Write-Check 'FAIL' 'codex-plugin.json' 'defaultPrompt must use supported skill invocation, not slash-only command examples'
                $Failures++
            }
            elseif ($PromptText -notmatch '\$ezpowers:[a-z0-9-]+') {
                Write-Check 'FAIL' 'codex-plugin.json' 'defaultPrompt must include an explicit $ezpowers:<skill> example'
                $Failures++
            }
            else {
                Write-Check 'PASS' 'codex-plugin.json' 'Codex skill discovery metadata valid'
            }
        }
    }
    catch {
        Write-Check 'FAIL' 'codex-plugin.json' "invalid JSON: $($_.Exception.Message)"
        $Failures++
    }
}

# ---------------------------------------------------------------------------
# 2. Assert-AgentFrontmatter
# ---------------------------------------------------------------------------
$AgentsDir = Join-Path $RepoRoot 'agents'
if (Test-Path -LiteralPath $AgentsDir) {
    $AgentFiles = Get-ChildItem -Path $AgentsDir -Filter '*.md' -File
    foreach ($AgentFile in $AgentFiles) {
        $AgentName = $AgentFile.BaseName
        $Text = Get-Content -LiteralPath $AgentFile.FullName -Raw -Encoding UTF8

        # implementer-prompt.md is a template, not an agent with frontmatter
        if ($Text -notmatch '^---\s*\r?\n') {
            Write-Check 'WARN' "agent:$AgentName" 'no YAML frontmatter (may be a template)'
            $Warnings++
            continue
        }

        $FmMatch = [regex]::Match($Text, '(?s)^---\s*\r?\n(.*?)\r?\n---')
        if (-not $FmMatch.Success) {
            Write-Check 'FAIL' "agent:$AgentName" 'malformed YAML frontmatter'
            $Failures++
            continue
        }

        $Frontmatter = $FmMatch.Groups[1].Value
        $RequiredFields = @('name', 'description', 'tools')
        $MissingFields = @()
        foreach ($Field in $RequiredFields) {
            if ($Frontmatter -notmatch "(?m)^${Field}:") {
                $MissingFields += $Field
            }
        }

        if ($MissingFields.Count -gt 0) {
            Write-Check 'FAIL' "agent:$AgentName" "missing fields: $($MissingFields -join ', ')"
            $Failures++
        }
        else {
            $ToolsMatch = [regex]::Match($Frontmatter, 'tools:\s*\[([^\]]*)\]')
            $ToolsList = if ($ToolsMatch.Success) { $ToolsMatch.Groups[1].Value } else { '?' }
            Write-Check 'PASS' "agent:$AgentName" "frontmatter valid (tools: $ToolsList)"
        }
    }
}
else {
    Write-Check 'FAIL' 'agents' 'agents/ directory not found'
    $Failures++
}

# ---------------------------------------------------------------------------
# 3. Assert-CommandStructure
# ---------------------------------------------------------------------------
$CommandsDir = Join-Path $RepoRoot 'commands'
if (Test-Path -LiteralPath $CommandsDir) {
    $CommandFiles = Get-ChildItem -Path $CommandsDir -Filter '*.md' -File
    foreach ($CmdFile in $CommandFiles) {
        $CmdName = $CmdFile.BaseName
        $Text = Get-Content -LiteralPath $CmdFile.FullName -Raw -Encoding UTF8

        if ($Text -match '^---\s*\r?\n') {
            $FmMatch = [regex]::Match($Text, '(?s)^---\s*\r?\n(.*?)\r?\n---')
            if (-not $FmMatch.Success) {
                Write-Check 'FAIL' "command:$CmdName" 'frontmatter opened but not closed'
                $Failures++
                continue
            }
            $Fm = $FmMatch.Groups[1].Value
            if ($Fm -notmatch '(?m)^description:') {
                Write-Check 'WARN' "command:$CmdName" 'frontmatter missing description'
                $Warnings++
                continue
            }
        }

        Write-Check 'PASS' "command:$CmdName" 'structure valid'
    }
}
else {
    Write-Check 'FAIL' 'commands' 'commands/ directory not found'
    $Failures++
}

# ---------------------------------------------------------------------------
# 4. Assert-SkillIntegrity
# ---------------------------------------------------------------------------
$SkillsDir = Join-Path $RepoRoot 'skills'
if (Test-Path -LiteralPath $SkillsDir) {
    $SkillDirs = Get-ChildItem -Path $SkillsDir -Directory
    foreach ($SkillDir in $SkillDirs) {
        $SkillName = $SkillDir.Name
        $SkillMd = Join-Path $SkillDir.FullName 'SKILL.md'

        if (-not (Test-Path -LiteralPath $SkillMd)) {
            Write-Check 'FAIL' "skill:$SkillName" 'missing SKILL.md'
            $Failures++
            continue
        }

        $Text = Get-Content -LiteralPath $SkillMd -Raw -Encoding UTF8
        $FmMatch = [regex]::Match($Text, '(?s)^---\s*\r?\n(.*?)\r?\n---')
        if (-not $FmMatch.Success) {
            Write-Check 'FAIL' "skill:$SkillName" 'SKILL.md missing YAML frontmatter'
            $Failures++
            continue
        }

        $Fm = $FmMatch.Groups[1].Value
        if ($Fm -notmatch '(?m)^name:') {
            Write-Check 'FAIL' "skill:$SkillName" 'SKILL.md frontmatter missing name field'
            $Failures++
            continue
        }

        # Check references/ subdir files if referenced in SKILL.md
        $RefsDir = Join-Path $SkillDir.FullName 'references'
        if (Test-Path -LiteralPath $RefsDir) {
            # Match markdown links like (references/file.md) or bare references/file.md
            $RefMatches = [regex]::Matches($Text, '\(?(references/[^\s\)\]]+\.md)')
            $SeenRefs = @{}
            $BrokenRefs = @()
            foreach ($RefMatch in $RefMatches) {
                $RefValue = $RefMatch.Groups[1].Value
                if ($SeenRefs.ContainsKey($RefValue)) { continue }
                $SeenRefs[$RefValue] = $true
                $RefPath = Join-Path $SkillDir.FullName $RefValue
                if (-not (Test-Path -LiteralPath $RefPath)) {
                    $BrokenRefs += $RefValue
                }
            }
            if ($BrokenRefs.Count -gt 0) {
                Write-Check 'FAIL' "skill:$SkillName" "broken references: $($BrokenRefs -join ', ')"
                $Failures++
                continue
            }
        }

        Write-Check 'PASS' "skill:$SkillName" 'SKILL.md valid'
    }
}
else {
    Write-Check 'WARN' 'skills' 'skills/ directory not found'
    $Warnings++
}

# ---------------------------------------------------------------------------
# 5. Assert-CrossReferences
# ---------------------------------------------------------------------------
$CommandFiles = @()
if (Test-Path -LiteralPath $CommandsDir) {
    $CommandFiles = Get-ChildItem -Path $CommandsDir -Filter '*.md' -File
}

foreach ($CmdFile in $CommandFiles) {
    $CmdName = $CmdFile.BaseName
    $Text = Get-Content -LiteralPath $CmdFile.FullName -Raw -Encoding UTF8
    $SeenXrefs = @{}
    $OptionalGeneratedDocs = @{
        'set-rules' = @('conventions.md')
        'review' = @('conventions.md')
        'sync-docs' = @('architecture.md', 'protocol.md', 'schema.md', 'config.md')
    }

    # Check agent references
    $AgentRefs = [regex]::Matches($Text, 'agents/([^\s\),`]+\.md)')
    foreach ($Ref in $AgentRefs) {
        $Key = "${CmdName}->agent:$($Ref.Groups[1].Value)"
        if ($SeenXrefs.ContainsKey($Key)) { continue }
        $SeenXrefs[$Key] = $true
        $AgentPath = Join-Path $RepoRoot $Ref.Value
        if (Test-Path -LiteralPath $AgentPath) {
            Write-Check 'PASS' "xref:${CmdName}->$($Ref.Groups[1].Value)" 'agent exists'
        }
        else {
            Write-Check 'FAIL' "xref:${CmdName}->$($Ref.Groups[1].Value)" "$($Ref.Value) not found"
            $Failures++
        }
    }

    # Check docs/reference references
    $DocRefs = [regex]::Matches($Text, 'docs/reference/([^\s\),`]+\.md)')
    foreach ($Ref in $DocRefs) {
        $Key = "${CmdName}->doc:$($Ref.Groups[1].Value)"
        if ($SeenXrefs.ContainsKey($Key)) { continue }
        $SeenXrefs[$Key] = $true
        $DocPath = Join-Path $RepoRoot $Ref.Value
        if (Test-Path -LiteralPath $DocPath) {
            Write-Check 'PASS' "xref:${CmdName}->$($Ref.Groups[1].Value)" 'doc exists'
        }
        elseif ($OptionalGeneratedDocs.ContainsKey($CmdName) -and $OptionalGeneratedDocs[$CmdName] -contains $Ref.Groups[1].Value) {
            Write-Check 'WARN' "xref:${CmdName}->$($Ref.Groups[1].Value)" "$($Ref.Value) is an optional generated doc slot"
            $Warnings++
        }
        else {
            Write-Check 'FAIL' "xref:${CmdName}->$($Ref.Groups[1].Value)" "$($Ref.Value) not found"
            $Failures++
        }
    }
}

# ---------------------------------------------------------------------------
# 6. Assert-DocsIndex
# ---------------------------------------------------------------------------
$IndexPath = Join-Path $RepoRoot 'docs/INDEX.md'
if (Test-Path -LiteralPath $IndexPath) {
    $IndexText = Get-Content -LiteralPath $IndexPath -Raw -Encoding UTF8
    $LinkMatches = [regex]::Matches($IndexText, '\]\(([^\)]+\.md)\)')
    foreach ($Link in $LinkMatches) {
        $LinkTarget = $Link.Groups[1].Value
        # Resolve relative to docs/
        $ResolvedPath = Join-Path (Join-Path $RepoRoot 'docs') $LinkTarget
        if (Test-Path -LiteralPath $ResolvedPath) {
            Write-Check 'PASS' "docs-index->$LinkTarget" 'linked file exists'
        }
        else {
            Write-Check 'WARN' "docs-index->$LinkTarget" 'linked file not found'
            $Warnings++
        }
    }
}
else {
    Write-Check 'WARN' 'docs/INDEX.md' 'docs index not found'
    $Warnings++
}

# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------
if ($Failures -gt 0) {
    Write-Output "Plugin smoke verdict: FAIL ($Failures failure(s), $Warnings warning(s))"
    exit 1
}

Write-Output "Plugin smoke verdict: PASS ($Warnings warning(s))"
exit 0
