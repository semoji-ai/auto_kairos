# M3c — 스토리보드 (씬별 프레임 imagegen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** 씬 분해(scenes.json) 결과의 씬마다 codex imagegen으로 semoji 스토리보드 프레임을 생성해 패널에서 씬별 썸네일+나레이션으로 본다. + 갤러리 새로고침 버튼 보강.

**Architecture:** M3b의 `imagegen.generate_one`을 재사용(출력 subdir만 `storyboard/`로). scenes.json의 씬별 image_prompt를 그대로 써서 프레임 생성(별도 스킬 없이 DRY). 패널은 file:// 썸네일.

**Tech Stack:** Python 3.12(표준 라이브러리), pytest, codex CLI(image_gen), CEP 패널.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` **repo 루트에서**.

근거: `docs/design/M3_pipeline_contract.md` §3.4(스토리보드=imagegen), `backend/imagegen.py`(재사용), M2 scene-decompose(scenes.json 씬별 image_prompt 보유).

---

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/imagegen.py` | `generate_one`에 `subdir` 파라미터 추가(기본 "images") |
| `backend/router.py` | `/api/storyboard/generate`, `/api/storyboard/list` |
| `cep/com.autokairos.pd/{index.html,js/main.js}` | 스토리보드 썸네일 뷰 + 갤러리 새로고침 버튼 |
| `tests/test_imagegen.py`(추가) `tests/test_router.py`(추가) | 단위 테스트 |

**설계 결정**: scenes.json이 이미 씬별 `image_prompt`를 가지므로 **별도 storyboard 스킬을 만들지 않고** scenes.json을 직접 사용(DRY). storyboard.json = 씬별 메타+프레임 경로. 레퍼런스 이미지 `--image` 첨부(일관성)는 후속 강화로 보류(M3c는 style-only).

---

## Task 1: generate_one subdir 파라미터 (imagegen.py)

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_imagegen.py`에 추가:
```python
def test_versioned_path_in_subdir_concept(tmp_path):
    # subdir 분리 동작: storyboard 디렉토리에 독립 버전
    sb = tmp_path / "storyboard"; sb.mkdir()
    p = imagegen.versioned_path(sb, "sb_1.png")
    assert p.parent.name == "storyboard"
    assert p.name == "sb_1.png"
```
(generate_one의 subdir는 실호출이라 단위는 versioned_path 기반으로 확인)

- [ ] **Step 2: 실패 확인** — 기존 통과 상태에서 새 테스트는 즉시 통과할 수도 있음(versioned_path는 디렉토리 받음). 먼저 `... -m pytest tests/test_imagegen.py -v` 실행해 현 상태 확인.

- [ ] **Step 3: generate_one에 subdir 추가** — `backend/imagegen.py`의 `generate_one` 시그니처를 변경:
```python
def generate_one(proj_dir: Path, rel_out: str, image_prompt: str,
                 *, subdir: str = "images", retries: int = 2, on_line=None) -> dict:
    """레퍼런스/스토리보드 1장 생성. subdir로 출력 폴더 분리(images|storyboard). rate limit 백오프."""
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = versioned_path(out_base, Path(rel_out).name)
    rel = out.relative_to(proj_dir).as_posix()
    prompt = build_image_prompt(image_prompt, load_style(), rel)
    last = ""
    for attempt in range(retries + 1):
        captured = []
        res = run_skill(
            prompt, proj_dir, sandbox="workspace-write",
            output_last=str(proj_dir / ".imagegen_last.txt"),
            on_line=lambda ln: (captured.append(ln), on_line and on_line(ln)),
        )
        last = "\n".join(captured)
        if res["returncode"] == 0 and out.exists():
            return {"status": "completed", "path": str(out)}
        if is_rate_limited(last) and attempt < retries:
            time.sleep(20 * (attempt + 1))
            continue
        break
    return {"status": "failed", "error": "rate_limit_or_no_file", "log_tail": last[-200:]}
```
(기존 `images_dir = proj_dir / "images"` 고정 부분만 `out_base = proj_dir / subdir`로 교체. 나머지 로직 동일. 기본값 "images"라 M3b 호출 무영향.)

- [ ] **Step 4: 통과** — `... -m pytest tests/test_imagegen.py -v` → PASS. 전체 `... -m pytest tests/ -q` 도 통과(M3b /api/images/generate 회귀 없는지).

- [ ] **Step 5: 커밋**
```bash
git add backend/imagegen.py tests/test_imagegen.py
git commit -m "feat(backend): imagegen generate_one subdir 파라미터(images|storyboard)"
```

---

## Task 2: /api/storyboard/generate + /api/storyboard/list (router.py)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_router.py`에 추가(generate는 imagegen 모킹):
```python
def test_storyboard_generate_from_scenes(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"project_id":"p","total_scenes":2,"scenes":['
        '{"sceneNumber":1,"title":"A","narration":"가","image_prompt":"장면1"},'
        '{"sceneNumber":2,"title":"B","narration":"나","image_prompt":"장면2"}]}',
        encoding="utf-8")

    def fake_gen(proj_dir, rel_out, image_prompt, **kw):
        assert kw.get("subdir") == "storyboard"
        out = proj_dir / "storyboard" / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_gen)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/storyboard/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 200
    assert body["generated"] == 2


def test_storyboard_generate_requires_scenes(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/storyboard/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 422


def test_storyboard_list(tmp_path):
    proj = tmp_path / "p"; (proj / "storyboard").mkdir(parents=True)
    (proj / "storyboard" / "sb_1.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/storyboard/list",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    assert "sb_1.png" in body["images"]
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -v` → 새 3개 FAIL

- [ ] **Step 3: router.py 확장** — `/api/images/list` 블록 **다음**에 추가(imagegen는 이미 import됨):
```python
    if method == "POST" and p == "/api/storyboard/generate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        scenes_fp = proj_dir / "scenes.json"
        if not scenes_fp.exists():
            return 422, {"error": "scenes.json 없음 — 씬 분해(scene-decompose) 먼저 실행"}
        import json as _json
        scenes = _json.loads(scenes_fp.read_text(encoding="utf-8")).get("scenes", [])
        jobs = ctx["jobs"]
        jid = jobs.create("storyboard", pid)
        done = 0
        for sc in scenes:
            n = sc.get("sceneNumber", done + 1)
            prompt = sc.get("image_prompt") or sc.get("visual_summary") or sc.get("narration", "")
            res = imagegen.generate_one(proj_dir, f"sb_{n}.png", prompt,
                                        subdir="storyboard",
                                        on_line=lambda ln: jobs.append_log(jid, ln))
            if res["status"] == "completed":
                done += 1
            else:
                jobs.append_log(jid, f"FAIL sb_{n}: {res.get('error')}")
        jobs.set_status(jid, "completed" if done else "failed",
                        artifact_paths=[str(proj_dir / "storyboard")])
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"],
                     "generated": done, "total": len(scenes)}

    if method == "GET" and p == "/api/storyboard/list":
        pid = query.get("project_id", "")
        sb_dir = root / pid / "storyboard"
        if not sb_dir.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in sb_dir.glob("*.png"))
        return 200, {"images": names, "dir": str(sb_dir)}
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → 전부 PASS, git status 클린.

- [ ] **Step 5: 커밋**
```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/storyboard/generate(scenes→프레임) + /api/storyboard/list"
```

---

## Task 3: 패널 스토리보드 뷰 + 갤러리 새로고침

**Files:** Modify `cep/com.autokairos.pd/{index.html,js/main.js}`

- [ ] **Step 1: index.html** — 「레퍼런스 이미지」 블록 다음에 추가:
```html
  <button id="btnRefreshGallery">갤러리 새로고침</button>

  <div class="label">스토리보드</div>
  <button id="btnGenStoryboard">스토리보드 생성 (씬별)</button>
  <div class="box" id="storyboard">—</div>
```

- [ ] **Step 2: main.js** — DOMContentLoaded 위에 추가:
```js
function genStoryboard() {
  if (!SELECTED_PROJECT) { $("storyboard").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("storyboard").textContent = "스토리보드 생성 중... (씬별 codex, 수 분)";
  fetch(BACKEND + "/api/storyboard/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "completed") { $("storyboard").textContent = "실패/일부: " + JSON.stringify(j); }
      return showStoryboard();
    })
    .catch(function (e) { $("storyboard").textContent = "오류: " + e; });
}

function showStoryboard() {
  fetch(BACKEND + "/api/storyboard/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", imgs = j.images || [];
      if (!imgs.length) { $("storyboard").textContent = "(스토리보드 없음)"; return; }
      $("storyboard").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:120px;height:auto;margin:3px;border-radius:4px;" title="' + n + '">';
      }).join("");
    });
}
```
DOMContentLoaded 핸들러에 바인딩 추가:
```js
  $("btnRefreshGallery").addEventListener("click", showGallery);
  $("btnGenStoryboard").addEventListener("click", genStoryboard);
```
(`showGallery`는 M3b에서 정의됨 — 재사용으로 "갤러리 새로고침" 구현.)

- [ ] **Step 3: JS 문법 점검** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/main.js','utf8'))" && echo OK`

- [ ] **Step 4: 커밋**
```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 스토리보드 생성/표시 + 갤러리 새로고침 버튼"
```

---

## Task 4: 라이브 e2e — 테슬라 스토리보드 (사용자 확인)

> ⚠️ scene-decompose(있으면 스킵) + 씬 수만큼 codex imagegen. 다회 호출 — 크레딧/rate limit. **사용자 합의 후.**

- [ ] **Step 1: 씬 분해 (scenes.json 없으면)** — 백엔드 기동 후:
```bash
curl -s -X POST http://127.0.0.1:8765/api/skills/run -H 'Content-Type: application/json' -d '{"project_id":"tesla","skill_name":"scene-decompose"}'
cat projects/tesla/scenes.json | head -c 400
```

- [ ] **Step 2: 스토리보드 생성**
```bash
curl -s -X POST http://127.0.0.1:8765/api/storyboard/generate -H 'Content-Type: application/json' -d '{"project_id":"tesla"}'
ls -la projects/tesla/storyboard/
```
Expected: `{"generated":N}` + storyboard/sb_*.png (씬 수만큼).

- [ ] **Step 3: 시각 확인** — sb_*.png 2~3장 Read로 열어 semoji 스타일 + 씬 내용 일치 확인.

- [ ] **Step 4: 정리** — storyboard/는 gitignore(projects/*/storyboard/ 추가 필요 — 아래 Task 5에서). ~/.codex 캐시는 사용자 정리.

---

## Task 5: gitignore + 통합 검증

- [ ] **Step 1: gitignore에 storyboard 추가** — `.gitignore`에 `projects/*/storyboard/` 추가.
- [ ] **Step 2: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` → 전부 PASS, git status 클린.
- [ ] **Step 3: import** — `... -c "from backend import imagegen, router; print('ok')"`
- [ ] **Step 4: 커밋**
```bash
git add .gitignore
git commit -m "chore: storyboard/ 생성물 gitignore + M3c 검증"
```

---

## Self-Review (작성자 체크)
- **계약 커버리지**: §3.4 스토리보드=imagegen 씬별 프레임 → T1(subdir)·T2(API)·T4(라이브). 갤러리 새로고침 보강 → T3.
- **Placeholder**: 없음 — 코드 전부 포함.
- **타입 일관성**: `generate_one(subdir=)`, `/api/storyboard/generate|list`, 패널 `genStoryboard/showStoryboard/showGallery(재사용)` — 일치. M3b `/api/images/*` 회귀 없음(subdir 기본 "images").
- **단순화(의도)**: 별도 storyboard 스킬 없이 scenes.json image_prompt 직접 사용(DRY). 레퍼런스 `--image` 첨부(씬 일관성)는 후속. scenes.json 전제(씬분해 선행).
- **미반영**: M4(TTS/씬레이어/AE 컴프 조립)는 이후.
