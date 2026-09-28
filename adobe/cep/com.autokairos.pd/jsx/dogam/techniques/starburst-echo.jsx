/* 스타버스트 말풍선 에코 팝 — starburst-echo  [도감 core-17 · fx.tsx Starburst]
   노란 가시 말풍선(주아체 글자)이 3f 만에 튀어나오고, 150%·50% 고스트가 13f 동안 100%·0 으로 겹쳐 사라집니다.
   테두리 보일링 = 가시 꼭짓점 반지름을 boilEvery 마다 흔든 패스 홀드 키(Remotion random 과 같은 난수 — 미리보기와 같은 모양).
   AE 구성: 프리컴프 "NN 스타버스트 <글자>"(가시 도형 + 글자) 를 두 번 올립니다 — 본체, 고스트(에코).
   ※ 방사형 광선이 아니라 말풍선 외곽 가시입니다(금지 기법 아님). */
AKD.register("starburst-echo", {
  kind: "element", name: "스타버스트 말풍선 에코 팝",
  params: { popLen: 3, echoLen: 13, echoScale: 1.5, echoOp: 0.5, spikes: 18, innerR: 0.72, boilEvery: 4, boilAmt: 0.025, outLen: 6, rot: -8, size: 58, color: "#F7D84A" },
  content: { text: "짜장면!", x: 1360, y: 400, w: 500, h: 340, outAfter: 0, dur: 0 },
  starPath: function (P, w, h, seed, pad) {
    var A = AKD, N = Math.round(P.spikes), v = [];
    for (var i = 0; i < N * 2; i++) {
      var a = (i / (N * 2)) * Math.PI * 2;
      var r = (i % 2 === 0) ? 1 : P.innerR + 0.1 * A.rand("sb" + i);
      var j = 1 + P.boilAmt * (A.rand("j" + i + "-" + seed) - 0.5);
      v.push([pad + (0.5 + 0.5 * r * j * Math.cos(a)) * w, pad + (0.5 + 0.5 * r * j * Math.sin(a)) * h]);
    }
    return A.shapeOf(v, true);
  },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, w = C.w, h = C.h, pad = 20, me = this;
    var outF = C.outAfter > 0 ? C.outAfter : 0;
    var durF = C.dur > 0 ? C.dur : Math.round((X.comp.duration - X.t) / X.fd);
    if (outF) { durF = Math.min(durF, outF + P.outLen); }
    var pc = app.project.items.addComp(X.sceneNo + " 스타버스트 " + C.text, w + pad * 2, h + pad * 2, 1, Math.max(X.fd, durF * X.fd), X.fps);
    try { pc.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var rec = A._rec; A._rec = null;
    try {
      var s = pc.layers.addShape(); s.name = "가시 말풍선";
      var g = A.group(s.property("ADBE Root Vectors Group"), "가시");
      g.addProperty("ADBE Vector Shape - Group");
      A.paint(g, P.color);
      // 속성을 더하면 앞서 받은 참조가 무효가 됩니다 — 칠을 붙인 뒤 다시 찾습니다
      var pp = s.property("ADBE Root Vectors Group").property(1).property("ADBE Vectors Group").property(1);
      A.P(s).setValue([0, 0]); A.AP(s).setValue([0, 0]);
      // 보일링: boilEvery 마다 모양 교체(홀드)
      var ps = pp.property("ADBE Vector Shape"), ts = [], vs = [], every = Math.max(1, Math.round(P.boilEvery));
      for (var k = 0; k * every <= durF; k++) { ts.push(k * every * X.fd); vs.push(me.starPath(P, w, h, k, pad)); }
      A.holdKeys(ps, ts, vs);
      var t = A.text(pc, String(C.text).replace(/\n/g, "\r"), "글자", { font: A.FONT.jua, size: P.size, fill: "#1d1d1d", leading: P.size * 1.05 });
      A.centerText(t); A.P(t).setValue([pad + w / 2, pad + h / 2]);
    } finally { A._rec = rec; }
    var main = A.addItem(X.comp, pc, A.name(X, "스타버스트 " + C.text));
    main.startTime = X.t; main.inPoint = X.t;
    A.P(main).setValue([C.x, C.y]); A.R(main).setValue(P.rot);
    A.anim(A.S(main), [X.t, X.f(Math.max(1, P.popLen))], [[0, 0], [100, 100]], "quadOut");
    A.shadow(main, 5, 6, 0.3);
    if (outF) { A.anim(A.S(main), [X.f(outF), X.f(outF + P.outLen)], [[100, 100], [0, 0]], "cubicOut"); main.outPoint = X.f(outF + P.outLen); }
    if (P.echoLen > 0) {
      var echo = A.addItem(X.comp, pc, A.name(X, "스타버스트 고스트"));
      echo.startTime = X.t; echo.inPoint = X.t; echo.outPoint = X.f(P.echoLen);
      A.P(echo).setValue([C.x, C.y]); A.R(echo).setValue(P.rot);
      A.anim(A.S(echo), [X.t, X.f(P.echoLen)], [[100 * P.echoScale, 100 * P.echoScale], [100, 100]], "cubicOut");
      A.anim(A.O(echo), [X.t, X.f(P.echoLen)], [100 * P.echoOp, 0], "cubicOut");
      echo.moveAfter(main);
    }
    return { msg: "스타버스트 「" + C.text + "」" };
  }
});
