# adobe 독립 Stage 1-2 — P1: 결정적 리서치 기반 — 설계

작성일: 2026-06-16
상태: 승인됨 (구현 계획 대기)

## 큰 그림 (이 P1이 속한 전체 목표)

auto_kairos_adobe를 **독립적으로** v3 수준의 기획·리서치·원고까지 수행하게 만든다(이후 기존 Stage 3 제작·편집으로 이어짐). 전략은 **하이브리드**: v3에서 품질을 만드는 stdlib 코드·프롬프트는 이식, 거대 러너(5,714줄)·Claude `Task` fan-out은 adobe식(jobs 병렬)으로 재구현.

지켜야 할 전체 흐름(목표):
> 기획 → **브리프 평가·개선 래칫(점수 게이트)** → 리서치 → 원고 초안 → 타겟 쿼리 추출 → 타겟 리서치 → 타겟 적용 원고 → **원고 평가·개선 래칫(점수 게이트)** → 씬 분석

분해(빌드 순서):
- **P1 — 결정적 리서치 기반**(이 문서): 리서치 레인 4종 + 수집기 이식.
- P2 — editorial brief + 평가·개선 래칫.
- P3 — 리서치 오케스트레이션(브리프→쿼리→레인 병렬 + 선택 LLM 웹리서치 + 머지).
- P4 — 다단계 원고(초안→타겟쿼리→타겟리서치→적용→래칫) + 씬 분석.
- P5 — 패널·파이프라인 통합·Stage3 핸드오프.

## P1 범위 / 목표

**결정적(LLM 없는) 리서치 수집 토대**를 adobe에 이식한다. 쿼리 리스트를 받으면 4개 외부 데이터 레인(위키·뉴스·CrossRef·OpenLibrary)을 병렬 호출해 정규화·신뢰도 표시 후 소스노트·매니페스트로 적재한다. 상위 단계(P3 리서치, P4 타겟 리서치)가 이 위에 얹힌다.

**P1이 하지 않는 것(YAGNI):** 쿼리 생성/LLM, editorial brief, 오케스트레이션, 원고. 입력은 이미 만들어진 쿼리 리스트.

## 출처 (v3 이식 원본)

`/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/research/`:
- `lanes/_http.py`(urllib), `lanes/_text.py`, `lanes/_trust.py` + `trust_tiers.json`
- `lanes/wikipedia.py`, `lanes/news_rss.py`, `lanes/crossref.py`, `lanes/openlibrary.py`
- `modules/fresh_collector_module.py`(수집 오케스트레이션·정규화·적재)

모두 **순수 stdlib**(urllib·xml.etree·concurrent.futures·hashlib·json·functools). 서드파티 0.

## 아키텍처

### 모듈 레이아웃
```
backend/research/
  __init__.py
  lanes/
    __init__.py        # search_wikipedia/news/crossref/openlibrary 재노출
    _http.py           # fetch_json/fetch_text (urllib, User-Agent, timeout)
    _text.py           # contains_korean, extract_domain, clean_html_fragment 등
    _trust.py          # classify_tier / is_evidence_eligible (trust_tiers.json 룩업)
    trust_tiers.json   # A/B/C tier 도메인 데이터 (v3에서 복사)
    wikipedia.py  news_rss.py  crossref.py  openlibrary.py
  collector.py         # collect_lanes_parallel + collect_queries (적재)
```

### 단위별 책임·인터페이스
| 단위 | 책임 | 인터페이스 |
|---|---|---|
| `lanes/_http.py` | urllib HTTP | `fetch_json(url,*,timeout,headers)`, `fetch_text(...)` |
| `lanes/_text.py` | 텍스트 유틸 | `contains_korean`, `extract_domain`, `clean_html_fragment`, `title_similar`, `split_google_news_title` |
| `lanes/_trust.py` | 도메인 신뢰 tier | `classify_tier(url)->'A'|'B'|'C'|'unknown'`, `is_evidence_eligible(url)->bool` |
| `lanes/<lane>.py` | 단일 소스 검색 | `search_X(query,*,limit=8,fetch_json_impl=None,fetch_text_impl=None)->list[dict]` |
| `collector.py` | 병렬 수집·정규화·적재 | `collect_lanes_parallel(query,*,limit_per_lane=8)->{lane:[items]}` / `collect_queries(proj_dir,queries,*,on_event=None)->dict` |

### 정규화 소스 스키마 (레인 반환 dict)
`{title, url, lang, snippet, publisher, kind, lane, tier_hint}` — v3와 동일. 실패 시 `{error, lane, query}`.

### 데이터 흐름
```
queries: [str | {query, lang?}]
   │  collect_queries(proj_dir, queries, on_event)
   ▼  각 query마다:
collect_lanes_parallel(query)  ── ThreadPoolExecutor ──► wikipedia/news/crossref/openlibrary 동시
   │  정규화(_normalize_source) + tier 표시(_trust)
   ▼
research/raw/<topic>/<run_id>/source_notes/<src_id>.md   (frontmatter: title/url/publisher/tier/lane/lang/snippet)
research/manifests/<topic>/sources.jsonl                 (소스 1건/라인)
research/manifests/<topic>/runs.jsonl                    (실행 1건/라인)
반환: {"sources": n, "lanes_ok": [...], "lanes_err": [...], "manifest": "<sources.jsonl 경로>"}
```

## v3 → adobe 적응 (변경점)

1. import 경로 `auto_agent.research.*` → `backend.research.*`.
2. **전역 의존 제거**:
   - `PROGRESS_FILE` env 기반 진행 로그 → adobe **`on_event(msg)` 콜백**(jobs/SSE에 연결). env 폴백 제거.
   - `PROJECT_DIR` env → **`proj_dir: Path` 인자**로 명시 전달.
3. **출력 위치**를 adobe 프로젝트 규약에 맞춤: `proj_dir/research/...`. 소스노트·매니페스트 **포맷은 v3와 동일**(상위 단계 호환).
4. `collector.py`의 brief 파싱·토픽 추출(`_read_brief`, `_extract_topics_from_brief`)·query_planner 호출은 **이식 제외**(P3 영역). P1 수집기는 **쿼리 리스트를 직접 입력**으로 받는다.
5. `trust_tiers.json`은 v3 파일을 그대로 복사. `_trust.py`의 경로는 `backend/research/lanes/trust_tiers.json` 기준으로 조정.
6. Jina Reader 본문 수집(`include_content`)은 기본 off(스니펫만) — 외부 의존 최소화. 인터페이스는 유지(후속 옵트인).

## 에러 처리

- 레인 호출 실패 → 해당 레인 결과를 `[{error,...}]`로 기록하고 **다른 레인은 계속**(부분 실패 허용).
- HTTP 타임아웃/네트워크 오류 → 레인 내부에서 잡아 error 엔트리.
- 빈 쿼리/중복 url → 스킵(`seen` 셋).
- 적재 I/O 실패 → 해당 소스만 건너뛰고 진행(전체 중단 금지).

## 테스트 전략 (stdlib·monkeypatch, 외부 HTTP 0)

1. **레인 단위**(4종): `fetch_json_impl`/`fetch_text_impl`에 고정 API 응답 주입 → 정규화 dict 필드·중복제거·언어순서·tier_hint 검증.
2. **레인 에러**: fetcher가 예외 → `{error,...}` 엔트리 반환 검증.
3. **trust tier**: `classify_tier`가 A/B/C/unknown을 도메인 패턴(`*.go.kr` 등)대로 분류.
4. **collect_lanes_parallel**: 레인 함수 monkeypatch → 4레인 dict 집계, 1개 실패해도 나머지 반환.
5. **collect_queries**: 레인 monkeypatch + tmp proj_dir → 소스노트 파일·sources.jsonl·runs.jsonl 적재, 반환 카운트, `on_event` 호출 검증.
6. **stdlib 전용 확인**: 모듈 import 시 서드파티 없음(메인 env에서 import 성공).

## 범위 밖 (P2~P5)

- 쿼리 생성·editorial brief·평가 래칫(P2)
- 리서치 오케스트레이션·LLM 웹리서치 fan-out·머지 research_report(P3)
- 원고·타겟 리서치·씬 분석(P4)
- 패널/파이프라인 통합(P5)
