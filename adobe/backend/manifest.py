"""scenes.json + 에셋 → AE build_scene.jsx 용 manifest.json(레이어 스택 포함)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from backend import motion, scene_layouts, scenes, themes, timeline

W, H, FPS = 1920, 1080, 30
DEFAULT_DUR = timeline.DEFAULT_DUR      # 길이 규칙은 timeline이 단일 기준


def _key(n):
    """씬 번호 비교용 — 삽입 씬의 소수 번호(25.25)를 int로 자르면 서로 다른 씬이 섞인다."""
    try:
        return float(n)
    except (TypeError, ValueError):
        return None


def _abs(proj_dir: Path, rel: str) -> str:
    return str((proj_dir / rel).resolve())


def _svg_ratio(svg_path, png_path) -> float:
    """PNG 픽셀 폭 ÷ SVG 선언 폭. 배율에 곱하면 들어온 크기가 무엇이든 자리가 맞는다."""
    import re as _re
    try:
        head = svg_path.read_text(encoding="utf-8", errors="replace")[:400]
        m = _re.search(r'\swidth="([\d.]+)"', head)
        sw = float(m.group(1)) if m else 0.0
        pw = float((_img_size(png_path) or (0, 0))[0])
        if sw > 0 and pw > 0:
            return pw / sw
    except Exception:
        pass
    return 1.0


def _scene_video(proj_dir: Path, sid: str):
    """이 씬의 영상. 없으면 None.

    두 길로 들어온다 — **만든 것**은 `video/v_<sid>_*.mp4`(힉스필드), **끌어다
    놓은 것**은 `video_sources/`(대시보드). 만든 것이 있으면 그것이 먼저다.
    같은 씬을 여러 번 만들었으면 가장 최근 것을 쓴다.
    """
    if not sid:
        return None
    d = proj_dir / "video"
    if d.is_dir():
        hits = sorted(d.glob(f"v_{sid}_*.mp4"), key=lambda p: p.stat().st_mtime,
                      reverse=True)
        if hits:
            return hits[0]
    va = proj_dir / "video_assets.json"
    if va.is_file():
        try:
            for e in json.loads(va.read_text(encoding="utf-8")).get("scenes", []):
                if e.get("sceneId") != sid:
                    continue
                p = proj_dir / "video_sources" / (e.get("videoFile") or "")
                if p.is_file():
                    return p
        except Exception:
            pass
    return None


def _svg_size(svg_path):
    """SVG 가 선언한 크기 (w, h). 못 읽으면 None."""
    import re as _re
    try:
        head = svg_path.read_text(encoding="utf-8", errors="replace")[:400]
        mw = _re.search(r'\swidth="([\d.]+)"', head)
        mh = _re.search(r'\sheight="([\d.]+)"', head)
        if mw and mh:
            return [float(mw.group(1)), float(mh.group(1))]
    except Exception:
        pass
    return None


def _img_size(path: Path):
    """이미지 픽셀 크기 (w, h). 실패 시 None."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:
        return None


def fit_transform(sw, sh, comp_w: int = W, comp_h: int = H):
    """세로 기준 배율과 좌우 중앙 정렬 오프셋 (f, ox).

    f = 컴프높이 / 이미지높이 — 위아래를 자르지 않는다. 폭이 남으면 좌우에 여백이
    생기고(ox 양수), 16:9보다 가로로 길면 좌우로 넘친다(ox 음수).
    크기를 못 읽었거나 비정상이면 (1.0, 0.0)으로 물러선다."""
    try:
        sw = float(sw)
        sh = float(sh)
    except (TypeError, ValueError):
        return (1.0, 0.0)
    if sw <= 0 or sh <= 0:
        return (1.0, 0.0)
    f = comp_h / sh
    return (f, (comp_w - sw * f) / 2)


def camera_keys(cam, *, sw, sh, f: float, ox: float, dur: float,
                comp_w: int = W, comp_h: int = H) -> list:
    """카메라를 가이드 널 키프레임 [{t, scale, position, ease?}]로 굽는다.

    입력 두 형태:
    - [{t, rect:[x,y,w,h], ease?}] — 인수인계 문서의 화각 키. rect는 씬 이미지 좌표라
      레이어와 같은 f·ox 변환을 거친다(두 번 변환 금지). 널의 자식은 바인딩 시점의
      상대 위치를 유지하므로 P = 중앙 - (화각중심 - 중앙) × s 로 역산한다.
    - {type, amount} — 구 모션 플랜·지도 기본값. 같은 수치의 키 2개로 번역한다.
    jsx는 이 값을 그대로 찍는다 — 계산하지 않는다."""
    cx0, cy0 = comp_w / 2, comp_h / 2
    if cam is None:
        return []
    if isinstance(cam, dict):
        t = cam.get("type")
        if not t or t == "none":
            return []
        amt = cam.get("amount")
        if t in ("slow_zoom_in", "slow_zoom_out"):
            z = 1 + float(amt or 6) / 100.0
            s0, s1 = (100.0, 100.0 * z) if t == "slow_zoom_in" else (100.0 * z, 100.0)
            return [{"t": 0.0, "scale": round(s0, 3), "position": [cx0, cy0]},
                    {"t": round(float(dur), 3), "scale": round(s1, 3),
                     "position": [cx0, cy0], "ease": "70:30"}]
        if t in ("pan_left", "pan_right"):
            px = float(amt or 40)
            d = -1.0 if t == "pan_left" else 1.0
            return [{"t": 0.0, "scale": 100.0, "position": [cx0 - d * px / 2, cy0]},
                    {"t": round(float(dur), 3), "scale": 100.0,
                     "position": [cx0 + d * px / 2, cy0], "ease": "70:30"}]
        return []
    out = []
    for k in cam or []:
        r = (k or {}).get("rect")
        if not r or len(r) != 4:
            continue
        try:
            vx, vy, vw, vh = [float(v) for v in r]
        except (TypeError, ValueError):
            continue
        if vw <= 0 or vh <= 0:
            continue
        vx, vy, vw, vh = vx * f + ox, vy * f, vw * f, vh * f
        s = comp_w / vw
        ccx, ccy = vx + vw / 2, vy + vh / 2
        entry = {"t": round(float(k.get("t") or 0), 3),
                 "scale": round(s * 100, 3),
                 "position": [round(cx0 - (ccx - cx0) * s, 2),
                              round(cy0 - (ccy - cy0) * s, 2)]}
        if k.get("ease"):
            entry["ease"] = str(k["ease"])
        out.append(entry)
    return out


def _scene_layers(proj_dir: Path, layer_rels: list, sid: str = "", scene_width: int | None = None,
                  *, prefix: str = "", f: float = 1.0, ox: float = 0.0,
                  scene_height: int | None = None) -> list:
    """[{name, aeName, path, kind, position, scale, foot?}] — 배경(__bg)을 맨 앞(최하단)으로.

    좌표는 **컴프 공간**이다. layerize 레이어는 요소 크기로 크롭돼 오므로 사이드카 bbox로
    씬 이미지 좌표를 되살린 뒤, 세로 기준 배율 f와 좌우 오프셋 ox를 곱해 컴프 좌표로 굽는다.
    jsx는 이 숫자를 그대로 찍는다 — 계산하지 않는다.

    bbox가 없는 레이어(배경판·레거시 풀프레임)도 좌표를 싣는다. 씬 사각형을 채우도록
    자기 PNG 폭 기준으로 배율을 낸다."""
    from backend import imagegen
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(proj_dir / "layers", sid)} if sid else {}
    bg = [r for r in layer_rels if "__bg" in Path(r).name]
    el = [r for r in layer_rels if "__bg" not in Path(r).name]
    # 프로젝트에서 제거한 요소는 내보내지 않는다. hidden은 패널 미리보기 전용이라 무시한다.
    el = [r for r in el if not (specs.get(Path(r).stem) or {}).get("removed")]
    el.sort(key=lambda r: (specs.get(Path(r).stem, {}).get("z") is None,
                           specs.get(Path(r).stem, {}).get("z") or 0,
                           Path(r).name))
    sw = float(scene_width or W)
    sh = float(scene_height or H)
    scale_factor = 1.0
    if scene_width and bg:
        plate_size = _img_size(proj_dir / bg[0])
        if plate_size and plate_size[0]:
            scale_factor = scene_width / plate_size[0]
    out = []
    idx = 0
    n_el = len(el)
    for r in bg + el:
        stem = Path(r).stem
        is_bg = "__bg" in Path(r).name
        # 벡터화한 레이어는 SVG로 내보낸다 — AE에서 연속 래스터화를 켜면 확대해도 깨지지 않는다.
        # 크기 계산은 PNG 기준을 그대로 쓴다. PIL은 SVG를 읽지 못한다.
        svg_rel = str(Path(r).with_suffix(".svg"))
        has_svg = (proj_dir / svg_rel).is_file()
        if is_bg:
            ae_name = prefix + "배경"
        else:
            # 순번은 최상위(가장 앞) 레이어가 01 — 배열은 z 오름차순(뒤→앞)이라 뒤집어 센다.
            idx += 1
            nm = (specs.get(stem) or {}).get("name") or stem
            ae_name = "%s%02d_%s" % (prefix, n_el - idx + 1, re.sub(r"\s+", "", str(nm)))
        entry = {"name": stem, "aeName": ae_name,
                 "path": _abs(proj_dir, svg_rel if has_svg else r),
                 "kind": "bg" if is_bg else "element"}
        if has_svg:
            entry["vector"] = True
            # **배율은 들어올 크기 기준이어야 한다.** 좌표와 배율은 PNG 픽셀
            # 기준으로 계산하는데(PIL 이 SVG 를 못 읽는다), 애프터이펙트는
            # SVG 가 선언한 크기로 들여온다. 둘이 다르면 자리가 통째로 밀린다.
            # 머리말을 읽어 그 비를 곱해 둔다 — 1/10 로 줄여 넣어도 자리가 맞는다.
            entry["vectorRatio"] = _svg_ratio(proj_dir / svg_rel, proj_dir / r)
            # **무엇을 전제로 계산했는지 함께 적는다.**
            #
            # 배율은 「SVG 가 이 크기로 들어온다」를 전제로 굽는다. 그런데 SVG
            # 파일이 나중에 바뀌면(창을 고치거나 다시 벡터화하면) 그 전제가
            # 깨지고, 매니페스트를 다시 굽지 않으면 아무도 모른다 — 창을 1/10
            # 로 선언하던 시절의 매니페스트로 들여왔더니 쉐이프가 24배로
            # 커졌다. 전제를 적어 두면 jsx 가 들여온 실제 크기와 대 보고
            # 스스로 맞춘다.
            entry["vectorSize"] = _svg_size(proj_dir / svg_rel)
            # **요소만 쉐이프로 편다.** 배경판은 path 가 900개를 넘어 레이어가
            # 쏟아진다 — 타임라인이 감당이 안 되고 렌더도 무거워진다.
            # 요소는 10~40KB 라 펴도 몇 장 안 된다.
            if not is_bg:
                entry["explode"] = True
            # **SVG 가 안 들어올 때를 대비해 PNG 를 함께 준다.** 애프터이펙트가
            # SVG 하나를 거부하면 그 씬 빌드가 통째로 멈춰, 배경만 들어오고
            # 나머지는 사라진다(100씬이 그랬다). 한 장이 실패해도 그림은 나와야 한다.
            entry["fallback"] = _abs(proj_dir, r)
        placed = False
        if not is_bg:
            bbox = (specs.get(stem) or {}).get("bbox")
            if bbox and len(bbox) == 4:
                try:
                    l, t, rr, b = [float(v) * scale_factor for v in bbox]
                except (TypeError, ValueError):
                    l = rr = None      # 비정상(비수치) bbox — bbox 없는 것으로 취급
                if l is not None and (rr - l) > 0:
                    size = _img_size(proj_dir / r)
                    if size and size[0]:
                        entry["position"] = [(l + rr) / 2 * f + ox, (t + b) / 2 * f]
                        entry["scale"] = (rr - l) / size[0] * 100 * f * entry.get("vectorRatio", 1.0)
                        entry["foot"] = [(l + rr) / 2 * f + ox, b * f]
                        placed = True
        if not placed:
            # 풀프레임(배경판·bbox 없는 레거시) — 씬 사각형을 채운다
            size = _img_size(proj_dir / r) or (sw, sh)
            pw = float(size[0] or sw)
            entry["position"] = [sw * f / 2 + ox, sh * f / 2]
            entry["scale"] = sw * f / pw * 100 * entry.get("vectorRatio", 1.0)
            if not is_bg:
                foot = _alpha_foot(proj_dir / r)
                if foot:
                    entry["foot"] = [foot[0] * f + ox, foot[1] * f]
        out.append(entry)
    return out


def _info_layers(proj_dir: Path, info: dict, prefix: str) -> tuple[list, list]:
    """도해를 **레이어와 글자**로 굽는다 — 요소 하나가 레이어 하나다.

    도해는 한 장으로 구운 그림이 아니라 배경이 빠진 요소 PNG 여럿과 백분율
    좌표다. 그래서 어도비에서 레이어마다 집어 옮길 수 있다. 좌표가 조금
    어긋난 자리는 사람이 직접 옮기는 편이 모델에게 다시 물어보는 것보다 낫다.

      left/top (%)  → 컴프 좌표 (앵커는 가운데)
      size (%)      → 화면 너비 대비 배율
      label         → 요소 아래 글자
      marks         → 잇는 기호(= → ×5)와 도장(확인불가)
    """
    layers, texts = [], []
    for i, it in enumerate(info.get("items") or []):
        rel = it.get("src") or ""
        f = proj_dir / rel
        if not f.is_file():
            continue
        size = _img_size(f) or (W, H)
        want_w = W * float(it.get("size", 20)) / 100.0
        cx = W * float(it.get("left", 50)) / 100.0
        cy = H * float(it.get("top", 50)) / 100.0
        layers.append({
            "name": f"{prefix}info_{it.get('id', i)}_{i}",
            "aeName": f"{prefix}info_{it.get('id', i)}_{i}",
            "path": str(f.resolve()),
            "kind": "element",
            "position": [round(cx, 2), round(cy, 2)],
            "scale": round(want_w / (size[0] or W) * 100, 3),
        })
        if (it.get("label") or "").strip():
            texts.append({"text": it["label"], "position": [round(cx, 2),
                          round(cy + want_w / 2 + H * 0.045, 2)],
                          "style": "label", "size": 30,
                          "accent": it.get("emphasis") == "accent"})
    for m in info.get("marks") or []:
        texts.append({
            "text": str(m.get("text", "")),
            "position": [round(W * float(m.get("left", 50)) / 100.0, 2),
                         round(H * float(m.get("top", 50)) / 100.0, 2)],
            "style": m.get("style", "mark"),
            "size": int(m.get("size", 52)),
            "accent": False,
        })
    return layers, texts


def _alpha_foot(path: Path) -> list | None:
    """불투명 영역 bbox의 하단 중앙 [x, y](레이어=컴프 좌표). 전부 투명/실패 시 None.
    bbox 사이드카가 없는 기존(풀프레임) 레이어의 까딱 모션 피벗 폴백."""
    try:
        from PIL import Image
        with Image.open(path) as im:
            bbox = im.convert("RGBA").getchannel("A").getbbox()
        if not bbox:
            return None
        l, t, r, b = bbox
        return [round((l + r) / 2, 1), float(b)]
    except Exception:
        return None


def build_manifest(proj_dir: Path, only_scene: int | None = None,
                   only_scenes: list | None = None) -> dict:
    """manifest.json 생성. 반환 {path, scenes}.

    only_scene = 한 씬(manifest_scene_{n}.json), only_scenes = 여러 씬(manifest_subset.json).
    둘 다 없으면 전체(manifest.json). 평면 구조에서는 Final이 유일한 컴프이므로 부분
    빌드도 같은 컴프에 들어간다 — 각 씬은 자기 start(전체 타임라인 기준)를 그대로 낸다."""
    proj_dir = Path(proj_dir)
    data = scenes.load_scenes(proj_dir)
    starts = {}
    for s_t, start_t, _dur_t in timeline.scene_timings(proj_dir, data):
        starts[_key(s_t.get("sceneNumber"))] = start_t
    picked = None
    if only_scenes:
        picked = {_key(x) for x in only_scenes}
    elif only_scene is not None:
        picked = {_key(only_scene)}
    out_scenes = []
    for s in data.get("scenes", []):
        if picked is not None and _key(s.get("sceneNumber")) not in picked:
            continue
        sid = s.get("sceneId")
        audio = _abs(proj_dir, s["_audio"]) if s.get("_audio") else None
        # **시작점과 같은 격자를 쓴다.** 시작은 프레임에 맞추고 길이는 실측
        # 그대로 쓰면 씬 끝이 다음 씬 시작과 어긋난다.
        dur = timeline.snap(timeline.scene_duration(proj_dir, s))
        layout = s.get("layout") or "cinematic"
        layout = scene_layouts.resolve_layout(layout)   # 별칭·미지원 이름 → 그릴 수 있는 이름
        # 지도 씬 — 패널(MapLibre)이 렌더한 지도 이미지가 링크되면 일반 이미지 씬으로 취급
        is_map = layout == "map"
        if is_map and s.get("_image"):
            layout = "cinematic"
        is_layout_scene = layout != "cinematic"
        # width/height는 씬 이미지 원본 크기(fit 계산 기준) — 컴프 좌표는 fit_transform으로 굽는다.
        # 레이아웃 씬(비이미지)은 이미지/레이어를 쓰지 않음 — 기본 1920×1080 기준
        # 레이아웃 씬이어도 **그림이 있으면 그 크기를 쓴다.** v3 의 timeline·
        # flow·items_list 는 씬 그림 위에 항목이 얹히는 구조라 배경이 필요하다.
        # 여기서 None 을 주면 fit 계산이 1920×1080 기준이 되어 배경이 어긋난다.
        size = _img_size(proj_dir / s["_image"]) if s.get("_image") else None
        sw, sh = size if size else (W, H)
        f, ox = fit_transform(sw, sh)
        prefix = "S%s_" % timeline.comp_num(s.get("sceneNumber"))
        layers = [] if is_layout_scene else _scene_layers(
            proj_dir, s.get("_layers") or [], sid, sw,
            prefix=prefix, f=f, ox=ox, scene_height=sh)
        # 레이어 종류(캐릭터/사물) — 옛 모션 사이드카·기본 bob 규칙 둘 다 이걸 쓴다.
        kinds = {}
        kp = proj_dir / "layers" / f"{sid}__kinds.json"
        if kp.is_file():
            try:
                kinds = json.loads(kp.read_text(encoding="utf-8"))
            except Exception:
                kinds = {}
        cam = None
        mp = proj_dir / f"motion_{sid}.json"
        if mp.is_file():
            try:
                mo = json.loads(mp.read_text(encoding="utf-8"))
                moves_by = {L.get("layer"): L.get("moves", []) for L in mo.get("layers", [])}
                for entry in layers:
                    mv = moves_by.get(entry["name"])
                    if mv:
                        # 캐릭터는 오퍼시티 키프레임 금지 — fade류·stamp 제거, slide는 noFade 플래그
                        if "_char" in entry["name"]:
                            mv = [m for m in mv if m.get("type") not in ("fade_in", "exit_fade", "stamp")]
                            for m in mv:
                                m["noFade"] = True
                        # 옛 사이드카는 종류별 허용 목록을 거치지 않았을 수 있다 — 여기서 한 번 더 거른다.
                        kind = "character" if "_char" in entry["name"] else (kinds.get(entry["name"]) or "object")
                        allowed = motion.ALLOWED_BY_KIND.get(kind) or set()
                        mv = [m for m in mv if m.get("type") in allowed]
                        if mv:
                            entry["moves"] = mv
                c = mo.get("camera")
                if isinstance(c, list) and c:            # 화각 키 배열(신형)
                    cam = c
                elif isinstance(c, dict) and c.get("type") and c["type"] != "none":
                    cam = c
            except Exception:
                cam = None
        # 씬 자체에 화각 키가 실려 있으면(v3 파이프라인 산출) 그것을 쓴다 — 사이드카가 우선
        if cam is None and isinstance(s.get("camera"), list) and s.get("camera"):
            cam = s["camera"]
        if is_map and cam is None:
            cam = {"type": "slow_zoom_in", "amount": 6}   # 지도 씬 기본 — 천천히 푸시인
        cam = camera_keys(cam, sw=sw, sh=sh, f=f, ox=ox, dur=dur) or None
        # 차트 명세서 사이드카(chart_{sid}.spec.json) — chartagent 패턴/모티프 토큰을 jsx bar에 전달
        chart_spec = None
        csp = proj_dir / f"chart_{sid}.spec.json"
        if layout == "bar" and csp.is_file():
            try:
                chart_spec = json.loads(csp.read_text(encoding="utf-8"))
            except Exception:
                chart_spec = None
        # 지도 geo 사이드카({이미지}.geo.json) — 마커/경로 픽셀 좌표를 jsx에 전달(AE 네이티브 레이어)
        map_geo = None
        if is_map and s.get("_image"):
            gp = proj_dir / f"{s['_image']}.geo.json"
            if gp.is_file():
                try:
                    map_geo = json.loads(gp.read_text(encoding="utf-8"))
                except Exception:
                    map_geo = None
        # 결정적 규칙: 캐릭터 레이어(_char 접미사 또는 kinds 사이드카)는 LLM 플랜 없이도
        # 항상 발밑 피벗 bob(까딱임) — 모션 버튼은 부가 연출(fade_in/camera)용 옵션
        # (kinds는 위 모션 사이드카 필터에서 이미 로드했다)
        for entry in layers:
            if entry["kind"] != "element" or entry.get("moves") or not entry.get("foot"):
                continue
            is_char = "_char" in entry["name"] or kinds.get(entry["name"]) == "character"
            if is_char:
                # 숫자는 여기 적지 않는다 — 까딱임 기본값은 motion.py 하나뿐이다
                entry["moves"] = [motion.bob_move(0, dur)]
        # 레이아웃 데이터 — v3 공통 계약으로 정규화해서 넘긴다(jsx는 정규 이름만 안다)
        data_fields = scene_layouts.normalize_fields(s)
        # 도해 — 요소를 레이어로, 라벨과 기호를 글자로 굽는다
        info_texts = []
        info_src = s.get("infographic")
        if isinstance(info_src, dict) and (info_src.get("items") or info_src.get("marks")):
            il, info_texts = _info_layers(proj_dir, info_src, prefix)
            layers = list(layers) + il
        out_scenes.append({
            "ae_comp_name": timeline.comp_name(s),
            "width": sw, "height": sh,
            "image": _abs(proj_dir, s["_image"]) if s.get("_image") else None,
            # **영상이 있으면 그것이 그 씬의 화면이다.**
            #
            # 영상은 씬 그림을 움직인 것이라, 그림·레이어와 같은 자리를 두고
            # 다툰다. 셋을 다 얹으면 겹쳐서 아무것도 안 보인다. 있으면
            # 영상만 얹고 그림과 레이어는 건너뛴다 — 판단은 jsx 가 한다.
            **({"video": _abs(proj_dir, str(_vid.relative_to(proj_dir)))}
               if (_vid := _scene_video(proj_dir, str(s.get("sceneId") or ""))) else {}),
            "layers": layers,
            "audio": audio,
            "subtitle": scenes.subtitle_text(s),   # 화면 표시용(TTS 발음 텍스트 아님)
            "duration": dur,
            "start": starts.get(_key(s.get("sceneNumber")), 0.0),
            "prefix": prefix,
            **({"source": str(s.get("source")).strip()}
               if s.get("source") and str(s.get("source")).strip() else {}),
            # fit — jsx는 읽지 않는다(레이어 좌표는 이미 컴프 공간으로 구워서 낸다).
            # 테스트·디버깅에서 fit_transform 계산값을 매니페스트만 보고 검증하려고 남긴다.
            "fit": {"f": f, "ox": ox, "w": sw, "h": sh},
            "bgFill": (sw * f) < (W - 1),
            **({"imageFit": {"position": [sw * f / 2 + ox, sh * f / 2],
                             "scale": sw * f / float((_img_size(proj_dir / s["_image"]) or (sw, sh))[0] or sw) * 100}}
               if s.get("_image") else {}),
            "layout": layout,
            **({"infoTexts": info_texts} if info_texts else {}),
            **({"infoBackground": (s.get("infographic") or {}).get("background")}
               if isinstance(s.get("infographic"), dict) else {}),
            **data_fields,
            **({"camera": cam} if cam else {}),
            **({"mapGeo": map_geo} if map_geo else {}),
            **({"chartSpec": chart_spec} if chart_spec else {}),
        })
    mf = {"width": W, "height": H, "fps": FPS, "scenes": out_scenes}
    tokens_path = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json"
    if tokens_path.is_file():
        mf["ae_tokens"] = str(tokens_path)
    proj_theme = themes.resolve_theme(proj_dir, None)
    if proj_theme.get("colors"):
        mf["themeColors"] = proj_theme["colors"]   # jsx가 ae_tokens.colors 위에 오버라이드
    if only_scenes:
        name = "manifest_subset.json"
    elif only_scene is not None:
        name = f"manifest_scene_{only_scene}.json"
    else:
        name = "manifest.json"
    out = proj_dir / name
    out.write_text(json.dumps(mf, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(out), "scenes": len(out_scenes)}
