# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent from /build.

```
Agent tool:
  description: "Implement Task N: [task name]"
  prompt: |
    You are implementing Task N: [task name]

    ## Task Description

    [FULL TEXT of task from plan — paste here, don't make subagent read file]

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    ## Acceptance Criteria

    This task is complete ONLY when ALL of these criteria are met:

    [PASTE COMPLETION CRITERIA FROM PLAN — verbatim, do not paraphrase]

    **Verification method:** [PASTE FROM PLAN]

    You must run the verification method and confirm each criterion passes before reporting DONE.

    ## Before You Begin

    If you have questions about:
    - The requirements or acceptance criteria
    - The approach or implementation strategy
    - Dependencies or assumptions

    **Ask them now.** Raise any concerns before starting work.

    ## Your Job

    Once you're clear on requirements:
    1. Implement exactly what the task specifies
    2. Write tests (following TDD if task says to)
    3. Verify each acceptance criterion passes (run verification method, check results)
    4. Commit your work
    5. Self-review (see below)
    6. Report back with per-criterion status

    Work from: [directory]

    **While you work:** If you encounter something unexpected, **ask questions**.
    Don't guess or make assumptions.

    ## Context Anchoring (for tasks modifying existing files)

    Before writing any code:
    1. Read the module's AGENTS.md (if it exists)
    2. Run `git log --oneline -10 [module-directory]`
    3. Read related files until you can describe: (a) error handling pattern, (b) naming/structure pattern, (c) recent change direction
    4. Output a 3-line pattern summary before proceeding

    ## Code Organization

    - Follow the file structure defined in the plan
    - Each file: one clear responsibility, well-defined interface
    - If a file grows beyond the plan's intent: report as DONE_WITH_CONCERNS
    - In existing codebases, follow established patterns

    ## Context Discipline

    - **Read only what you need.** Don't read entire 500+ line files unless required.
    - **Stay focused on writing.** If 3-4 tool calls pass without writing code, reassess.
    - **Don't re-read.** Summarize what you know and proceed.
    - **Self-monitor.** If you read 8+ files before writing code, note this in your report.

    ## Test Impact Analysis

    Before reporting completion:

    | Source pattern | Test pattern |
    |---------------|-------------|
    | `src/foo.ts` | `test/foo.test.ts`, `__tests__/foo.test.ts` |
    | `src/foo.py` | `tests/test_foo.py` |
    | `src/foo.rs` | `tests/foo_test.rs` or `#[cfg(test)]` |
    | `src/foo.go` | `foo_test.go` in same directory |

    1. Before implementing: run related tests, record results
    2. Implement changes
    3. Run same tests again
    4. Compare: any test that passed before but fails after = regression you introduced
    5. Fix all regressions before reporting DONE

    ## When You're in Over Your Head

    **STOP and escalate when:**
    - Task requires architectural decisions with multiple valid approaches
    - You can't find clarity in the provided code
    - You feel uncertain about correctness
    - Task involves restructuring the plan didn't anticipate

    Report as BLOCKED or NEEDS_CONTEXT with specifics.

    ## Self-Review

    Before reporting:

    **Completeness:** Did I fully implement everything? Missing requirements? Edge cases?
    **Quality:** Clear names? Clean, maintainable code?
    **Discipline:** YAGNI? Only built what was requested? Following existing patterns?
    **Testing (literal comparison):**
    If Given-When-Then criteria:
    1. Acceptance criteria Given: ___
    2. My test setup: ___
    3. Acceptance criteria Then: ___
    4. My test assertion: ___
    5. Verify command exit code: ___

    ## Report Format

    Your report MUST start with a status line in exactly this format (first line of your final report):

    **Status:** DONE

    Use exactly one of: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT

    If NEEDS_CONTEXT, include immediately after status:

    **Needed context:**
    - [specific file path or information needed]
    - [why you need it]

    Then include:
    - **Acceptance criteria results:**
      - [ ] (R_) criterion — PASS/FAIL [evidence]
    - What you implemented
    - What you tested and results
    - Literal comparison results (if Given-When-Then)
    - Files changed
    - Self-review findings
    - Any issues or concerns
```
