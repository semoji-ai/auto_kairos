# P5b — 씬 구조 편집(add/delete/split/merge) + 상태 체크리스트 Implementation Plan

**Goal:** 시트에서 씬을 추가/삭제/분할/병합한다. `sceneId`는 기존 씬에서 유지(에셋이 따라감), 신규 씬만 새로 발급, `sceneNumber`는 배열 순서로 재번호. **무삭제**(파일 삭제 금지 — 배열에서만 제거). 추가로 씬별 상태 체크리스트(나레이션/이미지/레이어/TTS) 뱃지를 시트에 표시.

**Architecture:** `backend/scenes.py`에 순수 mutate 함수(`add_scene`/`remove_scene`/`split_scene`/`merge_scenes` + `_renumber`/`_save`/`_split_text`) 추가. `load_scenes`에 `_status` 계산 추가. 라우터 4개 엔드포인트(모두 갱신된 `load_scenes` 반환). 패널 renderRow에 씬 컨트롤(➕✂⤵🗑) + 상태 뱃지, JS 핸들러 4종. 모든 변경은 sceneId 보존(에셋 안전), 무삭제.

**Tech Stack:** stdlib Python, pytest, vanilla JS(CEP).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트. JS: `node -e "new Function(require('fs').readFileSync('<path>','utf8'))"`.

**현재 사실(확인됨):**
- `scenes.json` = `{"scenes":[{sceneNumber,sceneId,title,narration,visual_summary,image_prompt,characters,imageRef,...}]}`.
- `load_scenes`는 sceneId 보장 후 `_image`(최신 imageRef 존재 시), `_layers`(`layers/*{sid}*.png` glob) 부여, `dir` 세팅.
- 에셋은 sceneId 키(`sb_{sid}`, `{sid}__*.png`)라 sceneNumber 재번호와 무관.
- 기존 함수: `_new_sid()`, `_path()`, `ensure_scene_ids`, `update_narration`(sceneNumber로 탐색), `set_image_ref`.
- 패널 renderRow: col-num/col-img/col-script/col-asset/col-tts. `unlinkScene`(이미지 링크해제, 씬 삭제 아님)·`analyzeLayers` 존재. `loadSheet()`가 전체 갱신.

---

## File Structure

- **Modify** `backend/scenes.py` — mutate 함수 5종 + `_status` 계산.
- **Modify** `backend/router.py` — `/api/scenes/add|delete|split|merge`.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` — 씬 컨트롤 + 상태 뱃지 + 핸들러.
- **Modify** `cep/com.autokairos.pd/index.html` — 컨트롤/뱃지 CSS.
- **Test** `tests/test_scenes.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: scenes.py — mutate 함수 + _status

**Files:** Modify `backend/scenes.py`; Test `tests/test_scenes.py`

먼저 `backend/scenes.py` 전체와 `tests/test_scenes.py`의 `_proj` 헬퍼를 Read 한다.

- [ ] **Step 1: 실패 테스트** — `tests/test_scenes.py`에 추가(파일 상단 import에 `from backend import scenes` 가정):

```python
def test_add_scene_appends_with_new_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "첫째"}])
    data = scenes.add_scene(d, after_number=1, narration="둘째", title="새 씬")
    ss = data["scenes"]
    assert [s["sceneNumber"] for s in ss] == [1, 2]
    assert ss[0]["sceneId"] == "aaa"                 # 기존 유지
    assert ss[1]["sceneId"] and ss[1]["sceneId"] != "aaa"   # 신규 발급
    assert ss[1]["narration"] == "둘째" and ss[1]["title"] == "새 씬"
    assert ss[1]["imageRef"] == ""

def test_add_scene_at_end_when_no_after(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    data = scenes.add_scene(d)
    assert [s["sceneNumber"] for s in data["scenes"]] == [1, 2]

def test_remove_scene_renumbers_keeps_files(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"},
                         {"sceneNumber": 2, "sceneId": "bbb"},
                         {"sceneNumber": 3, "sceneId": "ccc"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_bbb.png").write_bytes(b"\x89PNG")
    data = scenes.remove_scene(d, 2)
    assert [s["sceneId"] for s in data["scenes"]] == ["aaa", "ccc"]
    assert [s["sceneNumber"] for s in data["scenes"]] == [1, 2]
    assert (d / "storyboard" / "sb_bbb.png").exists()       # 무삭제

def test_split_scene_keeps_sid_first_new_sid_second(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa",
                          "narration": "첫 문장이다. 둘째 문장이다.", "imageRef": "x.png"}])
    data = scenes.split_scene(d, 1)
    ss = data["scenes"]
    assert len(ss) == 2 and ss[0]["sceneId"] == "aaa"
    assert ss[1]["sceneId"] != "aaa" and ss[1]["imageRef"] == ""
    assert ss[0]["narration"] and ss[1]["narration"]        # 양쪽 비어있지 않음
    assert ss[0]["imageRef"] == "x.png"                     # 원본 이미지는 첫 씬에 유지

def test_split_scene_explicit_parts(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "원본"}])
    data = scenes.split_scene(d, 1, first="앞", second="뒤")
    assert data["scenes"][0]["narration"] == "앞" and data["scenes"][1]["narration"] == "뒤"

def test_merge_scenes_concat_keeps_first_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "앞", "imageRef": "a.png"},
                         {"sceneNumber": 2, "sceneId": "bbb", "narration": "뒤", "imageRef": "b.png"}])
    data = scenes.merge_scenes(d, 1)
    ss = data["scenes"]
    assert len(ss) == 1 and ss[0]["sceneId"] == "aaa"
    assert "앞" in ss[0]["narration"] and "뒤" in ss[0]["narration"]
    assert ss[0]["imageRef"] == "a.png"

def test_merge_last_scene_noop(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    data = scenes.merge_scenes(d, 1)            # 다음 씬 없음
    assert len(data["scenes"]) == 1

def test_load_scenes_status_flags(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa",
                          "narration": "내용", "imageRef": "storyboard/sb_aaa.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_aaa.png").write_bytes(b"\x89PNG")
    (d / "layers").mkdir(); (d / "layers" / "aaa__0_x.png").write_bytes(b"\x89PNG")
    st = scenes.load_scenes(d)["scenes"][0]["_status"]
    assert st["narration"] is True and st["image"] is True and st["layers"] is True
    assert st["tts"] is False
```

(주: `_proj`가 없으면 `tests/test_scenes.py` 기존 헬퍼 확인 후 형태 맞춤. scenes.json + scenes 배열 기록하는 헬퍼.)

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_scenes.py -q` → FAIL.

- [ ] **Step 3: 구현** — `backend/scenes.py`에 추가(파일 끝). `_save`/`_renumber`/`_split_text` 헬퍼 먼저:

```python
def _save(proj_dir: Path, data: dict) -> dict:
    _path(proj_dir).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _renumber(data: dict) -> dict:
    for i, s in enumerate(data.get("scenes", []), start=1):
        s["sceneNumber"] = i
    return data


def _split_text(text: str) -> tuple[str, str]:
    """문장 단위로 가운데 분할. 문장 경계 없으면 (전체, '')."""
    import re
    t = (text or "").strip()
    if not t:
        return "", ""
    parts = re.split(r"(?<=[.!?。])\s+", t)
    if len(parts) < 2:
        return t, ""
    mid = (len(parts) + 1) // 2
    return " ".join(parts[:mid]).strip(), " ".join(parts[mid:]).strip()


def _blank_scene(sid: str, narration: str = "", title: str = "") -> dict:
    return {"sceneNumber": 0, "sceneId": sid, "title": title, "narration": narration,
            "visual_summary": "", "image_prompt": "", "characters": [], "imageRef": ""}


def add_scene(proj_dir: Path, after_number: int | None = None,
              narration: str = "", title: str = "") -> dict:
    """after_number 다음에 새 씬 삽입(없으면 끝). 새 sceneId 발급. 재번호 후 저장. 반환=load_scenes."""
    data = ensure_scene_ids(proj_dir)
    ss = data.setdefault("scenes", [])
    new = _blank_scene(_new_sid(), narration, title)
    idx = len(ss)
    if after_number is not None:
        for i, s in enumerate(ss):
            if s.get("sceneNumber") == after_number:
                idx = i + 1
                break
    ss.insert(idx, new)
    _save(proj_dir, _renumber(data))
    return load_scenes(proj_dir)


def remove_scene(proj_dir: Path, scene_number: int) -> dict:
    """배열에서 씬 제거(파일 무삭제). 재번호 후 저장. 반환=load_scenes."""
    data = ensure_scene_ids(proj_dir)
    ss = data.get("scenes", [])
    data["scenes"] = [s for s in ss if s.get("sceneNumber") != scene_number]
    _save(proj_dir, _renumber(data))
    return load_scenes(proj_dir)


def split_scene(proj_dir: Path, scene_number: int,
                first: str | None = None, second: str | None = None) -> dict:
    """씬을 둘로 분할. 첫 씬=기존 sceneId+imageRef 유지, 둘째=새 sceneId+빈 imageRef.
    first/second 미지정 시 나레이션 문장 단위 분할. 반환=load_scenes."""
    data = ensure_scene_ids(proj_dir)
    ss = data.get("scenes", [])
    for i, s in enumerate(ss):
        if s.get("sceneNumber") == scene_number:
            if first is None and second is None:
                first, second = _split_text(s.get("narration", ""))
            s["narration"] = first or ""
            nxt = _blank_scene(_new_sid(), second or "", s.get("title", ""))
            nxt["visual_summary"] = s.get("visual_summary", "")
            ss.insert(i + 1, nxt)
            break
    _save(proj_dir, _renumber(data))
    return load_scenes(proj_dir)


def merge_scenes(proj_dir: Path, scene_number: int) -> dict:
    """scene_number 와 그 다음 씬을 병합. 첫 씬 sceneId+imageRef 유지, 나레이션 연결.
    둘째 씬 에셋은 디스크에 남김(무삭제). 다음 씬 없으면 no-op. 반환=load_scenes."""
    data = ensure_scene_ids(proj_dir)
    ss = data.get("scenes", [])
    for i, s in enumerate(ss):
        if s.get("sceneNumber") == scene_number and i + 1 < len(ss):
            nxt = ss[i + 1]
            a, b = (s.get("narration") or "").strip(), (nxt.get("narration") or "").strip()
            s["narration"] = (a + "\n" + b).strip()
            del ss[i + 1]
            break
    _save(proj_dir, _renumber(data))
    return load_scenes(proj_dir)
```

그리고 `load_scenes`의 루프 안(‑layers 세팅 다음)에 `_status` 추가:

```python
        aud = proj_dir / "audio"
        s["_status"] = {
            "narration": bool((s.get("narration") or "").strip()),
            "image": s["_image"] is not None,
            "layers": len(s["_layers"]) > 0,
            "tts": bool(sid and aud.is_dir() and any(aud.glob(f"*{sid}*"))),
        }
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_scenes.py -q` → PASS.

- [ ] **Step 5: 커밋** — `git add backend/scenes.py tests/test_scenes.py && git commit -m "feat(scenes): 씬 add/delete/split/merge(sceneId 보존·무삭제·재번호) + _status 체크리스트"`

---

## Task 2: 라우터 — add/delete/split/merge

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

`router.py`의 `/api/scenes/narration` 핸들러 인근을 Read 한다(패턴 일치).

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def _mk_scenes(tmp_path, arr):
    import json as _j
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(_j.dumps({"scenes": arr}, ensure_ascii=False), encoding="utf-8")
    return proj

def test_scenes_add(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/add", {},
                                {"project_id": "p", "after": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 2

def test_scenes_delete(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}, {"sceneNumber": 2, "sceneId": "b"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/delete", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and [s["sceneId"] for s in body["scenes"]] == ["b"]

def test_scenes_split(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "하나다. 둘이다."}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 2

def test_scenes_merge(tmp_path):
    _mk_scenes(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "앞"},
                          {"sceneNumber": 2, "sceneId": "b", "narration": "뒤"}])
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/merge", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and len(body["scenes"]) == 1

def test_scenes_add_missing_project_404(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/scenes/add", {}, {"project_id": "none"}, ctx)
    assert code == 404
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `router.py`의 `/api/scenes/narration` 핸들러 블록 다음에 추가(`scenes` 모듈은 이미 import됨, 로컬 변수로 가리지 말 것):

```python
    if method == "POST" and p in ("/api/scenes/add", "/api/scenes/delete",
                                  "/api/scenes/split", "/api/scenes/merge"):
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if p == "/api/scenes/add":
            return 200, scenes.add_scene(proj_dir, after_number=b.get("after"),
                                         narration=b.get("narration", ""), title=b.get("title", ""))
        if p == "/api/scenes/delete":
            return 200, scenes.remove_scene(proj_dir, b.get("sceneNumber"))
        if p == "/api/scenes/split":
            return 200, scenes.split_scene(proj_dir, b.get("sceneNumber"),
                                           first=b.get("first"), second=b.get("second"))
        return 200, scenes.merge_scenes(proj_dir, b.get("sceneNumber"))
```

- [ ] **Step 4: 통과(멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋** — `git add backend/router.py tests/test_router.py && git commit -m "feat(scenes): /api/scenes/add|delete|split|merge"`

---

## Task 3: 패널 — 씬 컨트롤 + 상태 뱃지

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`, `index.html`; Test `tests/test_panel_structure.py`

`storyboard.js`의 `renderRow`·`bindRows`·`loadSheet`(헤더에 "씬 추가" 버튼 추가)와 `index.html` `<style>`을 Read 한다.

- [ ] **Step 1: renderRow — col-num에 상태 뱃지 + 씬 컨트롤** — `'  <div class="col-num">' + n + '</div>'` 를 아래로 교체:

```javascript
    + '  <div class="col-num">' + n
    +      '<div class="scene-badges">'
    +        _badge("나", s._status && s._status.narration)
    +        _badge("이", s._status && s._status.image)
    +        _badge("레", s._status && s._status.layers)
    +        _badge("음", s._status && s._status.tts)
    +      '</div>'
    +      '<div class="scene-ops">'
    +        '<button class="op-add" data-scene="' + n + '" title="아래에 씬 추가">＋</button>'
    +        '<button class="op-split" data-scene="' + n + '" title="이 씬 분할">✂</button>'
    +        '<button class="op-merge" data-scene="' + n + '" title="다음 씬과 병합">⤵</button>'
    +        '<button class="op-del" data-scene="' + n + '" title="이 씬 삭제">🗑</button>'
    +      '</div>'
    + '  </div>'
```

그리고 파일에 헬퍼 추가(`_esc` 다음):

```javascript
function _badge(label, on) {
  return '<span class="badge ' + (on ? "on" : "off") + '">' + label + '</span>';
}
```

- [ ] **Step 2: bindRows — 4개 컨트롤 바인딩** — `analyzeLayers` 바인딩 루프 다음에 추가:

```javascript
  _bindOp("op-add", function (n) { sceneOp("add", { after: parseInt(n, 10) }); });
  _bindOp("op-split", function (n) { sceneOp("split", { sceneNumber: parseInt(n, 10) }); });
  _bindOp("op-merge", function (n) { sceneOp("merge", { sceneNumber: parseInt(n, 10) }); });
  _bindOp("op-del", function (n) {
    if (confirm("씬 " + n + " 을 삭제할까요? (이미지/레이어 파일은 보존됩니다)"))
      sceneOp("delete", { sceneNumber: parseInt(n, 10) });
  });
```

파일에 헬퍼 + 공통 핸들러 추가(파일 끝):

```javascript
function _bindOp(cls, fn) {
  var els = $("sheet").querySelectorAll("button." + cls);
  for (var i = 0; i < els.length; i++) {
    els[i].addEventListener("click", function () { fn(this.getAttribute("data-scene")); });
  }
}

function sceneOp(op, extra) {
  var b = { project_id: SELECTED_PROJECT };
  for (var k in extra) b[k] = extra[k];
  fetch(BACKEND + "/api/scenes/" + op, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { alert("실패: " + j.error); return; }
      loadSheet();      // 갱신
    })
    .catch(function (e) { alert("오류: " + e); });
}
```

- [ ] **Step 3: index.html CSS** — `<style>`에 추가:

```css
    .scene-badges { display:flex; gap:2px; margin-top:4px; }
    .scene-badges .badge { font-size:9px; padding:1px 3px; border-radius:3px; }
    .scene-badges .badge.on { background:#2d7d46; color:#fff; }
    .scene-badges .badge.off { background:#333; color:#777; }
    .scene-ops { display:flex; flex-wrap:wrap; gap:2px; margin-top:4px; }
    .scene-ops button { font-size:11px; padding:1px 4px; width:auto; margin:0;
      background:rgba(255,255,255,0.08); border:none; color:#bbb; cursor:pointer; border-radius:3px; }
    .scene-ops button:hover { background:rgba(255,255,255,0.2); color:#fff; }
```

- [ ] **Step 4: 구조 테스트 + 문법** — `tests/test_panel_structure.py`에:

```python
def test_storyboard_js_has_scene_ops():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function sceneOp" in js and "op-split" in js and "op-merge" in js
    assert "scene-badges" in js
```

`node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK`. `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 5: 커밋** — `git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py && git commit -m "feat(panel): 씬 컨트롤(＋✂⤵🗑) + 상태 뱃지(나/이/레/음)"`

---

## Task 4: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — main/nav/planning/storyboard/gallery/genmodal `node` 체크.
- [ ] **Step 3: 라이브 스모크** — 백엔드 재시작 후 tesla로: add→delete→split→merge curl 호출이 200 + scenes 길이 변화 확인. sceneId 보존·파일 잔존 확인.

---

## Self-Review

- **무삭제 준수**: delete/merge는 배열에서만 제거, 파일 보존(테스트로 검증). split은 파일 안 건드림.
- **sceneId 보존**: add=신규만 발급, delete=영향 없음, split=첫 씬 유지·둘째 신규, merge=첫 씬 유지. 에셋(sb_{sid}, {sid}__*)이 정확히 따라감.
- **재번호 일관성**: 모든 mutate가 `_renumber`로 1..N. NAR_ORIG는 loadSheet가 재구성하므로 정합.
- **라우터 일관성**: 4 엔드포인트 모두 `load_scenes`(=`_image/_layers/_status/dir` 포함) 반환 → 패널 즉시 갱신.
- **placeholder 없음**: 전 코드 완전.
- **한계(정직)**: split 자동 분할은 문장 경계 휴리스틱 — 경계 없으면 둘째 씬 나레이션이 빈다(사용자가 편집). merge는 다음 씬 에셋을 버림(디스크엔 잔존). 둘 다 의도된 동작.
