// 타이레놀 컷3 재현 — AI 검색창 UI ("타이레놀을 다들 쉽게 알아보면 좋겠어").
// gemini 정밀 분석 기반: 흰 그리드 배경 + 둥근 검색창(좌→우 슬라이드인) + 하단 아이콘 + 타이핑 텍스트.
// 실행: AE > File > Scripts > Run Script File... → 이 파일.

function akTylenolSearch() {
    try {
        var W = 1920, H = 1080, FPS = 30, DUR = 2.2;
        var GRID_BG = [247 / 255, 247 / 255, 247 / 255];     // #F7F7F7
        var RED = [228 / 255, 0, 43 / 255];                  // #E4002B
        var INK = [51 / 255, 51 / 255, 51 / 255];            // #333333
        var GRAY = [0.78, 0.78, 0.80];
        var proj = app.project || app.newProject();
        app.beginUndoGroup("TYL Cut03 Search");
        var comp = proj.items.addComp("TYL_03_Search", W, H, 1.0, DUR, FPS);
        comp.motionBlur = true;

        function rrect(name, x, y, w, h, round, fill, stroke, sw) {
            var sl = comp.layers.addShape(); sl.name = name;
            var g = sl.property("Contents").addProperty("ADBE Vector Group");
            var rc = g.property("Contents").addProperty("ADBE Vector Shape - Rect");
            rc.property("Size").setValue([w, h]);
            rc.property("Roundness").setValue(round);
            if (fill) { var f = g.property("Contents").addProperty("ADBE Vector Graphic - Fill"); f.property("Color").setValue(fill); }
            if (stroke) { var s = g.property("Contents").addProperty("ADBE Vector Graphic - Stroke"); s.property("Color").setValue(stroke); s.property("Stroke Width").setValue(sw || 2); }
            sl.property("Position").setValue([x + w / 2, y + h / 2]);
            return sl;
        }
        function txt(str, x, y, size, rgb, fonts, just) {
            var tl = comp.layers.addText(String(str));
            var td = tl.property("Source Text").value;
            td.fontSize = size; td.fillColor = rgb;
            td.justification = just || ParagraphJustification.LEFT_JUSTIFY;
            var ff = fonts || ["AppleSDGothicNeo-Bold"];
            for (var i = 0; i < ff.length; i++) { try { td.font = ff[i]; } catch (e) {} }
            tl.property("Source Text").setValue(td);
            var r = tl.sourceRectAtTime(0, false);
            var ax = just === ParagraphJustification.CENTER_JUSTIFY ? r.left + r.width / 2 : r.left;
            tl.property("Anchor Point").setValue([ax, r.top + r.height / 2]);
            tl.property("Position").setValue([x, y]);
            return tl;
        }

        // (1) 흰 그리드 배경
        comp.layers.addSolid(GRID_BG, "bg", W, H, 1.0);
        var gridGroup = comp.layers.addShape(); gridGroup.name = "grid";
        var gc = gridGroup.property("Contents");
        for (var gx = 0; gx <= W; gx += 80) {
            var ln = gc.addProperty("ADBE Vector Group");
            var p = ln.property("Contents").addProperty("ADBE Vector Shape - Group");
            var sh = new Shape(); sh.vertices = [[gx, 0], [gx, H]]; sh.closed = false; p.property("Path").setValue(sh);
        }
        for (var gy = 0; gy <= H; gy += 80) {
            var ln2 = gc.addProperty("ADBE Vector Group");
            var p2 = ln2.property("Contents").addProperty("ADBE Vector Shape - Group");
            var sh2 = new Shape(); sh2.vertices = [[0, gy], [W, gy]]; sh2.closed = false; p2.property("Path").setValue(sh2);
        }
        var gst = gc.addProperty("ADBE Vector Graphic - Stroke");
        gst.property("Color").setValue([0.90, 0.90, 0.92]); gst.property("Stroke Width").setValue(1);
        gridGroup.property("Opacity").setValue(60);

        // (2) 검색창(둥근 사각형) + 하단 아이콘 — 좌→우 슬라이드인(0~0.3s)
        var barW = W * 0.62, barH = 220, barX = W / 2 - barW / 2, barY = H / 2 - barH / 2;
        var slideGrp = [];
        var bar = rrect("searchbar", barX, barY, barW, barH, 28, [1, 1, 1], GRAY, 2);
        slideGrp.push(bar);
        // 하단 아이콘 3개(+/클립/문서) — 작은 원/사각 근사
        for (var ic = 0; ic < 3; ic++) {
            var icx = barX + 40 + ic * 60;
            slideGrp.push(rrect("ic" + ic, icx, barY + barH - 56, 36, 36, 8, [0.85, 0.85, 0.87], null, 0));
        }
        // 우측 화살표 버튼(원형 근사)
        slideGrp.push(rrect("send", barX + barW - 76, barY + barH - 60, 44, 44, 22, RED, null, 0));
        // 슬라이드인 키프레임(공통)
        for (var si = 0; si < slideGrp.length; si++) {
            var L = slideGrp[si], pos = L.property("Position").value;
            var pp = L.property("Position");
            pp.setValueAtTime(0, [pos[0] - W * 0.5, pos[1]]);
            pp.setValueAtTime(0.3, [pos[0], pos[1]]);
            try { pp.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80)], [new KeyframeEase(0, 80)]); } catch (e) {}
            L.motionBlur = true;
        }

        // (3) 타이핑 텍스트 — "타이레놀"(빨강) + "을 다들 쉽게 알아보면 좋겠어."(검정)
        //  검색창 내부 좌측 정렬. 0.3s부터 타이핑(글자 순차).
        var tx0 = barX + 56, ty = H / 2 - 16;
        var t1 = txt("타이레놀", tx0, ty, 58, RED, ["OTSBAggroB", "AppleSDGothicNeo-Bold"]);
        var w1 = t1.sourceRectAtTime(0, false).width;
        var t2 = txt("을 다들 쉽게 알아보면 좋겠어.", tx0 + w1 + 6, ty, 58, INK, ["OTSBAggroM", "AppleSDGothicNeo-Bold"]);
        function typeAnim(tl, t0, dur) {
            try {
                var an = tl.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
                var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
                try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
                var off = sel.property("ADBE Text Percent Offset");
                off.setValueAtTime(t0, 0); off.setValueAtTime(t0 + dur, 100);
            } catch (e) {}
        }
        typeAnim(t1, 0.35, 0.4);          // "타이레놀" 먼저
        typeAnim(t2, 0.75, 1.3);          // 나머지 이어서

        // (4) Drop Shadow — 검색창/아이콘/버튼에 부드러운 그림자(UI 입체감)
        function dropShadow(layer, opacity, dist, soft) {
            try {
                var ds = layer.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
                ds.property("ADBE Drop Shadow-0001").setValue([0, 0, 0]);       // 색
                ds.property("ADBE Drop Shadow-0002").setValue(opacity);          // 불투명도(0~255)
                ds.property("ADBE Drop Shadow-0003").setValue(135);              // 방향
                ds.property("ADBE Drop Shadow-0004").setValue(dist);             // 거리
                ds.property("ADBE Drop Shadow-0005").setValue(soft);             // 부드러움
            } catch (e) {}
        }
        dropShadow(bar, 38, 16, 50);                                            // 검색창 — 넓고 부드러운 그림자
        for (var di = 0; di < slideGrp.length; di++) {
            if (slideGrp[di] !== bar) dropShadow(slideGrp[di], 28, 6, 16);
        }

        // (5) 그레인 — 조정 레이어 전체에 필름 질감(약하게)
        var grain = comp.layers.addSolid([1, 1, 1], "grain", W, H, 1.0);
        grain.adjustmentLayer = true;
        try {
            var ag = grain.property("ADBE Effect Parade").addProperty("ADBE Add Grain");
            ag.property("ADBE AddGrain-0002").setValue(0.4);                     // Intensity(약하게)
            ag.property("ADBE AddGrain-0003").setValue(0.6);                     // Size
        } catch (eg) {
            try {                                                               // Add Grain 없으면 Noise 폴백
                var nz = grain.property("ADBE Effect Parade").addProperty("ADBE Noise2");
                nz.property("ADBE Noise2-0001").setValue(6);                     // Amount
                grain.property("Opacity").setValue(40);
            } catch (eN) {}
        }

        comp.openInViewer();
        app.endUndoGroup();
        return "OK: TYL_03_Search (검색창 UI 재현)";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) {}
        return "ERROR: " + e.toString();
    }
}
akTylenolSearch();
