"""Adobe adapter for the shared video-track contract."""
import json
import sys
from pathlib import Path
# Adobe is also launched from adobe/ without installing the monorepo package.
_repo = str(Path(__file__).resolve().parents[2])
if _repo not in sys.path:
    sys.path.insert(0, _repo)
from auto_agent import video_tracks as shared
from backend import timeline

FILE_NAME = shared.FILE_NAME
SCHEMA_VERSION = shared.SCHEMA_VERSION
load = shared.load


def _timings(root, fps=30):
    if (Path(root) / "scene_specs.json").exists():
        return shared.project_timings(root, fps)
    from backend import scenes
    return timeline.scene_timings(root, scenes.load_scenes(root), fps=fps)


def save(proj_dir, data, *, expect_revision=None):
    checked = resolve(proj_dir, data)
    if checked["errors"]:
        return {"error": "트랙 검증 실패", "errors": checked["errors"]}
    return shared.save(proj_dir, data, expect_revision=expect_revision,
                       timings=_timings(proj_dir))


def resolve(proj_dir, data, *, fps=30):
    if not data.get("tracks") or data.get("error"):
        return shared.resolve(proj_dir, data, fps=fps)
    timings = _timings(proj_dir, fps)
    result = shared.resolve(proj_dir, data, fps=fps, timings=timings)
    path = Path(proj_dir) / "scenes.json"
    if (Path(proj_dir) / "scene_specs.json").exists() and path.exists():
        adobe = json.loads(path.read_text(encoding="utf-8")).get("scenes", [])
        if [s.get("sceneNumber") for s in adobe] != [s.get("sceneNumber") for s, _, _ in timings]:
            return {"clips": [], "covered": set(), "errors": ["Adobe/specs 씬 순서 불일치 — 동기화 필요"]}
        aliases = {a["sceneId"]: b["sceneId"] for (a, _, _), b in zip(timings, adobe)}
        result["covered"].update(aliases[s] for s in list(result["covered"]) if s in aliases)
    return result
