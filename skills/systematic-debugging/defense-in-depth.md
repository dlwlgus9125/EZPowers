# Defense-in-Depth Validation

## Overview

버그를 수정할 때 한 곳에 검증을 추가하는 것으로 충분하다고 느껴진다. 하지만 단일 검사는 다른 코드 경로, 리팩토링, mock에 의해 우회될 수 있다.

**핵심 원칙:** 데이터가 통과하는 모든 계층에서 검증한다. 버그를 구조적으로 불가능하게 만든다.

## Why Multiple Layers

단일 검증: "버그를 고쳤다"
다중 계층: "버그를 불가능하게 만들었다"

## The 4 Layers

### Layer 1: Entry Point Validation
API 경계에서 명백히 잘못된 입력 거부.

```typescript
function createProject(name: string, dir: string) {
  if (!dir || dir.trim() === '') throw new Error('dir cannot be empty');
  if (!existsSync(dir)) throw new Error(`dir does not exist: ${dir}`);
}
```

### Layer 2: Business Logic Validation
데이터가 현재 작업에 적합한지 확인.

```typescript
function initializeWorkspace(projectDir: string) {
  if (!projectDir) throw new Error('projectDir required');
}
```

### Layer 3: Environment Guards
특정 컨텍스트에서 위험한 작업 방지.

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
포렌식을 위한 컨텍스트 포착.

```typescript
async function gitInit(directory: string) {
  logger.debug('About to git init', {
    directory, cwd: process.cwd(), stack: new Error().stack
  });
}
```

## Applying the Pattern

1. **데이터 흐름 추적** — 잘못된 값의 발생점과 사용점
2. **모든 체크포인트 매핑** — 데이터가 통과하는 모든 지점
3. **각 계층에 검증 추가** — entry, business, environment, debug
4. **각 계층 테스트** — Layer 1 우회 시 Layer 2가 잡는지 확인

**단일 검증 지점에서 멈추지 말 것.** 모든 계층에 검사를 추가한다.
