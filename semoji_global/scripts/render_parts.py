"""파트 렌더(전체 또는 부분).  usage: render_parts.py <EP> <lang> [--incremental]
--incremental: 직전 렌더의 스냅숏(build/<lang>/warp_rendered.json·l10n_built.json)과 render/<lang>/part_<id>.mp4가 있으면
타이밍이 바뀐 구간과 글자·그림·자막이 바뀐 구간만 AE로 렌더하고 나머지는 직전 렌더를 시간만 옮겨 이어 붙인다.
하나라도 없으면 전체 렌더. 성공하면 스냅숏을 지금 것으로 갱신. (사용자 규칙 2026-10-31: 부분 수정이면 부분 빌드)
⚠ 직전 빌드 뒤 포맷·공용 에셋·raster/styles·manual 판처럼 l10n 밖에서 바뀐 것은 감지 못함 → 그럴 땐 FULL=1(전체 렌더)."""
import json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sg.edl import master_to_pr
from sg.incremental import plan_parts

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ep, lang = os.path.abspath(sys.argv[1]), sys.argv[2]
INC = "--incremental" in sys.argv
code = os.path.basename(ep)
bd, rd = os.path.join(ep, "build", lang), os.path.join(ep, "render", lang)
FPS, TPL = 29.97, "H.264 - Match Render Settings - 15 Mbps"
aep = os.path.join(bd, f"{code}_{lang}_subs.aep")
W = json.load(open(os.path.join(bd, "warp.json")))


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout)


def render(comp, a, b, out):
    subprocess.run([os.path.join(ROOT, "scripts/ae/render.sh"), aep, comp, f"{a:.4f}", f"{b:.4f}", out, str(FPS), TPL], check=True)


def master_to_u(edl, pid, m0, m1):
    """마스터 구간 → 이 파트 원본 시간 구간들."""
    p0, p1 = master_to_pr(edl, m0), master_to_pr(edl, m1)
    out = []
    for c in edl["parts"]:
        if c["id"] != pid:
            continue
        a, b = max(p0, c["pr_in"]), min(p1, c["pr_in"] + c["dur"])
        if b > a:
            out.append((c["src_in"] + a - c["pr_in"], c["src_in"] + b - c["pr_in"]))
    return out


def dirty_master(prev, cur):
    """직전 빌드와 달라진 번역(구간·화면 문자열·그림 글자)의 마스터 구간."""
    src = json.load(open(os.path.join(ep, "master", "source.json")))
    seg = {g["id"]: g for g in src["segments"]}
    strs = {s["id"]: s for s in src.get("strings", [])}
    items = {x["id"]: x for x in json.load(open(os.path.join(ep, "raster", "items.json")))}
    out = []
    for k, v in cur.get("segments", {}).items():
        if v.get("text") != prev.get("segments", {}).get(k, {}).get("text") and k in seg:
            out.append((seg[k]["in"], seg[k]["out"]))
    for k, v in cur.get("strings", {}).items():
        if v.get("text") != prev.get("strings", {}).get(k, {}).get("text") and k in strs:
            out += [tuple(s) for s in strs[k].get("spans", [])]
    for k, v in cur.get("raster", {}).items():
        if v != prev.get("raster", {}).get(k):
            i = k.split("#")[0]
            if i in items:
                out += [tuple(s) for s in items[i]["master_spans"]]
    return out


edl = json.load(open(os.path.join(ep, "master", "edl.json")))
cur = json.load(open(os.path.join(ep, "l10n", f"{lang}.json")))
built = os.path.join(bd, "l10n_built.json")
prev_w = os.path.join(bd, "warp_rendered.json")
log = {}
for pid, P in W["parts"].items():
    out = os.path.join(rd, f"part_{pid}.mp4")
    prev_mp4 = os.path.join(rd, f"part_{pid}_prev.mp4")
    pw = json.load(open(prev_w))["parts"].get(pid) if os.path.exists(prev_w) else None
    if INC and pw and os.path.exists(built) and os.path.exists(out) and "--plan-only" not in sys.argv:
        os.replace(out, prev_mp4)
    if not (INC and pw and os.path.exists(prev_mp4) and os.path.exists(built)):
        if "--plan-only" in sys.argv:
            print(json.dumps({pid: "full (직전 렌더 스냅숏 없음)"})); continue
        tmpf = out + ".rendering.mp4"            # 실패·중단해도 기존 파일은 남게: 임시 파일로 받고 성공하면 바꿔 끼움
        render(P["comp"], 0, P["dur_new"], tmpf); os.replace(tmpf, out); log[pid] = "full"; continue
    dm = dirty_master(json.load(open(built)), cur)
    du = [u for m0, m1 in dm for u in master_to_u(edl, pid, m0, m1)]
    cfg = json.load(open(os.path.join(ep, "master_config.json")))
    G = json.load(open(os.path.join(ep, cfg["graph"])))
    lay = G["comps"][str(cfg["parts"][pid]["comp_id"])]["layers"]
    scenes = [(L["in"], L["out"]) for L in lay if 0.2 < L.get("out", 0) - L.get("in", 0) < 60]   # 장면 레이어(질감·자막·상단바처럼 편 전체에 걸친 것 제외)
    plan = plan_parts(pw["anchors"], P["anchors"], P["dur_new"], du, scenes_u=scenes)
    if "--plan-only" in sys.argv:
        print(json.dumps({pid: plan})); continue
    tmp = os.path.join(rd, f"_inc_{pid}"); os.makedirs(tmp, exist_ok=True)   # 렌더 조각은 남겨 둠(실패 후 다시 돌릴 때 재사용)
    ins, fc, vs, n_reuse = [prev_mp4], [], [], sum(1 for x in plan if x[0] == "reuse")
    if n_reuse:
        fc.append(f"[0:v]split={n_reuse}" + "".join(f"[pv{i}]" for i in range(n_reuse)))
        fc.append(f"[0:a]asplit={n_reuse}" + "".join(f"[pa{i}]" for i in range(n_reuse)))
    r = 0
    for k, x in enumerate(plan):
        nf = round((x[2] - x[1]) * FPS)                 # 조각 길이는 프레임 수로 정확히(조각마다 인코딩하면 자투리가 쌓여 길이가 늘어남)
        if x[0] == "render":
            f = os.path.join(tmp, f"r_{x[1]:.3f}_{x[2]:.3f}.mp4")
            if not (os.path.exists(f) and os.path.getsize(f) > 0):
                render(P["comp"], x[1], x[2], f)
            ins.append(f); j = len(ins) - 1
            fc.append(f"[{j}:v]trim=end_frame={nf},setpts=PTS-STARTPTS[v{k}]")
            fc.append(f"[{j}:a]apad,atrim=end={nf / FPS:.6f},asetpts=PTS-STARTPTS[a{k}]")
        else:
            s0 = round(x[3] * FPS)
            fc.append(f"[pv{r}]trim=start_frame={s0}:end_frame={s0 + nf},setpts=PTS-STARTPTS[v{k}]")
            fc.append(f"[pa{r}]atrim=start={s0 / FPS:.6f}:end={(s0 + nf) / FPS:.6f},asetpts=PTS-STARTPTS[a{k}]")
            r += 1
        vs.append(f"[v{k}][a{k}]")
    fc.append("".join(vs) + f"concat=n={len(plan)}:v=1:a=1[v][a]")
    args = ["ffmpeg", "-v", "error", "-y"]
    for f in ins:
        args += ["-i", f]
    tmpf = out + ".joining.mp4"
    subprocess.run(args + ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-r", str(FPS),
                           "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-c:a", "aac", "-b:a", "256k", tmpf], check=True)
    os.replace(tmpf, out)
    d = dur(out)
    if abs(d - P["dur_new"]) > 0.2:
        sys.exit(f"{pid}: 이어 붙인 길이 {d:.3f} ≠ {P['dur_new']:.3f}")
    rend = sum(x[2] - x[1] for x in plan if x[0] == "render")
    log[pid] = {"rendered_s": round(rend, 1), "total_s": round(P["dur_new"], 1), "pieces": len(plan)}
    shutil.rmtree(tmp, ignore_errors=True)
if "--plan-only" in sys.argv:
    sys.exit(0)
shutil.copyfile(os.path.join(ep, "l10n", f"{lang}.json"), built)
shutil.copyfile(os.path.join(bd, "warp.json"), prev_w)
for pid in W["parts"]:
    pm = os.path.join(rd, f"part_{pid}_prev.mp4")
    if os.path.exists(pm):
        os.remove(pm)
print("render_parts", log)
