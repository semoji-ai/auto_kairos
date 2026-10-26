"""언어별 삽입 구간(그 언어 시청자용으로 새로 만든 도입·결말 등).  usage:
  inserts.py <EP> <lang> tts        장면 내레이션 TTS → tts/<lang>/inserts/<id>.mp3, align, 길이
  inserts.py <EP> <lang> plan       장면 시각표 + 자막 큐 → build/<lang>/inserts_plan.json
  inserts.py <EP> <lang> build      AE 장면 조립(build_inserts.jsx) + 렌더 → render/<lang>/insert_<name>.mp4
  inserts.py <EP> <lang> audio      삽입 구간 오디오(새 내레이션 + 원래 구간 배경음 맞춤) → render/<lang>/insert_<name>.wav
  inserts.py <EP> <lang> splice     미리보기에서 replace_master 구간을 잘라 삽입 → render/<lang>/<EP>_<LANG>_final.mp4 + .srt
정의: l10n/<lang>_inserts.json"""
import json, os, re, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.tts import synthesize, load_key, speech_bounds, trim, zh_spoken
from sg.subs import cues_for_segment, snap_to_onsets, close_gaps, resolve_overlaps, srt_time, bar_intervals
from sg.audio import decode as decode16, speech_spans
from sg.timemap import PiecewiseMap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEAD, TAIL = 0.15, 0.45            # 장면 시작 후 내레이션까지, 내레이션 끝 후 다음 장면까지(초)
SR = 48000


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def load(ep, lang):
    return json.load(open(os.path.join(ep, "l10n", f"{lang}_inserts.json")))


def cmd_tts(ep, lang, force=False):
    prof = json.load(open(os.path.join(ROOT, "profiles", f"{lang}.json")))
    key = load_key(os.path.expanduser("~/LocalProjects/auto_kairos/.env"))
    od = os.path.join(ep, "tts", lang, "inserts"); os.makedirs(od, exist_ok=True)
    meta_p = os.path.join(od, "meta.json"); meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    for name, ins in load(ep, lang)["inserts"].items():
        for sc in ins["scenes"]:
            say = sc.get("tts") or sc["text"]
            if lang == "zh":
                say = zh_spoken(say)
            if not force and meta.get(sc["id"], {}).get("say") == say and os.path.exists(os.path.join(od, f"{sc['id']}.mp3")):
                continue
            for k in range(4):
                try:
                    audio, al = synthesize(say, prof["tts_voice"], prof["tts_model"], prof["language_code"], prof["tts_settings"], key); break
                except Exception as e:
                    if k == 3: raise
                    print("retry", sc["id"], e); time.sleep(5 * (k + 1))
            raw = os.path.join(od, f"{sc['id']}.raw.mp3"); open(raw, "wb").write(audio)
            t0, t1 = speech_bounds(al)
            start = trim(raw, os.path.join(od, f"{sc['id']}.mp3"), t0, t1); os.remove(raw)
            al = {"characters": al["characters"],
                  "character_start_times_seconds": [x - start for x in al["character_start_times_seconds"]],
                  "character_end_times_seconds": [x - start for x in al["character_end_times_seconds"]]}
            json.dump(al, open(os.path.join(od, f"{sc['id']}.align.json"), "w"), ensure_ascii=False)
            meta[sc["id"]] = {"say": say, "dur": round(dur(os.path.join(od, f"{sc['id']}.mp3")), 3)}
            print(sc["id"], meta[sc["id"]]["dur"], flush=True)
            json.dump(meta, open(meta_p, "w"), ensure_ascii=False, indent=1)
    return meta


def cmd_plan(ep, lang):
    prof = json.load(open(os.path.join(ROOT, "profiles", f"{lang}.json")))
    gl = json.load(open(os.path.join(ROOT, "glossary", f"{lang}.json")))
    protect = sorted({w for v in gl.values() for w in re.split(r"[（(—\s/，,;；]", v) if len(w) >= 2}, key=len, reverse=True)
    od = os.path.join(ep, "tts", lang, "inserts"); meta = json.load(open(os.path.join(od, "meta.json")))
    S = load(ep, lang); plan = {}
    for name, ins in S["inserts"].items():
        t, scenes, cues = 0.0, [], []
        for sc in ins["scenes"]:
            nd = meta[sc["id"]]["dur"]; d = round(LEAD + nd + TAIL, 3)
            al = json.load(open(os.path.join(od, f"{sc['id']}.align.json")))
            cs = cues_for_segment(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"],
                                  sc["text"] if sc.get("tts") else None, prof["subs"]["max_chars"], prof["subs"]["min_dur"],
                                  cjk=prof["subs"].get("cjk", False), protect=protect)
            if prof["subs"].get("snap_pauses"):
                x = decode16(os.path.join(od, f"{sc['id']}.mp3"), 16000)
                cs = snap_to_onsets(cs, [a for a, b in speech_spans(x, 16000, min_silence=0.12, pad=0.0)])
            cues += [{"in": round(t + LEAD + c["t0"], 3), "out": round(t + LEAD + c["t1"], 3), "text": c["text"]} for c in cs]
            scenes.append({**sc, "start": round(t, 3), "dur": d, "narr_at": round(t + LEAD, 3), "narr_dur": nd})
            t = round(t + d, 3)
        cues = close_gaps(resolve_overlaps(cues, prof["subs"]["gap"]))
        plan[name] = {"replace_master": ins["replace_master"], "dur": t, "scenes": scenes, "cues": cues,
                      "bar": bar_intervals(cues, 0.0)}           # 자막바는 자막 있을 때만(본편과 같은 규칙)
    bd = os.path.join(ep, "build", lang); os.makedirs(bd, exist_ok=True)
    json.dump(plan, open(os.path.join(bd, "inserts_plan.json"), "w"), ensure_ascii=False, indent=1)
    for n, p in plan.items():
        print(n, "dur", p["dur"], "scenes", len(p["scenes"]), "cues", len(p["cues"]))
    return plan


def cmd_build(ep, lang):
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    ep = os.path.abspath(ep); code = os.path.basename(ep); bd = os.path.join(ep, "build", lang)
    plan = json.load(open(os.path.join(bd, "inserts_plan.json")))
    S = load(ep, lang)
    from PIL import Image
    ad = os.path.join(bd, "insert_assets"); os.makedirs(ad, exist_ok=True)
    def fix(p):                       # 투명 여백을 잘라낸 사본(크기·위치 지정이 보이는 그림 기준이 되게)
        src = os.path.join(ep, p) if p and not os.path.isabs(p) else p
        if not os.path.exists(src):
            return src
        im = Image.open(src).convert("RGBA"); bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
        out = os.path.join(ad, os.path.basename(os.path.dirname(src)) + "_" + os.path.basename(src))
        (im.crop(bb) if bb else im).save(out)
        return out
    for n, p in plan.items():
        for sc in p["scenes"]:
            for L in sc["layers"]:
                if "src" in L:
                    L["src"] = fix(L["src"])
                    if not os.path.exists(L["src"]):
                        sys.exit(f"없는 이미지: {L['src']}")
    job = {"aep": os.path.join(bd, f"{code}_{lang}_subs.aep"), "save_as": os.path.join(bd, f"{code}_{lang}_inserts.aep"),
           "out": os.path.join(bd, "build_inserts_log.json"), "fonts": S["fonts"], "plan": plan, "fps": 29.97,
           "sub_name": cfg["subtitle_comp_prefix"], "bar_layers": cfg.get("subtitle_bar_layers", ["자막바", "자막바그림자"])}
    jp = os.path.join(ROOT, "scripts", "ae", "build_inserts_job.json")
    json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
    if os.path.exists(job["out"]):
        os.remove(job["out"])
    import shutil, tempfile
    tj = os.path.join(tempfile.gettempdir(), "build_inserts_check.js"); shutil.copy(os.path.join(ROOT, "scripts/ae/build_inserts.jsx"), tj)
    subprocess.run(["node", "--check", tj], check=True)
    subprocess.run([os.path.join(ROOT, "scripts/ae/run.sh"), os.path.join(ROOT, "scripts/ae/build_inserts.jsx")], check=True)
    if not os.path.exists(job["out"]):
        sys.exit("build_inserts.jsx가 기록을 남기지 않음(AE 오류 대화상자 확인)")
    log = json.load(open(job["out"])); print(log)
    if log.get("errors"):
        sys.exit("build_inserts 오류")
    rd = os.path.join(ep, "render", lang)
    for n, p in plan.items():
        out = os.path.join(rd, f"insert_{n}.mp4")
        subprocess.run([os.path.join(ROOT, "scripts/ae/render.sh"), job["save_as"], f"INSERT_{n}", "0", f"{p['dur']:.3f}", out,
                        "29.97", "H.264 - Match Render Settings - 15 Mbps"], check=True, capture_output=True)
        print("rendered", out, dur(out))


def _decode(path, ss=0.0, d=None):
    args = ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, ss):.4f}"] + (["-t", f"{d:.4f}"] if d else []) + \
           ["-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(args, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


def fit_bed(x, n, fade=1.0):
    """배경음 조각 x를 길이 n 샘플로: 길면 자르고 끝 페이드, 짧으면 반복(이음새 0.5초 크로스페이드)."""
    if len(x) == 0:
        return np.zeros((n, 2), np.float32)
    out = x[:n].copy()
    xf = int(0.5 * SR)
    while len(out) < n:
        k = min(xf, len(out), len(x))
        w = np.linspace(0, 1, k, dtype=np.float32)[:, None]
        seam = out[-k:] * (1 - w) + x[:k] * w
        out = np.concatenate([out[:-k], seam, x[k:]])[:n] if len(x) > k else np.concatenate([out[:-k], seam])
    f = min(n, int(fade * SR))
    out[n - f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    return out


def cmd_audio(ep, lang):
    from scripts.audio_mix import lufs, narration_gain_db
    ep = os.path.abspath(ep); bd = os.path.join(ep, "build", lang); rd = os.path.join(ep, "render", lang)
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    plan = json.load(open(os.path.join(bd, "inserts_plan.json")))
    T = PiecewiseMap(json.load(open(os.path.join(bd, "warp.json")))["master"])
    bed = os.path.join(rd, "bed.wav")
    if not os.path.exists(bed):
        sys.exit("bed.wav 없음 — audio_mix.py <EP> <lang> --bed 먼저")
    ref = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ep, "src")) for f in fs
           if f in {p["narration"] for p in cfg["parts"].values()} or
           __import__("unicodedata").normalize("NFC", f) in {p["narration"] for p in cfg["parts"].values()}]
    ko = [lufs(r) for r in ref]
    od = os.path.join(ep, "tts", lang, "inserts")
    S = load(ep, lang)
    for n, p in plan.items():
        a, b = T(p["replace_master"][0]), T(p["replace_master"][1])
        N = int(round(p["dur"] * SR))
        buf = fit_bed(_decode(bed, a, b - a), N)
        for sc in p["scenes"]:
            f = os.path.join(od, f"{sc['id']}.mp3")
            g = 10 ** (narration_gain_db(ko, lufs(f)) / 20)
            x = _decode(f) * g; s = int(round(sc["narr_at"] * SR))
            m = min(len(x), N - s); buf[s:s + m] += x[:m]
        # 효과음: 장면 요소의 등장 애니메이션마다(종류별 소리, 반복 요소는 묶음당 1번)
        sfx = {k: _decode(os.path.join(ep, v)) for k, v in S.get("sfx", {}).items() if not k.startswith("_")}
        n_sfx = 0
        for sc in p["scenes"]:
            for L in sc["layers"]:
                kind = "bar" if L.get("type") == "bar" else L.get("anim")
                if kind not in sfx:
                    continue
                t = sc["narr_at"] + L.get("at", 0) * sc["narr_dur"]
                x = sfx[kind]; s0 = int(round(t * SR)); m = min(len(x), N - s0)
                if m > 0:
                    buf[s0:s0 + m] += x[:m]; n_sfx += 1
        pk = float(np.abs(buf).max())
        if pk > 0.97:
            buf *= 0.97 / pk
        import wave
        with wave.open(os.path.join(rd, f"insert_{n}.wav"), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(buf, -1, 1) * 32767).astype("<i2").tobytes())
        print(n, "audio", round(N / SR, 3), "s, bed(BGM) from", round(a, 2), "-", round(b, 2), "sfx", n_sfx, "peak", round(pk, 3))


def cmd_splice(ep, lang):
    ep = os.path.abspath(ep); code = os.path.basename(ep); bd = os.path.join(ep, "build", lang); rd = os.path.join(ep, "render", lang)
    plan = json.load(open(os.path.join(bd, "inserts_plan.json")))
    T = PiecewiseMap(json.load(open(os.path.join(bd, "warp.json")))["master"])
    prev = os.path.join(rd, f"{code}_{lang.upper()}_preview.mp4"); total = dur(prev)
    ins = sorted(plan.items(), key=lambda kv: kv[1]["replace_master"][0])
    # 조각 목록: ("prev", a, b) 또는 ("ins", name)
    segs, cur = [], 0.0
    for n, p in ins:
        a, b = T(p["replace_master"][0]), T(p["replace_master"][1])
        if a > cur + 1e-3:
            segs.append(("prev", cur, a))
        segs.append(("ins", n)); cur = b
    if cur < total - 1e-3:
        segs.append(("prev", cur, total))
    args, filt, k = ["ffmpeg", "-v", "error", "-y", "-i", prev], [], 1
    vlabels = []
    for i, s in enumerate(segs):
        if s[0] == "prev":
            filt.append(f"[0:v]trim={s[1]:.4f}:{s[2]:.4f},setpts=PTS-STARTPTS,fps=30000/1001,format=yuv420p[v{i}];"
                        f"[0:a]atrim={s[1]:.4f}:{s[2]:.4f},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
        else:
            args += ["-i", os.path.join(rd, f"insert_{s[1]}.mp4"), "-i", os.path.join(rd, f"insert_{s[1]}.wav")]
            d = plan[s[1]]["dur"]
            filt.append(f"[{k}:v]trim=0:{d:.4f},setpts=PTS-STARTPTS,scale=1920:1080,fps=30000/1001,format=yuv420p,setsar=1[v{i}];"
                        f"[{k + 1}:a]atrim=0:{d:.4f},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
            k += 2
        vlabels.append(f"[v{i}][a{i}]")
    fc = ";".join(filt) + ";" + "".join(vlabels) + f"concat=n={len(segs)}:v=1:a=1[v][a]"
    out = os.path.join(rd, f"{code}_{lang.upper()}_final.mp4")
    subprocess.run(args + ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                           "-c:a", "aac", "-b:a", "192k", out], check=True)
    # SRT: 원래 큐 중 남는 구간만 + 삽입 큐, 시각 이동
    srt_in = open(os.path.join(rd, f"{lang}.srt")).read().strip().split("\n\n")
    def ts(x):
        h, m, r = x.split(":"); s_, ms = r.split(","); return int(h) * 3600 + int(m) * 60 + int(s_) + int(ms) / 1000
    old = [(ts(b.split("\n")[1].split(" --> ")[0]), ts(b.split("\n")[1].split(" --> ")[1]), "\n".join(b.split("\n")[2:])) for b in srt_in]
    new, pos = [], 0.0
    for s in segs:
        if s[0] == "prev":
            for a, b, t in old:
                if a >= s[1] - 1e-3 and a < s[2] - 1e-3:
                    new.append((pos + a - s[1], pos + min(b, s[2]) - s[1], t))
            pos += s[2] - s[1]
        else:
            for c in plan[s[1]]["cues"]:
                new.append((pos + c["in"], pos + c["out"], c["text"]))
            pos += plan[s[1]]["dur"]
    with open(os.path.join(rd, f"{lang}_final.srt"), "w") as f:
        for i, (a, b, t) in enumerate(new, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n")
    print(out, round(dur(out), 3), "srt", len(new), "expected", round(pos, 3))


if __name__ == "__main__":
    ep, lang, c = sys.argv[1], sys.argv[2], sys.argv[3]
    {"tts": lambda: cmd_tts(ep, lang, "--force" in sys.argv), "plan": lambda: cmd_plan(ep, lang), "build": lambda: cmd_build(ep, lang),
     "audio": lambda: cmd_audio(ep, lang), "splice": lambda: cmd_splice(ep, lang)}[c]()
