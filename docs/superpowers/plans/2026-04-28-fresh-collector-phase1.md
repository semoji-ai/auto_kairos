# Phase 1 — Fresh Collector 구현 계획

작성일: 2026-04-28
연관 spec: `docs/superpowers/specs/2026-04-28-research-redesign.md`
브랜치: `feature/live-doc-snapshot` (또는 분리 검토)

---

## 목표

기존 `step_1_ingest`(ResearchAgent + 7-stage 게이트)의 대안으로, **검증 게이트 없는 가벼운 lane 호출 모듈**을 구현합니다. 이 단계는 raw 수집 + 메타 인덱싱까지만. 클레임화/검증은 후속 단계가 담당.

성공 기준:
- 한국어/영어 토픽 모두 lane 호출 성공 (Wikipedia/Google News/Crossref/OpenLibrary)
- 한국 뉴스 RSS URL 데드 문제 해소
- `output/<proj>/research/raw/` + `manifests/sources.jsonl` 생성
- 기존 `step_1_ingest`와 **병행 실행** 가능 (둘 다 유지, 비교 검증)
- 영상 2~3편 검증 후 컷오버 결정

## 산출물

```
auto_agent/research/
├── __init__.py
├── trust_tiers.json              # 도메인 신뢰도 화이트리스트 (Phase 2)
└── lanes/
    ├── __init__.py
    ├── wikipedia.py              # ko/en wiki API
    ├── news_rss.py               # Google News + 한국 뉴스
    ├── crossref.py               # 학술 (api.crossref.org)
    └── openlibrary.py            # 도서 (Open Library + Google Books)

auto_agent/modules/
└── fresh_collector_module.py     # lane 호출 + raw 저장 + 메타 인덱싱

auto_agent/data/
├── agents.json                   # step_1_fresh 등록
└── pipeline.json                 # phase 추가

tests/
├── test_lanes_wikipedia.py
├── test_lanes_news_rss.py
├── test_lanes_crossref.py
├── test_lanes_openlibrary.py
└── test_fresh_collector.py
```

## 단계별 실행 순서

### Step 1.1 — Lane 인프라 import
- NAS의 `/Volumes/jleavens/Projects/ResearchAgent/scripts/research_lane_tools.py`에서 함수 분리:
  - `search_wikipedia`, `fetch_wikipedia_article_content` → `lanes/wikipedia.py`
  - `search_google_news_rss`, `search_korean_news_rss`, `search_news` → `lanes/news_rss.py`
  - `search_crossref` → `lanes/crossref.py`
  - `search_openlibrary` → `lanes/openlibrary.py`
- 공통 헬퍼(`fetch_json`, `fetch_text`, `news_confidence`, `extract_domain`) → 각 lane에 인라인 또는 `lanes/_http.py`로 분리
- **NAS 의존성 제거** — 우리 레포에서만 import 가능하게

### Step 1.2 — 한국 뉴스 RSS 패치
현재 데드 URL:
- Naver: `news.naver.com/rss/search.naver?query=...` → **404**
- 연합: `yna.co.kr/rss/search.nhn?query=...` → **400**

대체 방안 (우선순위):
1. **Naver Open API** (`openapi.naver.com/v1/search/news.json`) — Client ID 필요
2. **Daum 뉴스 검색** (`search.daum.net`) — 검색 RSS 없으니 HTML 스크레이핑 (라이선스 주의)
3. **카테고리 RSS만 살리기** — 검색 없이 분야별(`yna.co.kr/rss/news.xml`)만 → 토픽 매칭 약함

→ **추천**: Naver Open API + Google News RSS 조합. Naver 키 없으면 Google News만.

`.env.example`에 추가:
```
NAVER_API_CLIENT_ID=
NAVER_API_CLIENT_SECRET=
```

### Step 1.3 — `fresh_collector_module.py` 신규
입력:
- `topic_slug`, `query`, `entities[]`, `language` (ko/en/auto)
- `output_dir` (`output/<proj>/research/`)

동작:
1. lane 4종 병렬 호출 (asyncio 또는 ThreadPoolExecutor)
2. 결과 normalize → 공통 스키마:
   ```json
   {
     "source_id": "...",
     "title": "...",
     "url": "...",
     "publisher": "...",
     "published_at": "...",
     "retrieved_at": "...",
     "source_type": "wikipedia|news|academic|book",
     "lane": "wikipedia|news_rss|crossref|openlibrary",
     "domain": "...",
     "tier_hint": "A|B|C",
     "summary": "...",
     "raw_path": "raw/<topic>/<run>/source_notes/<source_id>.md"
   }
   ```
3. raw markdown 작성 (`raw/<topic>/<run>/source_notes/*.md`)
4. `manifests/<topic>/sources.jsonl` 추가 (append)
5. 종료 시 `manifests/<topic>/runs.jsonl`에 run 메타 기록

**검증 게이트 없음**: 결과는 모두 기록. tier_hint만 도메인 룩업으로 표시.

### Step 1.4 — pipeline 등록
`pipeline.json`에 새 step 추가:
```json
{
  "id": "step_1_fresh",
  "phase": "stage_1",
  "module": "fresh_collector",
  "blocking": false,
  "parallel_with": ["step_1_ingest"]
}
```

→ 기존 `step_1_ingest`와 **동시 실행**. 결과는 같은 `manifests/`에 다른 lane 태그로 누적.

### Step 1.5 — Tier A 도메인 화이트리스트 초안
`auto_agent/research/trust_tiers.json` 생성. 별도 도큐먼트 참조.

### Step 1.6 — 테스트
- 각 lane 단위 테스트: mock HTTP fixture
- 통합: 실제 네트워크로 "유한양행" / "vaseline" / "Apollo program" 쿼리 → 결과 ≥ 5개 검증

### Step 1.7 — 병행 실행 + 비교
- 영상 2~3편을 `step_1_fresh` + 기존 `step_1_ingest` 동시 실행
- 비교 항목:
  - sources 수 (lane별 분포)
  - tier_hint 분포
  - 한국어 토픽 vs 영어 토픽 회수율
  - 실행 시간
- 결과가 더 풍부하면 Phase 2 진행. 부족하면 lane 추가/조정.

## 의존성 / 환경변수

| 항목 | 필수 | 비고 |
|---|---|---|
| `NAVER_API_CLIENT_ID/SECRET` | 선택 | 없으면 Naver lane 스킵 |
| 인터넷 연결 | 필수 | lane 전부 외부 호출 |
| Python 표준 라이브러리 | 필수 | urllib만 사용. requests/httpx 의존 X |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| Naver Open API 일일 쿼터 | 호출 카운트 + 한도 도달 시 Google News로 fallback |
| Wikipedia API 레이트리밋 | UA 명시 + 재시도 backoff |
| 한국어 검색 결과 빈약 | tier_hint=B 학술 + 1차 사료 PDF 추가 검색 |
| 병행 실행 시 manifests 충돌 | lane 이름 prefix로 source_id 분리 (`fresh_*`, `ingest_*`) |
| ResearchAgent 호환성 깨짐 | 기존 step_1_ingest 그대로 유지, 동시에 step_1_fresh 추가 |

## 작업 시간 추정

| Step | 시간 |
|---|---|
| 1.1 lane import | 1.5h |
| 1.2 한국 RSS 패치 | 1h |
| 1.3 fresh_collector | 1.5h |
| 1.4 pipeline 등록 | 0.5h |
| 1.5 trust_tiers.json | 0.5h |
| 1.6 테스트 | 1h |
| 1.7 병행 실행 검증 | (별도, 1주일 누적) |
| **합계 (코딩)** | **~6h** |

## 다음 Phase 미리 보기

- **Phase 2**: `vault_lookup_module.py` (NAS 연결 + LLM slug matcher)
- **Phase 3**: `wiki_compiler_module.py` + `fact-retriever` 에이전트
- **Phase 4**: `vault-sync-agent` (manual trigger)
- **Phase 5**: cutover & cleanup
