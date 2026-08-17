// auto_kairos — Final 컴프를 렌더 큐에 추가(+선택 시 즉시 렌더).
// 입력: compName(보통 "Final"), outPath(절대경로, 확장자 포함), omTemplate(출력 모듈 템플릿명, ""면 기본),
//       startNow("1"이면 즉시 render() — AE UI가 렌더 동안 블로킹됨).
// 반환: "OK: ..." | "ERROR: ..."

function akQueueRender(compName, outPath, omTemplate, startNow) {
    try {
        var comp = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === compName) { comp = it; break; }
        }
        if (!comp) { return "ERROR: 컴프 없음: " + compName; }

        var rqi = app.project.renderQueue.items.add(comp);
        var om = rqi.outputModule(1);
        if (omTemplate) {
            try { om.applyTemplate(omTemplate); }
            catch (e) { /* 템플릿 없으면 기본 유지 */ }
        }
        om.file = new File(outPath);

        if (startNow === "1") {
            app.project.renderQueue.render();   // 블로킹 — 완료까지 AE 멈춤
            return "OK: 렌더 완료 → " + outPath;
        }
        return "OK: 렌더 큐 추가됨(" + compName + " → " + outPath + ") — AE 렌더 큐에서 [Render] 실행";
    } catch (e) {
        try { return "ERROR: " + e.toString(); } catch (_) { return "ERROR"; }
    }
}
