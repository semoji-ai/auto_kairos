/* 아이들 까딱(바디 밥) — idle-bob  [도감 core-28 · fx.tsx LayeredCover]
   선택한 인물 레이어마다 발밑에 "NN 이름 까딱까딱" 널을 두고 ScaleY 100↔100+bobAmp 를 bobFrames 마다 핑퐁 키(이지이지).
   위상은 인물마다 다르게(시드 = 레이어 이름 또는 content.seeds) — Remotion random("bob-"+seed) 과 같은 값.
   눈 깜빡임: 선택 안에 "…눈감음 / …blink / …closed" 레이어가 있으면 짝 인물의 널에 같이 달고, 불투명 홀드 키로 깜빡입니다.
   발밑 = 알파가 있는 범위의 아래 가운데(A.alphaBBox) — 전체 캔버스 크기 누끼 PNG 도 맞습니다. content.bbox 로 직접 줄 수 있습니다.
   drift(패럴랙스)는 아직 옮기지 않았습니다(AE 지원 partial). */
AKD.register("idle-bob", {
  kind: "layer", name: "아이들 까딱(바디 밥)",
  params: { bobFrames: 10, bobAmp: 1, blink: true, blinkEvery: 120, blinkJitter: 90, blinkLen: 3, blinkTwice: 0.2, drift: 0, bgPar: 0.45, fgPar: 0.5 },
  content: { seeds: null, bboxes: null, until: 0 },
  CLOSED: /(눈감음|감은눈|__blink|blink|closed)/i,
  base: function (name) { return String(name).replace(this.CLOSED, "").replace(/(메인|main)/i, "").replace(/[\s_\-]+$/, "").replace(/[\s_\-]+/g, " "); },
  /** fx.tsx blinkClosed 와 같은 스케줄 → 감는 구간 [[g0,g1],…] (프레임) */
  blinkSpans: function (seed, P, nF) {
    var A = AKD, out = [], t = Math.round(A.rand(seed + "o") * 60) + 30, i = 0, L = Math.max(1, Math.round(P.blinkLen));
    while (t < nF && i < 1000) {
      out.push([t, t + L]);
      if (A.rand(seed + "d" + i) < P.blinkTwice) { out.push([t + 2 * L, t + 3 * L]); }
      t += Math.max(1, P.blinkEvery + Math.round(A.rand(seed + "g" + i) * P.blinkJitter));
      i++;
    }
    return out;
  },
  apply: function (X) {
    var A = AKD, P = X.P, me = this, mains = [], closed = [], i, j;
    for (i = 0; i < X.layers.length; i++) { (me.CLOSED.test(X.layers[i].name) ? closed : mains).push({ layer: X.layers[i], idx: i }); }
    var BF = Math.max(1, Math.round(P.bobFrames)), n = 0;
    for (i = 0; i < mains.length; i++) {
      var L = mains[i].layer, k = mains[i].idx;
      var seed = (X.C.seeds && X.C.seeds[k]) ? X.C.seeds[k] : L.name;
      // 발밑 피벗(컴프 좌표)
      var bb = (X.C.bboxes && X.C.bboxes[k]) ? X.C.bboxes[k] : A.alphaBBox(X.comp, L, X.t);
      var foot = (X.C.bboxes && X.C.bboxes[k]) ? [(bb[0] + bb[2]) / 2, bb[3]] : A.toComp(L, [(bb[0] + bb[2]) / 2, bb[3]]);
      var t1 = X.C.until ? X.f(X.C.until) : L.outPoint;
      var ph = Math.floor(A.rand("bob-" + seed) * BF * 2);
      var nm = me.base(L.name).replace(/^\d+\s*/, "") || ("인물" + (i + 1));
      var nul = A.bobNull(X, X.comp, L, { every: BF, amp: P.bobAmp, phase: ph, ez: "easy", t0: X.t, t1: t1, pivot: foot, label: nm + " 까딱까딱" });
      // 짝 눈감음 레이어
      for (j = 0; j < closed.length; j++) {
        var cl = closed[j].layer;
        if (closed[j].used || me.base(cl.name) !== me.base(L.name)) { continue; }
        closed[j].used = true;
        A.setAttr(cl, "parent", nul);
        if (P.blink) {
          var cseed = (X.C.seeds && X.C.seeds[closed[j].idx]) ? X.C.seeds[closed[j].idx] : seed;
          var nF = Math.round((t1 - X.t) / X.fd), sp = me.blinkSpans(cseed, P, nF), ts = [X.t], vs = [0];
          for (var s = 0; s < sp.length; s++) { ts.push(X.f(sp[s][0])); vs.push(100); ts.push(X.f(sp[s][1])); vs.push(0); }
          A.holdKeys(A.O(cl), ts, vs);
        }
      }
      n++;
    }
    return { msg: "까딱까딱 — 인물 " + n + "명" + (closed.length ? ", 눈 깜빡임 " + closed.length : "") };
  }
});
