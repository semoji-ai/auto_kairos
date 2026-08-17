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
