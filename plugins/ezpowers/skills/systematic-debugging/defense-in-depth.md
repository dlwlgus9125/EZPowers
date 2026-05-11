# Defense-in-Depth Validation

## Overview

When fixing a bug, adding validation in one place feels sufficient. But a single check can be bypassed by other code paths, refactoring, or mocks.

**Core principle:** Validate at every layer the data passes through. Make the bug structurally impossible.

## Why Multiple Layers

Single validation: "Fixed the bug"
Multiple layers: "Made the bug impossible"

## The 4 Layers

### Layer 1: Entry Point Validation
Reject obviously invalid input at the API boundary.

```typescript
function createProject(name: string, dir: string) {
  if (!dir || dir.trim() === '') throw new Error('dir cannot be empty');
  if (!existsSync(dir)) throw new Error(`dir does not exist: ${dir}`);
}
```

### Layer 2: Business Logic Validation
Verify data is appropriate for the current operation.

```typescript
function initializeWorkspace(projectDir: string) {
  if (!projectDir) throw new Error('projectDir required');
}
```

### Layer 3: Environment Guards
Prevent dangerous operations in specific contexts.

```typescript
async function gitInit(directory: string) {
  if (process.env.NODE_ENV === 'test') {
    const normalized = normalize(resolve(directory));
    if (!normalized.startsWith(normalize(tmpdir()))) {
      throw new Error(`Refusing git init outside temp dir during tests: ${directory}`);
    }
  }
}
```

### Layer 4: Debug Instrumentation
Capture context for forensic analysis.

```typescript
async function gitInit(directory: string) {
  logger.debug('About to git init', {
    directory, cwd: process.cwd(), stack: new Error().stack
  });
}
```

## Applying the Pattern

1. **Trace the data flow** — where the wrong value originates and where it is consumed
2. **Map all checkpoints** — every point the data passes through
3. **Add validation at each layer** — entry, business, environment, debug
4. **Test each layer** — verify Layer 2 catches what bypasses Layer 1

**Do not stop at a single validation point.** Add checks at every layer.
