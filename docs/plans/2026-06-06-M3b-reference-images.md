# M3b — 레퍼런스 + 이미지 생성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** 최종 원고에서 핵심 레퍼런스 목록을 뽑고, codex imagegen(단일 인증)으로 semoji 스타일 레퍼런스 이미지를 프로젝트 폴더에 생성해 패널 갤러리에 표시한다.

**Architecture:** ⑧ reference-list = codex 텍스트 스킬(references.json). ⑨ imagegen = 백엔드 모듈이 `codex exec -s workspace-write`로 이미지를 projects/{id}/images/에 직접 저장(rate-limit 재시도, 버전 무삭제). 패널은 `<img src="file://...">`로 갤러리 표시.

**Tech Stack:** Python 3.12(표준 라이브러리), pytest, codex CLI(exec, image_gen 도구), CEP 패널.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` **repo 루트에서**.

근거: `docs/design/M3_pipeline_contract.md` §3.2(imagegen), `docs/poc/POC_codex_imagegen.md`(검증: `-s workspace-write`, rate limit 재시도 필요).

---

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/codex_runner.py` | `build_codex_cmd`/`run_skill`에 `sandbox` 파라미터 추가 |
| `backend/imagegen.py` | codex imagegen 호출(workspace-write) + 재시도 + 버전 경로 |
| `backend/router.py` | `/api/images/generate`, `/api/images/list` |
| `data/artstyle/semoji.md` | semoji 스타일 기술(imagegen 프롬프트 prepend, v4 참고 복사) |
| `skills/reference-list/` | SKILL.md + skill.json + references.schema.json (⑧) |
| `cep/com.autokairos.pd/{index.html,js/main.js}` | 레퍼런스 이미지 갤러리 |
| `tests/test_imagegen.py` `tests/test_codex_runner.py`(추가) `tests/test_skills_cfg.py`(추가) `tests/test_router.py`(추가) | 단위 테스트 |

---

## Task 1: run_skill sandbox 파라미터 (codex_runner.py)

**Files:** Modify `backend/codex_runner.py`; Test `tests/test_codex_runner.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_codex_runner.py`에 추가:
```python
def test_build_cmd_with_sandbox():
    cmd = build_codex_cmd(sandbox="workspace-write")
    assert "-s" in cmd
    assert cmd[cmd.index("-s") + 1] == "workspace-write"


def test_build_cmd_no_sandbox_by_default():
    cmd = build_codex_cmd()
    assert "-s" not in cmd
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_codex_runner.py -v` → 새 2개 FAIL

- [ ] **Step 3: 구현** — `backend/codex_runner.py`의 `build_codex_cmd`에 `sandbox` 파라미터 추가. 시그니처에 `sandbox: str | None = None` 추가(키워드), `if skip_git:` 줄 **앞**에 삽입:
```python
    if sandbox:
        cmd += ["-s", sandbox]
```
그리고 `run_skill`에도 `sandbox: str | None = None` 파라미터 추가 후 `build_codex_cmd(...)` 호출에 `sandbox=sandbox` 전달:
```python
    cmd = build_codex_cmd(
        session_id=session_id, output_schema=output_schema,
        output_last=output_last, sandbox=sandbox,
    )
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_codex_runner.py -v` → PASS (기존 + 2). 전체 `... -m pytest tests/ -q` 깨지지 않는지.

- [ ] **Step 5: 커밋**
```bash
git add backend/codex_runner.py tests/test_codex_runner.py
git commit -m "feat(backend): run_skill에 sandbox 파라미터(-s workspace-write) 추가"
```

---

## Task 2: semoji 스타일 데이터 (data/artstyle/semoji.md)

**Files:** Create `data/artstyle/semoji.md`; Test `tests/test_imagegen.py`(존재 확인 일부)

- [ ] **Step 1: semoji 스타일 파일 작성** — `data/artstyle/semoji.md` (v4 semoji.json 참고 자체 복사):
```markdown
# semoji 아트스타일 (이미지 생성용)

Modern editorial flat-design illustration. Friendly, approachable, professional clean.

CRITICAL — borderless: NO black ink outlines. Forms defined by flat color shapes meeting. Clean crisp vector edges.

CHARACTER: 3 to 3.5 head chibi-ish proportions. Big round head, chunky torso, short stubby legs. Eyes = small black dot ovals (no iris). Optional soft pink cheek blush. Thin curved line mouth.

COLOR & SHADING: Flat solid block colors. At most ONE soft cell-shadow tone per surface. NO gradients, NO painterly blending, NO 3D, NO photorealistic.

BACKGROUND: Single solid muted color (sage green, off-white, dusty rose, cream) or extremely simplified flat shapes. Generous negative space.

PALETTE: Muted warm — dusty pastels, sage green, off-white, dusty blue, soft beige.

EXPLICITLY NOT: Disney/Pixar, painterly, comic-book outlines, 3D, photorealistic. NO text, NO captions, NO logos.
```

- [ ] **Step 2: 커밋**
```bash
git add data/artstyle/semoji.md
git commit -m "feat(artstyle): semoji 스타일 기술(imagegen 프롬프트용) — v4 참고 자체 복사"
```

---

## Task 3: reference-list 스킬 (⑧)

**Files:** Create `skills/reference-list/{SKILL.md,skill.json,references.schema.json}`; Test `tests/test_skills_cfg.py`(추가)

- [ ] **Step 1: references.schema.json** (strict — additionalProperties:false + 전체 required):
```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["project_id", "references"],
  "properties": {
    "project_id": { "type": "string" },
    "references": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "subject", "image_prompt"],
        "properties": {
          "id": { "type": "string" },
          "subject": { "type": "string" },
          "image_prompt": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: skill.json** — `skills/reference-list/skill.json`:
```json
{"name":"reference-list","inputs":["final_manuscript.md"],"output":"references.json","output_kind":"json","schema":"references.schema.json"}
```

- [ ] **Step 3: SKILL.md** — `skills/reference-list/SKILL.md`:
```markdown
---
name: reference-list
description: 최종 원고에서 핵심 시각 레퍼런스 목록을 뽑아 references.json 생성(이미지 생성용 프롬프트 포함).
---
# reference-list
final_manuscript.md를 읽고 영상의 핵심 시각 소재 3~6개를 고른다(주요 장면·사물·인물).
## 출력(references.json, 스키마 references.schema.json)
- 각 항목: id("ref_1"…), subject(한 줄 소재), image_prompt(생성용 시각 묘사, 한국어)
- image_prompt에는 아트스타일 키워드(평면/3등신 등) 넣지 말 것 — 스타일은 생성 단계가 따로 입힌다.
## 금지
- 6개 초과. 텍스트가 들어간 이미지 요구.
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 4: 설정 로드 테스트** — `tests/test_skills_cfg.py`에 추가:
```python
def test_reference_list_config():
    c = skills_cfg.load_config(SKILLS, "reference-list")
    assert c["output"] == "references.json"
    assert c["schema"] == "references.schema.json"
    assert c["inputs"] == ["final_manuscript.md"]
```

- [ ] **Step 5: 통과 + 커밋**
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_skills_cfg.py -v
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -c "import json;json.load(open('skills/reference-list/references.schema.json'));print('valid')"
git add skills/reference-list tests/test_skills_cfg.py
git commit -m "feat(skill): reference-list — 원고에서 시각 레퍼런스 목록(references.json)"
```

---

## Task 4: imagegen 모듈 (⑨ — codex imagegen + 재시도 + 버전)

**Files:** Create `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트 (순수 로직)** — `tests/test_imagegen.py`:
```python
from pathlib import Path
from backend import imagegen


def test_versioned_path_first(tmp_path):
    p = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p.name == "ref_1.png"


def test_versioned_path_no_overwrite(tmp_path):
    (tmp_path / "ref_1.png").write_text("x", encoding="utf-8")
    p = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p.name == "ref_1_v2.png"
    (tmp_path / "ref_1_v2.png").write_text("x", encoding="utf-8")
    p2 = imagegen.versioned_path(tmp_path, "ref_1.png")
    assert p2.name == "ref_1_v3.png"


def test_is_rate_limited():
    assert imagegen.is_rate_limited("image_gen rate limit으로 실패") is True
    assert imagegen.is_rate_limited("OK 저장 완료") is False


def test_build_image_prompt():
    pr = imagegen.build_image_prompt("전기차 한 대", "STYLE_DESC", "images/ref_1.png")
    assert "STYLE_DESC" in pr
    assert "전기차 한 대" in pr
    assert "images/ref_1.png" in pr
    assert "image_gen" in pr
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_imagegen.py -v` → FAIL

- [ ] **Step 3: 구현** — `backend/imagegen.py`:
```python
"""codex imagegen(빌트인 image_gen, 단일 인증) 호출 — workspace-write 저장 + 재시도 + 버전."""
from __future__ import annotations

import time
from pathlib import Path

from backend.codex_runner import run_skill

STYLE_FILE = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "semoji.md"


def load_style() -> str:
    return STYLE_FILE.read_text(encoding="utf-8") if STYLE_FILE.exists() else ""


def versioned_path(images_dir: Path, name: str) -> Path:
    """name이 이미 있으면 _v2,_v3... 으로 (무삭제)."""
    base = images_dir / name
    if not base.exists():
        return base
    stem, ext = name.rsplit(".", 1)
    n = 2
    while (images_dir / f"{stem}_v{n}.{ext}").exists():
        n += 1
    return images_dir / f"{stem}_v{n}.{ext}"


def is_rate_limited(text: str) -> bool:
    return "rate limit" in (text or "").lower()


def build_image_prompt(image_prompt: str, style_desc: str, rel_out: str) -> str:
    return (
        f"{style_desc}\n\n## 생성 지시\n"
        f"image_gen 도구로 위 아트스타일을 적용한 이미지 1장을 생성해 "
        f"현재 폴더의 {rel_out} 로 저장해줘.\n내용: {image_prompt}\n"
        f"텍스트 없음. 저장되면 'OK'만 답해."
    )


def generate_one(proj_dir: Path, rel_out: str, image_prompt: str,
                 *, retries: int = 2, on_line=None) -> dict:
    """레퍼런스 1장 생성. rate limit 시 백오프 재시도. 반환 {status, path|error}."""
    images_dir = proj_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    out = versioned_path(images_dir, Path(rel_out).name)
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

- [ ] **Step 4: 통과** — `... -m pytest tests/test_imagegen.py -v` → PASS (4 passed). 전체도 확인.

- [ ] **Step 5: 커밋**
```bash
git add backend/imagegen.py tests/test_imagegen.py
git commit -m "feat(backend): imagegen 모듈 — codex workspace-write 저장 + rate limit 재시도 + 버전 무삭제"
```

---

## Task 5: /api/images/generate + /api/images/list (router.py)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트 추가** — `tests/test_router.py`에 추가(generate는 imagegen 모킹):
```python
def test_images_generate_from_references(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "references.json").write_text(
        '{"project_id":"p","references":[{"id":"ref_1","subject":"차","image_prompt":"전기차"}]}',
        encoding="utf-8")

    def fake_gen(proj_dir, rel_out, image_prompt, **kw):
        out = proj_dir / "images" / rel_out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_gen)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/images/generate", {},
                                {"project_id": "p"}, ctx)
    assert code == 200
    assert body["generated"] == 1


def test_images_list(tmp_path):
    proj = tmp_path / "p"; (proj / "images").mkdir(parents=True)
    (proj / "images" / "ref_1.png").write_bytes(b"\x89PNG")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/images/list",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    assert "ref_1.png" in body["images"]
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -v` → 새 2개 FAIL

- [ ] **Step 3: router.py 확장** — 상단 import에 `from backend import imagegen` 추가. `/api/pipeline/run` 블록 다음에:
```python
    if method == "POST" and p == "/api/images/generate":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        refs_fp = proj_dir / "references.json"
        if not refs_fp.exists():
            return 422, {"error": "references.json 없음 — reference-list 먼저 실행"}
        import json as _json
        refs = _json.loads(refs_fp.read_text(encoding="utf-8")).get("references", [])
        jobs = ctx["jobs"]
        jid = jobs.create("images", pid)
        done = 0
        for ref in refs:
            rel = f"{ref['id']}.png"
            res = imagegen.generate_one(proj_dir, rel, ref["image_prompt"],
                                        on_line=lambda ln: jobs.append_log(jid, ln))
            if res["status"] == "completed":
                done += 1
            else:
                jobs.append_log(jid, f"FAIL {ref['id']}: {res.get('error')}")
        jobs.set_status(jid, "completed" if done else "failed",
                        artifact_paths=[str(proj_dir / "images")])
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"],
                     "generated": done, "total": len(refs)}

    if method == "GET" and p == "/api/images/list":
        pid = query.get("project_id", "")
        images_dir = root / pid / "images"
        if not images_dir.is_dir():
            return 200, {"images": []}
        names = sorted(f.name for f in images_dir.glob("*.png"))
        return 200, {"images": names, "dir": str(images_dir)}
```

- [ ] **Step 4: 통과 (멱등 2회) + 커밋**
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -q   # 2회
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/images/generate(references→이미지) + /api/images/list"
```

---

## Task 6: 패널 이미지 갤러리

**Files:** Modify `cep/com.autokairos.pd/{index.html,js/main.js}`

- [ ] **Step 1: index.html** — 「씬 분해」 블록 다음에 추가:
```html
  <div class="label">레퍼런스 이미지</div>
  <button id="btnRefList">레퍼런스 목록 생성</button>
  <button id="btnGenImages" class="alt">이미지 생성</button>
  <div class="box" id="gallery">—</div>
```

- [ ] **Step 2: main.js** — DOMContentLoaded 위에 추가:
```js
function makeReferences() {
  if (!SELECTED_PROJECT) { $("gallery").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery").textContent = "레퍼런스 목록 생성 중...";
  fetch(BACKEND + "/api/skills/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, skill_name: "reference-list" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) { $("gallery").textContent = "레퍼런스 목록: " + j.status + " — 이제 [이미지 생성]"; })
    .catch(function (e) { $("gallery").textContent = "오류: " + e; });
}

function genImages() {
  if (!SELECTED_PROJECT) { $("gallery").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery").textContent = "이미지 생성 중... (codex, 수십 초)";
  fetch(BACKEND + "/api/images/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "completed") { $("gallery").textContent = "실패: " + JSON.stringify(j); return; }
      return showGallery();
    })
    .catch(function (e) { $("gallery").textContent = "오류: " + e; });
}

function showGallery() {
  fetch(BACKEND + "/api/images/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "";
      var imgs = j.images || [];
      if (!imgs.length) { $("gallery").textContent = "(이미지 없음)"; return; }
      $("gallery").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:90px;height:auto;margin:3px;border-radius:4px;" title="' + n + '">';
      }).join("");
    });
}
```
DOMContentLoaded 핸들러에 바인딩 추가:
```js
  $("btnRefList").addEventListener("click", makeReferences);
  $("btnGenImages").addEventListener("click", genImages);
```

- [ ] **Step 3: JS 문법 점검** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/main.js','utf8'))" && echo OK`

- [ ] **Step 4: 커밋**
```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 레퍼런스 목록 생성 + 이미지 생성 + 갤러리 표시"
```

---

## Task 7: 라이브 e2e — 테슬라 레퍼런스 이미지 (사용자 확인)

> ⚠️ 실제 codex image_gen 다회 호출 — 크레딧/rate limit. **사용자 합의 후.**

- [ ] **Step 1: reference-list 실행** — 백엔드 기동 후:
```bash
curl -s -X POST http://127.0.0.1:8765/api/skills/run -H 'Content-Type: application/json' -d '{"project_id":"tesla","skill_name":"reference-list"}'
cat projects/tesla/references.json
```
Expected: references 3~6개 (id/subject/image_prompt).

- [ ] **Step 2: 이미지 생성**
```bash
curl -s -X POST http://127.0.0.1:8765/api/images/generate -H 'Content-Type: application/json' -d '{"project_id":"tesla"}'
ls -la projects/tesla/images/
```
Expected: `{"generated":N}` + projects/tesla/images/ref_*.png. rate limit 시 재시도 로그.

- [ ] **Step 3: 이미지 시각 확인** — 생성된 ref_*.png를 Read로 열어 semoji 스타일 확인.

- [ ] **Step 4: 정리** — `~/.codex/generated_images/` 캐시는 별도(사용자 주기 정리). projects/tesla/images/는 보고용.

---

## Task 8: 통합 검증

- [ ] **Step 1: 전체 단위 테스트 멱등 2회** — `... -m pytest tests/ -q` → 전부 PASS, git status 클린.
- [ ] **Step 2: import** — `... -c "from backend import imagegen, router, codex_runner; print('ok')"`
- [ ] **Step 3: reference-list skill.json + semoji.md 존재 확인.**

---

## Self-Review (작성자 체크)
- **계약 커버리지**: §3.2 imagegen(workspace-write/재시도/버전)→T1·T4, semoji 스타일→T2, ⑧ reference-list→T3, ⑨ /api/images/generate→T5, 패널 갤러리→T6, 라이브→T7.
- **Placeholder**: 없음 — 모든 코드/스킬/스타일 본문 포함.
- **타입 일관성**: `build_codex_cmd(sandbox=)`/`run_skill(sandbox=)`, `imagegen.versioned_path/is_rate_limited/build_image_prompt/generate_one`, `/api/images/generate`·`/api/images/list` — Task 간 일치.
- **미반영(의도)**: 스토리보드(⑩)=M3c(imagegen 모듈 재사용). 비동기/실시간 표시는 동기+수동갱신 유지.
- **리스크**: rate limit(재시도/백오프 반영), 패널 file:// 이미지 표시(CEP 파일접근 플래그 기존 설정됨).
