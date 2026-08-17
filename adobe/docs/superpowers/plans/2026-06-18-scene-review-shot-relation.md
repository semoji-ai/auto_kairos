# S1 씬 검토 + shot_relation + 엔티티 태그 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** scene-analyze가 씬별 shot_relation(cut|continue)·location·props를 결정하고, 별도 `review_scenes`가 scenes.json을 검토해 advisory 리포트 scene_review.json을 산출한다(래칫 없음).

**Architecture:** scene-analyze 스킬/스키마에 shot_relation·location·props를 추가하고 `analyze_scenes`가 통과·보존한다. 신규 scene-review 스킬 + scene_review 스키마 + `review_scenes`(결정적 체크 Python + LLM 검토)가 권고 리포트를 낸다. 자동 수정 없음.

**Tech Stack:** Python stdlib + `backend.llm`(claude) + 재사용 `backend.brief.parse_plan`. 테스트는 pytest + monkeypatch(_direct_scenes/_review_scenes_llm/llm, 실 LLM 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트).

**계약(고정):** `review_scenes(proj_dir, *, on_event=None) -> {report, flags, det_issues} | {error}`

---

## Task 1: scene-analyze에 shot_relation·location·props 추가

**Files:**
- Modify: `backend/schemas/scene_specs.schema.json`
- Modify: `skills/scene-analyze/SKILL.md`
- Modify: `backend/scene_analysis.py` (`analyze_scenes` specs + adobe 보존)
- Test: `tests/test_scene_shot_relation.py`

- [ ] **Step 1: Write the failing test** — `tests/test_scene_shot_relation.py`:

```python
import json
from pathlib import Path
from backend import scene_analysis


def _setup(tmp_path, manuscript="씬1.\n<!--SCENE-->\n씬2."):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def test_shot_relation_location_props_passthrough(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: [
        {"visual_summary": "v1", "shot_relation": "cut", "location": "연구실", "props": ["접착제"]},
        {"visual_summary": "v2", "shot_relation": "continue", "location": "연구실", "props": []}])
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["shot_relation"] == "cut" and s[0]["location"] == "연구실" and s[0]["props"] == ["접착제"]
    assert s[1]["shot_relation"] == "continue"


def test_shot_relation_defaults_cut_and_validates(tmp_path, monkeypatch):
    _setup(tmp_path, "한 씬뿐.")
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: [
        {"visual_summary": "v", "shot_relation": "zoom"}])   # 이상값
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["shot_relation"] == "cut"        # 이상값/누락→cut


def test_scene_specs_schema_has_shot_relation():
    sp = json.loads(Path("backend/schemas/scene_specs.schema.json").read_text(encoding="utf-8"))
    props = sp["properties"]["scenes"]["items"]["properties"]
    assert props["shot_relation"]["enum"] == ["cut", "continue"]
    assert props["location"]["type"] == "string" and props["props"]["type"] == "array"


def test_scene_analyze_skill_instructs_shot_relation():
    t = Path("skills/scene-analyze/SKILL.md").read_text(encoding="utf-8")
    assert "shot_relation" in t and "continue" in t and "location" in t and "props" in t
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_shot_relation.py -v`
Expected: FAIL — 필드/스키마/스킬 없음.

- [ ] **Step 3: Overwrite `backend/schemas/scene_specs.schema.json`** with EXACTLY:

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
          "layout": { "type": "string", "enum": ["headline_only", "items_list", "metric_spotlight", "quote", "map", "cinematic"] },
          "asset_source": { "type": "string", "enum": ["generate", "search"] },
          "search_query": { "type": "string" },
          "shot_relation": { "type": "string", "enum": ["cut", "continue"] },
          "location": { "type": "string" },
          "props": { "type": "array" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Edit `skills/scene-analyze/SKILL.md`** — extend the per-scene output contract + JSON example so the skill also outputs `shot_relation`("cut"|"continue"), `location`(string), `props`(array). ADD a guide section (Korean, no kana/Hanja):

```
## 씬 연결성(shot_relation)과 엔티티 태그

각 씬에 shot_relation, location, props도 함께 출력한다.
- **shot_relation**: 이 씬이 이전 씬과 어떤 관계인가.
  - "continue"(연결): 이전 씬과 **시각적으로 이어지는** 장면 — 같은 공간/상황이 카메라 이동·줌으로 연속(특히 cinematic을 한 장면에 걸쳐 연출할 때).
  - "cut"(전환): 시간·장소·소재가 달라진 **새 시퀀스**. **첫 씬은 항상 cut**. headline/items/quote/metric 같은 카드형은 대개 cut.
- **location**: 이 씬의 장소·배경을 짧게(예: "3M 연구실", "교회 성가대석"). 없으면 빈 문자열.
- **props**: 이 씬의 핵심 소품·사물 배열(예: ["포스트잇", "특허 문서"]). 없으면 빈 배열.
```

Update the output JSON example to include `"shot_relation"`, `"location"`, `"props"`. Read the current SKILL.md first; keep existing content, only add. No kana/Hanja.

- [ ] **Step 5: In `backend/scene_analysis.py` `analyze_scenes`, extend the `specs.append({...})` dict** — add these three keys (keep all existing keys):

```python
            "shot_relation": d.get("shot_relation") if d.get("shot_relation") in ("cut", "continue") else "cut",
            "location": str(d.get("location") or ""),
            "props": list(d.get("props") or []),
```

And in the adobe-preserve loop (after `m["asset_source"] = s["asset_source"]` / the `search_query` line), add:

```python
        m["shot_relation"] = s["shot_relation"]
        if s.get("location"):
            m["location"] = s["location"]
        if s.get("props"):
            m["props"] = s["props"]
```

- [ ] **Step 6: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_shot_relation.py -v`
Expected: 4 passed. Full suite → all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/schemas/scene_specs.schema.json skills/scene-analyze/SKILL.md backend/scene_analysis.py tests/test_scene_shot_relation.py
git commit -m "feat(scene): scene-analyze에 shot_relation(cut/continue)+location/props 추가"
```

---

## Task 2: scene-review 스킬 + review_scenes (advisory 검토)

**Files:**
- Create: `backend/schemas/scene_review.schema.json`
- Create: `skills/scene-review/SKILL.md`, `skills/scene-review/skill.json`
- Modify: `backend/scene_analysis.py` (상수 + `_scene_det_checks` + `_review_scenes_llm` + `review_scenes`)
- Test: `tests/test_scene_review.py`

- [ ] **Step 1: Create `backend/schemas/scene_review.schema.json`** with EXACTLY:

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
          "sceneNumber": { "type": "number" },
          "layout_fit": { "type": "string" },
          "shot_relation_fit": { "type": "string" },
          "note": { "type": "string" }
        }
      }
    },
    "flags": { "type": "array", "items": { "type": "string" } },
    "overall": { "type": "string" }
  }
}
```

- [ ] **Step 2: Create the scene-review skill** — `skills/scene-review/SKILL.md`: 씬 검토기 프롬프트(한국어, 가나·한자 금지). 입력으로 씬 목록(번호·layout·shot_relation·characters·location·narration 요약)과 editorial brief가 주입됨을 전제. 평가:
  - **layout_fit**: 각 씬의 layout이 내용에 적합한가("ok" 또는 "warn"). 수치 강조 씬은 metric_spotlight, 나열은 items_list, 인용은 quote, 짧은 테제는 headline_only, 서사·감정은 cinematic이 자연스럽다.
  - **shot_relation_fit**: cut/continue 분류가 내러티브 흐름에 맞는가("ok"|"warn"). 같은 장소·상황이 이어지는데 cut이면 continue 권장, 장소·시간이 바뀌었는데 continue면 cut 권장.
  - **note**: 그 씬에 대한 한 줄 평/권고.
  - **flags**: 전체에서 주의가 필요한 항목을 원인+권고로 명시(예: "씬7: 특허번호가 핵심 → metric_spotlight 권장").
  - **overall**: 한 줄 총평.
  출력은 scene_review JSON만. **자동 수정 지시가 아니라 권고(advisory)임을 명시.**

`skills/scene-review/skill.json`:
```json
{ "name": "scene-review", "inputs": ["scenes.json", "editorial_brief.json"], "output": "scene_review_llm.json", "output_kind": "json" }
```

- [ ] **Step 3: Write the failing test** — `tests/test_scene_review.py`:

```python
import json
from pathlib import Path
from backend import scene_analysis, llm


def _setup(tmp_path, scenes, manuscript=None, duration="1분"):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    (tmp_path / "plan.md").write_text(f"# t\n채널: semoji\n분량: {duration}\n", encoding="utf-8")
    man = manuscript if manuscript is not None else " ".join(s.get("narration", "") for s in scenes)
    (tmp_path / "final_manuscript.md").write_text(man, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def _good_scenes():
    return [{"sceneNumber": 1, "narration": "첫 씬 내용.", "visual_summary": "v1",
             "layout": "cinematic", "shot_relation": "cut", "characters": [], "location": ""},
            {"sceneNumber": 2, "narration": "둘째 씬 내용.", "visual_summary": "v2",
             "layout": "headline_only", "shot_relation": "cut", "characters": [], "location": ""}]


def test_det_checks_clean(tmp_path):
    det = scene_analysis._scene_det_checks(tmp_path_factory_scenes(tmp_path))
    # helper below


import pytest


@pytest.fixture
def proj(tmp_path):
    return tmp_path


def test_review_merges_llm_flags(proj, monkeypatch):
    _setup(proj, _good_scenes())
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm",
                        lambda pd, scenes, **k: {"scenes": [{"sceneNumber": 1, "layout_fit": "ok"}],
                                                 "flags": ["씬2: headline 적절"], "overall": "양호"})
    r = scene_analysis.review_scenes(proj)
    assert r["flags"] == 1
    rep = json.loads((proj / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["overall"] == "양호" and rep["flags"] == ["씬2: headline 적절"]
    assert rep["deterministic"]["scenes"] == 2


def test_det_detects_first_scene_continue_and_bad_visual(proj, monkeypatch):
    bad = _good_scenes()
    bad[0]["shot_relation"] = "continue"     # 첫 씬 continue 위반
    bad[1]["visual_summary"] = ""             # visual 누락
    _setup(proj, bad)
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    r = scene_analysis.review_scenes(proj)
    rep = json.loads((proj / "scene_review.json").read_text(encoding="utf-8"))
    issues = " ".join(rep["deterministic"]["issues"])
    assert "첫 씬" in issues and "visual_summary" in issues
    assert r["det_issues"] >= 2


def test_det_detects_per_minute_too_many(proj, monkeypatch):
    many = [{"sceneNumber": i + 1, "narration": f"씬{i}.", "visual_summary": "v",
             "layout": "cinematic", "shot_relation": "cut"} for i in range(20)]
    _setup(proj, many, duration="1분")        # 20씬/1분 = 20 > 12
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    scene_analysis.review_scenes(proj)
    rep = json.loads((proj / "scene_review.json").read_text(encoding="utf-8"))
    assert any("분당 씬 수" in x for x in rep["deterministic"]["issues"])


def test_review_llm_failure_fallback(proj, monkeypatch):
    _setup(proj, _good_scenes())
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = scene_analysis.review_scenes(proj)         # 실제 _review_scenes_llm 경유 → rc≠0 → 빈 검토
    assert r["flags"] == 0
    rep = json.loads((proj / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["scenes"] == [] and rep["deterministic"]["scenes"] == 2   # 결정적은 동작


def test_review_no_scenes_errors(proj):
    (proj / "final_manuscript.md").write_text("x", encoding="utf-8")
    r = scene_analysis.review_scenes(proj)
    assert r.get("error")
```

추가 헬퍼는 쓰지 않는다 — 위 `test_det_checks_clean`/`ttest_path_factory_scenes`는 **삭제**하고 아래 최종 테스트 파일을 사용한다. 즉 **Step 3의 테스트 파일은 다음 최종본으로 작성**한다(불필요한 헬퍼 제거):

```python
import json
import pytest
from backend import scene_analysis, llm


def _setup(tmp_path, scenes, manuscript=None, duration="1분"):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    (tmp_path / "plan.md").write_text(f"# t\n채널: semoji\n분량: {duration}\n", encoding="utf-8")
    man = manuscript if manuscript is not None else " ".join(s.get("narration", "") for s in scenes)
    (tmp_path / "final_manuscript.md").write_text(man, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def _good_scenes():
    return [{"sceneNumber": 1, "narration": "첫 씬 내용.", "visual_summary": "v1",
             "layout": "cinematic", "shot_relation": "cut", "characters": [], "location": ""},
            {"sceneNumber": 2, "narration": "둘째 씬 내용.", "visual_summary": "v2",
             "layout": "headline_only", "shot_relation": "cut", "characters": [], "location": ""}]


def test_review_merges_llm_flags(tmp_path, monkeypatch):
    _setup(tmp_path, _good_scenes())
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm",
                        lambda pd, scenes, **k: {"scenes": [{"sceneNumber": 1, "layout_fit": "ok"}],
                                                 "flags": ["씬2: headline 적절"], "overall": "양호"})
    r = scene_analysis.review_scenes(tmp_path)
    assert r["flags"] == 1
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["overall"] == "양호" and rep["flags"] == ["씬2: headline 적절"]
    assert rep["deterministic"]["scenes"] == 2


def test_det_detects_first_scene_continue_and_bad_visual(tmp_path, monkeypatch):
    bad = _good_scenes()
    bad[0]["shot_relation"] = "continue"
    bad[1]["visual_summary"] = ""
    _setup(tmp_path, bad)
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    r = scene_analysis.review_scenes(tmp_path)
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    issues = " ".join(rep["deterministic"]["issues"])
    assert "첫 씬" in issues and "visual_summary" in issues
    assert r["det_issues"] >= 2


def test_det_detects_per_minute_too_many(tmp_path, monkeypatch):
    many = [{"sceneNumber": i + 1, "narration": f"씬{i}.", "visual_summary": "v",
             "layout": "cinematic", "shot_relation": "cut"} for i in range(20)]
    _setup(tmp_path, many, duration="1분")
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    scene_analysis.review_scenes(tmp_path)
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert any("분당 씬 수" in x for x in rep["deterministic"]["issues"])


def test_review_llm_failure_fallback(tmp_path, monkeypatch):
    _setup(tmp_path, _good_scenes())
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = scene_analysis.review_scenes(tmp_path)
    assert r["flags"] == 0
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["scenes"] == [] and rep["deterministic"]["scenes"] == 2


def test_review_no_scenes_errors(tmp_path):
    (tmp_path / "final_manuscript.md").write_text("x", encoding="utf-8")
    r = scene_analysis.review_scenes(tmp_path)
    assert r.get("error")
```

- [ ] **Step 4: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_review.py -v`
Expected: FAIL — `review_scenes`/`_scene_det_checks`/`_review_scenes_llm` 부재.

- [ ] **Step 5: Add constants + 3 functions to `backend/scene_analysis.py`** — near the top constants add:

```python
_REVIEW_SCHEMA = _SCHEMAS / "scene_review.schema.json"
_LAYOUTS = {"headline_only", "items_list", "metric_spotlight", "quote", "map", "cinematic"}
_REL = {"cut", "continue"}
```

Then append at end of file EXACTLY:

```python
def _scene_det_checks(proj_dir: Path, scenes: list) -> dict:
    """결정적 씬 검토(LLM 무관) — issues 리스트 + 카운트."""
    from backend import brief as brief_mod
    issues: list = []
    n = len(scenes)
    for s in scenes:
        sn = s.get("sceneNumber")
        if not str(s.get("visual_summary") or "").strip():
            issues.append(f"씬{sn}: visual_summary 비어 있음")
        if s.get("layout") and s.get("layout") not in _LAYOUTS:
            issues.append(f"씬{sn}: layout 비표준값 '{s.get('layout')}'")
        if s.get("shot_relation") and s.get("shot_relation") not in _REL:
            issues.append(f"씬{sn}: shot_relation 비표준값 '{s.get('shot_relation')}'")
    if scenes and scenes[0].get("shot_relation") == "continue":
        issues.append("씬1: 첫 씬은 cut이어야 함(continue로 표시됨)")
    per_min = None
    try:
        dur = brief_mod.parse_plan(proj_dir).get("duration", "")
        m = re.search(r"(\d+)", str(dur or ""))
        mins = int(m.group(1)) if m else 0
        if mins > 0:
            per_min = round(n / mins, 1)
            if per_min < 2:
                issues.append(f"분당 씬 수 {per_min}로 너무 적음(2 미만)")
            elif per_min > 12:
                issues.append(f"분당 씬 수 {per_min}로 너무 많음(12 초과)")
    except Exception:
        per_min = None
    man = re.sub(r"<!--.*?-->", "", _read(proj_dir, "final_manuscript.md"))
    coverage = all(str(s.get("narration") or "")[:30] in man for s in scenes) if scenes else False
    if scenes and not coverage:
        issues.append("narration 커버리지 불완전(일부 씬 narration이 원고에 없음)")
    return {"scenes": n, "per_minute": per_min, "narration_coverage": coverage, "issues": issues}


def _review_scenes_llm(proj_dir: Path, scenes: list, *, on_event=None) -> dict:
    """scene-review 스킬로 레이아웃/연결성/엔티티 검토. 실패 시 {scenes:[], flags:[]}."""
    out = proj_dir / "scene_review_llm.json"
    summary = "\n".join(
        f"씬{s.get('sceneNumber')}: layout={s.get('layout')} shot_relation={s.get('shot_relation')} "
        f"chars={s.get('characters')} loc={s.get('location', '')} | {str(s.get('narration') or '')[:60]}"
        for s in scenes)
    prompt = (
        _load_skill("scene-review")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + f"\n\n## 씬 목록({len(scenes)}개)\n{summary}\n\n"
        + "scene_review JSON만 출력(scenes 평가 + flags + overall). 권고이며 자동 수정 아님."
    )
    if on_event:
        on_event("씬 검토(LLM)")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REVIEW_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return {"scenes": [], "flags": []}
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return {"scenes": list(data.get("scenes") or []), "flags": list(data.get("flags") or []),
                "overall": str(data.get("overall") or "")}
    except Exception:
        return {"scenes": [], "flags": []}


def review_scenes(proj_dir, *, on_event=None) -> dict:
    """scenes.json을 검토해 advisory 리포트 scene_review.json 산출(래칫 없음).
    반환 {report, flags, det_issues} 또는 {error}."""
    proj_dir = Path(proj_dir)
    sp = proj_dir / "scenes.json"
    if not sp.is_file():
        return {"error": "scenes.json 필요 (씬 분석 먼저)"}
    if not (proj_dir / "final_manuscript.md").is_file():
        return {"error": "final_manuscript.md 필요"}
    try:
        scenes = json.loads(sp.read_text(encoding="utf-8")).get("scenes") or []
    except Exception:
        return {"error": "scenes.json 파싱 실패"}
    det = _scene_det_checks(proj_dir, scenes)
    rv = _review_scenes_llm(proj_dir, scenes, on_event=on_event)
    report = {
        "overall": str(rv.get("overall") or ""),
        "deterministic": det,
        "scenes": list(rv.get("scenes") or []),
        "flags": list(rv.get("flags") or []),
    }
    (proj_dir / "scene_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_event:
        on_event(f"씬 검토 — flags {len(report['flags'])}, det_issues {len(det['issues'])}")
    return {"report": str(proj_dir / "scene_review.json"),
            "flags": len(report["flags"]), "det_issues": len(det["issues"])}
```

- [ ] **Step 6: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_review.py -v`
Expected: 5 passed.

- [ ] **Step 7: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존 + 신규 전부 PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/schemas/scene_review.schema.json skills/scene-review/SKILL.md skills/scene-review/skill.json backend/scene_analysis.py tests/test_scene_review.py
git commit -m "feat(scene): review_scenes — advisory 씬 검토(결정적 체크+LLM 레이아웃/연결성)"
```

---

## Self-Review 결과

**Spec coverage:**
- shot_relation(cut/continue)·location·props 추가(스킬+스키마+analyze_scenes 통과/보존) → Task 1 ✓
- shot_relation 기본 cut·유효성 → Task 1 테스트 ✓
- review_scenes(결정적 체크+LLM 검토→scene_review.json) → Task 2 ✓
- 결정적: visual 누락·layout enum·첫 씬 cut·분당 씬 수·narration 커버리지 → Task 2 `_scene_det_checks` + 테스트 ✓
- LLM 검토: 레이아웃/연결성/엔티티 + flags → scene-review 스킬 + 병합 ✓
- LLM 실패 폴백(결정적만) → Task 2 테스트 ✓
- scenes 없음 → error → Task 2 테스트 ✓
- 범위 밖(S2 시트, 래칫) 미포함 ✓

**Placeholder scan:** 스킬 작성(Task1 Step4, Task2 Step2)은 구체 가이드 명시. 스키마·코드·테스트 전부 완전. (Task2 Step3는 최종 테스트 파일을 명시적으로 제공.) ✓

**Type consistency:** `review_scenes→{report,flags,det_issues}|{error}`, `_scene_det_checks→{scenes,per_minute,narration_coverage,issues}`, `_review_scenes_llm→{scenes,flags,overall?}`. analyze_scenes specs의 shot_relation/location/props가 det 체크·보존과 일치. `_REVIEW_SCHEMA`/`_LAYOUTS`/`_REL` 상수 정의. parse_plan(duration) 재사용 정확. ✓

**알려진 결정:** review_scenes는 독립 함수(analyze_scenes가 자동 호출하지 않음 — advisory 분리). _review_scenes_llm은 모듈 전역(테스트 monkeypatch 지점). LLM 출력 스키마는 claude에서 --json-schema 제거됨(claude_runner) → 프롬프트 지시 + 추출로 동작.
