"""프리미어 층 오디오 믹스.  usage:
  audio_mix.py <EP> ko-identity [--key-base clip|media]   한국어 원래 재료를 워프 없이 다시 섞어 유튜브 원본과 대조(믹서 검증)
  audio_mix.py <EP> <lang>                                  영어 등: 내레이션 + AE 효과음(파트 mp4) + 효과음 wav + BGM + 아웃트로 BGM → render/<lang>/mix.wav
볼륨: 프리미어 클립 Level(선형)·키프레임을 중첩 단계마다 곱함. 키프레임 시각 기준(key_base)은 ko-identity로 정해 master_config에 기록."""
import json, os, re, subprocess, sys, unicodedata
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.audiomix import flatten, to_master, warp_piece, sound_chunks, chunk_segments, join_fades
from sg.mixgraph import envelope, place
from sg.timemap import PiecewiseMap
from sg.edl import pr_to_master

SR = 48000
nfc = lambda s: unicodedata.normalize("NFC", s or "")


def decode(path, ss=0.0, dur=None, sr=SR, ch=2):
    args = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, ss):.4f}"] + (["-t", f"{dur:.4f}"] if dur else []) + \
           ["-i", path, "-f", "f32le", "-ac", str(ch), "-ar", str(sr), "-"]
    raw = subprocess.run(args, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, ch).copy()


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout.strip())


def lufs(path):
    err = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", path, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def narration_gain_db(ref_lufs, en_lufs):
    """영어 내레이션을 한국어 원본 녹음 라우드니스(평균)에 맞추는 dB. 기준 녹음이 없으면 실패(NaN 믹스 방지)."""
    if not ref_lufs:
        sys.exit("한국어 내레이션 기준 녹음을 찾지 못함(master_config parts.narration 파일이 src 안에 있어야 함)")
    return round(float(np.mean(ref_lufs)) - en_lufs, 2)


def level_gain(piece, w_t, n, key_base, edl=None, T=None):
    """조각이 출력 w_t초에 놓일 때 샘플별 볼륨(중첩 단계 곱).
    키프레임은 프리미어 시각 → 마스터 → 워프 T 로 출력 시각에 옮겨 평가(곡 전환 페이드가 줄어든 조각 안으로 따라옴).
    edl·T가 없으면 조각 안을 원래 속도로 본다(프리미어 시각 = pr_in + (출력-w_t))."""
    out = w_t + np.arange(n, dtype=np.float64) / SR
    g = np.ones(n, np.float32)
    for L in piece.get("levels") or [{"clip_start": piece["pr_in"], "clip_in": piece["src_in"], "gain": piece["gain"], "keys": piece["gain_keys"]}]:
        prk = [((L["clip_start"] + k) if key_base == "clip" else (L["clip_start"] + k - L["clip_in"]), v) for k, v in L["keys"]]
        if T is not None:
            keys = [[T(pr_to_master(edl, p)), v] for p, v in prk]
        else:
            keys = [[w_t + (p - piece["pr_in"]), v] for p, v in prk]
        g *= envelope(out, L["gain"], keys)
    return g


class Files:
    def __init__(self, ep, nas_lookup=None):
        self.dir = os.path.join(ep, "src", "audio"); self.nas = nas_lookup; self.cache = {}

    def path(self, name, file=None):
        p = os.path.join(self.dir, nfc(name))
        if os.path.exists(p):
            return p
        if self.nas and file:
            return self.nas(file)
        return None


def place_pieces(buf, pieces, T, files, key_base, log, label, edl, db=0.0):
    plan = []
    for p in pieces:
        f = files.path(p["name"], p.get("file"))
        if not f:
            log.setdefault("missing", []).append(p["name"]); continue
        w = warp_piece(p, T, duration(f))
        if w["dur"] > 0:
            plan.append({**w, "name": p["name"], "_p": p, "_f": f})
    for w in join_fades(sorted(plan, key=lambda w: w["t"])):
        x = decode(w["_f"], w["src_in"], w["dur"])
        place(buf, x, w["t"], SR, level_gain(w["_p"], w["t"], len(x), key_base, edl, T) * 10 ** (db / 20), w["fade_out"])
        log[label] = log.get(label, 0) + 1


def place_sfx(buf, items, edl, T, files, key_base, log):
    for it in items:
        f = files.path(it["name"], it.get("file"))
        if not f:
            log.setdefault("missing", []).append(it["name"]); continue
        win = it["end"] - it["start"]
        x = decode(f, it["in"], win)
        mono = x.mean(1)
        for a, b in sound_chunks(mono, SR):
            for sa, sb, m in chunk_segments(a, b, it["start"], 0.0, edl):     # 컷에 걸친 덩어리는 앞뒤만
                seg = x[int(sa * SR):int(sb * SR)]
                piece = {"pr_in": it["start"] + sa, "src_in": it["in"] + sa, "gain": it["gain"], "gain_keys": it["gain_keys"],
                         "levels": [{"clip_start": it["start"], "clip_in": it["in"], "gain": it["gain"], "keys": it["gain_keys"]}]}
                t = T(m)
                place(buf, seg, t, SR, level_gain(piece, t, len(seg), key_base, edl, T))
                log["sfx_chunks"] = log.get("sfx_chunks", 0) + 1


def env_db(x, sr, win=0.5):
    n = int(sr * win); k = len(x) // n
    return 20 * np.log10(np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1)) + 1e-6)


if __name__ == "__main__":
    ep, mode = sys.argv[1], sys.argv[2]
    a = sys.argv[3:]
    cfg = json.load(open(os.path.join(ep, "master_config.json"))); A = cfg["audio"]
    key_base = a[a.index("--key-base") + 1] if "--key-base" in a else A.get("key_base", "clip")
    edl = json.load(open(os.path.join(ep, "master/edl.json")))
    P = json.load(open(os.path.join(ep, "pr_timeline.json")))
    main = {s["uid"]: s for s in P}[A["main_seq_uid"]]
    tr = {t["index"]: t for t in main["tracks"] if t["kind"] == "audio"}
    log = {}
    if mode == "ko-identity":
        from scripts.audio_fetch import resolve
        T = PiecewiseMap.identity()
        files = Files(ep, lambda f: resolve(f.split("\\")[4:]) if f.startswith("\\\\") else None)
        total = edl["length"] + (edl["outro"]["dur"] if edl.get("outro") else 0)
        buf = np.zeros((int(total * SR) + SR, 2), np.float32)
        base = [dict(it, levels=[{"clip_start": it["start"], "clip_in": it["in"], "gain": it["gain"], "keys": it["gain_keys"]}],
                     pr_in=it["start"], pr_out=it["end"], src_in=it["in"]) for it in tr[0]["items"]]
        place_pieces(buf, to_master(base, edl), T, files, key_base, log, "track0", edl, A.get("ae_gain_db", 0.0))
        out = os.path.join(ep, "render", "ko"); os.makedirs(out, exist_ok=True)
    else:
        lang = mode
        W = json.load(open(os.path.join(ep, "build", lang, "warp.json")))
        T = PiecewiseMap(W["master"])
        files = Files(ep)
        rd = os.path.join(ep, "render", lang)
        vdur = duration(os.path.join(rd, "video_only.mp4"))
        buf = np.zeros((int(vdur * SR) + SR, 2), np.float32)
        # 내레이션: 한국어 원본 녹음과 같은 라우드니스
        nar = os.path.join(rd, "narration.wav")
        ref = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ep, "src")) for f in fs
               if nfc(f) in {nfc(p["narration"]) for p in cfg["parts"].values()}]
        gdb = narration_gain_db([lufs(r) for r in ref], lufs(nar))
        g = 10 ** ((gdb + A.get("ae_gain_db", 0.0)) / 20); log["narration_gain_db"] = gdb
        g_ae = 10 ** (A.get("ae_gain_db", 0.0) / 20)   # 프리미어 트랙 볼륨(파서가 못 읽음) 보정 — ko-identity 회귀로 정함
        BED = "--bed" in a                        # --bed: 배경음악만(삽입 구간용 — 원래 장면의 효과음·내레이션은 새 장면과 안 맞음) → bed.wav
        if not BED:
            place(buf, decode(nar), 0.0, SR, np.full(len(buf), g, np.float32))
        # AE 효과음: 파트 mp4 오디오를 미리보기와 같은 순서·시각으로
        t = 0.0
        order = []
        for c in edl["parts"]:
            if c["id"] not in order:
                order.append(c["id"])
        for pid in (order if not BED else []):
            pf = os.path.join(rd, f"part_{pid}.mp4")
            x = decode(pf)
            ga = np.full(len(x), g_ae, np.float32)
            for m0, m1, db in A.get("ae_duck", []):    # 유튜브판에서 줄인 AE 안 영상 클립 소리(원래 시각, dB) — 내레이션은 그대로
                a0, a1 = int((T(m0) - t) * SR), int((T(m1) - t) * SR)
                ga[max(0, a0):max(0, a1)] *= 10 ** (db / 20)
            place(buf, x, t, SR, ga); t += W["parts"][pid]["dur_new"]
            log["ae_parts"] = log.get("ae_parts", 0) + 1
        # 아웃트로 BGM(0트랙의 outro_bgm 클립)
        ob = [dict(it, levels=[{"clip_start": it["start"], "clip_in": it["in"], "gain": it["gain"], "keys": it["gain_keys"]}],
                   pr_in=it["start"], pr_out=it["end"], src_in=it["in"]) for it in tr[0]["items"] if nfc(it["name"]) == nfc(A["outro_bgm"])]
        place_pieces(buf, to_master(ob, edl), T, files, key_base, log, "outro_bgm", edl)
        out = rd
        cut_to = int(round(vdur * SR))                 # 영상 길이와 정확히 같게(쓸 때 자름)
    if A.get("sfx_track") is not None and not (mode != "ko-identity" and BED):   # 프리미어 효과음 트랙 없는 편(효과음이 AE 안에만)
        place_sfx(buf, tr[A["sfx_track"]]["items"], edl, T, files, key_base, log)
    place_pieces(buf, to_master(flatten(P, A["main_seq_uid"], A["bgm_tracks"]), edl), T, files, key_base, log, "bgm_pieces", edl,
                 A.get("bgm_gain_db", 0.0))   # BGM 트랙 볼륨 보정
    name = "identity_mix.wav" if mode == "ko-identity" else ("bed.wav" if "--bed" in a else "mix.wav")
    peak = float(np.abs(buf).max()); log["peak"] = round(peak, 3)
    if peak > 0.97:                                  # 클리핑 방지: 전체를 같은 비율로 낮춤(상대 레벨 유지)
        buf *= 0.97 / peak; log["master_gain_db"] = round(20 * np.log10(0.97 / peak), 2)
    log["clipped"] = int((np.abs(buf) >= 1.0).sum())
    if mode != "ko-identity":
        buf = buf[:cut_to]
    import wave
    with wave.open(os.path.join(out, name), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())
    print(json.dumps(log, ensure_ascii=False))
    if log.get("missing") and mode != "ko-identity":
        sys.exit(f"오디오 재료 없음 {sorted(set(log['missing']))} — audio_fetch.py 먼저")
    if mode == "ko-identity":
        sr = 8000
        ref = decode(os.path.join(ep, "yt_master.mp4"), sr=sr, ch=1)[:, 0]
        mix = decode(os.path.join(out, name), sr=sr, ch=1)[:, 0]
        e1, e2 = env_db(ref, sr), env_db(mix, sr)
        n = min(len(e1), len(e2))
        best = max(range(-4, 5), key=lambda L: np.corrcoef(e1[max(0, L):n + min(0, L)], e2[max(0, -L):n - max(0, L)])[0, 1])
        a1, a2 = e1[max(0, best):n + min(0, best)], e2[max(0, -best):n - max(0, best)]
        tt = np.arange(len(a1)) * 0.5
        keep = np.ones(len(a1), bool)
        for x0, x1 in A.get("identity_exclude", []):        # 재료가 없어 재현 못 하는 구간(사유는 config)
            keep &= ~((tt >= x0) & (tt < x1))
        a1, a2 = a1[keep], a2[keep]
        c = np.corrcoef(a1, a2)[0, 1]
        wins = [np.corrcoef(a1[i:i + 60], a2[i:i + 60])[0, 1] for i in range(0, len(a1) - 60, 60)]
        print(f"key_base={key_base} lag={best * 0.5:+.1f}s corr={c:.4f} min30s={np.nanmin(wins):.4f} "
              f"level_diff_db={np.median(a2 - a1):+.2f}")
