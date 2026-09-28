/* 원형·사진 팝(줌블러) — photo-pop  [도감 core-15 · fx.tsx CircleImg]
   선택한 사진 레이어를 원형으로 오리고(마스크) 흰 링을 두른 뒤, 사진 팝 곡선으로 튀어나오게 합니다.
   곡선: 0.4→0.7→1.0→1.08→1.03→1.0 (popLen 5f, 선형 구간) + 가우시안 블러 6→0 (popBlurLen 3f).
   링 = 레이어 뒤 원판(링 색) — 사진보다 ringW 만큼 큽니다. 그림자는 원판에 겁니다(box-shadow 0 10 24). */
AKD.register("photo-pop", {
  kind: "layer", name: "원형·사진 팝(줌블러)",
  params: { popLen: 5, popFrom: 0.4, popOver: 0.08, popBlur: 6, popBlurLen: 3, ringW: 10, shadow: 0.4, border: "#fff" },
  content: { circle: true },
  apply: function (X) {
    var A = AKD, P = X.P, done = 0;
    for (var i = 0; i < X.layers.length; i++) {
      var L = X.layers[i];
      var r = L.sourceRectAtTime(X.t, false);
      var cx = r.left + r.width / 2, cy = r.top + r.height / 2, d = Math.min(r.width, r.height);
      A.moveAnchor(L, cx, cy);
      var sc = A.S(L).value, base = [sc[0], sc[1]];
      var dispD = d * Math.abs(sc[0]) / 100;
      // 원형 마스크 + 뒤 원판(링)
      var ring = null;
      if (X.C.circle !== false) {
        A.mask(L, "원형", A.ellipseShape(cx, cy, d / 2, d / 2));
        ring = A.ellipse(X.comp, A.name(X, "원형 테두리"), dispD + 2 * P.ringW, dispD + 2 * P.ringW, P.border);
        A.P(ring).setValue(A.P(L).value);
        A.shadow(ring, 10, 24, P.shadow);
        ring.moveAfter(L);
        ring.inPoint = X.t; ring.outPoint = L.outPoint;
        ring.setParentWithJump(L);
      }
      // 등장 전에는 보이지 않게(Remotion: f < at 이면 그리지 않음)
      if (L.inPoint < X.t) { A.setAttr(L, "inPoint", X.t); }
      // 팝 곡선(선형 5구간)
      var Ln = Math.max(1, P.popLen), a = P.popFrom, ov = P.popOver;
      var ks = [a, a + (1 - a) * 0.5, 1.0, 1 + ov, 1 + ov * 0.375, 1.0], ts = [], vs = [];
      for (var k = 0; k < 6; k++) { ts.push(X.t + (k * Ln / 5) * X.fd); vs.push([base[0] * ks[k], base[1] * ks[k]]); }
      A.anim(A.S(L), ts, vs, "linear");
      // 줌블러: 사진·링 모두
      if (P.popBlur > 0) {
        var targets = ring ? [L, ring] : [L];
        for (var j = 0; j < targets.length; j++) {
          var b = A.gblur(targets[j], "팝 줌블러");
          A.anim(b.property("ADBE Gaussian Blur 2-0001"), [X.t, X.f(Math.max(1, P.popBlurLen))], [P.popBlur * A.BLUR_K, 0], "linear");
        }
      }
      done++;
    }
    return { msg: "원형·사진 팝 — 레이어 " + done + "개" };
  }
});
