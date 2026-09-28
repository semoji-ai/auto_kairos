/* 연도 두루마리 태그 — year-tag  [도감 core-11 · fx.tsx YearTag]
   왼쪽 화면 밖에서 태그 전체(종이·롤러)가 16f 감속(quartOut) 슬라이드로 들어옵니다.
   교체: 같은 컴프에 이미 떠 있는 연도 태그가 있으면, 새 태그가 그 위로 같은 방식으로 들어와 덮고
         덮인 뒤(slideLen 뒤) 이전 태그의 아웃 포인트를 자릅니다(Remotion out = 새 at + 16 과 같음).
   AE 구성: 프리컴프 "NN 연도태그 <글자>"(종이·띠·안쪽 선·롤러·글자) 하나 — 글자는 프리컴프 안에서 고칩니다.
   CSS 치수: 종이 폭 = 110 + 글자수·charW, 높이 = 줄 1.15·fontSize + 여백 16 + 띠 9×2, 롤러 28×150(+금색 캡 34×16). */
AKD.register("year-tag", {
  kind: "element", name: "연도 두루마리 태그",
  params: { slideLen: 16, fontSize: 70, charW: 58, skew: -5, paperColor: "#F7E1C4", bandColor: "#B03A2E", textColor: "#4B2420" },
  content: { text: "1912년 무렵", top: 175, outAfter: 0 },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C, text = String(C.text);
    var full = 110 + text.length * P.charW, paperH = P.fontSize * 1.15 + 16 + 18, rodH = 150;
    var W = Math.round(full + 28 + 12), H = rodH + 30;            // 캡이 위아래로 12 나옵니다
    var pc = app.project.items.addComp(X.sceneNo + " 연도태그 " + text, W, H, 1, X.comp.duration, X.fps);
    try { pc.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var cy = H / 2, rec = A._rec; A._rec = null;
    try {
      // 종이 + 위아래 띠
      var paper = A.rect(pc, "종이", full, paperH, 0, P.paperColor); A.P(paper).setValue([full / 2, cy]);
      var bandT = A.rect(pc, "띠 위", full, 9, 0, P.bandColor); A.P(bandT).setValue([full / 2, cy - paperH / 2 + 4.5]);
      var bandB = A.rect(pc, "띠 아래", full, 9, 0, P.bandColor); A.P(bandB).setValue([full / 2, cy + paperH / 2 - 4.5]);
      // 안쪽 선(inset 3~5px #D9A77E) — 띠 안쪽 영역 기준
      var innerH = paperH - 18;
      var line = A.rect(pc, "안쪽 선", full - 8, innerH - 8, 0, null, "#D9A77E", 2); A.P(line).setValue([full / 2, cy]);
      // 롤러 + 금색 캡
      var rod = A.rect(pc, "롤러", 28, rodH, 4, P.bandColor); A.P(rod).setValue([full + 14, cy]);
      var capT = A.rect(pc, "롤러 캡 위", 34, 16, 5, "#E3A33A"); A.P(capT).setValue([full + 14, cy - rodH / 2 - 4]);
      var capB = A.rect(pc, "롤러 캡 아래", 34, 16, 5, "#E3A33A"); A.P(capB).setValue([full + 14, cy + rodH / 2 + 4]);
      // 글자(연성체 + 같은 색 외곽 1.6px), 왼쪽 여백 50, 기울임 skew°
      var t = A.text(pc, text, "연도", { font: A.FONT.yeonsung, size: P.fontSize, fill: P.textColor, stroke: P.textColor, strokeW: 1.6, just: "left" });
      var r = A.centerText(t, 0, 0.5);
      A.P(t).setValue([50, cy + 2]);
      try {
        var an = t.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator"); an.name = "기울임";
        an.property("ADBE Text Animator Properties").addProperty("ADBE Text Skew").setValue(-P.skew);
      } catch (e2) {}
      void r;
    } finally { A._rec = rec; }
    // 이전 태그 교체: 지금 떠 있는 year-tag 레이어의 아웃을 새 태그가 덮은 뒤로
    for (var i = 1; i <= X.comp.numLayers; i++) {
      var L = X.comp.layer(i), ms = A.marks(L);
      for (var j = 0; j < ms.length; j++) {
        if (ms[j].id === "year-tag" && ms[j].role === "created" && L.inPoint < X.t && L.outPoint > X.t) { L.outPoint = X.f(P.slideLen); }
      }
    }
    var tag = A.addItem(X.comp, pc, A.name(X, "연도태그 " + text));
    A.AP(tag).setValue([0, cy]);
    var y = C.top + rodH / 2;
    A.anim(A.P(tag), [X.t, X.f(P.slideLen)], [[-(full + 40), y], [0, y]], "quartOut");
    A.shadow(tag, 4, 6, 0.35);
    tag.inPoint = X.t;
    if (C.outAfter > 0) { tag.outPoint = X.f(C.outAfter); }
    return { msg: "연도 태그 「" + text + "」" };
  }
});
