# Root Cause Tracing

## Overview

Bugs often surface deep in the call stack. The instinct is to fix where the error appears, but that treats the symptom.

**Core principle:** Trace the call chain backward until the original trigger is found, and fix at the source.

## When to Use

- Error occurs deep in execution (not at the entry point)
- Stack trace shows a long call chain
- Origin of the wrong data is unclear
- Unknown which test/code triggers the issue

## Tracing Process

### 1. Observe the Symptom
```
Error: git init failed in /Users/user/project/packages/core
```

### 2. Find the Direct Cause
**What code directly produces this?**
```typescript
await execFileAsync('git', ['init'], { cwd: projectDir });
```

### 3. What Called This?
```
WorktreeManager.createSessionWorktree(projectDir, sessionId)
  -> Session.initializeWorkspace()
  -> Session.create()
  -> test at Project.create()
```

### 4. Trace the Passed Values
- `projectDir = ''` (empty string!)
- Empty `cwd` resolves to `process.cwd()`
- That is the source code directory

### 5. Find the Original Trigger
```typescript
const context = setupCoreTest(); // Returns { tempDir: '' }
Project.create('name', context.tempDir); // Accessed before beforeEach!
```

## Adding Stack Traces

Add instrumentation when manual tracing is insufficient:

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory, cwd: process.cwd(), stack
  });
  await execFileAsync('git', ['init'], { cwd: directory });
}
```

**In tests:** Use `console.error()` (loggers may be suppressed)
**Before dangerous operations:** Log before the failure, not after
**Include context:** directory, cwd, environment variables, timestamps

## Key Principle

**Do not fix only where the error appears.** Trace backward until the original trigger is found.

After fixing at the root cause -> add validation at each layer via [defense-in-depth.md](defense-in-depth.md).
