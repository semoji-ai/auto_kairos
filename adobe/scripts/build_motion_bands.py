"""애니메이션 컴포저 프리뷰를 재서 `adobe/data/motion-bands.json` 을 만든다.

왜 이렇게 하나
--------------
프리셋 본체(`.mhcitem`)는 `MHACCIPF` 로 암호화돼 있고 **열지 않는다.**
그런데 프리뷰(`.mhpreview.webm` 8,273편)는 평문이고, 그건 그 프리셋이
**실제로 그린 화면**이다. 프레임 단위로 재면 크기·위치·투명도 곡선이
그대로 나온다. 남의 자산을 뜯는 게 아니라 결과를 관찰하는 것이다.

여기서 나온 수치가 `motion_fx.jsx` 기본값의 근거다. 「오버슛 10% 쯤이
좋더라」가 아니라 상용 프리셋이 실제로 그린 값이다.

재는 방법
---------
배경색(가장자리 중앙값) 대비 마스크 → bbox 대각·중심·잉크 곡선.
**유지 구간(plateau)을 먼저 찾아** 기준 크기로 삼고, 그 앞뒤를 등장·퇴장으로
가른다. 꼬리를 기준으로 삼으면 퇴장 중인 크기가 기준이 되어 전부 어긋난다.

한계 — 읽을 때 주의할 것
-----------------------
`position` 계열의 「크기 곡선」은 프리셋이 크기를 움직인 게 아니라 화면 밖에서
들어오며 bbox 가 **잘린** 흔적이다. 크기 애니메이션으로 알고 쓰면 안 된다
(`SCALE_FAMILIES` 만 곡선을 쓴다).

사용
----
    python3 adobe/scripts/build_motion_bands.py            # 기본 설치 경로에서
    python3 adobe/scripts/build_motion_bands.py --root <프리뷰 폴더> --limit 200

애니메이션 컴포저가 깔려 있어야 한다. 없으면 기존 결과 파일이 그대로 쓰인다.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import statistics as st
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ac_measure import analyze  # noqa: E402

DEFAULT_ROOT = (Path.home() / "Library/Application Support/MisterHorse"
                / "ProductManager/Products")
OUT = Path(__file__).resolve().parents[1] / "data" / "motion-bands.json"

# 측정이 낸 계열 이름 → jsx 프리셋 이름
FAMILIES = {
    "overshoot_scale": "overshoot_scale_in",
    "scale": "scale_in",
    "bounce_scale": "bounce_scale_in",
    "overshoot_position": "overshoot_position_in",
    "position": "position_in",
    "fade": "fade_in",
}
SCALE_FAMILIES = {"overshoot_scale", "scale", "bounce_scale"}


def shape(x, s0, ov, pk, bk, pw):
    """motion_fx.jsx 의 shape() 를 옮긴 것. 곡선 피팅에 쓴다."""
    if x <= 0:
        return s0
    if x >= 1:
        return 1.0
    if ov <= 0:
        y = s0 + (1 - s0) * (1 - (1 - x) ** pw)
    elif x < pk:
        y = s0 + (1 + ov - s0) * (1 - (1 - x / pk) ** pw)
    else:
        v = (x - pk) / (1 - pk)
        y = 1 + ov * math.exp(-4 * v) * math.cos(v * math.pi * (0.5 + bk))
    if x > 0.8:
        y = 1 + (y - 1) * (1 - (x - 0.8) / 0.2)
    return y


def fit(curve, bk):
    """곡선 하나에 (정점, 부드러움) 을 맞춘다 → (rmse, peak, pw)."""
    n = len(curve)
    if n < 6:
        return None
    s0, ov = curve[0], max(curve) - 1
    return min(
        (math.sqrt(sum((shape(j / (n - 1), s0, ov, pk / 100, bk, pw / 10) - v) ** 2
                       for j, v in enumerate(curve)) / n), pk, pw)
        for pw in range(10, 41) for pk in range(15, 90, 5)
    )


def resample(c, n=15):
    if len(c) < 3:
        return None
    out = []
    for i in range(n):
        p = i * (len(c) - 1) / (n - 1)
        lo = int(p)
        hi = min(lo + 1, len(c) - 1)
        out.append(c[lo] + (c[hi] - c[lo]) * (p - lo))
    return out


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p))] if v else 0


def _one(p: str) -> dict:
    path = Path(p)
    try:
        return {"file": path.name, "product": path.parent.parent.name, **analyze(path)}
    except Exception as e:  # noqa: BLE001
        return {"file": path.name, "error": repr(e)}


def measure_all(root: Path, limit: int = 0) -> list[dict]:
    files = sorted(str(p) for p in root.rglob("*.mhpreview.webm"))
    if not files:
        raise SystemExit(f"프리뷰를 못 찾았습니다: {root}")
    if limit:
        files = files[:: max(1, len(files) // limit)][:limit]
    print(f"대상 {len(files)}편", flush=True)
    rows, done = [], 0
    with ProcessPoolExecutor(max(1, (os.cpu_count() or 4) - 2)) as ex:
        for r in ex.map(_one, files, chunksize=8):
            rows.append(r)
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{len(files)}", flush=True)
    return rows


def build(rows: list[dict], fit_cap: int = 400) -> dict:
    ok = [r for r in rows if not r.get("error") and r.get("kind") != "empty"]
    out = {
        "_출처": f"애니메이션 컴포저 프리뷰 {len(rows)}편 실측(유효 {len(ok)}편). "
                 "프리셋 본체는 암호화라 열지 않았고, 프리뷰가 그린 화면을 쟀다.",
        "_방법": "배경 대비 마스크 → bbox 대각/중심/잉크 곡선 → 유지 구간을 기준으로 "
                 "등장·퇴장을 갈라 정규화. peak/smooth 는 shape() 를 맞춰 얻었다.",
        "_주의": "기본값은 p50 이다. p10~p90 은 그 계열이 실제로 쓰는 범위이니, "
                 "슬라이더를 그 밖으로 미는 것은 이상한 게 아니라 드문 것이다. "
                 "position 계열의 median_curve 는 bbox 가 화면 밖에서 잘린 흔적이라 "
                 "크기 애니메이션으로 읽으면 안 된다.",
        "_만든이": "adobe/scripts/build_motion_bands.py",
        "families": {},
    }
    for name, kind in FAMILIES.items():
        g = [r for r in ok if r["kind"] == kind]
        if not g:
            continue
        ins = [r["in"] for r in g]
        bk = 2 if "bounce" in name else 0
        curves = [c for c in (resample(i["curve"]) for i in ins if i.get("curve")) if c]
        med = [st.median([c[i] for c in curves]) for i in range(15)] if curves else []
        fits = [f for f in (fit(i.get("curve") or [], bk) for i in ins[:fit_cap])
                if f and f[0] < 0.08]
        ent = {
            "n": len(g),
            "start_pct": [round(q([i["scale_edge"] * 100 for i in ins], p), 1) for p in (.1, .5, .9)],
            "overshoot_pct": [round(q([i["overshoot"] * 100 for i in ins], p), 1) for p in (.1, .5, .9)],
            "in_frames": [q([i["frames"] for i in ins], p) for p in (.1, .5, .9)],
            "out_frames": [q([r["out"]["frames"] for r in g], p) for p in (.1, .5, .9)],
            "peak_pct": round(st.median([f[1] for f in fits])) if fits else None,
            "smooth": round((st.median([f[2] for f in fits]) / 10 - 1) / 3 * 100) if fits else None,
            "fit_rmse": round(st.median([f[0] for f in fits]), 4) if fits else None,
            "median_curve": [round(v, 4) for v in med],
        }
        if "position" in name:
            ent["move_pct"] = [round(q([r["travel"] * 100 for r in g], p), 1) for p in (.1, .5, .9)]
            ent["directions"] = dict(collections.Counter(r["direction"] for r in g).most_common())
        out["families"][name] = ent

    b = [r for r in ok if r["kind"].startswith("burst")]
    if b:
        out["families"]["burst"] = {
            "n": len(b),
            "attack_frames": [q([r["attack"] for r in b], p) for p in (.1, .5, .9)],
            "decay_frames": [q([r["decay"] for r in b], p) for p in (.1, .5, .9)],
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--limit", type=int, default=0, help="표본만 (0=전량)")
    ap.add_argument("--raw", type=Path, help="측정 원자료 jsonl 저장/재사용")
    ap.add_argument("-o", "--out", type=Path, default=OUT)
    a = ap.parse_args()

    if a.raw and a.raw.exists():
        rows = [json.loads(l) for l in a.raw.open(encoding="utf-8")]
        print(f"원자료 재사용: {a.raw} ({len(rows)}편)")
    else:
        rows = measure_all(a.root, a.limit)
        if a.raw:
            with a.raw.open("w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    bands = build(rows)
    a.out.write_text(json.dumps(bands, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"→ {a.out}")
    for k, v in bands["families"].items():
        if v.get("peak_pct") is not None:
            print(f"  {k:20s} n={v['n']:5d} 시작{v['start_pct'][1]:6.1f} "
                  f"오버슛{v['overshoot_pct'][1]:5.1f} 등장{v['in_frames'][1]:3d} "
                  f"퇴장{v['out_frames'][1]:3d} 정점{v['peak_pct']:3d} "
                  f"부드{v['smooth']:3d} rmse{v['fit_rmse']}")


if __name__ == "__main__":
    main()
