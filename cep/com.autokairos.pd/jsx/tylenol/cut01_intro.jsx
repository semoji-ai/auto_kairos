// 타이레놀 페이스리프트 70초 — 컷01 인트로(0~2.5s) 1:1 재현.
// 영상 분석: 0~1.8s 빨강 배경+흰 TYLENOL 로고 → 1.8s 흰배경 와이프 전환 → 1.9s "타이레놀을" 타이핑.
// AE 네이티브: 솔리드 + 스케일 팝 + 모션블러 + Linear Wipe 전환 + Text Animator(타이핑).
// 실행: AE > File > Scripts > Run Script File... 로 이 파일 선택(끝에서 자동 호출).

function akTylenolCut01() {
    try {
        var W = 1920, H = 1080, FPS = 30, DUR = 2.6;
        var RED = [207 / 255, 0, 43 / 255];        // 타이레놀 레드 #CF002B(프레임 추출)
        var WHITE = [0.95, 0.95, 0.96];
        var proj = app.project || app.newProject();
        app.beginUndoGroup("TYL Cut01 Intro");
        var comp = proj.items.addComp("TYL_01_Intro", W, H, 1.0, DUR, FPS);
        comp.motionBlur = true;

        // (1) 빨강 배경
        comp.layers.addSolid(RED, "bg_red", W, H, 1.0);

        // (2) TYLENOL 워드마크(흰, 이탤릭 세리프 근사) — 스케일 팝 + 페이드 등장
        var logo = comp.layers.addText("TYLENOL");
        var td = logo.property("Source Text").value;
        td.fontSize = 200; td.fillColor = [1, 1, 1]; td.tracking = 30;
        td.justification = ParagraphJustification.CENTER_JUSTIFY;
        var lf = ["Georgia-BoldItalic", "Georgia Bold Italic", "TimesNewRomanPS-BoldItalicMT"];
        for (var i = 0; i < lf.length; i++) { try { td.font = lf[i]; } catch (e) {} }
        logo.property("Source Text").setValue(td);
        var r = logo.sourceRectAtTime(0, false);
        logo.property("Anchor Point").setValue([r.left + r.width / 2, r.top + r.height / 2]);
        logo.property("Position").setValue([W / 2, H / 2]);
        var sc = logo.property("Scale");
        sc.setValueAtTime(0, [88, 88]); sc.setValueAtTime(0.3, [104, 104]); sc.setValueAtTime(0.45, [100, 100]);
        try { sc.setTemporalEaseAtKey(3, [new KeyframeEase(0, 70)], [new KeyframeEase(0, 70)]); } catch (e) {}
        var op = logo.property("Opacity"); op.setValueAtTime(0, 0); op.setValueAtTime(0.18, 100);
        logo.motionBlur = true;
        logo.outPoint = 1.95;

        // (3) 흰 배경 와이프 전환(1.8s, 좌→우) — 빨강 위를 덮음
        var white = comp.layers.addSolid(WHITE, "bg_white", W, H, 1.0);
        var lw = white.property("ADBE Effect Parade").addProperty("ADBE Linear Wipe");
        var trans = lw.property("ADBE Linear Wipe-0001");     // Transition Completion(100=완전투명)
        trans.setValueAtTime(1.78, 100); trans.setValueAtTime(1.92, 0);
        lw.property("ADBE Linear Wipe-0002").setValue(90);     // Wipe Angle = 90°(좌→우)
        try { lw.property("ADBE Linear Wipe-0003").setValue(40); } catch (e) {}   // Feather

        // (4) "타이레놀을" 타이핑(1.9~2.35s, 글자 순차)
        var t2 = comp.layers.addText("타이레놀을");
        var td2 = t2.property("Source Text").value;
        td2.fontSize = 150; td2.fillColor = RED;
        var hf = ["Cafe24Ssurround", "OTSBAggroB", "AppleSDGothicNeo-Bold"];
        for (var j = 0; j < hf.length; j++) { try { td2.font = hf[j]; } catch (e) {} }
        td2.justification = ParagraphJustification.CENTER_JUSTIFY;
        t2.property("Source Text").setValue(td2);
        var r2 = t2.sourceRectAtTime(0, false);
        t2.property("Anchor Point").setValue([r2.left + r2.width / 2, r2.top + r2.height / 2]);
        t2.property("Position").setValue([W / 2, H / 2]);
        // 타이핑 Text Animator — Opacity 0 + Range Selector Offset 0→100(글자 순차 등장), 폭 0(딱딱한 글자단위)
        var an = t2.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
        an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
        var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
        try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
        var offp = sel.property("ADBE Text Percent Offset");
        offp.setValueAtTime(1.9, 0); offp.setValueAtTime(2.35, 100);

        comp.openInViewer();
        app.endUndoGroup();
        return "OK: TYL_01_Intro 생성(2.6s)";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) {}
        return "ERROR: " + e.toString();
    }
}
akTylenolCut01();
