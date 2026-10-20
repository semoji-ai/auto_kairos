"""형광펜을 번역 문장의 같은 뜻 구절에 다시 맞춤.  usage: highlights.py <EP> <lang>
build/<lang>/<EP>_<lang>_text_raster.aep 에서: 칠해 나가는 막대(Scale X 0→) 중 번역된 문단(__en_ 프리컴프) 줄 위에 놓인 것을 찾고,
한국어 줄에서 덮던 글자 범위 → (claude) 영어 줄의 같은 뜻 구절 → AE에서 구절 폭을 재 막대 위치·최종 폭을 맞춰 같은 파일에 저장."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from sg.highlight import is_sweep, bar_span, to_local, ko_span
from sg.translate import claude_runner, parse_response

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run(job):
    jp = os.path.join(ROOT, "scripts", "ae", "highlights_job.json")
    json.dump(job, open(jp, "w"), ensure_ascii=False, indent=1)
    if os.path.exists(job["out"]):
        os.remove(job["out"])
    subprocess.run([os.path.join(ROOT, "scripts", "ae", "run.sh"), os.path.join(ROOT, "scripts", "ae", "highlights.jsx")], check=True)
    if not os.path.exists(job["out"]):
        sys.exit("highlights.jsx가 기록을 남기지 않음(AE 오류 대화상자 확인)")
    log = json.load(open(job["out"]))
    if log.get("errors"):
        sys.exit(f"highlights.jsx 오류: {log['errors']}")
    return log


def match_bars(scan, items_by_id):
    """막대 ↔ (번역 문단 레이어, 줄) 짝과 한국어 강조 범위."""
    pairs = []
    for b in scan["bars"]:
        if not is_sweep(b):
            continue
        x0, x1, y0, y1 = bar_span(b, b["w"], b["h"])
        for t in scan["texts"]:
            if t["comp"] != b["comp"] or t["out"] <= b["in"] or b["out"] <= t["in"]:
                continue
            fid = t["sub"].replace("__en_", "")
            u0, v = to_local(x0, (y0 + y1) / 2, t)
            u1, _ = to_local(x1, (y0 + y1) / 2, t)
            best = None
            for ln in t["lines"]:
                cy = ln["pos"][1]; hh = ln["height"] * ln["scale"][1] / 100
                if abs(v - cy) < hh * 0.9 and (best is None or abs(v - cy) < abs(v - best["pos"][1])):
                    best = ln
            if best is None:
                continue
            fid, n = best["key"].split("#")
            it = items_by_id.get(fid)
            if not it:
                continue
            e = it["items"][int(n)]; s = it["w"] / it["png_w"]           # OCR 상자(PNG) → footage 좌표
            bx0, bx1 = e["box"][0] * s, (e["box"][0] + e["box"][2]) * s
            i0, i1 = ko_span(e["text"], bx0, bx1, u0, u1)
            pairs.append({"comp": b["comp"], "bar_idx": b["idx"], "sub": t["sub"], "key": best["key"], "layer_tr":
                          {"anchor": t["anchor"], "pos": t["pos"], "scale": t["scale"]}, "ko": e["text"], "ko_emph": e["text"][i0:i1],
                          "text": best["text"]})
    return pairs


def english_spans(pairs, lang, runner=claude_runner):
    if not pairs:
        return []
    items = [{"id": f"h{k}", "ko_line": p["ko"], "ko_emphasized": p["ko_emph"], "translated_line": p["text"]} for k, p in enumerate(pairs)]
    prompt = ("A Korean video highlights part of a Korean sentence with a marker. The sentence was translated. For each item, "
              "return the shortest contiguous substring of translated_line, copied EXACTLY (same characters, case, punctuation), "
              "that carries the meaning of ko_emphasized. Return ONLY a JSON object mapping id to that substring.\n\n"
              + json.dumps(items, ensure_ascii=False, indent=0))
    res = parse_response(runner(prompt), [x["id"] for x in items])
    out = []
    for k, p in enumerate(pairs):
        sub = res[f"h{k}"]
        i0 = p["text"].find(sub)
        if i0 < 0:
            sys.exit(f"구절이 문장에 없음: {sub!r} / {p['text']!r}")
        out.append({**p, "i0": i0, "i1": i0 + len(sub), "pad": 1.0})
    return out


if __name__ == "__main__":
    ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
    code = os.path.basename(ep); bd = os.path.join(ep, "build", lang)
    aep = os.path.join(bd, f"{code}_{lang}_text_raster.aep")
    items = {x["id"]: x for x in json.load(open(os.path.join(ep, "raster", "items.json")))}
    scan = run({"mode": "scan", "aep": aep, "out": os.path.join(bd, "highlights_scan.json")})
    pairs = match_bars(scan, items)
    print("sweep bars", sum(1 for b in scan["bars"] if is_sweep(b)), "on translated lines", len(pairs))
    for p in pairs:
        print(" ", p["key"], "ko:", p["ko_emph"])
    job = english_spans(pairs, lang)
    if job:
        log = run({"mode": "apply", "aep": aep, "save_as": aep, "items": job, "out": os.path.join(bd, "highlights_log.json")})
        for f in log["fitted"]:
            print("  fitted", f["key"], "→", f["phrase"])
