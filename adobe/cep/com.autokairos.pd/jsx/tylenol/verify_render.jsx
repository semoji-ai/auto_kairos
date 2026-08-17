// verify_render.jsx — 헤드리스 빌드+렌더. 실행: "After Effects" -r verify_render.jsx
// env: AK_VERIFY_MOTION(motion.json 절대경로), AK_VERIFY_OUT(.mov 절대경로), AK_VERIFY_AEP(.aep 절대경로)
// build_from_json.jsx 가 AK_VERIFY_MOTION 을 읽어 TYL_Final 컴프를 만든다. 여기선 그 컴프를 렌더.
// 전제: AE 환경설정 "Allow Scripts to Write Files and Access Network" ON
//       (Pref_SCRIPTING_FILE_NETWORK_SECURITY=1) — OFF면 save/render-to-file이 보안 다이얼로그로 막힘.
(function () {
    function findComp(name) {
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof CompItem && it.name === name) return it;
        }
        return null;
    }
    app.beginSuppressDialogs();   // 폰트/에셋 누락 등 비보안 경고 모달 억제(헤드리스 블로킹 방지)
    try {
        var here = new File($.fileName).parent;
        $.evalFile(new File(here.fsName + "/build_from_json.jsx"));  // 자동 실행 → TYL_Final 생성
        var comp = findComp("TYL_Final");
        if (!comp) { $.writeln("ERROR: TYL_Final 컴프 없음"); app.quit(); return; }
        var outPath = $.getenv("AK_VERIFY_OUT");
        var aepPath = $.getenv("AK_VERIFY_AEP");
        if (aepPath && String(aepPath).length) app.project.save(new File(aepPath));
        var rqi = app.project.renderQueue.items.add(comp);
        rqi.outputModule(1).file = new File(outPath);
        app.project.renderQueue.render();
        $.writeln("OK: " + outPath);
    } catch (e) {
        $.writeln("ERROR: " + e.toString());
    }
    app.quit();
})();
