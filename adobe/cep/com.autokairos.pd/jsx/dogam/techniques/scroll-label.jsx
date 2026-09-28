/* 가로 두루마리 라벨 — scroll-label  [도감 core-12 · fx.tsx ScrollLabel]
   가운데에서 두루마리가 좌우로 펼쳐집니다(startW 6% → 100%, unrollDelay 뒤 unrollLen f, cubicOut)
   + 전체가 스프링 팝(damping 11 · stiffness 190 · mass 0.7) — 스프링은 극값 키로 굽습니다.
   AE 구성
     "NN 두루마리 <글자>" 널(스프링 스케일·퇴장) ─┬─ "NN 두루마리 속지"(프리컴프: 종이·안쪽 선·한자·글자, 가운데 마스크 폭 키로 펼침)
                                                ├─ "NN 두루마리 롤러 왼쪽" / "… 오른쪽"(펼침과 같은 이징으로 x 이동)
   퇴장(outAfter > 0): 스케일 1→0 (outLen f, cubicOut). */
AKD.register("scroll-label", {
  kind: "element", name: "가로 두루마리 라벨",
  params: { unrollDelay: 3, unrollLen: 11, startW: 0.06, damping: 11, stiffness: 190, outLen: 6, size: 70, color: "#2E7D4F", paperColor: "#F6E6C2" },
  content: { text: "공화춘", sub: "", x: 960, y: 540, w: 420, outAfter: 0 },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, w = C.w, h = 116, text = String(C.text), sub = C.sub ? String(C.sub) : "";
    // 속지 프리컴프
    var pw = Math.round(w), ph = h;
    var pc = app.project.items.addComp(X.sceneNo + " 두루마리 속지 " + text, pw, ph, 1, X.comp.duration, X.fps);
    try { pc.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var rec = A._rec; A._rec = null;
    try {
      var paper = A.rect(pc, "종이", pw, ph, 0, P.paperColor); A.P(paper).setValue([pw / 2, ph / 2]);
      var line = A.rect(pc, "안쪽 선", pw - 15, ph - 15, 0, null, P.color, 3); A.P(line).setValue([pw / 2, ph / 2]);
      var t = A.text(pc, text, "글자", { font: A.FONT.yeonsung, size: P.size, fill: "#3A1F1A" });
      var rt = A.centerText(t);
      var total = rt.width, subL = null, sr = null;
      if (sub) {
        // 세로쓰기 한자(26px) — 글자 사이 줄바꿈으로 세웁니다
        subL = A.text(pc, sub.split("").join("\r"), "한자", { font: A.FONT.songti, size: 26, fill: "#5a3a2a", leading: 26 });
        sr = A.centerText(subL);
        total += sr.width + 18;
      }
      var x0 = pw / 2 - total / 2;
      if (subL) { A.P(subL).setValue([x0 + sr.width / 2, ph / 2]); x0 += sr.width + 18; }
      A.P(t).setValue([x0 + rt.width / 2, ph / 2 + 4]);   // paddingTop 8 → 가운데에서 4 아래
    } finally { A._rec = rec; }
    var grp = A.nul(X.comp, A.name(X, "두루마리 " + text));
    A.P(grp).setValue([C.x, C.y]);
    var body = A.addItem(X.comp, pc, A.name(X, "두루마리 속지"));
    A.P(body).setValue([C.x, C.y]);
    A.shadow(body, 6, 8, 0.35);
    // 펼침 마스크(가운데 기준 폭 startW·w → w)
    var ua = P.unrollDelay, ul = Math.max(1, P.unrollLen);
    function band(k) { var bw = w * k; return A.rectShape(pw / 2 - bw / 2, -2, pw / 2 + bw / 2, ph + 2); }
    var mk = A.mask(body, "펼침", band(P.startW));
    A.anim(mk, [X.f(ua), X.f(ua + ul)], [band(P.startW), band(1)], "cubicOut");
    // 롤러: 가장자리 −16 에서 폭 30 → 중심 = 가장자리 − 1
    var rods = [];
    for (var sgn = -1; sgn <= 1; sgn += 2) {
      var rod = A.shapeLayer(X.comp, A.name(X, "두루마리 롤러 " + (sgn < 0 ? "왼쪽" : "오른쪽")));
      var root = rod.property("ADBE Root Vectors Group");
      var g1 = A.group(root, "캡 위"); var r1 = g1.addProperty("ADBE Vector Shape - Rect"); r1.property("ADBE Vector Rect Size").setValue([38, 14]); r1.property("ADBE Vector Rect Position").setValue([0, -(h + 28) / 2 + 3]); r1.property("ADBE Vector Rect Roundness").setValue(4); A.paint(g1, "#6B3B22");
      var g2 = A.group(root, "캡 아래"); var r2 = g2.addProperty("ADBE Vector Shape - Rect"); r2.property("ADBE Vector Rect Size").setValue([38, 14]); r2.property("ADBE Vector Rect Position").setValue([0, (h + 28) / 2 - 3]); r2.property("ADBE Vector Rect Roundness").setValue(4); A.paint(g2, "#6B3B22");
      var g3 = A.group(root, "그늘"); var r3 = g3.addProperty("ADBE Vector Shape - Rect"); r3.property("ADBE Vector Rect Size").setValue([6, h + 28]); r3.property("ADBE Vector Rect Position").setValue([12, 0]); A.paint(g3, "#000000");
      g3.parentProperty.property("ADBE Vector Transform Group").property("ADBE Vector Group Opacity").setValue(18);
      var g4 = A.group(root, "봉"); var r4 = g4.addProperty("ADBE Vector Shape - Rect"); r4.property("ADBE Vector Rect Size").setValue([30, h + 28]); r4.property("ADBE Vector Rect Roundness").setValue(6); A.paint(g4, P.color);
      A.shadow(rod, 6, 8, 0.35);
      var xs = function (k) { return C.x + sgn * (w * k / 2 + 1); };
      A.anim(A.P(rod), [X.f(ua), X.f(ua + ul)], [[xs(P.startW), C.y], [xs(1), C.y]], "cubicOut");
      rods.push(rod);
    }
    var all = [body].concat(rods);
    for (var i = 0; i < all.length; i++) { all[i].inPoint = X.t; all[i].setParentWithJump(grp); }
    grp.inPoint = X.t;
    // 스프링 팝(극값 키)
    var n = 40;
    A.fnKeys(A.S(grp), X.comp, X.t, n, function (g) { var s = A.spring(g, X.fps, P.damping, P.stiffness, 0.7) * 100; return [s, s]; });
    if (C.outAfter > 0) {
      A.anim(A.S(grp), [X.f(C.outAfter), X.f(C.outAfter + P.outLen)], [[100, 100], [0, 0]], "cubicOut");
      for (i = 0; i < all.length; i++) { all[i].outPoint = X.f(C.outAfter + P.outLen); }
    }
    return { msg: "두루마리 「" + text + "」" };
  }
});
