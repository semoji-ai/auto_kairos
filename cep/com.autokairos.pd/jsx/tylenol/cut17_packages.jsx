// 타이레놀 컷17 재현 — 4제품 패키지 2.5D + 3D 카메라.
// gemini 분석: 흰 그리드 배경, 4패키지가 각기 다른 방향에서 중앙으로 슬라이드인, 2.5D 약간 기울임.
// 고급: 3D 레이어 + 카메라 푸시인(깊이감) + Drop Shadow(패키지 그림자) + 그레인.
// 실행: AE > File > Scripts > Run Script File... → 이 파일.

function akTylenolPackages() {
    try {
        var W = 1920, H = 1080, FPS = 30, DUR = 2.0;
        var GRID_BG = [247 / 255, 247 / 255, 247 / 255];
        var proj = app.project || app.newProject();
        var here = new File($.fileName).parent;
        app.beginUndoGroup("TYL Cut17 Packages");
        var comp = proj.items.addComp("TYL_17_Packages", W, H, 1.0, DUR, FPS);
        comp.motionBlur = true;

        // (1) 흰 그리드 배경
        comp.layers.addSolid(GRID_BG, "bg", W, H, 1.0);
        var grid = comp.layers.addShape(); grid.name = "grid";
        var gc = grid.property("Contents");
        for (var gx = 0; gx <= W; gx += 80) { var l = gc.addProperty("ADBE Vector Group").property("Contents").addProperty("ADBE Vector Shape - Group"); var s = new Shape(); s.vertices = [[gx, 0], [gx, H]]; s.closed = false; l.property("Path").setValue(s); }
        for (var gy = 0; gy <= H; gy += 80) { var l2 = gc.addProperty("ADBE Vector Group").property("Contents").addProperty("ADBE Vector Shape - Group"); var s2 = new Shape(); s2.vertices = [[0, gy], [W, gy]]; s2.closed = false; l2.property("Path").setValue(s2); }
        var gst = gc.addProperty("ADBE Vector Graphic - Stroke"); gst.property("Color").setValue([0.90, 0.90, 0.92]); gst.property("Stroke Width").setValue(1);
        grid.property("Opacity").setValue(55);

        // (2) 카메라 먼저 만들어 실제 거리(D)를 읽는다 — 3D 공간 스케일 계산의 기준.
        var cam = comp.layers.addCamera("cam", [W / 2, H / 2]);
        var camPos = cam.property("ADBE Transform Group").property("ADBE Position");
        var D = Math.abs(camPos.value[2]);              // AE 기본 카메라 거리(1080 comp ≈ 2666px)

        // 3D 공간에서 화면상 목표 크기를 유지하는 스케일 — Z가 멀면(양수) 원근으로 작아지므로 보정.
        //  화면 비율 r 폭이 되려면: scale = (W*r/item.width) * ((D + Z) / D)
        function scaleAt(item, r, z) { return (W * r / item.width) * 100 * ((D + z) / D); }
        // Z 위치의 레이어가 화면 (px,py)에 보이려면 3D Position xy = (px-W/2)*(D+z)/D + W/2
        function projX(px, z) { return (px - W / 2) * ((D + z) / D) + W / 2; }
        function projY(py, z) { return (py - H / 2) * ((D + z) / D) + H / 2; }

        // 패키지 — Z축 깊이로 명확히 분리(카메라 거리의 ±20~28%). 공간 뒤에서 앞으로 날아와 정착.
        var items = [
            { f: "assets/pkg_cold.png", px: W * 0.30, py: H * 0.34, z: -D * 0.10, tilt: -8 },
            { f: "assets/pkg_er.png", px: W * 0.70, py: H * 0.34, z: D * 0.22, tilt: 9 },
            { f: "assets/pkg_500mg.png", px: W * 0.30, py: H * 0.66, z: D * 0.10, tilt: -5 },
            { f: "assets/pkg_womens.png", px: W * 0.70, py: H * 0.66, z: -D * 0.18, tilt: 7 }
        ];
        for (var i = 0; i < items.length; i++) {
            var it = items[i];
            var ff = new File(here.fsName + "/" + it.f);
            if (!ff.exists) continue;
            var item = proj.importFile(new ImportOptions(ff));
            var pkg = comp.layers.add(item);
            pkg.threeDLayer = true;
            var tg = pkg.property("ADBE Transform Group");
            // 목표 Z에서 화면 22% 폭이 되도록 원근 보정 스케일(깊이 달라도 크기 일정)
            var sTarget = scaleAt(item, 0.22, it.z);
            tg.property("ADBE Rotate Y").setValue(it.tilt);
            // 등장: 공간 깊숙이(Z = D*0.7 뒤)서 작게 → 목표 Z로 날아와 정착. 원근으로 다가오며 커짐.
            var zStart = D * 0.7;
            var sStart = scaleAt(item, 0.22, zStart);           // 시작은 같은 화면비율이지만 더 멀리
            var sc = tg.property("ADBE Scale");
            sc.setValueAtTime(0.1 + i * 0.18, [sStart, sStart, sStart]);
            sc.setValueAtTime(0.1 + i * 0.18 + 0.55, [sTarget, sTarget, sTarget]);
            var pos = tg.property("ADBE Position");
            var t0 = 0.1 + i * 0.18, t1 = t0 + 0.55;
            pos.setValueAtTime(t0, [projX(it.px, zStart), projY(it.py, zStart), zStart]);
            pos.setValueAtTime(t1, [it.px, it.py, it.z]);       // 목표 Z의 3D 좌표(투영 보정 불필요 — 실제 깊이 배치)
            try {
                sc.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80), new KeyframeEase(0, 80)]);
                pos.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80), new KeyframeEase(0, 80)]);
            } catch (e) {}
            var op = tg.property("ADBE Opacity"); op.setValueAtTime(t0, 0); op.setValueAtTime(t0 + 0.2, 100);
            pkg.motionBlur = true;
            try {
                var ds = pkg.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
                ds.property("ADBE Drop Shadow-0002").setValue(70);
                ds.property("ADBE Drop Shadow-0004").setValue(30);
                ds.property("ADBE Drop Shadow-0005").setValue(70);
            } catch (eD) {}
        }

        // (3) 카메라 횡이동(패럴랙스) — 무브폭을 거리 비례로(D*0.06 ≈ 160px) 충분히 줘야 깊이가 드러남.
        var mv = D * 0.06;
        camPos.setValueAtTime(0, [W / 2 - mv, H / 2, camPos.value[2]]);
        camPos.setValueAtTime(DUR, [W / 2 + mv, H / 2, camPos.value[2]]);
        try { camPos.setTemporalEaseAtKey(1, [new KeyframeEase(0, 35), new KeyframeEase(0, 35), new KeyframeEase(0, 35)]);
              camPos.setTemporalEaseAtKey(2, [new KeyframeEase(0, 35), new KeyframeEase(0, 35), new KeyframeEase(0, 35)]); } catch (e) {}

        // (4) 그레인 — 조정 레이어
        var grain = comp.layers.addSolid([1, 1, 1], "grain", W, H, 1.0);
        grain.adjustmentLayer = true;
        try {
            var ag = grain.property("ADBE Effect Parade").addProperty("ADBE Add Grain");
            ag.property("ADBE AddGrain-0002").setValue(0.4); ag.property("ADBE AddGrain-0003").setValue(0.6);
        } catch (eg) {
            try { var nz = grain.property("ADBE Effect Parade").addProperty("ADBE Noise2"); nz.property("ADBE Noise2-0001").setValue(6); grain.property("Opacity").setValue(40); } catch (eN) {}
        }

        comp.openInViewer();
        app.endUndoGroup();
        return "OK: TYL_17_Packages (2.5D 패키지 + 3D 카메라)";
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) {}
        return "ERROR: " + e.toString();
    }
}
akTylenolPackages();
