# URL UUID Routing — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백엔드 라우트가 uuid를 정본 식별자로 받도록 전환. slug로 들어오면 자동 301 redirect → uuid 형태. 프론트는 미변경 (자동 redirect로 흡수).

**Architecture:** 라우트 시그니처는 `{slug}` → `{project_ref}`로 리네임 (의미 정직). 단일 helper `resolve_project_ref(project_ref)`가 8자 hex이면 uuid로, 아니면 slug로 조회 후 `(project, canonical_redirect_or_none)` 반환. slug로 조회됐으면 핸들러는 즉시 301로 uuid URL 리다이렉트. 라우트는 1벌만 유지(중복 핸들러 없음).

**Tech Stack:** FastAPI, Python 3.11+, pytest, project_manager (auto_agent.db)

**Spec:** `docs/superpowers/specs/2026-04-28-url-uuid-routing-design.md`

**Scope:** Phase 1만 (백엔드). Phase 2(프론트), Phase 3(Remotion), Phase 4(정리)는 별도 플랜.

---

## File Structure

| 파일 | 역할 | 변경 |
|------|------|------|
| `auto_agent/dashboard/project_ref.py` | 새 helper 모듈 (resolver + canonical redirect) | Create |
| `tests/dashboard/test_project_ref.py` | helper 단위 테스트 | Create |
| `app.py` | 38개 slug 라우트의 path param + 핸들러 | Modify |
| `auto_agent/dashboard/scene_editor.py` | APIRouter 2개의 prefix 변경 + 핸들러 | Modify |
| `auto_agent/dashboard/design_presets.py` | 2개 slug 라우트 | Modify |
| `auto_agent/dashboard/enrichment_routes.py` | 3개 `{project_slug}` 라우트 | Modify |

---

## Task 1: resolve_project_ref helper + 테스트

**Files:**
- Create: `auto_agent/dashboard/project_ref.py`
- Create: `tests/dashboard/test_project_ref.py`

- [ ] **Step 1: 테스트 디렉토리 확인**

```bash
ls tests/dashboard/ 2>/dev/null || mkdir -p tests/dashboard && touch tests/dashboard/__init__.py
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/dashboard/test_project_ref.py`:

```python
"""project_ref helper 단위 테스트."""
from unittest.mock import MagicMock
import pytest

from auto_agent.dashboard.project_ref import (
    is_uuid_form,
    resolve_project_ref,
    canonical_uuid_url,
)


def test_is_uuid_form_recognizes_8char_hex():
    assert is_uuid_form("9f202fb4") is True
    assert is_uuid_form("00000000") is True
    assert is_uuid_form("abcdef12") is True


def test_is_uuid_form_rejects_non_hex():
    assert is_uuid_form("포켓몬스터") is False
    assert is_uuid_form("my-slug") is False
    assert is_uuid_form("9f202fb") is False  # 7자
    assert is_uuid_form("9f202fb4a") is False  # 9자
    assert is_uuid_form("9F202FB4") is False  # 대문자 — slug로 취급
    assert is_uuid_form("ghijklmn") is False  # hex 아님


def test_resolve_by_uuid_returns_project_no_redirect():
    pm = MagicMock()
    pm.get_project.return_value = {"uuid": "9f202fb4", "slug": "포켓몬"}

    project, needs_redirect = resolve_project_ref(pm, "9f202fb4")

    assert project["uuid"] == "9f202fb4"
    assert needs_redirect is False
    pm.get_project.assert_called_once_with(uuid="9f202fb4")


def test_resolve_by_slug_returns_project_with_redirect_flag():
    pm = MagicMock()
    pm.get_project.return_value = {"uuid": "9f202fb4", "slug": "포켓몬"}

    project, needs_redirect = resolve_project_ref(pm, "포켓몬")

    assert project["uuid"] == "9f202fb4"
    assert needs_redirect is True
    pm.get_project.assert_called_once_with(slug="포켓몬")


def test_resolve_returns_none_when_not_found():
    pm = MagicMock()
    pm.get_project.return_value = None

    project, needs_redirect = resolve_project_ref(pm, "nonexistent")

    assert project is None
    assert needs_redirect is False


def test_canonical_uuid_url_replaces_first_segment_after_p():
    assert canonical_uuid_url(
        "/p/포켓몬?tab=storyboard", uuid="9f202fb4"
    ) == "/p/9f202fb4?tab=storyboard"


def test_canonical_uuid_url_handles_api_path():
    assert canonical_uuid_url(
        "/api/p/포켓몬/editor/scenes/3/select-image", uuid="9f202fb4"
    ) == "/api/p/9f202fb4/editor/scenes/3/select-image"


def test_canonical_uuid_url_preserves_query_string():
    assert canonical_uuid_url(
        "/p/my-slug?tab=studio&debug=1", uuid="abc12345"
    ) == "/p/abc12345?tab=studio&debug=1"
```

- [ ] **Step 3: 테스트 실행하여 실패 확인**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3 && python -m pytest tests/dashboard/test_project_ref.py -v
```

Expected: `ModuleNotFoundError: No module named 'auto_agent.dashboard.project_ref'`

- [ ] **Step 4: helper 구현**

`auto_agent/dashboard/project_ref.py`:

```python
"""프로젝트 식별자(uuid 또는 slug) 해석 helper.

URL의 path 파라미터로 들어온 식별자를 uuid 정본으로 해석한다.
- 8자 hex(`^[a-f0-9]{8}$`)면 uuid로 조회
- 그 외는 slug로 조회 → 호출자에게 canonical redirect 신호 반환

진입 형태(uuid/slug)와 무관하게 핸들러 로직은 동일하게 동작하며,
slug 진입 시에만 301 redirect를 반환하는 책임은 호출자에게 있다.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

_UUID_RE = re.compile(r"^[a-f0-9]{8}$")


def is_uuid_form(value: str) -> bool:
    """value가 uuid 형식(8자 소문자 hex)인지."""
    return bool(_UUID_RE.match(value))


def resolve_project_ref(pm, project_ref: str) -> Tuple[Optional[dict], bool]:
    """project_ref(uuid 또는 slug) → (project, needs_redirect).

    Returns:
        (project, needs_redirect)
        - project: dict 또는 None(미발견)
        - needs_redirect: True면 호출자가 301 redirect 응답 반환해야 함
    """
    if is_uuid_form(project_ref):
        return pm.get_project(uuid=project_ref), False
    return pm.get_project(slug=project_ref), True


def canonical_uuid_url(original_path: str, uuid: str) -> str:
    """URL 경로의 `/p/{...}` 첫 세그먼트를 uuid로 치환.

    `/p/포켓몬?tab=storyboard` + uuid=`9f202fb4`
        → `/p/9f202fb4?tab=storyboard`
    `/api/p/포켓몬/editor/scenes/3` + uuid=`9f202fb4`
        → `/api/p/9f202fb4/editor/scenes/3`
    """
    # /p/ 또는 /api/p/ 직후 한 세그먼트만 치환
    return re.sub(
        r"(?P<prefix>/(?:api/)?p/)[^/?]+",
        lambda m: m.group("prefix") + uuid,
        original_path,
        count=1,
    )
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
python -m pytest tests/dashboard/test_project_ref.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/dashboard/project_ref.py tests/dashboard/test_project_ref.py tests/dashboard/__init__.py
git commit -m "feat(dashboard): add project_ref resolver helper

uuid(8자 hex) 또는 slug를 받아 프로젝트 조회 + canonical redirect
신호 반환. URL UUID 라우팅 전환의 기반.

Refs: docs/superpowers/specs/2026-04-28-url-uuid-routing-design.md"
```

---

## Task 2: 첫 라우트(`/p/{slug}`) 전환 — 패턴 확립

**Files:**
- Modify: `app.py:643-652` (`project_by_slug` 핸들러)

**배경**: 38개 라우트 일괄 변환 전에, 가장 단순한 HTML 라우트 1개로 전체 패턴을 확립한다. 이후 Task 3-5는 같은 패턴 기계적 적용.

- [ ] **Step 1: 현재 핸들러 확인**

```bash
sed -n '643,652p' app.py
```

확인할 내용:
```python
@app.get("/p/{slug}", response_class=HTMLResponse)
async def project_by_slug(request: Request, slug: str, tab: str = "pipeline"):
    """slug 기반 프로젝트 상세 페이지."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    return templates.TemplateResponse(request, "project.html", context)
```

- [ ] **Step 2: import 추가 (파일 상단)**

`app.py` 상단의 기존 dashboard import 블록 옆에:

```python
from auto_agent.dashboard.project_ref import (
    resolve_project_ref,
    canonical_uuid_url,
)
```

- [ ] **Step 3: 핸들러 변환**

`app.py:643-652` 교체:

```python
@app.get("/p/{project_ref}", response_class=HTMLResponse)
async def project_page(request: Request, project_ref: str, tab: str = "pipeline"):
    """프로젝트 상세 페이지. project_ref는 uuid(8자 hex) 또는 slug.

    slug로 진입 시 canonical uuid URL로 301 redirect.
    """
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""), project["uuid"]),
            status_code=301,
        )

    context = _load_tab_data(pm, project, tab)
    return templates.TemplateResponse(request, "project.html", context)
```

- [ ] **Step 4: 서버 기동 + 수동 검증**

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8080 &
sleep 3
```

수동 확인:
1. uuid로 직접 진입: `curl -sI "http://localhost:8080/p/9f202fb4?tab=storyboard"` → `200 OK`
2. slug로 진입 → 301 redirect: `curl -sI "http://localhost:8080/p/포켓몬스터30주년브랜드백과사전_2편"` → `301` + `location: /p/9f202fb4`
3. 잘못된 ref: `curl -sI "http://localhost:8080/p/nonexistent"` → `404`

(uuid/slug는 본인 환경의 실제 프로젝트로 치환)

```bash
kill %1 2>/dev/null || pkill -f "uvicorn app:app"
```

- [ ] **Step 5: 커밋**

```bash
git add app.py
git commit -m "refactor(dashboard): /p/{slug} → /p/{project_ref} (uuid 정본 + slug redirect)

첫 라우트로 패턴 확립. slug 진입 시 canonical uuid URL로 301
redirect. 나머지 37개 라우트는 후속 task에서 동일 패턴 적용."
```

---

## Task 3: app.py — API 라우트 일괄 전환 (그룹 1: 조회/manuscript/research)

**Files:**
- Modify: `app.py` — `/api/p/{slug}/research/...`, `/api/p/{slug}/manuscript/...`, `/api/p/{slug}/summary`, `/api/p/{slug}/scenes` 등 GET 위주 라우트 (~12개)

- [ ] **Step 1: 대상 라우트 목록 추출**

```bash
grep -n '@app\.\(get\|post\)("/api/p/{slug}' app.py | head -40
```

이번 그룹 대상 (URL 패턴):
- `/api/p/{slug}/research/canvas`
- `/api/p/{slug}/research/images`
- `/api/p/{slug}/research/wiki`
- `/api/p/{slug}/research/wiki/{page}`
- `/api/p/{slug}/manuscript/raw`
- `/api/p/{slug}/manuscript/save`
- `/api/p/{slug}/summary`
- `/api/p/{slug}/scenes`
- `/api/p/{slug}/tab/{tab}`
- `/api/p/{slug}/storyboard/scene/{scene_num}`
- 기타 GET 라우트로 분류되는 것

- [ ] **Step 2: 각 라우트에 동일 패턴 적용**

각 핸들러에 대해:
1. path 패턴 `{slug}` → `{project_ref}`
2. 함수 시그니처 `slug: str` → `project_ref: str`, `request: Request` 추가(없으면)
3. 내부 `project = pm.get_project(slug=slug)` → `project, needs_redirect = resolve_project_ref(pm, project_ref)`
4. 404 체크 직후 `if needs_redirect: return RedirectResponse(...)` 추가

표준 변환 템플릿 (예: `/api/p/{slug}/summary`):

**전**:
```python
@app.get("/api/p/{slug}/summary")
async def project_summary(slug: str):
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    # ... 기존 로직 (slug 변수 사용 시 그대로 둠 — project["slug"]로 치환 필요한 곳만)
    return {...}
```

**후**:
```python
@app.get("/api/p/{project_ref}/summary")
async def project_summary(request: Request, project_ref: str):
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""), project["uuid"]),
            status_code=301,
        )
    # ... 기존 로직 (이제 project_ref가 uuid임을 보장)
    return {...}
```

**주의**: 함수 본문 안에서 `slug` 변수를 직접 사용하던 곳은 `project["slug"]`로 치환. 단, `pm.get_project(slug=slug)` 호출은 이미 위에서 처리됨.

- [ ] **Step 3: 단위별로 변환 후 서버 기동·수동 확인**

각 라우트 변환 후 한 번씩:
```bash
python -m uvicorn app:app --port 8080 &
sleep 3
# uuid 진입
curl -sI "http://localhost:8080/api/p/<uuid>/<endpoint>" | head -1
# slug 진입 → 301
curl -sI "http://localhost:8080/api/p/<slug>/<endpoint>" | head -3
pkill -f "uvicorn app:app"
```

- [ ] **Step 4: 그룹 1 완료 후 grep 카운터**

```bash
grep -c '@app\..*"/api/p/{slug}' app.py
```

Expected: 38(시작) − 변환한 라우트 수 만큼 감소

- [ ] **Step 5: 커밋**

```bash
git add app.py
git commit -m "refactor(dashboard): API 라우트 그룹1 uuid 전환 (research/manuscript/summary)

GET 위주 ~12개 라우트의 slug 파라미터를 project_ref로 변환.
uuid 정본, slug 진입 시 301 redirect."
```

---

## Task 4: app.py — API 라우트 일괄 전환 (그룹 2: 씬/이미지/오디오 mutation)

**Files:**
- Modify: `app.py` — POST/DELETE 위주 라우트 (~14개)

**배경**: mutation API라 회귀 위험 더 큼. 그룹 1과 동일 패턴이지만 변환 후 실제 mutation도 검증 필요.

- [ ] **Step 1: 대상 라우트 추출**

```bash
grep -n '@app\.\(post\|delete\|put\)("/api/p/{slug}' app.py
```

대상 예시:
- `/api/p/{slug}/scene/{scene_num}/select-image`
- `/api/p/{slug}/scene/{scene_num}/image-candidates`
- `/api/p/{slug}/images/versions/{scene_num}`
- `/api/p/{slug}/images/candidates/{scene_num}`
- `/api/p/{slug}/audio/...`
- `/api/p/{slug}/rebuild-manifest`
- `/api/p/{slug}/art-style`
- ... (실제 grep 결과에 따름)

- [ ] **Step 2: Task 3과 동일 패턴 적용**

각 핸들러에 대해 동일 변환 (path param 리네임 + resolver + redirect 분기). mutation API는 GET과 달리 body가 있을 수 있으나 redirect는 status 301로 method 보존되며 클라이언트가 동일 method로 재요청.

> **주의**: 일부 클라이언트(특히 fetch API)는 301에서 POST → GET 변환이 발생할 수 있음. **307 Temporary Redirect** 사용을 권장:
>
> ```python
> return RedirectResponse(url=..., status_code=307)
> ```
>
> 단, 일관성을 위해 GET 라우트(Task 3, Task 2)도 이 시점에 307로 통일하는 게 좋음. 다음 Step 참조.

- [ ] **Step 3: redirect status code 통일 (301 → 307)**

helper에는 status code가 없으므로 변경 불필요. 호출 site만 일괄 변경:

```bash
grep -rn "status_code=301" app.py
```

이전 Task에서 추가한 redirect를 모두 `307`로 교체. 이유: POST/PUT/DELETE의 method/body 보존.

> 단, `/projects/{project_ref}` 라우트(원래 있던 uuid → slug redirect)는 GET 전용이므로 301 유지해도 무방. 또는 함께 307로 통일.

- [ ] **Step 4: mutation 라우트 변환 후 수동 검증**

서버 기동 후:
```bash
# slug로 POST → 307 → uuid로 재요청 → 200
curl -X POST -H "Content-Type: application/json" -d '{"image_url":"x"}' \
  "http://localhost:8080/api/p/<slug>/scene/1/select-image" -L -sI | head -10
```

확인: 첫 응답 `307`, `Location: /api/p/<uuid>/...`, 두 번째 응답 `200`(또는 핸들러 정상 응답)

- [ ] **Step 5: grep 카운터 + 커밋**

```bash
grep -c '@app\..*"/api/p/{slug}' app.py  # 0이 되어야 함 (app.py 한정)
git add app.py
git commit -m "refactor(dashboard): API 라우트 그룹2 uuid 전환 + 307 redirect 통일

POST/DELETE 위주 ~14개 라우트 변환. 301 → 307로 method/body 보존."
```

---

## Task 5: scene_editor.py + design_presets.py + enrichment_routes.py

**Files:**
- Modify: `auto_agent/dashboard/scene_editor.py:19, 25` (APIRouter prefix) + 모든 핸들러
- Modify: `auto_agent/dashboard/design_presets.py:321, 389` (라우트 2개)
- Modify: `auto_agent/dashboard/enrichment_routes.py:34, 45, 62` (`{project_slug}` 3개)

- [ ] **Step 1: scene_editor.py — APIRouter prefix 변경**

`auto_agent/dashboard/scene_editor.py:19`:
```python
# 전
router = APIRouter(prefix="/api/p/{slug}/editor", tags=["scene-editor"])
# 후
router = APIRouter(prefix="/api/p/{project_ref}/editor", tags=["scene-editor"])
```

`auto_agent/dashboard/scene_editor.py:25`:
```python
# 전
manifest_router = _AR(prefix="/api/p/{slug}", tags=["manifest-utils"])
# 후
manifest_router = _AR(prefix="/api/p/{project_ref}", tags=["manifest-utils"])
```

- [ ] **Step 2: scene_editor.py 모든 핸들러 시그니처 변경**

각 핸들러에서:
- `slug: str` → `project_ref: str`
- 함수 본문 시작 부분 `pm.get_project(slug=slug)` → resolver + redirect 분기 (Task 3 패턴 동일)

핸들러가 많으므로 리스트 추출:
```bash
grep -n "^async def\|^def " auto_agent/dashboard/scene_editor.py | head -30
```

각 핸들러에 동일 변환. Request 파라미터가 없는 핸들러는 추가:
```python
async def some_handler(request: Request, project_ref: str, scene_num: int):
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    # ... 기존 로직
```

import 추가 (파일 상단):
```python
from fastapi.responses import RedirectResponse
from auto_agent.dashboard.project_ref import resolve_project_ref, canonical_uuid_url
```

- [ ] **Step 3: design_presets.py — 동일 패턴**

`auto_agent/dashboard/design_presets.py:321, 389` 두 라우트도 동일 변환.

- [ ] **Step 4: enrichment_routes.py — `{project_slug}` 처리**

`auto_agent/dashboard/enrichment_routes.py`의 3개 라우트는 path param 이름이 `{project_slug}`. 일관성을 위해 `{project_ref}`로 리네임 + 함수 시그니처 + 본문 변환.

- [ ] **Step 5: 서버 기동 후 통합 수동 검증**

```bash
python -m uvicorn app:app --port 8080 &
sleep 3
```

체크리스트(브라우저에서):
- [ ] uuid URL로 대시보드 진입 → 9개 탭 모두 클릭 (research, manuscript, storyboard, studio, upload, multi, version, agent, pipeline)
- [ ] slug URL로 진입 → 자동 redirect 후 위와 동일하게 동작
- [ ] 씬에디터 진입 → 저장 → 정상
- [ ] 이미지 교체 (스토리보드에서) → 정상
- [ ] design preset 적용 → 정상
- [ ] enrichment 큐 조회 → 정상

```bash
pkill -f "uvicorn app:app"
```

- [ ] **Step 6: grep 카운터 (전체 0 확인)**

```bash
grep -rn "{slug}" app.py auto_agent/dashboard/*.py | grep -E "@(app|router|manifest_router)\." | wc -l
# Expected: 0
grep -rn "{project_slug}" auto_agent/dashboard/*.py | grep -E "@(app|router)\." | wc -l
# Expected: 0
```

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/dashboard/scene_editor.py auto_agent/dashboard/design_presets.py auto_agent/dashboard/enrichment_routes.py
git commit -m "refactor(dashboard): scene_editor/design_presets/enrichment uuid 전환

scene_editor.py APIRouter prefix 2개 + 모든 핸들러,
design_presets 2개, enrichment {project_slug} 3개 변환.
Phase 1 백엔드 라우트 전환 완료."
```

---

## Task 6: Phase 1 회귀 검증 + 체크포인트

**Files:** 없음 (검증만)

- [ ] **Step 1: 자동 검증 (C) — grep 카운터**

```bash
echo "=== app.py slug 라우트 잔존 ===" && grep -c '@app\..*"/api/p/{slug}\|@app\..*"/p/{slug}' app.py
echo "=== dashboard slug 라우트 잔존 ===" && grep -rn "{slug}\|{project_slug}" auto_agent/dashboard/*.py | grep -E "@(app|router|manifest_router)\." | wc -l
echo "=== resolve_project_ref 호출 site ===" && grep -rn "resolve_project_ref" app.py auto_agent/dashboard/*.py | wc -l
```

Expected:
- app.py slug 라우트: 0
- dashboard slug 라우트: 0
- resolver 호출 site: 40+ (변환된 라우트 수)

- [ ] **Step 2: 단위 테스트 재실행**

```bash
python -m pytest tests/dashboard/test_project_ref.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 3: 수동 회귀 체크리스트 (A)**

서버 기동:
```bash
python -m uvicorn app:app --host 0.0.0.0 --port 8080 &
sleep 3
```

브라우저에서 (각 항목 ✓ 마킹):

**진입 경로 검증**
- [ ] uuid URL로 대시보드 진입: `http://localhost:8080/p/<uuid>` → 200
- [ ] slug URL로 진입: `http://localhost:8080/p/<slug>` → 자동 redirect → uuid URL로 표시
- [ ] 잘못된 ref: `http://localhost:8080/p/nonexistent` → 404

**탭별 동작 확인 (uuid URL 상태에서)**
- [ ] 리서치 탭 — 데이터 로드, wiki 보기
- [ ] 원고 탭 — 원고 로드, 저장 1회
- [ ] 스토리보드 탭 — 씬 목록, 이미지 교체 1회, 씬 split 1회
- [ ] 스튜디오 탭 — Remotion 미리보기 로드
- [ ] 업로드 탭 — release info 로드
- [ ] 멀티 탭 — multi-format 콘텐츠 로드
- [ ] 버전 탭 — 버전 히스토리
- [ ] 에이전트 탭
- [ ] 파이프라인 탭

**API 인코딩 회귀 검증**
- [ ] 한글 slug로 진입 후 storyboard 탭에서 이미지 교체 → 200 (이중 인코딩 발생 안 함)
- [ ] 씬에디터에서 저장 → 200 → manifest 재빌드 트리거 → 200

**(선택) Stage 3 렌더 1회**
- [ ] 작은 프로젝트 1개 Stage 3 완주 → 정상 .mp4 생성

```bash
pkill -f "uvicorn app:app"
```

- [ ] **Step 4: 회귀 결과 기록**

체크리스트 결과를 spec 파일에 기록(완료 정의 갱신용):

```bash
cat >> docs/superpowers/specs/2026-04-28-url-uuid-routing-design.md <<'EOF'

## Phase 1 완료 기록 (2026-04-28)

- [x] 백엔드 라우트 38(app.py) + 5(dashboard) + 3(enrichment) = 46개 전환
- [x] grep 카운터 0
- [x] resolve_project_ref 단위 테스트 통과
- [x] 수동 회귀 체크리스트 통과
- 다음 단계: Phase 2 (프론트 fetch 영역별 전환)
EOF
```

- [ ] **Step 5: Phase 1 완료 커밋 + 푸시**

```bash
git add docs/superpowers/specs/2026-04-28-url-uuid-routing-design.md
git commit -m "docs(spec): URL UUID Phase 1 완료 기록

백엔드 라우트 46개 전환 완료. grep 카운터 0, 회귀 검증 통과.
Phase 2(프론트) 진행 가능 상태."
git push
```

---

## Phase 1 완료 정의

- ✅ `resolve_project_ref()` helper + 단위 테스트 통과
- ✅ 모든 백엔드 라우트가 `{project_ref}` path param 사용
- ✅ slug 진입 시 자동 307(또는 GET 한정 301) → uuid URL redirect
- ✅ 대시보드 9개 탭 회귀 통과
- ✅ 이미지 교체 + 씬에디터 저장 등 mutation API 회귀 통과
- ✅ grep 카운터 0
- ✅ Phase 2 진행을 위한 깨끗한 상태 (프론트는 미변경, redirect로 자동 흡수 중)

---

## 다음 단계

Phase 2 플랜: `docs/superpowers/plans/2026-XX-XX-url-uuid-routing-phase2.md` (프론트 fetch 사이트 영역별 전환). Phase 1 완료 + 회귀 안정 확인 후 별도 세션에서 작성·실행.
