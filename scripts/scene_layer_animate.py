"""scene-layer-animate Phase 1+2 시범 — 1씬에 대해 배경/캐릭터 sprite/소품 분리 생성.

사용:
    python3 scripts/scene_layer_animate.py --project f793a99b --scene 35
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_GEN_CLI = Path("/Users/jleavens_macmini/.codex/skills/.system/imagegen/scripts/image_gen.py")
CHROMA_CLI = Path("/Users/jleavens_macmini/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py")


def _load_env() -> None:
    env_p = ROOT / ".env"
    if not env_p.exists(): return
    for line in env_p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def resolve_project_dir(project_arg: str) -> Path:
    """프로젝트 디렉토리 해석 — v3 (output/<uuid>_<slug>/) + v4 (projects/<id>/) 호환.

    macOS 파일시스템 NFD 한글 정규화 차이를 위해 NFC/NFD 양방향 비교.

    우선순위:
      1. 절대경로
      2. v4: ROOT/projects/<arg>
      3. v3: ROOT/output/<arg>
      4. v3 slug 검색: NFC/NFD 양방향
    """
    import unicodedata
    p = Path(project_arg)
    if p.is_absolute() and p.exists():
        return p
    v4 = ROOT / "projects" / project_arg
    if v4.exists():
        return v4
    v3_root = ROOT / "output"
    v3_exact = v3_root / project_arg
    if v3_exact.exists():
        return v3_exact
    # NFC/NFD 정규화 양쪽 시도 (macOS 한글)
    nfc = unicodedata.normalize("NFC", project_arg)
    nfd = unicodedata.normalize("NFD", project_arg)
    if v3_root.exists():
        for entry in v3_root.iterdir():
            entry_nfc = unicodedata.normalize("NFC", entry.name)
            entry_nfd = unicodedata.normalize("NFD", entry.name)
            for needle in (nfc, nfd):
                if (
                    entry_nfc.endswith(f"_{needle}")
                    or entry_nfd.endswith(f"_{needle}")
                    or entry_nfc.startswith(f"{needle}_")
                    or entry_nfd.startswith(f"{needle}_")
                ):
                    return entry
    raise FileNotFoundError(f"project not found in projects/ or output/: {project_arg}")


def load_iromism():
    # semoji-animating 스킬 분기 — v4 에서 다시 설정한 art style 우선 사용.
    # v3 의 일반 파이프라인 art style 과 분리되어 있어, 영상 톤을 v4 디자인 결정에 맞춤.
    # 우선순위:
    #   1. v3 styles_v4/iromism.json (v4 art style 이식본)
    #   2. v3 styles_v4/quirky_cartoon.json (이로미즘 == quirky_cartoon 폴백)
    #   3. v3 styles/quirky_cartoon.json (일반 v3 폴백 — 최후 수단)
    #   4. v4 원본 data/artstyle/styles/iromism.json (legacy)
    v3_v4_dir = ROOT / "auto_agent" / "data" / "artstyle" / "styles_v4"
    candidates = [
        v3_v4_dir / "iromism.json",
        v3_v4_dir / "quirky_cartoon.json",
        ROOT / "auto_agent" / "data" / "artstyle" / "styles" / "quirky_cartoon.json",
        ROOT / "data" / "artstyle" / "styles" / "iromism.json",
    ]
    p = next((c for c in candidates if c.exists()), None)
    if p is None:
        raise FileNotFoundError("iromism/quirky_cartoon art style not found")
    d = json.loads(p.read_text(encoding="utf-8"))
    ref_rel = d.get("reference_image", "")
    # ref 후보: 같은 디렉토리 내, 또는 ROOT/data 기준
    ref_candidates = [
        p.parent / Path(ref_rel).name,
        p.parent.parent / Path(ref_rel).name,
        ROOT / "data" / ref_rel,
        ROOT / "auto_agent" / "data" / ref_rel,
    ]
    ref = next((c for c in ref_candidates if c.exists()), None)
    return d, ref


def load_roster(pdir: Path) -> dict:
    rp = pdir / "characters" / "roster.json"
    if not rp.exists(): return {}
    d = json.loads(rp.read_text(encoding="utf-8"))
    return {c["name"]: c for c in d.get("characters", [])}


def gen_image(prompt: str, out: Path, ref_images: list[Path], size: str = "1536x1024", quality: str = "medium") -> tuple[bool, str]:
    cmd = ["python3", str(IMAGE_GEN_CLI)]
    img_args = []
    for r in ref_images:
        if r and r.exists():
            img_args += ["--image", str(r)]
    if img_args:
        cmd += ["edit"] + img_args
    else:
        cmd += ["generate"]
    cmd += [
        "--prompt", prompt,
        "--no-augment",
        "--size", size,
        "--quality", quality,
        "--output-format", "png",
        "--out", str(out),
        "--force",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            return (True, "")
        return (False, (r.stderr or r.stdout)[-300:])
    except Exception as e:
        return (False, str(e))


def remove_chroma(img: Path, key_color: str = "#FF00FF") -> bool:
    """remove_chroma_key.py 호출.

    원본은 *_raw.png 로 보존(재처리 가능). auto-key/despill 사용 안 함 —
    피부 분홍·옷 자홍 톤이 키로 잘못 잡혀 얼굴/몸에 구멍이 생기는 사례가 있음.
    """
    if not CHROMA_CLI.exists():
        return False
    raw = img.with_name(img.stem + "_raw.png")
    if not raw.exists():
        # 원본 백업 (한 번만)
        try:
            raw.write_bytes(img.read_bytes())
        except Exception:
            pass
    try:
        r = subprocess.run(
            [
                "python3", str(CHROMA_CLI),
                "--input", str(raw),
                "--out", str(img),
                "--key-color", key_color,
                "--tolerance", "40",
                "--soft-matte",
                "--transparent-threshold", "30",
                "--opaque-threshold", "80",
                "--force",
            ],
            capture_output=True, text=True, timeout=60
        )
        return r.returncode == 0
    except Exception:
        return False


def style_block(art_style: dict) -> str:
    return json.dumps({
        "name": art_style.get("name"),
        "scene_style_description": art_style.get("scene_style_description"),
        "technical": art_style.get("technical"),
    }, ensure_ascii=False)


def build_background_prompt(scene: dict, art_style: dict) -> str:
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        "**SCENE BACKGROUND ONLY:**",
        f"Scene context: {scene.get('title','')} ({scene.get('section','')})",
        f"Narration context: {scene.get('narration','')[:250]}",
        f"Entities/locations: {', '.join(str(e) for e in (scene.get('entities') or [])[:5])}",
        "",
        "**CRITICAL — BACKGROUND ONLY, NO CHARACTERS, NO PROPS:**",
        "- Generate ONLY the empty environment/setting for this scene.",
        "- ABSOLUTELY NO PEOPLE, NO HUMAN FIGURES, NO CHARACTERS, NO ANIMALS in the image.",
        "- ABSOLUTELY NO FOREGROUND PROPS that would normally be held/used by a person.",
        "- Just the empty room, landscape, or environment as if waiting for actors.",
        "- 16:9 cinematic framing.",
        "",
        "**STYLE LOCK:**",
        "- 이로미즘 hand-drawn ink line + flat colors + simple shapes",
        "- Same drawing technique throughout (no realistic photo, no painterly)",
        "",
        "NO text, NO logos, NO captions.",
    ]
    return "\n\n".join(parts)


def build_sprite_prompt(character: dict, art_style: dict) -> str:
    name = character["name"]
    desc_en = character.get("description_en", "")
    desc_ko = character.get("description_ko", "")
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        f"**CHARACTER 2×3 GRID SPRITE SHEET — {name}:**",
        f"Subject: {name}",
        f"Description: {desc_en}",
        f"한국어 묘사: {desc_ko}",
        "",
        "**SPRITE SHEET LAYOUT (CRITICAL):**",
        "- Output is a 2-row × 3-column GRID of six poses (1024×1024 total → each frame is roughly 341×512).",
        "- Reading order top-left → top-right → middle row left → right → bottom-left → bottom-right (rows of 3).",
        "- Each frame shows the SAME character with the SAME outfit, SAME hairstyle, SAME proportions.",
        "- Magenta #FF00FF fills the entire background (chroma-key — will be removed to transparency).",
        "",
        "**6 POSES (in reading order — VARIED, not identical flipbook):**",
        "  1. IDLE — standing neutral, looking forward, arms relaxed at sides, calm expression",
        "  2. BLINK — IDENTICAL to pose 1 in body/arms/clothing, ONLY the eyes close (blinking)",
        "  3. HEAD TILT — body unchanged, ONLY the head tilts slightly to one side (curious look)",
        "  4. HAND ON CHIN — one hand raised to the chin (thinking/interested), other arm still at side",
        "  5. ONE HAND POINT — one arm raised pointing forward in emphasis (the OTHER arm stays relaxed at side)",
        "  6. BOTH HANDS UP — both hands raised at chest/shoulder height in surprise/reaction, eyes wide",
        "",
        "**BODY CENTER ANCHOR (VERY IMPORTANT for smooth animation):**",
        "- The character's TORSO CENTER must be at the EXACT HORIZONTAL CENTER of each frame box.",
        "- The character's FEET must be at the SAME VERTICAL POSITION (same baseline) in every frame.",
        "- Across all 6 poses, the body silhouette stays anchored at the same place — only eyes/mouth/arms change.",
        "- Poses 1, 2, 3 share the SAME body/arms — only eyes (pose 2) or head angle (pose 3) change.",
        "- Poses 4, 5, 6 add arm motion but feet positions and outfit stay identical to pose 1.",
        "- ABSOLUTELY NO part of the character (arm, hand, gesture, hair) extends BEYOND its own frame box into neighboring frames or into frame edges.",
        "- Leave generous magenta margin around the character within each frame — the character should fill ~70% of frame height, centered with safe padding.",
        "",
        "**STYLE LOCK:**",
        "- 이로미즘 3-head stubby + UGLY-CUTE caricature + hand-drawn ink + flat colors",
        "- All 6 poses identical character — only the specified pose differences",
        "",
        "NO text, NO labels under poses, NO frame borders/dividers/lines drawn, NO logos. Pure clean sprite grid.",
    ]
    return "\n\n".join(parts)


def build_prop_prompt(prop_label: str, prop_desc: str, art_style: dict) -> str:
    parts = [
        "**ART STYLE (must follow strictly):**",
        style_block(art_style),
        "",
        f"**ISOLATED PROP — {prop_label}:**",
        f"Description: {prop_desc}",
        "",
        "**LAYOUT:**",
        "- Single prop centered, no character, no environment, no background detail.",
        "- Background: solid magenta #FF00FF (chroma-key — will be removed).",
        "- Prop drawn in 이로미즘 hand-drawn ink + flat color style.",
        "",
        "NO text, NO logos.",
    ]
    return "\n\n".join(parts)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--scene", type=int, required=True)
    args = p.parse_args()

    _load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY missing", file=sys.stderr); sys.exit(1)

    pdir = resolve_project_dir(args.project)
    specs = json.loads((pdir / "scene_specs.json").read_text(encoding="utf-8"))
    scene = next((s for s in specs["scenes"] if s["sceneNumber"] == args.scene), None)
    if not scene:
        print(f"씬 {args.scene} 없음"); sys.exit(1)

    art_style, ref = load_iromism()
    roster = load_roster(pdir)

    # 씬 cast
    roster_full = json.loads((pdir / "characters" / "roster.json").read_text(encoding="utf-8"))
    cast_names = roster_full.get("scene_casts", {}).get(str(args.scene), []) \
                  or roster_full.get("scene_casts", {}).get(args.scene, [])

    out_dir = pdir / "remotion" / "public" / "images" / f"scene_{args.scene:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    layers = {
        "scene_number": args.scene,
        "canvas": {"width": 1920, "height": 1080},
        "background": None,
        "characters": [],
        "props": [],
    }

    # 1. 배경
    print(f"\n=== Phase 1: 배경 생성 ===")
    bg_path = out_dir / "background.png"
    t0 = time.time()
    ok, err = gen_image(build_background_prompt(scene, art_style), bg_path, ref_images=[ref] if ref else [], size="1536x1024")
    print(f"  배경 {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:100]}")
    if ok:
        layers["background"] = {"src": f"scene_{args.scene:03d}/background.png", "z": 0}

    # 2. 캐릭터 sprite (cast)
    print(f"\n=== Phase 2: 캐릭터 sprite stripe (cast {len(cast_names)}명) ===")
    for cname in cast_names:
        char = roster.get(cname)
        if not char:
            print(f"  {cname}: roster 없음 스킵"); continue
        sheet_path = pdir / char.get("sheet_path", "") if char.get("sheet_path") else None
        sprite_path = out_dir / f"character_{cname.replace(' ','_')}_sprite.png"
        ref_imgs = [ref] if ref else []
        if sheet_path and sheet_path.exists():
            ref_imgs.append(sheet_path)
        t0 = time.time()
        ok, err = gen_image(
            build_sprite_prompt(char, art_style),
            sprite_path,
            ref_images=ref_imgs,
            size="1024x1024",  # 2x3 그리드
            quality="high",
        )
        print(f"  {cname:14s} sprite {'✓' if ok else '✗'} ({round(time.time()-t0,1)}s) {err[:80]}")
        if ok:
            # chroma key 제거
            print(f"    chroma-key 제거 중...")
            removed = remove_chroma(sprite_path)
            print(f"    {'✓' if removed else '⚠'} chroma key removal")
            layers["characters"].append({
                "name": cname,
                "sprite_src": f"scene_{args.scene:03d}/{sprite_path.name}",
                "sprite_frames": 6,
                "sprite_layout": "grid_2x3",  # 2 rows × 3 cols
                "frame_size": {"width": 1024 // 3, "height": 1024 // 2},  # ~341 × 512
                "frame_order": "row_major",  # 0,1,2 (top row), 3,4,5 (bottom row)
                "anchor": {"x": 960, "y": 540},
                "scale": 1.0,
                "z": 10,
                "default_pose": 0,
                "blink_poses": [0, 1],
                "head_tilt_pose": 2,
                "thinking_pose": 3,
                "point_pose": 4,
                "react_pose": 5,
                "chroma_key_removed": removed,
            })

    # layers.json 저장
    layers_path = out_dir / "layers.json"
    layers_path.write_text(json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nlayers.json: {layers_path}")
    print(f"디렉토리: {out_dir}")
    for f in sorted(out_dir.glob("*")):
        print(f"  {f.name} ({f.stat().st_size//1024}KB)")


if __name__ == "__main__":
    main()
