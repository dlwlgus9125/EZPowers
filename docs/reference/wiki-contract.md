---
doc_type: contract
authority: canonical
status: active
---

# Local Wiki Contract

EZPowers 5.1 provides an optional, worktree-local Markdown wiki for reusable
session knowledge. The wiki is supporting memory only. Repository files,
instructions, specs, plans, config, and verification evidence always take
precedence.

## Storage And Lifecycle

The runtime owns:

```text
.ezpowers/wiki/
  pages/<id>.md
  index.md
  log.md
  errors/*.json
  backups/<prune-id>/
```

The tree is excluded from EZPowers completion fingerprints and should remain
untracked. The installer does not edit `.gitignore`. Each worktree has its own
wiki; no global or cross-worktree synchronization is implied.

Pages use flat YAML frontmatter with `id`, `title`, `category`, `status`,
`tags`, `source`, `created_at`, and `updated_at`. Categories are
`architecture`, `decision`, `convention`, `debugging`, `environment`,
`verification`, `reference`, or `session-log`. Status is `candidate`,
`promoted`, or `archived`.

`index.md` is derived from pages. `log.md` is an operation chronicle. Use
`wiki refresh` to rebuild the index; do not treat either file as canonical
knowledge.

## Operations

All structured inputs are JSON objects and all automation should request JSON
output:

```text
python .ezpowers/ezpowers.py wiki add --input <json> --json
python .ezpowers/ezpowers.py wiki read --id <id> --json
python .ezpowers/ezpowers.py wiki list --input <json> --json
python .ezpowers/ezpowers.py wiki query --input <json> --json
python .ezpowers/ezpowers.py wiki lint --json
python .ezpowers/ezpowers.py wiki refresh --json
```

`add` accepts only `id`, `title`, `category`, `tags`, and `body`; its source is
recorded as manual. Query is deterministic keyword and tag search. It
normalizes Unicode with NFKC, case-folds text, and indexes word tokens plus CJK
characters and bigrams. It does not use embeddings, a network service, or
hidden model state.

Candidate pages are unverified hints. Before relying on one, query or read it,
then confirm the claim against repository evidence.

## Promotion

Promotion never writes canonical project documentation. First author the
settled knowledge through the normal documentation, spec, plan, or code
workflow. The target must already exist and must be `AGENTS.md`, `CLAUDE.md`,
or Markdown under `docs/`.

Run promotion without `--confirm` to receive a preview hash binding the page
bytes, target path, and target bytes. Confirm with the unchanged hash:

```text
python .ezpowers/ezpowers.py wiki promote --input <json> --json
python .ezpowers/ezpowers.py wiki promote --input <same-json> --confirm --preview-sha256 <sha> --json
```

Confirmation changes only the local page status and records the target path
and SHA-256. Lint reports target deletion or hash drift. Promotion is a
traceability marker, not ownership or completion evidence.

## Pruning

There is no automatic deletion. `wiki prune` requires an explicit non-empty
list of page IDs, rejects promoted pages, previews the exact pages and a
binding hash, and requires `--confirm` with that hash. Confirmation copies the
pages and a hash manifest below `backups/` before removal. The preview becomes
stale if a page changes.

## SessionEnd Capture

Capture hooks are disabled by default and separate from completion Stop hooks.
Setup may add `--enable-wiki-hooks claude`, `codex`, or `both` only after
explicit approval. The installed commands are:

```text
<absolute-python> <project>/.ezpowers/ezpowers.py wiki capture --host claude
<absolute-python> <project>/.ezpowers/ezpowers.py wiki capture --host codex
```

The capture process reads at most 256 KiB of JSON and retains only:

- a one-way fingerprint of an allowlisted session ID;
- host and lifecycle event name;
- changed project-relative paths, excluding runtime-local trees;
- active plan;
- latest all-scope evidence status and check IDs/statuses.

It never stores transcript text, prompts, responses, arbitrary hook fields,
tool inputs or outputs, command output, environment variables, credentials, or
file contents. `cwd` may be read from the hook payload but is not persisted.
Capture writes one `session-log` candidate, returns `{}`, and exits zero.
Failures are best effort and may create only a bounded local error record.

## Evidence

- [OMX wiki skill](https://github.com/Yeachan-Heo/oh-my-codex/blob/main/skills/wiki/SKILL.md)
- [OMC wiki skill](https://github.com/Yeachan-Heo/oh-my-claudecode/blob/main/skills/wiki/SKILL.md)
- `scripts/ezpowers.py`
- `docs/reference/documentation-contract.md`
