"""기법 도감 AE 이식 검증 하네스.

기법마다 AE 에 도감 데모와 같은 테스트 컴프(1920×1080 30fps, 같은 배경·데이터·시작 시각)를 만들고
AKD.apply 로 기법을 건 뒤 지정 프레임을 PNG 로 뽑아, 도감 미리보기 mp4(960×540)의 같은 프레임과
나란히 붙인 비교 시트 + 유사도 수치를 만듭니다.

    python3 adobe/scripts/dogam_verify.py                 # 파일럿 전부
    python3 adobe/scripts/dogam_verify.py stamp-slam year-tag
    python3 adobe/scripts/dogam_verify.py --no-ae stamp-slam   # AE 는 건너뛰고 시트만 다시

안전 규칙
  · AE 에 열려 있는 프로젝트는 닫지도 저장하지도 않습니다. 테스트 컴프는 "_AKD_VERIFY" 폴더에 만들고,
    실행 전 아이템 id 를 찍어 두었다가 새로 생긴 아이템을 전부 지웁니다(열린 프로젝트는 원래대로).
  · 스크립트 전체를 try/finally 로 감싸고 대화상자를 끕니다(모달이 뜨면 AE 가 멈춥니다). 결과는 파일로만.
  · 배경은 도감 미리보기의 "기법 시작 전" 프레임을 2배로 키운 판(plate)을 씁니다 — 비교 대상은 기법이지 배경이 아닙니다.

산출물: adobe/tmp/dogam_verify/<id>/ (시트 sheet.png, ae_fNNN.png, ref_fNNN.png, result.json), summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

ADOBE = Path(__file__).resolve().parents[1]
EXT = ADOBE / "cep" / "com.autokairos.pd"
JSX = EXT / "jsx"
ASSETS = JSX / "dogam" / "assets"
OUT = ADOBE / "tmp" / "dogam_verify"
AE_APP = os.environ.get("AE_APP_NAME", "Adobe After Effects 2026")


def semoji_dir() -> Path:
    return Path(os.environ.get("SEMOJI_MOTION_DIR") or Path.home() / "Projects" / "semoji-motion").expanduser()


SM = semoji_dir()
PUB = SM / "video" / "public"
PREV = SM / "dogam" / "previews"
LAYERS = json.loads((SM / "video/src/layers.json").read_text(encoding="utf-8"))


def js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def layered_setup(key: str, num: str = "01") -> str:
    """LayeredCover 와 같은 배치: 컨테이너 1920×(1920·ar) 가운데, 배경은 사방 40px 크게, 인물·전경 원위치"""
    spec = LAYERS[key]
    h = 1920 * spec["ar"]
    top = (1080 - h) / 2
    lines = [f'var LY = {{chars: [], closed: [], seeds: [], bboxes: [], all: []}};',
             f'var bg = H.img({js(str(PUB / spec["bg"]))}, "{num} 배경", 960, {top + h / 2:.2f}, 2000, {h + 80:.2f}, "fill"); LY.all.push(bg);']
    names = {"family_mom": "엄마", "family_dad": "아빠", "family_son": "아들", "dock_left": "노동자1", "dock_mid": "노동자2", "dock_right": "노동자3",
             "factory_man": "왕송산", "crowd_1": "군중1", "crowd_2": "군중2", "crowd_3": "군중3", "crowd_4": "군중4", "family_bowls": "그릇"}
    for c in spec["chars"]:
        nm = names.get(Path(c["png"]).stem.split("__")[1], "인물")
        x0, y0, x1, y1 = c["bbox"]
        bb = [x0 * 1920, top + y0 * h, x1 * 1920, top + y1 * h]
        lines.append(f'var m = H.img({js(str(PUB / c["png"]))}, "{num} {nm} 메인", 960, {top + h / 2:.2f}, 1920, {h:.2f}, "fill"); LY.chars.push(m); LY.all.push(m); LY.seeds.push({js(c["png"])}); LY.bboxes.push({js(bb)});')
        if c.get("closed"):
            lines.append(f'var cl = H.img({js(str(PUB / c["closed"]))}, "{num} {nm} 눈감음", 960, {top + h / 2:.2f}, 1920, {h:.2f}, "fill"); LY.closed.push(cl); LY.all.push(cl); LY.chars.push(cl); LY.seeds.push({js(c["png"])}); LY.bboxes.push({js(bb)});')
    for g in spec.get("fg", []):
        nm = names.get(Path(g).stem.split("__")[1], "전경")
        lines.append(f'var fg = H.img({js(str(PUB / g))}, "{num} {nm}", 960, {top + h / 2:.2f}, 1920, {h:.2f}, "fill"); LY.all.push(fg);')
    return "\n".join(lines)


# ── 파일럿 12개: 도감 데모(video/src/gallery)와 같은 데이터·시작 시각 ─────────────
CASES: dict[str, dict] = {
    "photo-pop": dict(preview="core-15", plate=0, frames=[6, 7, 8, 9, 11, 20, 45], setup="""
var ph = H.photoComp(%s, 360, 360, 0.5, 0.5, "01 짜장면 사진"); H.P(ph).setValue([1520, 250]);
R.push(AKD.apply("photo-pop", {comp: comp, layers: [ph], t: 6/30, assetsRoot: ASSETS}));
""" % js(str(PUB / "real/jjajang.jpg"))),
    "stamp-slam": dict(preview="core-16", plate=0, frames=[8, 9, 10, 12, 14, 17, 20, 24, 28, 40, 70], setup="""
R.push(AKD.apply("stamp-slam", {comp: comp, layers: [], t: 8/30, params: {size: 150}, content: {text: "폐업", x: 960, y: 560}, assetsRoot: ASSETS}));
"""),
    "idle-bob": dict(preview="core-28", plate=None, frames=[0, 5, 10, 15, 20, 40, 75, 110, 149], setup=layered_setup("s02_dock", "02") + """
R.push(AKD.apply("idle-bob", {comp: comp, layers: LY.chars, t: 0, content: {seeds: LY.seeds, bboxes: LY.bboxes}, assetsRoot: ASSETS}));
"""),
    "dim-cutaway-drop-exit": dict(preview="x_pirates-06", plate=0, frames=[8, 12, 16, 20, 28, 34, 40, 50, 62, 64, 66, 70, 75, 99], setup="""
R.push(AKD.apply("dim-cutaway-drop-exit", {comp: comp, layers: [], t: 8/30, assetsRoot: ASSETS}));
"""),
    "starburst-echo": dict(preview="core-17", plate=0, frames=[6, 7, 8, 9, 11, 14, 19, 30, 60], setup="""
R.push(AKD.apply("starburst-echo", {comp: comp, layers: [], t: 6/30, params: {size: 80}, content: {text: "짜장면!", x: 1360, y: 400, w: 500, h: 340}, assetsRoot: ASSETS}));
"""),
    "year-tag": dict(preview="core-11", plate=0, frames=[6, 8, 10, 14, 22, 40, 60, 64, 70, 76, 80, 109], setup="""
R.push(AKD.apply("year-tag", {comp: comp, layers: [], t: 6/30, content: {text: "1900년대 초"}, assetsRoot: ASSETS}));
R.push(AKD.apply("year-tag", {comp: comp, layers: [], t: 60/30, content: {text: "1912년 무렵"}, assetsRoot: ASSETS}));
"""),
    "scroll-label": dict(preview="core-12", plate=0, frames=[6, 8, 10, 12, 15, 18, 22, 30, 60, 80, 82, 84, 86], setup="""
R.push(AKD.apply("scroll-label", {comp: comp, layers: [], t: 6/30, params: {size: 78}, content: {text: "공화춘", sub: "共和春", x: 960, y: 540, w: 460, outAfter: 74}, assetsRoot: ASSETS}));
"""),
    "wipe-reveal-bubble": dict(preview="x_pirates-05", plate=0, frames=[8, 11, 14, 17, 20, 40, 52, 53, 54, 58, 62, 66, 70, 104, 106], setup="""
R.push(AKD.apply("wipe-reveal-bubble", {comp: comp, layers: [], t: 8/30, content: {x: 1260, y: 330, w: 560, h: 260, text: "짜장면이\\n뭔고?", size: 64, outAfter: 44}, assetsRoot: ASSETS}));
R.push(AKD.apply("wipe-reveal-bubble", {comp: comp, layers: [], t: 58/30, content: {x: 1300, y: 360, w: 640, h: 280, text: "춘장에 비빈\\n국수라니!", size: 64, outAfter: 46}, assetsRoot: ASSETS}));
"""),
    "bar-chart-v": dict(preview="charts-04", plate=0, frames=[4, 8, 13, 16, 20, 25, 31, 36, 40, 50, 61, 66, 76, 85, 100, 139], setup="""
R.push(AKD.apply("bar-chart-v", {comp: comp, layers: [], t: 4/30, assetsRoot: ASSETS}));
"""),
    "smoke-wipe": dict(preview="core-33", plate=0, plateB=51, frames=[6, 8, 9, 11, 13, 16, 19, 22, 26, 30, 36, 46], setup="""
var pa = H.plateLayer(PLATE, "01 장면 A"), pb = H.plateLayer(PLATE_B, "02 장면 B"); pb.moveToEnd();
R.push(AKD.apply("smoke-wipe", {comp: comp, layers: [pa, pb], t: 6/30, assetsRoot: ASSETS}));
"""),
    "map-route": dict(preview="core-42", plate=None, frames=[0, 6, 8, 12, 16, 20, 26, 32, 40, 56, 79], setup="""
R.push(AKD.apply("map-route", {comp: comp, layers: [], t: 0, content: {routeAt: 20, labelsAt: 6}, assetsRoot: ASSETS}));
"""),
    "pullback-reveal": dict(preview="core-07", plate=None, frames=[0, 6, 15, 25, 33, 45, 61, 89], setup=layered_setup("s01_family", "01") + """
AKD.apply("idle-bob", {comp: comp, layers: LY.chars, t: 0, content: {seeds: LY.seeds, bboxes: LY.bboxes}, assetsRoot: ASSETS});
R.push(AKD.apply("pullback-reveal", {comp: comp, layers: LY.all, t: 0, assetsRoot: ASSETS}));
"""),
}

PRELUDE = r"""
(function () {
var RES = { ok: false, results: [], frames: [], log: [] };
var OUTDIR = %(outdir)s, ASSETS = %(assets)s, PLATE = %(plate)s, PLATE_B = %(plateB)s;
function readFile(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }
function writeRes() { var f = new File(OUTDIR + "/result.json"); f.encoding = "UTF-8"; f.lineFeed = "Unix"; f.open("w"); f.write(AKD_S(RES)); f.close(); }
var AKD_S = function (o) { try { return AKD.stringify(o); } catch (e) { return '{"ok":false,"log":["stringify ' + e + '"]}'; } };
var snap = {}, i;
for (i = 1; i <= app.project.numItems; i++) { snap[app.project.item(i).id] = 1; }
app.beginSuppressDialogs();
var R = RES.results;
try {
  eval(readFile(%(json2)s));
  eval(readFile(%(core)s));
  %(techs)s
  var fold = app.project.items.addFolder("_AKD_VERIFY");
  var comp = app.project.items.addComp("akd_verify_%(id)s", 1920, 1080, 1, %(dur)s / 30, 30);
  comp.parentFolder = fold; comp.bgColor = [0.11, 0.11, 0.11];
  var H = {
    P: function (l) { return l.property("ADBE Transform Group").property("ADBE Position"); },
    S: function (l) { return l.property("ADBE Transform Group").property("ADBE Scale"); },
    imp: function (p) { var it = app.project.importFile(new ImportOptions(new File(p))); it.parentFolder = fold; return it; },
    /** 이미지 레이어: 중심 (cx,cy), 상자 w×h, fit = fill(늘림)|cover|contain */
    img: function (p, name, cx, cy, w, h, fit) {
      var it = H.imp(p), l = comp.layers.add(it); l.name = name;
      var sx = w / it.width * 100, sy = h / it.height * 100;
      if (fit === "cover") { sx = sy = Math.max(sx, sy); } else if (fit === "contain") { sx = sy = Math.min(sx, sy); }
      H.S(l).setValue([sx, sy]); H.P(l).setValue([cx, cy]); return l;
    },
    /** 사진 comp(w×h, cover + objectPosition px,py) — PhotoFrame·CircleImg 의 img 와 같은 크롭 */
    photoComp: function (p, w, h, px, py, name) {
      var it = H.imp(p), c = app.project.items.addComp(name, w, h, 1, comp.duration, 30); c.parentFolder = fold;
      var l = c.layers.add(it), s = Math.max(w / it.width, h / it.height) * 100; H.S(l).setValue([s, s]);
      H.P(l).setValue([w / 2 + (it.width * s / 100 - w) * (0.5 - px), h / 2 + (it.height * s / 100 - h) * (0.5 - py)]);
      var L = comp.layers.add(c); L.name = name; return L;
    },
    plateLayer: function (p, name) { return H.img(p, name, 960, 540, 1920, 1080, "fill"); }
  };
  if (PLATE) { H.plateLayer(PLATE, "00 배경(도감 미리보기 판)"); }
  %(setup)s
  RES.log.push("layers " + comp.numLayers);
  if (%(debug)s) { for (i = 1; i <= comp.numLayers; i++) { var Ld = comp.layer(i); try { RES.log.push(i + " " + Ld.name + " in=" + Ld.inPoint.toFixed(2) + " out=" + Ld.outPoint.toFixed(2) + " en=" + Ld.enabled + " par=" + (Ld.parent ? Ld.parent.name : "-") + " P=" + H.P(Ld).valueAtTime(0.5, false) + " S=" + H.S(Ld).valueAtTime(0.5, false) + " O=" + Ld.property("ADBE Transform Group").property("ADBE Opacity").valueAtTime(0.5, false)); } catch (ed) { RES.log.push("dbg " + ed); } } }
  // 프레임 저장(비동기 — 파일이 생기고 크기가 멈출 때까지 기다립니다)
  var FR = %(frames)s;
  for (i = 0; i < FR.length; i++) {
    var f = new File(OUTDIR + "/ae_f" + ("00" + FR[i]).slice(-3) + ".png"); if (f.exists) { f.remove(); }
    comp.saveFrameToPng(FR[i] / 30, f);
    var k = 0, last = -1;
    while (k < 600) { $.sleep(50); k++; if (f.exists) { var ln = f.length; if (ln > 0 && ln === last) { break; } last = ln; } }
    RES.frames.push({ f: FR[i], ok: f.exists });
  }
  RES.ok = true;
} catch (e) {
  RES.log.push("ERR " + e + (e.line ? " line " + e.line : ""));
} finally {
  try {
    for (i = app.project.numItems; i >= 1; i--) { var it = null; try { it = app.project.item(i); } catch (e1) { continue; } if (it && !snap[it.id]) { try { it.remove(); } catch (e2) {} } }
  } catch (e3) { RES.log.push("cleanup " + e3); }
  RES.log.push("items after cleanup " + app.project.numItems);
  app.endSuppressDialogs(false);
  writeRes();
}
})();
"""


def ffmpeg_frame(mp4: Path, n: int, out: Path, scale: tuple[int, int] | None = None) -> None:
    vf = f"select=eq(n\\,{n})"
    if scale:
        vf += f",scale={scale[0]}:{scale[1]}:flags=lanczos"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp4), "-vf", vf, "-vframes", "1", str(out)], check=True)


def run_ae(jsx_path: Path, timeout: int = 600) -> None:
    script = f'with timeout of {timeout} seconds\ntell application "{AE_APP}" to DoScriptFile "{jsx_path}"\nend timeout'
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout + 30)


def font(size: int):
    for p in ["/System/Library/Fonts/AppleSDGothicNeo.ttc", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def compare(tid: str, case: dict, d: Path) -> dict:
    mp4 = PREV / f"{case['preview']}.mp4"
    rows, scores = [], []
    F = font(18)
    # 기법 영역: 판(plate)과 달라진 픽셀만 따로 잰다 — 전체 평균은 배경이 대부분이라 차이가 묻힌다
    base = None
    if case.get("plate") is not None and (d / "plate.png").exists():
        base = np.asarray(Image.open(d / "plate.png").convert("RGB").resize((240, 135), Image.BILINEAR), dtype=np.float32)
    for n in case["frames"]:
        ref, ae = d / f"ref_f{n:03d}.png", d / f"ae_f{n:03d}.png"
        ffmpeg_frame(mp4, n, ref)
        if not ae.exists():
            continue
        a = Image.open(ae).convert("RGB").resize((960, 540), Image.LANCZOS)
        r = Image.open(ref).convert("RGB")
        sa = np.asarray(a.resize((240, 135), Image.BILINEAR), dtype=np.float32)
        sr = np.asarray(r.resize((240, 135), Image.BILINEAR), dtype=np.float32)
        mad = float(np.abs(sa - sr).mean())
        rec = {"f": n, "mad": round(mad, 2), "sim": round(100 - mad / 255 * 100, 2)}
        if base is not None:
            m = (np.abs(sr - base).max(axis=2) > 24) | (np.abs(sa - base).max(axis=2) > 24)
            if m.sum() > 30:
                rm = float(np.abs(sa - sr)[m].mean())
                rec.update({"region_px": int(m.sum()), "region_sim": round(100 - rm / 255 * 100, 2)})
        scores.append(rec)
        diff = Image.fromarray(np.clip(np.abs(np.asarray(a, dtype=np.int16) - np.asarray(r, dtype=np.int16)) * 3, 0, 255).astype(np.uint8))
        row = Image.new("RGB", (960 * 3, 540 + 30), (20, 20, 20))
        row.paste(r, (0, 30)); row.paste(a, (960, 30)); row.paste(diff, (1920, 30))
        dr = ImageDraw.Draw(row)
        dr.text((10, 5), f"도감 f{n}", fill=(255, 255, 255), font=F)
        rs = scores[-1].get("region_sim")
        dr.text((970, 5), f"AE f{n}   유사도 {scores[-1]['sim']}%" + (f"  기법영역 {rs}%" if rs is not None else "") + f"  (평균색차 {mad:.1f})", fill=(255, 220, 120), font=F)
        dr.text((1930, 5), "차이 ×3", fill=(200, 200, 200), font=F)
        rows.append(row)
    if rows:
        sheet = Image.new("RGB", (960 * 3, sum(r.height for r in rows)), (0, 0, 0))
        y = 0
        for r in rows:
            sheet.paste(r, (0, y)); y += r.height
        sheet.save(d / "sheet.png")
        # 가볍게 보는 판(절반 크기)
        sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(d / "sheet_small.jpg", quality=85)
    sims = [s["sim"] for s in scores]
    rsims = [s["region_sim"] for s in scores if "region_sim" in s]
    return {"id": tid, "preview": case["preview"], "frames": scores, "sim_mean": round(sum(sims) / len(sims), 2) if sims else None,
            "sim_min": min(sims) if sims else None, "region_mean": round(sum(rsims) / len(rsims), 2) if rsims else None,
            "sheet": str(d / "sheet.png")}


def run_case(tid: str, case: dict, with_ae: bool) -> dict:
    d = OUT / tid
    d.mkdir(parents=True, exist_ok=True)
    mp4 = PREV / f"{case['preview']}.mp4"
    plate = plate_b = None
    if case.get("plate") is not None:
        plate = d / "plate.png"; ffmpeg_frame(mp4, case["plate"], plate, (1920, 1080))
    if case.get("plateB") is not None:
        plate_b = d / "plateB.png"; ffmpeg_frame(mp4, case["plateB"], plate_b, (1920, 1080))
    n_frames = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                                   "-of", "csv=p=0", str(mp4)], capture_output=True, text=True).stdout.strip().strip(","))
    techs = sorted({tid, *case.get("extra", [])} | ({"idle-bob"} if "idle-bob" in case["setup"] else set()))
    if with_ae:
        for f in d.glob("ae_f*.png"):
            f.unlink()
        jsx = PRELUDE % {
            "outdir": js(str(d)), "assets": js(str(ASSETS)), "plate": js(str(plate) if plate else ""), "plateB": js(str(plate_b) if plate_b else ""),
            "json2": js(str(JSX / "json2.jsx")), "core": js(str(JSX / "dogam/core.jsx")),
            "techs": "\n  ".join(f"eval(readFile({js(str(JSX / 'dogam/techniques' / (t + '.jsx')))}));" for t in techs),
            "id": tid, "dur": n_frames, "debug": "true" if os.environ.get("AKD_DEBUG") else "false", "setup": case["setup"], "frames": js(case["frames"]),
        }
        jp = d / "run.jsx"
        jp.write_text(jsx, encoding="utf-8")
        (d / "result.json").unlink(missing_ok=True)
        t0 = time.time()
        run_ae(jp)
        print(f"  AE {time.time() - t0:.1f}s")
    res = json.loads((d / "result.json").read_text(encoding="utf-8")) if (d / "result.json").exists() else {"ok": False, "log": ["result.json 없음"]}
    cmp_ = compare(tid, case, d)
    cmp_["ae"] = res
    (d / "compare.json").write_text(json.dumps(cmp_, ensure_ascii=False, indent=1), encoding="utf-8")
    return cmp_


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="기법 id (없으면 파일럿 전부)")
    ap.add_argument("--no-ae", action="store_true", help="AE 실행 없이 비교 시트만 다시")
    a = ap.parse_args()
    ids = a.ids or list(CASES)
    OUT.mkdir(parents=True, exist_ok=True)
    summ_p = OUT / "summary.json"
    summ = json.loads(summ_p.read_text(encoding="utf-8")) if summ_p.exists() else {}
    for tid in ids:
        if tid not in CASES:
            print("알 수 없는 id:", tid); continue
        print(f"▶ {tid}")
        r = run_case(tid, CASES[tid], not a.no_ae)
        ae = r["ae"]
        msgs = []
        for x in ae.get("results") or []:
            try:
                x = json.loads(x) if isinstance(x, str) else x
                msgs.append(x.get("msg") or ("오류: " + str(x.get("error"))))
            except Exception:
                msgs.append(str(x))
        print(f"  유사도 평균 {r['sim_mean']} 최저 {r['sim_min']} 기법영역 {r['region_mean']} | AE ok={ae.get('ok')} {ae.get('log')} {msgs}")
        summ[tid] = {k: r[k] for k in ("preview", "sim_mean", "sim_min", "region_mean", "sheet")} | {"ae_ok": ae.get("ok"), "ae_log": ae.get("log"), "apply": msgs}
    summ_p.write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    print("요약:", summ_p)


if __name__ == "__main__":
    main()
