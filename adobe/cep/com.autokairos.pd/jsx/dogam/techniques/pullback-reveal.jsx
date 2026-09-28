/* 대형 풀백 리빌 — pullback-reveal  [도감 core-07 · fx.tsx Scene cam(s0 1.5→s1 1.0, y0 255, moveF 55, delay 6)]
   사용자 방식의 "가이드 카메라": 널 "NN 가이드"에 장면 레이어를 부모로 달고, 가이드의 스케일·위치 키 두 개로
   확대(s0)에서 원래 크기(s1)로 빠져나옵니다(delay 뒤 moveF f, easeInOutCubic). 푸시인은 s0<s1 로 같은 기법입니다.
   선택 레이어가 없으면 지금 시각에 보이는(부모 없는) 레이어 전부를 답니다.
   CSS: translate(cx,cy) scale(s) · origin 50% 50% → 가이드 위치 = 화면 중심 + (x,y), 스케일 = s. */
AKD.register("pullback-reveal", {
  kind: "scene", name: "대형 풀백 리빌",
  params: { s0: 1.5, s1: 1, y0: 255, moveF: 55, delay: 6 },
  content: { x0: 0, x1: 0, y1: 0 },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, W = X.comp.width, H = X.comp.height, i;
    var ls = X.layers.slice(0);
    if (!ls.length) {
      for (i = 1; i <= X.comp.numLayers; i++) {
        var l = X.comp.layer(i);
        if (!l.parent && !l.locked && l.inPoint <= X.t && l.outPoint > X.t && !(l instanceof CameraLayer) && !(l instanceof LightLayer) && !l.adjustmentLayer) { ls.push(l); }
      }
    }
    // 이미 부모가 있는 레이어는 최상위 부모만 답니다
    var tops = [];
    for (i = 0; i < ls.length; i++) { var t = ls[i]; while (t.parent) { t = t.parent; } var dup = false; for (var j = 0; j < tops.length; j++) { if (tops[j] === t) { dup = true; } } if (!dup) { tops.push(t); } }
    var g = A.nul(X.comp, A.name(X, "가이드"));
    g.label = 9;
    A.P(g).setValue([W / 2, H / 2]);                    // 부모 연결은 정지 자세(100%, 중심)에서
    for (i = 0; i < tops.length; i++) { A.setAttr(tops[i], "parent", g); }
    var t0 = X.f(P.delay), t1 = X.f(P.delay + Math.max(1, P.moveF));
    A.anim(A.S(g), [t0, t1], [[P.s0 * 100, P.s0 * 100], [P.s1 * 100, P.s1 * 100]], "inOutCubic");
    A.anim(A.P(g), [t0, t1], [[W / 2 + C.x0, H / 2 + P.y0], [W / 2 + C.x1, H / 2 + C.y1]], "inOutCubic");
    g.inPoint = X.t;
    return { msg: "가이드 카메라 " + P.s0 + "→" + P.s1 + " (" + P.moveF + "f) — 레이어 " + tops.length + "개" };
  }
});
