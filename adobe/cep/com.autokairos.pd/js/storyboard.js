/* 스토리보드 프로덕션 시트 — 씬당 1행. BACKEND/$/SELECTED_PROJECT/SELECTED_CHARACTER는 main.js 전역. */

function _esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/* 진행 점 — 작업 칸에서 완료 상태 표시(●=완료, ○=미완) */
function _dot(label, on) {
  return '<span class="dot ' + (on ? "on" : "off") + '" title="' + label + (on ? " 완료" : " 미완") + '"></span>';
}

/* 컬럼 너비(px) — 4컬럼(씬#·이미지·스크립트·작업) 드래그 조절 + localStorage 저장 */
var COL_KEY = "ak_sheet_cols";
var COL_DEFAULT = [30, 200, 300, 260];      // 씬# · 이미지 · 스크립트 · 작업
var COLW = _loadCols();

function _loadCols() {
  // 작업 컬럼은 260px 이 최소다. 버튼이 기호(▣ ♪ ✎ ⤓)일 때 잡은 150px 로는
  // 「이미지 재생성」 한 글자도 안 들어가고 목소리 고르개도 눌려 버린다.
  // 저장해 둔 값이 그보다 좁으면 끌어올린다 — 예전 폭이 남아 있으면 새 버튼이
  // 계속 찌그러진 채로 보인다.
  var MIN_WORK = 260;
  try {
    var s = window.localStorage.getItem(COL_KEY);
    if (s) {
      var a = JSON.parse(s);
      if (a && a.length === 4) {
        if (a[3] < MIN_WORK) a[3] = MIN_WORK;
        return a;
      }
    }
  } catch (e) {}
  return COL_DEFAULT.slice();
}

function _persistCols() {
  try { window.localStorage.setItem(COL_KEY, JSON.stringify(COLW)); } catch (e) {}
}

/* 씬별 원본 나레이션 — blur 시 변경 감지용 */
var NAR_ORIG = {};

function _colsCss() {
  return COLW.map(function (w) { return w + "px"; }).join(" ");
}

function _applyCols() {
  var el = $("sheet");
  if (el) el.style.setProperty("--cols", _colsCss());
}

function _autosizeAll() {
  var tas = $("sheet").querySelectorAll("textarea.nar");
  for (var i = 0; i < tas.length; i++) _autosize(tas[i]);
}

function _bindColResize() {
  var handles = $("sheet").querySelectorAll(".col-resize");
  for (var i = 0; i < handles.length; i++) {
    handles[i].title = "끌어서 너비 조절 · 두 번 누르면 기본값";
    // 두 번 누르면 그 컬럼만 기본 너비로. 잘못 끌어 좁혀 놓고 되돌릴 방법이 없었다.
    handles[i].addEventListener("dblclick", function (e) {
      e.preventDefault(); e.stopPropagation();
      var idx = parseInt(this.getAttribute("data-col"), 10);
      COLW[idx] = COL_DEFAULT[idx] || 150;
      _applyCols(); _autosizeAll(); _persistCols();
    });
    handles[i].addEventListener("mousedown", function (e) {
      e.preventDefault();
      var idx = parseInt(this.getAttribute("data-col"), 10);
      var startX = e.clientX, startW = COLW[idx] || 100;
      var grip = this;
      grip.classList.add("dragging");     // 끄는 동안 손잡이가 보이게
      function move(ev) {
        COLW[idx] = Math.max(24, startW + (ev.clientX - startX));
        _applyCols();
        _autosizeAll();          // 폭 변하면 줄바꿈 → 세로 높이 재계산
      }
      function up() {
        grip.classList.remove("dragging");
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
        _persistCols();          // 설정값 저장(다음에도 유지)
      }
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    });
  }
}

// 디자인 토큰(ae_tokens) — 시트 미리보기가 색/크기를 AE 빌드와 동일 소스로 사용
var TOKENS = null;
function _loadTokens() {
  if (TOKENS) return Promise.resolve(TOKENS);
  return fetch(BACKEND + "/api/tokens").then(function (r) { return r.json(); })
    .then(function (j) { TOKENS = j || {}; return TOKENS; })
    .catch(function () { TOKENS = {}; return TOKENS; });
}

// 컴프 결과 미리보기 — jsx renderLayout(1920 기준)을 200px 폭으로 축소 미러링.
// 이미지 씬=이미지+자막 오버레이, 레이아웃 씬=셰이프/텍스트 근사 렌더(동일 토큰).
function _previewHTML(s, dir) {
  var T = TOKENS || {}, t = T.type || {};
  var c = (s._theme && s._theme.colors) || T.colors || {};   // 씬 resolve된 테마 색 우선
  function px(v) { return (v * 200 / 1920).toFixed(1) + "px"; }      // 1920 디자인 px → 미리보기 px
  function rgb(a, fb) { a = a || fb; return "rgb(" + a[0] + "," + a[1] + "," + a[2] + ")"; }
  var BG = rgb(c.bgRgb, [35, 38, 43]), TX = rgb(c.textRgb, [232, 234, 237]),
      MU = rgb(c.mutedRgb, [154, 160, 166]), AC = rgb(c.accentRgb, [74, 144, 217]);
  // 자막 미리보기 — 나레이션 첫 ~20자(어절 경계), 하단 중앙
  var nar = (s.narration || "").replace(/\s+/g, " ").trim(), sub1 = "";
  if (nar) {
    var ws = nar.split(" ");
    for (var wi = 0; wi < ws.length; wi++) {
      if (sub1 && (sub1 + " " + ws[wi]).length > 20) break;
      sub1 = sub1 ? sub1 + " " + ws[wi] : ws[wi];
    }
  }
  var subEl = sub1 ? '<div class="pv-subtitle" style="font-size:' + px(t.subtitle || 54) + '">' + _esc(sub1) + "</div>" : "";
  var inner = "";

  /* 도해 요소 — 배경 위에 백분율 좌표로 얹는다.
     패널에 이 분기가 아예 없어, 요소를 만들어 배치까지 끝낸 씬도 배경 그림만
     보였다. v3 가 정한 자리(left·top·size, 화면 대비 %)를 그대로 읽는다 —
     여기서 따로 배치하면 v3·대시보드·어도비 셋이 어긋난다. */
  var ig = s.infographic;
  if (ig && ig.items && ig.items.length) {
    var base = "";
    if ((ig.background === "scene" || ig.background === "scene_blur") && s._image) {
      base = '<img class="main" src="file://' + dir + "/" + s._image + "?t=" + IV_STAMP + '"'
           + (ig.background === "scene_blur" ? ' style="filter:blur(3px)"' : "") + '>';
    }
    var els = "";
    for (var q = 0; q < ig.items.length; q++) {
      var it = ig.items[q];
      if (!it || !it.src) continue;
      els += '<img class="pv-abs" src="file://' + dir + "/" + it.src + '"'
           + ' style="left:' + (it.left || 50) + '%;top:' + (it.top || 50) + '%;'
           + 'width:' + (it.size || 20) + '%;transform:translate(-50%,-50%)">';
    }
    return '<div class="pv" style="background:' + BG + '">' + base + els + subEl + "</div>";
  }

  if (s.layout === "map" && !s._map_rendered) {
    /* 좌표·마커가 다 들어와 있어도 누가 🗺 지도를 누르기 전에는 지도가
       생기지 않는다. 그런데 v3 가 그려 준 삽화가 링크돼 있어 「다 된 것」처럼
       보였다 — 지도 씬 셋이 그 상태로 남아 있었다. 아직임을 화면에 적는다. */
    var mBadge = '<div class="layout-badge" style="position:absolute;left:4%;top:4%;'
      + 'padding:3px 7px;font-size:10px;background:rgba(0,0,0,0.66);border-color:#e8b339;'
      + 'color:#e8b339">🗺 지도 미렌더 — 체크 후 「🗺 지도」</div>';
    if (!s._image) return '<div class="layout-badge">map — 🗺 지도 버튼으로 렌더</div>';
    return '<div class="pv" style="background:' + BG + '">'
      + '<img class="main" src="file://' + dir + "/" + s._image + "?t=" + IV_STAMP + '">' + mBadge + subEl + "</div>";
  }
  if (!s.layout || s.layout === "cinematic" || s.layout === "map") {
    if (!s._image) return '<div style="color:#666;font-size:11px">(없음)</div>';
    return '<div class="pv" style="background:' + BG + '">'
      + '<img class="main" src="file://' + dir + "/" + s._image + "?t=" + IV_STAMP + '">' + subEl + "</div>";
  }
  if (s.layout === "headline_only") {
    inner = '<div class="pv-abs" style="left:50%;top:30%;width:' + px(120) + ";height:" + px(10) + ";background:" + AC + ';transform:translateX(-50%)"></div>'
      + '<div class="pv-abs pv-headline" style="left:8%;width:84%;top:34%;font-size:' + px(t.headline || 110) + ";color:" + TX + ';text-align:center;line-height:1.25">' + _esc(s.headline || "") + "</div>"
      + (s.sub ? '<div class="pv-abs pv-body" style="left:15%;width:70%;top:62%;font-size:' + px(t.sub || 48) + ";color:" + MU + ';text-align:center">' + _esc(s.sub) + "</div>" : "");
  } else if (s.layout === "items_list") {
    inner = '<div class="pv-abs pv-headline" style="left:0;width:100%;top:11%;font-size:' + px((t.sub || 48) * 1.5) + ";color:" + TX + ';text-align:center">' + _esc(s.headline || "") + "</div>"
      + '<div class="pv-abs" style="left:16%;width:68%;top:23.5%;height:1px;background:' + AC + '"></div>';
    var items = s.items || [], gpct = Math.min(12, 58 / Math.max(1, items.length));
    for (var ii = 0; ii < items.length; ii++) {
      var typ = 33 + ii * gpct;
      inner += '<div class="pv-abs" style="left:16%;top:' + (typ - 1.8) + "%;width:" + px(12) + ";height:" + px(42) + ";background:" + AC + '"></div>'
        + '<div class="pv-abs pv-body" style="left:20%;width:62%;top:' + (typ - 2.2) + "%;font-size:" + px(t.item || 52) + ";color:" + TX + ';text-align:left;white-space:nowrap;overflow:hidden">' + _esc(items[ii]) + "</div>";
    }
  } else if (s.layout === "metric_spotlight") {
    inner = '<div class="pv-abs pv-number" style="left:0;width:100%;top:32%;font-size:' + px(t.metric || 220) + ";color:" + AC + ';text-align:center;line-height:1">' + _esc(s.value || "") + "</div>"
      + '<div class="pv-abs" style="left:50%;top:58.5%;width:' + px(220) + ";height:" + px(5) + ";background:" + AC + ';transform:translateX(-50%)"></div>'
      + '<div class="pv-abs pv-body" style="left:15%;width:70%;top:63%;font-size:' + px(t.metricLabel || 54) + ";color:" + TX + ';text-align:center">' + _esc(s.label || "") + "</div>";
  } else if (s.layout === "bar") {
    inner = '<div class="pv-abs pv-headline" style="left:0;width:100%;top:9%;font-size:' + px((t.sub || 48) * 1.4) + ";color:" + TX + ';text-align:center">' + _esc(s.headline || "") + "</div>"
      + '<div class="pv-abs" style="left:13%;width:74%;top:76%;height:1px;background:' + MU + '"></div>';
    var ch = s.chart || {}, vals = ch.values || [], labels = ch.labels || [];
    var n2 = Math.max(1, vals.length), maxV = 0;
    for (var vi = 0; vi < vals.length; vi++) if (vals[vi] > maxV) maxV = vals[vi];
    for (var bi = 0; bi < vals.length; bi++) {
      var bhPct = maxV ? (vals[bi] / maxV) * 42 : 0;                 // jsx maxH=H*0.42
      var gw = 70 / n2, bxPct = 15 + gw * bi + gw * 0.225, bwPct = gw * 0.55;
      var barStyle = "background:" + AC;
      var CS = s.chartSpec || {};
      var pk = CS.patternKind;
      if (pk && pk !== "solid" && pk !== "none") {
        // 미리보기 해칭 — jsx addBarShape와 같은 종류로(일치): 한방향/교차/세로/점
        var gap = Math.max(3, (CS.patternSpacing || 12) / 4);
        var line = AC + " 0 1.5px,transparent 1.5px " + gap + "px";
        var faint = AC.replace("rgb", "rgba").replace(")", "," + (CS.patternOpacity || 0.4) + ")");
        var bg;
        if (pk === "dot_sparse") {
          bg = "radial-gradient(" + AC + " 22%,transparent 23%)," + faint;
          barStyle = "background:" + bg + ";background-size:" + (gap * 1.6) + "px " + (gap * 1.6) + "px";
        } else {
          var grads;
          if (pk === "crosshatch_light") {                 // 양방향 X자
            grads = "repeating-linear-gradient(45deg," + line + "),repeating-linear-gradient(-45deg," + line + ")";
          } else if (pk === "vertical_stripe") {           // 세로
            grads = "repeating-linear-gradient(90deg," + line + ")";
          } else {                                         // diagonal_hatch / wide_diagonal — 한 방향
            grads = "repeating-linear-gradient(45deg," + line + ")";
          }
          barStyle = "background:" + grads + "," + faint;
        }
        if (CS.outlineWidth) barStyle += ";outline:1px solid " + AC;
      }
      inner += '<div class="pv-abs" style="left:' + bxPct + "%;width:" + bwPct + "%;top:" + (76 - bhPct) + "%;height:" + bhPct + "%;" + barStyle + '"></div>'
        + '<div class="pv-abs pv-body" style="left:' + (bxPct - gw * 0.2) + "%;width:" + (bwPct + gw * 0.4) + "%;top:78.5%;font-size:" + px(t.barLabel || 36) + ";color:" + MU + ';text-align:center;white-space:nowrap;overflow:hidden">' + _esc(labels[bi] || "") + "</div>"
        + '<div class="pv-abs pv-bold" style="left:' + (bxPct - gw * 0.2) + "%;width:" + (bwPct + gw * 0.4) + "%;top:" + (76 - bhPct - 4.5) + "%;font-size:" + px(t.barValue || 40) + ";color:" + TX + ';text-align:center">' + _esc(String(vals[bi]) + (ch.unit || "")) + "</div>";
    }
  } else if (s.layout === "quote") {
    inner = '<div class="pv-abs pv-quote" style="left:12%;top:24%;font-size:' + px((t.quote || 64) * 2.2) + ";color:" + AC + ';line-height:1">“</div>'
      + '<div class="pv-abs pv-quote" style="left:19%;width:62%;top:32%;font-size:' + px(t.quote || 64) + ";color:" + TX + ';text-align:center;line-height:1.5">' + _esc(s.quote_text || "") + "</div>"
      + '<div class="pv-abs pv-quote" style="right:12%;top:58%;font-size:' + px((t.quote || 64) * 2.2) + ";color:" + AC + ';line-height:1">”</div>'
      + '<div class="pv-abs pv-quote" style="left:19%;width:62%;top:72%;font-size:' + px(t.quoteWho || 40) + ";color:" + MU + ';text-align:right">— ' + _esc(s.quote_who || "") + "</div>";
  } else if (s._image) {
    /* **아직 그리는 법을 모르는 레이아웃이라도 그림은 버리지 않는다.**
       timeline·flow 처럼 전용 분기가 없는 이름이 오면 예전에는 이름표만
       띄우고 씬 이미지를 통째로 감췄다 — 레이아웃 정보가 넘어오기 시작하자
       멀쩡히 있던 그림이 사라진 것처럼 보였다. v3 에서 이 씬들은 **그림이
       배경이고 그 위에 항목이 얹히는** 구조다. */
    inner = '<div class="layout-badge" style="position:absolute;left:4%;top:4%;'
          + 'padding:2px 6px;font-size:10px;opacity:0.75">' + _esc(s.layout) + '</div>';
  } else {
    return '<div class="layout-badge">' + _esc(s.layout) + "</div>";
  }
  // 그림이 있으면 항상 배경으로 깐다. 레이아웃 요소는 그 위에 얹힌다.
  var bgImg = s._image
    ? '<img class="main" src="file://' + dir + "/" + s._image + "?t=" + IV_STAMP + '">' : "";
  return '<div class="pv" style="background:' + BG + '">' + bgImg + inner + subEl + "</div>";
}

// 「시트 불러오기」 버튼이 화면에만 있고 아무 데도 묶여 있지 않았다.
// 눌러도 반응이 없어 패널이 죽은 것처럼 보였다.
document.addEventListener("DOMContentLoaded", function () {
  var b = document.getElementById("btnLoadSheet");
  if (b) b.addEventListener("click", function () { loadSheet(); });
});

function loadSheet() {
  if (!SELECTED_PROJECT) { $("sheet").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("sheet").textContent = "불러오는 중...";
  // 목소리 프리셋을 먼저 받는다 — 행마다 고르개를 그려야 하므로 시트보다 앞서야 한다
  _loadTokens().then(loadVoices).then(function () {
  return fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", list = j.scenes || [];
        // 모달들이 `file://` 미리보기에 쓴다. 시트를 읽을 때 잡아 두지 않으면
        // 모달이 자기 요청을 기다리는 동안 깨진 그림이 잠깐 뜬다.
        IMG_DIR = dir || IMG_DIR;
      if (!list.length) { $("sheet").textContent = "(씬 없음 — 씬 분해 먼저)"; return; }
      NAR_ORIG = {};
      list.forEach(function (s) { NAR_ORIG[s.sceneNumber] = s.narration || ""; });
      /* 범위 고르기와 나레이션 찾기는 **시트 밖**(`#sheet-tools`)에 그린다.
         시트 안에 있으면 목록과 함께 스크롤돼, 아래로 내려가면 화면에서
         사라진다 — 체크하고 버튼을 누르러 매번 맨 위로 올라가야 했다. */
      /* 범위 고르기와 나레이션 찾기를 **한 줄로** 둔다. 두 줄을 차지할 만큼
         큰 일이 아니고, 머리가 두꺼워지면 정작 씬 목록이 좁아진다.
         더하기·이것만·빼기는 기호(＋ ＝ －)로 줄인다 — 뜻은 툴팁에 남긴다. */
      var tools =
          '<div class="sel-range">'
          // 씬이 백 개를 넘으면 하나씩 누르는 것이 일이다. 범위로 고른다.
        +   '<input id="selRange" type="text" placeholder="예: 1-10, 25, 40-52" '
        +     'title="범위나 번호를 쉼표로. 엔터로 적용">'
        +   '<button id="selRangeAdd" class="sr-ico" title="고른 것에 더한다">＋</button>'
        +   '<button id="selRangeOnly" class="sr-ico" title="이것만 고른다">＝</button>'
        +   '<button id="selRangeOff" class="sr-ico" title="고른 것에서 뺀다">－</button>'
        +   '<span id="selRangeMsg"></span>'
        +   '<span class="sr-div"></span>'
          // 나레이션 찾기 — 씬이 백 개를 넘으면 눈으로 훑을 수 없다
        +   '<input id="sbFind" type="text" placeholder="🔎 나레이션 찾기">'
        +   '<span id="sbFindMsg"></span>'
        + '</div>';
      var tb = $("sheet-tools");
      if (tb) tb.innerHTML = tools;

      var head = '<div class="sheet-head">'
        + '<div><input type="checkbox" id="selAllScenes" title="전체 선택/해제">#<span class="col-resize" data-col="0"></span></div>'
        + '<div>이미지<span class="col-resize" data-col="1"></span></div>'
        + '<div>스크립트<span class="col-resize" data-col="2"></span></div>'
        + '<div>작업<span class="col-resize" data-col="3"></span></div>'
        + '</div>'
        + (tb ? "" : tools);          // 옛 마크업이면 예전처럼 시트 안에 둔다
      $("sheet").innerHTML = head + list.map(function (s) { return renderRow(s, dir); }).join("");
      _applyCols();
      _bindColResize();
      bindRows();
      loadThemes();
      var sa = $("selAllScenes");
      if (sa) sa.addEventListener("change", function () {
        var on = this.checked;
        SEL_SCENES = {};
        var cbs = $("sheet").querySelectorAll("input.scene-sel");
        for (var c = 0; c < cbs.length; c++) {
          cbs[c].checked = on;
          if (on) SEL_SCENES[cbs[c].getAttribute("data-scene")] = true;
        }
      });
      _bindRangeSelect();
      _bindFind();
      // 레이아웃 후 나레이션 높이 재계산(탭 표시 직후 scrollHeight=0 방지)
      if (window.requestAnimationFrame) requestAnimationFrame(_autosizeAll); else _autosizeAll();
    });
  })
    .catch(function (e) { $("sheet").textContent = "오류: " + e; });
}

/* 저장된 전용 텍스트가 원고와 다르면 배지 + 원고에서 다시 채우기 버튼.
   원고를 고쳐도 전용 텍스트를 자동으로 덮어쓰지 않으므로, 어긋남을 눈에 보이게 한다. */
/* 백엔드 `_clean_text` 와 같은 정리를 한다. 자동 저장되는 값은 이 정리를
   거친 것이라, 날것끼리 비교하면 **원고에 괄호나 이모지가 있기만 해도**
   「원고와 다름」이 뜬다. 디아지오 141개 중 49개가 그 헛경보였고, 진짜로
   손봐야 할 72개가 그 속에 묻혔다. */
function _clean(t) {
  return (t || "")
    .replace(/\([^)]*\)/g, " ")
    .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function _teBadge(n, kind, stored, narration) {
  var st = (stored || "").trim();
  if (!st || _clean(st) === _clean(narration)) return "";
  return ' <span class="te-diff">원고와 다름</span>'
    + '<button class="mini te-reset" data-scene="' + n + '" data-kind="' + kind + '"'
    + ' title="이 칸을 비워 원고 기준으로 되돌립니다">원고에서 다시 채우기</button>';
}

/* ===== 레이어 목록 — 포토샵식. 기본은 접힘(썸네일 띠), 펴면 세로 목록. ===== */
var LYR_OPEN = {};      // {sceneNumber: true} — 재렌더에도 펼침 유지
var LYR_SEL = {};       // {sceneNumber: {stem: true}} — 벡터화 선택(눈과 무관)

function _lyrStem(rel) {
  return rel.split("/").pop().replace(/\.(png|svg)$/i, "");
}

/* 접힌 상태 — 지금까지 쓰던 가로 썸네일 띠(클릭하면 펴진다). */
function _lyrStrip(s, dir) {
  var meta = s._layer_meta || {};
  var html = "";
  for (var i = 0; i < (s._layers || []).length; i++) {
    var stem = _lyrStem(s._layers[i]);
    var m = meta[stem] || {};
    if (m.removed) continue;
    html += '<img class="lyr" src="file://' + dir + '/' + s._layers[i] + '"'
          + ' title="' + _esc(m.name || stem) + '"'
          + (m.hidden ? ' style="opacity:0.35"' : '') + '>';
  }
  return html;
}

/* 펼친 상태 — 세로 목록. z 오름차순, 배경이 맨 위(AE 최하단). */
function renderLayerList(s, dir) {
  var n = s.sceneNumber;
  var meta = s._layer_meta || {};
  var rels = (s._layers || []).slice();
  rels.sort(function (a, b) {
    var ma = meta[_lyrStem(a)] || {}, mb = meta[_lyrStem(b)] || {};
    if ((ma.kind === "bg") !== (mb.kind === "bg")) return ma.kind === "bg" ? -1 : 1;
    var za = (ma.z == null) ? 9999 : ma.z, zb = (mb.z == null) ? 9999 : mb.z;
    if (za !== zb) return za - zb;
    return a < b ? -1 : 1;
  });
  var sel = LYR_SEL[n] || {};
  var live = "", gone = "";
  for (var i = 0; i < rels.length; i++) {
    var stem = _lyrStem(rels[i]);
    var m = meta[stem] || {};
    var isBg = m.kind === "bg";
    var kindLabel = isBg ? "배경" : (m.kind === "character" ? "인물" : "사물");
    var thumb = '<img class="lyr" src="file://' + dir + '/' + rels[i] + '">';
    var nameCell = '<span class="lyr-name" title="' + _esc(stem) + '">'
                 + _esc(m.name || stem) + '</span>'
                 + '<span class="lyr-kind">' + kindLabel + '</span>'
                 + (m.svg ? '<span class="lyr-badge">SVG</span>' : '');
    if (m.removed) {
      gone += '<div class="lyr-row gone" data-scene="' + n + '" data-layer="' + _esc(stem) + '">'
            +   thumb + nameCell
            +   '<button class="lyr-restore" title="이 레이어를 프로젝트에 되돌립니다">↩ 복구</button>'
            + '</div>';
      continue;
    }
    live += '<div class="lyr-row' + (m.hidden ? ' off' : '') + '"'
          +   ' data-scene="' + n + '" data-layer="' + _esc(stem) + '">'
          +   '<input type="checkbox" class="lyr-pick"' + (sel[stem] ? ' checked' : '')
          +     ' title="벡터화 대상 선택">'
          +   '<button class="lyr-eye" title="패널 미리보기에서만 끕니다 — 내보내기에는 그대로 들어갑니다">'
          +     (m.hidden ? '🚫' : '👁') + '</button>'
          +   thumb + nameCell
          +   (isBg ? '<button class="lyr-regen" title="씬을 다시 분리합니다 — 레이어 전체가 새로 만들어집니다">↻</button>' : '')
          +   (m.svg ? '<button class="lyr-revec" title="이 레이어를 다시 벡터화합니다(1크레딧)">↻SVG</button>'
                     : '<button class="lyr-revec" title="이 레이어를 벡터화합니다(1크레딧)">SVG</button>')
          +   (isBg ? '' : '<button class="lyr-rm" title="프로젝트에서 뺍니다 — 파일은 남고 되돌릴 수 있습니다">🗑</button>')
          + '</div>';
  }
  return '<div class="lyr-list">' + live
       + (gone ? '<div class="lyr-sep">제거됨</div>' + gone : '')
       + '</div>';
}

/* 레이어 합성 미리보기 — 배경판을 깔고 요소를 bbox 백분율로 얹는다.
   눈을 끈 레이어는 그리지 않는다. 백엔드 호출 없이 이미 받은 PNG만 쓴다. */
function renderComposite(s, dir) {
  var meta = s._layer_meta || {};
  var rels = (s._layers || []).slice();
  if (rels.length < 2) return "";                 // 배경 + 요소가 있어야 합성이다
  rels.sort(function (a, b) {
    var ma = meta[_lyrStem(a)] || {}, mb = meta[_lyrStem(b)] || {};
    if ((ma.kind === "bg") !== (mb.kind === "bg")) return ma.kind === "bg" ? -1 : 1;
    var za = (ma.z == null) ? 9999 : ma.z, zb = (mb.z == null) ? 9999 : mb.z;
    return za - zb;
  });
  var bgRel = null, html = "";
  for (var i = 0; i < rels.length; i++) {
    var stem = _lyrStem(rels[i]);
    var m = meta[stem] || {};
    if (m.removed || m.hidden) continue;
    var src = 'file://' + dir + '/' + rels[i];
    if (m.kind === "bg" && !bgRel) {
      bgRel = src;
      continue;
    }
    if (m.box) {
      html += '<img class="comp-el" src="' + src + '"'
            + ' style="left:' + m.box.left + '%;top:' + m.box.top + '%;width:'
            + m.box.width + '%">';
    } else {
      html += '<img class="comp-el full" src="' + src + '">';   // bbox 없는 레거시 풀프레임
    }
  }
  if (!bgRel) {
    // 배경을 껐거나 없다 — 씬 이미지를 바탕으로 쓴다(요소 위치 기준이 같다)
    if (!s._image) return "";
    bgRel = 'file://' + dir + '/' + s._image;
  }
  return '<div class="comp"><img class="comp-bg" src="' + bgRel + '">' + html + '</div>';
}

function _lyrHead(s) {
  var n = s.sceneNumber;
  var open = !!LYR_OPEN[n];
  var count = 0, meta = s._layer_meta || {};
  for (var i = 0; i < (s._layers || []).length; i++) {
    if (!(meta[_lyrStem(s._layers[i])] || {}).removed) count++;
  }
  return '<div class="lyr-head">'
       + '<button class="lyr-toggle" data-scene="' + n + '">' + (open ? '▾' : '▸') + '</button>'
       + '<span>레이어 ' + count + '</span>'
       + (open ? '<button class="lyr-vec-all" data-scene="' + n + '"'
                 + ' title="SVG가 없는 레이어를 모두 벡터화합니다(레이어당 1크레딧)">전체 벡터화</button>'
               + '<button class="lyr-vec-sel" data-scene="' + n + '"'
                 + ' title="체크한 레이어만 벡터화합니다">선택 벡터화</button>'
             : '')
       + '</div>';
}

function renderRow(s, dir) {
  var n = s.sceneNumber;
  // 레이어가 있으면 합성 미리보기(눈 토글이 즉시 보인다), 없으면 기존 컴프 미리보기.
  var comp = renderComposite(s, dir);
  var media = comp || _previewHTML(s, dir);   // 컴프 결과 미리보기(배경+레이아웃+자막)
  var hasLayers = (s._layers || []).length > 0;
  var layerBlock = hasLayers
    ? (_lyrHead(s) + (LYR_OPEN[n] ? renderLayerList(s, dir)
                                  : '<div class="lyr-strip">' + _lyrStrip(s, dir) + '</div>'))
    : "";
  var chars = (s.characters || []).join(", ");
  var st = s._status || {};
  return ''
    + '<div class="sheet-row" data-scene="' + n + '" ondragover="event.preventDefault()" ondrop="dropOnScene(event,' + n + ')">'
    // 씬# — 체크박스로 선택 → 상단 도구상자 버튼이 체크된 씬에 일괄 실행
    + '  <div class="col-num">'
    +      '<label class="scene-sel-wrap"><input type="checkbox" class="scene-sel" data-scene="' + n + '"'
    +        (SEL_SCENES[n] ? ' checked' : '') + '> ' + n + '</label>'
    + '  </div>'
    // 이미지 미리보기 + 레이어 썸네일(클릭=씬 위에 빨간 윤곽선 오버레이)
    + '  <div class="col-img">'
    +      (s._image ? '<button class="unlink-img" data-scene="' + n + '" title="씬 이미지 링크 해제">✕</button>' : '')
    /* 비디오는 **미리보기 자리에서 바꿔 본다.** 아래에 따로 플레이어를 두면
       같은 씬 미리보기가 둘이 되어 자리만 잡아먹는다. 🎞 를 누르면 그림 위에
       비디오가 덮이고, 다시 누르면 그림으로 돌아온다. */
    +      (s.videoRef
        ? ('<button class="vid-toggle" data-scene="' + n + '" '
           + 'data-src="' + _esc("file://" + dir + "/" + s.videoRef) + '" '
           + 'title="' + _esc(String(s.videoRef).split("/").pop()) + '">🎞 영상</button>')
        : '')
    + '    <div class="img-wrap">' + media + '</div>'
    /* 후보 판본 — 씬마다 여러 판을 쌓아 두고 하나를 고르는 구조인데
       패널에는 고른 것만 보였다. 눌러서 바로 되돌릴 수 있게 띠로 깐다. */
    + '    <div class="img-vers" data-scene="' + n + '"></div>'
    +      layerBlock
    + '  </div>'
    // 스크립트(나레이션)
    + '  <div class="col-script">'
    + '    <div class="row-title">' + _esc(s.title || "") + '</div>'
    + '    <textarea class="nar" data-scene="' + n + '" rows="3">' + _esc(s.narration || "") + '</textarea>'
    + '  </div>'
    // 작업 — 진행 점(●=완료) + 플레이어 + 상태(실행 버튼은 시트 상단 도구상자)
    + '  <div class="col-work">'
    +      '<div class="work-dots" title="이미지·레이어·음성·모션 진행 상태">'
    +        _dot("이미지", st.image) + _dot("레이어", st.layers) + _dot("음성", st.tts) + _dot("모션", st.motion)
    +      '</div>'
    // 씬 전용 버튼 — 체크박스와 무관하게 이 씬에만 즉시 실행
    +      '<div class="row-acts">'
    /* 기호 버튼(▣ ♪ ✎ ⤓)은 무엇을 하는 단추인지 알 수 없어 글자로 바꾼다.
       ♪ 와 ✎ 는 둘 다 TTS 를 다시 만든다 — ✎ 는 텍스트를 고쳐서 그 자리에서
       다시 만드는 것이라, 「수정」이 아니라 「TTS 재생성」이 하는 일에 맞다. */
    +        '<button class="ra" data-act="img" data-scene="' + n + '" title="참조와 프롬프트를 골라 다시 그립니다">이미지 재생성</button>'
    +        '<button class="ra" data-act="txt" data-scene="' + n + '" title="TTS·자막 텍스트를 고쳐 다시 만듭니다">TTS 재생성</button>'
    +        '<button class="ra" data-act="vid" data-scene="' + n + '" title="이 씬 그림으로 영상을 만듭니다 (힉스필드)">🎞 비디오</button>'
    +        '<button class="ra" data-act="tl" data-scene="' + n + '" title="이 씬을 현재 타임라인에 배치합니다">import</button>'
    +      '</div>'
    // 텍스트 편집 패널(✎ 토글) — TTS용/자막용 분리
    +      '<div class="txt-edit" data-scene="' + n + '" hidden>'
    +        '<div class="te-label">TTS 텍스트 <span class="te-hint">발음용 — 비우면 원고 사용</span>'
    +          _teBadge(n, "tts", s.narration_tts, s.narration) + '</div>'
    +        '<textarea class="te-tts" data-scene="' + n + '" rows="3">' + _esc(s._tts_text || "") + '</textarea>'
    +        '<div class="te-label">자막 텍스트 <span class="te-hint">화면 표시용 — 비우면 원고 사용</span>'
    +          _teBadge(n, "sub", s.subtitle_text, s.narration) + '</div>'
    +        '<textarea class="te-sub" data-scene="' + n + '" rows="3">' + _esc(s._subtitle_text || "") + '</textarea>'
    +        voiceSelectHtml(n)
    +        '<div class="te-acts">'
    +          '<button class="mini te-save" data-scene="' + n + '">저장</button>'
    +          '<button class="mini te-regen" data-scene="' + n + '">저장 후 TTS 재생성</button>'
    +        '</div>'
    +      '</div>'
    + (chars ? '<div class="work-chars">👤 ' + _esc(chars) + '</div>' : '')
    +      (s._audio
        ? ('<div class="tts-player">'
           + '<button class="tts-play" title="재생/정지">▶</button>'
           + '<span class="tts-dur">' + (s._audio_dur ? _fmtDur(s._audio_dur) : "--:--") + '</span>'
           /* 파일 이름이 늘 같고(`tts_{sid}.mp3`) 재생성은 덮어쓴다. 캐시버스터가
              없으면 CEP(Chromium)가 옛 음성을 계속 재생해, 제대로 다시 만들었는데도
              「안 바뀐다」로 보인다. 길이를 붙여 파일이 바뀌면 주소도 바뀌게 한다. */
           + '<audio class="tts-audio" preload="none" src="file://' + dir + '/' + s._audio
           + '?t=' + Math.round((s._audio_dur || 0) * 1000) + '"></audio>'
           + '</div>')
        : '')
    + '    <div class="row-status" data-scene="' + n + '"></div>'
    + '  </div>'
    + '</div>';
}

function _autosize(ta) {
  ta.style.height = "auto";
  ta.style.height = (ta.scrollHeight + 2) + "px";   // 내용 높이에 맞춰 확장(스크롤 없음)
}

function _fmtDur(sec) {
  sec = Math.round(sec || 0);
  var m = Math.floor(sec / 60), s = sec % 60;
  return m + ":" + (s < 10 ? "0" : "") + s;
}

/* 커스텀 TTS 플레이어 — 좁은 칸에서도 재생 버튼·길이가 보이게 */
function _bindTtsPlayer(pl) {
  var audio = pl.querySelector(".tts-audio");
  var btn = pl.querySelector(".tts-play");
  var durEl = pl.querySelector(".tts-dur");
  if (!audio || !btn) return;
  audio.addEventListener("loadedmetadata", function () {
    if (isFinite(audio.duration)) durEl.textContent = _fmtDur(audio.duration);
  });
  btn.addEventListener("click", function () {
    if (audio.paused) { audio.play(); btn.textContent = "⏸"; }
    else { audio.pause(); btn.textContent = "▶"; }
  });
  audio.addEventListener("ended", function () { btn.textContent = "▶"; });
}

/* scope: 바인딩 대상 루트(기본 전체 시트). refreshRow는 새 행만 넘겨 중복 리스너 방지. */
function bindRows(scope) {
  scope = scope || $("sheet");
  // 나레이션: 저장 버튼 없이 blur 시 변경되었으면 확인 후 저장(아니오=되돌림)
  var tas = scope.querySelectorAll("textarea.nar");
  for (var t = 0; t < tas.length; t++) {
    _autosize(tas[t]);
    tas[t].addEventListener("input", function () { _autosize(this); });
    tas[t].addEventListener("blur", function () {
      var n = this.getAttribute("data-scene");
      var orig = NAR_ORIG[n] || "";
      if (this.value === orig) return;
      if (confirm("씬 " + n + " 나레이션 변경사항을 저장하시겠습니까?")) {
        saveNarration(n);
        NAR_ORIG[n] = this.value;
      } else {
        this.value = orig;   // 되돌림
        _autosize(this);
      }
    });
  }
  // 미리보기를 누르면 크게 본다. 썸네일은 200px 남짓이라 도해 글자도
  // 자막 자리도 확인할 수 없다 — 화면을 보고 판단하려면 크게 봐야 한다.
  var wraps = scope.querySelectorAll(".col-img .img-wrap");
  for (var wi2 = 0; wi2 < wraps.length; wi2++) {
    wraps[wi2].addEventListener("click", function (ev) {
      if (ev.target.closest("button")) return;      // ✕(링크 해제) 같은 버튼은 그대로
      var row = this.closest(".sheet-row");
      pvZoom(this.innerHTML, row ? row.getAttribute("data-scene") : "");
    });
  }
  // 후보 띠 채우기 — **한 번에 받아 나눠 준다.** 씬마다 따로 물으면
  // 142씬이면 왕복이 142번이라 시트가 한참 뜬다.
  var vboxes = scope.querySelectorAll(".img-vers");
  if (vboxes.length === 1) { _loadVersions(vboxes[0]); }
  else if (vboxes.length) { _loadVersionsAll(vboxes); }

  /* 🎞 영상 — 미리보기 자리에서 그림 ↔ 비디오를 오간다.
     비디오를 새로 만들지 않고 `<video>` 를 그림 위에 덮었다 걷는다.
     떠날 때는 반드시 멈춘다 — 안 그러면 다른 씬을 보는데 소리가 계속 난다. */
  var vt = scope.querySelectorAll("button.vid-toggle");
  for (var vq = 0; vq < vt.length; vq++) {
    vt[vq].addEventListener("click", function (ev) {
      ev.stopPropagation();                       // 확대 보기가 같이 뜨지 않게
      var col = this.closest(".col-img");
      var wrap = col && col.querySelector(".img-wrap");
      if (!wrap) return;
      var have = wrap.querySelector("video.vid-el");
      if (have) {                                  // 이미 영상 → 그림으로 되돌린다
        have.pause();
        wrap.innerHTML = wrap.getAttribute("data-img-html") || "";
        wrap.removeAttribute("data-img-html");
        this.classList.remove("on");
        this.textContent = "🎞 영상";
        return;
      }
      wrap.setAttribute("data-img-html", wrap.innerHTML);
      wrap.innerHTML = '<video class="vid-el" controls autoplay preload="metadata" src="'
                     + this.getAttribute("data-src") + '"></video>';
      this.classList.add("on");
      this.textContent = "🖼 그림";
    });
  }

  var un = scope.querySelectorAll("button.unlink-img");
  for (var u = 0; u < un.length; u++) {
    un[u].addEventListener("click", function () { unlinkScene(this.getAttribute("data-scene")); });
  }
  var players = scope.querySelectorAll(".tts-player");
  for (var pp = 0; pp < players.length; pp++) { _bindTtsPlayer(players[pp]); }
  var cbs = scope.querySelectorAll("input.scene-sel");
  for (var cb = 0; cb < cbs.length; cb++) {
    cbs[cb].addEventListener("change", function () {
      var n = this.getAttribute("data-scene");
      if (this.checked) SEL_SCENES[n] = true; else delete SEL_SCENES[n];
    });
  }
  var acts = scope.querySelectorAll("button.ra");
  for (var a = 0; a < acts.length; a++) {
    acts[a].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      var act = this.getAttribute("data-act");
      if (act === "img") { openImageModal(n); }
      else if (act === "tts") { genTts(n); }
      else if (act === "txt") { toggleTextEditor(n); }
      else if (act === "vid") { openVideoModal(n); }
      else if (act === "tl") { exportToTimeline(parseFloat(n)); }
    });
  }
  var saves = scope.querySelectorAll("button.te-save");
  for (var sv = 0; sv < saves.length; sv++) {
    saves[sv].addEventListener("click", function () { saveSceneTexts(this.getAttribute("data-scene"), false); });
  }
  var regens = scope.querySelectorAll("button.te-regen");
  for (var rg = 0; rg < regens.length; rg++) {
    regens[rg].addEventListener("click", function () { saveSceneTexts(this.getAttribute("data-scene"), true); });
  }
  var resets = scope.querySelectorAll("button.te-reset");
  for (var rs = 0; rs < resets.length; rs++) {
    resets[rs].addEventListener("click", function () {
      resetSceneText(this.getAttribute("data-scene"), this.getAttribute("data-kind"));
    });
  }
  var regs = scope.querySelectorAll("button.lyr-regen");
  for (var rgn = 0; rgn < regs.length; rgn++) {
    regs[rgn].addEventListener("click", function (ev) {
      ev.stopPropagation();
      var it = this.closest(".lyr-row");
      regenLayer(it.getAttribute("data-scene"), it.getAttribute("data-layer"));
    });
  }
  var tgs = scope.querySelectorAll("button.lyr-toggle");
  for (var tg = 0; tg < tgs.length; tg++) {
    tgs[tg].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      LYR_OPEN[n] = !LYR_OPEN[n];
      refreshRow(n);
    });
  }
  var eyes = scope.querySelectorAll("button.lyr-eye");
  for (var ey = 0; ey < eyes.length; ey++) {
    eyes[ey].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { hidden: !row.classList.contains("off") });
    });
  }
  var rms = scope.querySelectorAll("button.lyr-rm");
  for (var rm = 0; rm < rms.length; rm++) {
    rms[rm].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { removed: true });
    });
  }
  var rsts = scope.querySelectorAll("button.lyr-restore");
  for (var rst = 0; rst < rsts.length; rst++) {
    rsts[rst].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { removed: false });
    });
  }
  var picks = scope.querySelectorAll("input.lyr-pick");
  for (var pk = 0; pk < picks.length; pk++) {
    picks[pk].addEventListener("change", function () {
      var row = this.closest(".lyr-row");
      var n = row.getAttribute("data-scene"), stem = row.getAttribute("data-layer");
      if (!LYR_SEL[n]) LYR_SEL[n] = {};
      if (this.checked) LYR_SEL[n][stem] = true; else delete LYR_SEL[n][stem];
    });
  }
  var vall = scope.querySelectorAll("button.lyr-vec-all");
  for (var va = 0; va < vall.length; va++) {
    vall[va].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      vectorizeLayers(n, _lyrStemsOf(n, false), false);
    });
  }
  var vsel = scope.querySelectorAll("button.lyr-vec-sel");
  for (var vs = 0; vs < vsel.length; vs++) {
    vsel[vs].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      vectorizeLayers(n, _lyrStemsOf(n, true), false);
    });
  }
  var revs = scope.querySelectorAll("button.lyr-revec");
  for (var rv = 0; rv < revs.length; rv++) {
    revs[rv].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      var n = row.getAttribute("data-scene");
      // 이미 SVG가 있는 레이어를 다시 벡터화할 때만 force가 필요하다.
      var has = !!row.querySelector(".lyr-badge");
      vectorizeLayers(n, [row.getAttribute("data-layer")], has);
    });
  }
}

/* ===== 도구상자(시트 상단) — 체크된 씬에 일괄 실행 ===== */
// 「1-10, 25, 40-52」 같은 글을 씬 번호로 편다.
// 화면에 있는 번호만 고른다 — 씬을 다시 나누면 번호가 띄엄띄엄해지기 때문에
// (951·968·1023…) 1..N 으로 세면 없는 씬을 고르게 된다.
function _parseRange(text, present) {
  var want = {}, bad = [];
  String(text || "").split(",").forEach(function (part) {
    part = part.trim();
    if (!part) return;
    var m = part.match(/^(\d+)\s*[-~]\s*(\d+)$/);
    if (m) {
      var a = parseInt(m[1], 10), b = parseInt(m[2], 10);
      if (a > b) { var tmp = a; a = b; b = tmp; }
      // 순서대로 훑어 그 구간에 실제로 있는 씬만 담는다
      for (var i = 0; i < present.length; i++) {
        var v = present[i];
        if (v >= a && v <= b) want[v] = true;
      }
      return;
    }
    if (/^\d+$/.test(part)) {
      var n = parseInt(part, 10);
      if (present.indexOf(n) >= 0) want[n] = true; else bad.push(n);
      return;
    }
    bad.push(part);
  });
  return { nums: Object.keys(want).map(Number).sort(function (x, y) { return x - y; }),
           bad: bad };
}

function _bindRangeSelect() {
  var box = document.getElementById("selRange");
  if (!box) return;
  var msg = document.getElementById("selRangeMsg");
  function present() {
    var cbs = document.getElementById("sheet").querySelectorAll("input.scene-sel"), out = [];
    for (var i = 0; i < cbs.length; i++) out.push(parseFloat(cbs[i].getAttribute("data-scene")));
    return out;
  }
  function apply(mode) {
    var have = present();
    var r = _parseRange(box.value, have);
    if (mode === "only") SEL_SCENES = {};
    r.nums.forEach(function (n) {
      if (mode === "off") delete SEL_SCENES[String(n)];
      else SEL_SCENES[String(n)] = true;
    });
    var cbs = document.getElementById("sheet").querySelectorAll("input.scene-sel");
    for (var i = 0; i < cbs.length; i++) {
      cbs[i].checked = !!SEL_SCENES[cbs[i].getAttribute("data-scene")];
    }
    var n = Object.keys(SEL_SCENES).length;
    if (msg) {
      msg.textContent = n + "개 선택됨"
        + (r.bad.length ? "  (없는 씬: " + r.bad.join(", ") + ")" : "");
      msg.style.color = r.bad.length ? "#e0894a" : "#9aa0a6";
    }
  }
  document.getElementById("selRangeAdd").addEventListener("click", function () { apply("add"); });
  document.getElementById("selRangeOnly").addEventListener("click", function () { apply("only"); });
  document.getElementById("selRangeOff").addEventListener("click", function () { apply("off"); });
  box.addEventListener("keydown", function (e) {
    if (e.key === "Enter") { e.preventDefault(); apply("add"); }
  });
}

function _bindFind() {
  var box = document.getElementById("sbFind");
  if (!box) return;
  var msg = document.getElementById("sbFindMsg");
  function run() {
    var q = (box.value || "").trim().toLowerCase();
    var rows = document.getElementById("sheet").querySelectorAll(".sheet-row");
    var hit = 0;
    for (var i = 0; i < rows.length; i++) {
      var el = rows[i].querySelector("textarea.nar");
      var txt = ((el ? el.value : "") || rows[i].textContent || "").toLowerCase();
      var on = !q || txt.indexOf(q) >= 0;
      rows[i].style.display = on ? "" : "none";
      if (q && on) hit++;
    }
    if (msg) msg.textContent = q ? hit + "개 씬" : "";
  }
  box.addEventListener("input", run);
  box.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { box.value = ""; run(); }
  });
}

var SEL_SCENES = {};    // {sceneNumber(str): true} — 재렌더에도 유지

function _checkedScenes() {
  return Object.keys(SEL_SCENES).map(function (k) { return parseFloat(k); })
    .sort(function (a, b) { return a - b; });
}

function _needChecked(min, what) {
  var ns = _checkedScenes();
  if (ns.length < (min || 1)) { alert("씬을 먼저 체크하세요" + (what ? " — " + what : "") + "."); return null; }
  return ns;
}

/* 순차 실행 — 각 씬을 차례로(fn은 promise 반환). 행 상태는 각 fn이 표시. */
function _runSeq(ns, fn) {
  return ns.reduce(function (p, n) {
    return p.then(function () { return fn(n); }).catch(function () { /* 한 씬 실패해도 계속 */ });
  }, Promise.resolve());
}

function bindSheetToolbar() {
  function on(id, h) { var b = $(id); if (b) b.addEventListener("click", h); }
  on("sa-img", function () {
    var ns = _needChecked(1, "이미지 생성"); if (ns) _runSeq(ns, genSceneImage);
  });
  on("sa-layer", function () {
    var ns = _needChecked(1, "레이어 분리"); if (!ns) return;
    analyzeLayers(ns);            // 여러 씬이면 탭 모달 — 분석 병렬, 분리도 병렬 잡
  });
  on("sa-tts", function () {
    var ns = _needChecked(1, "TTS 생성"); if (ns) _runSeq(ns, genTts);
  });
  on("sa-motion", function () {
    var ns = _needChecked(1, "모션 플랜"); if (ns) _runSeq(ns, planMotion);
  });
  on("sa-comp", function () {
    var ns = _needChecked(1, "AE 컴프"); if (!ns) return;
    // 체크한 씬 전체를 한 번에 — 씬마다 매니페스트·jsx를 반복하면 씬 많은 프로젝트에서 몇 분씩 걸린다
    var st = $("sa-status");
    _assemble(ns, function (m) { if (st) st.textContent = m; $("aeresult").textContent = m; });
  });
  on("sa-sub", function () {
    var ns = _needChecked(1, "말자막"); if (!ns) return;
    var st2 = $("sa-status");
    buildSubtitles(ns, function (m) { if (st2) st2.textContent = m; $("aeresult").textContent = m; });
  });
  on("sa-map", function () {
    var ns = _needChecked(1, "지도 렌더"); if (!ns) return;
    var box = $("aeresult"), st = $("sa-status");
    function say(t) { if (st) st.textContent = t; if (box) box.textContent = t; }
    say("지도 렌더 중... (타일 다운로드 수 초)");
    fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
      .then(function (r) { return r.json(); })
      .then(function (j) {
        var by = {}; (j.scenes || []).forEach(function (s) { by[s.sceneNumber] = s; });
        return _runSeq(ns, function (n) {
          var s = by[n];
          if (!s) return Promise.resolve();
          if (s.layout !== "map") { say("씬 " + n + ": layout이 map이 아니라 건너뜀"); return Promise.resolve(); }
          return genMapForScene(s)
            .then(function (res) {
              if (res && res.error) { say("씬 " + n + " 지도 실패: " + res.error); return; }
              say("씬 " + n + " 지도 완료 ✓"); refreshRow(n);
            })
            .catch(function (e) { say("씬 " + n + " 지도 실패: " + e); });
        });
      })
      .catch(function (e) { say("지도 렌더 실패: " + e); });
  });
  on("sa-chart", function () {
    var ns = _needChecked(1, "차트 명세서"); if (!ns) return;
    var st = $("sa-status"), box = $("aeresult");
    function say(t) { if (st) st.textContent = t; if (box) box.textContent = t; }
    say("차트 명세서 생성 중...");
    _runSeq(ns, function (n) {
      return fetch(BACKEND + "/api/scenes/chart-spec", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n }),
      }).then(function (r) { return r.json(); })
        .then(function (res) {
          if (res && res.error) { say("씬 " + n + " 차트: " + res.error); return; }
          say("씬 " + n + " 차트 명세 완료 ✓ (" + (res.theme_set || "") + ")");
        })
        .catch(function (e) { say("씬 " + n + " 차트 실패: " + e); });
    });
  });
  /* 업스케일·벡터화 — 체크한 씬에 한 번에 건다.
     업스케일은 원본을 덮지 않고 새 판본을 만들어 링크만 옮긴다. */
  function _batchTool(url, label) {
    var ns = _needChecked(1, label); if (!ns) return;
    var st = $("sa-status");
    function say(m) { if (st) st.textContent = m; }
    say(label + " " + ns.length + "씬 처리 중...");
    fetch(BACKEND + url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumbers: ns }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.error) { say(label + " 실패: " + j.error); return; }
        var d = (j.done || []).length, f = (j.failed || []).length;
        say(label + " 완료 " + d + "씬" + (f ? (" · 실패 " + f) : ""));
        for (var k = 0; k < (j.done || []).length; k++) refreshRow(j.done[k]);
      })
      .catch(function (e) { say(label + " 오류: " + e); });
  }
  on("sa-upscale", function () { _batchTool("/api/scenes/upscale", "업스케일"); });
  on("sa-vector", function () { _batchTool("/api/scenes/vectorize", "벡터화"); });


  on("sa-theme", function () {
    var ns = _needChecked(1, "씬 테마"); if (!ns) return;
    var tid = window.prompt("이 씬에 적용할 테마 id(비우면 해제):", "");
    _runSeq(ns, function (n) {
      return fetch(BACKEND + "/api/themes/set-scene", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n, theme_id: tid || null }),
      }).then(function (r) { return r.json(); }).then(function () { refreshRow(n); });
    });
  });
  on("sa-add", function () {
    var ns = _checkedScenes();
    sceneOp("add", ns.length ? { after: ns[ns.length - 1] } : {});   // 체크 없으면 맨 끝에
  });
  on("sa-split", function () {
    var ns = _needChecked(1, "분할(1개만)"); if (!ns) return;
    if (ns.length > 1) { alert("분할은 한 씬만 체크하세요."); return; }
    sceneOp("split", { sceneNumber: ns[0] });
  });
  on("sa-merge", function () {
    var ns = _needChecked(1, "병합(1개만 — 다음 씬과 합쳐짐)"); if (!ns) return;
    if (ns.length > 1) { alert("병합은 한 씬만 체크하세요(그 씬과 다음 씬이 합쳐집니다)."); return; }
    sceneOp("merge", { sceneNumber: ns[0] });
  });
  on("sa-del", function () {
    var ns = _needChecked(1, "삭제"); if (!ns) return;
    if (!confirm("체크된 씬 " + ns.join(", ") + " 을 삭제할까요? (이미지/레이어 파일은 보존됩니다)")) return;
    SEL_SCENES = {};
    _runSeq(ns.slice().reverse(), function (n) {           // 높은 번호부터(재번호 영향 회피)
      return fetch(BACKEND + "/api/scenes/delete", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n }),
      }).then(function (r) { return r.json(); });
    }).then(function () { loadSheet(); });
  });
}

document.addEventListener("DOMContentLoaded", bindSheetToolbar);

/* 단일 씬 행만 갱신 — 전체 loadSheet의 포커스 손실/스크롤 점프 방지.
   행 수가 변하는 구조 편집(add/del/split/merge)은 loadSheet 사용. */
function refreshRow(n) {
  // **그 씬만 받는다.** 142씬을 통째로 받아 한 행을 고치면 그 시간이 그대로
  // 「바꾸는 중…」으로 보인다.
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT)
        + "&sceneNumber=" + encodeURIComponent(n))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var s = (j.scenes || []).filter(function (x) { return x.sceneNumber === parseFloat(n); })[0];
      var old = $("sheet").querySelector('.sheet-row[data-scene="' + n + '"]');
      if (!s || !old) { loadSheet(); return; }            // 못 찾으면 전체 갱신 폴백
      NAR_ORIG[s.sceneNumber] = s.narration || "";
      var tmp = document.createElement("div");
      tmp.innerHTML = renderRow(s, j.dir || "");
      var fresh = tmp.firstChild;
      old.parentNode.replaceChild(fresh, old);
      bindRows(fresh);                                     // 새 행만 바인딩(중복 리스너 방지)
      var ta = fresh.querySelector("textarea.nar");
      if (ta) _autosize(ta);
    })
    .catch(function () { loadSheet(); });
}

/* 씬 모션 플랜(LLM) — 동기 호출, 완료 시 상태줄 안내 */
function planMotion(n) {
  _rowBusy(n, true, "모션 설계 중... (LLM, 비동기)");
  return fetch(BACKEND + "/api/scenes/motion", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n) }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) { _rowStatus(n, "실패: " + (j.error || JSON.stringify(j))); return; }
      return new Promise(function (resolve) {
        _awaitJob(j.job_id, function (job) {
          var plan = job.result && job.result.plan;
          if (job.status === "completed" && plan) {
            var nmoves = (plan.layers || []).reduce(function (a, L) { return a + (L.moves || []).length; }, 0);
            _rowStatus(n, "모션 " + nmoves + "개 + 카메라 " + ((plan.camera || {}).type || "none") + " ✓ — 🎬 컴프로 적용");
            refreshRow(n);                                 // 모션 점 갱신
          } else {
            _rowStatus(n, "실패: " + (job.error || JSON.stringify(job)));
          }
          resolve();
        });
      });
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

function _rowStatus(n, msg) {
  var el = $("sheet").querySelector('.row-status[data-scene="' + n + '"]');
  if (el) el.textContent = msg;
}

/* 씬이 일하는 중인지 **글자 말고 눈으로** 보이게 한다.
   `_rowStatus` 만 있던 때는 작은 회색 글씨 한 줄이 전부라, 돌고 있는 건지
   아무 일도 안 일어난 건지 구분이 안 됐다 — 비서가 계획을 못 세워 아무것도
   안 했을 때도 화면이 똑같아 보였다.
   `on` 이 참이면 이미지 칸에 도는 고리를 얹고, 거짓이면 걷는다. */
function _rowBusy(n, on, msg) {
  var row = $("sheet").querySelector('.sheet-row[data-scene="' + n + '"]');
  if (row) row.classList.toggle("busy", !!on);
  if (msg) _rowStatus(n, msg);
}

/* 일이 끝나면 **누르지 않아도** 화면에 반영한다. 끝난 줄 모르고 기다리거나
   새로고침을 눌러야 보이면 안 만든 것과 같다. */
function _rowDone(n, ok, msg) {
  _rowBusy(n, false, msg);
  if (ok) refreshRow(n);
}

function saveNarration(n) {
  var ta = $("sheet").querySelector('textarea.nar[data-scene="' + n + '"]');
  if (!ta) return;
  _rowStatus(n, "저장 중...");
  fetch(BACKEND + "/api/scenes/narration", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n), narration: ta.value }),
  }).then(function (r) { return r.json(); })
    .then(function (j) { _rowStatus(n, j.ok ? "저장됨 ✓" : ("실패: " + JSON.stringify(j))); })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* ===== 재생성 모달 — 무엇을 보고 무슨 말로 그릴지 먼저 정한다 ===== */
var IMG_SCENE = null, IMG_REFS = {}, IMG_TAB = "chars", IMG_DATA = null, IMG_DIR = "";
var IMG_MODE = "gen";      // gen=새로 그리기 · edit=지금 그림 고치기

/* 새로 그리기 ↔ 고치기. 고치기는 지금 그림을 참조로 붙이고 바꿀 것 하나만
   말하므로 구도·자세가 유지된다 — 참조 고르기와 이전 프롬프트는 필요 없다. */
function _setImgMode(m) {
  IMG_MODE = m;
  var bs = $("imgModeTabs").querySelectorAll(".imgmode");
  for (var i = 0; i < bs.length; i++) {
    bs[i].className = "mini imgmode" + (bs[i].getAttribute("data-mode") === m ? "" : " alt");
  }
  var edit = m === "edit";
  $("imgRefBlock").hidden = edit;
  $("imgPromptLabel").textContent = edit
    ? "무엇을 바꿀까요 — 바꿀 것 하나만 적으세요. 나머지는 지금 그림 그대로 둡니다."
    : "프롬프트 — 이전 내용이 채워집니다. 고쳐서 다시 그리세요.";
  $("imgSubmit").textContent = edit ? "이대로 고치기" : "이 내용으로 생성";
  var ta = $("imgPrompt");
  if (edit) { ta._genText = ta.value; ta.value = ta._editText || ""; ta.placeholder = "예: 인물이 쓴 안경을 없애고 맨 얼굴로"; }
  else { ta._editText = ta.value; ta.value = ta._genText || ""; ta.placeholder = ""; }
}

function openImageModal(n) {
  IMG_SCENE = n; IMG_REFS = {}; IMG_TAB = "chars"; IMG_DATA = null;
  var ta0 = $("imgPrompt"); ta0._genText = ""; ta0._editText = "";
  _setImgMode("gen");
  $("imgRefList").textContent = "불러오는 중...";
  $("imgModalStatus").textContent = "—";
  $("imgPrompt").value = "";
  $("imgModal").hidden = false;

  // 프롬프트는 이전 것을 먼저 띄운다 — 빈 칸에서 다시 쓰게 하면 손이 많이 간다.
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      IMG_DIR = j.dir || "";
      var s = (j.scenes || []).filter(function (x) { return x.sceneNumber === parseFloat(n); })[0];
      if (s) $("imgPrompt").value = s.image_prompt || s.visual_summary || "";
      _renderImgRefs();                       // 경로가 늦게 와도 썸네일이 뜨도록
    });

  fetch(BACKEND + "/api/scenes/image-refs?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) { IMG_DATA = j; _renderImgRefs(); })
    .catch(function (e) { $("imgRefList").textContent = "참조 목록 오류: " + e; });
}

function _renderImgRefs() {
  if (!IMG_DATA) return;
  var tabs = $("imgRefTabs").querySelectorAll(".imgreftab");
  for (var t = 0; t < tabs.length; t++) {
    var on = tabs[t].getAttribute("data-tab") === IMG_TAB;
    tabs[t].className = "mini imgreftab" + (on ? "" : " alt");
  }
  var items = IMG_TAB === "chars" ? (IMG_DATA.characters || [])
            : IMG_TAB === "docs"  ? (IMG_DATA.docs || [])
            : (IMG_DATA.scenes || []);
  if (!items.length) {
    $("imgRefList").textContent =
        IMG_TAB === "chars" ? "이 프로젝트에 인물 시트가 없습니다."
      : IMG_TAB === "docs"  ? "실물 자료가 없습니다 — 프로젝트를 다시 불러오면 들어옵니다."
      : "링크된 씬 이미지가 없습니다.";
    return;
  }
  var dir = IMG_DIR || "";
  var h = '<div style="display:flex;flex-wrap:wrap;gap:6px">';
  for (var i = 0; i < items.length; i++) {
    var it = items[i], rel = it.rel;
    var cap = IMG_TAB === "scenes" ? ("씬 " + it.sceneNumber) : (it.name || "");
    h += '<label class="imgref" style="width:78px;text-align:center;cursor:pointer'
      + (IMG_REFS[rel] ? ';outline:2px solid #3a6df0' : '') + '">'
      + '<img src="file://' + dir + '/' + rel + '" style="width:100%;border-radius:4px;display:block">'
      + '<input type="checkbox" data-rel="' + rel + '"' + (IMG_REFS[rel] ? " checked" : "") + '>'
      + '<span style="font-size:10px;color:#9aa0a6">' + _esc(cap) + '</span></label>';
  }
  $("imgRefList").innerHTML = h + '</div>';
  var cbs = $("imgRefList").querySelectorAll('input[type="checkbox"]');
  for (var c = 0; c < cbs.length; c++) {
    cbs[c].addEventListener("change", function () {
      var r = this.getAttribute("data-rel");
      if (this.checked) IMG_REFS[r] = true; else delete IMG_REFS[r];
      _renderImgRefs();
    });
  }
  var picked = Object.keys(IMG_REFS);
  $("imgRefPicked").textContent = "고른 참조: " + (picked.length ? picked.length + "장" : "없음");
}

/* 지금 그림을 참조로 붙여 지시한 곳만 고친다. 옛 그림은 지우지 않고
   새 판본으로 쌓은 뒤 링크만 옮긴다. */
function editSceneImage(n, instruction) {
  _rowBusy(n, true, "이미지 고치는 중... (codex, 수십 초)");
  return fetch(BACKEND + "/api/scenes/image-edit", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
                           instruction: instruction }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.status === "completed";
      _rowDone(n, ok, ok ? "수정 완료 ✓" : ("실패: " + JSON.stringify(j)));
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

function genSceneImage(n, prompt, refs) {
  _rowBusy(n, true, "씬 이미지 생성 중... (codex, 수십 초)" + (SELECTED_CHARACTER ? " [" + SELECTED_CHARACTER + "]" : ""));
  return fetch(BACKEND + "/api/scenes/image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
                           character: SELECTED_CHARACTER || "",
                           prompt: prompt || "", refs: refs || [] }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.status === "completed";
      _rowDone(n, ok, ok ? "생성 완료 ✓" : ("실패: " + JSON.stringify(j)));   // 썸네일 갱신(행 단위)
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

function unlinkScene(n) {
  _rowStatus(n, "링크 해제 중...");
  fetch(BACKEND + "/api/scenes/unlink-image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n) }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _rowStatus(n, j.ok ? "링크 해제됨(파일은 갤러리에 보존)" : ("실패: " + JSON.stringify(j)));
      if (j.ok) refreshRow(n);
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* 레이어 분리 — 여러 씬 동시: 씬별 분석을 병렬로 돌리고 탭으로 확인·체크 후 일괄(병렬) 분리 */
var _layerMulti = {};        // {n: {els: [...], done: bool}}

function analyzeLayers(ns) {
  if (!(ns instanceof Array)) ns = [ns];
  _layerMulti = {};
  $("layerTabs").innerHTML = ns.map(function (n, i) {
    return '<button class="layer-tab' + (i === 0 ? " active" : "") + '" data-scene="' + n + '">씬 ' + n + '</button>';
  }).join("");
  $("layerList").innerHTML = "";
  ns.forEach(function (n) {
    var pane = document.createElement("div");
    pane.className = "layer-pane";
    pane.setAttribute("data-scene", n);
    pane.innerHTML = '<div style="color:#9aa0a6;padding:8px">씬 ' + n + ' 분석 중... (codex, 수십 초)</div>';
    pane.hidden = String(n) !== String(ns[0]);
    $("layerList").appendChild(pane);
  });
  $("layerModalStatus").textContent = ns.length + "개 씬 분석 중 — 완료된 탭부터 확인하세요.";
  $("layerModal").hidden = false;
  var tabs = $("layerTabs").querySelectorAll(".layer-tab");
  for (var t = 0; t < tabs.length; t++) {
    tabs[t].addEventListener("click", function () { _switchLayerTab(this.getAttribute("data-scene")); });
  }
  // 씬별 분석 병렬 실행
  ns.forEach(function (n) {
    _rowStatus(n, "레이어 분석 중...");
    fetch(BACKEND + "/api/scenes/analyze-layers", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n) }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        var els = j.elements || [], dropped = j.dropped || [];
        _layerMulti[n] = { els: els.concat(dropped), done: true, prompt: j.prompt || "" };
        _renderLayerPane(n, els, j.error, dropped);
        _rowStatus(n, els.length
          ? (els.length + "개 요소 분석됨" + (dropped.length ? " (+" + dropped.length + "개 예산 초과)" : ""))
          : ("분석 실패: " + (j.error || "")));
        _updateLayerModalStatus();
      })
      .catch(function (e) {
        _layerMulti[n] = { els: [], done: true };
        _renderLayerPane(n, [], String(e));
        _updateLayerModalStatus();
      });
  });
}

function _renderLayerPane(n, els, err, dropped) {
  var pane = $("layerList").querySelector('.layer-pane[data-scene="' + n + '"]');
  if (!pane) return;
  if (!els.length) {
    pane.innerHTML = '<div style="color:#e74c3c;padding:8px">씬 ' + n + ' 분석 실패: ' + _esc(err || "") + '</div>';
    return;
  }
  function row(e, i, off) {
    var tag = e.kind === "character" ? "👤 인물" : "📦 사물";
    return '<label class="layer-chk' + (off ? " layer-dropped" : "") + '">'
      + '<input type="checkbox" data-idx="' + i + '"' + (off ? ' data-dropped="1"' : "") + (off ? "" : " checked") + (off ? " disabled" : "") + '>'
      + '<span><b>' + tag + '</b> ' + _esc(e.name)
      + ' <span style="color:#9aa0a6">(' + _esc(e.location) + ')</span>'
      + (off ? ' <span style="color:#e8b339">예산 초과로 제외</span>' : '')
      + (e.reason ? '<br><span style="font-size:10px;color:#9aa0a6">' + _esc(e.reason) + '</span>' : '')
      + (e.intent ? '<br><span style="font-size:10px;color:#7ab0ff">▸ ' + _esc(e.intent) + '</span>' : '')
      + '</span></label>';
  }
  var html = '<div class="layer-cap-note" style="font-size:11px;color:#9aa0a6;padding:4px 2px"></div>';
  html += els.map(function (e, i) { return row(e, i, false); }).join("");
  html += (dropped || []).map(function (e, i) { return row(e, els.length + i, true); }).join("");
  /* **분석 결과가 곧 씨드림 프롬프트다.** 체크한 요소 이름을 영어로 나열한
     것이 그대로 모델에 간다 — 그런데 화면에 안 보여 고칠 방법이 없었다.
     체크를 바꾸면 여기도 따라 바뀌고, 손으로 고치면 고친 것이 그대로 나간다. */
  html += '<div class="lp-prompt-wrap">'
        +   '<div class="lp-prompt-lab">씨드림 5.0 프롬프트 '
        +     '<span class="lp-prompt-hint">나눌 레이어 이름만, 쉼표로 — 고쳐도 됩니다</span>'
        +     '<button class="mini lp-prompt-reset" type="button">되돌리기</button>'
        +   '</div>'
        +   '<textarea class="lp-prompt" rows="4"></textarea>'
        + '</div>';
  pane.innerHTML = html;
  var chks = pane.querySelectorAll('input[type="checkbox"]');
  for (var c = 0; c < chks.length; c++) {
    chks[c].addEventListener("change", function () {
      _enforceLayerCap(pane);
      _syncLayerPrompt(n, pane);
    });
  }
  var ta = pane.querySelector("textarea.lp-prompt");
  if (ta) ta.addEventListener("input", function () { pane.setAttribute("data-prompt-edited", "1"); });
  var rb = pane.querySelector(".lp-prompt-reset");
  if (rb) rb.addEventListener("click", function () {
    pane.removeAttribute("data-prompt-edited");
    _syncLayerPrompt(n, pane);
  });
  _enforceLayerCap(pane);
  _syncLayerPrompt(n, pane);
}

/* 체크된 요소로 프롬프트를 다시 짠다. **손으로 고친 뒤에는 덮지 않는다** —
   고쳐 놓은 문장이 체크 한 번에 날아가면 고칠 수가 없다. 되돌리기로 푼다.
   문구는 백엔드 `build_layerize_prompt` 와 같아야 한다. */
function _syncLayerPrompt(n, pane) {
  var ta = pane.querySelector("textarea.lp-prompt");
  if (!ta || pane.getAttribute("data-prompt-edited") === "1") return;
  var info = _layerMulti[n] || {};
  var chks = pane.querySelectorAll('input[type="checkbox"]');
  var names = [];
  for (var i = 0; i < chks.length; i++) {
    if (!chks[i].checked) continue;
    var e = (info.els || [])[parseInt(chks[i].getAttribute("data-idx"), 10)];
    var en = e && (e.name_en || "").trim();
    if (en) names.push(en);
  }
  // 이름만 나열한다 — 백엔드 build_layerize_prompt 와 같은 문자열이어야 한다
  ta.value = names.length ? names.join(", ") : (info.prompt || "");
}

/* 씬당 요소 레이어 상한 — 배경 1장을 더해 최대 11레이어(백엔드 MAX_ELEMENTS와 같은 값). */
var MAX_LAYER_ELEMENTS = 10;

/* 체크 개수를 상한으로 묶는다 — 상한에 닿으면 꺼진 체크박스를 잠근다. */
function _enforceLayerCap(pane) {
  var chks = pane.querySelectorAll('input[type="checkbox"]');
  var on = 0, i;
  for (i = 0; i < chks.length; i++) if (chks[i].checked) on++;
  for (i = 0; i < chks.length; i++) {
    var isDropped = chks[i].getAttribute("data-dropped") === "1";
    chks[i].disabled = isDropped || (!chks[i].checked && on >= MAX_LAYER_ELEMENTS);
  }
  var note = pane.querySelector(".layer-cap-note");
  if (note) note.textContent = on + "개 선택 (최대 " + MAX_LAYER_ELEMENTS + " — 배경 1장이 자동으로 더해집니다)";
}

function _switchLayerTab(n) {
  var tabs = $("layerTabs").querySelectorAll(".layer-tab");
  for (var t = 0; t < tabs.length; t++) {
    tabs[t].classList.toggle("active", tabs[t].getAttribute("data-scene") === String(n));
  }
  var panes = $("layerList").querySelectorAll(".layer-pane");
  for (var p = 0; p < panes.length; p++) {
    panes[p].hidden = panes[p].getAttribute("data-scene") !== String(n);
  }
}

function _updateLayerModalStatus() {
  var total = Object.keys(_layerMulti).length;
  var done = Object.keys(_layerMulti).filter(function (k) { return _layerMulti[k].done; }).length;
  $("layerModalStatus").textContent = done < total
    ? ("분석 " + done + "/" + total + " 완료 — 완료된 탭부터 확인 가능")
    : "전체 분석 완료 — 탭별로 체크 확인 후 [선택 분리]를 누르세요(씬별 병렬 실행).";
}

function _closeLayerModal() { $("layerModal").hidden = true; }

function _submitLayerSplit() {
  var panes = $("layerList").querySelectorAll(".layer-pane");
  var jobs = [];
  for (var p = 0; p < panes.length; p++) {
    var n = panes[p].getAttribute("data-scene");
    var info = _layerMulti[n];
    if (!info || !info.els.length) continue;
    var chks = panes[p].querySelectorAll('input[type="checkbox"]');
    var chosen = [];
    for (var i = 0; i < chks.length; i++) {
      if (chks[i].checked) chosen.push(info.els[parseInt(chks[i].getAttribute("data-idx"), 10)]);
    }
    var pta = panes[p].querySelector("textarea.lp-prompt");
    if (chosen.length) jobs.push({ n: n, els: chosen,
                                   prompt: pta ? pta.value.trim() : "" });
  }
  if (!jobs.length) { $("layerModalStatus").textContent = "분리할 요소를 1개 이상 체크하세요."; return; }
  _closeLayerModal();
  jobs.forEach(function (j) { splitLayers(j.n, j.els, j.prompt); });   // 씬별 병렬 잡(각자 폴링)
}

document.addEventListener("DOMContentLoaded", function () {
  var s = $("layerSubmit"); if (s) s.addEventListener("click", _submitLayerSplit);
  var c = $("layerCancel"); if (c) c.addEventListener("click", _closeLayerModal);
  var x = $("layerClose"); if (x) x.addEventListener("click", _closeLayerModal);

  /* 재생성 모달 */
  function _closeImg() { $("imgModal").hidden = true; }
  function _closeImgAll() { VID_SLOT_TARGET = null; $("imgSubmit").textContent = "이 내용으로 생성"; _closeImg(); }
  var ic = $("imgCancel"); if (ic) ic.addEventListener("click", _closeImgAll);
  var ix = $("imgClose"); if (ix) ix.addEventListener("click", _closeImgAll);

  /* 비디오 모달 */
  function _closeVid() { $("vidModal").hidden = true; }
  var vc = $("vidCancel"); if (vc) vc.addEventListener("click", _closeVid);
  var vx = $("vidClose"); if (vx) vx.addEventListener("click", _closeVid);
  var vm = $("vidModel"); if (vm) vm.addEventListener("change", _renderVidModel);
  var vs = $("vidSubmit");
  if (vs) vs.addEventListener("click", function () {
    if (VID_SCENE == null) return;
    if (!$("vidPrompt").value.trim()) { $("vidStatus").textContent = "프롬프트를 채우세요."; return; }
    genSceneVideo(VID_SCENE).then(_closeVid);
  });
  var itb = $("imgRefTabs");
  if (itb) itb.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest(".imgreftab") : null;
    if (!b) return;
    IMG_TAB = b.getAttribute("data-tab");
    _renderImgRefs();
  });
  var mtb = $("imgModeTabs");
  if (mtb) mtb.addEventListener("click", function (e) {
    var b = e.target.closest ? e.target.closest(".imgmode") : null;
    if (b) _setImgMode(b.getAttribute("data-mode"));
  });
  var isb = $("imgSubmit");
  if (isb) isb.addEventListener("click", function () {
    // 비디오 모달이 참조를 고르려고 이 창을 빌려 쓴 경우 — 고른 것만 넘기고 닫는다
    if (VID_SLOT_TARGET) {
      VID_PICK[VID_SLOT_TARGET] = Object.keys(IMG_REFS);
      VID_SLOT_TARGET = null;
      $("imgSubmit").textContent = "이 내용으로 생성";
      _closeImg();
      _renderVidSlots();
      return;
    }
    if (IMG_SCENE == null) return;
    var p = $("imgPrompt").value.trim();
    if (!p) {
      $("imgModalStatus").textContent = IMG_MODE === "edit"
        ? "무엇을 바꿀지 적으세요." : "프롬프트를 채우세요.";
      return;
    }
    $("imgModalStatus").textContent = (IMG_MODE === "edit" ? "고치는 중" : "생성 중") + "... (수십 초)";
    var run = IMG_MODE === "edit"
      ? editSceneImage(IMG_SCENE, p)
      : genSceneImage(IMG_SCENE, p, Object.keys(IMG_REFS));
    run.then(function () { _closeImg(); });
  });
});

function splitLayers(n, els, prompt) {
  _rowBusy(n, true, "레이어 분리 중... (" + els.length + "개 요소 + 배경, fal)");
  fetch(BACKEND + "/api/scenes/split-layers", {
    method: "POST", headers: { "Content-Type": "application/json" },
    // 비우면 백엔드가 요소 이름으로 다시 짠다 — 고친 것이 있을 때만 넘어간다
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
                           elements: els, prompt: prompt || "" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) { _rowStatus(n, "실패: " + JSON.stringify(j)); return; }
      _awaitJob(j.job_id, function (job) {
        var res = (job.result && job.result.result) || {};
        var done = (res.layers || []).filter(function (l) { return l.status === "completed"; }).length;
        var missing = res.missing || [];
        var unexpected = res.unexpected || [];
        var extra = "";
        if (missing.length) extra += " (못 만든 요소 " + missing.length + "개: " + missing.join(", ") + ")";
        if (unexpected.length) extra += " (요청 외 " + unexpected.length + "개)";
        _rowStatus(n, done ? ("레이어 " + done + "개 생성 ✓" + extra) : ("실패: " + JSON.stringify(job.error || job)));
        if (done) refreshRow(n);   // 레이어 썸네일 갱신(행 단위)
      }, function (logs) {
        if (logs.length) _rowStatus(n, "레이어 분리 중... " + logs[logs.length - 1]);
      }, 1600);   // 40분 한도 — 병렬 분리 시 큐 대기 포함(5분 기본은 거짓 타임아웃 유발)
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

function dropOnScene(ev, n) {
  ev.preventDefault();
  var src = ev.dataTransfer.getData("text/plain");
  if (!src) return;
  _rowStatus(n, "적용 중... (" + src + ")");
  fetch(BACKEND + "/api/scenes/set-image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n, src: src }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.ok;
      _rowStatus(n, ok ? "적용됨 ✓" : ("실패: " + JSON.stringify(j)));
      if (ok) refreshRow(n);
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}


function sceneOp(op, extra) {
  var b = { project_id: SELECTED_PROJECT };
  for (var k in extra) b[k] = extra[k];
  fetch(BACKEND + "/api/scenes/" + op, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { alert("실패: " + j.error); return; }
      loadSheet();      // 갱신
    })
    .catch(function (e) { alert("오류: " + e); });
}

/* 레이어 낱개 편집 — 눈/제거/복구/벡터화 */
function _layerBusy(n, stem, on) {
  var it = $("sheet").querySelector('.lyr-row[data-scene="' + n + '"][data-layer="' + stem + '"]');
  if (it) it.classList.toggle("busy", !!on);
}

/* 재생성 — layerize는 씬 단위 호출이라 그 요소만 따로 다시 만들 수 없다. 씬 전체를 다시 분리한다. */
function regenLayer(n, stem) {
  _layerBusy(n, stem, true);
  _rowStatus(n, "씬 다시 분리 중... (layerize)");
  return fetch(BACKEND + "/api/layers/regenerate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n), layer: stem }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) {
        _layerBusy(n, stem, false); _rowStatus(n, "실패: " + JSON.stringify(j)); return;
      }
      _awaitJob(j.job_id, function (job) {
        _layerBusy(n, stem, false);
        _rowStatus(n, job.status === "completed" ? "레이어 재생성 완료 ✓"
                                                 : ("실패: " + (job.error || JSON.stringify(job))));
        if (job.status === "completed") refreshRow(n);
      }, function (logs) {
        if (logs.length) _rowStatus(n, "레이어 재생성 중... " + logs[logs.length - 1]);
      }, 1200);
    })
    .catch(function (e) { _layerBusy(n, stem, false); _rowStatus(n, "오류: " + e); });
}

/* 눈 토글 / 제거 / 복구 — 사이드카 플래그만 바꾼다. 파일은 그대로 남는다. */
function setLayerState(n, stem, patch) {
  var b = { project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n), layer: stem };
  if (patch.hidden != null) b.hidden = patch.hidden;
  if (patch.removed != null) b.removed = patch.removed;
  _layerBusy(n, stem, true);
  return fetch(BACKEND + "/api/layers/state", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(b),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _layerBusy(n, stem, false);
      if (!j.ok) { _rowStatus(n, "실패: " + (j.error || JSON.stringify(j))); return; }
      refreshRow(n);
    })
    .catch(function (e) { _layerBusy(n, stem, false); _rowStatus(n, "오류: " + e); });
}

/* 벡터화 — 레이어당 1크레딧. 한 장이 실패해도 나머지는 계속된다. */
function vectorizeLayers(n, stems, force) {
  if (!stems.length) { _rowStatus(n, "벡터화할 레이어를 고르세요"); return; }
  if (!confirm("레이어 " + stems.length + "장을 벡터화합니다.\n\n"
             + "레이어당 1크레딧이 들고 장당 10초쯤 걸립니다.")) return;
  _rowStatus(n, "벡터화 중... (Recraft)");
  return fetch(BACKEND + "/api/layers/vectorize", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
                           layers: stems, force: !!force }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) {
        _rowStatus(n, "실패: " + (j.error || JSON.stringify(j))); return;
      }
      _awaitJob(j.job_id, function (job) {
        if (job.status !== "completed") {
          _rowStatus(n, "벡터화 실패: " + (job.error || "")); return;
        }
        var res = job.result || {};
        var okn = (res.ok || []).length, sk = (res.skipped || []).length,
            fl = (res.failed || []).length;
        _rowStatus(n, "벡터화 완료 " + okn + "장"
                    + (sk ? " (건너뜀 " + sk + ")" : "")
                    + (fl ? " — 실패 " + fl + ": "
                          + res.failed.map(function (f) { return f.layer; }).join(", ") : ""));
        refreshRow(n);
      }, function (logs) {
        if (logs.length) _rowStatus(n, "벡터화 중... " + logs[logs.length - 1]);
      }, 1500);
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* 벡터화 대상 — 전체 버튼은 SVG가 없는 살아 있는 레이어만 넘긴다(있는 것은 백엔드가 건너뛴다). */
function _lyrStemsOf(n, onlySelected) {
  var rows = $("sheet").querySelectorAll('.lyr-row[data-scene="' + n + '"]');
  var out = [];
  for (var i = 0; i < rows.length; i++) {
    if (rows[i].classList.contains("gone")) continue;
    if (onlySelected) {
      var cb = rows[i].querySelector("input.lyr-pick");
      if (!cb || !cb.checked) continue;
    }
    out.push(rows[i].getAttribute("data-layer"));
  }
  return out;
}

/* 목소리 프리셋 — 한 번 받아 두고 재생성 자리마다 고를 수 있게 한다.
   전에는 고를 자리가 아예 없어, 프로젝트에 걸린 것과 다른 목소리로 나와도
   패널에서 손쓸 방법이 없었다. */
var VOICES = null, VOICE_NOW = "";

function loadVoices() {
  if (!SELECTED_PROJECT) return Promise.resolve(null);
  return fetch(BACKEND + "/api/tts/settings?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      VOICES = j;
      VOICE_NOW = (j.config && j.config.voice_id) || "";
      return j;
    }).catch(function () { return null; });
}

/* 행 편집 패널에 끼울 목소리 고르개. 지금 걸린 것이 먼저 선택돼 있다. */
function voiceSelectHtml(n) {
  if (!VOICES) return "";
  var pr = (VOICES.presets && VOICES.presets.presets) || {};
  var h = '<label class="te-label" style="display:block;margin-top:6px">목소리 '
        + '<select class="te-voice" data-scene="' + n + '">';
  var seen = {};
  for (var k in pr) {
    if (!pr[k] || !pr[k].voice_id) continue;
    var vid = pr[k].voice_id;
    if (seen[vid]) continue;
    seen[vid] = 1;
    h += '<option value="' + vid + '"' + (vid === VOICE_NOW ? " selected" : "") + '>'
       + _esc((pr[k].label || pr[k].name || k) + " — " + vid.slice(0, 8)) + '</option>';
  }
  if (VOICE_NOW && !seen[VOICE_NOW]) {
    h += '<option value="' + VOICE_NOW + '" selected>프로젝트 설정 — '
       + _esc(VOICE_NOW.slice(0, 8)) + '</option>';
  }
  return h + '</select></label>';
}

function genTts(n, voice) {
  _rowStatus(n, "TTS 생성 중... (ElevenLabs)");
  var body = { project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n) };
  // 고르개에서 고른 목소리를 함께 보낸다. 안 고르면 프로젝트 설정을 따른다.
  var sel = $("sheet").querySelector('select.te-voice[data-scene="' + n + '"]');
  var v = voice || (sel ? sel.value : "");
  if (v) body.voice = v;
  return fetch(BACKEND + "/api/scenes/tts", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.status === "completed";
      _rowStatus(n, ok ? ("TTS 완료 (" + (j.result.duration || 0).toFixed(1) + "s)") : ("실패: " + JSON.stringify(j)));
      if (ok) refreshRow(n);      // 오디오 플레이어 표시(행 단위)
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* ✎ — 행의 텍스트 편집 패널 열고 닫기 */
function toggleTextEditor(n) {
  var pane = $("sheet").querySelector('.txt-edit[data-scene="' + n + '"]');
  if (!pane) return;
  pane.hidden = !pane.hidden;
  if (!pane.hidden) {
    var tas = pane.querySelectorAll("textarea");
    for (var i = 0; i < tas.length; i++) _autosize(tas[i]);
  }
}

/* TTS·자막 텍스트 저장. regen=true면 저장 후 그 씬 TTS 재생성. */
function saveSceneTexts(n, regen) {
  var pane = $("sheet").querySelector('.txt-edit[data-scene="' + n + '"]');
  if (!pane) return;
  var tts = pane.querySelector(".te-tts").value;
  var sub = pane.querySelector(".te-sub").value;
  _rowStatus(n, "텍스트 저장 중...");
  return fetch(BACKEND + "/api/scenes/texts", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
      narration_tts: tts, subtitle_text: sub,
    }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (!j.ok) { _rowStatus(n, "실패: " + JSON.stringify(j)); return; }
      _rowStatus(n, "텍스트 저장됨 ✓");
      if (regen) return genTts(n);
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* 전용 텍스트 필드를 비워 원고 기준으로 되돌림. kind: "tts" | "sub" */
function resetSceneText(n, kind) {
  var b = { project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n) };
  b[kind === "tts" ? "narration_tts" : "subtitle_text"] = "";
  _rowStatus(n, "원고 기준으로 되돌리는 중...");
  return fetch(BACKEND + "/api/scenes/texts", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (!j.ok) { _rowStatus(n, "실패: " + JSON.stringify(j)); return; }
      _rowStatus(n, "원고 기준으로 되돌림 ✓");
      refreshRow(n);
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}

/* ⤓ — 이 씬을 타임라인에 다시 놓는다. 평면 컴프라 씬 빌드가 곧 재배치다:
   빌드가 S{번호}_ 로 시작하는 레이어를 지우고 같은 시각 구간에 다시 넣는다.
   sceneNumber=null이면 전체. */
function exportToTimeline(sceneNumber) {
  var say = sceneNumber == null
    ? function (m) { var e = $("aeresult"); if (e) e.textContent = m; }
    : function (m) { _rowStatus(sceneNumber, m); };
  if (!SELECTED_PROJECT) { say("프로젝트를 먼저 선택하세요."); return; }
  if (typeof _assemble !== "function") { say("빌드 함수를 찾지 못했습니다."); return; }
  return _assemble(sceneNumber == null ? null : parseFloat(sceneNumber), say);
}

function exportAllToTimeline() { exportToTimeline(null); }

function loadTtsSettings() {
  if (!SELECTED_PROJECT) return;
  fetch(BACKEND + "/api/tts/settings?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var sel = $("ttsStyle"); if (!sel) return;
      var presets = (j.presets && j.presets.presets) || {};
      sel.innerHTML = Object.keys(presets).map(function (k) {
        return '<option value="' + k + '">' + _esc(presets[k].label || k) + '</option>';
      }).join("");
      if (j.config) {
        sel.value = j.config.style;
        $("ttsStatus").textContent = "현재: " + j.config.style + " / voice " + j.config.voice_id;
      }
    }).catch(function () {});
}

function saveTtsSettings() {
  if (!SELECTED_PROJECT) { $("ttsStatus").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var style = $("ttsStyle").value;
  var vid = ($("ttsVoiceId").value || "").trim();
  $("ttsStatus").textContent = "저장 중...";
  fetch(BACKEND + "/api/tts/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, style: style, voice_id: vid }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      $("ttsStatus").textContent = j.config
        ? ("저장됨 — " + j.config.style + " / voice " + j.config.voice_id) : ("실패: " + JSON.stringify(j));
      $("ttsVoiceId").value = "";
    }).catch(function (e) { $("ttsStatus").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  var b = $("btnSaveTts"); if (b) b.addEventListener("click", saveTtsSettings);
  var d = $("ttsSettings");
  if (d) d.addEventListener("toggle", function () { if (d.open) loadTtsSettings(); });
});

// 프로젝트 테마 드롭다운 — 카탈로그 로드 + 현재 프로젝트 테마 선택 + 변경 시 저장
function loadThemes() {
  var sel = $("projectTheme");
  if (!sel || !SELECTED_PROJECT) return;
  fetch(BACKEND + "/api/themes").then(function (r) { return r.json(); }).then(function (j) {
    var themeList = j.themes || [];
    fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
      .then(function (r) { return r.json(); }).then(function (sd) {
        var cur = (sd._theme && sd._theme.id) || "";
        sel.innerHTML = themeList.map(function (t) {
          return '<option value="' + t.id + '"' + (t.id === cur ? " selected" : "") + ">" + _esc(t.label || t.id) + "</option>";
        }).join("");
      });
  });
  sel.onchange = function () {
    fetch(BACKEND + "/api/themes/set-project", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, theme_id: sel.value }),
    }).then(function () { loadSheet(); });
  };
}

/* ===== 도구 구역 — AE 보조 기능(tools.jsx) ===== */
function _toolsSay(m) { var e = $("toolsStatus"); if (e) e.textContent = m; }

function _runTool(call) {
  var jsx;
  try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/tools.jsx"); }
  catch (e) { _toolsSay("jsx 로드 실패: " + e); return; }
  return evalScript(jsx + "\n" + call).then(function (r) { _toolsSay(r || "(빈 응답)"); });
}

function importSrtFile() {
  var inp = $("srtFile");
  if (!inp || !inp.files || !inp.files.length) { _toolsSay("SRT 파일을 고르세요"); return; }
  var reader = new FileReader();
  reader.onload = function () {
    _toolsSay("파싱 중...");
    fetch(BACKEND + "/api/tools/srt-parse", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ srt: String(reader.result || "") }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j.cues || !j.cues.length) { _toolsSay("실패: " + (j.error || "큐 없음")); return; }
        _toolsSay("AE에 넣는 중... (" + j.cues.length + "줄)");
        var tokens = j.tokens_path || "";   // 백엔드가 빌드와 동일 토큰 파일의 절대 경로를 실어 준다
        _runTool("akImportSrt(" + JSON.stringify(JSON.stringify(j.cues)) + ", " + JSON.stringify(tokens) + ");");
      })
      .catch(function (e) { _toolsSay("오류: " + e); });
  };
  reader.readAsText(inp.files[0]);
}

function bindTools() {
  var b1 = $("srtImportBtn");
  if (b1) b1.addEventListener("click", importSrtFile);
  var b2 = $("insertNullBtn");
  if (b2) b2.addEventListener("click", function () { _runTool("akInsertNull();"); });
  var b3 = $("presetApplyBtn");
  if (b3) b3.addEventListener("click", function () {
    var t = $("presetSelect").value;
    var a = $("presetAmt").value;
    _runTool("akApplyPreset(" + JSON.stringify(t) + ", " + JSON.stringify(a) + ");");
  });
}

document.addEventListener("DOMContentLoaded", bindTools);


// 미리보기 겹창 — 패널 안에 덮어 띄운다. 어도비 CEP 는 새 창을 못 연다.
function pvZoom(html, sceneNo) {
  var box = document.getElementById("pv-zoom");
  if (!box) return;
  box.querySelector(".inner").innerHTML = html;
  box.querySelector(".cap").textContent = sceneNo ? "씬 " + sceneNo : "";
  box.classList.add("on");
}
/* 닫기 — **문서에 위임한다.**
   겹창 마크업(`#pv-zoom`)이 index.html 에서 이 스크립트 **뒤에** 있다.
   스크립트가 읽히는 시점에는 그 요소가 아직 없어 `getElementById` 가
   null 을 돌려주고, 예전 코드는 거기서 `return` 해 핸들러를 한 번도 걸지
   못했다 — 겹창은 열리는데 ✕ 를 눌러도 닫히지 않던 원인이다.
   위임하면 마크업 순서를 타지 않는다. */
function _pvClose() {
  var box = document.getElementById("pv-zoom");
  if (!box) return;
  box.classList.remove("on");
  var inner = box.querySelector(".inner");
  if (inner) inner.innerHTML = "";
}
document.addEventListener("click", function (e) {
  var box = document.getElementById("pv-zoom");
  if (!box || !box.classList.contains("on")) return;
  var t = e.target;
  if (t === box || (t.classList && t.classList.contains("x"))
      || (t.closest && t.closest("#pv-zoom .x"))) _pvClose();
});
document.addEventListener("keydown", function (e) {
  var box = document.getElementById("pv-zoom");
  if (e.key === "Escape" && box && box.classList.contains("on")) _pvClose();
});

/* ===== 씬 비디오 생성 (힉스필드) =====
   모델마다 받는 파라미터도, 붙일 수 있는 이미지 칸도, 해상도 목록도 다르다.
   그 차이를 손으로 적어 두면 힉스필드가 바꿀 때마다 어긋나므로,
   백엔드가 CLI 산출을 그대로 넘겨 주고 화면은 그것만 보고 짠다. */
var VID_MODELS = null, VID_SCENE = null, VID_PICK = {}, VID_SCENE_IMG = "";

function openVideoModal(n) {
  VID_SCENE = n; VID_PICK = {};
  $("vidStatus").textContent = "—";
  $("vidModal").hidden = false;
  $("vidPrompt").value = "";

  // 씬이 들고 있는 프롬프트를 먼저 채운다 — 빈 칸에서 시작하면 손이 많이 간다
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      IMG_DIR = j.dir || IMG_DIR;
      var s = (j.scenes || []).filter(function (x) { return x.sceneNumber === parseFloat(n); })[0];
      if (s) $("vidPrompt").value = s.image_prompt || s.visual_summary || "";
      VID_SCENE_IMG = (s && s._image) || "";
      _seedVidStart();
      _renderVidSlots();
    });

  if (VID_MODELS) { _renderVidModel(); return; }
  fetch(BACKEND + "/api/video/models").then(function (r) { return r.json(); })
    .then(function (j) {
      VID_MODELS = j.models || [];
      if (!j.cli) $("vidStatus").textContent = "higgsfield CLI 를 찾을 수 없습니다.";
      var sel = $("vidModel");
      sel.innerHTML = VID_MODELS.map(function (m, i) {
        return '<option value="' + i + '">' + _esc(m.display_name) + "</option>";
      }).join("");
      _renderVidModel();
    })
    .catch(function (e) { $("vidStatus").textContent = "모델 목록 오류: " + e; });
}

/* 씬 그림을 첫 프레임으로 미리 넣는다. 비디오는 그 씬의 그림에서 움직이기
   시작하는 것이 기본이고, 매번 손으로 고르게 하면 잊기 쉽다.

   **모델이 `start_image` 를 안 받으면 `image_references` 로 넣는다.**
   gemini_omni 는 그 칸이 아예 없어, 그대로 보내면 CLI 가 거절한다. */
function _seedVidStart() {
  if (!VID_SCENE_IMG) return;
  var m = _vidModel();
  var slots = (m && m.image_slots) || [];
  var already = false;
  for (var k in VID_PICK) {
    if ((VID_PICK[k] || []).indexOf(VID_SCENE_IMG) >= 0) { already = true; break; }
  }
  if (already) return;
  if (slots.indexOf("start_image") >= 0) VID_PICK.start_image = [VID_SCENE_IMG];
  else if (slots.indexOf("image_references") >= 0) VID_PICK.image_references = [VID_SCENE_IMG];
}

/* **인덱스로 고른다.** 「Seedance 2.0」과 「Seedance 2.0 Fast」는 job_type 이
   같아(`seedance_2_0`), 이름으로 찾으면 늘 앞의 것이 잡힌다 — Fast 를 골라도
   std 로 나간다. */
function _vidModel() {
  var i = parseInt($("vidModel").value, 10);
  return (VID_MODELS || [])[i] || null;
}

/* 파라미터 칸을 모델 스펙대로 그린다. enum 이 있으면 드롭다운, 없으면 입력칸. */
function _renderVidModel() {
  var m = _vidModel();
  if (!m) return;
  $("vidRules").innerHTML = (m.rules || []).map(function (r) {
    return "· " + _esc(r);
  }).join("<br>");
  var h = "";
  for (var i = 0; i < m.params.length; i++) {
    var p = m.params[i];
    if (p.name === "prompt") continue;                       // 프롬프트는 아래 큰 칸
    if (p.name.indexOf("image") >= 0 || p.name.indexOf("reference") >= 0) continue;
    if (p.type === "boolean") {
      h += '<label class="vp"><input type="checkbox" data-p="' + p.name + '"'
         + (p["default"] ? " checked" : "") + '> ' + _esc(p.name) + "</label>";
    } else if (p["enum"]) {
      // 프리셋(예: Fast 의 mode=fast)이 있으면 기본값 대신 그것을 고른다
      var pre = (m.preset || {})[p.name];
      var cur = pre == null ? p["default"] : pre;
      h += '<label class="vp">' + _esc(p.name) + ' <select data-p="' + p.name + '">'
         + p["enum"].map(function (v) {
             return '<option value="' + v + '"' + (String(v) === String(cur) ? " selected" : "")
                  + ">" + _esc(String(v)) + "</option>";
           }).join("") + "</select></label>";
    } else if (p.type === "integer" || p.type === "number") {
      h += '<label class="vp">' + _esc(p.name) + ' <input type="number" data-p="' + p.name
         + '" value="' + (p["default"] == null ? "" : p["default"]) + '"></label>';
    }
  }
  $("vidParams").innerHTML = '<div class="vp-grid">' + h + "</div>";
  // 모델을 바꾸면 그 모델이 **안 받는 칸은 버린다.** 남겨 두면 CLI 가 거절한다.
  for (var k in VID_PICK) {
    if (m.image_slots.indexOf(k) < 0) delete VID_PICK[k];
  }
  _seedVidStart();
  _renderVidSlots();
}

/* 이미지 칸 — 모델이 받는 것만 낸다. 씬 그림·인물 시트·실물 자료에서 고른다. */
function _renderVidSlots() {
  var m = _vidModel();
  if (!m) { $("vidSlots").innerHTML = ""; return; }
  var lim = m.max_images == null ? "" : ' (최대 ' + m.max_images + '장)';
  var h = '<div class="label" style="margin-top:8px">참조 이미지' + lim + '</div>';
  for (var i = 0; i < m.image_slots.length; i++) {
    var slot = m.image_slots[i];
    var cur = VID_PICK[slot] || [];
    /* **붙인 그림을 전부 보여 준다.** 「3장」이라고만 적으면 무엇을 붙였는지
       알 수 없어, 엉뚱한 것을 붙여 놓고도 모른 채 돌리게 된다.
       한 장씩 뺄 수 있게 각 그림에 ✕ 를 단다. */
    h += '<div class="vslot"><span class="vslot-name">' + _esc(slot) + "</span>"
       + '<button class="mini vslot-add" data-slot="' + slot + '">'
       + (cur.length ? "더 고르기" : "고르기") + "</button>"
       + (cur.length ? '<button class="mini vslot-clr" data-slot="' + slot + '">비우기</button>'
                     : '<span class="vslot-cnt">없음</span>')
       + "</div>";
    if (cur.length) {
      h += '<div class="vthumbs">';
      for (var q = 0; q < cur.length; q++) {
        var isScene = cur[q] === VID_SCENE_IMG;
        h += '<div class="vthumb' + (isScene ? " is-scene" : "") + '">'
           + '<img src="file://' + (IMG_DIR || "") + "/" + cur[q] + '" alt="">'
           + '<button class="vthumb-x" data-slot="' + slot + '" data-i="' + q + '"'
           + ' title="이 그림만 뺍니다">✕</button>'
           + '<span class="vthumb-cap">'
           + _esc(isScene ? "이 씬 그림" : cur[q].split("/").pop().slice(0, 16))
           + "</span></div>";
      }
      h += "</div>";
    }
  }
  $("vidSlots").innerHTML = h;
  var adds = $("vidSlots").querySelectorAll(".vslot-add");
  for (var a = 0; a < adds.length; a++) {
    adds[a].addEventListener("click", function () { _pickVidImage(this.getAttribute("data-slot")); });
  }
  var clrs = $("vidSlots").querySelectorAll(".vslot-clr");
  for (var c = 0; c < clrs.length; c++) {
    clrs[c].addEventListener("click", function () {
      delete VID_PICK[this.getAttribute("data-slot")]; _renderVidSlots();
    });
  }
  var xs = $("vidSlots").querySelectorAll(".vthumb-x");
  for (var x = 0; x < xs.length; x++) {
    xs[x].addEventListener("click", function () {
      var sl = this.getAttribute("data-slot"), ix = parseInt(this.getAttribute("data-i"), 10);
      (VID_PICK[sl] || []).splice(ix, 1);
      if (!(VID_PICK[sl] || []).length) delete VID_PICK[sl];
      _renderVidSlots();
    });
  }
}

/* 이미지 고르기는 재생성 모달의 참조 목록을 그대로 쓴다 — 같은 것을 두 벌
   만들면 한쪽만 고치는 일이 생긴다. */
function _pickVidImage(slot) {
  fetch(BACKEND + "/api/scenes/image-refs?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var all = (j.scenes || []).map(function (x) { return x.rel; })
        .concat((j.characters || []).map(function (x) { return x.rel; }))
        .concat((j.docs || []).map(function (x) { return x.rel; }));
      IMG_DATA = j; IMG_TAB = "scenes"; IMG_REFS = {};
      // 이미 붙은 것을 체크된 채로 연다 — 「더 고르기」가 앞의 것을 지우면 안 된다
      var had = VID_PICK[slot] || [];
      for (var q = 0; q < had.length; q++) IMG_REFS[had[q]] = true;
      VID_SLOT_TARGET = slot;
      $("imgModal").hidden = false;
      _setImgMode("gen");
      $("imgRefBlock").hidden = false;
      $("imgPromptLabel").textContent = "이 목록에서 참조로 쓸 그림을 고른 뒤 「고른 것 쓰기」를 누르세요.";
      $("imgPrompt").value = "";
      $("imgSubmit").textContent = "고른 것 쓰기";
      _renderImgRefs();
    });
}
var VID_SLOT_TARGET = null;

function genSceneVideo(n) {
  var m = _vidModel();
  if (!m) return Promise.resolve();
  var params = { prompt: $("vidPrompt").value.trim() };
  var els = $("vidParams").querySelectorAll("[data-p]");
  for (var i = 0; i < els.length; i++) {
    var k = els[i].getAttribute("data-p");
    params[k] = els[i].type === "checkbox" ? els[i].checked : els[i].value;
  }
  _rowStatus(n, "비디오 생성 중... (힉스필드, 몇 분)");
  $("vidStatus").textContent = "생성 중... 창을 닫아도 계속됩니다.";
  return fetch(BACKEND + "/api/scenes/video", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseFloat(n),
                           job_type: m.job_type, params: params, images: VID_PICK }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var ok = j.result && j.result.status === "completed";
      _rowDone(n, ok, ok ? "비디오 완료 ✓"
                         : ("실패: " + JSON.stringify(j.result || j).slice(0, 200)));
    })
    .catch(function (e) { _rowBusy(n, false, "오류: " + e); });
}


/* 씬의 판본을 읽어 후보 띠를 그린다. 하나뿐이면 자리를 차지하지 않는다. */
/* 파일명이 같은데 내용만 바뀌는 경우가 있다(업스케일·편집이 덮을 때).
   그때 옛 그림이 남지 않도록 후보 썸네일에 도장을 붙인다. */
var IV_STAMP = 1;

function _loadVersions(box) {
  var n = box.getAttribute("data-scene");
  fetch(BACKEND + "/api/scenes/image-versions?project_id="
        + encodeURIComponent(SELECTED_PROJECT) + "&sceneNumber=" + encodeURIComponent(n))
    .then(function (r) { return r.json(); })
    .then(function (j) { _paintVersions(box, j); })
    .catch(function (e) {
      // 조용히 비우면 「후보가 없다」와 「불러오지 못했다」가 같아 보인다
      box.innerHTML = '<div class="iv-msg">후보 조회 오류: ' + _esc(String(e)) + "</div>";
    });
}

/* 받은 후보를 박스에 그린다. 하나씩 받든 한 번에 받든 여기로 모인다 —
   두 벌로 두면 한쪽만 고치는 일이 생긴다. */
function _paintVersions(box, j) {
  var n = box.getAttribute("data-scene");
  if (j && j.error) {
    box.innerHTML = '<div class="iv-msg">후보 조회 실패: ' + _esc(j.error) + "</div>";
    return;
  }
  var vs = (j && j.versions) || [];
  if (vs.length < 2) { box.innerHTML = ""; return; }   // 판본이 하나뿐 — 대부분의 씬
  var dir = IMG_DIR || "";
  box.innerHTML = '<div class="iv-strip">' + vs.map(function (x) {
    var on = x.rel === j.selected;
    return '<img class="iv' + (on ? " on" : "") + '" src="file://' + dir + "/" + x.rel + "?t=" + IV_STAMP
         + '" data-rel="' + x.rel + '" data-scene="' + n + '"'
         + ' title="' + _esc(x.name) + (on ? " (지금 쓰는 것)" : " — 눌러서 바꿉니다") + '">';
  }).join("") + "</div>";

  /* **박스에 위임한다.** 각 <img> 에 직접 걸면 innerHTML 을 다시 쓸 때마다
     리스너가 사라진다 — 한 번 바꾸면 그다음부터는 눌러도 아무 일이 없었다. */
  if (!box._ivBound) {
    box._ivBound = true;
    box.addEventListener("click", function (ev) {
      var im = ev.target;
      if (!im || im.tagName !== "IMG" || im.className.indexOf("iv") < 0) return;
      if (im.className.indexOf("on") >= 0) return;        // 지금 쓰는 것
      var sc = im.getAttribute("data-scene");
      var rel = im.getAttribute("data-rel");
      _rowStatus(sc, "이미지 바꾸는 중...");
      var sibs = box.querySelectorAll("img.iv");
      for (var q = 0; q < sibs.length; q++) {
        sibs[q].className = "iv" + (sibs[q] === im ? " on" : "");
      }
      fetch(BACKEND + "/api/scenes/select-image", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: SELECTED_PROJECT,
                               sceneNumber: parseFloat(sc), rel: rel }),
      }).then(function (r) { return r.json(); })
        .then(function (res) {
          if (res.error) { _rowStatus(sc, "바꾸지 못했습니다: " + res.error); return; }
          IV_STAMP = IV_STAMP + 1;
          _rowStatus(sc, "이미지 바꿈 \u2713 " + rel.split("/").pop());
          refreshRow(sc);
        })
        .catch(function (e) { _rowStatus(sc, "바꾸기 오류: " + e); });
    });
  }
}


/* 후보를 한 번에 받아 각 박스에 나눠 준다. 시트를 처음 열 때 쓴다. */
function _loadVersionsAll(boxes) {
  fetch(BACKEND + "/api/scenes/image-versions?project_id="
        + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var by = {};
      (j.scenes || []).forEach(function (x) { by[String(x.sceneNumber)] = x; });
      for (var i = 0; i < boxes.length; i++) {
        var box = boxes[i];
        var d = by[String(box.getAttribute("data-scene"))];
        _paintVersions(box, d || { versions: [], selected: "" });
      }
    })
    .catch(function (e) {
      // 일괄이 실패하면 하나씩이라도 — 조용히 비우지 않는다
      for (var i = 0; i < boxes.length; i++) _loadVersions(boxes[i]);
    });
}
