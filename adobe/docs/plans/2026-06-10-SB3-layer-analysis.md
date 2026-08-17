# SB3 — 호버 레이어 분리(LLM 사전분석 → 확인 → 요소별 분리) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 시트의 씬 이미지에 호버하면 "레이어 분리" 버튼이 뜨고, 클릭하면 codex 멀티모달이 그 씬 이미지를 분석해 **분할 요소 목록**(예: 왼쪽 전기차/인물/작업대/배경)을 제시, 사용자가 **확인**하면 요소별로 레이어(투명 PNG) + 배경 레이어를 생성한다.

**Architecture:** 백엔드: `analyze_scene_layers`(codex `-i` 씬이미지 + `--output-schema` → 요소 목록), `split_scene_to_elements`(요소별로 씬 이미지 기준 재드로잉→마젠타 키 투명 + 배경 레이어). 라우터 `/api/scenes/analyze-layers`·`/api/scenes/split-layers`. 레이어 파일은 sceneId 키(`{sid}__*.png`)라 구조 편집에도 안전. 패널: 호버 버튼→분석→confirm→분리→시트 레이어 썸네일 갱신. 무삭제(versioned).

**Tech Stack:** stdlib Python(codex_runner.run_skill, ThreadPoolExecutor, PIL chroma), pytest(codex monkeypatch), vanilla JS(CEP).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**현재 사실:** `run_skill(prompt, cwd, *, output_schema, output_last, images, on_line)`. `chroma_key_magenta(src,out)`. `_run_codex_image`. scenes.load_scenes `_layers`는 `bg_{sid}/char_{sid}` 고정 → glob로 일반화 필요. `_image`(imageRef)로 씬 이미지 절대경로 얻음.

---

## File Structure

- **Create** `backend/schemas/layer_elements.schema.json` — 분석 결과 strict 스키마.
- **Modify** `backend/imagegen.py` — `analyze_scene_layers`·`build_element_layer_prompt`·`generate_element_layer`·`split_scene_to_elements`.
- **Modify** `backend/scenes.py` — `load_scenes._layers`를 `layers/*{sid}*.png` glob으로.
- **Modify** `backend/router.py` — `/api/scenes/analyze-layers`·`/api/scenes/split-layers`.
- **Test** `tests/test_imagegen.py`, `tests/test_scenes.py`, `tests/test_router.py`.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` + `index.html` — 호버 "레이어" 버튼 + 분석/확인/분리.

---

## Task 1: 분석 스키마 + scenes._layers glob 일반화

**Files:** Create `backend/schemas/layer_elements.schema.json`; Modify `backend/scenes.py`; Test `tests/test_scenes.py`

- [ ] **Step 1: 스키마 파일 생성** — `backend/schemas/layer_elements.schema.json`:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["elements"],
  "properties": {
    "elements": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["name", "location"],
        "properties": {
          "name": { "type": "string" },
          "location": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: 실패 테스트** — `tests/test_scenes.py`에 추가:

```python
def test_load_scenes_layers_glob_by_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lyr00001",
                          "imageRef": "storyboard/sb_lyr00001.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_lyr00001.png").write_bytes(b"\x89PNG")
    lay = d / "layers"; lay.mkdir()
    (lay / "lyr00001__0_car.png").write_bytes(b"\x89PNG")
    (lay / "lyr00001__bg.png").write_bytes(b"\x89PNG")
    (lay / "other__x.png").write_bytes(b"\x89PNG")          # 다른 씬 — 제외
    s = scenes.load_scenes(d)["scenes"][0]
    assert "layers/lyr00001__0_car.png" in s["_layers"]
    assert "layers/lyr00001__bg.png" in s["_layers"]
    assert "layers/other__x.png" not in s["_layers"]
```

- [ ] **Step 3: 실패 확인** — `... -m pytest tests/test_scenes.py -q` → FAIL.

- [ ] **Step 4: 구현** — `backend/scenes.py`의 `load_scenes` 내 `_layers` 라인 교체. 현재:

```python
        s["_layers"] = [f"layers/{nm}" for nm in (f"bg_{sid}.png", f"char_{sid}.png")
                        if (lay_dir / nm).exists()]
```

을:

```python
        s["_layers"] = (sorted(f"layers/{p.name}" for p in lay_dir.glob(f"*{sid}*.png"))
                        if sid and lay_dir.is_dir() else [])
```

- [ ] **Step 5: 통과** — `... -m pytest tests/test_scenes.py -q` → PASS.

- [ ] **Step 6: 커밋**

```bash
git add backend/schemas/layer_elements.schema.json backend/scenes.py tests/test_scenes.py
git commit -m "feat(scenes): 레이어 분석 스키마 + _layers를 sid glob으로 일반화(요소 레이어 지원)"
```

---

## Task 2: imagegen — analyze_scene_layers + split_scene_to_elements

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

먼저 `backend/imagegen.py`의 상단 import와 `generate_layer`/`chroma_key_magenta`/`_run_codex_image`를 Read 한다.

- [ ] **Step 1: 실패 테스트** — `tests/test_imagegen.py`에 추가:

```python
def test_build_element_layer_prompt():
    p = imagegen.build_element_layer_prompt("왼쪽 전기차", "프레임 왼쪽", "STYLE", "layers/x.png")
    assert "왼쪽 전기차" in p and "마젠타" in p and "#FF00FF" in p and "layers/x.png" in p


def test_analyze_scene_layers_parses(tmp_path, monkeypatch):
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir(); img = proj / "storyboard" / "s.png"; img.write_bytes(b"\x89PNG")

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        from pathlib import Path as _P
        _P(output_last).write_text('{"elements":[{"name":"전기차","location":"왼쪽"},'
                                   '{"name":"인물","location":"오른쪽"}]}', encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(ig, "run_skill", fake_run)
    res = ig.analyze_scene_layers(proj, str(img))
    assert [e["name"] for e in res["elements"]] == ["전기차", "인물"]


def test_split_scene_to_elements(tmp_path, monkeypatch):
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir(); img = proj / "storyboard" / "s.png"; img.write_bytes(b"\x89PNG")
    made = []

    def fake_run_codex(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        out.write_bytes(b"\x89PNG"); made.append(out.name)
        if post: post(out)
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "_run_codex_image", fake_run_codex)
    monkeypatch.setattr(ig, "chroma_key_magenta", lambda a, b: {"transparent_ratio": 0.5})
    res = ig.split_scene_to_elements(proj, str(img), "sid9",
                                     [{"name": "전기차", "location": "왼쪽"},
                                      {"name": "인물", "location": "오른쪽"}], concurrency=2)
    names = [r["rel"] for r in res["layers"]]
    # 요소 2개 + 배경 1개
    assert any("sid9__0" in n for n in names) and any("sid9__1" in n for n in names)
    assert any("sid9__bg" in n for n in names)
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_imagegen.py -q` → FAIL.

- [ ] **Step 3: 구현** — `backend/imagegen.py`:

(a) 상단 import에 추가(없으면): `import json`, `import re`, 그리고 `from backend.codex_runner import run_skill`(이미 있을 수 있음 — 확인).

(b) `chroma_key_magenta` 앞(또는 generate_layer 뒤)에 추가:

```python
_LAYER_SCHEMA = Path(__file__).resolve().parent / "schemas" / "layer_elements.schema.json"


def analyze_scene_layers(proj_dir: Path, scene_image: str, *, on_line=None) -> dict:
    """codex 멀티모달로 씬 이미지를 분석해 분할 요소 목록 반환. {elements:[{name,location}]}|{error}."""
    prompt = (
        "첨부한 씬 이미지를 애니메이션용 레이어로 분리하려 한다. "
        "서로 겹치지 않는 주요 시각 요소(피사체)들을 구분해라. "
        "각 요소의 짧은 한국어 이름과 화면 내 위치를 알려줘. 배경은 목록에 포함하지 말 것."
    )
    out_json = proj_dir / ".layer_analysis.json"
    res = run_skill(prompt, proj_dir, output_schema=str(_LAYER_SCHEMA),
                    output_last=str(out_json), images=[scene_image], on_line=on_line)
    if res.get("returncode") != 0 or not out_json.is_file():
        return {"error": "분석 실패", "elements": []}
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "분석 결과 파싱 실패", "elements": []}
    return {"elements": data.get("elements", [])}


def build_element_layer_prompt(name: str, location: str, style_desc: str, rel_out: str) -> str:
    return (
        f"{style_desc}\n\n## 레이어 분리 — 단일 요소\n첨부한 씬 이미지를 레퍼런스로 사용한다.\n"
        f"이 씬에서 '{name}'({location})만 동일한 위치·크기·외형으로 다시 그리고, "
        f"그 외 전 영역은 순수 마젠타 단색(#FF00FF)으로 채운다.\n"
        f"image_gen 도구로 생성해 현재 폴더의 {rel_out} 로 저장. 텍스트 없음. 저장되면 OK만 답해."
    )


def _layer_slug(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "_", name).strip("_")
    return s[:24] or "el"


def split_scene_to_elements(proj_dir: Path, scene_image: str, sid: str, elements: list,
                            *, subdir: str = "layers", concurrency: int = 4, on_event=None) -> dict:
    """요소별 투명 레이어({sid}__{i}_{slug}.png) + 배경 레이어({sid}__bg.png) 생성.
    요소는 마젠타→투명 후처리. 무삭제(versioned)."""
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    style = load_style()

    def _element(i_el):
        i, el = i_el
        name, loc = el.get("name", f"el{i}"), el.get("location", "")
        out = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(name)}.png")
        rel = out.relative_to(proj_dir).as_posix()
        prompt = build_element_layer_prompt(name, loc, style, rel)
        res = _run_codex_image(proj_dir, out, prompt, images=[scene_image],
                               post=chroma_key_magenta)
        r = {"name": name, "rel": rel, "status": res.get("status")}
        if on_event:
            on_event(r)
        return r

    def _bg():
        names = ", ".join(e.get("name", "") for e in elements)
        out = versioned_path(out_base, f"{sid}__bg.png")
        rel = out.relative_to(proj_dir).as_posix()
        prompt = (f"{style}\n\n## 레이어 분리 — 배경\n첨부한 씬 이미지를 레퍼런스로 사용한다.\n"
                  f"다음 피사체들을 모두 제거하고({names}) 배경·환경만 자연스럽게 채워서 그린다.\n"
                  f"image_gen 도구로 생성해 현재 폴더의 {rel} 로 저장. 텍스트 없음. 저장되면 OK만 답해.")
        res = _run_codex_image(proj_dir, out, prompt, images=[scene_image])
        r = {"name": "배경", "rel": rel, "status": res.get("status")}
        if on_event:
            on_event(r)
        return r

    layers = []
    tasks = list(enumerate(elements))
    with ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as ex:
        layers = list(ex.map(_element, tasks))
    layers.append(_bg())
    return {"layers": layers}
```

(주: `ThreadPoolExecutor`는 파일 상단에서 이미 import됨 — 확인. `_run_codex_image`의 `post=` 인자로 chroma 후처리.)

- [ ] **Step 4: 통과** — `... -m pytest tests/test_imagegen.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/imagegen.py tests/test_imagegen.py
git commit -m "feat(imagegen): analyze_scene_layers(codex 멀티모달)+split_scene_to_elements(요소별 투명 레이어+배경)"
```

---

## Task 3: 라우터 — analyze-layers / split-layers

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

먼저 `router.py`의 `/api/scenes/image` 인근을 Read 한다.

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def test_scenes_analyze_layers(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","imageRef":"storyboard/sb_sa.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb_sa.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(r.imagegen, "analyze_scene_layers",
                        lambda proj_dir, img, **kw: {"elements": [{"name": "차", "location": "왼쪽"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/analyze-layers", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["elements"][0]["name"] == "차"


def test_scenes_analyze_layers_no_image(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","imageRef":""}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/analyze-layers", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 422       # 씬 이미지 없음


def test_scenes_split_layers(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sb1","imageRef":"storyboard/sb_sb1.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb_sb1.png").write_bytes(b"\x89PNG")
    seen = {}
    monkeypatch.setattr(r.imagegen, "split_scene_to_elements",
                        lambda proj_dir, img, sid, elements, **kw: seen.update(sid=sid, n=len(elements)) or {"layers": [{"rel": "layers/sb1__0_x.png", "status": "completed"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split-layers", {},
                                {"project_id": "p", "sceneNumber": 1,
                                 "elements": [{"name": "차", "location": "왼쪽"}]}, ctx)
    assert code == 200 and seen["sid"] == "sb1" and seen["n"] == 1
    assert body["result"]["layers"][0]["rel"].startswith("layers/sb1__")
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → 새 3개 FAIL.

- [ ] **Step 3: 구현** — `router.py`의 `/api/scenes/unlink-image` 블록 다음에 추가:

```python
    if method == "POST" and p == "/api/scenes/analyze-layers":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = next((s for s in data["scenes"] if s.get("sceneNumber") == b.get("sceneNumber")), None)
        if not sc:
            return 404, {"error": "씬 없음"}
        if not sc.get("_image"):
            return 422, {"error": "씬 이미지 먼저 생성/링크 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("analyze-layers", b.get("project_id", ""))
        res = imagegen.analyze_scene_layers(
            proj_dir, str(proj_dir / sc["_image"]),
            on_line=lambda ln: jobs.append_log(jid, ln))
        jobs.set_status(jid, "completed" if res.get("elements") else "failed")
        return 200, {"job_id": jid, "elements": res.get("elements", []), "error": res.get("error")}

    if method == "POST" and p == "/api/scenes/split-layers":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = next((s for s in data["scenes"] if s.get("sceneNumber") == b.get("sceneNumber")), None)
        if not sc:
            return 404, {"error": "씬 없음"}
        if not sc.get("_image"):
            return 422, {"error": "씬 이미지 없음"}
        elements = b.get("elements") or []
        if not elements:
            return 400, {"error": "elements 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("split-layers", b.get("project_id", ""))
        conc = int(b.get("concurrency", 4))
        res = imagegen.split_scene_to_elements(
            proj_dir, str(proj_dir / sc["_image"]), sc.get("sceneId"), elements,
            concurrency=conc, on_event=lambda r: jobs.append_log(jid, f"{r['name']}: {r['status']}"))
        ok = any(l.get("status") == "completed" for l in res.get("layers", []))
        jobs.set_status(jid, "completed" if ok else "failed", artifact_paths=[str(proj_dir / "layers")])
        return 200, {"job_id": jid, "result": res}
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(scenes): /api/scenes/analyze-layers + /api/scenes/split-layers"
```

---

## Task 4: 패널 — 호버 "레이어" 버튼 + 분석/확인/분리

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`, `index.html`; Modify `tests/test_panel_structure.py`

먼저 `storyboard.js`의 `renderRow`(col-img, unlink-img 버튼)와 `bindRows`를 Read 한다.

- [ ] **Step 1: renderRow — col-img에 "레이어" 버튼(이미지 있을 때)** — col-img의 unlink 버튼 옆에 추가. unlink 버튼 줄

```javascript
    +      (s._image ? '<button class="unlink-img" data-scene="' + n + '" title="씬 이미지 링크 해제">✕</button>' : '')
```

다음에 추가:

```javascript
    +      (s._image ? '<button class="layer-img" data-scene="' + n + '" title="레이어 분리(LLM 분석)">⧉</button>' : '')
```

- [ ] **Step 2: bindRows — 레이어 버튼 바인딩** — unlink-img 바인딩 루프 다음에 추가:

```javascript
  var ly = $("sheet").querySelectorAll("button.layer-img");
  for (var L = 0; L < ly.length; L++) {
    ly[L].addEventListener("click", function () { analyzeLayers(this.getAttribute("data-scene")); });
  }
```

- [ ] **Step 3: analyzeLayers + splitLayers 함수 추가** — 파일 끝(unlinkScene 다음):

```javascript
function analyzeLayers(n) {
  _rowStatus(n, "레이어 분석 중... (codex가 분할 요소 파악, 수십 초)");
  fetch(BACKEND + "/api/scenes/analyze-layers", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10) }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var els = j.elements || [];
      if (!els.length) { _rowStatus(n, "분석 실패: " + (j.error || JSON.stringify(j))); return; }
      var list = els.map(function (e) { return "· " + e.name + " (" + e.location + ")"; }).join("\n");
      if (confirm("이 씬을 다음 요소로 분리합니다:\n\n" + list + "\n\n진행할까요?")) {
        splitLayers(n, els);
      } else {
        _rowStatus(n, "분리 취소됨");
      }
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}

function splitLayers(n, els) {
  _rowStatus(n, "레이어 분리 중... (" + els.length + "개 요소 + 배경, codex)");
  fetch(BACKEND + "/api/scenes/split-layers", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10), elements: els }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var done = (j.result && j.result.layers) ? j.result.layers.filter(function (l) { return l.status === "completed"; }).length : 0;
      _rowStatus(n, done ? ("레이어 " + done + "개 생성 ✓") : ("실패: " + JSON.stringify(j)));
      if (done) loadSheet();   // 레이어 썸네일 갱신
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}
```

- [ ] **Step 4: CSS — 레이어 버튼 호버 표시** — `index.html` `<style>`의 unlink-img CSS 다음에 추가:

```css
    .sheet-row .layer-img { display:none; position:absolute; top:2px; right:28px;
      width:auto; margin:0; padding:2px 6px; font-size:11px; background:rgba(0,0,0,0.6); }
    .sheet-row .col-img:hover .layer-img { display:block; }
```

- [ ] **Step 5: 구조 테스트 + 문법** — `tests/test_panel_structure.py` 끝에:

```python
def test_storyboard_js_has_layer_analysis():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function analyzeLayers" in js and "analyze-layers" in js and "split-layers" in js
```

`node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK`. `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 씬 이미지 호버 레이어(⧉) 버튼 — LLM 분석→요소 확인→분리, 레이어 썸네일 갱신"
```

---

## Task 5: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning storyboard gallery genmodal; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 시트에서 씬 이미지 호버 → ⧉ → 분석(요소 목록 confirm) → 확인 → 요소별 투명 레이어 + 배경 생성 → 행에 레이어 썸네일. (백엔드 재시작 필요 — 신규 엔드포인트.)

---

## Self-Review

- **스펙 커버리지(§C 호버 레이어 + LLM 사전분석 → 확인 → 요소별 분리)**: 호버 ⧉(T4)+analyze(codex 멀티모달, T2/T3)+confirm(T4)+요소별 분리(투명 PNG)+배경(T2/T3)+썸네일 갱신(scenes glob T1). 사용자가 "무엇무엇으로 나뉘는지" 확인 후 진행.
- **무삭제 준수**: split은 versioned_path. 기존 레이어 보존.
- **sceneId 키**: 레이어 `{sid}__*.png` — 구조 편집(P5b) 시에도 안전. _layers는 sid glob.
- **Placeholder 없음**: 전 코드 완전. run_skill(output_schema+images 동시) 사용 — build_codex_cmd가 둘 다 지원하는지 구현 중 확인(미지원 시 보고).
- **타입/일관성**: analyze→{elements:[{name,location}]}, /analyze-layers→{elements}. split→{layers:[{name,rel,status}]}, /split-layers→{result}. storyboard.js analyzeLayers/splitLayers 일치. `_run_codex_image(post=chroma)` 재사용.
- **한계(정직)**: 생성형 요소 재드로잉은 원본과 미세 차이 가능(이전 실증). 분석→확인 단계로 통제하되 완벽 분리는 아님 — 사용자 인지.
