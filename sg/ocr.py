"""OCR 결과 합치기: 투명 PNG를 흰/검은 배경에 합성해 다시 읽은 결과를 기존 결과 뒤에 덧붙인다(기존 번호 유지)."""
import re

SYL = re.compile(r"[가-힣]")


def _overlap(a, b):
    ax, ay, aw, ah = a; bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx)); iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    return ix * iy / max(1e-6, min(aw * ah, bw * bh))


def merge_items(base, extra, min_conf=0.5, min_syl=2, max_overlap=0.3):
    out = list(base)
    for e in extra:
        if e["conf"] < min_conf or len(SYL.findall(e["text"])) < min_syl:
            continue
        # 겹쳐도 상대가 낮은 신뢰도의 잡음 읽기면 막지 않음(잡음 항목은 번역 단계에서 __SKIP__)
        if any(_overlap(e["box"], o["box"]) > max_overlap and o["conf"] >= min_conf for o in out):
            continue
        out.append(e)
    return out
