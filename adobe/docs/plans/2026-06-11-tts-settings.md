# TTS 설정(스타일별 voice 프리셋 + 프로젝트 override) Implementation Plan

**Goal:** TTS voice를 설정 가능하게. 기본은 **semoji**(voice_id `W7FnAxJNpD5WGjrF5GLp`). 스타일별 voice 프리셋 제공, 프로젝트별로 스타일 선택 또는 voice_id 직접 입력으로 변경 가능. 패널에 TTS 설정 UI.

**Architecture:** `data/artstyle/voices.json`(스타일→voice 프리셋). `tts.py`에 `effective_voice(proj_dir)`(프로젝트 `tts_config.json` override → 스타일 프리셋 → semoji 기본 순). `synthesize`/`_eleven_fetch`가 voice **cfg dict**(voice_id/model/voice_settings) 사용. 라우터 `GET/POST /api/tts/settings`. 패널 sb-right에 "TTS 설정" 아코디언(스타일 선택·voice_id override·저장·현재 표시).

**Tech Stack:** stdlib Python(urllib), pytest, vanilla JS(CEP).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`. JS: `node -e`.

**현재 사실(확인됨):**
- `backend/tts.py`: 엔진 ElevenLabs(키 있을 때)/say 폴백. `_engine`/`_ext`/`scene_audio_name`/`_eleven_fetch(text, voice)`/`synthesize(text, out_path, voice=None)`/`generate_scene_tts(proj_dir, sid, text, voice=None)`/`audio_duration`/`_clean_text`. `env.get_key(name)`로 env 읽음. 현재 DEFAULT_VOICE_ID=`9Sj8...`(틀림 — quirky용).
- 호출처: `router.py`(`/api/scenes/tts`,`/api/tts/all` — voice=b.get("voice")), `assistant.py`(`_h_tts_all` — voice 미지정), `manifest.py`(audio_duration만).
- `imagegen.STYLE_FILE = data/artstyle/semoji.md`(이미지용, voice 없음). adobe엔 스타일별 JSON 없음.
- v3 실제 voice: semoji/semoji_3D=`W7FnAxJNpD5WGjrF5GLp`(settings: stability1.0,similarity_boost0.9,style0.9,speed1.1), quirky_cartoon=`9Sj8ugvpK1DmcAXyvi3a`(similarity_boost0.6), lego=`4JJwo477JUAx3HV0T7n7`(0.9).
- 패널 sb-right에 `<details class="sb-acc">` 아코디언 패턴(기준 캐릭터) 존재. storyboard.js에 `$`/`BACKEND`/`SELECTED_PROJECT`/`_esc`.

---

## File Structure

- **Create** `data/artstyle/voices.json`.
- **Modify** `backend/tts.py` — voice 프리셋 로드 + `effective_voice` + cfg 기반 합성 + 설정 read/write.
- **Modify** `backend/router.py` — `GET/POST /api/tts/settings`.
- **Modify** `cep/com.autokairos.pd/js/storyboard.js`, `index.html` — TTS 설정 아코디언.
- **Modify** `.gitignore` — `projects/*/tts_config.json`, `projects/*/manifest.json`.
- **Test** `tests/test_tts.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: voices.json + tts.py 설정/해석

**Files:** Create `data/artstyle/voices.json`; Modify `backend/tts.py`; Test `tests/test_tts.py`

- [ ] **Step 1: voices.json** — `data/artstyle/voices.json`:

```json
{
  "default_style": "semoji",
  "presets": {
    "semoji":         { "label": "세모지", "voice_id": "W7FnAxJNpD5WGjrF5GLp",
                        "voice_settings": { "stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": true, "speed": 1.1 } },
    "semoji_3D":      { "label": "세모지 3D", "voice_id": "W7FnAxJNpD5WGjrF5GLp",
                        "voice_settings": { "stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": true, "speed": 1.1 } },
    "quirky_cartoon": { "label": "이로미즘 (quirky cartoon)", "voice_id": "9Sj8ugvpK1DmcAXyvi3a",
                        "voice_settings": { "stability": 1.0, "similarity_boost": 0.6, "style": 0.9, "use_speaker_boost": true, "speed": 1.1 } },
    "lego":           { "label": "레고", "voice_id": "4JJwo477JUAx3HV0T7n7",
                        "voice_settings": { "stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": true, "speed": 1.1 } }
  }
}
```

- [ ] **Step 2: 실패 테스트** — `tests/test_tts.py`에 추가:

```python
def test_load_presets_has_semoji_default():
    pr = tts.load_voice_presets()
    assert pr["default_style"] == "semoji"
    assert pr["presets"]["semoji"]["voice_id"] == "W7FnAxJNpD5WGjrF5GLp"


def test_effective_voice_default_semoji(tmp_path):
    cfg = tts.effective_voice(tmp_path / "p")     # 설정 파일 없음 → semoji 기본
    assert cfg["style"] == "semoji" and cfg["voice_id"] == "W7FnAxJNpD5WGjrF5GLp"
    assert cfg["voice_settings"]["similarity_boost"] == 0.9


def test_set_and_get_tts_config_style(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    tts.set_tts_config(d, style="lego")
    cfg = tts.effective_voice(d)
    assert cfg["style"] == "lego" and cfg["voice_id"] == "4JJwo477JUAx3HV0T7n7"


def test_set_tts_config_voice_id_override(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    tts.set_tts_config(d, style="semoji", voice_id="CUSTOM123")
    cfg = tts.effective_voice(d)
    assert cfg["voice_id"] == "CUSTOM123" and cfg["style"] == "semoji"   # override 우선


def test_effective_voice_unknown_style_falls_back(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    tts.set_tts_config(d, style="nonexistent")
    cfg = tts.effective_voice(d)
    assert cfg["voice_id"] == "W7FnAxJNpD5WGjrF5GLp"    # semoji 프리셋으로 폴백
```

`_eleven_fetch`/`synthesize` cfg화에 맞춰 **기존 test_tts의 ElevenLabs 테스트 갱신**:
- `test_synthesize_elevenlabs`: `monkeypatch.setattr(tts, "_eleven_fetch", lambda text, cfg=None: b"ID3mp3bytes")` 로 시그니처 맞춤. `tts.synthesize("안녕", out, cfg={"voice_id":"V","model":"m","voice_settings":{}})` 호출. (cfg 인자명은 구현과 일치시킬 것.)
- `test_synthesize_elevenlabs_failure`: `def boom(text, cfg=None): raise RuntimeError("401")`.
- `test_synthesize_say_fallback`: say는 cfg 무시·SAY_VOICE 사용 → `res["engine"]=="say"`, cmd에 SAY_VOICE("Yuna") 포함. synthesize 호출 시 cfg 생략 가능.

- [ ] **Step 3: 실패 확인** — FAIL.

- [ ] **Step 4: 구현** — `backend/tts.py` 수정:

(a) 상단에 프리셋 경로 + 로더:

```python
_VOICES_FILE = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "voices.json"


def load_voice_presets() -> dict:
    try:
        return json.loads(_VOICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"default_style": "semoji", "presets": {}}


def _tts_config_path(proj_dir: Path) -> Path:
    return Path(proj_dir) / "tts_config.json"


def get_tts_config(proj_dir: Path) -> dict:
    """프로젝트 tts_config.json(없으면 {})."""
    p = _tts_config_path(proj_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def set_tts_config(proj_dir: Path, *, style=None, voice_id=None, model=None, voice_settings=None) -> dict:
    """프로젝트 TTS 설정 저장(부분 갱신). 반환=effective_voice."""
    proj_dir = Path(proj_dir)
    cfg = get_tts_config(proj_dir)
    if style is not None:
        cfg["style"] = style
    if voice_id is not None:
        cfg["voice_id"] = voice_id          # 빈 문자열이면 override 해제(스타일 프리셋 사용)
        if voice_id == "":
            cfg.pop("voice_id", None)
    if model is not None:
        cfg["model"] = model
    if voice_settings is not None:
        cfg["voice_settings"] = voice_settings
    _tts_config_path(proj_dir).write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return effective_voice(proj_dir)


def effective_voice(proj_dir: Path) -> dict:
    """유효 voice 설정 해석: 프로젝트 override → 스타일 프리셋 → semoji 기본.
    반환 {style, voice_id, model, voice_settings}."""
    presets = load_voice_presets()
    table = presets.get("presets", {})
    default_style = presets.get("default_style", "semoji")
    cfg = get_tts_config(proj_dir)
    style = cfg.get("style") or default_style
    base = table.get(style) or table.get(default_style) or {}
    voice_id = cfg.get("voice_id") or base.get("voice_id") or DEFAULT_VOICE_ID
    voice_settings = cfg.get("voice_settings") or base.get("voice_settings") or VOICE_SETTINGS
    model = cfg.get("model") or base.get("model") or DEFAULT_MODEL
    return {"style": style, "voice_id": voice_id, "model": model, "voice_settings": voice_settings}
```

(b) `DEFAULT_VOICE_ID`를 semoji로 교정: `DEFAULT_VOICE_ID = "W7FnAxJNpD5WGjrF5GLp"`.

(c) `_eleven_fetch`와 `synthesize`를 cfg 기반으로:

```python
def _eleven_fetch(text: str, cfg: dict | None = None) -> bytes:
    cfg = cfg or {}
    key = env.get_key("ELEVENLABS_API_KEY")
    vid = cfg.get("voice_id") or DEFAULT_VOICE_ID
    model = cfg.get("model") or DEFAULT_MODEL
    settings = cfg.get("voice_settings") or VOICE_SETTINGS
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128"
    body = json.dumps({"text": text, "model_id": model, "voice_settings": settings}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def synthesize(text: str, out_path: Path, cfg: dict | None = None) -> dict:
    out_path = Path(out_path); out_path.parent.mkdir(parents=True, exist_ok=True)
    eng = _engine(); clean = _clean_text(text)
    try:
        if eng == "elevenlabs":
            out_path.write_bytes(_eleven_fetch(clean, cfg))
        else:
            if shutil.which("say") is None:
                return {"status": "failed", "error": "say 없음·ElevenLabs 키 없음", "path": str(out_path), "duration": 0.0}
            _synth_say(clean, out_path, SAY_VOICE)
    except Exception as e:
        return {"status": "failed", "error": str(e)[:200], "path": str(out_path), "duration": 0.0, "engine": eng}
    if not out_path.exists() or out_path.stat().st_size == 0:
        return {"status": "failed", "error": "출력 없음", "path": str(out_path), "duration": 0.0, "engine": eng}
    dur = audio_duration(out_path)
    if dur == 0.0 and eng == "elevenlabs":
        dur = round(out_path.stat().st_size * 8 / 128000, 3)
    return {"status": "completed", "path": str(out_path), "duration": dur, "engine": eng}
```

(d) `generate_scene_tts`가 effective_voice 사용(+ voice 인자로 voice_id 1회 override):

```python
def generate_scene_tts(proj_dir: Path, sid: str, text: str, voice: str | None = None) -> dict:
    if not (text or "").strip():
        return {"status": "failed", "error": "내레이션 비어있음"}
    cfg = effective_voice(proj_dir)
    if voice:
        cfg = {**cfg, "voice_id": voice}
    out = Path(proj_dir) / "audio" / scene_audio_name(sid)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = synthesize(text, out, cfg=cfg)
    if res.get("status") == "completed":
        res["rel"] = f"audio/{out.name}"
        res["voice_id"] = cfg["voice_id"]
    return res
```

- [ ] **Step 5: 통과** — `... -m pytest tests/test_tts.py -q` → PASS.

- [ ] **Step 6: 커밋** — `git add data/artstyle/voices.json backend/tts.py tests/test_tts.py && git commit -m "feat(tts): 스타일별 voice 프리셋 + 프로젝트 override(effective_voice). 기본 semoji 교정(W7Fn…)"`

---

## Task 2: 라우터 — /api/tts/settings

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`:

```python
def test_tts_settings_get_default(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/tts/settings", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["config"]["style"] == "semoji"
    assert body["config"]["voice_id"] == "W7FnAxJNpD5WGjrF5GLp"
    assert "semoji" in body["presets"]["presets"]


def test_tts_settings_post_style(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/tts/settings", {},
                                {"project_id": "p", "style": "lego"}, ctx)
    assert code == 200 and body["config"]["voice_id"] == "4JJwo477JUAx3HV0T7n7"


def test_tts_settings_post_voice_override(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/tts/settings", {},
                                {"project_id": "p", "voice_id": "ZZZ999"}, ctx)
    assert code == 200 and body["config"]["voice_id"] == "ZZZ999"
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `/api/assembly/manifest` 인근에 추가:

```python
    if p == "/api/tts/settings" and method in ("GET", "POST"):
        pid = (query.get("project_id") if method == "GET" else (body or {}).get("project_id")) or ""
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if method == "POST":
            b = body or {}
            tts.set_tts_config(proj_dir, style=b.get("style"), voice_id=b.get("voice_id"),
                               model=b.get("model"), voice_settings=b.get("voice_settings"))
        return 200, {"config": tts.effective_voice(proj_dir), "presets": tts.load_voice_presets()}
```

- [ ] **Step 4: 통과(멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋** — `git add backend/router.py tests/test_router.py && git commit -m "feat(api): GET/POST /api/tts/settings — 스타일/voice_id 설정"`

---

## Task 3: 패널 — TTS 설정 아코디언

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`, `index.html`; Test `tests/test_panel_structure.py`

`index.html`의 sb-right "기준 캐릭터" `<details>` 인근을 Read 한다.

- [ ] **Step 1: index.html — TTS 설정 아코디언** — "기준 캐릭터" details 다음(또는 앞)에 추가:

```html
            <details class="sb-acc" id="ttsSettings">
              <summary>🔊 TTS 설정</summary>
              <div class="label">스타일</div>
              <select id="ttsStyle"></select>
              <div class="label">voice ID (직접 지정 시 스타일보다 우선, 비우면 스타일 사용)</div>
              <input id="ttsVoiceId" type="text" placeholder="voice ID">
              <button id="btnSaveTts" class="mini">저장</button>
              <div class="box" id="ttsStatus" style="font-size:11px">—</div>
            </details>
```

- [ ] **Step 2: storyboard.js — 로드/저장** — 파일 끝에:

```javascript
function loadTtsSettings() {
  if (!SELECTED_PROJECT) return;
  fetch(BACKEND + "/api/tts/settings?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var sel = $("ttsStyle"); if (!sel) return;
      var presets = (j.presets && j.presets.presets) || {};
      sel.innerHTML = Object.keys(presets).map(function (k) {
        return '<option value="' + k + '">' + _esc(presets[k].label || k) + '</option>';
      }).join("");
      if (j.config) {
        sel.value = j.config.style;
        $("ttsStatus").textContent = "현재: " + j.config.style + " / voice " + j.config.voice_id;
      }
    }).catch(function () {});
}

function saveTtsSettings() {
  if (!SELECTED_PROJECT) { $("ttsStatus").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var style = $("ttsStyle").value;
  var vid = ($("ttsVoiceId").value || "").trim();
  $("ttsStatus").textContent = "저장 중...";
  fetch(BACKEND + "/api/tts/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, style: style, voice_id: vid }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      $("ttsStatus").textContent = j.config
        ? ("저장됨 — " + j.config.style + " / voice " + j.config.voice_id) : ("실패: " + JSON.stringify(j));
      $("ttsVoiceId").value = "";
    }).catch(function (e) { $("ttsStatus").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  var b = $("btnSaveTts"); if (b) b.addEventListener("click", saveTtsSettings);
  var d = $("ttsSettings");
  if (d) d.addEventListener("toggle", function () { if (d.open) loadTtsSettings(); });
});
```

- [ ] **Step 3: 테스트 + 문법** — `tests/test_panel_structure.py`:

```python
def test_tts_settings_panel():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadTtsSettings" in js and "/api/tts/settings" in js
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'id="ttsStyle"' in html and 'id="ttsVoiceId"' in html
```

`node` 문법(storyboard.js). `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 4: 커밋** — `git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py && git commit -m "feat(panel): TTS 설정 아코디언(스타일 선택·voice ID override·저장)"`

---

## Task 4: .gitignore + 통합 검증

- [ ] **Step 1: .gitignore** — 추가: `projects/*/tts_config.json`, `projects/*/manifest.json`. 커밋.
- [ ] **Step 2: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 3: 전체 JS 문법** — main/nav/planning/storyboard/gallery/genmodal/assistant `node` 체크.
- [ ] **Step 4: 라이브 스모크** — 백엔드 재시작 후 tesla 복사본(`projects/_smoke_tts`):
  - `GET /api/tts/settings` → 기본 semoji + voice W7Fn… 확인.
  - `POST {style:"lego"}` → voice 4JJ… 확인. `POST {voice_id:"X1"}` → override 확인. tts_config.json 생성 확인.
  - 복사본 제거. tesla 원본 미변경.

---

## Self-Review

- **기본 semoji 교정**: DEFAULT_VOICE_ID·semoji 프리셋 모두 `W7FnAxJNpD5WGjrF5GLp`. (이전 `9Sj8…`는 quirky였던 버그 수정.)
- **해석 우선순위**: 프로젝트 voice_id override > 스타일 프리셋 > semoji 기본. 알 수 없는 스타일은 semoji 폴백.
- **변경 가능**: 스타일 선택 또는 voice_id 직접 입력(빈 값=프리셋 사용). 프로젝트별 `tts_config.json` 영속.
- **호출처 호환**: `generate_scene_tts`는 voice 미지정 시 effective_voice 사용 → router/assistant 변경 불필요. voice 인자는 1회 override 유지.
- **cfg 시그니처 일관**: `_eleven_fetch(text, cfg)`/`synthesize(text, out, cfg)`. say 폴백은 cfg 무시·SAY_VOICE.
- **gitignore**: tts_config.json·manifest.json(런타임 산출) 제외.
- **placeholder 없음**: 전 코드 완전.
- **한계(정직)**: 보이스 미리듣기(설정창 내)는 미구현 — 저장 후 씬 TTS로 확인. voice_settings 세부(stability 등)는 스타일 프리셋 값 사용, 패널에서 개별 슬라이더 편집은 미구현(필요 시 확장).
