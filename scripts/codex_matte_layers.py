#!/usr/bin/env python3
"""[폐기 — 2026-10-07] 완성 장면 한 장을 codex 매트로 나눈다 (마이디어편 방식).

**레이어 분리 규칙은 fal Seedream 5.0(bytedance/seedream/v5/pro/layerize) 단일 경로다**
(scripts/layerize_scenes.py, docs/rules/scene-visual-decision.md ⑥). 이 스크립트는
마이디어편 재현·비교용으로만 남긴다. 실행하려면 사용자 승인 사유를 `--approved "<사유>"`
로 적어야 한다. 알려진 한계: 마젠타 거리 키 40 고정(alpha_from_matte), 매트가 원본과
어긋나면 가장자리에 배경이 묻는다. 색은 원본에서 오리므로 마젠타 번짐(디스필)은 생기지 않는다.

---
완성 장면 한 장을 codex 매트로 나눈다 — 픽셀은 원본 그대로 (마이디어편 방식).

Seedream 처럼 레이어를 다시 그리지 않는다. codex(`$imagegen` 편집)에게 두 장을 시킨다.

    plate  지정한 요소를 지우고 그 자리를 주변 배경으로 메운 같은 구도의 판
    matte  지정한 요소만 남기고 나머지를 순수 마젠타(#FF00FF)로 칠한 판

matte 에서 마젠타가 아닌 곳이 요소다. 그 자리의 **색은 원본에서 오려 온다** —
얼굴·글자·제품이 다시 그려지며 흔들리지 않는다. 붙어 있지 않은 덩어리는 따로
떼어 `<name>_NN.png` 로 저장한다(크기 순). plate 는 요소 바깥은 원본을 그대로 두고
요소가 빠진 자리만 생성된 메움을 쓴다(경계 7px 페더).

언제 쓰나: 요소가 서로 겹쳐 모션 때 가려진 쪽이 드러나는 도해·씬, 요소가 17개를
넘어 Seedream 상한에 걸리는 화면, 원본 픽셀 보존이 중요한 실존 인물 컷.

입력 JSON: {"<key>": {"image": 경로, "groups": [{"name": "buildings",
            "desc": "the five buildings standing on the stairs"}, ...]}}
그룹마다 matte 를 한 번, plate 는 모든 그룹을 함께 지운 판 한 번.

    python3 scripts/codex_matte_layers.py <jobs.json> -o <out_dir> [--only k] [-j 3]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MATTE = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러오세요:** {src}

첨부한 원본 그림을 레이어 분리용으로 편집합니다. 새로 그리는 것이 아닙니다.
캔버스 크기·구도·화면 배치를 원본과 정확히 같게 둡니다.

**남길 것:** {desc}
남길 것은 원본과 똑같은 자리, 똑같은 크기, 똑같은 모양과 색으로 둡니다.
옮기거나 키우거나 다시 그리지 않습니다.

**나머지 전부**(바닥, 배경, 모눈, 다른 사물, 글자)는 순수한 마젠타 #FF00FF 한 가지
색으로 꽉 채웁니다. 마젠타는 색 키입니다 — 투명이 아닙니다.

생성 후 이번 세션에서 만든 그림을 아래로 복사하세요:
{out}
"""

PLATE = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러오세요:** {src}

첨부한 원본 그림을 레이어 분리용으로 편집합니다. 캔버스 크기·구도·시점을 원본과
정확히 같게 둡니다.

**지울 것:** {desc}
지운 자리는 그 뒤에 있었을 배경(바닥·계단·지도·모눈·벽)으로 자연스럽게 이어 채웁니다.
지운 것 말고는 원본 그대로 둡니다. 새 사물·글자·사람을 더하지 않습니다.
같은 장면의 빈 배경판입니다.

생성 후 이번 세션에서 만든 그림을 아래로 복사하세요:
{out}
"""


def codex(prompt: str, out: Path, timeout: int) -> bool:
    # 늦게 불러온다 — 이 브랜치의 codex_cli 에는 claim_session_image 가 없어(로컬 전용이던
    # 스크립트) import 가 실패하면 폐기 안내조차 못 띄운다.
    from auto_agent.utils.codex_cli import claim_session_image, imagegen_model_args
    try:
        r = subprocess.run(["codex", "exec", *imagegen_model_args(), "--skip-git-repo-check",
                            "--sandbox", "workspace-write", prompt],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
        claim_session_image((r.stdout or "") + (r.stderr or ""), out)
    except subprocess.TimeoutExpired:
        pass
    return out.exists()


def alpha_from_matte(matte: Image.Image, size) -> np.ndarray:
    """마젠타에서 먼 정도로 알파를 만든다(키 40, 디스필 없음)."""
    m = np.asarray(matte.convert("RGB").resize(size, Image.LANCZOS)).astype(np.int32)
    dist = np.sqrt((m[..., 0] - 255) ** 2 + (m[..., 1] - 0) ** 2 + (m[..., 2] - 255) ** 2)
    a = np.clip((dist - 40) * 4, 0, 255).astype(np.uint8)
    return a


def components(alpha: np.ndarray, min_px: int):
    """붙어 있는 덩어리끼리 나눈다. 작은 조각은 버리지 않고 가장 가까운 큰 덩어리에 붙인다.

    버리면 배경판에서는 지워진 채라 화면에서 사라진다 — 한화편 #58 의 「지배인 김종희」
    이름표, #1 의 말풍선이 그랬다. 글자·말풍선처럼 작은 것은 곁의 주인과 함께 움직인다.
    """
    from scipy import ndimage
    lab, n = ndimage.label(alpha > 127)
    big, small = [], []
    for i in range(1, n + 1):
        m = lab == i
        cnt = int(m.sum())
        (big if cnt >= min_px else small).append(m)
    if not big:
        big, small = small[:1], small[1:]
    cents = [np.argwhere(m).mean(0) for m in big]
    for m in small:
        c = np.argwhere(m).mean(0)
        k = int(np.argmin([np.hypot(*(c - x)) for x in cents]))
        big[k] = big[k] | m
    out = []
    for m in big:
        ys, xs = np.nonzero(m)
        out.append((len(xs), (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1), m))
    return sorted(out, key=lambda t: -t[0])


def run(key: str, job: dict, root: Path, timeout: int) -> dict:
    d = root / key
    d.mkdir(parents=True, exist_ok=True)
    src = Path(job["image"]).resolve()
    orig = Image.open(src).convert("RGBA")
    W, H = orig.size
    o = np.asarray(orig)
    elements, union = [], np.zeros((H, W), np.uint8)
    for g in job["groups"]:
        mp = d / f"_matte_{g['name']}.png"
        if not mp.exists() and not codex(MATTE.format(src=src, desc=g["desc"], out=mp.resolve()), mp, timeout):
            return {"key": key, "error": f"matte {g['name']} 실패"}
        a = alpha_from_matte(Image.open(mp), (W, H))
        union = np.maximum(union, a)
        for i, (_, (l, t, r, b), mask) in enumerate(components(a, int(W * H * 0.0004))):
            rgba = o.copy()
            rgba[..., 3] = np.where(mask, a, 0)
            fn = f"{g['name']}_{i:02d}.png"
            Image.fromarray(rgba[t:b, l:r]).save(d / fn)
            elements.append({"layer": fn, "name": g["name"], "bbox": [int(l), int(t), int(r), int(b)],
                             "kind": g.get("kind", "object"), "motion": g.get("motion")})
    pp = d / "_plate_raw.png"
    all_desc = "; ".join(g["desc"] for g in job["groups"])
    if not pp.exists() and not codex(PLATE.format(src=src, desc=all_desc, out=pp.resolve()), pp, timeout):
        return {"key": key, "error": "plate 실패"}
    plate = Image.open(pp).convert("RGBA").resize((W, H), Image.LANCZOS)
    # 요소 자리(조금 넓혀서)만 생성 메움을 쓰고, 바깥은 원본 그대로
    m = Image.fromarray(union).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(7))
    bg = Image.composite(plate, orig, m)
    bg.save(d / "background.png")
    elements.insert(0, {"layer": "background.png", "name": "background", "bbox": None, "kind": "background"})
    (d / "elements.json").write_text(json.dumps({"key": key, "source": str(src), "method": "codex_matte",
                                                 "pixel_policy": "원본 RGB · 생성 매트(알파)만 사용",
                                                 "elements": elements}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return {"key": key, "layers": len(elements)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jobs", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--only")
    ap.add_argument("-j", "--jobs-n", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--approved", default="",
                    help="폐기된 경로 — 사용자 승인 사유(예외). 없으면 실행하지 않는다")
    a = ap.parse_args()
    if not a.approved.strip():
        print("codex 매트 분리는 폐기됐다 — scripts/layerize_scenes.py(fal Seedream 5.0)를 쓴다.\n"
              "예외로 꼭 써야 하면 사용자 승인 사유를 --approved \"…\" 로 적는다.", file=sys.stderr)
        return 2
    print(f"[예외 실행] 승인 사유: {a.approved}", flush=True)
    jobs = json.loads(a.jobs.read_text(encoding="utf-8"))
    keys = [k for k in jobs if not a.only or k in a.only.split(",")]
    with ThreadPoolExecutor(max_workers=a.jobs_n) as ex:
        for r in ex.map(lambda k: run(k, jobs[k], a.out, a.timeout), keys):
            print(f"  {'✗' if r.get('error') else '✓'} {r['key']} {r.get('layers', '')} {r.get('error', '')}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
