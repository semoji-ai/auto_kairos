# Stage 3 QA Persist + 재시도 축소 + enable_web_search 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** step_3b 재시도 시 이미지 중복 생성 문제 해결 — QA 결과를 image_assets.json에 persist하여 재시작 시 중복 검수/재생성 방지, 재시도 횟수 축소, banobanana2 enable_web_search 자동 판단 추가.

**Architecture:** image_assets.py에 QA 결과 저장 함수 추가 → assembly-director SKILL.md에서 1회 검수 후 결과 기록, 재시작 시 스킵 → 스토리보드에 미달 씬 배지 표시. enable_web_search는 scene_specs에 LLM이 기록하고 image_generate.py가 읽어 FAL 호출 시 전달.

**Tech Stack:** Python (image_assets.py, image_generate.py, runner.py), Jinja2 (HTML 템플릿), pytest

---

## 파일 변경 목록

| 파일 | 변경 유형 | 내용 |
|------|---------|------|
| `auto_agent/tools/image_assets.py` | 수정 | `set_qa_result()`, `get_qa_result()` 추가 |
| `auto_agent/tools/image_generate.py` | 수정 | `_infer_web_search()` 추가, `_build_scene_fal_input()`에 `enable_web_search` 전달 |
| `auto_agent/orchestrator/runner.py` | 수정 | assembly-director max_attempts 3 → 2 |
| `auto_agent/data/skills/agents/assembly-director/SKILL.md` | 수정 | Phase B-3 QA 1회 규칙, persist 기록, 재생성 제거 |
| `auto_agent/data/skills/agents/script-director/SKILL.md` | 수정 | `enable_web_search` 판단 기준 추가 |
| `auto_agent/dashboard/helpers.py` | 수정 | `enrich_scenes_with_media()`에 qa 필드 병합 |
| `auto_agent/dashboard/templates/partials/_storyboard_scene.html` | 수정 | QA 미달 배지 추가 |
| `auto_agent/dashboard/templates/styles.html` | 수정 | `.qa-badge` CSS 추가 |
| `tests/test_image_assets_qa.py` | 생성 | QA persist 함수 테스트 |
| `tests/test_image_generate_web_search.py` | 생성 | enable_web_search 판단 테스트 |

---

## Task 1: image_assets.py — QA persist 함수 추가

**Files:**
- Modify: `auto_agent/tools/image_assets.py`
- Create: `tests/test_image_assets_qa.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# tests/test_image_assets_qa.py
import json
import tempfile
from pathlib import Path
import pytest
from auto_agent.tools import image_assets


@pytest.fixture
def images_dir(tmp_path):
    """임시 images 디렉토리 (image_assets.json 없음)."""
    return tmp_path / "images"


def _init_scene(images_dir: Path, scene_num: int):
    """테스트용 씬 등록."""
    images_dir.mkdir(exist_ok=True)
    image_assets.add_version(images_dir, scene_num, f"generated/scene_{scene_num:03d}_gen_01.png", "generate")


class TestSetQaResult:
    def test_passed_true(self, images_dir):
        _init_scene(images_dir, 1)
        image_assets.set_qa_result(images_dir, 1, passed=True)
        qa = image_assets.get_qa_result(images_dir, 1)
        assert qa is not None
        assert qa["passed"] is True
        assert qa.get("issues") == []
        assert "checked_at" in qa

    def test_passed_false_with_issues(self, images_dir):
        _init_scene(images_dir, 2)
        issues = ["캐릭터 의상 불일치", "프롬프트 미매칭"]
        image_assets.set_qa_result(images_dir, 2, passed=False, issues=issues)
        qa = image_assets.get_qa_result(images_dir, 2)
        assert qa["passed"] is False
        assert qa["issues"] == issues

    def test_overwrite_existing(self, images_dir):
        _init_scene(images_dir, 3)
        image_assets.set_qa_result(images_dir, 3, passed=False, issues=["issue1"])
        image_assets.set_qa_result(images_dir, 3, passed=True)
        qa = image_assets.get_qa_result(images_dir, 3)
        assert qa["passed"] is True

    def test_thread_safe(self, images_dir):
        import threading
        _init_scene(images_dir, 4)
        errors = []

        def write():
            try:
                image_assets.set_qa_result(images_dir, 4, passed=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


class TestGetQaResult:
    def test_returns_none_when_no_qa(self, images_dir):
        _init_scene(images_dir, 5)
        assert image_assets.get_qa_result(images_dir, 5) is None

    def test_returns_none_for_unknown_scene(self, images_dir):
        images_dir.mkdir(exist_ok=True)
        assert image_assets.get_qa_result(images_dir, 999) is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m pytest tests/test_image_assets_qa.py -v 2>&1 | head -30
```

Expected: `ImportError` 또는 `AttributeError: module 'image_assets' has no attribute 'set_qa_result'`

- [ ] **Step 3: image_assets.py에 함수 구현**

`auto_agent/tools/image_assets.py` 파일 끝에 추가 (270번 줄 다음):

```python
def set_qa_result(images_dir: Path, scene_num: int, passed: bool, issues: list | None = None) -> None:
    """QA 결과를 image_assets.json에 기록. Thread-safe.

    Args:
        images_dir: images/ 디렉토리 경로
        scene_num: 씬 번호
        passed: True=통과, False=미달
        issues: 미달 이유 목록 (passed=False일 때)
    """
    from datetime import datetime
    with _file_lock:
        data = _load(images_dir)
        scene = _get_scene(data, scene_num)
        scene["qa"] = {
            "passed": passed,
            "issues": issues or [],
            "checked_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save(images_dir, data)


def get_qa_result(images_dir: Path, scene_num: int) -> dict | None:
    """qa 필드 반환. qa 기록 없으면 None.

    Returns:
        {"passed": bool, "issues": list, "checked_at": str} 또는 None
    """
    data = _load(images_dir)
    for s in data["scenes"]:
        if s["sceneNumber"] == scene_num:
            return s.get("qa") or None
    return None
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_image_assets_qa.py -v
```

Expected:
```
tests/test_image_assets_qa.py::TestSetQaResult::test_passed_true PASSED
tests/test_image_assets_qa.py::TestSetQaResult::test_passed_false_with_issues PASSED
tests/test_image_assets_qa.py::TestSetQaResult::test_overwrite_existing PASSED
tests/test_image_assets_qa.py::TestSetQaResult::test_thread_safe PASSED
tests/test_image_assets_qa.py::TestGetQaResult::test_returns_none_when_no_qa PASSED
tests/test_image_assets_qa.py::TestGetQaResult::test_returns_none_for_unknown_scene PASSED
6 passed
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/image_assets.py tests/test_image_assets_qa.py
git commit -m "feat: image_assets에 QA persist 함수 추가 (set_qa_result, get_qa_result)"
```

---

## Task 2: runner.py — assembly-director 재시도 횟수 축소

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:4767`

- [ ] **Step 1: 변경**

`auto_agent/orchestrator/runner.py` 4767번 줄:

```python
# 변경 전
        if agent == "assembly-director" or step_name == "assembly":
            return 3

# 변경 후
        if agent == "assembly-director" or step_name == "assembly":
            return 2  # 최초 1회 + 재시도 1회 (QA persist로 중복 생성 방지됨)
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "fix: assembly-director max_attempts 3→2 (QA persist와 함께 중복 생성 방지)"
```

---

## Task 3: image_generate.py — enable_web_search 자동 판단

**Files:**
- Modify: `auto_agent/tools/image_generate.py`
- Create: `tests/test_image_generate_web_search.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# tests/test_image_generate_web_search.py
"""
_infer_web_search() 함수 단위 테스트.
실제 FAL API는 호출하지 않음.
"""
import pytest
from datetime import datetime
from unittest.mock import patch


# 현재 연도와 전년도 (규칙 기반 fallback 판단 기준)
CURRENT_YEAR = str(datetime.now().year)
PREV_YEAR = str(datetime.now().year - 1)


def _infer(scene: dict, is_search_fallback: bool = False) -> bool:
    """테스트용 래퍼 — image_generate 모듈에서 직접 임포트."""
    from auto_agent.tools.image_generate import _infer_web_search
    return _infer_web_search(scene, is_search_fallback)


class TestInferWebSearch:
    def test_search_fallback_always_true(self):
        scene = {"imageAsset": {"prompt": "만화 캐릭터"}}
        assert _infer(scene, is_search_fallback=True) is True

    def test_current_year_in_prompt(self):
        scene = {"imageAsset": {"prompt": f"{CURRENT_YEAR}년 이란 핵시설 공습"}}
        assert _infer(scene) is True

    def test_prev_year_in_prompt(self):
        scene = {"imageAsset": {"prompt": f"{PREV_YEAR}년 정상회담"}}
        assert _infer(scene) is True

    def test_cartoon_scene_false(self):
        scene = {"imageAsset": {"prompt": "귀여운 만화 캐릭터가 뛰어다니는 장면"}}
        assert _infer(scene) is False

    def test_empty_prompt_false(self):
        scene = {"imageAsset": {}}
        assert _infer(scene) is False

    def test_no_image_asset_false(self):
        scene = {}
        assert _infer(scene) is False


class TestBuildSceneFalInputWebSearch:
    """_build_scene_fal_input()이 enable_web_search를 FAL input에 포함하는지 확인."""

    def _make_scene(self, enable_web_search=None, prompt="테스트 장면"):
        scene = {
            "imageAsset": {
                "source": "generate",
                "prompt": prompt,
                "aspectRatio": "16:9",
            }
        }
        if enable_web_search is not None:
            scene["imageAsset"]["enable_web_search"] = enable_web_search
        return scene

    def _call(self, scene, is_search_fallback=False, tmp_path=None):
        from pathlib import Path
        import tempfile, json
        from auto_agent.tools.image_generate import _build_scene_fal_input

        # art_style.json mock
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "art_style.json").write_text(json.dumps({
                "scene_style_description": "test style",
                "technical": {"critical_requirements": []},
                "reference_image": "",
            }), encoding="utf-8")
            with patch("auto_agent.tools.image_generate._translate_to_english", side_effect=lambda x: x):
                endpoint, fal_input = _build_scene_fal_input(
                    scene, p, is_search_fallback=is_search_fallback
                )
        return fal_input

    def test_explicit_true_passed(self):
        scene = self._make_scene(enable_web_search=True)
        fal_input = self._call(scene)
        assert fal_input.get("enable_web_search") is True

    def test_explicit_false_passed(self):
        scene = self._make_scene(enable_web_search=False)
        fal_input = self._call(scene)
        assert fal_input.get("enable_web_search") is False

    def test_none_uses_infer_fallback(self):
        scene = self._make_scene(enable_web_search=None, prompt="귀여운 만화 캐릭터")
        fal_input = self._call(scene)
        assert fal_input.get("enable_web_search") is False

    def test_search_fallback_enables_web_search(self):
        scene = self._make_scene(enable_web_search=None, prompt="귀여운 만화")
        fal_input = self._call(scene, is_search_fallback=True)
        assert fal_input.get("enable_web_search") is True
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_image_generate_web_search.py -v 2>&1 | head -30
```

Expected: `ImportError` 또는 `TypeError` (`_infer_web_search` 없음, `_build_scene_fal_input` 시그니처 불일치)

- [ ] **Step 3: image_generate.py 수정**

`auto_agent/tools/image_generate.py` 상단 import 섹션에 추가 (기존 `from datetime import ...` 있으면 생략):

```python
from datetime import datetime
```

`_build_scene_fal_input()` 함수 정의 바로 앞에 추가:

```python
def _infer_web_search(scene: dict, is_search_fallback: bool) -> bool:
    """enable_web_search 명시 없을 때 규칙 기반 판단.

    True 조건:
    - search fallback된 씬 (원래 실사가 필요했던 씬)
    - imageAsset.prompt에 최근 2년 연도가 포함된 경우 (뉴스/사건 씬)
    """
    if is_search_fallback:
        return True
    prompt = (scene.get("imageAsset") or {}).get("prompt", "")
    current_year = str(datetime.now().year)
    prev_year = str(datetime.now().year - 1)
    return current_year in prompt or prev_year in prompt
```

`_build_scene_fal_input()` 함수 시그니처 변경 (is_search_fallback 파라미터 추가):

```python
def _build_scene_fal_input(
    scene: dict,
    project_dir: Path,
    char_paths: Optional[Dict[str, Optional[Path]]] = None,
    style_path: Optional[str] = None,
    is_search_fallback: bool = False,          # ← 추가
) -> tuple[str, dict]:
```

`_build_scene_fal_input()` 함수 내부 끝 부분 (712번 줄 fal_input 생성 직후) 수정:

```python
    # 변경 전 (712-715번 줄)
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return endpoint, fal_input

    # 변경 후
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls

    # enable_web_search: scene_specs 명시값 우선, 없으면 규칙 기반
    explicit_web_search = (scene.get("imageAsset") or {}).get("enable_web_search")
    fal_input["enable_web_search"] = (
        explicit_web_search if explicit_web_search is not None
        else _infer_web_search(scene, is_search_fallback)
    )

    return endpoint, fal_input
```

- [ ] **Step 4: image_batch_module.py에서 is_search_fallback 전달**

`auto_agent/modules/image_batch_module.py`에서 `_build_scene_fal_input()` 호출 시 `is_search_fallback` 파라미터 추가.

검색:
```bash
grep -n "_build_scene_fal_input\|image_generate" auto_agent/modules/image_batch_module.py
```

search fallback generate 호출 부분을 찾아 `is_search_fallback=True` 추가:

```python
# search fallback → generate 전환 시
endpoint, fal_input = _build_scene_fal_input(
    scene, project_dir, char_paths=char_paths, style_path=style_path,
    is_search_fallback=True,   # ← 추가
)

# 일반 generate 씬
endpoint, fal_input = _build_scene_fal_input(
    scene, project_dir, char_paths=char_paths, style_path=style_path,
    is_search_fallback=False,  # 기본값이지만 명시
)
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_image_generate_web_search.py -v
```

Expected:
```
tests/test_image_generate_web_search.py::TestInferWebSearch::test_search_fallback_always_true PASSED
tests/test_image_generate_web_search.py::TestInferWebSearch::test_current_year_in_prompt PASSED
tests/test_image_generate_web_search.py::TestInferWebSearch::test_prev_year_in_prompt PASSED
tests/test_image_generate_web_search.py::TestInferWebSearch::test_cartoon_scene_false PASSED
tests/test_image_generate_web_search.py::TestInferWebSearch::test_empty_prompt_false PASSED
tests/test_image_generate_web_search.py::TestInferWebSearch::test_no_image_asset_false PASSED
tests/test_image_generate_web_search.py::TestBuildSceneFalInputWebSearch::test_explicit_true_passed PASSED
tests/test_image_generate_web_search.py::TestBuildSceneFalInputWebSearch::test_explicit_false_passed PASSED
tests/test_image_generate_web_search.py::TestBuildSceneFalInputWebSearch::test_none_uses_infer_fallback PASSED
tests/test_image_generate_web_search.py::TestBuildSceneFalInputWebSearch::test_search_fallback_enables_web_search PASSED
10 passed
```

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/tools/image_generate.py auto_agent/modules/image_batch_module.py tests/test_image_generate_web_search.py
git commit -m "feat: banobanana2 enable_web_search 자동 판단 추가 (_infer_web_search)"
```

---

## Task 4: 스토리보드 QA 배지

**Files:**
- Modify: `auto_agent/dashboard/helpers.py` (enrich_scenes_with_media)
- Modify: `auto_agent/dashboard/templates/partials/_storyboard_scene.html`
- Modify: `auto_agent/dashboard/templates/styles.html`

- [ ] **Step 1: helpers.py — enrich_scenes_with_media에 qa 필드 병합**

`auto_agent/dashboard/helpers.py`에서 `enrich_scenes_with_media()` 함수의 씬 루프 내부(이미지/오디오 URL 추가 직후)에 qa 병합 추가.

기존 패턴 (약 380번 줄 부근):
```python
        scene["_image_url"] = get_scene_image_url(...)
        scene["_audio_url"] = get_scene_audio_url(...)
```

이 블록 뒤에 추가:
```python
        # QA 결과 병합
        try:
            from auto_agent.tools import image_assets as _ia
            from pathlib import Path as _Path
            _images_dir = _Path(output_dir) / "images"
            _qa = _ia.get_qa_result(_images_dir, scene.get("sceneNumber", 0))
            if _qa:
                scene["_qa"] = _qa
        except Exception:
            pass
```

- [ ] **Step 2: _storyboard_scene.html — QA 배지 추가**

`auto_agent/dashboard/templates/partials/_storyboard_scene.html` 의 `<div class="tags">` 블록 (174번 줄 부근) 직후에 추가:

```html
      {% if scene._qa and not scene._qa.passed %}
        <span class="qa-badge" title="{{ scene._qa.issues | join(', ') }}">⚠ QA 미달</span>
      {% endif %}
```

결과:
```html
    <div class="tags">
      {% if _layout %}<span class="layout-badge">{{ _layout }}</span>{% endif %}
      {% if _motion %}<span class="viz-badge">🎬 {{ _motion }}</span>{% endif %}
      {% if _mood %}<span class="mood-badge">{{ _mood }}</span>{% endif %}
      {% if scene._qa and not scene._qa.passed %}
        <span class="qa-badge" title="{{ scene._qa.issues | join(', ') }}">⚠ QA 미달</span>
      {% endif %}
      ...
    </div>
```

- [ ] **Step 3: styles.html — .qa-badge CSS 추가**

`auto_agent/dashboard/templates/styles.html`의 `.channel-badge` 블록 (59번 줄) 뒤에 추가:

```css
.qa-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #EF4444;
  color: #FFFFFF;
  font-weight: 600;
  cursor: help;
  letter-spacing: 0.3px;
}
```

- [ ] **Step 4: 대시보드 서버 재시작 후 수동 확인**

```bash
# image_assets.json에 qa 미달 씬 수동 삽입 후 대시보드 확인
python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

테스트 데이터 삽입 (`output/*/images/image_assets.json`의 아무 씬에):
```json
"qa": {
  "passed": false,
  "issues": ["캐릭터 의상 불일치"],
  "checked_at": "2026-04-15T10:00:00"
}
```

대시보드 스토리보드 탭에서 해당 씬 카드에 빨간 `⚠ QA 미달` 배지 확인.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/helpers.py \
        auto_agent/dashboard/templates/partials/_storyboard_scene.html \
        auto_agent/dashboard/templates/styles.html
git commit -m "feat: 스토리보드에 QA 미달 씬 배지 표시"
```

---

## Task 5: assembly-director SKILL.md — QA 1회 규칙 + persist

**Files:**
- Modify: `auto_agent/data/skills/agents/assembly-director/SKILL.md` (Phase B-3 섹션, 303-343번 줄)

- [ ] **Step 1: Phase B-3 섹션 교체**

303번 줄 `**B-3. ⭐ 이미지 품질 검수 (LLM의 핵심 가치 단계)**` 부터 343번 줄까지를 아래 내용으로 교체:

```markdown
**B-3. ⭐ 이미지 품질 검수 (씬당 1회, persist)**

배치 생성 완료 후 모든 selected 이미지를 Read 도구로 멀티모달 검수합니다.

**⚠️ 핵심 규칙:**
- 씬당 **1회만** 검수 — 재검수/재생성 없음
- 재시작 시 이미 검수된 씬은 **스킵** (이전 결과 유지)
- 미달 씬은 스토리보드에 표시되며 사용자가 수동 처리

```
각 씬에 대해:

1. image_assets.json에서 qa 결과 확인:
   python3 -c "
   from auto_agent.tools import image_assets
   from pathlib import Path
   qa = image_assets.get_qa_result(Path('$PROJECT_DIR/images'), SCENE_NUM)
   print(qa)
   "
   → qa가 있으면 (passed 여부 무관) 스킵 — 다음 씬으로

2. qa 없으면 Read 도구로 이미지 직접 검수:
   Read(file_path="$PROJECT_DIR/images/generated/scene_NNN_gen_01.png")

3. 검수 체크리스트:
   ┌─ 캐릭터 일관성: 다른 씬 동일 인물과 얼굴/의상/나이대 일치?
   ├─ prompt 의도: scene_specs.imageAsset.prompt 내용이 이미지에 보이는가?
   ├─ placement 적합성: fullscreen(16:9 꽉 참) / side(자연스러운 세로) / badge(중앙 집중)
   └─ 품질: 워터마크, 흐림, 한글 텍스트 깨짐, 잘못된 객체

4. 결과 기록 (반드시 실행):
   # 통과 시
   python3 -c "
   from auto_agent.tools import image_assets
   from pathlib import Path
   image_assets.set_qa_result(Path('$PROJECT_DIR/images'), SCENE_NUM, passed=True)
   "

   # 미달 시 (재생성 없이 기록만)
   python3 -c "
   from auto_agent.tools import image_assets
   from pathlib import Path
   image_assets.set_qa_result(
       Path('$PROJECT_DIR/images'), SCENE_NUM,
       passed=False,
       issues=['캐릭터 의상 불일치', '프롬프트 미매칭']  # 실제 이유 기록
   )
   "
```

미달 씬은 스토리보드에서 ⚠ QA 미달 배지로 표시됩니다. 재생성하지 마세요.
```

- [ ] **Step 2: Phase C (검수+보정) 섹션에서 이미지 재생성 부분 제거**

Phase C (464번 줄 부근) 이미지 검수 항목에서 재생성 관련 내용 제거:

```markdown
이미지 검수:
  - Phase B-3에서 QA 완료됨 — 이 단계에서 추가 검수/재생성 없음
  - qa.passed == false 씬은 스토리보드에 배지 표시됨 (사용자가 수동 처리)
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/agents/assembly-director/SKILL.md
git commit -m "feat: assembly-director QA 1회+persist 규칙 적용, 재생성 루프 제거"
```

---

## Task 6: script-director SKILL.md — enable_web_search 기준 추가

**Files:**
- Modify: `auto_agent/data/skills/agents/script-director/SKILL.md`

- [ ] **Step 1: imageAsset 필드 작성 섹션 찾기**

```bash
grep -n "imageAsset\|source.*generate\|source.*search" \
  auto_agent/data/skills/agents/script-director/SKILL.md | head -20
```

- [ ] **Step 2: imageAsset 필드 설명 섹션에 enable_web_search 추가**

`imageAsset` 필드 목록이 있는 위치에 다음 추가:

```markdown
#### `imageAsset.enable_web_search` (선택 필드)

FAL banobanana2 이미지 생성 시 웹 최신 정보 참조 여부.

| 씬 유형 | 값 |
|--------|-----|
| 실존 인물 등장 (정치인, 유명인, 역사적 인물) | `true` |
| 실제 사건/뉴스 장면 (전쟁, 재난, 정상회담, 사고) | `true` |
| 실제 장소 (랜드마크, 도시 전경, 특정 건물) | `true` |
| 순수 일러스트/만화/아트 씬 | `false` |
| 데이터 시각화, 차트 배경, 추상 씬 | `false` |
| 판단 불명확 | 생략 (시스템이 자동 판단) |

생략하면 `image_generate.py`가 prompt의 최근 연도 포함 여부로 자동 판단합니다.
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/agents/script-director/SKILL.md
git commit -m "docs: script-director에 enable_web_search 판단 기준 추가"
```

---

## Task 7: 전체 테스트 + 최종 커밋

- [ ] **Step 1: 전체 테스트 실행**

```bash
.venv/bin/python -m pytest tests/test_image_assets_qa.py tests/test_image_generate_web_search.py -v
```

Expected: 16 passed

- [ ] **Step 2: 기존 image_assets 테스트 회귀 확인**

```bash
.venv/bin/python -m pytest tests/test_image_batch_module.py -v
```

Expected: 기존 테스트 모두 통과

- [ ] **Step 3: 푸시**

```bash
git push
```

---

## Self-Review

**Spec coverage:**
- ✅ QA persist — Task 1 (image_assets.py), Task 5 (SKILL.md)
- ✅ 스토리보드 QA 배지 — Task 4
- ✅ step_3b 재시도 2회 — Task 2
- ✅ enable_web_search 자동 판단 — Task 3
- ✅ script-director 판단 기준 — Task 6

**Placeholder scan:** 없음. 모든 코드 블록 완성.

**Type consistency:**
- `set_qa_result(images_dir, scene_num, passed, issues)` — Task 1 정의, Task 5 Bash 호출에서 동일 시그니처 사용 ✅
- `get_qa_result(images_dir, scene_num) → dict | None` — Task 1 정의, Task 4 helpers.py에서 동일 시그니처 사용 ✅
- `_infer_web_search(scene, is_search_fallback)` — Task 3 정의, 테스트에서 동일 시그니처 사용 ✅
- `_build_scene_fal_input(..., is_search_fallback=False)` — Task 3 시그니처 변경, 테스트에서 동일하게 호출 ✅
- `scene["_qa"]` — Task 4 helpers.py에서 `_qa` 키 사용, 템플릿에서 `scene._qa`로 접근 ✅
