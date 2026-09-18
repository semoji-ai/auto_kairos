"""Prepare a disabled track draft from an existing cutlist and download ledger.

No file writes and no paid generation. Redirect/capture stdout for review.
File matching uses ledger IDs (never guessed filenames); media must be inside
the project. Technical validation does not approve image quality or internal cuts.
"""
import argparse
import json
from pathlib import Path
from auto_agent import video_tracks as vt


def prepare(root: Path, cutlist: dict, downloads: list) -> dict:
    root = root.resolve()
    timings = vt.project_timings(root)
    scenes = {s["sceneId"]: s for s, _, _ in timings}
    ledger = {row["id"]: row for row in downloads}
    clips, audit = [], []
    for unit in cutlist["units"]:
        uid = unit["id"]
        row = ledger.get(uid)
        if not row:
            audit.append({"clipId": uid, "errors": ["다운로드 원장에 없음"]})
            continue
        # Only use the ledger's basename inside the intended project directory;
        # this also permits a reviewed ledger to travel between Mac/NAS machines.
        source = root / "video_sources" / Path(row["path"]).name
        sids = [shot["sceneId"] for shot in unit["shots"]]
        clip = dict(clipId=uid, enabled=True, sourcePath=source.relative_to(root).as_posix(),
                    sceneIds=sids, anchor={"sceneId": sids[0], "offsetFrames": 0},
                    sourceInSec=0, sourceOutSec=vt.media_duration(source) if source.is_file() else 0,
                    playbackRate=1, audioPolicy="mute")
        trial = {"schemaVersion": 1, "tracks": [{"trackId": "primary-video", "clips": [clip]}]}
        check = vt.resolve(root, trial, timings=timings)
        warnings = [w for c in check["clips"] for w in c.get("warnings", [])]
        for shot in unit["shots"]:
            current = scenes.get(shot["sceneId"], {})
            if shot.get("narration") != current.get("narration"):
                warnings.append(f"S{shot.get('sceneNumber')}: 생성 당시 원고와 현재 원고 대조 필요")
        clip.update(enabled=False, status="needs_visual_and_timing_review")
        clips.append(clip)
        audit.append({"clipId": uid, "errors": check["errors"], "warnings": warnings})
    return {"data": {"schemaVersion": 1, "revision": 0,
                     "tracks": [{"trackId": "primary-video", "enabled": True, "clips": clips}]},
            "audit": audit, "note": "비활성 초안. 원본 내용·내부 컷·TTS 검수 후 UI/API에서 명시적으로 활성화."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--cutlist", required=True, type=Path)
    parser.add_argument("--downloads", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.project, json.loads(args.cutlist.read_text()),
                             json.loads(args.downloads.read_text())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
