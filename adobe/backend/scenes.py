"""scenes.json 조회/수정 — sceneId 기반 에셋, 미디어·레이어 enrich, 나레이션 편집(무삭제)."""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
import uuid
from pathlib import Path

from backend import themes


_LOCK = threading.RLock()


def _path(proj_dir: Path) -> Path:
    return proj_dir / "scenes.json"


def _new_sid() -> str:
    return uuid.uuid4().hex[:8]


def _migrate_assets(proj_dir: Path, old_key, sid: str) -> None:
    """번호 기반 에셋(sb_{old}/bg_{old}/char_{old})을 sid 기반으로 복사(무삭제·멱등)."""
    sb, lay = proj_dir / "storyboard", proj_dir / "layers"
    if sb.is_dir():
        for p in list(sb.glob(f"sb_{old_key}.png")) + list(sb.glob(f"sb_{old_key}_v*.png")):
            tgt = sb / p.name.replace(f"sb_{old_key}", f"sb_{sid}", 1)
            if not tgt.exists():
                shutil.copy(p, tgt)
    if lay.is_dir():
        for nm in (f"bg_{old_key}.png", f"char_{old_key}.png"):
            src = lay / nm
            tgt = lay / nm.replace(f"_{old_key}.", f"_{sid}.", 1)
            if src.exists() and not tgt.exists():
                shutil.copy(src, tgt)


def ensure_scene_ids(proj_dir: Path) -> dict:
    """모든 씬에 sceneId 보장(없으면 발급). 신규 발급 시 번호 기반 에셋을 sid로 복사 마이그레이션.
    변경 시 scenes.json 저장. 멱등. 반환=data."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"scenes": []}
        data = json.loads(fp.read_text(encoding="utf-8"))
        changed = False
        for s in data.get("scenes", []):
            if not s.get("sceneId"):
                sid = _new_sid()
                s["sceneId"] = sid
                _migrate_assets(proj_dir, s.get("sceneNumber"), sid)
                changed = True
            if "imageRef" not in s:                       # 최초 1회 백필
                latest = _latest_image(proj_dir / "storyboard", s.get("sceneId"))
                s["imageRef"] = latest or ""
                changed = True
        if changed:
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data


def scene_id_for(proj_dir: Path, scene_number) -> str | None:
    data = ensure_scene_ids(proj_dir)
    for s in data.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            return s.get("sceneId")
    return None


def _latest_image(sb_dir: Path, sid: str) -> str | None:
    """storyboard/sb_{sid}.png 및 버전(sb_{sid}_v2.png …) 중 최신(버전 번호 숫자 정렬)."""
    if not sb_dir.is_dir() or not sid:
        return None
    files: list[tuple[str, int]] = []
    if (sb_dir / f"sb_{sid}.png").exists():
        files.append((f"sb_{sid}.png", 0))
    for p in sb_dir.glob(f"sb_{sid}_v*.png"):
        try:
            files.append((p.name, int(p.name.split("_v")[1].split(".")[0])))
        except (IndexError, ValueError):
            pass
    if not files:
        return None
    files.sort(key=lambda x: x[1])
    return f"storyboard/{files[-1][0]}"


def load_scenes(proj_dir: Path) -> dict:
    """sceneId 보장 후 각 씬에 _image(최신)·_layers(sid 기반) 부여. dir=프로젝트 절대경로."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"scenes": [], "dir": ""}
    data = ensure_scene_ids(proj_dir)
    lay_dir = proj_dir / "layers"
    for s in data.get("scenes", []):
        sid = s.get("sceneId")
        ref = s.get("imageRef") or ""
        s["_image"] = ref if (ref and (proj_dir / ref).is_file()) else None
        # 지도 씬이 **아직 안 그려졌는지** 알려 준다. 좌표·마커가 다 들어와
        # 있어도 누가 🗺 지도를 누르기 전에는 지도가 생기지 않는데, 화면에는
        # v3 가 그려 준 삽화가 링크돼 있어 「다 된 것」처럼 보였다.
        # 지도를 렌더하면 `<이미지>.geo.json` 사이드카가 함께 생긴다 — 그것이 표식이다.
        s["_map_rendered"] = bool(
            ref and (proj_dir / (ref + ".geo.json")).is_file())
        s["_layers"] = (sorted(f"layers/{p.name}" for p in lay_dir.glob(f"*{sid}*.png"))
                        if sid and lay_dir.is_dir() else [])
        s["_layer_meta"] = _layer_meta(lay_dir, sid) if sid and lay_dir.is_dir() else {}
        # 못 뗀 요소 — 있으면 화면에 「빠진 N개 더 분리」를 낸다.
        # 이것이 없으면 절반만 분리된 씬이 다 된 것처럼 보인다.
        if sid and lay_dir.is_dir():
            from backend import imagegen as _ig
            s["_layer_missing"] = _ig.load_missing(lay_dir, sid)
        else:
            s["_layer_missing"] = []
        aud_dir = proj_dir / "audio"
        auds = ([p for p in aud_dir.glob(f"tts_{sid}.*") if p.suffix != ".json"]
                if sid and aud_dir.is_dir() else [])    # .timestamps.json 사이드카 제외
        if auds:
            s["_audio"] = f"audio/{max(auds, key=lambda p: p.stat().st_mtime).name}"
        else:
            # 이름이 `tts_{sceneId}` 인 것만 찾으면, **다른 데서 가져온 음성은
            # 통째로 사라진다.** v3 는 음성을 해시로 저장하므로(`6fa8547e.mp3`)
            # 이 규칙에 하나도 걸리지 않는다. 가져오기가 `scenes.json` 에
            # 141개를 적어 넣어도 여기서 매번 None 으로 덮여, 파일이 다 있는데
            # 패널에는 음성이 하나도 없었다.
            #
            # 적혀 있고 파일이 실제로 있으면 그것을 믿는다.
            saved = s.get("_audio") or ""
            s["_audio"] = saved if (saved and (proj_dir / saved).is_file()) else None
        if s["_audio"]:                         # 길이는 백엔드(afinfo)에서 — 브라우저 메타 불안정(MP3 Infinity)
            from backend import tts as _tts
            s["_audio_dur"] = _tts.audio_duration(proj_dir / s["_audio"])
        else:
            s["_audio_dur"] = 0.0
        # 차트 명세서 사이드카(chart_{sid}.spec.json) — 시트 미리보기 해칭 표시용
        if sid and s.get("layout") == "bar":
            csp = proj_dir / f"chart_{sid}.spec.json"
            if csp.is_file():
                try:
                    s["chartSpec"] = json.loads(csp.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
        aud = proj_dir / "audio"
        s["_status"] = {
            "narration": bool((s.get("narration") or "").strip()),
            "image": s["_image"] is not None,
            "layers": len(s["_layers"]) > 0,
            "tts": bool(sid and aud.is_dir() and any(aud.glob(f"*{sid}*"))),
            "motion": bool(sid and (proj_dir / f"motion_{sid}.json").is_file()),
        }
        # 유효 텍스트(필드가 비면 원고 폴백) — 패널이 편집기 초기값으로 사용
        s["_tts_text"] = tts_text(s)
        s["_subtitle_text"] = subtitle_text(s)
        s["_theme"] = themes.resolve_theme(proj_dir, s)   # 씬별 resolve(override 반영)
    data["_theme"] = themes.resolve_theme(proj_dir, None)  # 프로젝트 전역 테마
    data["dir"] = str(proj_dir)
    data["_specs_drift"] = specs_drift(proj_dir)           # 원고 파일과 어긋난 곳
    return data


SPECS = "scene_specs.json"


def mirror_to_specs(proj_dir: Path, scene_number, fields: dict) -> bool:
    """같은 폴더의 `scene_specs.json` 에도 함께 쓴다.

    **원고는 두 파일에 있다.** 어도비는 `scenes.json` 을, 리모션·대시보드는
    `scene_specs.json` 을 본다. 한쪽만 고치면 같은 폴더 안에서 갈리고, 갈린 줄
    모른 채 한쪽으로 렌더된다.

    지금은 142씬이 전부 일치한다(대조해 확인했다). 그 상태를 지키는 것이
    이 함수의 일이다.

    `sceneId` 는 **건드리지 않는다.** 두 파일의 ID 가 다른데 각자 다른 산출물의
    이름을 쥐고 있다 — v3 ID 는 음성 92개, 어도비 ID 는 그림·레이어 347장과
    비디오 29편. 어느 쪽으로 통일해도 반대쪽 파일을 전부 이름 바꿔야 하고,
    지금도 서로를 잘 찾고 있으므로 그대로 둔다.
    """
    fp = Path(proj_dir) / SPECS
    if not fp.is_file():
        return False
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        rows = data.get("scenes") if isinstance(data, dict) else data
        for s in rows or []:
            try:
                same = float(s.get("sceneNumber")) == float(scene_number)
            except (TypeError, ValueError):
                continue
            if not same:
                continue
            for k, v in fields.items():
                if v is None:
                    continue
                s[k] = v
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
    except Exception:
        return False
    return False


_DRIFT_CACHE: dict = {}


def specs_drift(proj_dir: Path) -> dict:
    """`scene_specs.json` 과 어긋난 곳을 센다. {scenes, narration} 또는 {}.

    나레이션·TTS·자막은 `mirror_to_specs` 가 함께 쓰지만, **씬을 더하거나
    지우거나 나누면 되비출 수 없다** — 번호가 밀리고 ID 가 새로 생긴다.
    그때는 막지 말고 **어긋났다고 알린다.** 모르고 지나가면 리모션이 옛 구성으로
    렌더한다.

    파일이 바뀌지 않았으면 다시 세지 않는다 — 1MB 를 씬마다 읽으면 시트가 느려진다.
    """
    fp = Path(proj_dir) / SPECS
    mine = _path(proj_dir)
    if not (fp.is_file() and mine.is_file()):
        return {}
    try:
        key = (fp.stat().st_mtime_ns, fp.stat().st_size,
               mine.stat().st_mtime_ns, mine.stat().st_size)
    except OSError:
        return {}
    hit = _DRIFT_CACHE.get(str(proj_dir))
    if hit and hit[0] == key:
        return hit[1]
    out = {}
    try:
        a = json.loads(fp.read_text(encoding="utf-8"))
        a = a.get("scenes") if isinstance(a, dict) else a
        b = json.loads(mine.read_text(encoding="utf-8")).get("scenes") or []
        A = {str(s.get("sceneNumber")): s for s in a or []}
        B = {str(s.get("sceneNumber")): s for s in b}
        if len(A) != len(B) or set(A) != set(B):
            out["scenes"] = [len(A), len(B)]
        n = sum(1 for k in (set(A) & set(B))
                if (A[k].get("narration") or "") != (B[k].get("narration") or ""))
        if n:
            out["narration"] = n
    except Exception:
        out = {}
    _DRIFT_CACHE[str(proj_dir)] = (key, out)
    return out


def update_narration(proj_dir: Path, scene_number: int, narration: str) -> dict:
    """씬 나레이션 수정 + narration_dirty=True 저장. {ok, sceneNumber} 또는 {error}."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                s["narration"] = narration
                s["narration_dirty"] = True
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                mirror_to_specs(proj_dir, scene_number, {"narration": narration})
                return {"ok": True, "sceneNumber": scene_number}
        return {"error": f"scene {scene_number} 없음"}


def narration_stamp(narration: str) -> str:
    """이 원고에서 나온 전용 텍스트인지 표시할 지문."""
    from backend import tts as _tts
    return hashlib.sha1(
        _tts._clean_text(narration or "").encode("utf-8")).hexdigest()[:12]


def tts_text(scene: dict) -> str:
    """씬의 TTS 발음용 텍스트. narration_tts 없으면 narration을 정리해서 반환(저장은 안 함).

    **전용 텍스트가 원고를 영원히 이기면 안 된다.** 합성할 때마다 쓴 텍스트가
    narration_tts 로 자동 저장되므로, 한 번이라도 TTS 를 돌린 씬은 그 값이
    굳는다. 그 뒤로 원고를 아무리 고쳐도 여기서 굳은 값을 돌려주어 음성이
    바뀌지 않았다 — 「될 때가 있고 안 될 때가 있다」의 정체다.

    그래서 전용 텍스트를 저장할 때 **그때의 원고 지문**을 함께 남긴다.
    지금 원고의 지문과 다르면 원고가 그 뒤에 바뀐 것이므로 전용 텍스트를
    지나치고 원고를 쓴다. 손으로 넣은 발음 교정은 원고가 그대로인 동안
    살아남는다.

    지문이 없는 옛 값은 그대로 믿는다 — 그 안에 의도한 발음 교정이 섞여
    있어 일괄로 버릴 수 없다. 화면의 「원고와 다름」 배지로 사람이 고른다.
    """
    t = (scene.get("narration_tts") or "").strip()
    if t:
        stamp = scene.get("narration_tts_of")
        if not stamp or stamp == narration_stamp(scene.get("narration") or ""):
            return t
    from backend import tts as _tts
    return _tts._clean_text(scene.get("narration") or "")


def subtitle_text(scene: dict) -> str:
    """씬의 화면 자막용 텍스트. subtitle_text 없으면 narration."""
    t = (scene.get("subtitle_text") or "").strip()
    return t if t else (scene.get("narration") or "").strip()


def _layer_meta(lay_dir, sid: str) -> dict:
    """{stem: {name, kind, z, hidden, removed, svg}} — 패널 레이어 목록용.

    사이드카에 없는 레이어(배경·레거시)도 파일 기준으로 항목을 만든다.
    svg는 같은 이름의 .svg 파일 존재 여부다."""
    from backend import imagegen
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(lay_dir, sid)}
    plate = None
    for p in lay_dir.glob(f"*{sid}*bg*.png"):
        try:
            from PIL import Image
            with Image.open(p) as im:
                plate = (im.width, im.height)
        except Exception:
            plate = None
        break
    out = {}
    for p in sorted(lay_dir.glob(f"*{sid}*.png")):
        stem = p.stem
        sp = specs.get(stem) or {}
        is_bg = imagegen.is_background_layer(stem)
        out[stem] = {
            "name": sp.get("name") or ("배경" if is_bg else stem),
            "kind": "bg" if is_bg else (sp.get("kind") or "object"),
            "z": sp.get("z"),
            "hidden": bool(sp.get("hidden")),
            "removed": bool(sp.get("removed")),
            "svg": (lay_dir / (stem + ".svg")).is_file(),
            "box": _box_pct(sp.get("bbox"), plate) if not is_bg else None,
        }
    return out


def _box_pct(bbox, plate):
    """bbox(배경판 픽셀) → {left, top, width} 백분율. 패널 합성 미리보기용.
    bbox나 배경판 크기가 없으면 None — 패널이 풀프레임으로 겹친다."""
    if not bbox or len(bbox) != 4 or not plate or not plate[0] or not plate[1]:
        return None
    try:
        l, t, r, b = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return None
    if r - l <= 0 or b - t <= 0:
        return None
    pw, ph = plate
    return {"left": l / pw * 100, "top": t / ph * 100, "width": (r - l) / pw * 100}


def update_texts(proj_dir: Path, scene_number: int,
                 narration_tts: str | None = None,
                 subtitle_text: str | None = None) -> dict:
    """씬의 TTS/자막 텍스트 저장(부분 갱신). 빈 문자열이면 필드 제거(= 원고 폴백으로 복귀)."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                for key, val in (("narration_tts", narration_tts),
                                 ("subtitle_text", subtitle_text)):
                    if val is None:
                        continue
                    if val.strip():
                        s[key] = val
                        # 이 전용 텍스트가 **어느 원고에서 나왔는지** 함께 남긴다.
                        # 나중에 원고가 바뀌면 tts_text() 가 이 지문을 보고
                        # 굳은 값을 지나친다.
                        if key == "narration_tts":
                            s["narration_tts_of"] = narration_stamp(s.get("narration") or "")
                    else:
                        s.pop(key, None)
                        if key == "narration_tts":
                            s.pop("narration_tts_of", None)
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                # 원고 쪽에도 함께 — 리모션·대시보드가 그 파일을 본다
                mirror_to_specs(proj_dir, scene_number, {
                    "narration_tts": s.get("narration_tts"),
                    "subtitle_text": s.get("subtitle_text"),
                })
                return {"ok": True, "sceneNumber": scene_number,
                        "narration_tts": s.get("narration_tts", ""),
                        "subtitle_text": s.get("subtitle_text", "")}
        return {"error": f"scene {scene_number} 없음"}


def new_scene_image_name(sid: str) -> str:
    """생성 씬 이미지의 고유 파일명(여러 번 생성해도 충돌·덮어쓰기 없음)."""
    return f"scene_{sid}_{uuid.uuid4().hex[:6]}.png"


def set_scene_video(proj_dir: Path, scene_number, video_rel: str) -> dict:
    """씬에 만들어 둔 비디오를 매단다.

    **원격 URL 을 그대로 두지 않는다.** 힉스필드 결과 링크는 만료되므로
    프로젝트 안으로 받아 둔 상대 경로만 적는다.
    """
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        rel = (video_rel or "").strip()
        if rel and not (proj_dir / rel).is_file():
            return {"error": f"파일 없음: {rel}"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                if rel:
                    s["videoRef"] = rel
                else:
                    s.pop("videoRef", None)
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "sceneNumber": scene_number, "videoRef": rel}
        return {"error": f"scene {scene_number} 없음"}


def set_image_prompt(proj_dir: Path, scene_number, prompt: str) -> dict:
    """씬의 image_prompt 를 갈아 끼운다.

    재생성 모달에서 고쳐 넣은 프롬프트를 남겨 두기 위한 것이다. 안 남기면
    다음에 모달을 열 때 옛 프롬프트가 떠서 같은 수정을 매번 다시 해야 한다.
    """
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                s["image_prompt"] = prompt
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "sceneNumber": scene_number}
        return {"error": f"scene {scene_number} 없음"}


def set_image_ref(proj_dir: Path, scene_number, image_rel) -> dict:
    """씬의 imageRef 설정(링크) 또는 빈 문자열로 해제. 경로는 프로젝트 내부 + 존재 검증."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        rel = (image_rel or "").strip()
        if rel:
            target = (proj_dir / rel).resolve()
            if not target.is_relative_to(proj_dir.resolve()):
                return {"error": "잘못된 경로"}
            if not target.is_file():
                return {"error": f"파일 없음: {rel}"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                s["imageRef"] = rel
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "sceneNumber": scene_number, "imageRef": rel}
        return {"error": f"scene {scene_number} 없음"}


def _save(proj_dir: Path, data: dict) -> dict:
    _path(proj_dir).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def _renumber(data: dict) -> dict:
    for i, s in enumerate(data.get("scenes", []), start=1):
        s["sceneNumber"] = i
    return data


def _split_text(text: str) -> tuple[str, str]:
    """문장 단위로 가운데 분할. 문장 경계 없으면 (전체, '')."""
    import re
    t = (text or "").strip()
    if not t:
        return "", ""
    parts = re.split(r"(?<=[.!?。])\s+", t)
    if len(parts) < 2:
        return t, ""
    mid = (len(parts) + 1) // 2
    return " ".join(parts[:mid]).strip(), " ".join(parts[mid:]).strip()


def _blank_scene(sid: str, narration: str = "", title: str = "") -> dict:
    return {"sceneNumber": 0, "sceneId": sid, "title": title, "narration": narration,
            "visual_summary": "", "image_prompt": "", "characters": [], "imageRef": ""}


def add_scene(proj_dir: Path, after_number: int | None = None,
              narration: str = "", title: str = "") -> dict:
    """after_number 다음에 새 씬 삽입(없으면 끝). 새 sceneId 발급. 재번호 후 저장. 반환=load_scenes."""
    with _LOCK:
        data = ensure_scene_ids(proj_dir)
        ss = data.setdefault("scenes", [])
        new = _blank_scene(_new_sid(), narration, title)
        idx = len(ss)
        if after_number is not None:
            for i, s in enumerate(ss):
                if s.get("sceneNumber") == after_number:
                    idx = i + 1
                    break
        ss.insert(idx, new)
        _save(proj_dir, _renumber(data))
        return load_scenes(proj_dir)


def remove_scene(proj_dir: Path, scene_number: int) -> dict:
    """배열에서 씬 제거(파일 무삭제). 재번호 후 저장. 반환=load_scenes."""
    with _LOCK:
        data = ensure_scene_ids(proj_dir)
        ss = data.get("scenes", [])
        data["scenes"] = [s for s in ss if s.get("sceneNumber") != scene_number]
        _save(proj_dir, _renumber(data))
        return load_scenes(proj_dir)


def split_scene(proj_dir: Path, scene_number: int,
                first: str | None = None, second: str | None = None) -> dict:
    """씬을 둘로 분할. 첫 씬=기존 sceneId+imageRef 유지, 둘째=새 sceneId+빈 imageRef.
    first/second 미지정 시 나레이션 문장 단위 분할. 반환=load_scenes."""
    with _LOCK:
        data = ensure_scene_ids(proj_dir)
        ss = data.get("scenes", [])
        for i, s in enumerate(ss):
            if s.get("sceneNumber") == scene_number:
                if first is None and second is None:
                    first, second = _split_text(s.get("narration", ""))
                s["narration"] = first or ""
                nxt = _blank_scene(_new_sid(), second or "", s.get("title", ""))
                nxt["visual_summary"] = s.get("visual_summary", "")
                ss.insert(i + 1, nxt)
                break
        _save(proj_dir, _renumber(data))
        return load_scenes(proj_dir)


def set_project_theme(proj_dir: Path, theme_id: str) -> dict:
    """scenes.json 최상위 theme 설정. {ok} 또는 {error}."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        data["theme"] = theme_id
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "theme": theme_id}


def set_scene_theme(proj_dir: Path, scene_number: int, theme_id: str | None) -> dict:
    """씬 themeOverride 설정(None이면 해제). {ok} 또는 {error}."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                if theme_id:
                    s["themeOverride"] = theme_id
                else:
                    s.pop("themeOverride", None)
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "sceneNumber": scene_number, "themeOverride": theme_id}
        return {"error": f"scene {scene_number} 없음"}


def merge_scenes(proj_dir: Path, scene_number: int) -> dict:
    """scene_number 와 그 다음 씬을 병합. 첫 씬 sceneId+imageRef 유지, 나레이션 연결.
    둘째 씬 에셋은 디스크에 남김(무삭제). 다음 씬 없으면 no-op. 반환=load_scenes."""
    with _LOCK:
        data = ensure_scene_ids(proj_dir)
        ss = data.get("scenes", [])
        for i, s in enumerate(ss):
            if s.get("sceneNumber") == scene_number and i + 1 < len(ss):
                nxt = ss[i + 1]
                a, b = (s.get("narration") or "").strip(), (nxt.get("narration") or "").strip()
                s["narration"] = (a + "\n" + b).strip()
                del ss[i + 1]
                break
        _save(proj_dir, _renumber(data))
        return load_scenes(proj_dir)


def neighbor_context(scenes_list: list, scene_number) -> str:
    """앞뒤 씬 한 줄 요약 + 이 씬의 shot_relation.
    이어지는 샷(continue)이면 레이어 구성을 앞 씬과 맞춰야 연결이 끊기지 않는다."""
    def _line(s):
        if not s:
            return "(없음)"
        nar = (s.get("narration") or "").strip().replace("\n", " ")[:60]
        return f"{s.get('title', '') or '(제목 없음)'} — {nar}"

    idx = next((i for i, s in enumerate(scenes_list)
                if s.get("sceneNumber") == scene_number), None)
    if idx is None:
        return "앞 씬: (없음)\n뒤 씬: (없음)"
    prev = scenes_list[idx - 1] if idx > 0 else None
    nxt = scenes_list[idx + 1] if idx + 1 < len(scenes_list) else None
    rel = (scenes_list[idx].get("shot_relation") or "").strip()
    head = f"앞 씬: {_line(prev)}"
    if rel:
        head += f"  (이 씬은 앞 씬과 {rel})"
    return head + f"\n뒤 씬: {_line(nxt)}"
