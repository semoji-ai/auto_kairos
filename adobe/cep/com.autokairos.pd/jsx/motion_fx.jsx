// auto_kairos — 레이어에 「거는」 모션. 키프레임이 아니라 **익스프레션 + 이펙트 컨트롤**이다.
//
// 왜 바꿨나
// ---------
// tools.jsx 의 akApplyPreset 은 키프레임을 찍는다. `t0 + 0.5` 같은 수가 코드에
// 박혀 있어 **걸고 나면 못 고친다.** 세기를 바꾸려면 지우고 다시 걸어야 했고,
// 타이밍은 아예 손댈 수가 없었다.
//
// 여기서는 둘을 나눈다.
//
//   시간 → **레이어 마커**       (`AK등장`/`AK퇴장` 을 끌면 즉시 다시 잡힌다)
//   모양 → **이펙트 컨트롤**     (시작 크기·오버슛·정점·되돌림·부드러움)
//
// 마커가 정본이고, 등장/퇴장 프레임 슬라이더는 마커를 지웠을 때의 폴백이다.
//
// 애니메이션 컴포저에서 가져온 세 가지
// ------------------------------------
// 실제로 그쪽이 레이어에 심는 식을 뜯어보고 고친 것들이다. 셋 다 견고함 문제다.
//
//   1. **모든 컨트롤 읽기를 try/catch 로 감싼다.** 사용자가 이펙트 컨트롤 하나를
//      지우면 식 전체가 죽어 레이어가 사라진다. 기본값으로 물러서면 계속 돈다.
//   2. **마커의 역할은 `parameters` 에 적는다.** 주석 칸은 사용자 것이다.
//      `zzz` 로 시작하는 이름을 쓰면 마커 대화상자에서 맨 아래로 밀린다.
//   3. **끄고 켜기는 이펙트의 fx 토글로 한다.** `effect(n).active` 를 읽으면
//      「켜기」 체크박스를 따로 둘 필요가 없다.
//
// 그리고 그쪽 `mhOvershoot` 는 진행도 0.8 부터 선형으로 깎아 **정확히 0 으로
// 끝낸다.** 감쇠식만 쓰면 끝에 미세한 잔차가 남아 레이어가 제 크기로 안 온다.
//
// 기본값의 근거
// -------------
// 애니메이션 컴포저 프리뷰를 프레임 단위로 재서 얻은 실측값이다. 「오버슛 10%
// 쯤이 좋더라」가 아니라 상용 프리셋이 실제로 그린 수치다(측정 방법은
// docs/rules 의 모션 문서 참고).
//
// 파이프라인(build_scene.jsx 의 applyMoves)은 건드리지 않는다 — 그쪽은
// motion.py 가 낸 플랜을 키프레임으로 굽는 자리이고 정본이 따로 있다.

var AK_FX = "AK ";                  // 이펙트 이름 접두사 — 지울 때 이걸로 찾는다
var AK_MASTER = "AK 모션";          // 이 이펙트의 fx 토글이 전체 on/off
var AK_TAG = "// AK-MOTION";        // 익스프레션 첫 줄 표식 — 남의 식을 지우지 않으려고
var AK_PARAM = "zzz_AK역할";        // 마커 파라미터 이름 (z 로 시작해 목록 맨 아래)
var AK_MK_IN = "AK등장";
var AK_MK_OUT = "AK퇴장";

// 계열별 기본값 — **`adobe/data/motion-bands.json` 의 p50 이다.**
// 그 파일이 정본이고 여기는 옮겨 적은 것이다(테스트가 둘이 갈리는지 본다).
//
// 근거는 애니메이션 컴포저 프리뷰 8,273편 실측이다. `peak`/`smooth` 는
// 눈대중이 아니라 곡선에 shape() 를 맞춰 얻었다(피팅 RMSE 0.005~0.038).
//
// 두 번 틀렸다.
//   · 처음엔 정점을 「곡선의 최대점 위치」로 읽었다. 정점 구간이 평평해
//     실제 무게중심은 더 뒤에 있다 — 40 이 아니라 70 이었다.
//   · 그다음엔 **대표 곡선 한 편**에 맞췄다(정점 62·부드러움 83). 그 한 편은
//     잘 맞지만 계열 전체와는 어긋난다. 기준은 분포여야 한다.
//
// `stamp` 만 실측이 없다 — 애니메이션 컴포저에 대응하는 계열이 없고,
// tools.jsx 의 기존 도장(5프레임, 300%)을 그대로 옮긴 것이다.
var AK_DEFAULTS = {
    overshoot_scale:    { start: 13,   over: 9.0,  back: 0, peak: 70, smooth: 75, inF: 13, outF: 12 },
    scale:              { start: 11,   over: 0,    back: 0, peak: 50, smooth: 37, inF: 18, outF: 16 },
    bounce_scale:       { start: 8,    over: 10.6, back: 2, peak: 80, smooth: 80, inF: 24, outF: 24 },
    position:           { move: 14.2,  dir: 1, over: 0,   peak: 50, back: 0, smooth: 23, inF: 16, outF: 15 },
    overshoot_position: { move: 14.2,  dir: 1, over: 7.0, peak: 65, back: 0, smooth: 70, inF: 16, outF: 13 },
    fade:               { smooth: 7,  inF: 14, outF: 12 },
    stamp:              { start: 300,  over: 0,    back: 0, peak: 50, smooth: 15, inF: 5,  outF: 5 }
};

var AK_DIRS = ["아래에서", "왼쪽에서", "위에서", "오른쪽에서"];

// 계열마다 안 쓰는 칸이 있다(`fade` 에는 시작 크기가 없다). 그 값이 그대로
// 식에 구워지면 `S('시작 크기 %', undefined)` 가 되어 **NaN 이 나온다** —
// 레이어가 화면에서 사라지는데 AE 는 이유를 안 알려준다.
// 안 쓰는 칸이라도 반드시 수를 채운다.
var AK_FALLBACK = { start: 100, over: 0, back: 0, peak: 50, move: 0,
                    dir: 1, smooth: 60, inF: 15, outF: 0 };

function akFxFill(d) {
    var out = {}, k;
    for (k in AK_FALLBACK) { if (AK_FALLBACK.hasOwnProperty(k)) { out[k] = AK_FALLBACK[k]; } }
    for (k in d) {
        if (d.hasOwnProperty(k) && typeof d[k] === "number" && !isNaN(d[k])) { out[k] = d[k]; }
    }
    return out;
}

function akFxIsPos(kind) { return kind === "position" || kind === "overshoot_position"; }


/* ── 이펙트 컨트롤 붙이기 ── */

function akFxSlider(il, name, val) {
    var e = il.property("ADBE Effect Parade").addProperty("ADBE Slider Control");
    e.name = AK_FX + name;
    e.property("Slider").setValue(val);
    return e;
}

function akFxCheck(il, name, on) {
    var e = il.property("ADBE Effect Parade").addProperty("ADBE Checkbox Control");
    e.name = AK_FX + name;
    e.property("Checkbox").setValue(on ? 1 : 0);
    return e;
}

// 드롭다운은 AE 17 부터다. 없으면 슬라이더로 물러선다 — 뜻은 같고 손맛만 떨어진다.
// setPropertyParameters 는 이펙트를 새로 만들어 꽂으므로, 이름은 **그 뒤에** 붙인다.
function akFxMenu(il, name, items, idx) {
    var par = il.property("ADBE Effect Parade");
    try {
        var e = par.addProperty("ADBE Dropdown Control");
        e.property(1).setPropertyParameters(items);
        e = par.property(par.numProperties);
        e.name = AK_FX + name;
        e.property(1).setValue(idx);
        return e;
    } catch (err) {
        return akFxSlider(il, name + " (1~" + items.length + ")", idx);
    }
}


/* ── 마커 ── */

// 역할은 parameters 에 적고 주석은 사람이 읽을 이름만 둔다.
// 사용자가 주석을 고쳐도 식은 parameters 로 계속 찾는다.
function akFxMarker(il, role, comment, t) {
    var mp = il.property("Marker");
    for (var i = 1; i <= mp.numKeys; i++) {
        var p = null;
        try { p = mp.keyValue(i).getParameters(); } catch (eP) { p = null; }
        if (p && p[AK_PARAM] === role) { return; }        // 이미 있으면 사용자 자리가 우선
        if (mp.keyValue(i).comment === comment) { return; }
    }
    var mv = new MarkerValue(comment);
    try {
        var o = {};
        o[AK_PARAM] = role;
        mv.setParameters(o);
    } catch (eS) { }                                       // 구버전이면 주석으로만 찾는다
    mp.setValueAtTime(t, mv);
}

function akFxClearMarkers(il) {
    var mp = il.property("Marker");
    for (var i = mp.numKeys; i >= 1; i--) {
        var mv = mp.keyValue(i), hit = false;
        try {
            var p = mv.getParameters();
            if (p && (p[AK_PARAM] === "in" || p[AK_PARAM] === "out")) { hit = true; }
        } catch (eP) { }
        if (mv.comment === AK_MK_IN || mv.comment === AK_MK_OUT) { hit = true; }
        if (hit) { mp.removeKey(i); }
    }
}


/* ── 익스프레션 조각 ──
   컨트롤을 지워도 죽지 않게 **모든 읽기에 기본값을 함께 싣는다.** */

function akFxReaders(d) {
    return [
        "function S(n, dv) { try { return effect('" + AK_FX + "' + n)('Slider'); } catch (e) { return dv; } }",
        "function C(n, dv) { try { return effect('" + AK_FX + "' + n)('Checkbox'); } catch (e) { return dv; } }",
        "function D(n, dv) { try { return effect('" + AK_FX + "' + n)(1); } catch (e) { return dv; } }",
        "function EN() { try { return effect('" + AK_MASTER + "').active ? 1 : 0; } catch (e) { return 1; } }"
    ].join("\n");
}

// 등장/퇴장 시각. 마커가 있으면 마커가 이긴다 — parameters 우선, 주석은 폴백.
function akFxTimeBlock(d) {
    return [
        "function mkT(role, cmt, dv) {",
        "  try {",
        "    for (var i = 1; i <= marker.numKeys; i++) {",
        "      var p = marker.key(i).parameters;",
        "      if (p && p['" + AK_PARAM + "'] == role) { return marker.key(i).time; }",
        "    }",
        "  } catch (e) {}",
        "  try { return marker.key(cmt).time; } catch (e2) {}",
        "  return dv;",
        "}",
        "var fd = thisComp.frameDuration;",
        "var t0 = inPoint, t3 = outPoint;",
        "var iF = S('등장 프레임', " + d.inF + "), oF = S('퇴장 프레임', " + d.outF + ");",
        "var t1 = mkT('in',  '" + AK_MK_IN + "',  t0 + iF * fd);",
        "var t2 = mkT('out', '" + AK_MK_OUT + "', t3 - oF * fd);",
        "var uIn  = (t1 > t0) ? (time - t0) / (t1 - t0) : 1;",
        "var uOut = (oF > 0 && t3 > t2) ? (t3 - time) / (t3 - t2) : 1;",
        "var u = Math.max(0, Math.min(1, Math.min(uIn, uOut)));"
    ].join("\n");
}

// 진행도 u(0~1) → 배율. 시작값에서 정점(1+over)을 찍고 1 로 감쇠한다.
// 끝 20% 는 선형으로 깎아 **정확히 1 로 닫는다** — 감쇠식만 쓰면 잔차가 남아
// 레이어가 제 크기로 돌아오지 않는다(애니메이션 컴포저도 같은 처리를 한다).
function akFxShapeFn(d) {
    return [
        "var pw = 1 + 3 * Math.max(0, Math.min(100, S('부드러움', " + d.smooth + "))) / 100;",
        "function shape(x, s0, ov, pk, bk) {",
        "  if (x <= 0) return s0;",
        "  if (x >= 1) return 1;",
        "  var y;",
        "  if (ov <= 0) { y = s0 + (1 - s0) * (1 - Math.pow(1 - x, pw)); }",
        "  else if (x < pk) { y = s0 + (1 + ov - s0) * (1 - Math.pow(1 - x / pk, pw)); }",
        "  else {",
        "    var v = (x - pk) / (1 - pk);",
        "    y = 1 + ov * Math.exp(-4 * v) * Math.cos(v * Math.PI * (0.5 + bk));",
        "  }",
        "  if (x > 0.8) { y = 1 + (y - 1) * (1 - (x - 0.8) / 0.2); }",
        "  return y;",
        "}"
    ].join("\n");
}

function akFxScaleExpr(d) {
    d = akFxFill(d);
    return [
        AK_TAG + " 크기",
        akFxReaders(d),
        "if (EN() < 0.5) { value; } else {",
        akFxTimeBlock(d),
        akFxShapeFn(d),
        "var m = shape(u, S('시작 크기 %', " + d.start + ") / 100,",
        "                 S('오버슛 %', " + d.over + ") / 100,",
        "                 Math.max(0.05, Math.min(0.95, S('정점 %', " + d.peak + ") / 100)),",
        "                 S('되돌림', " + d.back + "));",
        "var r = [];",
        "for (var i = 0; i < value.length; i++) { r[i] = value[i] * m; }",
        "r;",
        "}"
    ].join("\n");
}

function akFxPositionExpr(d) {
    d = akFxFill(d);
    return [
        AK_TAG + " 위치",
        akFxReaders(d),
        "if (EN() < 0.5) { value; } else {",
        akFxTimeBlock(d),
        akFxShapeFn(d),
        // 0(아직 화면 밖) → 1(제자리). 오버슛이 있으면 1 을 넘겨 지나쳤다 돌아온다.
        "var m = shape(u, 0, S('오버슛 %', " + d.over + ") / 100,",
        "                    Math.max(0.05, Math.min(0.95, S('정점 %', " + d.peak + ") / 100)),",
        "                    S('되돌림', " + d.back + "));",
        "var off = (1 - m) * S('이동 %', " + d.move + ") / 100;",
        "var dir = D('방향', " + d.dir + ");",
        "var dx = 0, dy = 0;",
        "if (dir == 1) { dy = off * thisComp.height; }",
        "else if (dir == 2) { dx = -off * thisComp.width; }",
        "else if (dir == 3) { dy = -off * thisComp.height; }",
        "else { dx = off * thisComp.width; }",
        "var r = [value[0] + dx, value[1] + dy];",
        "if (value.length > 2) { r[2] = value[2]; }",
        "r;",
        "}"
    ].join("\n");
}

function akFxOpacityExpr(d) {
    d = akFxFill(d);
    return [
        AK_TAG + " 투명도",
        akFxReaders(d),
        "if (EN() < 0.5 || C('투명도', 1) < 0.5) { value; } else {",
        akFxTimeBlock(d),
        akFxShapeFn(d),
        "value * shape(u, 0, 0, 0.5, 0);",
        "}"
    ].join("\n");
}


/* ── 해제 ── */

// AK 가 건 것만 걷어낸다. 사용자가 손으로 쓴 식은 남긴다.
function akFxClearOne(il) {
    var props = ["Scale", "Position", "Opacity"];
    for (var i = 0; i < props.length; i++) {
        try {
            var p = il.property("Transform").property(props[i]);
            if (p.expression && p.expression.indexOf(AK_TAG) === 0) {
                p.expression = "";
                p.expressionEnabled = false;
            }
        } catch (e) { }
    }
    var par = il.property("ADBE Effect Parade");
    for (var j = par.numProperties; j >= 1; j--) {
        var nm = par.property(j).name;
        if (nm.length >= AK_FX.length && nm.substring(0, AK_FX.length) === AK_FX) {
            par.property(j).remove();
        }
    }
    akFxClearMarkers(il);
}

function akFxClear() {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        app.beginUndoGroup("auto_kairos 모션 해제");
        for (var i = 0; i < sel.length; i++) { akFxClearOne(sel[i]); }
        app.endUndoGroup();
        return "OK: " + sel.length + "개 레이어에서 걷어냈습니다";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}


/* ── 걸기 ── */

function akFxApplyOne(il, kind, d, comp) {
    akFxClearOne(il);                         // 두 번 걸면 겹친다 — 먼저 걷어낸다

    var isPos = akFxIsPos(kind);
    var isFade = (kind === "fade");

    // 첫 이펙트가 마스터다 — 이것의 fx 토글을 끄면 전체가 꺼진다.
    akFxCheck(il, "모션", true);
    if (isPos) {
        akFxSlider(il, "이동 %", d.move);
        akFxMenu(il, "방향", AK_DIRS, d.dir);
    } else if (!isFade) {
        akFxSlider(il, "시작 크기 %", d.start);
    }
    if (!isFade) {
        akFxSlider(il, "오버슛 %", d.over);
        akFxSlider(il, "정점 %", d.peak);
        akFxSlider(il, "되돌림", d.back);
    }
    akFxSlider(il, "부드러움", d.smooth);
    akFxSlider(il, "등장 프레임", d.inF);
    akFxSlider(il, "퇴장 프레임", d.outF);
    akFxCheck(il, "투명도", true);

    // 마커를 미리 찍어 둔다 — 이게 타이밍의 손잡이다. 끌면 바로 다시 잡힌다.
    var fd = comp.frameDuration;
    akFxMarker(il, "in", AK_MK_IN, Math.min(il.outPoint - fd, il.inPoint + d.inF * fd));
    if (d.outF > 0) {
        akFxMarker(il, "out", AK_MK_OUT, Math.max(il.inPoint + fd, il.outPoint - d.outF * fd));
    }

    var T = il.property("Transform");
    if (isPos) { T.property("Position").expression = akFxPositionExpr(d); }
    else if (!isFade) { T.property("Scale").expression = akFxScaleExpr(d); }
    T.property("Opacity").expression = akFxOpacityExpr(d);
}

// kind: overshoot_scale | scale | bounce_scale | position | overshoot_position | fade | stamp
function akFxApply(kind, overrideJson) {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        var base = AK_DEFAULTS[kind];
        if (!base) { return "ERROR: 모르는 방식: " + kind; }

        var d = {}, k;
        for (k in base) { if (base.hasOwnProperty(k)) { d[k] = base[k]; } }
        if (overrideJson) {
            try {
                var o = (typeof JSON === "object" && JSON.parse)
                    ? JSON.parse(overrideJson) : eval("(" + overrideJson + ")");
                for (k in o) { if (o.hasOwnProperty(k)) { d[k] = o[k]; } }
            } catch (eJ) { }
        }

        d = akFxFill(d);

        app.beginUndoGroup("auto_kairos 모션: " + kind);
        var done = 0, fails = [];
        for (var i = 0; i < sel.length; i++) {
            try { akFxApplyOne(sel[i], kind, d, comp); done++; }
            catch (eOne) { fails.push(sel[i].name + "(" + eOne.toString() + ")"); }
        }
        app.endUndoGroup();
        if (!done) { return "ERROR: 전부 실패 — " + fails.join(", "); }
        return "OK: " + done + "개에 " + kind
            + (fails.length ? (" / 실패 " + fails.length) : "")
            + " — 마커를 끌어 시점을, 이펙트 컨트롤에서 세기를 고치세요";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}


/* ── 굽기 ── */

// 익스프레션은 조절에 좋지만 mogrt·외부 이관에는 키프레임이 필요하다.
// 프레임마다 값을 읽어 찍고 식을 끈다. 되돌리려면 다시 걸면 된다.
function akFxBake() {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        app.beginUndoGroup("auto_kairos 모션 굽기");
        var names = ["Scale", "Position", "Opacity"], done = 0;
        for (var i = 0; i < sel.length; i++) {
            var il = sel[i];
            for (var n = 0; n < names.length; n++) {
                var p;
                try { p = il.property("Transform").property(names[n]); } catch (eP) { continue; }
                if (!p.expression || p.expression.indexOf(AK_TAG) !== 0) { continue; }
                var vals = [], times = [], t;
                for (t = il.inPoint; t <= il.outPoint + 1e-6; t += comp.frameDuration) {
                    times.push(t); vals.push(p.valueAtTime(t, false));
                }
                p.expression = "";
                p.expressionEnabled = false;
                p.setValuesAtTimes(times, vals);
                done++;
            }
            akFxClearOne(il);
        }
        app.endUndoGroup();
        return "OK: " + done + "개 속성을 키프레임으로 구웠습니다";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}
