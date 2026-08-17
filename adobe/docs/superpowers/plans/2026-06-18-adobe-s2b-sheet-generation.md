# S2b Sheet Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** entities.json의 엔티티별 멀티패널 일관성 시트를 codex로 1장씩 생성하고 references/에 저장, entities.json에 sheet 경로를 역기록한다.

**Architecture:** 새 모듈 `backend/sheets.py`가 type별 프롬프트를 만들어 기존 `imagegen._run_codex_image`로 엔티티당 1회 생성한다. 캐릭터는 1회성 기준 시트(`data/artstyle/semoji_base_sheet.png`)를 첨부 리스타일, 장소·소품은 단일샷 멀티패널. PIL 합성 불필요. 코드 TDD는 codex를 monkeypatch로 모킹하고, 실 이미지는 컨트롤러가 1회 생성·실증한다.

**Tech Stack:** Python 3 (stdlib + 기존 imagegen), pytest + monkeypatch. 테스트 러너: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`.

---

## 사전 정보 (구현자 필독)

- 작업 위치(격리 워크트리): `/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/.claude/worktrees/s2b-sheet-generation`. 모든 명령은 이 디렉터리에서.
- 테스트 명령 접두: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`
- 재사용 대상: `backend/imagegen.py` — `_run_codex_image(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None) -> {"status","path"|"error"}`, `versioned_path(dir, name)`, `base_img() -> Path|None`, `load_style() -> str`.
- 한국어 규칙: 가타카나/히라가나/한자 금지(순수 한국어/영어). 주석·문자열 모두.
- 커밋 메시지 말미에 추가:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```
- **Task 4(베이스 시트 실 생성)는 컨트롤러가 직접 수행**한다. 구현 subagent는 Task 1~3만.

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/sheets.py` (생성) | 프롬프트 빌더 + generate_sheet/generate_all_sheets + base_sheet/build_base_character_sheet |
| `data/artstyle/semoji_base_sheet.png` (Task 4, 실 생성·커밋) | 1회성 기준 캐릭터 시트 |
| `tests/test_sheets.py` (생성) | monkeypatch 단위 테스트 |

---

## Task 1: 프롬프트 빌더 + base_sheet()

**Files:**
- Create: `backend/sheets.py`
- Test: `tests/test_sheets.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_sheets.py` 생성:

```python
from pathlib import Path
from backend import sheets


def test_looks_from_visual_joins_fields():
    looks = sheets._looks_from_visual({"hair": "갈색 단발", "outfit": "노란 셔츠", "appearance": "둥근 얼굴"})
    assert "갈색 단발" in looks and "노란 셔츠" in looks
    assert sheets._looks_from_visual({}) == "원본 그대로"


def test_character_prompt_keeps_layout_and_name():
    p = sheets.build_character_sheet_prompt("하루", {"hair": "검은 머리", "expressions": ["미소", "놀람"]}, "references/characters/char-1.png")
    assert "하루" in p
    assert "유지" in p and "헤어" in p
    assert "references/characters/char-1.png" in p
    assert "미소" in p


def test_location_prompt_six_panels_no_person():
    p = sheets.build_location_sheet_prompt("거실", {"space": "아파트 거실", "mood": "따뜻함", "lighting": "오후"}, "references/locations/loc-1.png")
    assert "6패널" in p or "6" in p
    assert "인물" in p  # 인물 금지 문구
    assert "거실" in p


def test_prop_prompt_four_views_no_person():
    p = sheets.build_prop_sheet_prompt("포스트잇", {"form": "사각 메모지", "material": "종이", "color": "노랑"}, "references/props/prop-1.png")
    assert "4" in p
    assert "인물" in p
    assert "포스트잇" in p


def test_base_sheet_returns_none_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(sheets, "_BASE_SHEET", tmp_path / "nope.png")
    assert sheets.base_sheet() is None
    (tmp_path / "yes.png").write_bytes(b"x")
    monkeypatch.setattr(sheets, "_BASE_SHEET", tmp_path / "yes.png")
    assert sheets.base_sheet() == tmp_path / "yes.png"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: FAIL (ModuleNotFoundError: backend.sheets)

- [ ] **Step 3: Create `backend/sheets.py` with builders**

```python
"""일관성 시트 생성 (adobe 독립 Stage1-2 S2b) — entities.json의 엔티티별 멀티패널 시트를
codex로 1장씩 생성하고 references/에 저장, entities.json에 sheet 경로 역기록.
캐릭터는 세모지 베이스 시트를 리스타일(레이아웃·정체성 단일 소스), 장소·소품은 단일샷 멀티패널.
런타임 v3 의존 없음."""
from __future__ import annotations

import json
from pathlib import Path

from backend import imagegen

_ROOT = Path(__file__).resolve().parents[1]
_BASE_SHEET = _ROOT / "data" / "artstyle" / "semoji_base_sheet.png"


def base_sheet():
    """세모지 기준 캐릭터 시트(턴어라운드+표정 레이아웃) 경로. 없으면 None."""
    return _BASE_SHEET if _BASE_SHEET.exists() else None


def _looks_from_visual(visual: dict) -> str:
    """character visual {appearance,hair,outfit} → looks 문자열."""
    v = visual or {}
    parts = [str(v[k]).strip() for k in ("hair", "outfit", "appearance")
             if str(v.get(k) or "").strip()]
    return ", ".join(parts) if parts else "원본 그대로"


def build_character_sheet_prompt(name: str, visual: dict, rel_out: str) -> str:
    """베이스 캐릭터 시트(첨부 1번)를 리스타일 — 레이아웃·포즈·표정·비율 유지, 헤어·의상만 변경."""
    looks = _looks_from_visual(visual)
    exprs = ", ".join(str(e) for e in (visual or {}).get("expressions") or []) or "기본 표정들"
    return (
        f"첨부된 1번 이미지는 캐릭터 기준 시트(전신 턴어라운드 + 얼굴 클로즈업 + 표정 5컷)다.\n"
        f"이 시트의 캐릭터를 '{name}'(이)라는 캐릭터로 변경해서 같은 레이아웃으로 새로 그려줘.\n"
        f"- 패널 구성·포즈·표정 칸 배치·신체 비율·체형·얼굴 구조·그림체는 1번 시트 그대로 유지.\n"
        f"- 헤어와 의상만 변경: {looks}\n"
        f"- 표정 칸은 다음 정서를 반영: {exprs}\n"
        f"비율을 텍스트로 새로 지정하지 말 것. 글자·로고 없음. "
        f"image_gen으로 생성 후 현재 폴더의 {rel_out} 로 저장. 저장되면 'OK'만 답해."
    )


def build_location_sheet_prompt(name: str, visual: dict, rel_out: str) -> str:
    """장소 6패널 단일샷 — 인물 없음, 세모지 그림체."""
    v = visual or {}
    space = str(v.get("space") or "").strip()
    mood = str(v.get("mood") or "").strip()
    lighting = str(v.get("lighting") or "").strip()
    return (
        f"{imagegen.load_style()}\n\n## 장소 위치 시트(인물 없음)\n"
        f"'{name}' 장소를 한 이미지 안 6패널 그리드(2열 3행)로 그려줘:\n"
        f"1) 항공 와이드  2) 다른 각도 항공  3) 지상 아이레벨  "
        f"4) 랜드마크 디테일  5) 수면/원경 와이드  6) 야경.\n"
        f"- 공간: {space}\n- 분위기: {mood}\n- 조명: {lighting}\n"
        f"[첨부 이미지]는 그림체·색감 참고용 — 인물(사람)·캐릭터는 절대 그리지 말 것. 배경/장소만.\n"
        f"image_gen으로 1장 생성해 현재 폴더의 {rel_out} 로 저장. "
        f"비율을 텍스트로 새로 지정하지 말 것. 글자 없음. 저장되면 'OK'만 답해."
    )


def build_prop_sheet_prompt(name: str, visual: dict, rel_out: str) -> str:
    """소품 4뷰 단일샷 — 인물 없음, 세모지 그림체."""
    v = visual or {}
    form = str(v.get("form") or "").strip()
    material = str(v.get("material") or "").strip()
    color = str(v.get("color") or "").strip()
    return (
        f"{imagegen.load_style()}\n\n## 소품 시트(인물 없음)\n"
        f"'{name}' 소품을 한 이미지 안 4뷰(2x2)로 그려줘: 정면, 측면, 디테일 클로즈업, 인컨텍스트.\n"
        f"- 형태: {form}\n- 재질: {material}\n- 색: {color}\n"
        f"[첨부 이미지]는 그림체·색감 참고용 — 인물(사람)·캐릭터는 절대 그리지 말 것. 사물만.\n"
        f"image_gen으로 1장 생성해 현재 폴더의 {rel_out} 로 저장. "
        f"비율을 텍스트로 새로 지정하지 말 것. 글자 없음. 저장되면 'OK'만 답해."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/sheets.py tests/test_sheets.py
git commit -m "feat(s2b): sheet prompt builders + base_sheet

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: generate_sheet + generate_all_sheets + 소품 필터

**Files:**
- Modify: `backend/sheets.py` (append)
- Test: `tests/test_sheets.py` (append)

- [ ] **Step 1: Write the failing tests**

`tests/test_sheets.py`에 추가:

```python
import json
from backend import imagegen


def _fake_codex(monkeypatch, fail_ids=()):
    calls = []

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        calls.append({"out": str(out), "prompt": prompt, "images": images})
        if any(fid in str(out) for fid in fail_ids):
            return {"status": "failed", "error": "no_file"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(b"\x89PNG\r\n\x1a\n")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    return calls


def _entities_doc():
    return {"entities": [
        {"id": "char-1", "type": "character", "name": "하루", "visual": {"hair": "검은 머리"}, "scenes": [1, 2]},
        {"id": "loc-1", "type": "location", "name": "거실", "visual": {"space": "거실"}, "scenes": [1]},
        {"id": "prop-1", "type": "prop", "name": "포스트잇", "visual": {"color": "노랑"}, "scenes": [1, 3]},
        {"id": "prop-2", "type": "prop", "name": "컵", "visual": {}, "scenes": [2]},
    ]}


def test_generate_all_sheets_happy(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    _fake_codex(monkeypatch)
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"] == {"character": 1, "location": 1, "prop": 1}
    assert r["skipped"] == []
    doc = json.loads((tmp_path / "entities.json").read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in doc["entities"]}
    assert by_id["char-1"]["sheet"] == "references/characters/char-1.png"
    assert by_id["loc-1"]["sheet"] == "references/locations/loc-1.png"
    assert by_id["prop-1"]["sheet"] == "references/props/prop-1.png"
    assert "sheet" not in by_id["prop-2"]   # 1씬 소품 미생성
    assert (tmp_path / "references/characters/char-1.png").exists()


def test_prop_single_scene_filtered(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    calls = _fake_codex(monkeypatch)
    sheets.generate_all_sheets(tmp_path)
    assert not any("prop-2" in c["out"] for c in calls)   # 컵(1씬) codex 미호출


def test_character_without_base_sheet_skipped(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: None)
    _fake_codex(monkeypatch)
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"]["character"] == 0
    assert any(s["id"] == "char-1" for s in r["skipped"])
    assert r["sheets"]["location"] == 1   # 나머지 진행


def test_codex_failure_isolated(tmp_path, monkeypatch):
    (tmp_path / "entities.json").write_text(json.dumps(_entities_doc(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sheets, "base_sheet", lambda: tmp_path / "bs.png")
    (tmp_path / "bs.png").write_bytes(b"x")
    _fake_codex(monkeypatch, fail_ids=("loc-1",))
    r = sheets.generate_all_sheets(tmp_path)
    assert r["sheets"]["location"] == 0
    assert any(s["id"] == "loc-1" for s in r["skipped"])
    assert r["sheets"]["character"] == 1


def test_no_entities_errors(tmp_path):
    assert sheets.generate_all_sheets(tmp_path).get("error")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: FAIL (AttributeError: module 'backend.sheets' has no attribute 'generate_all_sheets')

- [ ] **Step 3: Append generation to `backend/sheets.py`**

```python
_SUBDIR = {"character": "references/characters",
           "location": "references/locations",
           "prop": "references/props"}


def generate_sheet(proj_dir, entity, *, on_line=None) -> dict:
    """엔티티 1개 시트 생성 → references/<type>/<id>.png. {status,path,rel}|{status:failed,error}."""
    proj_dir = Path(proj_dir)
    etype = entity.get("type")
    eid = entity.get("id") or "entity"
    name = entity.get("name") or eid
    visual = entity.get("visual") or {}
    subdir = _SUBDIR.get(etype)
    if not subdir:
        return {"status": "failed", "error": f"unknown type {etype}"}
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = imagegen.versioned_path(out_base, f"{eid}.png")
    rel = out.relative_to(proj_dir).as_posix()

    if etype == "character":
        bs = base_sheet()
        if not bs:
            return {"status": "failed", "error": "semoji_base_sheet.png 없음 — 캐릭터 시트 불가"}
        prompt = build_character_sheet_prompt(name, visual, rel)
        images = [str(bs)]
    elif etype == "location":
        prompt = build_location_sheet_prompt(name, visual, rel)
        images = [str(imagegen.base_img())] if imagegen.base_img() else None
    else:
        prompt = build_prop_sheet_prompt(name, visual, rel)
        images = [str(imagegen.base_img())] if imagegen.base_img() else None

    res = imagegen._run_codex_image(proj_dir, out, prompt, images=images, on_line=on_line)
    if res.get("status") == "completed":
        return {"status": "completed", "path": str(out), "rel": rel}
    return {"status": "failed", "error": res.get("error", "no_file")}


def _wants_sheet(entity) -> bool:
    """소품은 재등장(scenes ≥2)만. 캐릭터·장소는 항상."""
    if entity.get("type") == "prop":
        return len(entity.get("scenes") or []) >= 2
    return entity.get("type") in ("character", "location")


def generate_all_sheets(proj_dir, *, types=("character", "location", "prop"), on_event=None) -> dict:
    """entities.json 읽기 → 대상 필터(소품 ≥2씬) → 엔티티별 시트 → entities.json sheet 역기록.
    반환 {sheets:{character,location,prop}, skipped:[{id,error}]} | {error}."""
    proj_dir = Path(proj_dir)
    ep = proj_dir / "entities.json"
    if not ep.is_file():
        return {"error": "entities.json 필요 (S2a 먼저)"}
    try:
        doc = json.loads(ep.read_text(encoding="utf-8"))
        ents = list(doc.get("entities") or [])
    except Exception:
        return {"error": "entities.json 파싱 실패"}

    counts = {"character": 0, "location": 0, "prop": 0}
    skipped: list = []
    for e in ents:
        if e.get("type") not in types or not _wants_sheet(e):
            continue
        if on_event:
            on_event(f"시트 생성: {e.get('type')} {e.get('id')}")
        res = generate_sheet(proj_dir, e, on_line=on_event)
        if res.get("status") == "completed":
            e["sheet"] = res["rel"]
            counts[e["type"]] = counts.get(e["type"], 0) + 1
        else:
            skipped.append({"id": e.get("id"), "error": res.get("error")})
            if on_event:
                on_event(f"시트 실패: {e.get('id')} — {res.get('error')}")

    doc["entities"] = ents
    ep.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_event:
        on_event(f"시트 완료 — char {counts['character']} loc {counts['location']} "
                 f"prop {counts['prop']}, skip {len(skipped)}")
    return {"sheets": counts, "skipped": skipped}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/sheets.py tests/test_sheets.py
git commit -m "feat(s2b): generate_sheet + generate_all_sheets with prop recurrence filter

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: build_base_character_sheet (1회성 베이스 시트 생성 함수)

**Files:**
- Modify: `backend/sheets.py` (append)
- Test: `tests/test_sheets.py` (append)

- [ ] **Step 1: Write the failing tests**

`tests/test_sheets.py`에 추가:

```python
def test_build_base_sheet_prompt_has_turnaround_and_expressions(tmp_path, monkeypatch):
    captured = {}

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        captured["prompt"] = prompt
        captured["images"] = images
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    monkeypatch.setattr(imagegen, "base_img", lambda: tmp_path / "base.jpg")
    (tmp_path / "base.jpg").write_bytes(b"x")
    r = sheets.build_base_character_sheet()
    assert r["status"] == "completed"
    assert "턴어라운드" in captured["prompt"] or "전신" in captured["prompt"]
    assert "표정" in captured["prompt"]
    assert captured["images"] == [str(tmp_path / "base.jpg")]


def test_build_base_sheet_no_base_fails(monkeypatch):
    monkeypatch.setattr(imagegen, "base_img", lambda: None)
    assert sheets.build_base_character_sheet()["status"] == "failed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: FAIL (AttributeError: build_base_character_sheet)

- [ ] **Step 3: Append to `backend/sheets.py`**

```python
def build_base_character_sheet(*, on_line=None) -> dict:
    """1회성: semoji_base.jpg → 턴어라운드+표정 기준 시트(semoji_base_sheet.png) 생성.
    실 codex 호출. 결과는 수동 실증 후 자산으로 커밋."""
    base = imagegen.base_img()
    if not base:
        return {"status": "failed", "error": "semoji_base.jpg 없음"}
    _BASE_SHEET.parent.mkdir(parents=True, exist_ok=True)
    prompt = (
        f"첨부된 1번 이미지의 캐릭터로 캐릭터 기준 시트를 한 장으로 그려줘.\n"
        f"- 상단: 전신 정면, 전신 측면, 전신 후면, 그리고 큰 얼굴 클로즈업.\n"
        f"- 하단: 같은 인물의 표정 5컷(중립, 놀람, 슬픔, 걱정, 미소).\n"
        f"- 신체 비율·체형·얼굴 구조·그림체는 1번 이미지 그대로 유지. 같은 인물.\n"
        f"비율을 텍스트로 새로 지정하지 말 것. 글자·로고 없음. "
        f"image_gen으로 생성 후 현재 폴더의 {_BASE_SHEET.name} 로 저장. 저장되면 'OK'만 답해."
    )
    return imagegen._run_codex_image(_BASE_SHEET.parent, _BASE_SHEET, prompt,
                                     images=[str(base)], on_line=on_line)
```

- [ ] **Step 4: Run the module test suite to verify pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_sheets.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Run the WHOLE suite to confirm no regressions**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: PASS (521 passed, 1 skipped — 기존 509 + 12 신규)

- [ ] **Step 6: Commit**

```bash
git add backend/sheets.py tests/test_sheets.py
git commit -m "feat(s2b): build_base_character_sheet one-time base sheet generator

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: 베이스 시트 실 생성·실증·커밋 (컨트롤러 전담 — subagent 아님)

> 이 태스크는 실제 codex 이미지 생성 + 사용자 시각 검증을 포함하므로 컨트롤러가 직접 수행한다. 구현 subagent는 여기까지 오지 않는다.

- [ ] **Step 1: 실 베이스 시트 생성** — `python -c "from backend import sheets; print(sheets.build_base_character_sheet())"` (실 codex). `data/artstyle/semoji_base_sheet.png` 생성 확인.
- [ ] **Step 2: 사용자 시각 실증** — 생성 이미지를 사용자에게 보여 레이아웃(전신 턴어라운드 3컷 + 얼굴 클로즈업 + 표정 5컷)·세모지 그림체·비율을 확인받는다. 불만족 시 프롬프트 조정 후 재생성.
- [ ] **Step 3: 자산 커밋** — 승인되면 `git add data/artstyle/semoji_base_sheet.png && git commit`.

---

## Self-Review (작성자 점검 완료)

**Spec coverage:** base_sheet(Task1) · 프롬프트 빌더 3종(Task1) · generate_sheet/generate_all_sheets/_wants_sheet 필터(Task2) · build_base_character_sheet(Task3) · 실 생성·실증·커밋(Task4) · entities.json sheet 역기록(Task2) · 에러 처리(Task2 분기) · 테스트(Task1~3) — 스펙 전 항목 커버.

**Placeholder scan:** 없음 — 모든 코드 스텝 완전한 코드 포함.

**Type consistency:** `base_sheet`/`_looks_from_visual`/`build_character_sheet_prompt`/`build_location_sheet_prompt`/`build_prop_sheet_prompt`/`generate_sheet`/`_wants_sheet`/`generate_all_sheets`/`build_base_character_sheet` 시그니처 Task 간 일치. 반환 키 `{status,path,rel}`/`{sheets,skipped}`/`{error}` 일관. `_SUBDIR`/`_BASE_SHEET` 상수 일관. references 경로 `references/<type>/<id>.png` 일관.
