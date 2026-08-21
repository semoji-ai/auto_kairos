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
    # 도해 — 요소마다 배경이 빠진 PNG 한 장과 백분율 좌표가 있다. 어도비가
    # 원하는 모양 그대로다(레이어 하나 = 요소 하나). 이 매핑이 없어서 도해
    # 씬은 어도비로 넘어오면 배경만 남았다.
    info = s.get("infographic")
    if isinstance(info, dict) and (info.get("items") or info.get("marks")):
        out["infographic"] = {
            "background": info.get("background", "grid"),
            "contrast": info.get("contrast", "plain"),
            "divider": info.get("divider", "none"),
            "items": [dict(it) for it in info.get("items") or []],
            "marks": [dict(m) for m in info.get("marks") or []],
        }
    if s.get("durationFrames"):
        out["duration_estimate_sec"] = round(float(s["durationFrames"]) / FPS, 2)
    elif s.get("duration_estimate_sec"):
        out["duration_estimate_sec"] = s["duration_estimate_sec"]

    # 레이아웃 이관 — 어도비가 모르는 이름이어도 그대로 싣는다
    # (별칭표·범용 렌더러가 받는다).
    #
    # **플랫 스키마를 안 읽고 있었다.** v3 는 `layout`·`items`·`values`·
    # `headline` 을 씬 최상위에 둔다(중첩 `visualization` 은 옛 구조다).
    # 그런데 여기서 `viz` 가 비면 블록 전체를 건너뛰어, 디아지오 142씬 중
    # **139씬이 레이아웃 없이** 넘어왔다 — 지도·차트·항목·헤드라인이 통째로
    # 사라져 전부 그림 한 장짜리 컷이 됐다. 둘 다 읽는다.
    viz = s.get("visualization") or {}
    cre = viz.get("creative") or {}
    layout = (viz.get("vizType") or cre.get("layout") or s.get("layout") or "").strip()
    if s.get("mapScene"):
        out.update(_map_fields(s["mapScene"]))
    elif layout:
        out["layout"] = layout

    if viz.get("title"):
        out.setdefault("headline", viz["title"])   # 씬의 title(씬 이름)과 충돌하지 않게 headline으로
    elif cre.get("headline"):
        out.setdefault("headline", cre["headline"])
    elif s.get("headline"):
        out.setdefault("headline", s["headline"])

    for key in ("items", "values", "descriptions", "unit",
                "left", "right", "relations", "profileName", "profileSubtitle"):
        val = viz.get(key) or s.get(key)            # 중첩 우선, 없으면 플랫
        if val:
            out[key] = val

    if viz.get("source") or s.get("source"):
        out.setdefault("source", viz.get("source") or s.get("source"))
    if not out.get("unit"):
        chart_unit = (viz.get("chart") or {}).get("unit") or (s.get("chart") or {}).get("unit")
        if chart_unit:
            out["unit"] = chart_unit

    # 인용 씬은 전용 필드를 쓴다 — 없으면 quote 레이아웃이 빈 따옴표만 그린다
    for k_src, k_dst in (("quote_text", "quote_text"), ("quote", "quote_text"),
                         ("quote_who", "quote_who"), ("speaker", "quote_who"),
                         ("mood", "mood"), ("icons", "icons"), ("sub", "sub")):
        if s.get(k_src) and not out.get(k_dst):
            out[k_dst] = s[k_src]
    return out


# adobe/backend/v3_import.py → adobe/backend → adobe → auto_kairos
CODE_ROOT = Path(__file__).resolve().parents[2]


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

    # 도해 요소 PNG 복사 — v3 의 `_imggen/…` 는 어도비 프로젝트 밖이다.
    # 밖을 가리키는 경로는 다른 컴퓨터에서 깨진다. 안으로 들여온다.
    cur0 = scenes.load_scenes(d)
    info_n = 0
    root_v3 = v3.parent.parent if (v3.parent.parent / "_imggen").is_dir() else v3.parent
    for s in cur0["scenes"]:
        info = s.get("infographic")
        if not isinstance(info, dict):
            continue
        for it in info.get("items") or []:
            rel = it.get("src") or ""
            src = None
            # 설계가 적어 둔 경로는 `ep01_info/…` 처럼 _imggen 안쪽 기준이다.
            # v3 출력 폴더는 NAS 에 있고 _imggen 은 코드 저장소에 있다 —
            # 출력 폴더 둘레만 뒤지면 못 찾는다(도해 요소가 통째로 빠졌다).
            for base in (CODE_ROOT / "_imggen", root_v3 / "_imggen", root_v3,
                         v3 / "_imggen", v3, Path.cwd() / "_imggen", Path.cwd()):
                cand = Path(base) / rel
                if cand.is_file():
                    src = cand
                    break
            if src is None:
                continue
            box = d / "infographic"
            box.mkdir(exist_ok=True)
            dst = box / src.name
            if not dst.exists():
                shutil.copy(src, dst)
            it["src"] = f"infographic/{dst.name}"
            info_n += 1
    if info_n:
        scenes._save(d, cur0)

    man = v3 / "final_manuscript.md"
    if man.is_file():
        shutil.copy(man, d / "final_manuscript.md")

    # 인물 시트 복사 — 재생성 모달이 「이 인물로 다시」를 하려면 시트가
    # 프로젝트 안에 있어야 한다. v3 시트는 저장소의 `_imggen/characters/…`
    # 에 있어 어도비 프로젝트 밖이다. 밖을 가리키면 다른 컴퓨터에서 깨진다.
    char_n = 0
    for base in (CODE_ROOT / "_imggen" / "characters",
                 root_v3 / "_imggen" / "characters", v3 / "characters"):
        sheets = sorted(Path(base).glob("*/*_sheet.png")) + sorted(Path(base).glob("*_sheet.png")) \
            if Path(base).is_dir() else []
        if not sheets:
            continue
        box = d / "characters"
        box.mkdir(exist_ok=True)
        for s_ in sheets:
            dst = box / f"char_{s_.stem.replace('_sheet', '')}.png"
            if not dst.exists():
                shutil.copy(s_, dst)
            char_n += 1
        break

    # 조사로 확보한 실물 자료. 둘로 나뉜다.
    #   ① 화면에 그대로 나가는 것(`images/search/`) — 씬의 그림 자체다
    #   ② 보고 그리기 위한 참조(`refAssets`) — 화면에는 안 나가지만 재생성
    #      모달에서 골라 붙일 수 있어야 한다
    # 둘 다 안 옮기고 있었다. 어도비에서 「자료 이미지가 하나도 안 보인다」의 정체다.
    doc_n = 0
    sdir = v3 / "images" / "search"
    if sdir.is_dir():
        box = d / "docs"
        for f_ in sorted(sdir.iterdir()):
            if f_.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                continue
            box.mkdir(exist_ok=True)
            if not (box / f_.name).exists():
                shutil.copy2(f_, box / f_.name)
            doc_n += 1

    # refAssets — v3 프로젝트 밖(`_imggen/refs/…`)을 가리키는 것이 많다.
    # 밖을 가리키는 경로는 다른 컴퓨터에서 깨지므로 안으로 들여온다.
    seen_ref: set = set()
    for s in src_scenes:
        for r in ((s.get("imageAsset") or {}).get("refAssets") or []):
            lp = r.get("local")
            if not lp:
                continue
            for base in (v3, CODE_ROOT, root_v3):
                cand = Path(base) / lp
                if cand.is_file():
                    box = d / "docs"
                    box.mkdir(exist_ok=True)
                    dst = box / cand.name
                    if cand.name not in seen_ref and not dst.exists():
                        shutil.copy2(cand, dst)
                        doc_n += 1
                    seen_ref.add(cand.name)
                    break

    # TTS 음성 복사 — 가져오기가 이 단계를 아예 갖고 있지 않았다.
    # 원고와 그림은 들어오는데 소리만 빠져 「연동이 안 됐다」로 보였다.
    #
    # v3 음성 파일은 **씬 번호가 아니라 해시로** 저장된다(`6fa8547e.mp3`).
    # 그래서 이름을 짐작할 수 없고, 씬과 파일을 잇는 것은 `tts_results.json`
    # 하나뿐이다. 그것을 읽지 않으면 282개 파일을 놓고도 어느 것이 몇 번
    # 씬인지 알 수 없다.
    audio_n = 0
    tts_f = v3 / "tts_results.json"
    if tts_f.is_file():
        try:
            results = json.loads(tts_f.read_text(encoding="utf-8")).get("results") or []
        except Exception:
            results = []
        cur_a = scenes.load_scenes(d)
        by_n = {s.get("sceneNumber"): s for s in cur_a["scenes"]}
        box = d / "audio"
        for r in results:
            if r.get("status") != "ok":
                continue
            s = by_n.get(r.get("scene"))
            src = Path(r.get("path") or "")
            # 절대경로는 만든 컴퓨터의 것이다. 파일 이름으로 v3 audio/ 를 다시 본다.
            if not src.is_file():
                src = v3 / "audio" / src.name
            if not (s and src.is_file()):
                continue
            box.mkdir(exist_ok=True)
            dst = box / src.name
            if not dst.exists():
                shutil.copy(src, dst)
            # 자막 타이밍도 함께 온다. 없으면 자막이 소리와 어긋난다.
            ts = src.with_suffix(".timestamps.json")
            if ts.is_file() and not (box / ts.name).exists():
                shutil.copy(ts, box / ts.name)
            s["_audio"] = f"audio/{dst.name}"
            s["_audio_dur"] = float(r.get("duration") or 0.0)
            audio_n += 1
        if audio_n:
            scenes._save(d, cur_a)

    # 기존 씬 이미지 복사(있으면): v3 images/scene_{n:03d}.* → storyboard/ + imageRef
    copied = 0
    img_dir = v3 / "images"
    picked, versions = {}, {}
    ia = img_dir / "image_assets.json"
    if ia.is_file():
        try:
            for e in json.loads(ia.read_text(encoding="utf-8")).get("scenes", []):
                sel = e.get("selected") or next(
                    (i.get("file") for i in e.get("images") or [] if i.get("selected")), None)
                if sel:
                    picked[e.get("sceneNumber")] = sel
                # 후보 전체 — 판본을 다 가져와야 패널에서 되돌릴 수 있다
                versions[e.get("sceneNumber")] = e.get("images") or []
        except Exception:
            picked, versions = {}, {}
    if img_dir.is_dir():
        cur = scenes.load_scenes(d)
        for s in cur["scenes"]:
            n = s.get("sceneNumber")
            if not isinstance(n, int):
                continue
            # 고른 그림은 image_assets.json 에 적혀 있다. 파일 이름이
            # scene_011_fix.png 처럼 판이 올라가므로, 이름만 짐작하면
            # 옛 그림을 가져가거나 아무것도 못 가져간다.
            cands = []
            if picked.get(n):
                cands.append(img_dir / picked[n])
            cands += [img_dir / f"scene_{n:03d}.{e}" for e in ("png", "jpg", "jpeg", "webp")]
            # `source: search` 씬은 **조사한 실물 사진이 곧 화면**이다.
            # `images/search/scene_NNN_search_01.jpg` 로 들어 있는데 여기를
            # 안 봐서 28씬이 통째로 그림 없이 넘어왔다.
            sdir_ = img_dir / "search"
            if sdir_.is_dir():
                cands += sorted(sdir_.glob(f"scene_{n:03d}*"))
            # **판본을 전부 가져온다.** 예전에는 첫 장만 옮기고 끝냈다
            # (`break`). v3 는 씬마다 여러 판을 쌓아 두고 `selected` 로 하나만
            # 고르는데, 어도비에는 그 하나만 와서 **후보를 볼 수도 되돌릴 수도
            # 없었다** — 디아지오편에서 38씬이 그 상태였다.
            # 대시보드·앱은 후보를 보여 주는데 패널만 못 보던 이유다.
            all_vers = [img_dir / i["file"] for i in (versions.get(n) or [])]
            for extra in cands:
                if extra not in all_vers:
                    all_vers.append(extra)
            sel_rel, k = None, 0
            for src in all_vers:
                if not src.is_file():
                    continue
                sb = d / "storyboard"; sb.mkdir(exist_ok=True)
                # 첫 장은 sb_{sid}.png, 나머지는 _v2·_v3… — `_latest_image`·
                # 후보 목록이 이 이름 규칙을 읽는다.
                dst = sb / (f"sb_{s['sceneId']}.png" if k == 0
                            else f"sb_{s['sceneId']}_v{k + 1}.png")
                if src.suffix.lower() == ".png":
                    shutil.copy(src, dst)
                else:
                    from PIL import Image
                    Image.open(src).convert("RGB").save(dst)
                # v3 가 고른 판본을 링크한다. 못 찾으면 첫 장.
                if picked.get(n) and src == img_dir / picked[n]:
                    sel_rel = f"storyboard/{dst.name}"
                if sel_rel is None and k == 0:
                    sel_rel = f"storyboard/{dst.name}"
                k += 1
            if sel_rel:
                scenes.set_image_ref(d, n, sel_rel)
                copied += 1
    return {"project_id": pid, "title": name, "scenes": len(mapped),
            "images": copied, "audio": audio_n, "infographic": info_n, "docs": doc_n,
            "characters": char_n}
