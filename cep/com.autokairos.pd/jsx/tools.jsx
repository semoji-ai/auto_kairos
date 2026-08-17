// auto_kairos — 패널 '도구' 구역의 AE 보조 기능. 빌드 파이프라인과 무관하게
// 현재 AE 상태(선택 레이어·Final 컴프)에 작용한다. SEMOJI TOOL 1.57 이식.
// json2.jsx와 함께 로드된다(패널이 이어붙여 evalScript).

var AK_SRT_LAYER = "가져온자막";

function akToolsFindComp(name) {
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === name) { return it; }
    }
    return null;
}

// SRT 큐를 Final의 텍스트 레이어 1장에 Source Text 키프레임으로 넣는다.
// 줄별 레이어를 만들지 않는다 — 수백 줄이어도 레이어는 1개(말자막과 같은 방식).
function akImportSrt(cuesJson, tokensPath) {
    try {
        var cues = (typeof JSON === "object" && JSON.parse) ? JSON.parse(cuesJson) : eval("(" + cuesJson + ")");
        if (!cues || !cues.length) { return "ERROR: 넣을 자막이 없습니다"; }
        var comp = akToolsFindComp("Final");
        if (!comp) { return "ERROR: Final 컴프 없음 — 먼저 컴프를 빌드하세요"; }

        var size = 54, fontName = "";
        try {
            if (tokensPath) {
                var tf = new File(tokensPath);
                if (tf.exists) {
                    tf.open("r"); var raw = tf.read(); tf.close();
                    var tk = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
                    if (tk.type && tk.type.subtitle) { size = tk.type.subtitle; }
                    if (tk.fonts && tk.fonts.subtitle) { fontName = tk.fonts.subtitle; }
                }
            }
        } catch (eTk) { }

        app.beginUndoGroup("auto_kairos SRT 가져오기");
        for (var i = comp.numLayers; i >= 1; i--) {          // 같은 이름은 지우고 다시
            if (comp.layer(i).name === AK_SRT_LAYER) { comp.layer(i).remove(); }
        }
        var tl = comp.layers.addText("");
        tl.name = AK_SRT_LAYER;
        var prop = tl.property("Source Text");
        var doc = prop.value;
        doc.fontSize = size;
        doc.fillColor = [1, 1, 1];
        try { doc.applyStroke = true; doc.strokeColor = [0, 0, 0]; doc.strokeWidth = Math.max(4, size / 12); doc.strokeOverFill = false; } catch (e2) { }
        try { if (fontName) { doc.font = fontName; } } catch (e3) { }
        try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e4) { }
        tl.property("Anchor Point").setValue([0, 0]);
        tl.property("Position").setValue([comp.width / 2, comp.height * 0.86]);   // 말자막(0.92)보다 한 줄 위

        var made = 0, maxEnd = 0;
        for (var q = 0; q < cues.length; q++) {
            var c = cues[q];
            if (!c.text || c.start == null || c.end == null) { continue; }
            doc.text = String(c.text);
            prop.setValueAtTime(c.start, doc);
            made++;
            var nextStart = (q + 1 < cues.length) ? cues[q + 1].start : null;
            if (nextStart === null || nextStart > c.end + 0.02) {
                doc.text = "";
                prop.setValueAtTime(c.end, doc);
            }
            if (c.end > maxEnd) { maxEnd = c.end; }
        }
        if (maxEnd > comp.duration) { comp.duration = maxEnd; }
        tl.startTime = 0; tl.inPoint = 0; tl.outPoint = comp.duration;
        app.endUndoGroup();
        return "OK: 자막 " + made + "줄 → 레이어 1개(" + AK_SRT_LAYER + ")";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}

// 선택 레이어와 그 부모 사이에 널을 끼운다 — 계층 보존. SEMOJI NULL추가 이식.
function akInsertNull() {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        app.beginUndoGroup("auto_kairos 널 끼우기");
        var lay = sel[0];
        var prevParent = lay.parent;
        lay.parent = null;
        var pos = lay.property("Position").value;
        var nl = comp.layers.addNull();
        nl.name = lay.name + "_널";
        nl.property("Position").setValue(pos);
        nl.moveAfter(lay);
        lay.parent = nl;
        if (prevParent) { nl.parent = prevParent; }
        app.endUndoGroup();
        return "OK: " + nl.name;
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}

// 선택 레이어들에 프리셋을 건다 — 시작은 각 레이어의 inPoint, 기준값은 현재 값.
// 매니페스트 좌표·씬 시각이 없는 수동 단순판이라 build_scene.jsx의 applyMoves와 별개다.
function akApplyPreset(type, amount) {
    try {
        var comp = app.project.activeItem;
        if (!comp || !(comp instanceof CompItem)) { return "ERROR: 컴프를 여세요"; }
        var sel = comp.selectedLayers;
        if (!sel.length) { return "레이어를 선택하세요"; }
        var amt = (amount != null && amount !== "") ? parseFloat(amount) : null;
        app.beginUndoGroup("auto_kairos 프리셋: " + type);
        var done = 0;
        for (var i = 0; i < sel.length; i++) {
            var il = sel[i];
            var t0 = il.inPoint;
            var P = il.property("Position").value;
            var S = il.property("Scale").value;
            try {
                if (type === "slide_in") {
                    var off = amt || comp.width * 0.18;
                    var pp = il.property("Position");
                    pp.setValueAtTime(t0, [P[0] - off, P[1]]);
                    pp.setValueAtTime(t0 + 0.5, [P[0], P[1]]);
                } else if (type === "fade_in") {
                    var op = il.property("Opacity");
                    op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + 0.5, 100);
                } else if (type === "exit_fade") {
                    var oe = il.property("Opacity");
                    oe.setValueAtTime(il.outPoint - 0.5, 100); oe.setValueAtTime(il.outPoint, 0);
                } else if (type === "pop") {
                    var sp = il.property("Scale");
                    sp.setValueAtTime(t0, [S[0] * 0.6, S[1] * 0.6]);
                    sp.setValueAtTime(t0 + 0.35, [S[0] * 1.06, S[1] * 1.06]);
                    sp.setValueAtTime(t0 + 0.5, [S[0], S[1]]);
                } else if (type === "zoom_emphasis") {
                    var sz = il.property("Scale");
                    sz.setValueAtTime(t0, [S[0], S[1]]);
                    sz.setValueAtTime(t0 + 0.4, [S[0] * 1.08, S[1] * 1.08]);
                    sz.setValueAtTime(t0 + 0.8, [S[0], S[1]]);
                } else if (type === "drift") {
                    var dd = amt || 18;
                    var pd = il.property("Position");
                    pd.setValueAtTime(t0, [P[0], P[1]]);
                    pd.setValueAtTime(il.outPoint, [P[0] + dd, P[1] - dd * 0.4]);
                } else if (type === "shake") {
                    var sa = amt || 10, ps = il.property("Position");
                    for (var si = 0; si <= 6; si++) {
                        var ts = t0 + 0.8 * si / 6;
                        ps.setValueAtTime(ts, [P[0] + ((si % 2) ? sa : -sa) * (1 - si / 6), P[1]]);
                    }
                } else if (type === "stamp") {
                    var m0 = (amt && amt > 100) ? amt : 300;
                    var hit = t0 + 5 / (comp.frameRate || 30);
                    var st = il.property("Scale");
                    st.setValueAtTime(t0, [S[0] * m0 / 100, S[1] * m0 / 100]);
                    st.setValueAtTime(hit, [S[0], S[1]]);
                    try {
                        var ezt = new KeyframeEase(0, 33.34);
                        st.setTemporalEaseAtKey(st.nearestKeyIndex(hit), [ezt, ezt], [ezt, ezt]);
                    } catch (eEz) { }
                    var ot = il.property("Opacity");
                    ot.setValueAtTime(t0, 0); ot.setValueAtTime(hit, 100);
                } else if (type === "wiggle") {
                    var wa = amt || 8;
                    il.property("Position").expression = "wiggle(1, " + wa + ")";
                } else {
                    continue;
                }
                done++;
            } catch (eOne) { }
        }
        app.endUndoGroup();
        return "OK: " + done + "개 레이어에 " + type;
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}
