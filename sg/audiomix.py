"""프리미어 층 오디오(효과음 wav·BGM) → 마스터 시각 조각 → 워프 배치."""
import numpy as np
from sg.edl import pr_to_master

FADE = 10 / 29.97


def flatten(timeline, main_uid, track_indices, _off=0.0, _gain=1.0, _win=None, _levels=()):
    """메인 시퀀스의 지정 audio 트랙을 중첩 시퀀스까지 풀어 프리미어 시각 조각 목록으로.
    levels = 바깥→안 클립마다 {clip_start(절대 프리미어 시각), clip_in, gain, keys} — 볼륨은 단계별로 곱한다."""
    seqs = {s["uid"]: s for s in timeline}
    out = []
    for t in seqs[main_uid]["tracks"]:
        if t["kind"] != "audio" or (track_indices is not None and t["index"] not in track_indices):
            continue
        for it in t["items"]:
            a, b = it["start"], it["end"]
            if _win is not None:                       # 중첩 시퀀스: 바깥 클립이 보여 주는 구간만
                a, b = max(a, _win[0]), min(b, _win[1])
                if b <= a:
                    continue
            lv = {"clip_start": round(_off + it["start"], 4), "clip_in": it["in"], "gain": it.get("gain", 1.0),
                  "keys": it.get("gain_keys", [])}
            if it["seq_uid"]:
                shift = _off + it["start"] - it["in"]
                w_out = it["out"] if it["out"] > it["in"] else it["in"] + (it["end"] - it["start"])   # 중첩 클립은 out=0으로 저장됨
                out += flatten(timeline, it["seq_uid"], None, shift, _gain * it.get("gain", 1.0), (it["in"], w_out),
                               _levels + (lv,))
                continue
            out.append({"name": it["name"], "file": it["file"], "pr_in": round(_off + a, 4), "pr_out": round(_off + b, 4),
                        "src_in": round(it["in"] + (a - it["start"]), 4), "gain": _gain * it.get("gain", 1.0),
                        "gain_keys": it.get("gain_keys", []), "levels": list(_levels) + [lv]})
    return sorted(out, key=lambda x: x["pr_in"])


def to_master(pieces, edl):
    """컷을 빼고 마스터 시각(m_in, m_out) 부여. 컷에 걸친 조각은 둘로 나눈다."""
    out = []
    for p in pieces:
        segs, a = [], p["pr_in"]
        for c in sorted(edl["cuts"], key=lambda c: c["pr_in"]):
            if c["pr_out"] <= a or c["pr_in"] >= p["pr_out"]:
                continue
            if c["pr_in"] > a:
                segs.append((a, c["pr_in"]))
            a = max(a, c["pr_out"])
        if a < p["pr_out"]:
            segs.append((a, p["pr_out"]))
        for s, e in segs:
            out.append({**p, "pr_in": round(s, 4), "pr_out": round(e, 4),
                        "m_in": round(pr_to_master(edl, s), 4), "m_out": round(pr_to_master(edl, e), 4),
                        "src_in": round(p["src_in"] + (s - p["pr_in"]), 4)})
    return out


def warp_piece(p, T, src_len):
    """시작 T(m_in), 끝 T(m_out). 길어지면 같은 소스를 더 재생(소스 끝에서 멈춤), 짧아지거나 소스가 모자라면 페이드."""
    t0, t1 = T(p["m_in"]), T(p["m_out"])
    dur, orig = t1 - t0, p["m_out"] - p["m_in"]
    room = src_len - p["src_in"]
    fade = FADE if (dur < orig - 1e-6 or dur > room + 1e-6) else 0.0
    return {"t": round(t0, 4), "dur": round(min(dur, room), 4), "src_in": p["src_in"], "fade_out": round(fade, 4)}


def join_fades(warped):
    """같은 곡의 다음 조각이 출력에서 바로 이어지면(하위 클립 편집점) 끝 페이드를 빼서 소리 구멍을 막는다."""
    out = [dict(w) for w in warped]
    for a, b in zip(out, out[1:]):
        if a["name"] == b["name"] and abs(b["t"] - (a["t"] + a["dur"])) < 0.02:
            a["fade_out"] = 0.0
    return out


def chunk_segments(a, b, file_pr_in, file_src_in, edl):
    """효과음 wav 덩어리 [a,b](wav 시각) → 컷을 뺀 [(src_a, src_b, 마스터 시작)] — 컷에 걸치면 앞뒤만 남김."""
    piece = {"pr_in": file_pr_in + (a - file_src_in), "pr_out": file_pr_in + (b - file_src_in), "src_in": a}
    return [(x["src_in"], round(x["src_in"] + (x["pr_out"] - x["pr_in"]), 4), x["m_in"]) for x in to_master([piece], edl)]


def sound_chunks(x, sr, thresh_db=-45.0, min_silence=0.15):
    """효과음 wav를 무음(thresh_db 미만이 min_silence초 이상) 기준으로 소리 덩어리 [시작, 끝](초)로."""
    hop = int(sr * 0.01)
    n = len(x) // hop
    rms = np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    loud = 20 * np.log10(rms) > thresh_db
    chunks, start, quiet = [], None, 0
    for i, v in enumerate(loud):
        if v:
            start = i if start is None else start
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet * 0.01 >= min_silence:
                chunks.append([round(start * 0.01, 3), round((i - quiet + 1) * 0.01, 3)])
                start, quiet = None, 0
    if start is not None:
        chunks.append([round(start * 0.01, 3), round(n * 0.01, 3)])
    return chunks


def place_chunk(a, b, file_pr_in, file_src_in, edl, T):
    """효과음 wav 시각 [a,b] → 프리미어 → 마스터 → T. 덩어리 길이 유지, 컷 안이면 None."""
    pa = file_pr_in + (a - file_src_in)
    m = pr_to_master(edl, pa, clamp=False)
    if m is None:
        return None
    return {"t": round(T(m), 4), "src_in": a, "dur": round(b - a, 4)}
