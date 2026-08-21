// auto_kairos — manifest 기반 AE 컴프 생성 (PoC, 최소 모션)
// 입력: manifest 경로(JSON). 출력: 씬별 컴프 + Final 컴프(순서 배치).
// JSON 파싱: json2.jsx 폴리필(JSON.parse) 우선, 없으면 eval 폴백.

function akBuildScene(manifestPath) {
    // 디자인 토큰(semoji) — manifest.ae_tokens 로드 실패 시 내장 기본값
    var TK = { colors: { bgRgb: [35, 38, 43], textRgb: [232, 234, 237], mutedRgb: [154, 160, 166], accentRgb: [74, 144, 217] },
               fonts: { headline: "", body: "", number: "", fallback: "AppleSDGothicNeo-Bold" },
               type: { headline: 110, sub: 48, item: 52, metric: 220, metricLabel: 54, quote: 64, quoteWho: 40, barLabel: 36, barValue: 40 } };

    // 폰트 해석 — AE 폰트 DB(app.fonts)에서 PS명 검증, 실패 시 패밀리 키워드 검색으로 보정.
    // AE가 못 찾으면 경고 수집(빌드 결과 문자열에 노출) — 조용한 폴백 금지.
    var FONT_WARN = [];
    function resolveFontPS(ps, famKey, styleHint) {
        try {
            if (!(app.fonts && app.fonts.allFonts)) return ps;   // 구버전 AE — 검증 불가, 그대로
            var groups = app.fonts.allFonts, i, j, f;
            for (i = 0; i < groups.length; i++) for (j = 0; j < groups[i].length; j++) {
                if (groups[i][j].postScriptName === ps) return ps;   // 설치 확인됨
            }
            if (famKey) {                                        // PS명 불일치 → 패밀리로 탐색
                var best = null, key = String(famKey).toLowerCase();
                for (i = 0; i < groups.length && !best; i++) for (j = 0; j < groups[i].length; j++) {
                    f = groups[i][j];
                    if (String(f.familyName).toLowerCase().indexOf(key) < 0) continue;
                    if (!best) best = f;
                    if (styleHint && String(f.styleName).toLowerCase().indexOf(String(styleHint).toLowerCase()) >= 0) { best = f; break; }
                }
                if (best) { FONT_WARN.push(ps + "→" + best.postScriptName); return best.postScriptName; }
            }
            FONT_WARN.push(ps + " 미설치(AE 재시작 필요)");
        } catch (e) { }
        return ps;
    }

    // 배경 솔리드 + 텍스트/셰이프 빌더 — 레이아웃 씬(JSON→결정적 렌더)
    function addBgSolid(comp, W, H, rgb) {
        return comp.layers.addSolid([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255], "bg", W, H, 1.0);
    }
    // 텍스트 레이어 — opts: {x,y,size,rgb,font,just,track,box:[w,h],leading}
    // box 지정 시 박스 텍스트(자동 줄바꿈, x/y=박스 중심). 폰트는 폴백 체인 + 적용 검증.
    // 키네틱 타이포 — Text Animator + Range Selector. anim={type,t0,dur,dir,ease}.
    // type: reveal(글자별 닦임 등장) / slide(방향 슬라이드) / type(타이핑) / word_stagger(단어 시차).
    // Range Selector Offset를 0→100% 키프레임 → 셀렉터가 텍스트를 쓸며 등장. 실패해도 무해(텍스트는 정상).
    function _addTextAnim(tl, anim) {
        try {
            var t0 = anim.t0 || 0, dur = anim.dur || 1.0, type = anim.type || "reveal";
            var animers = tl.property("ADBE Text Properties").property("ADBE Text Animators");
            var an = animers.addProperty("ADBE Text Animator");
            var props = an.property("ADBE Text Animator Properties");
            if (type === "slide") {                       // 글자별 위치 오프셋
                var dir = anim.dir || "up";
                var off = dir === "left" ? [-80, 0] : dir === "right" ? [80, 0]
                        : dir === "down" ? [0, -60] : [0, 60];
                props.addProperty("ADBE Text Position 3D").setValue([off[0], off[1], 0]);
                props.addProperty("ADBE Text Opacity").setValue(0);
            } else {                                       // reveal/type/word — 투명도 닦임
                props.addProperty("ADBE Text Opacity").setValue(0);
            }
            var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
            if (type === "word_stagger") {                 // 단위=단어(3). 1=글자,2=공백제외글자,3=단어,4=줄
                try { sel.property("ADBE Text Range Type2").setValue(3); } catch (eW) { }
            }
            // 셀렉터 폭 — 타이핑은 좁게(딱딱한 글자단위), 나머지는 부드럽게
            try {
                var smooth = sel.property("ADBE Text Range Advanced").property("ADBE Text Range Smoothness");
                if (smooth) smooth.setValue(type === "type" ? 0 : 100);
            } catch (eS) { }
            // Offset 0→100: 전체선택(opacity 0=안보임) → 선택해제(보임). 글자가 왼쪽부터 순차 등장.
            // (-100→0은 보였다 사라지는 역방향이라 금지)
            var offP = sel.property("ADBE Text Percent Offset");
            offP.setValueAtTime(t0, 0);
            offP.setValueAtTime(t0 + dur, 100);
            try {
                offP.setTemporalEaseAtKey(1, [new KeyframeEase(0, 75)], [new KeyframeEase(0, 75)]);
                offP.setTemporalEaseAtKey(2, [new KeyframeEase(0, 33)], [new KeyframeEase(0, 33)]);
            } catch (eE) { }
            tl.motionBlur = true;
        } catch (e) { }
    }
    function addTextL(comp, str, opts) {
        var tl = opts.box
            ? comp.layers.addBoxText([opts.box[0], opts.box[1]], String(str))
            : comp.layers.addText(String(str));
        var td = tl.property("Source Text").value;
        td.fontSize = opts.size;
        td.fillColor = [opts.rgb[0] / 255, opts.rgb[1] / 255, opts.rgb[2] / 255];
        var chain = [opts.font, TK.fonts.fallback, "AppleSDGothicNeo-Bold"];
        for (var fi = 0; fi < chain.length; fi++) {
            if (!chain[fi]) continue;
            try {
                td.font = chain[fi];
                tl.property("Source Text").setValue(td);
                td = tl.property("Source Text").value;
                if (td.font === chain[fi]) break;        // 실제 적용됐는지 되읽어 확인
            } catch (e) { }
        }
        try { td.justification = opts.just || ParagraphJustification.CENTER_JUSTIFY; } catch (e) { }
        try { if (opts.track) td.tracking = opts.track; } catch (e) { }
        try { if (opts.leading) { td.autoLeading = false; td.leading = opts.size * opts.leading; } } catch (e) { }
        tl.property("Source Text").setValue(td);
        // 앵커포인트를 실제 텍스트 박스 중앙으로 — 점 텍스트(box 없음)는 기본 앵커가 베이스라인
        // 좌하단이라 Position이 어긋남. sourceRectAtTime으로 렌더된 bounds 중앙을 앵커로(정렬 반영됨).
        try {
            var rc = tl.sourceRectAtTime(0, false);
            tl.property("Anchor Point").setValue([rc.left + rc.width / 2, rc.top + rc.height / 2]);
        } catch (e) { }
        tl.property("Position").setValue([opts.x, opts.y]);
        if (opts.anim) _addTextAnim(tl, opts.anim);    // 키네틱 타이포(있으면)
        return tl;
    }
    function addRectL(comp, name, x, y, w, h, rgb) {   // 좌상단 기준 사각형 셰이프
        var sl = comp.layers.addShape(); sl.name = name;
        var grp = sl.property("Contents").addProperty("ADBE Vector Group");
        var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
        rect.property("Size").setValue([w, h]);
        var fill = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("Color").setValue([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255]);
        sl.property("Position").setValue([x + w / 2, y + h / 2]);
        return sl;
    }
    // 점선 적용 — dash="4 6" 형식(있으면). 셰이프 레이어 첫 스트로크에.
    function applyDash(layer, dash, S) {
        if (!dash) return;
        try {
            var grp = layer.property("Contents").property(1);
            var stroke = null, cc = grp.property("Contents");
            for (var i = 1; i <= cc.numProperties; i++) {
                if (cc.property(i).matchName === "ADBE Vector Graphic - Stroke") { stroke = cc.property(i); break; }
            }
            if (!stroke) return;
            var parts = String(dash).split(/\s+/);
            var dProp = stroke.property("Dashes").addProperty("ADBE Vector Stroke Dash 1");
            dProp.setValue(parseFloat(parts[0]) * S);
        } catch (e) { }
    }
    // 평행선 해칭 한 방향을 사각형 [x0..x1, y0..y1]에 클립해 그룹에 추가.
    // dir: "diag1"(↘ 기울기1) / "diag2"(↙ 기울기-1) / "vert" / "horiz"
    function _hatchDir(hc, x0, x1, y0, y1, sp, dir) {
        var b, pts, pp, shp;
        if (dir === "vert") {
            for (b = x0 + sp / 2; b < x1; b += sp) {
                pp = hc.addProperty("ADBE Vector Shape - Group");
                shp = new Shape(); shp.vertices = [[b, y0], [b, y1]]; shp.closed = false;
                pp.property("Path").setValue(shp);
            }
            return;
        }
        if (dir === "horiz") {
            for (b = y0 + sp / 2; b < y1; b += sp) {
                pp = hc.addProperty("ADBE Vector Shape - Group");
                shp = new Shape(); shp.vertices = [[x0, b], [x1, b]]; shp.closed = false;
                pp.property("Path").setValue(shp);
            }
            return;
        }
        var slope = (dir === "diag2") ? -1 : 1;          // y = slope*x + b
        var bMin = (slope > 0) ? (y0 - x1) : (y0 + x0);
        var bMax = (slope > 0) ? (y1 - x0) : (y1 + x1);
        for (b = bMin; b <= bMax; b += sp) {
            pts = [];
            var yA = slope * x0 + b; if (yA >= y0 && yA <= y1) pts.push([x0, yA]);
            var yB = slope * x1 + b; if (yB >= y0 && yB <= y1) pts.push([x1, yB]);
            var xA = (y0 - b) / slope; if (xA > x0 && xA < x1) pts.push([xA, y0]);
            var xB = (y1 - b) / slope; if (xB > x0 && xB < x1) pts.push([xB, y1]);
            if (pts.length < 2) continue;
            pp = hc.addProperty("ADBE Vector Shape - Group");
            shp = new Shape(); shp.vertices = [pts[0], pts[1]]; shp.closed = false;
            pp.property("Path").setValue(shp);
        }
    }
    // chartagent 명세 반영 막대 — 채움(+패턴 오퍼시티) + 외곽선 + 패턴을 한 레이어에.
    // 사각형은 레이어 원점 중심 [-w/2..w/2, -h/2..h/2] → bar 루프가 앵커/포지션으로 하단 고정.
    function addBarShape(comp, name, w, h, rgb, CS, S) {
        var sl = comp.layers.addShape(); sl.name = name;
        var root = sl.property("Contents");
        // 패턴 종류 — chartagent: diagonal_hatch / wide_diagonal / crosshatch_light / vertical_stripe / dot_sparse
        var pk = CS.patternKind || "";
        var patterned = pk && pk !== "solid" && pk !== "none";
        var outlineW = (CS.outlineWidth || 0) * S;
        var x0 = -w / 2, x1 = w / 2, y0 = -h / 2, y1 = h / 2;
        // 채움 — 패턴이면 약하게(패턴 오퍼시티), 아니면 단색
        var fg = root.addProperty("ADBE Vector Group");
        var rect = fg.property("Contents").addProperty("ADBE Vector Shape - Rect");
        rect.property("Size").setValue([w, h]);
        var fill = fg.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("Color").setValue(rgb);
        if (patterned) { try { fill.property("Opacity").setValue((CS.patternOpacity != null ? CS.patternOpacity : 0.45) * 100); } catch (e) { } }
        // 패턴 — 사각형에 클립된 선/점들(같은 레이어 → Scale 동반)
        if (patterned) {
            var sp = (CS.patternSpacing || 14) * S, sw = (CS.patternStrokeWidth || 1.3) * S;
            if (pk === "wide_diagonal") sp *= 1.7;
            if (pk === "dot_sparse") {
                // 점 격자 — 작은 원 채움
                var dg = root.addProperty("ADBE Vector Group"), dc = dg.property("Contents");
                var r = Math.max(1.2 * S, sw);
                for (var dx = x0 + sp; dx < x1; dx += sp) {
                    for (var dy = y0 + sp; dy < y1; dy += sp) {
                        var eg = dc.addProperty("ADBE Vector Group");
                        var el = eg.property("Contents").addProperty("ADBE Vector Shape - Ellipse");
                        el.property("Size").setValue([r * 2, r * 2]);
                        el.property("Position").setValue([dx, dy]);
                    }
                }
                var df = dc.addProperty("ADBE Vector Graphic - Fill");
                df.property("Color").setValue(rgb);
            } else {
                var hg = root.addProperty("ADBE Vector Group"), hc = hg.property("Contents");
                if (pk === "vertical_stripe") {
                    _hatchDir(hc, x0, x1, y0, y1, sp, "vert");
                } else if (pk === "crosshatch_light") {
                    _hatchDir(hc, x0, x1, y0, y1, sp, "diag1");
                    _hatchDir(hc, x0, x1, y0, y1, sp, "diag2");   // 양방향 교차
                } else {                                          // diagonal_hatch / wide_diagonal / 기타
                    _hatchDir(hc, x0, x1, y0, y1, sp, "diag1");
                }
                var hst = hg.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
                hst.property("Color").setValue(rgb);
                hst.property("Stroke Width").setValue(sw);
            }
        }
        // 외곽선 — 마지막에 추가(맨 위)
        if (outlineW > 0) {
            var og = root.addProperty("ADBE Vector Group");
            var orect = og.property("Contents").addProperty("ADBE Vector Shape - Rect");
            orect.property("Size").setValue([w, h]);
            var ost = og.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
            ost.property("Color").setValue(rgb);
            ost.property("Stroke Width").setValue(outlineW);
        }
        return sl;
    }
    // 지도 오버레이 — 지도는 배경판(이미지)이고 마커/라벨/경로는 AE 네이티브 레이어.
    // geo: {markers:[{name,x,y}], route:[[x,y]...], labelRgb} — 픽셀 좌표(map.project 기준).
    // 키프레임/경로/라벨 전부 AE에서 직접 수정 가능.
    function renderMapOverlay(comp, geo, W, H, dur) {
        var c = TK.colors, S = W / 1920;
        var ac = [c.accentRgb[0] / 255, c.accentRgb[1] / 255, c.accentRgb[2] / 255];
        var lr = geo.labelRgb || [26, 26, 26];
        // 1) 이동 경로 — 셰이프 패스 + Trim Paths(끝 0→100%)로 선이 그려지는 애니메이션
        if (geo.route && geo.route.length >= 2) {
            var rl = comp.layers.addShape(); rl.name = "map_route";
            rl.property("Position").setValue([0, 0]);
            rl.property("Anchor Point").setValue([0, 0]);
            var rg = rl.property("Contents").addProperty("ADBE Vector Group");
            var pathProp = rg.property("Contents").addProperty("ADBE Vector Shape - Group");
            var shp = new Shape();
            shp.vertices = geo.route; shp.closed = false;
            pathProp.property("Path").setValue(shp);
            var st = rg.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
            st.property("Color").setValue(ac);
            st.property("Stroke Width").setValue(8 * S);
            try {
                st.property("Line Cap").setValue(2);                    // 둥근 끝
                st.property("Dashes").addProperty("Dash");              // 점선(여정 느낌)
                st.property("Dashes").property("Dash").setValue(26 * S);
            } catch (eD) { }
            var trim = rg.property("Contents").addProperty("ADBE Vector Filter - Trim");
            var te = trim.property("End");
            te.setValueAtTime(0.4, 0); te.setValueAtTime(Math.max(1.2, dur * 0.6), 100);
            try { te.setTemporalEaseAtKey(2, [new KeyframeEase(0, 33)], [new KeyframeEase(0, 33)]); } catch (eE) { }
        }
        // 2) 마커 — 점별 셰이프 레이어(흰 테두리 원), 순차 팝 등장
        var marks = geo.markers || [];
        for (var mi = 0; mi < marks.length; mi++) {
            var m = marks[mi], t0 = 0.3 + mi * 0.4;
            var ml = comp.layers.addShape(); ml.name = "map_marker_" + (m.name || mi);
            var mg = ml.property("Contents").addProperty("ADBE Vector Group");
            var el = mg.property("Contents").addProperty("ADBE Vector Shape - Ellipse");
            el.property("Size").setValue([34 * S, 34 * S]);
            var mfill = mg.property("Contents").addProperty("ADBE Vector Graphic - Fill");
            mfill.property("Color").setValue(ac);
            var mst = mg.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
            mst.property("Color").setValue([1, 1, 1]);
            mst.property("Stroke Width").setValue(6 * S);
            ml.property("Anchor Point").setValue([0, 0]);               // 피벗=원 중심(팝이 제자리)
            ml.property("Position").setValue([m.x, m.y]);
            var msc = ml.property("Scale");
            msc.setValueAtTime(t0, [0, 0]);
            msc.setValueAtTime(t0 + 0.25, [115, 115]);
            msc.setValueAtTime(t0 + 0.38, [100, 100]);
            // 3) 라벨 — 텍스트 레이어(테마 대비색), 마커 옆에서 페이드 인
            if (m.name) {
                var tl2 = addTextL(comp, m.name, { x: m.x, y: m.y + 56 * S, size: 36 * S,
                                                   rgb: lr, font: TK.fonts.bold || TK.fonts.body });
                tl2.name = "map_label_" + m.name;
                var lop = tl2.property("Opacity");
                lop.setValueAtTime(t0 + 0.15, 0); lop.setValueAtTime(t0 + 0.45, 100);
            }
        }
    }

    // 레이아웃 5종 결정적 렌더 — 1080p 기준 토큰을 S=W/1920 배율로 스케일(4K/720p 대응).
    // 긴 텍스트는 박스 텍스트(자동 줄바꿈 + 행간 1.25). 세로 폼은 별도 템플릿 필요(추후).
    function renderLayout(proj, comp, s, W, H) {
        var c = TK.colors, t = TK.type;
        var S = W / 1920;                                  // 해상도 배율(1080p=1)
        addBgSolid(comp, W, H, c.bgRgb);
        // v3 레이아웃은 원래 스토리보드 이미지 위에 겹쳐 그린다 — 있으면 풀프레임 배경으로 먼저 깐다.
        if (s.image) {
            try {
                var imgF = new File(s.image);
                if (imgF.exists) {
                    var imgFoot = proj.importFile(new ImportOptions(imgF));
                    var imgL = comp.layers.add(imgFoot);
                    // 좌표는 매니페스트가 구워서 준다 — 세로 기준 배율이라 위아래가 안 잘린다.
                    var ifit = s.imageFit || {};
                    var ipos = ifit.position || [W / 2, H / 2];
                    var isc = (ifit.scale != null) ? ifit.scale : 100;
                    imgL.property("Anchor Point").setValue([imgL.source.width / 2, imgL.source.height / 2]);
                    imgL.property("Position").setValue([ipos[0], ipos[1]]);
                    imgL.property("Scale").setValue([isc, isc]);
                }
            } catch (eImg) { }
        }
        // 렌더러는 layouts.jsx에 있다. 헬퍼가 이 함수의 클로저라 ctx로 넘긴다.
        akRenderLayout(comp, s, {
            W: W, H: H, S: S, colors: c, type: t, fonts: TK.fonts,
            addTextL: addTextL, addRectL: addRectL, addBarShape: addBarShape, applyDash: applyDash
        });
    }
    // 평면 컴프 — 컴프는 Final 하나. 씬은 S{번호}_ 접두사 레이어 그룹으로 구분한다.
    function akFindOrMakeComp(proj, name, W, H, fps, dur) {
        for (var i = 1; i <= proj.numItems; i++) {
            var it = proj.item(i);
            if (it instanceof CompItem && it.name === name) {
                if (dur > it.duration) { it.duration = dur; }
                return it;
            }
        }
        return proj.items.addComp(name, W, H, 1.0, Math.max(dur, 1), fps);
    }

    // 이 씬의 레이어를 전부 지운다(재빌드는 지우고 다시 넣는다).
    function akRemoveSceneGroup(comp, prefix) {
        var n = 0;
        for (var i = comp.numLayers; i >= 1; i--) {
            if (comp.layer(i).name.indexOf(prefix) === 0) { comp.layer(i).remove(); n++; }
        }
        return n;
    }

    // 다음 씬 그룹의 최상단 레이어 — 새 그룹을 그 위에 놓아 씬 번호 순서를 지킨다.
    function akGroupAnchor(comp, scenes, idx) {
        for (var j = idx + 1; j < scenes.length; j++) {
            var pf = scenes[j].prefix;
            if (!pf) { continue; }
            for (var i = 1; i <= comp.numLayers; i++) {
                if (comp.layer(i).name.indexOf(pf) === 0) { return comp.layer(i); }
            }
        }
        return null;
    }

    // 방금 만들어진 레이어 구간(맨 위 ~ fromIndex)에 접두사를 붙이고 가이드에 묶는다.
    // renderLayout/renderMapOverlay가 만든 레이어를 돌려주지 않으므로 개수로 구간을 잡는다.
    function akTagGroup(comp, madeCount, prefix, guide, t0, t1) {
        for (var i = 1; i <= madeCount && i <= comp.numLayers; i++) {
            var lay = comp.layer(i);
            if (lay === guide) { continue; }
            if (lay.name.indexOf(prefix) !== 0) { lay.name = prefix + lay.name; }
            lay.inPoint = t0; lay.outPoint = t1;
            if (!lay.parent) { lay.parent = guide; }
        }
    }

    // 레이어 추가. layer.position 있으면 그 좌표·스케일로(크롭된 요소), 없으면 컴프 채움·중앙(풀프레임/배경).
    // 자동 효과(페이드 등)는 넣지 않는다 — 모든 모션은 모션 플랜(applyMoves)에서만(규칙 기반).
    function addLayerObj(proj, comp, layer, W, H) {
        var f = new File(layer.path);
        if (!f.exists) return null;
        var foot = proj.importFile(new ImportOptions(f));
        var il = comp.layers.add(foot);
        // SVG는 기본값으로 100% 크기에서 한 번만 래스터화된다 — 확대하면 PNG처럼 깨진다.
        // 연속 래스터화를 켜야 배율마다 벡터에서 다시 그린다. 이것이 벡터화의 목적 그 자체다.
        // 부작용: 이 스위치를 켠 레이어는 블렌딩 모드와 일부 이펙트가 무시된다(AE 제약).
        if (layer.vector) { try { il.collapseTransformation = true; } catch (eCR) { } }
        var sw = il.source.width, sh = il.source.height;
        il.property("Anchor Point").setValue([sw / 2, sh / 2]);
        // 좌표는 매니페스트가 컴프 공간으로 구워서 준다 — 여기서 계산하지 않는다.
        var lp = layer.position || [W / 2, H / 2];
        var ls = (layer.scale != null) ? layer.scale : 100;
        il.property("Position").setValue([lp[0], lp[1]]);
        il.property("Scale").setValue([ls, ls]);
        return il;
    }
    // 프리셋 모션 → 키프레임(결정적). 실패해도 빌드는 계속(try/catch).
    // 발밑(불투명 하단 중앙) 피벗 null 생성 + 페어런팅 + 세로 스케일 100↔(100+amt) 이지이즈 핑퐁 루프.
    // foot = manifest가 계산한 알파 bbox 하단 중앙(전신=발, 상반신=절단점) — 까딱까딱 idle.
    function addBobNull(comp, il, layer, t0, amt, tEnd) {
        var prevParent = il.parent;
        il.parent = null;
        var nl = comp.layers.addNull();
        nl.name = (layer.aeName || layer.name || "el") + "_피벗";
        nl.property("Position").setValue([layer.foot[0], layer.foot[1]]);
        nl.inPoint = il.inPoint;
        nl.outPoint = il.outPoint;
        il.parent = nl;                                   // AE가 월드 변환 보존하며 페어런팅
        if (prevParent) { nl.parent = prevParent; }
        nl.moveAfter(il);                                 // 씬 그룹 안에 머무르게
        var sp = nl.property("Scale");
        var half = 0.6;                                   // 반주기 0.6s
        sp.setValueAtTime(t0, [100, 100]);
        sp.setValueAtTime(Math.min(tEnd, t0 + half), [100, 100 + amt]);
        try {                                             // easy ease 양 키
            var ez = new KeyframeEase(0, 33.34);
            sp.setTemporalEaseAtKey(1, [ez, ez], [ez, ez]);
            sp.setTemporalEaseAtKey(2, [ez, ez], [ez, ez]);
        } catch (e) { }
        try { sp.expression = 'loopOut("pingpong")'; } catch (e) { }
        return nl;
    }

    function applyMoves(comp, il, layer, sceneStart, sceneDur, cw, ch, fps) {
        var moves = layer.moves;
        if (!moves || !moves.length) return;
        var P = il.property("Position").value;
        var S = il.property("Scale").value;
        for (var mi = 0; mi < moves.length; mi++) {
            var mv = moves[mi];
            var t0 = sceneStart + Math.max(0, mv.start || 0);
            var t1 = Math.min(sceneStart + sceneDur, t0 + (mv.duration || 0.5));
            if (t1 <= t0) continue;
            var amt = mv.amount;
            try {
                if (mv.type === "slide_in") {
                    var dx = 0, dy = 0, off = amt || cw * 0.18;
                    if (mv.direction === "right") dx = off; else if (mv.direction === "up") dy = -off;
                    else if (mv.direction === "down") dy = off; else dx = -off;
                    var pp = il.property("Position");
                    pp.setValueAtTime(t0, [P[0] + dx, P[1] + dy]);
                    pp.setValueAtTime(t1, [P[0], P[1]]);
                    if (!mv.noFade) {                        // 캐릭터(noFade)는 오퍼시티 키프레임 금지
                        var op0 = il.property("Opacity");
                        op0.setValueAtTime(t0, 0); op0.setValueAtTime(t0 + (t1 - t0) * 0.5, 100);
                    }
                } else if (mv.type === "fade_in") {
                    var op1 = il.property("Opacity");
                    op1.setValueAtTime(t0, 0); op1.setValueAtTime(t1, 100);
                } else if (mv.type === "exit_fade") {
                    var op2 = il.property("Opacity");
                    op2.setValueAtTime(t0, 100); op2.setValueAtTime(t1, 0);
                } else if (mv.type === "pop") {
                    var sp = il.property("Scale");
                    sp.setValueAtTime(t0, [S[0] * 0.6, S[1] * 0.6]);
                    sp.setValueAtTime(t0 + (t1 - t0) * 0.7, [S[0] * 1.06, S[1] * 1.06]);
                    sp.setValueAtTime(t1, [S[0], S[1]]);
                } else if (mv.type === "zoom_emphasis") {
                    var sp2 = il.property("Scale");
                    sp2.setValueAtTime(t0, [S[0], S[1]]);
                    sp2.setValueAtTime(t0 + (t1 - t0) * 0.5, [S[0] * 1.08, S[1] * 1.08]);
                    sp2.setValueAtTime(t1, [S[0], S[1]]);
                } else if (mv.type === "drift") {
                    var d2 = amt || 18;
                    var pd = il.property("Position");
                    pd.setValueAtTime(t0, [P[0], P[1]]);
                    pd.setValueAtTime(t1, [P[0] + d2, P[1] - d2 * 0.4]);
                } else if (mv.type === "bob") {
                    if (layer.foot) {                     // 발밑 피벗 null 스쿼시 루프(우월 경로)
                        addBobNull(comp, il, layer, t0, (amt && amt <= 5 ? amt : 1), sceneStart + sceneDur);
                    } else {                              // foot 없으면 구식 y 진동 폴백
                        var b2 = amt || 8, pb = il.property("Position");
                        var steps = Math.max(2, Math.floor((t1 - t0) / 0.6));
                        for (var bi = 0; bi <= steps; bi++) {
                            var tb = t0 + (t1 - t0) * bi / steps;
                            pb.setValueAtTime(tb, [P[0], P[1] + ((bi % 2) ? -b2 : 0)]);
                        }
                    }
                } else if (mv.type === "shake") {
                    var s2 = amt || 10, ps = il.property("Position");
                    for (var si2 = 0; si2 <= 6; si2++) {
                        var ts = t0 + (t1 - t0) * si2 / 6;
                        ps.setValueAtTime(ts, [P[0] + ((si2 % 2) ? s2 : -s2) * (1 - si2 / 6), P[1]]);
                    }
                } else if (mv.type === "stamp") {
                    // 도장 — 크게서 제 크기로 5프레임 내리찍기. SEMOJI 도장효과의 타격부.
                    // 잔상 복제본은 결정적 재빌드와 충돌해 생략(설계 문서 결정 2).
                    var m0 = (amt && amt > 100) ? amt : 300;
                    var hit = t0 + 5 / (fps || 30);
                    var sst = il.property("Scale");
                    sst.setValueAtTime(t0, [S[0] * m0 / 100, S[1] * m0 / 100]);
                    sst.setValueAtTime(hit, [S[0], S[1]]);
                    if (!mv.noFade) {                        // 캐릭터(noFade)는 오퍼시티 키프레임 금지
                        var ost = il.property("Opacity");
                        ost.setValueAtTime(t0, 0);
                        ost.setValueAtTime(hit, 100);
                    }
                    try {
                        var ezs = new KeyframeEase(0, 33.34);
                        sst.setTemporalEaseAtKey(sst.nearestKeyIndex(hit), [ezs, ezs], [ezs, ezs]);
                    } catch (eSt) { }
                } else if (mv.type === "wiggle") {
                    // 위글 — 익스프레션이라 레이어 수명 전체에 걸린다(구간 제어는 범위 밖).
                    var wa = amt || 8;
                    try { il.property("Position").expression = "wiggle(1, " + wa + ")"; } catch (eWg) { }
                }
            } catch (e) { /* 모션 1개 실패는 무시 — 빌드 지속 */ }
        }
    }

    // Final 씬 레이어 카메라 — slow zoom/pan(결정적)
    // 카메라 이징 — 도착 키에 붙은 ease가 그 직전 구간의 성격을 정한다.
    // "ease"=양쪽 33.34, "70:30"=이전 키 나감 70 / 이 키 들어옴 30(속도 0 — 툭 출발·툭 멈춤 방지).
    // dims: Scale은 2, Position(공간 속성)은 1 — AE가 요구하는 이징 배열 길이가 다르다.
    function akCamEase(prop, keyTime, outInf, inInf, dims) {
        try {
            var ki = prop.nearestKeyIndex(keyTime);
            var eIn = [], eOut = [], d;
            for (d = 0; d < dims; d++) { eIn.push(new KeyframeEase(0, inInf)); }
            prop.setTemporalEaseAtKey(ki, eIn, eIn);
            if (ki > 1) {
                for (d = 0; d < dims; d++) { eOut.push(new KeyframeEase(0, outInf)); }
                prop.setTemporalEaseAtKey(ki - 1, eOut, eOut);
            }
        } catch (e) { }
    }

    // 가이드 널 카메라 — 매니페스트가 구운 키 [{t, scale, position, ease?}]를 그대로 찍는다.
    // 좌표·배율 계산은 백엔드(camera_keys)가 이미 끝냈다. 같은 값 연속 키 = 정지 구간.
    function applyCamera(guide, keys, sceneStart) {
        if (!keys || !keys.length) return;
        try {
            var sp = guide.property("Scale");
            var pp = guide.property("Position");
            var i, k, tt;
            for (i = 0; i < keys.length; i++) {
                k = keys[i];
                tt = sceneStart + (k.t || 0);
                sp.setValueAtTime(tt, [k.scale, k.scale]);
                pp.setValueAtTime(tt, [k.position[0], k.position[1]]);
            }
            for (i = 0; i < keys.length; i++) {
                k = keys[i];
                if (!k.ease || k.ease === "linear") { continue; }
                tt = sceneStart + (k.t || 0);
                var outInf = 70, inInf = 30;             // 기본 70:30
                if (k.ease === "ease") { outInf = 33.34; inInf = 33.34; }
                akCamEase(sp, tt, outInf, inInf, 2);
                akCamEase(pp, tt, outInf, inInf, 1);
            }
        } catch (e) { }
    }

    // 출처 자막 — 우하단 검정 판(60%) + 흰 텍스트. SEMOJI 출처자막 구조.
    // 판 폭은 텍스트 폭 + 50px을 따라간다(익스프레션). 가이드에 페어런팅하지 않는다 —
    // 카메라 줌이 출처 표기까지 키우면 안 된다. 접두사 덕에 재빌드 시 함께 지워진다.
    function addSourceCaption(comp, s, W, H) {
        var pf = s.prefix || "S00_";
        var t0 = s.start || 0;
        var t1 = t0 + (s.duration || 5);
        var mx = W * 0.03;                                // 우측 여백 3%

        var plate = comp.layers.addShape();
        plate.name = pf + "출처판";
        var grp = plate.property("Contents").addProperty("ADBE Vector Group");
        var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
        var fillP = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fillP.property("Color").setValue([0, 0, 0]);
        plate.property("Opacity").setValue(60);
        plate.inPoint = t0; plate.outPoint = t1;

        var textL = comp.layers.addText(String(s.source));
        textL.name = pf + "출처";
        var tp = textL.property("Source Text");
        var doc = tp.value;
        doc.fontSize = 24;
        doc.fillColor = [1, 1, 1];
        try { if (TK.fonts && TK.fonts.subtitle) { doc.font = TK.fonts.subtitle; } } catch (eF) { }
        try { doc.justification = ParagraphJustification.CENTER_JUSTIFY; } catch (eJ) { }
        tp.setValue(doc);
        textL.inPoint = t0; textL.outPoint = t1;

        // 판 크기 — 텍스트 폭을 따라가는 익스프레션(SEMOJI 그대로)
        try {
            rect.property("Size").expression =
                'var t = thisComp.layer("' + textL.name + '");\n' +
                'var w = t.sourceRectAtTime(time, false).width;\n' +
                '[w + 50, 50]';
        } catch (eX) { }

        // 텍스트 앵커 중앙 → 판 중앙과 겹치게 우하단 배치
        var tw = 0;
        try {
            var tb = textL.sourceRectAtTime(t0, false);
            textL.property("Anchor Point").setValue([tb.left + tb.width / 2, tb.top + tb.height / 2]);
            tw = tb.width;
        } catch (eA) { }
        // 판 우변이 W-mx에 오도록 중심을 안쪽으로 당긴다 — 폭의 절반만큼 왼쪽으로.
        // (판 폭 익스프레션 [w+50, 50]과 동일한 폭을 정적으로 계산해 위치를 잡는다.
        //  출처 텍스트는 빌드 후 바뀌지 않으므로 정적 계산으로 충분하다.)
        var px = W - mx - (tw + 50) / 2;
        var py = H - mx;
        plate.property("Position").setValue([px, py]);
        textL.property("Position").setValue([px, py]);
        textL.parent = plate;                              // 판이 움직이면 텍스트가 따라간다
        return plate;
    }

    // 씬 하나를 평면 컴프에 놓는다. 쌓임은 위에서 아래로 요소 → 배경 → 판 → 가이드 널.
    // comp.layers.add는 맨 위에 넣으므로 가이드부터 거꾸로 추가하면 그 순서가 나온다.
    function buildSceneGroup(proj, comp, s, W, H, log, fps) {
        var pf = s.prefix || "S00_";
        var t0 = s.start || 0;
        var dur = s.duration || 5;
        var t1 = t0 + dur;

        var guide = comp.layers.addNull();
        guide.name = s.prefix + "가이드";
        guide.property("Position").setValue([W / 2, H / 2]);
        guide.inPoint = t0; guide.outPoint = t1;

        if (s.bgFill) {                                   // 좌우 여백 — 테마 배경색으로
            var c = TK.colors.bgRgb;
            var fill = comp.layers.addSolid([c[0] / 255, c[1] / 255, c[2] / 255], pf + "판", W, H, 1.0);
            fill.inPoint = t0; fill.outPoint = t1;
            fill.parent = guide;
        }

        var isLayoutScene = s.layout && s.layout !== "cinematic";
        if (isLayoutScene) {
            var beforeL = comp.numLayers;
            try { renderLayout(proj, comp, s, W, H); }
            catch (eL) { log.push(pf + "레이아웃 렌더 실패 " + eL.toString()); }
            akTagGroup(comp, comp.numLayers - beforeL, pf, guide, t0, t1);
        }

        if (s.layers && s.layers.length) {
            for (var li = 0; li < s.layers.length; li++) {
                var lay = s.layers[li];
                var il = addLayerObj(proj, comp, lay, W, H);
                if (!il) { log.push(pf + "레이어 누락 " + (lay.aeName || lay.name)); continue; }
                il.name = lay.aeName || lay.name;
                il.inPoint = t0; il.outPoint = t1;
                il.parent = guide;
                if (lay.moves) { applyMoves(comp, il, lay, t0, dur, W, H, fps); }
                var top = il;                             // 까딱까딱 널이 끼면 그 널이 가이드의 자식
                while (top.parent && top.parent !== guide) { top = top.parent; }
                if (top !== guide && !top.parent) { top.parent = guide; }
            }
        }
        // 도해의 라벨·기호·도장 — AE 텍스트 레이어로 올린다. 이미지에 구워
        // 버리면 고칠 수도 옮길 수도 없다. 요소는 위에서 레이어로 올라갔다.
        if (s.infoTexts && s.infoTexts.length) {
            for (var ti = 0; ti < s.infoTexts.length; ti++) {
                var tx = s.infoTexts[ti];
                var isStamp = (tx.style === "stamp");
                var rgb = isStamp ? [198, 40, 40]
                    : (tx.accent ? TK.colors.accentRgb : TK.colors.inkRgb);
                var tl2 = null;
                try {
                    tl2 = addTextL(comp, tx.text, {
                        x: tx.position[0], y: tx.position[1],
                        size: tx.size || 30, rgb: rgb, font: TK.fonts.body
                    });
                } catch (eT) { log.push(pf + "도해 글자 실패 " + eT.toString()); continue; }
                tl2.name = pf + "info_" + (isStamp ? "stamp_" : "text_") + ti;
                tl2.inPoint = t0; tl2.outPoint = t1;
                tl2.parent = guide;
                if (isStamp) {
                    // 붉은 둥근 네모 — 도장이 찍혔다는 것 자체가 「찾아봤다」는 뜻이다
                    try {
                        var rc2 = tl2.sourceRectAtTime(0, false);
                        var bw = rc2.width + 44, bh = rc2.height + 28;
                        var sl2 = comp.layers.addShape();
                        sl2.name = pf + "info_stampbox_" + ti;
                        var g2 = sl2.property("Contents").addProperty("ADBE Vector Group");
                        var r2 = g2.property("Contents").addProperty("ADBE Vector Shape - Rect");
                        r2.property("Size").setValue([bw, bh]);
                        try { r2.property("Roundness").setValue(14); } catch (eR) { }
                        var st2 = g2.property("Contents").addProperty("ADBE Vector Graphic - Stroke");
                        st2.property("Color").setValue([198 / 255, 40 / 255, 40 / 255]);
                        st2.property("Stroke Width").setValue(6);
                        sl2.property("Position").setValue([tx.position[0], tx.position[1]]);
                        sl2.inPoint = t0; sl2.outPoint = t1;
                        sl2.parent = guide;
                        sl2.moveAfter(tl2);
                    } catch (eS) { log.push(pf + "도장 테두리 실패 " + eS.toString()); }
                }
            }
        }
        // 레이아웃 씬도 **그림이 있으면 배경으로 깐다.** v3 의 timeline·flow·
        // items_list 는 도해만 있는 화면이 아니라, 씬 그림 위에 항목이 얹히는
        // 구조다. isLayoutScene 으로 막아 두어 컴프에서 배경이 통째로 빠졌다.
        if (!(s.layers && s.layers.length) && s.image) {
            var one = addLayerObj(proj, comp, {
                path: s.image,
                position: (s.imageFit || {}).position,
                scale: (s.imageFit || {}).scale
            }, W, H);
            if (one) {
                one.name = pf + "이미지";
                one.inPoint = t0; one.outPoint = t1;
                one.parent = guide;
            } else { log.push(pf + "image 누락"); }
        }

        if (s.mapGeo) {
            var beforeM = comp.numLayers;
            try { renderMapOverlay(comp, s.mapGeo, W, H, dur); }
            catch (eMap) { log.push(pf + "지도 오버레이 실패 " + eMap.toString()); }
            akTagGroup(comp, comp.numLayers - beforeM, pf, guide, t0, t1);
        }

        if (s.source) {
            try { addSourceCaption(comp, s, W, H); }
            catch (eSrc) { log.push(pf + "출처 자막 실패 " + eSrc.toString()); }
        }

        if (s.audio) {
            var aF = new File(s.audio);
            if (aF.exists) {
                var al = comp.layers.add(proj.importFile(new ImportOptions(aF)));
                al.name = pf + "음성";
                al.startTime = t0;                        // 이것이 없으면 0초부터 재생된다
                al.inPoint = t0; al.outPoint = t1;
            }
        }

        if (s.camera && s.camera.length) { applyCamera(guide, s.camera, t0); }
        return guide;
    }
    try {
        var mf = new File(manifestPath);
        if (!mf.exists) { return "ERROR: manifest 없음: " + manifestPath; }
        mf.open("r"); var raw = mf.read(); mf.close();
        var m = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");

        // ae_tokens 로드(있으면 기본 토큰 덮어쓰기) — 실패해도 내장 기본값으로 진행
        try {
            if (m.ae_tokens) {
                var tf = new File(m.ae_tokens);
                if (tf.exists) {
                    tf.open("r"); var tr = tf.read(); tf.close();
                    var tj = (typeof JSON === "object" && JSON.parse) ? JSON.parse(tr) : eval("(" + tr + ")");
                    if (tj.colors) TK.colors = tj.colors;
                    if (tj.fonts) TK.fonts = tj.fonts;
                    if (tj.type) TK.type = tj.type;
                    if (tj.families) TK.families = tj.families;
                }
            }
        } catch (eTk) { }

        // 프로젝트 테마 색 오버라이드(manifest.themeColors) — ae_tokens 로드 여부와 무관하게 항상 적용
        if (m.themeColors) {
            for (var ck in m.themeColors) { TK.colors[ck] = m.themeColors[ck]; }
        }

        // 폰트 PS명을 AE 폰트 DB 기준으로 검증/보정(패밀리 키워드 + 굵기 힌트)
        try {
            var FAM = TK.families || {};
            var HINT = { body: "Medium", subtitle: "Medium", bold: "Bold" };
            for (var fk in TK.fonts) {
                if (fk === "fallback" || !TK.fonts[fk]) continue;
                TK.fonts[fk] = resolveFontPS(TK.fonts[fk], FAM[fk], HINT[fk]);
            }
        } catch (eF) { }

        var W = m.width || 1920, H = m.height || 1080, FPS = m.fps || 30;
        var scenes = m.scenes || [];
        if (!scenes.length) { return "ERROR: scenes 비어있음"; }

        app.beginUndoGroup("auto_kairos PoC build");
        var proj = app.project || app.newProject();

        var log = [];
        var endT = 0;
        for (var ei = 0; ei < scenes.length; ei++) {
            var se = (scenes[ei].start || 0) + (scenes[ei].duration || 5);
            if (se > endT) { endT = se; }
        }
        var comp = akFindOrMakeComp(proj, "Final", W, H, FPS, endT);

        for (var i = 0; i < scenes.length; i++) {
            var s = scenes[i];
            akRemoveSceneGroup(comp, s.prefix);           // 재빌드 — 지우고 다시 넣는다
            var before = comp.numLayers;
            try { buildSceneGroup(proj, comp, s, W, H, log, FPS); }
            catch (eB) {
                log.push((s.prefix || "") + "빌드 실패 " + eB.toString());
                // 실패해도 이미 만들어진 레이어는 남는다 — 접두사를 붙여 두지 않으면
                // 다음 재빌드의 akRemoveSceneGroup이 못 지워 컴프에 영원히 쌓인다.
                var madeErr = comp.numLayers - before;
                if (madeErr > 0) {
                    akTagGroup(comp, madeErr, s.prefix || "S00_", null,
                               s.start || 0, (s.start || 0) + (s.duration || 5));
                }
                continue;
            }
            var made = comp.numLayers - before;
            var group = [];                               // 인덱스는 옮기는 즉시 밀리므로 참조를 먼저 모은다
            for (var k = 1; k <= made && k <= comp.numLayers; k++) { group.push(comp.layer(k)); }
            var anchor = akGroupAnchor(comp, scenes, i);  // 다음 씬 그룹 위로 옮긴다
            if (anchor) {
                // 위에서부터 차례로 anchor 바로 위에 놓으면 그룹 안 순서가 그대로 유지된다
                for (var g = 0; g < group.length; g++) { group[g].moveBefore(anchor); }
            }
        }
        // 말자막(subtitle_layers.jsx)이 씬 그룹 아래로 깔리는 것을 막는다.
        // 씬 그룹 재배치는 위에서 다음 씬 그룹 위로만 옮기므로, 그룹이 없는 부분 빌드나
        // 마지막 씬은 최상단에 남는다 — 그러면 그 아래 자막이 불투명 배경에 가려진다.
        // 자막 레이어(이름 "말자막")를 마지막에 다시 최상단으로 올려 항상 보이게 한다.
        for (var subI = 1; subI <= comp.numLayers; subI++) {
            if (comp.layer(subI).name === "말자막") { comp.layer(subI).moveToBeginning(); break; }
        }
        comp.openInViewer();
        app.endUndoGroup();

        return "OK: 씬 " + scenes.length + "개 → Final(" + endT + "s)" +
               (log.length ? " | " + log.join(", ") : "") +
               (FONT_WARN.length ? " | 폰트: " + FONT_WARN.join(", ") : "");
    } catch (e) {
        return "ERROR: " + e.toString();
    }
}
