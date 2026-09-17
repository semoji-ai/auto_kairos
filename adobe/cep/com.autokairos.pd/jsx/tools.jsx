// auto_kairos — 패널 '도구' 구역의 AE 보조 기능. 빌드 파이프라인과 무관하게
// 현재 AE 상태(선택 레이어·Final 컴프)에 작용한다. SEMOJI TOOL 1.57 이식.
// json2.jsx와 함께 로드된다(패널이 이어붙여 evalScript).

var AK_SRT_LAYER = "가져온자막";      // 예전 방식(레이어 1개 + 키프레임)의 레이어 — 발견하면 정리
var AK_SRT_PREFIX = "srt_";           // 줄별 레이어 이름: srt_<번호> <자막 텍스트>

function akToolsFindComp(name) {
    for (var i = 1; i <= app.project.numItems; i++) {
        var it = app.project.item(i);
        if (it instanceof CompItem && it.name === name) { return it; }
    }
    return null;
}

// akImportSrt 가 만든 줄별 자막 레이어인가 — "srt_" + 숫자 (+ " 텍스트")
function akIsSrtLayerName(nm) {
    if (nm.length <= AK_SRT_PREFIX.length) { return false; }
    if (nm.substring(0, AK_SRT_PREFIX.length) !== AK_SRT_PREFIX) { return false; }
    var i = AK_SRT_PREFIX.length, sawDigit = false;
    while (i < nm.length && nm.charAt(i) >= "0" && nm.charAt(i) <= "9") { i++; sawDigit = true; }
    if (!sawDigit) { return false; }
    return i === nm.length || nm.charAt(i) === " ";
}

// SRT 큐를 Final에 **줄마다 텍스트 레이어 하나씩** 넣는다 — SEMOJI TOOL 자막작업 방식.
// 스타일은 선택한 텍스트 레이어가 있으면 그것을 기준으로 통째로 복사하고,
// 없으면 ae_tokens.json 값으로 만든다(말자막 subtitle_layers.jsx 와 같은 규칙).
function akImportSrt(cuesJson, tokensPath) {
    try {
        var cues = (typeof JSON === "object" && JSON.parse) ? JSON.parse(cuesJson) : eval("(" + cuesJson + ")");
        if (!cues || !cues.length) { return "ERROR: 넣을 자막이 없습니다"; }
        var comp = akToolsFindComp("Final");
        if (!comp) { return "ERROR: Final 컴프 없음 — 먼저 컴프를 빌드하세요"; }

        // 크기·글꼴·**색** 모두 ae_tokens.json 에서 — 말자막(subtitle_layers.jsx)과 같은 값.
        // 색만 [1,1,1] 로 박아 두었던 탓에 가져온 자막은 순백, 말자막은 #E8EAED 로
        // 한 화면에서 미묘하게 어긋났다. 토큰이 없을 때의 폴백도 말자막과 같게 둔다.
        var size = 54, fontName = "", txt = [1, 1, 1];
        try {
            if (tokensPath) {
                var tf = new File(tokensPath);
                if (tf.exists) {
                    tf.open("r"); var raw = tf.read(); tf.close();
                    var tk = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
                    if (tk.type && tk.type.subtitle) { size = tk.type.subtitle; }
                    if (tk.fonts && tk.fonts.subtitle) { fontName = tk.fonts.subtitle; }
                    if (tk.colors && tk.colors.textRgb) {
                        txt = [tk.colors.textRgb[0] / 255, tk.colors.textRgb[1] / 255, tk.colors.textRgb[2] / 255];
                    }
                }
            }
        } catch (eTk) { }

        app.beginUndoGroup("auto_kairos SRT 가져오기");

        // 스타일 기준 — 세모지툴처럼 선택한 텍스트 레이어. 지우기 전에 값을 떠 둔다.
        var tplDoc = null, tplPos = null, tplScale = null, tplAnchor = null, tplName = null;
        try {
            var sel = comp.selectedLayers;
            for (var si = 0; si < sel.length; si++) {
                if (sel[si] instanceof TextLayer) {
                    tplName = sel[si].name;
                    tplDoc = sel[si].property("Source Text").value;
                    tplPos = sel[si].property("Position").value;
                    tplScale = sel[si].property("Scale").value;
                    tplAnchor = sel[si].property("Anchor Point").value;
                    break;
                }
            }
        } catch (eSel) { tplDoc = null; }

        // 예전 결과는 지우고 다시 — 단일 키프레임 레이어와 이전 줄별 레이어 모두
        for (var i = comp.numLayers; i >= 1; i--) {
            var nm = comp.layer(i).name;
            if (nm === AK_SRT_LAYER || akIsSrtLayerName(nm)) { comp.layer(i).remove(); }
        }

        var made = 0, maxEnd = 0;
        for (var q = 0; q < cues.length; q++) {
            var c = cues[q];
            if (!c.text || c.start == null || c.end == null) { continue; }
            var text = String(c.text);
            var tl = comp.layers.addText(text);
            tl.name = AK_SRT_PREFIX + (q + 1) + " " + text;
            var prop = tl.property("Source Text");

            var styled = false;
            if (tplDoc) {
                try { tplDoc.text = text; prop.setValue(tplDoc); styled = true; } catch (eCopy) { }
            }
            if (!styled) {
                var doc = prop.value;
                doc.fontSize = size;
                doc.fillColor = txt;
                try { doc.applyStroke = true; doc.strokeColor = [0, 0, 0]; doc.strokeWidth = Math.max(4, size / 12); doc.strokeOverFill = false; } catch (e2) { }
                try { if (fontName) { doc.font = fontName; } } catch (e3) { }
                try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e4) { }
                prop.setValue(doc);
            }
            if (styled && tplPos) {
                try {
                    tl.property("Anchor Point").setValue(tplAnchor);
                    tl.property("Position").setValue(tplPos);
                    tl.property("Scale").setValue([tplScale[0], tplScale[1]]);
                } catch (ePos) { }
            } else {
                tl.property("Anchor Point").setValue([0, 0]);
                tl.property("Position").setValue([comp.width / 2, comp.height * 0.86]);   // 말자막(0.92)보다 한 줄 위
            }

            // 다음 큐가 바로 이어지면(틈 0.02s 이하) outPoint를 다음 시작에 붙인다
            tl.inPoint = c.start;
            var nextStart = (q + 1 < cues.length) ? cues[q + 1].start : null;
            var outT = (nextStart !== null && nextStart <= c.end + 0.02) ? nextStart : c.end;
            if (outT <= c.start) { outT = c.start + comp.frameDuration; }
            tl.outPoint = outT;
            tl.shy = true;
            made++;
            if (c.end > maxEnd) { maxEnd = c.end; }
        }
        if (maxEnd > comp.duration) { comp.duration = maxEnd; }
        try { comp.hideShyLayers = true; } catch (eShy) { }
        app.endUndoGroup();
        return "OK: 자막 " + made + "줄 → 레이어 " + made + "개"
            + (tplName ? " / 스타일 기준: " + tplName : " / 스타일: ae_tokens");
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
                } else if (type === "bob") {
                    // 까딱까딱 — **발밑을 축으로 세로만 눌렀다 편다.**
                    // 조립할 때 인물 레이어에 자동으로 붙는 것과 같은 방식이다.
                    // 위치를 흔드는 wiggle·shake 와는 다르다 — 발이 땅에 붙어 있다.
                    var bAmt = amt || 1;              // 100 → 101
                    var rc = il.sourceRectAtTime(t0, false);
                    // 발밑(불투명 영역 하단 중앙)을 컴프 좌표로 — 앵커 기준 오프셋을 더한다
                    var ap = il.property("Anchor Point").value;
                    var sc = il.property("Scale").value;
                    var footX = P[0] + (rc.left + rc.width / 2 - ap[0]) * sc[0] / 100;
                    var footY = P[1] + (rc.top + rc.height - ap[1]) * sc[1] / 100;
                    var prevP = il.parent;
                    il.parent = null;
                    var nb = comp.layers.addNull();
                    nb.name = il.name + "_피벗";
                    nb.property("Position").setValue([footX, footY]);
                    nb.inPoint = il.inPoint; nb.outPoint = il.outPoint;
                    il.parent = nb;                        // AE 가 월드 변환을 보존하며 붙인다
                    if (prevP) { nb.parent = prevP; }
                    nb.moveAfter(il);
                    var bs = nb.property("Scale");
                    // 반주기 10프레임 — 초로 적으면 fps 가 바뀔 때 어긋난다.
                    // 조립할 때 붙는 것과 같은 값이어야 한다(motion.py 가 정본).
                    // 여기는 손으로 거는 프리셋이라 매니페스트가 없다 — 같은 수를 적는다.
                    var half = 10 * comp.frameDuration;
                    bs.setValueAtTime(t0, [100, 100]);
                    bs.setValueAtTime(Math.min(il.outPoint, t0 + half), [100, 100 + bAmt]);
                    try {
                        var ezb = new KeyframeEase(0, 33.34);
                        bs.setTemporalEaseAtKey(1, [ezb, ezb], [ezb, ezb]);
                        bs.setTemporalEaseAtKey(2, [ezb, ezb], [ezb, ezb]);
                    } catch (eB) { }
                    try { bs.expression = 'loopOut("pingpong")'; } catch (eE) { }
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
