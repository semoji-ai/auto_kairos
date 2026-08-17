// auto_kairos — Final 컴프의 말자막. 줄마다 레이어를 만들지 않고
// **텍스트 레이어 1개**의 Source Text에 키프레임을 찍는다(줄 수가 수백이어도 레이어는 1개).
// 입력: subsPath(subtitles.json 절대경로), tokensPath(ae_tokens.json, ""면 기본).
// 부분 빌드(체크한 씬만)면 그 시간 구간의 키프레임만 갈아끼운다.
// 반환: "OK: ..." | "ERROR: ..."

var AK_SUB_LAYER = "말자막";

function akSubReadJson(path) {
    var f = new File(path);
    if (!f.exists) { return null; }
    f.open("r"); var raw = f.read(); f.close();
    return (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
}

// 예전 방식으로 만들어진 줄별 레이어(sub_1, sub_2 …)를 정리 — AE가 무거워지는 주범
function akRemoveLegacySubLayers(comp) {
    var removed = 0;
    for (var i = comp.numLayers; i >= 1; i--) {
        var nm = comp.layer(i).name;
        if (nm.length > 4 && nm.substring(0, 4) === "sub_") {
            var tail = nm.substring(4), digits = true;
            for (var c = 0; c < tail.length; c++) {
                if (tail.charAt(c) < "0" || tail.charAt(c) > "9") { digits = false; break; }
            }
            if (digits) { comp.layer(i).remove(); removed++; }
        }
    }
    return removed;
}

function akFindLayer(comp, name) {
    for (var i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === name) { return comp.layer(i); }
    }
    return null;
}

function akBuildSubtitles(subsPath, tokensPath) {
    try {
        var data = akSubReadJson(subsPath);
        if (!data) { return "ERROR: subtitles.json 없음"; }
        var cues = data.cues || [];
        if (!cues.length) { return "ERROR: 자막 줄 없음"; }

        var size = 54, fontName = "", txt = [1, 1, 1];
        try {
            if (tokensPath) {
                var tk = akSubReadJson(tokensPath);
                if (tk) {
                    if (tk.type && tk.type.subtitle) { size = tk.type.subtitle; }
                    if (tk.fonts && tk.fonts.subtitle) { fontName = tk.fonts.subtitle; }
                    if (tk.colors && tk.colors.textRgb) {
                        txt = [tk.colors.textRgb[0] / 255, tk.colors.textRgb[1] / 255, tk.colors.textRgb[2] / 255];
                    }
                }
            }
        } catch (e) { }

        var comp = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === "Final") { comp = it; break; }
        }
        if (!comp) { return "ERROR: Final 컴프 없음 — 먼저 컴프를 빌드하세요"; }

        app.beginUndoGroup("auto_kairos subtitles");
        var W = comp.width, H = comp.height;
        var legacy = akRemoveLegacySubLayers(comp);

        var tl = akFindLayer(comp, AK_SUB_LAYER);
        var fresh = false;
        if (!tl) {
            tl = comp.layers.addText("");
            tl.name = AK_SUB_LAYER;
            fresh = true;
        }
        var prop = tl.property("Source Text");

        // 스타일 — 가운데 정렬이면 글자 수가 바뀌어도 앵커 보정 없이 수평 중앙이 유지된다
        var doc = prop.value;
        doc.fontSize = size;
        doc.fillColor = txt;
        try { doc.applyStroke = true; doc.strokeColor = [0, 0, 0]; doc.strokeWidth = Math.max(4, size / 12); doc.strokeOverFill = false; } catch (e2) { }
        try { if (fontName) { doc.font = fontName; } } catch (e3) { }
        try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (e4) { }
        if (fresh) {
            tl.property("Anchor Point").setValue([0, 0]);   // 점 텍스트 기준점(베이스라인)
            tl.property("Position").setValue([W / 2, H * 0.92]);
        }

        // 이번에 쓰는 시간 구간 — 부분 빌드면 이 범위의 키프레임만 교체
        var t0 = cues[0].start, t1 = cues[0].end;
        for (var q = 0; q < cues.length; q++) {
            if (cues[q].start < t0) { t0 = cues[q].start; }
            if (cues[q].end > t1) { t1 = cues[q].end; }
        }
        for (var k = prop.numKeys; k >= 1; k--) {
            var kt = prop.keyTime(k);
            if (kt >= t0 - 0.001 && kt <= t1 + 0.001) { prop.removeKey(k); }
        }

        var made = 0;
        for (var ci = 0; ci < cues.length; ci++) {
            var c = cues[ci];
            if (!c.text || c.end == null || c.start == null) { continue; }
            doc.text = String(c.text);
            prop.setValueAtTime(c.start, doc);
            made++;
            // 다음 줄까지 틈이 있으면 빈 문자열 키로 지운다(마지막 줄도 동일)
            var nextStart = (ci + 1 < cues.length) ? cues[ci + 1].start : null;
            if (nextStart === null || nextStart > c.end + 0.02) {
                doc.text = "";
                prop.setValueAtTime(c.end, doc);
            }
        }
        // 레이어는 컴프 전체 구간 — 빈 문자열 구간은 아무것도 그리지 않는다
        tl.startTime = 0;
        tl.inPoint = 0;
        tl.outPoint = comp.duration;

        app.endUndoGroup();
        return "OK: 자막 " + made + "줄 → 레이어 1개(" + AK_SUB_LAYER + ")"
            + (legacy ? " / 예전 줄별 레이어 " + legacy + "개 정리" : "");
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}
