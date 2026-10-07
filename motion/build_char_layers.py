"""GPT 제자리 편집 에셋 → 씬 좌표 그대로의 인물 레이어 + 구멍 메운 배경.
(v2: 원본 픽셀을 마스크로 오리던 방식은 가장자리가 지저분해 폐기 — 에셋 자체를 쓴다)

GPT에게 "인물만 남기고 나머지를 초록으로" 제자리 편집을 시키면 구도가 거의 그대로 유지된다.
그 결과는 **마스크 모양으로만** 쓰고 픽셀은 원본에서 가져온다 → 원위치·원화질.
뒤에 선 인물 마스크에서 앞 인물 영역을 빼 겹침을 정리하고, 배경은 인물 자리를 인페인팅한다
(까딱임 진폭이 작아 드러나는 건 가장자리 몇 px뿐).
    .venv/bin/python build_char_layers.py
"""
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).parent
GEN, MASKS = ROOT / "assets/gen", ROOT / "assets/masks"
OUT = ROOT / "video/public/layers"
# 씬별 인물 마스크 — 뒤→앞 순서
SCENES = {
    "s01_family": ["family_mom", "family_dad", "family_son"],
    "s02_dock": ["dock_left", "dock_right", "dock_mid"],
    "s05_factory": ["factory_man"],  # 가마솥은 FG(전경 고정 레이어)
    "s06_crowd": ["crowd_1", "crowd_2", "crowd_3", "crowd_4"],
}
FG = {"s05_factory": ["factory_cauldron"], "s01_family": ["family_bowls"]}
KEYED = MASKS / "keyed"   # remove_chroma_key.py(soft-matte·despill) 결과
PLATES = ROOT / "assets/layers"   # image-layerkit이 만든 GPT 인물 제거 배경판
# 제자리 편집으로 다시 그린 배경판(그릇·가마솥 위치 보존) — layerkit 판보다 우선
PLATE_OVERRIDE = {"s01_family": MASKS / "plate_family.png", "s05_factory": MASKS / "plate_factory.png"}
GREEN = np.array([0, 177, 64])


def mask_of(name, W, H, orig):
    m = cv2.cvtColor(cv2.imread(str(MASKS / f"{name}.png")), cv2.COLOR_BGR2RGB)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(int)
    keep = np.abs(m - GREEN).sum(2) > 110
    # GPT가 원본과 다르게 그린 곳(색 불일치)은 버린다 — 원본에 없는 걸 오려내지 않게
    agree = np.abs(m - orig.astype(int)).sum(2) < 150
    k = (keep & agree).astype(np.uint8) * 255
    k = cv2.morphologyEx(k, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    k = cv2.morphologyEx(k, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    # 가장 큰 덩어리들만(잔티 제거): 면적 1.5% 이상 컴포넌트
    n, lab, st, _ = cv2.connectedComponentsWithStats(k)
    keepl = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.015 * st[1:, cv2.CC_STAT_AREA].sum()]
    k = np.isin(lab, keepl).astype(np.uint8) * 255
    # 구멍 메우기(인물 내부의 작은 누락)
    ff = k.copy(); h_, w_ = k.shape
    cv2.floodFill(ff, np.zeros((h_ + 2, w_ + 2), np.uint8), (0, 0), 255)
    holes = cv2.bitwise_not(ff)
    small = holes.copy()
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(holes)
    for i in range(1, n2):
        if st2[i, cv2.CC_STAT_AREA] > 4000:
            small[lab2 == i] = 0
    return cv2.bitwise_or(k, small)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    specs = {}
    for sc, names in SCENES.items():
        orig = cv2.cvtColor(cv2.imread(str(GEN / f"{sc}.png")), cv2.COLOR_BGR2RGB)
        H, W = orig.shape[:2]
        masks = [mask_of(n, W, H, orig) for n in names]
        fgm = [mask_of(n, W, H, orig) for n in FG.get(sc, [])]
        for fm in fgm:   # 전경에 가려지는 부분은 인물 레이어에서 뺀다
            masks = [cv2.bitwise_and(m, cv2.bitwise_not(fm)) for m in masks]
        # 겹침 정리: 앞 인물이 이긴다
        for i in range(len(masks)):
            for j in range(i + 1, len(masks)):
                masks[i] = cv2.bitwise_and(masks[i], cv2.bitwise_not(masks[j]))
        union = np.zeros((H, W), np.uint8)
        chars = []
        for n, m in zip(names, masks):
            # 레이어 = GPT가 씬 좌표 그대로 초록 위에 따로 그린 에셋(키잉본). 원본을 오리지 않는다
            L = cv2.imread(str(KEYED / f"{n}.png"), cv2.IMREAD_UNCHANGED)
            L = cv2.resize(L, (W, H), interpolation=cv2.INTER_AREA)
            p = OUT / f"{sc}__{n}.png"
            cv2.imwrite(str(p), L)
            m = cv2.bitwise_or(m, (L[..., 3] > 128).astype(np.uint8) * 255)
            ys, xs = np.where(L[..., 3] > 128)
            chars.append({"png": f"layers/{p.name}", "bbox": [round(xs.min() / W, 4), round(ys.min() / H, 4), round(xs.max() / W, 4), round(ys.max() / H, 4)]})
            union = cv2.bitwise_or(union, m)
        # 배경 구멍: GPT 배경판으로 채운다(없으면 인페인팅). 경계는 부드럽게 섞는다
        hole = cv2.dilate(union, np.ones((25, 25), np.uint8))
        plate_p = PLATE_OVERRIDE.get(sc, PLATES / sc / "bg.png")
        if plate_p.exists():
            plate = cv2.resize(cv2.cvtColor(cv2.imread(str(plate_p)), cv2.COLOR_BGR2RGB), (W, H)).astype(float)
        else:
            plate = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(orig, cv2.COLOR_RGB2BGR), hole, 9, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB).astype(float)
        # 배경도 따로 그린 판을 통째로 쓴다 — 원본과 섞으면 미세 어긋남이 잔상으로 보인다
        bg = plate.astype(np.uint8) if plate_p.exists() else (orig * (1 - cv2.GaussianBlur(hole, (31, 31), 0)[..., None] / 255.0) + plate * cv2.GaussianBlur(hole, (31, 31), 0)[..., None] / 255.0).astype(np.uint8)
        cv2.imwrite(str(OUT / f"{sc}__bg.jpg"), cv2.cvtColor(bg, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 94])
        fgs = []
        for n, fm in zip(FG.get(sc, []), fgm):
            p = OUT / f"{sc}__{n}.png"
            cv2.imwrite(str(p), cv2.resize(cv2.imread(str(KEYED / f"{n}.png"), cv2.IMREAD_UNCHANGED), (W, H), interpolation=cv2.INTER_AREA))
            fgs.append(f"layers/{p.name}")
        specs[sc] = {"bg": f"layers/{sc}__bg.jpg", "ar": round(H / W, 5), "chars": chars, "fg": fgs}
        print(sc, [(c["png"].split("__")[1], c["bbox"]) for c in chars])
    (ROOT / "video/src/layers.json").write_text(json.dumps(specs, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
