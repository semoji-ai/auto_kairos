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
    """베이스 캐릭터 시트(1번 첨부)를 기준으로 새 캐릭터 시트 생성(사용자 확정 공식).
    1번에서 유지: 그림체·눈 스타일·등신 비율·레이아웃. 바꾸는 것: 헤어·의상·인상만.
    참조 [[feedback_codex_image_generation_cli_rule]]."""
    looks = _looks_from_visual(visual)
    exprs = ", ".join(str(e) for e in (visual or {}).get("expressions") or []) or "기본 표정들"
    return (
        f"1번 이미지는 다음 4가지의 절대 기준이다(반드시 1번을 따른다): "
        f"①플랫 세모지 일러스트 그림체, "
        f"②얼굴 이목구비 스타일(작고 단순한 점 같은 세모지 눈 + 볼터치 — 눈을 크게 키우거나 "
        f"애니메풍으로 바꾸지 말 것), "
        f"③1번과 정확히 동일한 등신 비율·키·체형(머리가 약간 크고 몸은 슬림하되 키가 짧은 약 4등신 — "
        f"사실적 성인 비율로 늘리지 말 것, 통통하게도 만들지 말 것), "
        f"④시트 레이아웃(전신 턴어라운드 정면·측면·후면 + 얼굴 클로즈업 + 표정 5컷). "
        f"바꾸는 것은 오직 헤어(모양·색)·의상·전체 인상(성별·연령)뿐: '{name}' — {looks}. "
        f"표정 칸 정서: {exprs}. 글자 없음."
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
        size = "1536x1024"
    elif etype == "location":
        prompt = build_location_sheet_prompt(name, visual, rel)
        images = [str(imagegen.base_img())] if imagegen.base_img() else None
        size = "1536x1024"
    else:
        prompt = build_prop_sheet_prompt(name, visual, rel)
        images = [str(imagegen.base_img())] if imagegen.base_img() else None
        size = "1024x1024"

    res = imagegen._run_codex_image(proj_dir, out, prompt, images=images, on_line=on_line, size=size)
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
