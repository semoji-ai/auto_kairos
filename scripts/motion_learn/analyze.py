"""gemini 동영상이해 → motion.json(컷·프리셋) + new_presets.json(신규 후보).
gemini는 기존 프리셋 카탈로그를 받아 가능한 건 매핑, 안 되는 건 후보 제안."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.motion_learn import state


def _gemini_analyze(mp4_path: str, lib_keys: list[str]) -> dict:
    """gemini 동영상이해 → {cuts, new_presets}. gemini_client에 위임."""
    from scripts.motion_learn import gemini_client
    prompt = (
        "이 모션그래픽 영상을 After Effects 컴프로 재현할 JSON으로만 출력(순수 JSON).\n"
        "모션은 가능한 한 아래 기존 프리셋명으로 매핑: " + json.dumps(lib_keys, ensure_ascii=False) + "\n"
        "기존으로 표현 안 되는 모션은 new_presets에 후보로 제안: "
        "{name(snake_case), props(opacity/scale/position/rotationY/trimEnd/textOffset 우선), ease, params, why}.\n"
        "출력: {\"cuts\":[{type,start,dur,bg,layers:[{type,text,color,font,x,y,w,h,"
        "anim:[{preset,t0,dur,params}]}]}], \"new_presets\":[...]}\n순수 JSON만."
    )
    return gemini_client.analyze_video(mp4_path, prompt)


def analyze(slug: str, refs_dir: Path, lib_path: Path) -> dict:
    """refs/{slug}.mp4 분석 → refs/{slug}/motion.json + new_presets.json. 반환 {cuts, new_preset_count}."""
    ref_dir = refs_dir / slug
    mp4 = refs_dir / (slug + ".mp4")
    lib_keys = list(json.loads(lib_path.read_text(encoding="utf-8")).get("presets", {}).keys())
    data = _gemini_analyze(str(mp4), lib_keys)
    cuts = data.get("cuts", [])
    new_presets = data.get("new_presets", [])
    (ref_dir / "motion.json").write_text(json.dumps({"cuts": cuts}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ref_dir / "new_presets.json").write_text(json.dumps(new_presets, ensure_ascii=False, indent=2), encoding="utf-8")
    state.set_stage(ref_dir, "analyzed", {"cut_count": len(cuts), "new_preset_count": len(new_presets)})
    return {"cuts": len(cuts), "new_preset_count": len(new_presets)}
