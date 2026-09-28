#!/usr/bin/env python3
"""Apply audited, native-size source insert layouts to selected scene images."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from auto_agent.tools.image_assets import get_selected


def apply(project: Path, audit: Path, *, write: bool = False) -> int:
    specs_path = project / "scene_specs.json"
    data = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes = {scene["sceneNumber"]: scene for scene in data["scenes"]}
    records = json.loads(audit.read_text(encoding="utf-8"))["scenes"]
    seen: set[int] = set()
    for record in records:
        number = record["sceneNumber"]
        if number in seen or number not in scenes:
            raise ValueError(f"Duplicate or missing scene: {number}")
        seen.add(number)
        selected = get_selected(project / "images", number)
        if selected != record["selected_file"]:
            raise ValueError(f"Selected image changed in S{number}: {selected!r}")
        native = record["native_pixels"]
        rect = record["proposed_insert_1920x1080"]
        image = project / "images" / selected
        if not image.is_file():
            raise FileNotFoundError(image)
        if rect["source_crop"] or rect["width"] > native["width"] or rect["height"] > native["height"]:
            raise ValueError(f"Crop or upscale in S{number}")
        if min(rect["x"], rect["y"], rect["width"], rect["height"]) < 0:
            raise ValueError(f"Negative insert coordinate in S{number}")
        if rect["x"] + rect["width"] > 1920 or rect["y"] + rect["height"] > 780:
            raise ValueError(f"Insert outside subtitle-safe region in S{number}")
        asset = scenes[number].setdefault("imageAsset", {})
        asset["placement"] = "source_insert"
        asset["insert"] = {key: rect[key] for key in ("x", "y", "width", "height")}
        asset["nativePixels"] = native
    if write:
        specs_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(seen)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    count = apply(args.project, args.audit, write=args.write)
    print(f"Validated {count} source inserts" + (" and applied" if args.write else " (dry run)"))
