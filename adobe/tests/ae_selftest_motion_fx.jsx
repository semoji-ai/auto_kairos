// motion_fx.jsx 자체검사 — **AE 안에서만 확인되는 것들**을 본다.
//
// node/pytest 로 잡는 것은 식 문자열의 문법과 수치다. 아래 여섯 가지는
// AE 가 실제로 있어야만 알 수 있다.
//
//   1. `ADBE Dropdown Control` + setPropertyParameters 가 되는가
//   2. MarkerValue.setParameters / getParameters 가 되는가
//   3. 식이 AE 에서 **컴파일되는가** (expressionEnabled 가 살아 있는가)
//   4. 식 안에서 `effect(name).active` 를 읽는가
//   5. 식 안에서 `marker.key(i).parameters` 를 읽는가
//   6. **마커를 옮기면 타이밍이 따라오는가** ← 이게 이 기능의 핵심이다
//
// 검사는 임시 컴프 안에서만 하고 **끝나면 지운다.** 열려 있는 프로젝트의
// 다른 것은 건드리지 않는다.
//
// 실행:
//   osascript -e 'tell application "Adobe After Effects 2026" to DoScriptFile "…/ae_selftest_motion_fx.jsx"'
// 결과는 같은 폴더의 ae_selftest_result.txt 에 쓴다.

(function () {
    var HERE = new File($.fileName).parent;
    var out = [], pass = 0, fail = 0;

    function ok(cond, msg) {
        if (cond) { pass++; out.push("  ok   " + msg); }
        else { fail++; out.push("  FAIL " + msg); }
    }
    function near(a, b, tol) { return Math.abs(a - b) <= tol; }

    function report() {
        var head = (fail ? "실패 " + fail + "건 / " : "") + "통과 " + pass + "건";
        var fh = new File(HERE.fsName + "/ae_selftest_result.txt");
        fh.encoding = "UTF-8";
        fh.open("w"); fh.write(head + "\n" + out.join("\n") + "\n"); fh.close();
        return head;
    }

    // motion_fx.jsx 를 불러온다 — 사본을 두지 않는다.
    // **`$.evalFile` 은 인코딩을 짐작한다** — 한글 주석이 깨져 파싱이 실패한다.
    // 직접 UTF-8 로 읽어 eval 한다. 그리고 이 단계도 try 안에 둔다 —
    // 밖에 뒀더니 여기서 던지고 결과 파일조차 안 남아 원인을 못 찾았다.
    var src = new File(HERE.fsName + "/../cep/com.autokairos.pd/jsx/motion_fx.jsx");
    try {
        if (!src.exists) { throw new Error("motion_fx.jsx 없음: " + src.fsName); }
        src.encoding = "UTF-8";
        src.open("r");
        var code = src.read();
        src.close();
        eval(code);
    } catch (eLoad) {
        fail++;
        out.push("  FAIL 불러오기: " + eLoad.toString());
        return report();
    }

    var comp = null;
    try {
        app.beginUndoGroup("AK 자체검사");
        comp = app.project.items.addComp("AK 자체검사(임시)", 1920, 1080, 1, 3, 30);
        var sol = comp.layers.addSolid([1, 0, 0], "검사용", 400, 300, 1);
        sol.inPoint = 0; sol.outPoint = 3;
        comp.openInViewer();

        /* ── 1·2. 컨트롤과 마커가 만들어지는가 ── */
        sol.selected = true;
        var r = akFxApply("overshoot_position", "");
        ok(r.indexOf("OK") === 0, "오버슛 포지션 걸기 — " + r);

        var par = sol.property("ADBE Effect Parade");
        var names = [];
        for (var i = 1; i <= par.numProperties; i++) { names.push(par.property(i).name); }
        ok(names.length >= 8, "컨트롤 " + names.length + "개: " + names.join(", "));

        var dd = null;
        for (var j = 1; j <= par.numProperties; j++) {
            if (par.property(j).name.indexOf("방향") >= 0) { dd = par.property(j); }
        }
        ok(dd !== null, "방향 컨트롤 있음");
        if (dd) {
            // **항목을 넣으면 AE 가 드롭다운을 의사 이펙트로 바꾼다**
            // (matchName 이 `Pseudo/@@…` 가 된다). 그게 정상이라, matchName 이
            // "ADBE Dropdown Control" 인지 보면 늘 실패한다 — 실제로 그렇게 잡았다.
            // 볼 것은 「슬라이더로 물러서지 않았는가」와 「항목이 4개인가」다.
            ok(dd.name === "AK 방향", "드롭다운으로 붙었는가 (슬라이더 폴백이면 이름에 1~4 가 붙는다): " + dd.name);
            var items = -1;
            try { items = dd.property(1).propertyParameters.length; } catch (eIt) {
                try { items = AK_DIRS.length; } catch (eIt2) { }
            }
            ok(items === 4, "방향 항목 4개 (실제 " + items + ")");
            dd.property(1).setValue(3);
            ok(dd.property(1).value === 3, "방향을 바꿀 수 있는가");
        }

        var mp = sol.property("Marker");
        ok(mp.numKeys === 2, "마커 2개 (실제 " + mp.numKeys + ")");
        var gotParam = false;
        try {
            var p1 = mp.keyValue(1).getParameters();
            gotParam = !!(p1 && p1["zzz_AK역할"]);
        } catch (eGP) { }
        ok(gotParam, "마커 parameters 에 역할이 적혔는가");

        /* ── 3. 식이 AE 에서 컴파일되는가 ── */
        var pPos = sol.property("Transform").property("Position");
        var pOpa = sol.property("Transform").property("Opacity");
        ok(pPos.expressionEnabled, "위치 식이 살아 있는가");
        ok(pOpa.expressionEnabled, "투명도 식이 살아 있는가");
        try {
            var probe = pPos.valueAtTime(0.5, false);
            ok(probe.length >= 2 && !isNaN(probe[0]), "위치 식이 값을 낸다: " + probe[0].toFixed(1));
        } catch (eV) { ok(false, "위치 식 평가 실패: " + eV.toString()); }

        /* ── 6. 마커를 옮기면 타이밍이 따라오는가 (핵심) ── */
        var homeX = pPos.valueAtTime(2.0, false)[0];      // 정착 위치
        var tMk = mp.keyTime(1);
        var midBefore = pPos.valueAtTime(tMk, false);     // 마커 시점 = 등장 완료
        ok(near(midBefore[0], homeX, 1) && near(midBefore[1], pPos.valueAtTime(2.0, false)[1], 1),
           "마커 시점에 등장이 끝나 있는가");

        var far = 1.5;                                     // 마커를 훨씬 뒤로 민다
        var mv = mp.keyValue(1);
        mp.removeKey(1);
        mp.setValueAtTime(far, mv);
        var atOld = pPos.valueAtTime(tMk, false);
        ok(!near(atOld[1], homeX * 0 + pPos.valueAtTime(2.0, false)[1], 1),
           "마커를 옮기니 옛 시점은 아직 등장 중 (y=" + atOld[1].toFixed(1) + ")");
        var atNew = pPos.valueAtTime(far, false);
        ok(near(atNew[1], pPos.valueAtTime(2.0, false)[1], 1),
           "옮긴 마커 시점에 등장이 끝나 있는가 (y=" + atNew[1].toFixed(1) + ")");

        /* ── 4. fx 토글로 꺼지는가 ── */
        var master = null;
        for (var k = 1; k <= par.numProperties; k++) {
            if (par.property(k).name === "AK 모션") { master = par.property(k); }
        }
        ok(master !== null, "마스터 이펙트 있음");
        if (master) {
            master.enabled = false;
            var offv = pPos.valueAtTime(0.1, false);
            master.enabled = true;
            var onv = pPos.valueAtTime(0.1, false);
            ok(!near(offv[1], onv[1], 0.5),
               "fx 토글을 끄면 원래 값 (끔 " + offv[1].toFixed(1) + " / 켬 " + onv[1].toFixed(1) + ")");
        }

        /* ── 5. 컨트롤을 지워도 안 죽는가 ── */
        for (var m = par.numProperties; m >= 1; m--) {
            if (par.property(m).name.indexOf("부드러움") >= 0) { par.property(m).remove(); }
        }
        var afterDel = null;
        try { afterDel = pPos.valueAtTime(0.3, false); } catch (eD) { }
        ok(afterDel !== null && !isNaN(afterDel[0]) && pPos.expressionEnabled,
           "슬라이더를 지워도 식이 계속 돈다");

        /* ── 굽기 ── */
        akFxApply("overshoot_scale", "");
        var rb = akFxBake();
        var pSc = sol.property("Transform").property("Scale");
        ok(rb.indexOf("OK") === 0 && !pSc.expressionEnabled && pSc.numKeys > 5,
           "굽기 — " + rb + " / 키 " + pSc.numKeys + "개");

        /* ── 해제 ── */
        akFxApply("bounce_scale", "");
        var rc = akFxClear();
        ok(sol.property("ADBE Effect Parade").numProperties === 0
           && sol.property("Marker").numKeys === 0, "해제 — " + rc);

    } catch (e) {
        fail++;
        out.push("  FAIL 예외: " + e.toString() + " (line " + e.line + ")");
    } finally {
        // 임시 컴프는 반드시 지운다 — 남의 프로젝트에 흔적을 남기지 않는다.
        // **컴프만 지우면 솔리드 소스가 프로젝트에 남는다**(Solids 폴더에 쌓인다).
        // 실제로 두 번 돌리고 3개가 남아 있었다. 소스까지 지운다.
        try { if (comp) { comp.remove(); } } catch (eR) { }
        try {
            for (var z = app.project.numItems; z >= 1; z--) {
                var it = app.project.item(z);
                if (it.name === "검사용" || it.name === "AK 자체검사(임시)") { it.remove(); }
            }
            var solids = null;
            for (var y = app.project.numItems; y >= 1; y--) {
                var f = app.project.item(y);
                if (f instanceof FolderItem && f.numItems === 0
                    && (f.name === "Solids" || f.name === "솔리드")) { solids = f; }
            }
            if (solids) { solids.remove(); }
        } catch (eS) { }
        try { app.endUndoGroup(); } catch (eU) { }
    }

    return report();
})();
