"""
오디오 파일을 scene_NNN.mp3 → {sceneId}.mp3 방식으로 마이그레이션.

먼저 shift 수정이 필요한 경우 --fix-shift 옵션으로 scene_NNN → scene_N+1 rename 먼저 실행.
그 후 sceneId 기반으로 rename.

사용:
    python3 -m auto_agent.tools.migrate_audio_to_scene_id <project_dir> [--fix-shift <from_scene>] [--dry-run]
"""
import json
import sys
from pathlib import Path


def fix_shift(audio_dir: Path, from_scene: int, max_scene: int, dry_run: bool):
    """scene_NNN.mp3 파일을 from_scene~max_scene 범위에서 +1 shift."""
    print(f"[shift] scene_{from_scene:03d} ~ scene_{max_scene:03d} → +1 rename")
    for n in range(max_scene, from_scene - 1, -1):
        for suffix in [".mp3", ".timestamps.json"]:
            src = audio_dir / f"scene_{n:03d}{suffix}"
            dst = audio_dir / f"scene_{n+1:03d}{suffix}"
            if src.exists():
                print(f"  {'[DRY]' if dry_run else ''} {src.name} → {dst.name}")
                if not dry_run:
                    src.rename(dst)


def migrate_to_scene_id(project_dir: Path, dry_run: bool):
    """scene_NNN.mp3 → {sceneId}.mp3 rename."""
    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        print(f"ERROR: scene_specs.json 없음 ({project_dir})")
        return

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes = specs.get("scenes", [])
    audio_dir = project_dir / "audio"

    print(f"\n[migrate] {project_dir.name}: {len(scenes)}씬")
    renamed = 0
    skipped = 0
    missing = 0

    for scene in scenes:
        num = scene.get("sceneNumber", 0)
        scene_id = scene.get("sceneId", "")
        if not scene_id:
            print(f"  씬{num:03d}: sceneId 없음 — SKIP")
            skipped += 1
            continue

        for suffix in [".mp3", ".timestamps.json"]:
            src = audio_dir / f"scene_{num:03d}{suffix}"
            dst = audio_dir / f"{scene_id}{suffix}"
            if dst.exists():
                # 이미 sceneId 방식으로 존재
                skipped += 1
                continue
            if src.exists():
                print(f"  {'[DRY]' if dry_run else ''} {src.name} → {dst.name}")
                if not dry_run:
                    src.rename(dst)
                renamed += 1
            else:
                if suffix == ".mp3" and scene.get("narration", "").strip():
                    print(f"  씬{num:03d} ({scene_id}): {suffix} 없음 — TTS 생성 필요")
                    missing += 1

    print(f"\n결과: rename {renamed}, skip {skipped}, TTS필요 {missing}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("Usage: migrate_audio_to_scene_id <project_dir> [--fix-shift <from>] [--dry-run]")
        sys.exit(1)

    project_dir = Path(args[0])
    dry_run = "--dry-run" in args
    fix_shift_from = None

    for i, a in enumerate(args):
        if a == "--fix-shift" and i + 1 < len(args):
            fix_shift_from = int(args[i + 1])

    audio_dir = project_dir / "audio"

    if fix_shift_from is not None:
        # max 씬 번호 파악
        max_n = fix_shift_from
        for f in audio_dir.glob("scene_*.mp3"):
            try:
                n = int(f.stem.split("_")[1])
                max_n = max(max_n, n)
            except (IndexError, ValueError):
                pass
        fix_shift(audio_dir, fix_shift_from, max_n, dry_run)

    migrate_to_scene_id(project_dir, dry_run)
