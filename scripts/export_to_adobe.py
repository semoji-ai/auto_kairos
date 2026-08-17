#!/usr/bin/env python3
"""v3에서 만든 편을 auto_kairos_adobe 프로젝트로 넘긴다.

**렌더링은 Remotion이 아니라 After Effects로 간다.** v3는 씬 분할까지의 강점이
있고(원고 래칫, 실물 자료 관문, 화풍 재정비), 그 뒤 모션·합성은 adobe 패널이
맡는다. 두 곳을 잇는 것이 이 스크립트다.

    v3                                   adobe
    scene_specs.json  ─────────────────▶  scenes.json
    images/ (선택된 것)  ────────────────▶  storyboard/sb_<sceneId>.png
    audio/*.mp3       ─────────────────▶  audio/tts_<sceneId>.mp3
    _imggen/characters/final_v2_up ────▶  characters/

adobe가 이어받는 것: 레이어 분리 → 모션 계획 → ae_manifest → JSX 빌드.
그래서 여기서는 **레이어를 나누지 않는다.** 통짜 씬 이미지를 넘기고,
분리는 adobe의 fal 경로가 한다(전역 규칙의 레이어 분리 예외).

    python3 scripts/export_to_adobe.py EP01
    python3 scripts/export_to_adobe.py EP01 --name lg_ep01 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ADOBE_ROOT = Path.home() / "LocalProjects" / "auto_kairos_adobe" / "projects"


# v3는 헤드라인에 {{1936}}처럼 강조 마커를 쓴다. adobe에는 렌더러가 없으니
# 그대로 넘기면 화면에 중괄호가 박힌다.
ACCENT = re.compile(r"\{\{([^}]*)\}\}")


def plain(t: str | None) -> str:
    return ACCENT.sub(r"\1", t or "").strip()


def summarize(s: dict, ia: dict) -> str:
    """무엇을 그린 화면인지 한 줄. 헤드라인 복사는 설명이 되지 않는다."""
    if ia.get("moment"):
        return plain(ia["moment"])
    narr = plain(s.get("narration")).replace("\n", " ")
    first = re.split(r"(?<=[.!?])\s", narr)[0] if narr else ""
    return (first[:80] or plain(s.get("headline")))


def scene_id(s: dict, n: int) -> str:
    """adobe는 sceneId로 파일을 잇는다. v3에 있으면 그대로, 없으면 번호로 만든다."""
    return str(s.get("sceneId") or f"s{n:03d}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--name", help="adobe 프로젝트 폴더 이름 (기본: lg_<ep 소문자>)")
    ap.add_argument("--in-place", action="store_true",
                    help="복사하지 않고 v3 프로젝트 폴더에 scenes.json만 쓴다 (권장)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    key = next((k for k in emap if k.startswith(args.ep)), None)
    if not key:
        print(f"  {args.ep}: ep_map에 없음")
        return 1
    D = Path(emap[key]["dir"])
    # 복사본을 만들면 원본이 갱신될 때 어긋난다. 12편에 2.1GB가 중복됐다.
    # 제자리에 쓰고 adobe는 AK_PROJECTS_ROOT로 이 폴더를 직접 본다.
    out = D if args.in_place else ADOBE_ROOT / (args.name or f"lg_{args.ep.lower()}")

    specs = json.loads((D / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = specs["scenes"]

    # 길이는 실측 오디오가 정한다. scene_specs의 예상치는 비어 있는 경우가 많다.
    dur: dict[int, float] = {}
    apath: dict[int, Path] = {}
    man = Path("/Volumes/jleavens/Projects/auto_kairos_v3/remotion/public/manifests") / f"{D.name}.json"
    if man.exists():
        md = json.loads(man.read_text(encoding="utf-8"))
        for x in (md.get("manifest") or md).get("scenes", []):
            if x.get("audioDurationSec"):
                dur[x["sceneNumber"]] = round(float(x["audioDurationSec"]), 2)
            # scene_specs를 재생성하면 sceneId가 바뀌어 오디오 파일명과 어긋난다.
            # 매니페스트는 그때 실제로 이어 붙인 경로를 들고 있다.
            if x.get("audioPath"):
                apath[x["sceneNumber"]] = Path(str(x["audioPath"]).split("project/", 1)[-1])

    db_path = D / "images" / "image_assets.json"
    sel = {}
    if db_path.exists():
        for e in json.loads(db_path.read_text(encoding="utf-8"))["scenes"]:
            f = next((i["file"] for i in e["images"] if i.get("selected")), None)
            if f:
                sel[e["sceneNumber"]] = f

    rows, n_img, n_audio = [], 0, 0
    for s in scenes:
        n = s["sceneNumber"]
        sid = scene_id(s, n)
        ia = s.get("imageAsset") or {}
        row = {
            "sceneNumber": n,
            "sceneId": sid,
            "section": s.get("chapter"),
            "title": plain(s.get("headline")) or None,
            "narration": plain(s.get("narration")),
            # adobe는 characters를 이름 목록으로 쓴다. v3의 cast(시트 id)와
            # people(무명 배역 서술)을 합쳐 넘긴다 — 레이어 분리에서 인물을 찾는 근거.
            "characters": list(s.get("cast") or []) + list(s.get("people") or []),
            "visual_summary": summarize(s, ia),
            "image_prompt": ia.get("prompt") or "",
            "duration_estimate_sec": dur.get(n) or s.get("durationSec") or s.get("duration"),
            # 레이아웃·수치는 adobe의 텍스트 레이어가 쓴다
            "layout": s.get("layout"),
            "items": [plain(x) for x in (s.get("items") or [])] or None,
            "values": s.get("values"),
            "unit": s.get("unit"),
            "badge": s.get("badge"),
            "attribution": s.get("attribution"),
            "attributionStatus": s.get("attributionStatus"),
            "assetSource": ia.get("source"),
        }
        if sel.get(n):
            row["imageRef"] = (f"images/{sel[n]}" if args.in_place
                               else f"storyboard/sb_{sid}.png")
            n_img += 1
        audio = D / apath[n] if n in apath else D / "audio" / f"{sid}.mp3"
        if not audio.exists():
            audio = D / "audio" / f"scene_{n:03d}.mp3"
        if audio.exists():
            row["audioRef"] = (str(audio.relative_to(D)) if args.in_place
                               else f"audio/tts_{sid}.mp3")
            n_audio += 1
        rows.append(row)

    payload = {
        "version": "v3-bridge/1",
        "project_id": out.name,
        "topic": key,
        "source_project": str(D),
        "total_scenes": len(rows),
        "scenes": rows,
    }

    print(f"  {args.ep} → {out}")
    print(f"    씬 {len(rows)} / 이미지 {n_img} / 오디오 {n_audio}")
    if args.dry_run:
        print("    [dry-run]")
        return 0

    if args.in_place:
        (out / "scenes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
        print(f"    ✓ scenes.json 제자리 생성 (자산 복사 없음)")
        return 0

    for sub in ("storyboard", "audio", "characters"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    for s in scenes:
        n = s["sceneNumber"]
        sid = scene_id(s, n)
        if sel.get(n):
            shutil.copy2(D / "images" / sel[n], out / "storyboard" / f"sb_{sid}.png")
        a = D / apath[n] if n in apath else D / "audio" / f"{sid}.mp3"
        if not a.exists():
            a = D / "audio" / f"scene_{n:03d}.mp3"
        if a.exists():
            shutil.copy2(a, out / "audio" / f"tts_{sid}.mp3")

    # 인물 시트 — adobe가 레이어 분리·재생성에서 얼굴 근거로 쓴다
    sheets = root / "_imggen" / "characters" / "final_v2_up"
    if sheets.exists():
        for p in sheets.glob("*_sheet.png"):
            shutil.copy2(p, out / "characters" / p.name)

    (out / "scenes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    for f in ("final_manuscript.md",):
        if (D / f).exists():
            shutil.copy2(D / f, out / f)

    print(f"    ✓ scenes.json + storyboard {n_img} + audio {n_audio}"
          f" + 시트 {len(list((out / 'characters').glob('*.png')))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
