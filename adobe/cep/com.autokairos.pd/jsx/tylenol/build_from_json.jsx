// 타이레놀 — gemini 모션 분석(motion.json)을 읽어 AE 컴프를 자동 생성하는 범용 빌더.
// 파이프라인: gemini 영상분석 → 구조화 JSON → 이 빌더가 기계적으로 컴프화.
// 레이어 type: text / rrect(검색창·버튼·블록) / line(그리드·가이드) / image(패키지) / live(실사).
// anim prop: opacity / scale / position / typeOn(타이핑·리빌). ease: in/out/inout/over/linear.
// 실행: AE > File > Scripts > Run Script File... → 이 파일.

function akBuildFromJson() {
    try {
        var here = new File($.fileName).parent;
        var envMotion = $.getenv("AK_VERIFY_MOTION");
        var jf = (envMotion && String(envMotion).length) ? new File(envMotion) : new File(here.fsName + "/motion.json");
        if (!jf.exists) return "ERROR: motion.json 없음: " + jf.fsName;
        jf.open("r"); var raw = jf.read(); jf.close();
        var D = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
        function loadJson(name) {
            var f = new File(here.fsName + "/" + name);
            if (!f.exists) return {};
            f.open("r"); var t = f.read(); f.close();
            try { return (typeof JSON === "object" && JSON.parse) ? JSON.parse(t) : eval("(" + t + ")"); }
            catch (e) { return {}; }
        }
        var PRESETS = (loadJson("motion_presets.json").presets) || {};
        var FONTMAP = loadJson("font_map.json");
        var COLORS = loadJson("color_tokens.json");
        function resolveFont(role) { return FONTMAP[role] || role || FONTMAP.fallback || "AppleSDGothicNeo-Bold"; }
        function resolveColor(key) {
            if (!key) return null;
            var v = (key.charAt(0) === "#") ? key : COLORS[key];
            return v ? hex(v) : null;
        }
        var W = (D.comp && D.comp.w) || 1920, H = (D.comp && D.comp.h) || 1080, FPS = (D.comp && D.comp.fps) || 30;
        var proj = app.project || app.newProject();
        app.beginUndoGroup("TYL Build from JSON");

        function hex(h) {
            if (!h) return [1, 1, 1]; h = String(h).replace("#", "");
            if (!/^[0-9a-fA-F]{6}/.test(h)) return [1, 1, 1];   // 비-hex(토큰키 등) → 흰색 폴백
            return [parseInt(h.substr(0, 2), 16) / 255, parseInt(h.substr(2, 2), 16) / 255, parseInt(h.substr(4, 2), 16) / 255];
        }
        function applyEase(prop, ki, dim, ease) {
            try {
                var inf = 75, e = []; for (var d = 0; d < dim; d++) e.push(new KeyframeEase(0, inf));
                if (ease === "in" || ease === "inout" || ease === "over") prop.setTemporalEaseAtKey(ki - 1, e, e);
                if (ease === "out" || ease === "inout" || ease === "over") prop.setTemporalEaseAtKey(ki, e, e);
            } catch (x) {}
        }
        function anchorCenter(layer) {
            try { var r = layer.sourceRectAtTime(0, false);
                  layer.property("Anchor Point").setValue([r.left + r.width / 2, r.top + r.height / 2]); } catch (x) {}
        }
        function assetFile(key) {
            var ext = (key === "live_clip" || key === "character_clip") ? ".mp4" : ".png";
            var f = new File(here.fsName + "/assets/" + key + ext);
            return f.exists ? f : null;
        }

        // 레이어 생성 ─ type별
        function makeText(comp, L) {
            var tl = comp.layers.addText(String(L.text || ""));
            var td = tl.property("Source Text").value;
            td.fontSize = L.size || 48; td.fillColor = L.rgb || hex(L.color && L.color.charAt(0) === "#" ? L.color : "#FFFFFF");
            var left = (L.align === "left");
            td.justification = left ? ParagraphJustification.LEFT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY;
            var ff = L._fontResolved ? [L._fontResolved, "AppleSDGothicNeo-Bold"] : ["OTSBAggroM", "Cafe24Ssurround", "AppleSDGothicNeo-Bold"];
            for (var i = 0; i < ff.length; i++) { try { td.font = ff[i]; } catch (e) {} }
            tl.property("Source Text").setValue(td);
            var r = tl.sourceRectAtTime(0, false);
            tl.property("Anchor Point").setValue([left ? r.left : r.left + r.width / 2, r.top + r.height / 2]);
            tl.property("Position").setValue([L.x == null ? W / 2 : L.x, L.y == null ? H / 2 : L.y]);
            return tl;
        }
        function makeRRect(comp, L) {
            var sl = comp.layers.addShape(); sl.name = "rrect";
            var g = sl.property("Contents").addProperty("ADBE Vector Group");
            var rc = g.property("Contents").addProperty("ADBE Vector Shape - Rect");
            rc.property("Size").setValue([L.w || 200, L.h || 80]);
            rc.property("Roundness").setValue(L.round || 0);
            var f = g.property("Contents").addProperty("ADBE Vector Graphic - Fill"); f.property("Color").setValue(L.rgb || hex(L.color && L.color.charAt(0) === "#" ? L.color : "#FFFFFF"));
            if (L.stroke) { var s = g.property("Contents").addProperty("ADBE Vector Graphic - Stroke"); s.property("Color").setValue(hex(L.stroke)); s.property("Stroke Width").setValue(L.size || 2); }
            sl.property("Anchor Point").setValue([0, 0]);   // 그룹 원점 = 중심 → 스케일 팝 제자리
            sl.property("Position").setValue([L.x == null ? W / 2 : L.x, L.y == null ? H / 2 : L.y]);
            // 텍스트 라벨(버튼)
            if (L.text) {
                var t2 = makeText(comp, { text: L.text, color: "#333333", size: L.labelSize || 40, x: L.x, y: L.y, align: "center" });
            }
            return sl;
        }
        function makeLine(comp, L) {
            var sl = comp.layers.addShape(); sl.name = "line";
            var g = sl.property("Contents").addProperty("ADBE Vector Group");
            var p = g.property("Contents").addProperty("ADBE Vector Shape - Group");
            var sh = new Shape();
            var x = L.x == null ? W / 2 : L.x, y = L.y == null ? H / 2 : L.y, w = L.w || W, h = L.h || 0;
            sh.vertices = [[x - w / 2, y - h / 2], [x + w / 2, y + h / 2]]; sh.closed = false; p.property("Path").setValue(sh);
            var st = g.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
            st.property("Color").setValue(L.rgb || hex(L.color && L.color.charAt(0) === "#" ? L.color : "#CCCCCC")); st.property("Stroke Width").setValue(L.size || 1);
            return sl;
        }
        function makeImage(comp, L) {
            var f = assetFile(L.asset); if (!f) return null;
            var item = proj.importFile(new ImportOptions(f));
            var L2 = comp.layers.add(item);
            var fit = (L.w ? L.w : W * 0.24) / item.width * 100;
            L2.property("Scale").setValue([fit, fit]);
            L2.property("Position").setValue([L.x == null ? W / 2 : L.x, L.y == null ? H / 2 : L.y]);
            return L2;
        }

        // ── 컴포넌트: 검색창 — 내부 요소(박스/아이콘/텍스트/전송버튼)를 상대좌표 규칙으로 자체 정렬.
        //  gemini 좌표 추정 오차와 무관하게 정렬 보장. 박스 좌→우 슬라이드인 + 텍스트 타이핑.
        function makeSearchbar(comp, cut) {
            var cy = cut.y == null ? H * 0.5 : cut.y;
            var barW = W * 0.62, barH = 200, barX = W / 2 - barW / 2, barY = cy - barH / 2;
            var GRAY = [0.80, 0.80, 0.82], RED = hex("#E4002B"), INK = hex("#333333");
            var grp = [];
            // 박스
            var box = makeRRect(comp, { color: "#FFFFFF", w: barW, h: barH, x: W / 2, y: cy, round: 28, stroke: "#E0E0E0", size: 2 });
            grp.push(box);
            // 하단 아이콘 3개(좌하단) + 전송버튼(우하단) — 박스 기준 상대좌표
            for (var k = 0; k < 3; k++) grp.push(makeRRect(comp, { color: "#E8E8EA", w: 34, h: 34, x: barX + 40 + k * 52, y: barY + barH - 44, round: 8 }));
            var send = makeRRect(comp, { color: "#E4002B", w: 44, h: 44, x: barX + barW - 56, y: barY + barH - 44, round: 22 });
            grp.push(send);
            // 텍스트(박스 내부 좌측) — 박스 폭에 맞춰 크기 동적 조정(넘침 방지). 타이핑. redText 앞부분 빨강.
            var tx = barX + 50, ty = cy - 24, maxTextW = barW - 110;
            var full = cut.text || "", red = cut.redText || "";
            // 한글 ~0.55·size, 공백/영문 ~0.3·size → 기준 폰트 46에서 폭 추정해 초과 시 축소
            var sz = 46, estW = full.length * sz * 0.52;
            if (estW > maxTextW) sz = Math.max(24, Math.floor(maxTextW / (full.length * 0.52)));
            ty = cy - sz / 2;
            var textLayers = [];
            if (red && full.indexOf(red) === 0) {        // 빨강이 맨 앞
                var tr = makeText(comp, { text: red, color: "#E4002B", size: sz, x: tx, y: ty, align: "left" });
                var rw = tr.sourceRectAtTime(0, false).width;
                var tk = makeText(comp, { text: full.substr(red.length), color: "#333333", size: sz, x: tx + rw + 4, y: ty, align: "left" });
                textLayers = [tr, tk];
            } else {
                textLayers = [makeText(comp, { text: full, color: "#333333", size: sz, x: tx, y: ty, align: "left" })];
            }
            // 슬라이드인(0~0.3s): 박스+아이콘+버튼 좌→우
            for (var g = 0; g < grp.length; g++) {
                var L = grp[g], p = L.property("Position"), pv = p.value;
                p.setValueAtTime(0, [pv[0] - W * 0.5, pv[1]]); p.setValueAtTime(0.3, [pv[0], pv[1]]);
                try { p.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80)]); } catch (e) {}
                L.motionBlur = true;
            }
            // 타이핑(0.4s~) — 텍스트 순차
            var tt = 0.4;
            for (var ti = 0; ti < textLayers.length; ti++) {
                applyAnim(textLayers[ti], true, [{ prop: "typeOn", from: [0], to: [100], t0: tt, t1: tt + (ti === 0 ? 0.4 : 1.4) }]);
                tt += (ti === 0 ? 0.45 : 0);
            }
        }
        // ── 컴포넌트: 버튼 — 둥근 회색 버튼 + 중앙 라벨, 스케일 팝(박스·라벨 동반).
        function makeButton(comp, cut) {
            var label = cut.text || "", w = Math.max(220, label.length * 60 + 100), h = 110;
            var box = makeRRect(comp, { color: "#EDEDED", w: w, h: h, x: W / 2, y: H / 2, round: h / 2 });
            var lab = makeText(comp, { text: label, color: "#333333", size: 44, x: W / 2, y: H / 2, align: "center" });
            var pair = [box, lab];
            for (var i = 0; i < pair.length; i++) {
                var sc = pair[i].property("Scale");
                sc.setValueAtTime(0, [60, 60]); sc.setValueAtTime(0.28, [100, 100]);
                try { sc.setTemporalEaseAtKey(2, [new KeyframeEase(0, 78), new KeyframeEase(0, 78)]); } catch (e) {}
                pair[i].motionBlur = true;
            }
        }

        // 프리셋명 → AE 키프레임+이징. params는 프리셋 기본값 + 컷별 오버라이드 병합.
        function easeDefaultSmoothness(ease) {
            if (ease === "linear") return 0.0;
            return 0.75; // easeOut/easeInOut/overshoot → 현행 influence 75
        }
        function smoothnessToInfluence(s) {
            if (s === undefined || s === null) return 75;
            if (s <= 0.0) return 0.1;   // AE influence 최소 0.1
            if (s >= 1.0) return 95;
            var ax = [0.0, 0.5, 0.75, 0.9, 1.0], ay = [0, 33, 75, 90, 95];
            for (var i = 0; i < ax.length - 1; i++) {
                if (s > ax[i] && s <= ax[i + 1]) {
                    return Math.round(ay[i] + (ay[i + 1] - ay[i]) * (s - ax[i]) / (ax[i + 1] - ax[i]));
                }
            }
            return 75;
        }
        function easeKeys(prop, dim, ease, smoothness) {
            try {
                var s = (smoothness === undefined || smoothness === null) ? easeDefaultSmoothness(ease) : smoothness;
                var inf = smoothnessToInfluence(s);
                var arr = []; for (var d = 0; d < dim; d++) arr.push(new KeyframeEase(0, inf));
                var n = prop.numKeys;
                if (ease === "easeOut" || ease === "overshoot") prop.setTemporalEaseAtKey(n, arr, arr);
                else if (ease === "easeInOut") { prop.setTemporalEaseAtKey(1, arr, arr); prop.setTemporalEaseAtKey(n, arr, arr); }
            } catch (e) {}
        }
        function applyPreset(layer, isText, presetName, t0, dur, params) {
            var P = PRESETS[presetName]; if (!P) return;
            var pr = {}; for (var k in (P.params || {})) pr[k] = P.params[k];
            var cut = params || {};
            for (var k2 in cut) pr[k2] = cut[k2];   // 컷별 오버라이드
            dur = dur || 0.6; t0 = t0 || 0;
            // 옵션 해석: 컷 params > 프리셋 레벨 > 기본
            function opt(key, dflt) { return (cut[key] !== undefined) ? cut[key] : (P[key] !== undefined) ? P[key] : dflt; }
            var role = opt("role", "in");
            var dist = opt("distance", 1.0);
            var smooth = (cut.smoothness !== undefined) ? cut.smoothness
                       : (P.smoothness !== undefined) ? P.smoothness : null;  // null → easeKeys가 ease 기본 매핑
            var rev = (role === "out");
            layer.motionBlur = true;
            try {
                if (presetName === "type_on" && isText) {
                    var an = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                    an.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
                    var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
                    try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
                    var off = sel.property("ADBE Text Percent Offset");
                    off.setValueAtTime(t0, rev ? 100 : 0); off.setValueAtTime(t0 + dur, rev ? 0 : 100);
                } else if (presetName === "fade_scale_in") {
                    var sf = 100 - (100 - (pr.scaleFrom || 85)) * dist;
                    var op = layer.property("Opacity"); op.setValueAtTime(t0, rev ? 100 : 0); op.setValueAtTime(t0 + dur * 0.6, rev ? 0 : 100);
                    var sc = layer.property("Scale");
                    sc.setValueAtTime(t0, rev ? [100, 100] : [sf, sf]); sc.setValueAtTime(t0 + dur, rev ? [sf, sf] : [100, 100]);
                    easeKeys(sc, 2, "easeOut", smooth);
                } else if (presetName === "slide_in") {
                    var dir = pr.dir || "left", off2 = (pr.offset || 80) * dist, ps = layer.property("Position"), cur = ps.value;
                    var dx = dir === "left" ? -off2 : dir === "right" ? off2 : 0;
                    var dy = dir === "up" ? -off2 : dir === "down" ? off2 : 0;
                    var pStart = rev ? [cur[0], cur[1]] : [cur[0] + dx, cur[1] + dy];
                    var pEnd = rev ? [cur[0] + dx, cur[1] + dy] : [cur[0], cur[1]];
                    ps.setValueAtTime(t0, pStart); ps.setValueAtTime(t0 + dur, pEnd); easeKeys(ps, 2, "easeOut", smooth);
                    var op2 = layer.property("Opacity"); op2.setValueAtTime(t0, rev ? 100 : 0); op2.setValueAtTime(t0 + dur * 0.4, rev ? 0 : 100);
                } else if (presetName === "pop_bounce") {
                    var ov = 100 + ((pr.overshoot || 110) - 100) * dist, sc2 = layer.property("Scale");
                    if (rev) {
                        sc2.setValueAtTime(t0, [100, 100]); sc2.setValueAtTime(t0 + dur * 0.4, [ov, ov]); sc2.setValueAtTime(t0 + dur, [0, 0]);
                    } else {
                        sc2.setValueAtTime(t0, [0, 0]); sc2.setValueAtTime(t0 + dur * 0.6, [ov, ov]); sc2.setValueAtTime(t0 + dur, [100, 100]);
                    }
                    try { sc2.setTemporalEaseAtKey(2, [new KeyframeEase(0, 80), new KeyframeEase(0, 80)]); sc2.setTemporalEaseAtKey(3, [new KeyframeEase(0, 60), new KeyframeEase(0, 60)]); } catch (e) {}
                    var op3 = layer.property("Opacity"); op3.setValueAtTime(t0, rev ? 100 : 0); op3.setValueAtTime(t0 + dur * 0.2, rev ? 0 : 100);
                } else if (presetName === "mask_reveal") {
                    try {
                        var cont = layer.property("ADBE Root Vectors Group");
                        var trim = cont.addProperty("ADBE Vector Filter - Trim");
                        var te = trim.property("ADBE Vector Trim End");
                        te.setValueAtTime(t0, rev ? 100 : 0); te.setValueAtTime(t0 + dur, rev ? 0 : 100); easeKeys(te, 1, "easeInOut", smooth);
                    } catch (eM) {
                        var op4 = layer.property("Opacity"); op4.setValueAtTime(t0, rev ? 100 : 0); op4.setValueAtTime(t0 + dur, rev ? 0 : 100);
                    }
                } else if (presetName === "tilt_2_5d") {
                    layer.threeDLayer = true;
                    var ang = (pr.angle || -15) * dist, ry = layer.property("ADBE Transform Group").property("ADBE Rotate Y");
                    ry.setValueAtTime(t0, rev ? ang : 0); ry.setValueAtTime(t0 + dur, rev ? 0 : ang); easeKeys(ry, 1, "easeOut", smooth);
                }
            } catch (eP) {}
        }
        function applyDetail(layer, details) {
            if (!details || !details.length) return;
            for (var i = 0; i < details.length; i++) {
                var d = details[i];
                try {
                    if (d === "shadow") {
                        var ds = layer.property("ADBE Effect Parade").addProperty("ADBE Drop Shadow");
                        ds.property("ADBE Drop Shadow-0002").setValue(55); ds.property("ADBE Drop Shadow-0004").setValue(18); ds.property("ADBE Drop Shadow-0005").setValue(120);   // 리서치: 부드러운 섀도(softness 120)가 프리미엄
                    } else if (d === "glow") {
                        layer.property("ADBE Effect Parade").addProperty("ADBE Glo2");
                    } else if (d === "depth_blur") {
                        var gb = layer.property("ADBE Effect Parade").addProperty("ADBE Gaussian Blur 2");
                        gb.property("ADBE Gaussian Blur 2-0001").setValue(4);
                    } else if (d === "motion_blur") {
                        layer.motionBlur = true;
                    }
                } catch (e) {}
            }
        }
        function addGrainAdjustment(comp) {
            try {
                var g = comp.layers.addSolid([1, 1, 1], "grain", comp.width, comp.height, 1.0);
                g.adjustmentLayer = true;
                try { var ag = g.property("ADBE Effect Parade").addProperty("ADBE Add Grain"); ag.property("ADBE AddGrain-0002").setValue(0.4); }
                catch (eA) { var nz = g.property("ADBE Effect Parade").addProperty("ADBE Noise2"); nz.property("ADBE Noise2-0001").setValue(6); g.property("Opacity").setValue(40); }
            } catch (e) {}
        }
        function applyAnim(layer, isText, anims) {
            if (!anims) return;
            for (var a = 0; a < anims.length; a++) {
                var an = anims[a], t0 = an.t0 || 0, t1 = an.t1 == null ? t0 + 0.5 : an.t1;
                if (an.preset) { applyPreset(layer, isText, an.preset, t0, (an.dur || (t1 - t0)), an.params); continue; }
                var fr = an.from || [0], to = an.to || [100];
                try {
                    if (an.prop === "opacity") {
                        var op = layer.property("Opacity");
                        op.setValueAtTime(t0, fr[0]); op.setValueAtTime(t1, to[0]); applyEase(op, 2, 1, an.ease);
                    } else if (an.prop === "scale") {
                        var sc = layer.property("Scale");
                        sc.setValueAtTime(t0, [fr[0], fr[fr.length > 1 ? 1 : 0]]);
                        sc.setValueAtTime(t1, [to[0], to[to.length > 1 ? 1 : 0]]); applyEase(sc, 2, 2, an.ease);
                        if (an.ease === "over") { sc.setValueAtTime(t1 - (t1 - t0) * 0.25, [to[0] * 1.08, to[0] * 1.08]); }
                    } else if (an.prop === "position") {
                        var ps = layer.property("Position"), cur = ps.value;
                        var f2 = fr.length > 1 ? [fr[0], fr[1]] : [cur[0] + fr[0], cur[1]];
                        var t2 = to.length > 1 ? [to[0], to[1]] : [cur[0], cur[1]];
                        ps.setValueAtTime(t0, f2); ps.setValueAtTime(t1, t2); applyEase(ps, 2, 2, an.ease);
                    } else if (an.prop === "typeOn" && isText) {
                        var anim = layer.property("ADBE Text Properties").property("ADBE Text Animators").addProperty("ADBE Text Animator");
                        anim.property("ADBE Text Animator Properties").addProperty("ADBE Text Opacity").setValue(0);
                        var sel = anim.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
                        try { sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness").setValue(0); } catch (e) {}
                        var off = sel.property("ADBE Text Percent Offset");
                        off.setValueAtTime(t0, 0); off.setValueAtTime(t1, 100);
                    }
                } catch (eA) {}
                layer.motionBlur = true;
            }
        }

        // ── 컷별 컴프 생성 ──
        var comps = [], log = [];
        for (var ci = 0; ci < D.cuts.length; ci++) {
            var cut = D.cuts[ci];
            var comp = proj.items.addComp("TYL_" + (cut.id || ci), W, H, 1.0, Math.max(0.4, cut.dur || 2), FPS);
            comp.motionBlur = true;
            comp.layers.addSolid(resolveColor(cut.bg) || hex(cut.bg && cut.bg.charAt(0) === "#" ? cut.bg : "#FFFFFF"), "bg", W, H, 1.0);
            // 컴포넌트 타입 — 검색창/버튼은 내부 자체 정렬(좌표 추정 무관)
            if (cut.type === "searchbar") { try { makeSearchbar(comp, cut); } catch (eS) { log.push(cut.id + ": searchbar " + eS); } comps.push({ c: comp, dur: cut.dur || 2 }); continue; }
            if (cut.type === "button") { try { makeButton(comp, cut); } catch (eB) { log.push(cut.id + ": button " + eB); } comps.push({ c: comp, dur: cut.dur || 2 }); continue; }
            var layers = cut.layers || [];
            // 정순: layers[0]=배경(먼저 add=아래), 뒤일수록 전경(위). AE는 나중 add가 위라
            //  정순으로 add해야 text(전경)가 rrect(배경) 위에 보임.
            for (var li = 0; li < layers.length; li++) {
                var L = layers[li], lay = null, isText = false;
                if (L.font) L._fontResolved = resolveFont(L.font);
                var lc = resolveColor(L.color); if (lc) L.rgb = lc;
                try {
                    if (L.type === "text") { lay = makeText(comp, L); isText = true; }
                    else if (L.type === "rrect") lay = makeRRect(comp, L);
                    else if (L.type === "line") lay = makeLine(comp, L);
                    else if (L.type === "image" || L.type === "live") lay = makeImage(comp, L);
                } catch (eL) { log.push((cut.id) + "/" + L.type + ": " + eL.toString()); }
                if (lay) applyAnim(lay, isText, L.anim);
                if (lay && L.detail) applyDetail(lay, L.detail);
            }
            if (cut.grain) addGrainAdjustment(comp);
            comps.push({ c: comp, dur: cut.dur || 2 });
        }

        // ── Final 조립 ──
        var total = 0; for (var k = 0; k < comps.length; k++) total += comps[k].dur;
        var fc = proj.items.addComp("TYL_Final", W, H, 1.0, Math.max(1, total), FPS);
        var t = 0;
        for (var j = 0; j < comps.length; j++) { var fl = fc.layers.add(comps[j].c); fl.startTime = t; t += comps[j].dur; }
        fc.openInViewer();
        app.endUndoGroup();
        return "OK: " + comps.length + "컷 + Final(" + Math.round(total) + "s)" + (log.length ? " | 오류 " + log.length + ": " + log.slice(0, 3).join(" ; ") : "");
    } catch (e) {
        try { app.endUndoGroup(); } catch (_) {}
        return "ERROR: " + e.toString();
    }
}
akBuildFromJson();
