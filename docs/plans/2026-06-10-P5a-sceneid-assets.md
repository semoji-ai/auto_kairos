# P5a — 에셋 sceneId 기반 전환(마이그레이션) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 씬 에셋(씬 이미지·레이어)의 파일 키를 `sceneNumber` → 안정적인 `sceneId`로 전환한다. 이후 P5b의 구조 편집(split/merge/add/delete)으로 씬 번호가 바뀌어도 에셋 매핑이 깨지지 않게 한다.

**Architecture:** `scenes.py`에 `ensure_scene_ids()`(모든 씬에 sceneId 보장 + 기존 번호 기반 에셋을 sceneId 기반으로 일회성 복사 마이그레이션, 무삭제·멱등) + `scene_id_for()`. 에셋 명명: 씬 이미지 `sb_{sid}.png`, 레이어 `bg_{sid}.png`/`char_{sid}.png`. `load_scenes`·`media.set_scene_image`·라우터(`/api/scenes/image`·`/api/storyboard/generate`·`/api/layers/generate`)를 sid 기반으로 일괄 전환. 동작은 동일(에셋 키만 변경) — 독립 출시 가능.

**Tech Stack:** stdlib Python(uuid), pytest, vanilla JS(영향 없음 — 패널은 sceneNumber로 호출, 백엔드가 sid로 변환).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**확정 사실(현재 코드):** sceneId=uuid4().hex[:8](언더스코어 없음 → glob 안전). 무삭제 버전=`imagegen.versioned_path`. `imagegen.generate_scene_layers(proj_dir, items, ...)`는 items=[(key, img)]에서 key를 파일명/딕셔너리 키로 쓰는 **key-제네릭** 구조라 시그니처 변경 불필요(key에 sid 전달).

---

## File Structure

- **Modify** `backend/scenes.py` — `ensure_scene_ids`(마이그레이션)·`scene_id_for`·sid 기반 `_latest_image`/`load_scenes`.
- **Modify** `backend/media.py` — `set_scene_image`가 sceneNumber→sceneId 변환 후 `sb_{sid}.png` 작성.
- **Modify** `backend/router.py` — `/api/scenes/image`·`/api/storyboard/generate`·`/api/layers/generate`를 sid 기반으로.
- **Test** `tests/test_scenes.py`, `tests/test_media.py`, `tests/test_router.py`, `tests/test_imagegen.py`(영향 시).

---

## Task 1: scenes — sceneId 보장 + 마이그레이션

**Files:** Modify `backend/scenes.py`; Test `tests/test_scenes.py`

먼저 `backend/scenes.py` 전체를 Read 한다(현재 _latest_image/load_scenes/update_narration 보존하며 sid 기반으로 교체).

- [ ] **Step 1: 실패 테스트** — `tests/test_scenes.py`에 추가:

```python
def test_ensure_scene_ids_assigns_and_persists(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"},
                         {"sceneNumber": 2, "image_prompt": "y"}])
    scenes.ensure_scene_ids(d)
    saved = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    sids = [s["sceneId"] for s in saved]
    assert all(sids) and len(set(sids)) == 2          # 발급 + 고유
    # 멱등: 재호출해도 sceneId 불변
    scenes.ensure_scene_ids(d)
    saved2 = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert [s["sceneId"] for s in saved2] == sids


def test_ensure_scene_ids_migrates_number_assets(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    (sb / "sb_1.png").write_bytes(b"IMG")
    (sb / "sb_1_v2.png").write_bytes(b"IMG2")
    lay = d / "layers"; lay.mkdir()
    (lay / "bg_1.png").write_bytes(b"BG"); (lay / "char_1.png").write_bytes(b"CH")
    scenes.ensure_scene_ids(d)
    sid = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]["sceneId"]
    # 번호 에셋이 sid 기반으로 복사됨(무삭제 — 원본도 남음)
    assert (sb / f"sb_{sid}.png").read_bytes() == b"IMG"
    assert (sb / f"sb_{sid}_v2.png").read_bytes() == b"IMG2"
    assert (lay / f"bg_{sid}.png").read_bytes() == b"BG"
    assert (lay / f"char_{sid}.png").read_bytes() == b"CH"
    assert (sb / "sb_1.png").exists()   # 원본 보존(무삭제)


def test_scene_id_for(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 5, "image_prompt": "x"}])
    scenes.ensure_scene_ids(d)
    sid = scenes.scene_id_for(d, 5)
    assert sid and scenes.scene_id_for(d, 99) is None
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_scenes.py -q` → 새 3개 FAIL.

- [ ] **Step 3: 구현** — `backend/scenes.py`를 아래로 전면 교체:

```python
"""scenes.json 조회/수정 — sceneId 기반 에셋, 미디어·레이어 enrich, 나레이션 편집(무삭제)."""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path


def _path(proj_dir: Path) -> Path:
    return proj_dir / "scenes.json"


def _new_sid() -> str:
    return uuid.uuid4().hex[:8]


def _migrate_assets(proj_dir: Path, old_key, sid: str) -> None:
    """번호 기반 에셋(sb_{old}/bg_{old}/char_{old})을 sid 기반으로 복사(무삭제·멱등)."""
    sb, lay = proj_dir / "storyboard", proj_dir / "layers"
    if sb.is_dir():
        for p in list(sb.glob(f"sb_{old_key}.png")) + list(sb.glob(f"sb_{old_key}_v*.png")):
            tgt = sb / p.name.replace(f"sb_{old_key}", f"sb_{sid}", 1)
            if not tgt.exists():
                shutil.copy(p, tgt)
    if lay.is_dir():
        for nm in (f"bg_{old_key}.png", f"char_{old_key}.png"):
            src = lay / nm
            tgt = lay / nm.replace(f"_{old_key}.", f"_{sid}.", 1)
            if src.exists() and not tgt.exists():
                shutil.copy(src, tgt)


def ensure_scene_ids(proj_dir: Path) -> dict:
    """모든 씬에 sceneId 보장(없으면 발급). 신규 발급 시 번호 기반 에셋을 sid로 복사 마이그레이션.
    변경 시 scenes.json 저장. 멱등. 반환=data."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"scenes": []}
    data = json.loads(fp.read_text(encoding="utf-8"))
    changed = False
    for s in data.get("scenes", []):
        if not s.get("sceneId"):
            sid = _new_sid()
            s["sceneId"] = sid
            _migrate_assets(proj_dir, s.get("sceneNumber"), sid)
            changed = True
    if changed:
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def scene_id_for(proj_dir: Path, scene_number) -> str | None:
    data = ensure_scene_ids(proj_dir)
    for s in data.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            return s.get("sceneId")
    return None


def _latest_image(sb_dir: Path, sid: str) -> str | None:
    """storyboard/sb_{sid}.png 및 버전(sb_{sid}_v2.png …) 중 최신(버전 번호 숫자 정렬)."""
    if not sb_dir.is_dir() or not sid:
        return None
    files: list[tuple[str, int]] = []
    if (sb_dir / f"sb_{sid}.png").exists():
        files.append((f"sb_{sid}.png", 0))
    for p in sb_dir.glob(f"sb_{sid}_v*.png"):
        try:
            files.append((p.name, int(p.name.split("_v")[1].split(".")[0])))
        except (IndexError, ValueError):
            pass
    if not files:
        return None
    files.sort(key=lambda x: x[1])
    return f"storyboard/{files[-1][0]}"


def load_scenes(proj_dir: Path) -> dict:
    """sceneId 보장 후 각 씬에 _image(최신)·_layers(sid 기반) 부여. dir=프로젝트 절대경로."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"scenes": [], "dir": ""}
    data = ensure_scene_ids(proj_dir)
    sb_dir, lay_dir = proj_dir / "storyboard", proj_dir / "layers"
    for s in data.get("scenes", []):
        sid = s.get("sceneId")
        s["_image"] = _latest_image(sb_dir, sid)
        s["_layers"] = [f"layers/{nm}" for nm in (f"bg_{sid}.png", f"char_{sid}.png")
                        if (lay_dir / nm).exists()]
    data["dir"] = str(proj_dir)
    return data


def update_narration(proj_dir: Path, scene_number: int, narration: str) -> dict:
    """씬 나레이션 수정 + narration_dirty=True 저장. {ok, sceneNumber} 또는 {error}."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"error": "scenes.json 없음"}
    data = json.loads(fp.read_text(encoding="utf-8"))
    for s in data.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            s["narration"] = narration
            s["narration_dirty"] = True
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "sceneNumber": scene_number}
    return {"error": f"scene {scene_number} 없음"}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_scenes.py -q` → 새 3개 PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): ensure_scene_ids 마이그레이션(번호→sceneId 에셋 복사, 무삭제·멱등)+scene_id_for"
```

---

## Task 2: 기존 load_scenes 테스트를 sceneId 기반으로 갱신

**Files:** Modify `tests/test_scenes.py`

P3에서 작성한 enrich 테스트들은 번호 기반 파일명을 가정한다. sceneId 기반으로 갱신한다.

- [ ] **Step 1: 기존 테스트 수정** — `test_load_scenes_enriches_media_and_layers`·`test_load_scenes_picks_latest_image_version`·`test_load_scenes_latest_version_numeric_sort`를 아래로 교체(씬에 `sceneId` 명시 + 파일을 sid로 명명):

```python
def test_load_scenes_enriches_media_and_layers(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa11111", "title": "A",
                          "narration": "가", "image_prompt": "장면1"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_aaa11111.png").write_bytes(b"\x89PNG")
    (d / "layers").mkdir()
    (d / "layers" / "bg_aaa11111.png").write_bytes(b"\x89PNG")
    (d / "layers" / "char_aaa11111.png").write_bytes(b"\x89PNG")
    data = scenes.load_scenes(d)
    s = data["scenes"][0]
    assert s["_image"] == "storyboard/sb_aaa11111.png"
    assert s["_layers"] == ["layers/bg_aaa11111.png", "layers/char_aaa11111.png"]
    assert data["dir"] == str(d)


def test_load_scenes_picks_latest_image_version(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 2, "sceneId": "bbb22222", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    (sb / "sb_bbb22222.png").write_bytes(b"\x89PNG")
    (sb / "sb_bbb22222_v2.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "storyboard/sb_bbb22222_v2.png"


def test_load_scenes_latest_version_numeric_sort(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 5, "sceneId": "ccc55555", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    for nm in ("sb_ccc55555.png", "sb_ccc55555_v2.png", "sb_ccc55555_v3.png", "sb_ccc55555_v10.png"):
        (sb / nm).write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "storyboard/sb_ccc55555_v10.png"
```

(`test_load_scenes_no_media`·`test_load_scenes_missing_file`·`test_update_narration_*`는 그대로 통과 — sceneId 없으면 load_scenes가 발급만 하고 미디어 None.)

- [ ] **Step 2: 통과** — `... -m pytest tests/test_scenes.py -q` → 전부 PASS.

- [ ] **Step 3: 커밋**

```bash
git add tests/test_scenes.py
git commit -m "test(scenes): load_scenes enrich 테스트를 sceneId 기반 파일명으로 갱신"
```

---

## Task 3: media.set_scene_image + /api/scenes/image → sceneId

**Files:** Modify `backend/media.py`, `backend/router.py`; Test `tests/test_media.py`, `tests/test_router.py`

먼저 `backend/media.py`와 `router.py`의 `/api/scenes/image` 블록을 Read 한다.

- [ ] **Step 1: 실패 테스트 갱신** — `tests/test_media.py`의 `test_set_scene_image_copies_versioned`를 sceneId 기반으로 교체:

```python
def test_set_scene_image_copies_versioned(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":2,"sceneId":"sid22222","image_prompt":"x"}]}', encoding="utf-8")
    (p / "images").mkdir(); src = p / "images" / "pick.png"; src.write_bytes(b"\x89PNG")
    (p / "storyboard").mkdir(); (p / "storyboard" / "sb_sid22222.png").write_bytes(b"old")  # 기존
    res = media.set_scene_image(p, 2, "images/pick.png")
    assert res["status"] == "completed"
    assert res["rel"] == "storyboard/sb_sid22222_v2.png"   # sceneId 키 + 무삭제
    assert (p / "storyboard" / "sb_sid22222_v2.png").read_bytes() == b"\x89PNG"
```

`tests/test_router.py`의 `test_scenes_image_single`에서 `seen["rel_out"] == "sb_3.png"` 단언을 sceneId 기반으로 교체 — 씬에 sceneId를 주고 rel_out이 그 sid를 쓰도록:

```python
def test_scenes_image_single(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":3,"sceneId":"sid33333","image_prompt":"전기차 공장"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt, character_ref=character_ref)
        return {"status": "completed", "path": str(proj_dir / subdir / rel_out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 3, "character": "지오"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"] == "sb_sid33333.png" and seen["subdir"] == "storyboard"
    assert seen["prompt"] == "전기차 공장"
    assert seen["character_ref"] is None
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_media.py tests/test_router.py -q` → 해당 케이스 FAIL.

- [ ] **Step 3: media.set_scene_image 교체** — 현재 함수를 아래로:

```python
def set_scene_image(proj_dir: Path, scene_number, src_rel: str) -> dict:
    """proj/src_rel 이미지를 storyboard/sb_{sceneId}.png 로 복사(무삭제 버전). 트래버설 방지."""
    from backend import scenes  # 지연 임포트(순환 방지)
    sid = scenes.scene_id_for(proj_dir, scene_number)
    if not sid:
        return {"status": "failed", "error": f"scene {scene_number} 없음"}
    src = (proj_dir / src_rel).resolve()
    if not src.is_relative_to(proj_dir.resolve()):
        return {"status": "failed", "error": "잘못된 경로"}
    if not src.is_file():
        return {"status": "failed", "error": f"소스 없음: {src_rel}"}
    sb = proj_dir / "storyboard"
    sb.mkdir(parents=True, exist_ok=True)
    dest = versioned_path(sb, f"sb_{sid}.png")
    shutil.copy(src, dest)
    return {"status": "completed", "path": str(dest),
            "rel": dest.relative_to(proj_dir).as_posix()}
```

`test_set_scene_image_rejects_traversal`/`test_set_scene_image_missing_src`는 scenes.json이 없어 `scene_id_for`가 None→`failed` 반환하므로 여전히 통과(둘 다 status=failed 기대).

- [ ] **Step 4: 라우터 /api/scenes/image 교체** — `imagegen.generate_one(proj_dir, f"sb_{sn}.png", ...)` 호출에서 파일명을 sid로. 블록 내 scene 조회 직후 sid 확보:

`scene = next(...)` 다음에 `sid = scene.get("sceneId")` 추가하고, generate_one 첫 인자 파일명을 `f"sb_{sid}.png"`로 변경. (scene은 load_scenes 결과라 ensure_scene_ids로 sceneId 보장됨.)

- [ ] **Step 5: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 6: 커밋**

```bash
git add backend/media.py backend/router.py tests/test_media.py tests/test_router.py
git commit -m "feat(scenes): set_scene_image·/api/scenes/image를 sceneId 기반 파일명으로"
```

---

## Task 4: 배치 엔드포인트(/api/storyboard·/api/layers) → sceneId

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

먼저 `router.py`의 `/api/storyboard/generate`·`/api/layers/generate` 블록을 Read 한다.

- [ ] **Step 1: /api/storyboard/generate — 아이템 파일명을 sid로** — 현재 `scene_list = _json.loads(...)["scenes"]` + `items.append((f"sb_{n}.png", prompt))` 부분을 `scenes.load_scenes`로 교체:

`scenes_fp` 검사 후 본문을:

```python
        data = scenes.load_scenes(proj_dir)   # sceneId 보장 + enrich
        scene_list = data["scenes"]
        jobs = ctx["jobs"]
        jid = jobs.create("storyboard", pid)
        conc = int(b.get("concurrency", 4))
        char = (b.get("character") or "").strip()
        character_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                character_ref = str(cref)
        items = []
        for sc in scene_list:
            sid = sc.get("sceneId")
            prompt = sc.get("image_prompt") or sc.get("visual_summary") or sc.get("narration", "")
            items.append((f"sb_{sid}.png", prompt))
        results = imagegen.generate_many(
            proj_dir, items, subdir="storyboard", concurrency=conc, character_ref=character_ref,
            on_event=lambda rel, res: jobs.append_log(jid, f"{rel}: {res['status']}"))
```
(기존 `import json as _json`/`scene_list` 라인은 위 블록으로 대체. 나머지 done/status/return은 유지.)

- [ ] **Step 2: /api/layers/generate — sb_{sid} 읽고 bg_{sid}/char_{sid} 생성** — 현재 번호 기반 부분을 sid 기반으로:

`sb_dir`/`scenes.json` 검사 후 본문을:

```python
        data = scenes.load_scenes(proj_dir)
        items = []        # (sid, sb_path)
        sid_to_n = {}
        for sc in data["scenes"]:
            sid, n = sc.get("sceneId"), sc.get("sceneNumber")
            if sc.get("_image"):
                items.append((sid, proj_dir / sc["_image"]))
                sid_to_n[sid] = n
        if not items:
            return 422, {"error": "씬 이미지 없음(sb_{sid}.png)"}
        jobs = ctx["jobs"]
        jid = jobs.create("layers", pid)
        conc = int(b.get("concurrency", 4))
        results = imagegen.generate_scene_layers(
            proj_dir, items, concurrency=conc,
            on_event=lambda key, kind, res: jobs.append_log(jid, f"{key}/{kind}: {res['status']}"))
        ok = sum(1 for v in results.values()
                 if v.get("background", {}).get("status") == "completed"
                 and v.get("character", {}).get("status") == "completed")
        layers = {"project_id": pid, "scenes": [
            {"sceneNumber": sid_to_n[sid], "background": f"layers/bg_{sid}.png",
             "character": f"layers/char_{sid}.png"} for sid in sid_to_n]}
        (proj_dir / "layers.json").write_text(_json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
        jobs.set_status(jid, "completed" if ok else "failed", artifact_paths=[str(proj_dir / "layers.json")])
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"], "scenes": ok, "total": len(items)}
```
(주: `generate_scene_layers`는 items의 첫 원소를 파일명 키로 사용 → sid 전달 시 `bg_{sid}.png`/`char_{sid}.png` 생성. `_json` import가 이 블록에서 쓰이면 상단 `import json as _json` 유지 확인.)

- [ ] **Step 3: 기존 배치 테스트 갱신** — `tests/test_router.py`의 `test_storyboard_generate_from_scenes`·`test_storyboard_passes_character_ref`·레이어 테스트가 sb_{n} 가정 시 sceneId 기반으로 수정. 각 fixture 씬에 `sceneId` 추가하고, 단언이 파일명을 보면 sid 기반으로. (sb_{sid} 파일명; generate_many는 monkeypatch라 파일명 내용만 확인.)

구체적으로 `test_storyboard_passes_character_ref`의 scenes.json에 `"sceneId":"sidAA"` 추가(파일명 단언 없음 — character_ref만 확인하므로 그대로 통과). `test_storyboard_generate_from_scenes`도 각 씬에 sceneId 추가(generate_many monkeypatch가 items를 받으므로 rel 파일명이 sb_{sid}.png여도 카운트만 검증 — 통과). 레이어 테스트가 `bg_1.png` 등을 단언하면 sid 기반으로 교체.

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(scenes): /api/storyboard·/api/layers 배치를 sceneId 기반 파일명으로"
```

---

## Task 5: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 마이그레이션 스모크** — tesla 프로젝트가 있으면(`projects/tesla/scenes.json`+`storyboard/sb_1.png`…) 다음으로 마이그레이션 확인:
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -c "
from pathlib import Path; from backend import scenes
d=Path('projects/tesla')
if (d/'scenes.json').is_file():
    data=scenes.load_scenes(d)
    for s in data['scenes'][:3]:
        print(s['sceneNumber'], s.get('sceneId'), s.get('_image'))
"
```
Expected: 각 씬에 sceneId 발급 + 기존 sb_{n}.png가 sb_{sid}.png로 복사되어 `_image`가 sid 경로. (실 프로젝트라 무삭제로 원본 보존.)
- [ ] **Step 3: JS 영향 없음 확인** — 패널 JS 미변경(sceneNumber로 호출, 백엔드가 sid 변환). `for f in main nav planning storyboard gallery; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK`

---

## Self-Review

- **목표 커버리지**: ensure_scene_ids(T1)로 sceneId 보장+마이그레이션, load_scenes/set_scene_image/scenes·storyboard·layers 엔드포인트(T2~T4)를 sid 기반으로 일괄 전환. 패널은 sceneNumber로 계속 호출(백엔드가 변환) — UI 무변경.
- **무삭제 준수**: 마이그레이션은 copy(원본 보존), 모든 생성은 versioned_path. 트래버설 방지 유지.
- **멱등성**: ensure_scene_ids는 sceneId 있으면 no-op, 마이그레이션은 타겟 존재 시 skip — load_scenes 매 호출 안전.
- **Placeholder 없음**: 전 코드 완전. sceneId=uuid4().hex[:8](언더스코어 없음 → `sb_{sid}_v*` glob/파싱 안전).
- **타입/ID 일관성**: 에셋 키 일원화 — 씬 이미지 `sb_{sid}`, 레이어 `bg_{sid}`/`char_{sid}`. load_scenes `_image`/`_layers`, set_scene_image, /api/scenes/image(generate_one rel_out), /api/storyboard(items), /api/layers(generate_scene_layers key + layers.json) 모두 sid. generate_scene_layers는 key-제네릭이라 시그니처 무변경(sid를 key로). update_narration은 sceneNumber 기준 유지(나레이션은 씬 객체에 저장 — 구조 편집 시 함께 이동).
- **P5b 준비 완료**: 에셋이 sceneId 키라 split/merge/add/delete로 sceneNumber 재배치해도 에셋 안 깨짐.
