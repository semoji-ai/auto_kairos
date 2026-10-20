"""프리미어 층 오디오 믹스.  usage:
  audio_mix.py <EP> ko-identity [--key-base clip|media]   한국어 원래 재료를 워프 없이 다시 섞어 유튜브 원본과 대조(믹서 검증)
  audio_mix.py <EP> <lang>                                  영어 등: 내레이션 + AE 효과음(파트 mp4) + 효과음 wav + BGM + 아웃트로 BGM → render/<lang>/mix.wav
볼륨: 프리미어 클립 Level(선형)·키프레임을 중첩 단계마다 곱함. 키프레임 시각 기준(key_base)은 ko-identity로 정해 master_config에 기록."""
import json, os, re, subprocess, sys, unicodedata
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.audiomix import flatten, to_master, warp_piece, sound_chunks
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


def level_gain(piece, w_t, n, key_base):
    """조각이 출력 w_t초에 놓일 때 샘플별 볼륨(중첩 단계 곱). 조각 안은 소스 그대로 흐르므로 프리미어 시각 = pr_in + (출력-w_t)."""
    pr = piece["pr_in"] + np.arange(n, dtype=np.float64) / SR
    g = np.ones(n, np.float32)
    for L in piece.get("levels") or [{"clip_start": piece["pr_in"], "clip_in": piece["src_in"], "gain": piece["gain"], "keys": piece["gain_keys"]}]:
        keys = [[(L["clip_start"] + k) if key_base == "clip" else (L["clip_start"] + k - L["clip_in"]), v] for k, v in L["keys"]]
        g *= envelope(pr, L["gain"], keys)
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


def place_pieces(buf, pieces, T, files, key_base, log, label):
    for p in pieces:
        f = files.path(p["name"], p.get("file"))
        if not f:
            log.setdefault("missing", []).append(p["name"]); continue
        w = warp_piece(p, T, duration(f))
        if w["dur"] <= 0:
            continue
        x = decode(f, w["src_in"], w["dur"])
        place(buf, x, w["t"], SR, level_gain(p, w["t"], len(x), key_base), w["fade_out"])
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
            pa = it["start"] + a
            m = pr_to_master(edl, pa, clamp=False)
            if m is None:
                continue
            seg = x[int(a * SR):int(b * SR)]
            piece = {"pr_in": pa, "src_in": it["in"] + a, "gain": it["gain"], "gain_keys": it["gain_keys"],
                     "levels": [{"clip_start": it["start"], "clip_in": it["in"], "gain": it["gain"], "keys": it["gain_keys"]}]}
            t = T(m)
            place(buf, seg, t, SR, level_gain(piece, t, len(seg), key_base))
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
        place_pieces(buf, to_master(base, edl), T, files, key_base, log, "track0")
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
        ko_l = float(np.mean([lufs(r) for r in ref])); en_l = lufs(nar)
        g = 10 ** ((ko_l - en_l) / 20); log["narration_gain_db"] = round(ko_l - en_l, 2)
        place(buf, decode(nar), 0.0, SR, np.full(len(buf), g, np.float32))
        # AE 효과음: 파트 mp4 오디오를 미리보기와 같은 순서·시각으로
        t = 0.0
        order = []
        for c in edl["parts"]:
            if c["id"] not in order:
                order.append(c["id"])
        for pid in order:
            pf = os.path.join(rd, f"part_{pid}.mp4")
            x = decode(pf)
            place(buf, x, t, SR, np.ones(len(x), np.float32)); t += W["parts"][pid]["dur_new"]
            log["ae_parts"] = log.get("ae_parts", 0) + 1
        # 아웃트로 BGM(0트랙의 outro_bgm 클립)
        ob = [dict(it, levels=[{"clip_start": it["start"], "clip_in": it["in"], "gain": it["gain"], "keys": it["gain_keys"]}],
                   pr_in=it["start"], pr_out=it["end"], src_in=it["in"]) for it in tr[0]["items"] if nfc(it["name"]) == nfc(A["outro_bgm"])]
        place_pieces(buf, to_master(ob, edl), T, files, key_base, log, "outro_bgm")
        out = rd
    place_sfx(buf, tr[A["sfx_track"]]["items"], edl, T, files, key_base, log)
    place_pieces(buf, to_master(flatten(P, A["main_seq_uid"], A["bgm_tracks"]), edl), T, files, key_base, log, "bgm_pieces")
    name = "identity_mix.wav" if mode == "ko-identity" else "mix.wav"
    peak = float(np.abs(buf).max()); log["peak"] = round(peak, 3); log["clipped"] = int((np.abs(buf) >= 1.0).sum())
    import wave
    with wave.open(os.path.join(out, name), "wb") as wv:
        wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
        wv.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())
    print(json.dumps(log, ensure_ascii=False))
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
