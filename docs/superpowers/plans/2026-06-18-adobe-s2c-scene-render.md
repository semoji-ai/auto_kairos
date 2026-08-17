# S2c Scene Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** scenes.json의 엔티티 ID를 entities.json의 시트로 해석해 각 씬을 관련 시트 첨부로 일관 렌더하고, continue 씬은 직전 렌더 씬도 첨부한다.

**Architecture:** 새 모듈 `backend/scene_render.py`가 씬→시트 resolver(순수) + 멀티시트 프롬프트 빌더(순수) + 순차 렌더 오케스트레이터로 구성된다. 기존 `imagegen._run_codex_image`/`versioned_path`/`base_img`/`load_style`와 `scenes.set_image_ref`를 재사용한다. 코드 TDD는 codex를 monkeypatch로 모킹한다.

**Tech Stack:** Python 3 (stdlib + 기존 imagegen/scenes), pytest + monkeypatch. 테스트 러너: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`.

---

## 사전 정보 (구현자 필독)

- 작업 위치(격리 워크트리): `/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/.claude/worktrees/s2c-scene-render`. 모든 명령은 이 디렉터리에서.
- 테스트 명령 접두: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`
- 재사용 대상:
  - `imagegen._run_codex_image(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None) -> {"status","path"|"error"}`
  - `imagegen.versioned_path(dir, name)`, `imagegen.base_img() -> Path|None`, `imagegen.load_style() -> str`
  - `scenes.set_image_ref(proj_dir, scene_number, image_rel) -> dict` (sceneNumber 매칭 + 경로 검증 + 파일 존재 확인)
- 한국어 규칙: 가타카나/히라가나/한자 금지(순수 한국어/영어). 주석·문자열 모두.
- 커밋 메시지 말미에 추가:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **Task 4(실 검증)는 컨트롤러 전담** — 구현 subagent는 Task 1~3만.

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/scene_render.py` (생성) | resolver + 프롬프트 빌더 + render_scenes |
| `tests/test_scene_render.py` (생성) | monkeypatch 단위 테스트 |

---

## Task 1: resolver + 프롬프트 빌더 (순수 함수)

**Files:**
- Create: `backend/scene_render.py`
- Test: `tests/test_scene_render.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_scene_render.py` 생성:

```python
import json
from pathlib import Path
from backend import scene_render


def _mksheet(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n")


def test_resolve_scene_refs_existing_only(tmp_path):
    _mksheet(tmp_path, "references/characters/char-1.png")
    ents = {
        "char-1": {"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"},
        "char-2": {"id": "char-2", "type": "character", "name": "미아", "sheet": "references/characters/char-2.png"},
    }
    scene = {"sceneNumber": 1, "character_ids": ["char-1", "char-2"], "location_id": "", "prop_ids": []}
    refs = scene_render.resolve_scene_refs(scene, ents, tmp_path)
    assert len(refs["character_sheets"]) == 1   # char-2 시트 파일 없음 → 제외
    assert refs["character_sheets"][0]["name"] == "하루"
    assert refs["location_sheet"] == {}
    assert refs["prop_sheets"] == []


def test_resolve_scene_refs_location_and_props(tmp_path):
    _mksheet(tmp_path, "references/locations/loc-1.png")
    _mksheet(tmp_path, "references/props/prop-1.png")
    ents = {
        "loc-1": {"id": "loc-1", "type": "location", "name": "거실", "sheet": "references/locations/loc-1.png"},
        "prop-1": {"id": "prop-1", "type": "prop", "name": "포스트잇", "sheet": "references/props/prop-1.png"},
    }
    scene = {"sceneNumber": 1, "character_ids": [], "location_id": "loc-1", "prop_ids": ["prop-1"]}
    refs = scene_render.resolve_scene_refs(scene, ents, tmp_path)
    assert refs["location_sheet"]["name"] == "거실"
    assert refs["prop_sheets"][0]["name"] == "포스트잇"


def test_build_scene_prompt_includes_scene_and_descriptors():
    p = scene_render.build_scene_prompt(
        {"image_prompt": "공원 산책"},
        ["1번 캐릭터 시트 '하루'", "인물 없음"],
        "STYLE", "scenes/scene_1.png")
    assert "공원 산책" in p
    assert "하루" in p
    assert "scenes/scene_1.png" in p
    assert "STYLE" in p
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_render.py -q`
Expected: FAIL (ModuleNotFoundError: backend.scene_render)

- [ ] **Step 3: Create `backend/scene_render.py` with resolver + builder**

```python
"""씬↔시트 첨부 렌더 (adobe 독립 Stage1-2 S2c) — scenes.json의 엔티티 ID를 entities.json의
시트로 해석해 씬 이미지를 시트 첨부로 일관 렌더. shot_relation=continue는 직전 씬도 첨부.
런타임 v3 의존 없음."""
from __future__ import annotations

import json
from pathlib import Path

from backend import imagegen
from backend import scenes as scenes_mod

_SUBDIR = "scenes"


def _entities_by_id(proj_dir: Path) -> dict:
    ep = proj_dir / "entities.json"
    if not ep.is_file():
        return {}
    try:
        ents = json.loads(ep.read_text(encoding="utf-8")).get("entities") or []
    except Exception:
        return {}
    return {e.get("id"): e for e in ents if e.get("id")}


def _sheet_rel(proj_dir: Path, ent) -> str:
    """엔티티의 sheet 경로(존재하는 파일만). 없으면 ''."""
    rel = str((ent or {}).get("sheet") or "").strip()
    if rel and (proj_dir / rel).is_file():
        return rel
    return ""


def resolve_scene_refs(scene, entities_by_id, proj_dir) -> dict:
    """씬의 character_ids/location_id/prop_ids → 존재하는 시트 rel(이름 동반).
    {character_sheets:[{rel,name}], location_sheet:{rel,name}|{}, prop_sheets:[{rel,name}]}."""
    proj_dir = Path(proj_dir)
    char_sheets = []
    for cid in (scene.get("character_ids") or []):
        ent = entities_by_id.get(cid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            char_sheets.append({"rel": rel, "name": (ent or {}).get("name") or cid})
    location_sheet = {}
    lid = scene.get("location_id")
    if lid:
        ent = entities_by_id.get(lid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            location_sheet = {"rel": rel, "name": (ent or {}).get("name") or lid}
    prop_sheets = []
    for pid in (scene.get("prop_ids") or []):
        ent = entities_by_id.get(pid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            prop_sheets.append({"rel": rel, "name": (ent or {}).get("name") or pid})
    return {"character_sheets": char_sheets, "location_sheet": location_sheet,
            "prop_sheets": prop_sheets}


def build_scene_prompt(scene, descriptors, style_desc, rel_out, *, has_prev=False) -> str:
    """descriptors(첨부 순서와 일치)를 합쳐 씬 프롬프트 생성."""
    scene_desc = (scene.get("image_prompt") or scene.get("visual_summary")
                  or scene.get("narration") or "").strip()
    lines = "\n".join(f"- {d}" for d in descriptors)
    return (
        f"{style_desc}\n\n## 장면\n{scene_desc}\n\n"
        f"[첨부 이미지 — 순서대로]\n{lines}\n\n## 생성 지시\n"
        f"image_gen 도구로 위 아트스타일의 이미지 1장을 생성해 현재 폴더의 {rel_out} 로 저장.\n"
        f"첨부한 캐릭터·장소·소품 시트의 정체성을 그대로 유지(비율·형태를 새로 디자인하지 말 것). "
        f"비율을 텍스트로 새로 지정하지 말 것. 텍스트 없음. 저장되면 'OK'만 답해."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_render.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/scene_render.py tests/test_scene_render.py
git commit -m "feat(s2c): scene ref resolver + multi-sheet prompt builder

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: render_scenes 오케스트레이터 (순차 + continue 연속)

**Files:**
- Modify: `backend/scene_render.py` (append)
- Test: `tests/test_scene_render.py` (append)

- [ ] **Step 1: Write the failing tests**

`tests/test_scene_render.py`에 추가:

```python
from backend import imagegen


def _setup(tmp_path, scene_list, entities, sheets=()):
    (tmp_path / "scenes.json").write_text(
        json.dumps({"scenes": scene_list}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "entities.json").write_text(
        json.dumps({"entities": entities}, ensure_ascii=False), encoding="utf-8")
    for rel in sheets:
        _mksheet(tmp_path, rel)


def _fake_codex(monkeypatch, fail_scenes=()):
    calls = []

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        calls.append({"out": str(out), "prompt": prompt, "images": list(images or [])})
        if any(f"scene_{n}.png" == Path(out).name for n in fail_scenes):
            return {"status": "failed", "error": "no_file"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(b"\x89PNG\r\n")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    return calls


def test_render_scenes_attaches_sheets_and_links(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "shot_relation": "cut", "character_ids": ["char-1"],
          "location_id": "loc-1", "prop_ids": [], "image_prompt": "등장"}],
        [{"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"},
         {"id": "loc-1", "type": "location", "name": "거실", "sheet": "references/locations/loc-1.png"}],
        sheets=["references/characters/char-1.png", "references/locations/loc-1.png"])
    calls = _fake_codex(monkeypatch)
    r = scene_render.render_scenes(tmp_path)
    assert r["rendered"] == 1 and r["total"] == 1 and r["skipped"] == []
    imgs = calls[0]["images"]
    assert any("char-1.png" in i for i in imgs)
    assert any("loc-1.png" in i for i in imgs)
    doc = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert doc[0]["imageRef"] == "scenes/scene_1.png"
    assert (tmp_path / "scenes/scene_1.png").exists()


def test_render_continue_attaches_prev_scene(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "shot_relation": "cut", "character_ids": ["char-1"]},
         {"sceneNumber": 2, "shot_relation": "continue", "character_ids": ["char-1"]}],
        [{"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"}],
        sheets=["references/characters/char-1.png"])
    calls = _fake_codex(monkeypatch)
    scene_render.render_scenes(tmp_path)
    c1 = [c for c in calls if Path(c["out"]).name == "scene_1.png"][0]
    c2 = [c for c in calls if Path(c["out"]).name == "scene_2.png"][0]
    assert any(Path(i).name == "scene_1.png" for i in c2["images"])   # 씬2가 씬1 첨부
    assert ("직전" in c2["prompt"]) or ("연속" in c2["prompt"])
    assert not any(Path(i).name.startswith("scene_") for i in c1["images"])   # 씬1은 prev 없음


def test_render_skip_on_failure(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "character_ids": []}, {"sceneNumber": 2, "character_ids": []}],
        [])
    _fake_codex(monkeypatch, fail_scenes=(1,))
    r = scene_render.render_scenes(tmp_path)
    assert r["rendered"] == 1
    assert any(s["scene"] == 1 for s in r["skipped"])


def test_render_no_entities_errors(tmp_path):
    (tmp_path / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    assert scene_render.render_scenes(tmp_path).get("error")


def test_render_no_scenes_errors(tmp_path):
    assert scene_render.render_scenes(tmp_path).get("error")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_render.py -q`
Expected: FAIL (AttributeError: module 'backend.scene_render' has no attribute 'render_scenes')

- [ ] **Step 3: Append `render_scenes` to `backend/scene_render.py`**

```python
def render_scenes(proj_dir, *, subdir=_SUBDIR, on_event=None) -> dict:
    """scenes.json의 각 씬을 시트 첨부로 순차 렌더 → scenes/scene_<n>.png + imageRef.
    continue 씬은 직전 렌더 씬도 첨부. 반환 {rendered, total, skipped}|{error}."""
    proj_dir = Path(proj_dir)
    sp = proj_dir / "scenes.json"
    if not sp.is_file():
        return {"error": "scenes.json 필요 (씬 분석 먼저)"}
    if not (proj_dir / "entities.json").is_file():
        return {"error": "entities.json 필요 (S2a 먼저)"}
    try:
        scene_list = json.loads(sp.read_text(encoding="utf-8")).get("scenes") or []
    except Exception:
        return {"error": "scenes.json 파싱 실패"}

    ents = _entities_by_id(proj_dir)
    base = imagegen.base_img()
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)

    rendered = 0
    skipped: list = []
    prev_rel = ""
    for sc in sorted(scene_list, key=lambda s: s.get("sceneNumber") or 0):
        sn = sc.get("sceneNumber")
        refs = resolve_scene_refs(sc, ents, proj_dir)
        images: list = []
        descriptors: list = []
        n = 1
        for cs in refs["character_sheets"]:
            images.append(str(proj_dir / cs["rel"]))
            descriptors.append(f"{n}번 캐릭터 시트 '{cs['name']}': 이 인물을 그대로 사용"
                               f"(비율·얼굴·헤어·의상 100% 유지).")
            n += 1
        if refs["location_sheet"]:
            images.append(str(proj_dir / refs["location_sheet"]["rel"]))
            descriptors.append(f"{n}번 장소 시트 '{refs['location_sheet']['name']}': 이 장소를 배경으로 사용.")
            n += 1
        for ps in refs["prop_sheets"]:
            images.append(str(proj_dir / ps["rel"]))
            descriptors.append(f"{n}번 소품 시트 '{ps['name']}': 이 소품을 그대로 사용.")
            n += 1
        has_prev = sc.get("shot_relation") == "continue" and bool(prev_rel)
        if has_prev:
            images.append(str(proj_dir / prev_rel))
            descriptors.append(f"{n}번 직전 씬: 카메라·배경·톤이 이어지는 연속 장면 — "
                               f"구도가 자연스럽게 이어지게.")
            n += 1
        if not refs["character_sheets"]:
            descriptors.append("인물(사람)은 포함하지 말 것 — 배경/사물만.")
        if base:
            images.append(str(base))
            descriptors.append("마지막 세모지 베이스: 전체 그림체·색감 기준(베이스 인물 정체성 복사 금지).")

        out = imagegen.versioned_path(out_base, f"scene_{sn}.png")
        rel = out.relative_to(proj_dir).as_posix()
        prompt = build_scene_prompt(sc, descriptors, imagegen.load_style(), rel, has_prev=has_prev)
        if on_event:
            on_event(f"씬 {sn} 렌더 (첨부 {len(images)}장)")
        res = imagegen._run_codex_image(proj_dir, out, prompt, images=images or None, on_line=on_event)
        if res.get("status") == "completed":
            scenes_mod.set_image_ref(proj_dir, sn, rel)
            prev_rel = rel
            rendered += 1
        else:
            skipped.append({"scene": sn, "error": res.get("error")})
            if on_event:
                on_event(f"씬 {sn} 실패 — {res.get('error')}")

    if on_event:
        on_event(f"씬 렌더 완료 — {rendered}/{len(scene_list)}, skip {len(skipped)}")
    return {"rendered": rendered, "total": len(scene_list), "skipped": skipped}
```

- [ ] **Step 4: Run the module test suite to verify pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scene_render.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Run the WHOLE suite for regressions**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: PASS (529 passed, 1 skipped — 기존 521 + 8 신규)

- [ ] **Step 6: Commit**

```bash
git add backend/scene_render.py tests/test_scene_render.py
git commit -m "feat(s2c): render_scenes — sequential sheet-attached scene render with continue continuity

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: 실 검증 (컨트롤러 전담 — subagent 아님)

> 실제 codex 이미지 생성 + 사용자 시각 검증 포함. 구현 subagent는 여기까지 오지 않는다.

- [ ] **Step 1: 작은 프로젝트로 S2a→S2b→S2c 연결 실행** — `entities.json`/시트가 있는 샘플 프로젝트에서 `python -c "from backend import scene_render; print(scene_render.render_scenes('<proj>'))"` (실 codex). 씬 이미지 생성·imageRef 링크 확인.
- [ ] **Step 2: 사용자 시각 실증** — 렌더된 씬이 캐릭터/장소/소품 시트와 일관된지, continue 씬이 연속성을 유지하는지 사용자에게 확인받는다. 불만족 시 프롬프트 조정 후 재렌더.

---

## Self-Review (작성자 점검 완료)

**Spec coverage:** resolver(Task1) · 프롬프트 빌더(Task1) · render_scenes 순차+continue(Task2) · imageRef 링크(Task2) · 에러 처리(Task2 분기) · 시트 존재 필터(Task1 `_sheet_rel`) · 실 검증(Task3) · 테스트 8종(Task1~2) — 스펙 전 항목 커버.

**Placeholder scan:** 없음 — 모든 코드 스텝 완전한 코드.

**Type consistency:** `_entities_by_id`/`_sheet_rel`/`resolve_scene_refs`/`build_scene_prompt`/`render_scenes` 시그니처 Task 간 일치. resolver 반환 `{character_sheets,location_sheet,prop_sheets}` 키 일관. render 반환 `{rendered,total,skipped}`/`{error}` 일관. 첨부 파일명 `scene_<n>.png`·subdir `scenes` 일관. `imagegen._run_codex_image` 가짜 시그니처(`post=None` 포함) 실제와 일치.
