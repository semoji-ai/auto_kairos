"""편 마스터 생성: master/edl.json, master/source.json.  usage: python3 scripts/master.py episodes/B209"""
import json, os, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.audio import decode, speech_spans, split_long
from sg.edl import build_edl, part_span_to_master
from sg.graph import walk
from sg.segments import attach_text, merge_textless, looks_like_speech
import subprocess, tempfile

NFC = lambda s: unicodedata.normalize("NFC", s)
WHISPER_MODEL = os.path.expanduser("~/LocalProjects/auto_kairos/artifacts/benchmarks/lg_ep01_tts_audit_20260916/ggml-small.bin")


def whisper_text(wav, a, b):
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", wav,
                        "-ac", "1", "-ar", "16000", f.name], check=True)
        r = subprocess.run(["whisper-cli", "-m", WHISPER_MODEL, "-l", "ko", "-nt", "-f", f.name],
                           capture_output=True, text=True, errors="replace")   # 깨진 UTF-8 조각이 섞여 나오기도 함
        return r.stdout.strip().replace("\n", " ")


def local_file(nas_file, nas_ep, ep_dir):
    rel = os.path.relpath(NFC(nas_file), NFC(nas_ep))
    p = os.path.join(ep_dir, "src", rel)
    if os.path.exists(p):
        return p
    # 옛 PD 경로(/Volumes/C/work/…)로 기록된 편: ingest.py가 복사한 src 안에서 파일명+꼬리 경로로 찾음
    from scripts.ingest import tail_score
    name = os.path.basename(NFC(nas_file).replace("\\", "/")).lower()
    cands = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(ep_dir, "src")) for f in fs if NFC(f).lower() == name]
    if not cands:
        raise FileNotFoundError(p)
    return max(cands, key=lambda c: tail_score(nas_file, c))


def main(ep_dir):
    C = json.load(open(os.path.join(ep_dir, "master_config.json")))
    tl = json.load(open(os.path.join(ep_dir, C["prproj_timeline"])))
    seq = [s for s in tl if s["uid"].startswith(C["sequence_uid"])][0]
    edl = build_edl(seq, {p["clip"]: pid for pid, p in C["parts"].items()}, C["outro_clip"], C["cuts_pr"])
    G = json.load(open(os.path.join(ep_dir, C["graph"])))
    inv = json.load(open(os.path.join(ep_dir, C["inventory"])))
    texts = {(str(t["comp_id"]), t["layer"]): t for t in inv["texts"]}

    segments, strings = [], {}
    for pid, P in C["parts"].items():
        layers = walk(G, P["comp_id"], 0, P["dur"])

        def to_master(spans):
            # 클립 밖(건너뛴 소스)·컷 안은 잘라 내고 남은 조각만(컷을 걸친 말도 잃지 않음)
            out = []
            for a, b in spans:
                out += part_span_to_master(edl, pid, a, b)
            return out

        subs = []
        for r in layers:
            t = texts.get((r["comp_id"], r["layer"]))
            if not t:
                continue
            ms = to_master(r["spans"])
            if not ms:
                continue
            if t["comp"].startswith(C["subtitle_comp_prefix"]):
                for a, b in ms:
                    subs.append({"text": t["text"], "in": a, "out": b, "layer": f"{t['comp']}:{t['layer']}"})
            else:
                sid = f"s{r['comp_id']}_{r['layer']}"
                e = strings.setdefault(sid, {"id": sid, "comp": t["comp"], "comp_id": int(r["comp_id"]), "layer": r["layer"],
                                             "ko": t["text"], "font": t["font"], "size": t["size"], "keys": len(t["keys"]), "spans": []})
                e["spans"] += ms
        # 내레이션: 파트 컴프 아래(프리컴프 안일 수 있음)의 내레이션 레이어 → wav 시간 → 파트 시간 → 마스터 시간
        nar = [r for r in layers if r["src"] is not None
               and G["items"].get(str(r["src"]), {}).get("name") == P["narration"]]
        if not nar:
            raise ValueError(f"{pid}: narration layer count 0")
        # 같은 녹음 wav가 레이어 여러 개로 나뉘어 놓인 편도 있음(B052·B053) → 레이어마다 자기 보이는 구간만
        spans, wav_of, wav = [], {}, None
        for r in nar:
            L = [x for x in G["comps"][r["comp_id"]]["layers"] if x["i"] == r["layer"]][0]
            sx = (L["sx"] or 100) / 100.0
            wav = local_file(G["items"][str(L["src"])]["file"], C["nas_ep"], ep_dir)
            x = decode(wav)
            for a, b in split_long(x, 16000, speech_spans(x, 16000)):
                for o in r["occ"]:
                    ua, ub = (L["st"] + a * sx) * o["k"] + o["off"], (L["st"] + b * sx) * o["k"] + o["off"]
                    ua, ub = max(ua, o["span"][0]), min(ub, o["span"][1])
                    if ub > ua:
                        wa = a + (ua - ((L["st"] + a * sx) * o["k"] + o["off"])) / (sx * o["k"])
                        wb = wa + (ub - ua) / (sx * o["k"])
                        for m in to_master([[ua, ub]]):
                            spans.append(tuple(m)); wav_of[tuple(m)] = (wa, wb)
        heard = {}

        def is_speech(g):
            wa, wb = wav_of[(g["in"], g["out"])]
            heard[g["in"]] = whisper_text(wav, wa, wb)
            return looks_like_speech(heard[g["in"]])

        part_segs = merge_textless(attach_text(spans, subs), is_speech)
        if not [g for g in part_segs if not g.get("nonverbal")]:
            raise ValueError(f"{pid}: no narration segments")
        for g in part_segs:
            g["part"] = pid
            if g["in"] in heard and g.get("nonverbal"):
                g["heard"] = heard[g["in"]]
            segments.append(g)
    segments.sort(key=lambda g: g["in"])
    for i, g in enumerate(segments, 1):
        g["id"] = f"n{i:03d}"
    os.makedirs(os.path.join(ep_dir, "master"), exist_ok=True)
    json.dump(edl, open(os.path.join(ep_dir, "master/edl.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"segments": segments, "strings": sorted(strings.values(), key=lambda s: s["spans"][0][0])},
              open(os.path.join(ep_dir, "master/source.json"), "w"), ensure_ascii=False, indent=1)
    nv = [g["id"] for g in segments if g.get("nonverbal")]
    empty = [g["id"] for g in segments if not g["ko"] and not g.get("nonverbal")]
    rv = [g["id"] for g in segments if g.get("review")]
    print(f"review {len(rv)} {rv}")
    print(f"segments {len(segments)}  strings {len(strings)}  length {edl['length']}  nonverbal {len(nv)} {nv}  no-text {len(empty)}")


if __name__ == "__main__":
    main(sys.argv[1])
