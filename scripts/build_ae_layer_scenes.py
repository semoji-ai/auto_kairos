#!/usr/bin/env python3
"""나눈 레이어(업스케일본)를 After Effects 에 챕터별 컴프로 원위치 배치한다 — TTS 전 조립용.

챕터마다 1920×1080 컴프 하나. 씬은 컴프로 묶지 않고 5초 칸에 레이어를 바로 놓는다
(씬 번호는 마커와 레이어 이름 앞 `S065` 로 구분). 칸마다:
    맨 아래   원본 씬 그림(또는 도해 원본) — 화면을 채우도록 맞춤
    그 위     레이어 배경판
    그 위     요소 레이어들 (z 순서) — 원본에서 있던 자리·크기 그대로

배치 규칙(실측 검증): 레이어 PNG 를 bbox 크기로 맞춰 bbox 자리에 놓으면 원본과 겹친다.
레이어 파일 크기는 bbox 와 다를 수 있고(Seedream 이 키워 돌려준다, 업스케일 ×2), 크기는
**bbox 를 기준으로** 다시 계산한다. 모션은 넣지 않는다.

`--timing` 에 `tts_v4_chapters.py` 의 timing.json 을 주면 챕터 나레이션을 컴프 맨 아래에
깔고, 씬 칸을 실제 발화 구간(start~end)에 맞춘다. 컴프 길이는 챕터 음성 길이다. 그림이
없는 씬(반전 카드 등)도 마커는 찍는다. 없으면 씬마다 임시 5초.

씬 그림과 도해를 둘 다 준비한 씬은 같은 칸에 도해 레이어를 `[도해안]` 이름으로 넣고 꺼 둔다.

    python3 scripts/build_ae_layer_scenes.py <project_dir> --info-dir <도해 폴더> -o <out.aep>
    → <out>.jsx 를 만들고 After Effects 에서 실행(--run)
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image

W, H, FPS, DUR = 1920, 1080, 30, 5.0


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
var D=__DATA__, OUT=__OUT__, STATUS=__STATUS__, DUR=__DUR__, FPS=__FPS__;
function log(s){var f=new File(STATUS);f.encoding="UTF-8";f.open("w");f.write(s);f.close();}
try{
 // 열려 있는 미저장 프로젝트를 건드리지 않는다 — 저장 창이 뜨면 스크립트가 멈추고 작업이 날아갈 수 있다
 // 저장된 적 없는 제목 없는 프로젝트(앞서 실패한 조립의 잔해)만 버린다. 파일이 있는 프로젝트는 지킨다.
 if(app.project && app.project.dirty){
  if(app.project.file) throw new Error("열린 프로젝트에 저장 안 한 변경이 있어 중단 — 저장하거나 닫은 뒤 다시 실행");
  app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);
 }
 var proj=app.newProject();
 app.beginUndoGroup("레이어 조립");
 var root=proj.items.addFolder(D.title), MEDIA=proj.items.addFolder("소재");MEDIA.parentFolder=root;
 var IMP={};function imp(p){if(IMP[p])return IMP[p];var f=new File(p);if(!f.exists)throw new Error("소재 없음: "+p);var it=proj.importFile(new ImportOptions(f));it.parentFolder=MEDIA;IMP[p]=it;return it;}
 function T(l){return l.property("ADBE Transform Group");}
 function put(c,path,name,scale,pos,t0,d,on){var l=c.layers.add(imp(path));l.name=name;l.startTime=0;l.inPoint=t0;l.outPoint=t0+d;
  T(l).property("ADBE Scale").setValue(scale);T(l).property("ADBE Position").setValue(pos);l.enabled=on;return l;}
 var nl=0, nc=0;
 for(var ci=0;ci<D.chapters.length;ci++){
  var ch=D.chapters[ci], c=proj.items.addComp(D.title+" · 챕터 "+ch.chapter,1920,1080,1,Math.max(1,ch.duration),FPS);
  c.parentFolder=root;c.bgColor=[1,1,1];nc++;
  for(var k=0;k<ch.slots.length;k++){
   var slot=ch.slots[k], t0=slot.t0, d=slot.dur, mk=new MarkerValue(slot.key);c.markerProperty.setValueAtTime(t0,mk);
   for(var v=0;v<slot.variants.length;v++){
    var s=slot.variants[v], on=(v==0), pre=s.key+(on?" ":" [도해안] ");
    put(c,s.source,pre+"원본",[s.source_scale,s.source_scale],[960,540],t0,d,on);
    for(var j=0;j<s.layers.length;j++){var L=s.layers[j];put(c,L.file,pre+(L.kind=="background"?"배경판":L.name),L.scale,L.pos,t0,d,on);nl++;}
   }
  }
  // 나레이션은 맨 아래 — 레이어를 다 쌓은 뒤 넣고 끝으로 내린다
  if(ch.audio){var au=c.layers.add(imp(ch.audio));au.name="나레이션 v4 · 챕터 "+ch.chapter;au.startTime=0;au.moveToEnd();}
 }
 app.endUndoGroup();proj.save(new File(OUT));
 log("OK\n"+OUT+"\nchapters="+nc+"\nlayers="+nl);
}catch(e){log("ERR line "+e.line+": "+e.toString());try{app.endUndoGroup();}catch(_){}}
})();"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--info-dir", type=Path, required=True)
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--title", default="한화 브랜드백과 1편")
    ap.add_argument("--timing", type=Path, help="tts_v4_chapters.py 의 timing.json")
    ap.add_argument("--run", action="store_true", help="After Effects 에서 바로 실행")
    ap.add_argument("--app", default="Adobe After Effects 2026")
    a = ap.parse_args()

    # 애펙은 자기 작업 폴더 기준으로 경로를 읽는다 — 상대 경로를 넘기면 소재를 못 찾는다
    P = a.project.resolve()
    a.info_dir = a.info_dir.resolve()
    specs = json.loads((P / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    assets = {s["sceneNumber"]: s for s in json.loads((P / "images" / "image_assets.json").read_text(encoding="utf-8"))["scenes"]}
    layers = P / "layers"
    timing, audio = {}, {}
    if a.timing:
        for c in json.loads(a.timing.read_text(encoding="utf-8"))["chapters"]:
            audio[c["chapter"]] = {"file": str(Path(c["audio"]).resolve()), "duration": c["duration"]}
            for sc in c["scenes"]:
                timing[sc["n"]] = (sc["start"], sc["end"] - sc["start"])
    chapters: dict[int, list] = {}
    for sp in specs:
        n, ch = sp["sceneNumber"], sp["chapter"]
        sel = (assets.get(n) or {}).get("selected")
        img_key, info_key = f"S{n:03d}", f"I{n:03d}"
        info_png = a.info_dir / f"scene_{n:04d}.png"
        variants = []
        if sel and sp.get("imageAsset", {}).get("source") == "generate":
            variants.append(scene_entry(img_key, img_key, P / "images" / sel, layers / img_key, ch))
        if info_png.exists():
            variants.append(scene_entry(info_key, info_key, info_png, layers / info_key, ch))
        slot = {"key": f"#{n} " + (variants[0]["key"] if variants else "(그림 없음)"), "variants": variants}
        if n in timing:
            slot["t0"], slot["dur"] = timing[n]
        if variants or n in timing:   # 씬 그림과 도해가 둘 다면 씬 그림이 앞(켜짐), 도해는 [도해안](꺼짐)
            chapters.setdefault(ch, []).append(slot)
    for c, slots in chapters.items():
        if c not in audio:            # 음성이 없는 챕터는 5초 칸
            for k, sl in enumerate(slots):
                sl["t0"], sl["dur"] = k * DUR, DUR
    scenes = [v for c in chapters.values() for sl in c for v in sl["variants"]]
    data = {"title": a.title, "chapters": [
        {"chapter": c, "slots": chapters[c], "audio": (audio.get(c) or {}).get("file"),
         "duration": (audio.get(c) or {}).get("duration") or len(chapters[c]) * DUR} for c in sorted(chapters)]}
    out = a.out.resolve()
    status = out.with_suffix(".status.txt")
    jsx = (JSX.replace("__DATA__", json.dumps(data, ensure_ascii=False))
              .replace("__OUT__", json.dumps(str(out), ensure_ascii=False))
              .replace("__STATUS__", json.dumps(str(status), ensure_ascii=False))
              .replace("__DUR__", str(DUR)).replace("__FPS__", str(FPS)))
    jp = out.with_suffix(".jsx")
    jp.write_text(jsx, encoding="utf-8")
    nl = sum(len(s["layers"]) for s in scenes)
    print(f"{jp}\n  챕터 컴프 {len(chapters)} · 씬 {sum(len(c) for c in chapters.values())} · 레이어 {nl}")
    if a.run:
        if status.exists():
            status.unlink()
        subprocess.run(["osascript", "-e", f'tell application "{a.app}" to DoScriptFile "{jp}"'],
                       check=False, timeout=3600)
        print(status.read_text(encoding="utf-8") if status.exists() else "상태 파일 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
