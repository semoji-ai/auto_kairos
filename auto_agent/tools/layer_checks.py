"""레이어 분리(fal Seedream 5.0 layerize) 결과 점검 — 이름 목록 누락, 배경판 잔상.

1. 이름 목록 누락: Seedream 은 **프롬프트에 적은 이름만** 떼어 낸다. 적지 않은 요소
   (글자 덩어리, 연결선, 화살표, 건물에 딸린 나무·연기)는 배경판에 남아 첫 프레임부터
   보인다. 씬에서 등장시킬 요소 목록(expected)과 보낼 이름 목록(names)을 미리 맞춘다.
2. 응답 누락: 이름을 보냈는데 그 레이어가 안 돌아온 경우.
3. 배경판 잔상(통합보고 §0-1 #8, §3-5): 요소 bbox·알파 안에서 원본과 z0 배경판의
   **세부 무늬(고주파)** 를 비교한다. 요소가 판에서 지워졌으면 판의 무늬는 원본과
   상관이 없고, 남아 있으면 원본 무늬가 거의 그대로(회귀 계수 ≈ 1) 있다.
   색 차이만 보면 밝은 벽 위 밝은 간판처럼 대비가 낮은 요소를 잔상으로 잘못 잡는다
   (한화 S158 간판 — 실제로는 잘 지워짐). 한화 EP01 554개 요소 실측: 중앙값 0.001,
   95% 0.11, 잔상이 눈으로 확인된 S186 달리는 아이 1.03, S157 사무실 집기 1.15.
   기준은 하나 — 0.25 이상이면 flag(다시 고칠 대상). 한화 EP01 에서 11개 요소(2%)가 걸린다.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RESIDUE_FLAG = 0.25     # 이 이상이면 요소가 배경판에 남아 있다(이중 표시) — 다시 고칠 대상. 단일 기준
MIN_DETAIL = 2.0        # 원본 요소 안 무늬 표준편차가 이보다 작으면(민무늬) 판정하지 않는다

_STOP = {"the", "a", "an", "of", "with", "and", "on", "in", "at", "to", "for", "left", "right",
         "top", "bottom", "center", "small", "large", "big"}


def _tokens(s: str) -> set[str]:
    toks = re.findall(r"[0-9A-Za-z가-힣]+", (s or "").lower())
    return {t[:-1] if len(t) > 3 and t.endswith("s") else t for t in toks if t not in _STOP}


def covers(expected: str, name: str) -> bool:
    """이름 하나가 기대 요소 하나를 덮는가 — 기대 요소의 핵심 낱말이 이름에 모두 있으면.

    "arrow to box" 는 "box" 로 덮이지 않는다(화살표가 빠진다)."""
    e, n = (expected or "").strip().lower(), (name or "").strip().lower()
    if not e or not n:
        return False
    if e in n:
        return True
    te = _tokens(e)
    return bool(te) and te <= _tokens(n)


def missing_expected(expected: list, names: list) -> list[str]:
    """이름 목록에 없는 기대 요소. expected 항목은 문자열 또는 {"name": ...}."""
    out = []
    for e in expected or []:
        label = e.get("name") if isinstance(e, dict) else e
        if label and not any(covers(label, n) for n in names or []):
            out.append(label)
    return out


def missing_returned(requested: list, returned: list) -> list[str]:
    """보냈는데 레이어로 돌아오지 않은 이름."""
    got = {(r or "").strip().lower() for r in returned if r}
    return [n for n in requested or [] if n and n.strip().lower() not in got]


def _detail(rgb: np.ndarray) -> np.ndarray:
    g = Image.fromarray(rgb.mean(-1).astype(np.uint8))
    a = np.asarray(g).astype(np.float32)
    return a - np.asarray(g.filter(ImageFilter.GaussianBlur(3))).astype(np.float32)


def residue_score(original: Image.Image, plate: Image.Image, element: Image.Image,
                  bbox) -> dict:
    """요소가 배경판에 남은 정도. {"score", "level": ok|flag|flat, "px"}.

    score = 원본 무늬에 대한 판 무늬의 회귀 계수(요소 알파 안). 1 이면 그대로 남음, 0 이면 지워짐."""
    W, H = original.size
    l, t, r, b = [int(round(v)) for v in bbox]
    l, t, r, b = max(0, l), max(0, t), min(W, r), min(H, b)
    if r - l < 2 or b - t < 2:
        return {"score": None, "level": "flat", "px": 0}
    if plate.size != original.size:
        plate = plate.resize(original.size, Image.LANCZOS)
    o = np.asarray(original.convert("RGB").crop((l, t, r, b)))
    p = np.asarray(plate.convert("RGB").crop((l, t, r, b)))
    el = element.convert("RGBA").resize((r - l, b - t), Image.LANCZOS)
    mask = np.asarray(el)[..., 3] > 127
    px = int(mask.sum())
    if px < 50:
        return {"score": None, "level": "flat", "px": px}
    do, dp = _detail(o)[mask], _detail(p)[mask]
    if do.std() < MIN_DETAIL:
        return {"score": None, "level": "flat", "px": px}
    beta = float(((do - do.mean()) * (dp - dp.mean())).mean() / (do.var() + 1e-6))
    level = "flag" if beta >= RESIDUE_FLAG else "ok"
    return {"score": round(beta, 3), "level": level, "px": px}


def check_layer_dir(d: Path, source: Path | None = None) -> list[dict]:
    """layerize 결과 폴더(elements.json) 하나를 점검해 요소마다 bg_residue 를 단다.

    elements.json 을 고쳐 쓰고, 잔상(flag) 요소 목록을 돌려준다."""
    import json
    d = Path(d)
    m = json.loads((d / "elements.json").read_text(encoding="utf-8"))
    src = Path(source or m.get("source") or "")
    if not src.is_file():
        return [{"key": m.get("key"), "error": f"원본 없음: {src}"}]
    orig = Image.open(src)
    bg = next((e for e in m["elements"] if e.get("kind") == "background"), None)
    if not bg:
        return [{"key": m.get("key"), "error": "배경판(z0) 없음"}]
    plate = Image.open(d / bg["layer"])
    issues = []
    for e in m["elements"]:
        if e is bg or not e.get("bbox"):
            continue
        f = d / e["layer"]
        if not f.is_file():
            continue
        res = residue_score(orig, plate, Image.open(f), e["bbox"])
        e["bg_residue"] = res
        if res["level"] == "flag":
            issues.append({"key": m.get("key"), "name": e["name"], **res})
    (d / "elements.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return issues
