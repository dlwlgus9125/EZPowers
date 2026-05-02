---
description: Synchronize reference docs with codebase state
allowed-tools: [Bash, Read, Write, Grep, Glob]
---

# /sync-docs — Reference Document Synchronization

Reflect the current codebase state in reference docs. Can be invoked independently at any time, and is automatically suggested at the `/choiceexecutor` completion step.

## 1. Pre-flight Checks

Read the following:
- `AGENTS.md`
- `.harness/config.json`
- `docs/INDEX.md`

If missing, direct and stop: "Run `/setup` first."

## 2. Codebase Scan

Collect the actual current state of the codebase.

### 2-1. Module Structure

- Explore source directories (manifest-based: `src/`, `lib/`, `app/`, `packages/`, etc.)
- Per module/package: name, role (inferred from main exports), dependencies
- Identify entrypoint files

### 2-2. Protocol/API

- Scan for API route or endpoint definition files
- Collect RPC, REST, GraphQL protocol interfaces
- Collect event/message contracts if present

### 2-3. Schema

- Scan DB migration files, ORM models, schema definitions
- Identify key entities and relationships

### 2-4. Config

- Locate environment variable usage (`process.env`, `os.environ`, `std::env`, etc.)
- Config files (`.env.example`, config modules, etc.)

### 2-5. Stack/Conventions

- Compare `AGENTS.md` Stack section vs actual dependencies (manifest)
- Identify newly added key dependencies

## 3. Read Current Document State

Read reference docs registered in `docs/INDEX.md`:
- `docs/reference/architecture.md`
- `docs/reference/protocol.md`
- `docs/reference/schema.md`
- `docs/reference/config.md`
- `AGENTS.md` (Stack, Conventions sections)

Check each document's `status` frontmatter: `draft` | `active` | `stale`

### Mismatch Detection

- **In index but file missing**: Warn and report to user. Ask whether it was deleted or a path error. Do not auto-delete.
- **File exists but not in index**: If `.md` files exist under `docs/reference/` but are not in `INDEX.md`, include them as `[unregistered]` items in the update proposal.

## 4. Diff Analysis

Compare scan results with existing docs to identify **items needing update**.

Classification:
- **New**: Exists in code but not in docs (modules/endpoints/entities/config)
- **Changed**: Code and doc content mismatch (name, structure, role, etc.)
- **Deleted**: In docs but removed from code
- **OK**: Matches

If no differences exist for any document, end with "Sync complete — no updates needed."

## 5. Update Proposal

Output proposals per document with differences:

```
## Update Proposal

### docs/reference/architecture.md
- [New] `src/billing/` module added — handles payment processing
- [Changed] `src/auth/` module — SAML added alongside OAuth
- [Deleted] `src/legacy-adapter/` removed

### docs/reference/protocol.md
- [New] POST /api/billing/charge endpoint

### AGENTS.md — Stack
- [New] Dependency `stripe` added
```

Each item is one line, describing **only what changed**. No implementation details or code.

## 6. User Approval

Show the proposal and ask:

> **Apply the above updates?**
>
> 1. Apply all
> 2. Select per document
> 3. Skip

**Option 1:** Apply all proposals
**Option 2:** List document names; user selects which to apply
**Option 3:** No modifications

### Cascading Update Protection (Option 2)

The same change may span multiple documents (e.g., new module → `architecture.md` + `AGENTS.md` Stack both affected). Selecting only some documents in Option 2 can cause cross-document inconsistency.

**Rules:**
- Analyze cascading relationships between proposal items; group documents that depend on the same fact.
- If only part of a group is selected, warn:

> "Warning: `architecture.md` and `AGENTS.md (Stack)` share the same change (`stripe` dependency added). Applying only one creates cross-document inconsistency. Proceed anyway?"

- If user confirms, proceed. Otherwise, re-select to include/exclude the entire group.

## 7. Apply

For approved documents:

### 7-1. Document Update Principles

- **Preserve existing structure** — follow the document's existing section layout and format
- **Preserve human-written content** — do not touch manually authored descriptions, intent, or context
- **Update facts only** — update only code-derivable facts: module lists, endpoint lists, entity lists, etc.
- **Preserve authority** — do not change a `canonical` document's authority
- **Update status** — `draft` → `active` (on first substantive content), preserve existing status on subsequent updates

### 7-2. Empty Slot Documents (status: draft, no body)

When populating a slot created by `/setup` for the first time:
- Change frontmatter `status` to `active`
- Compose initial sections based on scan results
- Describe only what currently exists in code — no excessive structure

### 7-3. Documents with Existing Content

- New items: add to appropriate section
- Changed items: modify the relevant line/section
- Deleted items: remove (no comments or history)

### 7-4. AGENTS.md Update

- **Only the Stack section** is auto-updated (derived from manifest)
- **Do not touch Conventions or Boundaries sections** — these are user-authored intentional rules

### 7-5. docs/INDEX.md Update

Update INDEX.md only when a new document is added or authority changes.

## 8. Post-Apply Verification

Before committing, re-verify that each update item actually matches the code.

### Verification Method

Re-read the updated documents and for each change item:

- **New items**: Confirm the code path actually exists (`ls` or `glob`)
- **Changed items**: Confirm the documented content matches the current code state (read the relevant file/export/endpoint)
- **Deleted items**: Confirm the code path no longer exists

### On Verification Failure

If a mismatch is found, fix that item only and re-verify. If still mismatched after fix, report to user and exclude that item from the commit.

### On Verification Pass

Proceed to commit after all items pass.

## 9. Commit

If updates were applied, commit:
```
docs: sync reference docs with codebase
```

Include the list of updated files in the commit body.

## 10. Output

```
## Sync Results

| Document | Status | Changes |
|----------|--------|---------|
| architecture.md | Updated | +2 modules, ~1 changed, -1 deleted |
| protocol.md | Updated | +1 endpoint |
| schema.md | No change | — |
| config.md | No change | — |
| AGENTS.md (Stack) | Updated | +1 dependency |
```

## /choiceexecutor Integration

At the `/choiceexecutor` completion step (Section 14), after final code review passes:

> **Sync reference docs with the codebase?** (`/sync-docs`)
>
> 1. Run
> 2. Skip

If user selects 1, follow this command's procedure.
Can also be invoked independently later by running `/sync-docs`.
