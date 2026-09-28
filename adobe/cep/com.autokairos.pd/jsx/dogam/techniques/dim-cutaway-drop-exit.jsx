/* 딤 컷어웨이 낙하 퇴장 — dim-cutaway-drop-exit  [도감 x_pirates-06 · x_acting.tsx BlurDimInterrupt(reveal=wipe, exit=drop)]
   해설 인물이 끼어드는 컷어웨이: 뒤 장면 블러·딤(8f) → 인물 슬라이드업 → 말풍선 와이프 → 인물·말풍선 아래로 낙하 + 딤 해제.
   선택한 레이어 = 컷어웨이 요소(이름에 "말풍선"이 있으면 말풍선, 나머지는 인물). 선택이 없으면 세모지 캐스트 흉상 + 말풍선을 만듭니다.
   AE 구성
     · "NN 컷어웨이 딤" 조정 레이어(가우시안 블러 + 변형 102%)와 "NN 컷어웨이 어둡게" 검정 단색(불투명 = dim) — 대상보다 아래에 놓여 뒤 장면만 누릅니다.
       CSS brightness(1−d) 는 검정을 d 만큼 덮은 것과 같습니다.
     · "NN 컷어웨이 낙하" 널: 대상 전부의 부모 — 낙하(ease-in quad)를 한 곳에서 고칩니다. 세로 모션블러 = 방향 블러 키(0→최대→0). */
AKD.register("dim-cutaway-drop-exit", {
  kind: "layer", create: true, name: "딤 컷어웨이 낙하 퇴장",
  params: { dimLen: 8, blur: 12, dim: 0.4, slideDelay: 4, slideLen: 10, slideDist: 720, bubbleDelay: 20, bubblePop: 6, reveal: "wipe", wipeLen: 12, exit: "drop", exitAt: 62, dropLen: 8, dropDist: 1100, dropBlur: 10, undimLen: 10 },
  content: { cast: "walker1", x: 760, y: 1110, h: 1500, armR: "arm_palm_stop", seed: "x06", bubble: { x: 1180, y: 330, w: 420, h: 250, text: "CPU에서의\n아키텍처란?", size: 44 } },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, i;
    var narrators = [], bubbles = [], slideTargets = [];
    for (i = 0; i < X.layers.length; i++) { (/말풍선|bubble/i.test(X.layers[i].name) ? bubbles : narrators).push(X.layers[i]); }
    var created = !X.layers.length;
    if (created) {
      var rig = A.castRig(X, X.comp, C.cast, { x: C.x, y: C.y, h: C.h, bust: true, pose: { armR: C.armR }, seed: C.seed, t0: 0, label: "해설 " + C.cast });
      narrators.push(rig.layer);
      slideTargets.push(rig.bob || rig.layer);
      var b = C.bubble, bc = A.bubbleComp(X, { w: b.w, h: b.h, text: b.text, size: b.size || 44 });
      var bl = A.addItem(X.comp, bc.comp, A.name(X, "말풍선"));
      A.AP(bl).setValue([bc.padX + b.w / 2, bc.padY + b.h / 2]); A.P(bl).setValue([b.x, b.y]);
      bubbles.push(bl);
    } else {
      for (i = 0; i < narrators.length; i++) { slideTargets.push(narrators[i]); }
    }
    var all = narrators.concat(bubbles);
    // 가장 아래 대상 밑에 딤 레이어 두 장
    var lowest = all[0];
    for (i = 1; i < all.length; i++) { if (all[i].index > lowest.index) { lowest = all[i]; } }
    var dark = A.solid(X.comp, "#000000", A.name(X, "컷어웨이 어둡게"));
    var adj = A.adjust(X.comp, A.name(X, "컷어웨이 딤"));
    adj.moveAfter(lowest); dark.moveAfter(adj);
    // 컷어웨이 레이어들(말풍선·인물)보다 딤이 아래 — 인물이 부모 널을 가진 경우도 레이어 순서는 그대로
    var e0 = P.exitAt, drop = P.exit === "drop";
    var kIn = [X.t, X.f(P.dimLen)];
    A.anim(A.O(dark), kIn, [0, 100 * P.dim], "quadOut");
    var gb = A.gblur(adj, "컷어웨이 블러");
    A.anim(gb.property("ADBE Gaussian Blur 2-0001"), kIn, [0, P.blur * A.BLUR_K], "quadOut");
    var tf = A.fx(adj, "ADBE Geometry2", "컷어웨이 102%");
    A.anim(tf.property("ADBE Geometry2-0003"), kIn, [100, 102], "quadOut");
    if (drop) {
      // 딤 해제: k·(1→0) quadOut, undimLen
      var kOut = [X.f(e0), X.f(e0 + P.undimLen)];
      A.anim(A.O(dark), kOut, [100 * P.dim, 0], "quadOut");
      A.anim(gb.property("ADBE Gaussian Blur 2-0001"), kOut, [P.blur * A.BLUR_K, 0], "quadOut");
      A.anim(tf.property("ADBE Geometry2-0003"), kOut, [102, 100], "quadOut");
    }
    adj.inPoint = dark.inPoint = X.t;
    if (drop) { adj.outPoint = dark.outPoint = X.f(e0 + P.undimLen); }
    // 인물 슬라이드업(expoOut)
    var sa = P.slideDelay;
    for (i = 0; i < slideTargets.length; i++) {
      var st = slideTargets[i], p0 = A.P(st).value;
      A.anim(A.P(st), [X.f(sa), X.f(sa + P.slideLen)], [[p0[0], p0[1] + P.slideDist], [p0[0], p0[1]]], "expoOut");
    }
    for (i = 0; i < narrators.length; i++) { if (created || narrators[i].inPoint < X.f(sa)) { A.setAttr(narrators[i], "inPoint", X.f(sa)); } }
    // 말풍선: wipe(좌→우 마스크) 또는 pop(125%→100% expoOut + 블러 + 불투명)
    var ba = P.bubbleDelay;
    for (i = 0; i < bubbles.length; i++) {
      var B = bubbles[i], r = B.sourceRectAtTime(X.t, false);
      if (created || B.inPoint < X.f(ba)) { A.setAttr(B, "inPoint", X.f(ba)); }
      if (P.reveal === "wipe") {
        var x0 = r.left, x1 = r.left + r.width;
        var mk = A.mask(B, "와이프", A.rectShape(x0, r.top, x0 + 1, r.top + r.height));
        A.anim(mk, [X.f(ba), X.f(ba + P.wipeLen)], [A.rectShape(x0, r.top, x0 + 1, r.top + r.height), A.rectShape(x0, r.top, x1, r.top + r.height)], "cubicOut");
      } else {
        var s0 = A.S(B).value;
        A.anim(A.S(B), [X.f(ba), X.f(ba + P.bubblePop)], [[s0[0] * 1.25, s0[1] * 1.25], [s0[0], s0[1]]], "expoOut");
        A.anim(A.O(B), [X.f(ba), X.f(ba + Math.max(1, P.bubblePop * 0.5))], [0, 100], "linear");
        var bb = A.gblur(B, "말풍선 팝 블러");
        A.anim(bb.property("ADBE Gaussian Blur 2-0001"), [X.f(ba), X.f(ba + P.bubblePop)], [10 * A.BLUR_K, 0], "expoOut");
      }
    }
    // 낙하 퇴장: 부모 널 하나로
    if (drop) {
      var nul = A.nul(X.comp, A.name(X, "컷어웨이 낙하"));
      A.P(nul).setValue([X.comp.width / 2, X.comp.height / 2]);
      nul.inPoint = X.t;
      for (i = 0; i < all.length; i++) {
        var top = all[i];
        // 이미 부모(까딱까딱 널 등)가 있으면 그 최상위 부모를 낙하 널에 답니다
        while (top.parent && !(created && top.parent === nul)) { top = top.parent; }
        if (top === nul) { continue; }
        if (created || top !== all[i]) { top.setParentWithJump(nul); } else { A.setAttr(top, "parent", nul); }
        var db = A.fx(all[i], "ADBE Motion Blur", "낙하 모션블러");
        db.property("ADBE Motion Blur-0001").setValue(0);   // 방향 0° = 세로
        var L2 = db.property("ADBE Motion Blur-0002"), mid = P.dropLen / 2;
        A.anim(L2, [X.f(e0), X.f(e0 + mid), X.f(e0 + P.dropLen)], [0, P.dropBlur * 2 * A.BLUR_K, 0], ["easy", "easy"]);
        A.setAttr(all[i], "outPoint", X.f(e0 + P.dropLen));
      }
      var np = A.P(nul).value;
      A.anim(A.P(nul), [X.f(e0), X.f(e0 + P.dropLen)], [[np[0], np[1]], [np[0], np[1] + P.dropDist]], "quadIn");
    }
    return { msg: "딤 컷어웨이 — 인물 " + narrators.length + " · 말풍선 " + bubbles.length + (drop ? " · 낙하 " + (e0) + "f" : "") };
  }
});
