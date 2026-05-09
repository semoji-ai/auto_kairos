# v4 Dashboard Compatibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v3 대시보드의 리서치·원고 탭이 v4 PD 워크플로 산출물(plan/research_reports/research_targeted/drafts/review/final_manuscript)을 같은 페이지에서 *조건부 노출*로 추가 표시하도록 확장. v3-only 프로젝트는 시각적 변화 0.

**Architecture:** 신규 모듈 `auto_agent/dashboard/v4_artifacts.py`에 frontmatter 파서 + v4 파일 lister + 통합 로더 2개(`load_research_v4`, `load_manuscript_v4`) 작성. `app.py`의 프로젝트 페이지 라우트에서 tab=research/manuscript 분기에 v4 컨텍스트를 *조건부로* 주입. 템플릿 `_research.html`/`_manuscript.html` 끝에 `{% if v4_... %}` 블록 추가. 마크다운 렌더링은 신규 의존성 `markdown` 추가, frontmatter 파싱은 `PyYAML`.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2, pytest, markdown(신규), PyYAML(신규)

**Spec:** `docs/superpowers/specs/2026-05-09-v4-dashboard-compat-design.md`

---

## Task 0: 워크트리 + 의존성 추가

**Files:**
- Create: `tests/dashboard/__init__.py`
- Create: `tests/dashboard/v4_fixtures/` (디렉토리)
- Modify: `pyproject.toml` (dashboard optional deps에 markdown + PyYAML 추가)

- [ ] **Step 1: 워크트리 생성**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
git worktree add -b v4-dashboard-compat ../auto_kairos_v3-dashboard main
cd ../auto_kairos_v3-dashboard
git branch --show-current
```

기대: `v4-dashboard-compat`. 모든 후속 작업은 `/Users/jleavens_macmini/LocalProjects/auto_kairos_v3-dashboard`에서.

- [ ] **Step 2: pyproject.toml 의존성 추가**

`pyproject.toml`의 `dashboard` optional dep에 두 라이브러리 추가:

```toml
dashboard = ["fastapi<1.0", "uvicorn", "jinja2", "python-multipart", "websockets", "markdown>=3.5", "PyYAML>=6.0"]
```

`all` 항목도 동일하게 갱신:

```toml
all = [
    "fastapi<1.0", "uvicorn", "jinja2", "python-multipart", "websockets",
    "markdown>=3.5", "PyYAML>=6.0",
    "whisperx", "matplotlib",
]
```

- [ ] **Step 3: 의존성 설치 + import 확인**

```bash
pip install 'markdown>=3.5' 'PyYAML>=6.0'
python3 -c "import markdown, yaml; print('markdown', markdown.__version__, 'yaml', yaml.__version__)"
```

기대: 버전 출력. 실패 시 venv 활성화 후 재실행.

- [ ] **Step 4: 테스트 디렉토리 생성**

```bash
mkdir -p tests/dashboard/v4_fixtures
touch tests/dashboard/__init__.py
```

- [ ] **Step 5: 픽스처 프로젝트 폴더 1개 만들기 (v4 PD 산출물 시뮬레이션)**

`tests/dashboard/v4_fixtures/abc12345_test/` 하위에 다음 파일 7개 생성:

```bash
mkdir -p tests/dashboard/v4_fixtures/abc12345_test/{research_reports,research_targeted,drafts,review}
```

`tests/dashboard/v4_fixtures/abc12345_test/plan.md`:
```markdown
---
project_id: abc12345
title: 테스트 영상 기획안
status: draft
---

# 기획안

## 한 줄 요약
이건 테스트 픽스처입니다.

## 미해결 질문
- 질문 1
```

`tests/dashboard/v4_fixtures/abc12345_test/research_reports/topic-1.md`:
```markdown
---
topic: 토픽 1
slug: topic-1
kind: fresh
created: 2026-05-09
---

# 토픽 1

## 본문
사실 1입니다.
```

`tests/dashboard/v4_fixtures/abc12345_test/research_reports/topic-2.md`:
```markdown
---
topic: 토픽 2
slug: topic-2
kind: deep
created: 2026-05-09
---

# 토픽 2 deep

본문.
```

`tests/dashboard/v4_fixtures/abc12345_test/research_targeted/q-1.md`:
```markdown
---
question: 첫 질문
slug: q-1
source: new
---

답변입니다.
```

`tests/dashboard/v4_fixtures/abc12345_test/drafts/v1.md`:
```markdown
---
version: 1
created: 2026-05-09
---

초안 v1 본문.
```

`tests/dashboard/v4_fixtures/abc12345_test/drafts/v2.md`:
```markdown
---
version: 2
created: 2026-05-09
---

초안 v2 본문.
```

`tests/dashboard/v4_fixtures/abc12345_test/review/review-draft-v2-2026-05-09.md`:
```markdown
---
draft_version: 2
viewer_score: 8.6
expert_verdict: PASS
---

리뷰 통합 노트.
```

`tests/dashboard/v4_fixtures/abc12345_test/final_manuscript.md`:
```markdown
---
status: final
viewer_score: 9.5
---

최종 원고 본문.
```

- [ ] **Step 6: 커밋**

```bash
git add pyproject.toml tests/dashboard/
git commit -m "chore(v4-dashboard): 워크트리 + markdown/PyYAML 의존성 + 테스트 픽스처"
```

---

## Task 1: frontmatter 파서 + 헬퍼 (TDD)

**Files:**
- Create: `auto_agent/dashboard/v4_artifacts.py`
- Create: `tests/dashboard/test_v4_frontmatter.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/dashboard/test_v4_frontmatter.py
"""v4_artifacts 모듈의 frontmatter 파서 테스트."""
from auto_agent.dashboard.v4_artifacts import parse_frontmatter, strip_frontmatter, read_or_empty
from pathlib import Path

FIXTURE = Path(__file__).parent / "v4_fixtures" / "abc12345_test"


def test_parse_frontmatter_returns_dict():
    text = "---\nkey: value\nnum: 42\n---\n\n본문"
    result = parse_frontmatter(text)
    assert result == {"key": "value", "num": 42}


def test_parse_frontmatter_no_block_returns_empty():
    text = "본문만 있음"
    assert parse_frontmatter(text) == {}


def test_parse_frontmatter_malformed_returns_empty():
    text = "---\n: : :\n---\n"
    # YAML 파싱 실패 시 빈 dict 반환 (예외 X)
    result = parse_frontmatter(text)
    assert isinstance(result, dict)


def test_strip_frontmatter_returns_body_only():
    text = "---\nkey: value\n---\n\n본문 시작\n둘째 줄"
    body = strip_frontmatter(text)
    assert "key: value" not in body
    assert body.startswith("\n본문 시작")


def test_strip_frontmatter_no_block_returns_full_text():
    text = "본문만 있음"
    assert strip_frontmatter(text) == "본문만 있음"


def test_read_or_empty_existing_file():
    p = FIXTURE / "plan.md"
    text = read_or_empty(p)
    assert "테스트 영상 기획안" in text


def test_read_or_empty_missing_file_returns_empty_string():
    p = FIXTURE / "nonexistent.md"
    assert read_or_empty(p) == ""
```

- [ ] **Step 2: 실패 확인**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3-dashboard
pytest tests/dashboard/test_v4_frontmatter.py -v
```

기대: ImportError (`auto_agent.dashboard.v4_artifacts` 미존재).

- [ ] **Step 3: 최소 구현**

```python
# auto_agent/dashboard/v4_artifacts.py
"""v4 PD 워크플로 산출물을 대시보드용으로 로드하는 헬퍼.

frontmatter 파싱 + 디렉토리별 .md 파일 lister + 통합 로더를 제공합니다.
모든 함수는 누락 파일·디렉토리에 대해 빈 값을 반환합니다 (조건부 노출 패턴).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """YAML frontmatter 블록을 dict로. 블록 없으면 빈 dict."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def strip_frontmatter(text: str) -> str:
    """frontmatter 블록을 제거한 본문 반환."""
    return _FRONTMATTER_RE.sub("", text, count=1)


def read_or_empty(path: Path) -> str:
    """파일 존재 시 본문, 아니면 빈 문자열."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/dashboard/test_v4_frontmatter.py -v
```

기대: 7 passed.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/v4_artifacts.py tests/dashboard/test_v4_frontmatter.py
git commit -m "feat(v4-dashboard): frontmatter 파서 + read_or_empty 헬퍼"
```

---

## Task 2: 디렉토리 lister + 통합 로더 (TDD)

**Files:**
- Modify: `auto_agent/dashboard/v4_artifacts.py`
- Create: `tests/dashboard/test_v4_loaders.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/dashboard/test_v4_loaders.py
"""v4 통합 로더(load_research_v4, load_manuscript_v4) 테스트."""
from pathlib import Path

from auto_agent.dashboard.v4_artifacts import (
    list_md_files,
    list_drafts,
    parse_review_scores,
    load_research_v4,
    load_manuscript_v4,
)

FIXTURE = Path(__file__).parent / "v4_fixtures" / "abc12345_test"


def test_list_md_files_returns_each_file_with_frontmatter_and_content():
    result = list_md_files(FIXTURE / "research_reports")
    assert len(result) == 2
    slugs = {r["slug"] for r in result}
    assert slugs == {"topic-1", "topic-2"}
    fresh = next(r for r in result if r["slug"] == "topic-1")
    assert fresh["frontmatter"]["kind"] == "fresh"
    assert "사실 1입니다" in fresh["content"]


def test_list_md_files_missing_dir_returns_empty():
    assert list_md_files(FIXTURE / "nonexistent_dir") == []


def test_list_drafts_sorted_by_version():
    result = list_drafts(FIXTURE / "drafts")
    assert len(result) == 2
    assert result[0]["version"] == 1
    assert result[1]["version"] == 2
    assert "초안 v2 본문" in result[1]["content"]


def test_list_drafts_missing_dir_returns_empty():
    assert list_drafts(FIXTURE / "nonexistent_dir") == []


def test_parse_review_scores_extracts_score_per_version():
    result = parse_review_scores(FIXTURE / "review")
    assert len(result) == 1
    assert result[0]["version"] == 2
    assert result[0]["viewer_score"] == 8.6
    assert result[0]["expert_verdict"] == "PASS"


def test_parse_review_scores_missing_dir_returns_empty():
    assert parse_review_scores(FIXTURE / "nonexistent_dir") == []


def test_load_research_v4_aggregates_all_sections():
    result = load_research_v4(FIXTURE)
    assert "테스트 영상 기획안" in result["plan_md"]
    assert len(result["fresh_reports"]) == 2
    assert len(result["targeted"]) == 1
    assert result["targeted"][0]["slug"] == "q-1"


def test_load_research_v4_empty_project_returns_empty_keys():
    empty = FIXTURE.parent / "nonexistent_project"
    result = load_research_v4(empty)
    assert result["plan_md"] == ""
    assert result["fresh_reports"] == []
    assert result["targeted"] == []


def test_load_manuscript_v4_includes_drafts_review_final():
    result = load_manuscript_v4(FIXTURE)
    assert len(result["drafts"]) == 2
    assert len(result["review_scores"]) == 1
    assert "최종 원고 본문" in result["final_manuscript"]
    assert result["final_marked"] == ""  # 픽스처에 final_manuscript_marked.md 없음


def test_load_manuscript_v4_empty_project():
    empty = FIXTURE.parent / "nonexistent_project"
    result = load_manuscript_v4(empty)
    assert result["drafts"] == []
    assert result["review_scores"] == []
    assert result["final_manuscript"] == ""
    assert result["final_marked"] == ""
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/dashboard/test_v4_loaders.py -v
```

기대: ImportError (`list_md_files` 등 미정의).

- [ ] **Step 3: 구현 추가**

`auto_agent/dashboard/v4_artifacts.py`에 다음 함수들 추가 (Task 1 코드 끝에 이어 붙임):

```python
_DRAFT_RE = re.compile(r"^v(\d+)\.md$")
_REVIEW_RE = re.compile(r"^review-draft-v(\d+)-")


def list_md_files(directory: Path) -> list[dict[str, Any]]:
    """디렉토리 내 .md 파일을 frontmatter+본문으로 분리해 반환.

    파일은 슬러그(파일명 stem) 알파벳 순. 디렉토리 부재 시 빈 리스트.
    """
    if not directory.exists() or not directory.is_dir():
        return []
    out = []
    for f in sorted(directory.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        out.append({
            "slug": f.stem,
            "frontmatter": parse_frontmatter(text),
            "content": strip_frontmatter(text),
        })
    return out


def list_drafts(directory: Path) -> list[dict[str, Any]]:
    """drafts/v{n}.md 파일을 버전 번호 순으로 반환."""
    if not directory.exists() or not directory.is_dir():
        return []
    drafts = []
    for f in directory.glob("v*.md"):
        m = _DRAFT_RE.match(f.name)
        if not m:
            continue
        text = f.read_text(encoding="utf-8")
        drafts.append({
            "version": int(m.group(1)),
            "frontmatter": parse_frontmatter(text),
            "content": strip_frontmatter(text),
        })
    drafts.sort(key=lambda d: d["version"])
    return drafts


def parse_review_scores(review_dir: Path) -> list[dict[str, Any]]:
    """review/review-draft-v{n}-*.md 의 frontmatter에서 점수 추출."""
    if not review_dir.exists() or not review_dir.is_dir():
        return []
    scores = []
    for f in sorted(review_dir.glob("review-draft-v*.md")):
        m = _REVIEW_RE.match(f.name)
        if not m:
            continue
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        scores.append({
            "version": int(m.group(1)),
            "viewer_score": fm.get("viewer_score"),
            "expert_verdict": fm.get("expert_verdict"),
        })
    scores.sort(key=lambda s: s["version"])
    return scores


def load_research_v4(project_dir: Path) -> dict[str, Any]:
    """v4 리서치 산출물 통합 로드. 키 모두 항상 존재 (없으면 빈 값)."""
    return {
        "plan_md": read_or_empty(project_dir / "plan.md"),
        "fresh_reports": list_md_files(project_dir / "research_reports"),
        "targeted": list_md_files(project_dir / "research_targeted"),
    }


def load_manuscript_v4(project_dir: Path) -> dict[str, Any]:
    """v4 원고 산출물 통합 로드."""
    return {
        "drafts": list_drafts(project_dir / "drafts"),
        "review_scores": parse_review_scores(project_dir / "review"),
        "final_manuscript": read_or_empty(project_dir / "final_manuscript.md"),
        "final_marked": read_or_empty(project_dir / "final_manuscript_marked.md"),
    }
```

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/dashboard/test_v4_loaders.py -v
```

기대: 10 passed.

- [ ] **Step 5: 전체 테스트 실행**

```bash
pytest tests/dashboard/ -v
```

기대: 17 passed (Task 1의 7 + Task 2의 10).

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/dashboard/v4_artifacts.py tests/dashboard/test_v4_loaders.py
git commit -m "feat(v4-dashboard): list_md_files + list_drafts + review scores + 통합 로더 2종"
```

---

## Task 3: app.py 라우트 확장 + Jinja markdown 필터

**Files:**
- Modify: `app.py` (프로젝트 페이지 라우트 핸들러 + Jinja env에 markdown 필터)
- Create: `tests/dashboard/test_route_v4_context.py`

- [ ] **Step 1: 라우트 핸들러 위치 확인**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3-dashboard
grep -n "@app.get.*project\|def project_page\|project.html" app.py | head -10
```

찾을 것: 프로젝트 페이지 라우트 정의 위치 (예: `@app.get("/project/{slug}")` 비슷한 패턴). 정확한 라인 번호 메모.

- [ ] **Step 2: Jinja 환경 + 템플릿 렌더 위치 확인**

```bash
grep -n "Jinja2Templates\|TemplateResponse\|filters\|register_filter" app.py | head -10
```

찾을 것: `Jinja2Templates(...)` 또는 환경 설정 라인.

- [ ] **Step 3: 실패 테스트 작성**

```python
# tests/dashboard/test_route_v4_context.py
"""프로젝트 페이지 라우트가 v4 컨텍스트를 주입하는지 검증."""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# app.py가 sys.path에서 import 가능해야 함
# 워크트리 루트에서 pytest 실행 시 작동


@pytest.fixture
def client(tmp_path, monkeypatch):
    """app.py를 import하고 테스트 픽스처를 output/으로 임시 매핑."""
    # 픽스처 프로젝트를 임시 output 디렉토리에 복사
    import shutil
    fixture_src = Path(__file__).parent / "v4_fixtures" / "abc12345_test"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    shutil.copytree(fixture_src, output_dir / "abc12345_test")

    monkeypatch.chdir(tmp_path)
    from app import app
    return TestClient(app)


def test_research_tab_includes_v4_section_when_files_exist(client):
    response = client.get("/project/abc12345_test?tab=research")
    assert response.status_code == 200
    assert "테스트 영상 기획안" in response.text  # plan.md 본문
    assert "topic-1" in response.text or "토픽 1" in response.text  # fresh report


def test_manuscript_tab_includes_v4_section_when_files_exist(client):
    response = client.get("/project/abc12345_test?tab=manuscript")
    assert response.status_code == 200
    assert "최종 원고 본문" in response.text  # final_manuscript.md
    assert "8.6" in response.text  # review score


def test_research_tab_has_no_v4_section_when_files_missing(tmp_path, monkeypatch):
    """v3-only 프로젝트(v4 파일 없음)는 v4 섹션 0건."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "v3only_test").mkdir()
    monkeypatch.chdir(tmp_path)
    from app import app
    c = TestClient(app)
    response = c.get("/project/v3only_test?tab=research")
    # v4 섹션 마커가 응답에 없어야 함 — id="v4-research" 부재로 검증
    assert 'id="v4-research"' not in response.text
```

- [ ] **Step 4: 실패 확인**

```bash
pytest tests/dashboard/test_route_v4_context.py -v
```

기대: assertion 실패 (v4 컨텍스트 미주입 상태) 또는 import 오류.

- [ ] **Step 5: app.py 수정 — 프로젝트 페이지 핸들러에 v4 컨텍스트 주입**

Step 1-2에서 찾은 라우트 핸들러를 수정. 실제 라인 위치가 변동되므로 다음 패턴으로 작업:

기존 핸들러가 다음과 비슷할 것:

```python
@app.get("/project/{slug}")
async def project_page(slug: str, tab: str = "pipeline", request: Request = None):
    project_dir = resolve_project_dir(slug)  # 또는 비슷한 함수
    context = {
        "request": request,
        "project": project_meta(project_dir),
        "tab": tab,
        # ... 기존 v3 컨텍스트
    }
    return templates.TemplateResponse("project.html", context)
```

다음 두 줄 추가 (return 직전):

```python
    from auto_agent.dashboard.v4_artifacts import load_research_v4, load_manuscript_v4
    if tab == "research":
        context["v4_research"] = load_research_v4(project_dir)
    elif tab == "manuscript":
        context["v4_manuscript"] = load_manuscript_v4(project_dir)
```

import는 함수 외부 상단에 옮겨도 OK. 함수 안에 둔 것은 lazy load + 기존 import 영역 안 건드리기 위함.

- [ ] **Step 6: Jinja 환경에 markdown 필터 등록**

`Jinja2Templates(...)` 라인 직후 다음 추가:

```python
import markdown as _md
templates.env.filters["markdown"] = lambda text: _md.markdown(
    text or "",
    extensions=["fenced_code", "tables", "nl2br"],
)
```

`templates`는 기존 변수명 (FastAPI 표준). 다른 이름이면 그것에 맞춤.

- [ ] **Step 7: 통과 확인**

```bash
pytest tests/dashboard/test_route_v4_context.py -v
```

기대: 3 passed (단, 1번·2번 테스트는 템플릿이 v4 섹션을 아직 안 보여주므로 *부분 실패*. 스코프상 라우트 컨텍스트 주입 검증이 1차 목표 — 템플릿 추가는 Task 4·5에서. 이 테스트는 임시로 컨텍스트 주입 자체를 dict 비교로 변경 가능).

수정안 — 1번·2번 테스트를 컨텍스트 직접 검증으로 단순화 (라우트 응답 200 + Task 4 이후 본문 확인):

```python
def test_research_tab_returns_200_with_v4_context_keys(client):
    response = client.get("/project/abc12345_test?tab=research")
    assert response.status_code == 200
    # v4 섹션 본문은 Task 4에서 추가, 여기서는 라우트가 깨지지 않음만 확인


def test_manuscript_tab_returns_200(client):
    response = client.get("/project/abc12345_test?tab=manuscript")
    assert response.status_code == 200
```

- [ ] **Step 8: 다시 통과 확인**

```bash
pytest tests/dashboard/test_route_v4_context.py -v
```

기대: 3 passed.

- [ ] **Step 9: 커밋**

```bash
git add app.py tests/dashboard/test_route_v4_context.py
git commit -m "feat(v4-dashboard): 라우트 v4 컨텍스트 주입 + Jinja markdown 필터"
```

---

## Task 4: _research.html v4 섹션 템플릿

**Files:**
- Modify: `auto_agent/dashboard/templates/partials/_research.html`
- Modify: `tests/dashboard/test_route_v4_context.py` (본문 검증 강화)

- [ ] **Step 1: _research.html 끝 확인**

```bash
tail -20 auto_agent/dashboard/templates/partials/_research.html
```

기존 본문의 마지막 줄 확인.

- [ ] **Step 2: 파일 끝에 v4 섹션 추가**

`_research.html` 파일 *맨 끝*에 다음 블록 추가:

```html
{# v4 PD 워크플로 섹션 — 조건부 노출 #}
{% if v4_research and (v4_research.plan_md or v4_research.fresh_reports or v4_research.targeted) %}
<section class="v4-section" id="v4-research">
  <h2 class="v4-section-title">PD 워크플로 (v4)</h2>

  {% if v4_research.plan_md %}
  <div class="v4-card">
    <h3>기획안 (plan.md)</h3>
    <div class="markdown-body v4-mini">{{ v4_research.plan_md | markdown | safe }}</div>
  </div>
  {% endif %}

  {% if v4_research.fresh_reports %}
  <div class="v4-card">
    <h3>Fresh + Deep Research ({{ v4_research.fresh_reports | length }}건)</h3>
    <div class="v4-split">
      <ul class="v4-list" data-target-pane="fresh">
        {% for r in v4_research.fresh_reports %}
          <li class="v4-list-item {% if loop.index0 == 0 %}active{% endif %}"
              data-target="fresh-{{ loop.index0 }}">
            {% if r.frontmatter.kind %}<span class="kind-badge kind-{{ r.frontmatter.kind }}">{{ r.frontmatter.kind }}</span>{% endif %}
            {{ r.slug }}
          </li>
        {% endfor %}
      </ul>
      <div class="v4-detail">
        {% for r in v4_research.fresh_reports %}
          <div id="fresh-{{ loop.index0 }}" class="v4-content {% if loop.index0 > 0 %}hidden{% endif %}">
            <div class="markdown-body">{{ r.content | markdown | safe }}</div>
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
  {% endif %}

  {% if v4_research.targeted %}
  <div class="v4-card">
    <h3>Targeted Research ({{ v4_research.targeted | length }}건)</h3>
    <div class="v4-split">
      <ul class="v4-list" data-target-pane="targeted">
        {% for r in v4_research.targeted %}
          <li class="v4-list-item {% if loop.index0 == 0 %}active{% endif %}"
              data-target="targeted-{{ loop.index0 }}">
            {% if r.frontmatter.source %}<span class="kind-badge kind-{{ r.frontmatter.source }}">{{ r.frontmatter.source }}</span>{% endif %}
            {{ r.slug }}
          </li>
        {% endfor %}
      </ul>
      <div class="v4-detail">
        {% for r in v4_research.targeted %}
          <div id="targeted-{{ loop.index0 }}" class="v4-content {% if loop.index0 > 0 %}hidden{% endif %}">
            <div class="markdown-body">{{ r.content | markdown | safe }}</div>
          </div>
        {% endfor %}
      </div>
    </div>
  </div>
  {% endif %}
</section>

<script>
// v4 list 클릭 시 detail pane 토글
document.querySelectorAll('.v4-list').forEach(list => {
  list.addEventListener('click', e => {
    const item = e.target.closest('.v4-list-item');
    if (!item) return;
    const targetId = item.dataset.target;
    list.querySelectorAll('.v4-list-item').forEach(li => li.classList.remove('active'));
    item.classList.add('active');
    const detailParent = list.parentElement.querySelector('.v4-detail');
    detailParent.querySelectorAll('.v4-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(targetId).classList.remove('hidden');
  });
});
</script>
{% endif %}
```

- [ ] **Step 3: 본문 검증 테스트 업데이트**

`tests/dashboard/test_route_v4_context.py`의 첫 번째 테스트를 본문 검증으로 다시 강화:

```python
def test_research_tab_includes_v4_section_when_files_exist(client):
    response = client.get("/project/abc12345_test?tab=research")
    assert response.status_code == 200
    assert 'id="v4-research"' in response.text  # v4 섹션 마커
    assert "테스트 영상 기획안" in response.text  # plan.md 렌더
    assert "topic-1" in response.text  # fresh report slug
    assert "topic-2" in response.text
    assert "q-1" in response.text  # targeted


def test_research_tab_no_v4_section_when_files_missing(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "v3only_test").mkdir()
    monkeypatch.chdir(tmp_path)
    from app import app
    c = TestClient(app)
    response = c.get("/project/v3only_test?tab=research")
    assert 'id="v4-research"' not in response.text
```

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/dashboard/test_route_v4_context.py -v
```

기대: 모두 pass.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/templates/partials/_research.html tests/dashboard/test_route_v4_context.py
git commit -m "feat(v4-dashboard): _research.html에 v4 섹션 추가 (plan + fresh/deep + targeted)"
```

---

## Task 5: _manuscript.html v4 섹션 + 점수 추이 차트

**Files:**
- Modify: `auto_agent/dashboard/templates/partials/_manuscript.html`
- Modify: `tests/dashboard/test_route_v4_context.py`

- [ ] **Step 1: _manuscript.html 끝 확인**

```bash
tail -20 auto_agent/dashboard/templates/partials/_manuscript.html
```

- [ ] **Step 2: v4 섹션 추가 (파일 끝)**

```html
{# v4 PD 워크플로 섹션 — 조건부 노출 #}
{% if v4_manuscript and (v4_manuscript.drafts or v4_manuscript.review_scores or v4_manuscript.final_manuscript) %}
<section class="v4-section" id="v4-manuscript">
  <h2 class="v4-section-title">PD 워크플로 (v4)</h2>

  {% if v4_manuscript.review_scores %}
  <div class="v4-card">
    <h3>Review-draft 점수 추이</h3>
    {# SVG 인라인 차트 — 외부 라이브러리 의존 없음 #}
    <svg class="v4-score-chart" viewBox="0 0 600 240" xmlns="http://www.w3.org/2000/svg">
      {% set scores = v4_manuscript.review_scores %}
      {% set max_v = 10 %}
      {% set count = scores | length %}
      <!-- 목표선 9.0 -->
      <line x1="40" y1="{{ 200 - (9.0/max_v)*180 }}" x2="580" y2="{{ 200 - (9.0/max_v)*180 }}"
            stroke="#888" stroke-dasharray="4,4" />
      <text x="585" y="{{ 200 - (9.0/max_v)*180 + 4 }}" font-size="10" fill="#888">9.0</text>
      <!-- y축 -->
      <line x1="40" y1="20" x2="40" y2="200" stroke="#ccc" />
      <!-- 시청자 점수 꺾은선 + 점 -->
      {% if count > 0 %}
        {% set step = (540 / (count if count > 1 else 1)) %}
        <polyline points="{% for s in scores %}{{ 40 + loop.index0 * step }},{{ 200 - ((s.viewer_score or 0)/max_v)*180 }} {% endfor %}"
                  fill="none" stroke="#3b82f6" stroke-width="2" />
        {% for s in scores %}
          <circle cx="{{ 40 + loop.index0 * step }}" cy="{{ 200 - ((s.viewer_score or 0)/max_v)*180 }}"
                  r="4" fill="#3b82f6" />
          <text x="{{ 40 + loop.index0 * step }}" y="{{ 200 - ((s.viewer_score or 0)/max_v)*180 - 8 }}"
                font-size="11" text-anchor="middle" fill="#1e3a8a">{{ s.viewer_score }}</text>
          <text x="{{ 40 + loop.index0 * step }}" y="220" font-size="10" text-anchor="middle" fill="#666">v{{ s.version }}</text>
        {% endfor %}
      {% endif %}
    </svg>
    <table class="v4-score-table">
      <thead><tr><th>버전</th><th>시청자</th><th>전문가</th></tr></thead>
      <tbody>
        {% for s in v4_manuscript.review_scores %}
        <tr>
          <td>v{{ s.version }}</td>
          <td>{{ s.viewer_score or "—" }}</td>
          <td><span class="verdict verdict-{{ (s.expert_verdict or 'pending') | lower }}">{{ s.expert_verdict or "—" }}</span></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {% if v4_manuscript.drafts %}
  <div class="v4-card">
    <h3>Drafts ({{ v4_manuscript.drafts | length }}개)</h3>
    <div class="v4-version-selector">
      {% set last_idx = (v4_manuscript.drafts | length) - 1 %}
      {% for d in v4_manuscript.drafts %}
        <button class="v4-version-btn {% if loop.index0 == last_idx %}active{% endif %}"
                data-target="draft-{{ d.version }}">v{{ d.version }}</button>
      {% endfor %}
    </div>
    <div class="v4-version-content">
      {% for d in v4_manuscript.drafts %}
        <div id="draft-{{ d.version }}" class="v4-content {% if loop.index0 != last_idx %}hidden{% endif %}">
          <div class="markdown-body">{{ d.content | markdown | safe }}</div>
        </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  {% if v4_manuscript.final_manuscript %}
  <div class="v4-card">
    <h3>Final Manuscript</h3>
    <div class="v4-final-toggle">
      <button class="v4-final-btn active" data-target="final-prose">Prose</button>
      {% if v4_manuscript.final_marked %}
      <button class="v4-final-btn" data-target="final-marked">Marked (Ch + ---)</button>
      {% endif %}
    </div>
    <div id="final-prose" class="v4-content">
      <div class="markdown-body">{{ v4_manuscript.final_manuscript | markdown | safe }}</div>
    </div>
    {% if v4_manuscript.final_marked %}
    <div id="final-marked" class="v4-content hidden">
      <pre class="v4-marked-pre">{{ v4_manuscript.final_marked }}</pre>
    </div>
    {% endif %}
  </div>
  {% endif %}
</section>

<script>
// 버전 셀렉터 + final 토글
document.querySelectorAll('.v4-version-selector').forEach(sel => {
  sel.addEventListener('click', e => {
    const btn = e.target.closest('.v4-version-btn');
    if (!btn) return;
    sel.querySelectorAll('.v4-version-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const parent = sel.parentElement.querySelector('.v4-version-content');
    parent.querySelectorAll('.v4-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(btn.dataset.target).classList.remove('hidden');
  });
});
document.querySelectorAll('.v4-final-toggle').forEach(tog => {
  tog.addEventListener('click', e => {
    const btn = e.target.closest('.v4-final-btn');
    if (!btn) return;
    tog.querySelectorAll('.v4-final-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const card = tog.closest('.v4-card');
    card.querySelectorAll(':scope > .v4-content').forEach(c => c.classList.add('hidden'));
    document.getElementById(btn.dataset.target).classList.remove('hidden');
  });
});
</script>
{% endif %}
```

- [ ] **Step 3: 테스트 추가**

`tests/dashboard/test_route_v4_context.py`에 다음 테스트 추가:

```python
def test_manuscript_tab_includes_v4_section(client):
    response = client.get("/project/abc12345_test?tab=manuscript")
    assert response.status_code == 200
    assert 'id="v4-manuscript"' in response.text
    assert "최종 원고 본문" in response.text
    assert "8.6" in response.text
    assert "PASS" in response.text
    assert 'data-target="draft-1"' in response.text  # 버전 버튼
    assert 'data-target="draft-2"' in response.text


def test_manuscript_tab_no_v4_section_when_files_missing(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "v3only_test").mkdir()
    monkeypatch.chdir(tmp_path)
    from app import app
    c = TestClient(app)
    response = c.get("/project/v3only_test?tab=manuscript")
    assert 'id="v4-manuscript"' not in response.text
```

- [ ] **Step 4: 통과 확인**

```bash
pytest tests/dashboard/test_route_v4_context.py -v
```

기대: 모든 테스트 pass.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/templates/partials/_manuscript.html tests/dashboard/test_route_v4_context.py
git commit -m "feat(v4-dashboard): _manuscript.html에 v4 섹션 + 점수 추이 SVG 차트 + 버전 셀렉터"
```

---

## Task 6: 스타일 (CSS)

**Files:**
- Modify: `auto_agent/dashboard/static/style.css` (또는 동등 파일 — Step 1에서 확인)

- [ ] **Step 1: 기존 CSS 파일 확인**

```bash
ls auto_agent/dashboard/static/
grep -rn "content-tab\|kind-badge" auto_agent/dashboard/static/ 2>/dev/null | head -5
```

기존 CSS 파일명을 메모. 보통 `style.css` 또는 `dashboard.css`.

- [ ] **Step 2: 신규 스타일 추가 (파일 끝)**

```css
/* === v4 Dashboard Compatibility === */

.v4-section {
  margin-top: 2.5rem;
  padding-top: 1.5rem;
  border-top: 2px dashed #c7d2fe;
  background: linear-gradient(180deg, #f5f3ff 0%, #ffffff 60px);
  padding-left: 1rem;
  padding-right: 1rem;
  padding-bottom: 1rem;
  border-radius: 8px;
}

.v4-section-title {
  font-size: 1.1rem;
  color: #6d28d9;
  margin-bottom: 1rem;
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #ede9fe;
  border-radius: 4px;
}

.v4-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.v4-card h3 {
  margin-top: 0;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
  color: #4b5563;
}

.v4-mini {
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid #f3f4f6;
  padding: 0.5rem;
  font-size: 0.85rem;
}

.v4-split {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 1rem;
  min-height: 200px;
}

.v4-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  overflow-y: auto;
  max-height: 400px;
}

.v4-list-item {
  padding: 0.5rem;
  cursor: pointer;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.85rem;
}

.v4-list-item:hover {
  background: #f9fafb;
}

.v4-list-item.active {
  background: #ede9fe;
  font-weight: 600;
}

.v4-detail {
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  padding: 0.75rem;
  overflow-y: auto;
  max-height: 400px;
  font-size: 0.85rem;
}

.v4-content.hidden {
  display: none;
}

.kind-badge {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  font-size: 0.7rem;
  border-radius: 3px;
  margin-right: 0.4rem;
  font-weight: 600;
}

.kind-fresh { background: #dbeafe; color: #1e40af; }
.kind-deep { background: #fce7f3; color: #9f1239; }
.kind-new { background: #dcfce7; color: #166534; }
.kind-existing { background: #fef3c7; color: #92400e; }

.v4-score-chart {
  width: 100%;
  max-width: 600px;
  height: auto;
}

.v4-score-table {
  margin-top: 0.5rem;
  font-size: 0.85rem;
  border-collapse: collapse;
}

.v4-score-table th, .v4-score-table td {
  padding: 0.3rem 0.75rem;
  border: 1px solid #e5e7eb;
}

.verdict {
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 600;
}

.verdict-pass { background: #dcfce7; color: #166534; }
.verdict-conditional_pass { background: #fef3c7; color: #92400e; }
.verdict-needs_revision { background: #fee2e2; color: #991b1b; }
.verdict-pending { background: #f3f4f6; color: #6b7280; }

.v4-version-selector, .v4-final-toggle {
  margin-bottom: 0.75rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.v4-version-btn, .v4-final-btn {
  padding: 0.3rem 0.75rem;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.v4-version-btn.active, .v4-final-btn.active {
  background: #6d28d9;
  color: #ffffff;
  border-color: #6d28d9;
}

.v4-marked-pre {
  background: #f3f4f6;
  padding: 1rem;
  overflow-x: auto;
  font-size: 0.8rem;
  white-space: pre-wrap;
  max-height: 600px;
  overflow-y: auto;
}

.markdown-body h1 { font-size: 1.2rem; margin-top: 0.75rem; }
.markdown-body h2 { font-size: 1.05rem; margin-top: 0.6rem; color: #4b5563; }
.markdown-body h3 { font-size: 0.95rem; margin-top: 0.5rem; color: #6b7280; }
.markdown-body p { margin: 0.4rem 0; line-height: 1.5; }
.markdown-body ul, .markdown-body ol { margin: 0.4rem 0; padding-left: 1.5rem; }
.markdown-body code { background: #f3f4f6; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85em; }
.markdown-body pre { background: #f3f4f6; padding: 0.75rem; border-radius: 4px; overflow-x: auto; }
.markdown-body table { border-collapse: collapse; margin: 0.5rem 0; }
.markdown-body th, .markdown-body td { border: 1px solid #e5e7eb; padding: 0.3rem 0.5rem; }
```

- [ ] **Step 3: 시각 회귀 점검 — 빠른 import + 라우트**

```bash
pytest tests/dashboard/ -v
```

기대: 17 + 라우트 테스트 = 20여 개 모두 pass.

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/dashboard/static/
git commit -m "style(v4-dashboard): v4 섹션 CSS — 보라 톤 분리 + 카드/리스트/차트/뱃지"
```

---

## Task 7: 수동 검증 (uvicorn + 브라우저)

**Files:** 없음 (런타임 검증 + docs/superpowers/specs 8장 위험 측정 결과 기록)

- [ ] **Step 1: dashboard 의존성 설치**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3-dashboard
pip install -e ".[dashboard]"
```

기대: markdown + PyYAML 포함 dashboard deps 모두 설치.

- [ ] **Step 2: uvicorn 시작**

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

(포트 8080이 이미 점유면 다른 포트 사용 — 8081 등.) 백그라운드 실행 또는 별도 터미널.

- [ ] **Step 3: v4 PD 프로젝트 페이지 확인**

브라우저에서:

```
http://localhost:8080/project/한컴_브랜드백과_10min?tab=research
```

수동 체크:
- 기존 v3 영역(research_report.json 관련)이 그대로 보이는가?
- 그 아래 보라 톤 박스 "PD 워크플로 (v4)"가 등장하는가?
- 기획안 plan.md 본문 마크다운 렌더가 보이는가?
- Fresh/Deep Research 좌측 목록에 9개 보고서가 보이고 클릭하면 우측 본문이 바뀌는가?
- Targeted Research 5개 질문이 보이는가?

```
http://localhost:8080/project/한컴_브랜드백과_10min?tab=manuscript
```

수동 체크:
- 점수 추이 SVG 차트에서 v2~v4(또는 v6) 점수가 꺾은선으로 보이는가?
- Drafts 버전 셀렉터(v1, v2, ...)가 작동하는가?
- Final Manuscript에 Prose / Marked 토글이 작동하는가?

- [ ] **Step 4: v3-only 프로젝트 회귀 확인**

```
http://localhost:8080/project/<v3 only slug>?tab=research
http://localhost:8080/project/<v3 only slug>?tab=manuscript
```

`output/` 안에 v4 파일 없는 프로젝트 1개 골라서. 예: `1d4ef77e_다이소의_역사`.

체크: v4 섹션 자체가 안 보여야 함 (기존 UI 변경 0).

- [ ] **Step 5: 결과 기록**

`docs/superpowers/specs/2026-05-09-v4-dashboard-compat-design.md`의 9장 위험 항목 옆에 측정 결과 추가:

```markdown
## 측정 결과 (2026-05-09 검증)

1. 마크다운 렌더링 — markdown 라이브러리 사용, 정상 작동
2. 점수 추이 차트 — SVG 인라인 채택, 외부 의존 0
3. 실시간 갱신 — 페이지 새로고침 패턴 채택 (자동 폴링 미구현)
4. PyYAML 의존성 — 추가 완료, frontmatter 정확 파싱
5. PD 노트 탭 — Phase 2로 이월
```

- [ ] **Step 6: 커밋**

```bash
git add docs/superpowers/specs/2026-05-09-v4-dashboard-compat-design.md
git commit -m "docs(v4-dashboard): 1차 검증 측정 결과 — 위험 5건 정량화"
```

---

## Self-Review

**Spec 커버리지:**
- 설계 1장(범위) Phase 1 → Task 0~7 ✅
- 설계 2장(graceful degradation) → Task 4·5 `{% if %}` 블록 + Task 7 회귀 ✅
- 설계 3장(데이터 흐름) → Task 1·2 헬퍼 + Task 3 라우트 ✅
- 설계 4장(UI 명세) → Task 4 research + Task 5 manuscript ✅
- 설계 5장(백엔드) → Task 1·2·3 ✅
- 설계 6장(템플릿) → Task 4·5 ✅
- 설계 7장(스타일) → Task 6 ✅
- 설계 8장(테스트 전략) → Task 1·2·3·4·5 단위/통합 + Task 7 수동 ✅
- 설계 9장(위험 5건) → Task 7 측정 결과 기록 ✅
- Phase 2(PD 노트 탭) → 본 plan 범위 외, 별도 plan에서 ✅

**Placeholder 스캔:** 모든 step에 실코드. Step 1 "라우트 핸들러 위치 확인"은 grep 명령 + 패턴 명시되어 있고, 실제 라인은 코드베이스 의존이라 동적임 — 패턴 + 수정 가이드는 명확.

**타입 일관성:** `parse_frontmatter() -> dict[str, Any]`, `list_md_files() -> list[dict]`, `load_research_v4() -> dict` 일관. 템플릿에서 `v4_research.fresh_reports[].slug/frontmatter/content` 키 일관 사용.
