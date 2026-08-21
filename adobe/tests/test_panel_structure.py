from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
HTML = PANEL / "index.html"
NAV = PANEL / "js" / "nav.js"
MAIN = PANEL / "js" / "main.js"


def test_index_has_two_views():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="view-list"' in html
    assert 'id="view-detail"' in html
    # 상세 뷰는 초기 숨김
    assert 'id="view-detail" hidden' in html or 'id="view-detail"  hidden' in html


def test_index_has_detail_header_and_back():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="detailTitle"' in html
    assert 'id="btnBackToList"' in html


def test_index_has_tabs():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="btnTabPlanning"', 'id="btnTabStoryboard"',
               'id="tab-planning"', 'id="tab-storyboard"']:
        assert el in html, el


def test_index_has_chat_dock():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="chat-dock"', 'id="chatInput"', 'id="btnChatSend"']:
        assert el in html, el


def test_index_has_taskbar():
    assert 'id="task-bar"' in HTML.read_text(encoding="utf-8")


def test_index_has_responsive_media_query():
    assert "@media" in HTML.read_text(encoding="utf-8")


def test_existing_controls_present_in_detail():
    # 기존 버튼 ID 보존(바인딩 깨짐 방지)
    html = HTML.read_text(encoding="utf-8")
    for bid in ['id="btnDecompose"', 'id="btnGenCharacter"',
                'id="btnRefList"', 'id="btnGenStoryboard"',
                'id="btnBuild"', 'id="btnCreate"', 'id="btnProjects"']:
        assert bid in html, bid


def test_nav_defines_functions():
    nav = NAV.read_text(encoding="utf-8")
    for fn in ["function enterProject", "function exitProject", "function switchTab"]:
        assert fn in nav, fn


def test_main_calls_enterProject():
    assert "enterProject(" in MAIN.read_text(encoding="utf-8")


def test_existing_result_boxes_wired():
    # checkBackend/buildComp가 쓰는 박스가 실제 존재 + main.js 참조 일치(레거시 #status 잔존 금지)
    html = HTML.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    # 백엔드 상태등(초록/빨강 점) + 연결 버튼 + AE 결과 박스
    assert 'id="healthDot"' in html and 'id="healthText"' in html and 'id="btnReconnect"' in html
    assert 'id="aeresult"' in html
    assert '$("status")' not in main   # 레거시 #status 잔존 금지


def test_planning_tab_has_file_viewer():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="btnReloadFiles"', 'id="planFiles"', 'id="planEdit"']:
        assert el in html, el
    # 임시 원고보기 버튼/박스는 제거됨
    assert 'id="btnManuscript"' not in html
    assert 'id="manuscript"' not in html


def test_index_loads_planning_js():
    assert 'src="js/planning.js"' in HTML.read_text(encoding="utf-8")


def test_storyboard_tab_has_sheet():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sheet"' in html and 'id="btnLoadSheet"' in html
    assert 'src="js/storyboard.js"' in html


def test_storyboard_js_defines_loadSheet():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadSheet" in js


def test_gallery_panel_present():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="gallery-panel"', 'id="galSearch"', 'id="galEngine"',
               'id="btnGalSearch"', 'id="btnGalRefresh"', 'src="js/gallery.js"']:
        assert el in html, el


def test_storyboard_js_has_drop_handler():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function dropOnScene" in js and "set-image" in js


def test_storyboard_js_has_unlink():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function unlinkScene" in js and "unlink-image" in js


def test_storyboard_2pane():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="sb-2pane"', 'id="sb-left"', 'id="sb-right"', 'id="sb-toolbar"', 'id="btnOpenGenModal"']:
        assert el in html, el


def test_storyboard_preserves_legacy_ids():
    html = HTML.read_text(encoding="utf-8")
    for bid in ['id="btnDecompose"', 'id="btnRefList"', 'id="btnGenStoryboard"',
                'id="btnBuild"', 'id="btnGenCharacter"',
                'id="btnRefreshCharacters"', 'id="btnGalRefresh"', 'id="btnGalSearch"',
                'id="sheet"', 'id="gallery-panel"', 'id="scenes"', 'id="aeresult"']:
        assert bid in html, bid


def test_storyboard_js_has_layer_analysis():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function analyzeLayers" in js and "analyze-layers" in js and "split-layers" in js


def test_genmodal_present():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="genModal"', 'id="genCategory"', 'id="genPrompt"', 'id="genSubmit"',
               'id="genScene"', 'src="js/genmodal.js"']:
        assert el in html, el


def test_storyboard_js_has_scene_ops():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function sceneOp" in js and "sa-split" in js and "sa-merge" in js   # 도구상자
    assert "work-dots" in js     # 진행 점(뱃지 대체)


def test_build_scene_jsx_handles_layers():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "s.layers" in jsx and "addLayerObj" in jsx and "position" in jsx


def test_storyboard_js_has_tts():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function genTts" in js and "/api/scenes/tts" in js


def test_main_js_assembly_uses_manifest():
    js = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert "/api/assembly/manifest" in js and "akBuildScene" in js


def test_assistant_js_wired():
    js = (PANEL / "js" / "assistant.js").read_text(encoding="utf-8")
    assert "function sendChat" in js and "/api/assistant" in js


def test_index_loads_assistant_js():
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert "js/assistant.js" in html and 'id="chatInput"' in html
    assert "disabled" not in html.split('id="chatInput"')[1].split(">")[0]   # 입력 활성화


def test_llm_selector():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="llmSelect"' in html
    assert "function loadLlmSetting" in MAIN.read_text(encoding="utf-8") and "/api/llm/settings" in MAIN.read_text(encoding="utf-8")


def test_tts_settings_panel():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadTtsSettings" in js and "/api/tts/settings" in js
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'id="ttsStyle"' in html and 'id="ttsVoiceId"' in html


def test_first_screen_auto_health_and_projects():
    html = HTML.read_text(encoding="utf-8")
    main = MAIN.read_text(encoding="utf-8")
    assert 'id="btnNewProject"' in html and 'id="newProjectForm"' in html
    assert "checkBackend();" in main                 # 열면 자동 호출
    assert "_setHealth" in main and "loadProjects()" in main
    assert ".proj-item" in main                       # 가독 카드형 목록


def test_tts_custom_player_and_scene_comp():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "tts-player" in js and "function _bindTtsPlayer" in js and "tts-dur" in js
    assert "sa-comp" in js                             # 도구상자 컴프 버튼
    main = MAIN.read_text(encoding="utf-8")
    assert "function buildSceneComp" in main and "function _assemble" in main


def test_buildall_button_and_full_comp():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnBuildAll"' in html
    assert "btnBuildAll" in MAIN.read_text(encoding="utf-8")


def test_gallery_select_import():
    js = (PANEL / "js" / "gallery.js").read_text(encoding="utf-8")
    assert "function importSelectedToProject" in js and "btnGalImport" in js


def test_storyboard_no_double_plus_concat():
    # '+   + ' 이중 플러스 = 단항 플러스로 문자열이 NaN 되는 버그 패턴(재발 방지)
    import re
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    bad = [ln for ln in js.splitlines() if re.match(r"\s*\+\s+\+\s", ln)]
    assert not bad, "이중 + 연결 발견(단항 플러스 NaN 위험): " + repr(bad[:3])


def test_storyboard_tts_player_renders_without_nan():
    # renderRow를 node로 실행해 TTS 플레이어 HTML이 NaN 없이 생성되는지 검증
    import subprocess, json
    sb = str(PANEL / "js" / "storyboard.js")
    script = (
        "global.window={localStorage:{getItem:function(){return null;},setItem:function(){}}};"
        "global.document={getElementById:function(){return null;},addEventListener:function(){}};"
        "eval(require('fs').readFileSync(" + json.dumps(sb) + ",'utf8'));"
        "var s={sceneNumber:1,sceneId:'x',title:'t',narration:'n',_image:'storyboard/a.png',"
        "_layers:[],_audio:'audio/tts_x.mp3',_audio_dur:13.5,"
        "_status:{narration:true,image:true,layers:false,tts:true},characters:[]};"
        "var h=renderRow(s,'/p');"
        "process.stdout.write(JSON.stringify({nan:h.indexOf('NaN')>=0,play:h.indexOf('>\\u25b6<')>=0,player:h.indexOf('tts-player')>=0}));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    res = json.loads(out.stdout)
    assert res["player"] and res["play"] and not res["nan"], (out.stdout, out.stderr)


def test_layer_select_modal():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="layerModal"' in html and 'id="layerList"' in html and 'id="layerSubmit"' in html
    assert 'id="layerTabs"' in html                       # 여러 씬 탭
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "_submitLayerSplit" in js and "_switchLayerTab" in js and "_layerMulti" in js
    assert "한 번에 한 씬만" not in js                      # 단일 제한 해제됨


def test_poll_job_helper_and_async_callers():
    main = MAIN.read_text(encoding="utf-8")
    assert "function _pollJob" in main and "/api/jobs/" in main   # 폴백 유지
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "_awaitJob" in js                     # splitLayers SSE 대기
    a = (PANEL / "js" / "assistant.js").read_text(encoding="utf-8")
    assert "_awaitJob" in a


def test_jsx_scene_comp_no_auto_subtitle():
    # 씬 컴프 자동 자막 제거 — 자막은 Final에 일괄(subtitle_layers.jsx)
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "if (s.subtitle)" not in jsx
    assert "[cw / 2, ch * 0.88]" not in jsx


def test_subtitle_layers_jsx():
    fp = PANEL / "jsx" / "subtitle_layers.jsx"
    assert fp.exists()
    jsx = fp.read_text(encoding="utf-8")
    assert "function akBuildSubtitles" in jsx
    assert "startTime" in jsx and "inPoint" in jsx and "outPoint" in jsx
    assert '"Final"' in jsx and "JSON.parse" in jsx
    # ES3 호환 — const/let/arrow 금지
    assert "=>" not in jsx and "const " not in jsx and "let " not in jsx


def test_ae_tokens_has_subtitle_keys():
    import json
    tk = json.loads((Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json")
                    .read_text(encoding="utf-8"))
    assert tk["type"]["subtitle"] == 54
    assert tk["fonts"]["subtitle"] == "OTSBAggroM"   # 실제 PS명


def test_no_hardcoded_machine_paths_in_panel():
    main = MAIN.read_text(encoding="utf-8")
    assert "/Users/jleavens_macmini" not in main


def test_main_js_escapes_dynamic_html():
    main = MAIN.read_text(encoding="utf-8")
    assert "_esc(p.title" in main            # 프로젝트 제목 이스케이프
    # data-name/data-label 왕복 속성은 encodeURIComponent/decodeURIComponent
    assert 'encodeURIComponent(nm)' in main
    assert 'decodeURIComponent(this.getAttribute("data-name")' in main
    assert "_esc(nm)" in main.split("function showCharacters")[1]


def test_refresh_row_single_scene():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function refreshRow" in js
    assert "bindRows(fresh)" in js                       # 새 행만 스코프 바인딩(중복 리스너 방지)
    assert "function bindRows(scope)" in js
    # 단일 씬 작업(genTts)은 refreshRow 사용
    assert "refreshRow" in js.split("function genTts")[1]


def test_jsx_uses_json_parse():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "JSON.parse" in jsx
    assert (PANEL / "jsx" / "json2.jsx").exists()
    # json2는 ES3 호환(parse만) — const/let/arrow 금지
    j2 = (PANEL / "jsx" / "json2.jsx").read_text(encoding="utf-8")
    assert "JSON.parse" in j2 and "=>" not in j2 and "const " not in j2 and "let " not in j2
    main = MAIN.read_text(encoding="utf-8")
    assert "json2.jsx" in main


def test_jsx_has_motion():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "function applyMoves" in jsx and "function applyCamera" in jsx
    for t in ["slide_in", "pop", "bob", "zoom_emphasis"]:
        assert t in jsx
    # 카메라는 이제 type 분기가 아니라 매니페스트가 구운 키프레임 — camera_keys(manifest.py)가 번역한다
    assert "slow_zoom_in" not in jsx


def test_panel_motion_button():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "sa-motion" in js and "function planMotion" in js and "/api/scenes/motion" in js
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sa-motion"' in html


def test_render_queue_wired():
    assert (PANEL / "jsx" / "render_queue.jsx").exists()
    jsx = (PANEL / "jsx" / "render_queue.jsx").read_text(encoding="utf-8")
    assert "function akQueueRender" in jsx and "renderQueue.items.add" in jsx
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnQueueRender"' in html
    main = MAIN.read_text(encoding="utf-8")
    assert "function queueRender" in main and "render_queue.jsx" in main


def test_v3_import_ui_wired():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnImportV3"' in html and 'id="v3Path"' in html and 'id="v3Status"' in html
    main = MAIN.read_text(encoding="utf-8")
    assert "function importV3" in main and "/api/projects/import-v3" in main
    assert '$("btnImportV3").addEventListener' in main


def test_pipeline_button_wired():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnRunPipeline"' in html and 'id="pipelineStatus"' in html
    pl = (PANEL / "js" / "planning.js").read_text(encoding="utf-8")
    assert "function runPipeline" in pl and "/api/pipeline/run" in pl and "_awaitJob" in pl


def test_sheet_toolbar_and_checkboxes():
    html = HTML.read_text(encoding="utf-8")
    for bid in ['id="sheet-actionbar"', 'id="sa-img"', 'id="sa-layer"', 'id="sa-tts"',
                'id="sa-motion"', 'id="sa-comp"', 'id="sa-del"']:
        assert bid in html, bid
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "scene-sel" in js and "SEL_SCENES" in js and "selAllScenes" in js
    assert "function bindSheetToolbar" in js and "_runSeq" in js
    assert "col-asset" not in js and "work-actions" not in js   # 구 구조 제거


def test_render_row_checkbox_and_dots():
    """renderRow 실행 — 체크박스 + 진행 점 4개 + 버튼 없음(도구상자로 이동)."""
    import subprocess, json
    sb = str(PANEL / "js" / "storyboard.js")
    script = (
        "global.window={localStorage:{getItem:function(){return null;},setItem:function(){}}};"
        "global.document={getElementById:function(){return null;},addEventListener:function(){}};"
        "eval(require('fs').readFileSync(" + json.dumps(sb) + ",'utf8'));"
        "var s={sceneNumber:3,sceneId:'y',title:'t',narration:'n',_image:'storyboard/a.png',"
        "_layers:['layers/y__0.png'],_audio:'audio/tts_y.mp3',_audio_dur:5,"
        "_status:{image:true,layers:true,tts:false,motion:false},characters:[]};"
        "var h=renderRow(s,'/p');"
        "process.stdout.write(JSON.stringify({"
        "chk:h.indexOf('scene-sel')>=0,"
        "dots:(h.match(/dot (on|off)/g)||[]).length===4,"
        "on:(h.match(/dot on/g)||[]).length===2,"
        "noBtn:h.indexOf('gen-img')<0&&h.indexOf('scene-comp')<0,"
        "player:h.indexOf('tts-player')>=0&&h.indexOf('NaN')<0}));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    res = json.loads(out.stdout)
    assert res["chk"] and res["dots"] and res["on"] and res["noBtn"] and res["player"], out.stdout


def test_composite_preview_and_text_buttons():
    """오버레이는 없어졌고 대체물은 renderComposite 합성 미리보기(comp-bg/comp-el) —
    실제로 배경을 깔고 눈 끈/제거된 레이어는 그리지 않는지 검사한다."""
    import subprocess, json
    sb = str(PANEL / "js" / "storyboard.js")
    script = (
        "global.window={localStorage:{getItem:function(){return null;},setItem:function(){}}};"
        "global.document={getElementById:function(){return null;},addEventListener:function(){}};"
        "eval(require('fs').readFileSync(" + json.dumps(sb) + ",'utf8'));"
        "var s={sceneNumber:9,sceneId:'z',_image:'storyboard/z.png',"
        "_layers:['layers/z__bg.png','layers/z__0_car.png','layers/z__1_hidden.png','layers/z__2_removed.png'],"
        "_layer_meta:{"
        "'z__bg':{kind:'bg',z:0},"
        "'z__0_car':{kind:'element',z:1,box:{left:10,top:20,width:30}},"
        "'z__1_hidden':{kind:'element',z:2,hidden:true},"
        "'z__2_removed':{kind:'element',z:3,removed:true}"
        "}};"
        "var comp=renderComposite(s,'/p');"
        "process.stdout.write(JSON.stringify({"
        "bg:comp.indexOf('comp-bg')>=0&&comp.indexOf('z__bg.png')>=0,"
        "el:comp.indexOf('comp-el')>=0&&comp.indexOf('z__0_car.png')>=0,"
        "box:comp.indexOf('left:10%;top:20%;width:30%')>=0,"
        "noHidden:comp.indexOf('z__1_hidden.png')<0,"
        "noRemoved:comp.indexOf('z__2_removed.png')<0}));"
    )
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True)
    res = json.loads(out.stdout)
    assert res["bg"] and res["el"] and res["box"] and res["noHidden"] and res["noRemoved"], out.stdout

    html = HTML.read_text(encoding="utf-8")
    assert ">씬 추가<" in html and ">병합<" in html and ">삭제<" in html   # 구조 버튼은 텍스트


def test_jsx_bob_null_pivot():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "function addBobNull" in jsx and "addNull" in jsx
    assert 'loopOut("pingpong")' in jsx and "KeyframeEase" in jsx
    assert "il.parent = nl" in jsx and "layer.foot" in jsx


def test_jsx_no_auto_fade():
    """자동 페이드(배경 오퍼시티 0→100) 금지 — 모든 모션은 모션 플랜에서만."""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "li === 0" not in jsx
    assert "function addLayerObj(proj, comp, layer, W, H)" in jsx   # fade 파라미터 제거


def test_sse_push_wired():
    main = MAIN.read_text(encoding="utf-8")
    assert "EventSource" in main and "/api/events" in main
    assert "function _awaitJob" in main and "function connectEvents" in main
    assert "connectEvents();" in main                      # 연결 시 SSE 구독
    # 호출부는 _awaitJob 사용(폴링은 폴백)
    for f in ["storyboard.js", "assistant.js", "planning.js"]:
        js = (PANEL / "js" / f).read_text(encoding="utf-8")
        assert "_awaitJob(j.job_id" in js, f


def test_build_scene_jsx_layout_renderers():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "function renderLayout" in jsx
    assert "function addBgSolid" in jsx and "function addTextL" in jsx and "function addRectL" in jsx
    assert "ae_tokens" in jsx                              # 토큰 로드
    # 평면 컴프에서 레이아웃 씬은 buildSceneGroup이 실제로 renderLayout을 호출해 배선한다
    # (cinematic이 아닌 레이아웃 씬만 — 이미지 씬은 renderLayout을 타지 않는다).
    assert "function buildSceneGroup" in jsx
    assert 's.layout && s.layout !== "cinematic"' in jsx
    assert "try { renderLayout(proj, comp, s, W, H); }" in jsx
    # 레이아웃 5종 렌더러는 layouts.jsx로 이동(Task 5)
    layouts = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    for l in ("headline_only", "items_list", "metric_spotlight", '"bar"', '"quote"'):
        assert l in layouts, l
    assert "Anchor Point" in jsx                            # 막대 하단 고정 성장(addBarShape는 build_scene.jsx에 남음)


def test_storyboard_comp_preview():
    """시트 미리보기 — 레이아웃 미러 렌더(_previewHTML) + 자막 오버레이 + 토큰 로드."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "_previewHTML" in js and "pv-subtitle" in js
    assert "/api/tokens" in js                                # AE 빌드와 동일 토큰 소스
    for layout in ("headline_only", "items_list", "metric_spotlight", "bar", "quote"):
        assert layout in js
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert ".pv " in html or ".pv {" in html
    assert ".pv-subtitle" in html and ".pv-quote" in html


def test_subtitles_button_wired():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnSubtitles"' in html
    main = MAIN.read_text(encoding="utf-8")
    assert "function buildSubtitles" in main and "/api/subtitles/build" in main
    assert "subtitle_layers.jsx" in main and "akBuildSubtitles" in main
    assert '$("btnSubtitles").addEventListener' in main


def test_jsx_typography_upgrade():
    """폰트 폴백 체인·줄바꿈 박스·해상도 스케일 적용."""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "addBoxText" in jsx                            # 자동 줄바꿈
    assert "td.font === chain[fi]" in jsx                 # 폰트 적용 검증(폴백 체인)
    assert "var S = W / 1920" in jsx                      # 1080p 기준 해상도 배율
    assert "leading" in jsx
    import json
    tk = json.loads((PANEL.parents[1] / "data" / "artstyle" / "ae_tokens.json").read_text(encoding="utf-8"))
    assert tk["fonts"]["body"] == "OTSBAggroM"            # 실제 PostScript 이름
    assert tk["fonts"]["headline"] == "Cafe24Ssurround"


def test_map_scene_wiring():
    """지도 씬 — vendor maplibre 로드 + mapgen.js + 도구상자 버튼 + 좌표 swap."""
    html = HTML.read_text(encoding="utf-8")
    assert "vendor/maplibre-gl.js" in html and 'id="sa-map"' in html
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "preserveDrawingBuffer" in mg            # 캔버스 캡처 필수 옵션
    assert "_swapLL" in mg                          # [위도,경도] → [경도,위도]
    assert "/api/scenes/map-image" in mg
    # v3 맵 테마 이식 — 세모지 기본 warm_earth + 오버라이드 적용
    assert "warm_earth" in mg and "_applyOverrides" in mg and "clean_white" in mg
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "sa-map" in js and "genMapForScene" in js


def test_map_overlay_native_layers():
    """지도 마커/라벨/경로 — 캔버스에 굽지 않고 AE 네이티브 레이어(jsx) + map.project geo."""
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "map.project" in mg and "labelRgb" in mg          # 픽셀 좌표 + 테마 대비색
    assert "addLayer" not in mg                              # 지도에 마커 굽기 금지
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "function renderMapOverlay" in jsx
    assert "ADBE Vector Filter - Trim" in jsx                # 경로 그리기 애니메이션
    assert "map_marker_" in jsx and "map_label_" in jsx
    # 평면 컴프(Task 3) — buildSceneGroup이 s.mapGeo와 함께 실제로 배선한다.
    assert "if (s.mapGeo)" in jsx
    assert "renderMapOverlay(comp, s.mapGeo, W, H, dur)" in jsx


def test_webgl_enabled_for_map():
    """지도(MapLibre)용 WebGL — CEF 플래그 + mapgen 사전 점검 + 도구상자 상태 표시."""
    mx = (PANEL / "CSXS" / "manifest.xml").read_text(encoding="utf-8")
    assert "--enable-webgl" in mx and "--ignore-gpu-blacklist" in mx
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "webgl" in mg                                     # 사전 점검(명확한 에러)
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sa-status"' in html                          # 시트 도구상자 상태 표시


def test_map_polyfills_for_cep():
    """CEP 구버전 CEF — maplibre v5용 AbortSignal/structuredClone 폴리필."""
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "throwIfAborted" in mg and "AbortSignal.timeout" in mg and "structuredClone" in mg


def test_map_raster_fallback():
    """MapLibre가 CEP에서 타일을 못 그리면 — 라스터 합성 폴백(워커·WebGL 불필요)."""
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "renderMapRaster" in mg and "BLANK_CANVAS" in mg
    assert "_mercPx" in mg                                 # 웹 메르카토르 투영(마커 좌표 일관)
    assert "crossOrigin" in mg                             # 캔버스 오염 방지(CORS)
    assert "basemaps.cartocdn.com" in mg


def test_chart_spec_wiring():
    """chartagent 차트 명세서 — 버튼 + jsx 패턴/가이드선/외곽선 반영."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sa-chart"' in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "sa-chart" in js and "/api/scenes/chart-spec" in js
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "addBarShape" in jsx
    layouts = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    assert "s.chartSpec" in layouts                        # bar 렌더러는 layouts.jsx로 이동(Task 5)
    assert "guideLineCount" in layouts                      # 가이드선 복원(Task 5 fix)
    assert "applyDash" in jsx and "ctx.applyDash" in layouts  # 함수 유지 + 실사용(죽은 코드 아님)
    # 성장 애니메이션 복원 — bar 렌더러가 Anchor Point로 하단 고정 성장한다
    assert "Anchor Point" in layouts
    # 패턴 종류 전부 처리(diagonal/crosshatch/vertical/dot)
    assert "crosshatch_light" in jsx and "vertical_stripe" in jsx and "dot_sparse" in jsx


def test_mapgen_uses_scene_theme():
    """지도 — 씬/프로젝트 resolve된 테마(_theme.map)를 우선 사용(하드코딩 MAP_THEMES는 폴백)."""
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "_theme" in mg
    assert "overrides" in mg and "rasterFilter" in mg


def test_theme_selector_ui():
    """테마 UI — 프로젝트 드롭다운 + 씬 테마 버튼 + 로드 함수."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="projectTheme"' in html
    assert 'id="sa-theme"' in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadThemes" in js and "/api/themes" in js
    assert "/api/themes/set-project" in js and "/api/themes/set-scene" in js


def test_subtitle_single_layer_keyframed():
    """자막은 레이어 1개 + Source Text 키프레임 — 줄마다 레이어를 만들면 AE가 멈춘다.

    줄마다 텍스트 길이가 달라지므로 앵커 보정(sourceRectAtTime) 대신
    가운데 정렬로 수평 위치를 고정한다."""
    jsx = (PANEL / "jsx" / "subtitle_layers.jsx").read_text(encoding="utf-8")
    assert "setValueAtTime" in jsx and "CENTER_JUSTIFY" in jsx
    assert "Anchor Point" in jsx and "Position" in jsx
    assert "akRemoveLegacySubLayers" in jsx          # 예전 줄별 레이어 정리
    assert "comp.layers.addText" in jsx and jsx.count("comp.layers.addText") == 1


def test_preview_hatch_matches_pattern_kind():
    """시트 미리보기 해칭 — patternKind별로 정확히(crosshatch=양방향, vertical=세로, dot=점)."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "crosshatch_light" in js and "-45deg" in js     # 교차(양방향)
    assert "dot_sparse" in js and "radial-gradient" in js  # 점


def test_jsx_flat_comp_reused_not_recreated():
    """jsx — 평면 컴프 전환 이후 skipFinal 분기는 없다. Final은 항상 찾거나 만든다(중복 생성 금지)."""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "skipFinal" not in jsx
    assert "function akFindOrMakeComp" in jsx
    assert 'akFindOrMakeComp(proj, "Final"' in jsx


def test_all_text_anchors_centered():
    """씬 컴프 텍스트 앵커는 sourceRectAtTime 중앙으로 — 베이스라인 어긋남 방지.

    (자막 레이어는 내용이 시간에 따라 바뀌어 고정 앵커를 쓸 수 없다 —
     test_subtitle_single_layer_keyframed 참고.)"""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    # addTextL이 box 유무와 무관하게 sourceRectAtTime으로 앵커 설정
    assert jsx.count("sourceRectAtTime") >= 1
    assert "Anchor Point" in jsx and "rc.left + rc.width / 2" in jsx


def test_kinetic_typo_animator():
    """키네틱 타이포 — Text Animator(Range Selector) 헬퍼 + 레이아웃 기본 anim."""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "_addTextAnim" in jsx
    assert "ADBE Text Animator" in jsx and "ADBE Text Selector" in jsx
    assert "ADBE Text Percent Offset" in jsx          # 셀렉터 오프셋 키프레임
    # 레이아웃이 기본 키네틱 모션을 지정(reveal/slide/type/word_stagger)
    for typ in ("reveal", "slide", "type", "word_stagger"):
        assert typ in jsx, typ
    assert "opts.anim" in jsx                          # addTextL이 anim 옵션 처리
    # Offset 0→100(등장) — -100→0(퇴장) 역방향 금지
    assert "setValueAtTime(t0, 0)" in jsx and "setValueAtTime(t0 + dur, 100)" in jsx
    assert 'setValue(3)' in jsx                         # word_stagger Units=Words(3)


def test_builder_loads_motion_lib():
    """빌더가 motion_presets/font_map/color_tokens 로드 + resolve 함수."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "motion_presets.json" in jsx and "font_map.json" in jsx and "color_tokens.json" in jsx
    assert "function resolveFont" in jsx and "function resolveColor" in jsx


def test_builder_apply_preset():
    """applyPreset가 7 프리셋 분기 + 커스텀 이징."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "function applyPreset" in jsx
    for p in ("type_on", "fade_scale_in", "slide_in", "pop_bounce", "mask_reveal", "tilt_2_5d"):
        assert p in jsx, p
    assert "KeyframeEase" in jsx


def test_builder_apply_detail():
    """applyDetail — shadow/glow/grain 이펙트."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "function applyDetail" in jsx
    assert "ADBE Drop Shadow" in jsx and "ADBE Glo2" in jsx and "ADBE Add Grain" in jsx


def test_builder_routes_preset_font_color():
    """anim.preset → applyPreset, layer.font → resolveFont, detail → applyDetail 라우팅 + 기존 prop 하위호환."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "applyPreset(" in jsx and "applyDetail(" in jsx
    assert "resolveFont(" in jsx and "resolveColor(" in jsx
    assert "an.preset" in jsx


def test_builder_backward_compatible_and_intact():
    """기존 prop 방식(preset 없는 anim)도 동작 + 빌더 괄호 균형."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert 'an.prop === "opacity"' in jsx and 'an.prop === "typeOn"' in jsx
    for o, c in [("{", "}"), ("(", ")"), ("[", "]")]:
        assert jsx.count(o) == jsx.count(c), o + c


def test_cut_bg_token_safe():
    """cut.bg 토큰키가 resolveColor 경유(검정 배경 방지) + hex 비-hex 가드."""
    jsx = (PANEL / "jsx" / "tylenol" / "build_from_json.jsx").read_text(encoding="utf-8")
    assert "resolveColor(cut.bg)" in jsx
    assert "[0-9a-fA-F]" in jsx        # hex 유효성 가드


def test_backend_autostart_on_health_fail():
    """health 실패 시 CEP createProcess로 python3 -m backend.app 자동 스폰 + 재시도."""
    js = MAIN.read_text(encoding="utf-8")
    assert "_spawnBackend" in js
    assert "createProcess" in js
    assert "-m backend.app" in js
    assert 'cd -P' in js               # 심링크 설치에서도 레포 루트 해석


def test_duration_free_input():
    """분량 자유 입력(숫자) + 프리셋 버튼."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="newDuration" type="number"' in html
    assert 'data-dur="5"' in html          # 프리셋 버튼


def test_planning_stepper_ui():
    """기획 탭 단계별 스텝퍼 + 단계 실행."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="pipeStepper"' in html
    js = (PANEL / "js" / "planning.js").read_text(encoding="utf-8")
    assert "/api/pipeline/status" in js
    assert "/api/pipeline/run-stage" in js


def test_timeline_export_wired():
    """전체 타임라인 버튼 + 씬 재빌드 경로 + 씬 행 버튼. 평면 컴프라 씬 컴프 배치 스크립트는 없다."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnTimelineAll"' in html
    assert not (PANEL / "jsx" / "place_on_timeline.jsx").exists()
    build_jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "akRemoveSceneGroup" in build_jsx
    sb = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    for fn in ["function exportToTimeline", "function toggleTextEditor", "function saveSceneTexts"]:
        assert fn in sb, fn
    assert "akPlaceOnTimeline" not in sb
    # 행 버튼은 셋이다. `tts` 는 따로 두지 않는다 — 텍스트 편집 패널이
    # 고친 자리에서 바로 다시 만들므로(genTts) 같은 일을 하는 단추가 둘이었다.
    for act in ['data-act="img"', 'data-act="txt"', 'data-act="tl"']:
        assert act in sb, act
    assert "function genTts" in sb          # 편집 패널이 부르는 재생성은 남아 있어야 한다


def test_sheet_toolbar_batches_checked_scenes():
    """컴프·말자막이 체크한 씬 목록을 한 번에 넘긴다(씬마다 반복 호출 금지)."""
    sb = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert 'id="sa-sub"' in HTML.read_text(encoding="utf-8") or "sa-sub" in sb
    assert "_assemble(ns," in sb                 # 목록을 통째로
    assert "buildSubtitles(ns," in sb
    assert "_runSeq(ns, function (n) {\n      return Promise.resolve(buildSceneComp(n));" not in sb
    main = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert "sceneNumbers" in main               # 배열 파라미터 전송


def test_assistant_has_stop_and_scope():
    """긴 비서 작업을 패널에서 중단할 수 있고, 계획에 대상 범위가 보여야 한다."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="btnChatStop"' in html
    js = (PANEL / "js" / "assistant.js").read_text(encoding="utf-8")
    assert "function stopChatJob" in js and "/cancel" in js
    assert "a.targets" in js                       # 계획에 대상 씬 표시
    assert "이전 작업이 아직 실행 중" in js          # 중복 실행 차단


def test_layer_thumbnail_has_edit_buttons():
    """레이어 목록 행에서 눈 토글·제거·복구·벡터화 — 배경은 제거 버튼 없음."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function regenLayer" in js
    assert "function setLayerState" in js and "function vectorizeLayers" in js
    assert "/api/layers/state" in js and "/api/layers/regenerate" in js
    assert "/api/layers/vectorize" in js
    assert "lyr-row" in js and "lyr-eye" in js and "lyr-rm" in js and "lyr-restore" in js
    assert "isBg ? '' :" in js                  # 배경 행엔 제거 버튼 없음
    html = HTML.read_text(encoding="utf-8")
    assert ".lyr-row" in html and ".lyr-row.busy" in html


def test_layer_modal_shows_budget():
    """씬당 요소 10개 상한 — 초과분은 '예산 초과로 제외'로 보이고 체크는 10개까지."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    # 정확한 상수 정의
    assert "MAX_LAYER_ELEMENTS = 10" in js
    # dropped 요소가 permanent disabled 되어야 함
    assert "layer-dropped" in js
    assert 'data-dropped' in js and 'getAttribute("data-dropped")' in js
    assert "예산 초과" in js
    assert "_enforceLayerCap" in js
    html = HTML.read_text(encoding="utf-8")
    assert ".layer-dropped" in html


def test_layer_modal_shows_intent():
    """왜 나뉘는지를 연출 언어로 보여준다. 상한은 목표가 아니므로 문구도 바꾼다."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "e.intent" in js
    assert "최대 " in js


def test_max_layer_elements_matches_backend():
    """패널 하드코딩 상한이 backend.imagegen.MAX_ELEMENTS와 어긋나지 않아야 한다."""
    import re
    from backend import imagegen
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    m = re.search(r"MAX_LAYER_ELEMENTS\s*=\s*(\d+)", js)
    assert m, "MAX_LAYER_ELEMENTS 정의를 찾지 못함"
    assert int(m.group(1)) == imagegen.MAX_ELEMENTS


def test_layouts_jsx_registry_and_generic():
    """모르는 레이아웃도 그려야 한다 — 등록표 + 범용 렌더러."""
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    assert "AK_LAYOUTS" in jsx
    assert "function akLayout_generic" in jsx
    assert "function akRenderLayout" in jsx
    for name in ("headline_only", "items_list", "metric_spotlight", "quote"):
        assert "akLayout_" + name in jsx, name
    # ES3 수준 — 화살표 함수·템플릿 리터럴 금지
    assert "=>" not in jsx and "`" not in jsx
    assert "const " not in jsx and "let " not in jsx


def test_build_scene_delegates_to_layouts():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "akRenderLayout(" in jsx
    main = MAIN.read_text(encoding="utf-8")
    assert "layouts.jsx" in main            # 이어붙이기에 포함


def test_generic_renderer_uses_common_contract():
    """범용 렌더러는 v3 공통 계약 필드로 그린다."""
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    for field in ("s.title", "s.items", "s.values", "s.descriptions", "s.source"):
        assert field in jsx, field


def test_generic_renderer_reads_v3_compare_and_profile_fields():
    """left/right/profileName은 정규화되지만 아무도 안 읽으면 내용이 사라진다(회귀: 발견5)."""
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    for field in ("s.left", "s.right", "s.profileName"):
        assert field in jsx, field


# 이동 전 렌더러(bfe7703의 build_scene.jsx) 대비 draw-call 최소치.
# 그립·훅으로 잡을 수 없는 "함수 몸통에서 애니메이션/도형이 조용히 빠지는" 회귀를
# 카운트로 잡는다 — grep-for-identifier 테스트는 함수가 존재하기만 해도 통과해버린다.
_MIN_DRAW_CALLS = {
    # (addTextL 호출 수, addRectL 호출 수, anim: 등장 수)
    "akLayout_headline_only": (2, 1, 2),
    "akLayout_items_list": (2, 2, 1),
    "akLayout_metric_spotlight": (2, 1, 1),
    "akLayout_quote": (4, 0, 1),
    "akLayout_bar": (3, 2, 1),
}


def test_layouts_jsx_conserves_draw_calls_from_pre_move_build_scene():
    """추출 리팩터로 애니메이션/도형 호출이 줄어들면 실패한다."""
    import re
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    names = list(_MIN_DRAW_CALLS) + ["akLayout_generic"]
    for i, fn in enumerate(names):
        m = re.search(r"function " + fn + r"\(", jsx)
        assert m, fn
        start = m.end()
        nxt = names[i + 1] if i + 1 < len(names) else None
        if nxt:
            m2 = re.search(r"function " + nxt + r"\(", jsx)
            end = m2.start()
        else:
            m3 = re.search(r"\nvar AK_LAYOUTS", jsx)
            end = m3.start() if m3 else len(jsx)
        body = jsx[start:end]
        if fn not in _MIN_DRAW_CALLS:
            continue
        min_text, min_rect, min_anim = _MIN_DRAW_CALLS[fn]
        assert body.count("addTextL(") >= min_text, fn
        assert body.count("addRectL(") >= min_rect, fn
        assert body.count("anim:") >= min_anim, fn


def test_layer_buttons_say_scene_resplit():
    """layerize는 씬 단위 호출이라 레이어 한 장만 다시 뽑을 수 없다 — 문구가 그걸 알려야 한다."""
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "씬을 다시 분리" in js
    assert "이 레이어만 다시 생성" not in js
