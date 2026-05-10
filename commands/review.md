---
description: Review changes against spec for completeness
disable-model-invocation: true
allowed-tools: [Bash, Read, Grep, Glob]
---

# /review — Change Review

Review project changes. Can be invoked independently at any time.

## 1. Context Collection

Read the following first:
- `CLAUDE.md`
- `AGENTS.md` (if present)
- `.harness/config.json` (if present)
- `docs/reference/conventions.md` (if present — coding rules and constraints)
- Spec document (if path given as argument, or if a recent spec exists)

Check changed files:
```bash
git diff --name-only
git diff --cached --name-only
```

If no changes, inform and stop.

## 2. Review Principles

- **Findings before summaries** — identify problems specifically
- **No evidence-free "no issues"** — state the basis for each check
- **Look beyond the diff** — trace related files affected by changes
- **Verify against spec if available** — confirm implementation meets spec AC

## 3. Checklist

### 3-1. Implementation Completeness vs Spec (when spec available)

- Are all R's AC reflected in the implementation?
- Run Verify commands to check PASS/FAIL
- Are files listed in Impact scope actually modified?
- Are edge cases handled?

### 3-2. Architecture Compliance

- Does directory structure and separation of concerns follow existing principles?
- Are layer boundaries preserved?
- Is new wiring actually connected?

### 3-3. Test Presence

- Do tests exist for the changes?
- Were tests also updated?
- No excessive mock dependency?

### 3-4. Security

- Input validation
- Auth/authz checks
- Sensitive data exposure
- Injection potential

### 3-5. Build/Test

If possible, verify using config commands:
- `config.build.command`
- `config.test.command`
- `config.lint.command`

## 4. Output Format

If issues found, in order of severity:

```
[path:line] [severity] Issue description
Basis: ...
Impact: ...
```

Severity: `critical` > `major` > `minor`

If no issues:

```
No review findings.
Verification results: [checks run and results]
Residual risks: [if any]
Test gaps: [if any]
```
