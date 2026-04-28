# 리서치 파이프라인 재설계 — 프로젝트 로컬 우선 + 볼트 sync-back

작성일: 2026-04-28
대상 모듈: `step_1_ingest`, `step_1b`, `step_2_draft`, `step_2_target`
연관 이슈: 유한양행 step_1_ingest 실패(specialist `seed_only` blocked), 2차 토픽 `source_ids=n/a`
연관 정책: `KAIROS_VAULT_DIR/02-research/llm-wiki-research-policy.md`

---

## 1. 문제 (Why)

현재 `step_1_ingest`는 **수집 + 신뢰도 게이팅 + 클레임화**를 한 번에 처리합니다. 결과:

- ResearchAgent의 7-stage 루프가 quality-assurance에서 `blocked / specialist seed_only`로 멈춤
- 게이트 통과한 클레임도 `source_ids: []`로 비어 나옴 — LLM 사전지식 의존(환각 위험)
- 한국 뉴스 RSS URL 데드 — 외부 NAS 코드라 우리 레포에서 패치 불가
- 클레임은 _수집 시점_이 아니라 _글 쓰는 시점_에 만들어져야 의미 있는데, 순서가 반대
- NAS 직접 read/write는 일시 단절 시 파이프라인 전체가 영향받음
- 볼트 토픽과 프로젝트 slug가 일치 안 해서 기존 자료 재사용 실패

근본:
1. 검증 게이트가 앞단에 너무 무겁게 박혀 있음
2. 볼트(NAS) 의존성이 파이프라인 핵심 경로에 있음

## 2. 목표 (What)

1. **Fresh 단계는 가볍게**: lane(API/RSS) 호출 + 프로젝트 로컬에 raw + wiki 보관. 검증 게이트 제거.
2. **볼트는 read-only 흡수만**: 매칭 실패/NAS 단절도 허용. 파이프라인은 멈추지 않음.
3. **클레임은 원고 작성 시점에**: 글의 맥락에서 retrieve.
4. **모든 클레임에 evidence span 강제**: 환각 차단.
5. **Vault 쓰기는 별도 에이전트로 분리**: 파이프라인 외부에서 manual trigger.
6. **ResearchAgent 의존성 제거**: lane만 우리 레포로.

## 3. 핵심 아키텍처 — git pull → work → push 패턴

```
[프로젝트 로컬]                      [볼트 (NAS, read-only 또는 sync-back)]
output/<proj>/research/              KAIROS_VAULT_DIR/02-research/
├── raw/                ──┐          ├── raw/
├── wiki/                 │          ├── wiki/<topic_slug>/
│   ├── overview.md       │          │   ├── overview.md
│   ├── claims.md         │  흡수    │   ├── claims.md      ← 기존 자료 재사용
│   ├── entities.md       │ ◀────────│   ├── entities.md
│   ├── timeline.md       │          │   ├── timeline.md
│   └── images.md         │          │   └── images.md
├── manifests/            │          ├── manifests/
│   ├── claims.jsonl      │          └── topics/
│   └── sources.jsonl     │
└── claims_ledger.jsonl ──┘──────▶ vault-sync-agent (별도, manual trigger)
                                     ↓
                                   slug normalization + dedup + merge
                                     ↓
                                   볼트 갱신
```

## 4. 4단계 파이프라인 흐름

### 4-1. `step_1_fresh` — 프로젝트 로컬 우선 수집
- lane 4종 호출 (Wikipedia API, Google News RSS, Crossref, OpenLibrary)
- 결과 → `output/<proj>/research/raw/` (immutable)
- 메타 인덱스 → `output/<proj>/research/manifests/sources.jsonl`
- **검증 게이트 없음**: Tier C(블로그/카페)는 색인하되 기록만, evidence로는 채택 ❌
- 한국 RSS 데드 URL 우리 레포에서 패치 (Naver Open API 또는 카테고리 RSS 대체)

### 4-2. `step_1_vault_lookup` — 볼트에서 흡수 (NAS 단절 허용)
1. NAS 마운트 헬스 체크 (5초 timeout)
   - 실패 → 스킵, `vault_lookup_skipped: true` 메타에만 기록
2. **LLM-driven slug matcher** (haiku/sonnet, max_turns=2):
   ```
   입력:
     새 프로젝트 entity 후보: ["유한양행", "유일한", "안티푸라민"]
     볼트 토픽 리스트: ["유한양행", "유일한", "바세린", ...]
   출력:
     매칭: { "유한양행": 0.95, "유일한": 0.85 }
   ```
3. confidence ≥ 0.7 토픽 → 볼트 wiki 페이지를 프로젝트 wiki에 **append/dedup**
4. 미만 → 스킵, 새 토픽으로 진행

### 4-3. `step_2_draft` + `step_2_target` — 글 쓰면서 클레임
- `script-director`(또는 `fact-retriever` 사이드카)가 글 쓰다가 사실 필요 → 프로젝트 wiki에서 retrieve
- 부족하면 lane으로 추가 수집 (`step_2_target`) → 프로젝트 wiki에 누적
- **클레임 ledger** = `output/<proj>/research/claims_ledger.jsonl` (origin 추적: vault | local | targeted)

### 4-4. `vault-sync-agent` — 파이프라인 외부, manual trigger
- CLI: `auto-agent vault-sync --project <slug>` 또는 대시보드 버튼
- 동작:
  1. 프로젝트 wiki/, claims_ledger를 읽음
  2. **slug normalization**: 프로젝트 슬러그 → 표준 entity slug로 변환 (`유한양행_100주년_1부터_…` → `유한양행`)
  3. 볼트 기존 claim과 dedup (claim_id 기반 + entity+date 매칭)
  4. evidence가 검증된 claim만 push (Tier A/B + span 매칭)
  5. 충돌 시 사용자 confirm (덮어쓸지 / 새 run으로 추가할지)
- **NAS 단절 시 재시도 큐**: `~/.auto_agent/vault_sync_queue/`에 보관 후 재가동 시 재시도

## 5. Evidence 기준 — claim_kind 차등

| claim_kind | 필수 evidence | 비고 |
|---|---|---|
| `fact:date_or_number` | A 1건 + 인용 span | 정확성 핵심 |
| `fact:event` | A 1건 또는 B 2건 |  |
| `fact:context` | A 1건 또는 B 2건 교차 | 배경 설명 |
| `interpretation` | A 1건 + "작성자 의견" 명시 | 해석/평가 |
| `filler / transition` | 불필요 | 연결어 |

**Tier 정의**:
- **A (canonical)**: ko/en.wikipedia.org, 공식 도메인(`*.go.kr`, 회사 official), 언론 mainstream
- **B (corroborated)**: Crossref/학술, 1차 사료 PDF, 정부 발간물
- **C (excluded)**: 블로그/나무위키/카페 — 색인은 하되 evidence 채택 ❌

**Evidence span 규격**:
- 30~300자 인용 텍스트
- 필수 메타: `source_url`, `retrieved_at`, `source_id`, `paragraph_anchor`
- **fact-retriever는 인용 span이 chunk 원문에 substring으로 포함되는지 강제 검증**

## 6. 디렉토리 구조

### 프로젝트 로컬 (작업 영역)
```
output/<proj>/research/
├── raw/                       # immutable raw (lane 결과)
├── wiki/<topic_slug>/         # Obsidian-style 위키 페이지
│   ├── overview.md
│   ├── claims.md
│   ├── entities.md
│   ├── timeline.md
│   └── images.md
├── manifests/<topic_slug>/
│   ├── sources.jsonl
│   └── claims.jsonl           # source_ids 백링크 포함
├── claims_ledger.jsonl        # 글 쓰면서 누적되는 사용 클레임
└── vault_lookup.json          # 볼트 흡수 결과 메타
```

### 볼트 (canonical, sync-back 전용)
이미 운영 중인 `02-research/` 구조 그대로:
```
KAIROS_VAULT_DIR/02-research/
├── raw/<topic_slug>/<run_id>/
├── wiki/<topic_slug>/{overview,claims,entities,timeline,images,log}.md
├── manifests/<topic_slug>/
└── topics/<topic_slug>.md
```

## 7. claims.jsonl 스키마 (호환)

기존 볼트 형식과 호환:
```json
{
  "claim_id": "claim_1933-안티푸라민-출시-자체개발-1호_a1b2c3d4",
  "claim": "1933년 안티푸라민 출시 (자체개발 1호)",
  "kind": "fact:date_or_number",
  "tier": "A",
  "confidence": "high",
  "source_ids": ["src_yuhan_history_official"],
  "evidence": "1933년 12월, 자체 개발 진통소염제 안티푸라민을 출시…",
  "evidence_span": {
    "url": "https://www.yuhan.co.kr/introduce/history/",
    "retrieved_at": "2026-04-28T16:42:00Z",
    "anchor": "history-1933"
  },
  "topic": "유한양행",
  "topic_slug": "유한양행",
  "origin": "local|vault|targeted",
  "linked_pages": ["timeline"],
  "status": "active"
}
```

## 8. 마이그레이션 계획

### Phase 1 — Fresh Collector
- `auto_agent/research/lanes/` 신규 (Wikipedia/News RSS/Crossref/OpenLibrary)
- 한국 RSS URL 패치 (Naver Open API 또는 카테고리 RSS)
- `fresh_collector_module.py` — lane 호출 → `raw/` + `manifests/sources.jsonl`
- Tier A 도메인 리스트 (`auto_agent/research/trust_tiers.json`)
- 새 step `step_1_fresh` 추가, 기존 `step_1_ingest`와 **병행 검증** (영상 2~3편)

### Phase 2 — Vault Lookup
- `vault_lookup_module.py` — NAS 헬스 체크 + slug matcher (LLM, haiku)
- 볼트 wiki 페이지 흡수 로직 (append/dedup)
- 단절 허용 정책 (timeout, skip 안전)

### Phase 3 — Wiki Compiler & Fact Retriever
- `wiki_compiler_module.py` — raw + 흡수자료 → 프로젝트 `wiki/<topic>/*.md` 생성
- `fact-retriever` 에이전트 신규 (sonnet, max_turns=5) — script-director가 tool로 호출
- evidence span 검증 로직

### Phase 4 — Vault Sync Agent (파이프라인 외부)
- `vault-sync-agent` 신규 — slug normalization + dedup + merge
- CLI 명령 + 대시보드 버튼
- 재시도 큐 (`~/.auto_agent/vault_sync_queue/`)

### Phase 5 — Cutover & Cleanup
- `step_1_ingest` 폐기, `step_1_fresh` + `step_1_vault_lookup` 으로 교체
- ResearchAgent NAS 호출 코드 제거
- 옛 manifests 형식 호환 코드 정리

## 9. 결정 사항

| 항목 | 결정 |
|---|---|
| 인덱스 형식 | **markdown wiki + manifests jsonl** (frontmatter 기반). 벡터 DB는 PASS — 토픽 한 개 wiki는 ~50KB라 컨텍스트에 그냥 들어감 |
| 클레임 주체 | **fact-retriever 사이드카 에이전트** (sonnet) — script-director는 tool로 호출 |
| Evidence | claim_kind 차등 + Tier A/B + 인용 span 30~300자 필수 |
| ResearchAgent | **lane만 우리 레포로 import**, 7-stage 루프 폐기 |
| 볼트 위치 | **read-only 흡수 + write-back 분리**. NAS 단절 허용 |
| Slug 매칭 | **LLM matcher (haiku)** — entity 기반 fuzzy. 0.7 이상만 채택 |
| Vault sync 트리거 | **manual** — CLI 또는 대시보드 버튼. 자동 sync ❌ |
| step_1_fresh ↔ ingest 병행 | **영상 2~3편** 동안 둘 다 실행, raw 결과 비교 후 컷오버 |

## 10. 위험과 대응

| 위험 | 대응 |
|---|---|
| Slug 매칭 false positive (다른 토픽을 같다고 흡수) | confidence ≥ 0.7 + entity 명시적 검증 + 사용자 confirm 옵션 |
| Vault sync 동시 실행 충돌 | file-lock (`~/.auto_agent/vault_sync.lock`) |
| 동일 토픽 다중 프로젝트 진행 시 wiki drift | sync 에이전트가 last-write-wins 대신 merge 전략 |
| LLM 환각으로 evidence span fabrication | retrieved chunk 원문 vs span substring 강제 검증 |
| NAS 권한/경로 이슈 | health check + 명확한 에러 메시지 + 큐 보관 |
| 옛 프로젝트 마이그레이션 | 기존 `claims.jsonl` → 새 `claims_ledger.jsonl` 변환 스크립트 |

## 11. 미결 항목

- [ ] Tier A 도메인 초기 리스트 작성 (~15개부터, PR로 갱신)
- [ ] fact-retriever와 script-director의 호출 인터페이스 (tool name, schema)
- [ ] vault-sync-agent의 충돌 해결 UX (대시보드 diff 뷰?)
- [ ] 한국 RSS 대체 URL 결정 (Naver Open API 키 필요 여부)
- [ ] LLM slug matcher의 입력 토큰 제한 (볼트 토픽 리스트가 커지면 어떻게 슬라이스?)

---

**작성 후 결정 흐름**: Phase 1 구현 plan을 별도 파일로 작성 → `docs/superpowers/plans/2026-04-28-fresh-collector-phase1.md`
