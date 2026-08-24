"""characters.png를 연결 컴포넌트로 분리하여 캐릭터별 cropped PNG + 좌표 기록.

⚠️ 대체됨 — 시드림 layerize가 요소별 PNG와 bbox를 직접 준다.
   연결요소로 크롭하던 이 방식은 인물이 겹치면 한 덩어리로 붙었다.


각 씬 v2 폴더의 characters.png를 처리:
- alpha 마스크 → connected components (8-neighbor BFS)
- min_area 이상 컴포넌트만 유지 (노이즈 제거)
- 가까운 컴포넌트는 dilation으로 병합 (캐릭터 내부의 분리된 머리/팔/소품)
- bbox 크롭 → characters/char_{i}.png
- layers.json 갱신: characters 배열에 개별 항목 추가
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from scene_layer_animate import resolve_project_dir  # noqa: E402


def dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """간단한 box dilation r회."""
    if r <= 0: return mask
    out = mask.copy()
    for _ in range(r):
        out[1:] |= out[:-1].copy()
        out[:-1] |= out[1:].copy()
        out[:,1:] |= out[:,:-1].copy()
        out[:,:-1] |= out[:,1:].copy()
    return out


def connected_components(mask: np.ndarray) -> list[tuple[int,int,int,int,np.ndarray]]:
    """8-neighbor CC. 반환: (xmin, ymin, xmax, ymax, label_mask)."""
    h, w = mask.shape
    visited = np.zeros_like(mask)
    comps = []
    for i in range(h):
        for j in range(w):
            if not mask[i,j] or visited[i,j]: continue
            q = deque([(i,j)]); visited[i,j] = True
            ymin=ymax=i; xmin=xmax=j
            pixels = []
            while q:
                ci, cj = q.popleft()
                pixels.append((ci,cj))
                if ci<ymin: ymin=ci
                if ci>ymax: ymax=ci
                if cj<xmin: xmin=cj
                if cj>xmax: xmax=cj
                for di in (-1,0,1):
                    for dj in (-1,0,1):
                        if di==0 and dj==0: continue
                        ni, nj = ci+di, cj+dj
                        if 0<=ni<h and 0<=nj<w and mask[ni,nj] and not visited[ni,nj]:
                            visited[ni,nj] = True; q.append((ni,nj))
            label_mask = np.zeros_like(mask)
            for p in pixels: label_mask[p] = True
            comps.append((xmin, ymin, xmax, ymax, label_mask))
    return comps


def split(chars_path: Path, layers_path: Path, alpha_thresh: int = 64,
          dilate_r: int = 12, min_area_pct: float = 0.4) -> int:
    img = Image.open(chars_path).convert("RGBA")
    arr = np.array(img)
    W, H = img.size
    alpha = arr[:,:,3]
    mask = alpha > alpha_thresh
    if not mask.any():
        print(f"  ⚠ 알파 없음 — 스킵"); return 0

    # 캐릭터 인근 영역 병합용 dilation
    merged = dilate(mask, dilate_r)
    comps = connected_components(merged)
    total_area = H * W
    min_area = int(total_area * min_area_pct / 100)  # 0.4% 미만 노이즈 제거

    char_dir = chars_path.parent / "characters"
    char_dir.mkdir(exist_ok=True)
    # 기존 cropped 파일 정리
    for old in char_dir.glob("char_*.png"): old.unlink()

    layers = json.loads(layers_path.read_text(encoding="utf-8"))
    # 기존 단일 characters 항목 백업·치환
    layers["characters_combined"] = layers.get("characters", [])
    new_chars = []

    kept = 0
    # bbox 면적 큰 순으로 정렬 (인덱스 안정성)
    comps.sort(key=lambda c: -((c[2]-c[0])*(c[3]-c[1])))
    for k, (xmin, ymin, xmax, ymax, lm) in enumerate(comps):
        area_px = lm.sum()
        if area_px < min_area: continue
        # 원본 마스크와 교집합으로 crop (dilation 결과 아닌 실제 픽셀)
        real_mask = mask & lm
        if not real_mask.any(): continue
        ys, xs = np.where(real_mask)
        bx1, by1, bx2, by2 = int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1
        sub = arr[by1:by2, bx1:bx2].copy()
        sub_mask = real_mask[by1:by2, bx1:bx2]
        sub[:,:,3] = np.where(sub_mask, sub[:,:,3], 0).astype(np.uint8)
        out_name = f"char_{kept:02d}.png"
        Image.fromarray(sub, "RGBA").save(char_dir / out_name)
        new_chars.append({
            "name": f"char_{kept}",
            "kind": "from_scene_split",
            "src": f"{chars_path.parent.name}/characters/{out_name}",
            "intrinsic_size": {"width": int(bx2-bx1), "height": int(by2-by1)},
            "source_canvas_size": {"width": W, "height": H},
            "source_bbox": {"x": bx1, "y": by1, "width": int(bx2-bx1), "height": int(by2-by1)},
            "z": 10 + kept,
            # 까딱임 — 반주기 10프레임 · 100 → 101 · ease-in-out.
            # `amplitude_pct`/`period_s` 는 SemojiLayerScene 이 읽지 않는 이름이라
            # 그동안 조용히 기본값으로 떨어지고 있었다. 정본 이름으로 적는다.
            # **폭과 주기는 모두 같고 위상만 흩는다** — 사람마다 주기가 다르면
            # 같은 인물이 씬마다 다르게 까딱인다. 한 박자로 맞으면 기계 같으니
            # 시작 시점만 어긋나게 둔다.
            "motion": {"type": "feet_bob", "max_scale": 1.01,
                       "period_frames": 20,
                       "phase_offset_frames": (kept * 7) % 20},
        })
        kept += 1

    layers["characters"] = new_chars
    layers_path.write_text(json.dumps(layers, ensure_ascii=False, indent=2), encoding="utf-8")
    return kept


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--scenes", help="쉼표 구분 (생략 시 v2 폴더 전체)")
    args = p.parse_args()

    pdir = resolve_project_dir(args.project)
    img_root = pdir / "remotion" / "public" / "images"
    if args.scenes:
        targets = [int(x) for x in args.scenes.split(",")]
    else:
        targets = sorted(int(d.name.split("_")[1]) for d in img_root.glob("scene_*_v2") if d.is_dir())

    for n in targets:
        d = img_root / f"scene_{n:03d}_v2"
        cp = d / "characters.png"
        lp = d / "layers.json"
        if not cp.exists() or not lp.exists():
            print(f"scene {n:>2}: ⚠ 누락 (characters.png={cp.exists()}, layers.json={lp.exists()})"); continue
        kept = split(cp, lp)
        print(f"scene {n:>2}: {kept} 캐릭터 분리")


if __name__ == "__main__":
    main()
