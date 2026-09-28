/* 세로 막대그래프 + 리본 헤더 + 마스코트 — bar-chart-v  [도감 charts-04 · charts.tsx BarChartV]
   리본 제목이 위에서 떨어지고(ribbonDrop f, cubicOut), 그룹마다 groupStagger 간격으로 기준선·라벨이 뜨고
   막대가 growDur f 동안 자랍니다(ease auto = cubicOut). 강조 막대 위 마스코트는 0→1.15→1.0 팝,
   icons(소품 id)가 있으면 막대 끝에 back-out 팝(아이콘 슬롯).
   AE 구성(모두 키프레임)
     "NN 막대 리본"(도형) + "NN 막대 리본 글자"   ← 리본 널 없이 글자를 리본에 부모 연결
     그룹마다: "NN 막대 기준선 g", 막대 "NN 막대 <라벨>"(사각형 크기·위치 키 — 둥근 윗모서리 유지), 값 "NN 막대 값 <라벨>"(막대 끝을 따라 이동),
               라벨 "NN 막대 라벨 <라벨>", 캡션, 마스코트/아이콘. */
AKD.register("bar-chart-v", {
  kind: "element", name: "세로 막대그래프 + 리본 헤더 + 마스코트",
  params: { ribbonDrop: 9, groupDelay: 12, groupStagger: 45, growDur: 15, ease: "auto", mascotOvershoot: 1.15, maxH: 380, barW: 130, gap: 44, hiColor: "#FB0000", color: "#555", textColor: "#1b1b1b", staggerF: 0, iconPop: 4, iconSize: 110 },
  content: {
    title: "1인당 연간 소비량", max: 80, baseY: 830, unit: "그릇", mascot: "demo/s06_kid.png", mascotSize: 150, icons: [],
    groups: [
      { x: 520, caption: "2014년", bars: [{ label: "짜장면", value: 72, hi: true }, { label: "짬뽕", value: 41 }, { label: "탕수육", value: 23 }] },
      { x: 1400, caption: "2024년", bars: [{ label: "짜장면", value: 58, hi: true }, { label: "짬뽕", value: 49 }, { label: "마라탕", value: 37 }] }
    ]
  },
  EASE: { auto: "cubicOut", snappy: "snappy", bar: "bar", inout: "inOutCubic", out: "cubicOut", linear: "linear" },
  ribbon: function (X) {
    var A = AKD, C = X.C, P = X.P, h = 96, size = 54, y = 60;
    var bw = Math.max(360, String(C.title).length * size * 0.98 + 120), tw = h * 0.75, d = h * 0.3;
    var s = A.shapeLayer(X.comp, A.name(X, "막대 리본")), root = s.property("ADBE Root Vectors Group");
    var L = tw, R = tw + bw, ox = -(bw / 2 + tw);   // 레이어 원점 = 리본 가운데 위
    function pts(a) { var o = []; for (var i = 0; i < a.length; i++) { o.push([a[i][0] + ox, a[i][1]]); } return o; }
    A.addPath(root, "꼬리 왼쪽", pts([[0, d], [tw * 1.6, d], [tw * 1.6, d + h], [0, d + h], [tw * 0.42, d + h / 2]]), true, "#333333");
    A.addPath(root, "꼬리 오른쪽", pts([[R + tw, d], [R - tw * 0.6, d], [R - tw * 0.6, d + h], [R + tw, d + h], [R + tw - tw * 0.42, d + h / 2]]), true, "#333333");
    A.addPath(root, "접힘 왼쪽", pts([[L, h], [L + tw * 0.6, h], [L + tw * 0.6, h + d]]), true, "#000000");
    A.addPath(root, "접힘 오른쪽", pts([[R, h], [R - tw * 0.6, h], [R - tw * 0.6, h + d]]), true, "#000000");
    A.addPath(root, "리본", pts([[L, 0], [R, 0], [R, h], [L, h]]), true, "#1b1b1b");
    // 도형 그룹 순서: 먼저 추가한 것이 위 → 리본 몸통이 맨 위로 오게 순서를 뒤집습니다
    for (var k = root.numProperties; k >= 1; k--) { root.property(k).moveTo(root.numProperties); }
    A.AP(s).setValue([0, 0]);
    var t = A.text(X.comp, C.title, A.name(X, "막대 리본 글자"), { font: A.FONT.neoHv, size: size, fill: "#ffffff" });
    A.centerText(t); A.P(t).setValue([X.comp.width / 2, y + h / 2]);
    A.P(s).setValue([X.comp.width / 2, y]);
    t.setParentWithJump(s);
    A.shadow(s, 10, 16, 0.28);
    A.anim(A.P(s), [X.t, X.f(Math.max(1, P.ribbonDrop))], [[X.comp.width / 2, y - (y + h + 60)], [X.comp.width / 2, y]], "cubicOut");
    s.inPoint = t.inPoint = X.t;
  },
  /** 위쪽만 둥근 막대: 둥근 사각형 + 아래 절반 덮는 사각형. 크기·위치 키를 높이 bh(g) 에 맞춰 */
  bar: function (X, name, x, baseY, barW, bhEnd, color, t0, dur, ez) {
    var A = AKD, s = A.shapeLayer(X.comp, name), root = s.property("ADBE Root Vectors Group");
    var g = A.group(root, "막대"), rr = g.addProperty("ADBE Vector Shape - Rect");
    rr.property("ADBE Vector Rect Roundness").setValue(10);
    var sq = g.addProperty("ADBE Vector Shape - Rect");
    A.paint(g, color);
    A.P(s).setValue([x + barW / 2, baseY]); A.AP(s).setValue([0, 0]);
    var t1 = t0 + dur * X.fd, e = ez;
    A.anim(rr.property("ADBE Vector Rect Size"), [t0, t1], [[barW, 0], [barW, bhEnd]], e);
    A.anim(rr.property("ADBE Vector Rect Position"), [t0, t1], [[0, 0], [0, -bhEnd / 2]], e);
    var sqH = Math.max(0, bhEnd - 10);
    A.anim(sq.property("ADBE Vector Rect Size"), [t0, t1], [[barW, 0], [barW, sqH]], e);
    A.anim(sq.property("ADBE Vector Rect Position"), [t0, t1], [[0, 0], [0, -sqH / 2]], e);
    s.inPoint = t0;
    return s;
  },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, me = this, ez = me.EASE[P.ease] || "cubicOut";
    me.ribbon(X);
    var gd = Math.max(1, P.growDur), idx = 0, nBars = 0;
    for (var gi = 0; gi < C.groups.length; gi++) {
      var G = C.groups[gi], ga = P.groupDelay + (G.delay !== undefined ? G.delay : gi * P.groupStagger);
      var n = G.bars.length, totalW = n * P.barW + (n - 1) * P.gap, x0 = G.x - totalW / 2;
      var fadeIn = function (l) { A.anim(A.O(l), [X.f(ga), X.f(ga + 4)], [0, 100], "linear"); l.inPoint = X.f(ga); };
      var base = A.rect(X.comp, A.name(X, "막대 기준선 " + (gi + 1)), totalW + 60, 8, 4, P.textColor);
      A.P(base).setValue([G.x, C.baseY + 4]); fadeIn(base);
      for (var i = 0; i < n; i++) {
        var b = G.bars[i], bs = ga + i * P.staggerF, bh = (b.value / C.max) * P.maxH, bx = x0 + i * (P.barW + P.gap);
        var col = b.hi ? P.hiColor : P.color;
        me.bar(X, A.name(X, "막대 " + b.label), bx, C.baseY, P.barW, bh, col, X.f(bs), gd, ez);
        var icon = C.icons && C.icons[idx], iconUp = icon ? P.iconSize * 0.96 : 0, hasM = b.hi && C.mascot;
        // 값: 막대 끝 위 64px(+마스코트·아이콘 높이), 막대와 같은 이징으로 올라갑니다
        var v = A.text(X.comp, A.num(b.value) + (C.unit || ""), A.name(X, "막대 값 " + b.label), { font: A.FONT.neoHv, size: 46, fill: b.hi ? P.hiColor : P.textColor });
        A.centerText(v, 0.5, 0.5);
        var extra = 64 + (hasM ? C.mascotSize * 0.98 : 0) + iconUp, vy = function (hh) { return C.baseY - hh - extra + 30; };
        A.anim(A.P(v), [X.f(bs), X.f(bs + gd)], [[bx + P.barW / 2, vy(0)], [bx + P.barW / 2, vy(bh)]], ez);
        A.anim(A.O(v), [X.f(bs + gd - 4), X.f(bs + gd + 2)], [0, 100], "linear");
        v.inPoint = X.f(bs);
        var lb = A.text(X.comp, b.label, A.name(X, "막대 라벨 " + b.label), { font: A.FONT.neoEb, size: 32, fill: P.textColor });
        A.centerText(lb, 0.5, 0.5); A.P(lb).setValue([bx + P.barW / 2, C.baseY + 20 + 22]); fadeIn(lb);
        if (hasM) {
          var mi = A.imp(C.mascot.charAt(0) === "/" ? C.mascot : A.asset(X, C.mascot));
          var m = A.addItem(X.comp, mi, A.name(X, "막대 마스코트"));
          var ms = C.mascotSize / mi.height * 100;
          A.AP(m).setValue([mi.width / 2, mi.height]); A.P(m).setValue([bx + P.barW / 2, C.baseY - bh]);
          m.inPoint = X.f(bs + gd);
          A.anim(A.S(m), [X.f(bs + gd), X.f(bs + gd + 4), X.f(bs + gd + 7)], [[0, 0], [ms * P.mascotOvershoot, ms * P.mascotOvershoot], [ms, ms]], "cubicOut");
        }
        if (icon) {
          var ii = A.imp(A.prop(X, icon), "기법 도감 에셋/kit");
          var il = A.addItem(X.comp, ii, A.name(X, "막대 아이콘 " + b.label));
          var is = Math.min(P.iconSize / ii.width, P.iconSize / ii.height) * 100;
          A.AP(il).setValue([ii.width / 2, ii.height]); A.P(il).setValue([bx + P.barW / 2, C.baseY - bh]);
          il.inPoint = X.f(bs + gd);
          A.anim(A.S(il), [X.f(bs + gd), X.f(bs + gd + P.iconPop)], [[0, 0], [is, is]], "back");
          A.shadow(il, 4, 5, 0.2);
        }
        idx++; nBars++;
      }
      if (G.caption) {
        var cp = A.text(X.comp, G.caption, A.name(X, "막대 캡션 " + G.caption), { font: A.FONT.jua, size: 44, fill: P.textColor });
        A.centerText(cp, 0.5, 0.5); A.P(cp).setValue([G.x, C.baseY + 70 + 28]); fadeIn(cp);
      }
    }
    return { msg: "세로 막대그래프 — 그룹 " + C.groups.length + " · 막대 " + nBars };
  }
});
