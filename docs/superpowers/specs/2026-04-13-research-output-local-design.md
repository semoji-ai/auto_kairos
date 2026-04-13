# Research Output-Local Storage 설계

**날짜:** 2026-04-13
**배경:** ResearchAgent raw path를 entity_slug 기반으로 마이그레이션하는 과정에서 볼트 write/read 간 slug 미스매치 오류가 반복됨. 파이프라인 실행 중 볼트를 직접 write 대상으로 쓰는 구조 자체가 복잡도의 원인.

---

## 목표

- 파이프라인 실행 중 리서치 데이터를 `output/<uuid>/research/`에 로컬 저장
- 볼트는 seed 제공(읽기)과 완성본 보관(쓰기)으로만 사용
- slug 라우팅 복잡도 제거

---

## 데이터 흐름

```
[step_1_ingest 시작 — seed copy]
볼트/02-research/wiki/<slug>/       → output/<uuid>/research/wiki/<slug>/
볼트/02-research/manifests/<slug>/  → output/<uuid>/research/manifests/<slug>/
볼트/02-research/raw/               → 복사 안 함

[ResearchAgent 실행]
research_root = output/<uuid>/research/
→ raw/<slug>/<run_id>/    신규 생성
→ wiki/<slug>/            추가/갱신
→ manifests/<slug>/       claims/sources 추가

[step_1a, step_1b]
source_ingest_status.json.research_root = output/<uuid>/research/
→ skeleton_from_vault_module, chapter_projection_module 자동으로 output 폴더 읽기

[step_2_vault_sync — step_2_review 직후]
output/<uuid>/research/wiki/        → 볼트/02-research/wiki/       (merge)
output/<uuid>/research/manifests/   → 볼트/02-research/manifests/  (merge)
raw는 sync 제외 (크기)
```

---

## 변경 컴포넌트

### `source_ingest_module.py`

- `_get_research_root()` → `project_dir / "research"` 반환 (볼트 참조 제거)
- `_seed_from_vault()` 추가 — step_1_ingest 시작 시 볼트 wiki/manifests → output/research 복사
  - 볼트 마운트 안 됐거나 해당 slug 없으면 경고만 출력하고 빈 폴더로 계속 진행
- skip 로직 제거 (`_topic_wiki_usable`, `_section_wiki_usable` 호출 제거)
- entity-slug 경로 탐색 복잡도 코드 제거
- `source_ingest_status.json.research_root` = output/research 경로

### `vault_sync_module.py` (신규)

- `output/<uuid>/research/wiki/` → 볼트 wiki/ merge (파일 단위 덮어쓰기)
- `output/<uuid>/research/manifests/` → 볼트 manifests/ merge
- raw 제외
- 볼트 마운트 실패 시 경고만, 파이프라인 중단 없음

### `pipeline.json`

```json
{
  "id": "step_2_vault_sync",
  "name": "vault_sync",
  "phase": "원고",
  "after": "step_2_review"
}
```

### `research_launcher.py` / `research_vault.py`

- 이번 마이그레이션에서 추가한 entity-slug 전달 코드 롤백
- `_existing_run_dir()` 유지 — output 폴더 내에서는 slug 변형 탐색이 단순하게 동작

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| seed copy 시 볼트 마운트 안 됨 | 경고 로그, 빈 research 폴더로 계속 진행 |
| seed copy 시 해당 slug 없음 | 경고 로그, 빈 폴더로 계속 진행 |
| vault sync 실패 | 경고 로그, 파이프라인 중단 없음 |
| output/research 폴더 없음 | 자동 생성 |

---

## 테스트

- `test_source_ingest_module.py` — `_seed_from_vault()` 볼트 없을 때 graceful skip
- `test_vault_sync_module.py` (신규) — wiki/manifests merge, raw 제외
- 기존 entity-slug 탐색 테스트 → 단순화 버전으로 교체

---

## 제거되는 것

- `source_ingest_module.py` entity-slug 경로 변형 탐색 로직
- `source_ingest_module.py` skip 로직 (`_topic_wiki_usable`, `_section_wiki_usable`)
- `research_launcher.py` ingest-bundle/finalize-session의 `--entity-slug` 전달 코드 (이번 마이그레이션 추가분)
