"""씬↔시트 첨부 렌더 (adobe 독립 Stage1-2 S2c) — scenes.json의 엔티티 ID를 entities.json의
시트로 해석해 씬 이미지를 시트 첨부로 일관 렌더. shot_relation=continue는 직전 씬도 첨부.
런타임 v3 의존 없음."""
from __future__ import annotations

import json
from pathlib import Path

from backend import imagegen
from backend import scenes as scenes_mod

_SUBDIR = "scenes"


def _entities_by_id(proj_dir: Path) -> dict:
    ep = proj_dir / "entities.json"
    if not ep.is_file():
        return {}
    try:
        ents = json.loads(ep.read_text(encoding="utf-8")).get("entities") or []
    except Exception:
        return {}
    return {e.get("id"): e for e in ents if e.get("id")}


def _sheet_rel(proj_dir: Path, ent) -> str:
    """엔티티의 sheet 경로(존재하는 파일만). 없으면 ''."""
    rel = str((ent or {}).get("sheet") or "").strip()
    if rel and (proj_dir / rel).is_file():
        return rel
    return ""


def resolve_scene_refs(scene, entities_by_id, proj_dir) -> dict:
    """씬의 character_ids/location_id/prop_ids → 존재하는 시트 rel(이름 동반).
    {character_sheets:[{rel,name}], location_sheet:{rel,name}|{}, prop_sheets:[{rel,name}]}."""
    proj_dir = Path(proj_dir)
    char_sheets = []
    for cid in (scene.get("character_ids") or []):
        ent = entities_by_id.get(cid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            char_sheets.append({"rel": rel, "name": (ent or {}).get("name") or cid})
    location_sheet = {}
    lid = scene.get("location_id")
    if lid:
        ent = entities_by_id.get(lid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            location_sheet = {"rel": rel, "name": (ent or {}).get("name") or lid}
    prop_sheets = []
    for pid in (scene.get("prop_ids") or []):
        ent = entities_by_id.get(pid)
        rel = _sheet_rel(proj_dir, ent)
        if rel:
            prop_sheets.append({"rel": rel, "name": (ent or {}).get("name") or pid})
    return {"character_sheets": char_sheets, "location_sheet": location_sheet,
            "prop_sheets": prop_sheets}


def build_scene_prompt(scene, descriptors, style_desc, rel_out, *, has_prev=False) -> str:
    """descriptors(첨부 순서와 일치)를 합쳐 씬 프롬프트 생성."""
    scene_desc = (scene.get("image_prompt") or scene.get("visual_summary")
                  or scene.get("narration") or "").strip()
    lines = "\n".join(f"- {d}" for d in descriptors)
    return (
        f"{style_desc}\n\n## 장면\n{scene_desc}\n\n"
        f"[첨부 이미지 — 순서대로]\n{lines}\n\n## 생성 지시\n"
        f"image_gen 도구로 위 아트스타일의 이미지 1장을 생성해 현재 폴더의 {rel_out} 로 저장.\n"
        f"첨부한 캐릭터·장소·소품 시트의 정체성을 그대로 유지(비율·형태를 새로 디자인하지 말 것). "
        f"비율을 텍스트로 새로 지정하지 말 것. 텍스트 없음. 저장되면 'OK'만 답해."
    )


def render_scenes(proj_dir, *, subdir=_SUBDIR, on_event=None) -> dict:
    """scenes.json의 각 씬을 시트 첨부로 순차 렌더 → scenes/scene_<n>.png + imageRef.
    continue 씬은 직전 렌더 씬도 첨부. 반환 {rendered, total, skipped}|{error}."""
    proj_dir = Path(proj_dir)
    sp = proj_dir / "scenes.json"
    if not sp.is_file():
        return {"error": "scenes.json 필요 (씬 분석 먼저)"}
    if not (proj_dir / "entities.json").is_file():
        return {"error": "entities.json 필요 (S2a 먼저)"}
    try:
        scene_list = json.loads(sp.read_text(encoding="utf-8")).get("scenes") or []
    except Exception:
        return {"error": "scenes.json 파싱 실패"}

    ents = _entities_by_id(proj_dir)
    base = imagegen.base_img()
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)

    rendered = 0
    skipped: list = []
    prev_rel = ""
    for sc in sorted(scene_list, key=lambda s: s.get("sceneNumber") or 0):
        sn = sc.get("sceneNumber")
        refs = resolve_scene_refs(sc, ents, proj_dir)
        images: list = []
        descriptors: list = []
        n = 1
        for cs in refs["character_sheets"]:
            images.append(str(proj_dir / cs["rel"]))
            descriptors.append(f"{n}번 캐릭터 시트 '{cs['name']}': 이 인물을 그대로 사용 — "
                               f"얼굴·눈 스타일·헤어·의상 동일, 그리고 등신 비율·키·체형도 시트와 "
                               f"정확히 같은 약 4등신 슬림 유지(사실적 성인 비율로 늘리지 말 것).")
            n += 1
        if refs["location_sheet"]:
            images.append(str(proj_dir / refs["location_sheet"]["rel"]))
            descriptors.append(f"{n}번 장소 시트 '{refs['location_sheet']['name']}': 이 장소를 배경으로 사용.")
            n += 1
        for ps in refs["prop_sheets"]:
            images.append(str(proj_dir / ps["rel"]))
            descriptors.append(f"{n}번 소품 시트 '{ps['name']}': 이 소품을 그대로 사용.")
            n += 1
        has_prev = sc.get("shot_relation") == "continue" and bool(prev_rel)
        if has_prev:
            images.append(str(proj_dir / prev_rel))
            descriptors.append(f"{n}번 직전 씬: 카메라·배경·톤이 이어지는 연속 장면 — "
                               f"구도가 자연스럽게 이어지게.")
            n += 1
        if not refs["character_sheets"]:
            descriptors.append("인물(사람)은 포함하지 말 것 — 배경/사물만.")
        if base:
            images.append(str(base))
            descriptors.append("마지막 세모지 베이스: 전체 그림체·색감 기준(베이스 인물 정체성 복사 금지).")

        out = imagegen.versioned_path(out_base, f"scene_{sn}.png")
        rel = out.relative_to(proj_dir).as_posix()
        prompt = build_scene_prompt(sc, descriptors, imagegen.load_style(), rel, has_prev=has_prev)
        if on_event:
            on_event(f"씬 {sn} 렌더 (첨부 {len(images)}장)")
        res = imagegen._run_codex_image(proj_dir, out, prompt, images=images or None, on_line=on_event)
        if res.get("status") == "completed":
            scenes_mod.set_image_ref(proj_dir, sn, rel)
            prev_rel = rel
            rendered += 1
        else:
            skipped.append({"scene": sn, "error": res.get("error")})
            if on_event:
                on_event(f"씬 {sn} 실패 — {res.get('error')}")

    if on_event:
        on_event(f"씬 렌더 완료 — {rendered}/{len(scene_list)}, skip {len(skipped)}")
    return {"rendered": rendered, "total": len(scene_list), "skipped": skipped}
