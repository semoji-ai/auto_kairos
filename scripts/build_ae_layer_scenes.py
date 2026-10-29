#!/usr/bin/env python3
"""나눈 레이어(업스케일본)를 After Effects 에 챕터별 컴프로 원위치 배치한다 — TTS 전 조립용.

챕터마다 1920×1080 컴프 하나. 씬은 컴프로 묶지 않고 5초 칸에 레이어를 바로 놓는다
(씬 번호는 마커와 레이어 이름 앞 `S065` 로 구분). 칸마다:
    맨 아래   원본 씬 그림 — **꺼 둔 가이드 레이어**(맞춤 확인용). 레이어로 나뉜 씬에서
              원본을 켜 두면 요소가 원본 그림과 겹쳐 두 번 보인다(통합보고 §0-1 #8).
              나뉘지 않은 씬은 원본이 유일한 그림이라 켜 둔다. `--omit-original` 이면 넣지 않는다.
    그 위     레이어 배경판
    그 위     요소 레이어들 (z 순서) — 원본에서 있던 자리·크기 그대로

배치 규칙(실측 검증): 레이어 PNG 를 bbox 크기로 맞춰 bbox 자리에 놓으면 원본과 겹친다.
레이어 파일 크기는 bbox 와 다를 수 있고(Seedream 이 키워 돌려준다, 업스케일 ×2), 크기는
**bbox 를 기준으로** 다시 계산한다. 모션은 넣지 않는다.

`--timing` 에 `tts_v4_chapters.py` 의 timing.json 을 주면 챕터 나레이션을 컴프 맨 아래에
깔고, 씬 칸을 실제 발화 구간(start~end)에 맞춘다. 컴프 길이는 챕터 음성 길이다. 그림이
없는 씬(반전 카드 등)도 마커는 찍는다. 없으면 씬마다 임시 5초.

씬 그림과 도해를 둘 다 준비한 씬은 같은 칸에 도해 레이어를 `[도해안]` 이름으로 넣고 꺼 둔다.

시각은 전부 프레임(n/30)에 맞춘다. 씬 칸의 out 은 다음 씬 in 보다 1프레임 겹친다 —
소수 반올림으로 경계에 검은 프레임이 생기던 것을 막는다(통합보고 §8-8).

단어 큐(`--cues`): {"S065": {"<요소 이름>": "키워드" | {"word": "키워드", "lead": 0.1,
"occurrence": 1} | {"offset": 1.2}}}. 키워드는 timing.json 의 씬 어절(words)에서 찾아
그 단어가 시작되는 프레임에 요소 레이어 in 을 둔다(오프셋은 씬 시작 기준 초). 못 찾은
큐는 `<out>.cues_report.json` 에 남기고 그 레이어는 씬 시작에 둔다(예전 동작).

After Effects 실행 안전(통합보고 §8):
  · 생성된 jsx 안에서 열린 프로젝트를 확인한다 — 항목이 있는 다른 프로젝트가 열려 있으면
    아무것도 하지 않고 끝낸다. 열린 프로젝트를 닫거나 newProject() 하지 않는다(저장 확인
    없이 닫혀 작업이 날아간 사고). 빈 프로젝트면 그 자리에서, 대상 aep 가 열려 있으면 거기에 만든다.
  · 대상 aep 파일이 이미 있으면 `--overwrite` 없이는 덮어쓰지 않는다.
  · 전체를 try/catch + beginSuppressDialogs + beginUndoGroup 으로 감싼다.
  · `--run` 은 After Effects 가 둘 이상 떠 있으면 실행하지 않는다(-r 이 엉뚱한 AE 로 간다).

    python3 scripts/build_ae_layer_scenes.py <project_dir> --info-dir <도해 폴더> -o <out.aep>
                                             [--timing timing.json] [--cues cues.json]
    → <out>.jsx 를 만들고 After Effects 에서 실행(--run)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.tools.word_timing import find_cue  # noqa: E402

W, H, FPS, DUR = 1920, 1080, 30, 5.0


def frame(t: float) -> int:
    """초 → 프레임 번호(n). 모든 시각은 n/FPS 로만 쓴다."""
    return int(round(float(t) * FPS))


def resolve_cue(spec, words: list, scene_start: float):
    """큐 하나 → 챕터 기준 초. 못 찾으면 None."""
    if isinstance(spec, (int, float)):
        return scene_start + float(spec)
    if isinstance(spec, str):
        spec = {"word": spec}
    if not isinstance(spec, dict):
        return None
    if "offset" in spec:
        return scene_start + float(spec["offset"])
    if spec.get("word"):
        return find_cue(words or [], spec["word"], int(spec.get("occurrence") or 1),
                        float(spec.get("lead") or 0.0))
    return None


def apply_cues(slot: dict, cues: dict, words: list, scene_start: float, report: list) -> None:
    """slot 의 variant 레이어에 큐 프레임(f_in)을 단다. 못 맞춘 큐는 report 에."""
    for v in slot["variants"]:
        want = cues.get(v["key"]) or {}
        names = {L["name"].lower(): L for L in v["layers"]}
        for lname, spec in want.items():
            L = names.get(lname.lower())
            if not L:
                report.append({"key": v["key"], "layer": lname, "cue": spec, "reason": "레이어 이름 없음"})
                continue
            t = resolve_cue(spec, words, scene_start)
            if t is None:
                report.append({"key": v["key"], "layer": lname, "cue": spec,
                               "reason": "단어를 못 찾음" if words else "씬 어절 시각 없음(timing words)"})
                continue
            f = frame(t)
            if not (slot["f0"] <= f < slot["f1"]):
                report.append({"key": v["key"], "layer": lname, "cue": spec, "t": round(t, 3),
                               "reason": "씬 구간 밖 — 씬 안으로 당김"})
                f = min(max(f, slot["f0"]), slot["f1"] - 1)
            L["f_in"] = f


def cover(w: int, h: int) -> tuple[float, float, float]:
    s = max(W / w, H / h)
    return s, (W - w * s) / 2, (H - h * s) / 2


def scene_entry(key: str, label: str, src: Path, layer_dir: Path | None, chapter: int) -> dict:
    sw, sh = Image.open(src).size
    s, dx, dy = cover(sw, sh)
    e = {"key": key, "label": label, "chapter": chapter, "source": str(src),
         "source_scale": s * 100, "layers": []}
    if not layer_dir or not (layer_dir / "elements.json").exists():
        return e
    m = json.loads((layer_dir / "elements.json").read_text(encoding="utf-8"))
    up = layer_dir / "up"
    for el in sorted(m["elements"], key=lambda x: (x["kind"] != "background", x.get("z") or 0)):
        f = up / el["layer"] if (up / el["layer"]).exists() else layer_dir / el["layer"]
        fw, fh = Image.open(f).size
        if el["kind"] == "background" or not el.get("bbox"):
            l, t, r, b = 0, 0, sw, sh
        else:
            l, t, r, b = el["bbox"]
        e["layers"].append({
            "file": str(f), "name": el["name"], "kind": el["kind"],
            "scale": [(r - l) * s / fw * 100, (b - t) * s / fh * 100],
            "pos": [(l + r) / 2 * s + dx, (t + b) / 2 * s + dy],
        })
    return e


JSX = r"""(function(){
var D=__DATA__, OUT=__OUT__, STATUS=__STATUS__, FPS=__FPS__, OVERWRITE=__OVERWRITE__;
function log(s){var f=new File(STATUS);f.encoding="UTF-8";f.open("w");f.write(s);f.close();}
function fname(f){return f?File.decode(f.name):"";}
var undo=false;
app.beginSuppressDialogs();
try{
 // 프로젝트 이름 가드 — 수정 스크립트 **안에서** 본다(통합보고 §8-1·§8-4).
 // 항목이 있는 다른 프로젝트가 열려 있으면 아무것도 하지 않는다. 닫지도, newProject() 하지도 않는다.
 var target=new File(OUT), proj=app.project;
 if(!proj) throw new Error("열린 프로젝트 없음 — After Effects 에서 빈 프로젝트를 연 뒤 다시 실행");
 var isTarget=proj.file && fname(proj.file)==fname(target);
 if(proj.numItems>0 && !isTarget)
  throw new Error("다른 프로젝트가 열려 있어 중단: "+(proj.file?fname(proj.file):"(저장 안 된 프로젝트, 항목 "+proj.numItems+"개)")+" — 대상: "+fname(target));
 if(!isTarget && target.exists && !OVERWRITE)
  throw new Error("대상 aep 가 이미 있음 — 덮어쓰려면 --overwrite: "+fname(target));
 app.beginUndoGroup("레이어 조립");undo=true;
 var root=proj.items.addFolder(D.title), MEDIA=proj.items.addFolder("소재");MEDIA.parentFolder=root;
 var IMP={};function imp(p){if(IMP[p])return IMP[p];var f=new File(p);if(!f.exists)throw new Error("소재 없음: "+p);var it=proj.importFile(new ImportOptions(f));it.parentFolder=MEDIA;IMP[p]=it;return it;}
 function T(l){return l.property("ADBE Transform Group");}
 // 시각은 전부 프레임 번호로 받아 n/FPS 로 넣는다 — 소수 반올림 경계 검은 프레임 방지
 function put(c,path,name,scale,pos,f0,f1,on,guide){var l=c.layers.add(imp(path));l.name=name;l.startTime=0;
  l.outPoint=f1/FPS;l.inPoint=f0/FPS;
  T(l).property("ADBE Scale").setValue(scale);T(l).property("ADBE Position").setValue(pos);
  if(guide)l.guideLayer=true;l.enabled=on;return l;}
 var nl=0, nc=0;
 for(var ci=0;ci<D.chapters.length;ci++){
  var ch=D.chapters[ci], c=proj.items.addComp(D.title+" · 챕터 "+ch.chapter,1920,1080,1,Math.max(1,ch.frames)/FPS,FPS);
  c.parentFolder=root;c.bgColor=[1,1,1];nc++;
  for(var k=0;k<ch.slots.length;k++){
   var slot=ch.slots[k], f0=slot.f0, f1=slot.f1, mk=new MarkerValue(slot.key);c.markerProperty.setValueAtTime(f0/FPS,mk);
   for(var v=0;v<slot.variants.length;v++){
    var s=slot.variants[v], on=(v==0), pre=s.key+(on?" ":" [도해안] ");
    if(s.original=="show") put(c,s.source,pre+"원본",[s.source_scale,s.source_scale],[960,540],f0,f1,on,false);
    else if(s.original=="guide") put(c,s.source,pre+"원본(가이드)",[s.source_scale,s.source_scale],[960,540],f0,f1,false,true);
    for(var j=0;j<s.layers.length;j++){var L=s.layers[j], fi=(L.f_in!=null?L.f_in:f0);
     var lay=put(c,L.file,pre+(L.kind=="background"?"배경판":L.name),L.scale,L.pos,fi,f1,on,false);
     if(L.f_in!=null)lay.property("ADBE Marker").setValueAtTime(fi/FPS,new MarkerValue("큐"));
     nl++;}
   }
  }
  // 나레이션은 맨 아래 — 레이어를 다 쌓은 뒤 넣고 끝으로 내린다
  if(ch.audio){var au=c.layers.add(imp(ch.audio));au.name="나레이션 v4 · 챕터 "+ch.chapter;au.startTime=0;au.moveToEnd();}
 }
 app.endUndoGroup();undo=false;
 proj.save(target);
 log("OK\n"+OUT+"\nchapters="+nc+"\nlayers="+nl);
}catch(e){log("ERR line "+e.line+": "+e.toString());}
finally{if(undo){try{app.endUndoGroup();}catch(_){}}app.endSuppressDialogs(false);}
})();"""


def ascii_jsx(src: str) -> str:
    """비 ASCII 글자를 \\uXXXX 로 — 한글이 든 jsx 가 인코딩 때문에 깨지거나 안 도는 것을 막는다(§8-6).
    jsx 의 비 ASCII 는 문자열·주석 안에만 있으므로 그대로 이스케이프해도 의미가 같다."""
    out = []
    for ch in src:
        o = ord(ch)
        if o < 128:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04x" % o)
        else:
            o -= 0x10000
            out.append("\\u%04x\\u%04x" % (0xD800 + (o >> 10), 0xDC00 + (o & 0x3FF)))
    return "".join(out)


def ae_processes() -> int:
    r = subprocess.run(["pgrep", "-f", "After Effects.app/Contents/MacOS/"], capture_output=True, text=True)
    return len([x for x in r.stdout.split() if x.strip()])


def build_data(P: Path, info_dir: Path, title: str, timing_doc: dict | None = None,
               cues: dict | None = None, original: str = "guide") -> tuple[dict, list]:
    """jsx 에 실을 데이터와 못 맞춘 큐 목록.

    original: "guide"(기본 — 레이어로 나뉜 씬은 원본을 꺼 둔 가이드로) | "omit"(넣지 않음).
    레이어가 없는 씬은 어느 쪽이든 원본을 켜 둔다(그것이 유일한 그림)."""
    specs = json.loads((P / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    assets = {s["sceneNumber"]: s for s in json.loads((P / "images" / "image_assets.json").read_text(encoding="utf-8"))["scenes"]}
    layers = P / "layers"
    timing, audio, words = {}, {}, {}
    for c in (timing_doc or {}).get("chapters", []):
        audio[c["chapter"]] = {"file": str(Path(c["audio"]).resolve()), "duration": c["duration"]}
        for sc in c["scenes"]:
            timing[sc["n"]] = (sc["start"], sc["end"])
            words[sc["n"]] = sc.get("words") or []
    chapters: dict[int, list] = {}
    for sp in specs:
        n, ch = sp["sceneNumber"], sp["chapter"]
        sel = (assets.get(n) or {}).get("selected")
        img_key, info_key = f"S{n:03d}", f"I{n:03d}"
        info_png = info_dir / f"scene_{n:04d}.png"
        variants = []
        if sel and sp.get("imageAsset", {}).get("source") == "generate":
            variants.append(scene_entry(img_key, img_key, P / "images" / sel, layers / img_key, ch))
        if info_png.exists():
            variants.append(scene_entry(info_key, info_key, info_png, layers / info_key, ch))
        for v in variants:
            v["original"] = "show" if not v["layers"] else ("omit" if original == "omit" else "guide")
        slot = {"n": n, "key": f"#{n} " + (variants[0]["key"] if variants else "(그림 없음)"), "variants": variants}
        if n in timing:
            slot["t0"], slot["t1"] = timing[n]
        if variants or n in timing:   # 씬 그림과 도해가 둘 다면 씬 그림이 앞(켜짐), 도해는 [도해안](꺼짐)
            chapters.setdefault(ch, []).append(slot)
    report: list = []
    out_chapters = []
    for c in sorted(chapters):
        slots = chapters[c]
        if c not in audio:            # 음성이 없는 챕터는 5초 칸
            for k, sl in enumerate(slots):
                sl["t0"], sl["t1"] = k * DUR, (k + 1) * DUR
        total = (audio.get(c) or {}).get("duration") or len(slots) * DUR
        frames = int(-(-float(total) * FPS // 1))          # 올림 — 음성 끝이 잘리지 않게
        for sl in slots:
            # 프레임 정렬 + 다음 씬과 1프레임 겹침(경계 검은 프레임 방지, §8-8)
            sl["f0"] = frame(sl["t0"])
            sl["f1"] = max(sl["f0"] + 1, frame(sl["t1"]) + 1)
            if cues:
                apply_cues(sl, cues, words.get(sl["n"]), sl["t0"], report)
        out_chapters.append({"chapter": c, "slots": slots, "audio": (audio.get(c) or {}).get("file"),
                             "frames": frames})
    if cues:
        known = {v["key"] for c in out_chapters for sl in c["slots"] for v in sl["variants"]}
        for k in cues:
            if k not in known:
                report.append({"key": k, "reason": "씬 키 없음(그림·레이어가 없는 씬)"})
    return {"title": title, "chapters": out_chapters}, report


def render_jsx(data: dict, out: Path, status: Path, overwrite: bool) -> str:
    jsx = (JSX.replace("__DATA__", json.dumps(data, ensure_ascii=False))
              .replace("__OUT__", json.dumps(str(out), ensure_ascii=False))
              .replace("__STATUS__", json.dumps(str(status), ensure_ascii=False))
              .replace("__OVERWRITE__", "true" if overwrite else "false")
              .replace("__FPS__", str(FPS)))
    return ascii_jsx(jsx)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--info-dir", type=Path, required=True)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--title", default="한화 브랜드백과 1편")
    ap.add_argument("--timing", type=Path, help="tts_v4_chapters.py 의 timing.json")
    ap.add_argument("--cues", type=Path, help='{"S065": {"요소 이름": "키워드"}} — 요소 등장을 단어 시점에')
    ap.add_argument("--omit-original", action="store_true", help="레이어로 나뉜 씬에 원본 가이드 레이어를 넣지 않는다")
    ap.add_argument("--overwrite", action="store_true", help="대상 aep 가 이미 있어도 덮어쓴다")
    ap.add_argument("--run", action="store_true", help="After Effects 에서 바로 실행")
    ap.add_argument("--app", default="Adobe After Effects 2026")
    a = ap.parse_args()

    # 애펙은 자기 작업 폴더 기준으로 경로를 읽는다 — 상대 경로를 넘기면 소재를 못 찾는다
    P = a.project.resolve()
    timing_doc = json.loads(a.timing.read_text(encoding="utf-8")) if a.timing else None
    cues = json.loads(a.cues.read_text(encoding="utf-8")) if a.cues else None
    data, report = build_data(P, a.info_dir.resolve(), a.title, timing_doc, cues,
                              "omit" if a.omit_original else "guide")
    out = a.out.resolve()
    if out.exists() and not a.overwrite:
        print(f"! 대상 aep 가 이미 있다 — 덮어쓰려면 --overwrite: {out}")
        if a.run:
            return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    status = out.with_suffix(".status.txt")
    jp = out.with_suffix(".jsx")
    jp.write_text(render_jsx(data, out, status, a.overwrite), encoding="utf-8")
    scenes = [v for c in data["chapters"] for sl in c["slots"] for v in sl["variants"]]
    nl = sum(len(s["layers"]) for s in scenes)
    print(f"{jp}\n  챕터 컴프 {len(data['chapters'])} · 씬 {sum(len(c['slots']) for c in data['chapters'])} · 레이어 {nl}")
    if cues is not None:
        rp = out.with_suffix(".cues_report.json")
        rp.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        n_cued = sum(1 for s in scenes for L in s["layers"] if L.get("f_in") is not None)
        print(f"  단어 큐 {n_cued}개 적용 · 못 맞춘 큐 {len(report)}개 → {rp}")
        for r in report[:20]:
            print(f"    ! {r.get('key')} {r.get('layer', '')}: {r['reason']}")
    if a.run:
        n = ae_processes()
        if n > 1:
            print(f"✗ After Effects 가 {n}개 떠 있다 — 대상 하나만 남기고 다시 실행(-r 이 엉뚱한 AE 로 간다)")
            return 1
        if n == 0:
            print("✗ After Effects 가 떠 있지 않다 — 빈 프로젝트로 연 뒤 다시 실행")
            return 1
        if status.exists():
            status.unlink()
        # 가드는 jsx 안에 있다(열린 프로젝트·대상 파일 확인). 여기서는 대상 앱을 앞으로 가져와 실행만 한다.
        subprocess.run(["osascript", "-e", f'tell application "{a.app}" to activate',
                        "-e", f'tell application "{a.app}" to DoScriptFile "{jp}"'],
                       check=False, timeout=3600)
        print(status.read_text(encoding="utf-8") if status.exists() else "상태 파일 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
