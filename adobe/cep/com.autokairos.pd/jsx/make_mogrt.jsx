// auto_kairos — 레이아웃을 필수 그래픽 템플릿(.mogrt)으로 찍어낸다.
//
// **디자인 소스를 둘로 만들지 않기 위한 스크립트다.**
//
// 프리미어에서 편집자가 글자를 고치려면 MOGRT 여야 한다. 그런데 MOGRT 를 손으로
// 만들면 같은 디자인이 두 벌이 된다 — `layouts.jsx` 한 벌, MOGRT 한 벌. 하나를
// 고치면 다른 쪽이 갈린다. 그래서 **여기서도 `akRenderLayout` 을 부른다.**
// 디자인은 계속 `layouts.jsx` 하나가 정하고, 이 파일은 그것을 굽기만 한다.
//
// 노출하는 것 — 글자마다 넷:
//
//   글자   Source Text        문구 (프리미어에서 폰트·크기도 함께 준다)
//   자리   Transform Position 위치
//   크기   Transform Scale    크기
//   색     Fill 이펙트 Color  색
//
// 색을 왜 이펙트로 주나 — 텍스트 색은 `Source Text` 안의 TextDocument 에 들어
// 있어 따로 노출할 수 없다. Fill 이펙트를 얹으면 색이 **독립된 속성**이 되어
// 프리미어에 색상 고르개로 뜬다. 도형은 Fill 색을 그대로 노출한다.

function akMakeMogrt(outDir, only) {
    var log = [];
    var made = [];
    try {
        if (typeof akRenderLayout !== "function") { return "ERROR: layouts.jsx 가 없습니다"; }
        // **폴더를 여기서 만들지 않는다.** `Folder.create()` 는 애프터이펙트의
        // 「스크립트가 파일을 쓰고 네트워크에 접근하도록 허용」 설정에 걸려
        // permission denied 로 죽는다. 백엔드가 미리 만들어 둔다.
        var d = new Folder(outDir);
        if (!d.exists) { return "ERROR: 폴더가 없습니다(백엔드가 만들어야 합니다) " + outDir; }

        var W = 1920, H = 1080, FPS = 30, DUR = 5;
        var want = only && only.length ? only : akMogrtLayouts();

        // **정리 폴더를 쓰지 않는다.**
        //
        // 처음에는 임시 폴더에 컴프를 모았는데, 컴프를 하나 지우고 나면 그
        // 폴더 참조가 무효가 되어 두 번째부터 「FolderItem is not of the
        // correct type」 으로 죽었다(11종 중 1종만 나왔다). 항목을 지우면
        // 색인이 밀리기 때문이다.
        //
        // 어차피 컴프는 찍자마자 지운다. 폴더는 정리하려고 둔 것이었으니 뺀다.
        app.beginUndoGroup("auto_kairos MOGRT 찍기");
        for (var i = 0; i < want.length; i++) {
            var key = want[i];
            if (akOneMogrt(key, d, W, H, FPS, DUR, log)) { made.push(key); }
        }
        app.endUndoGroup();

        return "OK: MOGRT " + made.length + "개 → " + outDir
             + " (" + made.join(", ") + ")"
             + (log.length ? (" | " + log.join(", ")) : "");
    } catch (e) {
        try { app.endUndoGroup(); } catch (eU) { }
        return "ERROR: " + e.toString() + (log.length ? (" | " + log.join(", ")) : "");
    }
}

/* 찍을 레이아웃. 등록표에 있는 것 중 글자가 있는 것만 — `generic` 은 폴백이라
   뺀다. 이 편에서 실제로 쓰는 것은 앞의 셋이다(headline_only 19 · items_list 12
   · metric_spotlight 5씬). */
function akMogrtLayouts() {
    return ["headline_only", "items_list", "metric_spotlight", "quote",
            "flow", "timeline", "split", "metric_wall", "before_after",
            "counter", "bar"];
}

/* 레이아웃 하나 → 컴프 → 속성 노출 → .mogrt → 컴프 삭제 */
function akOneMogrt(key, outFolder, W, H, FPS, DUR, log) {
    var comp = null;
    try {
        comp = app.project.items.addComp("ak_" + key, W, H, 1, DUR, FPS);

        // **본문은 layouts.jsx 가 그린다.** 여기서 그리면 그 순간 두 벌이 된다.
        akRenderLayout(comp, akSampleScene(key), akMogrtCtx(comp, W, H));

        var n = 0;
        for (var li = 1; li <= comp.numLayers; li++) {
            n += akExposeLayer(comp, comp.layer(li), li, log);
        }
        if (!n) { log.push(key + ": 노출할 속성이 없습니다"); }

        // **이름은 컴프가 정하고, 인자로는 폴더를 준다.**
        //
        // 파일 경로를 주었더니 애프터이펙트가 그 이름으로 **폴더를 만들었다**
        // (`headline_only.mogrt/` 가 빈 디렉터리로 생겼다). 내보내기는 목적지
        // 폴더를 받고 파일 이름은 `motionGraphicsTemplateName` 에서 가져간다.
        comp.motionGraphicsTemplateName = key;
        var ok = comp.exportAsMotionGraphicsTemplate(true, outFolder.fsName);
        if (!ok) {
            log.push(key + ": 내보내기 실패 — 설정 > 스크립팅 및 표현식 >"
                     + " 「스크립트가 파일을 쓰고 네트워크에 접근하도록 허용」 을 켜 보세요");
            return false;
        }
        return true;
    } catch (e) {
        log.push(key + ": " + e.toString());
        return false;
    } finally {
        // 컴프는 지운다 — 폴더째 지우면 되지만 실패했을 때를 위해 여기서도
        try { if (comp) { comp.remove(); } } catch (eR) { }
    }
}

/* 레이어 하나에서 고칠 수 있어야 하는 것을 노출한다. 반환 = 노출한 개수. */
function akExposeLayer(comp, lay, idx, log) {
    var n = 0;
    var nm = String(lay.name || ("레이어" + idx));

    // ── 글자 ────────────────────────────────────────────────────────
    if (lay instanceof TextLayer) {
        n += akAdd(comp, lay.property("Source Text"), nm + " 글자", log);
        // 색은 Fill 이펙트로 — TextDocument 안의 색은 따로 노출할 수 없다
        try {
            var fx = lay.property("ADBE Effect Parade").addProperty("ADBE Fill");
            var col = null;
            for (var p = 1; p <= fx.numProperties; p++) {
                if (fx.property(p).name === "Color" || fx.property(p).matchName === "ADBE Fill-0002") {
                    col = fx.property(p); break;
                }
            }
            if (col) { n += akAdd(comp, col, nm + " 색", log); }
        } catch (eF) { log.push(nm + " 색 노출 실패"); }
    } else {
        // ── 도형 ────────────────────────────────────────────────────
        // 도형은 Fill 색이 이미 독립된 속성이라 그대로 노출한다
        try {
            var g = lay.property("Contents").property(1).property("Contents");
            for (var q = 1; q <= g.numProperties; q++) {
                var pr = g.property(q);
                if (pr.matchName === "ADBE Vector Graphic - Fill") {
                    n += akAdd(comp, pr.property("Color"), nm + " 색", log);
                }
                if (pr.matchName === "ADBE Vector Graphic - Stroke") {
                    n += akAdd(comp, pr.property("Color"), nm + " 선색", log);
                }
            }
        } catch (eS) { }
    }

    // ── 자리·크기 — 글자든 도형이든 같다 ────────────────────────────
    n += akAdd(comp, lay.property("Position"), nm + " 자리", log);
    n += akAdd(comp, lay.property("Scale"), nm + " 크기", log);
    return n;
}

function akAdd(comp, prop, label, log) {
    try {
        if (!prop) { return 0; }
        if (!prop.canAddToMotionGraphicsTemplate(comp)) { return 0; }
        return prop.addToMotionGraphicsTemplateAs(comp, label) ? 1 : 0;
    } catch (e) {
        log.push(label + " 노출 실패");
        return 0;
    }
}

/* 그릴 때 쓸 표본 값. **자리를 잡으려고 넣는 것**이지 내용이 아니다 —
   프리미어에서 씬마다 값이 채워진다. 항목은 넉넉히 둔다: MOGRT 는 레이어 수가
   고정이라, 씬에 항목이 더 많으면 들어갈 자리가 없다. 남는 슬롯은 프리미어에서
   글자를 비우면 사라진다. */
function akSampleScene(key) {
    var items = ["항목 하나", "항목 둘", "항목 셋", "항목 넷", "항목 다섯", "항목 여섯"];
    return {
        layout: key,
        title: "제목을 여기에",
        headline: "제목을 여기에",
        descriptions: ["설명을 여기에"],
        items: items,
        values: [40, 65, 30, 80, 55, 20],   // **숫자여야 한다** — bar 가 이걸로 높이를 잰다
        unit: "단위",
        quote: "인용을 여기에",
        source: "출처",
        before: "이전", after: "이후",
        value: "1", label: "라벨"
    };
}

/* layouts.jsx 가 기대하는 ctx — build_scene.jsx 의 것과 같은 모양이다.
   헬퍼가 없으면 레이아웃이 그리다 만다. */
function akMogrtCtx(comp, W, H) {
    var TKc = (typeof TK !== "undefined" && TK) ? TK : null;
    var colors = TKc ? TKc.colors : {
        bgRgb: [18, 18, 20], textRgb: [235, 235, 240], mutedRgb: [150, 155, 165],
        accentRgb: [58, 109, 240], accentSoftRgb: [40, 60, 120]
    };
    // **키가 하나라도 없으면 NaN 이 된다.** `t.quote * S` 가 NaN 이 되어
    // addBoxText 가 죽었다(quote 레이아웃). build_scene 의 TK.type 와 같은
    // 키를 다 갖춘다.
    var type = TKc ? TKc.type : {
        headline: 110, sub: 48, item: 52, metric: 220, metricLabel: 54,
        quote: 64, quoteWho: 40, barLabel: 36, barValue: 40
    };
    var fonts = TKc ? TKc.fonts : { headline: "", body: "", value: "", fallback: "" };
    return {
        W: W, H: H, S: W / 1920, colors: colors, type: type, fonts: fonts,
        addTextL: akMogrtText, addRectL: akMogrtRect,
        // **서명이 다르다** — (comp, name, w, h, rgb, CS, S). addRectL 로
        // 대신 쓰면 인자가 밀려 Size 에 배열이 들어간다(bar 가 그랬다).
        addBarShape: akMogrtBar, applyDash: function () { }
    };
}

function akMogrtText(comp, str, opts) {
    var tl = opts.box
        ? comp.layers.addBoxText([opts.box[0], opts.box[1]], String(str))
        : comp.layers.addText(String(str));
    try {
        var td = tl.property("Source Text").value;
        td.fontSize = opts.size;
        td.fillColor = [opts.rgb[0] / 255, opts.rgb[1] / 255, opts.rgb[2] / 255];
        if (opts.font) { td.font = opts.font; }
        td.justification = ParagraphJustification.CENTER_JUSTIFY;
        tl.property("Source Text").setValue(td);
    } catch (e) { }
    tl.property("Position").setValue([opts.x, opts.y]);
    tl.name = String(str).substr(0, 18) || "글자";
    return tl;
}

/* 막대 — 무늬 없이 단색으로. MOGRT 는 색을 고를 수 있으면 되고, 해칭까지
   옮기면 컨트롤만 늘어난다. 앵커를 밑변에 두어 자라나는 느낌을 남긴다. */
function akMogrtBar(comp, name, w, h, rgb, CS, S) {
    var sl = comp.layers.addShape(); sl.name = name || "막대";
    var grp = sl.property("Contents").addProperty("ADBE Vector Group");
    var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
    rect.property("Size").setValue([w, h]);
    var fill = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
    fill.property("Color").setValue([rgb[0], rgb[1], rgb[2]]);
    return sl;
}

function akMogrtRect(comp, name, x, y, w, h, rgb) {
    var sl = comp.layers.addShape(); sl.name = name || "도형";
    var grp = sl.property("Contents").addProperty("ADBE Vector Group");
    var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
    rect.property("Size").setValue([w, h]);
    var fill = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
    fill.property("Color").setValue([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255]);
    sl.property("Position").setValue([x + w / 2, y + h / 2]);
    return sl;
}
