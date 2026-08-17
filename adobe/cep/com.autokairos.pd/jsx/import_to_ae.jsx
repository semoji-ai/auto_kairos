// auto_kairos — 파일들을 AE 프로젝트로 import (지정 폴더로 정리)
// 입력: pathsJson (절대경로 배열 JSON 문자열), folderName (하위 폴더명)
// 출력: "OK: N개 import -> auto_kairos/<folderName>" 또는 "ERROR: ..."

function akImportToProject(pathsJson, folderName) {
    try {
        var paths = eval("(" + pathsJson + ")");  // 절대경로 배열
        if (!paths || !paths.length) return "ERROR: no paths";
        app.beginUndoGroup("auto_kairos import");
        var parent = "auto_kairos";
        // 최상위 auto_kairos 폴더 확보
        var root = null, sub = null;
        for (var i = 1; i <= app.project.numItems; i++) {
            var it = app.project.item(i);
            if (it instanceof FolderItem && it.name === parent) { root = it; break; }
        }
        if (!root) root = app.project.items.addFolder(parent);
        // 하위 섹션 폴더 확보
        for (var k = 1; k <= app.project.numItems; k++) {
            var it2 = app.project.item(k);
            if (it2 instanceof FolderItem && it2.name === folderName && it2.parentFolder === root) { sub = it2; break; }
        }
        if (!sub) { sub = app.project.items.addFolder(folderName); sub.parentFolder = root; }
        var n = 0;
        for (var j = 0; j < paths.length; j++) {
            var f = new File(paths[j]);
            if (f.exists) {
                var io = new ImportOptions(f);
                var item = app.project.importFile(io);
                item.parentFolder = sub;
                n++;
            }
        }
        app.endUndoGroup();
        return "OK: " + n + "개 import -> auto_kairos/" + folderName;
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) {}
        return "ERROR: " + e.toString();
    }
}
