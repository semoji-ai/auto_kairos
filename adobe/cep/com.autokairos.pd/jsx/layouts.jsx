// auto_kairos — 씬 레이아웃 렌더러. build_scene.jsx가 ctx를 만들어 호출한다.
// 헬퍼(addTextL/addRectL/addBarShape)는 akBuildScene 안의 클로저라 ctx로 받는다.
// 모르는 레이아웃 이름은 akLayout_generic이 받는다 — 내용을 버리지 않기 위해서다.

function akLayout_headline_only(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addRectL(comp, "accent", W / 2 - 60 * S, H * 0.30, 120 * S, 10 * S, c.accentRgb);
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.47, size: t.headline * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, box: [W * 0.84, H * 0.34], leading: 1.25,
                                        anim: s.textAnim || { type: "reveal", t0: 0.2, dur: 0.8 } });
    var sub = (s.descriptions && s.descriptions.length) ? s.descriptions[0] : "";
    if (sub) {
        ctx.addTextL(comp, sub, { x: W / 2, y: H * 0.67, size: t.sub * S, rgb: c.mutedRgb,
                                  font: ctx.fonts.body, box: [W * 0.7, H * 0.12], leading: 1.3,
                                  anim: { type: "slide", dir: "up", t0: 0.5, dur: 0.6 } });
    }
}

function akLayout_items_list(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.16, size: t.sub * 1.5 * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
    ctx.addRectL(comp, "rule", W * 0.16, H * 0.235, W * 0.68, 3 * S, c.accentRgb);
    var items = s.items || [];
    var y0 = H * 0.33, gap = Math.min(130 * S, (H * 0.58) / Math.max(1, items.length));
    for (var ii = 0; ii < items.length; ii++) {
        var by = y0 + ii * gap;
        var bl = ctx.addRectL(comp, "bullet" + ii, W * 0.16, by - 21 * S, 12 * S, 42 * S, c.accentRgb);
        var boxW = W * 0.62;
        var il2 = ctx.addTextL(comp, items[ii], { x: W * 0.2 + boxW / 2, y: by, size: t.item * S, rgb: c.textRgb,
                                        font: ctx.fonts.body, just: ParagraphJustification.LEFT_JUSTIFY,
                                        box: [boxW, gap * 0.9], leading: 1.2 });
        var op = il2.property("Opacity");                     // 순차 등장
        op.setValueAtTime(0.2 + ii * 0.35, 0); op.setValueAtTime(0.5 + ii * 0.35, 100);
        var opb = bl.property("Opacity");
        opb.setValueAtTime(0.2 + ii * 0.35, 0); opb.setValueAtTime(0.5 + ii * 0.35, 100);
    }
}

function akLayout_metric_spotlight(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var val = (s.values && s.values.length) ? String(s.values[0]) : "";
    var lab = (s.items && s.items.length) ? s.items[0] : "";
    if (s.unit) { val = val + s.unit; }
    ctx.addTextL(comp, val, { x: W / 2, y: H * 0.46, size: t.metric * S, rgb: c.accentRgb,
                              font: ctx.fonts.number, leading: 1.0,
                              anim: { type: "type", t0: 0.2, dur: 0.7 } });
    ctx.addRectL(comp, "underline", W / 2 - 110 * S, H * 0.585, 220 * S, 5 * S, c.accentRgb);
    ctx.addTextL(comp, lab, { x: W / 2, y: H * 0.68, size: t.metricLabel * S, rgb: c.textRgb,
                              font: ctx.fonts.body, box: [W * 0.7, H * 0.12], leading: 1.3 });
}

function akLayout_quote(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    // 인용 — 명조(경기천년바탕). 여는따옴표=텍스트 박스 좌상단, 닫는따옴표=우하단, 출처=우측 정렬
    var qf = ctx.fonts.quote || ctx.fonts.headline;
    var text = (s.items && s.items.length) ? s.items[0] : "";
    var qBoxW = W * 0.62, qBoxH = H * 0.36, qY = H * 0.47;
    ctx.addTextL(comp, "“", { x: W / 2 - qBoxW / 2 - 70 * S, y: qY - qBoxH / 2 + 10 * S,
                          size: t.quote * 2.2 * S, rgb: c.accentRgb, font: qf });
    ctx.addTextL(comp, text, { x: W / 2, y: qY, size: t.quote * S, rgb: c.textRgb,
                               font: qf, box: [qBoxW, qBoxH], leading: 1.5,
                               anim: { type: "word_stagger", t0: 0.3, dur: 1.4 } });
    ctx.addTextL(comp, "”", { x: W / 2 + qBoxW / 2 + 70 * S, y: qY + qBoxH / 2 - 10 * S,
                          size: t.quote * 2.2 * S, rgb: c.accentRgb, font: qf });
    ctx.addTextL(comp, "— " + (s.source || ""), { x: W / 2 + qBoxW / 2 - 200 * S, y: qY + qBoxH / 2 + 90 * S,
                          size: t.quoteWho * S, rgb: c.mutedRgb, font: qf,
                          just: ParagraphJustification.RIGHT_JUSTIFY, box: [400 * S, t.quoteWho * 1.6 * S] });
}

function akLayout_bar(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.13, size: t.sub * 1.4 * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
    var labels = s.items || [], vals = s.values || [];
    var n = Math.max(1, vals.length), maxV = 0;
    for (var vi = 0; vi < vals.length; vi++) { if (vals[vi] > maxV) { maxV = vals[vi]; } }
    // chartagent 명세서(chartSpec) — 없으면 단순 단색 막대 기본값
    var CS = s.chartSpec || {};
    var areaW = W * 0.7, baseY = H * 0.76, maxH = H * 0.42;
    var bw = Math.min(150 * S, areaW / n * 0.55), gap2 = areaW / n;
    var accent = [c.accentRgb[0] / 255, c.accentRgb[1] / 255, c.accentRgb[2] / 255];
    // 가이드선(기준선 위 수평선) — chartSpec.guideLineCount 만큼 점선
    var glc = CS.guideLineCount || 0;
    for (var gi = 1; gi <= glc; gi++) {
        var gy = baseY - (maxH * gi) / (glc + 1);
        var gl = ctx.addRectL(comp, "guide" + gi, W * 0.13, gy, W * 0.74, (CS.guideStrokeWidth || 1) * S, c.mutedRgb);
        gl.property("Opacity").setValue((CS.guideOpacity != null ? CS.guideOpacity : 0.3) * 100);
        ctx.applyDash(gl, CS.guideDash, S);           // 점선 패턴(있으면)
    }
    ctx.addRectL(comp, "axis", W * 0.13, baseY, W * 0.74, (CS.axisStrokeWidth || 2) * S, c.mutedRgb);  // 기준선
    for (var bi = 0; bi < n; bi++) {
        var bh = maxV ? (vals[bi] / maxV) * maxH : 0;
        var bx = W * 0.15 + gap2 * bi + (gap2 - bw) / 2;
        // chartSpec 반영 막대(채움+외곽선+해칭이 한 레이어 → Scale 애니메이션 동반)
        var bar = ctx.addBarShape(comp, "bar" + bi, bw, bh, accent, CS, S);
        bar.property("Anchor Point").setValue([0, bh / 2]);   // 하단 고정 성장
        bar.property("Position").setValue([bx + bw / 2, baseY]);
        var sc2 = bar.property("Scale");
        sc2.setValueAtTime(0.2 + bi * 0.15, [100, 0]); sc2.setValueAtTime(0.7 + bi * 0.15, [100, 100]);
        ctx.addTextL(comp, labels[bi] || "", { x: bx + bw / 2, y: baseY + 56 * S, size: t.barLabel * S,
                                               rgb: c.mutedRgb, font: ctx.fonts.body });
        var vt = ctx.addTextL(comp, String(vals[bi]) + (s.unit || ""), { x: bx + bw / 2, y: baseY - bh - 28 * S,
                                               size: t.barValue * S, rgb: c.textRgb,
                                               font: ctx.fonts.bold || ctx.fonts.body });
        var vop = vt.property("Opacity");                     // 수치는 막대 완성 후 표시
        vop.setValueAtTime(0.55 + bi * 0.15, 0); vop.setValueAtTime(0.8 + bi * 0.15, 100);
    }
}

// 모르는 레이아웃 — 공통 계약(title/items/values/descriptions/source)만으로 그린다.
// 고유한 생김새는 아니지만 내용이 화면에서 사라지지 않는다.
function akLayout_generic(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var titleY = H * 0.15;
    if (s.title) {
        ctx.addTextL(comp, s.title, { x: W / 2, y: titleY, size: t.sub * 1.5 * S, rgb: c.textRgb,
                                      font: ctx.fonts.headline, box: [W * 0.84, H * 0.14], leading: 1.2,
                                      anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
        ctx.addRectL(comp, "rule", W * 0.16, H * 0.225, W * 0.68, 3 * S, c.accentRgb);
    }
    if (s.profileName) {
        ctx.addTextL(comp, s.profileName, { x: W / 2, y: H * 0.255, size: t.sub * S, rgb: c.textRgb,
                                      font: ctx.fonts.body, box: [W * 0.7, H * 0.08], leading: 1.2 });
        if (s.profileSubtitle) {
            ctx.addTextL(comp, s.profileSubtitle, { x: W / 2, y: H * 0.30, size: t.sub * 0.6 * S,
                                      rgb: c.mutedRgb, font: ctx.fonts.body, box: [W * 0.7, H * 0.06], leading: 1.2 });
        }
    }
    var items = [];
    if (s.items) { for (var ic = 0; ic < s.items.length; ic++) { items.push(s.items[ic]); } }
    var sides = [s.left, s.right];
    for (var sd = 0; sd < sides.length; sd++) {
        var side = sides[sd];
        if (!side) continue;
        if (side.title) { items.push(side.title); }
        if (side.items) {
            for (var si = 0; si < side.items.length; si++) { items.push(side.items[si]); }
        }
    }
    var vals = s.values || [], descs = s.descriptions || [];
    var y0 = H * 0.32, gap = Math.min(150 * S, (H * 0.50) / Math.max(1, items.length));
    for (var i = 0; i < items.length; i++) {
        var by = y0 + i * gap;
        ctx.addRectL(comp, "gbullet" + i, W * 0.16, by - 18 * S, 10 * S, 36 * S, c.accentRgb);
        ctx.addTextL(comp, items[i], { x: W * 0.20 + (W * 0.48) / 2, y: by, size: t.item * S, rgb: c.textRgb,
                                       font: ctx.fonts.body, just: ParagraphJustification.LEFT_JUSTIFY,
                                       box: [W * 0.48, gap * 0.55], leading: 1.2,
                                       anim: { type: "slide", dir: "left", t0: 0.3 + i * 0.1, dur: 0.5 } });
        if (i < vals.length && vals[i] !== null && vals[i] !== undefined) {
            var vtext = String(vals[i]) + (s.unit ? s.unit : "");
            ctx.addTextL(comp, vtext, { x: W * 0.80, y: by, size: t.item * 1.1 * S, rgb: c.accentRgb,
                                        font: ctx.fonts.number, just: ParagraphJustification.RIGHT_JUSTIFY,
                                        box: [W * 0.16, gap * 0.55] });
        }
        if (i < descs.length && descs[i]) {
            ctx.addTextL(comp, descs[i], { x: W * 0.20 + (W * 0.48) / 2, y: by + gap * 0.34,
                                           size: t.item * 0.62 * S, rgb: c.mutedRgb, font: ctx.fonts.body,
                                           just: ParagraphJustification.LEFT_JUSTIFY,
                                           box: [W * 0.48, gap * 0.3], leading: 1.15 });
        }
    }
    if (s.source) {
        ctx.addTextL(comp, s.source, { x: W / 2, y: H * 0.93, size: t.item * 0.6 * S,
                                       rgb: c.mutedRgb, font: ctx.fonts.body });
    }
}

var AK_LAYOUTS = {
    "headline_only": akLayout_headline_only,
    "items_list": akLayout_items_list,
    "metric_spotlight": akLayout_metric_spotlight,
    "quote": akLayout_quote,
    "bar": akLayout_bar,
    "generic": akLayout_generic
};

// 등록표 조회 + 폴백. 백엔드가 이미 별칭을 해석해 보내므로 여기서는 이름 그대로 찾는다.
function akRenderLayout(comp, s, ctx) {
    var fn = AK_LAYOUTS[s.layout];
    if (!fn) { fn = akLayout_generic; }
    fn(comp, s, ctx);
}
