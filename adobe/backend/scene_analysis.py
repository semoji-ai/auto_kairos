"""씬 분석 (adobe 독립 Stage1-2 P4b) — final_manuscript.md를 마커로 분할하고
씬별 연출(LLM)을 붙여 adobe 네이티브 scenes.json 산출. 런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import llm
from backend import scene_layouts as _scene_layouts

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
_SCENE_SCHEMA = _SCHEMAS / "scene_specs.schema.json"
_REVIEW_SCHEMA = _SCHEMAS / "scene_review.schema.json"
_LAYOUTS = _scene_layouts.KNOWN     # 목록은 scene_layouts가 단일 출처
_REL = {"cut", "continue"}

_SCENE_RE = re.compile(r"(?m)^[ \t]*<!--\s*SCENE\s*-->[ \t]*$")
_CHARS_RE = re.compile(r"(?m)^[ \t]*<!--\s*CHARS:\s*(.*?)\s*-->[ \t]*$")


def _load_skill(name: str) -> str:
    md = _SKILLS / name / "SKILL.md"
    if not md.is_file():
        return f"skill: {name}"
    text = md.read_text(encoding="utf-8")
    if text.startswith("---"):              # YAML frontmatter 제거(프롬프트 노이즈 방지)
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip("\n")
    return text


def _read(proj_dir: Path, name: str) -> str:
    p = proj_dir / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def split_manuscript(text: str) -> list:
    """<!--SCENE-->로 결정적 분할 → [{narration, characters}]. <!--CHARS-->는 추출·제거.
    마커 없으면 전체가 1씬. 빈 세그먼트는 버림."""
    segs: list = []
    for part in _SCENE_RE.split(text or ""):
        chars: list = []
        mm = _CHARS_RE.search(part)
        if mm:
            chars = [c.strip() for c in mm.group(1).split(",") if c.strip()]
            part = _CHARS_RE.sub("", part)
        narration = part.strip()
        if narration:
            segs.append({"narration": narration, "characters": chars})
    return segs


def _direct_scenes(proj_dir: Path, segments: list, *, on_event=None) -> list:
    """scene-analyze 스킬로 씬별 연출만 받음. 입력 순서 보존 리스트. 실패 시 []."""
    out = proj_dir / "scene_specs.json"
    narr = "\n\n".join(f"### 씬 {i + 1}\n{seg['narration']}" for i, seg in enumerate(segments))
    prompt = (
        _load_skill("scene-analyze")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + f"\n\n## 씬별 내레이션({len(segments)}개, 순서·개수 보존)\n{narr}\n\n"
        + "각 씬의 연출만 scene_specs JSON으로 출력(narration 미포함, 입력과 같은 개수·순서). "
        + f"project_id={proj_dir.name}."
    )
    if on_event:
        on_event(f"씬 연출 {len(segments)}개")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_SCENE_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return []
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return list(data.get("scenes") or [])
    except Exception:
        return []


def analyze_scenes(proj_dir, *, enrich: bool = True, on_event=None) -> dict:
    """final_manuscript.md → 마커 분할 + 연출 + 실사/생성 분류 → adobe scenes.json.
    enrich=True면 search 씬에 실사 1장을 검색·다운로드해 imageRef에 채움.
    반환 {scenes, count, searched} 또는 {error}."""
    proj_dir = Path(proj_dir)
    man = proj_dir / "final_manuscript.md"
    if not man.is_file():
        return {"error": "final_manuscript.md 필요 (P4a 먼저)"}
    segments = split_manuscript(man.read_text(encoding="utf-8"))
    if not segments:
        return {"error": "원고가 비어 있음"}

    directions = _direct_scenes(proj_dir, segments, on_event=on_event)
    specs = []
    for i, seg in enumerate(segments):
        d = directions[i] if i < len(directions) and isinstance(directions[i], dict) else {}
        chars = seg["characters"] or list(d.get("characters") or [])
        src = d.get("asset_source") if d.get("asset_source") in ("generate", "search") else "generate"
        specs.append({
            "sceneNumber": i + 1,
            "narration": seg["narration"],
            "visual_summary": str(d.get("visual_summary") or seg["narration"][:60]),
            "image_prompt": str(d.get("image_prompt") or ""),
            "characters": chars,
            "layout": d.get("layout"),
            "asset_source": src,
            "search_query": str(d.get("search_query") or ""),
            "shot_relation": d.get("shot_relation") if d.get("shot_relation") in ("cut", "continue") else "cut",
            "location": str(d.get("location") or ""),
            "props": list(d.get("props") or []),
        })

    from backend.v3_import import _map_scene
    from backend import scenes as scenes_mod
    adobe = []
    for s in specs:
        m = _map_scene(s)
        if s.get("layout"):
            m["layout"] = s["layout"]
        m["asset_source"] = s["asset_source"]
        if s.get("search_query"):
            m["search_query"] = s["search_query"]
        m["shot_relation"] = s["shot_relation"]
        if s.get("location"):
            m["location"] = s["location"]
        if s.get("props"):
            m["props"] = s["props"]
        adobe.append(m)
    (proj_dir / "scenes.json").write_text(
        json.dumps({"scenes": adobe}, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes_mod.ensure_scene_ids(proj_dir)

    searched = _enrich_real_assets(proj_dir, specs, on_event=on_event) if enrich else 0
    if on_event:
        on_event(f"씬 분석 완료 — {len(specs)}씬 (실사 {searched})")
    return {"scenes": str(proj_dir / "scenes.json"), "count": len(specs), "searched": searched}


def _enrich_real_assets(proj_dir: Path, specs: list, *, on_event=None) -> int:
    """asset_source=='search' 씬에 실사 1장 검색·다운로드 → imageRef. 실패는 격리. 붙은 수 반환."""
    from backend import search
    from backend import scenes as scenes_mod
    n = 0
    for s in specs:
        if (s.get("asset_source") or "generate") != "search":
            continue
        q = (s.get("search_query") or s.get("visual_summary") or "").strip()
        if not q:
            continue
        try:
            res = search.search_images(q, engine="serper")
            imgs = res.get("images") or []
            if not imgs:
                if on_event:
                    on_event(f"S{s['sceneNumber']} 실사 결과 없음: {q[:30]}")
                continue
            dl = search.save_image(proj_dir, imgs[0].get("url", ""), f"real_{s['sceneNumber']}.jpg")
            if dl.get("status") == "completed":
                scenes_mod.set_image_ref(proj_dir, s["sceneNumber"], dl["rel"])
                n += 1
                if on_event:
                    on_event(f"S{s['sceneNumber']} 실사: {q[:30]}")
        except Exception as e:  # noqa: BLE001 — 검색/다운로드 오류 격리(generate 폴백)
            if on_event:
                on_event(f"S{s['sceneNumber']} 실사 실패: {e}")
    return n


def _scene_det_checks(proj_dir: Path, scenes: list) -> dict:
    """결정적 씬 검토(LLM 무관) — issues 리스트 + 카운트."""
    from backend import brief as brief_mod
    issues: list = []
    n = len(scenes)
    for s in scenes:
        sn = s.get("sceneNumber")
        if not str(s.get("visual_summary") or "").strip():
            issues.append(f"씬{sn}: visual_summary 비어 있음")
        if s.get("layout") and s.get("layout") not in _LAYOUTS:
            issues.append(f"씬{sn}: layout 비표준값 '{s.get('layout')}'")
        if s.get("shot_relation") and s.get("shot_relation") not in _REL:
            issues.append(f"씬{sn}: shot_relation 비표준값 '{s.get('shot_relation')}'")
    if scenes and scenes[0].get("shot_relation") == "continue":
        issues.append("씬1: 첫 씬은 cut이어야 함(continue로 표시됨)")
    per_min = None
    try:
        dur = brief_mod.parse_plan(proj_dir).get("duration", "")
        m = re.search(r"(\d+)", str(dur or ""))
        mins = int(m.group(1)) if m else 0
        if mins > 0:
            per_min = round(n / mins, 1)
            if per_min < 2:
                issues.append(f"분당 씬 수 {per_min}로 너무 적음(2 미만)")
            elif per_min > 12:
                issues.append(f"분당 씬 수 {per_min}로 너무 많음(12 초과)")
    except Exception:
        per_min = None
    man = re.sub(r"<!--.*?-->", "", _read(proj_dir, "final_manuscript.md"))
    coverage = all(str(s.get("narration") or "")[:30] in man for s in scenes) if scenes else False
    if scenes and not coverage:
        issues.append("narration 커버리지 불완전(일부 씬 narration이 원고에 없음)")
    return {"scenes": n, "per_minute": per_min, "narration_coverage": coverage, "issues": issues}


def _review_scenes_llm(proj_dir: Path, scenes: list, *, on_event=None) -> dict:
    """scene-review 스킬로 레이아웃/연결성/엔티티 검토. 실패 시 {scenes:[], flags:[]}."""
    out = proj_dir / "scene_review_llm.json"
    summary = "\n".join(
        f"씬{s.get('sceneNumber')}: layout={s.get('layout')} shot_relation={s.get('shot_relation')} "
        f"chars={s.get('characters')} loc={s.get('location', '')} | {str(s.get('narration') or '')[:60]}"
        for s in scenes)
    prompt = (
        _load_skill("scene-review")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + f"\n\n## 씬 목록({len(scenes)}개)\n{summary}\n\n"
        + "scene_review JSON만 출력(scenes 평가 + flags + overall). 권고이며 자동 수정 아님."
    )
    if on_event:
        on_event("씬 검토(LLM)")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REVIEW_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return {"scenes": [], "flags": []}
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return {"scenes": list(data.get("scenes") or []), "flags": list(data.get("flags") or []),
                "overall": str(data.get("overall") or "")}
    except Exception:
        return {"scenes": [], "flags": []}


def review_scenes(proj_dir, *, on_event=None) -> dict:
    """scenes.json을 검토해 advisory 리포트 scene_review.json 산출(래칫 없음).
    반환 {report, flags, det_issues} 또는 {error}."""
    proj_dir = Path(proj_dir)
    sp = proj_dir / "scenes.json"
    if not sp.is_file():
        return {"error": "scenes.json 필요 (씬 분석 먼저)"}
    if not (proj_dir / "final_manuscript.md").is_file():
        return {"error": "final_manuscript.md 필요"}
    try:
        scenes = json.loads(sp.read_text(encoding="utf-8")).get("scenes") or []
    except Exception:
        return {"error": "scenes.json 파싱 실패"}
    det = _scene_det_checks(proj_dir, scenes)
    rv = _review_scenes_llm(proj_dir, scenes, on_event=on_event)
    report = {
        "overall": str(rv.get("overall") or ""),
        "deterministic": det,
        "scenes": list(rv.get("scenes") or []),
        "flags": list(rv.get("flags") or []),
    }
    (proj_dir / "scene_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_event:
        on_event(f"씬 검토 — flags {len(report['flags'])}, det_issues {len(det['issues'])}")
    return {"report": str(proj_dir / "scene_review.json"),
            "flags": len(report["flags"]), "det_issues": len(det["issues"])}
