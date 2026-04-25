# /feedback -- 세션 트레이스에 사용자 점수 부착

현재 세션의 트레이스에 사용자 피드백(점수 + 코멘트)을 기록한다. 메인 플로우와 독립적으로 언제든 호출 가능.

<HARD-GATE>
트레이스 파일이 존재하지 않으면 피드백을 기록하지 않는다. `/setup --enable-traces`로 트레이스 수집을 먼저 활성화해야 한다.
</HARD-GATE>

## Anti-Pattern: "나중에 한꺼번에 피드백하면 되지"

피드백은 세션 직후가 가장 정확하다. 시간이 지나면 어떤 상호작용이 좋았고 나빴는지 기억이 흐려진다. 세션 끝에 바로 `/feedback`을 호출한다.

## Usage

```
/feedback +1                # 마지막 세션에 긍정 점수 부착
/feedback +1 "spec이 명확했다"  # 긍정 점수 + 코멘트
/feedback -1 "불필요한 질문을 반복했다"  # 부정 점수 + 코멘트
/feedback last "추가 메모"      # 점수 없이 코멘트만 부착
```

## Process Flow

```
인자 파싱 (score, comment)
  -> 트레이스 디렉토리 탐색
  -> 최신 트레이스 파일 식별
  -> 마지막 엔트리의 scores 배열에 피드백 추가
  -> 저장
  -> 결과 보고
```

## 1. 트레이스 파일 탐색

트레이스 저장 위치: `${CLAUDE_PLUGIN_DATA}/traces/`

탐색 순서:
1. 오늘 날짜 디렉토리: `traces/$(date +%Y-%m-%d)/`
2. 해당 디렉토리에서 가장 최근 수정된 `.jsonl` 파일
3. 오늘 디렉토리가 비어있으면 어제 날짜로 fallback
4. 트레이스 파일이 없으면:

```
트레이스 파일을 찾을 수 없습니다.
`/setup --enable-traces`로 트레이스 수집을 활성화한 뒤 세션을 실행하세요.
```

## 2. 피드백 기록

### 2-1. Score 형식

Langfuse `create_score` 스키마 호환:

```jsonc
{
  "name": "user-feedback",
  "value": 1,          // +1 또는 -1
  "comment": "spec이 명확했다",
  "source": "user",
  "timestamp": "2026-04-25T14:30:00Z"
}
```

### 2-2. `/feedback +1` 또는 `/feedback -1 "reason"`

트레이스 파일의 **마지막 JSONL 엔트리**를 읽고, `scores` 배열에 피드백 객체를 append한다.

기존 `scores` 배열이 없으면 생성한다:
```jsonc
// before
{"trace_id": "...", "hook_event_name": "Stop", "scores": []}

// after
{"trace_id": "...", "hook_event_name": "Stop", "scores": [
  {"name": "user-feedback", "value": 1, "comment": "spec이 명확했다", "source": "user", "timestamp": "2026-04-25T14:30:00Z"}
]}
```

### 2-3. `/feedback last "comment"`

점수 없이 코멘트만 부착한다. `value` 필드를 `null`로 설정:

```jsonc
{"name": "user-feedback", "value": null, "comment": "추가 메모", "source": "user", "timestamp": "..."}
```

## 3. 출력

피드백 기록 후 간결하게 보고:

```
피드백 기록 완료.
  트레이스: traces/2026-04-25/session-abc123.jsonl
  세션: abc123
  점수: +1
  코멘트: "spec이 명확했다"
```

코멘트가 없으면 코멘트 행 생략.

## 4. 피드백 → eval 케이스 승격 안내

`-1` 피드백 기록 시 승격 안내를 표시:

```
이 실패 패턴을 eval 케이스로 등록하려면:
  python scripts/promote_trace.py --days 1
```

## Verification

- `/feedback +1 "test"` 실행 후 트레이스 파일의 마지막 엔트리에 score가 추가됐는지 확인
- 트레이스 파일 없는 상태에서 `/feedback +1` 실행 시 안내 메시지 출력 확인

## Common Rationalizations

| 시도할 변명 | 왜 안 되는가 |
|------------|-------------|
| "트레이스가 없어도 피드백만 별도 파일에 기록하면 되지 않나" | 트레이스와 분리된 피드백은 어떤 상호작용에 대한 것인지 추적 불가. |
| "+1/-1 이진 점수로는 뉘앙스를 못 담지 않나" | 코멘트 필드가 뉘앙스를 담는다. 점수는 필터링용. |
