#!/usr/bin/env python3
"""이미지가 미세한 결(빗금·그레인)로 지저분해졌는지 검출한다.

코덱스 image_gen으로 같은 이미지를 여러 번 고치면 화면에 미세한 결이 깔린다.
인물 얼굴까지 번지면 못 쓴다. EP07 씬 18에서 실제로 나왔다.

**원리.** 세모지 그림체는 평면 색면이라 넓은 면의 밝기가 거의 일정하다.
결이 깔리면 그 평탄해야 할 면에 고주파가 남는다. 굵은 구조를 뺀 나머지를
평탄 영역에서만 재면, 깨끗한 그림은 값이 낮고 지저분한 그림은 높다.

푸리에로 사선 봉우리를 찾는 방법도 해 봤으나 건물·창틀 같은 정상 구조와
구별되지 않아 버렸다.

    python3 scripts/detect_hatch.py <이미지|폴더> [--thr 30]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image


def _boxblur(a: np.ndarray, k: int) -> np.ndarray:
    p = np.pad(a, k, mode="edge")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    s = 2 * k + 1
    return (c[s:, s:] - c[:-s, s:] - c[s:, :-s] + c[:-s, :-s]) / (s * s)


def grain_score(path: Path, size: int = 768) -> float:
    """평탄한 색면에 남은 미세 결의 세기. 낮을수록 깨끗하다."""
    im = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32) / 255.0
    hi = a - _boxblur(a, 3)                      # 굵은 구조를 뺀 미세 성분
    coarse = _boxblur(a, 12)
    gy, gx = np.gradient(coarse)
    grad = np.abs(gy) + np.abs(gx)
    flat = grad < np.percentile(grad, 55)        # 평탄해야 할 면만
    return float(hi[flat].std() * 1000)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", type=Path)
    ap.add_argument("--thr", type=float, default=30.0)
    ap.add_argument("-o", "--out", type=Path)
    args = ap.parse_args()

    files = sorted(args.target.rglob("*.png")) if args.target.is_dir() else [args.target]
    rows = []
    for f in files:
        try:
            rows.append({"file": str(f), "score": round(grain_score(f), 1)})
        except Exception as e:
            print(f"  ! {f.name} {type(e).__name__}")
    rows.sort(key=lambda r: -r["score"])
    bad = [r for r in rows if r["score"] >= args.thr]
    for r in bad:
        p = Path(r["file"])
        print(f"  {r['score']:6.1f}  {p.parent.parent.name}/{p.name}")
    print(f"\n검사 {len(rows)}장 / 기준 {args.thr} 이상 {len(bad)}장")
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
