/* 지도 항로 드로우 — map-route  [도감 core-42 · fx.tsx MapRoute]
   세모지 지도(MapLibre 프리렌더 PNG) 위에 산둥(지부)→인천 항로가 그려지고(routeLen f, inOutCubic, Trim Paths),
   정크선이 항로를 따라 가며 흔들리고, 항구 점·라벨이 팝, 카메라는 zoom0→zoom1 로 천천히 다가갑니다(camLen f, inOutCubic).
   한반도가 크게 나오는 지도라 울릉도·독도 섬을 좌표로 직접 그립니다(필수 규칙, 라벨은 강제 아님).
   AE 구성: 프리컴프 "NN 지도 항로"
     "NN 가이드(지도)"            ← 카메라: 스케일·위치 키(프리렌더 줌 기준)
     항로·점·배·라벨·섬 레이어     ← 위치만 카메라 줌을 따라가고 크기는 고정(Remotion 과 같음)
   지도 배경은 video 쪽 MapBg(123.4°E 37.4°N, zoom 6.2, 2364×1330)로 뽑은 PNG 입니다.
   중심을 옮기면 그만큼 PNG 를 밀어 맞추지만, 바다·육지 색이나 범위를 크게 바꾸려면 MapBg 를 다시 렌더해야 합니다(AE 지원 partial). */
AKD.register("map-route", {
  kind: "scene", name: "지도 항로 드로우", support: "partial",
  note: "지도 배경은 프리렌더 PNG(바다·육지 색 변경 시 MapBg 재렌더). 붓 화살표(stroke=brush)는 굵은 선 + 흰 테두리로 근사.",
  params: { routeLen: 36, labelStagger: 1, dotLen: 6, camLen: 90, boatRock: 4, zoom0: 5.9, zoom1: 6.2, centerLng: 123.4, centerLat: 37.4, routeW: 9, dotR: 13, routeColor: "#C0392B", seaColor: "#8FBFD6", landColor: "#EAD9B6", stroke: "line", brushW: 30, brushTail: 0.25, brushBorder: 5, brushHead: 2, brushLen: 25 },
  content: {
    routeAt: 20, labelsAt: 6, dur: 0,
    mapImage: "map/map_bg.png", mapLng: 123.4, mapLat: 37.4, mapZoom: 6.2,
    from: [121.39, 37.54], to: [126.62, 37.46], ctrl: [124.0, 38.5],
    labels: [
      { text: "산둥(山東)", ll: [118.6, 36.3], dx: 0, dy: 0, dl: 0, big: true },
      { text: "인천", ll: [126.62, 37.46], dx: 0, dy: -66, dl: 6, big: false },
      { text: "청(淸)", ll: [116.4, 39.9], dx: 0, dy: 0, dl: 10, big: true },
      { text: "조선", ll: [127.8, 38.9], dx: 0, dy: 0, dl: 14, big: true }
    ],
    sea: { text: "황 해", ll: [123.6, 36.2] },
    boat: "junk_sailboat"
  },
  merc: function (ll) {
    var r = ll[1] * Math.PI / 180;
    return [(ll[0] + 180) / 360, (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2];
  },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, me = this, W = X.comp.width, H = X.comp.height;
    var durF = C.dur > 0 ? C.dur : Math.round((X.comp.duration - X.t) / X.fd);
    var fd = X.fd, zr = P.zoom1, mc = me.merc([P.centerLng, P.centerLat]);
    function px(ll) { var m = me.merc(ll), s = Math.pow(2, zr) * 512; return [W / 2 + (m[0] - mc[0]) * s, H / 2 + (m[1] - mc[1]) * s]; }
    var cam = P.camLen > 0, q0 = cam ? Math.pow(2, P.zoom0 - zr) : 1, CL = Math.max(1, P.camLen);
    function zq(f) { return cam ? Math.pow(2, A.lerp(f, 0, CL, P.zoom0, P.zoom1, "inOutCubic") - zr) : 1; }
    function at(p, q) { return [W / 2 + (p[0] - W / 2) * q, H / 2 + (p[1] - H / 2) * q]; }
    /** 줌을 따라가는 위치 키(크기는 고정) */
    function follow(l, p) { if (cam) { A.anim(A.P(l), [0, CL * fd], [at(p, q0), p], "inOutCubic"); } else { A.P(l).setValue(p); } }
    var pc = app.project.items.addComp(X.sceneNo + " 지도 항로", W, H, 1, durF * fd, X.fps);
    try { pc.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var rec = A._rec; A._rec = null;
    try {
      pc.bgColor = A.rgb(P.seaColor);
      // 가이드(지도 PNG) — 카메라
      var mi = A.imp(C.mapImage.charAt(0) === "/" ? C.mapImage : A.asset(X, C.mapImage));
      var g = pc.layers.add(mi); g.name = X.sceneNo + " 가이드(지도)";
      var mm = me.merc([C.mapLng, C.mapLat]);
      var gp = [W / 2 + (mm[0] - mc[0]) * Math.pow(2, zr) * 512, H / 2 + (mm[1] - mc[1]) * Math.pow(2, zr) * 512];
      var gs = Math.pow(2, zr - C.mapZoom) * 100;
      if (cam) { A.anim(A.S(g), [0, CL * fd], [[gs * q0, gs * q0], [gs, gs]], "inOutCubic"); } else { A.S(g).setValue([gs, gs]); }
      follow(g, gp);
      // 황해
      var sp = px(C.sea.ll), sea = A.text(pc, C.sea.text, "황해", { font: A.FONT.yeonsung, size: 70, fill: "#6FA3BD" });
      follow(sea, sp);
      // 항로(2차 베지어 41점) — 레이어 스케일로 줌, 선 두께는 반대로 보정
      var pts = [], i;
      for (i = 0; i <= 40; i++) {
        var tt = i / 40, a = C.from, c = C.ctrl, b = C.to;
        pts.push(px([(1 - tt) * (1 - tt) * a[0] + 2 * (1 - tt) * tt * c[0] + tt * tt * b[0], (1 - tt) * (1 - tt) * a[1] + 2 * (1 - tt) * tt * c[1] + tt * tt * b[1]]));
      }
      var brush = P.stroke === "brush", rw = brush ? P.brushW * 0.7 : P.routeW, rl = brush ? P.brushLen : P.routeLen;
      var rt = pc.layers.addShape(); rt.name = "항로";
      var rootC = rt.property("ADBE Root Vectors Group");
      var gc = A.addPath(rootC, "항로", pts.map ? pts : pts, false, null, P.routeColor, rw);
      if (brush && P.brushBorder > 0) { A.addPath(rootC, "항로 흰 테두리", pts, false, null, "#ffffff", rw + P.brushBorder * 2); }
      try { gc.property("ADBE Vector Graphic - Stroke").property("ADBE Vector Stroke Line Cap").setValue(2); } catch (e2) {}
      var trim = rootC.addProperty("ADBE Vector Filter - Trim");
      A.anim(trim.property("ADBE Vector Trim End"), [C.routeAt * fd, (C.routeAt + rl) * fd], [0, 100], "inOutCubic");
      A.AP(rt).setValue([W / 2, H / 2]); A.P(rt).setValue([W / 2, H / 2]);
      if (cam) {
        A.anim(A.S(rt), [0, CL * fd], [[q0 * 100, q0 * 100], [100, 100]], "inOutCubic");
        A.anim(gc.property("ADBE Vector Graphic - Stroke").property("ADBE Vector Stroke Width"), [0, CL * fd], [rw / q0, rw], "inOutCubic");
      }
      // 정크선: 항로 위 점을 프레임마다(Remotion: pts[round(k·40)]) + 흔들림
      if (!brush) {
        var bi = A.imp(A.prop(X, C.boat), "기법 도감 에셋/kit"), boat = pc.layers.add(bi); boat.name = "정크선";
        A.AP(boat).setValue([bi.width / 2, bi.height]);
        A.S(boat).setValue([90 / bi.width * 100, 92 / bi.height * 100]);
        var endF = Math.max(C.routeAt + rl, cam ? CL : 0), bts = [], bvs = [];
        for (var f = C.routeAt; f <= endF; f++) {
          var k = A.lerp(f, C.routeAt, C.routeAt + rl, 0, 1, "inOutCubic"), bp = pts[Math.min(40, Math.round(k * 40))];
          bts.push(f * fd); bvs.push(at([bp[0], bp[1] + 4], zq(f)));
        }
        A.anim(A.P(boat), bts, bvs, "linear");
        A.fnKeys(A.R(boat), pc, C.routeAt * fd, durF - C.routeAt, function (gg) { return Math.sin((gg + C.routeAt) / 5) * P.boatRock; });
        boat.inPoint = C.routeAt * fd;
      }
      // 항구 점
      var ends = [C.from, C.to];
      for (i = 0; i < 2; i++) {
        var d0 = C.labelsAt + i * 6 * P.labelStagger;
        var dot = A.ellipse(pc, "항구 점 " + (i + 1), 2 * P.dotR, 2 * P.dotR, P.routeColor, "#ffffff", 5);
        var el = dot.property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group").property("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size");
        A.anim(el, [d0 * fd, (d0 + P.dotLen) * fd], [[0, 0], [2 * P.dotR, 2 * P.dotR]], "expoOut");
        follow(dot, px(ends[i]));
      }
      // 울릉도·독도(필수) — 크기 고정, 위치만 줌을 따라감
      var pxPerDeg = Math.pow(2, zr) * 512 / 360, ur = Math.max(11, pxPerDeg * 0.11 / 2), dr = Math.max(5.5, pxPerDeg * 0.004);
      var ul = A.ellipse(pc, "울릉도", ur * 2, ur * 0.85 * 2, P.landColor, "#9C8B6A", 1.5); follow(ul, px([130.8667, 37.4833]));
      var de = px([131.8694, 37.2414]), dw = px([131.8639, 37.2422]), gap = Math.max(dr * 2.4, Math.abs(de[0] - dw[0]));
      var d1 = A.ellipse(pc, "독도 동도", dr * 2, dr * 2, P.landColor, "#9C8B6A", 1.2); follow(d1, [de[0] + gap / 2, de[1]]);
      var d2 = A.ellipse(pc, "독도 서도", dr * 2.2, dr * 2.2, P.landColor, "#9C8B6A", 1.2); follow(d2, [de[0] - gap / 2, dw[1]]);
      // 라벨(텍스트 팝: 1.25→1.0 7f, 불투명 0.4→1 2f)
      var XL = { f: function (n) { return n * fd; } };
      for (i = 0; i < C.labels.length; i++) {
        var lb = C.labels[i], a0 = C.labelsAt + lb.dl * P.labelStagger, lp = px(lb.ll), pos = [lp[0] + lb.dx, lp[1] + lb.dy], L;
        if (lb.big) {
          L = A.text(pc, lb.text, "라벨 " + lb.text, { font: A.FONT.yeonsung, size: 64, fill: "#4B2420", stroke: "#ffffff", strokeW: 10 });
          A.centerText(L);
        } else {
          L = A.rect(pc, "라벨 바탕 " + lb.text, 1, 56, 8, "#302e2f");
          var tl = A.text(pc, lb.text, "라벨 " + lb.text, { font: A.FONT.neoHv, size: 40, fill: "#ffffff" });
          var tr = A.centerText(tl);
          L.property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group").property("ADBE Vector Shape - Rect").property("ADBE Vector Rect Size").setValue([tr.width + 36, 56]);
          A.P(tl).setValue(pos); A.P(L).setValue(pos); tl.setParentWithJump(L); tl.inPoint = a0 * fd;
        }
        follow(L, pos);
        A.textPop(XL, L, a0, {});
        L.inPoint = a0 * fd;
      }
    } finally { A._rec = rec; }
    var layer = A.addItem(X.comp, pc, A.name(X, "지도 항로"));
    layer.startTime = X.t; layer.inPoint = X.t;
    return { msg: "지도 항로 — 항로 " + (C.routeAt) + "f 시작 · 카메라 " + (cam ? P.camLen + "f" : "고정") };
  }
});
