"""미리보기 오디오 배치: 번역 TTS와 nonverbal 원래 녹음 조각을 변환된 시각에."""
import os


def plan_audio(segments, warp, tts_dir):
    out = []
    for g in segments:
        if g.get("nonverbal"):
            out.append({"src_in": g["in"], "src_out": g["out"], "t": warp(g["in"]), "kind": "nonverbal", "id": g["id"]})
        else:
            out.append({"file": os.path.join(tts_dir, f"{g['id']}.mp3"), "t": warp(g["in"]), "id": g["id"]})
    return out


def part_to_wav(u, L, occ):
    """파트 시각 u → 내레이션 wav 시각. 파트 시각 = (L.st + wav*sx) * k + off (occ: graph.walk 출현별 변환)."""
    sx = (L.get("sx") or 100) / 100.0
    for o in occ:
        if o["span"][0] - 1e-6 <= u <= o["span"][1] + 1e-6 and o["k"]:
            return ((u - o["off"]) / o["k"] - L["st"]) / sx
    return None
