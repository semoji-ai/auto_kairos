# P6 — 씬별 TTS + AE 컴프 조립(레이어 스택) Implementation Plan

**Goal:** 씬별 내레이션을 TTS 오디오로 생성하고(macOS `say`, 한국어 Yuna), scenes.json + 에셋(이미지/레이어/오디오)을 매니페스트로 빌드한 뒤, AE에서 씬별 컴프(배경+요소 레이어 스택 + 오디오 + 자막)를 자동 조립한다.

**Architecture:** `backend/tts.py`(say 합성 + afinfo 길이), `backend/manifest.py`(scenes→manifest.json, 레이어 배열·abs 경로), `build_scene.jsx` 확장(단일 이미지 → 레이어 스택), 라우터 3 엔드포인트, 패널(씬별 TTS 버튼+재생, "AE 조립" 버튼이 manifest 빌드→`akBuildScene(path)`). 무삭제(이미지 규칙 유지; 오디오는 sid 고정명 갱신).

**Tech Stack:** stdlib Python + macOS `say`/`afinfo`(subprocess, 테스트는 monkeypatch), pytest, ExtendScript(jsx), vanilla JS(CEP).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트. JS: `node -e "new Function(...)"`. jsx는 node 파싱 불가(ExtendScript `new File`) → 문자열 포함 검증만.

**현재 사실(확인됨):**
- macOS: `/usr/bin/say`(한국어 보이스 `Yuna` ko_KR), `/usr/bin/afinfo`, `ffprobe`(/opt/homebrew) 사용 가능.
- `scenes.load_scenes`는 씬별 `_image`(최신 imageRef), `_layers`(`layers/*{sid}*.png`), `_status`(narration/image/layers/tts) 부여. tts 플래그는 `audio/*{sid}*` 존재로 판정(P5b에서 추가됨). `dir`=프로젝트 절대경로.
- 레이어 파일명: 요소 `{sid}__{i}_{name}.png`, 배경 `{sid}__bg.png`.
- `build_scene.jsx`의 `akBuildScene(manifestPath)`: manifest 파일을 읽어 씬별 컴프 생성. 현재 씬당 `s.image` 1장 + `s.subtitle` + `s.audio`만 처리. width/height/fps = m.width/height/fps.
- 패널: `main.js`의 `evalScript(jsx+call)`, `readLocal("./jsx/build_scene.jsx")`, `buildComp()`가 하드코딩 `MANIFEST` 경로로 `akBuildScene` 호출. `renderRow`의 col-tts는 `(P6)` 플레이스홀더.
- 라우터 `scenes`/`imagegen` import됨. `handle_request(method,path,query,body,ctx)->(status,dict)`, `ctx["jobs"]`=JobRegistry.

---

## File Structure

- **Create** `backend/tts.py`, `backend/manifest.py`.
- **Modify** `backend/scenes.py` — `load_scenes`에 `_audio` 부여.
- **Modify** `backend/router.py` — `/api/scenes/tts`, `/api/tts/all`, `/api/assembly/manifest`. import에 `tts, manifest` 추가.
- **Modify** `cep/com.autokairos.pd/jsx/build_scene.jsx` — 레이어 스택.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` + `main.js` + `index.html` — TTS 버튼/재생 + AE 조립 버튼.
- **Test** `tests/test_tts.py`, `tests/test_manifest.py`, `tests/test_scenes.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: TTS 모듈 + scenes._audio

**Files:** Create `backend/tts.py`; Modify `backend/scenes.py`; Test `tests/test_tts.py`, `tests/test_scenes.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_tts.py`:

```python
from pathlib import Path
from backend import tts


def test_parse_afinfo_duration():
    sample = "File: x.aiff\nestimated duration: 3.456 sec\nbit rate: ..."
    assert abs(tts._parse_afinfo_duration(sample) - 3.456) < 0.001


def test_parse_afinfo_duration_missing():
    assert tts._parse_afinfo_duration("no duration here") == 0.0


def test_scene_audio_name():
    assert tts.scene_audio_name("abc123") == "tts_abc123.aiff"


def test_synthesize_invokes_say(tmp_path, monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"FORM")   # 더미 오디오
        class R: returncode = 0
        return R()

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    monkeypatch.setattr(tts, "audio_duration", lambda p: 2.5)
    out = tmp_path / "a.aiff"
    res = tts.synthesize("안녕하세요", out, voice="Yuna")
    assert res["status"] == "completed" and out.exists() and res["duration"] == 2.5
    assert "say" in calls["cmd"][0] and "Yuna" in calls["cmd"]


def test_generate_scene_tts(tmp_path, monkeypatch):
    monkeypatch.setattr(tts, "synthesize",
                        lambda text, out, voice=None: (Path(out).write_bytes(b"x"),
                                                       {"status": "completed", "path": str(out), "duration": 1.0})[1])
    proj = tmp_path / "p"; proj.mkdir()
    res = tts.generate_scene_tts(proj, "sid9", "내레이션", voice="Yuna")
    assert res["status"] == "completed"
    assert (proj / "audio" / "tts_sid9.aiff").exists()
    assert res["rel"] == "audio/tts_sid9.aiff"


def test_generate_scene_tts_empty_text(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    res = tts.generate_scene_tts(proj, "sid9", "   ")
    assert res["status"] == "failed"            # 빈 내레이션
```

`tests/test_scenes.py`에 추가:

```python
def test_load_scenes_audio_ref(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aud1", "narration": "n"}])
    (d / "audio").mkdir(); (d / "audio" / "tts_aud1.aiff").write_bytes(b"x")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_audio"] == "audio/tts_aud1.aiff" and s["_status"]["tts"] is True
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `backend/tts.py`:

```python
"""씬 내레이션 TTS — macOS `say`(기본) 기반. 한국어 보이스 Yuna. afinfo로 길이 측정."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

DEFAULT_VOICE = os.environ.get("TTS_VOICE", "Yuna")     # 한국어 ko_KR


def scene_audio_name(sid: str) -> str:
    return f"tts_{sid}.aiff"


def _parse_afinfo_duration(text: str) -> float:
    m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", text)
    return float(m.group(1)) if m else 0.0


def audio_duration(path: Path) -> float:
    """afinfo로 길이(초). 실패 시 0.0."""
    try:
        r = subprocess.run(["afinfo", str(path)], capture_output=True, text=True, timeout=20)
        return _parse_afinfo_duration(r.stdout)
    except Exception:
        return 0.0


def synthesize(text: str, out_path: Path, voice: str | None = None) -> dict:
    """`say`로 합성해 out_path(.aiff) 생성. {status, path, duration}."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("say") is None:
        return {"status": "failed", "error": "say 없음(macOS 전용)", "path": str(out_path), "duration": 0.0}
    cmd = ["say", "-v", voice or DEFAULT_VOICE, "-o", str(out_path), text]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return {"status": "failed", "error": str(e), "path": str(out_path), "duration": 0.0}
    if r.returncode != 0 or not out_path.exists():
        return {"status": "failed", "error": (r.stderr or "")[:200], "path": str(out_path), "duration": 0.0}
    return {"status": "completed", "path": str(out_path), "duration": audio_duration(out_path)}


def generate_scene_tts(proj_dir: Path, sid: str, text: str, voice: str | None = None) -> dict:
    """씬 오디오 audio/tts_{sid}.aiff 생성(갱신). 빈 텍스트면 failed."""
    if not (text or "").strip():
        return {"status": "failed", "error": "내레이션 비어있음"}
    out = Path(proj_dir) / "audio" / scene_audio_name(sid)
    res = synthesize(text, out, voice=voice)
    if res.get("status") == "completed":
        res["rel"] = f"audio/{scene_audio_name(sid)}"
    return res
```

`backend/scenes.py`의 `load_scenes` 루프에서 `_status` 계산 직전/직후에 `_audio` 추가:

```python
        aud_name = f"tts_{sid}.aiff"
        s["_audio"] = (f"audio/{aud_name}"
                       if sid and (proj_dir / "audio" / aud_name).is_file() else None)
```

(주: `_status["tts"]`는 P5b 구현대로 `audio/*{sid}*` glob 유지 — `_audio`와 정합.)

- [ ] **Step 4: 통과** — `... -m pytest tests/test_tts.py tests/test_scenes.py -q` → PASS.

- [ ] **Step 5: 커밋** — `git add backend/tts.py backend/scenes.py tests/test_tts.py tests/test_scenes.py && git commit -m "feat(tts): macOS say 씬 TTS(Yuna) + afinfo 길이 + scenes._audio"`

---

## Task 2: 매니페스트 빌더

**Files:** Create `backend/manifest.py`; Test `tests/test_manifest.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_manifest.py`:

```python
import json
from pathlib import Path
from backend import manifest


def _proj(tmp_path, scenes_arr):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": scenes_arr}, ensure_ascii=False), encoding="utf-8")
    return d


def test_build_manifest_image_only(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "내레이션",
                          "imageRef": "storyboard/sb_a.png", "duration_estimate_sec": 4}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    res = manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert res["scenes"] == 1 and Path(res["path"]).name == "manifest.json"
    sc = mf["scenes"][0]
    assert sc["image"].endswith("storyboard/sb_a.png") and Path(sc["image"]).is_absolute()
    assert sc["subtitle"] == "내레이션" and sc["duration"] == 4
    assert sc["layers"] == [] and sc["audio"] is None


def test_build_manifest_layers_bg_first(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "b", "imageRef": "storyboard/sb_b.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_b.png").write_bytes(b"\x89PNG")
    lay = d / "layers"; lay.mkdir()
    (lay / "b__0_car.png").write_bytes(b"\x89PNG")
    (lay / "b__1_kid.png").write_bytes(b"\x89PNG")
    (lay / "b__bg.png").write_bytes(b"\x89PNG")
    sc = manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    names = [Path(l["path"]).name for l in mf["layers"]]
    assert names[0] == "b__bg.png"                  # 배경이 배열 맨 앞(=AE 최하단)
    assert mf["layers"][0]["kind"] == "bg"
    assert set(names[1:]) == {"b__0_car.png", "b__1_kid.png"}


def test_build_manifest_audio_duration(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "c", "narration": "n"}])
    (d / "audio").mkdir(); (d / "audio" / "tts_c.aiff").write_bytes(b"x")
    monkeypatch.setattr(manifest.tts, "audio_duration", lambda p: 5.5)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8")) if manifest.build_manifest(d) else {}
    sc = mf["scenes"][0]
    assert sc["audio"].endswith("audio/tts_c.aiff") and sc["duration"] == 5.5


def test_build_manifest_duration_fallback(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "e"}])     # 오디오·duration 없음
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["duration"] == 3.0                    # 기본값
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `backend/manifest.py`:

```python
"""scenes.json + 에셋 → AE build_scene.jsx 용 manifest.json(레이어 스택 포함)."""
from __future__ import annotations

import json
from pathlib import Path

from backend import scenes, tts

W, H, FPS = 1920, 1080, 30
DEFAULT_DUR = 3.0


def _abs(proj_dir: Path, rel: str) -> str:
    return str((proj_dir / rel).resolve())


def _scene_layers(proj_dir: Path, layer_rels: list) -> list:
    """[{name, path(abs), kind}] — 배경(__bg)을 맨 앞(AE 최하단)으로."""
    out = []
    bg = [r for r in layer_rels if "__bg" in Path(r).name]
    el = [r for r in layer_rels if "__bg" not in Path(r).name]
    for r in bg + el:
        out.append({"name": Path(r).stem, "path": _abs(proj_dir, r),
                    "kind": "bg" if "__bg" in Path(r).name else "element"})
    return out


def build_manifest(proj_dir: Path) -> dict:
    """manifest.json 생성. 반환 {path, scenes}."""
    proj_dir = Path(proj_dir)
    data = scenes.load_scenes(proj_dir)
    out_scenes = []
    for s in data.get("scenes", []):
        sid = s.get("sceneId")
        layers = _scene_layers(proj_dir, s.get("_layers") or [])
        audio = _abs(proj_dir, s["_audio"]) if s.get("_audio") else None
        if audio:
            dur = tts.audio_duration(proj_dir / s["_audio"]) or DEFAULT_DUR
        else:
            dur = float(s.get("duration_estimate_sec") or DEFAULT_DUR)
        out_scenes.append({
            "ae_comp_name": f"S{s.get('sceneNumber'):02d}_{sid}",
            "image": _abs(proj_dir, s["_image"]) if s.get("_image") else None,
            "layers": layers,
            "audio": audio,
            "subtitle": s.get("narration", "") or "",
            "duration": dur,
        })
    mf = {"width": W, "height": H, "fps": FPS, "scenes": out_scenes}
    out = proj_dir / "manifest.json"
    out.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(out), "scenes": len(out_scenes)}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_manifest.py -q` → PASS.

- [ ] **Step 5: 커밋** — `git add backend/manifest.py tests/test_manifest.py && git commit -m "feat(manifest): scenes→manifest.json(레이어 bg-first 스택·abs 경로·오디오 길이 duration)"`

---

## Task 3: build_scene.jsx — 레이어 스택

**Files:** Modify `cep/com.autokairos.pd/jsx/build_scene.jsx`; Test `tests/test_panel_structure.py`

`build_scene.jsx` 전체를 Read 한다. 씬 루프의 "이미지 레이어" 블록을 교체: `s.layers`가 있으면 레이어를 배열 순서대로 import·추가(배열 앞=먼저 추가=AE 최하단), 없으면 기존 `s.image` 단일 처리.

- [ ] **Step 1: 구현** — 씬 루프 내 이미지 처리부를 아래로 교체(헬퍼 `addFilledLayer`를 함수 상단에 정의):

```javascript
        // (akBuildScene 내부 상단 근처에 헬퍼)
        function addFilledLayer(proj, comp, absPath, W, H, fade) {
            var f = new File(absPath);
            if (!f.exists) return null;
            var foot = proj.importFile(new ImportOptions(f));
            var il = comp.layers.add(foot);
            var sc = Math.max(W / il.source.width, H / il.source.height) * 100;
            il.property("Scale").setValue([sc, sc]);
            if (fade) { var op = il.property("Opacity"); op.setValueAtTime(0, 0); op.setValueAtTime(0.5, 100); }
            return il;
        }
```

그리고 기존 `if (s.image) { ... }` 블록을 교체:

```javascript
            // 레이어 스택(있으면) — 배열 앞이 먼저 추가되어 최하단(배경). 없으면 단일 이미지.
            if (s.layers && s.layers.length) {
                for (var li = 0; li < s.layers.length; li++) {
                    var ok = addFilledLayer(proj, comp, s.layers[li].path, W, H, li === 0);
                    if (!ok) log.push(name + ": 레이어 누락 " + s.layers[li].name);
                }
            } else if (s.image) {
                if (!addFilledLayer(proj, comp, s.image, W, H, true)) log.push(name + ": image 누락");
            }
```

(나머지 자막·오디오·Final 컴프 로직은 그대로 둔다.)

- [ ] **Step 2: 테스트** — `tests/test_panel_structure.py`에:

```python
def test_build_scene_jsx_handles_layers():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "s.layers" in jsx and "addFilledLayer" in jsx
```

`... -m pytest tests/test_panel_structure.py -q` PASS. (jsx는 node 파싱 생략 — ExtendScript)

- [ ] **Step 3: 커밋** — `git add cep/com.autokairos.pd/jsx/build_scene.jsx tests/test_panel_structure.py && git commit -m "feat(jsx): build_scene 레이어 스택(배경 최하단+요소, 페이드)"`

---

## Task 4: 라우터 — tts / assembly

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

`router.py` 상단 import에 `tts, manifest` 추가(`from backend import projects, ..., scenes, search, media, tts, manifest`). `/api/scenes/narration` 인근 패턴 참고.

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`:

```python
def test_scenes_tts(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","narration":"안녕"}]}', encoding="utf-8")
    monkeypatch.setattr(r.tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: {"status": "completed", "rel": f"audio/tts_{sid}.aiff", "duration": 1.0})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/tts", {},
                                {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 200 and body["result"]["rel"] == "audio/tts_sa.aiff"


def test_scenes_tts_no_narration_422(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sa","narration":""}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/scenes/tts", {},
                             {"project_id": "p", "sceneNumber": 1}, ctx)
    assert code == 422


def test_assembly_manifest(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.manifest, "build_manifest",
                        lambda proj_dir: {"path": str(proj_dir / "manifest.json"), "scenes": 0})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assembly/manifest", {}, {"project_id": "p"}, ctx)
    assert code == 200 and body["path"].endswith("manifest.json")
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `/api/scenes/add|...|merge` 블록 다음에 추가:

```python
    if method == "POST" and p in ("/api/scenes/tts", "/api/tts/all"):
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        jobs = ctx["jobs"]
        voice = b.get("voice")
        if p == "/api/tts/all":
            jid = jobs.create("tts-all", b.get("project_id", ""))
            results = []
            for s in data["scenes"]:
                res = tts.generate_scene_tts(proj_dir, s.get("sceneId"), s.get("narration", ""), voice=voice)
                results.append({"sceneNumber": s.get("sceneNumber"), **res})
                jobs.append_log(jid, f"S{s.get('sceneNumber')}: {res.get('status')}")
            ok = any(x.get("status") == "completed" for x in results)
            jobs.set_status(jid, "completed" if ok else "failed", artifact_paths=[str(proj_dir / "audio")])
            return 200, {"job_id": jid, "results": results}
        sn = b.get("sceneNumber")
        sc = next((s for s in data["scenes"] if s.get("sceneNumber") == sn), None)
        if not sc:
            return 404, {"error": "씬 없음"}
        if not (sc.get("narration") or "").strip():
            return 422, {"error": "내레이션 비어있음"}
        jid = jobs.create("tts", b.get("project_id", ""))
        res = tts.generate_scene_tts(proj_dir, sc.get("sceneId"), sc.get("narration", ""), voice=voice)
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "audio")])
        return 200, {"job_id": jid, "result": res}

    if method == "POST" and p == "/api/assembly/manifest":
        proj_dir = root / (body or {}).get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        return 200, manifest.build_manifest(proj_dir)
```

- [ ] **Step 4: 통과(멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋** — `git add backend/router.py tests/test_router.py && git commit -m "feat(api): /api/scenes/tts, /api/tts/all, /api/assembly/manifest"`

---

## Task 5: 패널 — TTS 버튼/재생 + AE 조립

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`, `main.js`, `index.html`; Test `tests/test_panel_structure.py`

`storyboard.js`의 `renderRow`(col-tts), `bindRows`, `main.js`의 `buildComp`, `index.html`의 AE 조립 버튼 영역을 Read 한다.

- [ ] **Step 1: renderRow col-tts** — `'  <div class="col-tts" ...>(P6)</div>'` 를 교체:

```javascript
    + '  <div class="col-tts">'
    +      '<button class="gen-tts alt" data-scene="' + n + '">TTS 생성</button>'
    +      (s._audio ? '<audio controls preload="none" src="file://' + dir + '/' + s._audio + '"></audio>' : '')
    +      '<div class="row-status" data-scene="' + n + '"></div>'
    + '  </div>'
```

(주: row-status는 col-script에도 있음 — `_rowStatus`는 querySelector 첫 매치 사용. col-tts 상태는 별도 함수로 처리해 충돌 회피:)

- [ ] **Step 2: bindRows + 핸들러** — `_bindOp` 라인들 다음:

```javascript
  var gt = $("sheet").querySelectorAll("button.gen-tts");
  for (var g = 0; g < gt.length; g++) {
    gt[g].addEventListener("click", function () { genTts(this.getAttribute("data-scene")); });
  }
```

파일 끝에:

```javascript
function genTts(n) {
  _rowStatus(n, "TTS 생성 중... (say)");
  fetch(BACKEND + "/api/scenes/tts", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10) }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.status === "completed";
      _rowStatus(n, ok ? ("TTS 완료 (" + (j.result.duration || 0).toFixed(1) + "s)") : ("실패: " + JSON.stringify(j)));
      if (ok) loadSheet();      // 오디오 플레이어 표시
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}
```

- [ ] **Step 3: main.js — AE 조립을 매니페스트 빌드 후 실행** — `buildComp`를 프로젝트 기반으로 교체:

```javascript
function buildComp() {
  if (!SELECTED_PROJECT) { $("aeresult").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("aeresult").textContent = "매니페스트 빌드 중...";
  fetch(BACKEND + "/api/assembly/manifest", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error || !j.path) { $("aeresult").textContent = "매니페스트 실패: " + JSON.stringify(j); return; }
      var jsx;
      try { jsx = readLocal("./jsx/build_scene.jsx"); }
      catch (e) { $("aeresult").textContent = "jsx 로드 실패: " + e; return; }
      $("aeresult").textContent = "AE 조립 중... (씬 " + j.scenes + ")";
      var call = "\nakBuildScene(" + JSON.stringify(j.path) + ");";
      evalScript(jsx + call).then(function (r) {
        $("aeresult").textContent = r || "(빈 응답 — AE 콘솔 확인)";
      });
    })
    .catch(function (e) { $("aeresult").textContent = "오류: " + e; });
}
```

- [ ] **Step 4: index.html CSS** — col-tts audio 크기:

```css
    .col-tts audio { width:100%; height:28px; margin-top:4px; }
    .col-tts .gen-tts { width:auto; }
```

- [ ] **Step 5: 테스트 + 문법** — `tests/test_panel_structure.py`:

```python
def test_storyboard_js_has_tts():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function genTts" in js and "/api/scenes/tts" in js

def test_main_js_assembly_uses_manifest():
    js = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert "/api/assembly/manifest" in js and "akBuildScene" in js
```

`node` 문법 체크(storyboard.js, main.js). `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 6: 커밋** — `git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/js/main.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py && git commit -m "feat(panel): 씬별 TTS 생성·재생 + AE 조립(매니페스트→akBuildScene)"`

---

## Task 6: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — main/nav/planning/storyboard/gallery/genmodal `node` 체크.
- [ ] **Step 3: 라이브 스모크(say 실제 실행)** — tesla 복사본(`projects/_smoke_p6`)에서:
  - `POST /api/scenes/tts {sceneNumber:1}` → 200, `audio/tts_*.aiff` 생성 + duration>0 확인(실제 say 호출).
  - `POST /api/assembly/manifest` → 200, `manifest.json` 생성. 내용에 레이어가 있는 씬은 `layers` 배열(배경 first), 오디오 있는 씬은 `audio` abs 경로·`duration` 확인.
  - 검증 후 `_smoke_p6` 제거(Python shutil.rmtree). tesla 원본 미변경.

---

## Self-Review

- **TTS 엔진**: macOS `say`(오프라인·무키·결정적). `TTS_VOICE` env로 보이스 교체. say 부재 시 graceful failed. 추후 elevenlabs는 `synthesize` 교체로 확장 가능.
- **레이어 스택 순서**: manifest가 배경(`__bg`) first → jsx가 배열 순서로 add → AE에서 나중 add가 위 → 요소가 배경 위. 정합.
- **무삭제**: 이미지 규칙 유지. 오디오는 sid 고정명(`tts_{sid}.aiff`) 갱신 — 이미지 자산 아님, 재생성 빈번해 버전 미적용(의도).
- **duration**: 오디오 있으면 실제 길이, 없으면 `duration_estimate_sec`→3.0. 컴프 길이 정합.
- **라우터 일관성**: tts/all·assembly 모두 검증된 패턴. import에 tts·manifest 추가. `scenes` 변수 가리지 않음.
- **패널 정합**: `_audio`(load_scenes) → 오디오 플레이어. buildComp는 SELECTED_PROJECT 기반 매니페스트→akBuildScene(path). 기존 jsx 경로 인자 계약 유지.
- **placeholder 없음**: 전 코드 완전.
- **한계(정직)**: `say`는 합성음(고품질 성우 아님) — 타이밍·미리듣기·조립 검증용. AE 실제 조립은 사용자 환경에서만 확인 가능(headless 불가) → 스모크는 manifest 정확성까지.
