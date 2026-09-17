// auto_kairos — Final 컴프의 말자막. **자막(큐)마다 텍스트 레이어를 하나씩** 만든다.
// SEMOJI TOOL 자막작업 버튼 방식 이식 — 줄마다 addText 후 inPoint/outPoint로 배치,
// 스타일은 기준 텍스트 레이어에서 복사(선택 레이어 → "자막스타일" → 기존 "말자막").
// 기준 레이어가 없으면 ae_tokens.json 값으로 만든다.
// 입력: subsPath(subtitles.json 절대경로), tokensPath(ae_tokens.json, ""면 기본).
// 부분 빌드(체크한 씬만)면 그 시간 구간의 sub_ 레이어만 갈아끼운다.
// 레이어가 수백 장이라 타임라인이 무거워지므로 전부 shy로 접어 둔다.
// 반환: "OK: ..." | "ERROR: ..."

var AK_SUB_LAYER = "말자막";          // 예전 방식(레이어 1개 + Source Text 키프레임)의 레이어
var AK_SUB_PREFIX = "sub_";           // 줄별 레이어 이름: sub_<번호> <자막 텍스트>
var AK_SUB_STYLE_LAYER = "자막스타일";  // 이 이름의 텍스트 레이어가 있으면 스타일 기준으로 쓴다

function akSubReadJson(path) {
    var f = new File(path);
    if (!f.exists) { return null; }
    f.open("r"); var raw = f.read(); f.close();
    return (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
}

// 이 스크립트가 만든 줄별 자막 레이어인가 — "sub_" + 숫자 (+ " 텍스트")
function akIsSubLayerName(nm) {
    if (nm.length <= AK_SUB_PREFIX.length) { return false; }
    if (nm.substring(0, AK_SUB_PREFIX.length) !== AK_SUB_PREFIX) { return false; }
    var i = AK_SUB_PREFIX.length, sawDigit = false;
    while (i < nm.length && nm.charAt(i) >= "0" && nm.charAt(i) <= "9") { i++; sawDigit = true; }
    if (!sawDigit) { return false; }
    return i === nm.length || nm.charAt(i) === " ";
}

// [t0, t1] 구간에서 시작하는 줄별 자막 레이어 제거 — 부분 빌드는 그 구간만 교체
function akRemoveSubLayersInRange(comp, t0, t1) {
    var removed = 0;
    for (var i = comp.numLayers; i >= 1; i--) {
        var ly = comp.layer(i);
        if (!akIsSubLayerName(ly.name)) { continue; }
        if (ly.inPoint >= t0 - 0.001 && ly.inPoint <= t1 + 0.001) { ly.remove(); removed++; }
    }
    return removed;
}

function akFindLayer(comp, name) {
    for (var i = 1; i <= comp.numLayers; i++) {
        if (comp.layer(i).name === name) { return comp.layer(i); }
    }
    return null;
}

// 스타일 기준 텍스트 레이어 — 세모지툴처럼 선택 레이어가 최우선.
// 다음은 "자막스타일" 레이어, 마지막으로 예전 "말자막" 레이어(지우기 전에 값만 뜬다).
function akFindStyleTemplate(comp) {
    try {
        var sel = comp.selectedLayers;
        for (var i = 0; i < sel.length; i++) {
            if (sel[i] instanceof TextLayer) { return sel[i]; }
        }
    } catch (eSel) { }
    var named = akFindLayer(comp, AK_SUB_STYLE_LAYER);
    if (named && named instanceof TextLayer) { return named; }
    var old = akFindLayer(comp, AK_SUB_LAYER);
    if (old && old instanceof TextLayer) { return old; }
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

        // 스타일 기준 값은 레이어를 지우기 전에 떠 둔다(기준이 예전 말자막일 수 있다)
        var tpl = akFindStyleTemplate(comp);
        var tplName = null, tplDoc = null, tplPos = null, tplScale = null, tplAnchor = null;
        if (tpl) {
            try {
                tplName = tpl.name;
                tplDoc = tpl.property("Source Text").value;
                tplPos = tpl.property("Position").value;
                tplScale = tpl.property("Scale").value;
                tplAnchor = tpl.property("Anchor Point").value;
            } catch (eTpl) { tplDoc = null; }
        }

        // 이번에 쓰는 시간 구간 — 부분 빌드면 이 범위의 줄별 레이어만 교체
        var t0 = cues[0].start, t1 = cues[0].end;
        for (var q = 0; q < cues.length; q++) {
            if (cues[q].start < t0) { t0 = cues[q].start; }
            if (cues[q].end > t1) { t1 = cues[q].end; }
        }
        var replaced = akRemoveSubLayersInRange(comp, t0, t1);

        // 예전 단일 키프레임 말자막은 정리 — 남겨 두면 줄별 레이어와 겹쳐 두 번 보인다
        var legacy = 0;
        var oldLayer = akFindLayer(comp, AK_SUB_LAYER);
        if (oldLayer) { oldLayer.remove(); legacy = 1; }

        var made = 0;
        for (var ci = 0; ci < cues.length; ci++) {
            var c = cues[ci];
            if (!c.text || c.end == null || c.start == null) { continue; }
            var text = String(c.text);
            var ly = comp.layers.addText(text);
            ly.name = AK_SUB_PREFIX + (ci + 1) + " " + text;
            var prop = ly.property("Source Text");

            var styled = false;
            if (tplDoc) {
                // 세모지툴처럼 기준 레이어의 문자 스타일을 통째로 — 글꼴·크기·색·획·정렬 전부
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
                    ly.property("Anchor Point").setValue(tplAnchor);
                    ly.property("Position").setValue(tplPos);
                    ly.property("Scale").setValue([tplScale[0], tplScale[1]]);
                } catch (ePos) { }
            } else {
                // 가운데 정렬 점 텍스트 — 줄마다 글자 수가 달라도 수평 중앙이 유지된다
                ly.property("Anchor Point").setValue([0, 0]);
                ly.property("Position").setValue([W / 2, H * 0.92]);
            }

            // 시간 배치 — inPoint는 큐 시작. 다음 큐가 바로 이어지면(틈 0.02s 이하)
            // outPoint를 다음 시작에 붙여 한 프레임 깜빡임을 막는다
            // (세모지툴의 「이전 레이어 outPoint = 현재 inPoint」 연결과 같은 원리).
            ly.inPoint = c.start;
            var nextStart = (ci + 1 < cues.length) ? cues[ci + 1].start : null;
            var outT = (nextStart !== null && nextStart <= c.end + 0.02) ? nextStart : c.end;
            if (outT <= c.start) { outT = c.start + comp.frameDuration; }   // 0길이 큐 가드
            ly.outPoint = outT;
            ly.shy = true;
            made++;
        }
        try { comp.hideShyLayers = true; } catch (eShy) { }

        app.endUndoGroup();
        return "OK: 자막 " + made + "줄 → 레이어 " + made + "개"
            + (replaced ? " / 기존 줄별 레이어 " + replaced + "개 교체" : "")
            + (legacy ? " / 예전 키프레임 말자막 정리" : "")
            + (tplName ? " / 스타일 기준: " + tplName : " / 스타일: ae_tokens");
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) { }
        return "ERROR: " + e.toString();
    }
}
