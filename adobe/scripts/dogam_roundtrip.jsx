/* 기법 도감 왕복 검사 — 적용 → 다시 적용 → 제거 후 대상 레이어가 원래대로 돌아오는지.
   dogam_verify.py --roundtrip 이 경로를 채워 실행합니다(열린 프로젝트는 건드리지 않고, 만든 아이템은 지웁니다). */
(function () {
  var OUT = "%OUT%", ROOT = "%JSX%", ASSETS = "%ASSETS%";
  var R = { ok: false, checks: [], log: [] };
  function rd(p) { var f = new File(p); f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close(); return s; }
  function chk(name, cond, info) { R.checks.push({ name: name, ok: !!cond, info: info === undefined ? "" : String(info) }); }
  var snap = {}, i;
  for (i = 1; i <= app.project.numItems; i++) { snap[app.project.item(i).id] = 1; }
  app.beginSuppressDialogs();
  try {
    eval(rd(ROOT + "/json2.jsx")); eval(rd(ROOT + "/dogam/core.jsx"));
    var T = ["stamp-slam", "idle-bob", "photo-pop", "smoke-wipe", "pullback-reveal", "dim-cutaway-drop-exit"];
    for (i = 0; i < T.length; i++) { eval(rd(ROOT + "/dogam/techniques/" + T[i] + ".jsx")); }
    var comp = app.project.items.addComp("akd_roundtrip", 1920, 1080, 1, 5, 30);
    var par = comp.layers.addNull(); par.name = "원래 부모";
    var L = comp.layers.addSolid([0.2, 0.4, 0.8], "대상", 400, 300, 1);
    L.parent = par;
    var P = L.property("ADBE Transform Group").property("ADBE Position");
    P.setValueAtTime(0, [100, 100]); P.setValueAtTime(2, [300, 100]);
    var n0 = comp.numLayers, rot0 = L.property("ADBE Transform Group").property("ADBE Rotate Z").value, in0 = L.inPoint;
    function state() { var tr = L.property("ADBE Transform Group"); return [tr.property("ADBE Scale").numKeys, tr.property("ADBE Opacity").numKeys, tr.property("ADBE Rotate Z").value, P.numKeys, L.inPoint.toFixed(3), L.parent ? L.parent.name : "-", L.property("ADBE Effect Parade").numProperties, L.property("ADBE Mask Parade").numProperties, L.property("ADBE Marker").numKeys].join("|"); }
    var s0 = state();
    // 1) 도장(레이어형) 적용 → 다시 적용(rot 5) → 제거
    var a = AKD.parse(AKD.apply("stamp-slam", { comp: comp, layers: [L], t: 1, assetsRoot: ASSETS }));
    chk("stamp apply", a.ok, a.msg || a.error);
    chk("stamp marker", L.property("ADBE Marker").numKeys === 1, L.property("ADBE Marker").numKeys);
    var r = AKD.parse(AKD.reapply({ comp: comp, layer: L, params: { rot: 5 } }));
    chk("stamp reapply", r.ok && Math.abs(L.property("ADBE Transform Group").property("ADBE Rotate Z").value - 5) < 1e-6, r.msg || r.error);
    chk("stamp reapply layers", comp.numLayers === n0 + 1, comp.numLayers + " (잔상 1)");
    var d = AKD.parse(AKD.remove({ comp: comp, layer: L }));
    chk("stamp remove", d.ok && state() === s0 && comp.numLayers === n0, state() + " vs " + s0 + " layers " + comp.numLayers);
    // 2) 까딱까딱: 부모 교체 → 제거 시 원래 부모·위치 복원
    var w0 = L.toWorld ? "" : "";
    var p0 = P.valueAtTime(2, false);
    a = AKD.parse(AKD.apply("idle-bob", { comp: comp, layers: [L], t: 0, content: { bboxes: [[0, 0, 400, 300]] }, assetsRoot: ASSETS }));
    chk("bob apply", a.ok && L.parent && L.parent.name.indexOf("까딱까딱") >= 0, a.msg || a.error);
    d = AKD.parse(AKD.remove({ comp: comp, layer: L }));
    var p1 = P.valueAtTime(2, false);
    chk("bob remove", d.ok && state() === s0 && Math.abs(p0[0] - p1[0]) < 0.01 && Math.abs(p0[1] - p1[1]) < 0.01, state() + " pos " + p1);
    // 3) 사진 팝: 마스크·앵커 → 제거 복원
    a = AKD.parse(AKD.apply("photo-pop", { comp: comp, layers: [L], t: 1, assetsRoot: ASSETS }));
    chk("photo apply", a.ok && L.property("ADBE Mask Parade").numProperties === 1, a.msg || a.error);
    d = AKD.parse(AKD.remove({ comp: comp, layer: L }));
    chk("photo remove", d.ok && state() === s0 && comp.numLayers === n0, state());
    // 4) 연기 전환: 아웃 포인트 자르기 → 복원
    var out0 = L.outPoint;
    a = AKD.parse(AKD.apply("smoke-wipe", { comp: comp, layers: [L], t: 1, assetsRoot: ASSETS }));
    chk("smoke apply", a.ok && L.outPoint < out0, a.msg || a.error);
    d = AKD.parse(AKD.remove({ comp: comp, layer: L }));
    chk("smoke remove", d.ok && Math.abs(L.outPoint - out0) < 1e-6 && comp.numLayers === n0, L.outPoint);
    // 5) 가이드 카메라: 원래 부모(널)가 있는 대상 → 최상위(원래 부모)를 가이드에 → 제거
    a = AKD.parse(AKD.apply("pullback-reveal", { comp: comp, layers: [L], t: 0, assetsRoot: ASSETS }));
    chk("cam apply", a.ok && par.parent && par.parent.name.indexOf("가이드") >= 0, a.msg || a.error);
    d = AKD.parse(AKD.remove({ comp: comp, layer: par }));
    chk("cam remove", d.ok && !par.parent && comp.numLayers === n0 && state() === s0, (par.parent ? par.parent.name : "-") + " " + state());
    // 6) 컷어웨이(생성) → 제거 후 레이어 수
    a = AKD.parse(AKD.apply("dim-cutaway-drop-exit", { comp: comp, layers: [], t: 0.5, assetsRoot: ASSETS }));
    chk("cutaway apply", a.ok, a.msg || a.error);
    var created = null; for (i = 1; i <= comp.numLayers; i++) { if (comp.layer(i).name.indexOf("말풍선") >= 0) { created = comp.layer(i); } }
    d = AKD.parse(AKD.remove({ comp: comp, layer: created }));
    chk("cutaway remove", d.ok && comp.numLayers === n0, comp.numLayers + " " + (d.msg || d.error));
    R.ok = true;
  } catch (e) {
    try { R.log.push("ERR " + String(e.message || e) + (e.line ? " line " + e.line : "")); } catch (e0) {}
  } finally {
    try { for (i = app.project.numItems; i >= 1; i--) { var it = null; try { it = app.project.item(i); } catch (e1) { continue; } if (it && !snap[it.id]) { try { it.remove(); } catch (e2) {} } } } catch (e3) {}
    R.log.push("items after cleanup " + app.project.numItems);
    app.endSuppressDialogs(false);
    var f = new File(OUT); f.encoding = "UTF-8"; f.lineFeed = "Unix"; f.open("w"); try { f.write(AKD.stringify(R)); } catch (e4) { f.write('{"ok":false}'); } f.close();
  }
})();
