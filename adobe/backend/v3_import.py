"""v3 프로젝트(output/{uuid}_{slug}) → adobe 프로젝트 가져오기.
scene_specs 구(visualization.creative 중첩)/신(플랫) 스키마 양쪽 허용. 무삭제 — v3 원본은 읽기만."""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from backend import scenes

FPS = 30


def _visual_summary(s: dict) -> str:
    viz = s.get("visualization") or {}
    cre = viz.get("creative") or {}
    return (s.get("visual_summary") or cre.get("concept") or s.get("headline")
            or viz.get("concept") or "")


def _image_prompt(s: dict) -> str:
    ia = s.get("imageAsset") or {}
    return (ia.get("prompt") or ia.get("query") or s.get("image_prompt") or "")


def _num(v):
    """숫자면 그대로, 아니면 None. bool은 숫자로 치지 않는다."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def _lonlat_to_latlon(coord):
    """v3 [경도, 위도] → 어도비 [위도, 경도]. 길이 2의 숫자쌍이 아니면 None.

    패널(mapgen.js)은 map_center/map_markers를 [위도, 경도]로 읽고 MapLibre에 넘길 때
    다시 뒤집는다. 여기서 안 뒤집으면 예외 없이 엉뚱한 좌표가 렌더된다."""
    if not isinstance(coord, (list, tuple)) or len(coord) != 2:
        return None
    lon, lat = _num(coord[0]), _num(coord[1])
    if lon is None or lat is None:
        return None
    return [lat, lon]


def _center_to_latlon(coord):
    """v3 flat center(순서 미확정) → [위도, 경도]. v3 자체 휴리스틱을 따른다.

    위도는 90을 넘을 수 없다 — 둘째 값이 90을 넘으면 이미 [위도, 경도]이므로
    그대로 두고, 아니면 [경도, 위도]로 보고 뒤집는다."""
    if not isinstance(coord, (list, tuple)) or len(coord) != 2:
        return None
    a, b = _num(coord[0]), _num(coord[1])
    if a is None or b is None:
        return None
    if abs(b) > 90:
        return [a, b]
    return [b, a]


def _map_fields(map_scene: dict) -> dict:
    """v3 mapScene → 패널이 읽는 지도 필드(유효한 것만).

    카메라는 첫 키프레임을 쓴다 — 가장 넓어 마커가 다 들어오고,
    어도비가 지도 씬에 slow_zoom_in을 자동으로 걸어 v3의 밀어들어감이 재현된다.
    실제 코퍼스는 지도 씬 18개 중 10개가 camera 자체가 없고 mapScene에
    center/zoom을 바로 얹는다 — 그 경우 플랫 필드로 대체한다."""
    m = map_scene or {}
    out: dict = {"layout": "map", "map_v3": m}
    kfs = ((m.get("camera") or {}).get("keyframes")) or []
    first = kfs[0] if kfs and isinstance(kfs[0], dict) else {}
    center = _center_to_latlon(first.get("center"))
    zoom = _num(first.get("zoom"))
    if center is None:
        center = _center_to_latlon(m.get("center"))
    if zoom is None:
        zoom = _num(m.get("zoom"))
    if center:
        out["map_center"] = center
    if zoom is not None:
        out["map_zoom"] = zoom
    markers = []
    for mk in (m.get("markers") or []):
        if not isinstance(mk, dict):
            continue
        lat, lng = _num(mk.get("lat")), _num(mk.get("lng"))
        if lat is not None and lng is not None:
            coord = [lat, lng]                      # 이미 위도·경도 이름 — 뒤집지 않는다
        else:
            coord = _lonlat_to_latlon(mk.get("coordinates"))
        if coord:                                   # 깨진 마커는 그것만 건너뛴다
            markers.append({"coord": coord, "name": mk.get("label", "") or ""})
    if markers:
        out["map_markers"] = markers
    route = []
    route_src = m.get("route")
    if isinstance(route_src, list):
        for pt in route_src:
            if isinstance(pt, dict):
                at = pt.get("at")
                if (isinstance(at, (list, tuple)) and len(at) == 2
                        and _num(at[0]) is not None and _num(at[1]) is not None):
                    route.append([_num(at[0]), _num(at[1])])   # at은 이미 위도 먼저 — 뒤집지 않는다
                continue
            p = _lonlat_to_latlon(pt)
            if p:
                route.append(p)
    if route:
        out["map_route"] = route
    if m.get("title"):
        out["headline"] = m["title"]                # 씬의 title(씬 이름)과 충돌하지 않게
    if m.get("source"):
        out["source"] = m["source"]
    return out


def _map_scene(s: dict) -> dict:
    out = {
        "sceneNumber": s.get("sceneNumber"),
        "title": s.get("title", "") or "",
        "narration": s.get("narration", "") or "",
        "visual_summary": _visual_summary(s),
        "image_prompt": _image_prompt(s),
        "characters": s.get("characters") or [],
        "imageRef": "",
    }
    if s.get("narration_tts"):
        out["narration_tts"] = s["narration_tts"]
    if s.get("durationFrames"):
        out["duration_estimate_sec"] = round(float(s["durationFrames"]) / FPS, 2)
    elif s.get("duration_estimate_sec"):
        out["duration_estimate_sec"] = s["duration_estimate_sec"]

    # 레이아웃 이관 — v3의 visualization이 곧 레이아웃 정보다.
    # 어도비가 모르는 이름이어도 그대로 싣는다(별칭표·범용 렌더러가 받는다).
    viz = s.get("visualization") or {}
    cre = viz.get("creative") or {}
    layout = (viz.get("vizType") or cre.get("layout") or "").strip()
    if s.get("mapScene"):
        out.update(_map_fields(s["mapScene"]))
    elif layout:
        out["layout"] = layout
    if viz:
        if viz.get("title"):
            out.setdefault("headline", viz["title"])          # 씬의 title(씬 이름)과 충돌하지 않게 headline으로
        elif cre.get("headline"):
            out.setdefault("headline", cre["headline"])
        for key in ("items", "values", "descriptions", "unit",
                    "left", "right", "relations", "profileName", "profileSubtitle"):
            val = viz.get(key)
            if val:
                out[key] = val
        if viz.get("source"):
            out.setdefault("source", viz["source"])
        if not out.get("unit"):
            chart_unit = (viz.get("chart") or {}).get("unit")
            if chart_unit:
                out["unit"] = chart_unit
    return out


def import_v3(root: Path, v3_dir, title: str | None = None) -> dict:
    """v3 출력 폴더에서 adobe 프로젝트 생성. 반환 {project_id, scenes, images} 또는 {error}."""
    v3 = Path(v3_dir)
    specs = v3 / "scene_specs.json"
    if not specs.is_file():
        return {"error": f"scene_specs.json 없음: {v3}"}
    try:
        data = json.loads(specs.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"scene_specs 파싱 실패: {e}"}
    src_scenes = data.get("scenes") or []
    if not src_scenes:
        return {"error": "scenes 비어있음"}

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    pid = uuid.uuid4().hex[:8]
    d = root / pid
    d.mkdir(parents=True, exist_ok=False)
    name = title or data.get("topic") or v3.name.split("_", 1)[-1]
    (d / "plan.md").write_text(f"# {name}\n\n(v3 가져오기: {v3.name})\n", encoding="utf-8")

    mapped = [_map_scene(s) for s in src_scenes]
    (d / "scenes.json").write_text(json.dumps({"scenes": mapped}, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    scenes.ensure_scene_ids(d)          # sceneId 발급 + imageRef 백필

    man = v3 / "final_manuscript.md"
    if man.is_file():
        shutil.copy(man, d / "final_manuscript.md")

    # 기존 씬 이미지 복사(있으면): v3 images/scene_{n:03d}.* → storyboard/ + imageRef
    copied = 0
    img_dir = v3 / "images"
    if img_dir.is_dir():
        cur = scenes.load_scenes(d)
        for s in cur["scenes"]:
            n = s.get("sceneNumber")
            if not isinstance(n, int):
                continue
            for ext in ("png", "jpg", "jpeg", "webp"):
                src = img_dir / f"scene_{n:03d}.{ext}"
                if src.is_file():
                    sb = d / "storyboard"; sb.mkdir(exist_ok=True)
                    dst = sb / f"sb_{s['sceneId']}.png"
                    if ext == "png":
                        shutil.copy(src, dst)
                    else:
                        from PIL import Image
                        Image.open(src).convert("RGB").save(dst)
                    scenes.set_image_ref(d, n, f"storyboard/{dst.name}")
                    copied += 1
                    break
    return {"project_id": pid, "title": name, "scenes": len(mapped), "images": copied}
