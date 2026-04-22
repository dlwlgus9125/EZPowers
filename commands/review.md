# /review — 변경사항 리뷰

프로젝트 변경사항을 리뷰한다. 메인 플로우와 독립적으로 언제든 호출 가능.

## 1. 컨텍스트 수집

먼저 다음을 읽는다:
- `CLAUDE.md`
- `AGENTS.md` (있으면)
- `.harness/config.json` (있으면)
- spec 문서 (인자로 경로가 주어지거나, 최근 spec이 있으면)

변경 파일 확인:
```bash
git diff --name-only
git diff --cached --name-only
```

변경이 없으면 안내하고 종료.

## 2. 리뷰 원칙

- **Finding이 요약보다 먼저** — 문제를 구체적으로 짚는다
- **증거 없는 "문제 없음" 금지** — 각 체크에 근거를 기술
- **diff 바깥도 본다** — 변경이 영향을 미치는 관련 파일을 추적
- **spec이 있으면 spec 대비 검증** — 구현이 spec의 AC를 충족하는지

## 3. 체크리스트

### 3-1. Spec 대비 구현 완전성 (spec이 있을 때)

- 모든 R의 AC가 구현에 반영되었는가
- Verify 커맨드를 실행하여 PASS/FAIL 확인
- Impact scope에 명시된 파일이 실제로 수정되었는가
- Edge case가 처리되었는가

### 3-2. 아키텍처 준수

- 디렉터리 구조와 책임 분리가 기존 원칙을 따르는가
- 계층 경계를 깨지 않았는가
- 새 wiring이 실제로 연결되었는가

### 3-3. 테스트 존재

- 변경에 대응하는 테스트가 있는가
- 테스트도 함께 수정되었는가
- mock에 과도하게 의존하지 않는가

### 3-4. 보안

- 입력 검증
- 인증/인가 체크
- 민감 데이터 노출
- 인젝션 가능성

### 3-5. 빌드/테스트

가능하면 config의 명령으로 확인:
- `config.build.command`
- `config.test.command`
- `config.lint.command`

## 4. 출력 형식

문제가 있으면 severity 높은 순서대로:

```
[path:line] [severity] 문제 설명
근거: ...
영향: ...
```

severity: `critical` > `major` > `minor`

문제가 없으면:

```
리뷰 finding 없음.
검증 결과: [실행한 검증과 결과]
잔여 리스크: [있으면]
테스트 공백: [있으면]
```
