# /eval -- eval suite 실행 및 점수 보고

EZPowers eval 케이스를 실행하고 버전별 점수를 보고한다. 메인 플로우와 독립적으로 언제든 호출 가능.

<HARD-GATE>
`--baseline` 플래그 사용 시 golden split이 100% 통과해야만 베이스라인을 기록한다. golden 실패 상태에서 베이스라인을 강제 기록하지 않는다.
</HARD-GATE>

## Anti-Pattern: "케이스가 적으니까 eval은 아직 필요 없다"

케이스가 4개여도 regression guard는 작동한다. 측정 없는 변경은 허용되지 않는다. eval을 미루면 회귀가 누적된다.

## Usage

```
/eval                      # 모든 split 실행, compact 결과
/eval <split>              # 단일 split (optimization | holdout | golden | honeypot)
/eval --case <case_id>     # 단일 케이스 실행
/eval --baseline           # 현재 점수를 새 베이스라인으로 기록 (golden 100% 필수)
/eval --diff <version>     # 지정 버전 베이스라인과 비교
```

## Process Flow

```
인자 파싱
  -> 사전 확인 (evals/ 존재, plugin.json 버전)
  -> 케이스 수집 (split별 또는 단일 케이스)
  -> scripts/run_baseline.py 호출
  -> 결과 파싱
  -> 출력 포맷팅 (per-split, per-stratum, regressions, capabilities)
  -> Verdict 판정
```

## 1. 사전 확인

다음을 확인한다:
- `evals/` 디렉토리 존재 여부
- `.claude-plugin/plugin.json`에서 현재 버전 읽기
- `evals/results/baselines/` 에서 가장 최근 베이스라인 파일 식별

`evals/` 디렉토리가 없으면: "`/setup --with-evals`를 먼저 실행하세요." 안내 후 종료.

## 2. 서브커맨드별 실행

### 2-1. `/eval` (전체 실행)

모든 split을 실행한다:

```bash
python scripts/run_baseline.py --version <current_version> --splits optimization holdout golden honeypot
```

### 2-2. `/eval <split>`

단일 split만 실행한다:

```bash
python scripts/run_baseline.py --version <current_version> --splits <split>
```

### 2-3. `/eval --case <case_id>`

단일 케이스 파일을 실행한다. `case_id`에서 파일 경로를 역산한다:
- `case_id` 형식: `<split>.<slug>.<seq>` (예: `golden.banned_expression_detection.001`)
- `evals/` 아래를 재귀 탐색하여 `case_id` 일치 파일을 찾는다

```bash
python scripts/run_baseline.py --version <current_version> --cases <resolved_path>
```

### 2-4. `/eval --baseline`

현재 점수를 새 베이스라인으로 기록한다.

**Hard gate**: golden split 100% 통과 필수. golden에 실패 케이스가 있으면 차단:
```
BLOCKED: golden 4/4 통과 필수. 현재 <N>/4 통과.
베이스라인 기록 전 golden 실패를 해결하세요.
```

통과 시:
```bash
python scripts/run_baseline.py --version <current_version> --baseline --splits optimization holdout golden honeypot
```

기록 후 `evals/INDEX.md`의 "Last baseline" 섹션을 자동 업데이트한다.

### 2-5. `/eval --diff <version>`

지정 버전의 베이스라인 파일 `evals/results/baselines/<version>.json`을 로드하고 현재 실행 결과와 비교한다.

베이스라인 파일이 없으면: "베이스라인 `<version>` 없음. 사용 가능: [목록]" 안내.

## 3. 출력 형식

### 3-1. Per-split pass rate

```
## Split Summary

| Split | Pass | Total | Rate |
|-------|------|-------|------|
| golden | 4 | 4 | 100% |
| optimization | 18 | 30 | 60% |
| holdout | 5 | 8 | 63% |
| honeypot | 1 | 2 | 50% |
```

자동 실행 불가 케이스(mode=manual)는 Total에서 제외하고 별도 행으로 표시:
```
Manual-only (requires live execution): 19 cases
```

### 3-2. Per-stratum breakdown

```
## Stratum Breakdown

| Command | Pass | Auto | Manual | Rate |
|---------|------|------|--------|------|
| brainstorm | 3 | 11 | 2 | 27% |
| plan | 4 | 7 | 1 | 57% |
| choiceexecutor | 1 | 3 | 10 | 33% |
| setup | 2 | 4 | 0 | 50% |
| ... | | | | |
```

### 3-3. Regressions vs last baseline (`--diff` 사용 시)

이전 베이스라인에서 PASS였으나 현재 FAIL인 케이스를 최대 3개 표시:

```
## Top Regressions (vs 0.6.0)

1. golden.banned_expression_detection.001 — PASS → FAIL
2. optimization.greenfield_cli_tool.001 — PASS → FAIL
3. holdout.api_integration_ko.001 — PASS → FAIL
```

회귀가 없으면: "회귀 없음."

### 3-4. New capabilities

이전 FAIL이었으나 현재 PASS인 케이스를 최대 3개 표시:

```
## New Capabilities (vs 0.6.0)

1. optimization.vague_spec_ko.004 — FAIL → PASS
2. optimization.simple_three_r_spec.001 — FAIL → PASS
```

### 3-5. Verdict

모든 출력 끝에 최종 판정:

```
## Verdict: PASS
```

**PASS 조건:**
- golden split 100% 통과 (자동 실행 가능 케이스 기준)
- `--diff` 사용 시: golden 회귀 없음 + holdout 평균 -10% 이상 하락 없음

**FAIL 조건:**
- golden에 실패 케이스 존재
- `--diff` 사용 시: golden 회귀 또는 holdout >10% 하락

```
## Verdict: FAIL
Reason: golden 3/4 — banned-expression-detection FAIL
```

## Verification

이 커맨드 자체의 정상 작동 확인:
- `/eval golden` 실행 시 golden 4 케이스 결과 출력
- `/eval --diff 0.6.0` 실행 시 베이스라인 비교 출력
- 출력이 `## Verdict: PASS` 또는 `## Verdict: FAIL`로 종료

## Common Rationalizations

| 시도할 변명 | 왜 안 되는가 |
|------------|-------------|
| "golden이 1개만 실패했으니 베이스라인 기록해도 되지 않나" | golden은 inviolable invariant. 1개라도 실패하면 기록 차단. |
| "manual 케이스는 무시하고 자동만 보면 되지 않나" | manual 케이스도 Total에 집계. 자동화 비율 자체가 eval 성숙도 지표. |
| "이전 베이스라인이 없으니 diff를 건너뛰자" | 첫 실행이면 `--baseline`으로 기록부터. diff 없이도 per-split 결과는 항상 표시. |
