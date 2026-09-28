/* 만화 연기 전환 — smoke-wipe  [도감 core-33 · fx.tsx SmokeWipe]
   회색 연기 덩어리 판이 아래에서 inLen f 만에 화면을 덮고(quartOut), holdLen 동안 머문 뒤(여기서 컷),
   outLen f 동안 위로 걷히고(quadIn), tailLen 동안 사라집니다. 덩어리마다 몽글거림(스케일 사인)은 극값 키로 굽습니다.
   덩어리 배치·크기는 Remotion random(`px${i}` 등)과 같은 난수라 미리보기와 같은 모양입니다.
   AE 구성: "NN 연기 전환" 도형 레이어 하나(덩어리 = 그룹 하나: 원 + 흰 하이라이트 호).
   선택 레이어: 2개면 먼저 시작하는 쪽 = 나가는 장면(아웃 = 컷), 다른 쪽 = 들어오는 장면(인 = 컷). 1개면 나가는 장면만 자릅니다.
   컷 = 시작 + inLen + floor(holdLen/2) — 덮인 채 머무는 한가운데. */
AKD.register("smoke-wipe", {
  kind: "scene", name: "만화 연기 전환",
  params: { inLen: 5, holdLen: 5, outLen: 15, tailLen: 15, puffs: 22, puffSize: 260, wobble: 0.15, color: "#A8A29E", highlight: "#EDEBE8" },
  content: {},
  /** SVG 호 "M p0 a R,R 0 0 1 p1" (작은 호, 시계 방향) → 3차 베지어 한 조각 */
  arc: function (x0, y0, x1, y1, R) {
    var mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = x1 - x0, dy = y1 - y0, c = Math.sqrt(dx * dx + dy * dy), hh = Math.sqrt(Math.max(0, R * R - c * c / 4));
    // sweep=1(시계), large=0 → 중심은 진행 방향의 오른쪽 법선 쪽 (화면 y 아래가 +)
    var nx = -dy / c, ny = dx / c, cx = mx + nx * hh, cy = my + ny * hh;
    var a0 = Math.atan2(y0 - cy, x0 - cx), a1 = Math.atan2(y1 - cy, x1 - cx), da = a1 - a0;
    while (da <= 0) { da += Math.PI * 2; }
    if (da > Math.PI) { cx = mx - nx * hh; cy = my - ny * hh; a0 = Math.atan2(y0 - cy, x0 - cx); a1 = Math.atan2(y1 - cy, x1 - cx); da = a1 - a0; while (da <= 0) { da += Math.PI * 2; } }
    var k = 4 / 3 * Math.tan(da / 4) * R;
    return { v: [[x0, y0], [x1, y1]], out: [[-Math.sin(a0) * k, Math.cos(a0) * k], [0, 0]], inn: [[0, 0], [Math.sin(a1) * k, -Math.cos(a1) * k]] };
  },
  apply: function (X) {
    var A = AKD, P = X.P, me = this;
    var t1 = P.inLen, t2 = t1 + P.holdLen, t3 = t2 + P.outLen, END = t3 + P.tailLen;
    var s = A.shapeLayer(X.comp, A.name(X, "연기 전환")), root = s.property("ADBE Root Vectors Group");
    var N = Math.round(P.puffs);
    for (var i = 0; i < N; i++) {
      var px = (i % 6) * 380 - 60 + A.rand("px" + i) * 120, py = Math.floor(i / 6) * 330 + A.rand("py" + i) * 120 - 100, r = P.puffSize + A.rand("pr" + i) * 180;
      var grp = root.addProperty("ADBE Vector Group"); grp.name = "덩어리 " + (i + 1);
      var c = grp.property("ADBE Vectors Group");
      var e = c.addProperty("ADBE Vector Shape - Ellipse"); e.property("ADBE Vector Ellipse Size").setValue([r * 2, r * 2]);
      A.paint(c, P.color);
      var a = me.arc(-r * 0.55, -r * 0.35, -r * 0.55 + r * 0.7, -r * 0.35 - r * 0.3, r * 0.6);
      var hl = A.addPath(c, "하이라이트", a.v, false, null, P.highlight, 14, a.inn, a.out);
      try { hl.property("ADBE Vector Graphic - Stroke").property("ADBE Vector Stroke Line Cap").setValue(2); } catch (e1) {}
      // 하이라이트가 원 위에 오게(먼저 추가한 그룹이 위)
      hl.parentProperty.moveTo(1);
      var gt = grp.property("ADBE Vector Transform Group");
      gt.property("ADBE Vector Position").setValue([px, py]);
      if (P.wobble > 0) {
        (function (ii) {
          A.fnKeys(gt.property("ADBE Vector Scale"), X.comp, X.t, END, function (g) { var k = 100 * (1 + P.wobble * Math.sin(g / 6 + ii)); return [k, k]; });
        })(i);
      }
      root.property(root.numProperties).moveTo(1);   // SVG 처럼 나중 덩어리가 위로
    }
    A.P(s).setValue([0, 0]); A.AP(s).setValue([0, 0]);
    A.anim(A.P(s), [X.t, X.f(t1), X.f(t2), X.f(t3)], [[0, 1300], [0, 0], [0, 0], [0, -1500]], ["quartOut", "linear", "quadIn"]);
    A.anim(A.O(s), [X.f(t3), X.f(END)], [100, 0], "linear");
    s.inPoint = X.t; s.outPoint = X.f(END + 1);
    // 장면 자르기
    var cut = X.f(t1 + Math.floor(P.holdLen / 2)), ls = X.layers.slice(0).sort(function (p, q) { return (p.inPoint - q.inPoint) || (p.index - q.index); });   // 같이 시작하면 위 레이어가 나가는 장면
    if (ls.length >= 1) { A.setAttr(ls[0], "outPoint", cut); }
    if (ls.length >= 2) { A.setAttr(ls[1], "inPoint", cut); }
    return { msg: "연기 전환 — 컷 " + Math.round(cut / X.fd) + "f" + (ls.length ? " (장면 " + ls.length + "개 자름)" : "") };
  }
});
