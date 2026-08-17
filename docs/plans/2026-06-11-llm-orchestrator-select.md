# LLM 오케스트레이터 선택(Claude 추론 + codex 이미지) Implementation Plan

**Goal:** 추론(오케스트레이터) LLM을 **선택 가능**하게 — Claude(기본) 또는 codex. 텍스트 추론(씬 분해, 제작 비서 플래닝)은 선택된 LLM, **멀티모달(이미지 첨부)과 이미지 생성은 항상 codex**(claude 헤드리스 비전 미지원). 패널에서 선택.

**Architecture:** `claude_runner`(claude CLI 헤드리스 어댑터) + `llm`(오케스트레이터 선택·디스패치). 추론 호출부(`/api/skills/run`, `assistant.plan_actions`, `analyze_scene_layers`)를 `llm.run_orchestrator`로 라우팅. 디스패치 규칙: **images 있으면 무조건 codex**, 아니면 선택 엔진. 이미지 생성(`_run_codex_image`)은 불변. 선택값은 `data/llm_config.json` + env `AK_ORCHESTRATOR`, 패널 드롭다운.

**Tech Stack:** stdlib Python(subprocess), pytest(monkeypatch), vanilla JS(CEP).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`.

**검증된 사실(중요):**
- `claude` CLI 설치됨(2.1.173). `claude -p --output-format json --json-schema <file> [--model <m>]` 로 **구조화 출력 가능**. 프롬프트는 **stdin**.
- **중첩 방지**: `claude`를 서브프로세스로 띄울 때 env에서 `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT` **반드시 pop**(안 하면 행 걸림).
- `--output-format json` 은 `{type, result, ...}` 엔벨로프 반환 — 모델 최종 출력은 `result` 필드(스키마 지정 시 그 안이 JSON).
- **claude 헤드리스 멀티모달(@이미지)은 행 걸림 → 미지원.** 비전은 codex(`-i`).
- codex `codex_runner.run_skill(prompt, cwd, *, session_id, output_schema, output_last, sandbox, images, on_line) -> {returncode, session_id, output_last}`.
- `run_skill` 사용처: `router.py` `/api/skills/run`(scene-decompose), `imagegen.analyze_scene_layers`(images 첨부), `assistant.plan_actions`(텍스트). 이미지 생성은 `imagegen._run_codex_image`(별도, codex 빌트인 image_gen) — **불변**.

---

## File Structure

- **Create** `backend/claude_runner.py`, `backend/llm.py`.
- **Modify** `backend/router.py` — `/api/skills/run`·analyze·assistant를 `llm.run_orchestrator`로; `/api/llm/settings` 추가.
- **Modify** `backend/imagegen.py` — `analyze_scene_layers`가 `llm.run_orchestrator` 사용(images→codex 자동).
- **Modify** `backend/assistant.py` — `plan_actions`가 `llm.run_orchestrator` 사용.
- **Modify** `cep/com.autokairos.pd/index.html`, `js/main.js`(또는 nav) — LLM 선택 드롭다운.
- **Test** `tests/test_claude_runner.py`, `tests/test_llm.py`, `tests/test_router.py`, `tests/test_panel_structure.py`.

---

## Task 1: claude_runner 어댑터

**Files:** Create `backend/claude_runner.py`; Test `tests/test_claude_runner.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_claude_runner.py`:

```python
import json
from pathlib import Path
from backend import claude_runner


def test_clean_env_pops_nesting(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    monkeypatch.setenv("KEEP", "1")
    e = claude_runner._clean_env()
    assert "CLAUDECODE" not in e and "CLAUDE_CODE_ENTRYPOINT" not in e and e.get("KEEP") == "1"


def test_run_claude_writes_output_last(tmp_path, monkeypatch):
    calls = {}

    def fake_run(cmd, **kw):
        calls["cmd"] = cmd; calls["input"] = kw.get("input"); calls["env"] = kw.get("env")
        class R: returncode = 0; stdout = json.dumps({"type": "result", "result": '{"elements":[]}'}); stderr = ""
        return R()

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    out = tmp_path / "o.json"
    res = claude_runner.run_claude("프롬프트", tmp_path, output_schema=tmp_path / "s.json", output_last=str(out))
    assert res["returncode"] == 0
    assert out.read_text(encoding="utf-8") == '{"elements":[]}'      # result → output_last
    assert "claude" in calls["cmd"][0] and "--json-schema" in calls["cmd"]
    assert calls["input"] == "프롬프트"                               # stdin
    assert "CLAUDECODE" not in (calls["env"] or {})


def test_run_claude_no_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: None)
    res = claude_runner.run_claude("p", tmp_path)
    assert res["returncode"] != 0


def test_run_claude_plain_text_when_not_json(tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        class R: returncode = 0; stdout = "그냥 텍스트"; stderr = ""
        return R()
    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)
    monkeypatch.setattr(claude_runner.shutil, "which", lambda n: "/usr/bin/claude")
    out = tmp_path / "o.txt"
    claude_runner.run_claude("p", tmp_path, output_last=str(out))
    assert out.read_text(encoding="utf-8") == "그냥 텍스트"           # 엔벨로프 아니면 원문
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `backend/claude_runner.py`:

```python
"""claude CLI(헤드리스) 어댑터 — 텍스트 추론용. CLAUDECODE 등 중첩 변수 pop, --json-schema 구조화 출력.
프롬프트는 stdin. 멀티모달(이미지)은 헤드리스에서 행이 걸려 미지원 → 비전은 codex가 담당."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")


def _clean_env() -> dict:
    e = dict(os.environ)
    for k in _NEST_ENV:
        e.pop(k, None)          # 중첩 세션 방지(안 하면 claude -p 가 행)
    return e


def run_claude(prompt: str, cwd, *, session_id=None, output_schema=None, output_last=None,
               sandbox=None, images=None, model=None, on_line=None) -> dict:
    """codex run_skill과 동일 시그니처/반환. images/sandbox/session_id는 무시(헤드리스 텍스트 전용)."""
    if shutil.which("claude") is None:
        return {"returncode": 127, "session_id": None, "output_last": output_last}
    cmd = ["claude", "-p", "--output-format", "json"]
    if output_schema:
        cmd += ["--json-schema", str(output_schema)]
    if model:
        cmd += ["--model", str(model)]
    try:
        r = subprocess.run(cmd, input=prompt, cwd=str(cwd), env=_clean_env(),
                           capture_output=True, text=True, timeout=1200)
    except Exception:
        return {"returncode": 1, "session_id": None, "output_last": output_last}
    if on_line and r.stdout:
        on_line(r.stdout[:500])
    result_text = r.stdout
    try:                        # --output-format json 엔벨로프면 result 추출
        env = json.loads(r.stdout)
        if isinstance(env, dict) and "result" in env:
            result_text = env["result"]
    except Exception:
        pass
    if output_last and result_text:
        Path(output_last).write_text(result_text, encoding="utf-8")
    return {"returncode": r.returncode, "session_id": None, "output_last": output_last}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_claude_runner.py -q` PASS.

- [ ] **Step 5: 커밋** — `git add backend/claude_runner.py tests/test_claude_runner.py && git commit -m "feat(llm): claude CLI 헤드리스 어댑터 — json-schema 구조화 출력, CLAUDECODE pop, stdin"`

---

## Task 2: llm 오케스트레이터 선택·디스패치

**Files:** Create `backend/llm.py`; Test `tests/test_llm.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_llm.py`:

```python
from pathlib import Path
from backend import llm


def test_default_orchestrator_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "llm_config.json")
    monkeypatch.delenv("AK_ORCHESTRATOR", raising=False)
    assert llm.get_orchestrator() == "claude"


def test_set_get_orchestrator(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "llm_config.json")
    llm.set_orchestrator("codex")
    assert llm.get_orchestrator() == "codex"
    llm.set_orchestrator("이상한값")          # 검증 → claude로
    assert llm.get_orchestrator() == "claude"


def test_run_orchestrator_routes_text_to_claude(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("claude")
    seen = {}
    monkeypatch.setattr(llm.claude_runner, "run_claude", lambda *a, **k: seen.update(engine="claude") or {"returncode": 0})
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path)                       # 텍스트 → claude
    assert seen["engine"] == "claude"


def test_run_orchestrator_forces_codex_for_images(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("claude")
    seen = {}
    monkeypatch.setattr(llm.claude_runner, "run_claude", lambda *a, **k: seen.update(engine="claude") or {"returncode": 0})
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path, images=["/x.png"])    # 멀티모달 → codex 강제
    assert seen["engine"] == "codex"


def test_run_orchestrator_codex_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "_CFG", tmp_path / "c.json"); llm.set_orchestrator("codex")
    seen = {}
    monkeypatch.setattr(llm.codex_runner, "run_skill", lambda *a, **k: seen.update(engine="codex") or {"returncode": 0})
    llm.run_orchestrator("p", tmp_path)
    assert seen["engine"] == "codex"
```

- [ ] **Step 2: 실패 확인** — FAIL.

- [ ] **Step 3: 구현** — `backend/llm.py`:

```python
"""오케스트레이터(추론) LLM 선택·디스패치. claude(기본) 또는 codex.
규칙: images(멀티모달) 있으면 무조건 codex(claude 헤드리스 비전 미지원). 이미지 생성은 별도(항상 codex)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from backend import codex_runner, claude_runner

_CFG = Path(__file__).resolve().parents[1] / "data" / "llm_config.json"
VALID = ("claude", "codex")
DEFAULT = "claude"


def get_orchestrator() -> str:
    try:
        v = json.loads(_CFG.read_text(encoding="utf-8")).get("orchestrator")
        if v in VALID:
            return v
    except Exception:
        pass
    v = os.environ.get("AK_ORCHESTRATOR")
    return v if v in VALID else DEFAULT


def set_orchestrator(name: str) -> str:
    name = name if name in VALID else DEFAULT
    _CFG.parent.mkdir(parents=True, exist_ok=True)
    _CFG.write_text(json.dumps({"orchestrator": name}, ensure_ascii=False, indent=2), encoding="utf-8")
    return name


def run_orchestrator(prompt, cwd, *, session_id=None, output_schema=None, output_last=None,
                     sandbox=None, images=None, model=None, on_line=None) -> dict:
    """선택 오케스트레이터로 추론 실행. images 있으면 codex 강제."""
    engine = get_orchestrator()
    if images or engine == "codex":
        return codex_runner.run_skill(prompt, cwd, session_id=session_id, output_schema=output_schema,
                                      output_last=output_last, sandbox=sandbox, images=images, on_line=on_line)
    return claude_runner.run_claude(prompt, cwd, session_id=session_id, output_schema=output_schema,
                                    output_last=output_last, sandbox=sandbox, images=images, model=model,
                                    on_line=on_line)
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_llm.py -q` PASS.

- [ ] **Step 5: 커밋** — `git add backend/llm.py tests/test_llm.py && git commit -m "feat(llm): 오케스트레이터 선택·디스패치 — claude 기본, images면 codex 강제"`

---

## Task 3: 추론 호출부 라우팅 + /api/llm/settings

**Files:** Modify `backend/router.py`, `backend/imagegen.py`, `backend/assistant.py`; Test `tests/test_router.py`

- [ ] **Step 1: imagegen.analyze_scene_layers** — `run_skill(...)` 호출을 `from backend import llm` 후 `llm.run_orchestrator(...)`로 교체(상단 import는 그대로 둬도 무방; 호출만 변경). images=[scene_image]가 넘어가므로 자동 codex.

- [ ] **Step 2: assistant.plan_actions** — `from backend.codex_runner import run_skill` 를 유지하되 호출을 `llm.run_orchestrator`로(상단 `from backend import llm` 추가). 텍스트라 claude로 라우팅.

- [ ] **Step 3: router `/api/skills/run`** — `result = run_skill(...)` 를 `result = llm.run_orchestrator(...)`로. 상단 import에 `llm` 추가. (반환 형태 동일 {returncode, session_id, output_last}.)

- [ ] **Step 4: router `/api/llm/settings`** — 실패 테스트(`tests/test_router.py`):

```python
def test_llm_settings_get_default(tmp_path, monkeypatch):
    import backend.router as r, backend.llm as L
    monkeypatch.setattr(L, "_CFG", tmp_path / "llm.json")
    monkeypatch.delenv("AK_ORCHESTRATOR", raising=False)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/llm/settings", {}, None, ctx)
    assert code == 200 and body["orchestrator"] == "claude" and "claude" in body["choices"]


def test_llm_settings_post(tmp_path, monkeypatch):
    import backend.llm as L
    monkeypatch.setattr(L, "_CFG", tmp_path / "llm.json")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/llm/settings", {}, {"orchestrator": "codex"}, ctx)
    assert code == 200 and body["orchestrator"] == "codex"
```

  구현(라우터, 적절한 위치):

```python
    if p == "/api/llm/settings" and method in ("GET", "POST"):
        if method == "POST":
            llm.set_orchestrator((body or {}).get("orchestrator", ""))
        return 200, {"orchestrator": llm.get_orchestrator(), "choices": list(llm.VALID)}
```

- [ ] **Step 5: 통과(멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린. (기존 skills/assistant/analyze 테스트가 `run_skill`/`run_orchestrator` monkeypatch와 맞는지 확인 — 기존 테스트는 `r.run_skill`/`r.tts`처럼 모듈 속성을 패치하므로, 라우터가 `llm.run_orchestrator`를 부르면 기존 `monkeypatch.setattr(r, "run_skill", ...)` 테스트가 깨질 수 있음. 그 경우 해당 테스트를 `r.llm.run_orchestrator` 패치로 갱신.)

- [ ] **Step 6: 커밋** — `git add -A && git commit -m "feat(llm): 추론 호출부를 오케스트레이터로 라우팅 + /api/llm/settings"`

---

## Task 4: 패널 — LLM 선택 드롭다운

**Files:** Modify `cep/com.autokairos.pd/index.html`, `js/main.js`; Test `tests/test_panel_structure.py`

- [ ] **Step 1: index.html** — 목록 뷰 health-bar 아래(또는 sb-right)에 추가:

```html
    <div class="label">오케스트레이터 LLM</div>
    <div class="row" style="display:flex;gap:6px;align-items:center">
      <select id="llmSelect" style="flex:1;padding:6px;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px"></select>
      <span id="llmHint" style="font-size:10px;color:#9aa0a6">추론=선택 / 이미지=codex</span>
    </div>
```

- [ ] **Step 2: main.js** — 로드/변경:

```javascript
function loadLlmSetting() {
  fetch(BACKEND + "/api/llm/settings").then(function (r) { return r.json(); })
    .then(function (j) {
      var sel = $("llmSelect"); if (!sel) return;
      sel.innerHTML = (j.choices || ["claude", "codex"]).map(function (c) {
        return '<option value="' + c + '"' + (c === j.orchestrator ? " selected" : "") + '>' + c + '</option>';
      }).join("");
    }).catch(function () {});
}

function saveLlmSetting() {
  fetch(BACKEND + "/api/llm/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orchestrator: $("llmSelect").value }),
  }).then(function (r) { return r.json(); }).then(function (j) {
    if ($("llmHint")) $("llmHint").textContent = "추론=" + j.orchestrator + " / 이미지=codex";
  });
}
```

  DOMContentLoaded에 추가: `var ls=$("llmSelect"); if(ls) ls.addEventListener("change", saveLlmSetting);` 그리고 `checkBackend()` 성공 시 `loadLlmSetting()` 호출(또는 DOMContentLoaded에서 직접).

- [ ] **Step 3: 테스트 + 문법** — `tests/test_panel_structure.py`:

```python
def test_llm_selector():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="llmSelect"' in html
    assert "function loadLlmSetting" in MAIN.read_text(encoding="utf-8") and "/api/llm/settings" in MAIN.read_text(encoding="utf-8")
```

  `node` 문법(main.js). PASS.

- [ ] **Step 4: 커밋** — `git add -A && git commit -m "feat(panel): 오케스트레이터 LLM 선택 드롭다운(/api/llm/settings)"`

---

## Task 5: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — PASS, 클린.
- [ ] **Step 2: 전 JS 문법** — main/nav/planning/storyboard/gallery/genmodal/assistant.
- [ ] **Step 3: 라이브 스모크** — 백엔드 재시작 후:
  - `GET /api/llm/settings` → claude 기본.
  - `POST {orchestrator:"codex"}` → codex, 다시 claude로 복귀.
  - **실제 claude 텍스트 호출 검증**: 작은 텍스트 스킬 또는 assistant plan을 claude로 실행 → 결과 JSON 정상 + claude 프로세스가 CLAUDECODE 없이 동작. (백엔드는 standalone이라 CLAUDECODE 없음 — claude_runner가 추가로 pop.)
  - 멀티모달 analyze-layers는 orchestrator=claude여도 codex로 라우팅되는지 확인(images 강제 규칙).

---

## Self-Review

- **선택 가능**: `data/llm_config.json`(set/get) + env `AK_ORCHESTRATOR` + 패널 드롭다운. 기본 claude.
- **분담 정확**: 추론(텍스트)=선택 LLM, 멀티모달(images)=codex 강제, 이미지 생성(`_run_codex_image`)=불변 codex.
- **claude 헤드리스 주의**: CLAUDECODE 등 pop(검증함), stdin 프롬프트, `--json-schema` 구조화, json 엔벨로프 `result` 추출. 멀티모달 미지원이라 라우팅에서 회피.
- **드롭인 호환**: `run_orchestrator` 시그니처/반환이 `run_skill`과 동일 → 호출부 최소 변경.
- **테스트 정합**: 기존 라우터 테스트가 `r.run_skill`을 패치하면 라우팅 변경으로 깨질 수 있음 → 해당 테스트를 `r.llm.run_orchestrator` 패치로 갱신(Task3 Step5).
- **한계(정직)**: claude 헤드리스 멀티모달 불가(레이어 분석은 codex). claude `--json-schema`가 매우 복잡한 스키마(scene-decompose)에서 codex보다 약할 수 있음 → 그때 드롭다운으로 codex 전환(선택 가능이 안전판).
