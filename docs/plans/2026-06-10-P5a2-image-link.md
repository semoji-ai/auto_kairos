# P5a-2 — 씬 이미지 링크 모델(imageRef) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 씬 이미지를 "파일명=sceneId" 고정 대신 **씬이 이미지 파일을 링크(`imageRef`)** 하는 모델로 바꾼다. 이미지 재사용(여러 씬 공유)·연동 해제가 가능해지고, 링크를 끊으면 시트 미리보기만 끊긴다(파일은 보존).

**Architecture:** scenes.json 씬에 `imageRef`(프로젝트 상대경로) 필드 추가. `load_scenes._image`는 `imageRef`가 가리키는 파일(존재 시). 씬 이미지 생성은 `storyboard/`에 고유 이름(`scene_{sid}_{hex}.png`) 생성 후 그 씬 `imageRef`로 설정. 갤러리 드래그는 **복사 없이 링크**. 링크 해제 = `imageRef=""`. sceneId는 고유 파일명·레이어 키로 유지. 기존 `sb_{sid}.png`는 imageRef로 일회성 백필(하위호환). 이미지 무삭제.

**Tech Stack:** stdlib Python(uuid), pytest, vanilla JS(CEP).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**현재 사실:** scenes.py에 ensure_scene_ids/_latest_image/load_scenes(_image=sb_{sid})/update_narration. media.set_scene_image=storyboard/sb_{sid}.png 복사. router /api/scenes/image=generate_one(f"sb_{sid}.png"). /api/scenes/set-image=media.set_scene_image.

---

## File Structure

- **Modify** `backend/scenes.py` — ensure_scene_ids에 imageRef 백필 + `set_image_ref`(링크/해제) + `new_scene_image_name` + load_scenes `_image`를 imageRef 기반으로.
- **Modify** `backend/media.py` — set_scene_image을 **링크**(복사 X)로(scenes.set_image_ref 위임).
- **Modify** `backend/router.py` — /api/scenes/image(생성→imageRef 설정) + /api/scenes/unlink-image 추가.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` + `index.html` — 이미지 호버 시 "링크 해제" 버튼.
- **Test** `tests/test_scenes.py`, `tests/test_media.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: scenes — imageRef 백필 + set_image_ref + new_scene_image_name + load_scenes

**Files:** Modify `backend/scenes.py`; Test `tests/test_scenes.py`

먼저 `backend/scenes.py` 전체를 Read 한다.

- [ ] **Step 1: 실패 테스트** — `tests/test_scenes.py`에 추가:

```python
def test_load_scenes_image_from_imageref(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lnk00001",
                          "imageRef": "images/pick.png", "image_prompt": "x"}])
    (d / "images").mkdir(); (d / "images" / "pick.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "images/pick.png"      # 링크가 가리키는 파일


def test_load_scenes_imageref_missing_file(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lnk00002",
                          "imageRef": "images/gone.png"}])
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] is None                    # 파일 없으면 끊김


def test_load_scenes_backfills_imageref_from_sb(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "bf000001", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir(); (sb / "sb_bf000001.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["imageRef"] == "storyboard/sb_bf000001.png"   # 백필
    assert s["_image"] == "storyboard/sb_bf000001.png"


def test_set_image_ref_link_and_unlink(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 2, "sceneId": "s2", "image_prompt": "x"}])
    (d / "images").mkdir(); (d / "images" / "a.png").write_bytes(b"\x89PNG")
    assert scenes.set_image_ref(d, 2, "images/a.png")["ok"] is True
    assert _scene(d, 2)["imageRef"] == "images/a.png"
    # 해제
    assert scenes.set_image_ref(d, 2, "")["ok"] is True
    assert _scene(d, 2)["imageRef"] == ""


def test_set_image_ref_rejects_traversal_and_missing(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "s1"}])
    assert "error" in scenes.set_image_ref(d, 1, "../../etc/hosts")
    assert "error" in scenes.set_image_ref(d, 1, "images/nope.png")


def test_new_scene_image_name_unique(tmp_path):
    a = scenes.new_scene_image_name("abc")
    b = scenes.new_scene_image_name("abc")
    assert a.startswith("scene_abc_") and a.endswith(".png") and a != b
```

`tests/test_scenes.py` 상단 헬퍼에 추가(없으면):

```python
def _scene(d, n):
    import json as _j
    data = _j.loads((d / "scenes.json").read_text(encoding="utf-8"))
    return next(s for s in data["scenes"] if s["sceneNumber"] == n)
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_scenes.py -q` → 새 케이스 FAIL.

- [ ] **Step 3: 구현** — `backend/scenes.py` 수정:

(a) `ensure_scene_ids`의 루프에 imageRef 일회성 백필 추가(sceneId 처리 다음, 같은 for):

```python
    for s in data.get("scenes", []):
        if not s.get("sceneId"):
            sid = _new_sid()
            s["sceneId"] = sid
            _migrate_assets(proj_dir, s.get("sceneNumber"), sid)
            changed = True
        if "imageRef" not in s:                       # 최초 1회 백필
            latest = _latest_image(proj_dir / "storyboard", s.get("sceneId"))
            s["imageRef"] = latest or ""
            changed = True
```

(b) `load_scenes`의 `_image`/`_layers` 부여를 imageRef 기반으로:

```python
    for s in data.get("scenes", []):
        sid = s.get("sceneId")
        ref = s.get("imageRef") or ""
        s["_image"] = ref if (ref and (proj_dir / ref).is_file()) else None
        s["_layers"] = [f"layers/{nm}" for nm in (f"bg_{sid}.png", f"char_{sid}.png")
                        if (lay_dir / nm).exists()]
```

(c) 함수 추가(파일 끝):

```python
def new_scene_image_name(sid: str) -> str:
    """생성 씬 이미지의 고유 파일명(여러 번 생성해도 충돌·덮어쓰기 없음)."""
    return f"scene_{sid}_{uuid.uuid4().hex[:6]}.png"


def set_image_ref(proj_dir: Path, scene_number, image_rel) -> dict:
    """씬의 imageRef 설정(링크) 또는 빈 문자열로 해제. 경로는 프로젝트 내부 + 존재 검증."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"error": "scenes.json 없음"}
    rel = (image_rel or "").strip()
    if rel:
        target = (proj_dir / rel).resolve()
        if not target.is_relative_to(proj_dir.resolve()):
            return {"error": "잘못된 경로"}
        if not target.is_file():
            return {"error": f"파일 없음: {rel}"}
    data = json.loads(fp.read_text(encoding="utf-8"))
    for s in data.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            s["imageRef"] = rel
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "sceneNumber": scene_number, "imageRef": rel}
    return {"error": f"scene {scene_number} 없음"}
```

- [ ] **Step 4: 기존 enrich 테스트 호환 확인** — `test_load_scenes_enriches_media_and_layers`(sb_aaa11111.png)·버전 테스트는 imageRef 백필로 `_image`가 동일하게 채워져 통과해야 함. FAIL 시 백필 로직 점검.

- [ ] **Step 5: 통과** — `... -m pytest tests/test_scenes.py -q` → PASS.

- [ ] **Step 6: 커밋**

```bash
git add backend/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): imageRef 링크 모델 — set_image_ref(링크/해제)+백필+new_scene_image_name, load_scenes _image=imageRef"
```

---

## Task 2: media.set_scene_image → 링크(복사 X)

**Files:** Modify `backend/media.py`; Test `tests/test_media.py`

먼저 `backend/media.py`의 set_scene_image와 `tests/test_media.py`를 Read 한다.

- [ ] **Step 1: 테스트 갱신** — `tests/test_media.py`의 set_scene_image 케이스를 링크 기반으로 교체:

```python
def test_set_scene_image_links_no_copy(tmp_path):
    import json as _j
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":2,"sceneId":"s2","image_prompt":"x"}]}', encoding="utf-8")
    (p / "images").mkdir(); (p / "images" / "pick.png").write_bytes(b"\x89PNG")
    res = media.set_scene_image(p, 2, "images/pick.png")
    assert res["ok"] is True
    sc = _j.loads((p / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == "images/pick.png"        # 링크만
    assert not (p / "storyboard").exists()            # 복사 안 함


def test_set_scene_image_rejects_traversal(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"s1"}]}', encoding="utf-8")
    assert "error" in media.set_scene_image(p, 1, "../../etc/hosts")


def test_set_scene_image_missing_src(tmp_path):
    p = tmp_path / "p"; p.mkdir()
    (p / "scenes.json").write_text('{"scenes":[{"sceneNumber":1,"sceneId":"s1"}]}', encoding="utf-8")
    assert "error" in media.set_scene_image(p, 1, "images/nope.png")
```

(기존 `test_set_scene_image_copies_versioned`는 삭제.)

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_media.py -q` → FAIL.

- [ ] **Step 3: 구현** — `media.set_scene_image`를 링크 위임으로 교체:

```python
def set_scene_image(proj_dir: Path, scene_number, src_rel: str) -> dict:
    """갤러리/소스 이미지를 씬에 링크(복사하지 않음). scenes.set_image_ref 위임."""
    from backend import scenes  # 지연 임포트(순환 방지)
    return scenes.set_image_ref(proj_dir, scene_number, src_rel)
```

(주: 더 이상 versioned_path/shutil.copy를 쓰지 않으므로 media.py에서 미사용 import는 다른 함수가 쓰면 유지, 안 쓰면 제거.)

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/media.py tests/test_media.py
git commit -m "feat(media): set_scene_image을 링크(복사 X)로 — scenes.set_image_ref 위임"
```

---

## Task 3: router — /api/scenes/image(생성→imageRef) + /api/scenes/unlink-image

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

먼저 `router.py`의 `/api/scenes/image` 블록을 Read 한다.

- [ ] **Step 1: 테스트 갱신/추가** — `tests/test_router.py`의 `test_scenes_image_single`을 교체 + unlink 테스트 추가:

```python
def test_scenes_image_sets_imageref(tmp_path, monkeypatch):
    import json as _j
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":3,"sceneId":"sid333","image_prompt":"전기차 공장"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt)
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 3}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"].startswith("scene_sid333_") and seen["subdir"] == "storyboard"
    sc = _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == "storyboard/" + seen["rel_out"]   # 생성 후 링크됨


def test_scenes_unlink_image(tmp_path):
    import json as _j
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"s1","imageRef":"images/a.png"}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/unlink-image", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["ok"] is True
    sc = _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"] == ""
```

(기존 `test_scenes_image_single`은 삭제. `test_scenes_image_unknown_scene`는 유지.)

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → FAIL.

- [ ] **Step 3: 구현** — `/api/scenes/image` 블록 본문 교체(scene 조회 후):

```python
        sid = scene.get("sceneId")
        char = (b.get("character") or "").strip()
        character_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                character_ref = str(cref)
        jobs = ctx["jobs"]
        jid = jobs.create("scene-image", pid)
        name = scenes.new_scene_image_name(sid)
        res = imagegen.generate_one(
            proj_dir, name, scene.get("image_prompt", "") or scene.get("visual_summary", ""),
            subdir="storyboard", character_ref=character_ref,
            on_line=lambda ln: jobs.append_log(jid, ln))
        if res.get("status") == "completed":
            from pathlib import Path as _P
            rel = _P(res["path"]).relative_to(proj_dir).as_posix()
            scenes.set_image_ref(proj_dir, sn, rel)
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "storyboard")])
        return 200, {"job_id": jid, "result": res}
```

그리고 `/api/scenes/image` 블록 다음에 unlink 추가:

```python
    if method == "POST" and p == "/api/scenes/unlink-image":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_image_ref(proj_dir, b.get("sceneNumber"), "")
        return (200, res) if res.get("ok") else (404, res)
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(scenes): /api/scenes/image가 생성 후 imageRef 링크 + /api/scenes/unlink-image"
```

---

## Task 4: 패널 — 이미지 호버 시 "링크 해제" 버튼

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`, `index.html`; Modify `tests/test_panel_structure.py`

먼저 `storyboard.js`의 `renderRow`(col-img)와 `bindRows`를 Read 한다.

- [ ] **Step 1: renderRow — col-img에 링크 해제 버튼(이미지 있을 때만)** — col-img 생성부를 교체. 현재:

```javascript
    + '  <div class="col-img">' + media + (layers ? '<div>' + layers + '</div>' : '') + '</div>'
```

을:

```javascript
    + '  <div class="col-img">'
    +      (s._image ? '<button class="unlink-img" data-scene="' + n + '" title="씬 이미지 링크 해제">✕</button>' : '')
    +      media + (layers ? '<div>' + layers + '</div>' : '')
    + '  </div>'
```

- [ ] **Step 2: bindRows — 링크 해제 바인딩** — `bindRows` 안 gen-img 루프 다음에 추가:

```javascript
  var un = $("sheet").querySelectorAll("button.unlink-img");
  for (var u = 0; u < un.length; u++) {
    un[u].addEventListener("click", function () { unlinkScene(this.getAttribute("data-scene")); });
  }
```

- [ ] **Step 3: unlinkScene 함수 추가** — 파일 끝(dropOnScene 다음):

```javascript
function unlinkScene(n) {
  _rowStatus(n, "링크 해제 중...");
  fetch(BACKEND + "/api/scenes/unlink-image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10) }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _rowStatus(n, j.ok ? "링크 해제됨(파일은 갤러리에 보존)" : ("실패: " + JSON.stringify(j)));
      if (j.ok) loadSheet();
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}
```

- [ ] **Step 4: CSS — 호버 시 표시** — `index.html` `<style>`의 시트 CSS에 추가:

```css
    .sheet-row .col-img { position:relative; }
    .sheet-row .unlink-img { display:none; position:absolute; top:2px; right:2px;
      width:auto; margin:0; padding:2px 6px; font-size:11px; background:rgba(0,0,0,0.6); }
    .sheet-row .col-img:hover .unlink-img { display:block; }
```

- [ ] **Step 5: 구조 테스트 + 문법** — `tests/test_panel_structure.py` 끝에:

```python
def test_storyboard_js_has_unlink():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function unlinkScene" in js and "unlink-image" in js
```

`node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK`. `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 시트 이미지 호버 시 링크 해제 버튼(✕) — 미리보기만 끊김, 파일 보존"
```

---

## Task 5: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: JS 문법** — `for f in main nav planning storyboard gallery; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK`
- [ ] **Step 3: tesla 백필 스모크** — `... -c "from pathlib import Path; from backend import scenes; d=Path('projects/tesla'); [print(s['sceneNumber'], s.get('imageRef'), s.get('_image')) for s in scenes.load_scenes(d)['scenes'][:3]] if (d/'scenes.json').is_file() else print('no tesla')"` → 기존 sb_{sid}가 imageRef로 백필되어 _image 연결 확인.
- [ ] **Step 4: (사용자) AE 검증** — 시트: 씬 이미지 생성→미리보기 연결 / 갤러리 소스 드래그→링크(복사 없이) / 같은 소스를 다른 씬에도 드래그(공유) / 이미지 호버→✕로 링크 해제(미리보기 끊김, 갤러리엔 파일 그대로).

---

## Self-Review

- **목표 커버리지**: imageRef 필드(T1) + 링크/해제 set_image_ref(T1) + 드래그 링크(T2) + 생성 후 링크(T3) + 해제 엔드포인트(T3) + 호버 해제 UI(T4). 재사용=여러 씬 imageRef 동일 파일, 해제=imageRef "".
- **무삭제 준수**: 링크/해제는 파일 안 건드림. 생성은 고유 이름(충돌·덮어쓰기 없음). set_image_ref 트래버설 방지.
- **하위호환**: ensure_scene_ids가 imageRef 없을 때 sb_{sid} 최신본으로 일회성 백필 → 기존 프로젝트·기존 enrich 테스트 통과.
- **타입/일관성**: scenes.set_image_ref→{ok,sceneNumber,imageRef}|{error}. media.set_scene_image 위임. /api/scenes/set-image(링크)·/api/scenes/unlink-image·/api/scenes/image(생성+링크) 모두 일관. load_scenes _image=imageRef(존재 시). storyboard.js dropOnScene(set-image)·unlinkScene(unlink-image)·genSceneImage(image) 일치.
- **레이어**: 당분간 sceneId 기준 유지(씬 파생) — imageRef와 독립. 후속에 레이어도 링크화 검토.
