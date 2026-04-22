# Root Cause Tracing

## Overview

버그는 종종 호출 스택 깊은 곳에서 드러난다. 본능적으로 에러가 나타난 곳을 고치고 싶지만, 그것은 증상을 치료하는 것이다.

**핵심 원칙:** 원래의 트리거를 찾을 때까지 호출 체인을 역방향으로 추적하고, 소스에서 고친다.

## When to Use

- 에러가 실행 깊은 곳에서 발생 (진입점이 아님)
- 스택 트레이스가 긴 호출 체인을 보여줌
- 잘못된 데이터가 어디서 발생했는지 불분명
- 어떤 테스트/코드가 문제를 트리거하는지 모름

## Tracing Process

### 1. 증상 관찰
```
Error: git init failed in /Users/user/project/packages/core
```

### 2. 직접적 원인 찾기
**어떤 코드가 이를 직접 유발하는가?**
```typescript
await execFileAsync('git', ['init'], { cwd: projectDir });
```

### 3. 무엇이 이것을 호출했는가?
```
WorktreeManager.createSessionWorktree(projectDir, sessionId)
  -> Session.initializeWorkspace()
  -> Session.create()
  -> test at Project.create()
```

### 4. 전달된 값 추적
- `projectDir = ''` (빈 문자열!)
- 빈 `cwd`는 `process.cwd()`로 해석
- 그것은 소스 코드 디렉터리

### 5. 원래의 트리거 찾기
```typescript
const context = setupCoreTest(); // Returns { tempDir: '' }
Project.create('name', context.tempDir); // beforeEach 전에 접근!
```

## Adding Stack Traces

수동 추적 불가 시 계측 추가:

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('DEBUG git init:', {
    directory, cwd: process.cwd(), stack
  });
  await execFileAsync('git', ['init'], { cwd: directory });
}
```

**테스트에서:** `console.error()` 사용 (logger는 억제될 수 있음)
**위험한 작업 전에:** 실패 이후가 아닌 이전에 로깅
**컨텍스트 포함:** 디렉터리, cwd, 환경 변수, 타임스탬프

## Key Principle

**에러가 나타난 곳만 고치면 안 된다.** 원래의 트리거를 찾을 때까지 역방향으로 추적한다.

근본 원인에서 fix 후 -> [defense-in-depth.md](defense-in-depth.md)로 각 계층에 검증 추가.
