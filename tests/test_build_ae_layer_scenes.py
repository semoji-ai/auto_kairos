"""build_ae_layer_scenes.py — 프레임 정렬, 원본 가이드(꺼짐), 단어 큐, AE 실행 가드.

AE 는 돌리지 않는다. 생성된 jsx 를 node 에서 가짜 `app` 으로 실행해 가드와 배치를 본다.
"""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location("build_ae_layer_scenes",
                                                  ROOT / "scripts" / "build_ae_layer_scenes.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def proj(tmp_path):
    P = tmp_path / "proj"
    (P / "images").mkdir(parents=True)
    Image.new("RGB", (400, 225), "white").save(P / "images" / "s1.png")
    Image.new("RGB", (400, 225), "white").save(P / "images" / "s2.png")
    (tmp_path / "ch0.mp3").write_bytes(b"ID3")             # 소재 존재 확인용 빈 파일
    (P / "scene_specs.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "chapter": 0, "narration": "2026년, 재계 서열 5위에 오른 기업이 있습니다.",
         "imageAsset": {"source": "generate"}},
        {"sceneNumber": 2, "chapter": 0, "narration": "바로 한화입니다.", "imageAsset": {"source": "generate"}},
    ]}, ensure_ascii=False), encoding="utf-8")
    (P / "images" / "image_assets.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "selected": "s1.png"}, {"sceneNumber": 2, "selected": "s2.png"}]}), encoding="utf-8")
    L = P / "layers" / "S001"
    L.mkdir(parents=True)
    Image.new("RGBA", (400, 225), (255, 255, 255, 255)).save(L / "z00_background.png")
    Image.new("RGBA", (80, 60), (0, 0, 0, 255)).save(L / "z01_tower.png")
    (L / "elements.json").write_text(json.dumps({"elements": [
        {"layer": "z00_background.png", "name": "background", "z": 0, "bbox": None, "kind": "background"},
        {"layer": "z01_tower.png", "name": "golden tower", "z": 1, "bbox": [100, 50, 180, 110], "kind": "object"}]}),
        encoding="utf-8")
    timing = {"chapters": [{"chapter": 0, "audio": str(tmp_path / "ch0.mp3"), "duration": 7.637, "scenes": [
        {"n": 1, "start": 0.0, "end": 5.843, "words": [
            {"w": "2026년,", "start": 0.0, "end": 0.9}, {"w": "재계", "start": 1.0, "end": 1.3},
            {"w": "서열", "start": 1.35, "end": 1.7}, {"w": "5위에", "start": 1.77, "end": 2.2}]},
        {"n": 2, "start": 5.843, "end": 7.637, "words": [{"w": "바로", "start": 5.9, "end": 6.2}]}]}]}
    return P, timing


def test_frames_aligned_and_scene_out_overlaps_next_by_one_frame(proj, tmp_path):
    m = _mod()
    P, timing = proj
    data, _ = m.build_data(P, tmp_path / "noinfo", "t", timing)
    s1, s2 = data["chapters"][0]["slots"]
    assert (s1["f0"], s2["f0"]) == (0, round(5.843 * 30))
    assert s1["f1"] == s2["f0"] + 1                       # 앞 씬 out = 다음 씬 in + 1프레임
    assert data["chapters"][0]["frames"] == 230             # ceil(7.637 * 30)


def test_original_is_guide_off_when_layered_and_shown_when_not(proj, tmp_path):
    m = _mod()
    P, timing = proj
    data, _ = m.build_data(P, tmp_path / "noinfo", "t", timing)
    s1, s2 = data["chapters"][0]["slots"]
    assert s1["variants"][0]["original"] == "guide"         # 레이어 있음 → 꺼 둔 가이드
    assert s2["variants"][0]["original"] == "show"          # 레이어 없음 → 원본이 유일한 그림
    data2, _ = m.build_data(P, tmp_path / "noinfo", "t", timing, original="omit")
    assert data2["chapters"][0]["slots"][0]["variants"][0]["original"] == "omit"


def test_word_cues_set_layer_in_frame_and_report_unmatched(proj, tmp_path):
    m = _mod()
    P, timing = proj
    cues = {"S001": {"golden tower": "5위", "missing layer": "재계"}, "S009": {"x": "y"}}
    data, report = m.build_data(P, tmp_path / "noinfo", "t", timing, cues)
    tower = data["chapters"][0]["slots"][0]["variants"][0]["layers"][1]
    assert tower["f_in"] == round(1.77 * 30)
    reasons = {(r["key"], r.get("layer")): r["reason"] for r in report}
    assert reasons[("S001", "missing layer")] == "레이어 이름 없음"
    assert ("S009", None) in reasons
    cues2 = {"S001": {"golden tower": "없는단어"}}
    _, rep2 = m.build_data(P, tmp_path / "noinfo", "t", timing, cues2)
    assert rep2 and rep2[0]["reason"] == "단어를 못 찾음"


NODE_MOCK = r"""
var fs=require('fs');var LOG={status:null,newProject:0,close:0,saved:null,layers:[],suppress:0,undo:0};
function File(p){this.fsName=p;this.name=encodeURI(p.split('/').pop());this.exists=EXISTS.indexOf(p)>=0||(!/\.aep$/.test(p)&&fs.existsSync(p));this.encoding='';}
File.decode=function(s){return decodeURI(s);};
File.prototype.open=function(){};File.prototype.write=function(s){LOG.status=s;};File.prototype.close=function(){};
function MarkerValue(s){this.s=s;}function ImportOptions(f){this.f=f;}var CloseOptions={DO_NOT_SAVE_CHANGES:1};
function prop(){return {setValue:function(v){this.v=v;},setValueAtTime:function(t,v){}};}
function Layer(src){this.src=src;this.props={};this.enabled=true;this.guideLayer=false;}
Layer.prototype.property=function(n){if(!this.props[n])this.props[n]=(n=="ADBE Transform Group")?{property:(function(self){return function(k){if(!self.props[k])self.props[k]=prop();return self.props[k];};})(this)}:prop();return this.props[n];};
Layer.prototype.moveToEnd=function(){};
function Comp(){this.layers={add:function(src){var l=new Layer(src);LOG.layers.push(l);return l;}};this.markerProperty=prop();}
var PROJ={numItems:NUMITEMS,file:PFILE?new File(PFILE):null,items:{addFolder:function(n){return {};},addComp:function(){return new Comp();}},
 importFile:function(o){return {f:o.f.fsName};},save:function(f){LOG.saved=f.fsName;},close:function(){LOG.close++;}};
var app={project:PROJ,newProject:function(){LOG.newProject++;return PROJ;},beginSuppressDialogs:function(){LOG.suppress++;},
 endSuppressDialogs:function(){LOG.suppress--;},beginUndoGroup:function(){LOG.undo++;},endUndoGroup:function(){LOG.undo--;}};
eval(fs.readFileSync(process.argv[2],'utf8'));
console.log(JSON.stringify({status:LOG.status,newProject:LOG.newProject,close:LOG.close,saved:LOG.saved,suppress:LOG.suppress,undo:LOG.undo,
 layers:LOG.layers.map(function(l){return {name:l.name,in:l.inPoint,out:l.outPoint,enabled:l.enabled,guide:l.guideLayer};})}));
"""


def _run_jsx(tmp_path, jsx: str, numitems: int, pfile: str | None, exists: list):
    js = tmp_path / "run.js"
    head = (f"var NUMITEMS={numitems};var PFILE={json.dumps(pfile)};var EXISTS={json.dumps(exists)};\n")
    js.write_text(head + NODE_MOCK, encoding="utf-8")
    jf = tmp_path / "gen.jsx"
    jf.write_text(jsx, encoding="utf-8")
    r = subprocess.run(["node", str(js), str(jf)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node 없음")


@needs_node
def test_jsx_refuses_other_open_project_without_closing_it(proj, tmp_path):
    m = _mod()
    P, timing = proj
    data, _ = m.build_data(P, tmp_path / "noinfo", "t", timing)
    out = tmp_path / "out.aep"
    jsx = m.render_jsx(data, out, tmp_path / "s.txt", overwrite=False)
    assert all(ord(c) < 128 for c in jsx)                   # 한글은 \u 이스케이프
    res = _run_jsx(tmp_path, jsx, numitems=12, pfile="/Users/x/B231_master.aep", exists=[])
    assert res["status"].startswith("ERR") and "B231_master.aep" in res["status"]
    assert res["newProject"] == 0 and res["close"] == 0 and res["saved"] is None
    assert res["layers"] == [] and res["suppress"] == 0 and res["undo"] == 0


@needs_node
def test_jsx_builds_into_empty_project_with_guide_original_and_frame_times(proj, tmp_path):
    m = _mod()
    P, timing = proj
    data, _ = m.build_data(P, tmp_path / "noinfo", "t", timing, {"S001": {"golden tower": "5위"}})
    out = tmp_path / "out.aep"
    res = _run_jsx(tmp_path, m.render_jsx(data, out, tmp_path / "s.txt", False), 0, None, [])
    assert res["status"].startswith("OK") and res["saved"] == str(out)
    assert res["newProject"] == 0 and res["close"] == 0 and res["suppress"] == 0 and res["undo"] == 0
    by = {L["name"]: L for L in res["layers"]}
    g = by["S001 원본(가이드)"]
    assert g["enabled"] is False and g["guide"] is True
    assert by["S002 원본"]["enabled"] is True
    for L in res["layers"]:
        if L.get("in") is None:                          # 나레이션 오디오(in/out 안 건드림)
            continue
        assert abs(L["in"] * 30 - round(L["in"] * 30)) < 1e-9 and abs(L["out"] * 30 - round(L["out"] * 30)) < 1e-9
    assert round(by["S001 golden tower"]["in"] * 30) == round(1.77 * 30)


@needs_node
def test_jsx_refuses_to_overwrite_existing_target_unless_asked(proj, tmp_path):
    m = _mod()
    P, timing = proj
    data, _ = m.build_data(P, tmp_path / "noinfo", "t", timing)
    out = tmp_path / "out.aep"
    res = _run_jsx(tmp_path, m.render_jsx(data, out, tmp_path / "s.txt", False), 0, None, [str(out)])
    assert res["status"].startswith("ERR") and res["saved"] is None
    res2 = _run_jsx(tmp_path, m.render_jsx(data, out, tmp_path / "s.txt", True), 0, None, [str(out)])
    assert res2["status"].startswith("OK")
    # 대상 aep 가 이미 열려 있으면 그 안에 만든다
    res3 = _run_jsx(tmp_path, m.render_jsx(data, out, tmp_path / "s.txt", False), 5, str(out), [str(out)])
    assert res3["status"].startswith("OK")
