# Phase 4 — Vault Sync Agent 구현 계획

작성일: 2026-04-29
연관 spec: `docs/superpowers/specs/2026-04-28-research-redesign.md` (Phase 4)
연관 정책: `KAIROS_VAULT_DIR/02-research/llm-wiki-research-policy.md`

---

## 목표

프로젝트 로컬에서 만든 wiki/claims를 볼트(NAS 02-research)로 push.
**파이프라인 외부에서 manual trigger.** NAS 단절 시 큐 보관 후 재시도.

성공 기준:
- 펩시 프로젝트 wiki(12 토픽)를 볼트로 sync 가능
- 슬러그 정규화로 긴 프로젝트 슬러그(`유한양행_100주년_1부터…`)가 표준 entity 슬러그(`유한양행`)로 매핑
- 충돌 시 dedup 또는 새 run으로 추가 (덮어쓰기 안 함)
- file-lock으로 동시 실행 차단
- NAS 단절 시 `~/.auto_agent/vault_sync_queue/`에 보관 후 재가동 시 재시도

## 산출물

```
auto_agent/research/
├── vault_sync.py              # 핵심 sync 로직 + slug 정규화
└── vault_sync_queue.py        # 재시도 큐 관리

auto_agent/agents/             # (신규 디렉토리)
└── vault_sync_agent.py        # CLI 진입점

auto_agent/cli/                # 또는 기존 cli 모듈에 추가
└── vault_sync_command.py

auto_agent/dashboard/
└── vault_sync_routes.py       # POST /api/vault-sync/<slug> 엔드포인트

tests/
├── test_vault_sync.py
└── test_vault_sync_queue.py
```

## 단계별 실행 순서

### Step 4.1 — Slug 정규화기 (LLM-driven)
- `auto_agent/research/vault_sync.py` — `normalize_to_entity_slug(project_slug, vault_slugs)`
- 입력: 긴 프로젝트 슬러그 + 볼트 기존 토픽 슬러그 목록
- 출력: 매칭된 entity slug (없으면 생성 제안)
- LLM (haiku, max_turns=2): "이 프로젝트 슬러그를 어떤 표준 entity로 정규화해야?"
- 예: `유한양행_100주년_1부터_100까지_…` → `유한양행`

### Step 4.2 — Sync 핵심 로직 (NAS write)
- `vault_sync.py` — `sync_project_to_vault(project_dir, vault_root, options)`
- 동작:
  1. 프로젝트 토픽 목록 (manifests/<topic>/)
  2. 각 토픽:
     - normalize → entity slug
     - 볼트 wiki/<entity>/ 존재 여부 확인
     - 신규: wiki copy
     - 기존: claims dedup (claim_id 기반) + manifests/<entity>/claims.jsonl append
  3. raw/ 복사: `02-research/raw/<entity>/<run_id>/`로 immutable copy
  4. topics/<entity>.md snapshot 갱신 (선택)

### Step 4.3 — File-lock + 재시도 큐
- `vault_sync_queue.py`
- File-lock: `~/.auto_agent/vault_sync.lock` (fcntl.flock 또는 단순 mkdir)
- 큐: `~/.auto_agent/vault_sync_queue/<timestamp>_<slug>.json`
- NAS 단절 시 큐 추가
- 다음 sync 시 큐 비우기 시도

### Step 4.4 — CLI 진입점
- `auto-agent vault-sync --project <slug>` 명령 추가
- 옵션:
  - `--dry-run` 변경사항만 출력
  - `--force` 충돌 발생해도 진행
  - `--queue-only` NAS 호출 안 하고 큐에만 추가

### Step 4.5 — 대시보드 버튼 (선택)
- `auto_agent/dashboard/vault_sync_routes.py`
- POST `/api/p/<project_ref>/vault-sync` — sync 실행
- 결과를 SSE 메시지로 반환
- 대시보드 프로젝트 페이지에 "🔁 볼트로 sync" 버튼

### Step 4.6 — 테스트
- `test_vault_sync_queue.py`: 큐 추가/꺼내기/실패 시 보관
- `test_vault_sync.py`:
  - dedup 로직 (claim_id 매칭, 중복 무시)
  - file-lock 동시 실행 차단
  - normalize 매칭 (mock LLM)
  - dry-run 안전성 (write 안 일어남)

### Step 4.7 — 펩시 sync 실증
- `auto-agent vault-sync --project 펩시의_역사 --dry-run` 으로 변경사항 확인
- 실제 sync → 볼트의 `wiki/pepsi/`가 갱신되는지

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 다른 사용자/프로세스가 같은 토픽 동시 sync | file-lock + 토픽별 시간 stamp |
| 슬러그 매칭 false positive (잘못 정규화) | confidence 낮으면 사용자 confirm 또는 skip |
| 볼트 기존 wiki 덮어쓰기 | 항상 dedup + append 전략. wiki 페이지는 *.synced.md 접미사 검토 |
| NAS 부분 마운트 (read OK / write 실패) | write 시도 후 OSError 잡아 큐로 |
| evidence 없는 claim push | `claims_ledger.jsonl`에 evidence 있는 항목만 sync |
| 재시도 큐 무한 누적 | 24시간 이상된 항목은 자동 stale 마킹 |

## 작업 시간 추정

| Step | 시간 |
|---|---|
| 4.1 slug 정규화기 | 1h |
| 4.2 sync 핵심 로직 | 1.5h |
| 4.3 file-lock + 큐 | 1h |
| 4.4 CLI | 0.5h |
| 4.5 대시보드 (선택) | 1h |
| 4.6 테스트 | 1h |
| 4.7 펩시 검증 | 0.5h |
| **합계** | **~6.5h** |

## 다음 Phase 미리보기

- **Phase 5**: cutover & cleanup
  - step_1_ingest 폐기 → step_1_fresh + step_1_vault_lookup으로 교체
  - ResearchAgent NAS 호출 코드 제거
  - `auto_agent/tools/*_lane.py` 옛 복사본 정리
  - 옛 프로젝트 마이그레이션 스크립트 (claims.jsonl → claims_ledger.jsonl)
