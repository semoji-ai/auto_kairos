/**
 * map-editor.js — 맵 씬 전용 편집기
 *
 * Phase 1: mapType, mapStyle, title, source, camera keyframes, markers
 * Phase 2: route, territories, labels (mapType 조건부)
 * Phase 3: Leaflet 미니맵 (클릭 마커, 경로 그리기, 카메라 드래그)
 */
(function() {
  'use strict';

  var MAP_TYPES = [
    ['location_reveal', 'Location Reveal'],
    ['route_animation', 'Route Animation'],
    ['territory_overlay', 'Territory Overlay'],
    ['fly_through', 'Fly Through'],
  ];

  var MAP_STYLES = [
    ['modern_clean', 'Modern Clean'],
    ['vintage_parchment', 'Vintage Parchment'],
    ['minimal_light', 'Minimal Light'],
    ['dark_elegant', 'Dark Elegant'],
    ['blueprint', 'Blueprint'],
    ['warm_earth', 'Warm Earth'],
    ['historical', 'Historical'],
    ['dark_cyber', 'Dark Cyber'],
    ['clean_white', 'Clean White'],
    ['matte_slate', 'Matte Slate'],
  ];

  var MARKER_STYLES = [['pin', 'Pin'], ['dot', 'Dot'], ['pulse', 'Pulse']];
  var ROUTE_STYLES = [['solid', 'Solid'], ['dashed', 'Dashed']];
  var MAP_LANGUAGES = [
    ['', '기본 (현지어)'], ['en', 'English'], ['ko', '한국어'],
    ['ja', '日本語'], ['zh', '中文'], ['_none', '라벨 숨기기'],
  ];

  // Remotion과 동일한 타일 URL + CSS 필터
  var BRIGHT_URL = 'https://tiles.openfreemap.org/styles/bright';
  var DARK_URL = 'https://tiles.openfreemap.org/styles/dark';
  var STYLE_TILE_MAP = {
    modern_clean:      { url: BRIGHT_URL, filter: '' },
    historical:        { url: BRIGHT_URL, filter: 'sepia(0.2) saturate(0.85) brightness(0.95)' },
    dark_cyber:        { url: DARK_URL,   filter: '' },
    vintage_parchment: { url: BRIGHT_URL, filter: 'sepia(0.35) saturate(0.8) brightness(0.9)' },
    minimal_light:     { url: BRIGHT_URL, filter: '' },
    dark_elegant:      { url: DARK_URL,   filter: '' },
    blueprint:         { url: DARK_URL,   filter: 'hue-rotate(10deg) saturate(1.5) brightness(0.9)' },
    warm_earth:        { url: BRIGHT_URL, filter: 'sepia(0.15) saturate(1.1) brightness(0.95)' },
    matte_slate:       { url: DARK_URL,   filter: '' },
    clean_white:       { url: BRIGHT_URL, filter: 'saturate(0.3) brightness(1.05)' },
  };

  // ── 스타일 상수 ──
  var S = {
    bg: '#18181B', form: '#1E1E22', input: 'rgba(255,255,255,0.05)',
    border: 'rgba(255,255,255,0.1)', text: '#E4E4E7', muted: '#71717A',
    accent: '#F59E0B', danger: '#EF4444', success: '#22C55E',
  };

  // ── 유틸 ──
  function esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function(k) {
      if (k === 'style' && typeof attrs[k] === 'object') {
        Object.keys(attrs[k]).forEach(function(sk) { e.style[sk] = attrs[k][sk]; });
      } else if (k.startsWith('on')) { e.addEventListener(k.slice(2), attrs[k]); }
      else { e.setAttribute(k, attrs[k]); }
    });
    if (children) {
      if (typeof children === 'string') e.innerHTML = children;
      else if (Array.isArray(children)) children.forEach(function(c) { if (c) e.appendChild(c); });
      else e.appendChild(children);
    }
    return e;
  }

  // ── 메인 렌더 ──
  window.renderMapEditor = function(container, sceneData, sceneNum, slug, meta) {
    var ms = JSON.parse(JSON.stringify(sceneData.mapScene || {}));
    if (!ms.camera) ms.camera = { keyframes: [] };
    if (!ms.markers) ms.markers = [];
    if (!ms.labels) ms.labels = [];
    var leafletMap = null;
    var leafletMarkers = [];
    var leafletRoute = null;

    container.innerHTML = '';
    var wrapper = el('div', {style: {display:'flex', height:'100%', background:S.bg, color:S.text, fontFamily:"'Inter',sans-serif", fontSize:'12px'}});
    container.appendChild(wrapper);

    // ── 좌: 폼 ──
    var formArea = el('div', {style: {flex:'1 1 50%', overflowY:'auto', padding:'14px 16px', display:'flex', flexDirection:'column', gap:'12px'}});
    wrapper.appendChild(formArea);

    // ── 우: Leaflet 맵 ──
    var mapArea = el('div', {style: {flex:'1 1 50%', borderLeft:'1px solid '+S.border, display:'flex', flexDirection:'column'}});
    wrapper.appendChild(mapArea);

    // 검색창
    var searchBar = el('div', {style: {padding:'6px 10px', borderBottom:'1px solid '+S.border, display:'flex', gap:'6px', alignItems:'center'}});
    var searchInput = el('input', {type:'text', placeholder:'장소 검색 (예: 테헤란, Seoul...)', style:{
      flex:'1', background:S.input, border:'1px solid '+S.border, borderRadius:'4px',
      color:S.text, fontSize:'11px', padding:'5px 8px', outline:'none',
    }});
    var searchBtn = el('button', {style:{
      fontSize:'10px', padding:'4px 10px', borderRadius:'4px', cursor:'pointer',
      background:S.accent, color:'#000', border:'none', fontWeight:'600', whiteSpace:'nowrap',
    }}, '검색');
    var searchResults = el('div', {style: {
      position:'absolute', top:'100%', left:'0', right:'0', zIndex:'100',
      background:'#1E1E22', border:'1px solid '+S.border, borderRadius:'0 0 6px 6px',
      maxHeight:'200px', overflowY:'auto', display:'none',
    }});
    var searchWrap = el('div', {style:{position:'relative', flex:'1', display:'flex', gap:'6px'}}, [searchInput, searchBtn]);
    searchWrap.appendChild(searchResults);
    searchBar.appendChild(searchWrap);
    mapArea.appendChild(searchBar);

    function doSearch() {
      var q = searchInput.value.trim();
      if (!q) return;
      searchBtn.textContent = '...';
      fetch('https://nominatim.openstreetmap.org/search?format=json&limit=5&q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(results) {
          searchResults.innerHTML = '';
          if (!results.length) {
            searchResults.innerHTML = '<div style="padding:8px;color:'+S.muted+';font-size:10px">결과 없음</div>';
            searchResults.style.display = '';
            return;
          }
          results.forEach(function(r) {
            var item = el('div', {style:{
              padding:'6px 10px', cursor:'pointer', fontSize:'11px', borderBottom:'1px solid '+S.border,
            }}, '<b>' + esc(r.display_name.split(',')[0]) + '</b><br><span style="color:'+S.muted+';font-size:9px">' + esc(r.display_name) + '</span>');
            item.addEventListener('click', function() {
              var lng = parseFloat(r.lon);
              var lat = parseFloat(r.lat);
              searchResults.style.display = 'none';
              searchInput.value = r.display_name.split(',')[0];
              // 맵 이동
              if (leafletMap) leafletMap.flyTo({ center: [lng, lat], zoom: 10, duration: 1000 });
              // 마커 추가 확인
              akConfirm(r.display_name.split(',')[0] + '에 마커를 추가하시겠습니까?', function () {
                ms.markers.push({ coordinates: [Math.round(lng*10000)/10000, Math.round(lat*10000)/10000], label: r.display_name.split(',')[0], style: 'pin', appearAtFrame: 0 });
                renderMarkers();
                syncMap();
              });
            });
            item.addEventListener('mouseenter', function() { this.style.background = 'rgba(245,158,11,0.1)'; });
            item.addEventListener('mouseleave', function() { this.style.background = ''; });
            searchResults.appendChild(item);
          });
          searchResults.style.display = '';
        })
        .catch(function() { searchResults.innerHTML = '<div style="padding:8px;color:'+S.danger+';font-size:10px">검색 오류</div>'; searchResults.style.display = ''; })
        .finally(function() { searchBtn.textContent = '검색'; });
    }
    searchBtn.addEventListener('click', doSearch);
    searchInput.addEventListener('keydown', function(e) { if (e.key === 'Enter') doSearch(); });
    // 포커스 아웃 시 결과 숨기기
    document.addEventListener('click', function(e) { if (!searchWrap.contains(e.target)) searchResults.style.display = 'none'; });

    var mapToolbar = el('div', {style: {padding:'4px 10px', borderBottom:'1px solid '+S.border, fontSize:'10px', color:S.muted, display:'flex', gap:'8px', alignItems:'center'}});
    mapArea.appendChild(mapToolbar);

    var mapDiv = el('div', {id: 'map-editor-leaflet', style: {flex:'1'}});
    mapArea.appendChild(mapDiv);

    // ── Phase 1: 기본 필드 ──
    if (!ms._editorSettings) ms._editorSettings = {};
    var mapLang = ms._editorSettings.language || 'ko';

    formArea.appendChild(buildSection('기본 설정', [
      buildRow([
        buildSelect('mapType', 'Map Type', ms.mapType || 'location_reveal', MAP_TYPES, function(v) { ms.mapType = v; refreshConditional(); }),
        buildSelect('mapStyle', 'Map Style', ms.mapStyle || 'modern_clean', MAP_STYLES, function(v) { ms.mapStyle = v; if (window._mapEditorUpdateStyle) window._mapEditorUpdateStyle(v); }),
      ]),
      buildRow([
        buildInput('title', 'Title', ms.title || '', function(v) { ms.title = v; }),
        buildInput('source', 'Source', ms.source || '', function(v) { ms.source = v; }),
      ]),
      buildRow([
        buildSelect('mapLang', '맵 라벨 언어', mapLang, MAP_LANGUAGES, function(v) {
          mapLang = v; ms._editorSettings.language = v;
          applyMapLanguage(v);
        }),
      ]),
    ]));

    // Camera keyframes
    var cameraSection = el('div');
    formArea.appendChild(cameraSection);
    function renderCamera() {
      cameraSection.innerHTML = '';
      var kfs = ms.camera.keyframes || [];
      var items = kfs.map(function(kf, i) {
        return buildRow([
          buildNum('kf-frame-'+i, 'Frame', kf.frame||0, function(v){kf.frame=+v;}),
          buildNum('kf-lng-'+i, 'Lng', kf.center?kf.center[0]:0, function(v){if(!kf.center)kf.center=[0,0];kf.center[0]=+v;}),
          buildNum('kf-lat-'+i, 'Lat', kf.center?kf.center[1]:0, function(v){if(!kf.center)kf.center=[0,0];kf.center[1]=+v;}),
          buildNum('kf-zoom-'+i, 'Zoom', kf.zoom||5, function(v){kf.zoom=+v;}),
          buildNum('kf-bearing-'+i, 'Brg', kf.bearing||0, function(v){kf.bearing=+v;}),
          buildNum('kf-pitch-'+i, 'Pitch', kf.pitch||0, function(v){kf.pitch=+v;}),
          buildBtn('-', S.danger, function(){kfs.splice(i,1);renderCamera();syncMap();}),
        ]);
      });
      items.push(buildRow([buildBtn('+ 키프레임', S.accent, function(){kfs.push({frame:(kfs.length?kfs[kfs.length-1].frame+60:0),center:[127,37],zoom:7,bearing:0,pitch:0});renderCamera();syncMap();})]));
      cameraSection.appendChild(buildSection('Camera Keyframes (' + kfs.length + ')', items));
    }
    renderCamera();

    // Markers
    var markerSection = el('div');
    formArea.appendChild(markerSection);
    function renderMarkers() {
      markerSection.innerHTML = '';
      var items = ms.markers.map(function(m, i) {
        return buildRow([
          buildNum('mk-lng-'+i, 'Lng', m.coordinates?m.coordinates[0]:0, function(v){if(!m.coordinates)m.coordinates=[0,0];m.coordinates[0]=+v;syncMap();}),
          buildNum('mk-lat-'+i, 'Lat', m.coordinates?m.coordinates[1]:0, function(v){if(!m.coordinates)m.coordinates=[0,0];m.coordinates[1]=+v;syncMap();}),
          buildInput('mk-label-'+i, 'Label', m.label||'', function(v){m.label=v;}),
          buildSelect('mk-style-'+i, '', m.style||'pin', MARKER_STYLES, function(v){m.style=v;}),
          buildNum('mk-frame-'+i, 'Frame', m.appearAtFrame||0, function(v){m.appearAtFrame=+v;}),
          buildBtn('-', S.danger, function(){ms.markers.splice(i,1);renderMarkers();syncMap();}),
        ]);
      });
      items.push(buildRow([buildBtn('+ 마커', S.accent, function(){ms.markers.push({coordinates:[127,37],label:'',style:'pin',appearAtFrame:0});renderMarkers();syncMap();})]));
      markerSection.appendChild(buildSection('Markers (' + ms.markers.length + ')', items));
    }
    renderMarkers();

    // ── Phase 2: 조건부 필드 ──
    var conditionalArea = el('div');
    formArea.appendChild(conditionalArea);

    function refreshConditional() {
      conditionalArea.innerHTML = '';

      // Route (route_animation)
      if (ms.mapType === 'route_animation') {
        if (!ms.route) ms.route = { coordinates: [], color: '#FF6B6B', width: 5, style: 'solid' };
        var r = ms.route;
        var routeItems = [
          buildRow([
            buildInput('rt-color', 'Color', r.color||'#FF6B6B', function(v){r.color=v;}),
            buildNum('rt-width', 'Width', r.width||5, function(v){r.width=+v;}),
            buildNum('rt-dur', 'Draw Frames', r.drawDurationFrames||90, function(v){r.drawDurationFrames=+v;}),
            buildSelect('rt-style', 'Style', r.style||'solid', ROUTE_STYLES, function(v){r.style=v;}),
          ]),
        ];
        // Route coordinates
        (r.coordinates||[]).forEach(function(c, i) {
          routeItems.push(buildRow([
            el('span', {style:{color:S.muted,fontSize:'10px',minWidth:'20px'}}, '#'+i),
            buildNum('rc-lng-'+i, 'Lng', c[0], function(v){r.coordinates[i][0]=+v;syncMap();}),
            buildNum('rc-lat-'+i, 'Lat', c[1], function(v){r.coordinates[i][1]=+v;syncMap();}),
            buildBtn('-', S.danger, function(){r.coordinates.splice(i,1);refreshConditional();syncMap();}),
          ]));
        });
        routeItems.push(buildRow([
          buildBtn('+ 좌표', S.accent, function(){r.coordinates.push([127,37]);refreshConditional();syncMap();}),
          el('span', {style:{fontSize:'10px',color:S.muted}}, '또는 맵에서 Shift+클릭'),
        ]));
        conditionalArea.appendChild(buildSection('Route (' + (r.coordinates||[]).length + ' points)', routeItems));
      }

      // Territories (territory_overlay)
      if (ms.mapType === 'territory_overlay') {
        if (!ms.territories) ms.territories = [];
        var tItems = ms.territories.map(function(t, i) {
          return buildRow([
            buildInput('tr-geojson-'+i, 'GeoJSON Path', t.geojsonPath||'', function(v){t.geojsonPath=v;}),
            buildInput('tr-fill-'+i, 'Fill', t.fillColor||'#FF0000', function(v){t.fillColor=v;}),
            buildNum('tr-opacity-'+i, 'Opacity', t.fillOpacity!==undefined?t.fillOpacity:0.3, function(v){t.fillOpacity=+v;}),
            buildInput('tr-stroke-'+i, 'Stroke', t.strokeColor||'', function(v){t.strokeColor=v;}),
            buildNum('tr-frame-'+i, 'Frame', t.appearAtFrame||0, function(v){t.appearAtFrame=+v;}),
            buildBtn('-', S.danger, function(){ms.territories.splice(i,1);refreshConditional();}),
          ]);
        });
        tItems.push(buildRow([buildBtn('+ 영역', S.accent, function(){ms.territories.push({fillColor:'#FF6B6B',fillOpacity:0.3,appearAtFrame:0,fadeInFrames:20});refreshConditional();})]));
        conditionalArea.appendChild(buildSection('Territories (' + ms.territories.length + ')', tItems));
      }

      // Labels (all types)
      var lItems = (ms.labels||[]).map(function(l, i) {
        return buildRow([
          buildNum('lb-lng-'+i, 'Lng', l.coordinates?l.coordinates[0]:0, function(v){if(!l.coordinates)l.coordinates=[0,0];l.coordinates[0]=+v;syncMap();}),
          buildNum('lb-lat-'+i, 'Lat', l.coordinates?l.coordinates[1]:0, function(v){if(!l.coordinates)l.coordinates=[0,0];l.coordinates[1]=+v;syncMap();}),
          buildInput('lb-text-'+i, 'Text', l.text||'', function(v){l.text=v;}),
          buildNum('lb-size-'+i, 'Size', l.fontSize||14, function(v){l.fontSize=+v;}),
          buildNum('lb-frame-'+i, 'Frame', l.appearAtFrame||0, function(v){l.appearAtFrame=+v;}),
          buildBtn('-', S.danger, function(){ms.labels.splice(i,1);refreshConditional();syncMap();}),
        ]);
      });
      lItems.push(buildRow([buildBtn('+ 라벨', S.accent, function(){ms.labels.push({coordinates:[127,37],text:'',fontSize:14,appearAtFrame:0});refreshConditional();syncMap();})]));
      conditionalArea.appendChild(buildSection('Labels (' + (ms.labels||[]).length + ')', lItems));
    }
    refreshConditional();

    // ── 저장 버튼 ──
    var statusEl = el('div', {id:'map-save-status', style:{fontSize:'11px',textAlign:'center',marginTop:'4px'}});
    var saveBtn = el('button', {style:{
      width:'100%',padding:'8px',background:S.accent,color:'#000',border:'none',
      borderRadius:'6px',fontWeight:'700',fontSize:'13px',cursor:'pointer',
    }, onclick: function() { doSave(); }}, '저장');
    formArea.appendChild(el('div', {style:{marginTop:'auto',paddingTop:'12px',borderTop:'1px solid '+S.border}}, [saveBtn, statusEl]));

    function doSave() {
      saveBtn.disabled = true;
      saveBtn.textContent = '저장 중...';
      var payload = JSON.parse(JSON.stringify(sceneData));
      payload.mapScene = ms;
      fetch('/api/p/' + slug + '/editor/scenes/' + sceneNum, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ scene_data: payload, mode: 'save' }),
      })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.ok) {
          statusEl.style.color = S.success;
          statusEl.textContent = '저장 완료';
          document.dispatchEvent(new CustomEvent('scene-editor-saved', { detail: { sceneNumber: sceneNum } }));
        } else {
          statusEl.style.color = S.danger;
          statusEl.textContent = res.error || '저장 실패';
        }
      })
      .catch(function(e) { statusEl.style.color = S.danger; statusEl.textContent = e.message; })
      .finally(function() { saveBtn.disabled = false; saveBtn.textContent = '저장'; setTimeout(function(){statusEl.textContent='';},3000); });
    }

    // ── 맵 라벨 언어 변경 ──
    function applyMapLanguage(lang) {
      if (!leafletMap || !leafletMap.getStyle()) return;
      var style = leafletMap.getStyle();
      if (!style.layers) return;
      style.layers.forEach(function(layer) {
        if (layer.layout && layer.layout['text-field']) {
          try {
            if (lang === '_none') {
              // 라벨 완전 숨기기
              leafletMap.setLayoutProperty(layer.id, 'visibility', 'none');
            } else {
              leafletMap.setLayoutProperty(layer.id, 'visibility', 'visible');
              if (lang) {
                // name:ko, name:en 등으로 변경
                leafletMap.setLayoutProperty(layer.id, 'text-field', ['coalesce', ['get', 'name:' + lang], ['get', 'name']]);
              } else {
                // 기본 (현지어)
                leafletMap.setLayoutProperty(layer.id, 'text-field', ['get', 'name']);
              }
            }
          } catch(e) { /* 일부 레이어 무시 */ }
        }
      });
    }

    // ── Phase 3: MapLibre GL 맵 (Remotion과 동일 엔진) ──
    var mapMode = 'marker'; // 'marker' | 'route' | 'camera'
    var _mlMarkers = []; // MapLibre Marker 인스턴스
    var _mlPopups = [];

    setTimeout(function() {
      if (!window.maplibregl) return;

      // 초기 중심/줌 — 마지막 키프레임 사용 (최종 렌더링 상태)
      var initCenter = [127, 37];
      var initZoom = 5;
      var initBearing = 0;
      var initPitch = 0;
      if (ms.camera.keyframes.length) {
        var kfLast = ms.camera.keyframes[ms.camera.keyframes.length - 1];
        if (kfLast.center) initCenter = [kfLast.center[0], kfLast.center[1]];
        if (kfLast.zoom !== undefined && kfLast.zoom !== null) initZoom = kfLast.zoom;
        if (kfLast.bearing) initBearing = kfLast.bearing;
        if (kfLast.pitch) initPitch = kfLast.pitch;
      } else if (ms.markers.length && ms.markers[0].coordinates) {
        initCenter = ms.markers[0].coordinates;
        initZoom = 8;
      }

      // 테마에 맞는 스타일 URL + CSS 필터
      var tileInfo = STYLE_TILE_MAP[ms.mapStyle] || STYLE_TILE_MAP.modern_clean;

      leafletMap = new maplibregl.Map({
        container: mapDiv,
        style: tileInfo.url,
        center: initCenter,
        zoom: initZoom,
        bearing: initBearing,
        pitch: initPitch,
        attributionControl: false,
      });

      // CSS 필터 적용 (테마별 톤)
      if (tileInfo.filter) mapDiv.style.filter = tileInfo.filter;

      leafletMap.addControl(new maplibregl.NavigationControl(), 'top-right');

      leafletMap.on('load', function() {
        syncMap();
        // 초기 언어 적용
        if (mapLang) applyMapLanguage(mapLang);
      });

      // 맵 클릭 이벤트
      leafletMap.on('click', function(e) {
        var lng = Math.round(e.lngLat.lng * 10000) / 10000;
        var lat = Math.round(e.lngLat.lat * 10000) / 10000;

        if (e.originalEvent.shiftKey && ms.mapType === 'route_animation') {
          // Shift+클릭 = 경로 포인트
          if (!ms.route) ms.route = { coordinates: [], color: '#FF6B6B', width: 5, style: 'solid' };
          ms.route.coordinates.push([lng, lat]);
          refreshConditional();
          syncMap();
        } else if (mapMode === 'route' && ms.mapType === 'route_animation') {
          if (!ms.route) ms.route = { coordinates: [], color: '#FF6B6B', width: 5, style: 'solid' };
          ms.route.coordinates.push([lng, lat]);
          refreshConditional();
          syncMap();
        } else if (mapMode === 'camera') {
          var kfs = ms.camera.keyframes;
          if (kfs.length) { kfs[kfs.length - 1].center = [lng, lat]; }
          else { kfs.push({ frame: 0, center: [lng, lat], zoom: Math.round(leafletMap.getZoom()), bearing: 0, pitch: 0 }); }
          renderCamera();
          syncMap();
        } else {
          // 마커 추가
          ms.markers.push({ coordinates: [lng, lat], label: '', style: 'pin', appearAtFrame: 0 });
          renderMarkers();
          syncMap();
        }
      });

      // 모드 전환 버튼
      mapToolbar.innerHTML = '';
      var modes = [['marker','마커 추가'],['route','경로 추가'],['camera','카메라 중심']];
      modes.forEach(function(m) {
        var btn = el('button', {style:{
          fontSize:'10px',padding:'2px 8px',borderRadius:'3px',cursor:'pointer',
          border:'1px solid '+S.border, color: S.text,
          background: mapMode===m[0] ? 'rgba(245,158,11,0.2)' : 'transparent',
        }, onclick: function() {
          mapMode = m[0];
          mapToolbar.querySelectorAll('button').forEach(function(b) { b.style.background = 'transparent'; });
          btn.style.background = 'rgba(245,158,11,0.2)';
          // 커서 변경
          mapDiv.style.cursor = m[0] === 'marker' ? 'crosshair' : m[0] === 'route' ? 'copy' : 'move';
        }}, m[1]);
        mapToolbar.appendChild(btn);
      });
      mapDiv.style.cursor = 'crosshair';

      // 정리 함수
      window._mapEditorDestroy = function() {
        if (leafletMap) { leafletMap.remove(); leafletMap = null; }
        mapDiv.style.filter = '';
      };
    }, 200);

    // 맵 스타일 변경 시 재적용
    window._mapEditorUpdateStyle = function(styleName) {
      if (!leafletMap) return;
      var tileInfo = STYLE_TILE_MAP[styleName] || STYLE_TILE_MAP.modern_clean;
      leafletMap.setStyle(tileInfo.url);
      mapDiv.style.filter = tileInfo.filter || '';
      // 스타일 로드 후 오버레이 + 언어 재적용
      leafletMap.once('styledata', function() { setTimeout(function() { syncMap(); if (mapLang) applyMapLanguage(mapLang); }, 300); });
    };

    // ── 맵 동기화 (폼 → MapLibre) ──
    function syncMap() {
      if (!leafletMap) return;

      // 기존 마커 정리
      _mlMarkers.forEach(function(m) { m.remove(); });
      _mlMarkers = [];

      // 마커 배치
      ms.markers.forEach(function(m) {
        if (!m.coordinates) return;
        var markerEl = document.createElement('div');
        markerEl.style.cssText = 'width:14px;height:14px;background:'+S.accent+';border:2px solid #fff;border-radius:50%;box-shadow:0 1px 4px rgba(0,0,0,0.4);cursor:pointer;';
        var mk = new maplibregl.Marker({ element: markerEl, draggable: true })
          .setLngLat(m.coordinates)
          .addTo(leafletMap);
        if (m.label) {
          mk.setPopup(new maplibregl.Popup({ offset: 12, closeButton: false }).setText(m.label));
          mk.togglePopup();
        }
        mk.on('dragend', function() {
          var pos = mk.getLngLat();
          m.coordinates = [Math.round(pos.lng*10000)/10000, Math.round(pos.lat*10000)/10000];
          renderMarkers(); // 폼 업데이트
        });
        _mlMarkers.push(mk);
      });

      // 카메라 키프레임 표시 (파란 점)
      ms.camera.keyframes.forEach(function(kf, i) {
        if (!kf.center) return;
        var camEl = document.createElement('div');
        camEl.style.cssText = 'width:10px;height:10px;background:#3B82F6;border:1.5px solid #fff;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,0.3);cursor:pointer;';
        camEl.title = 'KF' + i + ' (f' + kf.frame + ', z' + kf.zoom + ')';
        var mk = new maplibregl.Marker({ element: camEl, draggable: true })
          .setLngLat(kf.center)
          .addTo(leafletMap);
        mk.on('dragend', function() {
          var pos = mk.getLngLat();
          kf.center = [Math.round(pos.lng*10000)/10000, Math.round(pos.lat*10000)/10000];
          renderCamera();
        });
        _mlMarkers.push(mk);
      });

      // 라벨 표시
      (ms.labels || []).forEach(function(l) {
        if (!l.coordinates || !l.text) return;
        var labelEl = document.createElement('div');
        labelEl.style.cssText = 'background:rgba(0,0,0,0.75);color:#fff;padding:2px 7px;border-radius:3px;font-size:10px;white-space:nowrap;pointer-events:none;';
        labelEl.textContent = l.text;
        var mk = new maplibregl.Marker({ element: labelEl })
          .setLngLat(l.coordinates)
          .addTo(leafletMap);
        _mlMarkers.push(mk);
      });

      // GeoJSON 소스: 경로 + 카메라 경로
      // 경로 레이어
      try {
        if (leafletMap.getLayer('route-line')) leafletMap.removeLayer('route-line');
        if (leafletMap.getSource('route-src')) leafletMap.removeSource('route-src');
        if (leafletMap.getLayer('cam-line')) leafletMap.removeLayer('cam-line');
        if (leafletMap.getSource('cam-src')) leafletMap.removeSource('cam-src');
      } catch(e) {}

      if (ms.route && ms.route.coordinates && ms.route.coordinates.length >= 2) {
        leafletMap.addSource('route-src', {
          type: 'geojson',
          data: { type: 'Feature', geometry: { type: 'LineString', coordinates: ms.route.coordinates } },
        });
        leafletMap.addLayer({
          id: 'route-line', type: 'line', source: 'route-src',
          paint: {
            'line-color': ms.route.color || '#FF6B6B',
            'line-width': ms.route.width || 3,
            'line-opacity': 0.8,
            ...(ms.route.style === 'dashed' ? {'line-dasharray': [2, 1.5]} : {}),
          },
        });
      }

      // 카메라 경로 (점선)
      var camCoords = ms.camera.keyframes.filter(function(k){return k.center;}).map(function(k){return k.center;});
      if (camCoords.length >= 2) {
        leafletMap.addSource('cam-src', {
          type: 'geojson',
          data: { type: 'Feature', geometry: { type: 'LineString', coordinates: camCoords } },
        });
        leafletMap.addLayer({
          id: 'cam-line', type: 'line', source: 'cam-src',
          paint: { 'line-color': '#3B82F6', 'line-width': 1.5, 'line-opacity': 0.5, 'line-dasharray': [3, 2] },
        });
      }
    }
  };

  // ── 폼 빌더 유틸 ──
  function buildSection(title, children) {
    var sec = el('div', {style:{background:S.form,border:'1px solid '+S.border,borderRadius:'6px',padding:'10px 12px'}});
    sec.appendChild(el('div', {style:{fontSize:'10px',fontWeight:'700',textTransform:'uppercase',letterSpacing:'0.5px',color:S.accent,marginBottom:'8px'}}, title));
    children.forEach(function(c) { sec.appendChild(c); });
    return sec;
  }

  function buildRow(children) {
    var row = el('div', {style:{display:'flex',gap:'6px',alignItems:'flex-end',marginBottom:'6px',flexWrap:'wrap'}});
    children.forEach(function(c) { if (c) row.appendChild(c); });
    return row;
  }

  function buildInput(id, label, val, onChange) {
    var g = el('div', {style:{display:'flex',flexDirection:'column',gap:'2px',flex:'1',minWidth:'60px'}});
    g.appendChild(el('span', {style:{fontSize:'9px',color:S.muted}}, label));
    var inp = el('input', {type:'text', value:val, style:{
      background:S.input,border:'1px solid '+S.border,borderRadius:'3px',
      color:S.text,fontSize:'11px',padding:'4px 6px',width:'100%',boxSizing:'border-box',outline:'none',
    }});
    inp.addEventListener('change', function() { onChange(inp.value); });
    g.appendChild(inp);
    return g;
  }

  function buildNum(id, label, val, onChange) {
    var g = el('div', {style:{display:'flex',flexDirection:'column',gap:'2px',flex:'0 0 55px'}});
    g.appendChild(el('span', {style:{fontSize:'9px',color:S.muted}}, label));
    var inp = el('input', {type:'number', value:String(val), step:'any', style:{
      background:S.input,border:'1px solid '+S.border,borderRadius:'3px',
      color:S.text,fontSize:'11px',padding:'4px 4px',width:'100%',boxSizing:'border-box',outline:'none',
    }});
    inp.addEventListener('change', function() { onChange(inp.value); });
    g.appendChild(inp);
    return g;
  }

  function buildSelect(id, label, val, opts, onChange) {
    var g = el('div', {style:{display:'flex',flexDirection:'column',gap:'2px',flex:'1',minWidth:'80px'}});
    if (label) g.appendChild(el('span', {style:{fontSize:'9px',color:S.muted}}, label));
    var sel = el('select', {style:{
      background:S.input,border:'1px solid '+S.border,borderRadius:'3px',
      color:S.text,fontSize:'11px',padding:'4px 4px',cursor:'pointer',outline:'none',
    }});
    opts.forEach(function(o) {
      var opt = el('option', {value:o[0]}, o[1]);
      if (o[0] === val) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.addEventListener('change', function() { onChange(sel.value); });
    g.appendChild(sel);
    return g;
  }

  function buildBtn(text, color, onClick) {
    return el('button', {style:{
      fontSize:'10px',padding:'3px 8px',borderRadius:'3px',cursor:'pointer',
      background:color===S.danger?'rgba(239,68,68,0.15)':color===S.accent?S.accent:'transparent',
      color:color===S.accent?'#000':color===S.danger?S.danger:S.text,
      border:'1px solid '+(color===S.danger?'rgba(239,68,68,0.3)':color===S.accent?S.accent:S.border),
      fontWeight:'600', whiteSpace:'nowrap',
    }, onclick: onClick}, text);
  }
})();
