# v4 Dashboard Compatibility — Design

**날짜:** 2026-05-09
**브랜치:** `v4-dashboard-compat` (워크트리)
**목표:** v3 대시보드가 v4 PD 워크플로 산출물(plan, pd_notebook, wiki, drafts, research_reports, research_targeted, review-draft, final_manuscript)을 *같은 페이지에서* 추가로 표시하도록 확장. v3 단일 흐름 프로젝트는 기존 그대로 작동(graceful degradation).

---

## 1. 범위

### Phase 1 (이번 워크트리)
- **리서치 탭 확장** — v3 `research_report.json`(기존) + v4 `research_reports/*.md`, `research_targeted/*.md` 목록·본문 뷰어 + `plan.md` 미니뷰
- **원고 탭 확장** — v3 `scene_specs.json`(기존) + v4 `drafts/v{n}.md` 버전 셀렉터 + review-draft 점수 추이 그래프 + `final_manuscript.md`

### Phase 2 (이후 별도 워크트리)
- **PD 노트 신규 탭** — `pd_notebook.md` (워크플로 플랜·게이트·결정 로그) + 챕터맵 + 5챕터 분량 비율 차트

### 범위 외
- v4 산출물 *편집* (대시보드는 읽기 전용). 편집은 텍스트 에디터 또는 Claude Code에서.
- Stage 3 탭(스토리보드/스튜디오/Upload/썸네일/Multi/Agent) — 변경 없음. 어댑터 통과 후 v3 산출물이 채워지면 그대로 작동.

---

## 2. Graceful Degradation 원칙

모든 v4 섹션은 *조건부 노출*:
- 백엔드: `Path.exists()` 체크로 v4 파일 유무 확인
- 템플릿: `{% if v4_artifacts %} ... {% endif %}` 블록으로 감쌈
- v3-only 프로젝트(기존 130여 개): v4 섹션 자체를 안 보여 → UI 변경 0
- v4 PD 진행 프로젝트: v3 영역 + v4 섹션 동시 표시

---

## 3. 데이터 흐름

```
auto-agent dashboard (uvicorn app.py)
    │
    ├── Route: /project/{slug}?tab=research
    │       │
    │       ├── helpers.load_research_v3(project_dir) → research_report.json (기존)
    │       └── helpers.load_research_v4(project_dir) → {
    │              "plan_md": <text>,                    # plan.md 본문
    │              "fresh_reports": [{slug, kind, content}],
    │              "targeted": [{slug, content}],
    │           }
    │       → _research.html 렌더 (v3 섹션 + v4 조건부 섹션)
    │
    └── Route: /project/{slug}?tab=manuscript
            │
            ├── helpers.load_manuscript_v3(project_dir) → scene_specs.json (기존)
            └── helpers.load_manuscript_v4(project_dir) → {
                   "drafts": [{version, content, frontmatter}],   # drafts/v{n}.md 모두
                   "review_scores": [{version, viewer, expert}],  # review/review-draft-v{n}-*.md
                   "final_manuscript": <text>,
                   "final_marked": <text>,                        # final_manuscript_marked.md
                }
            → _manuscript.html 렌더
```

---

## 4. UI 명세

### 4.1 리서치 탭 (`_research.html` 확장)

기존 v3 영역 그대로 유지. 그 아래 신규 v4 섹션 추가:

```
┌─ Research [기존 v3] ───────────────────┐
│  research_report.json …                │
│  source_grades, sources, claims …      │
└────────────────────────────────────────┘

[v4 PD 워크플로 섹션 — 조건부]

┌─ 기획안 plan.md ─────────────────────────┐
│  핵심 질문 / 챕터 가설 / 회피 방향        │
│  (마크다운 렌더, 약 200~300px 미니뷰)     │
└────────────────────────────────────────┘

┌─ Fresh + Deep Research ────────────────┐
│  좌측: 보고서 목록 (slug, kind, 작성일)  │
│  우측: 선택된 보고서 본문 (마크다운)      │
└────────────────────────────────────────┘

┌─ Targeted Research ────────────────────┐
│  좌측: 질문 목록 (slug, source: existing/new)│
│  우측: 선택된 답변 본문                   │
└────────────────────────────────────────┘
```

### 4.2 원고 탭 (`_manuscript.html` 확장)

```
┌─ Scene Specs [기존 v3] ────────────────┐
│  scene_specs.json 씬별 카드 …           │
└────────────────────────────────────────┘

[v4 PD 워크플로 섹션 — 조건부]

┌─ Review-draft 점수 추이 ──────────────┐
│  꺾은선 그래프: 시청자 점수 v{n}         │
│  바 그래프: 전문가 verdict v{n}         │
│  목표선: 9.0 (시청자), PASS (전문가)     │
└────────────────────────────────────────┘

┌─ Drafts ───────────────────────────────┐
│  버전 셀렉터: v1 / v2 / v3 / ... / vN   │
│  선택 버전 본문 (마크다운 + 출처 인라인) │
│  (기본: 가장 최신 버전)                  │
└────────────────────────────────────────┘

┌─ Final Manuscript ─────────────────────┐
│  탭 토글: prose / marked                │
│  prose: final_manuscript.md             │
│  marked: final_manuscript_marked.md (Ch 마커 + --- 표시) │
└────────────────────────────────────────┘
```

### 4.3 PD 노트 탭 (Phase 2)

```
┌─ pd_notebook.md ───────────────────────┐
│  워크플로 플랜 / 게이트 / 결정 로그 / 미해결 │
└────────────────────────────────────────┘

┌─ 챕터맵 ───────────────────────────────┐
│  chapter_map_v{n}.md 본문                │
│  + 5챕터 막 비율 도넛 차트              │
│  + 챕터별 와-모먼트 한 줄                │
└────────────────────────────────────────┘
```

---

## 5. 백엔드 변경

### 5.1 신규 함수 (`auto_agent/dashboard/helpers.py`)

```python
def load_research_v4(project_dir: Path) -> dict:
    """v4 PD 워크플로 리서치 산출물 로드. 누락 키는 빈 값."""
    return {
        "plan_md": _read_or_empty(project_dir / "plan.md"),
        "fresh_reports": _list_md_files(project_dir / "research_reports"),
        "targeted": _list_md_files(project_dir / "research_targeted"),
    }

def load_manuscript_v4(project_dir: Path) -> dict:
    """v4 원고 산출물 로드."""
    return {
        "drafts": _list_drafts(project_dir / "drafts"),  # v{n}.md sorted by version
        "review_scores": _parse_review_scores(project_dir / "review"),
        "final_manuscript": _read_or_empty(project_dir / "final_manuscript.md"),
        "final_marked": _read_or_empty(project_dir / "final_manuscript_marked.md"),
    }

def _list_md_files(d: Path) -> list[dict]:
    """디렉토리 내 .md 파일을 frontmatter 포함하여 반환."""
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.md")):
        text = f.read_text()
        out.append({
            "slug": f.stem,
            "frontmatter": _parse_frontmatter(text),
            "content": _strip_frontmatter(text),
        })
    return out

def _list_drafts(d: Path) -> list[dict]:
    """drafts/v{n}.md 파일을 버전 순 정렬."""
    if not d.exists():
        return []
    drafts = []
    import re
    for f in d.glob("v*.md"):
        m = re.match(r"v(\d+)\.md", f.name)
        if m:
            text = f.read_text()
            drafts.append({
                "version": int(m.group(1)),
                "frontmatter": _parse_frontmatter(text),
                "content": _strip_frontmatter(text),
            })
    drafts.sort(key=lambda d: d["version"])
    return drafts

def _parse_review_scores(review_dir: Path) -> list[dict]:
    """review/review-draft-v{n}-*.md 의 frontmatter에서 점수 추출."""
    if not review_dir.exists():
        return []
    scores = []
    import re
    for f in sorted(review_dir.glob("review-draft-v*.md")):
        m = re.match(r"review-draft-v(\d+)-", f.name)
        if not m:
            continue
        fm = _parse_frontmatter(f.read_text())
        scores.append({
            "version": int(m.group(1)),
            "viewer_score": fm.get("viewer_score"),
            "expert_verdict": fm.get("expert_verdict"),
        })
    return scores

def _parse_frontmatter(text: str) -> dict:
    """단순 YAML frontmatter 파싱 (--- ... --- 블록)."""
    import re, yaml
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}

def _strip_frontmatter(text: str) -> str:
    import re
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)

def _read_or_empty(p: Path) -> str:
    return p.read_text() if p.exists() else ""
```

### 5.2 라우트 변경 (`app.py`)

기존 프로젝트 페이지 라우트 핸들러에 v4 컨텍스트 주입:

```python
# 기존
@app.get("/project/{slug}")
async def project_page(slug: str, tab: str = "pipeline"):
    project_dir = resolve_project(slug)
    context = {
        "project": project_meta(project_dir),
        "tab": tab,
        # 기존 v3 컨텍스트 …
    }
    return render("project.html", context)

# v4 확장
    if tab == "research":
        context["v4_research"] = load_research_v4(project_dir)
    elif tab == "manuscript":
        context["v4_manuscript"] = load_manuscript_v4(project_dir)
    # Phase 2: tab == "pd_notebook" 분기
    return render("project.html", context)
```

`v4_research` / `v4_manuscript`가 빈 dict이거나 키 모두 비어 있으면 템플릿이 자동으로 v4 섹션 안 보임.

---

## 6. 템플릿 변경

### 6.1 `partials/_research.html` 확장

기존 본문 끝에 추가:

```jinja2
{# v4 PD 워크플로 섹션 — 조건부 #}
{% if v4_research and (v4_research.plan_md or v4_research.fresh_reports or v4_research.targeted) %}
<section class="v4-section" id="v4-research">
  <h2 class="v4-section-title">PD 워크플로 (v4)</h2>

  {% if v4_research.plan_md %}
  <div class="v4-card">
    <h3>기획안 (plan.md)</h3>
    <div class="markdown-body">{{ v4_research.plan_md | markdown }}</div>
  </div>
  {% endif %}

  {% if v4_research.fresh_reports %}
  <div class="v4-card">
    <h3>Fresh + Deep Research ({{ v4_research.fresh_reports | length }})</h3>
    <div class="v4-split">
      <ul class="v4-list">
        {% for r in v4_research.fresh_reports %}
          <li data-target="fresh-{{ loop.index0 }}">
            <span class="kind-badge {{ r.frontmatter.kind }}">{{ r.frontmatter.kind }}</span>
            {{ r.slug }}
          </li>
        {% endfor %}
      </ul>
      <div class="v4-detail">
        {% for r in v4_research.fresh_reports %}
          <div id="fresh-{{ loop.index0 }}" class="v4-content {% if loop.index0 > 0 %}hidden{% endif %}">
            {{ r.content | markdown }}
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
  {% endif %}

  {% if v4_research.targeted %}
  <div class="v4-card">
    <h3>Targeted Research ({{ v4_research.targeted | length }})</h3>
    {# 비슷한 split 구조 #}
  </div>
  {% endif %}
</section>
{% endif %}
```

### 6.2 `partials/_manuscript.html` 확장

비슷한 패턴. 추가로 점수 추이 그래프(Chart.js 또는 단순 SVG):

```jinja2
{% if v4_manuscript and v4_manuscript.review_scores %}
<div class="v4-card">
  <h3>Review-draft 점수 추이</h3>
  <canvas id="review-chart" data-scores='{{ v4_manuscript.review_scores | tojson }}'></canvas>
</div>
{% endif %}
```

`<script>` 블록에서 데이터 attribute 읽어 차트 그리기. Chart.js CDN 1개 추가 또는 단순 인라인 SVG 렌더.

---

## 7. 스타일

`auto_agent/dashboard/static/`에 신규 CSS 추가 또는 기존 CSS 확장:

- `.v4-section` — 다른 색조 배경 (옅은 보라/파랑) — v3 섹션과 시각 구분
- `.v4-card` — 카드 형태
- `.v4-split` — 좌측 목록 / 우측 본문 2분할 (가로 스크롤 안 생기게)
- `.kind-badge.fresh` / `.deep` — 작은 컬러 뱃지

---

## 8. 테스트 전략

### 단위 테스트
- `tests/dashboard/test_helpers_v4.py` — `_list_md_files`, `_list_drafts`, `_parse_review_scores`, `_parse_frontmatter` 각각

### 통합 테스트
- `tests/dashboard/test_project_page_v4.py` — FastAPI TestClient로 `/project/{slug}?tab=research` 호출, v4 섹션 HTML 출력 확인

### 회귀 테스트
- v3-only 프로젝트(예: `output/1d4ef77e_다이소의_역사`) 페이지 호출 → v4 섹션 HTML 0건 확인
- v4 PD 프로젝트(`output/e49bb50f_한컴_브랜드백과_10min`) → v4 섹션 표시 확인

### 수동 검증
- uvicorn 띄우고 두 프로젝트 페이지 직접 확인

---

## 9. 위험과 미해결 질문

1. **마크다운 렌더링 라이브러리 선택** — 기존 dashboard에 markdown 필터가 이미 있는지 확인 필요. 없으면 `markdown2` 또는 `python-markdown` 의존성 추가
2. **점수 추이 차트** — Chart.js CDN 의존 vs SVG 인라인 vs 단순 텍스트 표. 단순 텍스트 표가 가장 안전(외부 의존 0)
3. **실시간 갱신** — review-draft 새 라운드가 추가되면 페이지 새로고침으로 반영. 자동 폴링은 범위 외(현재 SSE는 파이프라인 이벤트 전용)
4. **YAML 의존성** — `_parse_frontmatter`는 PyYAML 필요. v3에 이미 있는지 확인. 없으면 정규식 기반 단순 파서로 대체
5. **PD 노트 탭 (Phase 2)** — `pd_notebook.md` 형식이 자유 markdown이라 구조화 표시 어려울 수 있음. 1차는 통째 렌더, 추후 섹션별 분리

---

## 10. 단계 분해

후속 implementation plan에서 확정. 큰 덩어리:

- (A) 워크트리 + 헬퍼 함수 + 단위 테스트
- (B) 라우트 확장 + 템플릿 v4 섹션 추가 (research)
- (C) 라우트 확장 + 템플릿 v4 섹션 추가 (manuscript) + 점수 추이 차트
- (D) 스타일 + 회귀 테스트
- (E) 수동 검증 (uvicorn + 브라우저)
- (Phase 2 — 별도 plan) PD 노트 탭 추가

---

## 11. 측정 결과 (2026-05-09 검증)

### HTTP 검증

- **v4 fixture 프로젝트** (`/p/abc12345_test?tab=research`): `id="v4-research"` 마커 + `PD 워크플로 (v4)` 헤딩 + 기획안/fresh/deep/targeted slug 모두 HTML에 박힘 ✓
- **v4 fixture 프로젝트** (`?tab=manuscript`): `id="v4-manuscript"` 마커 + `Review-draft 점수 추이` 섹션 + draft-1/draft-2 버전 셀렉터 + `viewer_score: 9.5` + `PASS` 뱃지 모두 HTML에 박힘 ✓
- **v3-only 프로젝트** (`포켓몬스터_30주년_브랜드백과사전_1편?tab=research|manuscript`): v4 마커 0건 → graceful degradation 작동 ✓

> 참고: 한컴 프로젝트가 대시보드 워크트리 DB/output에 없어 v4 fixture(`abc12345_test`)로 대체 검증. NAS 경로(`/Volumes/jleavens/...`) 미마운트 상태.

### 위험 항목 점검

1. 마크다운 렌더링 — `markdown` 라이브러리 사용, Jinja 필터로 등록, 정상 작동 ✓
2. 점수 추이 차트 — SVG 인라인 채택 (외부 라이브러리 의존 0) ✓
3. 실시간 갱신 — 페이지 새로고침 패턴 (자동 폴링 미구현, 범위 외) ✓
4. PyYAML 의존성 — pyproject.toml dashboard/all 양쪽 추가, frontmatter 정확 파싱 ✓
5. PD 노트 탭 — Phase 2로 이월

### 시각 점검

브라우저 검증은 사용자가 직접 진행 — 보라 톤 v4 섹션 + 카드/리스트/차트/뱃지 시각 확인.
