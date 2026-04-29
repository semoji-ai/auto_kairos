# Phase 5 — Cutover & Cleanup 구현 계획

작성일: 2026-04-29
연관 spec: `docs/superpowers/specs/2026-04-28-research-redesign.md` (Phase 5)

---

## 목표

옛 ResearchAgent 7-stage 경로 폐기, 새 경로(fresh + vault_lookup + wiki_compile + vault_sync)로 컷오버.
공식적으로 새 흐름만 stage_1으로 두고, 옛 코드 제거.

성공 기준:
- `step_1_ingest`가 pipeline.json에 없음 (optional 모드로만 유지하거나 완전 제거)
- `auto_agent/tools/{wikipedia,news_rss,crossref}_lane.py` 옛 복사본이 `auto_agent/research/lanes/`로 redirect
- 새 영상(예: 다이소 1분 또는 KFC 3분) 만들 때 옛 모듈 호출 0건
- 옛 프로젝트 backwards compat 유지 (claims.jsonl 형식 같이 읽음)

## 단계별 실행 순서

### Step 5.1 — pipeline.json에서 step_1_ingest 옵션화
- `step_1_ingest` 항목에 `disabled: true` 또는 `legacy: true` 표시
- 또는 별도 옵트인 환경변수(`ENABLE_LEGACY_INGEST=1`)로만 실행
- runner.py에서 disabled step skip 로직 추가
- 검증: 펩시 또는 새 영상에서 step_1_ingest 호출 안 일어나는지

### Step 5.2 — `auto_agent/tools/*_lane.py` 옛 복사본 정리
**옵션 A (안전)**: thin re-export로 남기고 deprecation warning
```python
# auto_agent/tools/wikipedia_lane.py
import warnings
warnings.warn("auto_agent.tools.wikipedia_lane is deprecated. Use auto_agent.research.lanes.wikipedia", DeprecationWarning)
from auto_agent.research.lanes.wikipedia import search_wikipedia, fetch_wikipedia_article_content as fetch_article_content
```

**옵션 B (과감)**: 파일 삭제 + 호출 코드 마이그레이션
- `skeleton_from_vault_module.py`의 import 경로 변경
- 파일 4개 삭제 (`wikipedia_lane.py` 등)
- 다른 사용처 grep으로 추적

→ 추천: **A** (안전, 옛 코드 깨질 위험 ↓). B는 다음 정리 작업으로.

### Step 5.3 — 옛 프로젝트 마이그레이션 스크립트
- `scripts/migrate_research_v3_to_v4.py`
- 입력: 옛 프로젝트의 `manifests/<topic>/claims.jsonl` (ResearchAgent 형식)
- 출력: 새 형식으로 변환 (필요 시 evidence span 빈 채로 두되 source_id 유지)
- dry-run 옵션 + 검증 모드

### Step 5.4 — 문서 정리
- CLAUDE.md 업데이트:
  - 스텝 ID 표 (step_1_ingest 제거, step_1_fresh / vault_lookup / wiki_compile 추가)
  - 에이전트 목록에 fact-retriever 추가
  - 볼트 정책 링크
- `02-research/llm-wiki-research-policy.md`에 vault-sync-agent 흐름 추가
  → 이건 별도 PR (NAS 직접 수정이라 신중)

### Step 5.5 — 검증
- 새 프로젝트(예: "다이소 1분") 한 편을 만들면서:
  - step_1_ingest 호출 없음 확인 (logs grep)
  - fresh + vault_lookup + wiki_compile 정상 작동
  - vault-sync 실 실행 (dry-run → real)
- 옛 프로젝트(유한양행 또는 펩시) resume:
  - 호환성 유지 확인 (옛 claims.jsonl 읽기)

## 작업 시간 추정

| Step | 시간 |
|---|---|
| 5.1 step_1_ingest 옵션화 | 0.5h |
| 5.2 lane re-export | 0.5h |
| 5.3 마이그레이션 스크립트 | 1h |
| 5.4 CLAUDE.md 정리 | 0.5h |
| 5.5 검증 | 1h |
| **합계** | **~3.5h** |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 옛 모듈 다른 곳에서 import (놓친 것) | grep으로 dependency 그래프 확인 후 정리 |
| 옛 프로젝트 resume 깨짐 | claims.jsonl 양쪽 형식 호환 read 유지 |
| 사용자가 옛 동작 원할 때 | `ENABLE_LEGACY_INGEST=1` 환경변수로 옵트인 |
| 마이그레이션 실수로 데이터 손실 | dry-run + 백업 강제 |
