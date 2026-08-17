# M3d — 씬 레이어 분리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** 씬(스토리보드 프레임)을 레퍼런스로 첨부해 배경/인물 레이어를 따로 재생성하고(인물=마젠타 크로마→투명), AE에서 레이어별 애니메이션이 가능하도록 layers.json + 레이어 PNG를 만든다.

**Architecture:** codex exec `-i <scene>` 로 씬을 레퍼런스 첨부 → "인물만 마젠타 배경"/"인물 없이 배경만" 재생성(PoC 검증). 인물 레이어는 PIL로 마젠타→투명. 씬별 레이어를 병렬(generate_many 패턴) 생성. M3b/M3c의 imagegen 모듈 확장.

**Tech Stack:** Python 3.12 + **Pillow/numpy(신규 의존성)**, pytest, codex CLI(image_gen, -i), CEP 패널.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` **repo 루트에서**.

근거: PoC(2026-06-06) — codex `-i scene` + "인물만 마젠타"(동일 포즈 일관) + PIL 마젠타→투명 전 구간 검증. `docs/poc/POC_codex_imagegen.md`.

---

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/codex_runner.py` | `build_codex_cmd`/`run_skill`에 `images`(-i 첨부) 파라미터 |
| `backend/imagegen.py` | `chroma_key_magenta`(PIL), `build_layer_prompt`, `generate_layer`, `generate_layers_for_scenes`(병렬) |
| `backend/router.py` | `/api/layers/generate`, `/api/layers/list` |
| `requirements.txt` | Pillow, numpy (신규) |
| `cep/com.autokairos.pd/{index.html,js/main.js}` | 레이어 뷰 |
| `tests/test_codex_runner.py`·`test_imagegen.py`·`test_router.py` (추가) | 단위 테스트 |

**레이어 모델(최소)**: 씬당 **배경(opaque) + 인물(투명)** 2레이어. 소품은 후속. 출력 `projects/{id}/layers/{bg_N.png, char_N.png}`. layers.json = 씬별 레이어 경로.

---

## Task 1: codex_runner -i(images) 파라미터

**Files:** Modify `backend/codex_runner.py`; Test `tests/test_codex_runner.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_codex_runner.py`:
```python
def test_build_cmd_with_images():
    cmd = build_codex_cmd(images=["/a/scene.png"])
    assert "-i" in cmd
    assert cmd[cmd.index("-i") + 1] == "/a/scene.png"


def test_build_cmd_multiple_images():
    cmd = build_codex_cmd(images=["/a.png", "/b.png"])
    assert cmd.count("-i") == 2
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_codex_runner.py -v` → 새 2개 FAIL

- [ ] **Step 3: 구현** — `build_codex_cmd`에 `images: list | None = None` 파라미터 추가. `if sandbox:` 줄 다음(또는 output 전)에 삽입:
```python
    if images:
        for img in images:
            cmd += ["-i", img]
```
그리고 `run_skill`에 `images: list | None = None` 추가 후 `build_codex_cmd(..., images=images)` 전달.

- [ ] **Step 4: 통과** — `... -m pytest tests/test_codex_runner.py -v` → PASS. 전체도 확인.

- [ ] **Step 5: 커밋**
```bash
git add backend/codex_runner.py tests/test_codex_runner.py
git commit -m "feat(backend): codex_runner -i(images) 첨부 파라미터 — 씬 레퍼런스용"
```

---

## Task 2: requirements.txt + chroma_key_magenta (PIL)

**Files:** Create `requirements.txt`; Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: requirements.txt** — 생성:
```
Pillow>=10
numpy>=1.24
```
(설치: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pip install -r requirements.txt` — venv엔 이미 있을 수 있음, 확인만)

- [ ] **Step 2: 실패 테스트** — `tests/test_imagegen.py`에 추가:
```python
def test_chroma_key_magenta(tmp_path):
    from PIL import Image
    from backend import imagegen
    # 좌측 마젠타, 우측 파랑 2x1 확대 이미지
    im = Image.new("RGBA", (4, 2), (255, 0, 255, 255))
    for y in range(2):
        im.putpixel((2, y), (30, 60, 200, 255))
        im.putpixel((3, y), (30, 60, 200, 255))
    src = tmp_path / "m.png"; im.save(src)
    out = tmp_path / "t.png"
    res = imagegen.chroma_key_magenta(src, out)
    from PIL import Image as I
    r = I.open(out).convert("RGBA")
    assert r.getpixel((0, 0))[3] == 0      # 마젠타 → 투명
    assert r.getpixel((3, 0))[3] == 255    # 파랑 → 보존
    assert res["transparent_ratio"] > 0.4
```

- [ ] **Step 3: 실패 확인** — `... -m pytest tests/test_imagegen.py::test_chroma_key_magenta -v` → FAIL

- [ ] **Step 4: 구현** — `backend/imagegen.py`에 추가(상단 `from PIL import Image`, `import numpy as np`):
```python
def chroma_key_magenta(src_png: Path, out_png: Path) -> dict:
    """마젠타(#FF00FF) 근방을 투명으로. 가장자리 디스필(마젠타 성분 감쇠)."""
    im = Image.open(src_png).convert("RGBA")
    a = np.array(im).astype(int)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mask = (r > 150) & (g < 110) & (b > 150)
    a[mask, 3] = 0
    # 디스필: 남은 픽셀에서 R/B가 G보다 과한 마젠타 끼 완화
    keep = ~mask
    over = keep & (g < np.minimum(r, b) - 40)
    a[over, 0] = np.minimum(a[over, 0], a[over, 1] + 40)
    a[over, 2] = np.minimum(a[over, 2], a[over, 1] + 40)
    out = Image.fromarray(a.astype("uint8"), "RGBA")
    out.save(out_png)
    return {"transparent_ratio": float(mask.sum()) / mask.size}
```

- [ ] **Step 5: 통과** — `... -m pytest tests/test_imagegen.py -v` → PASS. 전체 확인.

- [ ] **Step 6: 커밋**
```bash
git add requirements.txt backend/imagegen.py tests/test_imagegen.py
git commit -m "feat(backend): chroma_key_magenta(PIL 마젠타→투명+디스필) + requirements.txt(Pillow/numpy)"
```

---

## Task 3: build_layer_prompt + generate_layer

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_imagegen.py`에 추가:
```python
def test_build_layer_prompt_character():
    p = imagegen.build_layer_prompt("character", "STYLE", "char_1.png")
    assert "인물" in p and "마젠타" in p and "char_1.png" in p and "STYLE" in p


def test_build_layer_prompt_background():
    p = imagegen.build_layer_prompt("background", "STYLE", "bg_1.png")
    assert "배경" in p and "bg_1.png" in p
    assert "마젠타" not in p   # 배경은 크로마 아님
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_imagegen.py -v` → 새 2개 FAIL

- [ ] **Step 3: 구현** — `backend/imagegen.py`에 추가:
```python
def build_layer_prompt(layer_kind: str, style_desc: str, rel_out: str) -> str:
    head = f"{style_desc}\n\n## 레이어 분리 지시\n첨부한 scene 이미지를 레퍼런스로 사용한다."
    if layer_kind == "character":
        body = ("등장 인물(캐릭터)들만 동일한 포즈·외형·위치로 다시 그리고, "
                "인물 외 모든 영역은 순수 마젠타 단색(#FF00FF)으로 채운다.")
    else:  # background
        body = ("인물(캐릭터)을 모두 제거하고, 배경·환경·공간만 자연스럽게 채워서 그린다. "
                "인물이 있던 자리는 배경으로 메운다.")
    return (f"{head} {body}\nimage_gen 도구로 생성해 현재 폴더의 {rel_out} 로 저장. "
            f"텍스트 없음. 저장되면 OK만 답해.")


def generate_layer(proj_dir, scene_image, rel_out: str, layer_kind: str,
                   *, subdir: str = "layers", retries: int = 2, on_line=None) -> dict:
    """씬 레퍼런스(-i) + layer_kind로 레이어 재생성. character는 마젠타→투명 후처리."""
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    raw = versioned_path(out_base, Path(rel_out).name)
    rel = raw.relative_to(proj_dir).as_posix()
    prompt = build_layer_prompt(layer_kind, load_style(), rel)
    last = ""
    for attempt in range(retries + 1):
        captured = []
        res = run_skill(
            prompt, proj_dir, sandbox="workspace-write",
            images=[str(scene_image)],
            output_last=str(proj_dir / ".imagegen_last.txt"),
            on_line=lambda ln: (captured.append(ln), on_line and on_line(ln)),
        )
        last = "\n".join(captured)
        if res["returncode"] == 0 and raw.exists():
            if layer_kind == "character":
                chroma_key_magenta(raw, raw)  # 같은 경로에 투명화
            return {"status": "completed", "path": str(raw), "layer": layer_kind}
        if is_rate_limited(last) and attempt < retries:
            time.sleep(20 * (attempt + 1))
            continue
        break
    return {"status": "failed", "error": "rate_limit_or_no_file", "layer": layer_kind}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_imagegen.py -v` → PASS. 전체 확인.

- [ ] **Step 5: 커밋**
```bash
git add backend/imagegen.py tests/test_imagegen.py
git commit -m "feat(backend): generate_layer — 씬 -i 레퍼런스로 배경/인물(마젠타→투명) 레이어 재생성"
```

---

## Task 4: 씬 레이어 오케스트레이션 (병렬) + /api/layers

**Files:** Modify `backend/imagegen.py`, `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: imagegen에 씬 레이어 묶음 함수 추가**
```python
def generate_scene_layers(proj_dir, scenes_with_images, *, concurrency=4, on_event=None):
    """scenes_with_images=[(sceneNumber, scene_image_path)]. 각 씬당 background+character 레이어 병렬 생성.
    반환: {sceneNumber: {background:res, character:res}}."""
    from concurrent.futures import ThreadPoolExecutor
    tasks = []
    for n, img in scenes_with_images:
        tasks.append((n, "background", f"bg_{n}.png", img))
        tasks.append((n, "character", f"char_{n}.png", img))

    def _work(t):
        n, kind, rel, img = t
        res = generate_layer(proj_dir, img, rel, kind)
        if on_event:
            on_event(n, kind, res)
        return (n, kind, res)

    out = {}
    with ThreadPoolExecutor(max_workers=max(1, int(concurrency))) as ex:
        for n, kind, res in ex.map(_work, tasks):
            out.setdefault(n, {})[kind] = res
    return out
```

- [ ] **Step 2: 실패 테스트** — `tests/test_router.py`에 추가:
```python
def test_layers_generate(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; (proj / "storyboard").mkdir(parents=True)
    (proj / "storyboard" / "sb_1.png").write_bytes(b"\x89PNG")
    (proj / "scenes.json").write_text(
        '{"project_id":"p","total_scenes":1,"scenes":[{"sceneNumber":1,"title":"A","narration":"가"}]}',
        encoding="utf-8")

    def fake_layers(proj_dir, items, **kw):
        out = {}
        for n, img in items:
            ld = proj_dir / "layers"; ld.mkdir(parents=True, exist_ok=True)
            (ld / f"bg_{n}.png").write_bytes(b"\x89PNG")
            (ld / f"char_{n}.png").write_bytes(b"\x89PNG")
            out[n] = {"background": {"status": "completed"}, "character": {"status": "completed"}}
        return out

    monkeypatch.setattr(r.imagegen, "generate_scene_layers", fake_layers)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/layers/generate", {}, {"project_id": "p"}, ctx)
    assert code == 200
    assert body["scenes"] == 1


def test_layers_generate_requires_storyboard(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[{"sceneNumber":1}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/layers/generate", {}, {"project_id": "p"}, ctx)
    assert code == 422
```

- [ ] **Step 3: 실패 확인** — `... -m pytest tests/test_router.py -v` → 새 2개 FAIL

- [ ] **Step 4: router.py 확장** — `/api/storyboard/list` 블록 다음에:
```python
    if method == "POST" and p == "/api/layers/generate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        scenes_fp = proj_dir / "scenes.json"
        sb_dir = proj_dir / "storyboard"
        if not scenes_fp.exists() or not sb_dir.is_dir():
            return 422, {"error": "scenes.json + storyboard/ 필요 — 씬분해·스토리보드 먼저"}
        import json as _json
        scenes = _json.loads(scenes_fp.read_text(encoding="utf-8")).get("scenes", [])
        items = []
        for sc in scenes:
            n = sc.get("sceneNumber")
            sb = sb_dir / f"sb_{n}.png"
            if sb.exists():
                items.append((n, sb))
        if not items:
            return 422, {"error": "storyboard 프레임 없음(sb_N.png)"}
        jobs = ctx["jobs"]
        jid = jobs.create("layers", pid)
        conc = int(b.get("concurrency", 4))
        results = imagegen.generate_scene_layers(
            proj_dir, items, concurrency=conc,
            on_event=lambda n, kind, res: jobs.append_log(jid, f"scene{n}/{kind}: {res['status']}"))
        ok = sum(1 for v in results.values()
                 if v.get("background", {}).get("status") == "completed"
                 and v.get("character", {}).get("status") == "completed")
        # layers.json
        layers = {"project_id": pid, "scenes": [
            {"sceneNumber": n, "background": f"layers/bg_{n}.png", "character": f"layers/char_{n}.png"}
            for n, _ in items]}
        (proj_dir / "layers.json").write_text(_json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
        jobs.set_status(jid, "completed" if ok else "failed", artifact_paths=[str(proj_dir / "layers.json")])
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"], "scenes": ok, "total": len(items)}

    if method == "GET" and p == "/api/layers/list":
        pid = query.get("project_id", "")
        ld = root / pid / "layers"
        if not ld.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in ld.glob("*.png"))
        return 200, {"images": names, "dir": str(ld)}
```

- [ ] **Step 5: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → 전부 PASS, git status 클린.

- [ ] **Step 6: 커밋**
```bash
git add backend/imagegen.py backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/layers/generate(씬→배경+인물 레이어 병렬) + layers.json + list"
```

---

## Task 5: 패널 레이어 뷰

**Files:** Modify `cep/com.autokairos.pd/{index.html,js/main.js}`

- [ ] **Step 1: index.html** — 「스토리보드」 블록 다음에:
```html
  <div class="label">씬 레이어 (배경/인물 분리)</div>
  <button id="btnGenLayers">레이어 생성</button>
  <div class="box" id="layers">—</div>
```

- [ ] **Step 2: main.js** — DOMContentLoaded 위에 추가:
```js
function genLayers() {
  if (!SELECTED_PROJECT) { $("layers").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("layers").textContent = "레이어 생성 중... (씬별 배경+인물, codex)";
  fetch(BACKEND + "/api/layers/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "completed") { $("layers").textContent = "실패/일부: " + JSON.stringify(j); }
      return showLayers();
    })
    .catch(function (e) { $("layers").textContent = "오류: " + e; });
}

function showLayers() {
  fetch(BACKEND + "/api/layers/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", imgs = j.images || [];
      if (!imgs.length) { $("layers").textContent = "(레이어 없음)"; return; }
      $("layers").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:100px;height:auto;margin:3px;border:1px solid #444;border-radius:4px;background:#666;" title="' + n + '">';
      }).join("");
    });
}
```
DOMContentLoaded 바인딩 추가: `$("btnGenLayers").addEventListener("click", genLayers);`
(투명 PNG가 보이도록 img에 background:#666 회색 깔판.)

- [ ] **Step 3: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/main.js','utf8'))" && echo OK`

- [ ] **Step 4: 커밋**
```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 씬 레이어(배경/인물) 생성 + 표시(투명 회색 깔판)"
```

---

## Task 6: 라이브 e2e — 테슬라 레이어 (사용자 확인)

> ⚠️ 씬당 2장(배경+인물) × 5씬 = 10 codex 호출(병렬). 크레딧/시간. **사용자 합의 후.**

- [ ] **Step 1: 레이어 생성** — 백엔드 기동(tesla는 scenes.json + storyboard/ 이미 보유):
```bash
curl -s -X POST http://127.0.0.1:8765/api/layers/generate -H 'Content-Type: application/json' -d '{"project_id":"tesla","concurrency":5}'
ls -la projects/tesla/layers/
cat projects/tesla/layers.json
```
Expected: bg_1..5.png + char_1..5.png + layers.json.

- [ ] **Step 2: 시각 확인** — char_1.png(투명 인물), bg_1.png(인물 없는 배경) Read로 열어 분리 품질 확인.

- [ ] **Step 3: 정리** — layers/ gitignore(Task 7).

---

## Task 7: gitignore + 통합 검증

- [ ] **Step 1: gitignore** — `.gitignore`에 `projects/*/layers/` + `projects/*/layers.json` 추가.
- [ ] **Step 2: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` → 전부 PASS, git status 클린.
- [ ] **Step 3: import** — `... -c "from backend import imagegen, router, codex_runner; print('ok')"`
- [ ] **Step 4: 커밋**
```bash
git add .gitignore
git commit -m "chore: layers 생성물 gitignore + M3d 검증"
```

---

## Self-Review (작성자 체크)
- **PoC 커버리지**: codex -i 첨부(T1) / 마젠타→투명(T2) / 레이어 재생성(T3) / 씬별 병렬+layers.json(T4) / 패널(T5) / 라이브(T6). PoC 검증 경로와 일치.
- **Placeholder**: 없음.
- **타입 일관성**: `build_codex_cmd(images=)`/`run_skill(images=)`, `chroma_key_magenta`/`build_layer_prompt`/`generate_layer`/`generate_scene_layers`, `/api/layers/generate|list` — 일치. M3b/M3c imagegen 무손상(신규 함수 추가).
- **의존성**: Pillow/numpy 신규(requirements.txt). 백엔드 "stdlib only" 속성 변경 — 명시.
- **미반영(의도)**: 소품 레이어, 디스필 고도화, AE가 레이어로 컴프 조립은 M4. 투명은 마젠타 크로마(단일 인증), CLI gpt-image-1.5 미사용.
