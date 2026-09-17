"""여러 씬에 걸쳐 재생되는 독립 비디오 트랙 — video_tracks.json 계약 + resolver.

원본 MP4 하나가 씬 여러 개를 가로질러 재생된다. 원고·TTS·자막은 씬 기준을
유지하고, **영상만 연결된 씬 범위의 첫 씬 in점에 한 번** 배치한다
(docs/handoff-multiscene-video-track-20260917.md).

파일 계약(프로젝트 루트 `video_tracks.json`):

    {"schemaVersion": 1, "revision": 1,
     "tracks": [{"trackId": "primary-video", "enabled": true,
                 "clips": [{"clipId": "...", "enabled": true,
                            "sourcePath": "video_sources/xx.mp4",
                            "sceneIds": ["ffac7f1c", "d9055674"],
                            "anchor": {"sceneId": "ffac7f1c", "offsetFrames": 0},
                            "sourceInSec": 0, "sourceOutSec": 6.583333,
                            "playbackRate": 1, "audioPolicy": "mute"}]}]}

원칙:
- 시간의 단일 기준은 `timeline.scene_timings` 다. 여기서 따로 초를 더해
  새 타임라인을 만들지 않는다.
- 원본 구간은 반개방 `[sourceInSec, sourceOutSec)`. sourceOutSec 은 길이가
  아니라 원본 안의 종료 위치다.
- 배치 시작 = 앵커 씬 시작 + offsetFrames/fps. 절대 시작초를 따로 저장하지
  않는다 — 두 값을 독립 수정하면 반드시 어긋난다.
- 원본이 씬 범위보다 길면 **범위 끝에서 자른다**(끝 홀드를 덜 쓰는 것).
  다음 씬을 조용히 덮지 않는다. 짧으면 그대로 끝난다 — 몰래 늘이거나
  루프하지 않고, 남는 구간은 기존 씬 화면이 보인다. 둘 다 warnings 에 남긴다.
- 이 파일이 없으면 아무것도 달라지지 않는다(기존 프로젝트 회귀 없음).
"""
from __future__ import annotations

import json
from pathlib import Path

from backend import timeline

FILE_NAME = "video_tracks.json"
SCHEMA_VERSION = 1


def load(proj_dir: Path) -> dict:
    """video_tracks.json 을 읽는다. 없으면 빈 구조."""
    fp = Path(proj_dir) / FILE_NAME
    if not fp.is_file():
        return {"schemaVersion": SCHEMA_VERSION, "revision": 0, "tracks": []}
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {"schemaVersion": SCHEMA_VERSION, "revision": 0, "tracks": [],
                "error": "video_tracks.json 을 읽지 못했습니다(JSON 오류)"}
    d.setdefault("schemaVersion", SCHEMA_VERSION)
    d.setdefault("revision", 0)
    d.setdefault("tracks", [])
    return d


def save(proj_dir: Path, data: dict, *, expect_revision: int | None = None) -> dict:
    """원자적으로 저장. expect_revision 이 다르면 충돌로 거절(다른 창의 수정 보호)."""
    proj_dir = Path(proj_dir)
    cur = load(proj_dir)
    if expect_revision is not None and int(cur.get("revision") or 0) != int(expect_revision):
        return {"error": "revision 충돌 — 다른 곳에서 먼저 저장됐습니다. 다시 불러와 주세요.",
                "revision": cur.get("revision")}
    data = dict(data)
    data["schemaVersion"] = SCHEMA_VERSION
    data["revision"] = int(cur.get("revision") or 0) + 1
    fp = proj_dir / FILE_NAME
    tmp = fp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(fp)
    return {"ok": True, "revision": data["revision"]}


def _scene_index(timings: list) -> dict:
    """sceneId → (순번, scene, start, dur)."""
    out = {}
    for i, (s, start, dur) in enumerate(timings):
        sid = s.get("sceneId")
        if sid:
            out[sid] = (i, s, start, dur)
    return out


def resolve(proj_dir: Path, data: dict, *, fps: float = float(timeline.FPS)) -> dict:
    """활성 클립을 타임라인 좌표로 정규화한다.

    반환 {"clips": [정규화 클립…], "covered": {sceneId…}, "errors": […]}.
    errors 에 걸린 클립은 clips 에서 빠진다 — 잘못된 배치를 조용히 얹는 것보다
    빠뜨리고 알리는 편이 낫다. warnings 는 배치는 하되 알리는 것.
    """
    proj_dir = Path(proj_dir)
    from backend import scenes as _scenes
    sdata = _scenes.load_scenes(proj_dir)
    timings = timeline.scene_timings(proj_dir, sdata, fps=fps)
    idx = _scene_index(timings)

    clips_out: list = []
    covered: set = set()
    errors: list = []
    spans: list = []            # (trackId, start, end) — 같은 트랙 안 겹침 검사

    for tr in data.get("tracks") or []:
        if not tr.get("enabled", True):
            continue
        tid = tr.get("trackId") or "primary-video"
        for c in tr.get("clips") or []:
            cid = c.get("clipId") or "?"
            if not c.get("enabled", True):
                continue

            def bad(msg):
                errors.append(f"[{tid}/{cid}] {msg}")

            src_rel = c.get("sourcePath") or ""
            src = (proj_dir / src_rel).resolve()
            if not src_rel or not src.is_file():
                bad(f"원본 없음: {src_rel}")
                continue
            if proj_dir.resolve() not in src.parents:
                bad(f"원본이 프로젝트 밖: {src_rel}")
                continue

            sids = list(c.get("sceneIds") or [])
            if not sids:
                bad("sceneIds 비어 있음")
                continue
            missing = [s for s in sids if s not in idx]
            if missing:
                bad("없는 씬 ID: " + ", ".join(missing))
                continue
            orders = sorted(idx[s][0] for s in sids)
            if orders != list(range(orders[0], orders[0] + len(orders))):
                bad("씬 범위가 연속이 아님 — 첫 버전은 연속한 씬만 지원")
                continue

            try:
                s_in = float(c.get("sourceInSec") or 0.0)
                s_out = float(c.get("sourceOutSec") or 0.0)
                rate = float(c.get("playbackRate") or 1.0)
            except (TypeError, ValueError):
                bad("숫자 필드를 읽지 못함(sourceInSec/sourceOutSec/playbackRate)")
                continue
            if s_in < 0 or s_out <= s_in:
                bad(f"원본 구간이 뒤집힘: [{s_in}, {s_out})")
                continue
            if rate <= 0:
                bad(f"playbackRate 잘못됨: {rate}")
                continue

            anchor = c.get("anchor") or {}
            a_sid = anchor.get("sceneId") or sids[0]
            if a_sid not in idx:
                bad(f"앵커 씬 없음: {a_sid}")
                continue
            if idx[a_sid][0] != orders[0]:
                bad("앵커는 범위의 첫 씬이어야 함")
                continue
            try:
                off = int(anchor.get("offsetFrames") or 0)
            except (TypeError, ValueError):
                bad("offsetFrames 잘못됨")
                continue

            # 배치 — 앵커 씬 시작 + 프레임 offset. 끝은 범위 마지막 씬의 끝.
            first = idx[a_sid]
            last_i = orders[-1]
            range_end = timings[last_i][1] + timings[last_i][2]
            start = first[2] + off / fps
            if start >= range_end:
                bad("offset 이 씬 범위를 벗어남")
                continue

            warnings: list = []
            span = (s_out - s_in) / rate
            end = start + span
            if end > range_end + 1e-6:
                warnings.append(f"원본이 씬 범위보다 {end - range_end:.2f}s 길어 범위 끝에서 자름")
                end = range_end
            elif end < range_end - 1e-6:
                warnings.append(f"원본이 씬 범위보다 {range_end - end:.2f}s 짧음 — 남는 구간은 씬 화면")

            for (otid, os_, oe_) in spans:
                if otid == tid and start < oe_ - 1e-6 and os_ < end - 1e-6:
                    bad("같은 트랙의 다른 클립과 겹침")
                    break
            else:
                spans.append((tid, start, end))
                covered.update(sids)
                clips_out.append({
                    "clipId": cid,
                    "trackId": tid,
                    "sourcePath": str(src),
                    "sceneIds": sids,
                    "start": round(start, 6),
                    "duration": round(end - start, 6),
                    "sourceIn": s_in,
                    "sourceOut": s_out,
                    "playbackRate": rate,
                    "muted": (c.get("audioPolicy") or "mute") != "keep",
                    **({"warnings": warnings} if warnings else {}),
                })

    return {"clips": clips_out, "covered": covered, "errors": errors}
