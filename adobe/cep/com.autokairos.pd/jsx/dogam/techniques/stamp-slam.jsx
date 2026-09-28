/* 도장 슬램 + 깜빡임 — stamp-slam  [도감 core-16 · fx.tsx Stamp]
   선택한 레이어에 "내리꽂기(startScale→1) + 착지 흔들림 + 잔상 링 + 깜빡임"을 겁니다.
   아무것도 선택하지 않으면 세모지 도장(잘난체 글자 + 둥근 테두리, 곱하기 합성)을 만들어 겁니다.
     슬램: slamDur f, 이징 in(가속)=quadIn · expoOut
     흔들림: 1 + wobble·e^(−g/decay)·sin(1.6g) — 극값 키로 굽습니다(A.fnKeys)
     잔상: 같은 도장 사본이 1→(1+0.035·echoDur) 커지며 0.6→0 사라짐
     깜빡임: blinkDelay 부터 blinkPeriod 절반씩 불투명 95%↔95%·blinkDim, blinkCount 회 (홀드 키) */
AKD.register("stamp-slam", {
  kind: "layer", create: true, name: "도장 슬램 + 깜빡임",
  params: { slamDur: 5, startScale: 2.6, wobble: 0.05, wobbleDecay: 3, echoDur: 8, blinkDelay: 8, blinkCount: 3, blinkPeriod: 8, blinkDim: 0.55, rot: -12, size: 120, color: "#EC2D5C", blink: true, slamEase: "in" },
  content: { text: "폐업", x: 960, y: 560 },
  /** 세모지 도장 프리컴프: 둥근 테두리(두께 size·0.12, 반경 size·0.28) + 잘난체 글자 */
  makeStamp: function (X) {
    var A = AKD, P = X.P, sz = P.size, bw = sz * 0.12;
    var probeW = String(X.C.text).length * sz * 1.0;
    var c = app.project.items.addComp(X.sceneNo + " 도장 " + X.C.text, Math.round(probeW + sz * 1.2 + 40), Math.round(sz * 1.6 + 40), 1, X.comp.duration, X.fps);
    try { c.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var rec = A._rec; A._rec = null;
    var W, H;
    try {
      var t = A.text(c, X.C.text, "글자", { font: A.FONT.jalnan, size: sz, fill: P.color });
      var r = t.sourceRectAtTime(0, false);
      // CSS 상자: 글자 줄높이 1.1·size, 안쪽 여백 위 0.08·아래 0.02·좌우 0.3 (size 배), 테두리 두께 bw (content-box)
      var innerW = r.width + sz * 0.6, innerH = sz * 1.1 + sz * 0.1;
      W = Math.round(innerW + 2 * bw + 20); H = Math.round(innerH + 2 * bw + 20);
      c.width = W; c.height = H;
      var box = A.rect(c, "테두리", innerW + bw, innerH + bw, sz * 0.28, null, P.color, bw);
      A.P(box).setValue([W / 2, H / 2]);
      // 글자: 줄 상자(1.1·size) 가운데 — 잘난체는 글리프가 줄 상자 아래쪽에 치우쳐 sourceRect 중심으로 맞춥니다
      A.centerText(t);
      A.P(t).setValue([W / 2, H / 2 + sz * 0.03]);
    } finally { A._rec = rec; }
    var L = A.addItem(X.comp, c, A.name(X, "도장 " + X.C.text));
    A.P(L).setValue([X.C.x, X.C.y]);
    L.blendingMode = BlendingMode.MULTIPLY;
    L.inPoint = X.t;
    return L;
  },
  apply: function (X) {
    var A = AKD, P = X.P, targets = X.layers.slice(0);
    if (!targets.length) { targets = [this.makeStamp(X)]; }
    for (var i = 0; i < targets.length; i++) {
      var L = targets[i];
      if (L.source && !(L instanceof TextLayer)) {
        var rr = L.sourceRectAtTime(X.t, false); A.moveAnchor(L, rr.left + rr.width / 2, rr.top + rr.height / 2);
      }
      var sc = A.S(L).value, S = Math.max(1, P.slamDur);
      function sv(k) { return [sc[0] * k, sc[1] * k]; }
      A.set(A.R(L), P.rot);
      // 슬램
      A.anim(A.S(L), [X.t, X.f(S)], [sv(P.startScale), sv(1)], P.slamEase === "expoOut" ? "expoOut" : "quadIn");
      // 착지 흔들림(감쇠 사인)
      if (P.wobble > 0) {
        var dec = Math.max(0.5, P.wobbleDecay), n = Math.ceil(dec * 6);
        A.fnKeys(A.S(L), X.comp, X.f(S), n, function (g) { var k = 1 + P.wobble * Math.exp(-g / dec) * Math.sin(g * 1.6); return sv(k); }, { keepFirstIn: true });
      }
      // 불투명: 0→95 (4f, cubicOut) + 깜빡임(홀드)
      var ts = [X.t, X.f(4)], vs = [0, 95], ez = ["cubicOut"];
      if (P.blink && P.blinkCount > 0) {
        var half = P.blinkPeriod / 2, cnt = Math.round(P.blinkCount);
        for (var k = 0; k < cnt * 2; k++) {
          var g = P.blinkDelay + k * half;
          if (g <= 4) { continue; }
          ez.push("hold"); ts.push(X.f(g)); vs.push(k % 2 === 0 ? 95 * P.blinkDim : 95);
        }
      }
      A.anim(A.O(L), ts, vs, ez);
      if (L.inPoint < X.t) { A.setAttr(L, "inPoint", X.t); }
      // 잔상 링
      if (P.echoDur > 0) {
        var e = A.echoOf(L, A.name(X, "도장 잔상"));
        e.inPoint = X.f(S); e.outPoint = X.f(S + P.echoDur);
        A.anim(A.S(e), [X.f(S), X.f(S + P.echoDur)], [[100, 100], [100 * (1 + P.echoDur * 0.035), 100 * (1 + P.echoDur * 0.035)]], "linear");
        A.anim(A.O(e), [X.f(S), X.f(S + P.echoDur)], [60, 0], "cubicOut");
      }
    }
    return { msg: "도장 슬램 — 레이어 " + targets.length + "개" };
  }
});
