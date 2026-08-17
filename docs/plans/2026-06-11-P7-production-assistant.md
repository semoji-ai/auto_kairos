# P7 — 실행형 제작 비서(NL 지시 → 파이프라인 오케스트레이션) Implementation Plan

**Goal:** 하단 "제작 비서" 채팅에 자연어로 지시하면(예: "이미지 없는 씬 채우고 음성 입혀서 AE로 합쳐줘"), codex가 **정해진 액션 카탈로그** 중 무엇을 어떤 순서로 실행할지 판단하고, 백엔드가 기존 기능을 호출해 순차 실행한다.

**Architecture:** `backend/assistant.py` = (1) 안전한 **액션 카탈로그**(generate_missing_images / split_layers / tts_all / assemble) — 각 핸들러는 기존 모듈 함수 재사용, (2) `plan_actions`(codex+schema로 NL→액션 목록), (3) `run_assistant`(plan→순차 실행, 결과 수집). 라우터 `/api/assistant`(job). 패널 `#chat-dock` 활성화 + 플랜/결과 로그. **LLM은 카탈로그 enum 안에서만 선택**(임의 명령 실행 불가 — 바운디드·안전). 실행은 결정적 Python 디스패치(테스트는 핸들러 주입).

**Tech Stack:** stdlib Python + codex(run_skill, output_schema), pytest(주입/monkeypatch), vanilla JS(CEP).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`. JS: `node -e "new Function(...)"`.

**현재 사실(확인됨):**
- `scenes.load_scenes` → 씬별 `_image`/`_layers`/`_audio`/`_status`(narration/image/layers/tts), `dir`. `set_image_ref`, `new_scene_image_name(sid)` 존재.
- `imagegen.generate_one(proj_dir, rel_out, image_prompt, *, subdir, retries, on_line, character_ref)`, `analyze_scene_layers(proj_dir, scene_image, *, narration, context, on_line)→{elements}`, `split_scene_to_elements(proj_dir, scene_image, sid, elements, *, subdir, concurrency, on_event)`.
- `tts.generate_scene_tts(proj_dir, sid, text, voice)`. `manifest.build_manifest(proj_dir)→{path, scenes}`.
- `codex_runner.run_skill(prompt, cwd, *, output_schema, output_last, images, on_line)`.
- 라우터: `handle_request(method,path,query,body,ctx)`, top import에 `scenes,imagegen,tts,manifest` 있음(P6 후). `ctx["jobs"]`.
- 패널: `index.html`에 `#chat-dock`(#chatInput, #btnChatSend — 현재 disabled), `main.js` `$`/`BACKEND`/`SELECTED_PROJECT`/`evalScript`. 스크립트 로드 순서: main, nav, planning, storyboard, gallery, genmodal(끝).

---

## File Structure

- **Create** `backend/assistant.py`, `backend/schemas/assistant_plan.schema.json`.
- **Modify** `backend/router.py` — `/api/assistant`. import에 `assistant` 추가.
- **Create** `cep/com.autokairos.pd/js/assistant.js`; **Modify** `index.html`(chat-dock 활성화 + 로그 + script 태그).
- **Test** `tests/test_assistant.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: assistant.py — 카탈로그 + 핸들러 + plan/run

**Files:** Create `backend/assistant.py`, `backend/schemas/assistant_plan.schema.json`; Test `tests/test_assistant.py`

- [ ] **Step 1: 스키마** — `backend/schemas/assistant_plan.schema.json`:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["actions"],
  "properties": {
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["action", "reason"],
        "properties": {
          "action": { "type": "string",
            "enum": ["generate_missing_images", "split_layers", "tts_all", "assemble"] },
          "reason": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: 실패 테스트** — `tests/test_assistant.py`:

```python
import json
from pathlib import Path
from backend import assistant


def _proj(tmp_path, scenes_arr):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": scenes_arr}, ensure_ascii=False), encoding="utf-8")
    return d


def test_catalog_names():
    assert set(assistant.ACTION_HANDLERS) == {
        "generate_missing_images", "split_layers", "tts_all", "assemble"}


def test_project_status_summary(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "n",
                          "imageRef": "storyboard/sb_a.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    st = assistant.project_status(d)
    assert "1" in st and "이미지" in st


def test_plan_actions_parses(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])

    def fake_run(prompt, cwd, *, output_schema=None, output_last=None, images=None, on_line=None, **kw):
        Path(output_last).write_text('{"actions":[{"action":"tts_all","reason":"음성"},'
                                     '{"action":"assemble","reason":"합치기"}]}', encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}

    monkeypatch.setattr(assistant, "run_skill", fake_run)
    actions = assistant.plan_actions(d, "음성 입혀서 합쳐줘")
    assert [a["action"] for a in actions] == ["tts_all", "assemble"]


def test_plan_actions_failure_returns_empty(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    monkeypatch.setattr(assistant, "run_skill",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert assistant.plan_actions(d, "뭐든") == []


def test_run_assistant_dispatches_in_order(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    calls = []
    handlers = {
        "tts_all": lambda proj_dir, on_event=None: calls.append("tts") or {"done": 1},
        "assemble": lambda proj_dir, on_event=None: calls.append("asm") or {"path": "m.json"},
    }
    out = assistant.run_assistant(
        d, "x",
        planner=lambda proj_dir, instr, on_line=None: [
            {"action": "tts_all", "reason": "r1"}, {"action": "assemble", "reason": "r2"}],
        handlers=handlers)
    assert calls == ["tts", "asm"]
    assert [r["action"] for r in out["results"]] == ["tts_all", "assemble"]
    assert out["results"][0]["result"] == {"done": 1}


def test_run_assistant_unknown_action_skipped(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    out = assistant.run_assistant(
        d, "x",
        planner=lambda proj_dir, instr, on_line=None: [{"action": "nope", "reason": "?"}],
        handlers={})
    assert out["results"][0]["result"]["status"] == "skipped"


def test_generate_missing_images_only_missing(tmp_path, monkeypatch):
    from backend import imagegen, scenes as sc
    d = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "a", "image_prompt": "그림1", "imageRef": "storyboard/sb_a.png"},
        {"sceneNumber": 2, "sceneId": "b", "image_prompt": "그림2", "imageRef": ""}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    gen = []

    def fake_gen(proj_dir, rel_out, prompt, *, subdir="images", **kw):
        gen.append(prompt)
        (proj_dir / subdir).mkdir(parents=True, exist_ok=True)
        (proj_dir / subdir / rel_out).write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(proj_dir / subdir / rel_out)}

    monkeypatch.setattr(imagegen, "generate_one", fake_gen)
    res = assistant.ACTION_HANDLERS["generate_missing_images"](d)
    assert gen == ["그림2"] and res["generated"] == 1     # 씬2만(씬1은 이미 이미지 있음)


def test_tts_all_handler(tmp_path, monkeypatch):
    from backend import tts as _tts
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "안녕"},
                         {"sceneNumber": 2, "sceneId": "b", "narration": ""}])
    monkeypatch.setattr(_tts, "generate_scene_tts",
                        lambda proj_dir, sid, text, voice=None: {"status": "completed"})
    res = assistant.ACTION_HANDLERS["tts_all"](d)
    assert res["generated"] == 1                          # 내레이션 있는 씬만


def test_assemble_handler(tmp_path, monkeypatch):
    from backend import manifest
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"}])
    monkeypatch.setattr(manifest, "build_manifest", lambda proj_dir: {"path": "m.json", "scenes": 1})
    assert assistant.ACTION_HANDLERS["assemble"](d)["scenes"] == 1
```

- [ ] **Step 3: 실패 확인** — FAIL.

- [ ] **Step 4: 구현** — `backend/assistant.py`:

```python
"""실행형 제작 비서 — 자연어 지시를 안전한 액션 카탈로그로 매핑(codex)해 순차 실행.
LLM은 ACTION_HANDLERS의 enum 안에서만 선택한다(임의 실행 불가)."""
from __future__ import annotations

import json
from pathlib import Path

from backend import scenes, imagegen, tts, manifest
from backend.codex_runner import run_skill

_PLAN_SCHEMA = Path(__file__).resolve().parent / "schemas" / "assistant_plan.schema.json"


# ---- 액션 핸들러(각 (proj_dir, on_event=None) -> result dict) ----

def _h_generate_missing_images(proj_dir: Path, on_event=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in data["scenes"]:
        if s.get("_image"):
            continue
        prompt = (s.get("image_prompt") or s.get("visual_summary") or "").strip()
        if not prompt:
            continue
        name = scenes.new_scene_image_name(s.get("sceneId"))
        res = imagegen.generate_one(proj_dir, name, prompt, subdir="storyboard")
        if res.get("status") == "completed":
            rel = Path(res["path"]).relative_to(proj_dir).as_posix()
            scenes.set_image_ref(proj_dir, s.get("sceneNumber"), rel)
            n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} 이미지: {res.get('status')}")
    return {"generated": n}


def _h_split_layers(proj_dir: Path, on_event=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in data["scenes"]:
        if not s.get("_image") or s.get("_layers"):
            continue
        img = str(proj_dir / s["_image"])
        ctx = f"제목: {s.get('title', '')} / 요약: {s.get('visual_summary', '')}"
        els = imagegen.analyze_scene_layers(proj_dir, img,
                                            narration=s.get("narration", "") or "", context=ctx).get("elements", [])
        if not els:
            continue
        imagegen.split_scene_to_elements(proj_dir, img, s.get("sceneId"), els)
        n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} 레이어 {len(els)}개")
    return {"split_scenes": n}


def _h_tts_all(proj_dir: Path, on_event=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in data["scenes"]:
        if not (s.get("narration") or "").strip():
            continue
        res = tts.generate_scene_tts(proj_dir, s.get("sceneId"), s.get("narration", ""))
        if res.get("status") == "completed":
            n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} TTS: {res.get('status')}")
    return {"generated": n}


def _h_assemble(proj_dir: Path, on_event=None) -> dict:
    return manifest.build_manifest(proj_dir)


ACTION_HANDLERS = {
    "generate_missing_images": _h_generate_missing_images,
    "split_layers": _h_split_layers,
    "tts_all": _h_tts_all,
    "assemble": _h_assemble,
}

_CATALOG_DESC = (
    "- generate_missing_images: 이미지가 없는 씬에 씬 이미지를 생성한다.\n"
    "- split_layers: 이미지가 있고 레이어가 없는 씬을 캐릭터/움직임 기준으로 레이어 분리한다.\n"
    "- tts_all: 내레이션이 있는 모든 씬의 음성을 생성한다.\n"
    "- assemble: 매니페스트를 빌드해 AE 조립을 준비한다(보통 마지막).\n"
)


def project_status(proj_dir: Path) -> str:
    data = scenes.load_scenes(proj_dir)
    ss = data.get("scenes", [])
    img = sum(1 for s in ss if s.get("_image"))
    lay = sum(1 for s in ss if s.get("_layers"))
    aud = sum(1 for s in ss if s.get("_audio"))
    return f"총 {len(ss)}씬 / 이미지 {img} / 레이어 {lay} / TTS {aud}"


def plan_actions(proj_dir: Path, instruction: str, *, on_line=None) -> list:
    """codex로 NL 지시를 액션 목록으로. 실패 시 []."""
    prompt = (
        "너는 영상 제작 파이프라인 비서다. 사용자의 지시를 아래 액션들의 순서 있는 목록으로 변환해라. "
        "목록 외 동작은 만들지 말고, 지시에 필요한 액션만 골라라. 보통 assemble은 마지막에 둔다.\n\n"
        f"## 가능한 액션\n{_CATALOG_DESC}\n## 현재 프로젝트 상태\n{project_status(proj_dir)}\n\n"
        f"## 사용자 지시\n{instruction}"
    )
    out = proj_dir / ".assistant_plan.json"
    res = run_skill(prompt, proj_dir, output_schema=str(_PLAN_SCHEMA), output_last=str(out), on_line=on_line)
    if res.get("returncode") != 0 or not out.is_file():
        return []
    try:
        return json.loads(out.read_text(encoding="utf-8")).get("actions", [])
    except Exception:
        return []


def run_assistant(proj_dir: Path, instruction: str, *,
                  planner=None, handlers=None, on_event=None) -> dict:
    """plan_actions로 계획 → 핸들러 순차 실행 → 결과 수집. planner/handlers 주입 가능(테스트)."""
    proj_dir = Path(proj_dir)
    planner = planner or plan_actions
    handlers = handlers if handlers is not None else ACTION_HANDLERS
    actions = planner(proj_dir, instruction, on_line=on_event) if _accepts_on_line(planner) else planner(proj_dir, instruction)
    results = []
    for a in actions:
        name = a.get("action")
        if on_event:
            on_event(f"▶ {name}: {a.get('reason', '')}")
        h = handlers.get(name)
        if h is None:
            results.append({"action": name, "reason": a.get("reason"), "result": {"status": "skipped"}})
            continue
        try:
            r = h(proj_dir, on_event=on_event)
        except TypeError:
            r = h(proj_dir)
        results.append({"action": name, "reason": a.get("reason"), "result": r})
    return {"plan": actions, "results": results}


def _accepts_on_line(fn) -> bool:
    try:
        import inspect
        return "on_line" in inspect.signature(fn).parameters
    except (ValueError, TypeError):
        return False
```

(주: 테스트의 주입 planner는 `(proj_dir, instr, on_line=None)` 시그니처 — `_accepts_on_line`가 True여서 on_line=on_event로 호출됨. 실 planner도 on_line 받음. 핸들러 주입 시 `on_event=` 키워드 미지원 람다면 TypeError fallback로 위치 호출.)

- [ ] **Step 5: 통과** — `... -m pytest tests/test_assistant.py -q` → PASS.

- [ ] **Step 6: 커밋** — `git add backend/assistant.py backend/schemas/assistant_plan.schema.json tests/test_assistant.py && git commit -m "feat(assistant): NL→액션 카탈로그(codex) + 순차 실행 오케스트레이터"`

---

## Task 2: 라우터 — /api/assistant

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

상단 import에 `assistant` 추가(`from backend import projects, ..., tts, manifest, assistant`).

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`:

```python
def test_assistant_endpoint(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.assistant, "run_assistant",
                        lambda proj_dir, instr, on_event=None: {
                            "plan": [{"action": "assemble", "reason": "x"}],
                            "results": [{"action": "assemble", "reason": "x", "result": {"scenes": 0}}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assistant", {},
                                {"project_id": "p", "instruction": "합쳐줘"}, ctx)
    assert code == 200 and body["plan"][0]["action"] == "assemble"
    assert body["results"][0]["result"]["scenes"] == 0


def test_assistant_requires_instruction(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/assistant", {}, {"project_id": "p"}, ctx)
    assert code == 400


def test_assistant_missing_project_404(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, _ = handle_request("POST", "/api/assistant", {},
                             {"project_id": "none", "instruction": "x"}, ctx)
    assert code == 404
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `/api/assembly/manifest` 블록 다음:

```python
    if method == "POST" and p == "/api/assistant":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        instruction = (b.get("instruction") or "").strip()
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        if not instruction:
            return 400, {"error": "instruction 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("assistant", b.get("project_id", ""))
        out = assistant.run_assistant(proj_dir, instruction,
                                      on_event=lambda ln: jobs.append_log(jid, ln))
        jobs.set_status(jid, "completed")
        return 200, {"job_id": jid, **out}
```

- [ ] **Step 4: 통과(멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋** — `git add backend/router.py tests/test_router.py && git commit -m "feat(api): /api/assistant — NL 지시 오케스트레이션"`

---

## Task 3: 패널 — 제작 비서 채팅 활성화

**Files:** Create `cep/com.autokairos.pd/js/assistant.js`; Modify `index.html`; Test `tests/test_panel_structure.py`

`index.html`의 `#chat-dock`와 `</body>` 직전 script 태그들을 Read 한다.

- [ ] **Step 1: chat-dock 활성화 + 로그** — `#chat-dock` 블록 교체:

```html
    <div id="chat-dock">
      <div class="label" style="margin:0 0 4px">💬 제작 비서</div>
      <div class="box" id="chatLog" style="max-height:22vh;overflow:auto;margin-bottom:4px">무엇을 할까요? (예: "이미지 없는 씬 채우고 음성 입혀서 합쳐줘")</div>
      <div class="row">
        <input id="chatInput" type="text" placeholder='지시를 입력하세요…'>
        <button id="btnChatSend">전송</button>
      </div>
    </div>
```

- [ ] **Step 2: assistant.js** — 신규 파일:

```javascript
/* 제작 비서 — NL 지시를 /api/assistant 로 보내 플랜·결과를 로그에 표시. main.js 전역 사용. */
function _chatAppend(html) {
  var log = $("chatLog");
  log.innerHTML += '<div class="chat-msg">' + html + '</div>';
  log.scrollTop = log.scrollHeight;
}

function sendChat() {
  if (!SELECTED_PROJECT) { _chatAppend("⚠ 프로젝트를 먼저 선택하세요."); return; }
  var inp = $("chatInput");
  var msg = (inp.value || "").trim();
  if (!msg) return;
  _chatAppend("🧑 " + _esc(msg));
  inp.value = "";
  _chatAppend("🤖 계획 세우는 중…");
  fetch(BACKEND + "/api/assistant", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, instruction: msg }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { _chatAppend("실패: " + _esc(j.error)); return; }
      var plan = (j.plan || []).map(function (a) { return "• " + a.action + " — " + _esc(a.reason || ""); }).join("<br>");
      _chatAppend("📋 계획:<br>" + (plan || "(없음)"));
      (j.results || []).forEach(function (res) {
        _chatAppend("✓ " + res.action + ": " + _esc(JSON.stringify(res.result)));
      });
      _chatAppend("완료. 시트/AE를 확인하세요.");
      if (typeof loadSheet === "function") loadSheet();
    })
    .catch(function (e) { _chatAppend("오류: " + _esc(String(e))); });
}

document.addEventListener("DOMContentLoaded", function () {
  var b = $("btnChatSend"); if (b) b.addEventListener("click", sendChat);
  var i = $("chatInput");
  if (i) i.addEventListener("keydown", function (e) { if (e.key === "Enter") sendChat(); });
});
```

(주: `_esc`는 storyboard.js 전역. 로드 순서상 assistant.js를 storyboard.js 뒤에 둔다.)

- [ ] **Step 3: index.html script 태그** — genmodal.js 줄 다음(또는 마지막)에:

```html
  <script src="js/assistant.js"></script>
```

CSS(선택, `<style>`에): `.chat-msg { margin:2px 0; font-size:12px; line-height:1.4; }`

- [ ] **Step 4: 테스트 + 문법** — `tests/test_panel_structure.py`:

```python
def test_assistant_js_wired():
    js = (PANEL / "js" / "assistant.js").read_text(encoding="utf-8")
    assert "function sendChat" in js and "/api/assistant" in js

def test_index_loads_assistant_js():
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert "js/assistant.js" in html and 'id="chatInput"' in html
    assert "disabled" not in html.split('id="chatInput"')[1].split(">")[0]   # 입력 활성화
```

`node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/assistant.js','utf8'))" && echo OK`. `... -m pytest tests/test_panel_structure.py -q` PASS.

- [ ] **Step 5: 커밋** — `git add cep/com.autokairos.pd/js/assistant.js cep/com.autokairos.pd/index.html tests/test_panel_structure.py && git commit -m "feat(panel): 제작 비서 채팅 활성화(/api/assistant 플랜·결과 표시)"`

---

## Task 4: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — main/nav/planning/storyboard/gallery/genmodal/assistant `node` 체크.
- [ ] **Step 3: 라이브 스모크(가벼운 것만)** — tesla 복사본(`projects/_smoke_p7`)에서 백엔드 재시작 후:
  - `POST /api/assistant {instruction:"AE로 합쳐줘"}` → 200. 실제 codex 플래너가 `assemble`을 포함하는지 확인(플랜에 assemble 존재 + results에서 manifest 빌드 성공). **무거운 이미지/레이어 액션은 지시에 포함하지 말 것**(assemble만 가벼움). manifest.json 생성 확인.
  - `_smoke_p7` 제거(Python shutil.rmtree). tesla 원본 미변경(복사본에서만 실행).

---

## Self-Review

- **안전·바운디드**: LLM은 4개 enum 액션만 선택(스키마 강제). 임의 명령/쉘 실행 불가. 각 핸들러는 기존 검증된 모듈 함수만 호출.
- **결정적 실행**: `run_assistant`는 순수 디스패치. planner/handlers 주입으로 LLM 없이 테스트.
- **무삭제·재사용**: generate_missing_images는 이미지 없는 씬만(기존 보존), split_layers는 레이어 없는 씬만, tts_all은 내레이션 있는 씬만. 중복 작업·덮어쓰기 없음.
- **시그니처 정합**: 핸들러 `(proj_dir, on_event=None)`. run_assistant가 on_event 키워드로 호출, 미지원 시 TypeError fallback. 주입 planner on_line 처리는 `_accepts_on_line`로 분기.
- **라우터 일관성**: `/api/assistant`는 job 생성·로그·완료. import에 assistant 추가. 모듈명 미가림.
- **패널 정합**: chat-dock 활성화, assistant.js는 storyboard.js(`_esc`) 뒤 로드, 완료 후 loadSheet 갱신.
- **placeholder 없음**: 전 코드 완전.
- **한계(정직)**: codex 플래너는 비결정적 — 지시가 모호하면 액션 선택이 흔들릴 수 있음(reason으로 사용자 확인 가능). 실행은 동기(긴 작업은 응답 지연) — 진행 로그는 job 로그에 적재, 패널은 완료 후 일괄 표시(스트리밍 미구현). 무거운 액션(이미지/레이어)은 시간이 오래 걸림.
```
