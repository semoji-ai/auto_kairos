# scene-analyze 실사 자료 자동 배정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** scene-analyze가 씬을 실사(search)/생성(generate)으로 분류하고, search 씬은 `backend/search.py`로 실사 1장을 받아 imageRef에 자동으로 채운다.

**Architecture:** scene-analyze 스킬 출력에 `asset_source`+`search_query`를 추가하고 scene_specs 스키마를 확장한다. `backend/scene_analysis.py`의 `analyze_scenes`가 두 필드를 adobe scene에 보존하고, `enrich=True`면 search 씬마다 기존 `search.search_images`(serper)→`save_image`→`scenes.set_image_ref`로 실사를 붙인다. 실패는 격리(generate 폴백).

**Tech Stack:** Python stdlib + 재사용 `backend.search`(serper/pixabay)·`backend.scenes`. 테스트는 pytest + monkeypatch(_direct_scenes/search, 실 검색·LLM 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트).

**재사용 계약:**
- `backend.search.search_images(query, engine="serper", count=12) -> {"images":[{title,url,thumb,source}], "error"?}`
- `backend.search.save_image(proj_dir, url, name, subdir="images/search") -> {"status","path","rel"}` (무삭제 버전)
- `backend.scenes.set_image_ref(proj_dir, scene_number, image_rel) -> {ok}|{error}` (경로 존재 검증)

**계약(고정):** `analyze_scenes(proj_dir, *, enrich=True, on_event=None) -> {scenes, count, searched} | {error}`

---

## Task 1: scene_specs 스키마 + scene-analyze 스킬에 asset_source/search_query 추가

**Files:**
- Modify: `backend/schemas/scene_specs.schema.json`
- Modify: `skills/scene-analyze/SKILL.md`
- Test: `tests/test_scene_asset_assets.py`

- [ ] **Step 1: Write the failing test** — `tests/test_scene_asset_assets.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scene_specs_schema_has_asset_source():
    s = json.loads((ROOT / "backend/schemas/scene_specs.schema.json").read_text(encoding="utf-8"))
    props = s["properties"]["scenes"]["items"]["properties"]
    assert props["asset_source"]["enum"] == ["generate", "search"]
    assert props["search_query"]["type"] == "string"


def test_scene_analyze_skill_instructs_asset_source():
    t = (ROOT / "skills/scene-analyze/SKILL.md").read_text(encoding="utf-8")
    assert "asset_source" in t and "search_query" in t
    assert "search" in t and "generate" in t
    assert "실사" in t            # 분류 가이드(실사 vs 생성)
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_asset_assets.py -v`
Expected: FAIL — 스키마/스킬에 필드 없음.

- [ ] **Step 3: Replace the `items.properties` block in `backend/schemas/scene_specs.schema.json`** so the whole file becomes EXACTLY:

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
          "search_query": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Edit `skills/scene-analyze/SKILL.md`** — add asset_source/search_query to the output contract + a classification guide. Find the section that lists the per-scene output fields (visual_summary/image_prompt/characters/layout) and the JSON output instruction, and extend it so the skill instructs:
  - 출력 각 씬에 `asset_source`("generate" 또는 "search")와 `search_query`(문자열, search일 때만 의미) 포함.
  - **분류 가이드** 추가(한국어, 가나·한자 금지):
    ```
    ## 실사 자료(search) vs AI 생성(generate) 분류
    - search(실사 검색): 특허·문서, 역사 인물 사진, 실존 제품·로고·장소, 통계 그래프 등 **실재하는 구체물**이 화면의 핵심일 때. `search_query`에 그 실물을 찾을 구체 검색어를 영어/한국어로 적는다(예: "US 3691140 patent document", "Spencer Silver 3M scientist").
    - generate(AI 생성): 추상 서사·감정·은유·세모지 일러스트 톤 장면.
    - 목표: 실재 구체물이 중심인 씬은 적극적으로 search로(대략 전체의 40~50%까지). 애매하면 generate.
    ```
  - 출력 JSON 예시에 `"asset_source": "search"`, `"search_query": "..."` 가 포함되도록 갱신.
  한국어 규칙 유지(가나/한자 금지).

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_asset_assets.py -v`
Expected: 2 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/scene_specs.schema.json skills/scene-analyze/SKILL.md tests/test_scene_asset_assets.py
git commit -m "feat(scene): scene-analyze에 asset_source(실사/생성)+search_query 추가"
```

---

## Task 2: analyze_scenes 실사 enrich

**Files:**
- Modify: `backend/scene_analysis.py` (specs 필드 추가 + adobe 보존 + `_enrich_real_assets` + `enrich` 파라미터)
- Test: `tests/test_scene_enrich.py`

- [ ] **Step 1: Write the failing test** — `tests/test_scene_enrich.py`:

```python
import json
from pathlib import Path
from backend import scene_analysis, search, scenes as scenes_mod


def _setup(tmp_path, manuscript="씬1.\n<!--SCENE-->\n씬2."):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def _patch_directions(monkeypatch, dirs):
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: dirs)


def _patch_search(monkeypatch, *, images=None, fail=False):
    def fake_search(q, engine="serper", count=12):
        if fail:
            return {"error": "no key", "images": []}
        return {"images": images if images is not None else [{"url": "http://x/p.jpg", "title": "t"}]}
    def fake_save(proj_dir, url, name, subdir="images/search"):
        d = Path(proj_dir) / subdir
        d.mkdir(parents=True, exist_ok=True)
        f = d / name
        f.write_bytes(b"img")
        return {"status": "completed", "path": str(f), "rel": f"{subdir}/{name}"}
    monkeypatch.setattr(search, "search_images", fake_search)
    monkeypatch.setattr(search, "save_image", fake_save)


def test_search_scene_gets_imageref(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [
        {"visual_summary": "특허", "asset_source": "search", "search_query": "US 3691140 patent"},
        {"visual_summary": "감정", "asset_source": "generate"}])
    _patch_search(monkeypatch)
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["searched"] == 1 and r["count"] == 2
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["asset_source"] == "search" and s[0]["imageRef"].endswith(".jpg")
    assert s[1]["asset_source"] == "generate" and s[1]["imageRef"] == ""


def test_search_failure_falls_back(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [{"visual_summary": "특허", "asset_source": "search", "search_query": "q"}])
    _patch_search(monkeypatch, fail=True)
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["searched"] == 0
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["imageRef"] == ""        # 검색 실패 → 비움(generate 폴백)


def test_enrich_false_skips_search(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [{"visual_summary": "특허", "asset_source": "search", "search_query": "q"}])
    called = {"n": 0}
    monkeypatch.setattr(search, "search_images", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {"images": []})
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    assert r["searched"] == 0 and called["n"] == 0


def test_asset_source_defaults_generate(tmp_path, monkeypatch):
    _setup(tmp_path, "한 씬뿐.")
    _patch_directions(monkeypatch, [{"visual_summary": "v"}])   # asset_source 없음
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["asset_source"] == "generate"
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_enrich.py -v`
Expected: FAIL — `searched` 키 없음 / asset_source 미보존.

- [ ] **Step 3: Replace `analyze_scenes` in `backend/scene_analysis.py` and append `_enrich_real_assets`** — replace the existing `def analyze_scenes(...)` body with EXACTLY:

```python
def analyze_scenes(proj_dir, *, enrich: bool = True, on_event=None) -> dict:
    """final_manuscript.md → 마커 분할 + 연출 + 실사/생성 분류 → adobe scenes.json.
    enrich=True면 search 씬에 실사 1장을 검색·다운로드해 imageRef에 채움.
    반환 {scenes, count, searched} 또는 {error}."""
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
        src = d.get("asset_source") if d.get("asset_source") in ("generate", "search") else "generate"
        specs.append({
            "sceneNumber": i + 1,
            "narration": seg["narration"],
            "visual_summary": str(d.get("visual_summary") or seg["narration"][:60]),
            "image_prompt": str(d.get("image_prompt") or ""),
            "characters": chars,
            "layout": d.get("layout"),
            "asset_source": src,
            "search_query": str(d.get("search_query") or ""),
        })

    from backend.v3_import import _map_scene
    from backend import scenes as scenes_mod
    adobe = []
    for s in specs:
        m = _map_scene(s)
        if s.get("layout"):
            m["layout"] = s["layout"]
        m["asset_source"] = s["asset_source"]
        if s.get("search_query"):
            m["search_query"] = s["search_query"]
        adobe.append(m)
    (proj_dir / "scenes.json").write_text(
        json.dumps({"scenes": adobe}, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes_mod.ensure_scene_ids(proj_dir)

    searched = _enrich_real_assets(proj_dir, specs, on_event=on_event) if enrich else 0
    if on_event:
        on_event(f"씬 분석 완료 — {len(specs)}씬 (실사 {searched})")
    return {"scenes": str(proj_dir / "scenes.json"), "count": len(specs), "searched": searched}


def _enrich_real_assets(proj_dir: Path, specs: list, *, on_event=None) -> int:
    """asset_source=='search' 씬에 실사 1장 검색·다운로드 → imageRef. 실패는 격리. 붙은 수 반환."""
    from backend import search
    from backend import scenes as scenes_mod
    n = 0
    for s in specs:
        if (s.get("asset_source") or "generate") != "search":
            continue
        q = (s.get("search_query") or s.get("visual_summary") or "").strip()
        if not q:
            continue
        try:
            res = search.search_images(q, engine="serper")
            imgs = res.get("images") or []
            if not imgs:
                if on_event:
                    on_event(f"S{s['sceneNumber']} 실사 결과 없음: {q[:30]}")
                continue
            dl = search.save_image(proj_dir, imgs[0].get("url", ""), f"real_{s['sceneNumber']}.jpg")
            if dl.get("status") == "completed":
                scenes_mod.set_image_ref(proj_dir, s["sceneNumber"], dl["rel"])
                n += 1
                if on_event:
                    on_event(f"S{s['sceneNumber']} 실사: {q[:30]}")
        except Exception as e:  # noqa: BLE001 — 검색/다운로드 오류 격리(generate 폴백)
            if on_event:
                on_event(f"S{s['sceneNumber']} 실사 실패: {e}")
    return n
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_enrich.py -v`
Expected: 4 passed.

Note: 기존 `tests/test_scene_analyze.py`(P4b)는 `analyze_scenes` 반환에 `searched` 키가 추가됐을 뿐 기존 단언(scenes/count)은 유지되므로 그대로 통과해야 한다. enrich 기본 True이지만 그 테스트들은 asset_source가 없어(전부 generate) 검색이 호출되지 않는다.

- [ ] **Step 5: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존 + 신규 전부 PASS, 0 실패.

- [ ] **Step 6: Commit**

```bash
git add backend/scene_analysis.py tests/test_scene_enrich.py
git commit -m "feat(scene): analyze_scenes 실사 enrich — search 씬에 serper 실사 imageRef 자동"
```

---

## Self-Review 결과

**Spec coverage:**
- scene-analyze asset_source/search_query 출력 + 분류 가이드 → Task 1 ✓
- scene_specs 스키마 asset_source enum + search_query → Task 1 ✓
- analyze_scenes: specs 두 필드 통과 + adobe 보존 + enrich 루프 + enrich 파라미터 + searched 반환 → Task 2 ✓
- search 씬 imageRef 채움(serper→save_image→set_image_ref), generate 비움 → Task 2 테스트 ✓
- 검색 실패/키 없음 → 폴백(비블로킹) → Task 2 테스트 ✓
- enrich=False 스킵 → Task 2 테스트 ✓
- asset_source 기본 generate, 보존 → Task 2 테스트 ✓
- 기존 P4b 테스트 회귀 없음 → Task 2 Step4 노트 ✓
- 범위 밖(pixabay 자동 폴백·이미지 재검수) 미포함 ✓

**Placeholder scan:** 스킬 편집(Task1 Step4)은 추가 항목·가이드 문구를 구체적으로 명시. 스키마·코드·테스트 전부 완전. ✓

**Type consistency:** `analyze_scenes(proj_dir,*,enrich=True,on_event=None)→{scenes,count,searched}|{error}`, `_enrich_real_assets(proj_dir,specs,*,on_event)→int`. specs의 asset_source/search_query 키가 enrich 사용과 일치. search.search_images/save_image·scenes.set_image_ref 시그니처 정확. _map_scene 후 asset_source/layout 보존(이미 P4b에서 layout 보존 패턴 동일). ✓

**알려진 결정:** enrich는 set_image_ref(존재 검증)로 imageRef 설정 — 다운로드 파일이 실제 존재해야 함(save_image가 생성). 테스트의 fake save_image가 더미 파일 생성. _enrich의 search/scenes import는 함수 내부(테스트는 backend.search 모듈 함수 monkeypatch로 적용).
