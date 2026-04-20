---
name: search-tools
description: 리서치 에이전트용 검색 도구 사용 규칙 — lane/rss/api 우선, WebSearch는 fallback
---

# 검색 도구 사용 규칙

## 우선순위 (토큰 절약)

```
1순위: mcp__lane__wikipedia_search — 주제 개요, 역사, 인물 정보
2순위: mcp__lane__news_search      — 최신 뉴스, 시장 동향
3순위: mcp__lane__academic_search  — 학술 논문, 통계 출처
4순위: WebSearch                   — 위 도구로 커버 안 되는 경우만
5순위: WebFetch                    — 특정 URL 본문이 필요할 때만
```

**이유**: lane 도구는 LLM 검색 토큰 없이 구조화된 데이터를 바로 반환합니다. WebSearch는 LLM이 직접 쿼리를 소비하므로 꼭 필요한 경우만 사용하세요.

---

## 도구별 사용법

### 1. Wikipedia Lane

```bash
python3 -m auto_agent.tools.wikipedia_lane "쿼리" --limit 5 --content
```

- `--content`: 본문 전문 포함 (개요·역사 조사 시 필수)
- `--limit`: 결과 수 (기본 5)
- 언제: 주제의 배경, 역사, 핵심 인물 파악 시 **항상 먼저**

### 2. 뉴스 RSS Lane

```bash
# 쿼리를 반드시 3종으로 분해하여 각각 호출
python3 -m auto_agent.tools.news_rss_lane "고유명사(브랜드/인물)" --limit 10 --ko-only
python3 -m auto_agent.tools.news_rss_lane "시장/카테고리 키워드" --limit 10 --ko-only
python3 -m auto_agent.tools.news_rss_lane "EnglishKeyword" --limit 10 --en-only
```

- **쿼리 분해 필수**: "자동차의 역사" 전체를 쿼리로 쓰면 결과가 거의 없음
  - ❌ `"자동차의 역사"` → ✅ `"자동차"`, `"현대자동차 시장"`, `"automobile history"`
- `confidence: blocked` 항목 제외 (유튜브, 블로그, SNS 등)
- 동일 이벤트 유사 기사는 1건만 유지 (중복 제거)
- 뉴스 소스 총 **15건 이하**만 사용 (컨텍스트 과적재 방지)

### 3. CrossRef Lane (학술)

```bash
python3 -m auto_agent.tools.crossref_lane "query" --limit 5
python3 -m auto_agent.tools.crossref_lane "query" --books-only   # 도서만
python3 -m auto_agent.tools.crossref_lane "query" --papers-only  # 논문만
```

- 언제: 통계 수치, 연구 결과, 역사적 사실의 출처가 필요할 때

### 4. WebSearch (fallback)

위 세 도구로 커버되지 않는 정보에만 사용:
- 특정 사건의 날짜/수치 검증
- 최신 정보 (lane 뉴스 범위 초과)
- 공식 보도자료, 정부 발표

### 5. WebFetch (fallback)

WebSearch 결과에서 특정 URL의 본문이 필요할 때만 사용.

---

## 수집 상한선

| 소스 유형 | 최대 건수 |
|-----------|----------|
| Wikipedia 섹션 | 1~3개 |
| 뉴스 기사 | 15건 |
| 학술 자료 | 5건 |
| WebSearch 결과 | 10건 |

컨텍스트 과적재 방지를 위해 상한선을 초과하지 마세요.
