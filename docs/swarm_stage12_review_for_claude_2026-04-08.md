# Swarm Stage 1/2 Review Notes For Claude

작성일: 2026-04-08
대상: `auto_kairos_v3`의 Stage 1/2 개편
초점: `research + manuscript`를 swarm 모드로 돌리는 구조의 안정성 검토

## 검토 요청

아래 관점에서 현재 변경분을 다시 검토해 주세요.

1. 지금 구조가 정말로 `validator 통과 후 종료`인지
2. `character_register.json` + `[char:id]` 규칙이 런타임에서 일관되게 작동하는지
3. writer / validator / orchestrator 간 계약이 서로 충돌하지 않는지
4. 실제 swarm 실행에서 deadlock, stale state, false pass가 날 수 있는지

## 내가 본 핵심 우려

### 1. Writer가 끝났다고 표시하면 validator를 우회하고 종료될 수 있음

현재 `watch_done()`에서 `outline_state.status == "complete"`이면 validator가 아직 문제를 보고 있어도 `meta.status = "done"`으로 올리고 모든 agent를 정지시킵니다.

이건 사실상:

- 기대: validator가 citation/invalid tag 검사까지 끝내고 pass하면 종료
- 실제: writer가 complete 찍으면 일단 종료 가능

관련 파일:

- `auto_agent/swarm/orchestrator.py`
- 특히 `force_done_after_writer_complete` 경로

검토 포인트:

- 이 fallback이 정말 필요한지
- 필요하다면 최소한 validator의 마지막 상태가 pass일 때만 허용해야 하는지

### 2. Validator 재검증 트리거가 너무 약함

현재 validator는 `manuscript.md` 길이가 바뀌었을 때만 다시 검사합니다.

문제:

- 길이 유지한 채 `[claim:]` 태그만 수정하면 재검증 안 됨
- `character_register.json`만 수정해서 invalid char를 해소해도 재검증 안 됨
- manuscript 길이는 같지만 내용이 달라진 경우 stale validation이 남을 수 있음

관련 파일:

- `auto_agent/swarm/agents/validator.py`

검토 포인트:

- content hash 기반으로 바꾸는 게 맞는지
- `character_register.json` 변경도 validator 트리거에 포함해야 하는지

### 3. `[char:id]`는 prompt에서는 필수인데 validator pass 조건에는 반영되지 않음

writer prompt는 `[char:id]`를 사실상 필수 규칙으로 다룹니다.
하지만 validator는 `uncited_character`를 warning만 남기고, pass 계산에는 포함하지 않습니다.

즉:

- 문서상 계약: 필수
- 런타임 계약: 권장에 가까움

관련 파일:

- `auto_agent/swarm/prompts/writer.md`
- `auto_agent/swarm/agents/validator.py`

검토 포인트:

- `[char:]`를 진짜 hard requirement로 둘지
- 아니면 warning 수준으로 낮추고 prompt도 그에 맞춰 완화할지

### 4. 새 인물 append 예시가 실제 런타임과 안 맞을 수 있음

writer prompt의 예시 Bash는 `{workspace_path}` placeholder를 그대로 씁니다.
현재 writer는 prompt 파일을 raw text로 넣기만 하므로, 이 값이 실제로 치환되지 않을 가능성이 큽니다.

또한 `character_register.json`은 workspace ownership map에 명시돼 있지 않고, append 예시도 atomic write 계약을 통하지 않습니다.

가능한 문제:

- prompt 예시 그대로 실행 시 경로 오류
- partial JSON write
- validator가 read 중간에 깨진 JSON을 읽고 default로 fallback

관련 파일:

- `auto_agent/swarm/prompts/writer.md`
- `auto_agent/swarm/agents/writer.py`
- `auto_agent/swarm/workspace.py`

검토 포인트:

- prompt 예시를 실제 값이 들어가게 동적으로 렌더링해야 하는지
- `character_register.json`을 workspace 계약 안에 넣어야 하는지
- writer가 Bash 대신 workspace helper를 쓰게 해야 하는지

## 빠른 결론

내 현재 판단은 이렇습니다.

- 아이디어 자체는 좋음
- 하지만 지금은 `validator gated swarm`이라기보다 `writer complete 중심 swarm`에 더 가까움
- 그래서 Stage 1/2 개편의 방향은 맞아도, 품질 게이트는 아직 헐거움

## 클로드에게 확인받고 싶은 질문

1. `force_done_after_writer_complete`를 제거하는 게 맞는가
2. validator pass를 Phase 2 종료의 유일한 기준으로 두는 게 맞는가
3. `character_register.json`을 workspace의 공식 소유 파일로 승격해야 하는가
4. `[char:]` 규칙을 strict mode와 soft mode 중 어느 쪽으로 가져가는 게 맞는가
5. 지금 구조에서 가장 먼저 막아야 할 실제 장애 시나리오는 무엇인가

## 참고 경로

- `auto_agent/swarm/orchestrator.py`
- `auto_agent/swarm/agents/validator.py`
- `auto_agent/swarm/agents/writer.py`
- `auto_agent/swarm/agents/skeleton_identify.py`
- `auto_agent/swarm/agents/compiler.py`
- `auto_agent/swarm/prompts/writer.md`
- `auto_agent/swarm/prompts/skeleton_identify.md`

