# adobe Stage1-2 P4b — 씬 분석 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** final_manuscript.md를 `<!--SCENE-->` 마커로 결정적 분할하고 씬별 연출을 LLM으로 결정해 adobe 네이티브 `scenes.json`(Stage 3 입력)을 산출한다. 런타임 v3 의존 0.

**Architecture:** P4a manuscript-write 스킬이 씬 경계 `<!--SCENE-->`(+선택 `<!--CHARS: ...-->`)를 삽입하도록 보정한다. P4b `backend/scene_analysis.py`가 마커로 narration을 결정적 분할(정확한 부분문자열)하고, scene-analyze 스킬(llm)로 씬별 연출만 받아 zip한 뒤 기존 `backend/v3_import._map_scene`로 adobe scene을 정규화하고 `scenes.ensure_scene_ids`로 sceneId를 발급한다. 단일 패스(래칫 없음).

**Tech Stack:** Python stdlib + `backend.llm` + 재사용 `backend.v3_import._map_scene`·`backend.scenes.ensure_scene_ids`. 테스트는 pytest + monkeypatch(llm, 실 LLM 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트).

**재사용 계약:**
- `backend.v3_import._map_scene(scene_dict) -> adobe_scene` — sceneNumber/title/narration/visual_summary/image_prompt/characters/(narration_tts,duration_estimate_sec) 정규화.
- `backend.scenes.ensure_scene_ids(proj_dir: Path) -> dict` — 모든 씬에 sceneId 발급, scenes.json 저장.

**계약(전 태스크 고정):**
- `split_manuscript(text: str) -> list[dict]` → `[{narration, characters}]`
- `analyze_scenes(proj_dir, *, on_event=None) -> {scenes: str, count: int} | {error: str}`

---

## Task 1: P4a manuscript-write 마커 보정

**Files:**
- Modify: `skills/manuscript-write/SKILL.md`
- Test: `tests/test_manuscript_write_markers.py`

- [ ] **Step 1: Write the failing test** — `tests/test_manuscript_write_markers.py`:

```python
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "manuscript-write" / "SKILL.md"


def test_skill_instructs_scene_marker():
    t = SKILL.read_text(encoding="utf-8")
    assert "<!--SCENE-->" in t                       # 씬 경계 마커 삽입 지시 존재
    assert "마커는 사용하지 않습니다" not in t       # 옛 '마커 불필요' 문구 제거됨
    assert "불필요" not in t.split("출력 규칙")[-1].split("절대 금지")[0] or "<!--SCENE-->" in t
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_write_markers.py -v`
Expected: FAIL — 현재 스킬은 `<!--SCENE-->`가 없고 "마커는 사용하지 않습니다"가 있음.

- [ ] **Step 3: `skills/manuscript-write/SKILL.md` 보정** — "글쓰기 원칙"의 한 호흡 줄과 "출력 규칙"의 마커 금지 줄을 교체.

3a. 다음 줄을 찾는다:
```
- **한 호흡 prose**: 씬 구분 없이 자연스럽게 흘러가는 단일 본문.
```
아래로 교체:
```
- **한 호흡 prose + 씬 마커**: 자연스럽게 흘러가는 본문을 쓰되, 시각적으로 전환되는 자연스러운 씬 경계마다 단독 줄 `<!--SCENE-->`를 삽입하라. 분량 기준 분당 4~8씬이 되도록 나눈다.
```

3b. "출력 규칙"의 다음 두 줄을 찾는다:
```
- `---`와 `# Ch N.` 마커는 사용하지 않습니다. 이 스킬은 순수 prose만 작성합니다.
- 씬 분할 마커(`---`), 챕터 마커(`# Ch N.`), 캐릭터 마커(`<!-- chars: -->`) 불필요.
```
아래로 교체:
```
- 씬 경계는 단독 줄 `<!--SCENE-->`로 표시한다(렌더 시 비표시 HTML 주석). `# Ch N.` 챕터 마커는 쓰지 않는다.
- 특정 씬에 등장 캐릭터를 명시하려면 그 씬 안에 `<!--CHARS: 이름1, 이름2-->` 줄을 넣을 수 있다(선택).
- `<!--SCENE-->`/`<!--CHARS-->` 외에는 마크다운 prose만. 첫 씬 앞·마지막 씬 뒤에는 `<!--SCENE-->`를 두지 않는다.
```

- [ ] **Step 4: Run test**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_write_markers.py -v`
Expected: 1 passed. Full suite → all pass.

- [ ] **Step 5: Commit**

```bash
git add skills/manuscript-write/SKILL.md tests/test_manuscript_write_markers.py
git commit -m "feat(manuscript): write 스킬에 씬 경계 <!--SCENE--> 마커 삽입 지시(P4b 결정적 분할용)"
```

---

## Task 2: scene_specs 스키마 + split_manuscript

**Files:**
- Create: `backend/schemas/scene_specs.schema.json`
- Create: `backend/scene_analysis.py`
- Test: `tests/test_scene_split.py`

- [ ] **Step 1: Create `backend/schemas/scene_specs.schema.json`** EXACTLY:

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["scenes"],
  "properties": {
    "scenes": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true,
        "properties": {
          "visual_summary": { "type": "string" },
          "image_prompt": { "type": "string" },
          "characters": { "type": "array" },
          "layout": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write the failing test** — `tests/test_scene_split.py`:

```python
from backend import scene_analysis


def test_split_two_scenes():
    text = "첫 씬 내레이션.\n<!--SCENE-->\n둘째 씬 내레이션."
    segs = scene_analysis.split_manuscript(text)
    assert len(segs) == 2
    assert segs[0]["narration"] == "첫 씬 내레이션."
    assert segs[1]["narration"] == "둘째 씬 내레이션."
    assert segs[0]["characters"] == []


def test_split_extracts_chars_and_strips_marker():
    text = "본문 한 줄.\n<!--CHARS: 소년, 의사-->\n이어지는 본문."
    segs = scene_analysis.split_manuscript(text)
    assert len(segs) == 1
    assert segs[0]["characters"] == ["소년", "의사"]
    assert "<!--CHARS" not in segs[0]["narration"]
    assert "본문 한 줄." in segs[0]["narration"] and "이어지는 본문." in segs[0]["narration"]


def test_split_no_marker_single_scene():
    segs = scene_analysis.split_manuscript("마커 없는 원고 전체.")
    assert len(segs) == 1 and segs[0]["narration"] == "마커 없는 원고 전체."


def test_split_drops_empty_segments():
    text = "씬1.\n<!--SCENE-->\n\n<!--SCENE-->\n씬3."
    segs = scene_analysis.split_manuscript(text)
    assert [s["narration"] for s in segs] == ["씬1.", "씬3."]
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_split.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.scene_analysis`.

- [ ] **Step 4: Create `backend/scene_analysis.py`** with EXACTLY this content:

```python
"""씬 분석 (adobe 독립 Stage1-2 P4b) — final_manuscript.md를 마커로 분할하고
씬별 연출(LLM)을 붙여 adobe 네이티브 scenes.json 산출. 런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import llm

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
_SCENE_SCHEMA = _SCHEMAS / "scene_specs.schema.json"

_SCENE_RE = re.compile(r"(?m)^[ \t]*<!--\s*SCENE\s*-->[ \t]*$")
_CHARS_RE = re.compile(r"(?m)^[ \t]*<!--\s*CHARS:\s*(.*?)\s*-->[ \t]*$")


def _load_skill(name: str) -> str:
    md = _SKILLS / name / "SKILL.md"
    if not md.is_file():
        return f"skill: {name}"
    text = md.read_text(encoding="utf-8")
    if text.startswith("---"):              # YAML frontmatter 제거(프롬프트 노이즈 방지)
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip("\n")
    return text


def _read(proj_dir: Path, name: str) -> str:
    p = proj_dir / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def split_manuscript(text: str) -> list:
    """<!--SCENE-->로 결정적 분할 → [{narration, characters}]. <!--CHARS-->는 추출·제거.
    마커 없으면 전체가 1씬. 빈 세그먼트는 버림."""
    segs: list = []
    for part in _SCENE_RE.split(text or ""):
        chars: list = []
        mm = _CHARS_RE.search(part)
        if mm:
            chars = [c.strip() for c in mm.group(1).split(",") if c.strip()]
            part = _CHARS_RE.sub("", part)
        narration = part.strip()
        if narration:
            segs.append({"narration": narration, "characters": chars})
    return segs
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_split.py -v`
Expected: 4 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/scene_specs.schema.json backend/scene_analysis.py tests/test_scene_split.py
git commit -m "feat(scene): scene_specs 스키마 + split_manuscript(마커 결정적 분할)"
```

---

## Task 3: scene-analyze 스킬 + analyze_scenes

**Files:**
- Create: `skills/scene-analyze/SKILL.md`, `skills/scene-analyze/skill.json`
- Modify: `backend/scene_analysis.py` (add `_direct_scenes`, `analyze_scenes`)
- Test: `tests/test_scene_analyze.py`

- [ ] **Step 1: scene-analyze 스킬 이식** — Create `skills/scene-analyze/SKILL.md` porting the **chapters mode**(씬 연출 결정 부분) of `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/script-director/SKILL.md`. 적응: 씬 경계는 이미 결정됨(번호 매겨진 narration 목록이 프롬프트로 주입됨) — **narration은 절대 다시 쓰지 말 것**. 각 씬에 대해 **연출만** 결정: `visual_summary`(한 줄 시각 요약), `image_prompt`(이미지 생성용 묘사), `characters`(등장 인물명 배열), `layout`(선택: headline_only/items_list/metric_spotlight/quote/map/cinematic 중 제안). 출력은 JSON `{"scenes":[{visual_summary, image_prompt, characters, layout}]}` — **입력 씬과 같은 개수·같은 순서**, narration 미포함. v3 Task/CLI/파일읽기 제거. 한국어 규칙(가나·한자 금지).

`skills/scene-analyze/skill.json`:
```json
{ "name": "scene-analyze", "inputs": ["final_manuscript.md", "editorial_brief.json"], "output": "scene_specs.json", "output_kind": "json" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_scene_analyze.py`:

```python
import json
from pathlib import Path
from backend import scene_analysis, llm


def _setup(tmp_path, manuscript):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")


def _patch_direct(monkeypatch, scenes):
    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)


def test_analyze_scenes_builds_scenes_json(tmp_path, monkeypatch):
    _setup(tmp_path, "첫 씬.\n<!--SCENE-->\n둘째 씬.")
    _patch_direct(monkeypatch, [
        {"visual_summary": "공장 외경", "image_prompt": "1933 공장", "characters": []},
        {"visual_summary": "창업자 클로즈업", "image_prompt": "유일한 박사", "characters": ["유일한"]}])
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 2
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    s = data["scenes"]
    assert s[0]["narration"] == "첫 씬." and s[0]["visual_summary"] == "공장 외경"
    assert s[1]["narration"] == "둘째 씬." and s[1]["sceneNumber"] == 2
    assert all(sc.get("sceneId") for sc in s)        # ensure_scene_ids 발급
    assert s[1]["characters"] == ["유일한"]


def test_analyze_scenes_marker_chars_win(tmp_path, monkeypatch):
    _setup(tmp_path, "씬.\n<!--CHARS: 소년-->\n본문.")
    _patch_direct(monkeypatch, [{"visual_summary": "v", "image_prompt": "p", "characters": ["딴사람"]}])
    scene_analysis.analyze_scenes(tmp_path)
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["characters"] == ["소년"]   # 마커 우선


def test_analyze_scenes_direction_count_mismatch(tmp_path, monkeypatch):
    _setup(tmp_path, "씬1.\n<!--SCENE-->\n씬2.\n<!--SCENE-->\n씬3.")
    _patch_direct(monkeypatch, [{"visual_summary": "v1", "image_prompt": "p1"}])  # 1개만
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 3                           # 부족분은 빈 연출로 채움
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["visual_summary"] == "v1"
    assert data["scenes"][2]["narration"] == "씬3."


def test_analyze_scenes_llm_failure_fallback(tmp_path, monkeypatch):
    _setup(tmp_path, "씬1.\n<!--SCENE-->\n씬2.")
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 2                           # 연출 실패해도 narration만으로 생성
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["narration"] == "씬1."


def test_analyze_scenes_no_manuscript_errors(tmp_path):
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r.get("error")
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_analyze.py -v`
Expected: FAIL — `analyze_scenes` 부재.

- [ ] **Step 4: Add `_direct_scenes` + `analyze_scenes` to `backend/scene_analysis.py`** (append) with EXACTLY:

```python
def _direct_scenes(proj_dir: Path, segments: list, *, on_event=None) -> list:
    """scene-analyze 스킬로 씬별 연출만 받음. 입력 순서 보존 리스트. 실패 시 []."""
    out = proj_dir / "scene_specs.json"
    narr = "\n\n".join(f"### 씬 {i + 1}\n{seg['narration']}" for i, seg in enumerate(segments))
    prompt = (
        _load_skill("scene-analyze")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + f"\n\n## 씬별 내레이션({len(segments)}개, 순서·개수 보존)\n{narr}\n\n"
        + "각 씬의 연출만 scene_specs JSON으로 출력(narration 미포함, 입력과 같은 개수·순서). "
        + f"project_id={proj_dir.name}."
    )
    if on_event:
        on_event(f"씬 연출 {len(segments)}개")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_SCENE_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return []
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return list(data.get("scenes") or [])
    except Exception:
        return []


def analyze_scenes(proj_dir, *, on_event=None) -> dict:
    """final_manuscript.md → 마커 분할 + 연출 → adobe scenes.json. {scenes, count} 또는 {error}."""
    proj_dir = Path(proj_dir)
    man = proj_dir / "final_manuscript.md"
    if not man.is_file():
        return {"error": "final_manuscript.md 필요 (P4a 먼저)"}
    segments = split_manuscript(man.read_text(encoding="utf-8"))
    if not segments:
        return {"error": "원고가 비어 있음"}

    directions = _direct_scenes(proj_dir, segments, on_event=on_event)
    specs = []
    for i, seg in enumerate(segments):
        d = directions[i] if i < len(directions) and isinstance(directions[i], dict) else {}
        chars = seg["characters"] or list(d.get("characters") or [])
        specs.append({
            "sceneNumber": i + 1,
            "narration": seg["narration"],
            "visual_summary": str(d.get("visual_summary") or seg["narration"][:60]),
            "image_prompt": str(d.get("image_prompt") or ""),
            "characters": chars,
            "layout": d.get("layout"),
        })

    from backend.v3_import import _map_scene
    from backend import scenes as scenes_mod
    adobe = []
    for s in specs:
        m = _map_scene(s)
        if s.get("layout"):
            m["layout"] = s["layout"]
        adobe.append(m)
    (proj_dir / "scenes.json").write_text(
        json.dumps({"scenes": adobe}, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes_mod.ensure_scene_ids(proj_dir)
    if on_event:
        on_event(f"씬 분석 완료 — {len(specs)}씬")
    return {"scenes": str(proj_dir / "scenes.json"), "count": len(specs)}
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_analyze.py -v`
Expected: 5 passed.

- [ ] **Step 6: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존(P1-P4a 포함) + 신규(약 14) 전부 PASS.

- [ ] **Step 7: Commit**

```bash
git add skills/scene-analyze/SKILL.md skills/scene-analyze/skill.json backend/scene_analysis.py tests/test_scene_analyze.py
git commit -m "feat(scene): scene-analyze 스킬 + analyze_scenes — 연출 결정→adobe scenes.json"
```

---

## Self-Review 결과

**Spec coverage:**
- P4a 마커 보정(`<!--SCENE-->` 삽입 지시) → Task 1 ✓
- scene_specs 스키마 → Task 2 ✓
- split_manuscript(결정적 분할, CHARS 추출, 마커 없을 때 1씬, 빈 세그먼트 버림) → Task 2 ✓
- scene-analyze 스킬(연출만, narration 미생성) → Task 3 ✓
- analyze_scenes(연출 zip, 마커 chars 우선, _map_scene 매핑, layout 보존, ensure_scene_ids) → Task 3 ✓
- 개수 불일치(부족분 빈 연출) → Task 3 테스트 ✓
- 폴백(스킬 실패→narration만으로 생성) → Task 3 테스트 ✓
- 에러(원고 없음/세그먼트 0) → Task 3 테스트 ✓
- 범위 밖(P5) 미포함 ✓

**Placeholder scan:** 스킬 이식(Task 3 Step1)은 원본 경로+적응 규칙으로 구체적. 코드·테스트 전부 완전. ✓

**Type consistency:** `split_manuscript`(→[{narration,characters}])·`_direct_scenes`(→list)·`analyze_scenes`(→{scenes,count}|{error}) 시그니처 일치. scene_specs는 sceneNumber/narration/visual_summary/image_prompt/characters/layout → `_map_scene`가 소비하는 필드(sceneNumber/narration/visual_summary/image_prompt/characters)와 일치, layout은 매핑 후 보존. `ensure_scene_ids(proj_dir)` 호출 정확. ✓

**알려진 결정:** layout은 `_map_scene`가 안 들고 가므로 매핑 후 보존(제안값). characters는 마커(결정적) 우선, 없으면 LLM. 폴백 visual_summary=narration 앞 60자.
