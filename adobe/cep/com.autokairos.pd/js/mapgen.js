/* 지도 씬 렌더 — 패널(Chromium)에서 MapLibre GL을 직접 띄워 1920x1080 캔버스를 캡처하고
   백엔드에 PNG로 저장 → 씬 이미지로 링크. 타일: OpenFreeMap(키 불필요).
   좌표 규칙: scenes.json은 [위도, 경도] — MapLibre는 [경도, 위도]라서 여기서 swap. */

/* CEP Chromium 폴리필 — maplibre v5가 쓰는 최신 API가 구버전 CEF에 없음 */
(function () {
  if (typeof AbortSignal !== "undefined") {
    if (!AbortSignal.prototype.throwIfAborted) {           // Chrome 100+
      AbortSignal.prototype.throwIfAborted = function () {
        if (this.aborted) throw (this.reason !== undefined ? this.reason : new Error("Aborted"));
      };
    }
    if (!AbortSignal.timeout) {                            // Chrome 103+
      AbortSignal.timeout = function (ms) {
        var c = new AbortController();
        setTimeout(function () { c.abort(new Error("TimeoutError")); }, ms);
        return c.signal;
      };
    }
    if (!AbortSignal.abort) {                              // Chrome 93+
      AbortSignal.abort = function (reason) {
        var c = new AbortController(); c.abort(reason); return c.signal;
      };
    }
  }
  if (typeof structuredClone === "undefined") {            // Chrome 98+
    window.structuredClone = function (v) { return JSON.parse(JSON.stringify(v)); };
  }
  if (!Array.prototype.at) {                               // Chrome 92+
    Array.prototype.at = function (i) { return this[i < 0 ? this.length + i : i]; };
  }
})();

var MAP_BRIGHT_URL = "https://tiles.openfreemap.org/styles/bright";
var MAP_DARK_URL = "https://tiles.openfreemap.org/styles/dark";

/* 맵 테마 — v3 mapStyles.ts 이식(레이어 paint 오버라이드).
   CSS 필터 테마는 캔버스 캡처에 안 구워지므로 오버라이드 방식만 사용. */
var MAP_THEMES = {
  warm_earth: { url: MAP_BRIGHT_URL, overrides: [          // 세모지 기본 — 따뜻한 대지색
    { match: "background", paint: { "background-color": "#F0E8DE" } },
    { match: "water", paint: { "fill-color": "#C8BAA0" } },
    { match: "waterway*", paint: { "line-color": "#B8A888" } },
    { match: "landcover*", paint: { "fill-color": "#E4DCC8", "fill-opacity": 0.5 } },
    { match: "landuse*", paint: { "fill-color": "#E8DDCC", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#D4CCB8", "fill-opacity": 0.5 } },
    { match: "boundary*", paint: { "line-color": "#8A6E48", "line-width": 1.6, "line-opacity": 0.9 } },
    { match: "road*", paint: { "line-color": "#C8B498", "line-opacity": 0.7 } },
    { match: "building*", paint: { "fill-color": "#E0D6C8", "fill-opacity": 0.4 } },
  ] },
  matte_slate: { url: MAP_DARK_URL, overrides: [           // 뉴트럴 다크
    { match: "background", paint: { "background-color": "#1A1C22" } },
    { match: "water", paint: { "fill-color": "#0E1018" } },
    { match: "waterway*", paint: { "line-color": "#1E2030" } },
    { match: "landcover*", paint: { "fill-color": "#22242E", "fill-opacity": 0.4 } },
    { match: "landuse*", paint: { "fill-color": "#20222C", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#1E2028", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#6A6E7C", "line-width": 1.4, "line-opacity": 0.8 } },
    { match: "road*", paint: { "line-color": "#383C48", "line-opacity": 0.6 } },
    { match: "building*", paint: { "fill-color": "#24262E", "fill-opacity": 0.3 } },
  ] },
  clean_white: { url: MAP_BRIGHT_URL, overrides: [         // 순백 모던
    { match: "background", paint: { "background-color": "#FFFFFF" } },
    { match: "water", paint: { "fill-color": "#D6E6F5" } },
    { match: "waterway*", paint: { "line-color": "#B0D0F0" } },
    { match: "landcover*", paint: { "fill-color": "#F0F4F0", "fill-opacity": 0.3 } },
    { match: "landuse*", paint: { "fill-color": "#F8F8FA", "fill-opacity": 0.2 } },
    { match: "park*", paint: { "fill-color": "#E8F2E8", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#A0AAB8", "line-width": 1.2, "line-opacity": 0.8 } },
    { match: "road*", paint: { "line-color": "#D8DCE4", "line-opacity": 0.7 } },
    { match: "building*", paint: { "fill-color": "#F0F0F4", "fill-opacity": 0.3 } },
  ] },
  dark_cyber: { url: MAP_DARK_URL, overrides: [
    { match: "boundary*", paint: { "line-color": "#4A8080", "line-width": 1.2, "line-opacity": 0.8 } },
    { match: "water", paint: { "fill-color": "#18202A" } },
    { match: "road*", paint: { "line-color": "#2A3540", "line-opacity": 0.6 } },
  ] },
  bright: { url: MAP_BRIGHT_URL, overrides: [] },
};

// v3 applyLayerOverrides 이식 — match는 정확 일치 또는 "prefix*"
function _applyOverrides(map, overrides) {
  var style = map.getStyle();
  if (!style || !style.layers) return;
  for (var i = 0; i < overrides.length; i++) {
    var ov = overrides[i];
    var isPrefix = ov.match.charAt(ov.match.length - 1) === "*";
    var prefix = isPrefix ? ov.match.slice(0, -1) : "";
    for (var j = 0; j < style.layers.length; j++) {
      var id = style.layers[j].id;
      if (!(isPrefix ? id.indexOf(prefix) === 0 : id === ov.match)) continue;
      for (var k in (ov.paint || {})) {
        try { map.setPaintProperty(id, k, ov.paint[k]); } catch (e) { }
      }
    }
  }
}

// 씬에 resolve된 테마(_theme.map)가 있으면 그걸 우선 사용, 없으면 기존 MAP_THEMES(폴백).
function _mapTheme(scene) {
  var tm = scene && scene._theme && scene._theme.map;
  if (tm && tm.overrides) {
    return {
      url: tm.tile === "dark" ? MAP_DARK_URL : MAP_BRIGHT_URL,
      overrides: tm.overrides,
      rasterFilter: tm.rasterFilter || "",
    };
  }
  var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
  return MAP_THEMES[name] || MAP_THEMES.warm_earth;
}

function _swapLL(c) { return [c[1], c[0]]; }   // [lat,lng] → [lng,lat]

// s: 씬 객체(map_center/map_zoom/map_markers). resolve(상대경로) / reject(에러)
function renderMapScene(s) {
  return new Promise(function (resolve, reject) {
    if (typeof maplibregl === "undefined") { reject("maplibre-gl 미로드 — 패널 재오픈 필요"); return; }
    var glTest = document.createElement("canvas");
    if (!glTest.getContext("webgl2") && !glTest.getContext("webgl")) {
      reject("WebGL 비활성 — AE를 완전히 재시작해야 적용됩니다(manifest에 --enable-webgl 추가됨)"); return;
    }
    var center = s.map_center && s.map_center.length === 2 ? _swapLL(s.map_center) : [127.0, 37.5];
    var host = document.createElement("div");
    host.style.cssText = "position:fixed;left:-99999px;top:0;width:1920px;height:1080px";
    document.body.appendChild(host);
    var done = false;
    function finish(err, dataUrl) {
      if (done) return; done = true;
      stopRepaint();
      try { map.remove(); } catch (e) { }
      host.remove();
      if (err) reject(err); else resolve(dataUrl);
    }
    var map, stage = "init", lastErr = "";
    var repaint = null;                          // 숨김 패널 rAF 스로틀 대응 — 강제 리페인트
    function stopRepaint() { if (repaint) { clearInterval(repaint); repaint = null; } }
    try {
      var theme = _mapTheme(s);
      map = new maplibregl.Map({
        container: host, style: theme.url,
        center: center, zoom: s.map_zoom || 5,
        interactive: false, attributionControl: false,
        preserveDrawingBuffer: true,            // canvas.toDataURL 필수
        fadeDuration: 0,
      });
    } catch (e) { finish("지도 초기화 실패: " + e); return; }
    repaint = setInterval(function () { try { map.triggerRepaint(); } catch (e) { } }, 400);
    map.on("error", function (e) {
      // 타일 일부 실패는 무시(렌더 지속) — 마지막 에러는 타임아웃 진단에 사용
      lastErr = String((e && e.error && e.error.message) || e || "");
      if (/style/i.test(lastErr) && stage === "init") finish("스타일 로드 실패: " + lastErr);
    });
    map.on("load", function () {
      stage = "load";
      _applyOverrides(map, theme.overrides);               // 아트스타일 맵 테마 적용
      // idle(타일 완전 로드)을 기다리되, 못 받으면 8초 후 캡처 시도(빈 캔버스면 재시도→라스터 폴백)
      var bestEffort = setTimeout(function () { capture(); }, 8000);
      function capture() {
        clearTimeout(bestEffort);                          // 리페인트는 finish()가 멈춤(재시도 동안 유지)
        captureNow();
      }
      map.once("idle", function () {                       // 타일 렌더 완료 시점
        stage = "idle";
        capture();
      });
      // 마커/경로는 지도에 굽지 않는다 — captureNow가 map.project()로
      // 위경도→캡처 픽셀 좌표(geo 사이드카)만 추출(AE 셰이프/텍스트 재료)
      var capTries = 0;
      function _isBlank(ctx, w, h) {                       // 픽셀 샘플링 — 전부 동일색이면 빈 캔버스
        try {
          var pts = [[w >> 1, h >> 1], [w >> 2, h >> 2], [3 * w >> 2, h >> 2], [w >> 2, 3 * h >> 2], [3 * w >> 2, 3 * h >> 2]];
          var first = null, same = true;
          for (var i = 0; i < pts.length; i++) {
            var d = ctx.getImageData(pts[i][0], pts[i][1], 1, 1).data;
            var key = d[0] + "," + d[1] + "," + d[2] + "," + d[3];
            if (first === null) first = key; else if (key !== first) same = false;
          }
          return same;                                     // 진짜 지도라면 5점이 같을 수 없음
        } catch (e) { return false; }
      }
      function captureNow() {
        // CEF에서 WebGL toDataURL 직접 읽기가 빈 화면이 되는 문제 →
        // 강제 리페인트 직후 프레임에 2D 캔버스로 drawImage 복사 후 읽기 + 빈 캔버스면 재시도
        try { map.triggerRepaint(); } catch (e) { }
        requestAnimationFrame(function () {
          try {
            var src = map.getCanvas();
            var cv = document.createElement("canvas");
            cv.width = src.width; cv.height = src.height;
            var ctx = cv.getContext("2d");
            ctx.drawImage(src, 0, 0);
            if (_isBlank(ctx, cv.width, cv.height) && capTries < 6) {
              capTries++;                                  // 타일이 아직 안 그려짐 — 1.2초 후 재시도
              setTimeout(captureNow, 1200);
              return;
            }
            var dark = theme.url === MAP_DARK_URL;
            var geo = { markers: [], route: [],
                        labelRgb: dark ? [232, 234, 237] : [26, 26, 26] };   // 테마 대비색(jsx 라벨용)
            // 캡처 캔버스는 DPR 배율일 수 있음 — project() 좌표를 캔버스 픽셀로 환산
            var sx = cv.width / map.getContainer().clientWidth || 1;
            (s.map_markers || []).forEach(function (m) {
              var pt = map.project(_swapLL(m.coord));
              geo.markers.push({ name: m.name || "", x: Math.round(pt.x * sx), y: Math.round(pt.y * sx) });
            });
            (s.map_route || []).forEach(function (c) {
              var rp = map.project(_swapLL(c));
              geo.route.push([Math.round(rp.x * sx), Math.round(rp.y * sx)]);
            });
            if (capTries >= 6) { finish("BLANK_CANVAS"); return; }   // 타일 미렌더 → 라스터 폴백
            finish(null, { dataUrl: cv.toDataURL("image/png"), geo: geo });
          } catch (e) { finish("캡처 실패: " + e); }
        });
      }
    });
    setTimeout(function () {
      stopRepaint();
      finish("지도 렌더 타임아웃(45s) — 단계: " + stage + (lastErr ? ", 마지막 에러: " + lastErr : ""));
    }, 45000);
  });
}

/* ── 라스터 폴백 — MapLibre(WebGL/워커)가 CEP에서 타일을 못 그릴 때:
   Carto 라스터 타일을 2D 캔버스에 직접 합성(워커·WebGL 불필요, 웹 메르카토르 수학만). */
var RASTER_THEMES = {
  warm_earth: { url: "https://basemaps.cartocdn.com/light_all/", filter: "sepia(0.32) saturate(0.85) brightness(1.03)", dark: false },
  clean_white: { url: "https://basemaps.cartocdn.com/light_all/", filter: "", dark: false },
  matte_slate: { url: "https://basemaps.cartocdn.com/dark_all/", filter: "", dark: true },
  dark_cyber: { url: "https://basemaps.cartocdn.com/dark_all/", filter: "saturate(1.3) hue-rotate(160deg)", dark: true },
  bright: { url: "https://basemaps.cartocdn.com/light_all/", filter: "", dark: false },
};

function _mercPx(lat, lng, z) {                    // 위경도 → 줌 z 세계 픽셀(타일 256 기준)
  var sc = 256 * Math.pow(2, z);
  var x = (lng + 180) / 360 * sc;
  var r = lat * Math.PI / 180;
  var y = (1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * sc;
  return [x, y];
}

function renderMapRaster(s) {
  return new Promise(function (resolve, reject) {
    var tm = s && s._theme && s._theme.map;
    var th;
    if (tm && tm.overrides) {
      th = { url: tm.tile === "dark" ? "https://basemaps.cartocdn.com/dark_all/" : "https://basemaps.cartocdn.com/light_all/",
             filter: tm.rasterFilter || "", dark: tm.tile === "dark" };
    } else {
      var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
      th = RASTER_THEMES[name] || RASTER_THEMES.warm_earth;
    }
    var W = 1920, H = 1080, z = s.map_zoom || 5;
    var zi = Math.max(0, Math.min(19, Math.round(z)));
    var scale = Math.pow(2, z - zi);                       // 소수 줌 → 정수 타일 줌 + 배율
    var ctr = s.map_center && s.map_center.length === 2 ? s.map_center : [37.5, 127.0];
    var c0 = _mercPx(ctr[0], ctr[1], zi);
    var tlx = c0[0] - W / (2 * scale), tly = c0[1] - H / (2 * scale);   // 좌상단(zi 세계 px)
    var cv = document.createElement("canvas"); cv.width = W; cv.height = H;
    var ctx = cv.getContext("2d");
    var maxT = Math.pow(2, zi);
    var x0 = Math.floor(tlx / 256), x1 = Math.floor((tlx + W / scale) / 256);
    var y0 = Math.max(0, Math.floor(tly / 256)), y1 = Math.min(maxT - 1, Math.floor((tly + H / scale) / 256));
    var jobs = [];
    for (var tx = x0; tx <= x1; tx++) {
      for (var ty = y0; ty <= y1; ty++) {
        (function (tx2, ty2) {
          var wx = ((tx2 % maxT) + maxT) % maxT;           // 경도 래핑
          jobs.push(new Promise(function (done) {
            var img = new Image();
            img.crossOrigin = "anonymous";                  // CORS — 캔버스 오염 방지
            var t = setTimeout(function () { done(null); }, 12000);
            img.onload = function () { clearTimeout(t); done({ img: img, tx: tx2, ty: ty2 }); };
            img.onerror = function () { clearTimeout(t); done(null); };
            img.src = th.url + zi + "/" + wx + "/" + ty2 + ".png";
          }));
        })(tx, ty);
      }
    }
    Promise.all(jobs).then(function (tiles) {
      var drawn = 0;
      try { ctx.filter = th.filter || "none"; } catch (e) { }
      for (var i = 0; i < tiles.length; i++) {
        var tl2 = tiles[i]; if (!tl2) continue;
        ctx.drawImage(tl2.img, (tl2.tx * 256 - tlx) * scale, (tl2.ty * 256 - tly) * scale,
                      256 * scale + 0.5, 256 * scale + 0.5);
        drawn++;
      }
      try { ctx.filter = "none"; } catch (e) { }
      if (!drawn) { reject("라스터 타일 전부 로드 실패(네트워크?)"); return; }
      var geo = { markers: [], route: [], labelRgb: th.dark ? [232, 234, 237] : [26, 26, 26] };
      function toPx(coord) {
        var p = _mercPx(coord[0], coord[1], zi);
        return [Math.round((p[0] - tlx) * scale), Math.round((p[1] - tly) * scale)];
      }
      (s.map_markers || []).forEach(function (m) {
        var q = toPx(m.coord);
        geo.markers.push({ name: m.name || "", x: q[0], y: q[1] });
      });
      (s.map_route || []).forEach(function (c) { geo.route.push(toPx(c)); });
      resolve({ dataUrl: cv.toDataURL("image/png"), geo: geo });
    });
  });
}

// 체크된(또는 단일) 씬의 지도 생성 → 백엔드 저장(이미지+geo 사이드카) → 행 갱신
// 1차: MapLibre(벡터, 테마 충실) → 실패/빈 캔버스 시 2차: 라스터 합성(워커·WebGL 불필요)
function genMapForScene(s) {
  return renderMapScene(s)
    .catch(function (e) { return renderMapRaster(s); })
    .then(function (res) {
    return fetch(BACKEND + "/api/scenes/map-image", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: s.sceneNumber,
                             dataUrl: res.dataUrl, geo: res.geo }),
    }).then(function (r) { return r.json(); });
  });
}
