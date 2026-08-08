#!/usr/bin/env python3
"""채점표를 코드로 구현한다 — 매 편 똑같이 깎이는 항목을 데이터에서 유도해 채운다.

**깨달음.** EP01을 95점까지 올리는 데 밤을 다 썼는데, EP02·EP07을 채점하니
깎이는 항목이 글자 그대로 같았다. 편마다 손으로 고칠 일이 아니다.
네 항목 모두 이미 scene_specs 안에 답이 있다.

| 감점 항목 | 배점 | 유도 근거 |
|---|---:|---|
| 결정적 순간 (keyVisual) | 12 | `beat` — hook/turn/climax/close가 서사의 정점이다 |
| 숫자 시각화율 | 15 | 나레이션의 수치 + `cinematicOverlay`(그림을 살린 채 숫자를 띄운다) |
| 지도·차트 활용 | 10 | 지명 + 이동 동사 → `mapScene` |
| 페이싱 | 10 | 나레이션 길이 → 초 환산(412자/분), 12초 넘으면 정적 모션을 바꾼다 |

`apply_direction_fixes.py`(배지·레이아웃 정렬)와 짝을 이룬다. 그쪽이 신뢰도를,
이쪽이 지식 전달과 재미를 담당한다.

    python3 scripts/rubric_autofill.py <project_dir> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ElevenLabs semoji 보이스 실측치 (docs 참조)
CHARS_PER_MIN = 412
HOLD_LIMIT_SEC = 12.0

NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억원|만원|조원|억|만|원|달러|퍼센트|%|배|위|"
                 r"명|개|대|가마|필|년|개월|일|시간|분|초|mm|cm|kg|톤|건|종|곳|위안|엔)")

# 화면에 수치·항목을 띄울 수 있는 레이아웃
CAN_SHOW = {"counter", "metric_spotlight", "metric_wall", "bar", "bar_horizontal", "pie",
            "donut", "line", "icon_stat", "annotated_chart", "timeline", "items_list",
            "items_grid", "split", "before_after", "flow", "comparison_table",
            "headline_only", "quote_portrait"}

# 지리 이동 — 지명이 둘 이상이고 이동을 뜻하는 말이 있으면 지도가 필요하다
PLACES = {
    "진주": [35.1800, 128.1076], "부산": [35.1796, 129.0756], "서울": [37.5665, 126.9780],
    "구미": [36.1195, 128.3446], "창원": [35.2280, 128.6811], "평택": [36.9921, 127.1129],
    "파주": [37.7599, 126.7800], "청주": [36.6424, 127.4890], "울산": [35.5384, 129.3114],
    "대전": [36.3504, 127.3845], "광주": [35.1595, 126.8526], "인천": [37.4563, 126.7052],
    "미국": [38.9072, -77.0369], "중국": [39.9042, 116.4074], "일본": [35.6762, 139.6503],
    "영국": [51.5074, -0.1278], "유럽": [50.8503, 4.3517], "인도": [28.6139, 77.2090],
    "폴란드": [52.2297, 21.0122], "베트남": [21.0278, 105.8342], "브라질": [-15.79, -47.88],
    "독일": [52.5200, 13.4050], "프랑스": [48.8566, 2.3522], "러시아": [55.7558, 37.6173],
}
OVERSEAS = {"미국","중국","일본","영국","유럽","인도","폴란드","베트남","브라질",
            "독일","프랑스","러시아"}
MOVE = re.compile(r"(진출|수출|이전|옮기|건너|나가|들어가|공략|상륙|확장|철수|물러나|향[해했]|떠나|출시|판매)")

ITEM_LAYOUTS = {"items_list", "items_grid", "timeline", "flow", "split", "before_after",
                "comparison_table", "rank_list", "card_carousel"}
METRIC_ONLY = {"counter", "metric_spotlight", "metric_wall", "bar", "bar_horizontal",
               "pie", "donut", "line", "icon_stat"}

# 정적인 모션 — 12초를 넘기면 화면이 멈춘 것처럼 보인다
STATIC_MOTION = {"fade_rise", "calm_float", "cinematic_fade", None, ""}
DYNAMIC_FOR = {
    "cinematic": "ken_burns", "timeline": "build_sequence", "items_list": "stagger_wave",
    "items_grid": "stagger_wave", "flow": "build_sequence", "split": "split_compare",
    "before_after": "split_compare", "metric_wall": "count_and_grow",
    "metric_spotlight": "number_spotlight", "counter": "count_and_grow",
}


def fill_keyvisual(scenes: list[dict]) -> list[int]:
    """서사의 정점에 keyVisual을 세운다 — beat가 이미 답을 갖고 있다."""
    if any(s.get("keyVisual") for s in scenes):
        return []
    picked = []
    for beat in ("hook", "turn", "climax", "close"):
        cands = [s for s in scenes if s.get("beat") == beat]
        if not cands:
            continue
        # 같은 beat가 여럿이면 나레이션이 가장 실한 씬을 고른다
        best = max(cands, key=lambda s: len(s.get("narration") or ""))
        best["keyVisual"] = True
        picked.append(best["sceneNumber"])
    return picked


def _on_screen(scene: dict) -> str:
    parts = [str(scene.get("headline") or "")]
    parts += [str(i) for i in (scene.get("items") or [])]
    parts += [str(v) for v in (scene.get("values") or [])]
    ov = scene.get("cinematicOverlay") or {}
    parts.append(str(ov.get("text") or ""))
    return re.sub(r"[,\s]", "", " ".join(parts))


# 날짜와 수치를 통째로 잡는다 — '2006년 5월', '1억 70만 대', '11.8밀리미터'
PHRASE = re.compile(
    r"\d[\d,]*(?:\.\d+)?\s*년\s*\d{1,2}\s*월(?:\s*\d{1,2}\s*일)?"      # 2007년 1월 18일
    r"|\d[\d,]*(?:\.\d+)?\s*억\s*\d[\d,]*\s*만\s*대"                   # 1억 70만 대
    r"|\d[\d,]*(?:\.\d+)?\s*(?:만|억|조)?\s*"
    r"(?:달러|원|대|명|개|건|톤|위|배|퍼센트|%|밀리미터|mm|cm|kg|년|개월|일|초|분|곳|종)"
)


def _on_screen(scene: dict) -> str:
    parts = [str(scene.get("headline") or "")]
    parts += [str(i) for i in (scene.get("items") or [])]
    parts += [str(v) for v in (scene.get("values") or [])]
    ov = scene.get("cinematicOverlay") or {}
    parts.append(str(ov.get("text") or ""))
    return re.sub(r"[,\s]", "", " ".join(parts))


def _digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s)


def align_values_items(scene: dict) -> str | None:
    """values와 items의 개수를 맞춘다.

    metric 계열은 values[i]와 items[i]를 짝지어 카드를 만든다. 개수가 어긋나면
    라벨 없는 숫자나 숫자 없는 라벨이 뜬다. 연도와 수량이 한 unit을 공유하면
    '2009만 대'처럼 읽힌다 — 그때는 unit을 비우고 라벨에 단위를 넣는다.
    """
    vals = scene.get("values") or []
    items = list(scene.get("items") or [])
    if not vals:
        return None
    note = None
    # 연도(1900~2100)와 수량이 섞이면 공통 단위를 쓸 수 없다
    years = [v for v in vals if isinstance(v, (int, float)) and 1900 <= v <= 2100]
    if years and len(years) < len(vals) and scene.get("unit"):
        scene["unit"] = ""
        note = "연도·수량 혼재 → 단위를 라벨로"
    if len(items) != len(vals):
        if len(items) < len(vals):
            items += [""] * (len(vals) - len(items))
        else:
            items = items[:len(vals)]
        scene["items"] = items
        note = (note + "; " if note else "") + f"items {len(vals)}개로 정렬"
    return note


def fill_numbers(scene: dict) -> str | None:
    """나레이션의 수치를 화면에 올린다 — 단위까지 통째로.

    채점은 단위까지 화면에 있어야 인정한다. '1만'만으로는 '1만 달러'가 아니고,
    '2006년'만으로는 '2006년 5월'이 아니다. 그리고 values에 끼워 넣으면 unit이
    어긋나므로, **표기는 items나 오버레이 같은 문자열 자리에만 넣는다.**
    """
    phrases = [re.sub(r"\s+", " ", m.group(0)).strip()
               for m in PHRASE.finditer(scene.get("narration") or "")]
    if not phrases:
        return None
    screen = _on_screen(scene)
    missing = [p for p in phrases
               if _digits(p) not in screen or re.sub(r"[\d,.\s]", "", p) not in screen]
    if not missing:
        return None
    text = missing[0]
    layout = scene.get("layout")

    if layout == "cinematic":
        # 그림을 살린 채 숫자를 띄운다
        scene["cinematicOverlay"] = {"type": "caption", "text": text, "position": "bottom"}
    elif layout in ITEM_LAYOUTS or layout in METRIC_ONLY:
        items = list(scene.get("items") or [])
        vals = scene.get("values") or []
        if vals and len(items) >= len(vals):
            # 짝을 깨지 않도록 기존 라벨에 덧붙인다
            items[0] = f"{text} · {items[0]}" if items[0] else text
        else:
            items.insert(0, text)
        scene["items"] = items[:6]
    else:
        h = scene.get("headline") or ""
        scene["headline"] = f"{{{{{text}}}}}\n{h}" if h else f"{{{{{text}}}}}"
    return f"{scene['sceneNumber']}:{text}"


def fill_mapscene(scene: dict) -> str | None:
    """지명이 둘 이상이고 이동을 뜻하는 말이 있으면 지도를 붙인다."""
    if scene.get("mapScene"):
        return None
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    if not MOVE.search(text):
        return None
    # 나레이션에 나온 순서가 이동 순서다
    hits = sorted((p for p in PLACES if p in text), key=text.index)
    # 해외로 나가는 이야기는 출발지(한국)를 적지 않는 경우가 많다
    if len(hits) == 1 and hits[0] in OVERSEAS:
        hits = ["서울"] + hits
    if len(hits) < 2:
        return None
    scene["mapScene"] = {
        "mode": "route",
        "route": [{"label": p, "at": PLACES[p]} for p in hits[:4]],
        "focus": None,
    }
    if scene.get("motion") in STATIC_MOTION:
        scene["motion"] = "map_reveal"
    return " → ".join(hits[:4])


def audio_seconds(project: Path, scene: dict) -> float | None:
    """생성된 TTS의 실제 길이. 추정보다 이쪽이 진실이다."""
    sid = scene.get("sceneId")
    for name in ([f"{sid}.mp3"] if sid else []) + [f"scene_{scene.get('sceneNumber'):03d}.mp3"]:
        f = project / "audio" / name
        if f.exists():
            # MP3 128kbps 기준 — ffprobe 없이 크기로 환산한다
            return round(f.stat().st_size * 8 / 128000, 1)
    return None


def fill_pacing(scene: dict, project: Path | None = None) -> tuple[float, str | None]:
    """씬 길이를 확정하고, 12초를 넘는 정적 씬에 움직임을 준다.

    TTS가 있으면 실측을, 없으면 나레이션 길이로 추정한다.
    채점의 페이싱 항목은 실제 길이를 봐야 검증된다.
    """
    real = audio_seconds(project, scene) if project else None
    if real is not None:
        sec = real
        scene["durationSec"] = sec
        scene.pop("estimatedDurationSec", None)
    else:
        n = len(re.sub(r"\s", "", scene.get("narration") or ""))
        sec = round(n / CHARS_PER_MIN * 60, 1)
        scene["estimatedDurationSec"] = sec
    if sec <= HOLD_LIMIT_SEC or scene.get("motion") not in STATIC_MOTION:
        return sec, None
    want = DYNAMIC_FOR.get(scene.get("layout"))
    if not want:
        return sec, None
    old = scene.get("motion")
    scene["motion"] = want
    return sec, f"{old}→{want}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    kv = fill_keyvisual(scenes)
    ov, mp, pace, fixed = [], [], [], []
    total = 0.0
    for s in scenes:
        t = fill_numbers(s)
        if t:
            ov.append(t)
        a = align_values_items(s)
        if a:
            fixed.append(f"{s['sceneNumber']} {a}")
        r = fill_mapscene(s)
        if r:
            mp.append(f"{s['sceneNumber']} {r}")
        sec, ch = fill_pacing(s, args.project)
        total += sec
        if ch:
            pace.append(f"{s['sceneNumber']} {ch}")

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.project.name}" + (" [dry-run]" if args.dry_run else ""))
    print(f"    keyVisual   {kv or '이미 있음'}")
    print(f"    숫자 표기   {len(ov)}씬  {', '.join(ov[:5])}")
    print(f"    짝 정렬     {len(fixed)}씬")
    print(f"    지도        {len(mp)}씬  {'; '.join(mp[:3])}")
    print(f"    모션 보강    {len(pace)}씬 (12초 초과 정적)")
    real = sum(1 for s in scenes if s.get("durationSec"))
    print(f"    길이        {total/60:.1f}분 (실측 {real}/{len(scenes)}씬)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
