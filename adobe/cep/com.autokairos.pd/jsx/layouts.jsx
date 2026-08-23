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


/* ── flow · timeline · split ────────────────────────────────────────────
   셋 다 `items` 로 돈다. 전에는 이름을 몰라 generic 으로 떨어져, 69씬이
   밋밋한 기본꼴로 나왔다.

   items 의 뜻이 갈래마다 다르다.
     flow      단계 — 왼→오른쪽으로 이어진다
     timeline  연·사건이 짝을 이룬다 (홀수는 연, 짝수는 내용)
     split     좌우 대비 — 앞의 둘을 양쪽에 세운다
   ─────────────────────────────────────────────────────────────────────── */

function _akHead(comp, s, ctx, y) {
    /* 제목 한 줄 + 밑줄. 셋이 같은 머리를 쓴다. */
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    if (!s.title) { return; }
    ctx.addTextL(comp, s.title, { x: W / 2, y: H * y, size: t.sub * 1.5 * S, rgb: c.textRgb,
                                  font: ctx.fonts.headline, box: [W * 0.8, H * 0.12], leading: 1.2,
                                  anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
    ctx.addRectL(comp, "rule", W * 0.18, H * (y + 0.075), W * 0.64, 3 * S, c.accentRgb);
}

function akLayout_flow(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var items = s.items || [];
    if (!items.length) { akLayout_generic(comp, s, ctx); return; }
    var top = s.title ? 0.15 : 0.0;
    _akHead(comp, s, ctx, 0.15);
    var n = items.length;
    var midY = H * (top ? 0.58 : 0.5);
    // 칸 너비를 개수로 나눈다. 화살표 자리를 칸 사이에 둔다.
    var margin = W * 0.08;
    var span = (W - margin * 2) / n;
    var boxW = span * 0.78;
    for (var i = 0; i < n; i++) {
        var cx = margin + span * i + span / 2;
        var plate = ctx.addRectL(comp, "flowbox" + i, cx - boxW / 2, midY - 62 * S,
                                 boxW, 124 * S, c.accentSoftRgb || c.mutedRgb);
        var tl = ctx.addTextL(comp, items[i], { x: cx, y: midY, size: t.item * 0.9 * S,
                              rgb: c.textRgb, font: ctx.fonts.body,
                              box: [boxW * 0.86, 110 * S], leading: 1.2 });
        // 단계는 하나씩 들어온다 — 흐름이 눈으로 읽혀야 한다
        var t0 = 0.2 + i * 0.45;
        var op = plate.property("Opacity"); op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + 0.3, 100);
        var ot = tl.property("Opacity");    ot.setValueAtTime(t0, 0); ot.setValueAtTime(t0 + 0.3, 100);
        if (i < n - 1) {
            var ax = margin + span * (i + 1);
            var ar = ctx.addTextL(comp, "→", { x: ax, y: midY, size: t.item * 1.4 * S,
                                  rgb: c.accentRgb, font: ctx.fonts.headline });
            var oa = ar.property("Opacity");
            oa.setValueAtTime(t0 + 0.3, 0); oa.setValueAtTime(t0 + 0.45, 100);
        }
    }
}

function akLayout_timeline(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var items = s.items || [];
    if (!items.length) { akLayout_generic(comp, s, ctx); return; }
    _akHead(comp, s, ctx, 0.14);
    // 홀수 개수면 마지막은 짝 없이 선다 — 버리지 않는다
    var pairs = [];
    for (var k = 0; k < items.length; k += 2) {
        pairs.push([items[k], (k + 1 < items.length) ? items[k + 1] : ""]);
    }
    var n = pairs.length;
    var lineY = H * (s.title ? 0.62 : 0.55);
    var margin = W * 0.10;
    var span = (W - margin * 2) / Math.max(1, n - 1 || 1);
    // 가로 축 — 왼쪽부터 자라난다
    var axis = ctx.addRectL(comp, "axis", margin, lineY - 2 * S, W - margin * 2, 4 * S, c.accentRgb);
    try {
        var sc = axis.property("Scale");
        axis.property("Anchor Point").setValue([0, axis.height / 2]);
        axis.property("Position").setValue([margin, lineY]);
        sc.setValueAtTime(0.15, [0, 100]); sc.setValueAtTime(0.15 + 0.25 * n, [100, 100]);
    } catch (eA) { }
    for (var i = 0; i < n; i++) {
        var cx = (n === 1) ? W / 2 : margin + span * i;
        var dot = ctx.addRectL(comp, "tldot" + i, cx - 9 * S, lineY - 9 * S, 18 * S, 18 * S, c.accentRgb);
        var yr = ctx.addTextL(comp, pairs[i][0], { x: cx, y: lineY - 52 * S, size: t.item * 0.95 * S,
                              rgb: c.accentRgb, font: ctx.fonts.number,
                              box: [span * 0.92, 60 * S], leading: 1.15 });
        var ev = pairs[i][1] ? ctx.addTextL(comp, pairs[i][1], { x: cx, y: lineY + 66 * S,
                              size: t.item * 0.85 * S, rgb: c.textRgb, font: ctx.fonts.body,
                              box: [span * 0.92, 120 * S], leading: 1.2 }) : null;
        var t0 = 0.3 + i * 0.35;
        var arr = [dot, yr]; if (ev) { arr.push(ev); }
        for (var q = 0; q < arr.length; q++) {
            var o = arr[q].property("Opacity");
            o.setValueAtTime(t0, 0); o.setValueAtTime(t0 + 0.3, 100);
        }
    }
}

function akLayout_split(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var items = s.items || [];
    if (items.length < 2) { akLayout_generic(comp, s, ctx); return; }
    _akHead(comp, s, ctx, 0.14);
    var topY = s.title ? 0.60 : 0.5;
    var midY = H * topY;
    var halfW = W * 0.40;
    // 가운데 세로 구분선 — 대비할 때만 긋는다(흐름에 그으면 이야기가 끊긴다)
    ctx.addRectL(comp, "divider", W / 2 - 1.5 * S, midY - H * 0.20, 3 * S, H * 0.40, c.accentRgb);
    var side = [[W * 0.28, items[0]], [W * 0.72, items[1]]];
    for (var i = 0; i < 2; i++) {
        var tl = ctx.addTextL(comp, side[i][1], { x: side[i][0], y: midY, size: t.item * S,
                              rgb: c.textRgb, font: ctx.fonts.body,
                              box: [halfW * 0.86, H * 0.34], leading: 1.25 });
        var o = tl.property("Opacity");
        o.setValueAtTime(0.25 + i * 0.4, 0); o.setValueAtTime(0.55 + i * 0.4, 100);
    }
    // 셋 이상이면 남은 것을 아래에 한 줄로 — 버리지 않는다
    if (items.length > 2) {
        var rest = [];
        for (var r = 2; r < items.length; r++) { rest.push(items[r]); }
        ctx.addTextL(comp, rest.join("  ·  "), { x: W / 2, y: H * 0.88, size: t.sub * 0.9 * S,
                     rgb: c.mutedRgb, font: ctx.fonts.body, box: [W * 0.8, H * 0.1], leading: 1.2 });
    }
}


/* ── metric_wall · before_after · counter ──────────────────────────────── */

function _akUnits(unit, n) {
    /* 단위를 값 수만큼 돌려준다.

       **`unit` 은 씬에 하나뿐인데 값마다 다를 때가 있다** — `"ml / %"`,
       `"ppm / 시간"` 처럼 온다. 하나로 쓰면 두 값에 같은 단위가 붙어 둘 다
       틀린다. `/` 로 갈라 값 순서대로 준다. 개수가 안 맞으면 첫 것을 쓴다. */
    var out = [], i;
    var raw = String(unit == null ? "" : unit);
    if (!raw) { for (i = 0; i < n; i++) { out.push(""); } return out; }
    var parts = raw.split("/");
    if (parts.length === n) {
        for (i = 0; i < n; i++) { out.push(parts[i].replace(/^\s+|\s+$/g, "")); }
        return out;
    }
    for (i = 0; i < n; i++) { out.push(raw); }
    return out;
}

function _akPlain(s) {
    /* `{{강조}}` 는 리모션 표기다. 어도비는 모르므로 괄호만 걷는다 —
       그대로 두면 화면에 중괄호가 찍힌다. */
    return String(s == null ? "" : s).replace(/\{\{\s*/g, "").replace(/\s*\}\}/g, "");
}

function akLayout_metric_wall(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var vals = s.values || [], labs = s.items || [];
    var n = Math.max(vals.length, labs.length);
    if (!n) { akLayout_generic(comp, s, ctx); return; }
    if (s.title) { _akHead(comp, s, ctx, 0.13); }
    var units = _akUnits(s.unit, vals.length);
    // 한 줄에 넷까지. 다섯을 넘으면 두 줄로 접는다 — 옆으로만 늘리면 글자가 뭉갠다
    var perRow = (n > 4) ? Math.ceil(n / 2) : n;
    var rows = Math.ceil(n / perRow);
    var margin = W * 0.07;
    var span = (W - margin * 2) / perRow;
    var baseY = H * (s.title ? (rows > 1 ? 0.46 : 0.56) : (rows > 1 ? 0.40 : 0.50));
    var rowH = H * 0.28;
    for (var i = 0; i < n; i++) {
        var r = Math.floor(i / perRow), col = i % perRow;
        var cx = margin + span * col + span / 2;
        var cy = baseY + r * rowH;
        var v = (i < vals.length) ? (String(vals[i]) + (units[i] || "")) : "";
        var lb = _akPlain((i < labs.length) ? labs[i] : "");
        var t0 = 0.25 + i * 0.3;
        var vl = ctx.addTextL(comp, v, { x: cx, y: cy, size: t.metric * 0.62 * S,
                              rgb: c.accentRgb, font: ctx.fonts.number,
                              box: [span * 0.9, rowH * 0.5], leading: 1.05 });
        var ll = ctx.addTextL(comp, lb, { x: cx, y: cy + 72 * S, size: t.metricLabel * 0.85 * S,
                              rgb: c.textRgb, font: ctx.fonts.body,
                              box: [span * 0.9, rowH * 0.4], leading: 1.2 });
        var a = [vl, ll];
        for (var q = 0; q < a.length; q++) {
            var o = a[q].property("Opacity");
            o.setValueAtTime(t0, 0); o.setValueAtTime(t0 + 0.3, 100);
        }
    }
}

function akLayout_before_after(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var items = s.items || [];
    if (items.length < 2) { akLayout_generic(comp, s, ctx); return; }
    if (s.title) { _akHead(comp, s, ctx, 0.13); }
    var midY = H * (s.title ? 0.58 : 0.50);
    var halfW = W * 0.40;
    // 앞 → 뒤. **split 과 다른 점은 가운데가 화살표라는 것이다** —
    // 구분선은 대비를 가르고, 화살표는 바뀌었다고 말한다.
    var side = [[W * 0.27, items[0], c.mutedRgb], [W * 0.73, items[1], c.textRgb]];
    var made = [];
    for (var i = 0; i < 2; i++) {
        var plate = ctx.addRectL(comp, "ba" + i, side[i][0] - halfW / 2, midY - H * 0.17,
                                 halfW, H * 0.34, c.accentSoftRgb || c.mutedRgb);
        var tl = ctx.addTextL(comp, _akPlain(side[i][1]), { x: side[i][0], y: midY,
                              size: t.item * S, rgb: side[i][2], font: ctx.fonts.body,
                              box: [halfW * 0.84, H * 0.30], leading: 1.25 });
        made.push([plate, tl]);
    }
    var ar = ctx.addTextL(comp, "→", { x: W / 2, y: midY, size: t.metric * 0.5 * S,
                          rgb: c.accentRgb, font: ctx.fonts.headline });
    // 앞을 먼저 보이고, 화살표, 그다음 뒤 — 바뀌는 순서가 눈으로 읽혀야 한다
    var steps = [[made[0], 0.25], [[ar], 0.85], [made[1], 1.05]];
    for (var k = 0; k < steps.length; k++) {
        var arr = steps[k][0], t0 = steps[k][1];
        for (var q = 0; q < arr.length; q++) {
            var o = arr[q].property("Opacity");
            o.setValueAtTime(t0, 0); o.setValueAtTime(t0 + 0.3, 100);
        }
    }
    if (items.length > 2) {
        var rest = [];
        for (var r = 2; r < items.length; r++) { rest.push(_akPlain(items[r])); }
        ctx.addTextL(comp, rest.join("  ·  "), { x: W / 2, y: H * 0.88, size: t.sub * 0.9 * S,
                     rgb: c.mutedRgb, font: ctx.fonts.body, box: [W * 0.8, H * 0.1], leading: 1.2 });
    }
}

function akLayout_counter(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var vals = s.values || [];
    if (!vals.length) { akLayout_generic(comp, s, ctx); return; }
    var raw = vals[0];
    var unit = (_akUnits(s.unit, 1))[0] || "";
    var lab = _akPlain(s.title || ((s.items && s.items.length) ? s.items[0] : ""));
    var vl = ctx.addTextL(comp, String(raw) + unit, { x: W / 2, y: H * 0.47,
                          size: t.metric * S, rgb: c.accentRgb, font: ctx.fonts.number,
                          leading: 1.0 });
    // **0 에서 세어 올린다.** 이것이 metric_spotlight 와 다른 점이다 —
    // 숫자가 불어나는 것 자체가 내용일 때 쓴다.
    var num = parseFloat(String(raw).replace(/[^0-9.\-]/g, ""));
    if (!isNaN(num)) {
        try {
            var src = vl.property("Source Text");
            var dur = 1.2, steps = 24;
            for (var k = 0; k <= steps; k++) {
                var f = k / steps;
                var cur = Math.round(num * f);
                src.setValueAtTime(0.25 + dur * f, String(cur) + unit);
            }
            for (var h = 1; h <= src.numKeys; h++) { src.setInterpolationTypeAtKey(h, KeyframeInterpolationType.HOLD); }
        } catch (eC) { }
    }
    ctx.addRectL(comp, "underline", W / 2 - 110 * S, H * 0.585, 220 * S, 5 * S, c.accentRgb);
    if (lab) {
        ctx.addTextL(comp, lab, { x: W / 2, y: H * 0.68, size: t.metricLabel * S, rgb: c.textRgb,
                      font: ctx.fonts.body, box: [W * 0.7, H * 0.12], leading: 1.3,
                      anim: { type: "slide", dir: "up", t0: 1.4, dur: 0.5 } });
    }
}

var AK_LAYOUTS = {
    "headline_only": akLayout_headline_only,
    "items_list": akLayout_items_list,
    "metric_spotlight": akLayout_metric_spotlight,
    "quote": akLayout_quote,
    "quote_portrait": akLayout_quote,
    "flow": akLayout_flow,
    "timeline": akLayout_timeline,
    "split": akLayout_split,
    "metric_wall": akLayout_metric_wall,
    "before_after": akLayout_before_after,
    "counter": akLayout_counter,
    "bar": akLayout_bar,
    "generic": akLayout_generic
};

// 등록표 조회 + 폴백. 백엔드가 이미 별칭을 해석해 보내므로 여기서는 이름 그대로 찾는다.
function akRenderLayout(comp, s, ctx) {
    var fn = AK_LAYOUTS[s.layout];
    if (!fn) { fn = akLayout_generic; }
    fn(comp, s, ctx);
}
