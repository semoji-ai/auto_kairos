"""Shared, file-backed multi-scene video contract. No provider/LLM dependency.

All consumers use integer-frame timings. Existing projects without this file
retain their old timing policy. Original assets and scripts are never rewritten.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

FILE_NAME = "video_tracks.json"
SCHEMA_VERSION = 1


def load(root: Path) -> dict:
    path = Path(root) / FILE_NAME
    if not path.exists():
        return {"schemaVersion": 1, "revision": 0, "tracks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("object required")
        return data
    except (ValueError, OSError):
        return {"schemaVersion": 1, "revision": 0, "tracks": [], "error": "비디오 트랙 JSON 읽기 실패"}


@lru_cache(maxsize=1024)
def _probe(path: str, size: int, mtime: int) -> float:
    if Path(path).suffix.lower() == ".mp3":
        try:
            from mutagen.mp3 import MP3
            return float(MP3(path).info.length)
        except Exception:
            pass
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=nw=1:nk=1", path], capture_output=True,
                           text=True, timeout=15, check=True)
        d = float(r.stdout.strip())
        return d if math.isfinite(d) and d > 0 else 0
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def media_duration(path: Path) -> float:
    st = path.stat()
    return _probe(str(path.resolve()), st.st_size, st.st_mtime_ns)


def project_timings(root: Path, fps: float = 30) -> list:
    """Read-only canonical timeline; specs IDs win, no implicit ID migrations."""
    root = Path(root)
    path = root / "scene_specs.json"
    if not path.exists():
        path = root / "scenes.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    result, frame = [], 0
    for scene in data.get("scenes", []):
        sid = scene.get("sceneId")
        if not sid:
            raise ValueError("씬 ID가 없어 트랙 시간 기준을 만들 수 없습니다")
        audio = root / "audio" / f"{sid}.mp3"
        saved = root / (scene.get("_audio") or "__missing__")
        if not audio.is_file() and saved.is_file() and root.resolve() in saved.resolve().parents:
            audio = saved
        scene = dict(scene)
        if audio.is_file():
            st = audio.stat()
            scene["_trackAudioIdentity"] = [audio.name, st.st_size, st.st_mtime_ns]
        duration = media_duration(audio) if audio.is_file() else 0
        if audio.is_file() and not duration:
            raise ValueError(f"오디오 길이 검증 실패: {sid}")
        if not duration:
            duration = (scene.get("durationFrames", 0) / data.get("meta", {}).get("fps", fps)
                        or scene.get("duration_estimate_sec") or 3)
        if not math.isfinite(float(duration)) or float(duration) <= 0:
            raise ValueError(f"잘못된 씬 길이: {sid}")
        n = max(1, math.ceil(round(float(duration) * fps, 6)))
        result.append((scene, frame / fps, n / fps))
        frame += n
    return result


def fingerprint(timings: list, fps: float) -> str:
    rows = [(s["sceneId"], round(start * fps), round(d * fps),
             s.get("narration_tts") or s.get("narration") or "",
             s.get("_trackAudioIdentity")) for s, start, d in timings]
    return hashlib.sha256(json.dumps([fps, rows], ensure_ascii=False).encode()).hexdigest()


def resolve(root: Path, data: dict, *, fps: float = 30, timings: list | None = None) -> dict:
    root = Path(root).resolve()
    clips, errors, covered, spans = [], [], set(), []
    result = {"clips": clips, "errors": errors, "covered": covered}
    if data.get("error"):
        errors.append(data["error"])
        return result
    if data.get("schemaVersion", 1) != 1 or not isinstance(data.get("tracks", []), list):
        errors.append("지원하지 않는 트랙 계약")
        return result
    if not data.get("tracks"):
        return result
    try:
        timings = timings if timings is not None else project_timings(root, fps)
        stamp = fingerprint(timings, fps)
    except (ValueError, OSError, KeyError, TypeError) as e:
        errors.append(str(e))
        return result
    result["timelineFingerprint"] = stamp
    idx = {s["sceneId"]: (i, start, d) for i, (s, start, d) in enumerate(timings)}
    if len(idx) != len(timings):
        errors.append("중복 씬 ID")
        return result
    ids = set()
    for track in data.get("tracks", []):
        if not isinstance(track, dict) or not isinstance(track.get("clips", []), list):
            errors.append("잘못된 트랙 구조")
            continue
        tid = track.get("trackId") or "primary-video"
        for c in track.get("clips", []):
            try:
                cid = c["clipId"]
                if not isinstance(cid, str) or not cid or cid in ids:
                    raise ValueError("중복/빈 clipId")
                ids.add(cid)
                if not track.get("enabled", True) or not c.get("enabled", True):
                    continue
                if c.get("timelineFingerprint") and c["timelineFingerprint"] != stamp:
                    raise ValueError("씬 순서·TTS·길이 변경 — 타이밍 재검토 필요")
                rel = c.get("sourcePath", "")
                src = (root / rel).resolve()
                if Path(rel).is_absolute() or root not in src.parents:
                    raise ValueError("원본이 프로젝트 밖")
                if not rel or not src.is_file():
                    raise ValueError("원본 없음")
                sids = c.get("sceneIds") or []
                if not isinstance(sids, list) or not sids or any(not isinstance(s, str) or s not in idx for s in sids):
                    raise ValueError("없는 씬 ID 또는 빈 범위")
                orders = [idx[s][0] for s in sids]
                if orders != list(range(orders[0], orders[0] + len(orders))):
                    raise ValueError("씬 범위가 연속이 아님 또는 순서가 뒤집힘")
                anchor = c.get("anchor") or {}
                if not isinstance(anchor, dict):
                    raise ValueError("anchor는 object여야 함")
                if anchor.get("sceneId", sids[0]) != sids[0]:
                    raise ValueError("앵커는 범위 첫 씬이어야 함")
                off = anchor.get("offsetFrames", 0)
                if not isinstance(off, int) or isinstance(off, bool) or off < 0:
                    raise ValueError("offsetFrames는 0 이상의 정수")
                sin, sout = float(c.get("sourceInSec", 0)), float(c["sourceOutSec"])
                rate = float(c.get("playbackRate", 1))
                if not all(math.isfinite(x) for x in [sin, sout, rate]) or sin < 0 or sout <= sin:
                    raise ValueError("잘못된 원본 구간")
                if rate != 1:
                    raise ValueError("공통 MVP는 playbackRate=1만 지원")
                if c.get("audioPolicy", "mute") != "mute":
                    raise ValueError("공통 MVP는 무음 영상만 지원")
                length = media_duration(src)
                if not length or sout > length + 0.001:
                    raise ValueError("원본 길이 초과 또는 ffprobe 검증 실패")
                start = round(idx[sids[0]][1] * fps) + off
                end = round((idx[sids[-1]][1] + idx[sids[-1]][2]) * fps)
                available = math.floor(round((sout - sin) * fps, 6))
                duration = min(end - start, available)
                if duration < 1:
                    raise ValueError("재생 범위가 비어 있음")
                if any(start < b and a < start + duration for a, b in spans):
                    raise ValueError("다른 클립과 겹침 — MVP 단일 화면만 지원")
                spans.append((start, start + duration))
                warnings = []
                if available != end - start:
                    warnings.append("범위 끝에서 원본을 자름" if available > end - start
                                    else "원본이 짧음 — 남는 구간은 기존 씬 화면")
                # Only fully covered scenes suppress their old video; partial tails keep fallback.
                covered.update(s for s in sids if start <= round(idx[s][1] * fps)
                               and start + duration >= round((idx[s][1] + idx[s][2]) * fps))
                clips.append({"clipId": cid, "trackId": tid, "sourcePath": str(src),
                              "sceneIds": sids, "start": start / fps, "duration": duration / fps,
                              "timelineStartFrame": start, "timelineDurationFrames": duration,
                              "sourceIn": sin, "sourceOut": sin + duration / fps,
                              "playbackRate": 1, "muted": True,
                              **({"warnings": warnings} if warnings else {})})
            except (ValueError, TypeError, KeyError, OSError) as e:
                errors.append(f"[{tid}/{c.get('clipId', '?') if isinstance(c, dict) else '?'}] {e}")
    return result


@contextmanager
def _lock(root: Path):
    # Cross-process compare-and-swap, including Adobe and dashboard processes.
    fp = (root / ".video_tracks.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            fp.write(b"0"); fp.flush(); fp.seek(0)
            msvcrt.locking(fp.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(fp, fcntl.LOCK_EX)
        yield
    finally:
        fp.close()


def save(root: Path, data: dict, *, expect_revision: int | None = None, timings=None) -> dict:
    root = Path(root)
    with _lock(root):
        cur = load(root)
        if cur.get("error"):
            return {"error": cur["error"]}
        if expect_revision is None or cur.get("revision", 0) != expect_revision:
            return {"error": "revision 충돌 — 다시 불러오세요", "revision": cur.get("revision", 0)}
        r = resolve(root, data, timings=timings)
        if r["errors"]:
            return {"error": "트랙 검증 실패", "errors": r["errors"]}
        data = json.loads(json.dumps(data))
        data.update(schemaVersion=1, revision=expect_revision + 1)
        for tr in data.get("tracks", []):
            for c in tr.get("clips", []):
                if tr.get("enabled", True) and c.get("enabled", True):
                    c["timelineFingerprint"] = r["timelineFingerprint"]
        fd, name = tempfile.mkstemp(prefix=".video_tracks-", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush(); os.fsync(f.fileno())
            os.replace(name, root / FILE_NAME)
        finally:
            if Path(name).exists():
                Path(name).unlink()
        return {"ok": True, "revision": data["revision"]}


def attach_manifest(root: Path, manifest: dict) -> None:
    """Attach once to full timeline; scene slices are only for isolated previews."""
    if not (Path(root) / FILE_NAME).exists():
        return
    fps = manifest["meta"]["fps"]
    timings = project_timings(root, fps)
    r = resolve(root, load(root), fps=fps, timings=timings)
    manifest["videoClipErrors"] = r["errors"]
    manifest["videoClips"] = []
    for c in r["clips"]:
        manifest["videoClips"].append({**c, "sourcePath": "project/" + Path(c["sourcePath"]).relative_to(Path(root).resolve()).as_posix()})
    by_num = {s["sceneNumber"]: (s, start, d) for s, start, d in timings}
    for s in manifest["scenes"]:
        original, start, d = by_num[s["sceneNumber"]]
        s.update(sceneId=original["sceneId"], audioDurationSec=d,
                 timelineStartFrame=round(start * fps), durationFrames=round(d * fps), videoTrackSlices=[])
        for c in manifest["videoClips"]:
            lo, hi = max(start, c["start"]), min(start + d, c["start"] + c["duration"])
            if hi > lo + 1e-6:
                s["videoTrackSlices"].append({**c, "timelineStartFrame": round((lo-start)*fps),
                    "timelineDurationFrames": round((hi-lo)*fps),
                    "sourceIn": c["sourceIn"] + lo - c["start"],
                    "sourceOut": c["sourceIn"] + hi - c["start"]})


def web_paths(manifest: dict, prefix: str) -> None:
    for clip in manifest.get("videoClips", []):
        if clip["sourcePath"].startswith("project/"):
            clip["sourcePath"] = prefix + clip["sourcePath"][8:]
    for scene in manifest.get("scenes", []):
        for clip in scene.get("videoTrackSlices", []):
            if clip["sourcePath"].startswith("project/"):
                clip["sourcePath"] = prefix + clip["sourcePath"][8:]
