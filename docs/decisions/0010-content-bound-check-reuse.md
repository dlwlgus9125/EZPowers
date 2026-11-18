# ADR 0010: Content-bound check reuse

- Status: accepted
- Date: 2026-11-18
- Decision owners: EZPowers maintainers
- Related: `docs/reference/architecture.md`,
  `docs/decisions/0001-host-native-project-local-core.md`,
  `docs/decisions/0007-evidence-gated-assurance-graph.md`,
  `docs/decisions/0008-project-profile-artifact-assurance.md`

## Context

Completion binds an all-scope PASS to the whole workspace: Git HEAD, the
tracked diff, and the untracked-file digest. Any byte change makes every
declared check run again, and a named check referenced by several tasks or by
`required_checks` executes once per reference. In one installed project a
single all-scope run took 532 to 637 seconds, one end-to-end check was 55 to 86
percent of that, and it ran again after small rework that did not touch it.
ADR 0007 reduced wall time only through opt-in parallelism. No earlier decision
accepted or rejected carrying a recorded PASS forward.

The verification cost must follow what a change can affect. An agent must not
choose what to skip, and a project that does not opt in must keep its exact
behavior, evidence shape, and verdicts.

## Decision

A check may declare, inside its exact contract, the project-relative path
patterns whose content determines its outcome:

```json
"reuse": {"paths": ["server/**", "tools/check_api.py"], "exclude": ["**/*.md"]}
```

The declaration is an additive optional field of plan/config schema 2 and 3
checks. It joins the check contract hash only when present, so undeclared
graphs, chain previews, and approvals keep their bytes. A schema-1 check that
carries the field is now rejected instead of having it silently dropped; this
is the one intended visible change for existing files.

For a declared check in a graph-bound flow (plan schema 2 or later) the runtime
derives a reuse key from the check contract hash, the bytes and execute bit of
the matching Git-visible files, the installed-kit identity, the project
profile, the planning artifact inventory, the resolved project root, and the
platform. The pattern language is defined by the runtime, not by a library
matcher: `*` and `?` never cross `/`, and `**` is valid only as a whole segment.

When the latest real execution of the same contract passed under the same key,
the runtime records that PASS for the current occurrence without running the
command. The rules that keep this honest are:

- **Single hop.** Only a really executed PASS is a source. A carried entry
  never becomes a source, so the recorded origin is always the real execution.
- **Stable runs only.** A run that observed a workspace, plan, spec, config,
  installation, or planning-artifact change records no key and offers no
  source.
- **Evidence is the authority.** `.ezpowers/state.json` only locates a
  candidate. The key lives in the source evidence, and the source record, its
  hashes, and its logs are revalidated before every carry.
- **Failure revokes.** An executed failure of the same contract removes the
  candidate; a failed result is never carried into another run.
- **Fail-safe ineligibility.** A pattern that selects no file, a symlink,
  gitlink, unreadable or vanished entry, a spelling that differs from the
  directory listing, or a Git error makes the occurrence execute and neither
  consume nor produce a candidate.
- **Explicit full run.** `verify --no-reuse` executes every occurrence.

The all-scope record still contains every declared occurrence and remains
bound to the current workspace fingerprint. A carried entry is complete: it
holds the current occurrence identity, the source outcome, byte copies of the
source logs inside the new run, and the source run. Certification accepts such
a record and the certificate lists the carried occurrences. Freshness, status,
and the Stop hook neither rehash inputs nor revisit the source run.

A declared check that produced a key runs at most once per verification run;
its other occurrences share that result. Undeclared checks keep running once
per reference, so existing evidence and tests are unchanged.

In an explicit harness chain a carry is accepted only from a result bound to
the same approved run, so the first verification after approval always
executes everything. Preview rejects a reuse-declared oracle check whose scope
omits its own oracle files. The pre-approval baseline never reuses. Gate,
rework, and limit rules are unchanged. The planning profile adds the whole
artifact inventory to the key.

## What the key does not bind

Git history and HEAD, Git-ignored files such as build output and dependency
directories, environment variables, toolchain versions, the clock, the
network, external services, and another check's ignored output. A check that
depends on any of these must stay undeclared.

## Considered options

- Change-size tiers that shrink the required-check set would be simpler, but a
  person or agent would judge the tier, the verdict would mean something
  different per change, and it would resemble the retired lighter execution
  path.
- Keeping the final gate and only removing duplicate work around it preserves
  today's meaning exactly, but small rework still re-executes everything.
- A new plan/config schema version would make the contract change explicit.
  Plan v3 is planning-only and config v3 carries the profile, so a v4 would
  fork both profiles. Unlike the optional planning fields rejected by ADR
  0008, an older runtime that ignores `reuse` executes every check, which is
  the conservative direction.
- A time limit on a carried PASS would bound drift in what the key cannot see.
  The criterion stays content identity; the certificate records the original
  execution time and `--no-reuse` forces a full run. This can be revisited.
- Sharing one execution among undeclared duplicate occurrences would remove
  more work immediately, but it would change legacy execution counts and
  evidence.
- Revalidating the source run during certification would make deleting an old
  run flip a certified result and would add hashing to the Stop hook.

## Consequences

Small rework and commits no longer re-execute checks whose declared content is
unchanged. An incomplete declaration can now produce a false PASS; opt-in
declaration, the every-pattern-must-match rule, the certificate record, and
`--no-reuse` limit but do not remove that risk. A flaky check is carried until
its content changes. The evaluators, evidence, and certificate gain optional
reuse rules and fields, and the state file gains a lazily created hint map.
Installed projects receive the behavior only through `setup --refresh`, which
already makes prior evidence stale and, because the kit identity is in the key,
also invalidates every candidate.
