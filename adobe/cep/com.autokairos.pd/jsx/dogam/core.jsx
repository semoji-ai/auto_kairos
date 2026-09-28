/* 기법 도감(dogam) — AE 공용 코어.
   세모지 '기법 도감'(semoji-motion/dogam)의 기법을 AE 레이어·키프레임으로 옮기는 라이브러리입니다.

   원칙 (사용자 AE 작업 방식)
     · 모든 모션은 키프레임입니다. 표현식은 불가피할 때만 쓰고 그 자리에 사유를 적습니다.
     · 레이어 이름은 "NN 요소명"(NN = 씬 번호), 효과·마스크는 "AKD·" 접두 — 제거할 때 이 이름으로 찾습니다.
     · 적용한 레이어마다 마커 "ak-dogam:<기법 id>" 를 남기고, 마커 파라미터에 변수·적용 시각·되돌리기 기록을 둡니다.
       → AKD.reapply(레이어 또는 묶음 id) / AKD.remove(...) 가 이 마커만 보고 동작합니다.
     · 이징은 Remotion 쪽 cubic-bezier 를 AE 템포럴 이즈(속도·영향)로 정확히 환산합니다(AKD.anim).

   로드 순서: json2.jsx → dogam/core.jsx → dogam/techniques/<id>.jsx (여러 개 가능)
   호출:     AKD.apply("stamp-slam", {comp, layers, t, params, content, assetsRoot})  → JSON 문자열
   ExtendScript(ES3) 호환 — var/function 만 씁니다. */

var AKD = (typeof AKD === "object" && AKD) ? AKD : {};

(function (A) {
  A.VERSION = "0.1.0";
  A._reg = A._reg || {};

  // ── JSON 직렬화(json2.jsx 는 파싱만 있음) ─────────────────────────────
  function q(s) {
    return '"' + String(s).replace(/[\\"\u0000-\u001f]/g, function (c) {
      var m = { '"': '\\"', "\\": "\\\\", "\n": "\\n", "\r": "\\r", "\t": "\\t" };
      return m[c] || ("\\u" + ("0000" + c.charCodeAt(0).toString(16)).slice(-4));
    }) + '"';
  }
  A.stringify = function (v) {
    if (v === null || v === undefined) { return "null"; }
    var t = typeof v;
    if (t === "number") { return isFinite(v) ? String(Math.round(v * 1e6) / 1e6) : "null"; }
    if (t === "boolean") { return v ? "true" : "false"; }
    if (t === "string") { return q(v); }
    if (v instanceof Array) {
      var a = [];
      for (var i = 0; i < v.length; i++) { a.push(A.stringify(v[i])); }
      return "[" + a.join(",") + "]";
    }
    var o = [];
    for (var k in v) { if (v.hasOwnProperty(k) && typeof v[k] !== "function") { o.push(q(k) + ":" + A.stringify(v[k])); } }
    return "{" + o.join(",") + "}";
  };
  A.parse = function (s) {
    if (typeof JSON === "object" && JSON.parse) { return JSON.parse(s); }
    return eval("(" + s + ")");
  };

  // ── 등록 ─────────────────────────────────────────────────────────────
  /* def = { kind: "layer"|"element"|"scene", name, params: {기본값}, content: {기본 내용},
             create: 선택이 없을 때 스스로 대상을 만드는가(layer 형 옵션), apply: function(X) } */
  A.register = function (id, def) { def.id = id; A._reg[id] = def; return def; };
  A.list = function () { var a = []; for (var k in A._reg) { if (A._reg.hasOwnProperty(k)) { a.push(k); } } return a; };

  // ── 수치·색·난수 ─────────────────────────────────────────────────────
  A.rgb = function (hex) {
    if (hex instanceof Array) { return hex; }
    var h = String(hex).replace("#", "");
    if (h.length === 3) { h = h.charAt(0) + h.charAt(0) + h.charAt(1) + h.charAt(1) + h.charAt(2) + h.charAt(2); }
    return [parseInt(h.substr(0, 2), 16) / 255, parseInt(h.substr(2, 2), 16) / 255, parseInt(h.substr(4, 2), 16) / 255];
  };
  A.clamp = function (v, a, b) { return Math.max(a, Math.min(b, v)); };
  // Math.imul 폴리필 — Remotion random() 을 그대로 재현하려면 32비트 곱셈이 필요합니다
  function imul(a, b) {
    var ah = (a >>> 16) & 0xffff, al = a & 0xffff, bh = (b >>> 16) & 0xffff, bl = b & 0xffff;
    return ((al * bl) + (((ah * bl + al * bh) << 16) >>> 0) | 0);
  }
  /** Remotion random(seed) 과 같은 값 — mulberry32(hashCode(seed)). 도감 미리보기와 같은 배치를 얻습니다 */
  A.rand = function (seed) {
    var s = String(seed), h = 0;
    for (var i = 0; i < s.length; i++) { h = ((h << 5) - h + s.charCodeAt(i)) | 0; }
    var t = (h + 0x6d2b79f5) | 0;
    t = imul(t ^ (t >>> 15), t | 1);
    t ^= t + imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  A.hasHanja = function (s) { return /[\u3400-\u9FFF]/.test(String(s)); };

  // ── 이징: Remotion Easing → cubic-bezier(x1,y1,x2,y2) ───────────────
  // 정확한 환산: quad/cubic in·out, smoothstep 은 3차 베지어로 정확히 표현됩니다.
  // inOutCubic 만 근사(easings.net 표준 0.65,0,0.35,1).
  A.EZ = {
    linear: null,
    quadIn: [1 / 3, 0, 2 / 3, 1 / 3], quadOut: [1 / 3, 2 / 3, 2 / 3, 1],
    cubicIn: [1 / 3, 0, 2 / 3, 0], cubicOut: [1 / 3, 1, 2 / 3, 1],
    quartOut: [0.25, 1, 0.5, 1], expoOut: [0.16, 1, 0.3, 1],
    smooth: [1 / 3, 0, 2 / 3, 1],            // smoothstep(3e²−2e³) — 까딱까딱 핑퐁
    easy: [0.33, 0, 0.67, 1],               // AE 이지이지(33%)
    inOutCubic: [0.65, 0, 0.35, 1], inOutSin: [0.37, 0, 0.63, 1],
    back: [0.34, 1.56, 0.64, 1], bar: [0.35, 0, 0.25, 1], snappy: [0.3, 0, 0.2, 1]
  };

  // ── 되돌리기 기록 ─────────────────────────────────────────────────────
  // 적용 중에만 살아 있는 기록. 만든 레이어(created)와 건드린 대상 레이어의 키(touched)를 모읍니다.
  A._rec = null;
  function layerOf(prop) { return prop.propertyGroup(prop.propertyDepth); }
  function propPath(prop) {
    var p = [], cur = prop;
    while (cur && cur.propertyDepth > 0) { p.unshift(cur.matchName); cur = cur.parentProperty; }
    return p;
  }
  A.resolvePath = function (layer, path) {
    var cur = layer;
    for (var i = 0; i < path.length; i++) { cur = cur.property(path[i]); if (!cur) { return null; } }
    return cur;
  };
  function isCreated(layer) {
    if (!A._rec) { return true; }
    for (var i = 0; i < A._rec.created.length; i++) { if (A._rec.created[i] === layer) { return true; } }
    return false;
  }
  function touch(prop, times) {
    if (!A._rec) { return; }
    var l = layerOf(prop);
    if (A._rec.comp && l.containingComp !== A._rec.comp) { return; }   // 프리컴프 안(프리컴프째 지워짐)
    if (isCreated(l)) { return; }
    var path = propPath(prop);
    if (path.length && path[0] === "ADBE Effect Parade") { return; }   // 우리가 붙인 효과는 통째로 지웁니다
    var key = l.index + "|" + path.join("/");
    var T = A._rec.touched, e = T[key];
    if (!e) {
      e = T[key] = { layer: l, path: path, times: [], hadKeys: prop.numKeys > 0 };
      try { if (!prop.numKeys) { e.orig = prop.value; } } catch (er) {}
    }
    for (var i = 0; i < times.length; i++) { e.times.push(times[i]); }
  }
  A.touchStatic = function (prop) { touch(prop, []); };
  /** 대상 레이어의 속성(inPoint·outPoint·parent)을 바꾸고 원래 값을 기록합니다(제거 시 되돌림) */
  A.setAttr = function (layer, name, value) {
    if (A._rec && !isCreated(layer) && layer.containingComp === A._rec.comp) {
      var key = layer.index + "|@" + name, T = A._rec.touched;
      if (!T[key]) {
        var orig = (name === "parent") ? (layer.parent ? { name: layer.parent.name, index: layer.parent.index } : null) : layer[name];
        T[key] = { layer: layer, attr: name, orig: orig, times: [], path: [] };
      }
    }
    if (name === "parent") { A.parent(layer, value || null); } else { layer[name] = value; }
  };
  A.created = function (layer) { if (A._rec && (!A._rec.comp || layer.containingComp === A._rec.comp)) { A._rec.created.push(layer); } return layer; };

  // ── 키프레임 ─────────────────────────────────────────────────────────
  function isSpatial(prop) {
    var t = prop.propertyValueType;
    return t === PropertyValueType.TwoD_SPATIAL || t === PropertyValueType.ThreeD_SPATIAL;
  }
  function dimsOf(prop) { if (isSpatial(prop)) { return 1; } var v = prop.value; return (v instanceof Array) ? v.length : 1; }
  function zeros(n) { var z = []; for (var i = 0; i < n; i++) { z.push(0); } return z; }
  function delta(prop, a, b) {
    var n = dimsOf(prop), d = [];
    if (isSpatial(prop)) {
      var s = 0; for (var i = 0; i < a.length; i++) { s += (b[i] - a[i]) * (b[i] - a[i]); }
      return [Math.sqrt(s)];
    }
    if (!(a instanceof Array)) { return n > 1 ? [b - a].concat(zeros(n - 1)) : [b - a]; }
    for (var j = 0; j < n; j++) { d.push((j < a.length && j < b.length) ? (b[j] - a[j]) : 0); }   // 스케일은 3차원(z) — 안 준 축은 0
    return d;
  }
  /* 패스(마스크·도형) 값은 템포럴 이즈 속도가 숫자가 아니라 환산할 수 없습니다.
     이징 구간은 프레임마다 모양을 보간해 선형 키로 굽습니다(선형·홀드 구간은 키 두 개). 정점 수가 같은 모양끼리만 */
  function lerpShape(a, b, k) {
    function L(x, y) { var o = []; for (var i = 0; i < x.length; i++) { o.push([x[i][0] + (y[i][0] - x[i][0]) * k, x[i][1] + (y[i][1] - x[i][1]) * k]); } return o; }
    var sh = new Shape(); sh.vertices = L(a.vertices, b.vertices); sh.inTangents = L(a.inTangents, b.inTangents); sh.outTangents = L(a.outTangents, b.outTangents); sh.closed = a.closed;
    return sh;
  }
  function shapeAnim(prop, ts, vs, ez) {
    var T = [], V = [], E = [], fd = layerOf(prop).containingComp.frameDuration;
    for (var i = 0; i < ts.length - 1; i++) {
      var name = (ez instanceof Array) ? ez[i] : ez, n = Math.max(1, Math.round((ts[i + 1] - ts[i]) / fd));
      var eased = name && name !== "linear" && name !== "hold";
      var steps = eased ? n : 1;
      for (var g = 0; g < steps; g++) { T.push(ts[i] + (ts[i + 1] - ts[i]) * g / steps); V.push(lerpShape(vs[i], vs[i + 1], eased ? A.bez(name, g / steps) : 0)); E.push(name === "hold" ? "hold" : "linear"); }
    }
    T.push(ts[ts.length - 1]); V.push(vs[vs.length - 1]);
    touch(prop, T);
    for (var j = 0; j < T.length; j++) { prop.setValueAtTime(T[j], V[j]); }
    for (j = 0; j < T.length - 1; j++) {
      var ki = prop.nearestKeyIndex(T[j]);
      prop.setInterpolationTypeAtKey(ki, prop.keyInInterpolationType(ki), E[j] === "hold" ? KeyframeInterpolationType.HOLD : KeyframeInterpolationType.LINEAR);
    }
  }
  /** 값 키: ts(초)·vs(값) 배열, ez = 구간별 이징 이름(문자열 하나면 전 구간 공통, "hold"/"linear" 가능).
      cubic-bezier → 템포럴 이즈 환산: 나가는 키 영향 x1·속도 (y1/x1)Δ/T, 들어오는 키 영향 (1−x2)·속도 ((1−y2)/(1−x2))Δ/T */
  A.anim = function (prop, ts, vs, ez) {
    if (!prop || !ts.length) { return; }
    if (prop.propertyValueType === PropertyValueType.SHAPE && ts.length > 1) { return shapeAnim(prop, ts, vs, ez); }
    touch(prop, ts);
    var n = dimsOf(prop), idx = [], i, k;
    for (i = 0; i < ts.length; i++) { prop.setValueAtTime(ts[i], vs[i]); }
    for (i = 0; i < ts.length; i++) { idx.push(prop.nearestKeyIndex(ts[i])); }
    var inE = [], outE = [], inT = [], outT = [];
    function flat(inf) { var a = []; for (var d = 0; d < n; d++) { a.push(new KeyframeEase(0, inf)); } return a; }
    for (i = 0; i < ts.length; i++) { inE.push(null); outE.push(null); inT.push(null); outT.push(null); }
    for (i = 0; i < ts.length - 1; i++) {
      var name = (ez instanceof Array) ? ez[i] : ez;
      var T = ts[i + 1] - ts[i];
      if (name === "hold") { outT[i] = KeyframeInterpolationType.HOLD; continue; }
      var bz = (name && A.EZ[name] !== undefined) ? A.EZ[name] : (name instanceof Array ? name : null);
      if (!bz) { outT[i] = KeyframeInterpolationType.LINEAR; inT[i + 1] = KeyframeInterpolationType.LINEAR; continue; }
      var dl = delta(prop, vs[i], vs[i + 1]), oe = [], ie = [];
      var x1 = Math.max(0.001, bz[0]), x2 = Math.min(0.999, bz[2]);
      for (k = 0; k < dl.length; k++) {
        var sp = (T > 0) ? dl[k] / T : 0;
        oe.push(new KeyframeEase((bz[1] / x1) * sp, A.clamp(x1 * 100, 0.1, 100)));
        ie.push(new KeyframeEase(((1 - bz[3]) / (1 - x2)) * sp, A.clamp((1 - x2) * 100, 0.1, 100)));
      }
      outE[i] = oe; inE[i + 1] = ie;
      outT[i] = KeyframeInterpolationType.BEZIER; inT[i + 1] = KeyframeInterpolationType.BEZIER;
    }
    for (i = 0; i < ts.length; i++) {
      var ki = idx[i];
      var it = inT[i] || KeyframeInterpolationType.LINEAR, ot = outT[i] || (i === ts.length - 1 ? KeyframeInterpolationType.LINEAR : KeyframeInterpolationType.LINEAR);
      try {
        if (it === KeyframeInterpolationType.BEZIER || ot === KeyframeInterpolationType.BEZIER) {
          prop.setInterpolationTypeAtKey(ki, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
          prop.setTemporalEaseAtKey(ki, inE[i] || flat(16.667), outE[i] || flat(16.667));
          try { prop.setTemporalContinuousAtKey(ki, false); prop.setTemporalAutoBezierAtKey(ki, false); } catch (e0) {}
        }
        prop.setInterpolationTypeAtKey(ki, it, ot);
        if (isSpatial(prop)) {
          try { prop.setSpatialAutoBezierAtKey(ki, false); prop.setSpatialContinuousAtKey(ki, false); prop.setSpatialTangentsAtKey(ki, [0, 0, 0].slice(0, prop.value.length), [0, 0, 0].slice(0, prop.value.length)); } catch (e1) {}
        }
      } catch (e2) {}
    }
  };
  /** 함수 곡선을 키로 굽기: 프레임마다 샘플 → 시작·끝·극값만 키로 남기고, 각 키의 기울기를 이즈 속도로 넣습니다.
      스프링·감쇠 진동처럼 Remotion 이 수식으로 그리는 모션을 "고칠 수 있는 몇 개의 키"로 옮길 때 씁니다.
      fn(g) → 값(숫자 또는 배열), g = 시작 후 프레임. comp = 프레임 길이용 */
  A.fnKeys = function (prop, comp, t0, nFrames, fn, opt) {
    opt = opt || {};
    var fd = comp.frameDuration, S = [], i;
    for (i = 0; i <= nFrames; i++) { S.push(fn(i)); }
    var sc = function (v) { return (v instanceof Array) ? v[opt.dim || 0] : v; };
    var pick = [0];
    for (i = 1; i < nFrames; i++) {
      var a = sc(S[i - 1]), b = sc(S[i]), c = sc(S[i + 1]);
      if ((b - a) * (c - b) < 0 || (opt.every && i % opt.every === 0)) { pick.push(i); }
    }
    pick.push(nFrames);
    var ts = [], vs = [];
    for (i = 0; i < pick.length; i++) { ts.push(t0 + pick[i] * fd); vs.push(S[pick[i]]); }
    touch(prop, ts);
    for (i = 0; i < ts.length; i++) { prop.setValueAtTime(ts[i], vs[i]); }
    var n = dimsOf(prop);
    for (i = 0; i < pick.length; i++) {
      var g = pick[i], ki = prop.nearestKeyIndex(ts[i]);
      var g0 = Math.max(0, g - 1), g1 = Math.min(nFrames, g + 1);
      var inE = [], outE = [];
      var prevLen = i > 0 ? (g - pick[i - 1]) : 1, nextLen = i < pick.length - 1 ? (pick[i + 1] - g) : 1;
      for (var d = 0; d < n; d++) {
        var va = (S[g1] instanceof Array) ? S[g1][d] : (d === 0 ? S[g1] : 0), vb = (S[g0] instanceof Array) ? S[g0][d] : (d === 0 ? S[g0] : 0);
        var slope = (g1 > g0 && va !== undefined && vb !== undefined) ? (va - vb) / ((g1 - g0) * fd) : 0;      // 값/초
        var isExt = (i > 0 && i < pick.length - 1);
        if (isExt && !(opt.every && g % opt.every === 0)) { slope = 0; }
        inE.push(new KeyframeEase(slope, 33.33)); outE.push(new KeyframeEase(slope, 33.33));
      }
      try {
        if (i === 0 && opt.keepFirstIn) { try { inE = prop.keyInTemporalEase(ki); } catch (e0) {} }
        var inType = (i === 0 && opt.keepFirstIn) ? prop.keyInInterpolationType(ki) : KeyframeInterpolationType.BEZIER;
        prop.setInterpolationTypeAtKey(ki, KeyframeInterpolationType.BEZIER, KeyframeInterpolationType.BEZIER);
        prop.setTemporalEaseAtKey(ki, inE, outE);
        if (inType !== KeyframeInterpolationType.BEZIER) { prop.setInterpolationTypeAtKey(ki, inType, KeyframeInterpolationType.BEZIER); }
      } catch (e) {}
      void prevLen; void nextLen;
    }
    return pick.length;
  };
  /** 홀드 키(깜빡임·교체) */
  A.holdKeys = function (prop, ts, vs) {
    touch(prop, ts);
    for (var i = 0; i < ts.length; i++) { prop.setValueAtTime(ts[i], vs[i]); }
    for (var j = 0; j < ts.length; j++) {
      var k = prop.nearestKeyIndex(ts[j]);
      prop.setInterpolationTypeAtKey(k, KeyframeInterpolationType.HOLD, KeyframeInterpolationType.HOLD);
    }
  };

  // ── 트랜스폼 단축 ────────────────────────────────────────────────────
  A.tr = function (l) { return l.property("ADBE Transform Group"); };
  A.P = function (l) { return A.tr(l).property("ADBE Position"); };
  A.S = function (l) { return A.tr(l).property("ADBE Scale"); };
  A.R = function (l) { return A.tr(l).property("ADBE Rotate Z"); };
  A.O = function (l) { return A.tr(l).property("ADBE Opacity"); };
  A.AP = function (l) { return A.tr(l).property("ADBE Anchor Point"); };
  /** 정적 값 설정(대상 레이어면 원래 값을 기록해 두었다가 제거 때 되돌립니다) */
  A.set = function (prop, v) { touch(prop, []); prop.setValue(v); };
  /** 화면 위치를 유지한 채 앵커를 옮깁니다(레이어 좌표 기준). 대상 레이어 키가 없을 때만 */
  A.moveAnchor = function (l, ax, ay) {
    var ap = A.AP(l), p = A.P(l), s = A.S(l).value, r = A.R(l).value * Math.PI / 180;
    if (ap.numKeys || p.numKeys) { return false; }
    var a0 = ap.value, dx = (ax - a0[0]) * s[0] / 100, dy = (ay - a0[1]) * s[1] / 100;
    var pv = p.value;
    A.set(ap, [ax, ay].concat(a0.length > 2 ? [a0[2]] : []));
    A.set(p, [pv[0] + dx * Math.cos(r) - dy * Math.sin(r), pv[1] + dx * Math.sin(r) + dy * Math.cos(r)].concat(pv.length > 2 ? [pv[2]] : []));
    return true;
  };

  // ── 효과 ─────────────────────────────────────────────────────────────
  /** 효과 추가 — 이름은 "AKD·<설명>" (제거 시 이 접두로 찾습니다) */
  A.fx = function (l, match, label) {
    var e = l.property("ADBE Effect Parade").addProperty(match);
    try { e.name = "AKD·" + (label || e.name); } catch (er) {}
    return e;
  };
  /** CSS blur(px) → AE 가우시안 블러 Blurriness (σ 기준 약 2배, 헤드리스 비교로 맞춘 값) */
  A.BLUR_K = 2.0;
  A.gblur = function (l, label) { var e = A.fx(l, "ADBE Gaussian Blur 2", label || "블러"); try { e.property("ADBE Gaussian Blur 2-0003").setValue(1); } catch (er) {} return e; };
  /** CSS drop-shadow(0 dy blur rgba(0,0,0,op)) */
  A.shadow = function (l, dy, blur, op) {
    try {
      var d = A.fx(l, "ADBE Drop Shadow", "그림자");
      d.property("ADBE Drop Shadow-0002").setValue(op * 255);
      d.property("ADBE Drop Shadow-0003").setValue(180);
      d.property("ADBE Drop Shadow-0004").setValue(dy);
      d.property("ADBE Drop Shadow-0005").setValue(blur * 1.2);
      return d;
    } catch (e) { return null; }
  };

  // ── 프로젝트 아이템 ───────────────────────────────────────────────────
  A.folder = function (name) {
    var P = app.project;
    for (var i = 1; i <= P.numItems; i++) { var it = P.item(i); if (it instanceof FolderItem && it.name === name) { return it; } }
    return P.items.addFolder(name);
  };
  /** 파일 임포트(같은 파일이 이미 있으면 재사용 — 적용할 때마다 푸티지가 쌓이지 않게) */
  A.imp = function (path, folderName) {
    var f = new File(path);
    if (!f.exists) { throw new Error("에셋 없음: " + path); }
    var P = app.project;
    for (var i = 1; i <= P.numItems; i++) {
      var it = P.item(i);
      try { if (it instanceof FootageItem && it.file && it.file.fsName === f.fsName) { return it; } } catch (e) {}
    }
    var item = P.importFile(new ImportOptions(f));
    try { item.parentFolder = A.folder(folderName || "기법 도감 에셋"); } catch (e2) {}
    return item;
  };
  A.span = function (l, t0, t1) { if (t1 !== undefined && t1 !== null) { l.outPoint = t1; } l.inPoint = t0; return l; };

  // ── 레이어 생성(모두 created 로 기록) ─────────────────────────────────
  A.name = function (X, label) { return X.sceneNo + " " + label; };
  A.addItem = function (comp, item, name) { var l = comp.layers.add(item); l.name = name; return A.created(l); };
  A.nul = function (comp, name) { var l = comp.layers.addNull(); l.name = name; A.AP(l).setValue([50, 50]); return A.created(l); };
  A.solid = function (comp, hex, name, w, h) { var l = comp.layers.addSolid(A.rgb(hex), name, w || comp.width, h || comp.height, 1); return A.created(l); };
  A.adjust = function (comp, name) { var l = comp.layers.addSolid([1, 1, 1], name, comp.width, comp.height, 1); l.adjustmentLayer = true; return A.created(l); };
  A.shapeLayer = function (comp, name) { var s = comp.layers.addShape(); s.name = name; A.created(s); return s; };
  A.group = function (parentContents, name) { var g = parentContents.addProperty("ADBE Vector Group"); if (name) { g.name = name; } return g.property("ADBE Vectors Group"); };
  A.paint = function (c, fill, stroke, strokeW) {
    if (stroke) { var st = c.addProperty("ADBE Vector Graphic - Stroke"); st.property("ADBE Vector Stroke Color").setValue(A.rgb(stroke)); st.property("ADBE Vector Stroke Width").setValue(strokeW); }
    if (fill) { var fl = c.addProperty("ADBE Vector Graphic - Fill"); fl.property("ADBE Vector Fill Color").setValue(A.rgb(fill)); }
  };
  /** 도형 레이어 하나에 도형 하나: kind rect|ellipse|path, 레이어 원점 = 도형 중심 */
  A.rect = function (comp, name, w, h, r, fill, stroke, strokeW) {
    var s = A.shapeLayer(comp, name), c = A.group(s.property("ADBE Root Vectors Group"), "사각형");
    var rr = c.addProperty("ADBE Vector Shape - Rect"); rr.property("ADBE Vector Rect Size").setValue([w, h]); rr.property("ADBE Vector Rect Roundness").setValue(r || 0);
    A.paint(c, fill, stroke, strokeW); return s;
  };
  A.ellipse = function (comp, name, w, h, fill, stroke, strokeW) {
    var s = A.shapeLayer(comp, name), c = A.group(s.property("ADBE Root Vectors Group"), "타원");
    c.addProperty("ADBE Vector Shape - Ellipse").property("ADBE Vector Ellipse Size").setValue([w, h]);
    A.paint(c, fill, stroke, strokeW); return s;
  };
  A.shapeOf = function (verts, closed, inT, outT) { var sh = new Shape(); sh.vertices = verts; sh.closed = !!closed; if (inT) { sh.inTangents = inT; } if (outT) { sh.outTangents = outT; } return sh; };
  /** 패스 도형 추가(기존 레이어 contents 에). 반환 = 그룹 contents */
  A.addPath = function (contents, name, verts, closed, fill, stroke, strokeW, inT, outT) {
    var c = A.group(contents, name), pp = c.addProperty("ADBE Vector Shape - Group");
    pp.property("ADBE Vector Shape").setValue(A.shapeOf(verts, closed, inT, outT));
    A.paint(c, fill, stroke, strokeW); return c;
  };
  A.path = function (comp, name, verts, closed, fill, stroke, strokeW) {
    var s = A.shapeLayer(comp, name); A.addPath(s.property("ADBE Root Vectors Group"), name, verts, closed, fill, stroke, strokeW); return s;
  };

  // ── 텍스트 ───────────────────────────────────────────────────────────
  /** 세모지 폰트(PostScript 이름). 연성·주아·잘난·나눔스퀘어네오엔 한자 글리프가 없습니다 */
  A.FONT = {
    yeonsung: "BMYEONSUNG", jua: "BMJUAOTF", jalnan: "Jalnan", dohyeon: "BMDOHYEON",
    neoHv: "NanumSquareNeo-eHv", neoEb: "NanumSquareNeo-dEb",
    myeongjo: "NanumMyeongjoExtraBold", songti: "STSongti-SC-Bold"
  };
  var NO_HANJA = { "BMYEONSUNG": 1, "BMJUAOTF": 1, "Jalnan": 1, "BMDOHYEON": 1, "NanumSquareNeo-eHv": 1, "NanumSquareNeo-dEb": 1 };
  /** 텍스트 레이어. o = {font, size, fill, stroke, strokeW, just:"center"|"left"|"right", tracking, leading, fauxBold}
      한자가 섞이면 한자 구간만 송티로 바꿉니다(AE 24.3+ characterRange). 지원 안 되면 명조로 통째로 바꿉니다 */
  A.text = function (comp, str, name, o) {
    o = o || {};
    var t = comp.layers.addText(str); t.name = name; A.created(t);
    var sp = t.property("ADBE Text Properties").property("ADBE Text Document"), td = sp.value;
    var font = o.font || A.FONT.neoHv;
    td.resetCharStyle(); td.resetParagraphStyle();
    td.font = font; td.fontSize = o.size || 60; td.applyFill = true; td.fillColor = A.rgb(o.fill || "#1b1b1b");
    if (o.stroke && o.strokeW) { td.applyStroke = true; td.strokeColor = A.rgb(o.stroke); td.strokeWidth = o.strokeW; td.strokeOverFill = !!o.strokeOver; } else { td.applyStroke = false; }
    td.justification = o.just === "left" ? ParagraphJustification.LEFT_JUSTIFY : (o.just === "right" ? ParagraphJustification.RIGHT_JUSTIFY : ParagraphJustification.CENTER_JUSTIFY);
    if (o.tracking !== undefined) { td.tracking = o.tracking; }
    if (o.leading) { try { td.autoLeading = false; td.leading = o.leading; } catch (e) {} }
    sp.setValue(td);
    if (NO_HANJA[font] && A.hasHanja(str)) {
      var done = false;
      try {
        td = sp.value;
        var re = /[\u3400-\u9FFF]+/g, m;
        while ((m = re.exec(str)) !== null) { td.characterRange(m.index, m.index + m[0].length).font = o.hanjaFont || A.FONT.songti; }
        sp.setValue(td); done = true;
      } catch (e2) {}
      if (!done) { td = sp.value; td.font = A.FONT.myeongjo; sp.setValue(td); }
    }
    return t;
  };
  /** 텍스트 앵커를 글자 상자 중심(또는 fx,fy 비율)으로 — 위치 = 상자 중심 */
  A.centerText = function (t, fx, fy, time) {
    var r = t.sourceRectAtTime(time || 0, false);
    fx = (fx === undefined) ? 0.5 : fx; fy = (fy === undefined) ? 0.5 : fy;
    A.AP(t).setValue([r.left + r.width * fx, r.top + r.height * fy]);
    return r;
  };

  // ── 부모 연결 ────────────────────────────────────────────────────────
  /* 부모 바꾸기(화면 위치 유지). AE 스크립트에서
       layer.parent = p           → 자식 값을 보정해 화면 위치 유지(우리가 원하는 것)
       layer.setParentWithJump(p) → 값을 그대로 두어 화면에서 "점프" (실측으로 확인 — 이름과 반대로 헷갈리기 쉬움)
     그래서 항상 .parent 대입을 씁니다. t 는 호환용(무시). */
  A.parent = function (child, parent, t) { void t; if (child.parent !== (parent || null)) { child.parent = parent || null; } };

  // ── 마커 ─────────────────────────────────────────────────────────────
  A.MARK = "ak-dogam:";
  function markerAt(layer, t, comment, params) {
    var mp = layer.property("ADBE Marker"), fd = layer.containingComp.frameDuration, tt = t;
    for (var guard = 0; guard < 30; guard++) {
      var clash = false;
      for (var i = 1; i <= mp.numKeys; i++) { if (Math.abs(mp.keyTime(i) - tt) < fd / 2) { clash = true; break; } }
      if (!clash) { break; }
      tt += fd;
    }
    var mv = new MarkerValue(comment);
    try { mv.setParameters(params); } catch (e) {}
    mp.setValueAtTime(tt, mv);
  }
  /** 레이어의 ak-dogam 마커들 → [{id, group, role, params, content, t, rec, time}] */
  A.marks = function (layer) {
    var out = [], mp = layer.property("ADBE Marker");
    for (var i = 1; i <= mp.numKeys; i++) {
      var mv = mp.keyValue(i);
      if (String(mv.comment).indexOf(A.MARK) !== 0) { continue; }
      var p = {};
      try { p = mv.getParameters(); } catch (e) {}
      var o = { id: String(mv.comment).substr(A.MARK.length), time: mp.keyTime(i), key: i, layer: layer };
      try { o.group = p.akd_group; o.role = p.akd_role; o.t = parseFloat(p.akd_t); } catch (e1) {}
      try { o.params = A.parse(p.akd_params || "{}"); } catch (e2) { o.params = {}; }
      try { o.content = A.parse(p.akd_content || "{}"); } catch (e3) { o.content = {}; }
      try { o.rec = A.parse(p.akd_rec || "[]"); } catch (e4) { o.rec = []; }
      out.push(o);
    }
    return out;
  };
  function groupLayers(comp, group) {
    var res = [];
    for (var i = 1; i <= comp.numLayers; i++) {
      var ms = A.marks(comp.layer(i));
      for (var j = 0; j < ms.length; j++) { if (ms[j].group === group) { res.push(ms[j]); } }
    }
    return res;
  }

  // ── 씬 번호 ──────────────────────────────────────────────────────────
  A.sceneNo = function (comp, layers) {
    var m;
    for (var i = 0; layers && i < layers.length; i++) { m = /^(\d{1,3})\s/.exec(layers[i].name); if (m) { return m[1]; } }
    m = /(\d{1,3})/.exec(comp.name);
    if (m) { return (m[1].length < 2 ? "0" : "") + m[1]; }
    return "00";
  };

  // ── 에셋 경로 ────────────────────────────────────────────────────────
  A.asset = function (X, rel) { return X.assetsRoot + "/" + rel; };
  A.kitPart = function (X, cast, part) { return X.assetsRoot + "/kit/" + cast + "/" + part + ".png"; };
  A.prop = function (X, id) { return X.assetsRoot + "/kit/props/" + id + ".png"; };
  A.readJSON = function (path) {
    var f = new File(path); if (!f.exists) { return null; }
    f.encoding = "UTF-8"; f.open("r"); var s = f.read(); f.close();
    return A.parse(s);
  };

  // ── 세모지 캐스트 리그(kit PNG 부위 → 프리컴프) ───────────────────────
  /* SemojiRig 과 같은 규칙: 같은 1024×1536 캔버스 부위 PNG 를 겹칩니다.
     o = {x, y, h, bust, pose:{armR, armL, face}, seed, bobEvery(10), bobAmp(1), blinkEvery(90), t0, dur, flip}
     (x,y) = 발 사이 바닥점(전신) 또는 몸통 아래(흉상). 까딱까딱 = 널 "까딱까딱" ScaleY 핑퐁 키, 눈 깜빡임 = 홀드 키. */
  A.castRig = function (X, comp, cast, o) {
    var rig = A.readJSON(X.assetsRoot + "/kit/" + cast + "/rig.json");
    if (!rig) { throw new Error("캐스트 rig.json 없음: " + cast); }
    var s = o.h / (rig.feet[1] - rig.top);
    var clip = o.bust ? rig.torsoBottom + 10 : rig.h, ay = o.bust ? clip : rig.feet[1];
    var dur = o.dur || comp.duration;
    var pc = app.project.items.addComp(X.sceneNo + " 캐릭터 " + cast, rig.w, Math.round(clip), 1, dur, 1 / comp.frameDuration);
    try { pc.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var pose = o.pose || {};
    var FRONT = { arm_guard_fist: 1, arm_hold: 1, arm_hand_chest: 1, arm_hand_chin: 1 };
    function part(nm, label) {
      var l = pc.layers.add(A.imp(A.kitPart(X, cast, nm), "기법 도감 에셋/kit"));
      l.name = label || nm; l.moveToEnd();
      A.P(l).setValue([rig.w / 2, rig.h / 2]);
      return l;
    }
    function armName(n, side) { return (!n || n === "arm") ? "arm_" + side : n + "_" + side; }
    // 아래(뒤)부터 쌓습니다 — moveToEnd 로 맨 아래로 보내므로 앞쪽 부위를 먼저 만듭니다
    var order = [];
    if (pose.armFold) { order.push(["arms_folded", "팔짱"]); }
    if (!pose.face) { order.push(["mouth_open", "입 벌림"]); order.push(["eyes_closed", "눈 감음"]); } else { order.push([pose.face, "표정"]); }
    if (!pose.armFold && FRONT[pose.armL]) { order.push([armName(pose.armL, "l"), "왼팔(화면 오른쪽)"]); }
    if (!pose.armFold && FRONT[pose.armR]) { order.push([armName(pose.armR, "r"), "오른팔(화면 왼쪽)"]); }
    order.push(["torso", "몸통"]);
    if (!pose.armFold && !FRONT[pose.armL]) { order.push([armName(pose.armL, "l"), "왼팔(화면 오른쪽)"]); }
    if (!pose.armFold && !FRONT[pose.armR]) { order.push([armName(pose.armR, "r"), "오른팔(화면 왼쪽)"]); }
    if (!o.bust) { order.push([pose.legs || "legs_stand", "다리"]); }
    var L = {};
    for (var i = 0; i < order.length; i++) { L[order[i][1]] = part(order[i][0], order[i][1]); }
    // 팔 회전축 = 어깨
    function pivot(l, pv) { if (!l) { return; } A.AP(l).setValue([pv[0], pv[1]]); A.P(l).setValue([pv[0], pv[1]]); }
    pivot(L["오른팔(화면 왼쪽)"], rig.shoulderR); pivot(L["왼팔(화면 오른쪽)"], rig.shoulderL);
    if (pose.rotR && L["오른팔(화면 왼쪽)"]) { A.R(L["오른팔(화면 왼쪽)"]).setValue(pose.rotR); }
    if (pose.rotL && L["왼팔(화면 오른쪽)"]) { A.R(L["왼팔(화면 오른쪽)"]).setValue(pose.rotL); }
    var seed = o.seed || cast, fd = comp.frameDuration;
    // 눈 깜빡임: (t + floor(rand(seed+"b")·every)) % every < 4 → 4f 감음 (SemojiRig 과 같은 식)
    var eye = L["눈 감음"];
    if (eye) {
      var every = (o.blinkEvery === undefined) ? 90 : o.blinkEvery, ts = [0], vs = [0];
      if (every > 0) {
        var off = Math.floor(A.rand(seed + "b") * every), nF = Math.round(dur / fd);
        for (var g = 0; g < nF; g++) {
          var on = ((g + off) % every) < 4, prevOn = g > 0 && (((g - 1 + off) % every) < 4);
          if (on !== prevOn || g === 0) { ts.push(g * fd); vs.push(on ? 100 : 0); }
        }
      }
      A.holdKeys(A.O(eye), ts, vs);
    }
    if (L["입 벌림"]) { A.O(L["입 벌림"]).setValue(0); }
    // 본 컴프에 배치: 캔버스 점 (feet[0], ay) 가 화면 (x,y) 에
    var layer = A.addItem(comp, pc, X.sceneNo + " " + (o.label || cast));
    A.AP(layer).setValue([rig.feet[0], ay]);
    A.P(layer).setValue([o.x, o.y]);
    A.S(layer).setValue([(o.flip ? -s : s) * 100, s * 100]);
    layer.startTime = o.t0 || 0;
    var bob = null;
    if (o.bobEvery !== 0) {
      bob = A.bobNull(X, comp, layer, { every: o.bobEvery || 10, amp: (o.bobAmp === undefined ? 1 : o.bobAmp), phase: Math.floor(A.rand(seed) * 10), ez: "smooth", t0: o.t0 || 0, t1: (o.t0 || 0) + dur, pivot: [o.x, o.y], label: (o.label || cast) + " 까딱까딱" });
    }
    return { layer: layer, comp: pc, parts: L, rig: rig, scale: s, bob: bob };
  };

  /** 까딱까딱 널: pivot(화면 좌표, 보통 발밑)에 널을 두고 ScaleY 100↔100+amp 를 every 프레임마다 핑퐁 키.
      phase = 시작 위상(프레임). 대상 레이어는 널에 부모 연결(화면 위치 유지) */
  A.bobNull = function (X, comp, target, o) {
    var fd = comp.frameDuration, n = A.nul(comp, X.sceneNo + " " + (o.label || "까딱까딱"));
    n.label = 11;
    A.P(n).setValue([o.pivot[0], o.pivot[1]]);
    var t0 = o.t0 || 0, t1 = o.t1 || comp.duration, every = Math.max(1, o.every), amp = o.amp;
    // 부모 연결은 키를 넣기 전(정지 자세 100%)에 — 원래 부모가 있으면 널을 그 부모에 달아 계층 유지
    if (target.parent) { A.parent(n, target.parent, t0); }
    A.setAttr(target, "parent", n);
    // k = (g + phase), 반주기 every: seg 짝수 = 늘어나는 중(100→100+amp), 홀수 = 줄어드는 중
    var ts = [], vs = [], ph = o.phase || 0;
    var first = t0 - ((ph % every) * fd), seg = Math.floor(ph / every);
    for (var tt = first, s = seg; tt <= t1 + every * fd + 1e-6; tt += every * fd, s++) {
      ts.push(tt); vs.push([100, (s % 2 === 0) ? 100 : 100 + amp]);
    }
    A.anim(A.S(n), ts, vs, o.ez || "smooth");
    n.inPoint = t0; n.outPoint = t1;
    return n;
  };

  // ── 알파 경계(발밑 피벗용) ────────────────────────────────────────────
  /* 전체 캔버스 크기의 누끼 PNG(오토카이로스 레이어 씬)는 sourceRect 가 캔버스 전체라 발밑을 알 수 없습니다.
     표현식 sampleImage 로 알파가 있는 범위를 이분 탐색합니다 — 스크립트에서는 픽셀을 읽을 수 없어 불가피한 표현식이며,
     값을 한 번 읽은 뒤 임시 널을 지웁니다(결과물에는 표현식이 남지 않습니다). 반환 = 레이어 좌표 [x0,y0,x1,y1] */
  A.alphaBBox = function (comp, layer, t) {
    var w = layer.source ? layer.source.width : layer.width, h = layer.source ? layer.source.height : layer.height;
    var tmp = comp.layers.addNull(); tmp.name = "__akd_probe";
    var cc = tmp.property("ADBE Effect Parade").addProperty("ADBE Color Control");
    var nm = layer.name.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    var ex = [
      'var L=thisComp.layer(' + layer.index + '),W=' + w + ',H=' + h + ',T=' + (t || 0) + ';',
      'function rowHas(y0,y1){var a=L.sampleImage([W/2,(y0+y1)/2],[W/2,Math.max(0.5,(y1-y0)/2)],true,T);return a[3]>0.0005;}',
      'function colHas(x0,x1){var a=L.sampleImage([(x0+x1)/2,H/2],[Math.max(0.5,(x1-x0)/2),H/2],true,T);return a[3]>0.0005;}',
      'function lo(f,N){var a=0,b=N;while(b-a>2){var m=(a+b)/2;if(f(0,m))b=m;else a=m;}return a;}',
      'function hi(f,N){var a=0,b=N;while(b-a>2){var m=(a+b)/2;if(f(m,N))a=m;else b=m;}return b;}',
      '[lo(colHas,W)/W, lo(rowHas,H)/H, hi(colHas,W)/W, hi(rowHas,H)/H]'
    ].join("\n");
    var res = null;
    try {
      var pr = cc.property(1); pr.expression = ex;
      var v = pr.valueAtTime(t || 0, false);
      res = [v[0] * w, v[1] * h, v[2] * w, v[3] * h];
    } catch (e) { res = null; }
    tmp.remove();
    void nm;
    if (!res || !(res[2] > res[0]) || !(res[3] > res[1])) { return [0, 0, w, h]; }
    return res;
  };
  /** 레이어 좌표 → 컴프 좌표(부모 없음, 회전 무시 근사) */
  A.toComp = function (layer, pt) {
    var ap = A.AP(layer).value, p = A.P(layer).value, s = A.S(layer).value;
    return [p[0] + (pt[0] - ap[0]) * s[0] / 100, p[1] + (pt[1] - ap[1]) * s[1] / 100];
  };


  // ── 마스크 ───────────────────────────────────────────────────────────
  /** 사각형 마스크 모양(레이어 좌표) */
  A.rectShape = function (x0, y0, x1, y1) { return A.shapeOf([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], true); };
  /** 타원 마스크 모양(중심 cx,cy 반지름 rx,ry) — 베지어 4점(κ=0.5523) */
  A.ellipseShape = function (cx, cy, rx, ry) {
    var k = 0.5523;
    return A.shapeOf([[cx, cy - ry], [cx + rx, cy], [cx, cy + ry], [cx - rx, cy]], true,
      [[-rx * k, 0], [0, -ry * k], [rx * k, 0], [0, ry * k]], [[rx * k, 0], [0, ry * k], [-rx * k, 0], [0, -ry * k]]);
  };
  /** 마스크 추가(이름 "AKD·…"). 반환 = 마스크 모양 속성(키를 넣을 수 있음) */
  A.mask = function (layer, label, shape) {
    var m = layer.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
    m.name = "AKD·" + label;
    var sp = m.property("ADBE Mask Shape"); sp.setValue(shape);
    return sp;
  };

  // ── 곡선 함수 ────────────────────────────────────────────────────────
  /** Remotion spring({frame, fps, config:{damping, stiffness, mass}}) — 0→1, 초기 속도 0 (감쇠 진동 해석해) */
  A.spring = function (g, fps, damping, stiffness, mass) {
    if (g <= 0) { return 0; }
    var t = g / fps, m = mass || 1, c = damping, k = stiffness;
    var w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m));
    if (z < 1) {
      var wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t));
    }
    return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
  };
  /** 3차 베지어 이징 값(Remotion Easing.bezier 와 같은 정의) */
  A.bez = function (name, x) {
    var b = (name instanceof Array) ? name : A.EZ[name];
    if (!b) { return x; }
    var lo = 0, hi = 1, tt = x;
    for (var i = 0; i < 40; i++) {
      tt = (lo + hi) / 2;
      var xx = 3 * (1 - tt) * (1 - tt) * tt * b[0] + 3 * (1 - tt) * tt * tt * b[2] + tt * tt * tt;
      if (xx < x) { lo = tt; } else { hi = tt; }
    }
    return 3 * (1 - tt) * (1 - tt) * tt * b[1] + 3 * (1 - tt) * tt * tt * b[3] + tt * tt * tt;
  };
  /** Remotion lerp(f, a, b, v0, v1, e) 과 같은 값 */
  A.lerp = function (f, a, b, v0, v1, ez) {
    var k = (b === a) ? (f >= b ? 1 : 0) : A.clamp((f - a) / (b - a), 0, 1);
    return v0 + (v1 - v0) * A.bez(ez === undefined ? "cubicOut" : ez, k);
  };
  A.num = function (v) { var s = String(Math.round(v * 100) / 100), p = s.split("."); p[0] = p[0].replace(/\B(?=(\d{3})+(?!\d))/g, ","); return p.join("."); };

  // ── 세모지 공용 모션 ──────────────────────────────────────────────────
  /** 텍스트 팝(fx.tsx textPop): 크기 from→1 (len f, 3구간 선형) + 불투명 op0→1 (opLen f) */
  A.textPop = function (X, l, g0, o) {
    o = o || {};
    var L = o.len || 7, d = (o.from === undefined ? 1.25 : o.from) - 1, sc = o.base || 100, f = function (n) { return X.f(g0 + n); };
    A.anim(A.S(l), [f(0), f(2 * L / 7), f(5 * L / 7), f(L)], [[sc * (1 + d), sc * (1 + d)], [sc * (1 + d * 0.6), sc * (1 + d * 0.6)], [sc * (1 + d * 0.32), sc * (1 + d * 0.32)], [sc, sc]], "linear");
    A.anim(A.O(l), [f(0), f(o.opLen || 2)], [100 * (o.op0 === undefined ? 0.4 : o.op0), 100], "linear");
  };
  /** 레이어 사본(에코·고스트용): 부모 = 원본, 로컬 변환 = 원본과 겹치게. 키·마커는 지웁니다 */
  A.echoOf = function (L, name) {
    var d = L.duplicate(); d.name = name; A.created(d);
    var mp = d.property("ADBE Marker"); while (mp.numKeys) { mp.removeKey(1); }
    var props = [A.AP(d), A.P(d), A.S(d), A.R(d), A.O(d)];
    for (var i = 0; i < props.length; i++) { while (props[i].numKeys) { props[i].removeKey(1); } }
    var fxp = d.property("ADBE Effect Parade"); for (var j = fxp.numProperties; j >= 1; j--) { fxp.property(j).remove(); }
    d.parent = L;
    var ap = A.AP(L).value;
    A.AP(d).setValue(ap); A.P(d).setValue(ap.length > 2 ? ap : [ap[0], ap[1]]); A.S(d).setValue([100, 100]); A.R(d).setValue(0); A.O(d).setValue(100);
    d.moveAfter(L);
    return d;
  };

  /** 세모지 흰 타원 말풍선 프리컴프(SpeechBubble 몸체). 반환 {comp, W, H, ox, oy(컴프 안 좌표)}.
      o = {w, h, text, tail:"left"|"right", size}. 컴프 = 풍선 상자를 가운데 두고 사방 여유 20% */
  A.bubbleComp = function (X, o) {
    var w = o.w, h = o.h, padX = Math.round(w * 0.2), padY = Math.round(h * 0.3);
    var W = w + padX * 2, H = h + padY * 2;
    var c = app.project.items.addComp(X.sceneNo + " 말풍선 " + String(o.text).replace(/\n/g, " ").substr(0, 16), W, H, 1, o.dur || X.comp.duration, X.fps);
    try { c.parentFolder = A.folder("기법 도감 프리컴프"); } catch (e) {}
    var rec = A._rec; A._rec = null;      // 프리컴프 안 레이어는 기록하지 않습니다(프리컴프째 지워짐)
    try {
      var bx = padX, by = padY;
      var s = c.layers.addShape(); s.name = "풍선";
      var root = s.property("ADBE Root Vectors Group");
      var tail = o.tail === "right"
        ? [[bx + w * 0.8, by + h * 0.8], [bx + w * 1.08, by + h * 1.02], [bx + w * 0.66, by + h * 0.9]]
        : [[bx + w * 0.2, by + h * 0.8], [bx - w * 0.08, by + h * 1.02], [bx + w * 0.34, by + h * 0.9]];
      var g1 = A.group(root, "타원");
      var el = g1.addProperty("ADBE Vector Shape - Ellipse"); el.property("ADBE Vector Ellipse Size").setValue([w, h]); el.property("ADBE Vector Ellipse Position").setValue([bx + w / 2, by + h / 2]);
      A.paint(g1, "#ffffff");
      A.addPath(root, "꼬리", tail, true, "#ffffff");
      A.P(s).setValue([0, 0]); A.AP(s).setValue([0, 0]);
      var t = A.text(c, String(o.text).replace(/\n/g, "\r"), "글자", { font: A.FONT.yeonsung, size: o.size || 44, fill: "#1a1a1a", leading: (o.size || 44) * 1.1 });
      A.centerText(t);
      A.P(t).setValue([bx + w / 2, by + h / 2]);
    } finally { A._rec = rec; }
    var ox = (o.tail === "right") ? padX + w + 0.08 * w : padX - 0.08 * w, oy = padY + h * 0.52;
    return { comp: c, W: W, H: H, padX: padX, padY: padY, ox: ox, oy: oy };
  };

  // ── 적용 · 다시 적용 · 제거 ───────────────────────────────────────────
  function merge(a, b) { var o = {}, k; for (k in a) { if (a.hasOwnProperty(k)) { o[k] = a[k]; } } if (b) { for (k in b) { if (b.hasOwnProperty(k) && b[k] !== undefined && b[k] !== null && b[k] !== "") { o[k] = b[k]; } } } return o; }
  function coerce(defs, P) {
    for (var k in defs) {
      if (!defs.hasOwnProperty(k)) { continue; }
      var d = defs[k];
      if (typeof d === "number" && typeof P[k] !== "number") { var n = parseFloat(P[k]); P[k] = isNaN(n) ? d : n; }
      if (typeof d === "boolean" && typeof P[k] !== "boolean") { P[k] = (P[k] === "true" || P[k] === 1 || P[k] === "1"); }
    }
    return P;
  }
  function res(o) { return A.stringify(o); }

  A.apply = function (id, ctx) {
    ctx = ctx || {};
    var undo = false;
    try {
      var def = A._reg[id];
      if (!def) { return res({ ok: false, error: "AE 구현이 없는 기법입니다: " + id }); }
      var comp = ctx.comp || app.project.activeItem;
      if (!(comp instanceof CompItem)) { return res({ ok: false, error: "컴포지션을 열고(타임라인 활성) 다시 눌러 주세요." }); }
      var layers = [], i;
      var src = ctx.layers || comp.selectedLayers;
      for (i = 0; i < src.length; i++) { layers.push(src[i]); }
      if (def.kind === "layer" && !layers.length && !def.create) { return res({ ok: false, error: "이 기법은 레이어에 겁니다 — 타임라인에서 레이어를 선택하세요." }); }
      var fd = comp.frameDuration;
      var t = (ctx.t === undefined || ctx.t === null) ? comp.time : ctx.t;
      t = Math.round(t / fd) * fd;
      var P = coerce(def.params || {}, merge(def.params || {}, ctx.params));
      var C = merge(def.content || {}, ctx.content);
      var group = "g" + (new Date()).getTime().toString(36) + Math.floor(Math.random() * 1e4).toString(36);
      app.beginUndoGroup("기법 도감: " + (def.name || id)); undo = true;
      A._rec = { created: [], touched: {}, comp: comp };
      var X = {
        id: id, def: def, comp: comp, layers: layers, t: t, fd: fd, fps: Math.round(1 / fd), P: P, C: C,
        f: function (n) { return t + n * fd; },          // 시작 후 n 프레임의 시각
        sceneNo: ctx.sceneNo || A.sceneNo(comp, layers), assetsRoot: String(ctx.assetsRoot || A.assetsRoot || "").replace(/\/$/, ""),
        group: group
      };
      var out = def.apply(X) || {};
      // 마커: 만든 레이어 = created, 건드린 대상 레이어 = target(되돌리기 기록 포함)
      var base = { akd_group: group, akd_t: String(t), akd_params: A.stringify(P), akd_content: A.stringify(C) };
      var byLayer = {}, tk;
      for (tk in A._rec.touched) {
        if (!A._rec.touched.hasOwnProperty(tk)) { continue; }
        var e = A._rec.touched[tk], li = e.layer.index;
        if (!byLayer[li]) { byLayer[li] = { layer: e.layer, rec: [] }; }
        byLayer[li].rec.push(e.attr ? { attr: e.attr, orig: e.orig } : { path: e.path, times: e.times, hadKeys: e.hadKeys, orig: e.orig });
      }
      for (i = 0; i < layers.length; i++) { if (!byLayer[layers[i].index]) { byLayer[layers[i].index] = { layer: layers[i], rec: [] }; } }
      var nT = 0;
      for (tk in byLayer) {
        if (!byLayer.hasOwnProperty(tk)) { continue; }
        if (isCreated(byLayer[tk].layer)) { continue; }
        markerAt(byLayer[tk].layer, t, A.MARK + id, merge(base, { akd_role: "target", akd_rec: A.stringify(byLayer[tk].rec) }));
        nT++;
      }
      var created = A._rec.created, names = [];
      for (i = 0; i < created.length; i++) {
        try { markerAt(created[i], Math.max(t, created[i].inPoint), A.MARK + id, merge(base, { akd_role: "created" })); names.push(created[i].name); } catch (em) {}
      }
      A._rec = null;
      app.endUndoGroup(); undo = false;
      return res({ ok: true, id: id, group: group, t: t, created: names.length, targets: nT, names: names, msg: out.msg || ((def.name || id) + " 적용 — 새 레이어 " + names.length + "개, 대상 " + nT + "개") });
    } catch (err) {
      A._rec = null;
      if (undo) { try { app.endUndoGroup(); } catch (e9) {} }
      return res({ ok: false, error: String(err) + (err.line ? " (줄 " + err.line + ")" : "") });
    }
  };

  /** 묶음 제거: 만든 레이어 삭제 + 대상 레이어에 넣은 키·효과·마스크 되돌림. 반환 {removed, restored, info} */
  A._removeGroup = function (comp, group) {
    var ms = groupLayers(comp, group), info = null, removed = 0, restored = 0, targets = [], later = [], i, j;
    for (i = 0; i < ms.length; i++) {
      var m = ms[i];
      if (!info) { info = { id: m.id, t: m.t, params: m.params, content: m.content }; }
      if (m.role === "created") { continue; }
      targets.push(m.layer);
      var L = m.layer;
      for (j = 0; j < m.rec.length; j++) {
        var r = m.rec[j];
        if (r.attr) { later.push({ layer: L, r: r }); continue; }
        var pr = A.resolvePath(L, r.path);
        if (!pr) { continue; }
        for (var k = r.times.length - 1; k >= 0; k--) {
          if (!pr.numKeys) { break; }
          var ki = pr.nearestKeyIndex(r.times[k]);
          if (Math.abs(pr.keyTime(ki) - r.times[k]) < comp.frameDuration / 2) { pr.removeKey(ki); }
        }
        if (!pr.numKeys && r.orig !== undefined && r.orig !== null) { later.push({ layer: L, prop: r.path, orig: r.orig }); }
      }
      // AKD· 효과·마스크
      var fxp = L.property("ADBE Effect Parade");
      for (j = fxp.numProperties; j >= 1; j--) { if (String(fxp.property(j).name).indexOf("AKD·") === 0) { fxp.property(j).remove(); } }
      var mk = L.property("ADBE Mask Parade");
      if (mk) { for (j = mk.numProperties; j >= 1; j--) { if (String(mk.property(j).name).indexOf("AKD·") === 0) { mk.property(j).remove(); } } }
      L.property("ADBE Marker").removeKey(m.key);
      restored++;
    }
    // 지울 레이어를 부모로 둔 레이어는 먼저 떼어 냅니다(화면 위치 유지, 그 위 부모가 남으면 그쪽으로)
    var createdLayers = [];
    for (i = 0; i < ms.length; i++) { if (ms[i].role === "created") { createdLayers.push(ms[i].layer); } }
    for (i = 1; i <= comp.numLayers; i++) {
      var l = comp.layer(i);
      for (j = 0; j < createdLayers.length; j++) {
        if (l.parent === createdLayers[j] && !inArr(createdLayers, l)) {
          var gp = createdLayers[j].parent;
          while (gp && inArr(createdLayers, gp)) { gp = gp.parent; }
          A.parent(l, gp || null);
        }
      }
    }
    for (i = 0; i < createdLayers.length; i++) {
      var src = null; try { src = createdLayers[i].source; } catch (e2) {}
      createdLayers[i].remove(); removed++;
      // 이 적용이 만든 프리컴프는 쓰는 곳이 없으면 같이 지웁니다
      try { if (src instanceof CompItem && src.usedIn.length === 0 && src.parentFolder && src.parentFolder.name === "기법 도감 프리컴프") { src.remove(); } } catch (e3) {}
    }
    // 속성·정적 값 복원(부모 → 시간 → 값 순)
    for (i = 0; i < later.length; i++) {
      var it = later[i];
      try {
        if (it.r && it.r.attr === "parent") {
          var par = null;
          if (it.r.orig) { for (j = 1; j <= comp.numLayers; j++) { if (comp.layer(j).name === it.r.orig.name) { par = comp.layer(j); break; } } }
          A.parent(it.layer, par);
        }
      } catch (e4) {}
    }
    for (i = 0; i < later.length; i++) {
      var it2 = later[i];
      try {
        if (it2.r && (it2.r.attr === "inPoint" || it2.r.attr === "outPoint")) { it2.layer[it2.r.attr] = it2.r.orig; }
        if (it2.prop) { var pp = A.resolvePath(it2.layer, it2.prop); if (pp && !pp.numKeys) { pp.setValue(it2.orig); } }
      } catch (e5) {}
    }
    return { removed: removed, restored: restored, info: info, targets: targets };
  };
  function inArr(a, x) { for (var i = 0; i < a.length; i++) { if (a[i] === x) { return true; } } return false; }

  /** 선택 레이어(또는 지정 레이어)의 ak-dogam 묶음 찾기 → 가장 최근 적용 */
  A._pickGroup = function (comp, layer, group) {
    if (group) { return group; }
    var ls = layer ? [layer] : comp.selectedLayers, best = null;
    for (var i = 0; i < ls.length; i++) {
      var ms = A.marks(ls[i]);
      for (var j = 0; j < ms.length; j++) { if (!best || ms[j].time >= best.time) { best = ms[j]; } }
    }
    return best ? best.group : null;
  };
  A.remove = function (opt) {
    opt = opt || {};
    try {
      var comp = opt.comp || app.project.activeItem;
      if (!(comp instanceof CompItem)) { return res({ ok: false, error: "컴포지션을 열어 주세요." }); }
      var g = A._pickGroup(comp, opt.layer, opt.group);
      if (!g) { return res({ ok: false, error: "선택 레이어에 기법 도감 마커(ak-dogam)가 없습니다." }); }
      app.beginUndoGroup("기법 도감: 제거");
      var r = A._removeGroup(comp, g);
      app.endUndoGroup();
      return res({ ok: true, group: g, id: r.info ? r.info.id : null, removed: r.removed, restored: r.restored, msg: "제거 — 레이어 " + r.removed + "개 삭제, 대상 " + r.restored + "개 되돌림" });
    } catch (e) { try { app.endUndoGroup(); } catch (e2) {} return res({ ok: false, error: String(e) + (e.line ? " (줄 " + e.line + ")" : "") }); }
  };
  /** 다시 적용: 같은 묶음을 지우고 (이전 변수 + 새 변수)로 같은 시각·같은 대상에 다시 겁니다 */
  A.reapply = function (opt) {
    opt = opt || {};
    try {
      var comp = opt.comp || app.project.activeItem;
      if (!(comp instanceof CompItem)) { return res({ ok: false, error: "컴포지션을 열어 주세요." }); }
      var g = A._pickGroup(comp, opt.layer, opt.group);
      if (!g) { return res({ ok: false, error: "선택 레이어에 기법 도감 마커(ak-dogam)가 없습니다." }); }
      app.beginUndoGroup("기법 도감: 다시 적용");
      var r = A._removeGroup(comp, g);
      app.endUndoGroup();
      if (!r.info) { return res({ ok: false, error: "묶음 정보를 읽지 못했습니다." }); }
      var P = merge(r.info.params, opt.params), C = merge(r.info.content, opt.content);
      return A.apply(r.info.id, { comp: comp, layers: r.targets, t: (opt.t !== undefined ? opt.t : r.info.t), params: P, content: C, assetsRoot: opt.assetsRoot, sceneNo: opt.sceneNo });
    } catch (e) { try { app.endUndoGroup(); } catch (e2) {} return res({ ok: false, error: String(e) + (e.line ? " (줄 " + e.line + ")" : "") }); }
  };
  /** 선택 레이어의 적용 정보(패널이 폼을 채울 때) */
  A.selectedInfo = function () {
    try {
      var comp = app.project.activeItem;
      if (!(comp instanceof CompItem)) { return res({ ok: true, comp: null, items: [] }); }
      var ls = comp.selectedLayers, items = [];
      for (var i = 0; i < ls.length; i++) {
        var ms = A.marks(ls[i]);
        for (var j = 0; j < ms.length; j++) { items.push({ layer: ls[i].name, id: ms[j].id, group: ms[j].group, role: ms[j].role, t: ms[j].t, params: ms[j].params, content: ms[j].content }); }
      }
      return res({ ok: true, comp: comp.name, time: comp.time, selected: ls.length, items: items });
    } catch (e) { return res({ ok: false, error: String(e) }); }
  };
})(AKD);
