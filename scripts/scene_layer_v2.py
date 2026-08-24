"""scene-layer v2 — 단일 포즈 캐릭터 + 자산(로고/아이콘) 분리 생성.

⚠️ 대체됨 — 레이어 분리는 시드림 5.0(`scripts/animate_scene.py`)을 쓴다.
   이 스크립트는 codex imagegen으로 캐릭터를 다시 그려 분리했다. 시드림은
   **원본을 그대로 쪼개고** bbox와 인페인팅된 배경판까지 돌려주므로,
   다시 그리며 생기는 얼굴 흔들림이 없다. 옛 프로젝트 호환용으로만 남긴다.


v1 (scene_layer_animate.py) 차이:
- 캐릭터: 6포즈 그리드 → 단일 idle 포즈
- 자산: overlays.content의 logo_grid·source_caption 항목을 entity별 transparent PNG로
- layers.json: 자산 reveal 타임스탬프 포함 (motion_plan.overlay_reveals 매핑)

사용:
    python3 scripts/scene_layer_v2.py --project f793a99b --scene 1
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from scene_layer_animate import (
    _load_env, load_iromism, load_roster, gen_image, remove_chroma,
    style_block, build_background_prompt, resolve_project_dir,
)


def build_characters_from_existing_prompt(scene: dict, art_style: dict) -> str:
    """기존 씬 이미지의 인물(들)만 원래 포즈/위치 그대로 매젠타 배경에 분리."""
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        "**TASK — EXTRACT CHARACTERS, REMOVE BACKGROUND:**",
        "The reference image shows a scene with characters in specific poses. Keep ONLY the characters:",
        "- Same poses, same gestures, same facial expressions, same clothing — EXACTLY as drawn in reference",
        "- Same positions in the frame (do not recenter — keep the character where the reference placed it)",
        "- Same scale and proportions",
        "- If multiple characters, keep ALL of them in their original positions and poses",
        "",
        "**REPLACE BACKGROUND WITH MAGENTA:**",
        "- Solid magenta #FF00FF fills EVERYTHING except the characters themselves (chroma-key — will be removed)",
        "- No environment, no props, no furniture — only the character silhouettes",
        "- Remove ANY non-character object the characters were holding/touching unless it's part of their body/clothing",
        "",
        "**STYLE LOCK:**",
        "- 이로미즘 hand-drawn ink + flat colors — match reference style exactly",
        "- Do NOT redraw, redesign, restyle, or recompose the characters — copy them faithfully",
        "",
        "NO text, NO labels, NO logos.",
    ]
    return "\n\n".join(parts)


def build_bg_from_existing_prompt(scene: dict, art_style: dict) -> str:
    """기존 씬 이미지가 있을 때: 그 이미지의 구도·환경을 유지하고 인물만 제거."""
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        "**TASK — REMOVE CHARACTERS, PRESERVE EVERYTHING ELSE:**",
        "The reference image is the target scene. Keep the EXACT same:",
        "- Camera angle and framing",
        "- Background environment, walls, furniture, props, lighting",
        "- Color palette and overall composition",
        "- All non-character details (charts, signs, objects on tables, etc.)",
        "",
        "**REMOVE ONLY:**",
        "- All human figures / characters / people in the foreground or background",
        "- Replace their previous positions with the natural background that would be behind them",
        "  (continue the wall, floor, environment that was occluded by the characters)",
        "",
        "**KEEP IT AN EMPTY SET:**",
        "- The result is the SAME scene, same room, same composition — just empty of people, waiting for actors",
        "- 16:9 cinematic framing matching the reference",
        "",
        "**STYLE LOCK:**",
        "- 이로미즘 hand-drawn ink line + flat colors — match reference style exactly",
        "",
        "NO text, NO logos, NO captions.",
    ]
    return "\n\n".join(parts)


def build_single_pose_prompt(character: dict, art_style: dict, action_hint: str = "") -> str:
    name = character.get("name") or character.get("label", "character")
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        f"**SINGLE FULL-BODY POSE — {name}:**",
        f"Subject: {name}",
        f"Description: {character.get('description_en','')}",
        f"한국어 묘사: {character.get('description_ko','')}",
        f"Action hint: {action_hint}" if action_hint else "",
        "",
        "**LAYOUT:**",
        "- ONE single full-body character, standing centered, looking forward.",
        "- Arms relaxed at sides, neutral calm expression.",
        "- Magenta #FF00FF fills the entire background (chroma-key — will be removed to transparency).",
        "- Character fills ~70% of frame height, centered with safe magenta margin around.",
        "- Feet near bottom of frame (footing line), torso center on horizontal middle.",
        "",
        "**STYLE LOCK:**",
        "- 이로미즘 3-head stubby + UGLY-CUTE caricature + hand-drawn ink + flat colors",
        "",
        "NO text, NO labels, NO logos, NO frame borders.",
    ]
    return "\n\n".join(parts)


def build_asset_prompt(label: str, kind: str, art_style: dict) -> str:
    """단일 자산(로고·아이콘·차트요소) 생성 프롬프트.
    kind: logo | icon | chart_element
    """
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        f"**ISOLATED ASSET — {label} ({kind}):**",
    ]
    if kind == "logo":
        # 안전 필터 우회: 트레이드마크 명시적으로 회피, 일반 메모/뱃지 컨셉
        parts += [
            f"Subject: hand-lettered Korean-style ink badge that reads the text \"{label}\" — purely a typographic illustration.",
            "- Original hand-drawn lettering, NOT a copy or imitation of any company/brand/trademark logo.",
            "- Treat purely as a custom typographic decoration, like a 이로미즘 hand-painted notebook label.",
            "- Slight ink wobble, flat 1~2 color palette, no realistic effects.",
        ]
    elif kind == "icon":
        parts += [
            f"Subject: simple icon representing '{label}'.",
            "- Hand-drawn ink style, flat colors, recognizable silhouette.",
        ]
    else:
        parts += [
            f"Subject: simple chart/data element for '{label}'.",
            "- Hand-drawn flat illustration.",
        ]
    parts += [
        "",
        "**LAYOUT:**",
        "- Centered on solid magenta #FF00FF background (chroma-key — will be removed).",
        "- Generous magenta margin around the asset.",
        "- 이로미즘 hand-drawn ink + flat color style consistent with other scene assets.",
        "",
        "NO additional text, NO captions, NO frame borders.",
    ]
    return "\n\n".join(parts)


def collect_assets(scene: dict) -> list[dict]:
    """씬 overlays에서 분리 자산 후보 추출.
    반환: [{label, kind}], dedup.
    """
    assets, seen = [], set()
    ov = scene.get("overlays") or {}
    for c in ov.get("content", []) or []:
        t = c.get("type")
        if t == "logo_grid":
            for item in c.get("items", []):
                k = ("logo", item)
                if k not in seen:
                    assets.append({"label": item, "kind": "logo", "overlay_id": c.get("id")})
                    seen.add(k)
        elif t == "source_caption":
            for src in (c.get("sources") or [c.get("source")] if c.get("source") else []):
                if not src: continue
                k = ("logo", src)
                if k not in seen:
                    assets.append({"label": src, "kind": "logo", "overlay_id": c.get("id")})
                    seen.add(k)
    return assets


def get_reveal_timing(motion_plan: dict, scene_number: int, fps: int = 30) -> dict[str, list[float]]:
    """씬의 overlay_reveals → {overlay_id: [reveal_seconds, ...]}."""
    sc = next((s for s in motion_plan.get("transition_series", []) if s["scene_number"] == scene_number), None)
    if not sc: return {}
    reveals = sc.get("internal_timing", {}).get("overlay_reveals", []) or []
    out: dict[str, list[float]] = {}
    for r in reveals:
        target = r.get("target", "")  # e.g. "logo_grid:lg1"
        _, _, oid = target.partition(":")
        if not oid: continue
        out.setdefault(oid, []).append(round(r["at_frame"] / fps, 2))
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, required=True)
    p.add_argument("--skip-bg", action="store_true")
    p.add_argument("--skip-character", action="store_true")
    p.add_argument("--skip-extras", action="store_true")
    p.add_argument("--skip-assets", action="store_true", default=True)  # 기본 비활성
    args = p.parse_args()

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing", file=sys.stderr); sys.exit(1)

    pdir = resolve_project_dir(args.project)
    specs = json.loads((pdir / "scene_specs.json").read_text(encoding="utf-8"))
    scene = next((s for s in specs["scenes"] if s["sceneNumber"] == args.scene), None)
    if not scene:
        print(f"씬 {args.scene} 없음"); sys.exit(1)

    motion_plan = json.loads((pdir / "motion_plan.json").read_text(encoding="utf-8"))
    fps = motion_plan.get("fps", 30)
    art_style, ref = load_iromism()
    roster = load_roster(pdir)
    roster_full = json.loads((pdir / "characters" / "roster.json").read_text(encoding="utf-8"))
    cast_names = roster_full.get("scene_casts", {}).get(str(args.scene), []) or []
    extras_path = pdir / "scene_extras.json"
    extras_map = json.loads(extras_path.read_text(encoding="utf-8")) if extras_path.exists() else {}
    scene_extras = extras_map.get(str(args.scene), []) if not cast_names else []

    out_dir = pdir / "remotion" / "public" / "images" / f"scene_{args.scene:03d}_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_dir = pdir / "remotion" / "public" / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)  # 자산은 전 씬 공유

    CANVAS_W, CANVAS_H = 1920, 1080
    GEN_W, GEN_H = 3840, 2160  # 4K, 정확히 16:9, gpt-image-2 max 한도
    BG_W, BG_H = GEN_W, GEN_H  # 4K 원본 보존 (Remotion에서 줌인 가능)
    common_placement = {"x": 0, "y": 0, "width": CANVAS_W, "height": CANVAS_H}
    common_intrinsic = {"width": BG_W, "height": BG_H}
    GEN_SIZE = f"{GEN_W}x{GEN_H}"

    def _crop_to_1080(p: Path) -> None:
        # 4K 모드에서는 crop 불필요 (3840x2160은 정확히 16:9)
        pass

    layers = {
        "scene_number": args.scene,
        "canvas": {"width": CANVAS_W, "height": CANVAS_H},
        "fps": fps,
        "background": None,
        "characters": [],
        "assets": [],
    }

    # 1. 빈 배경 (기존 씬 이미지가 있으면 분위기 참조)
    if not args.skip_bg:
        print(f"\n=== Phase 1: 빈 배경 ===")
        bg_path = out_dir / "background.png"
        img_dir = pdir / "remotion" / "public" / "images"
        existing_scene = img_dir / f"scene_{args.scene:03d}.png"
        bg_refs = [ref] if ref else []
        if existing_scene.exists():
            bg_refs.append(existing_scene)
            print(f"  분위기 참조: {existing_scene.name}")
            bg_prompt = build_bg_from_existing_prompt(scene, art_style)
        else:
            bg_prompt = build_background_prompt(scene, art_style)
        t0 = time.time()
        ok, err = gen_image(bg_prompt, bg_path, ref_images=bg_refs, size=GEN_SIZE)
        if ok: _crop_to_1080(bg_path)
        print(f"  배경 {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:100]}")
        if ok:
            layers["background"] = {
                "src": f"scene_{args.scene:03d}_v2/background.png",
                "intrinsic_size": common_intrinsic,
                "placement": common_placement,
                "z": 0,
            }

    # 2. 기존 씬에서 인물 분리 — cast/extras 통합 (원래 포즈·위치 보존)
    if not args.skip_character:
        img_dir = pdir / "remotion" / "public" / "images"
        existing_scene = next((p for p in [img_dir / f"scene_{args.scene:03d}.png", img_dir / f"scene_{args.scene:03d}.jpg"] if p.exists()), None)
        if existing_scene:
            print(f"\n=== Phase 2: 인물 분리 ({'cast: '+', '.join(cast_names) if cast_names else 'extras'}) ===")
            char_refs = [existing_scene]
            # 캐스트 sheet도 외형 일관성 위해 첨부
            for cname in cast_names:
                char = roster.get(cname)
                if char and char.get("sheet_path"):
                    sh = pdir / char["sheet_path"]
                    if sh.exists(): char_refs.append(sh)
            sp = out_dir / "characters.png"
            t0 = time.time()
            ok, err = gen_image(
                build_characters_from_existing_prompt(scene, art_style),
                sp,
                ref_images=char_refs,
                size=GEN_SIZE, quality="medium",
            )
            print(f"  인물 분리 {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:100]}")
            if ok:
                _crop_to_1080(sp)
                removed = remove_chroma(sp)
                print(f"    chroma-key {'✓' if removed else '⚠'}")
                layers["characters"].append({
                    "name": "characters",
                    "cast": cast_names if cast_names else [],
                    "kind": "from_scene",
                    "src": f"scene_{args.scene:03d}_v2/{sp.name}",
                    "intrinsic_size": common_intrinsic,
                    "placement": common_placement,
                    "z": 10,
                    # 까딱임 — 반주기 10프레임 · 100 → 101 · ease-in-out.
                    # `amplitude_pct`/`period_s` 는 렌더러가 읽지 않는 이름이었다.
                    "motion": {"type": "feet_bob", "max_scale": 1.01,
                               "period_frames": 20},
                })
        else:
            print(f"\n  scene_{args.scene:03d}.png 없음 — 인물 분리 스킵")

    # (옛 Phase 2 단일 포즈 — 통합 후 미사용. 폴백용)
    if False and not args.skip_character:
        print(f"\n=== Phase 2: 단일 포즈 캐릭터 ({len(cast_names)}명) ===")
        for cname in cast_names:
            char = roster.get(cname)
            if not char: print(f"  {cname}: roster 없음 스킵"); continue
            sheet_path = pdir / char.get("sheet_path", "") if char.get("sheet_path") else None
            sp = out_dir / f"character_{cname.replace(' ','_')}.png"
            ref_imgs = [ref] if ref else []
            if sheet_path and sheet_path.exists(): ref_imgs.append(sheet_path)
            t0 = time.time()
            ok, err = gen_image(build_single_pose_prompt(char, art_style), sp,
                                ref_images=ref_imgs, size="1024x1024", quality="high")
            print(f"  {cname:14s} {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:80]}")
            if ok:
                removed = remove_chroma(sp)
                print(f"    chroma-key {'✓' if removed else '⚠'}")
                layers["characters"].append({
                    "name": cname,
                    "src": f"scene_{args.scene:03d}_v2/{sp.name}",
                    "anchor": {"x": 960, "y": 540, "origin": "feet_center"},
                    "scale": 1.0, "z": 10,
                    # 까딱임 — 반주기 10프레임 · 100 → 101 · ease-in-out.
                    # `amplitude_pct`/`period_s` 는 렌더러가 읽지 않는 이름이었다.
                    "motion": {"type": "feet_bob", "max_scale": 1.01,
                               "period_frames": 20},
                })

    # 3. 자산(로고·아이콘) — 공유 캐시
    if not args.skip_assets:
        timings = get_reveal_timing(motion_plan, args.scene, fps)
        candidates = collect_assets(scene)
        print(f"\n=== Phase 3: 자산 {len(candidates)}개 ===")
        for a in candidates:
            label, kind, oid = a["label"], a["kind"], a.get("overlay_id")
            safe = label.replace(" ", "_").replace("/", "_")
            ap = asset_dir / f"{kind}_{safe}.png"
            if not ap.exists():
                t0 = time.time()
                ok, err = gen_image(build_asset_prompt(label, kind, art_style), ap,
                                    ref_images=[ref] if ref else [],
                                    size="1024x1024", quality="medium")
                print(f"  {label:20s} ({kind}) {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:80]}")
                if ok:
                    remove_chroma(ap)
            else:
                print(f"  {label:20s} ({kind}) ↻ 캐시 재사용")
            if ap.exists():
                reveals = timings.get(oid, []) if oid else []
                layers["assets"].append({
                    "label": label, "kind": kind,
                    "src": f"assets/{ap.name}",
                    "reveal_at_s": reveals,
                    "anim": {"type": "overshoot_scale", "from": 0.0, "to": 1.0, "overshoot": 1.15, "duration_s": 0.35},
                    "z": 20,
                })

    layers_path = out_dir / "layers.json"
    layers_path.write_text(json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nlayers.json: {layers_path}")
    for f in sorted(out_dir.glob("*")):
        print(f"  {f.name} ({f.stat().st_size//1024}KB)")


if __name__ == "__main__":
    main()
