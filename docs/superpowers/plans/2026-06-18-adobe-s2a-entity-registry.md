# S2a Entity Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** auto_kairos_adobe의 씬별 free-text 엔티티 태그를 비디오 전체 정규화 레지스트리(`entities.json`)로 통합하고 안정적 ID를 각 씬에 역링크한다.

**Architecture:** 기존 Stage 1-2 모듈 패턴(모듈 전역 함수 + `llm.run_orchestrator` + monkeypatch 테스트)을 따른다. 결정적 수집·역링크는 순수 함수, 통합·시각명세 합성만 LLM. LLM 실패 시 결정적 폴백으로 비블로킹.

**Tech Stack:** Python 3 (stdlib only: json, re, pathlib), pytest + monkeypatch. 테스트 러너: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`.

---

## 사전 정보 (구현자 필독)

- 작업 위치(격리 워크트리): `/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/.claude/worktrees/s2a-entity-registry`. 모든 명령은 이 디렉터리에서.
- 테스트 명령 접두: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`
- 참고 패턴 파일: `backend/scene_analysis.py`(`_load_skill`/`_read`/`run_orchestrator` 사용법), `tests/test_scene_analyze.py`(monkeypatch idiom).
- `llm.run_orchestrator(prompt, cwd, *, output_schema=None, output_last=None, on_line=None, ...)` → `{"returncode": int, ...}`이고, 성공 시 `output_last` 경로에 JSON을 쓴다. 가짜 패치는 `output_last`에 직접 써주면 된다.
- 한국어 규칙: 가타카나/히라가나/한자 금지(순수 한국어/영어). 주석·문자열 모두 적용.
- 커밋 메시지 말미에 추가:
  ```
  Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
  ```

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/schemas/entities.schema.json` (생성) | LLM 통합 출력 계약 |
| `skills/entity-registry/SKILL.md` (생성) | 통합·시각명세 합성 프롬프트 |
| `backend/entities.py` (생성) | 수집·통합·폴백·역링크 오케스트레이션 |
| `tests/test_entities.py` (생성) | 단위·통합 테스트 |

---

## Task 1: 스키마 + 스킬 자산

**Files:**
- Create: `backend/schemas/entities.schema.json`
- Create: `skills/entity-registry/SKILL.md`
- Test: `tests/test_entities.py`

- [ ] **Step 1: Write the failing test**

`tests/test_entities.py` 생성:

```python
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_entities_schema_valid():
    schema = json.loads((_ROOT / "backend/schemas/entities.schema.json").read_text(encoding="utf-8"))
    items = schema["properties"]["entities"]["items"]
    assert items["properties"]["type"]["enum"] == ["character", "location", "prop"]
    assert items["required"] == ["id", "type", "name"]


def test_entity_registry_skill_exists():
    md = (_ROOT / "skills/entity-registry/SKILL.md").read_text(encoding="utf-8")
    assert "entity-registry" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: FAIL (FileNotFoundError — 스키마/스킬 파일 없음)

- [ ] **Step 3: Create the schema file**

`backend/schemas/entities.schema.json`:

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["entities"],
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": ["id", "type", "name"],
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["character", "location", "prop"] },
          "name": { "type": "string" },
          "aliases": { "type": "array" },
          "visual": { "type": "object" },
          "first_scene": { "type": "integer" },
          "scenes": { "type": "array" }
        }
      }
    }
  }
}
```

- [ ] **Step 4: Create the skill file**

`skills/entity-registry/SKILL.md`:

```markdown
---
name: entity-registry
description: 씬별 free-text 엔티티 태그를 비디오 전체 정규화 레지스트리로 통합 — 표기 변형 dedupe + 풍부 시각 명세 합성.
---
# entity-registry

씬에서 추출된 캐릭터/장소/소품 출현 목록을 받아 **비디오 전체에서 정규화된 엔티티 레지스트리**를 만든다. 이후 시트 생성·씬 렌더가 이 레지스트리를 단일 소스로 쓴다.

## 입력
- 엔티티 출현 목록: `- [type] raw (씬N)` 형태. type은 character|location|prop.
- editorial brief, 원고 — 각 엔티티의 시각 묘사 출처.

## 해야 할 일
1. **표기 변형 통합** — 같은 대상의 다른 표기(예 "할머니" / "할머니 캐릭터" / "노인")를 하나의 엔티티로 묶고, 본 표기들을 모두 `aliases`에 넣는다.
2. **canonical 부여** — 안정적 `id`(kebab-case, 타입 접두: `char-`, `loc-`, `prop-`), 대표 `name`(한국어), `type`.
3. **시각 명세 합성** — 원고·브리프 근거로 `visual` 작성:
   - character → `{appearance, hair, outfit, expressions[]}`
   - location → `{space, mood, lighting}`
   - prop → `{form, material, color}`
4. `first_scene`(최초 등장 씬 번호), `scenes`(등장 씬 번호 배열).

## 출력
entities JSON만 출력:
```
{ "entities": [ { "id", "type", "name", "aliases": [...], "visual": {...}, "first_scene", "scenes": [...] } ] }
```
- 모든 출현이 어떤 엔티티의 `name` 또는 `aliases`에 정확히 포함되어야 한다(역링크가 정확 일치로 매칭함).
- 근거 없는 엔티티를 새로 만들지 말 것. 출현에 있는 대상만.

## 한국어 규칙
- 가타카나/히라가나/한자 금지.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/entities.schema.json skills/entity-registry/SKILL.md tests/test_entities.py
git commit -m "feat(s2a): entities schema + entity-registry skill

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 결정적 헬퍼 (정규화·수집·폴백·역링크)

**Files:**
- Create: `backend/entities.py`
- Test: `tests/test_entities.py` (append)

- [ ] **Step 1: Write the failing tests**

`tests/test_entities.py`에 추가:

```python
from backend import entities


def test_norm_collapses_whitespace():
    assert entities._norm("  할머니   캐릭터 ") == "할머니 캐릭터"
    assert entities._norm(None) == ""


def test_gather_occurrences_orders_and_filters():
    scenes = [
        {"sceneNumber": 1, "characters": ["할머니", ""], "location": "거실", "props": ["포스트잇"]},
        {"sceneNumber": 2, "characters": [], "location": "", "props": []},
    ]
    occ = entities._gather_occurrences(scenes)
    assert occ == [
        {"type": "character", "raw": "할머니", "scene": 1},
        {"type": "location", "raw": "거실", "scene": 1},
        {"type": "prop", "raw": "포스트잇", "scene": 1},
    ]


def test_fallback_entities_dedupes_by_norm():
    occ = [
        {"type": "character", "raw": "할머니", "scene": 1},
        {"type": "character", "raw": "할머니", "scene": 2},
        {"type": "location", "raw": "거실", "scene": 1},
    ]
    ents = entities._fallback_entities(occ)
    assert len(ents) == 2
    grandma = next(e for e in ents if e["type"] == "character")
    assert grandma["id"] == "character-1"
    assert grandma["scenes"] == [1, 2]
    assert grandma["first_scene"] == 1
    assert grandma["aliases"] == ["할머니"]


def test_backlink_scenes_maps_ids_via_aliases():
    scenes = [
        {"sceneNumber": 1, "characters": ["할머니"], "location": "거실", "props": []},
        {"sceneNumber": 2, "characters": ["할머니 캐릭터"], "location": "", "props": []},
    ]
    ents = [
        {"id": "char-grandma", "type": "character", "name": "할머니",
         "aliases": ["할머니", "할머니 캐릭터"]},
        {"id": "loc-living", "type": "location", "name": "거실", "aliases": ["거실"]},
    ]
    updated = entities._backlink_scenes(scenes, ents)
    assert updated == 2
    assert scenes[0]["character_ids"] == ["char-grandma"]
    assert scenes[0]["location_id"] == "loc-living"
    assert scenes[0]["prop_ids"] == []
    assert scenes[1]["character_ids"] == ["char-grandma"]
    assert scenes[1]["location_id"] == ""


def test_backlink_unmatched_logs_and_skips():
    scenes = [{"sceneNumber": 1, "characters": ["미지의인물"], "location": "", "props": []}]
    events = []
    updated = entities._backlink_scenes(scenes, [], on_event=events.append)
    assert updated == 0
    assert scenes[0]["character_ids"] == []
    assert any("미매칭" in e for e in events)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: FAIL (ModuleNotFoundError: backend.entities)

- [ ] **Step 3: Create `backend/entities.py` with helpers**

```python
"""엔티티 레지스트리 (adobe 독립 Stage1-2 S2a) — scenes.json의 free-text 엔티티 태그를
비디오 전체 정규화 레지스트리로 통합하고 안정적 ID를 각 씬에 역링크. 런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import llm

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
_ENTITY_SCHEMA = _SCHEMAS / "entities.schema.json"
_TYPES = ("character", "location", "prop")


def _load_skill(name: str) -> str:
    md = _SKILLS / name / "SKILL.md"
    if not md.is_file():
        return f"skill: {name}"
    text = md.read_text(encoding="utf-8")
    if text.startswith("---"):              # YAML frontmatter 제거
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip("\n")
    return text


def _read(proj_dir: Path, name: str) -> str:
    p = proj_dir / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def _gather_occurrences(scenes: list) -> list:
    """각 씬의 characters/location/props → [{type, raw, scene}] 출현 목록(순서 보존)."""
    occ: list = []
    for s in scenes:
        sn = s.get("sceneNumber")
        for raw in (s.get("characters") or []):
            if _norm(raw):
                occ.append({"type": "character", "raw": str(raw), "scene": sn})
        if _norm(s.get("location")):
            occ.append({"type": "location", "raw": str(s.get("location")), "scene": sn})
        for raw in (s.get("props") or []):
            if _norm(raw):
                occ.append({"type": "prop", "raw": str(raw), "scene": sn})
    return occ


def _fallback_entities(occ: list) -> list:
    """LLM 실패 시 결정적 레지스트리 — unique (type, normalized raw)마다 자기 엔티티."""
    seen: dict = {}
    counters = {t: 0 for t in _TYPES}
    for o in occ:
        key = (o["type"], _norm(o["raw"]))
        if key not in seen:
            counters[o["type"]] += 1
            seen[key] = {
                "id": f"{o['type']}-{counters[o['type']]}",
                "type": o["type"],
                "name": o["raw"],
                "aliases": [o["raw"]],
                "visual": {},
                "first_scene": o["scene"],
                "scenes": [],
            }
        ent = seen[key]
        if o["scene"] not in ent["scenes"]:
            ent["scenes"].append(o["scene"])
    return list(seen.values())


def _alias_index(entities: list) -> dict:
    """(type, normalized alias/name) -> id. name도 alias로 포함. 첫 등록 우선."""
    idx: dict = {}
    for e in entities:
        et = e.get("type")
        for k in [e.get("name")] + list(e.get("aliases") or []):
            nk = _norm(k)
            if nk and (et, nk) not in idx:
                idx[(et, nk)] = e.get("id")
    return idx


def _backlink_scenes(scenes: list, entities: list, *, on_event=None) -> int:
    """각 씬에 character_ids/location_id/prop_ids 부여. 매칭된 씬 수 반환."""
    idx = _alias_index(entities)
    updated = 0
    for s in scenes:
        char_ids: list = []
        for raw in (s.get("characters") or []):
            if not _norm(raw):
                continue
            eid = idx.get(("character", _norm(raw)))
            if eid and eid not in char_ids:
                char_ids.append(eid)
            elif not eid and on_event:
                on_event(f"엔티티 미매칭(character): {raw}")
        loc_id = ""
        if _norm(s.get("location")):
            eid = idx.get(("location", _norm(s.get("location"))))
            if eid:
                loc_id = eid
            elif on_event:
                on_event(f"엔티티 미매칭(location): {s.get('location')}")
        prop_ids: list = []
        for raw in (s.get("props") or []):
            if not _norm(raw):
                continue
            eid = idx.get(("prop", _norm(raw)))
            if eid and eid not in prop_ids:
                prop_ids.append(eid)
            elif not eid and on_event:
                on_event(f"엔티티 미매칭(prop): {raw}")
        s["character_ids"] = char_ids
        s["location_id"] = loc_id
        s["prop_ids"] = prop_ids
        if char_ids or loc_id or prop_ids:
            updated += 1
    return updated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: PASS (7 passed — Task 1의 2개 + Task 2의 5개)

- [ ] **Step 5: Commit**

```bash
git add backend/entities.py tests/test_entities.py
git commit -m "feat(s2a): deterministic entity helpers (norm/gather/fallback/backlink)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: LLM 통합 + `build_entity_registry` 오케스트레이션

**Files:**
- Modify: `backend/entities.py` (append `_consolidate_llm`, `build_entity_registry`)
- Test: `tests/test_entities.py` (append)

- [ ] **Step 1: Write the failing tests**

`tests/test_entities.py`에 추가:

```python
import json as _json
from backend import llm


def _write_scenes(tmp_path, scenes):
    (tmp_path / "scenes.json").write_text(
        _json.dumps({"scenes": scenes}, ensure_ascii=False), encoding="utf-8")


def _patch_llm(monkeypatch, ents):
    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(_json.dumps({"entities": ents}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)


def test_build_registry_consolidates_and_backlinks(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "characters": ["할머니"], "location": "거실", "props": []},
        {"sceneNumber": 2, "characters": ["할머니 캐릭터"], "location": "거실", "props": []},
    ])
    _patch_llm(monkeypatch, [
        {"id": "char-grandma", "type": "character", "name": "할머니",
         "aliases": ["할머니", "할머니 캐릭터"], "visual": {}, "first_scene": 1, "scenes": [1, 2]},
        {"id": "loc-living", "type": "location", "name": "거실",
         "aliases": ["거실"], "visual": {}, "first_scene": 1, "scenes": [1, 2]},
    ])
    r = entities.build_entity_registry(tmp_path)
    assert r["entities"] == 2 and r["scenes_updated"] == 2
    reg = _json.loads((tmp_path / "entities.json").read_text(encoding="utf-8"))
    assert len(reg["entities"]) == 2
    scenes = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert scenes[0]["character_ids"] == ["char-grandma"]
    assert scenes[1]["character_ids"] == ["char-grandma"]   # 표기 변형 → 같은 id
    assert scenes[0]["location_id"] == "loc-living"


def test_build_registry_fallback_on_llm_failure(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "characters": ["소년"], "location": "", "props": ["연필"]},
    ])
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = entities.build_entity_registry(tmp_path)
    assert r["entities"] == 2   # 소년 + 연필
    scenes = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert scenes[0]["character_ids"] == ["character-1"]
    assert scenes[0]["prop_ids"] == ["prop-1"]


def test_build_registry_no_occurrences(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [{"sceneNumber": 1, "characters": [], "location": "", "props": []}])
    called = []
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: called.append(1) or {"returncode": 0})
    r = entities.build_entity_registry(tmp_path)
    assert r == {"entities": 0, "scenes_updated": 0}
    assert not called   # LLM 미호출


def test_build_registry_no_scenes_errors(tmp_path):
    r = entities.build_entity_registry(tmp_path)
    assert r.get("error")


def test_build_registry_preserves_existing_fields(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "narration": "옛날 옛적", "layout": "cinematic",
         "characters": ["소년"], "location": "숲", "props": []},
    ])
    _patch_llm(monkeypatch, [
        {"id": "char-boy", "type": "character", "name": "소년", "aliases": ["소년"]},
        {"id": "loc-forest", "type": "location", "name": "숲", "aliases": ["숲"]},
    ])
    entities.build_entity_registry(tmp_path)
    s = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert s["narration"] == "옛날 옛적" and s["layout"] == "cinematic"
    assert s["characters"] == ["소년"]   # 원본 free-text 보존
    assert s["character_ids"] == ["char-boy"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: FAIL (AttributeError: module 'backend.entities' has no attribute 'build_entity_registry')

- [ ] **Step 3: Append orchestration to `backend/entities.py`**

```python
def _consolidate_llm(proj_dir: Path, occ: list, *, on_event=None) -> list:
    """entity-registry 스킬로 통합. 실패/파싱오류 시 []."""
    out = proj_dir / "entities_llm.json"
    occ_lines = "\n".join(f"- [{o['type']}] {o['raw']} (씬{o['scene']})" for o in occ)
    prompt = (
        _load_skill("entity-registry")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + "\n\n## 원고\n" + _read(proj_dir, "final_manuscript.md")
        + f"\n\n## 엔티티 출현({len(occ)}건)\n{occ_lines}\n\n"
        + "표기 변형을 통합하고 각 엔티티의 시각 명세를 합성해 entities JSON으로 출력."
    )
    if on_event:
        on_event(f"엔티티 통합 {len(occ)}건")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_ENTITY_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return []
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return list(data.get("entities") or [])
    except Exception:
        return []


def build_entity_registry(proj_dir, *, on_event=None) -> dict:
    """scenes.json 엔티티 태그를 정규화 레지스트리로 통합하고 씬에 ID 역링크.
    반환 {entities, scenes_updated} 또는 {error}."""
    proj_dir = Path(proj_dir)
    sp = proj_dir / "scenes.json"
    if not sp.is_file():
        return {"error": "scenes.json 필요 (씬 분석 먼저)"}
    try:
        doc = json.loads(sp.read_text(encoding="utf-8"))
        scenes = list(doc.get("scenes") or [])
    except Exception:
        return {"error": "scenes.json 파싱 실패"}

    occ = _gather_occurrences(scenes)
    if not occ:
        return {"entities": 0, "scenes_updated": 0}

    ents = _consolidate_llm(proj_dir, occ, on_event=on_event)
    if not ents:
        ents = _fallback_entities(occ)
        if on_event:
            on_event("엔티티 통합 폴백(결정적)")

    updated = _backlink_scenes(scenes, ents, on_event=on_event)

    (proj_dir / "entities.json").write_text(
        json.dumps({"entities": ents}, ensure_ascii=False, indent=2), encoding="utf-8")
    doc["scenes"] = scenes
    sp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_event:
        on_event(f"엔티티 레지스트리 — {len(ents)}개, 씬 {updated} 역링크")
    return {"entities": len(ents), "scenes_updated": updated}
```

- [ ] **Step 4: Run the full module test suite to verify pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_entities.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Run the WHOLE suite to confirm no regressions**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: PASS (509 passed, 1 skipped — 기존 497 passed + 12 신규)

- [ ] **Step 6: Commit**

```bash
git add backend/entities.py tests/test_entities.py
git commit -m "feat(s2a): build_entity_registry — LLM consolidation + deterministic fallback

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (작성자 점검 완료)

**Spec coverage:** 읽기/수집(Task2 `_gather_occurrences`·Task3 `build_entity_registry`) · LLM 통합(Task3 `_consolidate_llm`) · 폴백(Task2 `_fallback_entities`+Task3 분기) · 역링크(Task2 `_backlink_scenes`) · 스키마(Task1) · 스킬(Task1) · 에러처리(Task3 분기) · 테스트 6+종(Task1~3) — 스펙 전 항목 커버.

**Placeholder scan:** 없음 — 모든 코드 스텝에 완전한 코드 포함.

**Type consistency:** `build_entity_registry`/`_gather_occurrences`/`_fallback_entities`/`_alias_index`/`_backlink_scenes`/`_consolidate_llm` 시그니처가 Task 간 일치. 반환 키 `{entities, scenes_updated}`·`{error}` 일관. 씬 추가 필드 `character_ids`/`location_id`/`prop_ids` 일관.
