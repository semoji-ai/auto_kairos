# P8 — 하드닝 A: 잡 비동기화 + scenes 락 + 최상위 예외 + 자막 좌표 버그 Implementation Plan

**Goal:** 긴 배치 작업(레이어 분리, TTS 전체, 스토리보드 생성, 비서)이 패널 fetch를 블로킹하지 않게 **백그라운드 잡 + 폴링**으로 전환. scenes.json 동시 쓰기 락. 라우터 최상위 예외 처리. jsx 자막 좌표 실버그 수정.

**Architecture:** `JobRegistry`에 `result` 필드 + `run_async(jobs, jid, fn)` 헬퍼(threading.Thread daemon — fn 반환값을 result에, 예외는 failed). 라우터의 **배치 엔드포인트만** 비동기화(즉시 `{job_id, status:"running"}` 반환): `split-layers`, `tts/all`, `assistant`, `storyboard/generate`, `images/generate`, `layers/generate`, `pipeline/run`. **동기 유지**: `analyze-layers`(모달이 elements 즉시 필요), `scenes/tts`(단건), `scenes/image`(단건), `skills/run`(scene-decompose — 완료 후 시트 로드 흐름 유지). scenes.py는 모듈 전역 `threading.Lock`으로 파일 RMW 보호. 패널은 `_pollJob(jid, onDone, onLog)` 헬퍼로 1.5s 폴링.

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`. JS: `node -e "new Function(...)"`.

**현재 사실(확인됨):**
- `JobRegistry`(backend/jobs.py): create/append_log/set_status/get, 스레드세이프, `result` 필드 없음.
- `GET /api/jobs/{id}` 라우트 존재(router.py:510 부근) — get() dict 반환.
- app.py: ThreadingHTTPServer, `_route`가 handle_request 직접 호출(예외 처리 없음).
- scenes.py: `_save`/`ensure_scene_ids`/`update_narration`/`set_image_ref`/mutate 4종 모두 read→write 비보호.
- 비동기화 대상 라우트들의 현재 응답: split-layers→{job_id,result}, tts/all→{job_id,results}, assistant→{job_id,plan,results}, storyboard/generate→{job_id,status,...}, images/generate→{job_id,generated,...}, layers/generate→{...}, pipeline/run→{job_id,status,completed}.
- 패널 호출부: storyboard.js `splitLayers`(완료 후 loadSheet), assistant.js `sendChat`(plan/results 표시), main.js `genStoryboard`/`genImages`/`genLayers`(레거시 아코디언, 완료 후 show*), `buildComp`은 manifest(동기, 빠름)라 무관.
- jsx 자막 버그: build_scene.jsx `tl.property("Position").setValue([W / 2, H * 0.88])` — 컴프는 cw×ch인데 W/H(1920/1080) 사용. **cw/ch로 수정.**

---

## Task 1: JobRegistry.result + run_async + 라우터 최상위 예외

**Files:** Modify `backend/jobs.py`, `backend/router.py`; Test `tests/test_jobs.py`(없으면 생성), `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_jobs.py`:

```python
import time
from backend.jobs import JobRegistry, run_async


def test_set_status_stores_result():
    j = JobRegistry(); jid = j.create("x", "p")
    j.set_status(jid, "completed", result={"n": 3})
    assert j.get(jid)["result"] == {"n": 3}


def test_run_async_success():
    j = JobRegistry(); jid = j.create("x", "p")
    run_async(j, jid, lambda: {"ok": True})
    for _ in range(50):
        if j.get(jid)["status"] != "running":
            break
        time.sleep(0.02)
    g = j.get(jid)
    assert g["status"] == "completed" and g["result"] == {"ok": True}


def test_run_async_failure_sets_failed():
    j = JobRegistry(); jid = j.create("x", "p")
    def boom(): raise RuntimeError("터짐")
    run_async(j, jid, boom)
    for _ in range(50):
        if j.get(jid)["status"] != "running":
            break
        time.sleep(0.02)
    g = j.get(jid)
    assert g["status"] == "failed" and "터짐" in (g["error"] or "")
```

`tests/test_router.py`에 최상위 예외 테스트:

```python
def test_handler_exception_returns_500(tmp_path, monkeypatch):
    import backend.router as r
    def boom(root): raise RuntimeError("내부 오류")
    monkeypatch.setattr(r.projects, "scan_projects", boom)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects", {}, None, ctx)
    assert code == 500 and "error" in body
```

- [ ] **Step 2: 구현** —
  - `jobs.py`: create()의 초기 dict에 `"result": None` 추가. `set_status(..., result=None)` 파라미터 추가(None 아니면 저장). 모듈 함수:

```python
def run_async(jobs: JobRegistry, job_id: str, fn) -> None:
    """fn을 데몬 스레드로 실행. 반환 dict → result/completed, 예외 → failed."""
    def _work():
        try:
            res = fn()
            jobs.set_status(job_id, "completed", result=res if isinstance(res, dict) else {"value": res})
        except Exception as e:
            jobs.set_status(job_id, "failed", error=str(e)[:300])
    threading.Thread(target=_work, daemon=True).start()
```

  - `router.py`: `handle_request` 본문 전체를 내부 함수 `_dispatch`로 빼고:

```python
def handle_request(method, path, query, body, ctx):
    try:
        return _dispatch(method, path, query, body, ctx)
    except Exception as e:
        return 500, {"error": f"내부 오류: {e}"}
```

(기존 본문을 `_dispatch`로 rename — 들여쓰기 변화 없는 최소 diff 방식: `def handle_request` 줄을 `def _dispatch`로 바꾸고 새 `handle_request` 4줄을 위에 추가.)

- [ ] **Step 3: 통과 + 커밋** — `git commit -m "feat(jobs): result 저장 + run_async(데몬 스레드) + 라우터 최상위 예외→500"`

---

## Task 2: scenes.json 락

**Files:** Modify `backend/scenes.py`; Test `tests/test_scenes.py`

- [ ] **Step 1: 실패 테스트**:

```python
def test_concurrent_mutations_consistent(tmp_path):
    import threading
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "c0", "narration": "기준"}])
    def add_many():
        for _ in range(5):
            scenes.add_scene(d, narration="동시")
    ts = [threading.Thread(target=add_many) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    data = scenes.load_scenes(d)
    assert len(data["scenes"]) == 21                       # 1 + 4*5 (유실 없음)
    nums = [s["sceneNumber"] for s in data["scenes"]]
    assert nums == list(range(1, 22))                      # 재번호 일관
```

- [ ] **Step 2: 구현** — `scenes.py` 상단에 `_LOCK = threading.RLock()` (import threading). 파일을 read→write 하는 모든 공개 함수(`ensure_scene_ids`, `update_narration`, `set_image_ref`, `add_scene`, `remove_scene`, `split_scene`, `merge_scenes`)의 본문을 `with _LOCK:` 으로 감싼다. (`load_scenes`는 ensure_scene_ids 경유라 자동 보호 — 단 ensure 내부에서 재진입하므로 **RLock** 필수.)

- [ ] **Step 3: 통과 + 커밋** — `git commit -m "fix(scenes): 모듈 RLock — scenes.json 동시 RMW 경합 방지"`

---

## Task 3: 배치 엔드포인트 비동기화

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

대상 7개: `/api/scenes/split-layers`, `/api/tts/all`, `/api/assistant`, `/api/storyboard/generate`, `/api/images/generate`, `/api/layers/generate`, `/api/pipeline/run`.

- [ ] **Step 1: 실패 테스트(대표 2개 + 폴링 검증)**:

```python
def test_split_layers_returns_running_then_completes(tmp_path, monkeypatch):
    import time, backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"as1","imageRef":"storyboard/sb.png"}]}', encoding="utf-8")
    (proj / "storyboard").mkdir(); (proj / "storyboard" / "sb.png").write_bytes(b"\x89PNG")
    monkeypatch.setattr(r.imagegen, "split_scene_to_elements",
                        lambda *a, **k: {"layers": [{"rel": "layers/x.png", "status": "completed"}]})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/split-layers", {},
                                {"project_id": "p", "sceneNumber": 1,
                                 "elements": [{"name": "차", "location": "왼쪽"}]}, ctx)
    assert code == 200 and body["status"] == "running" and body["job_id"]
    jid = body["job_id"]
    for _ in range(100):
        _, jb = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
        if jb["status"] != "running":
            break
        time.sleep(0.02)
    assert jb["status"] == "completed"
    assert jb["result"]["result"]["layers"][0]["status"] == "completed"


def test_assistant_async(tmp_path, monkeypatch):
    import time, backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    monkeypatch.setattr(r.assistant, "run_assistant",
                        lambda proj_dir, instr, on_event=None: {"plan": [], "results": []})
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assistant", {},
                                {"project_id": "p", "instruction": "x"}, ctx)
    assert code == 200 and body["status"] == "running"
    jid = body["job_id"]
    for _ in range(100):
        _, jb = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
        if jb["status"] != "running":
            break
        time.sleep(0.02)
    assert jb["status"] == "completed" and jb["result"] == {"plan": [], "results": []}
```

- [ ] **Step 2: 구현 패턴** — 각 대상 핸들러에서 검증(404/400/422)은 동기 유지, 실행부만:

```python
        jid = jobs.create("split-layers", b.get("project_id", ""))
        def _do(proj_dir=proj_dir, sc=sc, elements=elements, conc=conc, jid=jid):
            res = imagegen.split_scene_to_elements(
                proj_dir, str(proj_dir / sc["_image"]), sc.get("sceneId"), elements,
                concurrency=conc, on_event=lambda r: jobs.append_log(jid, f"{r['name']}: {r['status']}"))
            return {"result": res}
        run_async(jobs, jid, _do)
        return 200, {"job_id": jid, "status": "running"}
```

(상단 import에 `from backend.jobs import JobRegistry` 대신 — `from backend import jobs`가 아님: 기존 import 스타일 확인 후 `run_async`만 추가 import: `from backend.jobs import run_async`.)
- assistant: `_do`가 `assistant.run_assistant(...)` 반환(plan/results 그대로 result에).
- tts/all: 루프 전체를 `_do` 안으로. 결과 `{"results": results}`.
- storyboard/images/layers/pipeline: 기존 실행부를 `_do`로 감싸고 기존 응답 dict을 반환값으로.
- **기존 동기 테스트 갱신**: 위 7개를 검사하던 기존 테스트는 "running 반환 + 폴링 후 결과" 패턴으로 수정(monkeypatch는 동일). `/api/jobs/{id}` 응답에 result 포함되는지 확인(JobRegistry.get이 dict 복사라 자동 포함).

- [ ] **Step 3: 통과(전체 멱등 2회) + 커밋** — `git commit -m "feat(api): 배치 7종 비동기화 — 즉시 job_id 반환 + /api/jobs 폴링(result 포함)"`

---

## Task 4: 패널 폴링 전환 + jsx 자막 좌표

**Files:** Modify `cep/com.autokairos.pd/js/main.js`, `storyboard.js`, `assistant.js`, `jsx/build_scene.jsx`; Test `tests/test_panel_structure.py`

- [ ] **Step 1: `_pollJob` 헬퍼(main.js — 전역)**:

```javascript
/* 잡 폴링 — 1.5s 간격, onLog(logs)/onDone(job). 5분 한도. */
function _pollJob(jid, onDone, onLog) {
  var tries = 0;
  var t = setInterval(function () {
    if (++tries > 200) { clearInterval(t); onDone({ status: "failed", error: "타임아웃" }); return; }
    fetch(BACKEND + "/api/jobs/" + jid).then(function (r) { return r.json(); })
      .then(function (j) {
        if (onLog && j.logs) onLog(j.logs);
        if (j.status !== "running") { clearInterval(t); onDone(j); }
      })
      .catch(function () { /* 일시 오류 — 다음 틱 */ });
  }, 1500);
}
```

- [ ] **Step 2: 호출부 전환** —
  - `storyboard.js splitLayers`: 응답 `{job_id,status:"running"}` 받으면 `_rowStatus(n, "레이어 분리 중…")` 후 `_pollJob(j.job_id, done→ 기존 완료 처리(result.result.layers 카운트→loadSheet), logs→ _rowStatus(n, 마지막 로그))`.
  - `assistant.js sendChat`: running이면 `_chatAppend("🤖 실행 중…")` + `_pollJob` — done에서 `j.result.plan/results` 기존 표시 로직 재사용, onLog로 마지막 로그 1줄 갱신(중복 없이 — 직전 길이 기억).
  - `main.js genStoryboard/genImages/genLayers`: running이면 `_pollJob` 후 기존 show* 호출. (pipeline/run·tts/all은 패널 직접 호출 없음 — 변경 불요.)
- [ ] **Step 3: jsx 자막 좌표** — `tl.property("Position").setValue([W / 2, H * 0.88])` → `[cw / 2, ch * 0.88]`.
- [ ] **Step 4: 구조 테스트**:

```python
def test_poll_job_helper_and_async_callers():
    main = MAIN.read_text(encoding="utf-8")
    assert "function _pollJob" in main and "/api/jobs/" in main
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "_pollJob" in js                      # splitLayers 폴링 전환
    a = (PANEL / "js" / "assistant.js").read_text(encoding="utf-8")
    assert "_pollJob" in a


def test_jsx_subtitle_uses_comp_size():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "[cw / 2, ch * 0.88]" in jsx
    assert "[W / 2, H * 0.88]" not in jsx
```

- [ ] **Step 5: 전 JS node 문법 + 통과 + 커밋** — `git commit -m "feat(panel): 잡 폴링(_pollJob) 전환 + jsx 자막 좌표 cw/ch 수정"`

---

## Task 5: 통합 검증

- [ ] 전체 테스트 멱등 2회 + git 클린 + JS 7파일 문법.
- [ ] 라이브 스모크(tesla 복사본 `projects/_smoke_p8`): 백엔드 재시작 → `POST /api/assistant {instruction:"AE로 합쳐줘"}` → **즉시 running 반환** 확인 → `/api/jobs/{id}` 폴링으로 completed + result.plan에 assemble 확인. 복사본 제거(shutil.rmtree), tesla 미변경. 백엔드 8765 재시작 상태로 종료(패널용).

---

## Self-Review

- **동기/비동기 경계 명확**: 모달·단건(분석/단건TTS/단건이미지/씬분해)은 동기 유지 — 패널 UX 흐름 보존. 배치 7종만 비동기.
- **결과 전달**: result 필드 + /api/jobs 폴링(get이 전체 dict 복사 — result 자동 포함).
- **경합 방지**: scenes RLock(재진입 안전). 비동기 스레드에서 set_image_ref 등 호출돼도 안전.
- **예외 일관**: 최상위 500 + 비동기 내부 예외는 job failed.
- **자막 버그**: cw/ch — 컴프 크기 기준 정합.
- **한계(정직)**: 인메모리 잡 — 백엔드 재시작 시 진행 중 잡 소실(폴링이 타임아웃 처리). 동시 codex 폭주 제한(세마포어)은 미구현 — 필요 시 후속.
