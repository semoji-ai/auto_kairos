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
