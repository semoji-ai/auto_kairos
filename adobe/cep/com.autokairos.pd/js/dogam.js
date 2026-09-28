/* 기법 도감 탭 — 세모지 도감 기법을 AE 에 바로 건다.

   목록  : jsx/dogam/registry.json (scripts/sync_dogam.py 가 만든다 — AE 구현이 있는 기법만)
   미리보기: 카드 = jpg, 올리면 mp4 재생(jsx/dogam/assets/previews_src → 세모지 도감 폴더 링크)
   적용  : evalScript(json2 + dogam/core.jsx + techniques/<id>.jsx + "AKD.apply(...)")
           comp·layers·t 를 넘기지 않으므로 AE 쪽에서 활성 컴프·선택 레이어·CTI 를 씁니다.
   다시 적용·제거: 선택 레이어의 ak-dogam 마커가 기준(AKD.selectedInfo → reapply/remove).

   main.js 의 readLocal·evalScript 를 쓴다(main.js → dogam.js 순 로드). */

var DG = { reg: null, sel: null, cards: {}, hoverVideo: null, lastInfo: null };

function _dg(id) { return document.getElementById(id); }
function _dgEsc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
function _dgSay(m, bad) { var e = _dg("dgStatus"); if (e) { e.textContent = m; e.style.color = bad ? "#ff8a80" : ""; } }

/* 확장 폴더 실제 경로(ExtendScript 가 에셋을 읽는 곳). 심링크 경로여도 File 이 따라간다 */
function _dgExtPath() {
  try {
    var p = window.__adobe_cep__.getSystemPath("extension");
    return decodeURI(p || "").replace(/^file:\/\//, "");
  } catch (e) { return ""; }
}

var DG_KIND = { layer: "레이어형", element: "요소형", scene: "장면형" };
var DG_GROUP = { timing: "타이밍", motion: "움직임", size: "크기", look: "모양·색" };

function dogamInit() {
  if (DG.reg) return;
  try { DG.reg = JSON.parse(readLocal("./jsx/dogam/registry.json")); }
  catch (e) {
    _dg("dgGrid").innerHTML = '<div class="box">registry.json 을 읽지 못했습니다 — adobe 폴더에서 <b>python3 scripts/sync_dogam.py</b> 를 먼저 실행하세요.<br>' + _dgEsc(e) + "</div>";
    return;
  }
  var cats = DG.reg.categories || [], sel = _dg("dgCat");
  for (var i = 0; i < cats.length; i++) { var o = document.createElement("option"); o.value = cats[i]; o.textContent = cats[i]; sel.appendChild(o); }
  _dg("dgSearch").addEventListener("input", dogamRender);
  _dg("dgCat").addEventListener("change", dogamRender);
  _dg("dgKind").addEventListener("change", dogamRender);
  _dg("dgApply").addEventListener("click", dogamApply);
  _dg("dgReapply").addEventListener("click", dogamReapply);
  _dg("dgRemove").addEventListener("click", dogamRemove);
  _dg("dgReadSel").addEventListener("click", dogamReadSelection);
  dogamRender();
}

function _dgMatch(t, q) {
  if (!q) return true;
  var hay = [t.id, t.name, t.summary, t.category, (t.tags || []).join(" ")].join(" ").toLowerCase();
  var parts = q.toLowerCase().split(/\s+/);
  for (var i = 0; i < parts.length; i++) { if (parts[i] && hay.indexOf(parts[i]) < 0) return false; }
  return true;
}

function dogamRender() {
  var grid = _dg("dgGrid"), q = _dg("dgSearch").value.trim(), cat = _dg("dgCat").value, kind = _dg("dgKind").value;
  var list = (DG.reg.techniques || []).filter(function (t) { return (!cat || t.category === cat) && (!kind || t.kind === kind) && _dgMatch(t, q); });
  if (!list.length) { grid.innerHTML = '<div class="box">맞는 기법이 없습니다.</div>'; return; }
  grid.innerHTML = list.map(function (t) {
    return '<div class="dg-card' + (DG.sel && DG.sel.id === t.id ? " sel" : "") + '" data-id="' + _dgEsc(t.id) + '" title="' + _dgEsc(t.summary) + '">' +
      '<div class="dg-thumb">' + (t.previewJpg ? '<img loading="lazy" src="' + _dgEsc(t.previewJpg) + '" onerror="this.style.display=\'none\'">' : "") + "</div>" +
      '<div class="dg-meta"><div class="dg-name">' + _dgEsc(t.name) + "</div>" +
      '<div class="dg-sub"><span class="dg-badge ' + t.kind + '">' + (DG_KIND[t.kind] || t.kind) + "</span>" +
      (t.support === "partial" ? '<span class="dg-badge partial">부분</span>' : "") + _dgEsc(t.category) + "</div></div></div>";
  }).join("");
  var cards = grid.querySelectorAll(".dg-card");
  for (var i = 0; i < cards.length; i++) {
    cards[i].addEventListener("click", function () { dogamSelect(this.getAttribute("data-id")); });
    cards[i].addEventListener("mouseenter", _dgHoverOn);
    cards[i].addEventListener("mouseleave", _dgHoverOff);
  }
}

/* 호버 미리보기: mp4 를 그 자리에서 재생. 로드 실패(링크 없음)면 조용히 jpg 유지 */
function _dgHoverOn() {
  var t = _dgById(this.getAttribute("data-id")); if (!t || !t.previewMp4) return;
  _dgHoverOff();
  var v = document.createElement("video");
  v.muted = true; v.loop = true; v.autoplay = true; v.playsInline = true; v.src = t.previewMp4;
  v.onerror = function () { if (v.parentNode) v.parentNode.removeChild(v); };
  this.querySelector(".dg-thumb").appendChild(v);
  DG.hoverVideo = v;
}
function _dgHoverOff() { var v = DG.hoverVideo; if (v && v.parentNode) { v.pause(); v.parentNode.removeChild(v); } DG.hoverVideo = null; }
function _dgById(id) { var a = (DG.reg && DG.reg.techniques) || []; for (var i = 0; i < a.length; i++) if (a[i].id === id) return a[i]; return null; }

function dogamSelect(id, preset) {
  var t = _dgById(id); if (!t) return;
  DG.sel = t;
  var cs = document.querySelectorAll(".dg-card");
  for (var i = 0; i < cs.length; i++) cs[i].classList.toggle("sel", cs[i].getAttribute("data-id") === id);
  _dg("dgDetail").hidden = false;
  var hint = t.kind === "layer" ? (t.create ? "레이어를 고르면 그 레이어에, 안 고르면 새로 만들어 겁니다." : "타임라인에서 레이어를 고른 뒤 누르세요.")
    : t.kind === "element" ? "현재 시각에 새 레이어(프리컴프)를 만듭니다." : "현재 시각에 전환·카메라를 겁니다. 고른 레이어가 있으면 그 레이어를 대상으로 합니다.";
  _dg("dgHead").innerHTML =
    (t.previewMp4 ? '<video muted loop autoplay playsinline src="' + _dgEsc(t.previewMp4) + '" poster="' + _dgEsc(t.previewJpg || "") + '"></video>' : "") +
    "<h3>" + _dgEsc(t.name) + "</h3>" +
    '<div><span class="dg-badge ' + t.kind + '">' + (DG_KIND[t.kind] || t.kind) + '</span><span class="dg-badge' + (t.support === "partial" ? " partial" : "") + '">AE ' + (t.support === "partial" ? "부분 지원" : "그대로") + "</span>" +
    '<span class="dg-badge">' + _dgEsc(t.id) + "</span></div>" +
    '<div class="dg-sum">' + _dgEsc(t.summary) + "</div>" +
    '<div class="dg-sum" style="color:#9aa0a6">' + _dgEsc(hint) + (t.aeNote ? "<br>⚠ " + _dgEsc(t.aeNote) : "") + "</div>";
  var v = _dg("dgHead").querySelector("video"); if (v) v.onerror = function () { v.style.display = "none"; };
  _dgBuildForm(t, preset && preset.params);
  _dgBuildContent(t, preset && preset.content);
  _dgSay("—");
}

/* 변수 폼: 도감 스키마 그대로(key·기본값·범위·단위·그룹) */
function _dgHex(c) { c = String(c || "#000000"); if (/^#[0-9a-f]{3}$/i.test(c)) c = "#" + c[1] + c[1] + c[2] + c[2] + c[3] + c[3]; return /^#[0-9a-f]{6}$/i.test(c) ? c : "#000000"; }
function _dgBuildForm(t, preset) {
  var box = _dg("dgForm"), html = "", groups = {}, order = [];
  (t.params || []).forEach(function (p) { var g = p.group || "etc"; if (!groups[g]) { groups[g] = []; order.push(g); } groups[g].push(p); });
  order.forEach(function (g) {
    html += '<div class="dg-grp">' + _dgEsc(DG_GROUP[g] || g) + "</div>";
    groups[g].forEach(function (p) {
      var v = preset && preset[p.key] !== undefined ? preset[p.key] : p["default"], k = _dgEsc(p.key);
      var lab = '<label title="' + k + '">' + _dgEsc(p.label || p.key) + "</label>";
      if (p.type === "number") {
        html += '<div class="dg-row" data-key="' + k + '" data-type="number">' + lab +
          '<input type="range" min="' + p.min + '" max="' + p.max + '" step="' + (p.step || 1) + '" value="' + v + '">' +
          '<input type="number" min="' + p.min + '" max="' + p.max + '" step="' + (p.step || 1) + '" value="' + v + '"><span class="dg-unit">' + _dgEsc(p.unit || "") + "</span></div>";
      } else if (p.type === "color") {
        html += '<div class="dg-row" data-key="' + k + '" data-type="color">' + lab + '<input type="color" value="' + _dgHex(v) + '"><span class="dg-unit"></span></div>';
      } else if (p.type === "boolean") {
        html += '<div class="dg-row" data-key="' + k + '" data-type="boolean">' + lab + '<input type="checkbox"' + (v ? " checked" : "") + "></div>";
      } else if (p.options) {
        html += '<div class="dg-row" data-key="' + k + '" data-type="string">' + lab + "<select>" + p.options.map(function (o) { return '<option value="' + _dgEsc(o) + '"' + (o === v ? " selected" : "") + ">" + _dgEsc(o) + "</option>"; }).join("") + "</select></div>";
      } else {
        html += '<div class="dg-row" data-key="' + k + '" data-type="string">' + lab + '<input type="text" value="' + _dgEsc(v) + '"></div>';
      }
    });
  });
  box.innerHTML = html || '<div class="dg-sum">조절 변수가 없습니다.</div>';
  // 슬라이더 ↔ 숫자 칸 동기화 + 기본값과 다르면 표시
  var rows = box.querySelectorAll(".dg-row");
  for (var i = 0; i < rows.length; i++) {
    (function (row) {
      var ins = row.querySelectorAll("input,select");
      for (var j = 0; j < ins.length; j++) {
        ins[j].addEventListener("input", function () {
          if (row.getAttribute("data-type") === "number") { for (var m = 0; m < ins.length; m++) if (ins[m] !== this) ins[m].value = this.value; }
          row.classList.add("changed");
        });
      }
    })(rows[i]);
  }
}
function _dgReadForm() {
  var out = {}, rows = _dg("dgForm").querySelectorAll(".dg-row");
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i], k = r.getAttribute("data-key"), ty = r.getAttribute("data-type"), el = r.querySelector("input,select");
    if (ty === "number") out[k] = parseFloat(el.value);
    else if (ty === "boolean") out[k] = el.checked;
    else out[k] = el.value;
  }
  return out;
}

/* 내용 폼: 글자·좌표·데이터(기본값 = 도감 데모). 문자열·숫자는 칸, 배열·객체는 JSON */
function _dgBuildContent(t, preset) {
  var c = t.content || {}, html = "";
  Object.keys(c).forEach(function (k) {
    var v = preset && preset[k] !== undefined ? preset[k] : c[k], kk = _dgEsc(k);
    if (typeof v === "number") html += '<div class="dg-row" data-key="' + kk + '" data-type="number"><label>' + kk + '</label><input type="number" value="' + v + '" style="flex:1;width:auto"></div>';
    else if (typeof v === "boolean") html += '<div class="dg-row" data-key="' + kk + '" data-type="boolean"><label>' + kk + '</label><input type="checkbox"' + (v ? " checked" : "") + "></div>";
    else if (typeof v === "string" && v.indexOf("\n") < 0) html += '<div class="dg-row" data-key="' + kk + '" data-type="string"><label>' + kk + '</label><input type="text" value="' + _dgEsc(v) + '" style="flex:1"></div>';
    else if (typeof v === "string") html += '<div class="dg-row" data-key="' + kk + '" data-type="text"><label>' + kk + "</label><textarea>" + _dgEsc(v) + "</textarea></div>";
    else html += '<div class="dg-row" data-key="' + kk + '" data-type="json"><label>' + kk + "</label><textarea>" + _dgEsc(JSON.stringify(v, null, 1)) + "</textarea></div>";
  });
  _dg("dgContent").innerHTML = html || '<div class="dg-sum">내용 입력이 없습니다.</div>';
  _dg("dgContentBox").open = !!html && (t.kind !== "layer");
}
function _dgReadContent() {
  var out = {}, rows = _dg("dgContent").querySelectorAll(".dg-row");
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i], k = r.getAttribute("data-key"), ty = r.getAttribute("data-type"), el = r.querySelector("input,textarea");
    if (ty === "number") out[k] = parseFloat(el.value);
    else if (ty === "boolean") out[k] = el.checked;
    else if (ty === "json") { try { out[k] = JSON.parse(el.value); } catch (e) { throw new Error("내용 '" + k + "' JSON 형식 오류: " + e.message); } }
    else out[k] = el.value;
  }
  return out;
}

/* AE 호출 공통: json2 + core + (기법 파일들) + 호출문 → 결과 JSON */
function _dgRun(ids, call) {
  var jsx;
  try {
    jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/dogam/core.jsx") + "\n";
    for (var i = 0; i < ids.length; i++) jsx += readLocal("./jsx/dogam/techniques/" + ids[i] + ".jsx") + "\n";
  } catch (e) { _dgSay("jsx 로드 실패: " + e, true); return Promise.resolve(null); }
  jsx += "AKD.assetsRoot = " + JSON.stringify(_dgExtPath() + "/jsx/dogam/assets") + ";\n";
  // try 로 감싼다 — 스크립트 오류가 모달로 뜨면 AE 가 멈춘다
  var wrapped = jsx + "(function(){ try { return " + call + "; } catch (e) { return '{\"ok\":false,\"error\":' + AKD.stringify(String(e) + (e.line ? ' (줄 ' + e.line + ')' : '')) + '}'; } })();";
  return evalScript(wrapped).then(function (r) {
    var o = null;
    try { o = JSON.parse(r); } catch (e) { o = { ok: false, error: "AE 응답을 읽지 못했습니다: " + r }; }
    return o;
  });
}
function _dgReport(o) {
  if (!o) return;
  if (o.ok) _dgSay("✅ " + (o.msg || "완료") + (o.names && o.names.length ? "\n새 레이어: " + o.names.slice(0, 8).join(", ") + (o.names.length > 8 ? " …" : "") : ""));
  else _dgSay("⚠ " + (o.error || "실패"), true);
}

function dogamApply() {
  var t = DG.sel; if (!t) return;
  var P, C;
  try { P = _dgReadForm(); C = _dgReadContent(); } catch (e) { _dgSay("⚠ " + e.message, true); return; }
  _dgSay("AE 에 거는 중…");
  _dgRun([t.id], "AKD.apply(" + JSON.stringify(t.id) + ", {params: " + JSON.stringify(P) + ", content: " + JSON.stringify(C) + "})").then(_dgReport);
}

/* 다시 적용: 선택 레이어의 최근 묶음 id 를 먼저 읽고, 그 기법 파일을 실어 reapply.
   폼이 같은 기법이면 폼 변수로, 아니면 마커에 기록된 변수 그대로 */
function dogamReapply() {
  _dgSay("선택 레이어 확인 중…");
  _dgRun([], "AKD.selectedInfo()").then(function (info) {
    if (!info || !info.ok) { _dgReport(info); return; }
    var it = _dgLatest(info);
    if (!it) { _dgSay("⚠ 선택 레이어에 기법 도감 마커(ak-dogam)가 없습니다.", true); return; }
    var same = DG.sel && DG.sel.id === it.id, P = {}, C = {};
    try { if (same) { P = _dgReadForm(); C = _dgReadContent(); } } catch (e) { _dgSay("⚠ " + e.message, true); return; }
    _dgSay("다시 거는 중… (" + it.id + ")");
    _dgRun([it.id], "AKD.reapply({group: " + JSON.stringify(it.group) + ", params: " + JSON.stringify(P) + ", content: " + JSON.stringify(C) + "})").then(_dgReport);
  });
}
function dogamRemove() {
  _dgSay("제거 중…");
  _dgRun([], "AKD.remove({})").then(_dgReport);
}
function _dgLatest(info) {
  var best = null, a = info.items || [];
  for (var i = 0; i < a.length; i++) if (!best || a[i].t >= best.t) best = a[i];
  return best;
}
/* 선택 레이어에 걸린 기법을 읽어 폼에 채운다(그 값에서 고쳐 [다시 적용]) */
function dogamReadSelection() {
  _dgRun([], "AKD.selectedInfo()").then(function (info) {
    var box = _dg("dgSelInfo");
    if (!info || !info.ok) { box.textContent = "⚠ " + ((info && info.error) || "읽기 실패"); return; }
    if (!info.comp) { box.textContent = "열린 컴프가 없습니다."; return; }
    var a = info.items || [];
    if (!a.length) { box.textContent = info.comp + " — 선택 " + info.selected + "개, 기법 도감 마커 없음"; return; }
    box.textContent = a.map(function (x) { return x.layer + " ← " + x.id + " (" + x.role + ", " + Math.round(x.t * 30) + "f)"; }).join("\n");
    var it = _dgLatest(info);
    if (_dgById(it.id)) { dogamSelect(it.id, { params: it.params, content: it.content }); _dgSay("선택 레이어의 「" + it.id + "」 변수를 불러왔습니다 — 고친 뒤 [다시 적용]"); }
  });
}
