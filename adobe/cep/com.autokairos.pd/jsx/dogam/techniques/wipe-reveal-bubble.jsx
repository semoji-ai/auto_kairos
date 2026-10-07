/* 와이프 리빌 말풍선 — wipe-reveal-bubble  [도감 x_ref_b-05 · x_acting.tsx SpeechBubble(reveal=wipe)]
   세모지 흰 타원 말풍선이 왼쪽→오른쪽으로 펼쳐지고(wipeLen f, cubicOut — 마스크 오른쪽 끝 키),
   outAfter 뒤 꼬리 끝을 축으로 outScale 까지 줄며 사라집니다(outLen f, 선형).
   reveal=pop 이면 펼침 없이 정적으로 놓습니다(도감 기본 pop 은 "호출측이 팝을 건다").
   AE 구성: 프리컴프 "NN 말풍선 …"(타원·꼬리·연성체 글자) 한 장 — 앵커 = 꼬리 끝(퇴장 축소 중심). */
AKD.register("wipe-reveal-bubble", {
  kind: "element", name: "와이프 리빌 말풍선",
  params: { reveal: "wipe", wipeLen: 12, outLen: 3, outScale: 0.85 },
  content: { text: "짜장면이\n뭔고?", x: 1260, y: 330, w: 560, h: 260, tail: "left", size: 64, outAfter: 44 },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C;
    var bc = A.bubbleComp(X, { w: C.w, h: C.h, text: C.text, tail: C.tail, size: C.size });
    var L = A.addItem(X.comp, bc.comp, A.name(X, "말풍선 " + String(C.text).split("\n")[0]));
    // 앵커 = 꼬리 끝(ox, oy): 컴프 좌표로는 (x ∓ w/2 ∓ 0.08w, y + 0.52h)
    A.AP(L).setValue([bc.ox, bc.oy]);
    A.P(L).setValue([C.x - C.w / 2 - bc.padX + bc.ox, C.y - C.h / 2 - bc.padY + bc.oy]);
    L.startTime = 0; L.inPoint = X.t;
    if (P.reveal === "wipe") {
      // 여유 폭 −10%~110% 를 왼쪽부터 연다(Remotion clipPath inset)
      var x0 = bc.padX - 0.1 * C.w, x1 = bc.padX + 1.1 * C.w, y0 = bc.padY - 0.2 * C.h, y1 = bc.padY + 1.2 * C.h;
      var mk = A.mask(L, "와이프", A.rectShape(x0, y0, x0 + 0.5, y1));
      A.anim(mk, [X.t, X.f(Math.max(1, P.wipeLen))], [A.rectShape(x0, y0, x0 + 0.5, y1), A.rectShape(x0, y0, x1, y1)], "cubicOut");
    }
    if (C.outAfter > 0) {
      A.anim(A.S(L), [X.f(C.outAfter), X.f(C.outAfter + P.outLen)], [[100, 100], [100 * P.outScale, 100 * P.outScale]], "linear");
      A.anim(A.O(L), [X.f(C.outAfter), X.f(C.outAfter + P.outLen)], [100, 0], "linear");
      L.outPoint = X.f(C.outAfter + P.outLen);
    }
    return { msg: "말풍선 「" + String(C.text).replace(/\n/g, " ") + "」" };
  }
});
