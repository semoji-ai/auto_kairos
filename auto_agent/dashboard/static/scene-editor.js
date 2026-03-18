"use strict";
(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __require = /* @__PURE__ */ ((x) => typeof require !== "undefined" ? require : typeof Proxy !== "undefined" ? new Proxy(x, {
    get: (a2, b2) => (typeof require !== "undefined" ? require : a2)[b2]
  }) : x)(function(x) {
    if (typeof require !== "undefined") return require.apply(this, arguments);
    throw Error('Dynamic require of "' + x + '" is not supported');
  });
  var __commonJS = (cb, mod) => function __require2() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // node_modules/react/cjs/react.production.min.js
  var require_react_production_min = __commonJS({
    "node_modules/react/cjs/react.production.min.js"(exports) {
      "use strict";
      var l = Symbol.for("react.element");
      var n = Symbol.for("react.portal");
      var p = Symbol.for("react.fragment");
      var q = Symbol.for("react.strict_mode");
      var r = Symbol.for("react.profiler");
      var t = Symbol.for("react.provider");
      var u = Symbol.for("react.context");
      var v = Symbol.for("react.forward_ref");
      var w = Symbol.for("react.suspense");
      var x = Symbol.for("react.memo");
      var y = Symbol.for("react.lazy");
      var z = Symbol.iterator;
      function A(a2) {
        if (null === a2 || "object" !== typeof a2) return null;
        a2 = z && a2[z] || a2["@@iterator"];
        return "function" === typeof a2 ? a2 : null;
      }
      var B = { isMounted: function() {
        return false;
      }, enqueueForceUpdate: function() {
      }, enqueueReplaceState: function() {
      }, enqueueSetState: function() {
      } };
      var C = Object.assign;
      var D = {};
      function E(a2, b2, e) {
        this.props = a2;
        this.context = b2;
        this.refs = D;
        this.updater = e || B;
      }
      E.prototype.isReactComponent = {};
      E.prototype.setState = function(a2, b2) {
        if ("object" !== typeof a2 && "function" !== typeof a2 && null != a2) throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
        this.updater.enqueueSetState(this, a2, b2, "setState");
      };
      E.prototype.forceUpdate = function(a2) {
        this.updater.enqueueForceUpdate(this, a2, "forceUpdate");
      };
      function F() {
      }
      F.prototype = E.prototype;
      function G(a2, b2, e) {
        this.props = a2;
        this.context = b2;
        this.refs = D;
        this.updater = e || B;
      }
      var H = G.prototype = new F();
      H.constructor = G;
      C(H, E.prototype);
      H.isPureReactComponent = true;
      var I = Array.isArray;
      var J = Object.prototype.hasOwnProperty;
      var K = { current: null };
      var L = { key: true, ref: true, __self: true, __source: true };
      function M(a2, b2, e) {
        var d, c2 = {}, k = null, h = null;
        if (null != b2) for (d in void 0 !== b2.ref && (h = b2.ref), void 0 !== b2.key && (k = "" + b2.key), b2) J.call(b2, d) && !L.hasOwnProperty(d) && (c2[d] = b2[d]);
        var g = arguments.length - 2;
        if (1 === g) c2.children = e;
        else if (1 < g) {
          for (var f = Array(g), m = 0; m < g; m++) f[m] = arguments[m + 2];
          c2.children = f;
        }
        if (a2 && a2.defaultProps) for (d in g = a2.defaultProps, g) void 0 === c2[d] && (c2[d] = g[d]);
        return { $$typeof: l, type: a2, key: k, ref: h, props: c2, _owner: K.current };
      }
      function N(a2, b2) {
        return { $$typeof: l, type: a2.type, key: b2, ref: a2.ref, props: a2.props, _owner: a2._owner };
      }
      function O(a2) {
        return "object" === typeof a2 && null !== a2 && a2.$$typeof === l;
      }
      function escape(a2) {
        var b2 = { "=": "=0", ":": "=2" };
        return "$" + a2.replace(/[=:]/g, function(a3) {
          return b2[a3];
        });
      }
      var P = /\/+/g;
      function Q(a2, b2) {
        return "object" === typeof a2 && null !== a2 && null != a2.key ? escape("" + a2.key) : b2.toString(36);
      }
      function R(a2, b2, e, d, c2) {
        var k = typeof a2;
        if ("undefined" === k || "boolean" === k) a2 = null;
        var h = false;
        if (null === a2) h = true;
        else switch (k) {
          case "string":
          case "number":
            h = true;
            break;
          case "object":
            switch (a2.$$typeof) {
              case l:
              case n:
                h = true;
            }
        }
        if (h) return h = a2, c2 = c2(h), a2 = "" === d ? "." + Q(h, 0) : d, I(c2) ? (e = "", null != a2 && (e = a2.replace(P, "$&/") + "/"), R(c2, b2, e, "", function(a3) {
          return a3;
        })) : null != c2 && (O(c2) && (c2 = N(c2, e + (!c2.key || h && h.key === c2.key ? "" : ("" + c2.key).replace(P, "$&/") + "/") + a2)), b2.push(c2)), 1;
        h = 0;
        d = "" === d ? "." : d + ":";
        if (I(a2)) for (var g = 0; g < a2.length; g++) {
          k = a2[g];
          var f = d + Q(k, g);
          h += R(k, b2, e, f, c2);
        }
        else if (f = A(a2), "function" === typeof f) for (a2 = f.call(a2), g = 0; !(k = a2.next()).done; ) k = k.value, f = d + Q(k, g++), h += R(k, b2, e, f, c2);
        else if ("object" === k) throw b2 = String(a2), Error("Objects are not valid as a React child (found: " + ("[object Object]" === b2 ? "object with keys {" + Object.keys(a2).join(", ") + "}" : b2) + "). If you meant to render a collection of children, use an array instead.");
        return h;
      }
      function S(a2, b2, e) {
        if (null == a2) return a2;
        var d = [], c2 = 0;
        R(a2, d, "", "", function(a3) {
          return b2.call(e, a3, c2++);
        });
        return d;
      }
      function T(a2) {
        if (-1 === a2._status) {
          var b2 = a2._result;
          b2 = b2();
          b2.then(function(b3) {
            if (0 === a2._status || -1 === a2._status) a2._status = 1, a2._result = b3;
          }, function(b3) {
            if (0 === a2._status || -1 === a2._status) a2._status = 2, a2._result = b3;
          });
          -1 === a2._status && (a2._status = 0, a2._result = b2);
        }
        if (1 === a2._status) return a2._result.default;
        throw a2._result;
      }
      var U = { current: null };
      var V = { transition: null };
      var W = { ReactCurrentDispatcher: U, ReactCurrentBatchConfig: V, ReactCurrentOwner: K };
      function X() {
        throw Error("act(...) is not supported in production builds of React.");
      }
      exports.Children = { map: S, forEach: function(a2, b2, e) {
        S(a2, function() {
          b2.apply(this, arguments);
        }, e);
      }, count: function(a2) {
        var b2 = 0;
        S(a2, function() {
          b2++;
        });
        return b2;
      }, toArray: function(a2) {
        return S(a2, function(a3) {
          return a3;
        }) || [];
      }, only: function(a2) {
        if (!O(a2)) throw Error("React.Children.only expected to receive a single React element child.");
        return a2;
      } };
      exports.Component = E;
      exports.Fragment = p;
      exports.Profiler = r;
      exports.PureComponent = G;
      exports.StrictMode = q;
      exports.Suspense = w;
      exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = W;
      exports.act = X;
      exports.cloneElement = function(a2, b2, e) {
        if (null === a2 || void 0 === a2) throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + a2 + ".");
        var d = C({}, a2.props), c2 = a2.key, k = a2.ref, h = a2._owner;
        if (null != b2) {
          void 0 !== b2.ref && (k = b2.ref, h = K.current);
          void 0 !== b2.key && (c2 = "" + b2.key);
          if (a2.type && a2.type.defaultProps) var g = a2.type.defaultProps;
          for (f in b2) J.call(b2, f) && !L.hasOwnProperty(f) && (d[f] = void 0 === b2[f] && void 0 !== g ? g[f] : b2[f]);
        }
        var f = arguments.length - 2;
        if (1 === f) d.children = e;
        else if (1 < f) {
          g = Array(f);
          for (var m = 0; m < f; m++) g[m] = arguments[m + 2];
          d.children = g;
        }
        return { $$typeof: l, type: a2.type, key: c2, ref: k, props: d, _owner: h };
      };
      exports.createContext = function(a2) {
        a2 = { $$typeof: u, _currentValue: a2, _currentValue2: a2, _threadCount: 0, Provider: null, Consumer: null, _defaultValue: null, _globalName: null };
        a2.Provider = { $$typeof: t, _context: a2 };
        return a2.Consumer = a2;
      };
      exports.createElement = M;
      exports.createFactory = function(a2) {
        var b2 = M.bind(null, a2);
        b2.type = a2;
        return b2;
      };
      exports.createRef = function() {
        return { current: null };
      };
      exports.forwardRef = function(a2) {
        return { $$typeof: v, render: a2 };
      };
      exports.isValidElement = O;
      exports.lazy = function(a2) {
        return { $$typeof: y, _payload: { _status: -1, _result: a2 }, _init: T };
      };
      exports.memo = function(a2, b2) {
        return { $$typeof: x, type: a2, compare: void 0 === b2 ? null : b2 };
      };
      exports.startTransition = function(a2) {
        var b2 = V.transition;
        V.transition = {};
        try {
          a2();
        } finally {
          V.transition = b2;
        }
      };
      exports.unstable_act = X;
      exports.useCallback = function(a2, b2) {
        return U.current.useCallback(a2, b2);
      };
      exports.useContext = function(a2) {
        return U.current.useContext(a2);
      };
      exports.useDebugValue = function() {
      };
      exports.useDeferredValue = function(a2) {
        return U.current.useDeferredValue(a2);
      };
      exports.useEffect = function(a2, b2) {
        return U.current.useEffect(a2, b2);
      };
      exports.useId = function() {
        return U.current.useId();
      };
      exports.useImperativeHandle = function(a2, b2, e) {
        return U.current.useImperativeHandle(a2, b2, e);
      };
      exports.useInsertionEffect = function(a2, b2) {
        return U.current.useInsertionEffect(a2, b2);
      };
      exports.useLayoutEffect = function(a2, b2) {
        return U.current.useLayoutEffect(a2, b2);
      };
      exports.useMemo = function(a2, b2) {
        return U.current.useMemo(a2, b2);
      };
      exports.useReducer = function(a2, b2, e) {
        return U.current.useReducer(a2, b2, e);
      };
      exports.useRef = function(a2) {
        return U.current.useRef(a2);
      };
      exports.useState = function(a2) {
        return U.current.useState(a2);
      };
      exports.useSyncExternalStore = function(a2, b2, e) {
        return U.current.useSyncExternalStore(a2, b2, e);
      };
      exports.useTransition = function() {
        return U.current.useTransition();
      };
      exports.version = "18.3.1";
    }
  });

  // node_modules/react/index.js
  var require_react = __commonJS({
    "node_modules/react/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/scheduler/cjs/scheduler.production.min.js
  var require_scheduler_production_min = __commonJS({
    "node_modules/scheduler/cjs/scheduler.production.min.js"(exports) {
      "use strict";
      function f(a2, b2) {
        var c2 = a2.length;
        a2.push(b2);
        a: for (; 0 < c2; ) {
          var d = c2 - 1 >>> 1, e = a2[d];
          if (0 < g(e, b2)) a2[d] = b2, a2[c2] = e, c2 = d;
          else break a;
        }
      }
      function h(a2) {
        return 0 === a2.length ? null : a2[0];
      }
      function k(a2) {
        if (0 === a2.length) return null;
        var b2 = a2[0], c2 = a2.pop();
        if (c2 !== b2) {
          a2[0] = c2;
          a: for (var d = 0, e = a2.length, w = e >>> 1; d < w; ) {
            var m = 2 * (d + 1) - 1, C = a2[m], n = m + 1, x = a2[n];
            if (0 > g(C, c2)) n < e && 0 > g(x, C) ? (a2[d] = x, a2[n] = c2, d = n) : (a2[d] = C, a2[m] = c2, d = m);
            else if (n < e && 0 > g(x, c2)) a2[d] = x, a2[n] = c2, d = n;
            else break a;
          }
        }
        return b2;
      }
      function g(a2, b2) {
        var c2 = a2.sortIndex - b2.sortIndex;
        return 0 !== c2 ? c2 : a2.id - b2.id;
      }
      if ("object" === typeof performance && "function" === typeof performance.now) {
        l = performance;
        exports.unstable_now = function() {
          return l.now();
        };
      } else {
        p = Date, q = p.now();
        exports.unstable_now = function() {
          return p.now() - q;
        };
      }
      var l;
      var p;
      var q;
      var r = [];
      var t = [];
      var u = 1;
      var v = null;
      var y = 3;
      var z = false;
      var A = false;
      var B = false;
      var D = "function" === typeof setTimeout ? setTimeout : null;
      var E = "function" === typeof clearTimeout ? clearTimeout : null;
      var F = "undefined" !== typeof setImmediate ? setImmediate : null;
      "undefined" !== typeof navigator && void 0 !== navigator.scheduling && void 0 !== navigator.scheduling.isInputPending && navigator.scheduling.isInputPending.bind(navigator.scheduling);
      function G(a2) {
        for (var b2 = h(t); null !== b2; ) {
          if (null === b2.callback) k(t);
          else if (b2.startTime <= a2) k(t), b2.sortIndex = b2.expirationTime, f(r, b2);
          else break;
          b2 = h(t);
        }
      }
      function H(a2) {
        B = false;
        G(a2);
        if (!A) if (null !== h(r)) A = true, I(J);
        else {
          var b2 = h(t);
          null !== b2 && K(H, b2.startTime - a2);
        }
      }
      function J(a2, b2) {
        A = false;
        B && (B = false, E(L), L = -1);
        z = true;
        var c2 = y;
        try {
          G(b2);
          for (v = h(r); null !== v && (!(v.expirationTime > b2) || a2 && !M()); ) {
            var d = v.callback;
            if ("function" === typeof d) {
              v.callback = null;
              y = v.priorityLevel;
              var e = d(v.expirationTime <= b2);
              b2 = exports.unstable_now();
              "function" === typeof e ? v.callback = e : v === h(r) && k(r);
              G(b2);
            } else k(r);
            v = h(r);
          }
          if (null !== v) var w = true;
          else {
            var m = h(t);
            null !== m && K(H, m.startTime - b2);
            w = false;
          }
          return w;
        } finally {
          v = null, y = c2, z = false;
        }
      }
      var N = false;
      var O = null;
      var L = -1;
      var P = 5;
      var Q = -1;
      function M() {
        return exports.unstable_now() - Q < P ? false : true;
      }
      function R() {
        if (null !== O) {
          var a2 = exports.unstable_now();
          Q = a2;
          var b2 = true;
          try {
            b2 = O(true, a2);
          } finally {
            b2 ? S() : (N = false, O = null);
          }
        } else N = false;
      }
      var S;
      if ("function" === typeof F) S = function() {
        F(R);
      };
      else if ("undefined" !== typeof MessageChannel) {
        T = new MessageChannel(), U = T.port2;
        T.port1.onmessage = R;
        S = function() {
          U.postMessage(null);
        };
      } else S = function() {
        D(R, 0);
      };
      var T;
      var U;
      function I(a2) {
        O = a2;
        N || (N = true, S());
      }
      function K(a2, b2) {
        L = D(function() {
          a2(exports.unstable_now());
        }, b2);
      }
      exports.unstable_IdlePriority = 5;
      exports.unstable_ImmediatePriority = 1;
      exports.unstable_LowPriority = 4;
      exports.unstable_NormalPriority = 3;
      exports.unstable_Profiling = null;
      exports.unstable_UserBlockingPriority = 2;
      exports.unstable_cancelCallback = function(a2) {
        a2.callback = null;
      };
      exports.unstable_continueExecution = function() {
        A || z || (A = true, I(J));
      };
      exports.unstable_forceFrameRate = function(a2) {
        0 > a2 || 125 < a2 ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : P = 0 < a2 ? Math.floor(1e3 / a2) : 5;
      };
      exports.unstable_getCurrentPriorityLevel = function() {
        return y;
      };
      exports.unstable_getFirstCallbackNode = function() {
        return h(r);
      };
      exports.unstable_next = function(a2) {
        switch (y) {
          case 1:
          case 2:
          case 3:
            var b2 = 3;
            break;
          default:
            b2 = y;
        }
        var c2 = y;
        y = b2;
        try {
          return a2();
        } finally {
          y = c2;
        }
      };
      exports.unstable_pauseExecution = function() {
      };
      exports.unstable_requestPaint = function() {
      };
      exports.unstable_runWithPriority = function(a2, b2) {
        switch (a2) {
          case 1:
          case 2:
          case 3:
          case 4:
          case 5:
            break;
          default:
            a2 = 3;
        }
        var c2 = y;
        y = a2;
        try {
          return b2();
        } finally {
          y = c2;
        }
      };
      exports.unstable_scheduleCallback = function(a2, b2, c2) {
        var d = exports.unstable_now();
        "object" === typeof c2 && null !== c2 ? (c2 = c2.delay, c2 = "number" === typeof c2 && 0 < c2 ? d + c2 : d) : c2 = d;
        switch (a2) {
          case 1:
            var e = -1;
            break;
          case 2:
            e = 250;
            break;
          case 5:
            e = 1073741823;
            break;
          case 4:
            e = 1e4;
            break;
          default:
            e = 5e3;
        }
        e = c2 + e;
        a2 = { id: u++, callback: b2, priorityLevel: a2, startTime: c2, expirationTime: e, sortIndex: -1 };
        c2 > d ? (a2.sortIndex = c2, f(t, a2), null === h(r) && a2 === h(t) && (B ? (E(L), L = -1) : B = true, K(H, c2 - d))) : (a2.sortIndex = e, f(r, a2), A || z || (A = true, I(J)));
        return a2;
      };
      exports.unstable_shouldYield = M;
      exports.unstable_wrapCallback = function(a2) {
        var b2 = y;
        return function() {
          var c2 = y;
          y = b2;
          try {
            return a2.apply(this, arguments);
          } finally {
            y = c2;
          }
        };
      };
    }
  });

  // node_modules/scheduler/index.js
  var require_scheduler = __commonJS({
    "node_modules/scheduler/index.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_scheduler_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/cjs/react-dom.production.min.js
  var require_react_dom_production_min = __commonJS({
    "node_modules/react-dom/cjs/react-dom.production.min.js"(exports) {
      "use strict";
      var aa = require_react();
      var ca = require_scheduler();
      function p(a2) {
        for (var b2 = "https://reactjs.org/docs/error-decoder.html?invariant=" + a2, c2 = 1; c2 < arguments.length; c2++) b2 += "&args[]=" + encodeURIComponent(arguments[c2]);
        return "Minified React error #" + a2 + "; visit " + b2 + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
      }
      var da = /* @__PURE__ */ new Set();
      var ea = {};
      function fa(a2, b2) {
        ha(a2, b2);
        ha(a2 + "Capture", b2);
      }
      function ha(a2, b2) {
        ea[a2] = b2;
        for (a2 = 0; a2 < b2.length; a2++) da.add(b2[a2]);
      }
      var ia = !("undefined" === typeof window || "undefined" === typeof window.document || "undefined" === typeof window.document.createElement);
      var ja = Object.prototype.hasOwnProperty;
      var ka = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/;
      var la = {};
      var ma = {};
      function oa(a2) {
        if (ja.call(ma, a2)) return true;
        if (ja.call(la, a2)) return false;
        if (ka.test(a2)) return ma[a2] = true;
        la[a2] = true;
        return false;
      }
      function pa(a2, b2, c2, d) {
        if (null !== c2 && 0 === c2.type) return false;
        switch (typeof b2) {
          case "function":
          case "symbol":
            return true;
          case "boolean":
            if (d) return false;
            if (null !== c2) return !c2.acceptsBooleans;
            a2 = a2.toLowerCase().slice(0, 5);
            return "data-" !== a2 && "aria-" !== a2;
          default:
            return false;
        }
      }
      function qa(a2, b2, c2, d) {
        if (null === b2 || "undefined" === typeof b2 || pa(a2, b2, c2, d)) return true;
        if (d) return false;
        if (null !== c2) switch (c2.type) {
          case 3:
            return !b2;
          case 4:
            return false === b2;
          case 5:
            return isNaN(b2);
          case 6:
            return isNaN(b2) || 1 > b2;
        }
        return false;
      }
      function v(a2, b2, c2, d, e, f, g) {
        this.acceptsBooleans = 2 === b2 || 3 === b2 || 4 === b2;
        this.attributeName = d;
        this.attributeNamespace = e;
        this.mustUseProperty = c2;
        this.propertyName = a2;
        this.type = b2;
        this.sanitizeURL = f;
        this.removeEmptyString = g;
      }
      var z = {};
      "children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(a2) {
        z[a2] = new v(a2, 0, false, a2, null, false, false);
      });
      [["acceptCharset", "accept-charset"], ["className", "class"], ["htmlFor", "for"], ["httpEquiv", "http-equiv"]].forEach(function(a2) {
        var b2 = a2[0];
        z[b2] = new v(b2, 1, false, a2[1], null, false, false);
      });
      ["contentEditable", "draggable", "spellCheck", "value"].forEach(function(a2) {
        z[a2] = new v(a2, 2, false, a2.toLowerCase(), null, false, false);
      });
      ["autoReverse", "externalResourcesRequired", "focusable", "preserveAlpha"].forEach(function(a2) {
        z[a2] = new v(a2, 2, false, a2, null, false, false);
      });
      "allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(a2) {
        z[a2] = new v(a2, 3, false, a2.toLowerCase(), null, false, false);
      });
      ["checked", "multiple", "muted", "selected"].forEach(function(a2) {
        z[a2] = new v(a2, 3, true, a2, null, false, false);
      });
      ["capture", "download"].forEach(function(a2) {
        z[a2] = new v(a2, 4, false, a2, null, false, false);
      });
      ["cols", "rows", "size", "span"].forEach(function(a2) {
        z[a2] = new v(a2, 6, false, a2, null, false, false);
      });
      ["rowSpan", "start"].forEach(function(a2) {
        z[a2] = new v(a2, 5, false, a2.toLowerCase(), null, false, false);
      });
      var ra = /[\-:]([a-z])/g;
      function sa(a2) {
        return a2[1].toUpperCase();
      }
      "accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(a2) {
        var b2 = a2.replace(
          ra,
          sa
        );
        z[b2] = new v(b2, 1, false, a2, null, false, false);
      });
      "xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(a2) {
        var b2 = a2.replace(ra, sa);
        z[b2] = new v(b2, 1, false, a2, "http://www.w3.org/1999/xlink", false, false);
      });
      ["xml:base", "xml:lang", "xml:space"].forEach(function(a2) {
        var b2 = a2.replace(ra, sa);
        z[b2] = new v(b2, 1, false, a2, "http://www.w3.org/XML/1998/namespace", false, false);
      });
      ["tabIndex", "crossOrigin"].forEach(function(a2) {
        z[a2] = new v(a2, 1, false, a2.toLowerCase(), null, false, false);
      });
      z.xlinkHref = new v("xlinkHref", 1, false, "xlink:href", "http://www.w3.org/1999/xlink", true, false);
      ["src", "href", "action", "formAction"].forEach(function(a2) {
        z[a2] = new v(a2, 1, false, a2.toLowerCase(), null, true, true);
      });
      function ta(a2, b2, c2, d) {
        var e = z.hasOwnProperty(b2) ? z[b2] : null;
        if (null !== e ? 0 !== e.type : d || !(2 < b2.length) || "o" !== b2[0] && "O" !== b2[0] || "n" !== b2[1] && "N" !== b2[1]) qa(b2, c2, e, d) && (c2 = null), d || null === e ? oa(b2) && (null === c2 ? a2.removeAttribute(b2) : a2.setAttribute(b2, "" + c2)) : e.mustUseProperty ? a2[e.propertyName] = null === c2 ? 3 === e.type ? false : "" : c2 : (b2 = e.attributeName, d = e.attributeNamespace, null === c2 ? a2.removeAttribute(b2) : (e = e.type, c2 = 3 === e || 4 === e && true === c2 ? "" : "" + c2, d ? a2.setAttributeNS(d, b2, c2) : a2.setAttribute(b2, c2)));
      }
      var ua = aa.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
      var va = Symbol.for("react.element");
      var wa = Symbol.for("react.portal");
      var ya = Symbol.for("react.fragment");
      var za = Symbol.for("react.strict_mode");
      var Aa = Symbol.for("react.profiler");
      var Ba = Symbol.for("react.provider");
      var Ca = Symbol.for("react.context");
      var Da = Symbol.for("react.forward_ref");
      var Ea = Symbol.for("react.suspense");
      var Fa = Symbol.for("react.suspense_list");
      var Ga = Symbol.for("react.memo");
      var Ha = Symbol.for("react.lazy");
      Symbol.for("react.scope");
      Symbol.for("react.debug_trace_mode");
      var Ia = Symbol.for("react.offscreen");
      Symbol.for("react.legacy_hidden");
      Symbol.for("react.cache");
      Symbol.for("react.tracing_marker");
      var Ja = Symbol.iterator;
      function Ka(a2) {
        if (null === a2 || "object" !== typeof a2) return null;
        a2 = Ja && a2[Ja] || a2["@@iterator"];
        return "function" === typeof a2 ? a2 : null;
      }
      var A = Object.assign;
      var La;
      function Ma(a2) {
        if (void 0 === La) try {
          throw Error();
        } catch (c2) {
          var b2 = c2.stack.trim().match(/\n( *(at )?)/);
          La = b2 && b2[1] || "";
        }
        return "\n" + La + a2;
      }
      var Na = false;
      function Oa(a2, b2) {
        if (!a2 || Na) return "";
        Na = true;
        var c2 = Error.prepareStackTrace;
        Error.prepareStackTrace = void 0;
        try {
          if (b2) if (b2 = function() {
            throw Error();
          }, Object.defineProperty(b2.prototype, "props", { set: function() {
            throw Error();
          } }), "object" === typeof Reflect && Reflect.construct) {
            try {
              Reflect.construct(b2, []);
            } catch (l) {
              var d = l;
            }
            Reflect.construct(a2, [], b2);
          } else {
            try {
              b2.call();
            } catch (l) {
              d = l;
            }
            a2.call(b2.prototype);
          }
          else {
            try {
              throw Error();
            } catch (l) {
              d = l;
            }
            a2();
          }
        } catch (l) {
          if (l && d && "string" === typeof l.stack) {
            for (var e = l.stack.split("\n"), f = d.stack.split("\n"), g = e.length - 1, h = f.length - 1; 1 <= g && 0 <= h && e[g] !== f[h]; ) h--;
            for (; 1 <= g && 0 <= h; g--, h--) if (e[g] !== f[h]) {
              if (1 !== g || 1 !== h) {
                do
                  if (g--, h--, 0 > h || e[g] !== f[h]) {
                    var k = "\n" + e[g].replace(" at new ", " at ");
                    a2.displayName && k.includes("<anonymous>") && (k = k.replace("<anonymous>", a2.displayName));
                    return k;
                  }
                while (1 <= g && 0 <= h);
              }
              break;
            }
          }
        } finally {
          Na = false, Error.prepareStackTrace = c2;
        }
        return (a2 = a2 ? a2.displayName || a2.name : "") ? Ma(a2) : "";
      }
      function Pa(a2) {
        switch (a2.tag) {
          case 5:
            return Ma(a2.type);
          case 16:
            return Ma("Lazy");
          case 13:
            return Ma("Suspense");
          case 19:
            return Ma("SuspenseList");
          case 0:
          case 2:
          case 15:
            return a2 = Oa(a2.type, false), a2;
          case 11:
            return a2 = Oa(a2.type.render, false), a2;
          case 1:
            return a2 = Oa(a2.type, true), a2;
          default:
            return "";
        }
      }
      function Qa(a2) {
        if (null == a2) return null;
        if ("function" === typeof a2) return a2.displayName || a2.name || null;
        if ("string" === typeof a2) return a2;
        switch (a2) {
          case ya:
            return "Fragment";
          case wa:
            return "Portal";
          case Aa:
            return "Profiler";
          case za:
            return "StrictMode";
          case Ea:
            return "Suspense";
          case Fa:
            return "SuspenseList";
        }
        if ("object" === typeof a2) switch (a2.$$typeof) {
          case Ca:
            return (a2.displayName || "Context") + ".Consumer";
          case Ba:
            return (a2._context.displayName || "Context") + ".Provider";
          case Da:
            var b2 = a2.render;
            a2 = a2.displayName;
            a2 || (a2 = b2.displayName || b2.name || "", a2 = "" !== a2 ? "ForwardRef(" + a2 + ")" : "ForwardRef");
            return a2;
          case Ga:
            return b2 = a2.displayName || null, null !== b2 ? b2 : Qa(a2.type) || "Memo";
          case Ha:
            b2 = a2._payload;
            a2 = a2._init;
            try {
              return Qa(a2(b2));
            } catch (c2) {
            }
        }
        return null;
      }
      function Ra(a2) {
        var b2 = a2.type;
        switch (a2.tag) {
          case 24:
            return "Cache";
          case 9:
            return (b2.displayName || "Context") + ".Consumer";
          case 10:
            return (b2._context.displayName || "Context") + ".Provider";
          case 18:
            return "DehydratedFragment";
          case 11:
            return a2 = b2.render, a2 = a2.displayName || a2.name || "", b2.displayName || ("" !== a2 ? "ForwardRef(" + a2 + ")" : "ForwardRef");
          case 7:
            return "Fragment";
          case 5:
            return b2;
          case 4:
            return "Portal";
          case 3:
            return "Root";
          case 6:
            return "Text";
          case 16:
            return Qa(b2);
          case 8:
            return b2 === za ? "StrictMode" : "Mode";
          case 22:
            return "Offscreen";
          case 12:
            return "Profiler";
          case 21:
            return "Scope";
          case 13:
            return "Suspense";
          case 19:
            return "SuspenseList";
          case 25:
            return "TracingMarker";
          case 1:
          case 0:
          case 17:
          case 2:
          case 14:
          case 15:
            if ("function" === typeof b2) return b2.displayName || b2.name || null;
            if ("string" === typeof b2) return b2;
        }
        return null;
      }
      function Sa(a2) {
        switch (typeof a2) {
          case "boolean":
          case "number":
          case "string":
          case "undefined":
            return a2;
          case "object":
            return a2;
          default:
            return "";
        }
      }
      function Ta(a2) {
        var b2 = a2.type;
        return (a2 = a2.nodeName) && "input" === a2.toLowerCase() && ("checkbox" === b2 || "radio" === b2);
      }
      function Ua(a2) {
        var b2 = Ta(a2) ? "checked" : "value", c2 = Object.getOwnPropertyDescriptor(a2.constructor.prototype, b2), d = "" + a2[b2];
        if (!a2.hasOwnProperty(b2) && "undefined" !== typeof c2 && "function" === typeof c2.get && "function" === typeof c2.set) {
          var e = c2.get, f = c2.set;
          Object.defineProperty(a2, b2, { configurable: true, get: function() {
            return e.call(this);
          }, set: function(a3) {
            d = "" + a3;
            f.call(this, a3);
          } });
          Object.defineProperty(a2, b2, { enumerable: c2.enumerable });
          return { getValue: function() {
            return d;
          }, setValue: function(a3) {
            d = "" + a3;
          }, stopTracking: function() {
            a2._valueTracker = null;
            delete a2[b2];
          } };
        }
      }
      function Va(a2) {
        a2._valueTracker || (a2._valueTracker = Ua(a2));
      }
      function Wa(a2) {
        if (!a2) return false;
        var b2 = a2._valueTracker;
        if (!b2) return true;
        var c2 = b2.getValue();
        var d = "";
        a2 && (d = Ta(a2) ? a2.checked ? "true" : "false" : a2.value);
        a2 = d;
        return a2 !== c2 ? (b2.setValue(a2), true) : false;
      }
      function Xa(a2) {
        a2 = a2 || ("undefined" !== typeof document ? document : void 0);
        if ("undefined" === typeof a2) return null;
        try {
          return a2.activeElement || a2.body;
        } catch (b2) {
          return a2.body;
        }
      }
      function Ya(a2, b2) {
        var c2 = b2.checked;
        return A({}, b2, { defaultChecked: void 0, defaultValue: void 0, value: void 0, checked: null != c2 ? c2 : a2._wrapperState.initialChecked });
      }
      function Za(a2, b2) {
        var c2 = null == b2.defaultValue ? "" : b2.defaultValue, d = null != b2.checked ? b2.checked : b2.defaultChecked;
        c2 = Sa(null != b2.value ? b2.value : c2);
        a2._wrapperState = { initialChecked: d, initialValue: c2, controlled: "checkbox" === b2.type || "radio" === b2.type ? null != b2.checked : null != b2.value };
      }
      function ab(a2, b2) {
        b2 = b2.checked;
        null != b2 && ta(a2, "checked", b2, false);
      }
      function bb(a2, b2) {
        ab(a2, b2);
        var c2 = Sa(b2.value), d = b2.type;
        if (null != c2) if ("number" === d) {
          if (0 === c2 && "" === a2.value || a2.value != c2) a2.value = "" + c2;
        } else a2.value !== "" + c2 && (a2.value = "" + c2);
        else if ("submit" === d || "reset" === d) {
          a2.removeAttribute("value");
          return;
        }
        b2.hasOwnProperty("value") ? cb(a2, b2.type, c2) : b2.hasOwnProperty("defaultValue") && cb(a2, b2.type, Sa(b2.defaultValue));
        null == b2.checked && null != b2.defaultChecked && (a2.defaultChecked = !!b2.defaultChecked);
      }
      function db(a2, b2, c2) {
        if (b2.hasOwnProperty("value") || b2.hasOwnProperty("defaultValue")) {
          var d = b2.type;
          if (!("submit" !== d && "reset" !== d || void 0 !== b2.value && null !== b2.value)) return;
          b2 = "" + a2._wrapperState.initialValue;
          c2 || b2 === a2.value || (a2.value = b2);
          a2.defaultValue = b2;
        }
        c2 = a2.name;
        "" !== c2 && (a2.name = "");
        a2.defaultChecked = !!a2._wrapperState.initialChecked;
        "" !== c2 && (a2.name = c2);
      }
      function cb(a2, b2, c2) {
        if ("number" !== b2 || Xa(a2.ownerDocument) !== a2) null == c2 ? a2.defaultValue = "" + a2._wrapperState.initialValue : a2.defaultValue !== "" + c2 && (a2.defaultValue = "" + c2);
      }
      var eb = Array.isArray;
      function fb(a2, b2, c2, d) {
        a2 = a2.options;
        if (b2) {
          b2 = {};
          for (var e = 0; e < c2.length; e++) b2["$" + c2[e]] = true;
          for (c2 = 0; c2 < a2.length; c2++) e = b2.hasOwnProperty("$" + a2[c2].value), a2[c2].selected !== e && (a2[c2].selected = e), e && d && (a2[c2].defaultSelected = true);
        } else {
          c2 = "" + Sa(c2);
          b2 = null;
          for (e = 0; e < a2.length; e++) {
            if (a2[e].value === c2) {
              a2[e].selected = true;
              d && (a2[e].defaultSelected = true);
              return;
            }
            null !== b2 || a2[e].disabled || (b2 = a2[e]);
          }
          null !== b2 && (b2.selected = true);
        }
      }
      function gb(a2, b2) {
        if (null != b2.dangerouslySetInnerHTML) throw Error(p(91));
        return A({}, b2, { value: void 0, defaultValue: void 0, children: "" + a2._wrapperState.initialValue });
      }
      function hb(a2, b2) {
        var c2 = b2.value;
        if (null == c2) {
          c2 = b2.children;
          b2 = b2.defaultValue;
          if (null != c2) {
            if (null != b2) throw Error(p(92));
            if (eb(c2)) {
              if (1 < c2.length) throw Error(p(93));
              c2 = c2[0];
            }
            b2 = c2;
          }
          null == b2 && (b2 = "");
          c2 = b2;
        }
        a2._wrapperState = { initialValue: Sa(c2) };
      }
      function ib(a2, b2) {
        var c2 = Sa(b2.value), d = Sa(b2.defaultValue);
        null != c2 && (c2 = "" + c2, c2 !== a2.value && (a2.value = c2), null == b2.defaultValue && a2.defaultValue !== c2 && (a2.defaultValue = c2));
        null != d && (a2.defaultValue = "" + d);
      }
      function jb(a2) {
        var b2 = a2.textContent;
        b2 === a2._wrapperState.initialValue && "" !== b2 && null !== b2 && (a2.value = b2);
      }
      function kb(a2) {
        switch (a2) {
          case "svg":
            return "http://www.w3.org/2000/svg";
          case "math":
            return "http://www.w3.org/1998/Math/MathML";
          default:
            return "http://www.w3.org/1999/xhtml";
        }
      }
      function lb(a2, b2) {
        return null == a2 || "http://www.w3.org/1999/xhtml" === a2 ? kb(b2) : "http://www.w3.org/2000/svg" === a2 && "foreignObject" === b2 ? "http://www.w3.org/1999/xhtml" : a2;
      }
      var mb;
      var nb = function(a2) {
        return "undefined" !== typeof MSApp && MSApp.execUnsafeLocalFunction ? function(b2, c2, d, e) {
          MSApp.execUnsafeLocalFunction(function() {
            return a2(b2, c2, d, e);
          });
        } : a2;
      }(function(a2, b2) {
        if ("http://www.w3.org/2000/svg" !== a2.namespaceURI || "innerHTML" in a2) a2.innerHTML = b2;
        else {
          mb = mb || document.createElement("div");
          mb.innerHTML = "<svg>" + b2.valueOf().toString() + "</svg>";
          for (b2 = mb.firstChild; a2.firstChild; ) a2.removeChild(a2.firstChild);
          for (; b2.firstChild; ) a2.appendChild(b2.firstChild);
        }
      });
      function ob(a2, b2) {
        if (b2) {
          var c2 = a2.firstChild;
          if (c2 && c2 === a2.lastChild && 3 === c2.nodeType) {
            c2.nodeValue = b2;
            return;
          }
        }
        a2.textContent = b2;
      }
      var pb = {
        animationIterationCount: true,
        aspectRatio: true,
        borderImageOutset: true,
        borderImageSlice: true,
        borderImageWidth: true,
        boxFlex: true,
        boxFlexGroup: true,
        boxOrdinalGroup: true,
        columnCount: true,
        columns: true,
        flex: true,
        flexGrow: true,
        flexPositive: true,
        flexShrink: true,
        flexNegative: true,
        flexOrder: true,
        gridArea: true,
        gridRow: true,
        gridRowEnd: true,
        gridRowSpan: true,
        gridRowStart: true,
        gridColumn: true,
        gridColumnEnd: true,
        gridColumnSpan: true,
        gridColumnStart: true,
        fontWeight: true,
        lineClamp: true,
        lineHeight: true,
        opacity: true,
        order: true,
        orphans: true,
        tabSize: true,
        widows: true,
        zIndex: true,
        zoom: true,
        fillOpacity: true,
        floodOpacity: true,
        stopOpacity: true,
        strokeDasharray: true,
        strokeDashoffset: true,
        strokeMiterlimit: true,
        strokeOpacity: true,
        strokeWidth: true
      };
      var qb = ["Webkit", "ms", "Moz", "O"];
      Object.keys(pb).forEach(function(a2) {
        qb.forEach(function(b2) {
          b2 = b2 + a2.charAt(0).toUpperCase() + a2.substring(1);
          pb[b2] = pb[a2];
        });
      });
      function rb(a2, b2, c2) {
        return null == b2 || "boolean" === typeof b2 || "" === b2 ? "" : c2 || "number" !== typeof b2 || 0 === b2 || pb.hasOwnProperty(a2) && pb[a2] ? ("" + b2).trim() : b2 + "px";
      }
      function sb(a2, b2) {
        a2 = a2.style;
        for (var c2 in b2) if (b2.hasOwnProperty(c2)) {
          var d = 0 === c2.indexOf("--"), e = rb(c2, b2[c2], d);
          "float" === c2 && (c2 = "cssFloat");
          d ? a2.setProperty(c2, e) : a2[c2] = e;
        }
      }
      var tb = A({ menuitem: true }, { area: true, base: true, br: true, col: true, embed: true, hr: true, img: true, input: true, keygen: true, link: true, meta: true, param: true, source: true, track: true, wbr: true });
      function ub(a2, b2) {
        if (b2) {
          if (tb[a2] && (null != b2.children || null != b2.dangerouslySetInnerHTML)) throw Error(p(137, a2));
          if (null != b2.dangerouslySetInnerHTML) {
            if (null != b2.children) throw Error(p(60));
            if ("object" !== typeof b2.dangerouslySetInnerHTML || !("__html" in b2.dangerouslySetInnerHTML)) throw Error(p(61));
          }
          if (null != b2.style && "object" !== typeof b2.style) throw Error(p(62));
        }
      }
      function vb(a2, b2) {
        if (-1 === a2.indexOf("-")) return "string" === typeof b2.is;
        switch (a2) {
          case "annotation-xml":
          case "color-profile":
          case "font-face":
          case "font-face-src":
          case "font-face-uri":
          case "font-face-format":
          case "font-face-name":
          case "missing-glyph":
            return false;
          default:
            return true;
        }
      }
      var wb = null;
      function xb(a2) {
        a2 = a2.target || a2.srcElement || window;
        a2.correspondingUseElement && (a2 = a2.correspondingUseElement);
        return 3 === a2.nodeType ? a2.parentNode : a2;
      }
      var yb = null;
      var zb = null;
      var Ab = null;
      function Bb(a2) {
        if (a2 = Cb(a2)) {
          if ("function" !== typeof yb) throw Error(p(280));
          var b2 = a2.stateNode;
          b2 && (b2 = Db(b2), yb(a2.stateNode, a2.type, b2));
        }
      }
      function Eb(a2) {
        zb ? Ab ? Ab.push(a2) : Ab = [a2] : zb = a2;
      }
      function Fb() {
        if (zb) {
          var a2 = zb, b2 = Ab;
          Ab = zb = null;
          Bb(a2);
          if (b2) for (a2 = 0; a2 < b2.length; a2++) Bb(b2[a2]);
        }
      }
      function Gb(a2, b2) {
        return a2(b2);
      }
      function Hb() {
      }
      var Ib = false;
      function Jb(a2, b2, c2) {
        if (Ib) return a2(b2, c2);
        Ib = true;
        try {
          return Gb(a2, b2, c2);
        } finally {
          if (Ib = false, null !== zb || null !== Ab) Hb(), Fb();
        }
      }
      function Kb(a2, b2) {
        var c2 = a2.stateNode;
        if (null === c2) return null;
        var d = Db(c2);
        if (null === d) return null;
        c2 = d[b2];
        a: switch (b2) {
          case "onClick":
          case "onClickCapture":
          case "onDoubleClick":
          case "onDoubleClickCapture":
          case "onMouseDown":
          case "onMouseDownCapture":
          case "onMouseMove":
          case "onMouseMoveCapture":
          case "onMouseUp":
          case "onMouseUpCapture":
          case "onMouseEnter":
            (d = !d.disabled) || (a2 = a2.type, d = !("button" === a2 || "input" === a2 || "select" === a2 || "textarea" === a2));
            a2 = !d;
            break a;
          default:
            a2 = false;
        }
        if (a2) return null;
        if (c2 && "function" !== typeof c2) throw Error(p(231, b2, typeof c2));
        return c2;
      }
      var Lb = false;
      if (ia) try {
        Mb = {};
        Object.defineProperty(Mb, "passive", { get: function() {
          Lb = true;
        } });
        window.addEventListener("test", Mb, Mb);
        window.removeEventListener("test", Mb, Mb);
      } catch (a2) {
        Lb = false;
      }
      var Mb;
      function Nb(a2, b2, c2, d, e, f, g, h, k) {
        var l = Array.prototype.slice.call(arguments, 3);
        try {
          b2.apply(c2, l);
        } catch (m) {
          this.onError(m);
        }
      }
      var Ob = false;
      var Pb = null;
      var Qb = false;
      var Rb = null;
      var Sb = { onError: function(a2) {
        Ob = true;
        Pb = a2;
      } };
      function Tb(a2, b2, c2, d, e, f, g, h, k) {
        Ob = false;
        Pb = null;
        Nb.apply(Sb, arguments);
      }
      function Ub(a2, b2, c2, d, e, f, g, h, k) {
        Tb.apply(this, arguments);
        if (Ob) {
          if (Ob) {
            var l = Pb;
            Ob = false;
            Pb = null;
          } else throw Error(p(198));
          Qb || (Qb = true, Rb = l);
        }
      }
      function Vb(a2) {
        var b2 = a2, c2 = a2;
        if (a2.alternate) for (; b2.return; ) b2 = b2.return;
        else {
          a2 = b2;
          do
            b2 = a2, 0 !== (b2.flags & 4098) && (c2 = b2.return), a2 = b2.return;
          while (a2);
        }
        return 3 === b2.tag ? c2 : null;
      }
      function Wb(a2) {
        if (13 === a2.tag) {
          var b2 = a2.memoizedState;
          null === b2 && (a2 = a2.alternate, null !== a2 && (b2 = a2.memoizedState));
          if (null !== b2) return b2.dehydrated;
        }
        return null;
      }
      function Xb(a2) {
        if (Vb(a2) !== a2) throw Error(p(188));
      }
      function Yb(a2) {
        var b2 = a2.alternate;
        if (!b2) {
          b2 = Vb(a2);
          if (null === b2) throw Error(p(188));
          return b2 !== a2 ? null : a2;
        }
        for (var c2 = a2, d = b2; ; ) {
          var e = c2.return;
          if (null === e) break;
          var f = e.alternate;
          if (null === f) {
            d = e.return;
            if (null !== d) {
              c2 = d;
              continue;
            }
            break;
          }
          if (e.child === f.child) {
            for (f = e.child; f; ) {
              if (f === c2) return Xb(e), a2;
              if (f === d) return Xb(e), b2;
              f = f.sibling;
            }
            throw Error(p(188));
          }
          if (c2.return !== d.return) c2 = e, d = f;
          else {
            for (var g = false, h = e.child; h; ) {
              if (h === c2) {
                g = true;
                c2 = e;
                d = f;
                break;
              }
              if (h === d) {
                g = true;
                d = e;
                c2 = f;
                break;
              }
              h = h.sibling;
            }
            if (!g) {
              for (h = f.child; h; ) {
                if (h === c2) {
                  g = true;
                  c2 = f;
                  d = e;
                  break;
                }
                if (h === d) {
                  g = true;
                  d = f;
                  c2 = e;
                  break;
                }
                h = h.sibling;
              }
              if (!g) throw Error(p(189));
            }
          }
          if (c2.alternate !== d) throw Error(p(190));
        }
        if (3 !== c2.tag) throw Error(p(188));
        return c2.stateNode.current === c2 ? a2 : b2;
      }
      function Zb(a2) {
        a2 = Yb(a2);
        return null !== a2 ? $b(a2) : null;
      }
      function $b(a2) {
        if (5 === a2.tag || 6 === a2.tag) return a2;
        for (a2 = a2.child; null !== a2; ) {
          var b2 = $b(a2);
          if (null !== b2) return b2;
          a2 = a2.sibling;
        }
        return null;
      }
      var ac = ca.unstable_scheduleCallback;
      var bc = ca.unstable_cancelCallback;
      var cc = ca.unstable_shouldYield;
      var dc = ca.unstable_requestPaint;
      var B = ca.unstable_now;
      var ec = ca.unstable_getCurrentPriorityLevel;
      var fc = ca.unstable_ImmediatePriority;
      var gc = ca.unstable_UserBlockingPriority;
      var hc = ca.unstable_NormalPriority;
      var ic = ca.unstable_LowPriority;
      var jc = ca.unstable_IdlePriority;
      var kc = null;
      var lc = null;
      function mc(a2) {
        if (lc && "function" === typeof lc.onCommitFiberRoot) try {
          lc.onCommitFiberRoot(kc, a2, void 0, 128 === (a2.current.flags & 128));
        } catch (b2) {
        }
      }
      var oc = Math.clz32 ? Math.clz32 : nc;
      var pc = Math.log;
      var qc = Math.LN2;
      function nc(a2) {
        a2 >>>= 0;
        return 0 === a2 ? 32 : 31 - (pc(a2) / qc | 0) | 0;
      }
      var rc = 64;
      var sc = 4194304;
      function tc(a2) {
        switch (a2 & -a2) {
          case 1:
            return 1;
          case 2:
            return 2;
          case 4:
            return 4;
          case 8:
            return 8;
          case 16:
            return 16;
          case 32:
            return 32;
          case 64:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return a2 & 4194240;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
          case 67108864:
            return a2 & 130023424;
          case 134217728:
            return 134217728;
          case 268435456:
            return 268435456;
          case 536870912:
            return 536870912;
          case 1073741824:
            return 1073741824;
          default:
            return a2;
        }
      }
      function uc(a2, b2) {
        var c2 = a2.pendingLanes;
        if (0 === c2) return 0;
        var d = 0, e = a2.suspendedLanes, f = a2.pingedLanes, g = c2 & 268435455;
        if (0 !== g) {
          var h = g & ~e;
          0 !== h ? d = tc(h) : (f &= g, 0 !== f && (d = tc(f)));
        } else g = c2 & ~e, 0 !== g ? d = tc(g) : 0 !== f && (d = tc(f));
        if (0 === d) return 0;
        if (0 !== b2 && b2 !== d && 0 === (b2 & e) && (e = d & -d, f = b2 & -b2, e >= f || 16 === e && 0 !== (f & 4194240))) return b2;
        0 !== (d & 4) && (d |= c2 & 16);
        b2 = a2.entangledLanes;
        if (0 !== b2) for (a2 = a2.entanglements, b2 &= d; 0 < b2; ) c2 = 31 - oc(b2), e = 1 << c2, d |= a2[c2], b2 &= ~e;
        return d;
      }
      function vc(a2, b2) {
        switch (a2) {
          case 1:
          case 2:
          case 4:
            return b2 + 250;
          case 8:
          case 16:
          case 32:
          case 64:
          case 128:
          case 256:
          case 512:
          case 1024:
          case 2048:
          case 4096:
          case 8192:
          case 16384:
          case 32768:
          case 65536:
          case 131072:
          case 262144:
          case 524288:
          case 1048576:
          case 2097152:
            return b2 + 5e3;
          case 4194304:
          case 8388608:
          case 16777216:
          case 33554432:
          case 67108864:
            return -1;
          case 134217728:
          case 268435456:
          case 536870912:
          case 1073741824:
            return -1;
          default:
            return -1;
        }
      }
      function wc(a2, b2) {
        for (var c2 = a2.suspendedLanes, d = a2.pingedLanes, e = a2.expirationTimes, f = a2.pendingLanes; 0 < f; ) {
          var g = 31 - oc(f), h = 1 << g, k = e[g];
          if (-1 === k) {
            if (0 === (h & c2) || 0 !== (h & d)) e[g] = vc(h, b2);
          } else k <= b2 && (a2.expiredLanes |= h);
          f &= ~h;
        }
      }
      function xc(a2) {
        a2 = a2.pendingLanes & -1073741825;
        return 0 !== a2 ? a2 : a2 & 1073741824 ? 1073741824 : 0;
      }
      function yc() {
        var a2 = rc;
        rc <<= 1;
        0 === (rc & 4194240) && (rc = 64);
        return a2;
      }
      function zc(a2) {
        for (var b2 = [], c2 = 0; 31 > c2; c2++) b2.push(a2);
        return b2;
      }
      function Ac(a2, b2, c2) {
        a2.pendingLanes |= b2;
        536870912 !== b2 && (a2.suspendedLanes = 0, a2.pingedLanes = 0);
        a2 = a2.eventTimes;
        b2 = 31 - oc(b2);
        a2[b2] = c2;
      }
      function Bc(a2, b2) {
        var c2 = a2.pendingLanes & ~b2;
        a2.pendingLanes = b2;
        a2.suspendedLanes = 0;
        a2.pingedLanes = 0;
        a2.expiredLanes &= b2;
        a2.mutableReadLanes &= b2;
        a2.entangledLanes &= b2;
        b2 = a2.entanglements;
        var d = a2.eventTimes;
        for (a2 = a2.expirationTimes; 0 < c2; ) {
          var e = 31 - oc(c2), f = 1 << e;
          b2[e] = 0;
          d[e] = -1;
          a2[e] = -1;
          c2 &= ~f;
        }
      }
      function Cc(a2, b2) {
        var c2 = a2.entangledLanes |= b2;
        for (a2 = a2.entanglements; c2; ) {
          var d = 31 - oc(c2), e = 1 << d;
          e & b2 | a2[d] & b2 && (a2[d] |= b2);
          c2 &= ~e;
        }
      }
      var C = 0;
      function Dc(a2) {
        a2 &= -a2;
        return 1 < a2 ? 4 < a2 ? 0 !== (a2 & 268435455) ? 16 : 536870912 : 4 : 1;
      }
      var Ec;
      var Fc;
      var Gc;
      var Hc;
      var Ic;
      var Jc = false;
      var Kc = [];
      var Lc = null;
      var Mc = null;
      var Nc = null;
      var Oc = /* @__PURE__ */ new Map();
      var Pc = /* @__PURE__ */ new Map();
      var Qc = [];
      var Rc = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");
      function Sc(a2, b2) {
        switch (a2) {
          case "focusin":
          case "focusout":
            Lc = null;
            break;
          case "dragenter":
          case "dragleave":
            Mc = null;
            break;
          case "mouseover":
          case "mouseout":
            Nc = null;
            break;
          case "pointerover":
          case "pointerout":
            Oc.delete(b2.pointerId);
            break;
          case "gotpointercapture":
          case "lostpointercapture":
            Pc.delete(b2.pointerId);
        }
      }
      function Tc(a2, b2, c2, d, e, f) {
        if (null === a2 || a2.nativeEvent !== f) return a2 = { blockedOn: b2, domEventName: c2, eventSystemFlags: d, nativeEvent: f, targetContainers: [e] }, null !== b2 && (b2 = Cb(b2), null !== b2 && Fc(b2)), a2;
        a2.eventSystemFlags |= d;
        b2 = a2.targetContainers;
        null !== e && -1 === b2.indexOf(e) && b2.push(e);
        return a2;
      }
      function Uc(a2, b2, c2, d, e) {
        switch (b2) {
          case "focusin":
            return Lc = Tc(Lc, a2, b2, c2, d, e), true;
          case "dragenter":
            return Mc = Tc(Mc, a2, b2, c2, d, e), true;
          case "mouseover":
            return Nc = Tc(Nc, a2, b2, c2, d, e), true;
          case "pointerover":
            var f = e.pointerId;
            Oc.set(f, Tc(Oc.get(f) || null, a2, b2, c2, d, e));
            return true;
          case "gotpointercapture":
            return f = e.pointerId, Pc.set(f, Tc(Pc.get(f) || null, a2, b2, c2, d, e)), true;
        }
        return false;
      }
      function Vc(a2) {
        var b2 = Wc(a2.target);
        if (null !== b2) {
          var c2 = Vb(b2);
          if (null !== c2) {
            if (b2 = c2.tag, 13 === b2) {
              if (b2 = Wb(c2), null !== b2) {
                a2.blockedOn = b2;
                Ic(a2.priority, function() {
                  Gc(c2);
                });
                return;
              }
            } else if (3 === b2 && c2.stateNode.current.memoizedState.isDehydrated) {
              a2.blockedOn = 3 === c2.tag ? c2.stateNode.containerInfo : null;
              return;
            }
          }
        }
        a2.blockedOn = null;
      }
      function Xc(a2) {
        if (null !== a2.blockedOn) return false;
        for (var b2 = a2.targetContainers; 0 < b2.length; ) {
          var c2 = Yc(a2.domEventName, a2.eventSystemFlags, b2[0], a2.nativeEvent);
          if (null === c2) {
            c2 = a2.nativeEvent;
            var d = new c2.constructor(c2.type, c2);
            wb = d;
            c2.target.dispatchEvent(d);
            wb = null;
          } else return b2 = Cb(c2), null !== b2 && Fc(b2), a2.blockedOn = c2, false;
          b2.shift();
        }
        return true;
      }
      function Zc(a2, b2, c2) {
        Xc(a2) && c2.delete(b2);
      }
      function $c() {
        Jc = false;
        null !== Lc && Xc(Lc) && (Lc = null);
        null !== Mc && Xc(Mc) && (Mc = null);
        null !== Nc && Xc(Nc) && (Nc = null);
        Oc.forEach(Zc);
        Pc.forEach(Zc);
      }
      function ad(a2, b2) {
        a2.blockedOn === b2 && (a2.blockedOn = null, Jc || (Jc = true, ca.unstable_scheduleCallback(ca.unstable_NormalPriority, $c)));
      }
      function bd(a2) {
        function b2(b3) {
          return ad(b3, a2);
        }
        if (0 < Kc.length) {
          ad(Kc[0], a2);
          for (var c2 = 1; c2 < Kc.length; c2++) {
            var d = Kc[c2];
            d.blockedOn === a2 && (d.blockedOn = null);
          }
        }
        null !== Lc && ad(Lc, a2);
        null !== Mc && ad(Mc, a2);
        null !== Nc && ad(Nc, a2);
        Oc.forEach(b2);
        Pc.forEach(b2);
        for (c2 = 0; c2 < Qc.length; c2++) d = Qc[c2], d.blockedOn === a2 && (d.blockedOn = null);
        for (; 0 < Qc.length && (c2 = Qc[0], null === c2.blockedOn); ) Vc(c2), null === c2.blockedOn && Qc.shift();
      }
      var cd = ua.ReactCurrentBatchConfig;
      var dd = true;
      function ed(a2, b2, c2, d) {
        var e = C, f = cd.transition;
        cd.transition = null;
        try {
          C = 1, fd(a2, b2, c2, d);
        } finally {
          C = e, cd.transition = f;
        }
      }
      function gd(a2, b2, c2, d) {
        var e = C, f = cd.transition;
        cd.transition = null;
        try {
          C = 4, fd(a2, b2, c2, d);
        } finally {
          C = e, cd.transition = f;
        }
      }
      function fd(a2, b2, c2, d) {
        if (dd) {
          var e = Yc(a2, b2, c2, d);
          if (null === e) hd(a2, b2, d, id, c2), Sc(a2, d);
          else if (Uc(e, a2, b2, c2, d)) d.stopPropagation();
          else if (Sc(a2, d), b2 & 4 && -1 < Rc.indexOf(a2)) {
            for (; null !== e; ) {
              var f = Cb(e);
              null !== f && Ec(f);
              f = Yc(a2, b2, c2, d);
              null === f && hd(a2, b2, d, id, c2);
              if (f === e) break;
              e = f;
            }
            null !== e && d.stopPropagation();
          } else hd(a2, b2, d, null, c2);
        }
      }
      var id = null;
      function Yc(a2, b2, c2, d) {
        id = null;
        a2 = xb(d);
        a2 = Wc(a2);
        if (null !== a2) if (b2 = Vb(a2), null === b2) a2 = null;
        else if (c2 = b2.tag, 13 === c2) {
          a2 = Wb(b2);
          if (null !== a2) return a2;
          a2 = null;
        } else if (3 === c2) {
          if (b2.stateNode.current.memoizedState.isDehydrated) return 3 === b2.tag ? b2.stateNode.containerInfo : null;
          a2 = null;
        } else b2 !== a2 && (a2 = null);
        id = a2;
        return null;
      }
      function jd(a2) {
        switch (a2) {
          case "cancel":
          case "click":
          case "close":
          case "contextmenu":
          case "copy":
          case "cut":
          case "auxclick":
          case "dblclick":
          case "dragend":
          case "dragstart":
          case "drop":
          case "focusin":
          case "focusout":
          case "input":
          case "invalid":
          case "keydown":
          case "keypress":
          case "keyup":
          case "mousedown":
          case "mouseup":
          case "paste":
          case "pause":
          case "play":
          case "pointercancel":
          case "pointerdown":
          case "pointerup":
          case "ratechange":
          case "reset":
          case "resize":
          case "seeked":
          case "submit":
          case "touchcancel":
          case "touchend":
          case "touchstart":
          case "volumechange":
          case "change":
          case "selectionchange":
          case "textInput":
          case "compositionstart":
          case "compositionend":
          case "compositionupdate":
          case "beforeblur":
          case "afterblur":
          case "beforeinput":
          case "blur":
          case "fullscreenchange":
          case "focus":
          case "hashchange":
          case "popstate":
          case "select":
          case "selectstart":
            return 1;
          case "drag":
          case "dragenter":
          case "dragexit":
          case "dragleave":
          case "dragover":
          case "mousemove":
          case "mouseout":
          case "mouseover":
          case "pointermove":
          case "pointerout":
          case "pointerover":
          case "scroll":
          case "toggle":
          case "touchmove":
          case "wheel":
          case "mouseenter":
          case "mouseleave":
          case "pointerenter":
          case "pointerleave":
            return 4;
          case "message":
            switch (ec()) {
              case fc:
                return 1;
              case gc:
                return 4;
              case hc:
              case ic:
                return 16;
              case jc:
                return 536870912;
              default:
                return 16;
            }
          default:
            return 16;
        }
      }
      var kd = null;
      var ld = null;
      var md = null;
      function nd() {
        if (md) return md;
        var a2, b2 = ld, c2 = b2.length, d, e = "value" in kd ? kd.value : kd.textContent, f = e.length;
        for (a2 = 0; a2 < c2 && b2[a2] === e[a2]; a2++) ;
        var g = c2 - a2;
        for (d = 1; d <= g && b2[c2 - d] === e[f - d]; d++) ;
        return md = e.slice(a2, 1 < d ? 1 - d : void 0);
      }
      function od(a2) {
        var b2 = a2.keyCode;
        "charCode" in a2 ? (a2 = a2.charCode, 0 === a2 && 13 === b2 && (a2 = 13)) : a2 = b2;
        10 === a2 && (a2 = 13);
        return 32 <= a2 || 13 === a2 ? a2 : 0;
      }
      function pd() {
        return true;
      }
      function qd() {
        return false;
      }
      function rd(a2) {
        function b2(b3, d, e, f, g) {
          this._reactName = b3;
          this._targetInst = e;
          this.type = d;
          this.nativeEvent = f;
          this.target = g;
          this.currentTarget = null;
          for (var c2 in a2) a2.hasOwnProperty(c2) && (b3 = a2[c2], this[c2] = b3 ? b3(f) : f[c2]);
          this.isDefaultPrevented = (null != f.defaultPrevented ? f.defaultPrevented : false === f.returnValue) ? pd : qd;
          this.isPropagationStopped = qd;
          return this;
        }
        A(b2.prototype, { preventDefault: function() {
          this.defaultPrevented = true;
          var a3 = this.nativeEvent;
          a3 && (a3.preventDefault ? a3.preventDefault() : "unknown" !== typeof a3.returnValue && (a3.returnValue = false), this.isDefaultPrevented = pd);
        }, stopPropagation: function() {
          var a3 = this.nativeEvent;
          a3 && (a3.stopPropagation ? a3.stopPropagation() : "unknown" !== typeof a3.cancelBubble && (a3.cancelBubble = true), this.isPropagationStopped = pd);
        }, persist: function() {
        }, isPersistent: pd });
        return b2;
      }
      var sd = { eventPhase: 0, bubbles: 0, cancelable: 0, timeStamp: function(a2) {
        return a2.timeStamp || Date.now();
      }, defaultPrevented: 0, isTrusted: 0 };
      var td = rd(sd);
      var ud = A({}, sd, { view: 0, detail: 0 });
      var vd = rd(ud);
      var wd;
      var xd;
      var yd;
      var Ad = A({}, ud, { screenX: 0, screenY: 0, clientX: 0, clientY: 0, pageX: 0, pageY: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, getModifierState: zd, button: 0, buttons: 0, relatedTarget: function(a2) {
        return void 0 === a2.relatedTarget ? a2.fromElement === a2.srcElement ? a2.toElement : a2.fromElement : a2.relatedTarget;
      }, movementX: function(a2) {
        if ("movementX" in a2) return a2.movementX;
        a2 !== yd && (yd && "mousemove" === a2.type ? (wd = a2.screenX - yd.screenX, xd = a2.screenY - yd.screenY) : xd = wd = 0, yd = a2);
        return wd;
      }, movementY: function(a2) {
        return "movementY" in a2 ? a2.movementY : xd;
      } });
      var Bd = rd(Ad);
      var Cd = A({}, Ad, { dataTransfer: 0 });
      var Dd = rd(Cd);
      var Ed = A({}, ud, { relatedTarget: 0 });
      var Fd = rd(Ed);
      var Gd = A({}, sd, { animationName: 0, elapsedTime: 0, pseudoElement: 0 });
      var Hd = rd(Gd);
      var Id = A({}, sd, { clipboardData: function(a2) {
        return "clipboardData" in a2 ? a2.clipboardData : window.clipboardData;
      } });
      var Jd = rd(Id);
      var Kd = A({}, sd, { data: 0 });
      var Ld = rd(Kd);
      var Md = {
        Esc: "Escape",
        Spacebar: " ",
        Left: "ArrowLeft",
        Up: "ArrowUp",
        Right: "ArrowRight",
        Down: "ArrowDown",
        Del: "Delete",
        Win: "OS",
        Menu: "ContextMenu",
        Apps: "ContextMenu",
        Scroll: "ScrollLock",
        MozPrintableKey: "Unidentified"
      };
      var Nd = {
        8: "Backspace",
        9: "Tab",
        12: "Clear",
        13: "Enter",
        16: "Shift",
        17: "Control",
        18: "Alt",
        19: "Pause",
        20: "CapsLock",
        27: "Escape",
        32: " ",
        33: "PageUp",
        34: "PageDown",
        35: "End",
        36: "Home",
        37: "ArrowLeft",
        38: "ArrowUp",
        39: "ArrowRight",
        40: "ArrowDown",
        45: "Insert",
        46: "Delete",
        112: "F1",
        113: "F2",
        114: "F3",
        115: "F4",
        116: "F5",
        117: "F6",
        118: "F7",
        119: "F8",
        120: "F9",
        121: "F10",
        122: "F11",
        123: "F12",
        144: "NumLock",
        145: "ScrollLock",
        224: "Meta"
      };
      var Od = { Alt: "altKey", Control: "ctrlKey", Meta: "metaKey", Shift: "shiftKey" };
      function Pd(a2) {
        var b2 = this.nativeEvent;
        return b2.getModifierState ? b2.getModifierState(a2) : (a2 = Od[a2]) ? !!b2[a2] : false;
      }
      function zd() {
        return Pd;
      }
      var Qd = A({}, ud, { key: function(a2) {
        if (a2.key) {
          var b2 = Md[a2.key] || a2.key;
          if ("Unidentified" !== b2) return b2;
        }
        return "keypress" === a2.type ? (a2 = od(a2), 13 === a2 ? "Enter" : String.fromCharCode(a2)) : "keydown" === a2.type || "keyup" === a2.type ? Nd[a2.keyCode] || "Unidentified" : "";
      }, code: 0, location: 0, ctrlKey: 0, shiftKey: 0, altKey: 0, metaKey: 0, repeat: 0, locale: 0, getModifierState: zd, charCode: function(a2) {
        return "keypress" === a2.type ? od(a2) : 0;
      }, keyCode: function(a2) {
        return "keydown" === a2.type || "keyup" === a2.type ? a2.keyCode : 0;
      }, which: function(a2) {
        return "keypress" === a2.type ? od(a2) : "keydown" === a2.type || "keyup" === a2.type ? a2.keyCode : 0;
      } });
      var Rd = rd(Qd);
      var Sd = A({}, Ad, { pointerId: 0, width: 0, height: 0, pressure: 0, tangentialPressure: 0, tiltX: 0, tiltY: 0, twist: 0, pointerType: 0, isPrimary: 0 });
      var Td = rd(Sd);
      var Ud = A({}, ud, { touches: 0, targetTouches: 0, changedTouches: 0, altKey: 0, metaKey: 0, ctrlKey: 0, shiftKey: 0, getModifierState: zd });
      var Vd = rd(Ud);
      var Wd = A({}, sd, { propertyName: 0, elapsedTime: 0, pseudoElement: 0 });
      var Xd = rd(Wd);
      var Yd = A({}, Ad, {
        deltaX: function(a2) {
          return "deltaX" in a2 ? a2.deltaX : "wheelDeltaX" in a2 ? -a2.wheelDeltaX : 0;
        },
        deltaY: function(a2) {
          return "deltaY" in a2 ? a2.deltaY : "wheelDeltaY" in a2 ? -a2.wheelDeltaY : "wheelDelta" in a2 ? -a2.wheelDelta : 0;
        },
        deltaZ: 0,
        deltaMode: 0
      });
      var Zd = rd(Yd);
      var $d = [9, 13, 27, 32];
      var ae = ia && "CompositionEvent" in window;
      var be = null;
      ia && "documentMode" in document && (be = document.documentMode);
      var ce = ia && "TextEvent" in window && !be;
      var de = ia && (!ae || be && 8 < be && 11 >= be);
      var ee = String.fromCharCode(32);
      var fe = false;
      function ge(a2, b2) {
        switch (a2) {
          case "keyup":
            return -1 !== $d.indexOf(b2.keyCode);
          case "keydown":
            return 229 !== b2.keyCode;
          case "keypress":
          case "mousedown":
          case "focusout":
            return true;
          default:
            return false;
        }
      }
      function he(a2) {
        a2 = a2.detail;
        return "object" === typeof a2 && "data" in a2 ? a2.data : null;
      }
      var ie = false;
      function je(a2, b2) {
        switch (a2) {
          case "compositionend":
            return he(b2);
          case "keypress":
            if (32 !== b2.which) return null;
            fe = true;
            return ee;
          case "textInput":
            return a2 = b2.data, a2 === ee && fe ? null : a2;
          default:
            return null;
        }
      }
      function ke(a2, b2) {
        if (ie) return "compositionend" === a2 || !ae && ge(a2, b2) ? (a2 = nd(), md = ld = kd = null, ie = false, a2) : null;
        switch (a2) {
          case "paste":
            return null;
          case "keypress":
            if (!(b2.ctrlKey || b2.altKey || b2.metaKey) || b2.ctrlKey && b2.altKey) {
              if (b2.char && 1 < b2.char.length) return b2.char;
              if (b2.which) return String.fromCharCode(b2.which);
            }
            return null;
          case "compositionend":
            return de && "ko" !== b2.locale ? null : b2.data;
          default:
            return null;
        }
      }
      var le = { color: true, date: true, datetime: true, "datetime-local": true, email: true, month: true, number: true, password: true, range: true, search: true, tel: true, text: true, time: true, url: true, week: true };
      function me(a2) {
        var b2 = a2 && a2.nodeName && a2.nodeName.toLowerCase();
        return "input" === b2 ? !!le[a2.type] : "textarea" === b2 ? true : false;
      }
      function ne(a2, b2, c2, d) {
        Eb(d);
        b2 = oe(b2, "onChange");
        0 < b2.length && (c2 = new td("onChange", "change", null, c2, d), a2.push({ event: c2, listeners: b2 }));
      }
      var pe = null;
      var qe = null;
      function re(a2) {
        se(a2, 0);
      }
      function te(a2) {
        var b2 = ue(a2);
        if (Wa(b2)) return a2;
      }
      function ve(a2, b2) {
        if ("change" === a2) return b2;
      }
      var we = false;
      if (ia) {
        if (ia) {
          ye = "oninput" in document;
          if (!ye) {
            ze = document.createElement("div");
            ze.setAttribute("oninput", "return;");
            ye = "function" === typeof ze.oninput;
          }
          xe = ye;
        } else xe = false;
        we = xe && (!document.documentMode || 9 < document.documentMode);
      }
      var xe;
      var ye;
      var ze;
      function Ae() {
        pe && (pe.detachEvent("onpropertychange", Be), qe = pe = null);
      }
      function Be(a2) {
        if ("value" === a2.propertyName && te(qe)) {
          var b2 = [];
          ne(b2, qe, a2, xb(a2));
          Jb(re, b2);
        }
      }
      function Ce(a2, b2, c2) {
        "focusin" === a2 ? (Ae(), pe = b2, qe = c2, pe.attachEvent("onpropertychange", Be)) : "focusout" === a2 && Ae();
      }
      function De(a2) {
        if ("selectionchange" === a2 || "keyup" === a2 || "keydown" === a2) return te(qe);
      }
      function Ee(a2, b2) {
        if ("click" === a2) return te(b2);
      }
      function Fe(a2, b2) {
        if ("input" === a2 || "change" === a2) return te(b2);
      }
      function Ge(a2, b2) {
        return a2 === b2 && (0 !== a2 || 1 / a2 === 1 / b2) || a2 !== a2 && b2 !== b2;
      }
      var He = "function" === typeof Object.is ? Object.is : Ge;
      function Ie(a2, b2) {
        if (He(a2, b2)) return true;
        if ("object" !== typeof a2 || null === a2 || "object" !== typeof b2 || null === b2) return false;
        var c2 = Object.keys(a2), d = Object.keys(b2);
        if (c2.length !== d.length) return false;
        for (d = 0; d < c2.length; d++) {
          var e = c2[d];
          if (!ja.call(b2, e) || !He(a2[e], b2[e])) return false;
        }
        return true;
      }
      function Je(a2) {
        for (; a2 && a2.firstChild; ) a2 = a2.firstChild;
        return a2;
      }
      function Ke(a2, b2) {
        var c2 = Je(a2);
        a2 = 0;
        for (var d; c2; ) {
          if (3 === c2.nodeType) {
            d = a2 + c2.textContent.length;
            if (a2 <= b2 && d >= b2) return { node: c2, offset: b2 - a2 };
            a2 = d;
          }
          a: {
            for (; c2; ) {
              if (c2.nextSibling) {
                c2 = c2.nextSibling;
                break a;
              }
              c2 = c2.parentNode;
            }
            c2 = void 0;
          }
          c2 = Je(c2);
        }
      }
      function Le(a2, b2) {
        return a2 && b2 ? a2 === b2 ? true : a2 && 3 === a2.nodeType ? false : b2 && 3 === b2.nodeType ? Le(a2, b2.parentNode) : "contains" in a2 ? a2.contains(b2) : a2.compareDocumentPosition ? !!(a2.compareDocumentPosition(b2) & 16) : false : false;
      }
      function Me() {
        for (var a2 = window, b2 = Xa(); b2 instanceof a2.HTMLIFrameElement; ) {
          try {
            var c2 = "string" === typeof b2.contentWindow.location.href;
          } catch (d) {
            c2 = false;
          }
          if (c2) a2 = b2.contentWindow;
          else break;
          b2 = Xa(a2.document);
        }
        return b2;
      }
      function Ne(a2) {
        var b2 = a2 && a2.nodeName && a2.nodeName.toLowerCase();
        return b2 && ("input" === b2 && ("text" === a2.type || "search" === a2.type || "tel" === a2.type || "url" === a2.type || "password" === a2.type) || "textarea" === b2 || "true" === a2.contentEditable);
      }
      function Oe(a2) {
        var b2 = Me(), c2 = a2.focusedElem, d = a2.selectionRange;
        if (b2 !== c2 && c2 && c2.ownerDocument && Le(c2.ownerDocument.documentElement, c2)) {
          if (null !== d && Ne(c2)) {
            if (b2 = d.start, a2 = d.end, void 0 === a2 && (a2 = b2), "selectionStart" in c2) c2.selectionStart = b2, c2.selectionEnd = Math.min(a2, c2.value.length);
            else if (a2 = (b2 = c2.ownerDocument || document) && b2.defaultView || window, a2.getSelection) {
              a2 = a2.getSelection();
              var e = c2.textContent.length, f = Math.min(d.start, e);
              d = void 0 === d.end ? f : Math.min(d.end, e);
              !a2.extend && f > d && (e = d, d = f, f = e);
              e = Ke(c2, f);
              var g = Ke(
                c2,
                d
              );
              e && g && (1 !== a2.rangeCount || a2.anchorNode !== e.node || a2.anchorOffset !== e.offset || a2.focusNode !== g.node || a2.focusOffset !== g.offset) && (b2 = b2.createRange(), b2.setStart(e.node, e.offset), a2.removeAllRanges(), f > d ? (a2.addRange(b2), a2.extend(g.node, g.offset)) : (b2.setEnd(g.node, g.offset), a2.addRange(b2)));
            }
          }
          b2 = [];
          for (a2 = c2; a2 = a2.parentNode; ) 1 === a2.nodeType && b2.push({ element: a2, left: a2.scrollLeft, top: a2.scrollTop });
          "function" === typeof c2.focus && c2.focus();
          for (c2 = 0; c2 < b2.length; c2++) a2 = b2[c2], a2.element.scrollLeft = a2.left, a2.element.scrollTop = a2.top;
        }
      }
      var Pe = ia && "documentMode" in document && 11 >= document.documentMode;
      var Qe = null;
      var Re = null;
      var Se = null;
      var Te = false;
      function Ue(a2, b2, c2) {
        var d = c2.window === c2 ? c2.document : 9 === c2.nodeType ? c2 : c2.ownerDocument;
        Te || null == Qe || Qe !== Xa(d) || (d = Qe, "selectionStart" in d && Ne(d) ? d = { start: d.selectionStart, end: d.selectionEnd } : (d = (d.ownerDocument && d.ownerDocument.defaultView || window).getSelection(), d = { anchorNode: d.anchorNode, anchorOffset: d.anchorOffset, focusNode: d.focusNode, focusOffset: d.focusOffset }), Se && Ie(Se, d) || (Se = d, d = oe(Re, "onSelect"), 0 < d.length && (b2 = new td("onSelect", "select", null, b2, c2), a2.push({ event: b2, listeners: d }), b2.target = Qe)));
      }
      function Ve(a2, b2) {
        var c2 = {};
        c2[a2.toLowerCase()] = b2.toLowerCase();
        c2["Webkit" + a2] = "webkit" + b2;
        c2["Moz" + a2] = "moz" + b2;
        return c2;
      }
      var We = { animationend: Ve("Animation", "AnimationEnd"), animationiteration: Ve("Animation", "AnimationIteration"), animationstart: Ve("Animation", "AnimationStart"), transitionend: Ve("Transition", "TransitionEnd") };
      var Xe = {};
      var Ye = {};
      ia && (Ye = document.createElement("div").style, "AnimationEvent" in window || (delete We.animationend.animation, delete We.animationiteration.animation, delete We.animationstart.animation), "TransitionEvent" in window || delete We.transitionend.transition);
      function Ze(a2) {
        if (Xe[a2]) return Xe[a2];
        if (!We[a2]) return a2;
        var b2 = We[a2], c2;
        for (c2 in b2) if (b2.hasOwnProperty(c2) && c2 in Ye) return Xe[a2] = b2[c2];
        return a2;
      }
      var $e = Ze("animationend");
      var af = Ze("animationiteration");
      var bf = Ze("animationstart");
      var cf = Ze("transitionend");
      var df = /* @__PURE__ */ new Map();
      var ef = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
      function ff(a2, b2) {
        df.set(a2, b2);
        fa(b2, [a2]);
      }
      for (gf = 0; gf < ef.length; gf++) {
        hf = ef[gf], jf = hf.toLowerCase(), kf = hf[0].toUpperCase() + hf.slice(1);
        ff(jf, "on" + kf);
      }
      var hf;
      var jf;
      var kf;
      var gf;
      ff($e, "onAnimationEnd");
      ff(af, "onAnimationIteration");
      ff(bf, "onAnimationStart");
      ff("dblclick", "onDoubleClick");
      ff("focusin", "onFocus");
      ff("focusout", "onBlur");
      ff(cf, "onTransitionEnd");
      ha("onMouseEnter", ["mouseout", "mouseover"]);
      ha("onMouseLeave", ["mouseout", "mouseover"]);
      ha("onPointerEnter", ["pointerout", "pointerover"]);
      ha("onPointerLeave", ["pointerout", "pointerover"]);
      fa("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" "));
      fa("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" "));
      fa("onBeforeInput", ["compositionend", "keypress", "textInput", "paste"]);
      fa("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" "));
      fa("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" "));
      fa("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
      var lf = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" ");
      var mf = new Set("cancel close invalid load scroll toggle".split(" ").concat(lf));
      function nf(a2, b2, c2) {
        var d = a2.type || "unknown-event";
        a2.currentTarget = c2;
        Ub(d, b2, void 0, a2);
        a2.currentTarget = null;
      }
      function se(a2, b2) {
        b2 = 0 !== (b2 & 4);
        for (var c2 = 0; c2 < a2.length; c2++) {
          var d = a2[c2], e = d.event;
          d = d.listeners;
          a: {
            var f = void 0;
            if (b2) for (var g = d.length - 1; 0 <= g; g--) {
              var h = d[g], k = h.instance, l = h.currentTarget;
              h = h.listener;
              if (k !== f && e.isPropagationStopped()) break a;
              nf(e, h, l);
              f = k;
            }
            else for (g = 0; g < d.length; g++) {
              h = d[g];
              k = h.instance;
              l = h.currentTarget;
              h = h.listener;
              if (k !== f && e.isPropagationStopped()) break a;
              nf(e, h, l);
              f = k;
            }
          }
        }
        if (Qb) throw a2 = Rb, Qb = false, Rb = null, a2;
      }
      function D(a2, b2) {
        var c2 = b2[of];
        void 0 === c2 && (c2 = b2[of] = /* @__PURE__ */ new Set());
        var d = a2 + "__bubble";
        c2.has(d) || (pf(b2, a2, 2, false), c2.add(d));
      }
      function qf(a2, b2, c2) {
        var d = 0;
        b2 && (d |= 4);
        pf(c2, a2, d, b2);
      }
      var rf = "_reactListening" + Math.random().toString(36).slice(2);
      function sf(a2) {
        if (!a2[rf]) {
          a2[rf] = true;
          da.forEach(function(b3) {
            "selectionchange" !== b3 && (mf.has(b3) || qf(b3, false, a2), qf(b3, true, a2));
          });
          var b2 = 9 === a2.nodeType ? a2 : a2.ownerDocument;
          null === b2 || b2[rf] || (b2[rf] = true, qf("selectionchange", false, b2));
        }
      }
      function pf(a2, b2, c2, d) {
        switch (jd(b2)) {
          case 1:
            var e = ed;
            break;
          case 4:
            e = gd;
            break;
          default:
            e = fd;
        }
        c2 = e.bind(null, b2, c2, a2);
        e = void 0;
        !Lb || "touchstart" !== b2 && "touchmove" !== b2 && "wheel" !== b2 || (e = true);
        d ? void 0 !== e ? a2.addEventListener(b2, c2, { capture: true, passive: e }) : a2.addEventListener(b2, c2, true) : void 0 !== e ? a2.addEventListener(b2, c2, { passive: e }) : a2.addEventListener(b2, c2, false);
      }
      function hd(a2, b2, c2, d, e) {
        var f = d;
        if (0 === (b2 & 1) && 0 === (b2 & 2) && null !== d) a: for (; ; ) {
          if (null === d) return;
          var g = d.tag;
          if (3 === g || 4 === g) {
            var h = d.stateNode.containerInfo;
            if (h === e || 8 === h.nodeType && h.parentNode === e) break;
            if (4 === g) for (g = d.return; null !== g; ) {
              var k = g.tag;
              if (3 === k || 4 === k) {
                if (k = g.stateNode.containerInfo, k === e || 8 === k.nodeType && k.parentNode === e) return;
              }
              g = g.return;
            }
            for (; null !== h; ) {
              g = Wc(h);
              if (null === g) return;
              k = g.tag;
              if (5 === k || 6 === k) {
                d = f = g;
                continue a;
              }
              h = h.parentNode;
            }
          }
          d = d.return;
        }
        Jb(function() {
          var d2 = f, e2 = xb(c2), g2 = [];
          a: {
            var h2 = df.get(a2);
            if (void 0 !== h2) {
              var k2 = td, n = a2;
              switch (a2) {
                case "keypress":
                  if (0 === od(c2)) break a;
                case "keydown":
                case "keyup":
                  k2 = Rd;
                  break;
                case "focusin":
                  n = "focus";
                  k2 = Fd;
                  break;
                case "focusout":
                  n = "blur";
                  k2 = Fd;
                  break;
                case "beforeblur":
                case "afterblur":
                  k2 = Fd;
                  break;
                case "click":
                  if (2 === c2.button) break a;
                case "auxclick":
                case "dblclick":
                case "mousedown":
                case "mousemove":
                case "mouseup":
                case "mouseout":
                case "mouseover":
                case "contextmenu":
                  k2 = Bd;
                  break;
                case "drag":
                case "dragend":
                case "dragenter":
                case "dragexit":
                case "dragleave":
                case "dragover":
                case "dragstart":
                case "drop":
                  k2 = Dd;
                  break;
                case "touchcancel":
                case "touchend":
                case "touchmove":
                case "touchstart":
                  k2 = Vd;
                  break;
                case $e:
                case af:
                case bf:
                  k2 = Hd;
                  break;
                case cf:
                  k2 = Xd;
                  break;
                case "scroll":
                  k2 = vd;
                  break;
                case "wheel":
                  k2 = Zd;
                  break;
                case "copy":
                case "cut":
                case "paste":
                  k2 = Jd;
                  break;
                case "gotpointercapture":
                case "lostpointercapture":
                case "pointercancel":
                case "pointerdown":
                case "pointermove":
                case "pointerout":
                case "pointerover":
                case "pointerup":
                  k2 = Td;
              }
              var t = 0 !== (b2 & 4), J = !t && "scroll" === a2, x = t ? null !== h2 ? h2 + "Capture" : null : h2;
              t = [];
              for (var w = d2, u; null !== w; ) {
                u = w;
                var F = u.stateNode;
                5 === u.tag && null !== F && (u = F, null !== x && (F = Kb(w, x), null != F && t.push(tf(w, F, u))));
                if (J) break;
                w = w.return;
              }
              0 < t.length && (h2 = new k2(h2, n, null, c2, e2), g2.push({ event: h2, listeners: t }));
            }
          }
          if (0 === (b2 & 7)) {
            a: {
              h2 = "mouseover" === a2 || "pointerover" === a2;
              k2 = "mouseout" === a2 || "pointerout" === a2;
              if (h2 && c2 !== wb && (n = c2.relatedTarget || c2.fromElement) && (Wc(n) || n[uf])) break a;
              if (k2 || h2) {
                h2 = e2.window === e2 ? e2 : (h2 = e2.ownerDocument) ? h2.defaultView || h2.parentWindow : window;
                if (k2) {
                  if (n = c2.relatedTarget || c2.toElement, k2 = d2, n = n ? Wc(n) : null, null !== n && (J = Vb(n), n !== J || 5 !== n.tag && 6 !== n.tag)) n = null;
                } else k2 = null, n = d2;
                if (k2 !== n) {
                  t = Bd;
                  F = "onMouseLeave";
                  x = "onMouseEnter";
                  w = "mouse";
                  if ("pointerout" === a2 || "pointerover" === a2) t = Td, F = "onPointerLeave", x = "onPointerEnter", w = "pointer";
                  J = null == k2 ? h2 : ue(k2);
                  u = null == n ? h2 : ue(n);
                  h2 = new t(F, w + "leave", k2, c2, e2);
                  h2.target = J;
                  h2.relatedTarget = u;
                  F = null;
                  Wc(e2) === d2 && (t = new t(x, w + "enter", n, c2, e2), t.target = u, t.relatedTarget = J, F = t);
                  J = F;
                  if (k2 && n) b: {
                    t = k2;
                    x = n;
                    w = 0;
                    for (u = t; u; u = vf(u)) w++;
                    u = 0;
                    for (F = x; F; F = vf(F)) u++;
                    for (; 0 < w - u; ) t = vf(t), w--;
                    for (; 0 < u - w; ) x = vf(x), u--;
                    for (; w--; ) {
                      if (t === x || null !== x && t === x.alternate) break b;
                      t = vf(t);
                      x = vf(x);
                    }
                    t = null;
                  }
                  else t = null;
                  null !== k2 && wf(g2, h2, k2, t, false);
                  null !== n && null !== J && wf(g2, J, n, t, true);
                }
              }
            }
            a: {
              h2 = d2 ? ue(d2) : window;
              k2 = h2.nodeName && h2.nodeName.toLowerCase();
              if ("select" === k2 || "input" === k2 && "file" === h2.type) var na = ve;
              else if (me(h2)) if (we) na = Fe;
              else {
                na = De;
                var xa = Ce;
              }
              else (k2 = h2.nodeName) && "input" === k2.toLowerCase() && ("checkbox" === h2.type || "radio" === h2.type) && (na = Ee);
              if (na && (na = na(a2, d2))) {
                ne(g2, na, c2, e2);
                break a;
              }
              xa && xa(a2, h2, d2);
              "focusout" === a2 && (xa = h2._wrapperState) && xa.controlled && "number" === h2.type && cb(h2, "number", h2.value);
            }
            xa = d2 ? ue(d2) : window;
            switch (a2) {
              case "focusin":
                if (me(xa) || "true" === xa.contentEditable) Qe = xa, Re = d2, Se = null;
                break;
              case "focusout":
                Se = Re = Qe = null;
                break;
              case "mousedown":
                Te = true;
                break;
              case "contextmenu":
              case "mouseup":
              case "dragend":
                Te = false;
                Ue(g2, c2, e2);
                break;
              case "selectionchange":
                if (Pe) break;
              case "keydown":
              case "keyup":
                Ue(g2, c2, e2);
            }
            var $a;
            if (ae) b: {
              switch (a2) {
                case "compositionstart":
                  var ba = "onCompositionStart";
                  break b;
                case "compositionend":
                  ba = "onCompositionEnd";
                  break b;
                case "compositionupdate":
                  ba = "onCompositionUpdate";
                  break b;
              }
              ba = void 0;
            }
            else ie ? ge(a2, c2) && (ba = "onCompositionEnd") : "keydown" === a2 && 229 === c2.keyCode && (ba = "onCompositionStart");
            ba && (de && "ko" !== c2.locale && (ie || "onCompositionStart" !== ba ? "onCompositionEnd" === ba && ie && ($a = nd()) : (kd = e2, ld = "value" in kd ? kd.value : kd.textContent, ie = true)), xa = oe(d2, ba), 0 < xa.length && (ba = new Ld(ba, a2, null, c2, e2), g2.push({ event: ba, listeners: xa }), $a ? ba.data = $a : ($a = he(c2), null !== $a && (ba.data = $a))));
            if ($a = ce ? je(a2, c2) : ke(a2, c2)) d2 = oe(d2, "onBeforeInput"), 0 < d2.length && (e2 = new Ld("onBeforeInput", "beforeinput", null, c2, e2), g2.push({ event: e2, listeners: d2 }), e2.data = $a);
          }
          se(g2, b2);
        });
      }
      function tf(a2, b2, c2) {
        return { instance: a2, listener: b2, currentTarget: c2 };
      }
      function oe(a2, b2) {
        for (var c2 = b2 + "Capture", d = []; null !== a2; ) {
          var e = a2, f = e.stateNode;
          5 === e.tag && null !== f && (e = f, f = Kb(a2, c2), null != f && d.unshift(tf(a2, f, e)), f = Kb(a2, b2), null != f && d.push(tf(a2, f, e)));
          a2 = a2.return;
        }
        return d;
      }
      function vf(a2) {
        if (null === a2) return null;
        do
          a2 = a2.return;
        while (a2 && 5 !== a2.tag);
        return a2 ? a2 : null;
      }
      function wf(a2, b2, c2, d, e) {
        for (var f = b2._reactName, g = []; null !== c2 && c2 !== d; ) {
          var h = c2, k = h.alternate, l = h.stateNode;
          if (null !== k && k === d) break;
          5 === h.tag && null !== l && (h = l, e ? (k = Kb(c2, f), null != k && g.unshift(tf(c2, k, h))) : e || (k = Kb(c2, f), null != k && g.push(tf(c2, k, h))));
          c2 = c2.return;
        }
        0 !== g.length && a2.push({ event: b2, listeners: g });
      }
      var xf = /\r\n?/g;
      var yf = /\u0000|\uFFFD/g;
      function zf(a2) {
        return ("string" === typeof a2 ? a2 : "" + a2).replace(xf, "\n").replace(yf, "");
      }
      function Af(a2, b2, c2) {
        b2 = zf(b2);
        if (zf(a2) !== b2 && c2) throw Error(p(425));
      }
      function Bf() {
      }
      var Cf = null;
      var Df = null;
      function Ef(a2, b2) {
        return "textarea" === a2 || "noscript" === a2 || "string" === typeof b2.children || "number" === typeof b2.children || "object" === typeof b2.dangerouslySetInnerHTML && null !== b2.dangerouslySetInnerHTML && null != b2.dangerouslySetInnerHTML.__html;
      }
      var Ff = "function" === typeof setTimeout ? setTimeout : void 0;
      var Gf = "function" === typeof clearTimeout ? clearTimeout : void 0;
      var Hf = "function" === typeof Promise ? Promise : void 0;
      var Jf = "function" === typeof queueMicrotask ? queueMicrotask : "undefined" !== typeof Hf ? function(a2) {
        return Hf.resolve(null).then(a2).catch(If);
      } : Ff;
      function If(a2) {
        setTimeout(function() {
          throw a2;
        });
      }
      function Kf(a2, b2) {
        var c2 = b2, d = 0;
        do {
          var e = c2.nextSibling;
          a2.removeChild(c2);
          if (e && 8 === e.nodeType) if (c2 = e.data, "/$" === c2) {
            if (0 === d) {
              a2.removeChild(e);
              bd(b2);
              return;
            }
            d--;
          } else "$" !== c2 && "$?" !== c2 && "$!" !== c2 || d++;
          c2 = e;
        } while (c2);
        bd(b2);
      }
      function Lf(a2) {
        for (; null != a2; a2 = a2.nextSibling) {
          var b2 = a2.nodeType;
          if (1 === b2 || 3 === b2) break;
          if (8 === b2) {
            b2 = a2.data;
            if ("$" === b2 || "$!" === b2 || "$?" === b2) break;
            if ("/$" === b2) return null;
          }
        }
        return a2;
      }
      function Mf(a2) {
        a2 = a2.previousSibling;
        for (var b2 = 0; a2; ) {
          if (8 === a2.nodeType) {
            var c2 = a2.data;
            if ("$" === c2 || "$!" === c2 || "$?" === c2) {
              if (0 === b2) return a2;
              b2--;
            } else "/$" === c2 && b2++;
          }
          a2 = a2.previousSibling;
        }
        return null;
      }
      var Nf = Math.random().toString(36).slice(2);
      var Of = "__reactFiber$" + Nf;
      var Pf = "__reactProps$" + Nf;
      var uf = "__reactContainer$" + Nf;
      var of = "__reactEvents$" + Nf;
      var Qf = "__reactListeners$" + Nf;
      var Rf = "__reactHandles$" + Nf;
      function Wc(a2) {
        var b2 = a2[Of];
        if (b2) return b2;
        for (var c2 = a2.parentNode; c2; ) {
          if (b2 = c2[uf] || c2[Of]) {
            c2 = b2.alternate;
            if (null !== b2.child || null !== c2 && null !== c2.child) for (a2 = Mf(a2); null !== a2; ) {
              if (c2 = a2[Of]) return c2;
              a2 = Mf(a2);
            }
            return b2;
          }
          a2 = c2;
          c2 = a2.parentNode;
        }
        return null;
      }
      function Cb(a2) {
        a2 = a2[Of] || a2[uf];
        return !a2 || 5 !== a2.tag && 6 !== a2.tag && 13 !== a2.tag && 3 !== a2.tag ? null : a2;
      }
      function ue(a2) {
        if (5 === a2.tag || 6 === a2.tag) return a2.stateNode;
        throw Error(p(33));
      }
      function Db(a2) {
        return a2[Pf] || null;
      }
      var Sf = [];
      var Tf = -1;
      function Uf(a2) {
        return { current: a2 };
      }
      function E(a2) {
        0 > Tf || (a2.current = Sf[Tf], Sf[Tf] = null, Tf--);
      }
      function G(a2, b2) {
        Tf++;
        Sf[Tf] = a2.current;
        a2.current = b2;
      }
      var Vf = {};
      var H = Uf(Vf);
      var Wf = Uf(false);
      var Xf = Vf;
      function Yf(a2, b2) {
        var c2 = a2.type.contextTypes;
        if (!c2) return Vf;
        var d = a2.stateNode;
        if (d && d.__reactInternalMemoizedUnmaskedChildContext === b2) return d.__reactInternalMemoizedMaskedChildContext;
        var e = {}, f;
        for (f in c2) e[f] = b2[f];
        d && (a2 = a2.stateNode, a2.__reactInternalMemoizedUnmaskedChildContext = b2, a2.__reactInternalMemoizedMaskedChildContext = e);
        return e;
      }
      function Zf(a2) {
        a2 = a2.childContextTypes;
        return null !== a2 && void 0 !== a2;
      }
      function $f() {
        E(Wf);
        E(H);
      }
      function ag(a2, b2, c2) {
        if (H.current !== Vf) throw Error(p(168));
        G(H, b2);
        G(Wf, c2);
      }
      function bg(a2, b2, c2) {
        var d = a2.stateNode;
        b2 = b2.childContextTypes;
        if ("function" !== typeof d.getChildContext) return c2;
        d = d.getChildContext();
        for (var e in d) if (!(e in b2)) throw Error(p(108, Ra(a2) || "Unknown", e));
        return A({}, c2, d);
      }
      function cg(a2) {
        a2 = (a2 = a2.stateNode) && a2.__reactInternalMemoizedMergedChildContext || Vf;
        Xf = H.current;
        G(H, a2);
        G(Wf, Wf.current);
        return true;
      }
      function dg(a2, b2, c2) {
        var d = a2.stateNode;
        if (!d) throw Error(p(169));
        c2 ? (a2 = bg(a2, b2, Xf), d.__reactInternalMemoizedMergedChildContext = a2, E(Wf), E(H), G(H, a2)) : E(Wf);
        G(Wf, c2);
      }
      var eg = null;
      var fg = false;
      var gg = false;
      function hg(a2) {
        null === eg ? eg = [a2] : eg.push(a2);
      }
      function ig(a2) {
        fg = true;
        hg(a2);
      }
      function jg() {
        if (!gg && null !== eg) {
          gg = true;
          var a2 = 0, b2 = C;
          try {
            var c2 = eg;
            for (C = 1; a2 < c2.length; a2++) {
              var d = c2[a2];
              do
                d = d(true);
              while (null !== d);
            }
            eg = null;
            fg = false;
          } catch (e) {
            throw null !== eg && (eg = eg.slice(a2 + 1)), ac(fc, jg), e;
          } finally {
            C = b2, gg = false;
          }
        }
        return null;
      }
      var kg = [];
      var lg = 0;
      var mg = null;
      var ng = 0;
      var og = [];
      var pg = 0;
      var qg = null;
      var rg = 1;
      var sg = "";
      function tg(a2, b2) {
        kg[lg++] = ng;
        kg[lg++] = mg;
        mg = a2;
        ng = b2;
      }
      function ug(a2, b2, c2) {
        og[pg++] = rg;
        og[pg++] = sg;
        og[pg++] = qg;
        qg = a2;
        var d = rg;
        a2 = sg;
        var e = 32 - oc(d) - 1;
        d &= ~(1 << e);
        c2 += 1;
        var f = 32 - oc(b2) + e;
        if (30 < f) {
          var g = e - e % 5;
          f = (d & (1 << g) - 1).toString(32);
          d >>= g;
          e -= g;
          rg = 1 << 32 - oc(b2) + e | c2 << e | d;
          sg = f + a2;
        } else rg = 1 << f | c2 << e | d, sg = a2;
      }
      function vg(a2) {
        null !== a2.return && (tg(a2, 1), ug(a2, 1, 0));
      }
      function wg(a2) {
        for (; a2 === mg; ) mg = kg[--lg], kg[lg] = null, ng = kg[--lg], kg[lg] = null;
        for (; a2 === qg; ) qg = og[--pg], og[pg] = null, sg = og[--pg], og[pg] = null, rg = og[--pg], og[pg] = null;
      }
      var xg = null;
      var yg = null;
      var I = false;
      var zg = null;
      function Ag(a2, b2) {
        var c2 = Bg(5, null, null, 0);
        c2.elementType = "DELETED";
        c2.stateNode = b2;
        c2.return = a2;
        b2 = a2.deletions;
        null === b2 ? (a2.deletions = [c2], a2.flags |= 16) : b2.push(c2);
      }
      function Cg(a2, b2) {
        switch (a2.tag) {
          case 5:
            var c2 = a2.type;
            b2 = 1 !== b2.nodeType || c2.toLowerCase() !== b2.nodeName.toLowerCase() ? null : b2;
            return null !== b2 ? (a2.stateNode = b2, xg = a2, yg = Lf(b2.firstChild), true) : false;
          case 6:
            return b2 = "" === a2.pendingProps || 3 !== b2.nodeType ? null : b2, null !== b2 ? (a2.stateNode = b2, xg = a2, yg = null, true) : false;
          case 13:
            return b2 = 8 !== b2.nodeType ? null : b2, null !== b2 ? (c2 = null !== qg ? { id: rg, overflow: sg } : null, a2.memoizedState = { dehydrated: b2, treeContext: c2, retryLane: 1073741824 }, c2 = Bg(18, null, null, 0), c2.stateNode = b2, c2.return = a2, a2.child = c2, xg = a2, yg = null, true) : false;
          default:
            return false;
        }
      }
      function Dg(a2) {
        return 0 !== (a2.mode & 1) && 0 === (a2.flags & 128);
      }
      function Eg(a2) {
        if (I) {
          var b2 = yg;
          if (b2) {
            var c2 = b2;
            if (!Cg(a2, b2)) {
              if (Dg(a2)) throw Error(p(418));
              b2 = Lf(c2.nextSibling);
              var d = xg;
              b2 && Cg(a2, b2) ? Ag(d, c2) : (a2.flags = a2.flags & -4097 | 2, I = false, xg = a2);
            }
          } else {
            if (Dg(a2)) throw Error(p(418));
            a2.flags = a2.flags & -4097 | 2;
            I = false;
            xg = a2;
          }
        }
      }
      function Fg(a2) {
        for (a2 = a2.return; null !== a2 && 5 !== a2.tag && 3 !== a2.tag && 13 !== a2.tag; ) a2 = a2.return;
        xg = a2;
      }
      function Gg(a2) {
        if (a2 !== xg) return false;
        if (!I) return Fg(a2), I = true, false;
        var b2;
        (b2 = 3 !== a2.tag) && !(b2 = 5 !== a2.tag) && (b2 = a2.type, b2 = "head" !== b2 && "body" !== b2 && !Ef(a2.type, a2.memoizedProps));
        if (b2 && (b2 = yg)) {
          if (Dg(a2)) throw Hg(), Error(p(418));
          for (; b2; ) Ag(a2, b2), b2 = Lf(b2.nextSibling);
        }
        Fg(a2);
        if (13 === a2.tag) {
          a2 = a2.memoizedState;
          a2 = null !== a2 ? a2.dehydrated : null;
          if (!a2) throw Error(p(317));
          a: {
            a2 = a2.nextSibling;
            for (b2 = 0; a2; ) {
              if (8 === a2.nodeType) {
                var c2 = a2.data;
                if ("/$" === c2) {
                  if (0 === b2) {
                    yg = Lf(a2.nextSibling);
                    break a;
                  }
                  b2--;
                } else "$" !== c2 && "$!" !== c2 && "$?" !== c2 || b2++;
              }
              a2 = a2.nextSibling;
            }
            yg = null;
          }
        } else yg = xg ? Lf(a2.stateNode.nextSibling) : null;
        return true;
      }
      function Hg() {
        for (var a2 = yg; a2; ) a2 = Lf(a2.nextSibling);
      }
      function Ig() {
        yg = xg = null;
        I = false;
      }
      function Jg(a2) {
        null === zg ? zg = [a2] : zg.push(a2);
      }
      var Kg = ua.ReactCurrentBatchConfig;
      function Lg(a2, b2, c2) {
        a2 = c2.ref;
        if (null !== a2 && "function" !== typeof a2 && "object" !== typeof a2) {
          if (c2._owner) {
            c2 = c2._owner;
            if (c2) {
              if (1 !== c2.tag) throw Error(p(309));
              var d = c2.stateNode;
            }
            if (!d) throw Error(p(147, a2));
            var e = d, f = "" + a2;
            if (null !== b2 && null !== b2.ref && "function" === typeof b2.ref && b2.ref._stringRef === f) return b2.ref;
            b2 = function(a3) {
              var b3 = e.refs;
              null === a3 ? delete b3[f] : b3[f] = a3;
            };
            b2._stringRef = f;
            return b2;
          }
          if ("string" !== typeof a2) throw Error(p(284));
          if (!c2._owner) throw Error(p(290, a2));
        }
        return a2;
      }
      function Mg(a2, b2) {
        a2 = Object.prototype.toString.call(b2);
        throw Error(p(31, "[object Object]" === a2 ? "object with keys {" + Object.keys(b2).join(", ") + "}" : a2));
      }
      function Ng(a2) {
        var b2 = a2._init;
        return b2(a2._payload);
      }
      function Og(a2) {
        function b2(b3, c3) {
          if (a2) {
            var d2 = b3.deletions;
            null === d2 ? (b3.deletions = [c3], b3.flags |= 16) : d2.push(c3);
          }
        }
        function c2(c3, d2) {
          if (!a2) return null;
          for (; null !== d2; ) b2(c3, d2), d2 = d2.sibling;
          return null;
        }
        function d(a3, b3) {
          for (a3 = /* @__PURE__ */ new Map(); null !== b3; ) null !== b3.key ? a3.set(b3.key, b3) : a3.set(b3.index, b3), b3 = b3.sibling;
          return a3;
        }
        function e(a3, b3) {
          a3 = Pg(a3, b3);
          a3.index = 0;
          a3.sibling = null;
          return a3;
        }
        function f(b3, c3, d2) {
          b3.index = d2;
          if (!a2) return b3.flags |= 1048576, c3;
          d2 = b3.alternate;
          if (null !== d2) return d2 = d2.index, d2 < c3 ? (b3.flags |= 2, c3) : d2;
          b3.flags |= 2;
          return c3;
        }
        function g(b3) {
          a2 && null === b3.alternate && (b3.flags |= 2);
          return b3;
        }
        function h(a3, b3, c3, d2) {
          if (null === b3 || 6 !== b3.tag) return b3 = Qg(c3, a3.mode, d2), b3.return = a3, b3;
          b3 = e(b3, c3);
          b3.return = a3;
          return b3;
        }
        function k(a3, b3, c3, d2) {
          var f2 = c3.type;
          if (f2 === ya) return m(a3, b3, c3.props.children, d2, c3.key);
          if (null !== b3 && (b3.elementType === f2 || "object" === typeof f2 && null !== f2 && f2.$$typeof === Ha && Ng(f2) === b3.type)) return d2 = e(b3, c3.props), d2.ref = Lg(a3, b3, c3), d2.return = a3, d2;
          d2 = Rg(c3.type, c3.key, c3.props, null, a3.mode, d2);
          d2.ref = Lg(a3, b3, c3);
          d2.return = a3;
          return d2;
        }
        function l(a3, b3, c3, d2) {
          if (null === b3 || 4 !== b3.tag || b3.stateNode.containerInfo !== c3.containerInfo || b3.stateNode.implementation !== c3.implementation) return b3 = Sg(c3, a3.mode, d2), b3.return = a3, b3;
          b3 = e(b3, c3.children || []);
          b3.return = a3;
          return b3;
        }
        function m(a3, b3, c3, d2, f2) {
          if (null === b3 || 7 !== b3.tag) return b3 = Tg(c3, a3.mode, d2, f2), b3.return = a3, b3;
          b3 = e(b3, c3);
          b3.return = a3;
          return b3;
        }
        function q(a3, b3, c3) {
          if ("string" === typeof b3 && "" !== b3 || "number" === typeof b3) return b3 = Qg("" + b3, a3.mode, c3), b3.return = a3, b3;
          if ("object" === typeof b3 && null !== b3) {
            switch (b3.$$typeof) {
              case va:
                return c3 = Rg(b3.type, b3.key, b3.props, null, a3.mode, c3), c3.ref = Lg(a3, null, b3), c3.return = a3, c3;
              case wa:
                return b3 = Sg(b3, a3.mode, c3), b3.return = a3, b3;
              case Ha:
                var d2 = b3._init;
                return q(a3, d2(b3._payload), c3);
            }
            if (eb(b3) || Ka(b3)) return b3 = Tg(b3, a3.mode, c3, null), b3.return = a3, b3;
            Mg(a3, b3);
          }
          return null;
        }
        function r(a3, b3, c3, d2) {
          var e2 = null !== b3 ? b3.key : null;
          if ("string" === typeof c3 && "" !== c3 || "number" === typeof c3) return null !== e2 ? null : h(a3, b3, "" + c3, d2);
          if ("object" === typeof c3 && null !== c3) {
            switch (c3.$$typeof) {
              case va:
                return c3.key === e2 ? k(a3, b3, c3, d2) : null;
              case wa:
                return c3.key === e2 ? l(a3, b3, c3, d2) : null;
              case Ha:
                return e2 = c3._init, r(
                  a3,
                  b3,
                  e2(c3._payload),
                  d2
                );
            }
            if (eb(c3) || Ka(c3)) return null !== e2 ? null : m(a3, b3, c3, d2, null);
            Mg(a3, c3);
          }
          return null;
        }
        function y(a3, b3, c3, d2, e2) {
          if ("string" === typeof d2 && "" !== d2 || "number" === typeof d2) return a3 = a3.get(c3) || null, h(b3, a3, "" + d2, e2);
          if ("object" === typeof d2 && null !== d2) {
            switch (d2.$$typeof) {
              case va:
                return a3 = a3.get(null === d2.key ? c3 : d2.key) || null, k(b3, a3, d2, e2);
              case wa:
                return a3 = a3.get(null === d2.key ? c3 : d2.key) || null, l(b3, a3, d2, e2);
              case Ha:
                var f2 = d2._init;
                return y(a3, b3, c3, f2(d2._payload), e2);
            }
            if (eb(d2) || Ka(d2)) return a3 = a3.get(c3) || null, m(b3, a3, d2, e2, null);
            Mg(b3, d2);
          }
          return null;
        }
        function n(e2, g2, h2, k2) {
          for (var l2 = null, m2 = null, u = g2, w = g2 = 0, x = null; null !== u && w < h2.length; w++) {
            u.index > w ? (x = u, u = null) : x = u.sibling;
            var n2 = r(e2, u, h2[w], k2);
            if (null === n2) {
              null === u && (u = x);
              break;
            }
            a2 && u && null === n2.alternate && b2(e2, u);
            g2 = f(n2, g2, w);
            null === m2 ? l2 = n2 : m2.sibling = n2;
            m2 = n2;
            u = x;
          }
          if (w === h2.length) return c2(e2, u), I && tg(e2, w), l2;
          if (null === u) {
            for (; w < h2.length; w++) u = q(e2, h2[w], k2), null !== u && (g2 = f(u, g2, w), null === m2 ? l2 = u : m2.sibling = u, m2 = u);
            I && tg(e2, w);
            return l2;
          }
          for (u = d(e2, u); w < h2.length; w++) x = y(u, e2, w, h2[w], k2), null !== x && (a2 && null !== x.alternate && u.delete(null === x.key ? w : x.key), g2 = f(x, g2, w), null === m2 ? l2 = x : m2.sibling = x, m2 = x);
          a2 && u.forEach(function(a3) {
            return b2(e2, a3);
          });
          I && tg(e2, w);
          return l2;
        }
        function t(e2, g2, h2, k2) {
          var l2 = Ka(h2);
          if ("function" !== typeof l2) throw Error(p(150));
          h2 = l2.call(h2);
          if (null == h2) throw Error(p(151));
          for (var u = l2 = null, m2 = g2, w = g2 = 0, x = null, n2 = h2.next(); null !== m2 && !n2.done; w++, n2 = h2.next()) {
            m2.index > w ? (x = m2, m2 = null) : x = m2.sibling;
            var t2 = r(e2, m2, n2.value, k2);
            if (null === t2) {
              null === m2 && (m2 = x);
              break;
            }
            a2 && m2 && null === t2.alternate && b2(e2, m2);
            g2 = f(t2, g2, w);
            null === u ? l2 = t2 : u.sibling = t2;
            u = t2;
            m2 = x;
          }
          if (n2.done) return c2(
            e2,
            m2
          ), I && tg(e2, w), l2;
          if (null === m2) {
            for (; !n2.done; w++, n2 = h2.next()) n2 = q(e2, n2.value, k2), null !== n2 && (g2 = f(n2, g2, w), null === u ? l2 = n2 : u.sibling = n2, u = n2);
            I && tg(e2, w);
            return l2;
          }
          for (m2 = d(e2, m2); !n2.done; w++, n2 = h2.next()) n2 = y(m2, e2, w, n2.value, k2), null !== n2 && (a2 && null !== n2.alternate && m2.delete(null === n2.key ? w : n2.key), g2 = f(n2, g2, w), null === u ? l2 = n2 : u.sibling = n2, u = n2);
          a2 && m2.forEach(function(a3) {
            return b2(e2, a3);
          });
          I && tg(e2, w);
          return l2;
        }
        function J(a3, d2, f2, h2) {
          "object" === typeof f2 && null !== f2 && f2.type === ya && null === f2.key && (f2 = f2.props.children);
          if ("object" === typeof f2 && null !== f2) {
            switch (f2.$$typeof) {
              case va:
                a: {
                  for (var k2 = f2.key, l2 = d2; null !== l2; ) {
                    if (l2.key === k2) {
                      k2 = f2.type;
                      if (k2 === ya) {
                        if (7 === l2.tag) {
                          c2(a3, l2.sibling);
                          d2 = e(l2, f2.props.children);
                          d2.return = a3;
                          a3 = d2;
                          break a;
                        }
                      } else if (l2.elementType === k2 || "object" === typeof k2 && null !== k2 && k2.$$typeof === Ha && Ng(k2) === l2.type) {
                        c2(a3, l2.sibling);
                        d2 = e(l2, f2.props);
                        d2.ref = Lg(a3, l2, f2);
                        d2.return = a3;
                        a3 = d2;
                        break a;
                      }
                      c2(a3, l2);
                      break;
                    } else b2(a3, l2);
                    l2 = l2.sibling;
                  }
                  f2.type === ya ? (d2 = Tg(f2.props.children, a3.mode, h2, f2.key), d2.return = a3, a3 = d2) : (h2 = Rg(f2.type, f2.key, f2.props, null, a3.mode, h2), h2.ref = Lg(a3, d2, f2), h2.return = a3, a3 = h2);
                }
                return g(a3);
              case wa:
                a: {
                  for (l2 = f2.key; null !== d2; ) {
                    if (d2.key === l2) if (4 === d2.tag && d2.stateNode.containerInfo === f2.containerInfo && d2.stateNode.implementation === f2.implementation) {
                      c2(a3, d2.sibling);
                      d2 = e(d2, f2.children || []);
                      d2.return = a3;
                      a3 = d2;
                      break a;
                    } else {
                      c2(a3, d2);
                      break;
                    }
                    else b2(a3, d2);
                    d2 = d2.sibling;
                  }
                  d2 = Sg(f2, a3.mode, h2);
                  d2.return = a3;
                  a3 = d2;
                }
                return g(a3);
              case Ha:
                return l2 = f2._init, J(a3, d2, l2(f2._payload), h2);
            }
            if (eb(f2)) return n(a3, d2, f2, h2);
            if (Ka(f2)) return t(a3, d2, f2, h2);
            Mg(a3, f2);
          }
          return "string" === typeof f2 && "" !== f2 || "number" === typeof f2 ? (f2 = "" + f2, null !== d2 && 6 === d2.tag ? (c2(a3, d2.sibling), d2 = e(d2, f2), d2.return = a3, a3 = d2) : (c2(a3, d2), d2 = Qg(f2, a3.mode, h2), d2.return = a3, a3 = d2), g(a3)) : c2(a3, d2);
        }
        return J;
      }
      var Ug = Og(true);
      var Vg = Og(false);
      var Wg = Uf(null);
      var Xg = null;
      var Yg = null;
      var Zg = null;
      function $g() {
        Zg = Yg = Xg = null;
      }
      function ah(a2) {
        var b2 = Wg.current;
        E(Wg);
        a2._currentValue = b2;
      }
      function bh(a2, b2, c2) {
        for (; null !== a2; ) {
          var d = a2.alternate;
          (a2.childLanes & b2) !== b2 ? (a2.childLanes |= b2, null !== d && (d.childLanes |= b2)) : null !== d && (d.childLanes & b2) !== b2 && (d.childLanes |= b2);
          if (a2 === c2) break;
          a2 = a2.return;
        }
      }
      function ch(a2, b2) {
        Xg = a2;
        Zg = Yg = null;
        a2 = a2.dependencies;
        null !== a2 && null !== a2.firstContext && (0 !== (a2.lanes & b2) && (dh = true), a2.firstContext = null);
      }
      function eh(a2) {
        var b2 = a2._currentValue;
        if (Zg !== a2) if (a2 = { context: a2, memoizedValue: b2, next: null }, null === Yg) {
          if (null === Xg) throw Error(p(308));
          Yg = a2;
          Xg.dependencies = { lanes: 0, firstContext: a2 };
        } else Yg = Yg.next = a2;
        return b2;
      }
      var fh = null;
      function gh(a2) {
        null === fh ? fh = [a2] : fh.push(a2);
      }
      function hh(a2, b2, c2, d) {
        var e = b2.interleaved;
        null === e ? (c2.next = c2, gh(b2)) : (c2.next = e.next, e.next = c2);
        b2.interleaved = c2;
        return ih(a2, d);
      }
      function ih(a2, b2) {
        a2.lanes |= b2;
        var c2 = a2.alternate;
        null !== c2 && (c2.lanes |= b2);
        c2 = a2;
        for (a2 = a2.return; null !== a2; ) a2.childLanes |= b2, c2 = a2.alternate, null !== c2 && (c2.childLanes |= b2), c2 = a2, a2 = a2.return;
        return 3 === c2.tag ? c2.stateNode : null;
      }
      var jh = false;
      function kh(a2) {
        a2.updateQueue = { baseState: a2.memoizedState, firstBaseUpdate: null, lastBaseUpdate: null, shared: { pending: null, interleaved: null, lanes: 0 }, effects: null };
      }
      function lh(a2, b2) {
        a2 = a2.updateQueue;
        b2.updateQueue === a2 && (b2.updateQueue = { baseState: a2.baseState, firstBaseUpdate: a2.firstBaseUpdate, lastBaseUpdate: a2.lastBaseUpdate, shared: a2.shared, effects: a2.effects });
      }
      function mh(a2, b2) {
        return { eventTime: a2, lane: b2, tag: 0, payload: null, callback: null, next: null };
      }
      function nh(a2, b2, c2) {
        var d = a2.updateQueue;
        if (null === d) return null;
        d = d.shared;
        if (0 !== (K & 2)) {
          var e = d.pending;
          null === e ? b2.next = b2 : (b2.next = e.next, e.next = b2);
          d.pending = b2;
          return ih(a2, c2);
        }
        e = d.interleaved;
        null === e ? (b2.next = b2, gh(d)) : (b2.next = e.next, e.next = b2);
        d.interleaved = b2;
        return ih(a2, c2);
      }
      function oh(a2, b2, c2) {
        b2 = b2.updateQueue;
        if (null !== b2 && (b2 = b2.shared, 0 !== (c2 & 4194240))) {
          var d = b2.lanes;
          d &= a2.pendingLanes;
          c2 |= d;
          b2.lanes = c2;
          Cc(a2, c2);
        }
      }
      function ph(a2, b2) {
        var c2 = a2.updateQueue, d = a2.alternate;
        if (null !== d && (d = d.updateQueue, c2 === d)) {
          var e = null, f = null;
          c2 = c2.firstBaseUpdate;
          if (null !== c2) {
            do {
              var g = { eventTime: c2.eventTime, lane: c2.lane, tag: c2.tag, payload: c2.payload, callback: c2.callback, next: null };
              null === f ? e = f = g : f = f.next = g;
              c2 = c2.next;
            } while (null !== c2);
            null === f ? e = f = b2 : f = f.next = b2;
          } else e = f = b2;
          c2 = { baseState: d.baseState, firstBaseUpdate: e, lastBaseUpdate: f, shared: d.shared, effects: d.effects };
          a2.updateQueue = c2;
          return;
        }
        a2 = c2.lastBaseUpdate;
        null === a2 ? c2.firstBaseUpdate = b2 : a2.next = b2;
        c2.lastBaseUpdate = b2;
      }
      function qh(a2, b2, c2, d) {
        var e = a2.updateQueue;
        jh = false;
        var f = e.firstBaseUpdate, g = e.lastBaseUpdate, h = e.shared.pending;
        if (null !== h) {
          e.shared.pending = null;
          var k = h, l = k.next;
          k.next = null;
          null === g ? f = l : g.next = l;
          g = k;
          var m = a2.alternate;
          null !== m && (m = m.updateQueue, h = m.lastBaseUpdate, h !== g && (null === h ? m.firstBaseUpdate = l : h.next = l, m.lastBaseUpdate = k));
        }
        if (null !== f) {
          var q = e.baseState;
          g = 0;
          m = l = k = null;
          h = f;
          do {
            var r = h.lane, y = h.eventTime;
            if ((d & r) === r) {
              null !== m && (m = m.next = {
                eventTime: y,
                lane: 0,
                tag: h.tag,
                payload: h.payload,
                callback: h.callback,
                next: null
              });
              a: {
                var n = a2, t = h;
                r = b2;
                y = c2;
                switch (t.tag) {
                  case 1:
                    n = t.payload;
                    if ("function" === typeof n) {
                      q = n.call(y, q, r);
                      break a;
                    }
                    q = n;
                    break a;
                  case 3:
                    n.flags = n.flags & -65537 | 128;
                  case 0:
                    n = t.payload;
                    r = "function" === typeof n ? n.call(y, q, r) : n;
                    if (null === r || void 0 === r) break a;
                    q = A({}, q, r);
                    break a;
                  case 2:
                    jh = true;
                }
              }
              null !== h.callback && 0 !== h.lane && (a2.flags |= 64, r = e.effects, null === r ? e.effects = [h] : r.push(h));
            } else y = { eventTime: y, lane: r, tag: h.tag, payload: h.payload, callback: h.callback, next: null }, null === m ? (l = m = y, k = q) : m = m.next = y, g |= r;
            h = h.next;
            if (null === h) if (h = e.shared.pending, null === h) break;
            else r = h, h = r.next, r.next = null, e.lastBaseUpdate = r, e.shared.pending = null;
          } while (1);
          null === m && (k = q);
          e.baseState = k;
          e.firstBaseUpdate = l;
          e.lastBaseUpdate = m;
          b2 = e.shared.interleaved;
          if (null !== b2) {
            e = b2;
            do
              g |= e.lane, e = e.next;
            while (e !== b2);
          } else null === f && (e.shared.lanes = 0);
          rh |= g;
          a2.lanes = g;
          a2.memoizedState = q;
        }
      }
      function sh(a2, b2, c2) {
        a2 = b2.effects;
        b2.effects = null;
        if (null !== a2) for (b2 = 0; b2 < a2.length; b2++) {
          var d = a2[b2], e = d.callback;
          if (null !== e) {
            d.callback = null;
            d = c2;
            if ("function" !== typeof e) throw Error(p(191, e));
            e.call(d);
          }
        }
      }
      var th = {};
      var uh = Uf(th);
      var vh = Uf(th);
      var wh = Uf(th);
      function xh(a2) {
        if (a2 === th) throw Error(p(174));
        return a2;
      }
      function yh(a2, b2) {
        G(wh, b2);
        G(vh, a2);
        G(uh, th);
        a2 = b2.nodeType;
        switch (a2) {
          case 9:
          case 11:
            b2 = (b2 = b2.documentElement) ? b2.namespaceURI : lb(null, "");
            break;
          default:
            a2 = 8 === a2 ? b2.parentNode : b2, b2 = a2.namespaceURI || null, a2 = a2.tagName, b2 = lb(b2, a2);
        }
        E(uh);
        G(uh, b2);
      }
      function zh() {
        E(uh);
        E(vh);
        E(wh);
      }
      function Ah(a2) {
        xh(wh.current);
        var b2 = xh(uh.current);
        var c2 = lb(b2, a2.type);
        b2 !== c2 && (G(vh, a2), G(uh, c2));
      }
      function Bh(a2) {
        vh.current === a2 && (E(uh), E(vh));
      }
      var L = Uf(0);
      function Ch(a2) {
        for (var b2 = a2; null !== b2; ) {
          if (13 === b2.tag) {
            var c2 = b2.memoizedState;
            if (null !== c2 && (c2 = c2.dehydrated, null === c2 || "$?" === c2.data || "$!" === c2.data)) return b2;
          } else if (19 === b2.tag && void 0 !== b2.memoizedProps.revealOrder) {
            if (0 !== (b2.flags & 128)) return b2;
          } else if (null !== b2.child) {
            b2.child.return = b2;
            b2 = b2.child;
            continue;
          }
          if (b2 === a2) break;
          for (; null === b2.sibling; ) {
            if (null === b2.return || b2.return === a2) return null;
            b2 = b2.return;
          }
          b2.sibling.return = b2.return;
          b2 = b2.sibling;
        }
        return null;
      }
      var Dh = [];
      function Eh() {
        for (var a2 = 0; a2 < Dh.length; a2++) Dh[a2]._workInProgressVersionPrimary = null;
        Dh.length = 0;
      }
      var Fh = ua.ReactCurrentDispatcher;
      var Gh = ua.ReactCurrentBatchConfig;
      var Hh = 0;
      var M = null;
      var N = null;
      var O = null;
      var Ih = false;
      var Jh = false;
      var Kh = 0;
      var Lh = 0;
      function P() {
        throw Error(p(321));
      }
      function Mh(a2, b2) {
        if (null === b2) return false;
        for (var c2 = 0; c2 < b2.length && c2 < a2.length; c2++) if (!He(a2[c2], b2[c2])) return false;
        return true;
      }
      function Nh(a2, b2, c2, d, e, f) {
        Hh = f;
        M = b2;
        b2.memoizedState = null;
        b2.updateQueue = null;
        b2.lanes = 0;
        Fh.current = null === a2 || null === a2.memoizedState ? Oh : Ph;
        a2 = c2(d, e);
        if (Jh) {
          f = 0;
          do {
            Jh = false;
            Kh = 0;
            if (25 <= f) throw Error(p(301));
            f += 1;
            O = N = null;
            b2.updateQueue = null;
            Fh.current = Qh;
            a2 = c2(d, e);
          } while (Jh);
        }
        Fh.current = Rh;
        b2 = null !== N && null !== N.next;
        Hh = 0;
        O = N = M = null;
        Ih = false;
        if (b2) throw Error(p(300));
        return a2;
      }
      function Sh() {
        var a2 = 0 !== Kh;
        Kh = 0;
        return a2;
      }
      function Th() {
        var a2 = { memoizedState: null, baseState: null, baseQueue: null, queue: null, next: null };
        null === O ? M.memoizedState = O = a2 : O = O.next = a2;
        return O;
      }
      function Uh() {
        if (null === N) {
          var a2 = M.alternate;
          a2 = null !== a2 ? a2.memoizedState : null;
        } else a2 = N.next;
        var b2 = null === O ? M.memoizedState : O.next;
        if (null !== b2) O = b2, N = a2;
        else {
          if (null === a2) throw Error(p(310));
          N = a2;
          a2 = { memoizedState: N.memoizedState, baseState: N.baseState, baseQueue: N.baseQueue, queue: N.queue, next: null };
          null === O ? M.memoizedState = O = a2 : O = O.next = a2;
        }
        return O;
      }
      function Vh(a2, b2) {
        return "function" === typeof b2 ? b2(a2) : b2;
      }
      function Wh(a2) {
        var b2 = Uh(), c2 = b2.queue;
        if (null === c2) throw Error(p(311));
        c2.lastRenderedReducer = a2;
        var d = N, e = d.baseQueue, f = c2.pending;
        if (null !== f) {
          if (null !== e) {
            var g = e.next;
            e.next = f.next;
            f.next = g;
          }
          d.baseQueue = e = f;
          c2.pending = null;
        }
        if (null !== e) {
          f = e.next;
          d = d.baseState;
          var h = g = null, k = null, l = f;
          do {
            var m = l.lane;
            if ((Hh & m) === m) null !== k && (k = k.next = { lane: 0, action: l.action, hasEagerState: l.hasEagerState, eagerState: l.eagerState, next: null }), d = l.hasEagerState ? l.eagerState : a2(d, l.action);
            else {
              var q = {
                lane: m,
                action: l.action,
                hasEagerState: l.hasEagerState,
                eagerState: l.eagerState,
                next: null
              };
              null === k ? (h = k = q, g = d) : k = k.next = q;
              M.lanes |= m;
              rh |= m;
            }
            l = l.next;
          } while (null !== l && l !== f);
          null === k ? g = d : k.next = h;
          He(d, b2.memoizedState) || (dh = true);
          b2.memoizedState = d;
          b2.baseState = g;
          b2.baseQueue = k;
          c2.lastRenderedState = d;
        }
        a2 = c2.interleaved;
        if (null !== a2) {
          e = a2;
          do
            f = e.lane, M.lanes |= f, rh |= f, e = e.next;
          while (e !== a2);
        } else null === e && (c2.lanes = 0);
        return [b2.memoizedState, c2.dispatch];
      }
      function Xh(a2) {
        var b2 = Uh(), c2 = b2.queue;
        if (null === c2) throw Error(p(311));
        c2.lastRenderedReducer = a2;
        var d = c2.dispatch, e = c2.pending, f = b2.memoizedState;
        if (null !== e) {
          c2.pending = null;
          var g = e = e.next;
          do
            f = a2(f, g.action), g = g.next;
          while (g !== e);
          He(f, b2.memoizedState) || (dh = true);
          b2.memoizedState = f;
          null === b2.baseQueue && (b2.baseState = f);
          c2.lastRenderedState = f;
        }
        return [f, d];
      }
      function Yh() {
      }
      function Zh(a2, b2) {
        var c2 = M, d = Uh(), e = b2(), f = !He(d.memoizedState, e);
        f && (d.memoizedState = e, dh = true);
        d = d.queue;
        $h(ai.bind(null, c2, d, a2), [a2]);
        if (d.getSnapshot !== b2 || f || null !== O && O.memoizedState.tag & 1) {
          c2.flags |= 2048;
          bi(9, ci.bind(null, c2, d, e, b2), void 0, null);
          if (null === Q) throw Error(p(349));
          0 !== (Hh & 30) || di(c2, b2, e);
        }
        return e;
      }
      function di(a2, b2, c2) {
        a2.flags |= 16384;
        a2 = { getSnapshot: b2, value: c2 };
        b2 = M.updateQueue;
        null === b2 ? (b2 = { lastEffect: null, stores: null }, M.updateQueue = b2, b2.stores = [a2]) : (c2 = b2.stores, null === c2 ? b2.stores = [a2] : c2.push(a2));
      }
      function ci(a2, b2, c2, d) {
        b2.value = c2;
        b2.getSnapshot = d;
        ei(b2) && fi(a2);
      }
      function ai(a2, b2, c2) {
        return c2(function() {
          ei(b2) && fi(a2);
        });
      }
      function ei(a2) {
        var b2 = a2.getSnapshot;
        a2 = a2.value;
        try {
          var c2 = b2();
          return !He(a2, c2);
        } catch (d) {
          return true;
        }
      }
      function fi(a2) {
        var b2 = ih(a2, 1);
        null !== b2 && gi(b2, a2, 1, -1);
      }
      function hi(a2) {
        var b2 = Th();
        "function" === typeof a2 && (a2 = a2());
        b2.memoizedState = b2.baseState = a2;
        a2 = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: Vh, lastRenderedState: a2 };
        b2.queue = a2;
        a2 = a2.dispatch = ii.bind(null, M, a2);
        return [b2.memoizedState, a2];
      }
      function bi(a2, b2, c2, d) {
        a2 = { tag: a2, create: b2, destroy: c2, deps: d, next: null };
        b2 = M.updateQueue;
        null === b2 ? (b2 = { lastEffect: null, stores: null }, M.updateQueue = b2, b2.lastEffect = a2.next = a2) : (c2 = b2.lastEffect, null === c2 ? b2.lastEffect = a2.next = a2 : (d = c2.next, c2.next = a2, a2.next = d, b2.lastEffect = a2));
        return a2;
      }
      function ji() {
        return Uh().memoizedState;
      }
      function ki(a2, b2, c2, d) {
        var e = Th();
        M.flags |= a2;
        e.memoizedState = bi(1 | b2, c2, void 0, void 0 === d ? null : d);
      }
      function li(a2, b2, c2, d) {
        var e = Uh();
        d = void 0 === d ? null : d;
        var f = void 0;
        if (null !== N) {
          var g = N.memoizedState;
          f = g.destroy;
          if (null !== d && Mh(d, g.deps)) {
            e.memoizedState = bi(b2, c2, f, d);
            return;
          }
        }
        M.flags |= a2;
        e.memoizedState = bi(1 | b2, c2, f, d);
      }
      function mi(a2, b2) {
        return ki(8390656, 8, a2, b2);
      }
      function $h(a2, b2) {
        return li(2048, 8, a2, b2);
      }
      function ni(a2, b2) {
        return li(4, 2, a2, b2);
      }
      function oi(a2, b2) {
        return li(4, 4, a2, b2);
      }
      function pi(a2, b2) {
        if ("function" === typeof b2) return a2 = a2(), b2(a2), function() {
          b2(null);
        };
        if (null !== b2 && void 0 !== b2) return a2 = a2(), b2.current = a2, function() {
          b2.current = null;
        };
      }
      function qi(a2, b2, c2) {
        c2 = null !== c2 && void 0 !== c2 ? c2.concat([a2]) : null;
        return li(4, 4, pi.bind(null, b2, a2), c2);
      }
      function ri() {
      }
      function si(a2, b2) {
        var c2 = Uh();
        b2 = void 0 === b2 ? null : b2;
        var d = c2.memoizedState;
        if (null !== d && null !== b2 && Mh(b2, d[1])) return d[0];
        c2.memoizedState = [a2, b2];
        return a2;
      }
      function ti(a2, b2) {
        var c2 = Uh();
        b2 = void 0 === b2 ? null : b2;
        var d = c2.memoizedState;
        if (null !== d && null !== b2 && Mh(b2, d[1])) return d[0];
        a2 = a2();
        c2.memoizedState = [a2, b2];
        return a2;
      }
      function ui(a2, b2, c2) {
        if (0 === (Hh & 21)) return a2.baseState && (a2.baseState = false, dh = true), a2.memoizedState = c2;
        He(c2, b2) || (c2 = yc(), M.lanes |= c2, rh |= c2, a2.baseState = true);
        return b2;
      }
      function vi(a2, b2) {
        var c2 = C;
        C = 0 !== c2 && 4 > c2 ? c2 : 4;
        a2(true);
        var d = Gh.transition;
        Gh.transition = {};
        try {
          a2(false), b2();
        } finally {
          C = c2, Gh.transition = d;
        }
      }
      function wi() {
        return Uh().memoizedState;
      }
      function xi(a2, b2, c2) {
        var d = yi(a2);
        c2 = { lane: d, action: c2, hasEagerState: false, eagerState: null, next: null };
        if (zi(a2)) Ai(b2, c2);
        else if (c2 = hh(a2, b2, c2, d), null !== c2) {
          var e = R();
          gi(c2, a2, d, e);
          Bi(c2, b2, d);
        }
      }
      function ii(a2, b2, c2) {
        var d = yi(a2), e = { lane: d, action: c2, hasEagerState: false, eagerState: null, next: null };
        if (zi(a2)) Ai(b2, e);
        else {
          var f = a2.alternate;
          if (0 === a2.lanes && (null === f || 0 === f.lanes) && (f = b2.lastRenderedReducer, null !== f)) try {
            var g = b2.lastRenderedState, h = f(g, c2);
            e.hasEagerState = true;
            e.eagerState = h;
            if (He(h, g)) {
              var k = b2.interleaved;
              null === k ? (e.next = e, gh(b2)) : (e.next = k.next, k.next = e);
              b2.interleaved = e;
              return;
            }
          } catch (l) {
          } finally {
          }
          c2 = hh(a2, b2, e, d);
          null !== c2 && (e = R(), gi(c2, a2, d, e), Bi(c2, b2, d));
        }
      }
      function zi(a2) {
        var b2 = a2.alternate;
        return a2 === M || null !== b2 && b2 === M;
      }
      function Ai(a2, b2) {
        Jh = Ih = true;
        var c2 = a2.pending;
        null === c2 ? b2.next = b2 : (b2.next = c2.next, c2.next = b2);
        a2.pending = b2;
      }
      function Bi(a2, b2, c2) {
        if (0 !== (c2 & 4194240)) {
          var d = b2.lanes;
          d &= a2.pendingLanes;
          c2 |= d;
          b2.lanes = c2;
          Cc(a2, c2);
        }
      }
      var Rh = { readContext: eh, useCallback: P, useContext: P, useEffect: P, useImperativeHandle: P, useInsertionEffect: P, useLayoutEffect: P, useMemo: P, useReducer: P, useRef: P, useState: P, useDebugValue: P, useDeferredValue: P, useTransition: P, useMutableSource: P, useSyncExternalStore: P, useId: P, unstable_isNewReconciler: false };
      var Oh = { readContext: eh, useCallback: function(a2, b2) {
        Th().memoizedState = [a2, void 0 === b2 ? null : b2];
        return a2;
      }, useContext: eh, useEffect: mi, useImperativeHandle: function(a2, b2, c2) {
        c2 = null !== c2 && void 0 !== c2 ? c2.concat([a2]) : null;
        return ki(
          4194308,
          4,
          pi.bind(null, b2, a2),
          c2
        );
      }, useLayoutEffect: function(a2, b2) {
        return ki(4194308, 4, a2, b2);
      }, useInsertionEffect: function(a2, b2) {
        return ki(4, 2, a2, b2);
      }, useMemo: function(a2, b2) {
        var c2 = Th();
        b2 = void 0 === b2 ? null : b2;
        a2 = a2();
        c2.memoizedState = [a2, b2];
        return a2;
      }, useReducer: function(a2, b2, c2) {
        var d = Th();
        b2 = void 0 !== c2 ? c2(b2) : b2;
        d.memoizedState = d.baseState = b2;
        a2 = { pending: null, interleaved: null, lanes: 0, dispatch: null, lastRenderedReducer: a2, lastRenderedState: b2 };
        d.queue = a2;
        a2 = a2.dispatch = xi.bind(null, M, a2);
        return [d.memoizedState, a2];
      }, useRef: function(a2) {
        var b2 = Th();
        a2 = { current: a2 };
        return b2.memoizedState = a2;
      }, useState: hi, useDebugValue: ri, useDeferredValue: function(a2) {
        return Th().memoizedState = a2;
      }, useTransition: function() {
        var a2 = hi(false), b2 = a2[0];
        a2 = vi.bind(null, a2[1]);
        Th().memoizedState = a2;
        return [b2, a2];
      }, useMutableSource: function() {
      }, useSyncExternalStore: function(a2, b2, c2) {
        var d = M, e = Th();
        if (I) {
          if (void 0 === c2) throw Error(p(407));
          c2 = c2();
        } else {
          c2 = b2();
          if (null === Q) throw Error(p(349));
          0 !== (Hh & 30) || di(d, b2, c2);
        }
        e.memoizedState = c2;
        var f = { value: c2, getSnapshot: b2 };
        e.queue = f;
        mi(ai.bind(
          null,
          d,
          f,
          a2
        ), [a2]);
        d.flags |= 2048;
        bi(9, ci.bind(null, d, f, c2, b2), void 0, null);
        return c2;
      }, useId: function() {
        var a2 = Th(), b2 = Q.identifierPrefix;
        if (I) {
          var c2 = sg;
          var d = rg;
          c2 = (d & ~(1 << 32 - oc(d) - 1)).toString(32) + c2;
          b2 = ":" + b2 + "R" + c2;
          c2 = Kh++;
          0 < c2 && (b2 += "H" + c2.toString(32));
          b2 += ":";
        } else c2 = Lh++, b2 = ":" + b2 + "r" + c2.toString(32) + ":";
        return a2.memoizedState = b2;
      }, unstable_isNewReconciler: false };
      var Ph = {
        readContext: eh,
        useCallback: si,
        useContext: eh,
        useEffect: $h,
        useImperativeHandle: qi,
        useInsertionEffect: ni,
        useLayoutEffect: oi,
        useMemo: ti,
        useReducer: Wh,
        useRef: ji,
        useState: function() {
          return Wh(Vh);
        },
        useDebugValue: ri,
        useDeferredValue: function(a2) {
          var b2 = Uh();
          return ui(b2, N.memoizedState, a2);
        },
        useTransition: function() {
          var a2 = Wh(Vh)[0], b2 = Uh().memoizedState;
          return [a2, b2];
        },
        useMutableSource: Yh,
        useSyncExternalStore: Zh,
        useId: wi,
        unstable_isNewReconciler: false
      };
      var Qh = { readContext: eh, useCallback: si, useContext: eh, useEffect: $h, useImperativeHandle: qi, useInsertionEffect: ni, useLayoutEffect: oi, useMemo: ti, useReducer: Xh, useRef: ji, useState: function() {
        return Xh(Vh);
      }, useDebugValue: ri, useDeferredValue: function(a2) {
        var b2 = Uh();
        return null === N ? b2.memoizedState = a2 : ui(b2, N.memoizedState, a2);
      }, useTransition: function() {
        var a2 = Xh(Vh)[0], b2 = Uh().memoizedState;
        return [a2, b2];
      }, useMutableSource: Yh, useSyncExternalStore: Zh, useId: wi, unstable_isNewReconciler: false };
      function Ci(a2, b2) {
        if (a2 && a2.defaultProps) {
          b2 = A({}, b2);
          a2 = a2.defaultProps;
          for (var c2 in a2) void 0 === b2[c2] && (b2[c2] = a2[c2]);
          return b2;
        }
        return b2;
      }
      function Di(a2, b2, c2, d) {
        b2 = a2.memoizedState;
        c2 = c2(d, b2);
        c2 = null === c2 || void 0 === c2 ? b2 : A({}, b2, c2);
        a2.memoizedState = c2;
        0 === a2.lanes && (a2.updateQueue.baseState = c2);
      }
      var Ei = { isMounted: function(a2) {
        return (a2 = a2._reactInternals) ? Vb(a2) === a2 : false;
      }, enqueueSetState: function(a2, b2, c2) {
        a2 = a2._reactInternals;
        var d = R(), e = yi(a2), f = mh(d, e);
        f.payload = b2;
        void 0 !== c2 && null !== c2 && (f.callback = c2);
        b2 = nh(a2, f, e);
        null !== b2 && (gi(b2, a2, e, d), oh(b2, a2, e));
      }, enqueueReplaceState: function(a2, b2, c2) {
        a2 = a2._reactInternals;
        var d = R(), e = yi(a2), f = mh(d, e);
        f.tag = 1;
        f.payload = b2;
        void 0 !== c2 && null !== c2 && (f.callback = c2);
        b2 = nh(a2, f, e);
        null !== b2 && (gi(b2, a2, e, d), oh(b2, a2, e));
      }, enqueueForceUpdate: function(a2, b2) {
        a2 = a2._reactInternals;
        var c2 = R(), d = yi(a2), e = mh(c2, d);
        e.tag = 2;
        void 0 !== b2 && null !== b2 && (e.callback = b2);
        b2 = nh(a2, e, d);
        null !== b2 && (gi(b2, a2, d, c2), oh(b2, a2, d));
      } };
      function Fi(a2, b2, c2, d, e, f, g) {
        a2 = a2.stateNode;
        return "function" === typeof a2.shouldComponentUpdate ? a2.shouldComponentUpdate(d, f, g) : b2.prototype && b2.prototype.isPureReactComponent ? !Ie(c2, d) || !Ie(e, f) : true;
      }
      function Gi(a2, b2, c2) {
        var d = false, e = Vf;
        var f = b2.contextType;
        "object" === typeof f && null !== f ? f = eh(f) : (e = Zf(b2) ? Xf : H.current, d = b2.contextTypes, f = (d = null !== d && void 0 !== d) ? Yf(a2, e) : Vf);
        b2 = new b2(c2, f);
        a2.memoizedState = null !== b2.state && void 0 !== b2.state ? b2.state : null;
        b2.updater = Ei;
        a2.stateNode = b2;
        b2._reactInternals = a2;
        d && (a2 = a2.stateNode, a2.__reactInternalMemoizedUnmaskedChildContext = e, a2.__reactInternalMemoizedMaskedChildContext = f);
        return b2;
      }
      function Hi(a2, b2, c2, d) {
        a2 = b2.state;
        "function" === typeof b2.componentWillReceiveProps && b2.componentWillReceiveProps(c2, d);
        "function" === typeof b2.UNSAFE_componentWillReceiveProps && b2.UNSAFE_componentWillReceiveProps(c2, d);
        b2.state !== a2 && Ei.enqueueReplaceState(b2, b2.state, null);
      }
      function Ii(a2, b2, c2, d) {
        var e = a2.stateNode;
        e.props = c2;
        e.state = a2.memoizedState;
        e.refs = {};
        kh(a2);
        var f = b2.contextType;
        "object" === typeof f && null !== f ? e.context = eh(f) : (f = Zf(b2) ? Xf : H.current, e.context = Yf(a2, f));
        e.state = a2.memoizedState;
        f = b2.getDerivedStateFromProps;
        "function" === typeof f && (Di(a2, b2, f, c2), e.state = a2.memoizedState);
        "function" === typeof b2.getDerivedStateFromProps || "function" === typeof e.getSnapshotBeforeUpdate || "function" !== typeof e.UNSAFE_componentWillMount && "function" !== typeof e.componentWillMount || (b2 = e.state, "function" === typeof e.componentWillMount && e.componentWillMount(), "function" === typeof e.UNSAFE_componentWillMount && e.UNSAFE_componentWillMount(), b2 !== e.state && Ei.enqueueReplaceState(e, e.state, null), qh(a2, c2, e, d), e.state = a2.memoizedState);
        "function" === typeof e.componentDidMount && (a2.flags |= 4194308);
      }
      function Ji(a2, b2) {
        try {
          var c2 = "", d = b2;
          do
            c2 += Pa(d), d = d.return;
          while (d);
          var e = c2;
        } catch (f) {
          e = "\nError generating stack: " + f.message + "\n" + f.stack;
        }
        return { value: a2, source: b2, stack: e, digest: null };
      }
      function Ki(a2, b2, c2) {
        return { value: a2, source: null, stack: null != c2 ? c2 : null, digest: null != b2 ? b2 : null };
      }
      function Li(a2, b2) {
        try {
          console.error(b2.value);
        } catch (c2) {
          setTimeout(function() {
            throw c2;
          });
        }
      }
      var Mi = "function" === typeof WeakMap ? WeakMap : Map;
      function Ni(a2, b2, c2) {
        c2 = mh(-1, c2);
        c2.tag = 3;
        c2.payload = { element: null };
        var d = b2.value;
        c2.callback = function() {
          Oi || (Oi = true, Pi = d);
          Li(a2, b2);
        };
        return c2;
      }
      function Qi(a2, b2, c2) {
        c2 = mh(-1, c2);
        c2.tag = 3;
        var d = a2.type.getDerivedStateFromError;
        if ("function" === typeof d) {
          var e = b2.value;
          c2.payload = function() {
            return d(e);
          };
          c2.callback = function() {
            Li(a2, b2);
          };
        }
        var f = a2.stateNode;
        null !== f && "function" === typeof f.componentDidCatch && (c2.callback = function() {
          Li(a2, b2);
          "function" !== typeof d && (null === Ri ? Ri = /* @__PURE__ */ new Set([this]) : Ri.add(this));
          var c3 = b2.stack;
          this.componentDidCatch(b2.value, { componentStack: null !== c3 ? c3 : "" });
        });
        return c2;
      }
      function Si(a2, b2, c2) {
        var d = a2.pingCache;
        if (null === d) {
          d = a2.pingCache = new Mi();
          var e = /* @__PURE__ */ new Set();
          d.set(b2, e);
        } else e = d.get(b2), void 0 === e && (e = /* @__PURE__ */ new Set(), d.set(b2, e));
        e.has(c2) || (e.add(c2), a2 = Ti.bind(null, a2, b2, c2), b2.then(a2, a2));
      }
      function Ui(a2) {
        do {
          var b2;
          if (b2 = 13 === a2.tag) b2 = a2.memoizedState, b2 = null !== b2 ? null !== b2.dehydrated ? true : false : true;
          if (b2) return a2;
          a2 = a2.return;
        } while (null !== a2);
        return null;
      }
      function Vi(a2, b2, c2, d, e) {
        if (0 === (a2.mode & 1)) return a2 === b2 ? a2.flags |= 65536 : (a2.flags |= 128, c2.flags |= 131072, c2.flags &= -52805, 1 === c2.tag && (null === c2.alternate ? c2.tag = 17 : (b2 = mh(-1, 1), b2.tag = 2, nh(c2, b2, 1))), c2.lanes |= 1), a2;
        a2.flags |= 65536;
        a2.lanes = e;
        return a2;
      }
      var Wi = ua.ReactCurrentOwner;
      var dh = false;
      function Xi(a2, b2, c2, d) {
        b2.child = null === a2 ? Vg(b2, null, c2, d) : Ug(b2, a2.child, c2, d);
      }
      function Yi(a2, b2, c2, d, e) {
        c2 = c2.render;
        var f = b2.ref;
        ch(b2, e);
        d = Nh(a2, b2, c2, d, f, e);
        c2 = Sh();
        if (null !== a2 && !dh) return b2.updateQueue = a2.updateQueue, b2.flags &= -2053, a2.lanes &= ~e, Zi(a2, b2, e);
        I && c2 && vg(b2);
        b2.flags |= 1;
        Xi(a2, b2, d, e);
        return b2.child;
      }
      function $i(a2, b2, c2, d, e) {
        if (null === a2) {
          var f = c2.type;
          if ("function" === typeof f && !aj(f) && void 0 === f.defaultProps && null === c2.compare && void 0 === c2.defaultProps) return b2.tag = 15, b2.type = f, bj(a2, b2, f, d, e);
          a2 = Rg(c2.type, null, d, b2, b2.mode, e);
          a2.ref = b2.ref;
          a2.return = b2;
          return b2.child = a2;
        }
        f = a2.child;
        if (0 === (a2.lanes & e)) {
          var g = f.memoizedProps;
          c2 = c2.compare;
          c2 = null !== c2 ? c2 : Ie;
          if (c2(g, d) && a2.ref === b2.ref) return Zi(a2, b2, e);
        }
        b2.flags |= 1;
        a2 = Pg(f, d);
        a2.ref = b2.ref;
        a2.return = b2;
        return b2.child = a2;
      }
      function bj(a2, b2, c2, d, e) {
        if (null !== a2) {
          var f = a2.memoizedProps;
          if (Ie(f, d) && a2.ref === b2.ref) if (dh = false, b2.pendingProps = d = f, 0 !== (a2.lanes & e)) 0 !== (a2.flags & 131072) && (dh = true);
          else return b2.lanes = a2.lanes, Zi(a2, b2, e);
        }
        return cj(a2, b2, c2, d, e);
      }
      function dj(a2, b2, c2) {
        var d = b2.pendingProps, e = d.children, f = null !== a2 ? a2.memoizedState : null;
        if ("hidden" === d.mode) if (0 === (b2.mode & 1)) b2.memoizedState = { baseLanes: 0, cachePool: null, transitions: null }, G(ej, fj), fj |= c2;
        else {
          if (0 === (c2 & 1073741824)) return a2 = null !== f ? f.baseLanes | c2 : c2, b2.lanes = b2.childLanes = 1073741824, b2.memoizedState = { baseLanes: a2, cachePool: null, transitions: null }, b2.updateQueue = null, G(ej, fj), fj |= a2, null;
          b2.memoizedState = { baseLanes: 0, cachePool: null, transitions: null };
          d = null !== f ? f.baseLanes : c2;
          G(ej, fj);
          fj |= d;
        }
        else null !== f ? (d = f.baseLanes | c2, b2.memoizedState = null) : d = c2, G(ej, fj), fj |= d;
        Xi(a2, b2, e, c2);
        return b2.child;
      }
      function gj(a2, b2) {
        var c2 = b2.ref;
        if (null === a2 && null !== c2 || null !== a2 && a2.ref !== c2) b2.flags |= 512, b2.flags |= 2097152;
      }
      function cj(a2, b2, c2, d, e) {
        var f = Zf(c2) ? Xf : H.current;
        f = Yf(b2, f);
        ch(b2, e);
        c2 = Nh(a2, b2, c2, d, f, e);
        d = Sh();
        if (null !== a2 && !dh) return b2.updateQueue = a2.updateQueue, b2.flags &= -2053, a2.lanes &= ~e, Zi(a2, b2, e);
        I && d && vg(b2);
        b2.flags |= 1;
        Xi(a2, b2, c2, e);
        return b2.child;
      }
      function hj(a2, b2, c2, d, e) {
        if (Zf(c2)) {
          var f = true;
          cg(b2);
        } else f = false;
        ch(b2, e);
        if (null === b2.stateNode) ij(a2, b2), Gi(b2, c2, d), Ii(b2, c2, d, e), d = true;
        else if (null === a2) {
          var g = b2.stateNode, h = b2.memoizedProps;
          g.props = h;
          var k = g.context, l = c2.contextType;
          "object" === typeof l && null !== l ? l = eh(l) : (l = Zf(c2) ? Xf : H.current, l = Yf(b2, l));
          var m = c2.getDerivedStateFromProps, q = "function" === typeof m || "function" === typeof g.getSnapshotBeforeUpdate;
          q || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== d || k !== l) && Hi(b2, g, d, l);
          jh = false;
          var r = b2.memoizedState;
          g.state = r;
          qh(b2, d, g, e);
          k = b2.memoizedState;
          h !== d || r !== k || Wf.current || jh ? ("function" === typeof m && (Di(b2, c2, m, d), k = b2.memoizedState), (h = jh || Fi(b2, c2, h, d, r, k, l)) ? (q || "function" !== typeof g.UNSAFE_componentWillMount && "function" !== typeof g.componentWillMount || ("function" === typeof g.componentWillMount && g.componentWillMount(), "function" === typeof g.UNSAFE_componentWillMount && g.UNSAFE_componentWillMount()), "function" === typeof g.componentDidMount && (b2.flags |= 4194308)) : ("function" === typeof g.componentDidMount && (b2.flags |= 4194308), b2.memoizedProps = d, b2.memoizedState = k), g.props = d, g.state = k, g.context = l, d = h) : ("function" === typeof g.componentDidMount && (b2.flags |= 4194308), d = false);
        } else {
          g = b2.stateNode;
          lh(a2, b2);
          h = b2.memoizedProps;
          l = b2.type === b2.elementType ? h : Ci(b2.type, h);
          g.props = l;
          q = b2.pendingProps;
          r = g.context;
          k = c2.contextType;
          "object" === typeof k && null !== k ? k = eh(k) : (k = Zf(c2) ? Xf : H.current, k = Yf(b2, k));
          var y = c2.getDerivedStateFromProps;
          (m = "function" === typeof y || "function" === typeof g.getSnapshotBeforeUpdate) || "function" !== typeof g.UNSAFE_componentWillReceiveProps && "function" !== typeof g.componentWillReceiveProps || (h !== q || r !== k) && Hi(b2, g, d, k);
          jh = false;
          r = b2.memoizedState;
          g.state = r;
          qh(b2, d, g, e);
          var n = b2.memoizedState;
          h !== q || r !== n || Wf.current || jh ? ("function" === typeof y && (Di(b2, c2, y, d), n = b2.memoizedState), (l = jh || Fi(b2, c2, l, d, r, n, k) || false) ? (m || "function" !== typeof g.UNSAFE_componentWillUpdate && "function" !== typeof g.componentWillUpdate || ("function" === typeof g.componentWillUpdate && g.componentWillUpdate(d, n, k), "function" === typeof g.UNSAFE_componentWillUpdate && g.UNSAFE_componentWillUpdate(d, n, k)), "function" === typeof g.componentDidUpdate && (b2.flags |= 4), "function" === typeof g.getSnapshotBeforeUpdate && (b2.flags |= 1024)) : ("function" !== typeof g.componentDidUpdate || h === a2.memoizedProps && r === a2.memoizedState || (b2.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a2.memoizedProps && r === a2.memoizedState || (b2.flags |= 1024), b2.memoizedProps = d, b2.memoizedState = n), g.props = d, g.state = n, g.context = k, d = l) : ("function" !== typeof g.componentDidUpdate || h === a2.memoizedProps && r === a2.memoizedState || (b2.flags |= 4), "function" !== typeof g.getSnapshotBeforeUpdate || h === a2.memoizedProps && r === a2.memoizedState || (b2.flags |= 1024), d = false);
        }
        return jj(a2, b2, c2, d, f, e);
      }
      function jj(a2, b2, c2, d, e, f) {
        gj(a2, b2);
        var g = 0 !== (b2.flags & 128);
        if (!d && !g) return e && dg(b2, c2, false), Zi(a2, b2, f);
        d = b2.stateNode;
        Wi.current = b2;
        var h = g && "function" !== typeof c2.getDerivedStateFromError ? null : d.render();
        b2.flags |= 1;
        null !== a2 && g ? (b2.child = Ug(b2, a2.child, null, f), b2.child = Ug(b2, null, h, f)) : Xi(a2, b2, h, f);
        b2.memoizedState = d.state;
        e && dg(b2, c2, true);
        return b2.child;
      }
      function kj(a2) {
        var b2 = a2.stateNode;
        b2.pendingContext ? ag(a2, b2.pendingContext, b2.pendingContext !== b2.context) : b2.context && ag(a2, b2.context, false);
        yh(a2, b2.containerInfo);
      }
      function lj(a2, b2, c2, d, e) {
        Ig();
        Jg(e);
        b2.flags |= 256;
        Xi(a2, b2, c2, d);
        return b2.child;
      }
      var mj = { dehydrated: null, treeContext: null, retryLane: 0 };
      function nj(a2) {
        return { baseLanes: a2, cachePool: null, transitions: null };
      }
      function oj(a2, b2, c2) {
        var d = b2.pendingProps, e = L.current, f = false, g = 0 !== (b2.flags & 128), h;
        (h = g) || (h = null !== a2 && null === a2.memoizedState ? false : 0 !== (e & 2));
        if (h) f = true, b2.flags &= -129;
        else if (null === a2 || null !== a2.memoizedState) e |= 1;
        G(L, e & 1);
        if (null === a2) {
          Eg(b2);
          a2 = b2.memoizedState;
          if (null !== a2 && (a2 = a2.dehydrated, null !== a2)) return 0 === (b2.mode & 1) ? b2.lanes = 1 : "$!" === a2.data ? b2.lanes = 8 : b2.lanes = 1073741824, null;
          g = d.children;
          a2 = d.fallback;
          return f ? (d = b2.mode, f = b2.child, g = { mode: "hidden", children: g }, 0 === (d & 1) && null !== f ? (f.childLanes = 0, f.pendingProps = g) : f = pj(g, d, 0, null), a2 = Tg(a2, d, c2, null), f.return = b2, a2.return = b2, f.sibling = a2, b2.child = f, b2.child.memoizedState = nj(c2), b2.memoizedState = mj, a2) : qj(b2, g);
        }
        e = a2.memoizedState;
        if (null !== e && (h = e.dehydrated, null !== h)) return rj(a2, b2, g, d, h, e, c2);
        if (f) {
          f = d.fallback;
          g = b2.mode;
          e = a2.child;
          h = e.sibling;
          var k = { mode: "hidden", children: d.children };
          0 === (g & 1) && b2.child !== e ? (d = b2.child, d.childLanes = 0, d.pendingProps = k, b2.deletions = null) : (d = Pg(e, k), d.subtreeFlags = e.subtreeFlags & 14680064);
          null !== h ? f = Pg(h, f) : (f = Tg(f, g, c2, null), f.flags |= 2);
          f.return = b2;
          d.return = b2;
          d.sibling = f;
          b2.child = d;
          d = f;
          f = b2.child;
          g = a2.child.memoizedState;
          g = null === g ? nj(c2) : { baseLanes: g.baseLanes | c2, cachePool: null, transitions: g.transitions };
          f.memoizedState = g;
          f.childLanes = a2.childLanes & ~c2;
          b2.memoizedState = mj;
          return d;
        }
        f = a2.child;
        a2 = f.sibling;
        d = Pg(f, { mode: "visible", children: d.children });
        0 === (b2.mode & 1) && (d.lanes = c2);
        d.return = b2;
        d.sibling = null;
        null !== a2 && (c2 = b2.deletions, null === c2 ? (b2.deletions = [a2], b2.flags |= 16) : c2.push(a2));
        b2.child = d;
        b2.memoizedState = null;
        return d;
      }
      function qj(a2, b2) {
        b2 = pj({ mode: "visible", children: b2 }, a2.mode, 0, null);
        b2.return = a2;
        return a2.child = b2;
      }
      function sj(a2, b2, c2, d) {
        null !== d && Jg(d);
        Ug(b2, a2.child, null, c2);
        a2 = qj(b2, b2.pendingProps.children);
        a2.flags |= 2;
        b2.memoizedState = null;
        return a2;
      }
      function rj(a2, b2, c2, d, e, f, g) {
        if (c2) {
          if (b2.flags & 256) return b2.flags &= -257, d = Ki(Error(p(422))), sj(a2, b2, g, d);
          if (null !== b2.memoizedState) return b2.child = a2.child, b2.flags |= 128, null;
          f = d.fallback;
          e = b2.mode;
          d = pj({ mode: "visible", children: d.children }, e, 0, null);
          f = Tg(f, e, g, null);
          f.flags |= 2;
          d.return = b2;
          f.return = b2;
          d.sibling = f;
          b2.child = d;
          0 !== (b2.mode & 1) && Ug(b2, a2.child, null, g);
          b2.child.memoizedState = nj(g);
          b2.memoizedState = mj;
          return f;
        }
        if (0 === (b2.mode & 1)) return sj(a2, b2, g, null);
        if ("$!" === e.data) {
          d = e.nextSibling && e.nextSibling.dataset;
          if (d) var h = d.dgst;
          d = h;
          f = Error(p(419));
          d = Ki(f, d, void 0);
          return sj(a2, b2, g, d);
        }
        h = 0 !== (g & a2.childLanes);
        if (dh || h) {
          d = Q;
          if (null !== d) {
            switch (g & -g) {
              case 4:
                e = 2;
                break;
              case 16:
                e = 8;
                break;
              case 64:
              case 128:
              case 256:
              case 512:
              case 1024:
              case 2048:
              case 4096:
              case 8192:
              case 16384:
              case 32768:
              case 65536:
              case 131072:
              case 262144:
              case 524288:
              case 1048576:
              case 2097152:
              case 4194304:
              case 8388608:
              case 16777216:
              case 33554432:
              case 67108864:
                e = 32;
                break;
              case 536870912:
                e = 268435456;
                break;
              default:
                e = 0;
            }
            e = 0 !== (e & (d.suspendedLanes | g)) ? 0 : e;
            0 !== e && e !== f.retryLane && (f.retryLane = e, ih(a2, e), gi(d, a2, e, -1));
          }
          tj();
          d = Ki(Error(p(421)));
          return sj(a2, b2, g, d);
        }
        if ("$?" === e.data) return b2.flags |= 128, b2.child = a2.child, b2 = uj.bind(null, a2), e._reactRetry = b2, null;
        a2 = f.treeContext;
        yg = Lf(e.nextSibling);
        xg = b2;
        I = true;
        zg = null;
        null !== a2 && (og[pg++] = rg, og[pg++] = sg, og[pg++] = qg, rg = a2.id, sg = a2.overflow, qg = b2);
        b2 = qj(b2, d.children);
        b2.flags |= 4096;
        return b2;
      }
      function vj(a2, b2, c2) {
        a2.lanes |= b2;
        var d = a2.alternate;
        null !== d && (d.lanes |= b2);
        bh(a2.return, b2, c2);
      }
      function wj(a2, b2, c2, d, e) {
        var f = a2.memoizedState;
        null === f ? a2.memoizedState = { isBackwards: b2, rendering: null, renderingStartTime: 0, last: d, tail: c2, tailMode: e } : (f.isBackwards = b2, f.rendering = null, f.renderingStartTime = 0, f.last = d, f.tail = c2, f.tailMode = e);
      }
      function xj(a2, b2, c2) {
        var d = b2.pendingProps, e = d.revealOrder, f = d.tail;
        Xi(a2, b2, d.children, c2);
        d = L.current;
        if (0 !== (d & 2)) d = d & 1 | 2, b2.flags |= 128;
        else {
          if (null !== a2 && 0 !== (a2.flags & 128)) a: for (a2 = b2.child; null !== a2; ) {
            if (13 === a2.tag) null !== a2.memoizedState && vj(a2, c2, b2);
            else if (19 === a2.tag) vj(a2, c2, b2);
            else if (null !== a2.child) {
              a2.child.return = a2;
              a2 = a2.child;
              continue;
            }
            if (a2 === b2) break a;
            for (; null === a2.sibling; ) {
              if (null === a2.return || a2.return === b2) break a;
              a2 = a2.return;
            }
            a2.sibling.return = a2.return;
            a2 = a2.sibling;
          }
          d &= 1;
        }
        G(L, d);
        if (0 === (b2.mode & 1)) b2.memoizedState = null;
        else switch (e) {
          case "forwards":
            c2 = b2.child;
            for (e = null; null !== c2; ) a2 = c2.alternate, null !== a2 && null === Ch(a2) && (e = c2), c2 = c2.sibling;
            c2 = e;
            null === c2 ? (e = b2.child, b2.child = null) : (e = c2.sibling, c2.sibling = null);
            wj(b2, false, e, c2, f);
            break;
          case "backwards":
            c2 = null;
            e = b2.child;
            for (b2.child = null; null !== e; ) {
              a2 = e.alternate;
              if (null !== a2 && null === Ch(a2)) {
                b2.child = e;
                break;
              }
              a2 = e.sibling;
              e.sibling = c2;
              c2 = e;
              e = a2;
            }
            wj(b2, true, c2, null, f);
            break;
          case "together":
            wj(b2, false, null, null, void 0);
            break;
          default:
            b2.memoizedState = null;
        }
        return b2.child;
      }
      function ij(a2, b2) {
        0 === (b2.mode & 1) && null !== a2 && (a2.alternate = null, b2.alternate = null, b2.flags |= 2);
      }
      function Zi(a2, b2, c2) {
        null !== a2 && (b2.dependencies = a2.dependencies);
        rh |= b2.lanes;
        if (0 === (c2 & b2.childLanes)) return null;
        if (null !== a2 && b2.child !== a2.child) throw Error(p(153));
        if (null !== b2.child) {
          a2 = b2.child;
          c2 = Pg(a2, a2.pendingProps);
          b2.child = c2;
          for (c2.return = b2; null !== a2.sibling; ) a2 = a2.sibling, c2 = c2.sibling = Pg(a2, a2.pendingProps), c2.return = b2;
          c2.sibling = null;
        }
        return b2.child;
      }
      function yj(a2, b2, c2) {
        switch (b2.tag) {
          case 3:
            kj(b2);
            Ig();
            break;
          case 5:
            Ah(b2);
            break;
          case 1:
            Zf(b2.type) && cg(b2);
            break;
          case 4:
            yh(b2, b2.stateNode.containerInfo);
            break;
          case 10:
            var d = b2.type._context, e = b2.memoizedProps.value;
            G(Wg, d._currentValue);
            d._currentValue = e;
            break;
          case 13:
            d = b2.memoizedState;
            if (null !== d) {
              if (null !== d.dehydrated) return G(L, L.current & 1), b2.flags |= 128, null;
              if (0 !== (c2 & b2.child.childLanes)) return oj(a2, b2, c2);
              G(L, L.current & 1);
              a2 = Zi(a2, b2, c2);
              return null !== a2 ? a2.sibling : null;
            }
            G(L, L.current & 1);
            break;
          case 19:
            d = 0 !== (c2 & b2.childLanes);
            if (0 !== (a2.flags & 128)) {
              if (d) return xj(a2, b2, c2);
              b2.flags |= 128;
            }
            e = b2.memoizedState;
            null !== e && (e.rendering = null, e.tail = null, e.lastEffect = null);
            G(L, L.current);
            if (d) break;
            else return null;
          case 22:
          case 23:
            return b2.lanes = 0, dj(a2, b2, c2);
        }
        return Zi(a2, b2, c2);
      }
      var zj;
      var Aj;
      var Bj;
      var Cj;
      zj = function(a2, b2) {
        for (var c2 = b2.child; null !== c2; ) {
          if (5 === c2.tag || 6 === c2.tag) a2.appendChild(c2.stateNode);
          else if (4 !== c2.tag && null !== c2.child) {
            c2.child.return = c2;
            c2 = c2.child;
            continue;
          }
          if (c2 === b2) break;
          for (; null === c2.sibling; ) {
            if (null === c2.return || c2.return === b2) return;
            c2 = c2.return;
          }
          c2.sibling.return = c2.return;
          c2 = c2.sibling;
        }
      };
      Aj = function() {
      };
      Bj = function(a2, b2, c2, d) {
        var e = a2.memoizedProps;
        if (e !== d) {
          a2 = b2.stateNode;
          xh(uh.current);
          var f = null;
          switch (c2) {
            case "input":
              e = Ya(a2, e);
              d = Ya(a2, d);
              f = [];
              break;
            case "select":
              e = A({}, e, { value: void 0 });
              d = A({}, d, { value: void 0 });
              f = [];
              break;
            case "textarea":
              e = gb(a2, e);
              d = gb(a2, d);
              f = [];
              break;
            default:
              "function" !== typeof e.onClick && "function" === typeof d.onClick && (a2.onclick = Bf);
          }
          ub(c2, d);
          var g;
          c2 = null;
          for (l in e) if (!d.hasOwnProperty(l) && e.hasOwnProperty(l) && null != e[l]) if ("style" === l) {
            var h = e[l];
            for (g in h) h.hasOwnProperty(g) && (c2 || (c2 = {}), c2[g] = "");
          } else "dangerouslySetInnerHTML" !== l && "children" !== l && "suppressContentEditableWarning" !== l && "suppressHydrationWarning" !== l && "autoFocus" !== l && (ea.hasOwnProperty(l) ? f || (f = []) : (f = f || []).push(l, null));
          for (l in d) {
            var k = d[l];
            h = null != e ? e[l] : void 0;
            if (d.hasOwnProperty(l) && k !== h && (null != k || null != h)) if ("style" === l) if (h) {
              for (g in h) !h.hasOwnProperty(g) || k && k.hasOwnProperty(g) || (c2 || (c2 = {}), c2[g] = "");
              for (g in k) k.hasOwnProperty(g) && h[g] !== k[g] && (c2 || (c2 = {}), c2[g] = k[g]);
            } else c2 || (f || (f = []), f.push(
              l,
              c2
            )), c2 = k;
            else "dangerouslySetInnerHTML" === l ? (k = k ? k.__html : void 0, h = h ? h.__html : void 0, null != k && h !== k && (f = f || []).push(l, k)) : "children" === l ? "string" !== typeof k && "number" !== typeof k || (f = f || []).push(l, "" + k) : "suppressContentEditableWarning" !== l && "suppressHydrationWarning" !== l && (ea.hasOwnProperty(l) ? (null != k && "onScroll" === l && D("scroll", a2), f || h === k || (f = [])) : (f = f || []).push(l, k));
          }
          c2 && (f = f || []).push("style", c2);
          var l = f;
          if (b2.updateQueue = l) b2.flags |= 4;
        }
      };
      Cj = function(a2, b2, c2, d) {
        c2 !== d && (b2.flags |= 4);
      };
      function Dj(a2, b2) {
        if (!I) switch (a2.tailMode) {
          case "hidden":
            b2 = a2.tail;
            for (var c2 = null; null !== b2; ) null !== b2.alternate && (c2 = b2), b2 = b2.sibling;
            null === c2 ? a2.tail = null : c2.sibling = null;
            break;
          case "collapsed":
            c2 = a2.tail;
            for (var d = null; null !== c2; ) null !== c2.alternate && (d = c2), c2 = c2.sibling;
            null === d ? b2 || null === a2.tail ? a2.tail = null : a2.tail.sibling = null : d.sibling = null;
        }
      }
      function S(a2) {
        var b2 = null !== a2.alternate && a2.alternate.child === a2.child, c2 = 0, d = 0;
        if (b2) for (var e = a2.child; null !== e; ) c2 |= e.lanes | e.childLanes, d |= e.subtreeFlags & 14680064, d |= e.flags & 14680064, e.return = a2, e = e.sibling;
        else for (e = a2.child; null !== e; ) c2 |= e.lanes | e.childLanes, d |= e.subtreeFlags, d |= e.flags, e.return = a2, e = e.sibling;
        a2.subtreeFlags |= d;
        a2.childLanes = c2;
        return b2;
      }
      function Ej(a2, b2, c2) {
        var d = b2.pendingProps;
        wg(b2);
        switch (b2.tag) {
          case 2:
          case 16:
          case 15:
          case 0:
          case 11:
          case 7:
          case 8:
          case 12:
          case 9:
          case 14:
            return S(b2), null;
          case 1:
            return Zf(b2.type) && $f(), S(b2), null;
          case 3:
            d = b2.stateNode;
            zh();
            E(Wf);
            E(H);
            Eh();
            d.pendingContext && (d.context = d.pendingContext, d.pendingContext = null);
            if (null === a2 || null === a2.child) Gg(b2) ? b2.flags |= 4 : null === a2 || a2.memoizedState.isDehydrated && 0 === (b2.flags & 256) || (b2.flags |= 1024, null !== zg && (Fj(zg), zg = null));
            Aj(a2, b2);
            S(b2);
            return null;
          case 5:
            Bh(b2);
            var e = xh(wh.current);
            c2 = b2.type;
            if (null !== a2 && null != b2.stateNode) Bj(a2, b2, c2, d, e), a2.ref !== b2.ref && (b2.flags |= 512, b2.flags |= 2097152);
            else {
              if (!d) {
                if (null === b2.stateNode) throw Error(p(166));
                S(b2);
                return null;
              }
              a2 = xh(uh.current);
              if (Gg(b2)) {
                d = b2.stateNode;
                c2 = b2.type;
                var f = b2.memoizedProps;
                d[Of] = b2;
                d[Pf] = f;
                a2 = 0 !== (b2.mode & 1);
                switch (c2) {
                  case "dialog":
                    D("cancel", d);
                    D("close", d);
                    break;
                  case "iframe":
                  case "object":
                  case "embed":
                    D("load", d);
                    break;
                  case "video":
                  case "audio":
                    for (e = 0; e < lf.length; e++) D(lf[e], d);
                    break;
                  case "source":
                    D("error", d);
                    break;
                  case "img":
                  case "image":
                  case "link":
                    D(
                      "error",
                      d
                    );
                    D("load", d);
                    break;
                  case "details":
                    D("toggle", d);
                    break;
                  case "input":
                    Za(d, f);
                    D("invalid", d);
                    break;
                  case "select":
                    d._wrapperState = { wasMultiple: !!f.multiple };
                    D("invalid", d);
                    break;
                  case "textarea":
                    hb(d, f), D("invalid", d);
                }
                ub(c2, f);
                e = null;
                for (var g in f) if (f.hasOwnProperty(g)) {
                  var h = f[g];
                  "children" === g ? "string" === typeof h ? d.textContent !== h && (true !== f.suppressHydrationWarning && Af(d.textContent, h, a2), e = ["children", h]) : "number" === typeof h && d.textContent !== "" + h && (true !== f.suppressHydrationWarning && Af(
                    d.textContent,
                    h,
                    a2
                  ), e = ["children", "" + h]) : ea.hasOwnProperty(g) && null != h && "onScroll" === g && D("scroll", d);
                }
                switch (c2) {
                  case "input":
                    Va(d);
                    db(d, f, true);
                    break;
                  case "textarea":
                    Va(d);
                    jb(d);
                    break;
                  case "select":
                  case "option":
                    break;
                  default:
                    "function" === typeof f.onClick && (d.onclick = Bf);
                }
                d = e;
                b2.updateQueue = d;
                null !== d && (b2.flags |= 4);
              } else {
                g = 9 === e.nodeType ? e : e.ownerDocument;
                "http://www.w3.org/1999/xhtml" === a2 && (a2 = kb(c2));
                "http://www.w3.org/1999/xhtml" === a2 ? "script" === c2 ? (a2 = g.createElement("div"), a2.innerHTML = "<script><\/script>", a2 = a2.removeChild(a2.firstChild)) : "string" === typeof d.is ? a2 = g.createElement(c2, { is: d.is }) : (a2 = g.createElement(c2), "select" === c2 && (g = a2, d.multiple ? g.multiple = true : d.size && (g.size = d.size))) : a2 = g.createElementNS(a2, c2);
                a2[Of] = b2;
                a2[Pf] = d;
                zj(a2, b2, false, false);
                b2.stateNode = a2;
                a: {
                  g = vb(c2, d);
                  switch (c2) {
                    case "dialog":
                      D("cancel", a2);
                      D("close", a2);
                      e = d;
                      break;
                    case "iframe":
                    case "object":
                    case "embed":
                      D("load", a2);
                      e = d;
                      break;
                    case "video":
                    case "audio":
                      for (e = 0; e < lf.length; e++) D(lf[e], a2);
                      e = d;
                      break;
                    case "source":
                      D("error", a2);
                      e = d;
                      break;
                    case "img":
                    case "image":
                    case "link":
                      D(
                        "error",
                        a2
                      );
                      D("load", a2);
                      e = d;
                      break;
                    case "details":
                      D("toggle", a2);
                      e = d;
                      break;
                    case "input":
                      Za(a2, d);
                      e = Ya(a2, d);
                      D("invalid", a2);
                      break;
                    case "option":
                      e = d;
                      break;
                    case "select":
                      a2._wrapperState = { wasMultiple: !!d.multiple };
                      e = A({}, d, { value: void 0 });
                      D("invalid", a2);
                      break;
                    case "textarea":
                      hb(a2, d);
                      e = gb(a2, d);
                      D("invalid", a2);
                      break;
                    default:
                      e = d;
                  }
                  ub(c2, e);
                  h = e;
                  for (f in h) if (h.hasOwnProperty(f)) {
                    var k = h[f];
                    "style" === f ? sb(a2, k) : "dangerouslySetInnerHTML" === f ? (k = k ? k.__html : void 0, null != k && nb(a2, k)) : "children" === f ? "string" === typeof k ? ("textarea" !== c2 || "" !== k) && ob(a2, k) : "number" === typeof k && ob(a2, "" + k) : "suppressContentEditableWarning" !== f && "suppressHydrationWarning" !== f && "autoFocus" !== f && (ea.hasOwnProperty(f) ? null != k && "onScroll" === f && D("scroll", a2) : null != k && ta(a2, f, k, g));
                  }
                  switch (c2) {
                    case "input":
                      Va(a2);
                      db(a2, d, false);
                      break;
                    case "textarea":
                      Va(a2);
                      jb(a2);
                      break;
                    case "option":
                      null != d.value && a2.setAttribute("value", "" + Sa(d.value));
                      break;
                    case "select":
                      a2.multiple = !!d.multiple;
                      f = d.value;
                      null != f ? fb(a2, !!d.multiple, f, false) : null != d.defaultValue && fb(
                        a2,
                        !!d.multiple,
                        d.defaultValue,
                        true
                      );
                      break;
                    default:
                      "function" === typeof e.onClick && (a2.onclick = Bf);
                  }
                  switch (c2) {
                    case "button":
                    case "input":
                    case "select":
                    case "textarea":
                      d = !!d.autoFocus;
                      break a;
                    case "img":
                      d = true;
                      break a;
                    default:
                      d = false;
                  }
                }
                d && (b2.flags |= 4);
              }
              null !== b2.ref && (b2.flags |= 512, b2.flags |= 2097152);
            }
            S(b2);
            return null;
          case 6:
            if (a2 && null != b2.stateNode) Cj(a2, b2, a2.memoizedProps, d);
            else {
              if ("string" !== typeof d && null === b2.stateNode) throw Error(p(166));
              c2 = xh(wh.current);
              xh(uh.current);
              if (Gg(b2)) {
                d = b2.stateNode;
                c2 = b2.memoizedProps;
                d[Of] = b2;
                if (f = d.nodeValue !== c2) {
                  if (a2 = xg, null !== a2) switch (a2.tag) {
                    case 3:
                      Af(d.nodeValue, c2, 0 !== (a2.mode & 1));
                      break;
                    case 5:
                      true !== a2.memoizedProps.suppressHydrationWarning && Af(d.nodeValue, c2, 0 !== (a2.mode & 1));
                  }
                }
                f && (b2.flags |= 4);
              } else d = (9 === c2.nodeType ? c2 : c2.ownerDocument).createTextNode(d), d[Of] = b2, b2.stateNode = d;
            }
            S(b2);
            return null;
          case 13:
            E(L);
            d = b2.memoizedState;
            if (null === a2 || null !== a2.memoizedState && null !== a2.memoizedState.dehydrated) {
              if (I && null !== yg && 0 !== (b2.mode & 1) && 0 === (b2.flags & 128)) Hg(), Ig(), b2.flags |= 98560, f = false;
              else if (f = Gg(b2), null !== d && null !== d.dehydrated) {
                if (null === a2) {
                  if (!f) throw Error(p(318));
                  f = b2.memoizedState;
                  f = null !== f ? f.dehydrated : null;
                  if (!f) throw Error(p(317));
                  f[Of] = b2;
                } else Ig(), 0 === (b2.flags & 128) && (b2.memoizedState = null), b2.flags |= 4;
                S(b2);
                f = false;
              } else null !== zg && (Fj(zg), zg = null), f = true;
              if (!f) return b2.flags & 65536 ? b2 : null;
            }
            if (0 !== (b2.flags & 128)) return b2.lanes = c2, b2;
            d = null !== d;
            d !== (null !== a2 && null !== a2.memoizedState) && d && (b2.child.flags |= 8192, 0 !== (b2.mode & 1) && (null === a2 || 0 !== (L.current & 1) ? 0 === T && (T = 3) : tj()));
            null !== b2.updateQueue && (b2.flags |= 4);
            S(b2);
            return null;
          case 4:
            return zh(), Aj(a2, b2), null === a2 && sf(b2.stateNode.containerInfo), S(b2), null;
          case 10:
            return ah(b2.type._context), S(b2), null;
          case 17:
            return Zf(b2.type) && $f(), S(b2), null;
          case 19:
            E(L);
            f = b2.memoizedState;
            if (null === f) return S(b2), null;
            d = 0 !== (b2.flags & 128);
            g = f.rendering;
            if (null === g) if (d) Dj(f, false);
            else {
              if (0 !== T || null !== a2 && 0 !== (a2.flags & 128)) for (a2 = b2.child; null !== a2; ) {
                g = Ch(a2);
                if (null !== g) {
                  b2.flags |= 128;
                  Dj(f, false);
                  d = g.updateQueue;
                  null !== d && (b2.updateQueue = d, b2.flags |= 4);
                  b2.subtreeFlags = 0;
                  d = c2;
                  for (c2 = b2.child; null !== c2; ) f = c2, a2 = d, f.flags &= 14680066, g = f.alternate, null === g ? (f.childLanes = 0, f.lanes = a2, f.child = null, f.subtreeFlags = 0, f.memoizedProps = null, f.memoizedState = null, f.updateQueue = null, f.dependencies = null, f.stateNode = null) : (f.childLanes = g.childLanes, f.lanes = g.lanes, f.child = g.child, f.subtreeFlags = 0, f.deletions = null, f.memoizedProps = g.memoizedProps, f.memoizedState = g.memoizedState, f.updateQueue = g.updateQueue, f.type = g.type, a2 = g.dependencies, f.dependencies = null === a2 ? null : { lanes: a2.lanes, firstContext: a2.firstContext }), c2 = c2.sibling;
                  G(L, L.current & 1 | 2);
                  return b2.child;
                }
                a2 = a2.sibling;
              }
              null !== f.tail && B() > Gj && (b2.flags |= 128, d = true, Dj(f, false), b2.lanes = 4194304);
            }
            else {
              if (!d) if (a2 = Ch(g), null !== a2) {
                if (b2.flags |= 128, d = true, c2 = a2.updateQueue, null !== c2 && (b2.updateQueue = c2, b2.flags |= 4), Dj(f, true), null === f.tail && "hidden" === f.tailMode && !g.alternate && !I) return S(b2), null;
              } else 2 * B() - f.renderingStartTime > Gj && 1073741824 !== c2 && (b2.flags |= 128, d = true, Dj(f, false), b2.lanes = 4194304);
              f.isBackwards ? (g.sibling = b2.child, b2.child = g) : (c2 = f.last, null !== c2 ? c2.sibling = g : b2.child = g, f.last = g);
            }
            if (null !== f.tail) return b2 = f.tail, f.rendering = b2, f.tail = b2.sibling, f.renderingStartTime = B(), b2.sibling = null, c2 = L.current, G(L, d ? c2 & 1 | 2 : c2 & 1), b2;
            S(b2);
            return null;
          case 22:
          case 23:
            return Hj(), d = null !== b2.memoizedState, null !== a2 && null !== a2.memoizedState !== d && (b2.flags |= 8192), d && 0 !== (b2.mode & 1) ? 0 !== (fj & 1073741824) && (S(b2), b2.subtreeFlags & 6 && (b2.flags |= 8192)) : S(b2), null;
          case 24:
            return null;
          case 25:
            return null;
        }
        throw Error(p(156, b2.tag));
      }
      function Ij(a2, b2) {
        wg(b2);
        switch (b2.tag) {
          case 1:
            return Zf(b2.type) && $f(), a2 = b2.flags, a2 & 65536 ? (b2.flags = a2 & -65537 | 128, b2) : null;
          case 3:
            return zh(), E(Wf), E(H), Eh(), a2 = b2.flags, 0 !== (a2 & 65536) && 0 === (a2 & 128) ? (b2.flags = a2 & -65537 | 128, b2) : null;
          case 5:
            return Bh(b2), null;
          case 13:
            E(L);
            a2 = b2.memoizedState;
            if (null !== a2 && null !== a2.dehydrated) {
              if (null === b2.alternate) throw Error(p(340));
              Ig();
            }
            a2 = b2.flags;
            return a2 & 65536 ? (b2.flags = a2 & -65537 | 128, b2) : null;
          case 19:
            return E(L), null;
          case 4:
            return zh(), null;
          case 10:
            return ah(b2.type._context), null;
          case 22:
          case 23:
            return Hj(), null;
          case 24:
            return null;
          default:
            return null;
        }
      }
      var Jj = false;
      var U = false;
      var Kj = "function" === typeof WeakSet ? WeakSet : Set;
      var V = null;
      function Lj(a2, b2) {
        var c2 = a2.ref;
        if (null !== c2) if ("function" === typeof c2) try {
          c2(null);
        } catch (d) {
          W(a2, b2, d);
        }
        else c2.current = null;
      }
      function Mj(a2, b2, c2) {
        try {
          c2();
        } catch (d) {
          W(a2, b2, d);
        }
      }
      var Nj = false;
      function Oj(a2, b2) {
        Cf = dd;
        a2 = Me();
        if (Ne(a2)) {
          if ("selectionStart" in a2) var c2 = { start: a2.selectionStart, end: a2.selectionEnd };
          else a: {
            c2 = (c2 = a2.ownerDocument) && c2.defaultView || window;
            var d = c2.getSelection && c2.getSelection();
            if (d && 0 !== d.rangeCount) {
              c2 = d.anchorNode;
              var e = d.anchorOffset, f = d.focusNode;
              d = d.focusOffset;
              try {
                c2.nodeType, f.nodeType;
              } catch (F) {
                c2 = null;
                break a;
              }
              var g = 0, h = -1, k = -1, l = 0, m = 0, q = a2, r = null;
              b: for (; ; ) {
                for (var y; ; ) {
                  q !== c2 || 0 !== e && 3 !== q.nodeType || (h = g + e);
                  q !== f || 0 !== d && 3 !== q.nodeType || (k = g + d);
                  3 === q.nodeType && (g += q.nodeValue.length);
                  if (null === (y = q.firstChild)) break;
                  r = q;
                  q = y;
                }
                for (; ; ) {
                  if (q === a2) break b;
                  r === c2 && ++l === e && (h = g);
                  r === f && ++m === d && (k = g);
                  if (null !== (y = q.nextSibling)) break;
                  q = r;
                  r = q.parentNode;
                }
                q = y;
              }
              c2 = -1 === h || -1 === k ? null : { start: h, end: k };
            } else c2 = null;
          }
          c2 = c2 || { start: 0, end: 0 };
        } else c2 = null;
        Df = { focusedElem: a2, selectionRange: c2 };
        dd = false;
        for (V = b2; null !== V; ) if (b2 = V, a2 = b2.child, 0 !== (b2.subtreeFlags & 1028) && null !== a2) a2.return = b2, V = a2;
        else for (; null !== V; ) {
          b2 = V;
          try {
            var n = b2.alternate;
            if (0 !== (b2.flags & 1024)) switch (b2.tag) {
              case 0:
              case 11:
              case 15:
                break;
              case 1:
                if (null !== n) {
                  var t = n.memoizedProps, J = n.memoizedState, x = b2.stateNode, w = x.getSnapshotBeforeUpdate(b2.elementType === b2.type ? t : Ci(b2.type, t), J);
                  x.__reactInternalSnapshotBeforeUpdate = w;
                }
                break;
              case 3:
                var u = b2.stateNode.containerInfo;
                1 === u.nodeType ? u.textContent = "" : 9 === u.nodeType && u.documentElement && u.removeChild(u.documentElement);
                break;
              case 5:
              case 6:
              case 4:
              case 17:
                break;
              default:
                throw Error(p(163));
            }
          } catch (F) {
            W(b2, b2.return, F);
          }
          a2 = b2.sibling;
          if (null !== a2) {
            a2.return = b2.return;
            V = a2;
            break;
          }
          V = b2.return;
        }
        n = Nj;
        Nj = false;
        return n;
      }
      function Pj(a2, b2, c2) {
        var d = b2.updateQueue;
        d = null !== d ? d.lastEffect : null;
        if (null !== d) {
          var e = d = d.next;
          do {
            if ((e.tag & a2) === a2) {
              var f = e.destroy;
              e.destroy = void 0;
              void 0 !== f && Mj(b2, c2, f);
            }
            e = e.next;
          } while (e !== d);
        }
      }
      function Qj(a2, b2) {
        b2 = b2.updateQueue;
        b2 = null !== b2 ? b2.lastEffect : null;
        if (null !== b2) {
          var c2 = b2 = b2.next;
          do {
            if ((c2.tag & a2) === a2) {
              var d = c2.create;
              c2.destroy = d();
            }
            c2 = c2.next;
          } while (c2 !== b2);
        }
      }
      function Rj(a2) {
        var b2 = a2.ref;
        if (null !== b2) {
          var c2 = a2.stateNode;
          switch (a2.tag) {
            case 5:
              a2 = c2;
              break;
            default:
              a2 = c2;
          }
          "function" === typeof b2 ? b2(a2) : b2.current = a2;
        }
      }
      function Sj(a2) {
        var b2 = a2.alternate;
        null !== b2 && (a2.alternate = null, Sj(b2));
        a2.child = null;
        a2.deletions = null;
        a2.sibling = null;
        5 === a2.tag && (b2 = a2.stateNode, null !== b2 && (delete b2[Of], delete b2[Pf], delete b2[of], delete b2[Qf], delete b2[Rf]));
        a2.stateNode = null;
        a2.return = null;
        a2.dependencies = null;
        a2.memoizedProps = null;
        a2.memoizedState = null;
        a2.pendingProps = null;
        a2.stateNode = null;
        a2.updateQueue = null;
      }
      function Tj(a2) {
        return 5 === a2.tag || 3 === a2.tag || 4 === a2.tag;
      }
      function Uj(a2) {
        a: for (; ; ) {
          for (; null === a2.sibling; ) {
            if (null === a2.return || Tj(a2.return)) return null;
            a2 = a2.return;
          }
          a2.sibling.return = a2.return;
          for (a2 = a2.sibling; 5 !== a2.tag && 6 !== a2.tag && 18 !== a2.tag; ) {
            if (a2.flags & 2) continue a;
            if (null === a2.child || 4 === a2.tag) continue a;
            else a2.child.return = a2, a2 = a2.child;
          }
          if (!(a2.flags & 2)) return a2.stateNode;
        }
      }
      function Vj(a2, b2, c2) {
        var d = a2.tag;
        if (5 === d || 6 === d) a2 = a2.stateNode, b2 ? 8 === c2.nodeType ? c2.parentNode.insertBefore(a2, b2) : c2.insertBefore(a2, b2) : (8 === c2.nodeType ? (b2 = c2.parentNode, b2.insertBefore(a2, c2)) : (b2 = c2, b2.appendChild(a2)), c2 = c2._reactRootContainer, null !== c2 && void 0 !== c2 || null !== b2.onclick || (b2.onclick = Bf));
        else if (4 !== d && (a2 = a2.child, null !== a2)) for (Vj(a2, b2, c2), a2 = a2.sibling; null !== a2; ) Vj(a2, b2, c2), a2 = a2.sibling;
      }
      function Wj(a2, b2, c2) {
        var d = a2.tag;
        if (5 === d || 6 === d) a2 = a2.stateNode, b2 ? c2.insertBefore(a2, b2) : c2.appendChild(a2);
        else if (4 !== d && (a2 = a2.child, null !== a2)) for (Wj(a2, b2, c2), a2 = a2.sibling; null !== a2; ) Wj(a2, b2, c2), a2 = a2.sibling;
      }
      var X = null;
      var Xj = false;
      function Yj(a2, b2, c2) {
        for (c2 = c2.child; null !== c2; ) Zj(a2, b2, c2), c2 = c2.sibling;
      }
      function Zj(a2, b2, c2) {
        if (lc && "function" === typeof lc.onCommitFiberUnmount) try {
          lc.onCommitFiberUnmount(kc, c2);
        } catch (h) {
        }
        switch (c2.tag) {
          case 5:
            U || Lj(c2, b2);
          case 6:
            var d = X, e = Xj;
            X = null;
            Yj(a2, b2, c2);
            X = d;
            Xj = e;
            null !== X && (Xj ? (a2 = X, c2 = c2.stateNode, 8 === a2.nodeType ? a2.parentNode.removeChild(c2) : a2.removeChild(c2)) : X.removeChild(c2.stateNode));
            break;
          case 18:
            null !== X && (Xj ? (a2 = X, c2 = c2.stateNode, 8 === a2.nodeType ? Kf(a2.parentNode, c2) : 1 === a2.nodeType && Kf(a2, c2), bd(a2)) : Kf(X, c2.stateNode));
            break;
          case 4:
            d = X;
            e = Xj;
            X = c2.stateNode.containerInfo;
            Xj = true;
            Yj(a2, b2, c2);
            X = d;
            Xj = e;
            break;
          case 0:
          case 11:
          case 14:
          case 15:
            if (!U && (d = c2.updateQueue, null !== d && (d = d.lastEffect, null !== d))) {
              e = d = d.next;
              do {
                var f = e, g = f.destroy;
                f = f.tag;
                void 0 !== g && (0 !== (f & 2) ? Mj(c2, b2, g) : 0 !== (f & 4) && Mj(c2, b2, g));
                e = e.next;
              } while (e !== d);
            }
            Yj(a2, b2, c2);
            break;
          case 1:
            if (!U && (Lj(c2, b2), d = c2.stateNode, "function" === typeof d.componentWillUnmount)) try {
              d.props = c2.memoizedProps, d.state = c2.memoizedState, d.componentWillUnmount();
            } catch (h) {
              W(c2, b2, h);
            }
            Yj(a2, b2, c2);
            break;
          case 21:
            Yj(a2, b2, c2);
            break;
          case 22:
            c2.mode & 1 ? (U = (d = U) || null !== c2.memoizedState, Yj(a2, b2, c2), U = d) : Yj(a2, b2, c2);
            break;
          default:
            Yj(a2, b2, c2);
        }
      }
      function ak(a2) {
        var b2 = a2.updateQueue;
        if (null !== b2) {
          a2.updateQueue = null;
          var c2 = a2.stateNode;
          null === c2 && (c2 = a2.stateNode = new Kj());
          b2.forEach(function(b3) {
            var d = bk.bind(null, a2, b3);
            c2.has(b3) || (c2.add(b3), b3.then(d, d));
          });
        }
      }
      function ck(a2, b2) {
        var c2 = b2.deletions;
        if (null !== c2) for (var d = 0; d < c2.length; d++) {
          var e = c2[d];
          try {
            var f = a2, g = b2, h = g;
            a: for (; null !== h; ) {
              switch (h.tag) {
                case 5:
                  X = h.stateNode;
                  Xj = false;
                  break a;
                case 3:
                  X = h.stateNode.containerInfo;
                  Xj = true;
                  break a;
                case 4:
                  X = h.stateNode.containerInfo;
                  Xj = true;
                  break a;
              }
              h = h.return;
            }
            if (null === X) throw Error(p(160));
            Zj(f, g, e);
            X = null;
            Xj = false;
            var k = e.alternate;
            null !== k && (k.return = null);
            e.return = null;
          } catch (l) {
            W(e, b2, l);
          }
        }
        if (b2.subtreeFlags & 12854) for (b2 = b2.child; null !== b2; ) dk(b2, a2), b2 = b2.sibling;
      }
      function dk(a2, b2) {
        var c2 = a2.alternate, d = a2.flags;
        switch (a2.tag) {
          case 0:
          case 11:
          case 14:
          case 15:
            ck(b2, a2);
            ek(a2);
            if (d & 4) {
              try {
                Pj(3, a2, a2.return), Qj(3, a2);
              } catch (t) {
                W(a2, a2.return, t);
              }
              try {
                Pj(5, a2, a2.return);
              } catch (t) {
                W(a2, a2.return, t);
              }
            }
            break;
          case 1:
            ck(b2, a2);
            ek(a2);
            d & 512 && null !== c2 && Lj(c2, c2.return);
            break;
          case 5:
            ck(b2, a2);
            ek(a2);
            d & 512 && null !== c2 && Lj(c2, c2.return);
            if (a2.flags & 32) {
              var e = a2.stateNode;
              try {
                ob(e, "");
              } catch (t) {
                W(a2, a2.return, t);
              }
            }
            if (d & 4 && (e = a2.stateNode, null != e)) {
              var f = a2.memoizedProps, g = null !== c2 ? c2.memoizedProps : f, h = a2.type, k = a2.updateQueue;
              a2.updateQueue = null;
              if (null !== k) try {
                "input" === h && "radio" === f.type && null != f.name && ab(e, f);
                vb(h, g);
                var l = vb(h, f);
                for (g = 0; g < k.length; g += 2) {
                  var m = k[g], q = k[g + 1];
                  "style" === m ? sb(e, q) : "dangerouslySetInnerHTML" === m ? nb(e, q) : "children" === m ? ob(e, q) : ta(e, m, q, l);
                }
                switch (h) {
                  case "input":
                    bb(e, f);
                    break;
                  case "textarea":
                    ib(e, f);
                    break;
                  case "select":
                    var r = e._wrapperState.wasMultiple;
                    e._wrapperState.wasMultiple = !!f.multiple;
                    var y = f.value;
                    null != y ? fb(e, !!f.multiple, y, false) : r !== !!f.multiple && (null != f.defaultValue ? fb(
                      e,
                      !!f.multiple,
                      f.defaultValue,
                      true
                    ) : fb(e, !!f.multiple, f.multiple ? [] : "", false));
                }
                e[Pf] = f;
              } catch (t) {
                W(a2, a2.return, t);
              }
            }
            break;
          case 6:
            ck(b2, a2);
            ek(a2);
            if (d & 4) {
              if (null === a2.stateNode) throw Error(p(162));
              e = a2.stateNode;
              f = a2.memoizedProps;
              try {
                e.nodeValue = f;
              } catch (t) {
                W(a2, a2.return, t);
              }
            }
            break;
          case 3:
            ck(b2, a2);
            ek(a2);
            if (d & 4 && null !== c2 && c2.memoizedState.isDehydrated) try {
              bd(b2.containerInfo);
            } catch (t) {
              W(a2, a2.return, t);
            }
            break;
          case 4:
            ck(b2, a2);
            ek(a2);
            break;
          case 13:
            ck(b2, a2);
            ek(a2);
            e = a2.child;
            e.flags & 8192 && (f = null !== e.memoizedState, e.stateNode.isHidden = f, !f || null !== e.alternate && null !== e.alternate.memoizedState || (fk = B()));
            d & 4 && ak(a2);
            break;
          case 22:
            m = null !== c2 && null !== c2.memoizedState;
            a2.mode & 1 ? (U = (l = U) || m, ck(b2, a2), U = l) : ck(b2, a2);
            ek(a2);
            if (d & 8192) {
              l = null !== a2.memoizedState;
              if ((a2.stateNode.isHidden = l) && !m && 0 !== (a2.mode & 1)) for (V = a2, m = a2.child; null !== m; ) {
                for (q = V = m; null !== V; ) {
                  r = V;
                  y = r.child;
                  switch (r.tag) {
                    case 0:
                    case 11:
                    case 14:
                    case 15:
                      Pj(4, r, r.return);
                      break;
                    case 1:
                      Lj(r, r.return);
                      var n = r.stateNode;
                      if ("function" === typeof n.componentWillUnmount) {
                        d = r;
                        c2 = r.return;
                        try {
                          b2 = d, n.props = b2.memoizedProps, n.state = b2.memoizedState, n.componentWillUnmount();
                        } catch (t) {
                          W(d, c2, t);
                        }
                      }
                      break;
                    case 5:
                      Lj(r, r.return);
                      break;
                    case 22:
                      if (null !== r.memoizedState) {
                        gk(q);
                        continue;
                      }
                  }
                  null !== y ? (y.return = r, V = y) : gk(q);
                }
                m = m.sibling;
              }
              a: for (m = null, q = a2; ; ) {
                if (5 === q.tag) {
                  if (null === m) {
                    m = q;
                    try {
                      e = q.stateNode, l ? (f = e.style, "function" === typeof f.setProperty ? f.setProperty("display", "none", "important") : f.display = "none") : (h = q.stateNode, k = q.memoizedProps.style, g = void 0 !== k && null !== k && k.hasOwnProperty("display") ? k.display : null, h.style.display = rb("display", g));
                    } catch (t) {
                      W(a2, a2.return, t);
                    }
                  }
                } else if (6 === q.tag) {
                  if (null === m) try {
                    q.stateNode.nodeValue = l ? "" : q.memoizedProps;
                  } catch (t) {
                    W(a2, a2.return, t);
                  }
                } else if ((22 !== q.tag && 23 !== q.tag || null === q.memoizedState || q === a2) && null !== q.child) {
                  q.child.return = q;
                  q = q.child;
                  continue;
                }
                if (q === a2) break a;
                for (; null === q.sibling; ) {
                  if (null === q.return || q.return === a2) break a;
                  m === q && (m = null);
                  q = q.return;
                }
                m === q && (m = null);
                q.sibling.return = q.return;
                q = q.sibling;
              }
            }
            break;
          case 19:
            ck(b2, a2);
            ek(a2);
            d & 4 && ak(a2);
            break;
          case 21:
            break;
          default:
            ck(
              b2,
              a2
            ), ek(a2);
        }
      }
      function ek(a2) {
        var b2 = a2.flags;
        if (b2 & 2) {
          try {
            a: {
              for (var c2 = a2.return; null !== c2; ) {
                if (Tj(c2)) {
                  var d = c2;
                  break a;
                }
                c2 = c2.return;
              }
              throw Error(p(160));
            }
            switch (d.tag) {
              case 5:
                var e = d.stateNode;
                d.flags & 32 && (ob(e, ""), d.flags &= -33);
                var f = Uj(a2);
                Wj(a2, f, e);
                break;
              case 3:
              case 4:
                var g = d.stateNode.containerInfo, h = Uj(a2);
                Vj(a2, h, g);
                break;
              default:
                throw Error(p(161));
            }
          } catch (k) {
            W(a2, a2.return, k);
          }
          a2.flags &= -3;
        }
        b2 & 4096 && (a2.flags &= -4097);
      }
      function hk(a2, b2, c2) {
        V = a2;
        ik(a2, b2, c2);
      }
      function ik(a2, b2, c2) {
        for (var d = 0 !== (a2.mode & 1); null !== V; ) {
          var e = V, f = e.child;
          if (22 === e.tag && d) {
            var g = null !== e.memoizedState || Jj;
            if (!g) {
              var h = e.alternate, k = null !== h && null !== h.memoizedState || U;
              h = Jj;
              var l = U;
              Jj = g;
              if ((U = k) && !l) for (V = e; null !== V; ) g = V, k = g.child, 22 === g.tag && null !== g.memoizedState ? jk(e) : null !== k ? (k.return = g, V = k) : jk(e);
              for (; null !== f; ) V = f, ik(f, b2, c2), f = f.sibling;
              V = e;
              Jj = h;
              U = l;
            }
            kk(a2, b2, c2);
          } else 0 !== (e.subtreeFlags & 8772) && null !== f ? (f.return = e, V = f) : kk(a2, b2, c2);
        }
      }
      function kk(a2) {
        for (; null !== V; ) {
          var b2 = V;
          if (0 !== (b2.flags & 8772)) {
            var c2 = b2.alternate;
            try {
              if (0 !== (b2.flags & 8772)) switch (b2.tag) {
                case 0:
                case 11:
                case 15:
                  U || Qj(5, b2);
                  break;
                case 1:
                  var d = b2.stateNode;
                  if (b2.flags & 4 && !U) if (null === c2) d.componentDidMount();
                  else {
                    var e = b2.elementType === b2.type ? c2.memoizedProps : Ci(b2.type, c2.memoizedProps);
                    d.componentDidUpdate(e, c2.memoizedState, d.__reactInternalSnapshotBeforeUpdate);
                  }
                  var f = b2.updateQueue;
                  null !== f && sh(b2, f, d);
                  break;
                case 3:
                  var g = b2.updateQueue;
                  if (null !== g) {
                    c2 = null;
                    if (null !== b2.child) switch (b2.child.tag) {
                      case 5:
                        c2 = b2.child.stateNode;
                        break;
                      case 1:
                        c2 = b2.child.stateNode;
                    }
                    sh(b2, g, c2);
                  }
                  break;
                case 5:
                  var h = b2.stateNode;
                  if (null === c2 && b2.flags & 4) {
                    c2 = h;
                    var k = b2.memoizedProps;
                    switch (b2.type) {
                      case "button":
                      case "input":
                      case "select":
                      case "textarea":
                        k.autoFocus && c2.focus();
                        break;
                      case "img":
                        k.src && (c2.src = k.src);
                    }
                  }
                  break;
                case 6:
                  break;
                case 4:
                  break;
                case 12:
                  break;
                case 13:
                  if (null === b2.memoizedState) {
                    var l = b2.alternate;
                    if (null !== l) {
                      var m = l.memoizedState;
                      if (null !== m) {
                        var q = m.dehydrated;
                        null !== q && bd(q);
                      }
                    }
                  }
                  break;
                case 19:
                case 17:
                case 21:
                case 22:
                case 23:
                case 25:
                  break;
                default:
                  throw Error(p(163));
              }
              U || b2.flags & 512 && Rj(b2);
            } catch (r) {
              W(b2, b2.return, r);
            }
          }
          if (b2 === a2) {
            V = null;
            break;
          }
          c2 = b2.sibling;
          if (null !== c2) {
            c2.return = b2.return;
            V = c2;
            break;
          }
          V = b2.return;
        }
      }
      function gk(a2) {
        for (; null !== V; ) {
          var b2 = V;
          if (b2 === a2) {
            V = null;
            break;
          }
          var c2 = b2.sibling;
          if (null !== c2) {
            c2.return = b2.return;
            V = c2;
            break;
          }
          V = b2.return;
        }
      }
      function jk(a2) {
        for (; null !== V; ) {
          var b2 = V;
          try {
            switch (b2.tag) {
              case 0:
              case 11:
              case 15:
                var c2 = b2.return;
                try {
                  Qj(4, b2);
                } catch (k) {
                  W(b2, c2, k);
                }
                break;
              case 1:
                var d = b2.stateNode;
                if ("function" === typeof d.componentDidMount) {
                  var e = b2.return;
                  try {
                    d.componentDidMount();
                  } catch (k) {
                    W(b2, e, k);
                  }
                }
                var f = b2.return;
                try {
                  Rj(b2);
                } catch (k) {
                  W(b2, f, k);
                }
                break;
              case 5:
                var g = b2.return;
                try {
                  Rj(b2);
                } catch (k) {
                  W(b2, g, k);
                }
            }
          } catch (k) {
            W(b2, b2.return, k);
          }
          if (b2 === a2) {
            V = null;
            break;
          }
          var h = b2.sibling;
          if (null !== h) {
            h.return = b2.return;
            V = h;
            break;
          }
          V = b2.return;
        }
      }
      var lk = Math.ceil;
      var mk = ua.ReactCurrentDispatcher;
      var nk = ua.ReactCurrentOwner;
      var ok = ua.ReactCurrentBatchConfig;
      var K = 0;
      var Q = null;
      var Y = null;
      var Z = 0;
      var fj = 0;
      var ej = Uf(0);
      var T = 0;
      var pk = null;
      var rh = 0;
      var qk = 0;
      var rk = 0;
      var sk = null;
      var tk = null;
      var fk = 0;
      var Gj = Infinity;
      var uk = null;
      var Oi = false;
      var Pi = null;
      var Ri = null;
      var vk = false;
      var wk = null;
      var xk = 0;
      var yk = 0;
      var zk = null;
      var Ak = -1;
      var Bk = 0;
      function R() {
        return 0 !== (K & 6) ? B() : -1 !== Ak ? Ak : Ak = B();
      }
      function yi(a2) {
        if (0 === (a2.mode & 1)) return 1;
        if (0 !== (K & 2) && 0 !== Z) return Z & -Z;
        if (null !== Kg.transition) return 0 === Bk && (Bk = yc()), Bk;
        a2 = C;
        if (0 !== a2) return a2;
        a2 = window.event;
        a2 = void 0 === a2 ? 16 : jd(a2.type);
        return a2;
      }
      function gi(a2, b2, c2, d) {
        if (50 < yk) throw yk = 0, zk = null, Error(p(185));
        Ac(a2, c2, d);
        if (0 === (K & 2) || a2 !== Q) a2 === Q && (0 === (K & 2) && (qk |= c2), 4 === T && Ck(a2, Z)), Dk(a2, d), 1 === c2 && 0 === K && 0 === (b2.mode & 1) && (Gj = B() + 500, fg && jg());
      }
      function Dk(a2, b2) {
        var c2 = a2.callbackNode;
        wc(a2, b2);
        var d = uc(a2, a2 === Q ? Z : 0);
        if (0 === d) null !== c2 && bc(c2), a2.callbackNode = null, a2.callbackPriority = 0;
        else if (b2 = d & -d, a2.callbackPriority !== b2) {
          null != c2 && bc(c2);
          if (1 === b2) 0 === a2.tag ? ig(Ek.bind(null, a2)) : hg(Ek.bind(null, a2)), Jf(function() {
            0 === (K & 6) && jg();
          }), c2 = null;
          else {
            switch (Dc(d)) {
              case 1:
                c2 = fc;
                break;
              case 4:
                c2 = gc;
                break;
              case 16:
                c2 = hc;
                break;
              case 536870912:
                c2 = jc;
                break;
              default:
                c2 = hc;
            }
            c2 = Fk(c2, Gk.bind(null, a2));
          }
          a2.callbackPriority = b2;
          a2.callbackNode = c2;
        }
      }
      function Gk(a2, b2) {
        Ak = -1;
        Bk = 0;
        if (0 !== (K & 6)) throw Error(p(327));
        var c2 = a2.callbackNode;
        if (Hk() && a2.callbackNode !== c2) return null;
        var d = uc(a2, a2 === Q ? Z : 0);
        if (0 === d) return null;
        if (0 !== (d & 30) || 0 !== (d & a2.expiredLanes) || b2) b2 = Ik(a2, d);
        else {
          b2 = d;
          var e = K;
          K |= 2;
          var f = Jk();
          if (Q !== a2 || Z !== b2) uk = null, Gj = B() + 500, Kk(a2, b2);
          do
            try {
              Lk();
              break;
            } catch (h) {
              Mk(a2, h);
            }
          while (1);
          $g();
          mk.current = f;
          K = e;
          null !== Y ? b2 = 0 : (Q = null, Z = 0, b2 = T);
        }
        if (0 !== b2) {
          2 === b2 && (e = xc(a2), 0 !== e && (d = e, b2 = Nk(a2, e)));
          if (1 === b2) throw c2 = pk, Kk(a2, 0), Ck(a2, d), Dk(a2, B()), c2;
          if (6 === b2) Ck(a2, d);
          else {
            e = a2.current.alternate;
            if (0 === (d & 30) && !Ok(e) && (b2 = Ik(a2, d), 2 === b2 && (f = xc(a2), 0 !== f && (d = f, b2 = Nk(a2, f))), 1 === b2)) throw c2 = pk, Kk(a2, 0), Ck(a2, d), Dk(a2, B()), c2;
            a2.finishedWork = e;
            a2.finishedLanes = d;
            switch (b2) {
              case 0:
              case 1:
                throw Error(p(345));
              case 2:
                Pk(a2, tk, uk);
                break;
              case 3:
                Ck(a2, d);
                if ((d & 130023424) === d && (b2 = fk + 500 - B(), 10 < b2)) {
                  if (0 !== uc(a2, 0)) break;
                  e = a2.suspendedLanes;
                  if ((e & d) !== d) {
                    R();
                    a2.pingedLanes |= a2.suspendedLanes & e;
                    break;
                  }
                  a2.timeoutHandle = Ff(Pk.bind(null, a2, tk, uk), b2);
                  break;
                }
                Pk(a2, tk, uk);
                break;
              case 4:
                Ck(a2, d);
                if ((d & 4194240) === d) break;
                b2 = a2.eventTimes;
                for (e = -1; 0 < d; ) {
                  var g = 31 - oc(d);
                  f = 1 << g;
                  g = b2[g];
                  g > e && (e = g);
                  d &= ~f;
                }
                d = e;
                d = B() - d;
                d = (120 > d ? 120 : 480 > d ? 480 : 1080 > d ? 1080 : 1920 > d ? 1920 : 3e3 > d ? 3e3 : 4320 > d ? 4320 : 1960 * lk(d / 1960)) - d;
                if (10 < d) {
                  a2.timeoutHandle = Ff(Pk.bind(null, a2, tk, uk), d);
                  break;
                }
                Pk(a2, tk, uk);
                break;
              case 5:
                Pk(a2, tk, uk);
                break;
              default:
                throw Error(p(329));
            }
          }
        }
        Dk(a2, B());
        return a2.callbackNode === c2 ? Gk.bind(null, a2) : null;
      }
      function Nk(a2, b2) {
        var c2 = sk;
        a2.current.memoizedState.isDehydrated && (Kk(a2, b2).flags |= 256);
        a2 = Ik(a2, b2);
        2 !== a2 && (b2 = tk, tk = c2, null !== b2 && Fj(b2));
        return a2;
      }
      function Fj(a2) {
        null === tk ? tk = a2 : tk.push.apply(tk, a2);
      }
      function Ok(a2) {
        for (var b2 = a2; ; ) {
          if (b2.flags & 16384) {
            var c2 = b2.updateQueue;
            if (null !== c2 && (c2 = c2.stores, null !== c2)) for (var d = 0; d < c2.length; d++) {
              var e = c2[d], f = e.getSnapshot;
              e = e.value;
              try {
                if (!He(f(), e)) return false;
              } catch (g) {
                return false;
              }
            }
          }
          c2 = b2.child;
          if (b2.subtreeFlags & 16384 && null !== c2) c2.return = b2, b2 = c2;
          else {
            if (b2 === a2) break;
            for (; null === b2.sibling; ) {
              if (null === b2.return || b2.return === a2) return true;
              b2 = b2.return;
            }
            b2.sibling.return = b2.return;
            b2 = b2.sibling;
          }
        }
        return true;
      }
      function Ck(a2, b2) {
        b2 &= ~rk;
        b2 &= ~qk;
        a2.suspendedLanes |= b2;
        a2.pingedLanes &= ~b2;
        for (a2 = a2.expirationTimes; 0 < b2; ) {
          var c2 = 31 - oc(b2), d = 1 << c2;
          a2[c2] = -1;
          b2 &= ~d;
        }
      }
      function Ek(a2) {
        if (0 !== (K & 6)) throw Error(p(327));
        Hk();
        var b2 = uc(a2, 0);
        if (0 === (b2 & 1)) return Dk(a2, B()), null;
        var c2 = Ik(a2, b2);
        if (0 !== a2.tag && 2 === c2) {
          var d = xc(a2);
          0 !== d && (b2 = d, c2 = Nk(a2, d));
        }
        if (1 === c2) throw c2 = pk, Kk(a2, 0), Ck(a2, b2), Dk(a2, B()), c2;
        if (6 === c2) throw Error(p(345));
        a2.finishedWork = a2.current.alternate;
        a2.finishedLanes = b2;
        Pk(a2, tk, uk);
        Dk(a2, B());
        return null;
      }
      function Qk(a2, b2) {
        var c2 = K;
        K |= 1;
        try {
          return a2(b2);
        } finally {
          K = c2, 0 === K && (Gj = B() + 500, fg && jg());
        }
      }
      function Rk(a2) {
        null !== wk && 0 === wk.tag && 0 === (K & 6) && Hk();
        var b2 = K;
        K |= 1;
        var c2 = ok.transition, d = C;
        try {
          if (ok.transition = null, C = 1, a2) return a2();
        } finally {
          C = d, ok.transition = c2, K = b2, 0 === (K & 6) && jg();
        }
      }
      function Hj() {
        fj = ej.current;
        E(ej);
      }
      function Kk(a2, b2) {
        a2.finishedWork = null;
        a2.finishedLanes = 0;
        var c2 = a2.timeoutHandle;
        -1 !== c2 && (a2.timeoutHandle = -1, Gf(c2));
        if (null !== Y) for (c2 = Y.return; null !== c2; ) {
          var d = c2;
          wg(d);
          switch (d.tag) {
            case 1:
              d = d.type.childContextTypes;
              null !== d && void 0 !== d && $f();
              break;
            case 3:
              zh();
              E(Wf);
              E(H);
              Eh();
              break;
            case 5:
              Bh(d);
              break;
            case 4:
              zh();
              break;
            case 13:
              E(L);
              break;
            case 19:
              E(L);
              break;
            case 10:
              ah(d.type._context);
              break;
            case 22:
            case 23:
              Hj();
          }
          c2 = c2.return;
        }
        Q = a2;
        Y = a2 = Pg(a2.current, null);
        Z = fj = b2;
        T = 0;
        pk = null;
        rk = qk = rh = 0;
        tk = sk = null;
        if (null !== fh) {
          for (b2 = 0; b2 < fh.length; b2++) if (c2 = fh[b2], d = c2.interleaved, null !== d) {
            c2.interleaved = null;
            var e = d.next, f = c2.pending;
            if (null !== f) {
              var g = f.next;
              f.next = e;
              d.next = g;
            }
            c2.pending = d;
          }
          fh = null;
        }
        return a2;
      }
      function Mk(a2, b2) {
        do {
          var c2 = Y;
          try {
            $g();
            Fh.current = Rh;
            if (Ih) {
              for (var d = M.memoizedState; null !== d; ) {
                var e = d.queue;
                null !== e && (e.pending = null);
                d = d.next;
              }
              Ih = false;
            }
            Hh = 0;
            O = N = M = null;
            Jh = false;
            Kh = 0;
            nk.current = null;
            if (null === c2 || null === c2.return) {
              T = 1;
              pk = b2;
              Y = null;
              break;
            }
            a: {
              var f = a2, g = c2.return, h = c2, k = b2;
              b2 = Z;
              h.flags |= 32768;
              if (null !== k && "object" === typeof k && "function" === typeof k.then) {
                var l = k, m = h, q = m.tag;
                if (0 === (m.mode & 1) && (0 === q || 11 === q || 15 === q)) {
                  var r = m.alternate;
                  r ? (m.updateQueue = r.updateQueue, m.memoizedState = r.memoizedState, m.lanes = r.lanes) : (m.updateQueue = null, m.memoizedState = null);
                }
                var y = Ui(g);
                if (null !== y) {
                  y.flags &= -257;
                  Vi(y, g, h, f, b2);
                  y.mode & 1 && Si(f, l, b2);
                  b2 = y;
                  k = l;
                  var n = b2.updateQueue;
                  if (null === n) {
                    var t = /* @__PURE__ */ new Set();
                    t.add(k);
                    b2.updateQueue = t;
                  } else n.add(k);
                  break a;
                } else {
                  if (0 === (b2 & 1)) {
                    Si(f, l, b2);
                    tj();
                    break a;
                  }
                  k = Error(p(426));
                }
              } else if (I && h.mode & 1) {
                var J = Ui(g);
                if (null !== J) {
                  0 === (J.flags & 65536) && (J.flags |= 256);
                  Vi(J, g, h, f, b2);
                  Jg(Ji(k, h));
                  break a;
                }
              }
              f = k = Ji(k, h);
              4 !== T && (T = 2);
              null === sk ? sk = [f] : sk.push(f);
              f = g;
              do {
                switch (f.tag) {
                  case 3:
                    f.flags |= 65536;
                    b2 &= -b2;
                    f.lanes |= b2;
                    var x = Ni(f, k, b2);
                    ph(f, x);
                    break a;
                  case 1:
                    h = k;
                    var w = f.type, u = f.stateNode;
                    if (0 === (f.flags & 128) && ("function" === typeof w.getDerivedStateFromError || null !== u && "function" === typeof u.componentDidCatch && (null === Ri || !Ri.has(u)))) {
                      f.flags |= 65536;
                      b2 &= -b2;
                      f.lanes |= b2;
                      var F = Qi(f, h, b2);
                      ph(f, F);
                      break a;
                    }
                }
                f = f.return;
              } while (null !== f);
            }
            Sk(c2);
          } catch (na) {
            b2 = na;
            Y === c2 && null !== c2 && (Y = c2 = c2.return);
            continue;
          }
          break;
        } while (1);
      }
      function Jk() {
        var a2 = mk.current;
        mk.current = Rh;
        return null === a2 ? Rh : a2;
      }
      function tj() {
        if (0 === T || 3 === T || 2 === T) T = 4;
        null === Q || 0 === (rh & 268435455) && 0 === (qk & 268435455) || Ck(Q, Z);
      }
      function Ik(a2, b2) {
        var c2 = K;
        K |= 2;
        var d = Jk();
        if (Q !== a2 || Z !== b2) uk = null, Kk(a2, b2);
        do
          try {
            Tk();
            break;
          } catch (e) {
            Mk(a2, e);
          }
        while (1);
        $g();
        K = c2;
        mk.current = d;
        if (null !== Y) throw Error(p(261));
        Q = null;
        Z = 0;
        return T;
      }
      function Tk() {
        for (; null !== Y; ) Uk(Y);
      }
      function Lk() {
        for (; null !== Y && !cc(); ) Uk(Y);
      }
      function Uk(a2) {
        var b2 = Vk(a2.alternate, a2, fj);
        a2.memoizedProps = a2.pendingProps;
        null === b2 ? Sk(a2) : Y = b2;
        nk.current = null;
      }
      function Sk(a2) {
        var b2 = a2;
        do {
          var c2 = b2.alternate;
          a2 = b2.return;
          if (0 === (b2.flags & 32768)) {
            if (c2 = Ej(c2, b2, fj), null !== c2) {
              Y = c2;
              return;
            }
          } else {
            c2 = Ij(c2, b2);
            if (null !== c2) {
              c2.flags &= 32767;
              Y = c2;
              return;
            }
            if (null !== a2) a2.flags |= 32768, a2.subtreeFlags = 0, a2.deletions = null;
            else {
              T = 6;
              Y = null;
              return;
            }
          }
          b2 = b2.sibling;
          if (null !== b2) {
            Y = b2;
            return;
          }
          Y = b2 = a2;
        } while (null !== b2);
        0 === T && (T = 5);
      }
      function Pk(a2, b2, c2) {
        var d = C, e = ok.transition;
        try {
          ok.transition = null, C = 1, Wk(a2, b2, c2, d);
        } finally {
          ok.transition = e, C = d;
        }
        return null;
      }
      function Wk(a2, b2, c2, d) {
        do
          Hk();
        while (null !== wk);
        if (0 !== (K & 6)) throw Error(p(327));
        c2 = a2.finishedWork;
        var e = a2.finishedLanes;
        if (null === c2) return null;
        a2.finishedWork = null;
        a2.finishedLanes = 0;
        if (c2 === a2.current) throw Error(p(177));
        a2.callbackNode = null;
        a2.callbackPriority = 0;
        var f = c2.lanes | c2.childLanes;
        Bc(a2, f);
        a2 === Q && (Y = Q = null, Z = 0);
        0 === (c2.subtreeFlags & 2064) && 0 === (c2.flags & 2064) || vk || (vk = true, Fk(hc, function() {
          Hk();
          return null;
        }));
        f = 0 !== (c2.flags & 15990);
        if (0 !== (c2.subtreeFlags & 15990) || f) {
          f = ok.transition;
          ok.transition = null;
          var g = C;
          C = 1;
          var h = K;
          K |= 4;
          nk.current = null;
          Oj(a2, c2);
          dk(c2, a2);
          Oe(Df);
          dd = !!Cf;
          Df = Cf = null;
          a2.current = c2;
          hk(c2, a2, e);
          dc();
          K = h;
          C = g;
          ok.transition = f;
        } else a2.current = c2;
        vk && (vk = false, wk = a2, xk = e);
        f = a2.pendingLanes;
        0 === f && (Ri = null);
        mc(c2.stateNode, d);
        Dk(a2, B());
        if (null !== b2) for (d = a2.onRecoverableError, c2 = 0; c2 < b2.length; c2++) e = b2[c2], d(e.value, { componentStack: e.stack, digest: e.digest });
        if (Oi) throw Oi = false, a2 = Pi, Pi = null, a2;
        0 !== (xk & 1) && 0 !== a2.tag && Hk();
        f = a2.pendingLanes;
        0 !== (f & 1) ? a2 === zk ? yk++ : (yk = 0, zk = a2) : yk = 0;
        jg();
        return null;
      }
      function Hk() {
        if (null !== wk) {
          var a2 = Dc(xk), b2 = ok.transition, c2 = C;
          try {
            ok.transition = null;
            C = 16 > a2 ? 16 : a2;
            if (null === wk) var d = false;
            else {
              a2 = wk;
              wk = null;
              xk = 0;
              if (0 !== (K & 6)) throw Error(p(331));
              var e = K;
              K |= 4;
              for (V = a2.current; null !== V; ) {
                var f = V, g = f.child;
                if (0 !== (V.flags & 16)) {
                  var h = f.deletions;
                  if (null !== h) {
                    for (var k = 0; k < h.length; k++) {
                      var l = h[k];
                      for (V = l; null !== V; ) {
                        var m = V;
                        switch (m.tag) {
                          case 0:
                          case 11:
                          case 15:
                            Pj(8, m, f);
                        }
                        var q = m.child;
                        if (null !== q) q.return = m, V = q;
                        else for (; null !== V; ) {
                          m = V;
                          var r = m.sibling, y = m.return;
                          Sj(m);
                          if (m === l) {
                            V = null;
                            break;
                          }
                          if (null !== r) {
                            r.return = y;
                            V = r;
                            break;
                          }
                          V = y;
                        }
                      }
                    }
                    var n = f.alternate;
                    if (null !== n) {
                      var t = n.child;
                      if (null !== t) {
                        n.child = null;
                        do {
                          var J = t.sibling;
                          t.sibling = null;
                          t = J;
                        } while (null !== t);
                      }
                    }
                    V = f;
                  }
                }
                if (0 !== (f.subtreeFlags & 2064) && null !== g) g.return = f, V = g;
                else b: for (; null !== V; ) {
                  f = V;
                  if (0 !== (f.flags & 2048)) switch (f.tag) {
                    case 0:
                    case 11:
                    case 15:
                      Pj(9, f, f.return);
                  }
                  var x = f.sibling;
                  if (null !== x) {
                    x.return = f.return;
                    V = x;
                    break b;
                  }
                  V = f.return;
                }
              }
              var w = a2.current;
              for (V = w; null !== V; ) {
                g = V;
                var u = g.child;
                if (0 !== (g.subtreeFlags & 2064) && null !== u) u.return = g, V = u;
                else b: for (g = w; null !== V; ) {
                  h = V;
                  if (0 !== (h.flags & 2048)) try {
                    switch (h.tag) {
                      case 0:
                      case 11:
                      case 15:
                        Qj(9, h);
                    }
                  } catch (na) {
                    W(h, h.return, na);
                  }
                  if (h === g) {
                    V = null;
                    break b;
                  }
                  var F = h.sibling;
                  if (null !== F) {
                    F.return = h.return;
                    V = F;
                    break b;
                  }
                  V = h.return;
                }
              }
              K = e;
              jg();
              if (lc && "function" === typeof lc.onPostCommitFiberRoot) try {
                lc.onPostCommitFiberRoot(kc, a2);
              } catch (na) {
              }
              d = true;
            }
            return d;
          } finally {
            C = c2, ok.transition = b2;
          }
        }
        return false;
      }
      function Xk(a2, b2, c2) {
        b2 = Ji(c2, b2);
        b2 = Ni(a2, b2, 1);
        a2 = nh(a2, b2, 1);
        b2 = R();
        null !== a2 && (Ac(a2, 1, b2), Dk(a2, b2));
      }
      function W(a2, b2, c2) {
        if (3 === a2.tag) Xk(a2, a2, c2);
        else for (; null !== b2; ) {
          if (3 === b2.tag) {
            Xk(b2, a2, c2);
            break;
          } else if (1 === b2.tag) {
            var d = b2.stateNode;
            if ("function" === typeof b2.type.getDerivedStateFromError || "function" === typeof d.componentDidCatch && (null === Ri || !Ri.has(d))) {
              a2 = Ji(c2, a2);
              a2 = Qi(b2, a2, 1);
              b2 = nh(b2, a2, 1);
              a2 = R();
              null !== b2 && (Ac(b2, 1, a2), Dk(b2, a2));
              break;
            }
          }
          b2 = b2.return;
        }
      }
      function Ti(a2, b2, c2) {
        var d = a2.pingCache;
        null !== d && d.delete(b2);
        b2 = R();
        a2.pingedLanes |= a2.suspendedLanes & c2;
        Q === a2 && (Z & c2) === c2 && (4 === T || 3 === T && (Z & 130023424) === Z && 500 > B() - fk ? Kk(a2, 0) : rk |= c2);
        Dk(a2, b2);
      }
      function Yk(a2, b2) {
        0 === b2 && (0 === (a2.mode & 1) ? b2 = 1 : (b2 = sc, sc <<= 1, 0 === (sc & 130023424) && (sc = 4194304)));
        var c2 = R();
        a2 = ih(a2, b2);
        null !== a2 && (Ac(a2, b2, c2), Dk(a2, c2));
      }
      function uj(a2) {
        var b2 = a2.memoizedState, c2 = 0;
        null !== b2 && (c2 = b2.retryLane);
        Yk(a2, c2);
      }
      function bk(a2, b2) {
        var c2 = 0;
        switch (a2.tag) {
          case 13:
            var d = a2.stateNode;
            var e = a2.memoizedState;
            null !== e && (c2 = e.retryLane);
            break;
          case 19:
            d = a2.stateNode;
            break;
          default:
            throw Error(p(314));
        }
        null !== d && d.delete(b2);
        Yk(a2, c2);
      }
      var Vk;
      Vk = function(a2, b2, c2) {
        if (null !== a2) if (a2.memoizedProps !== b2.pendingProps || Wf.current) dh = true;
        else {
          if (0 === (a2.lanes & c2) && 0 === (b2.flags & 128)) return dh = false, yj(a2, b2, c2);
          dh = 0 !== (a2.flags & 131072) ? true : false;
        }
        else dh = false, I && 0 !== (b2.flags & 1048576) && ug(b2, ng, b2.index);
        b2.lanes = 0;
        switch (b2.tag) {
          case 2:
            var d = b2.type;
            ij(a2, b2);
            a2 = b2.pendingProps;
            var e = Yf(b2, H.current);
            ch(b2, c2);
            e = Nh(null, b2, d, a2, e, c2);
            var f = Sh();
            b2.flags |= 1;
            "object" === typeof e && null !== e && "function" === typeof e.render && void 0 === e.$$typeof ? (b2.tag = 1, b2.memoizedState = null, b2.updateQueue = null, Zf(d) ? (f = true, cg(b2)) : f = false, b2.memoizedState = null !== e.state && void 0 !== e.state ? e.state : null, kh(b2), e.updater = Ei, b2.stateNode = e, e._reactInternals = b2, Ii(b2, d, a2, c2), b2 = jj(null, b2, d, true, f, c2)) : (b2.tag = 0, I && f && vg(b2), Xi(null, b2, e, c2), b2 = b2.child);
            return b2;
          case 16:
            d = b2.elementType;
            a: {
              ij(a2, b2);
              a2 = b2.pendingProps;
              e = d._init;
              d = e(d._payload);
              b2.type = d;
              e = b2.tag = Zk(d);
              a2 = Ci(d, a2);
              switch (e) {
                case 0:
                  b2 = cj(null, b2, d, a2, c2);
                  break a;
                case 1:
                  b2 = hj(null, b2, d, a2, c2);
                  break a;
                case 11:
                  b2 = Yi(null, b2, d, a2, c2);
                  break a;
                case 14:
                  b2 = $i(null, b2, d, Ci(d.type, a2), c2);
                  break a;
              }
              throw Error(p(
                306,
                d,
                ""
              ));
            }
            return b2;
          case 0:
            return d = b2.type, e = b2.pendingProps, e = b2.elementType === d ? e : Ci(d, e), cj(a2, b2, d, e, c2);
          case 1:
            return d = b2.type, e = b2.pendingProps, e = b2.elementType === d ? e : Ci(d, e), hj(a2, b2, d, e, c2);
          case 3:
            a: {
              kj(b2);
              if (null === a2) throw Error(p(387));
              d = b2.pendingProps;
              f = b2.memoizedState;
              e = f.element;
              lh(a2, b2);
              qh(b2, d, null, c2);
              var g = b2.memoizedState;
              d = g.element;
              if (f.isDehydrated) if (f = { element: d, isDehydrated: false, cache: g.cache, pendingSuspenseBoundaries: g.pendingSuspenseBoundaries, transitions: g.transitions }, b2.updateQueue.baseState = f, b2.memoizedState = f, b2.flags & 256) {
                e = Ji(Error(p(423)), b2);
                b2 = lj(a2, b2, d, c2, e);
                break a;
              } else if (d !== e) {
                e = Ji(Error(p(424)), b2);
                b2 = lj(a2, b2, d, c2, e);
                break a;
              } else for (yg = Lf(b2.stateNode.containerInfo.firstChild), xg = b2, I = true, zg = null, c2 = Vg(b2, null, d, c2), b2.child = c2; c2; ) c2.flags = c2.flags & -3 | 4096, c2 = c2.sibling;
              else {
                Ig();
                if (d === e) {
                  b2 = Zi(a2, b2, c2);
                  break a;
                }
                Xi(a2, b2, d, c2);
              }
              b2 = b2.child;
            }
            return b2;
          case 5:
            return Ah(b2), null === a2 && Eg(b2), d = b2.type, e = b2.pendingProps, f = null !== a2 ? a2.memoizedProps : null, g = e.children, Ef(d, e) ? g = null : null !== f && Ef(d, f) && (b2.flags |= 32), gj(a2, b2), Xi(a2, b2, g, c2), b2.child;
          case 6:
            return null === a2 && Eg(b2), null;
          case 13:
            return oj(a2, b2, c2);
          case 4:
            return yh(b2, b2.stateNode.containerInfo), d = b2.pendingProps, null === a2 ? b2.child = Ug(b2, null, d, c2) : Xi(a2, b2, d, c2), b2.child;
          case 11:
            return d = b2.type, e = b2.pendingProps, e = b2.elementType === d ? e : Ci(d, e), Yi(a2, b2, d, e, c2);
          case 7:
            return Xi(a2, b2, b2.pendingProps, c2), b2.child;
          case 8:
            return Xi(a2, b2, b2.pendingProps.children, c2), b2.child;
          case 12:
            return Xi(a2, b2, b2.pendingProps.children, c2), b2.child;
          case 10:
            a: {
              d = b2.type._context;
              e = b2.pendingProps;
              f = b2.memoizedProps;
              g = e.value;
              G(Wg, d._currentValue);
              d._currentValue = g;
              if (null !== f) if (He(f.value, g)) {
                if (f.children === e.children && !Wf.current) {
                  b2 = Zi(a2, b2, c2);
                  break a;
                }
              } else for (f = b2.child, null !== f && (f.return = b2); null !== f; ) {
                var h = f.dependencies;
                if (null !== h) {
                  g = f.child;
                  for (var k = h.firstContext; null !== k; ) {
                    if (k.context === d) {
                      if (1 === f.tag) {
                        k = mh(-1, c2 & -c2);
                        k.tag = 2;
                        var l = f.updateQueue;
                        if (null !== l) {
                          l = l.shared;
                          var m = l.pending;
                          null === m ? k.next = k : (k.next = m.next, m.next = k);
                          l.pending = k;
                        }
                      }
                      f.lanes |= c2;
                      k = f.alternate;
                      null !== k && (k.lanes |= c2);
                      bh(
                        f.return,
                        c2,
                        b2
                      );
                      h.lanes |= c2;
                      break;
                    }
                    k = k.next;
                  }
                } else if (10 === f.tag) g = f.type === b2.type ? null : f.child;
                else if (18 === f.tag) {
                  g = f.return;
                  if (null === g) throw Error(p(341));
                  g.lanes |= c2;
                  h = g.alternate;
                  null !== h && (h.lanes |= c2);
                  bh(g, c2, b2);
                  g = f.sibling;
                } else g = f.child;
                if (null !== g) g.return = f;
                else for (g = f; null !== g; ) {
                  if (g === b2) {
                    g = null;
                    break;
                  }
                  f = g.sibling;
                  if (null !== f) {
                    f.return = g.return;
                    g = f;
                    break;
                  }
                  g = g.return;
                }
                f = g;
              }
              Xi(a2, b2, e.children, c2);
              b2 = b2.child;
            }
            return b2;
          case 9:
            return e = b2.type, d = b2.pendingProps.children, ch(b2, c2), e = eh(e), d = d(e), b2.flags |= 1, Xi(a2, b2, d, c2), b2.child;
          case 14:
            return d = b2.type, e = Ci(d, b2.pendingProps), e = Ci(d.type, e), $i(a2, b2, d, e, c2);
          case 15:
            return bj(a2, b2, b2.type, b2.pendingProps, c2);
          case 17:
            return d = b2.type, e = b2.pendingProps, e = b2.elementType === d ? e : Ci(d, e), ij(a2, b2), b2.tag = 1, Zf(d) ? (a2 = true, cg(b2)) : a2 = false, ch(b2, c2), Gi(b2, d, e), Ii(b2, d, e, c2), jj(null, b2, d, true, a2, c2);
          case 19:
            return xj(a2, b2, c2);
          case 22:
            return dj(a2, b2, c2);
        }
        throw Error(p(156, b2.tag));
      };
      function Fk(a2, b2) {
        return ac(a2, b2);
      }
      function $k(a2, b2, c2, d) {
        this.tag = a2;
        this.key = c2;
        this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null;
        this.index = 0;
        this.ref = null;
        this.pendingProps = b2;
        this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null;
        this.mode = d;
        this.subtreeFlags = this.flags = 0;
        this.deletions = null;
        this.childLanes = this.lanes = 0;
        this.alternate = null;
      }
      function Bg(a2, b2, c2, d) {
        return new $k(a2, b2, c2, d);
      }
      function aj(a2) {
        a2 = a2.prototype;
        return !(!a2 || !a2.isReactComponent);
      }
      function Zk(a2) {
        if ("function" === typeof a2) return aj(a2) ? 1 : 0;
        if (void 0 !== a2 && null !== a2) {
          a2 = a2.$$typeof;
          if (a2 === Da) return 11;
          if (a2 === Ga) return 14;
        }
        return 2;
      }
      function Pg(a2, b2) {
        var c2 = a2.alternate;
        null === c2 ? (c2 = Bg(a2.tag, b2, a2.key, a2.mode), c2.elementType = a2.elementType, c2.type = a2.type, c2.stateNode = a2.stateNode, c2.alternate = a2, a2.alternate = c2) : (c2.pendingProps = b2, c2.type = a2.type, c2.flags = 0, c2.subtreeFlags = 0, c2.deletions = null);
        c2.flags = a2.flags & 14680064;
        c2.childLanes = a2.childLanes;
        c2.lanes = a2.lanes;
        c2.child = a2.child;
        c2.memoizedProps = a2.memoizedProps;
        c2.memoizedState = a2.memoizedState;
        c2.updateQueue = a2.updateQueue;
        b2 = a2.dependencies;
        c2.dependencies = null === b2 ? null : { lanes: b2.lanes, firstContext: b2.firstContext };
        c2.sibling = a2.sibling;
        c2.index = a2.index;
        c2.ref = a2.ref;
        return c2;
      }
      function Rg(a2, b2, c2, d, e, f) {
        var g = 2;
        d = a2;
        if ("function" === typeof a2) aj(a2) && (g = 1);
        else if ("string" === typeof a2) g = 5;
        else a: switch (a2) {
          case ya:
            return Tg(c2.children, e, f, b2);
          case za:
            g = 8;
            e |= 8;
            break;
          case Aa:
            return a2 = Bg(12, c2, b2, e | 2), a2.elementType = Aa, a2.lanes = f, a2;
          case Ea:
            return a2 = Bg(13, c2, b2, e), a2.elementType = Ea, a2.lanes = f, a2;
          case Fa:
            return a2 = Bg(19, c2, b2, e), a2.elementType = Fa, a2.lanes = f, a2;
          case Ia:
            return pj(c2, e, f, b2);
          default:
            if ("object" === typeof a2 && null !== a2) switch (a2.$$typeof) {
              case Ba:
                g = 10;
                break a;
              case Ca:
                g = 9;
                break a;
              case Da:
                g = 11;
                break a;
              case Ga:
                g = 14;
                break a;
              case Ha:
                g = 16;
                d = null;
                break a;
            }
            throw Error(p(130, null == a2 ? a2 : typeof a2, ""));
        }
        b2 = Bg(g, c2, b2, e);
        b2.elementType = a2;
        b2.type = d;
        b2.lanes = f;
        return b2;
      }
      function Tg(a2, b2, c2, d) {
        a2 = Bg(7, a2, d, b2);
        a2.lanes = c2;
        return a2;
      }
      function pj(a2, b2, c2, d) {
        a2 = Bg(22, a2, d, b2);
        a2.elementType = Ia;
        a2.lanes = c2;
        a2.stateNode = { isHidden: false };
        return a2;
      }
      function Qg(a2, b2, c2) {
        a2 = Bg(6, a2, null, b2);
        a2.lanes = c2;
        return a2;
      }
      function Sg(a2, b2, c2) {
        b2 = Bg(4, null !== a2.children ? a2.children : [], a2.key, b2);
        b2.lanes = c2;
        b2.stateNode = { containerInfo: a2.containerInfo, pendingChildren: null, implementation: a2.implementation };
        return b2;
      }
      function al(a2, b2, c2, d, e) {
        this.tag = b2;
        this.containerInfo = a2;
        this.finishedWork = this.pingCache = this.current = this.pendingChildren = null;
        this.timeoutHandle = -1;
        this.callbackNode = this.pendingContext = this.context = null;
        this.callbackPriority = 0;
        this.eventTimes = zc(0);
        this.expirationTimes = zc(-1);
        this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0;
        this.entanglements = zc(0);
        this.identifierPrefix = d;
        this.onRecoverableError = e;
        this.mutableSourceEagerHydrationData = null;
      }
      function bl(a2, b2, c2, d, e, f, g, h, k) {
        a2 = new al(a2, b2, c2, h, k);
        1 === b2 ? (b2 = 1, true === f && (b2 |= 8)) : b2 = 0;
        f = Bg(3, null, null, b2);
        a2.current = f;
        f.stateNode = a2;
        f.memoizedState = { element: d, isDehydrated: c2, cache: null, transitions: null, pendingSuspenseBoundaries: null };
        kh(f);
        return a2;
      }
      function cl(a2, b2, c2) {
        var d = 3 < arguments.length && void 0 !== arguments[3] ? arguments[3] : null;
        return { $$typeof: wa, key: null == d ? null : "" + d, children: a2, containerInfo: b2, implementation: c2 };
      }
      function dl(a2) {
        if (!a2) return Vf;
        a2 = a2._reactInternals;
        a: {
          if (Vb(a2) !== a2 || 1 !== a2.tag) throw Error(p(170));
          var b2 = a2;
          do {
            switch (b2.tag) {
              case 3:
                b2 = b2.stateNode.context;
                break a;
              case 1:
                if (Zf(b2.type)) {
                  b2 = b2.stateNode.__reactInternalMemoizedMergedChildContext;
                  break a;
                }
            }
            b2 = b2.return;
          } while (null !== b2);
          throw Error(p(171));
        }
        if (1 === a2.tag) {
          var c2 = a2.type;
          if (Zf(c2)) return bg(a2, c2, b2);
        }
        return b2;
      }
      function el(a2, b2, c2, d, e, f, g, h, k) {
        a2 = bl(c2, d, true, a2, e, f, g, h, k);
        a2.context = dl(null);
        c2 = a2.current;
        d = R();
        e = yi(c2);
        f = mh(d, e);
        f.callback = void 0 !== b2 && null !== b2 ? b2 : null;
        nh(c2, f, e);
        a2.current.lanes = e;
        Ac(a2, e, d);
        Dk(a2, d);
        return a2;
      }
      function fl(a2, b2, c2, d) {
        var e = b2.current, f = R(), g = yi(e);
        c2 = dl(c2);
        null === b2.context ? b2.context = c2 : b2.pendingContext = c2;
        b2 = mh(f, g);
        b2.payload = { element: a2 };
        d = void 0 === d ? null : d;
        null !== d && (b2.callback = d);
        a2 = nh(e, b2, g);
        null !== a2 && (gi(a2, e, g, f), oh(a2, e, g));
        return g;
      }
      function gl(a2) {
        a2 = a2.current;
        if (!a2.child) return null;
        switch (a2.child.tag) {
          case 5:
            return a2.child.stateNode;
          default:
            return a2.child.stateNode;
        }
      }
      function hl(a2, b2) {
        a2 = a2.memoizedState;
        if (null !== a2 && null !== a2.dehydrated) {
          var c2 = a2.retryLane;
          a2.retryLane = 0 !== c2 && c2 < b2 ? c2 : b2;
        }
      }
      function il(a2, b2) {
        hl(a2, b2);
        (a2 = a2.alternate) && hl(a2, b2);
      }
      function jl() {
        return null;
      }
      var kl = "function" === typeof reportError ? reportError : function(a2) {
        console.error(a2);
      };
      function ll(a2) {
        this._internalRoot = a2;
      }
      ml.prototype.render = ll.prototype.render = function(a2) {
        var b2 = this._internalRoot;
        if (null === b2) throw Error(p(409));
        fl(a2, b2, null, null);
      };
      ml.prototype.unmount = ll.prototype.unmount = function() {
        var a2 = this._internalRoot;
        if (null !== a2) {
          this._internalRoot = null;
          var b2 = a2.containerInfo;
          Rk(function() {
            fl(null, a2, null, null);
          });
          b2[uf] = null;
        }
      };
      function ml(a2) {
        this._internalRoot = a2;
      }
      ml.prototype.unstable_scheduleHydration = function(a2) {
        if (a2) {
          var b2 = Hc();
          a2 = { blockedOn: null, target: a2, priority: b2 };
          for (var c2 = 0; c2 < Qc.length && 0 !== b2 && b2 < Qc[c2].priority; c2++) ;
          Qc.splice(c2, 0, a2);
          0 === c2 && Vc(a2);
        }
      };
      function nl(a2) {
        return !(!a2 || 1 !== a2.nodeType && 9 !== a2.nodeType && 11 !== a2.nodeType);
      }
      function ol(a2) {
        return !(!a2 || 1 !== a2.nodeType && 9 !== a2.nodeType && 11 !== a2.nodeType && (8 !== a2.nodeType || " react-mount-point-unstable " !== a2.nodeValue));
      }
      function pl() {
      }
      function ql(a2, b2, c2, d, e) {
        if (e) {
          if ("function" === typeof d) {
            var f = d;
            d = function() {
              var a3 = gl(g);
              f.call(a3);
            };
          }
          var g = el(b2, d, a2, 0, null, false, false, "", pl);
          a2._reactRootContainer = g;
          a2[uf] = g.current;
          sf(8 === a2.nodeType ? a2.parentNode : a2);
          Rk();
          return g;
        }
        for (; e = a2.lastChild; ) a2.removeChild(e);
        if ("function" === typeof d) {
          var h = d;
          d = function() {
            var a3 = gl(k);
            h.call(a3);
          };
        }
        var k = bl(a2, 0, false, null, null, false, false, "", pl);
        a2._reactRootContainer = k;
        a2[uf] = k.current;
        sf(8 === a2.nodeType ? a2.parentNode : a2);
        Rk(function() {
          fl(b2, k, c2, d);
        });
        return k;
      }
      function rl(a2, b2, c2, d, e) {
        var f = c2._reactRootContainer;
        if (f) {
          var g = f;
          if ("function" === typeof e) {
            var h = e;
            e = function() {
              var a3 = gl(g);
              h.call(a3);
            };
          }
          fl(b2, g, a2, e);
        } else g = ql(c2, b2, a2, e, d);
        return gl(g);
      }
      Ec = function(a2) {
        switch (a2.tag) {
          case 3:
            var b2 = a2.stateNode;
            if (b2.current.memoizedState.isDehydrated) {
              var c2 = tc(b2.pendingLanes);
              0 !== c2 && (Cc(b2, c2 | 1), Dk(b2, B()), 0 === (K & 6) && (Gj = B() + 500, jg()));
            }
            break;
          case 13:
            Rk(function() {
              var b3 = ih(a2, 1);
              if (null !== b3) {
                var c3 = R();
                gi(b3, a2, 1, c3);
              }
            }), il(a2, 1);
        }
      };
      Fc = function(a2) {
        if (13 === a2.tag) {
          var b2 = ih(a2, 134217728);
          if (null !== b2) {
            var c2 = R();
            gi(b2, a2, 134217728, c2);
          }
          il(a2, 134217728);
        }
      };
      Gc = function(a2) {
        if (13 === a2.tag) {
          var b2 = yi(a2), c2 = ih(a2, b2);
          if (null !== c2) {
            var d = R();
            gi(c2, a2, b2, d);
          }
          il(a2, b2);
        }
      };
      Hc = function() {
        return C;
      };
      Ic = function(a2, b2) {
        var c2 = C;
        try {
          return C = a2, b2();
        } finally {
          C = c2;
        }
      };
      yb = function(a2, b2, c2) {
        switch (b2) {
          case "input":
            bb(a2, c2);
            b2 = c2.name;
            if ("radio" === c2.type && null != b2) {
              for (c2 = a2; c2.parentNode; ) c2 = c2.parentNode;
              c2 = c2.querySelectorAll("input[name=" + JSON.stringify("" + b2) + '][type="radio"]');
              for (b2 = 0; b2 < c2.length; b2++) {
                var d = c2[b2];
                if (d !== a2 && d.form === a2.form) {
                  var e = Db(d);
                  if (!e) throw Error(p(90));
                  Wa(d);
                  bb(d, e);
                }
              }
            }
            break;
          case "textarea":
            ib(a2, c2);
            break;
          case "select":
            b2 = c2.value, null != b2 && fb(a2, !!c2.multiple, b2, false);
        }
      };
      Gb = Qk;
      Hb = Rk;
      var sl = { usingClientEntryPoint: false, Events: [Cb, ue, Db, Eb, Fb, Qk] };
      var tl = { findFiberByHostInstance: Wc, bundleType: 0, version: "18.3.1", rendererPackageName: "react-dom" };
      var ul = { bundleType: tl.bundleType, version: tl.version, rendererPackageName: tl.rendererPackageName, rendererConfig: tl.rendererConfig, overrideHookState: null, overrideHookStateDeletePath: null, overrideHookStateRenamePath: null, overrideProps: null, overridePropsDeletePath: null, overridePropsRenamePath: null, setErrorHandler: null, setSuspenseHandler: null, scheduleUpdate: null, currentDispatcherRef: ua.ReactCurrentDispatcher, findHostInstanceByFiber: function(a2) {
        a2 = Zb(a2);
        return null === a2 ? null : a2.stateNode;
      }, findFiberByHostInstance: tl.findFiberByHostInstance || jl, findHostInstancesForRefresh: null, scheduleRefresh: null, scheduleRoot: null, setRefreshHandler: null, getCurrentFiber: null, reconcilerVersion: "18.3.1-next-f1338f8080-20240426" };
      if ("undefined" !== typeof __REACT_DEVTOOLS_GLOBAL_HOOK__) {
        vl = __REACT_DEVTOOLS_GLOBAL_HOOK__;
        if (!vl.isDisabled && vl.supportsFiber) try {
          kc = vl.inject(ul), lc = vl;
        } catch (a2) {
        }
      }
      var vl;
      exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = sl;
      exports.createPortal = function(a2, b2) {
        var c2 = 2 < arguments.length && void 0 !== arguments[2] ? arguments[2] : null;
        if (!nl(b2)) throw Error(p(200));
        return cl(a2, b2, null, c2);
      };
      exports.createRoot = function(a2, b2) {
        if (!nl(a2)) throw Error(p(299));
        var c2 = false, d = "", e = kl;
        null !== b2 && void 0 !== b2 && (true === b2.unstable_strictMode && (c2 = true), void 0 !== b2.identifierPrefix && (d = b2.identifierPrefix), void 0 !== b2.onRecoverableError && (e = b2.onRecoverableError));
        b2 = bl(a2, 1, false, null, null, c2, false, d, e);
        a2[uf] = b2.current;
        sf(8 === a2.nodeType ? a2.parentNode : a2);
        return new ll(b2);
      };
      exports.findDOMNode = function(a2) {
        if (null == a2) return null;
        if (1 === a2.nodeType) return a2;
        var b2 = a2._reactInternals;
        if (void 0 === b2) {
          if ("function" === typeof a2.render) throw Error(p(188));
          a2 = Object.keys(a2).join(",");
          throw Error(p(268, a2));
        }
        a2 = Zb(b2);
        a2 = null === a2 ? null : a2.stateNode;
        return a2;
      };
      exports.flushSync = function(a2) {
        return Rk(a2);
      };
      exports.hydrate = function(a2, b2, c2) {
        if (!ol(b2)) throw Error(p(200));
        return rl(null, a2, b2, true, c2);
      };
      exports.hydrateRoot = function(a2, b2, c2) {
        if (!nl(a2)) throw Error(p(405));
        var d = null != c2 && c2.hydratedSources || null, e = false, f = "", g = kl;
        null !== c2 && void 0 !== c2 && (true === c2.unstable_strictMode && (e = true), void 0 !== c2.identifierPrefix && (f = c2.identifierPrefix), void 0 !== c2.onRecoverableError && (g = c2.onRecoverableError));
        b2 = el(b2, null, a2, 1, null != c2 ? c2 : null, e, false, f, g);
        a2[uf] = b2.current;
        sf(a2);
        if (d) for (a2 = 0; a2 < d.length; a2++) c2 = d[a2], e = c2._getVersion, e = e(c2._source), null == b2.mutableSourceEagerHydrationData ? b2.mutableSourceEagerHydrationData = [c2, e] : b2.mutableSourceEagerHydrationData.push(
          c2,
          e
        );
        return new ml(b2);
      };
      exports.render = function(a2, b2, c2) {
        if (!ol(b2)) throw Error(p(200));
        return rl(null, a2, b2, false, c2);
      };
      exports.unmountComponentAtNode = function(a2) {
        if (!ol(a2)) throw Error(p(40));
        return a2._reactRootContainer ? (Rk(function() {
          rl(null, null, a2, false, function() {
            a2._reactRootContainer = null;
            a2[uf] = null;
          });
        }), true) : false;
      };
      exports.unstable_batchedUpdates = Qk;
      exports.unstable_renderSubtreeIntoContainer = function(a2, b2, c2, d) {
        if (!ol(c2)) throw Error(p(200));
        if (null == a2 || void 0 === a2._reactInternals) throw Error(p(38));
        return rl(a2, b2, c2, false, d);
      };
      exports.version = "18.3.1-next-f1338f8080-20240426";
    }
  });

  // node_modules/react-dom/index.js
  var require_react_dom = __commonJS({
    "node_modules/react-dom/index.js"(exports, module) {
      "use strict";
      function checkDCE() {
        if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ === "undefined" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE !== "function") {
          return;
        }
        if (false) {
          throw new Error("^_^");
        }
        try {
          __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(checkDCE);
        } catch (err) {
          console.error(err);
        }
      }
      if (true) {
        checkDCE();
        module.exports = require_react_dom_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // node_modules/react-dom/client.js
  var require_client = __commonJS({
    "node_modules/react-dom/client.js"(exports) {
      "use strict";
      var m = require_react_dom();
      if (true) {
        exports.createRoot = m.createRoot;
        exports.hydrateRoot = m.hydrateRoot;
      } else {
        i = m.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
        exports.createRoot = function(c2, o) {
          i.usingClientEntryPoint = true;
          try {
            return m.createRoot(c2, o);
          } finally {
            i.usingClientEntryPoint = false;
          }
        };
        exports.hydrateRoot = function(c2, h, o) {
          i.usingClientEntryPoint = true;
          try {
            return m.hydrateRoot(c2, h, o);
          } finally {
            i.usingClientEntryPoint = false;
          }
        };
      }
      var i;
    }
  });

  // node_modules/react/cjs/react-jsx-runtime.production.min.js
  var require_react_jsx_runtime_production_min = __commonJS({
    "node_modules/react/cjs/react-jsx-runtime.production.min.js"(exports) {
      "use strict";
      var f = require_react();
      var k = Symbol.for("react.element");
      var l = Symbol.for("react.fragment");
      var m = Object.prototype.hasOwnProperty;
      var n = f.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner;
      var p = { key: true, ref: true, __self: true, __source: true };
      function q(c2, a2, g) {
        var b2, d = {}, e = null, h = null;
        void 0 !== g && (e = "" + g);
        void 0 !== a2.key && (e = "" + a2.key);
        void 0 !== a2.ref && (h = a2.ref);
        for (b2 in a2) m.call(a2, b2) && !p.hasOwnProperty(b2) && (d[b2] = a2[b2]);
        if (c2 && c2.defaultProps) for (b2 in a2 = c2.defaultProps, a2) void 0 === d[b2] && (d[b2] = a2[b2]);
        return { $$typeof: k, type: c2, key: e, ref: h, props: d, _owner: n.current };
      }
      exports.Fragment = l;
      exports.jsx = q;
      exports.jsxs = q;
    }
  });

  // node_modules/react/jsx-runtime.js
  var require_jsx_runtime = __commonJS({
    "node_modules/react/jsx-runtime.js"(exports, module) {
      "use strict";
      if (true) {
        module.exports = require_react_jsx_runtime_production_min();
      } else {
        module.exports = null;
      }
    }
  });

  // src/editor/EditorApp.tsx
  var import_client = __toESM(require_client());

  // src/editor/SceneEditorPanel.tsx
  var import_react109 = __toESM(require_react());

  // node_modules/@remotion/player/dist/esm/index.mjs
  var import_jsx_runtime37 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime38 = __toESM(require_jsx_runtime(), 1);

  // node_modules/remotion/dist/esm/index.mjs
  var import_react = __toESM(require_react(), 1);
  var import_react2 = __toESM(require_react(), 1);
  var import_jsx_runtime = __toESM(require_jsx_runtime(), 1);
  var import_react3 = __toESM(require_react(), 1);
  var import_jsx_runtime2 = __toESM(require_jsx_runtime(), 1);
  var import_react4 = __toESM(require_react(), 1);
  var import_react5 = __toESM(require_react(), 1);
  var import_jsx_runtime3 = __toESM(require_jsx_runtime(), 1);
  var import_react6 = __toESM(require_react(), 1);
  var import_react7 = __toESM(require_react(), 1);
  var import_jsx_runtime4 = __toESM(require_jsx_runtime(), 1);
  var import_react8 = __toESM(require_react(), 1);
  var import_react9 = __toESM(require_react(), 1);
  var import_react10 = __toESM(require_react(), 1);
  var import_react11 = __toESM(require_react(), 1);
  var import_react12 = __toESM(require_react(), 1);
  var import_react13 = __toESM(require_react(), 1);
  var import_react14 = __toESM(require_react(), 1);
  var import_react15 = __toESM(require_react(), 1);
  var import_jsx_runtime5 = __toESM(require_jsx_runtime(), 1);
  var import_react16 = __toESM(require_react(), 1);
  var import_react17 = __toESM(require_react(), 1);
  var React6 = __toESM(require_react(), 1);
  var import_jsx_runtime6 = __toESM(require_jsx_runtime(), 1);
  var import_react18 = __toESM(require_react(), 1);
  var import_react19 = __toESM(require_react(), 1);
  var import_react20 = __toESM(require_react(), 1);
  var import_jsx_runtime7 = __toESM(require_jsx_runtime(), 1);
  var import_react21 = __toESM(require_react(), 1);
  var import_react22 = __toESM(require_react(), 1);
  var import_react23 = __toESM(require_react(), 1);
  var import_jsx_runtime8 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime9 = __toESM(require_jsx_runtime(), 1);
  var import_react24 = __toESM(require_react(), 1);
  var import_react25 = __toESM(require_react(), 1);
  var import_jsx_runtime10 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime11 = __toESM(require_jsx_runtime(), 1);
  var import_react26 = __toESM(require_react(), 1);
  var import_react27 = __toESM(require_react(), 1);
  var import_jsx_runtime12 = __toESM(require_jsx_runtime(), 1);
  var import_react28 = __toESM(require_react(), 1);
  var import_react29 = __toESM(require_react(), 1);
  var import_jsx_runtime13 = __toESM(require_jsx_runtime(), 1);
  var import_react30 = __toESM(require_react(), 1);
  var import_react31 = __toESM(require_react(), 1);
  var import_jsx_runtime14 = __toESM(require_jsx_runtime(), 1);
  var import_react32 = __toESM(require_react(), 1);
  var import_jsx_runtime15 = __toESM(require_jsx_runtime(), 1);
  var import_react33 = __toESM(require_react(), 1);
  var import_react34 = __toESM(require_react(), 1);
  var import_react35 = __toESM(require_react(), 1);
  var import_react36 = __toESM(require_react(), 1);
  var import_jsx_runtime16 = __toESM(require_jsx_runtime(), 1);
  var import_react37 = __toESM(require_react(), 1);
  var import_react38 = __toESM(require_react(), 1);
  var import_react39 = __toESM(require_react(), 1);
  var import_react40 = __toESM(require_react(), 1);
  var import_react41 = __toESM(require_react(), 1);
  var import_react42 = __toESM(require_react(), 1);
  var import_react43 = __toESM(require_react(), 1);
  var import_jsx_runtime17 = __toESM(require_jsx_runtime(), 1);
  var import_react44 = __toESM(require_react(), 1);
  var import_react45 = __toESM(require_react(), 1);
  var import_react46 = __toESM(require_react(), 1);
  var import_react47 = __toESM(require_react(), 1);
  var import_react48 = __toESM(require_react(), 1);
  var import_jsx_runtime18 = __toESM(require_jsx_runtime(), 1);
  var import_react49 = __toESM(require_react(), 1);
  var import_jsx_runtime19 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime20 = __toESM(require_jsx_runtime(), 1);
  var import_react50 = __toESM(require_react(), 1);
  var import_react_dom = __toESM(require_react_dom(), 1);
  var import_react51 = __toESM(require_react(), 1);
  var import_jsx_runtime21 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime22 = __toESM(require_jsx_runtime(), 1);
  var import_react52 = __toESM(require_react(), 1);
  var import_jsx_runtime23 = __toESM(require_jsx_runtime(), 1);
  var import_react53 = __toESM(require_react(), 1);
  var import_jsx_runtime24 = __toESM(require_jsx_runtime(), 1);
  var import_react54 = __toESM(require_react(), 1);
  var import_jsx_runtime25 = __toESM(require_jsx_runtime(), 1);
  var import_react55 = __toESM(require_react(), 1);
  var import_react56 = __toESM(require_react(), 1);
  var import_react57 = __toESM(require_react(), 1);
  var import_jsx_runtime26 = __toESM(require_jsx_runtime(), 1);
  var import_react58 = __toESM(require_react(), 1);
  var import_react59 = __toESM(require_react(), 1);
  var import_react60 = __toESM(require_react(), 1);
  var import_jsx_runtime27 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime28 = __toESM(require_jsx_runtime(), 1);
  var import_react61 = __toESM(require_react(), 1);
  var import_react62 = __toESM(require_react(), 1);
  var import_react63 = __toESM(require_react(), 1);
  var import_jsx_runtime29 = __toESM(require_jsx_runtime(), 1);
  var import_react64 = __toESM(require_react(), 1);
  var import_react65 = __toESM(require_react(), 1);
  var import_jsx_runtime30 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime31 = __toESM(require_jsx_runtime(), 1);
  var import_react66 = __toESM(require_react(), 1);
  var import_jsx_runtime32 = __toESM(require_jsx_runtime(), 1);
  var import_react67 = __toESM(require_react(), 1);
  var import_react68 = __toESM(require_react(), 1);
  var import_react69 = __toESM(require_react(), 1);
  var import_jsx_runtime33 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime34 = __toESM(require_jsx_runtime(), 1);
  var import_react70 = __toESM(require_react(), 1);
  var import_react71 = __toESM(require_react(), 1);
  var import_react72 = __toESM(require_react(), 1);
  var import_jsx_runtime35 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime36 = __toESM(require_jsx_runtime(), 1);
  var __defProp2 = Object.defineProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp2(target, name, {
        get: all[name],
        enumerable: true,
        configurable: true,
        set: (newValue) => all[name] = () => newValue
      });
  };
  if (typeof import_react.createContext !== "function") {
    const err = [
      'Remotion requires React.createContext, but it is "undefined".',
      'If you are in a React Server Component, turn it into a client component by adding "use client" at the top of the file.',
      "",
      "Before:",
      '  import {useCurrentFrame} from "remotion";',
      "",
      "After:",
      '  "use client";',
      '  import {useCurrentFrame} from "remotion";'
    ];
    throw new Error(err.join(`
`));
  }
  function getNodeEnvString() {
    return ["NOD", "E_EN", "V"].join("");
  }
  var getEnvString = () => {
    return ["e", "nv"].join("");
  };
  var getRemotionEnvironment = () => {
    const isPlayer = typeof window !== "undefined" && window.remotion_isPlayer;
    const isRendering = typeof window !== "undefined" && typeof window.process !== "undefined" && typeof window.process.env !== "undefined" && (window.process[getEnvString()][getNodeEnvString()] === "test" || window.process[getEnvString()][getNodeEnvString()] === "production" && typeof window !== "undefined" && typeof window.remotion_puppeteerTimeout !== "undefined");
    const isStudio = typeof window !== "undefined" && window.remotion_isStudio;
    const isReadOnlyStudio = typeof window !== "undefined" && window.remotion_isReadOnlyStudio;
    return {
      isStudio,
      isRendering,
      isPlayer,
      isReadOnlyStudio,
      isClientSideRendering: false
    };
  };
  var originalCreateElement = import_react2.default.createElement;
  var originalJsx = import_jsx_runtime.default.jsx;
  var componentsToAddStacksTo = [];
  var enableProxy = (api) => {
    return new Proxy(api, {
      apply(target, thisArg, argArray) {
        if (componentsToAddStacksTo.includes(argArray[0])) {
          const [first, props, ...rest] = argArray;
          const newProps = {
            ...props ?? {},
            stack: new Error().stack
          };
          return Reflect.apply(target, thisArg, [first, newProps, ...rest]);
        }
        return Reflect.apply(target, thisArg, argArray);
      }
    });
  };
  var enableSequenceStackTraces = () => {
    if (!getRemotionEnvironment().isStudio) {
      return;
    }
    import_react2.default.createElement = enableProxy(originalCreateElement);
    import_jsx_runtime.default.jsx = enableProxy(originalJsx);
  };
  var addSequenceStackTraces = (component) => {
    componentsToAddStacksTo.push(component);
    enableSequenceStackTraces();
  };
  var IsPlayerContext = (0, import_react3.createContext)(false);
  var IsPlayerContextProvider = ({
    children
  }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime2.jsx)(IsPlayerContext.Provider, {
      value: true,
      children
    });
  };
  var useIsPlayer = () => {
    return (0, import_react3.useContext)(IsPlayerContext);
  };
  function truthy(value) {
    return Boolean(value);
  }
  var VERSION = "4.0.420";
  var checkMultipleRemotionVersions = () => {
    if (typeof globalThis === "undefined") {
      return;
    }
    const set = () => {
      globalThis.remotion_imported = VERSION;
      if (typeof window !== "undefined") {
        window.remotion_imported = VERSION;
      }
    };
    const alreadyImported = globalThis.remotion_imported || typeof window !== "undefined" && window.remotion_imported;
    if (alreadyImported) {
      if (alreadyImported === VERSION) {
        return;
      }
      if (typeof alreadyImported === "string" && alreadyImported.includes("webcodecs")) {
        set();
        return;
      }
      throw new TypeError(`\u{1F6A8} Multiple versions of Remotion detected: ${[
        VERSION,
        typeof alreadyImported === "string" ? alreadyImported : "an older version"
      ].filter(truthy).join(" and ")}. This will cause things to break in an unexpected way.
Check that all your Remotion packages are on the same version. If your dependencies depend on Remotion, make them peer dependencies. You can also run \`npx remotion versions\` from your terminal to see which versions are mismatching.`);
    }
    set();
  };
  var hasTailwindClassName = ({
    className: className2,
    classPrefix,
    type
  }) => {
    if (!className2) {
      return false;
    }
    if (type === "exact") {
      const split = className2.split(" ");
      return classPrefix.some((token) => {
        return split.some((part) => {
          return part.trim() === token || part.trim().endsWith(`:${token}`) || part.trim().endsWith(`!${token}`);
        });
      });
    }
    return classPrefix.some((prefix) => {
      return className2.startsWith(prefix) || className2.includes(` ${prefix}`) || className2.includes(`!${prefix}`) || className2.includes(`:${prefix}`);
    });
  };
  var AbsoluteFillRefForwarding = (props, ref) => {
    const { style: style2, ...other } = props;
    const actualStyle = (0, import_react5.useMemo)(() => {
      return {
        position: "absolute",
        top: hasTailwindClassName({
          className: other.className,
          classPrefix: ["top-", "inset-"],
          type: "prefix"
        }) ? void 0 : 0,
        left: hasTailwindClassName({
          className: other.className,
          classPrefix: ["left-", "inset-"],
          type: "prefix"
        }) ? void 0 : 0,
        right: hasTailwindClassName({
          className: other.className,
          classPrefix: ["right-", "inset-"],
          type: "prefix"
        }) ? void 0 : 0,
        bottom: hasTailwindClassName({
          className: other.className,
          classPrefix: ["bottom-", "inset-"],
          type: "prefix"
        }) ? void 0 : 0,
        width: hasTailwindClassName({
          className: other.className,
          classPrefix: ["w-"],
          type: "prefix"
        }) ? void 0 : "100%",
        height: hasTailwindClassName({
          className: other.className,
          classPrefix: ["h-"],
          type: "prefix"
        }) ? void 0 : "100%",
        display: hasTailwindClassName({
          className: other.className,
          classPrefix: [
            "block",
            "inline-block",
            "inline",
            "flex",
            "inline-flex",
            "flow-root",
            "grid",
            "inline-grid",
            "contents",
            "list-item",
            "hidden"
          ],
          type: "exact"
        }) ? void 0 : "flex",
        flexDirection: hasTailwindClassName({
          className: other.className,
          classPrefix: [
            "flex-row",
            "flex-col",
            "flex-row-reverse",
            "flex-col-reverse"
          ],
          type: "exact"
        }) ? void 0 : "column",
        ...style2
      };
    }, [other.className, style2]);
    return /* @__PURE__ */ (0, import_jsx_runtime3.jsx)("div", {
      ref,
      style: actualStyle,
      ...other
    });
  };
  var AbsoluteFill = (0, import_react5.forwardRef)(AbsoluteFillRefForwarding);
  var SequenceContext = (0, import_react6.createContext)(null);
  var SequenceManager = import_react7.default.createContext({
    registerSequence: () => {
      throw new Error("SequenceManagerContext not initialized");
    },
    unregisterSequence: () => {
      throw new Error("SequenceManagerContext not initialized");
    },
    sequences: []
  });
  var SequenceVisibilityToggleContext = import_react7.default.createContext({
    hidden: {},
    setHidden: () => {
      throw new Error("SequenceVisibilityToggle not initialized");
    }
  });
  var SequenceManagerProvider = ({ children }) => {
    const [sequences, setSequences] = (0, import_react7.useState)([]);
    const [hidden, setHidden] = (0, import_react7.useState)({});
    const registerSequence = (0, import_react7.useCallback)((seq) => {
      setSequences((seqs) => {
        return [...seqs, seq];
      });
    }, []);
    const unregisterSequence = (0, import_react7.useCallback)((seq) => {
      setSequences((seqs) => seqs.filter((s) => s.id !== seq));
    }, []);
    const sequenceContext = (0, import_react7.useMemo)(() => {
      return {
        registerSequence,
        sequences,
        unregisterSequence
      };
    }, [registerSequence, sequences, unregisterSequence]);
    const hiddenContext = (0, import_react7.useMemo)(() => {
      return {
        hidden,
        setHidden
      };
    }, [hidden]);
    return /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(SequenceManager.Provider, {
      value: sequenceContext,
      children: /* @__PURE__ */ (0, import_jsx_runtime4.jsx)(SequenceVisibilityToggleContext.Provider, {
        value: hiddenContext,
        children
      })
    });
  };
  function mulberry32(a2) {
    let t = a2 + 1831565813;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
  function hashCode(str) {
    let i = 0;
    let chr = 0;
    let hash = 0;
    for (i = 0; i < str.length; i++) {
      chr = str.charCodeAt(i);
      hash = (hash << 5) - hash + chr;
      hash |= 0;
    }
    return hash;
  }
  var random = (seed, dummy) => {
    if (dummy !== void 0) {
      throw new TypeError("random() takes only one argument");
    }
    if (seed === null) {
      return Math.random();
    }
    if (typeof seed === "string") {
      return mulberry32(hashCode(seed));
    }
    if (typeof seed === "number") {
      return mulberry32(seed * 1e10);
    }
    throw new Error("random() argument must be a number or a string");
  };
  var exports_timeline_position_state = {};
  __export(exports_timeline_position_state, {
    useTimelineSetFrame: () => useTimelineSetFrame,
    useTimelinePosition: () => useTimelinePosition,
    usePlayingState: () => usePlayingState,
    persistCurrentFrame: () => persistCurrentFrame,
    getInitialFrameState: () => getInitialFrameState,
    getFrameForComposition: () => getFrameForComposition
  });
  var RemotionEnvironmentContext = import_react11.default.createContext(null);
  var useRemotionEnvironment = () => {
    const context = (0, import_react10.useContext)(RemotionEnvironmentContext);
    const [env] = (0, import_react10.useState)(() => getRemotionEnvironment());
    return context ?? env;
  };
  var CompositionManager = (0, import_react13.createContext)({
    compositions: [],
    folders: [],
    currentCompositionMetadata: null,
    canvasContent: null
  });
  var CompositionSetters = (0, import_react13.createContext)({
    registerComposition: () => {
      return;
    },
    unregisterComposition: () => {
      return;
    },
    registerFolder: () => {
      return;
    },
    unregisterFolder: () => {
      return;
    },
    setCanvasContent: () => {
      return;
    },
    updateCompositionDefaultProps: () => {
      return;
    },
    onlyRenderComposition: null
  });
  var EditorPropsContext = (0, import_react15.createContext)({
    props: {},
    updateProps: () => {
      throw new Error("Not implemented");
    },
    resetUnsaved: () => {
      throw new Error("Not implemented");
    }
  });
  var editorPropsProviderRef = import_react15.default.createRef();
  var timeValueRef = import_react15.default.createRef();
  var EditorPropsProvider = ({ children }) => {
    const [props, setProps] = import_react15.default.useState({});
    const updateProps = (0, import_react15.useCallback)(({
      defaultProps,
      id,
      newProps
    }) => {
      setProps((prev) => {
        return {
          ...prev,
          [id]: typeof newProps === "function" ? newProps(prev[id] ?? defaultProps) : newProps
        };
      });
    }, []);
    const resetUnsaved = (0, import_react15.useCallback)((compositionId) => {
      setProps((prev) => {
        if (prev[compositionId]) {
          const newProps = { ...prev };
          delete newProps[compositionId];
          return newProps;
        }
        return prev;
      });
    }, []);
    (0, import_react15.useImperativeHandle)(editorPropsProviderRef, () => {
      return {
        getProps: () => props,
        setProps
      };
    }, [props]);
    const ctx = (0, import_react15.useMemo)(() => {
      return { props, updateProps, resetUnsaved };
    }, [props, resetUnsaved, updateProps]);
    return /* @__PURE__ */ (0, import_jsx_runtime5.jsx)(EditorPropsContext.Provider, {
      value: ctx,
      children
    });
  };
  var getKey = () => {
    return `remotion_inputPropsOverride` + window.location.origin;
  };
  var getInputPropsOverride = () => {
    if (typeof localStorage === "undefined")
      return null;
    const override = localStorage.getItem(getKey());
    if (!override)
      return null;
    return JSON.parse(override);
  };
  var setInputPropsOverride = (override) => {
    if (typeof localStorage === "undefined")
      return;
    if (override === null) {
      localStorage.removeItem(getKey());
      return;
    }
    localStorage.setItem(getKey(), JSON.stringify(override));
  };
  var DATE_TOKEN = "remotion-date:";
  var FILE_TOKEN = "remotion-file:";
  var serializeJSONWithSpecialTypes = ({
    data,
    indent,
    staticBase
  }) => {
    let customDateUsed = false;
    let customFileUsed = false;
    let mapUsed = false;
    let setUsed = false;
    try {
      const serializedString = JSON.stringify(data, function(key, value) {
        const item = this[key];
        if (item instanceof Date) {
          customDateUsed = true;
          return `${DATE_TOKEN}${item.toISOString()}`;
        }
        if (item instanceof Map) {
          mapUsed = true;
          return value;
        }
        if (item instanceof Set) {
          setUsed = true;
          return value;
        }
        if (typeof item === "string" && staticBase !== null && item.startsWith(staticBase)) {
          customFileUsed = true;
          return `${FILE_TOKEN}${item.replace(staticBase + "/", "")}`;
        }
        return value;
      }, indent);
      return { serializedString, customDateUsed, customFileUsed, mapUsed, setUsed };
    } catch (err) {
      throw new Error("Could not serialize the passed input props to JSON: " + err.message);
    }
  };
  var deserializeJSONWithSpecialTypes = (data) => {
    return JSON.parse(data, (_, value) => {
      if (typeof value === "string" && value.startsWith(DATE_TOKEN)) {
        return new Date(value.replace(DATE_TOKEN, ""));
      }
      if (typeof value === "string" && value.startsWith(FILE_TOKEN)) {
        return `${window.remotion_staticBase}/${value.replace(FILE_TOKEN, "")}`;
      }
      return value;
    });
  };
  var serializeThenDeserialize = (props) => {
    return deserializeJSONWithSpecialTypes(serializeJSONWithSpecialTypes({
      data: props,
      indent: 2,
      staticBase: window.remotion_staticBase
    }).serializedString);
  };
  var serializeThenDeserializeInStudio = (props) => {
    if (getRemotionEnvironment().isStudio) {
      return serializeThenDeserialize(props);
    }
    return props;
  };
  var didWarnSSRImport = false;
  var warnOnceSSRImport = () => {
    if (didWarnSSRImport) {
      return;
    }
    didWarnSSRImport = true;
    console.warn("Called `getInputProps()` on the server. This function is not available server-side and has returned an empty object.");
    console.warn("To hide this warning, don't call this function on the server:");
    console.warn("  typeof window === 'undefined' ? {} : getInputProps()");
  };
  var getInputProps = () => {
    if (typeof window === "undefined") {
      warnOnceSSRImport();
      return {};
    }
    if (getRemotionEnvironment().isPlayer) {
      throw new Error("You cannot call `getInputProps()` from a <Player>. Instead, the props are available as React props from component that you passed as `component` prop.");
    }
    const override = getInputPropsOverride();
    if (override) {
      return override;
    }
    if (typeof window === "undefined" || typeof window.remotion_inputProps === "undefined") {
      throw new Error("Cannot call `getInputProps()` - window.remotion_inputProps is not set. This API is only available if you are in the Studio, or while you are rendering server-side.");
    }
    const param = window.remotion_inputProps;
    if (!param) {
      return {};
    }
    const parsed = deserializeJSONWithSpecialTypes(param);
    return parsed;
  };
  function validateDimension(amount, nameOfProp, location) {
    if (typeof amount !== "number") {
      throw new Error(`The "${nameOfProp}" prop ${location} must be a number, but you passed a value of type ${typeof amount}`);
    }
    if (isNaN(amount)) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must not be NaN, but is NaN.`);
    }
    if (!Number.isFinite(amount)) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be finite, but is ${amount}.`);
    }
    if (amount % 1 !== 0) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be an integer, but is ${amount}.`);
    }
    if (amount <= 0) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be positive, but got ${amount}.`);
    }
  }
  function validateDurationInFrames(durationInFrames, options) {
    const { allowFloats, component } = options;
    if (typeof durationInFrames === "undefined") {
      throw new Error(`The "durationInFrames" prop ${component} is missing.`);
    }
    if (typeof durationInFrames !== "number") {
      throw new Error(`The "durationInFrames" prop ${component} must be a number, but you passed a value of type ${typeof durationInFrames}`);
    }
    if (durationInFrames <= 0) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be positive, but got ${durationInFrames}.`);
    }
    if (!allowFloats && durationInFrames % 1 !== 0) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be an integer, but got ${durationInFrames}.`);
    }
    if (!Number.isFinite(durationInFrames)) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be finite, but got ${durationInFrames}.`);
    }
  }
  function validateFps(fps, location, isGif) {
    if (typeof fps !== "number") {
      throw new Error(`"fps" must be a number, but you passed a value of type ${typeof fps} ${location}`);
    }
    if (!Number.isFinite(fps)) {
      throw new Error(`"fps" must be a finite, but you passed ${fps} ${location}`);
    }
    if (isNaN(fps)) {
      throw new Error(`"fps" must not be NaN, but got ${fps} ${location}`);
    }
    if (fps <= 0) {
      throw new TypeError(`"fps" must be positive, but got ${fps} ${location}`);
    }
    if (isGif && fps > 50) {
      throw new TypeError(`The FPS for a GIF cannot be higher than 50. Use the --every-nth-frame option to lower the FPS: https://remotion.dev/docs/render-as-gif`);
    }
  }
  var ResolveCompositionContext = (0, import_react14.createContext)(null);
  var resolveCompositionsRef = (0, import_react14.createRef)();
  var needsResolution = (composition) => {
    return Boolean(composition.calculateMetadata);
  };
  var PROPS_UPDATED_EXTERNALLY = "remotion.propsUpdatedExternally";
  var useResolvedVideoConfig = (preferredCompositionId) => {
    const context = (0, import_react14.useContext)(ResolveCompositionContext);
    const { props: allEditorProps } = (0, import_react14.useContext)(EditorPropsContext);
    const { compositions, canvasContent, currentCompositionMetadata } = (0, import_react14.useContext)(CompositionManager);
    const currentComposition = canvasContent?.type === "composition" ? canvasContent.compositionId : null;
    const compositionId = preferredCompositionId ?? currentComposition;
    const composition = compositions.find((c2) => c2.id === compositionId);
    const selectedEditorProps = (0, import_react14.useMemo)(() => {
      return composition ? allEditorProps[composition.id] ?? {} : {};
    }, [allEditorProps, composition]);
    const env = useRemotionEnvironment();
    return (0, import_react14.useMemo)(() => {
      if (!composition) {
        return null;
      }
      if (currentCompositionMetadata) {
        return {
          type: "success",
          result: {
            ...currentCompositionMetadata,
            id: composition.id,
            defaultProps: composition.defaultProps ?? {}
          }
        };
      }
      if (!needsResolution(composition)) {
        validateDurationInFrames(composition.durationInFrames, {
          allowFloats: false,
          component: `in <Composition id="${composition.id}">`
        });
        validateFps(composition.fps, `in <Composition id="${composition.id}">`, false);
        validateDimension(composition.width, "width", `in <Composition id="${composition.id}">`);
        validateDimension(composition.height, "height", `in <Composition id="${composition.id}">`);
        return {
          type: "success",
          result: {
            width: composition.width,
            height: composition.height,
            fps: composition.fps,
            id: composition.id,
            durationInFrames: composition.durationInFrames,
            defaultProps: composition.defaultProps ?? {},
            props: {
              ...composition.defaultProps ?? {},
              ...selectedEditorProps ?? {},
              ...typeof window === "undefined" || env.isPlayer || !window.remotion_inputProps ? {} : getInputProps() ?? {}
            },
            defaultCodec: null,
            defaultOutName: null,
            defaultVideoImageFormat: null,
            defaultPixelFormat: null,
            defaultProResProfile: null
          }
        };
      }
      if (!context) {
        return null;
      }
      if (!context[composition.id]) {
        return null;
      }
      return context[composition.id];
    }, [
      composition,
      context,
      currentCompositionMetadata,
      selectedEditorProps,
      env.isPlayer
    ]);
  };
  var useVideo = () => {
    const { canvasContent, compositions, currentCompositionMetadata } = (0, import_react12.useContext)(CompositionManager);
    const selected = compositions.find((c2) => {
      return canvasContent?.type === "composition" && c2.id === canvasContent.compositionId;
    });
    const resolved = useResolvedVideoConfig(selected?.id ?? null);
    return (0, import_react12.useMemo)(() => {
      if (!resolved) {
        return null;
      }
      if (resolved.type === "error") {
        return null;
      }
      if (resolved.type === "loading") {
        return null;
      }
      if (!selected) {
        return null;
      }
      return {
        ...resolved.result,
        defaultProps: selected.defaultProps ?? {},
        id: selected.id,
        ...currentCompositionMetadata ?? {},
        component: selected.component
      };
    }, [currentCompositionMetadata, resolved, selected]);
  };
  var makeKey = () => {
    return `remotion.time-all`;
  };
  var persistCurrentFrame = (time) => {
    localStorage.setItem(makeKey(), JSON.stringify(time));
  };
  var getInitialFrameState = () => {
    const item = localStorage.getItem(makeKey()) ?? "{}";
    const obj = JSON.parse(item);
    return obj;
  };
  var getFrameForComposition = (composition) => {
    const item = localStorage.getItem(makeKey()) ?? "{}";
    const obj = JSON.parse(item);
    if (obj[composition] !== void 0) {
      return Number(obj[composition]);
    }
    if (typeof window === "undefined") {
      return 0;
    }
    return window.remotion_initialFrame ?? 0;
  };
  var useTimelinePosition = () => {
    const videoConfig = useVideo();
    const state = (0, import_react9.useContext)(TimelineContext);
    const env = useRemotionEnvironment();
    if (!videoConfig) {
      return typeof window === "undefined" ? 0 : window.remotion_initialFrame ?? 0;
    }
    const unclamped = state.frame[videoConfig.id] ?? (env.isPlayer ? 0 : getFrameForComposition(videoConfig.id));
    return Math.min(videoConfig.durationInFrames - 1, unclamped);
  };
  var useTimelineSetFrame = () => {
    const { setFrame } = (0, import_react9.useContext)(SetTimelineContext);
    return setFrame;
  };
  var usePlayingState = () => {
    const { playing, imperativePlaying } = (0, import_react9.useContext)(TimelineContext);
    const { setPlaying } = (0, import_react9.useContext)(SetTimelineContext);
    return (0, import_react9.useMemo)(() => [playing, setPlaying, imperativePlaying], [imperativePlaying, playing, setPlaying]);
  };
  var getErrorStackWithMessage = (error2) => {
    const stack = error2.stack ?? "";
    return stack.startsWith("Error:") ? stack : `${error2.message}
${stack}`;
  };
  var isErrorLike = (err) => {
    if (err instanceof Error) {
      return true;
    }
    if (err === null) {
      return false;
    }
    if (typeof err !== "object") {
      return false;
    }
    if (!("stack" in err)) {
      return false;
    }
    if (typeof err.stack !== "string") {
      return false;
    }
    if (!("message" in err)) {
      return false;
    }
    if (typeof err.message !== "string") {
      return false;
    }
    return true;
  };
  function cancelRenderInternal(scope, err) {
    let error2;
    if (isErrorLike(err)) {
      error2 = err;
      if (!error2.stack) {
        error2.stack = new Error(error2.message).stack;
      }
    } else if (typeof err === "string") {
      error2 = Error(err);
    } else {
      error2 = Error("Rendering was cancelled");
    }
    if (scope) {
      scope.remotion_cancelledError = getErrorStackWithMessage(error2);
    }
    throw error2;
  }
  function cancelRender(err) {
    return cancelRenderInternal(typeof window !== "undefined" ? window : void 0, err);
  }
  var logLevels = ["trace", "verbose", "info", "warn", "error"];
  var getNumberForLogLevel = (level) => {
    return logLevels.indexOf(level);
  };
  var isEqualOrBelowLogLevel = (currentLevel, level) => {
    return getNumberForLogLevel(currentLevel) <= getNumberForLogLevel(level);
  };
  var transformArgs = ({
    args,
    logLevel,
    tag
  }) => {
    const arr = [...args];
    if (getRemotionEnvironment().isRendering && !getRemotionEnvironment().isClientSideRendering) {
      arr.unshift(Symbol.for(`__remotion_level_${logLevel}`));
    }
    if (tag && getRemotionEnvironment().isRendering && !getRemotionEnvironment().isClientSideRendering) {
      arr.unshift(Symbol.for(`__remotion_tag_${tag}`));
    }
    return arr;
  };
  var verbose = (options, ...args) => {
    if (isEqualOrBelowLogLevel(options.logLevel, "verbose")) {
      return console.debug(...transformArgs({ args, logLevel: "verbose", tag: options.tag }));
    }
  };
  var trace = (options, ...args) => {
    if (isEqualOrBelowLogLevel(options.logLevel, "trace")) {
      return console.debug(...transformArgs({ args, logLevel: "trace", tag: options.tag }));
    }
  };
  var info = (options, ...args) => {
    if (isEqualOrBelowLogLevel(options.logLevel, "info")) {
      return console.log(...transformArgs({ args, logLevel: "info", tag: options.tag }));
    }
  };
  var warn = (options, ...args) => {
    if (isEqualOrBelowLogLevel(options.logLevel, "warn")) {
      return console.warn(...transformArgs({ args, logLevel: "warn", tag: options.tag }));
    }
  };
  var error = (options, ...args) => {
    return console.error(...transformArgs({ args, logLevel: "error", tag: options.tag }));
  };
  var Log = {
    trace,
    verbose,
    info,
    warn,
    error
  };
  if (typeof window !== "undefined") {
    window.remotion_renderReady = false;
    if (!window.remotion_delayRenderTimeouts) {
      window.remotion_delayRenderTimeouts = {};
    }
    window.remotion_delayRenderHandles = [];
  }
  var DELAY_RENDER_CALLSTACK_TOKEN = "The delayRender was called:";
  var DELAY_RENDER_RETRIES_LEFT = "Retries left: ";
  var DELAY_RENDER_RETRY_TOKEN = "- Rendering the frame will be retried.";
  var DELAY_RENDER_CLEAR_TOKEN = "handle was cleared after";
  var defaultTimeout = 3e4;
  var delayRenderInternal = ({
    scope,
    environment,
    label: label3,
    options
  }) => {
    if (typeof label3 !== "string" && label3 !== null) {
      throw new Error("The label parameter of delayRender() must be a string or undefined, got: " + JSON.stringify(label3));
    }
    const handle = Math.random();
    scope.remotion_delayRenderHandles.push(handle);
    const called = Error().stack?.replace(/^Error/g, "") ?? "";
    if (environment.isRendering) {
      const timeoutToUse = (options?.timeoutInMilliseconds ?? scope.remotion_puppeteerTimeout ?? defaultTimeout) - 2e3;
      const retriesLeft = (options?.retries ?? 0) - (scope.remotion_attempt - 1);
      scope.remotion_delayRenderTimeouts[handle] = {
        label: label3 ?? null,
        startTime: Date.now(),
        timeout: setTimeout(() => {
          const message = [
            `A delayRender()`,
            label3 ? `"${label3}"` : null,
            `was called but not cleared after ${timeoutToUse}ms. See https://remotion.dev/docs/timeout for help.`,
            retriesLeft > 0 ? DELAY_RENDER_RETRIES_LEFT + retriesLeft : null,
            retriesLeft > 0 ? DELAY_RENDER_RETRY_TOKEN : null,
            DELAY_RENDER_CALLSTACK_TOKEN,
            called
          ].filter(truthy).join(" ");
          if (environment.isClientSideRendering) {
            scope.remotion_cancelledError = getErrorStackWithMessage(Error(message));
          } else {
            cancelRenderInternal(scope, Error(message));
          }
        }, timeoutToUse)
      };
    }
    scope.remotion_renderReady = false;
    return handle;
  };
  var delayRender = (label3, options) => {
    if (typeof window === "undefined") {
      return Math.random();
    }
    return delayRenderInternal({
      scope: window,
      environment: getRemotionEnvironment(),
      label: label3 ?? null,
      options: options ?? {}
    });
  };
  var continueRenderInternal = ({
    scope,
    handle,
    environment,
    logLevel
  }) => {
    if (typeof handle === "undefined") {
      throw new TypeError("The continueRender() method must be called with a parameter that is the return value of delayRender(). No value was passed.");
    }
    if (typeof handle !== "number") {
      throw new TypeError("The parameter passed into continueRender() must be the return value of delayRender() which is a number. Got: " + JSON.stringify(handle));
    }
    scope.remotion_delayRenderHandles = scope.remotion_delayRenderHandles.filter((h) => {
      if (h === handle) {
        if (environment.isRendering && scope !== void 0) {
          if (!scope.remotion_delayRenderTimeouts[handle]) {
            return false;
          }
          const { label: label3, startTime, timeout } = scope.remotion_delayRenderTimeouts[handle];
          clearTimeout(timeout);
          const message = [
            label3 ? `"${label3}"` : "A handle",
            DELAY_RENDER_CLEAR_TOKEN,
            `${Date.now() - startTime}ms`
          ].filter(truthy).join(" ");
          Log.verbose({ logLevel, tag: "delayRender()" }, message);
          delete scope.remotion_delayRenderTimeouts[handle];
        }
        return false;
      }
      return true;
    });
    if (scope.remotion_delayRenderHandles.length === 0) {
      scope.remotion_renderReady = true;
    }
  };
  var continueRender = (handle) => {
    if (typeof window === "undefined") {
      return;
    }
    continueRenderInternal({
      scope: window,
      handle,
      environment: getRemotionEnvironment(),
      logLevel: window.remotion_logLevel ?? "info"
    });
  };
  var LogLevelContext = (0, import_react17.createContext)({
    logLevel: "info",
    mountTime: 0
  });
  var useLogLevel = () => {
    const { logLevel } = React6.useContext(LogLevelContext);
    if (logLevel === null) {
      throw new Error("useLogLevel must be used within a LogLevelProvider");
    }
    return logLevel;
  };
  var useMountTime = () => {
    const { mountTime } = React6.useContext(LogLevelContext);
    if (mountTime === null) {
      throw new Error("useMountTime must be used within a LogLevelProvider");
    }
    return mountTime;
  };
  var DelayRenderContextType = (0, import_react16.createContext)(null);
  var useDelayRender = () => {
    const environment = useRemotionEnvironment();
    const scope = (0, import_react16.useContext)(DelayRenderContextType) ?? (typeof window !== "undefined" ? window : void 0);
    const logLevel = useLogLevel();
    const delayRender2 = (0, import_react16.useCallback)((label3, options) => {
      if (!scope) {
        return Math.random();
      }
      return delayRenderInternal({
        scope,
        environment,
        label: label3 ?? null,
        options: options ?? {}
      });
    }, [environment, scope]);
    const continueRender2 = (0, import_react16.useCallback)((handle) => {
      if (!scope) {
        return;
      }
      continueRenderInternal({
        scope,
        handle,
        environment,
        logLevel
      });
    }, [environment, logLevel, scope]);
    const cancelRender2 = (0, import_react16.useCallback)((err) => {
      return cancelRenderInternal(scope ?? (typeof window !== "undefined" ? window : void 0), err);
    }, [scope]);
    return { delayRender: delayRender2, continueRender: continueRender2, cancelRender: cancelRender2 };
  };
  var SetTimelineContext = (0, import_react8.createContext)({
    setFrame: () => {
      throw new Error("default");
    },
    setPlaying: () => {
      throw new Error("default");
    }
  });
  var TimelineContext = (0, import_react8.createContext)({
    frame: {},
    playing: false,
    playbackRate: 1,
    rootId: "",
    imperativePlaying: {
      current: false
    },
    setPlaybackRate: () => {
      throw new Error("default");
    },
    audioAndVideoTags: { current: [] }
  });
  var TimelineContextProvider = ({ children, frameState }) => {
    const [playing, setPlaying] = (0, import_react8.useState)(false);
    const imperativePlaying = (0, import_react8.useRef)(false);
    const [playbackRate, setPlaybackRate] = (0, import_react8.useState)(1);
    const audioAndVideoTags = (0, import_react8.useRef)([]);
    const [remotionRootId] = (0, import_react8.useState)(() => String(random(null)));
    const [_frame, setFrame] = (0, import_react8.useState)(() => getInitialFrameState());
    const frame = frameState ?? _frame;
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    if (typeof window !== "undefined") {
      (0, import_react8.useLayoutEffect)(() => {
        window.remotion_setFrame = (f, composition, attempt) => {
          window.remotion_attempt = attempt;
          const id = delayRender2(`Setting the current frame to ${f}`);
          let asyncUpdate = true;
          setFrame((s) => {
            const currentFrame = s[composition] ?? window.remotion_initialFrame;
            if (currentFrame === f) {
              asyncUpdate = false;
              return s;
            }
            return {
              ...s,
              [composition]: f
            };
          });
          if (asyncUpdate) {
            requestAnimationFrame(() => continueRender2(id));
          } else {
            continueRender2(id);
          }
        };
        window.remotion_isPlayer = false;
      }, [continueRender2, delayRender2]);
    }
    const timelineContextValue = (0, import_react8.useMemo)(() => {
      return {
        frame,
        playing,
        imperativePlaying,
        rootId: remotionRootId,
        playbackRate,
        setPlaybackRate,
        audioAndVideoTags
      };
    }, [frame, playbackRate, playing, remotionRootId]);
    const setTimelineContextValue = (0, import_react8.useMemo)(() => {
      return {
        setFrame,
        setPlaying
      };
    }, []);
    return /* @__PURE__ */ (0, import_jsx_runtime6.jsx)(TimelineContext.Provider, {
      value: timelineContextValue,
      children: /* @__PURE__ */ (0, import_jsx_runtime6.jsx)(SetTimelineContext.Provider, {
        value: setTimelineContextValue,
        children
      })
    });
  };
  var NonceContext = (0, import_react18.createContext)({
    getNonce: () => 0
  });
  var useNonce = () => {
    const context = (0, import_react18.useContext)(NonceContext);
    const [nonce, setNonce] = (0, import_react18.useState)(() => context.getNonce());
    const lastContext = (0, import_react18.useRef)(context);
    (0, import_react18.useEffect)(() => {
      if (lastContext.current === context) {
        return;
      }
      lastContext.current = context;
      setNonce(context.getNonce);
    }, [context]);
    return nonce;
  };
  var CanUseRemotionHooks = (0, import_react20.createContext)(false);
  var CanUseRemotionHooksProvider = ({ children }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime7.jsx)(CanUseRemotionHooks.Provider, {
      value: true,
      children
    });
  };
  var useUnsafeVideoConfig = () => {
    const context = (0, import_react21.useContext)(SequenceContext);
    const ctxWidth = context?.width ?? null;
    const ctxHeight = context?.height ?? null;
    const ctxDuration = context?.durationInFrames ?? null;
    const video = useVideo();
    return (0, import_react21.useMemo)(() => {
      if (!video) {
        return null;
      }
      const {
        id,
        durationInFrames,
        fps,
        height,
        width,
        defaultProps,
        props,
        defaultCodec,
        defaultOutName,
        defaultVideoImageFormat,
        defaultPixelFormat,
        defaultProResProfile
      } = video;
      return {
        id,
        width: ctxWidth ?? width,
        height: ctxHeight ?? height,
        fps,
        durationInFrames: ctxDuration ?? durationInFrames,
        defaultProps,
        props,
        defaultCodec,
        defaultOutName,
        defaultVideoImageFormat,
        defaultPixelFormat,
        defaultProResProfile
      };
    }, [ctxDuration, ctxHeight, ctxWidth, video]);
  };
  var useVideoConfig = () => {
    const videoConfig = useUnsafeVideoConfig();
    const context = (0, import_react19.useContext)(CanUseRemotionHooks);
    const isPlayer = useIsPlayer();
    if (!videoConfig) {
      if (typeof window !== "undefined" && window.remotion_isPlayer || isPlayer) {
        throw new Error([
          "No video config found. Likely reasons:",
          "- You are probably calling useVideoConfig() from outside the component passed to <Player />. See https://www.remotion.dev/docs/player/examples for how to set up the Player correctly.",
          "- You have multiple versions of Remotion installed which causes the React context to get lost."
        ].join("-"));
      }
      throw new Error("No video config found. You are probably calling useVideoConfig() from a component which has not been registered as a <Composition />. See https://www.remotion.dev/docs/the-fundamentals#defining-compositions for more information.");
    }
    if (!context) {
      throw new Error("Called useVideoConfig() outside a Remotion composition.");
    }
    return videoConfig;
  };
  var useCurrentFrame = () => {
    const canUseRemotionHooks = (0, import_react23.useContext)(CanUseRemotionHooks);
    const env = useRemotionEnvironment();
    if (!canUseRemotionHooks) {
      if (env.isPlayer) {
        throw new Error(`useCurrentFrame can only be called inside a component that was passed to <Player>. See: https://www.remotion.dev/docs/player/examples`);
      }
      throw new Error(`useCurrentFrame() can only be called inside a component that was registered as a composition. See https://www.remotion.dev/docs/the-fundamentals#defining-compositions`);
    }
    const frame = useTimelinePosition();
    const context = (0, import_react23.useContext)(SequenceContext);
    const contextOffset = context ? context.cumulatedFrom + context.relativeFrom : 0;
    return frame - contextOffset;
  };
  var Freeze = ({
    frame: frameToFreeze,
    children,
    active = true
  }) => {
    const frame = useCurrentFrame();
    const videoConfig = useVideoConfig();
    if (typeof frameToFreeze === "undefined") {
      throw new Error(`The <Freeze /> component requires a 'frame' prop, but none was passed.`);
    }
    if (typeof frameToFreeze !== "number") {
      throw new Error(`The 'frame' prop of <Freeze /> must be a number, but is of type ${typeof frameToFreeze}`);
    }
    if (Number.isNaN(frameToFreeze)) {
      throw new Error(`The 'frame' prop of <Freeze /> must be a real number, but it is NaN.`);
    }
    if (!Number.isFinite(frameToFreeze)) {
      throw new Error(`The 'frame' prop of <Freeze /> must be a finite number, but it is ${frameToFreeze}.`);
    }
    const isActive = (0, import_react22.useMemo)(() => {
      if (typeof active === "boolean") {
        return active;
      }
      if (typeof active === "function") {
        return active(frame);
      }
    }, [active, frame]);
    const timelineContext = (0, import_react22.useContext)(TimelineContext);
    const sequenceContext = (0, import_react22.useContext)(SequenceContext);
    const relativeFrom = sequenceContext?.relativeFrom ?? 0;
    const timelineValue = (0, import_react22.useMemo)(() => {
      if (!isActive) {
        return timelineContext;
      }
      return {
        ...timelineContext,
        playing: false,
        imperativePlaying: {
          current: false
        },
        frame: {
          [videoConfig.id]: frameToFreeze + relativeFrom
        }
      };
    }, [isActive, timelineContext, videoConfig.id, frameToFreeze, relativeFrom]);
    const newSequenceContext = (0, import_react22.useMemo)(() => {
      if (!sequenceContext) {
        return null;
      }
      if (!isActive) {
        return sequenceContext;
      }
      return {
        ...sequenceContext,
        cumulatedFrom: 0
      };
    }, [sequenceContext, isActive]);
    return /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(TimelineContext.Provider, {
      value: timelineValue,
      children: /* @__PURE__ */ (0, import_jsx_runtime8.jsx)(SequenceContext.Provider, {
        value: newSequenceContext,
        children
      })
    });
  };
  var RegularSequenceRefForwardingFunction = ({
    from = 0,
    durationInFrames = Infinity,
    children,
    name,
    height,
    width,
    showInTimeline = true,
    _remotionInternalLoopDisplay: loopDisplay,
    _remotionInternalStack: stack,
    _remotionInternalPremountDisplay: premountDisplay,
    _remotionInternalPostmountDisplay: postmountDisplay,
    ...other
  }, ref) => {
    const { layout = "absolute-fill" } = other;
    const [id] = (0, import_react4.useState)(() => String(Math.random()));
    const parentSequence = (0, import_react4.useContext)(SequenceContext);
    const { rootId } = (0, import_react4.useContext)(TimelineContext);
    const cumulatedFrom = parentSequence ? parentSequence.cumulatedFrom + parentSequence.relativeFrom : 0;
    const nonce = useNonce();
    if (layout !== "absolute-fill" && layout !== "none") {
      throw new TypeError(`The layout prop of <Sequence /> expects either "absolute-fill" or "none", but you passed: ${layout}`);
    }
    if (layout === "none" && typeof other.style !== "undefined") {
      throw new TypeError('If layout="none", you may not pass a style.');
    }
    if (typeof durationInFrames !== "number") {
      throw new TypeError(`You passed to durationInFrames an argument of type ${typeof durationInFrames}, but it must be a number.`);
    }
    if (durationInFrames <= 0) {
      throw new TypeError(`durationInFrames must be positive, but got ${durationInFrames}`);
    }
    if (typeof from !== "number") {
      throw new TypeError(`You passed to the "from" props of your <Sequence> an argument of type ${typeof from}, but it must be a number.`);
    }
    if (!Number.isFinite(from)) {
      throw new TypeError(`The "from" prop of a sequence must be finite, but got ${from}.`);
    }
    const absoluteFrame = useTimelinePosition();
    const videoConfig = useVideoConfig();
    const parentSequenceDuration = parentSequence ? Math.min(parentSequence.durationInFrames - from, durationInFrames) : durationInFrames;
    const actualDurationInFrames = Math.max(0, Math.min(videoConfig.durationInFrames - from, parentSequenceDuration));
    const { registerSequence, unregisterSequence } = (0, import_react4.useContext)(SequenceManager);
    const { hidden } = (0, import_react4.useContext)(SequenceVisibilityToggleContext);
    const premounting = (0, import_react4.useMemo)(() => {
      return parentSequence?.premounting || Boolean(other._remotionInternalIsPremounting);
    }, [other._remotionInternalIsPremounting, parentSequence?.premounting]);
    const postmounting = (0, import_react4.useMemo)(() => {
      return parentSequence?.postmounting || Boolean(other._remotionInternalIsPostmounting);
    }, [other._remotionInternalIsPostmounting, parentSequence?.postmounting]);
    const contextValue = (0, import_react4.useMemo)(() => {
      return {
        cumulatedFrom,
        relativeFrom: from,
        durationInFrames: actualDurationInFrames,
        parentFrom: parentSequence?.relativeFrom ?? 0,
        id,
        height: height ?? parentSequence?.height ?? null,
        width: width ?? parentSequence?.width ?? null,
        premounting,
        postmounting,
        premountDisplay: premountDisplay ?? null,
        postmountDisplay: postmountDisplay ?? null
      };
    }, [
      cumulatedFrom,
      from,
      actualDurationInFrames,
      parentSequence,
      id,
      height,
      width,
      premounting,
      postmounting,
      premountDisplay,
      postmountDisplay
    ]);
    const timelineClipName = (0, import_react4.useMemo)(() => {
      return name ?? "";
    }, [name]);
    const env = useRemotionEnvironment();
    (0, import_react4.useEffect)(() => {
      if (!env.isStudio) {
        return;
      }
      registerSequence({
        from,
        duration: actualDurationInFrames,
        id,
        displayName: timelineClipName,
        parent: parentSequence?.id ?? null,
        type: "sequence",
        rootId,
        showInTimeline,
        nonce,
        loopDisplay,
        stack: stack ?? null,
        premountDisplay: premountDisplay ?? null,
        postmountDisplay: postmountDisplay ?? null
      });
      return () => {
        unregisterSequence(id);
      };
    }, [
      durationInFrames,
      id,
      name,
      registerSequence,
      timelineClipName,
      unregisterSequence,
      parentSequence?.id,
      actualDurationInFrames,
      rootId,
      from,
      showInTimeline,
      nonce,
      loopDisplay,
      stack,
      premountDisplay,
      postmountDisplay,
      env.isStudio
    ]);
    const endThreshold = Math.ceil(cumulatedFrom + from + durationInFrames - 1);
    const content = absoluteFrame < cumulatedFrom + from ? null : absoluteFrame > endThreshold ? null : children;
    const styleIfThere = other.layout === "none" ? void 0 : other.style;
    const defaultStyle = (0, import_react4.useMemo)(() => {
      return {
        flexDirection: void 0,
        ...width ? { width } : {},
        ...height ? { height } : {},
        ...styleIfThere ?? {}
      };
    }, [height, styleIfThere, width]);
    if (ref !== null && layout === "none") {
      throw new TypeError('It is not supported to pass both a `ref` and `layout="none"` to <Sequence />.');
    }
    const isSequenceHidden = hidden[id] ?? false;
    if (isSequenceHidden) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(SequenceContext.Provider, {
      value: contextValue,
      children: content === null ? null : other.layout === "none" ? content : /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(AbsoluteFill, {
        ref,
        style: defaultStyle,
        className: other.className,
        children: content
      })
    });
  };
  var RegularSequence = (0, import_react4.forwardRef)(RegularSequenceRefForwardingFunction);
  var PremountedPostmountedSequenceRefForwardingFunction = (props, ref) => {
    const frame = useCurrentFrame();
    if (props.layout === "none") {
      throw new Error('`<Sequence>` with `premountFor` and `postmountFor` props does not support layout="none"');
    }
    const {
      style: passedStyle,
      from = 0,
      durationInFrames = Infinity,
      premountFor = 0,
      postmountFor = 0,
      styleWhilePremounted,
      styleWhilePostmounted,
      ...otherProps
    } = props;
    const endThreshold = Math.ceil(from + durationInFrames - 1);
    const premountingActive = frame < from && frame >= from - premountFor;
    const postmountingActive = frame > endThreshold && frame <= endThreshold + postmountFor;
    const freezeFrame = premountingActive ? from : postmountingActive ? from + durationInFrames - 1 : 0;
    const isFreezingActive = premountingActive || postmountingActive;
    const style2 = (0, import_react4.useMemo)(() => {
      return {
        ...passedStyle,
        opacity: premountingActive || postmountingActive ? 0 : 1,
        pointerEvents: premountingActive || postmountingActive ? "none" : passedStyle?.pointerEvents ?? void 0,
        ...premountingActive ? styleWhilePremounted : {},
        ...postmountingActive ? styleWhilePostmounted : {}
      };
    }, [
      passedStyle,
      premountingActive,
      postmountingActive,
      styleWhilePremounted,
      styleWhilePostmounted
    ]);
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Freeze, {
      frame: freezeFrame,
      active: isFreezingActive,
      children: /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(Sequence, {
        ref,
        from,
        durationInFrames,
        style: style2,
        _remotionInternalPremountDisplay: premountFor,
        _remotionInternalPostmountDisplay: postmountFor,
        _remotionInternalIsPremounting: premountingActive,
        _remotionInternalIsPostmounting: postmountingActive,
        ...otherProps
      })
    });
  };
  var PremountedPostmountedSequence = (0, import_react4.forwardRef)(PremountedPostmountedSequenceRefForwardingFunction);
  var SequenceRefForwardingFunction = (props, ref) => {
    const env = useRemotionEnvironment();
    if (props.layout !== "none" && !env.isRendering) {
      if (props.premountFor || props.postmountFor) {
        return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(PremountedPostmountedSequence, {
          ...props,
          ref
        });
      }
    }
    return /* @__PURE__ */ (0, import_jsx_runtime9.jsx)(RegularSequence, {
      ...props,
      ref
    });
  };
  var Sequence = (0, import_react4.forwardRef)(SequenceRefForwardingFunction);
  var calcArgs = (fit, frameSize, canvasSize) => {
    switch (fit) {
      case "fill": {
        return [
          0,
          0,
          frameSize.width,
          frameSize.height,
          0,
          0,
          canvasSize.width,
          canvasSize.height
        ];
      }
      case "contain": {
        const ratio = Math.min(canvasSize.width / frameSize.width, canvasSize.height / frameSize.height);
        const centerX = (canvasSize.width - frameSize.width * ratio) / 2;
        const centerY = (canvasSize.height - frameSize.height * ratio) / 2;
        return [
          0,
          0,
          frameSize.width,
          frameSize.height,
          centerX,
          centerY,
          frameSize.width * ratio,
          frameSize.height * ratio
        ];
      }
      case "cover": {
        const ratio = Math.max(canvasSize.width / frameSize.width, canvasSize.height / frameSize.height);
        const centerX = (canvasSize.width - frameSize.width * ratio) / 2;
        const centerY = (canvasSize.height - frameSize.height * ratio) / 2;
        return [
          0,
          0,
          frameSize.width,
          frameSize.height,
          centerX,
          centerY,
          frameSize.width * ratio,
          frameSize.height * ratio
        ];
      }
      default:
        throw new Error("Unknown fit: " + fit);
    }
  };
  var CanvasRefForwardingFunction = ({ width, height, fit, className: className2, style: style2 }, ref) => {
    const canvasRef = (0, import_react25.useRef)(null);
    const draw = (0, import_react25.useCallback)((imageData) => {
      const canvas = canvasRef.current;
      const canvasWidth = width ?? imageData.displayWidth;
      const canvasHeight = height ?? imageData.displayHeight;
      if (!canvas) {
        throw new Error("Canvas ref is not set");
      }
      const ctx = canvasRef.current?.getContext("2d");
      if (!ctx) {
        throw new Error("Could not get 2d context");
      }
      canvas.width = canvasWidth;
      canvas.height = canvasHeight;
      ctx.drawImage(imageData, ...calcArgs(fit, {
        height: imageData.displayHeight,
        width: imageData.displayWidth
      }, {
        width: canvasWidth,
        height: canvasHeight
      }));
    }, [fit, height, width]);
    (0, import_react25.useImperativeHandle)(ref, () => {
      return {
        draw,
        getCanvas: () => {
          if (!canvasRef.current) {
            throw new Error("Canvas ref is not set");
          }
          return canvasRef.current;
        },
        clear: () => {
          const ctx = canvasRef.current?.getContext("2d");
          if (!ctx) {
            throw new Error("Could not get 2d context");
          }
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        }
      };
    }, [draw]);
    return /* @__PURE__ */ (0, import_jsx_runtime10.jsx)("canvas", {
      ref: canvasRef,
      className: className2,
      style: style2
    });
  };
  var Canvas = import_react25.default.forwardRef(CanvasRefForwardingFunction);
  var CACHE_SIZE = 5;
  var getActualTime = ({
    loopBehavior,
    durationFound,
    timeInSec
  }) => {
    return loopBehavior === "loop" ? durationFound ? timeInSec % durationFound : timeInSec : Math.min(timeInSec, durationFound || Infinity);
  };
  var decodeImage = async ({
    resolvedSrc,
    signal,
    currentTime,
    initialLoopBehavior
  }) => {
    if (typeof ImageDecoder === "undefined") {
      throw new Error("Your browser does not support the WebCodecs ImageDecoder API.");
    }
    const res = await fetch(resolvedSrc, { signal });
    const { body } = res;
    if (!body) {
      throw new Error("Got no body");
    }
    const decoder = new ImageDecoder({
      data: body,
      type: res.headers.get("Content-Type") || "image/gif"
    });
    await decoder.completed;
    const { selectedTrack } = decoder.tracks;
    if (!selectedTrack) {
      throw new Error("No selected track");
    }
    const cache = [];
    let durationFound = null;
    const getFrameByIndex = async (frameIndex) => {
      const foundInCache = cache.find((c2) => c2.frameIndex === frameIndex);
      if (foundInCache && foundInCache.frame) {
        return foundInCache;
      }
      const frame = await decoder.decode({
        frameIndex,
        completeFramesOnly: true
      });
      if (foundInCache) {
        foundInCache.frame = frame.image;
      } else {
        cache.push({
          frame: frame.image,
          frameIndex,
          timeInSeconds: frame.image.timestamp / 1e6
        });
      }
      return {
        frame: frame.image,
        frameIndex,
        timeInSeconds: frame.image.timestamp / 1e6
      };
    };
    const clearCache = (closeToTimeInSec) => {
      const itemsInCache = cache.filter((c2) => c2.frame);
      const sortByClosestToCurrentTime = itemsInCache.sort((a2, b2) => {
        const aDiff = Math.abs(a2.timeInSeconds - closeToTimeInSec);
        const bDiff = Math.abs(b2.timeInSeconds - closeToTimeInSec);
        return aDiff - bDiff;
      });
      for (let i = 0; i < sortByClosestToCurrentTime.length; i++) {
        if (i < CACHE_SIZE) {
          continue;
        }
        const item = sortByClosestToCurrentTime[i];
        item.frame = null;
      }
    };
    const ensureFrameBeforeAndAfter = async ({
      timeInSec,
      loopBehavior
    }) => {
      const actualTimeInSec = getActualTime({
        durationFound,
        loopBehavior,
        timeInSec
      });
      const framesBefore = cache.filter((c2) => c2.timeInSeconds <= actualTimeInSec);
      const biggestIndex = framesBefore.map((c2) => c2.frameIndex).reduce((a2, b2) => Math.max(a2, b2), 0);
      let i = biggestIndex;
      while (true) {
        const f = await getFrameByIndex(i);
        i++;
        if (!f.frame) {
          throw new Error("No frame found");
        }
        if (!f.frame.duration) {
          break;
        }
        if (i === selectedTrack.frameCount && durationFound === null) {
          const duration = (f.frame.timestamp + f.frame.duration) / 1e6;
          durationFound = duration;
        }
        if (f.timeInSeconds > actualTimeInSec || i === selectedTrack.frameCount) {
          break;
        }
      }
      if (selectedTrack.frameCount - biggestIndex < 3 && loopBehavior === "loop") {
        await getFrameByIndex(0);
      }
      clearCache(actualTimeInSec);
    };
    await ensureFrameBeforeAndAfter({
      timeInSec: currentTime,
      loopBehavior: initialLoopBehavior
    });
    await ensureFrameBeforeAndAfter({
      timeInSec: currentTime,
      loopBehavior: initialLoopBehavior
    });
    const getFrame = async (timeInSec, loopBehavior) => {
      if (durationFound !== null && timeInSec > durationFound && loopBehavior === "clear-after-finish") {
        return null;
      }
      const actualTimeInSec = getActualTime({
        loopBehavior,
        durationFound,
        timeInSec
      });
      await ensureFrameBeforeAndAfter({ timeInSec: actualTimeInSec, loopBehavior });
      const itemsInCache = cache.filter((c2) => c2.frame);
      const closest = itemsInCache.reduce((a2, b2) => {
        const aDiff = Math.abs(a2.timeInSeconds - actualTimeInSec);
        const bDiff = Math.abs(b2.timeInSeconds - actualTimeInSec);
        return aDiff < bDiff ? a2 : b2;
      });
      if (!closest.frame) {
        throw new Error("No frame found");
      }
      return closest;
    };
    return {
      getFrame,
      frameCount: selectedTrack.frameCount
    };
  };
  var resolveAnimatedImageSource = (src) => {
    if (typeof window === "undefined") {
      return src;
    }
    return new URL(src, window.origin).href;
  };
  var AnimatedImage = (0, import_react24.forwardRef)(({
    src,
    width,
    height,
    onError,
    loopBehavior = "loop",
    playbackRate = 1,
    fit = "fill",
    ...props
  }, canvasRef) => {
    const mountState = (0, import_react24.useRef)({ isMounted: true });
    (0, import_react24.useEffect)(() => {
      const { current } = mountState;
      current.isMounted = true;
      return () => {
        current.isMounted = false;
      };
    }, []);
    const resolvedSrc = resolveAnimatedImageSource(src);
    const [imageDecoder, setImageDecoder] = (0, import_react24.useState)(null);
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    const [decodeHandle] = (0, import_react24.useState)(() => delayRender2(`Rendering <AnimatedImage/> with src="${resolvedSrc}"`));
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const currentTime = frame / playbackRate / fps;
    const currentTimeRef = (0, import_react24.useRef)(currentTime);
    currentTimeRef.current = currentTime;
    const ref = (0, import_react24.useRef)(null);
    (0, import_react24.useImperativeHandle)(canvasRef, () => {
      const c2 = ref.current?.getCanvas();
      if (!c2) {
        throw new Error("Canvas ref is not set");
      }
      return c2;
    }, []);
    const [initialLoopBehavior] = (0, import_react24.useState)(() => loopBehavior);
    (0, import_react24.useEffect)(() => {
      const controller = new AbortController();
      decodeImage({
        resolvedSrc,
        signal: controller.signal,
        currentTime: currentTimeRef.current,
        initialLoopBehavior
      }).then((d) => {
        setImageDecoder(d);
        continueRender2(decodeHandle);
      }).catch((err) => {
        if (err.name === "AbortError") {
          continueRender2(decodeHandle);
          return;
        }
        if (onError) {
          onError?.(err);
          continueRender2(decodeHandle);
        } else {
          cancelRender(err);
        }
      });
      return () => {
        controller.abort();
      };
    }, [
      resolvedSrc,
      decodeHandle,
      onError,
      initialLoopBehavior,
      continueRender2
    ]);
    (0, import_react24.useLayoutEffect)(() => {
      if (!imageDecoder) {
        return;
      }
      const delay2 = delayRender2(`Rendering frame at ${currentTime} of <AnimatedImage src="${src}"/>`);
      imageDecoder.getFrame(currentTime, loopBehavior).then((videoFrame) => {
        if (mountState.current.isMounted) {
          if (videoFrame === null) {
            ref.current?.clear();
          } else {
            ref.current?.draw(videoFrame.frame);
          }
        }
        continueRender2(delay2);
      }).catch((err) => {
        if (onError) {
          onError(err);
          continueRender2(delay2);
        } else {
          cancelRender(err);
        }
      });
    }, [
      currentTime,
      imageDecoder,
      loopBehavior,
      onError,
      src,
      continueRender2,
      delayRender2
    ]);
    return /* @__PURE__ */ (0, import_jsx_runtime11.jsx)(Canvas, {
      ref,
      width,
      height,
      fit,
      ...props
    });
  });
  var validateArtifactFilename = (filename) => {
    if (typeof filename !== "string") {
      throw new TypeError(`The "filename" must be a string, but you passed a value of type ${typeof filename}`);
    }
    if (filename.trim() === "") {
      throw new Error("The `filename` must not be empty");
    }
    if (!filename.match(/^([0-9a-zA-Z-!_.*'()/:&$@=;+,?]+)/g)) {
      throw new Error('The `filename` must match "/^([0-9a-zA-Z-!_.*\'()/:&$@=;+,?]+)/g". Use forward slashes only, even on Windows.');
    }
  };
  var validateContent = (content) => {
    if (typeof content !== "string" && !(content instanceof Uint8Array)) {
      throw new TypeError(`The "content" must be a string or Uint8Array, but you passed a value of type ${typeof content}`);
    }
    if (typeof content === "string" && content.trim() === "") {
      throw new Error("The `content` must not be empty");
    }
  };
  var validateRenderAsset = (artifact) => {
    if (artifact.type !== "artifact") {
      return;
    }
    validateArtifactFilename(artifact.filename);
    if (artifact.contentType === "thumbnail") {
      return;
    }
    validateContent(artifact.content);
  };
  var RenderAssetManager = (0, import_react27.createContext)({
    registerRenderAsset: () => {
      return;
    },
    unregisterRenderAsset: () => {
      return;
    },
    renderAssets: []
  });
  var RenderAssetManagerProvider = ({ children, collectAssets }) => {
    const [renderAssets, setRenderAssets] = (0, import_react27.useState)([]);
    const renderAssetsRef = (0, import_react27.useRef)([]);
    const registerRenderAsset = (0, import_react27.useCallback)((renderAsset) => {
      validateRenderAsset(renderAsset);
      renderAssetsRef.current = [...renderAssetsRef.current, renderAsset];
      setRenderAssets(renderAssetsRef.current);
    }, []);
    if (collectAssets) {
      (0, import_react27.useImperativeHandle)(collectAssets, () => {
        return {
          collectAssets: () => {
            const assets = renderAssetsRef.current;
            renderAssetsRef.current = [];
            setRenderAssets([]);
            return assets;
          }
        };
      }, []);
    }
    const unregisterRenderAsset = (0, import_react27.useCallback)((id) => {
      renderAssetsRef.current = renderAssetsRef.current.filter((a2) => a2.id !== id);
      setRenderAssets(renderAssetsRef.current);
    }, []);
    (0, import_react27.useLayoutEffect)(() => {
      if (typeof window !== "undefined") {
        window.remotion_collectAssets = () => {
          const assets = renderAssetsRef.current;
          renderAssetsRef.current = [];
          setRenderAssets([]);
          return assets;
        };
      }
    }, []);
    const contextValue = (0, import_react27.useMemo)(() => {
      return {
        registerRenderAsset,
        unregisterRenderAsset,
        renderAssets
      };
    }, [renderAssets, registerRenderAsset, unregisterRenderAsset]);
    return /* @__PURE__ */ (0, import_jsx_runtime12.jsx)(RenderAssetManager.Provider, {
      value: contextValue,
      children
    });
  };
  var ArtifactThumbnail = Symbol("Thumbnail");
  var Artifact = ({ filename, content, downloadBehavior }) => {
    const { registerRenderAsset, unregisterRenderAsset } = (0, import_react26.useContext)(RenderAssetManager);
    const env = useRemotionEnvironment();
    const frame = useCurrentFrame();
    const [id] = (0, import_react26.useState)(() => {
      return String(Math.random());
    });
    (0, import_react26.useLayoutEffect)(() => {
      if (!env.isRendering) {
        return;
      }
      if (content instanceof Uint8Array) {
        registerRenderAsset({
          type: "artifact",
          id,
          content: btoa(new TextDecoder("utf8").decode(content)),
          filename,
          frame,
          contentType: "binary",
          downloadBehavior: downloadBehavior ?? null
        });
      } else if (content === ArtifactThumbnail) {
        registerRenderAsset({
          type: "artifact",
          id,
          filename,
          frame,
          contentType: "thumbnail",
          downloadBehavior: downloadBehavior ?? null
        });
      } else {
        registerRenderAsset({
          type: "artifact",
          id,
          content,
          filename,
          frame,
          contentType: "text",
          downloadBehavior: downloadBehavior ?? null
        });
      }
      return () => {
        return unregisterRenderAsset(id);
      };
    }, [
      content,
      env.isRendering,
      filename,
      frame,
      id,
      registerRenderAsset,
      unregisterRenderAsset,
      downloadBehavior
    ]);
    return null;
  };
  Artifact.Thumbnail = ArtifactThumbnail;
  var getAbsoluteSrc = (relativeSrc) => {
    if (typeof window === "undefined") {
      return relativeSrc;
    }
    if (relativeSrc.startsWith("http://") || relativeSrc.startsWith("https://") || relativeSrc.startsWith("file://") || relativeSrc.startsWith("blob:") || relativeSrc.startsWith("data:")) {
      return relativeSrc;
    }
    return new URL(relativeSrc, window.origin).href;
  };
  var calculateMediaDuration = ({
    trimAfter,
    mediaDurationInFrames,
    playbackRate,
    trimBefore
  }) => {
    let duration = mediaDurationInFrames;
    if (typeof trimAfter !== "undefined") {
      duration = trimAfter;
    }
    if (typeof trimBefore !== "undefined") {
      duration -= trimBefore;
    }
    const actualDuration = duration / playbackRate;
    return Math.floor(actualDuration);
  };
  var LoopContext = (0, import_react29.createContext)(null);
  var useLoop = () => {
    return import_react29.default.useContext(LoopContext);
  };
  var Loop = ({ durationInFrames, times = Infinity, children, name, ...props }) => {
    const currentFrame = useCurrentFrame();
    const { durationInFrames: compDuration } = useVideoConfig();
    validateDurationInFrames(durationInFrames, {
      component: "of the <Loop /> component",
      allowFloats: true
    });
    if (typeof times !== "number") {
      throw new TypeError(`You passed to "times" an argument of type ${typeof times}, but it must be a number.`);
    }
    if (times !== Infinity && times % 1 !== 0) {
      throw new TypeError(`The "times" prop of a loop must be an integer, but got ${times}.`);
    }
    if (times < 0) {
      throw new TypeError(`The "times" prop of a loop must be at least 0, but got ${times}`);
    }
    const maxTimes = Math.ceil(compDuration / durationInFrames);
    const actualTimes = Math.min(maxTimes, times);
    const style2 = props.layout === "none" ? void 0 : props.style;
    const maxFrame = durationInFrames * (actualTimes - 1);
    const iteration = Math.floor(currentFrame / durationInFrames);
    const start = iteration * durationInFrames;
    const from = Math.min(start, maxFrame);
    const loopDisplay = (0, import_react29.useMemo)(() => {
      return {
        numberOfTimes: actualTimes,
        startOffset: -from,
        durationInFrames
      };
    }, [actualTimes, durationInFrames, from]);
    const loopContext = (0, import_react29.useMemo)(() => {
      return {
        iteration: Math.floor(currentFrame / durationInFrames),
        durationInFrames
      };
    }, [currentFrame, durationInFrames]);
    return /* @__PURE__ */ (0, import_jsx_runtime13.jsx)(LoopContext.Provider, {
      value: loopContext,
      children: /* @__PURE__ */ (0, import_jsx_runtime13.jsx)(Sequence, {
        durationInFrames,
        from,
        name: name ?? "<Loop>",
        _remotionInternalLoopDisplay: loopDisplay,
        layout: props.layout,
        style: style2,
        children
      })
    });
  };
  Loop.useLoop = useLoop;
  var playbackLogging = ({
    logLevel,
    tag,
    message,
    mountTime
  }) => {
    const tags = [mountTime ? Date.now() - mountTime + "ms " : null, tag].filter(Boolean).join(" ");
    Log.trace({ logLevel, tag: null }, `[${tags}]`, message);
  };
  var PreloadContext = (0, import_react31.createContext)({});
  var preloads = {};
  var updaters = [];
  var PrefetchProvider = ({ children }) => {
    const [_preloads, _setPreloads] = (0, import_react31.useState)(() => preloads);
    (0, import_react31.useEffect)(() => {
      const updaterFunction = () => {
        _setPreloads(preloads);
      };
      updaters.push(updaterFunction);
      return () => {
        updaters = updaters.filter((u) => u !== updaterFunction);
      };
    }, []);
    return /* @__PURE__ */ (0, import_jsx_runtime14.jsx)(PreloadContext.Provider, {
      value: _preloads,
      children
    });
  };
  var removeAndGetHashFragment = (src) => {
    const hashIndex = src.indexOf("#");
    if (hashIndex === -1) {
      return null;
    }
    return hashIndex;
  };
  var getSrcWithoutHash = (src) => {
    const hashIndex = removeAndGetHashFragment(src);
    if (hashIndex === null) {
      return src;
    }
    return src.slice(0, hashIndex);
  };
  var usePreload = (src) => {
    const preloads2 = (0, import_react30.useContext)(PreloadContext);
    const hashFragmentIndex = removeAndGetHashFragment(src);
    const withoutHashFragment = getSrcWithoutHash(src);
    if (!preloads2[withoutHashFragment]) {
      return src;
    }
    if (hashFragmentIndex !== null) {
      return preloads2[withoutHashFragment] + src.slice(hashFragmentIndex);
    }
    return preloads2[withoutHashFragment];
  };
  var validateMediaProps = (props, component) => {
    if (typeof props.volume !== "number" && typeof props.volume !== "function" && typeof props.volume !== "undefined") {
      throw new TypeError(`You have passed a volume of type ${typeof props.volume} to your <${component} /> component. Volume must be a number or a function with the signature '(frame: number) => number' undefined.`);
    }
    if (typeof props.volume === "number" && props.volume < 0) {
      throw new TypeError(`You have passed a volume below 0 to your <${component} /> component. Volume must be between 0 and 1`);
    }
    if (typeof props.playbackRate !== "number" && typeof props.playbackRate !== "undefined") {
      throw new TypeError(`You have passed a playbackRate of type ${typeof props.playbackRate} to your <${component} /> component. Playback rate must a real number or undefined.`);
    }
    if (typeof props.playbackRate === "number" && (isNaN(props.playbackRate) || !Number.isFinite(props.playbackRate) || props.playbackRate <= 0)) {
      throw new TypeError(`You have passed a playbackRate of ${props.playbackRate} to your <${component} /> component. Playback rate must be a real number above 0.`);
    }
  };
  var validateStartFromProps = (startFrom, endAt) => {
    if (typeof startFrom !== "undefined") {
      if (typeof startFrom !== "number") {
        throw new TypeError(`type of startFrom prop must be a number, instead got type ${typeof startFrom}.`);
      }
      if (isNaN(startFrom) || startFrom === Infinity) {
        throw new TypeError("startFrom prop can not be NaN or Infinity.");
      }
      if (startFrom < 0) {
        throw new TypeError(`startFrom must be greater than equal to 0 instead got ${startFrom}.`);
      }
    }
    if (typeof endAt !== "undefined") {
      if (typeof endAt !== "number") {
        throw new TypeError(`type of endAt prop must be a number, instead got type ${typeof endAt}.`);
      }
      if (isNaN(endAt)) {
        throw new TypeError("endAt prop can not be NaN.");
      }
      if (endAt <= 0) {
        throw new TypeError(`endAt must be a positive number, instead got ${endAt}.`);
      }
    }
    if (endAt < startFrom) {
      throw new TypeError("endAt prop must be greater than startFrom prop.");
    }
  };
  var validateTrimProps = (trimBefore, trimAfter) => {
    if (typeof trimBefore !== "undefined") {
      if (typeof trimBefore !== "number") {
        throw new TypeError(`type of trimBefore prop must be a number, instead got type ${typeof trimBefore}.`);
      }
      if (isNaN(trimBefore) || trimBefore === Infinity) {
        throw new TypeError("trimBefore prop can not be NaN or Infinity.");
      }
      if (trimBefore < 0) {
        throw new TypeError(`trimBefore must be greater than equal to 0 instead got ${trimBefore}.`);
      }
    }
    if (typeof trimAfter !== "undefined") {
      if (typeof trimAfter !== "number") {
        throw new TypeError(`type of trimAfter prop must be a number, instead got type ${typeof trimAfter}.`);
      }
      if (isNaN(trimAfter)) {
        throw new TypeError("trimAfter prop can not be NaN.");
      }
      if (trimAfter <= 0) {
        throw new TypeError(`trimAfter must be a positive number, instead got ${trimAfter}.`);
      }
    }
    if (trimAfter <= trimBefore) {
      throw new TypeError("trimAfter prop must be greater than trimBefore prop.");
    }
  };
  var validateMediaTrimProps = ({
    startFrom,
    endAt,
    trimBefore,
    trimAfter
  }) => {
    if (typeof startFrom !== "undefined" && typeof trimBefore !== "undefined") {
      throw new TypeError("Cannot use both startFrom and trimBefore props. Use trimBefore instead as startFrom is deprecated.");
    }
    if (typeof endAt !== "undefined" && typeof trimAfter !== "undefined") {
      throw new TypeError("Cannot use both endAt and trimAfter props. Use trimAfter instead as endAt is deprecated.");
    }
    const hasNewProps = typeof trimBefore !== "undefined" || typeof trimAfter !== "undefined";
    const hasOldProps = typeof startFrom !== "undefined" || typeof endAt !== "undefined";
    if (hasNewProps) {
      validateTrimProps(trimBefore, trimAfter);
    } else if (hasOldProps) {
      validateStartFromProps(startFrom, endAt);
    }
  };
  var resolveTrimProps = ({
    startFrom,
    endAt,
    trimBefore,
    trimAfter
  }) => {
    const trimBeforeValue = trimBefore ?? startFrom ?? void 0;
    const trimAfterValue = trimAfter ?? endAt ?? void 0;
    return { trimBeforeValue, trimAfterValue };
  };
  var durationReducer = (state, action) => {
    switch (action.type) {
      case "got-duration": {
        const absoluteSrc = getAbsoluteSrc(action.src);
        if (state[absoluteSrc] === action.durationInSeconds) {
          return state;
        }
        return {
          ...state,
          [absoluteSrc]: action.durationInSeconds
        };
      }
      default:
        return state;
    }
  };
  var DurationsContext = (0, import_react32.createContext)({
    durations: {},
    setDurations: () => {
      throw new Error("context missing");
    }
  });
  var DurationsContextProvider = ({ children }) => {
    const [durations, setDurations] = (0, import_react32.useReducer)(durationReducer, {});
    const value = (0, import_react32.useMemo)(() => {
      return {
        durations,
        setDurations
      };
    }, [durations]);
    return /* @__PURE__ */ (0, import_jsx_runtime15.jsx)(DurationsContext.Provider, {
      value,
      children
    });
  };
  var getCrossOriginValue = ({
    crossOrigin,
    requestsVideoFrame,
    isClientSideRendering
  }) => {
    if (crossOrigin !== void 0 && crossOrigin !== null) {
      return crossOrigin;
    }
    if (isClientSideRendering) {
      return "anonymous";
    }
    if (requestsVideoFrame) {
      return "anonymous";
    }
    return;
  };
  var playAndHandleNotAllowedError = ({
    mediaRef,
    mediaType,
    onAutoPlayError,
    logLevel,
    mountTime,
    reason,
    isPlayer
  }) => {
    const { current } = mediaRef;
    if (!current) {
      return;
    }
    playbackLogging({
      logLevel,
      tag: "play",
      message: `Attempting to play ${current.src}. Reason: ${reason}`,
      mountTime
    });
    const prom = current.play();
    if (!prom.catch) {
      return;
    }
    prom.catch((err) => {
      if (!current) {
        return;
      }
      if (err.message.includes("request was interrupted by a call to pause")) {
        return;
      }
      if (err.message.includes("The operation was aborted.")) {
        return;
      }
      if (err.message.includes("The fetching process for the media resource was aborted by the user agent")) {
        return;
      }
      if (err.message.includes("request was interrupted by a new load request")) {
        return;
      }
      if (err.message.includes("because the media was removed from the document")) {
        return;
      }
      if (err.message.includes("user didn't interact with the document") && current.muted) {
        return;
      }
      console.log(`Could not play ${mediaType} due to following error: `, err);
      if (!current.muted) {
        if (onAutoPlayError) {
          onAutoPlayError();
          return;
        }
        if (mediaType === "video" && isPlayer) {
          Log.info({ logLevel, tag: "<" + mediaType + ">" }, `The video will be muted and we'll retry playing it.`);
          Log.info({ logLevel, tag: "<" + mediaType + ">" }, "Use onAutoPlayError() to handle this error yourself.");
          current.muted = true;
          current.play();
        }
      }
    });
  };
  var makeSharedElementSourceNode = ({
    audioContext,
    ref
  }) => {
    let connected = null;
    let disposed = false;
    return {
      attemptToConnect: () => {
        if (disposed) {
          throw new Error("SharedElementSourceNode has been disposed");
        }
        if (!connected && ref.current) {
          const mediaElementSourceNode = audioContext.createMediaElementSource(ref.current);
          connected = mediaElementSourceNode;
        }
      },
      get: () => {
        if (!connected) {
          throw new Error("Audio element not connected");
        }
        return connected;
      },
      cleanup: () => {
        if (connected) {
          connected.disconnect();
          connected = null;
        }
        disposed = true;
      }
    };
  };
  var warned = false;
  var warnOnce = (logLevel) => {
    if (warned) {
      return;
    }
    warned = true;
    if (typeof window !== "undefined") {
      Log.warn({ logLevel, tag: null }, "AudioContext is not supported in this browser");
    }
  };
  var useSingletonAudioContext = ({
    logLevel,
    latencyHint,
    audioEnabled
  }) => {
    const env = useRemotionEnvironment();
    const audioContext = (0, import_react36.useMemo)(() => {
      if (env.isRendering) {
        return null;
      }
      if (!audioEnabled) {
        return null;
      }
      if (typeof AudioContext === "undefined") {
        warnOnce(logLevel);
        return null;
      }
      return new AudioContext({
        latencyHint,
        sampleRate: 48e3
      });
    }, [logLevel, latencyHint, env.isRendering, audioEnabled]);
    return audioContext;
  };
  var EMPTY_AUDIO = "data:audio/mp3;base64,/+MYxAAJcAV8AAgAABn//////+/gQ5BAMA+D4Pg+BAQBAEAwD4Pg+D4EBAEAQDAPg++hYBH///hUFQVBUFREDQNHmf///////+MYxBUGkAGIMAAAAP/29Xt6lUxBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV/+MYxDUAAANIAAAAAFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV";
  var compareProps = (obj1, obj2) => {
    const keysA = Object.keys(obj1).sort();
    const keysB = Object.keys(obj2).sort();
    if (keysA.length !== keysB.length) {
      return false;
    }
    for (let i = 0; i < keysA.length; i++) {
      if (keysA[i] !== keysB[i]) {
        return false;
      }
      if (obj1[keysA[i]] !== obj2[keysB[i]]) {
        return false;
      }
    }
    return true;
  };
  var didPropChange = (key, newProp, prevProp) => {
    if (key === "src" && !prevProp.startsWith("data:") && !newProp.startsWith("data:")) {
      return new URL(prevProp, window.origin).toString() !== new URL(newProp, window.origin).toString();
    }
    if (prevProp === newProp) {
      return false;
    }
    return true;
  };
  var SharedAudioContext = (0, import_react35.createContext)(null);
  var SharedAudioContextProvider = ({ children, numberOfAudioTags, audioLatencyHint, audioEnabled }) => {
    const audios = (0, import_react35.useRef)([]);
    const [initialNumberOfAudioTags] = (0, import_react35.useState)(numberOfAudioTags);
    if (numberOfAudioTags !== initialNumberOfAudioTags) {
      throw new Error("The number of shared audio tags has changed dynamically. Once you have set this property, you cannot change it afterwards.");
    }
    const logLevel = useLogLevel();
    const audioContext = useSingletonAudioContext({
      logLevel,
      latencyHint: audioLatencyHint,
      audioEnabled
    });
    const refs = (0, import_react35.useMemo)(() => {
      return new Array(numberOfAudioTags).fill(true).map(() => {
        const ref = (0, import_react35.createRef)();
        return {
          id: Math.random(),
          ref,
          mediaElementSourceNode: audioContext ? makeSharedElementSourceNode({
            audioContext,
            ref
          }) : null
        };
      });
    }, [audioContext, numberOfAudioTags]);
    const effectToUse = import_react35.default.useInsertionEffect ?? import_react35.default.useLayoutEffect;
    effectToUse(() => {
      return () => {
        requestAnimationFrame(() => {
          refs.forEach(({ mediaElementSourceNode }) => {
            mediaElementSourceNode?.cleanup();
          });
        });
      };
    }, [refs]);
    const takenAudios = (0, import_react35.useRef)(new Array(numberOfAudioTags).fill(false));
    const rerenderAudios = (0, import_react35.useCallback)(() => {
      refs.forEach(({ ref, id }) => {
        const data = audios.current?.find((a2) => a2.id === id);
        const { current } = ref;
        if (!current) {
          return;
        }
        if (data === void 0) {
          current.src = EMPTY_AUDIO;
          return;
        }
        if (!data) {
          throw new TypeError("Expected audio data to be there");
        }
        Object.keys(data.props).forEach((key) => {
          if (didPropChange(key, data.props[key], current[key])) {
            current[key] = data.props[key];
          }
        });
      });
    }, [refs]);
    const registerAudio = (0, import_react35.useCallback)((options) => {
      const { aud, audioId, premounting, postmounting } = options;
      const found = audios.current?.find((a2) => a2.audioId === audioId);
      if (found) {
        return found;
      }
      const firstFreeAudio = takenAudios.current.findIndex((a2) => a2 === false);
      if (firstFreeAudio === -1) {
        throw new Error(`Tried to simultaneously mount ${numberOfAudioTags + 1} <Html5Audio /> tags at the same time. With the current settings, the maximum amount of <Html5Audio /> tags is limited to ${numberOfAudioTags} at the same time. Remotion pre-mounts silent audio tags to help avoid browser autoplay restrictions. See https://remotion.dev/docs/player/autoplay#using-the-numberofsharedaudiotags-prop for more information on how to increase this limit.`);
      }
      const { id, ref, mediaElementSourceNode } = refs[firstFreeAudio];
      const cloned = [...takenAudios.current];
      cloned[firstFreeAudio] = id;
      takenAudios.current = cloned;
      const newElem = {
        props: aud,
        id,
        el: ref,
        audioId,
        mediaElementSourceNode,
        premounting,
        audioMounted: Boolean(ref.current),
        postmounting,
        cleanupOnMediaTagUnmount: () => {
        }
      };
      audios.current?.push(newElem);
      rerenderAudios();
      return newElem;
    }, [numberOfAudioTags, refs, rerenderAudios]);
    const unregisterAudio = (0, import_react35.useCallback)((id) => {
      const cloned = [...takenAudios.current];
      const index = refs.findIndex((r) => r.id === id);
      if (index === -1) {
        throw new TypeError("Error occured in ");
      }
      cloned[index] = false;
      takenAudios.current = cloned;
      audios.current = audios.current?.filter((a2) => a2.id !== id);
      rerenderAudios();
    }, [refs, rerenderAudios]);
    const updateAudio = (0, import_react35.useCallback)(({
      aud,
      audioId,
      id,
      premounting,
      postmounting
    }) => {
      let changed = false;
      audios.current = audios.current?.map((prevA) => {
        const audioMounted = Boolean(prevA.el.current);
        if (prevA.audioMounted !== audioMounted) {
          changed = true;
        }
        if (prevA.id === id) {
          const isTheSame = compareProps(aud, prevA.props) && prevA.premounting === premounting && prevA.postmounting === postmounting;
          if (isTheSame) {
            return prevA;
          }
          changed = true;
          return {
            ...prevA,
            props: aud,
            premounting,
            postmounting,
            audioId,
            audioMounted
          };
        }
        return prevA;
      });
      if (changed) {
        rerenderAudios();
      }
    }, [rerenderAudios]);
    const mountTime = useMountTime();
    const env = useRemotionEnvironment();
    const playAllAudios = (0, import_react35.useCallback)(() => {
      refs.forEach((ref) => {
        const audio = audios.current.find((a2) => a2.el === ref.ref);
        if (audio?.premounting) {
          return;
        }
        playAndHandleNotAllowedError({
          mediaRef: ref.ref,
          mediaType: "audio",
          onAutoPlayError: null,
          logLevel,
          mountTime,
          reason: "playing all audios",
          isPlayer: env.isPlayer
        });
      });
      audioContext?.resume();
    }, [audioContext, logLevel, mountTime, refs, env.isPlayer]);
    const value = (0, import_react35.useMemo)(() => {
      return {
        registerAudio,
        unregisterAudio,
        updateAudio,
        playAllAudios,
        numberOfAudioTags,
        audioContext
      };
    }, [
      numberOfAudioTags,
      playAllAudios,
      registerAudio,
      unregisterAudio,
      updateAudio,
      audioContext
    ]);
    return /* @__PURE__ */ (0, import_jsx_runtime16.jsxs)(SharedAudioContext.Provider, {
      value,
      children: [
        refs.map(({ id, ref }) => {
          return /* @__PURE__ */ (0, import_jsx_runtime16.jsx)("audio", {
            ref,
            preload: "metadata",
            src: EMPTY_AUDIO
          }, id);
        }),
        children
      ]
    });
  };
  var useSharedAudio = ({
    aud,
    audioId,
    premounting,
    postmounting
  }) => {
    const ctx = (0, import_react35.useContext)(SharedAudioContext);
    const [elem] = (0, import_react35.useState)(() => {
      if (ctx && ctx.numberOfAudioTags > 0) {
        return ctx.registerAudio({ aud, audioId, premounting, postmounting });
      }
      const el = import_react35.default.createRef();
      const mediaElementSourceNode = ctx?.audioContext ? makeSharedElementSourceNode({
        audioContext: ctx.audioContext,
        ref: el
      }) : null;
      return {
        el,
        id: Math.random(),
        props: aud,
        audioId,
        mediaElementSourceNode,
        premounting,
        audioMounted: Boolean(el.current),
        postmounting,
        cleanupOnMediaTagUnmount: () => {
          mediaElementSourceNode?.cleanup();
        }
      };
    });
    const effectToUse = import_react35.default.useInsertionEffect ?? import_react35.default.useLayoutEffect;
    if (typeof document !== "undefined") {
      effectToUse(() => {
        if (ctx && ctx.numberOfAudioTags > 0) {
          ctx.updateAudio({ id: elem.id, aud, audioId, premounting, postmounting });
        }
      }, [aud, ctx, elem.id, audioId, premounting, postmounting]);
      effectToUse(() => {
        return () => {
          if (ctx && ctx.numberOfAudioTags > 0) {
            ctx.unregisterAudio(elem.id);
          }
        };
      }, [ctx, elem.id]);
    }
    return elem;
  };
  var FLOATING_POINT_ERROR_THRESHOLD = 1e-5;
  var isApproximatelyTheSame = (num1, num2) => {
    return Math.abs(num1 - num2) < FLOATING_POINT_ERROR_THRESHOLD;
  };
  var toSeconds = (time, fps) => {
    return Math.round(time / fps * 100) / 100;
  };
  var isSafari = () => {
    if (typeof window === "undefined") {
      return false;
    }
    const isAppleWebKit = /AppleWebKit/.test(window.navigator.userAgent);
    if (!isAppleWebKit) {
      return false;
    }
    const isNotChrome = !window.navigator.userAgent.includes("Chrome/");
    return isNotChrome;
  };
  var isIosSafari = () => {
    if (typeof window === "undefined") {
      return false;
    }
    const isIpadIPodIPhone = /iP(ad|od|hone)/i.test(window.navigator.userAgent);
    return isIpadIPodIPhone && isSafari();
  };
  var isIOSSafariAndBlob = (actualSrc) => {
    return isIosSafari() && actualSrc.startsWith("blob:");
  };
  var getVideoFragmentStart = ({
    actualFrom,
    fps
  }) => {
    return toSeconds(Math.max(0, -actualFrom), fps);
  };
  var getVideoFragmentEnd = ({
    duration,
    fps
  }) => {
    return toSeconds(duration, fps);
  };
  var appendVideoFragment = ({
    actualSrc,
    actualFrom,
    duration,
    fps
  }) => {
    if (isIOSSafariAndBlob(actualSrc)) {
      return actualSrc;
    }
    if (actualSrc.startsWith("data:")) {
      return actualSrc;
    }
    const existingHash = Boolean(new URL(actualSrc, (typeof window === "undefined" ? null : window.location.href) ?? "http://localhost:3000").hash);
    if (existingHash) {
      return actualSrc;
    }
    if (!Number.isFinite(actualFrom)) {
      return actualSrc;
    }
    const withStartHash = `${actualSrc}#t=${getVideoFragmentStart({ actualFrom, fps })}`;
    if (!Number.isFinite(duration)) {
      return withStartHash;
    }
    return `${withStartHash},${getVideoFragmentEnd({ duration, fps })}`;
  };
  var isSubsetOfDuration = ({
    prevStartFrom,
    newStartFrom,
    prevDuration,
    newDuration,
    fps
  }) => {
    const previousFrom = getVideoFragmentStart({ actualFrom: prevStartFrom, fps });
    const newFrom = getVideoFragmentStart({ actualFrom: newStartFrom, fps });
    const previousEnd = getVideoFragmentEnd({ duration: prevDuration, fps });
    const newEnd = getVideoFragmentEnd({ duration: newDuration, fps });
    if (newFrom < previousFrom) {
      return false;
    }
    if (newEnd > previousEnd) {
      return false;
    }
    return true;
  };
  var useAppendVideoFragment = ({
    actualSrc: initialActualSrc,
    actualFrom: initialActualFrom,
    duration: initialDuration,
    fps
  }) => {
    const actualFromRef = (0, import_react37.useRef)(initialActualFrom);
    const actualDuration = (0, import_react37.useRef)(initialDuration);
    const actualSrc = (0, import_react37.useRef)(initialActualSrc);
    if (!isSubsetOfDuration({
      prevStartFrom: actualFromRef.current,
      newStartFrom: initialActualFrom,
      prevDuration: actualDuration.current,
      newDuration: initialDuration,
      fps
    }) || initialActualSrc !== actualSrc.current) {
      actualFromRef.current = initialActualFrom;
      actualDuration.current = initialDuration;
      actualSrc.current = initialActualSrc;
    }
    const appended = appendVideoFragment({
      actualSrc: actualSrc.current,
      actualFrom: actualFromRef.current,
      duration: actualDuration.current,
      fps
    });
    return appended;
  };
  var warned2 = false;
  var warnSafariOnce = (logLevel) => {
    if (warned2) {
      return;
    }
    warned2 = true;
    Log.warn({ logLevel, tag: null }, "In Safari, setting a volume and a playback rate at the same time is buggy.");
    Log.warn({ logLevel, tag: null }, "In Desktop Safari, only volumes <= 1 will be applied.");
    Log.warn({ logLevel, tag: null }, logLevel, "In Mobile Safari, the volume will be ignored and set to 1 if a playbackRate is set.");
  };
  var useVolume = ({
    mediaRef,
    volume,
    logLevel,
    source,
    shouldUseWebAudioApi
  }) => {
    const audioStuffRef = (0, import_react34.useRef)(null);
    const currentVolumeRef = (0, import_react34.useRef)(volume);
    currentVolumeRef.current = volume;
    const sharedAudioContext = (0, import_react34.useContext)(SharedAudioContext);
    if (!sharedAudioContext) {
      throw new Error("useAmplification must be used within a SharedAudioContext");
    }
    const { audioContext } = sharedAudioContext;
    if (typeof window !== "undefined") {
      (0, import_react34.useLayoutEffect)(() => {
        if (!audioContext) {
          return;
        }
        if (!mediaRef.current) {
          return;
        }
        if (!shouldUseWebAudioApi) {
          return;
        }
        if (mediaRef.current.playbackRate !== 1 && isSafari()) {
          warnSafariOnce(logLevel);
          return;
        }
        if (!source) {
          return;
        }
        const gainNode = new GainNode(audioContext, {
          gain: currentVolumeRef.current
        });
        source.attemptToConnect();
        source.get().connect(gainNode);
        gainNode.connect(audioContext.destination);
        audioStuffRef.current = {
          gainNode
        };
        Log.trace({ logLevel, tag: null }, `Starting to amplify ${mediaRef.current?.src}. Gain = ${currentVolumeRef.current}, playbackRate = ${mediaRef.current?.playbackRate}`);
        return () => {
          audioStuffRef.current = null;
          gainNode.disconnect();
          source.get().disconnect();
        };
      }, [logLevel, mediaRef, audioContext, source, shouldUseWebAudioApi]);
    }
    if (audioStuffRef.current) {
      const valueToSet = volume;
      if (!isApproximatelyTheSame(audioStuffRef.current.gainNode.gain.value, valueToSet)) {
        audioStuffRef.current.gainNode.gain.value = valueToSet;
        Log.trace({ logLevel, tag: null }, `Setting gain to ${valueToSet} for ${mediaRef.current?.src}`);
      }
    }
    const safariCase = isSafari() && mediaRef.current && mediaRef.current?.playbackRate !== 1;
    const shouldUseTraditionalVolume = safariCase || !shouldUseWebAudioApi;
    if (shouldUseTraditionalVolume && mediaRef.current && !isApproximatelyTheSame(volume, mediaRef.current?.volume)) {
      mediaRef.current.volume = Math.min(volume, 1);
    }
    return audioStuffRef;
  };
  var useMediaStartsAt = () => {
    const parentSequence = (0, import_react39.useContext)(SequenceContext);
    const startsAt = Math.min(0, parentSequence?.relativeFrom ?? 0);
    return startsAt;
  };
  var useFrameForVolumeProp = (behavior) => {
    const loop = Loop.useLoop();
    const frame = useCurrentFrame();
    const startsAt = useMediaStartsAt();
    if (behavior === "repeat" || loop === null) {
      return frame + startsAt;
    }
    return frame + startsAt + loop.durationInFrames * loop.iteration;
  };
  var getAssetDisplayName = (filename) => {
    if (/data:|blob:/.test(filename.substring(0, 5))) {
      return "Data URL";
    }
    const splitted = filename.split("/").map((s) => s.split("\\")).flat(1);
    return splitted[splitted.length - 1];
  };
  var evaluateVolume = ({
    frame,
    volume,
    mediaVolume = 1
  }) => {
    if (typeof volume === "number") {
      return volume * mediaVolume;
    }
    if (typeof volume === "undefined") {
      return Number(mediaVolume);
    }
    const evaluated = volume(frame) * mediaVolume;
    if (typeof evaluated !== "number") {
      throw new TypeError(`You passed in a a function to the volume prop but it did not return a number but a value of type ${typeof evaluated} for frame ${frame}`);
    }
    if (Number.isNaN(evaluated)) {
      throw new TypeError(`You passed in a function to the volume prop but it returned NaN for frame ${frame}.`);
    }
    if (!Number.isFinite(evaluated)) {
      throw new TypeError(`You passed in a function to the volume prop but it returned a non-finite number for frame ${frame}.`);
    }
    return Math.max(0, evaluated);
  };
  var didWarn = {};
  var warnOnce2 = (message) => {
    if (didWarn[message]) {
      return;
    }
    console.warn(message);
    didWarn[message] = true;
  };
  var useBasicMediaInTimeline = ({
    volume,
    mediaVolume,
    mediaType,
    src,
    displayName,
    trimBefore,
    trimAfter,
    playbackRate
  }) => {
    if (!src) {
      throw new Error("No src passed");
    }
    const startsAt = useMediaStartsAt();
    const parentSequence = (0, import_react38.useContext)(SequenceContext);
    const videoConfig = useVideoConfig();
    const [initialVolume] = (0, import_react38.useState)(() => volume);
    const mediaDuration = calculateMediaDuration({
      mediaDurationInFrames: videoConfig.durationInFrames,
      playbackRate,
      trimBefore,
      trimAfter
    });
    const duration = parentSequence ? Math.min(parentSequence.durationInFrames, mediaDuration) : mediaDuration;
    const volumes = (0, import_react38.useMemo)(() => {
      if (typeof volume === "number") {
        return volume;
      }
      return new Array(Math.floor(Math.max(0, duration + startsAt))).fill(true).map((_, i) => {
        return evaluateVolume({
          frame: i + startsAt,
          volume,
          mediaVolume
        });
      }).join(",");
    }, [duration, startsAt, volume, mediaVolume]);
    (0, import_react38.useEffect)(() => {
      if (typeof volume === "number" && volume !== initialVolume) {
        warnOnce2(`Remotion: The ${mediaType} with src ${src} has changed it's volume. Prefer the callback syntax for setting volume to get better timeline display: https://www.remotion.dev/docs/audio/volume`);
      }
    }, [initialVolume, mediaType, src, volume]);
    const doesVolumeChange = typeof volume === "function";
    const nonce = useNonce();
    const { rootId } = (0, import_react38.useContext)(TimelineContext);
    const env = useRemotionEnvironment();
    return {
      volumes,
      duration,
      doesVolumeChange,
      nonce,
      rootId,
      isStudio: env.isStudio,
      finalDisplayName: displayName ?? getAssetDisplayName(src)
    };
  };
  var useMediaInTimeline = ({
    volume,
    mediaVolume,
    src,
    mediaType,
    playbackRate,
    displayName,
    id,
    stack,
    showInTimeline,
    premountDisplay,
    postmountDisplay,
    loopDisplay
  }) => {
    const parentSequence = (0, import_react38.useContext)(SequenceContext);
    const startsAt = useMediaStartsAt();
    const { registerSequence, unregisterSequence } = (0, import_react38.useContext)(SequenceManager);
    const {
      volumes,
      duration,
      doesVolumeChange,
      nonce,
      rootId,
      isStudio,
      finalDisplayName
    } = useBasicMediaInTimeline({
      volume,
      mediaVolume,
      mediaType,
      src,
      displayName,
      trimAfter: void 0,
      trimBefore: void 0,
      playbackRate
    });
    (0, import_react38.useEffect)(() => {
      if (!src) {
        throw new Error("No src passed");
      }
      if (!isStudio && window.process?.env?.NODE_ENV !== "test") {
        return;
      }
      if (!showInTimeline) {
        return;
      }
      registerSequence({
        type: mediaType,
        src,
        id,
        duration,
        from: 0,
        parent: parentSequence?.id ?? null,
        displayName: finalDisplayName,
        rootId,
        volume: volumes,
        showInTimeline: true,
        nonce,
        startMediaFrom: 0 - startsAt,
        doesVolumeChange,
        loopDisplay,
        playbackRate,
        stack,
        premountDisplay,
        postmountDisplay
      });
      return () => {
        unregisterSequence(id);
      };
    }, [
      duration,
      id,
      parentSequence,
      src,
      registerSequence,
      unregisterSequence,
      volumes,
      doesVolumeChange,
      nonce,
      mediaType,
      startsAt,
      playbackRate,
      stack,
      showInTimeline,
      premountDisplay,
      postmountDisplay,
      isStudio,
      loopDisplay,
      rootId,
      finalDisplayName
    ]);
  };
  var useBufferManager = (logLevel, mountTime) => {
    const [blocks, setBlocks] = (0, import_react43.useState)([]);
    const [onBufferingCallbacks, setOnBufferingCallbacks] = (0, import_react43.useState)([]);
    const [onResumeCallbacks, setOnResumeCallbacks] = (0, import_react43.useState)([]);
    const env = useRemotionEnvironment();
    const rendering = env.isRendering;
    const buffering = (0, import_react43.useRef)(false);
    const addBlock = (0, import_react43.useCallback)((block) => {
      if (rendering) {
        return {
          unblock: () => {
            return;
          }
        };
      }
      setBlocks((b2) => [...b2, block]);
      return {
        unblock: () => {
          setBlocks((b2) => {
            const newArr = b2.filter((bx) => bx !== block);
            if (newArr.length === b2.length) {
              return b2;
            }
            return newArr;
          });
        }
      };
    }, [rendering]);
    const listenForBuffering = (0, import_react43.useCallback)((callback) => {
      setOnBufferingCallbacks((c2) => [...c2, callback]);
      return {
        remove: () => {
          setOnBufferingCallbacks((c2) => c2.filter((cb) => cb !== callback));
        }
      };
    }, []);
    const listenForResume = (0, import_react43.useCallback)((callback) => {
      setOnResumeCallbacks((c2) => [...c2, callback]);
      return {
        remove: () => {
          setOnResumeCallbacks((c2) => c2.filter((cb) => cb !== callback));
        }
      };
    }, []);
    (0, import_react43.useEffect)(() => {
      if (rendering) {
        return;
      }
      if (blocks.length > 0) {
        onBufferingCallbacks.forEach((c2) => c2());
        playbackLogging({
          logLevel,
          message: "Player is entering buffer state",
          mountTime,
          tag: "player"
        });
      }
    }, [blocks]);
    if (typeof window !== "undefined") {
      (0, import_react43.useLayoutEffect)(() => {
        if (rendering) {
          return;
        }
        if (blocks.length === 0) {
          onResumeCallbacks.forEach((c2) => c2());
          playbackLogging({
            logLevel,
            message: "Player is exiting buffer state",
            mountTime,
            tag: "player"
          });
        }
      }, [blocks]);
    }
    return (0, import_react43.useMemo)(() => {
      return { addBlock, listenForBuffering, listenForResume, buffering };
    }, [addBlock, buffering, listenForBuffering, listenForResume]);
  };
  var BufferingContextReact = import_react43.default.createContext(null);
  var BufferingProvider = ({ children }) => {
    const { logLevel, mountTime } = (0, import_react43.useContext)(LogLevelContext);
    const bufferManager = useBufferManager(logLevel ?? "info", mountTime);
    return /* @__PURE__ */ (0, import_jsx_runtime17.jsx)(BufferingContextReact.Provider, {
      value: bufferManager,
      children
    });
  };
  var useIsPlayerBuffering = (bufferManager) => {
    const [isBuffering, setIsBuffering] = (0, import_react43.useState)(bufferManager.buffering.current);
    (0, import_react43.useEffect)(() => {
      const onBuffer = () => {
        setIsBuffering(true);
      };
      const onResume = () => {
        setIsBuffering(false);
      };
      bufferManager.listenForBuffering(onBuffer);
      bufferManager.listenForResume(onResume);
      return () => {
        bufferManager.listenForBuffering(() => {
          return;
        });
        bufferManager.listenForResume(() => {
          return;
        });
      };
    }, [bufferManager]);
    return isBuffering;
  };
  var useBufferState = () => {
    const buffer = (0, import_react42.useContext)(BufferingContextReact);
    const addBlock = buffer ? buffer.addBlock : null;
    return (0, import_react42.useMemo)(() => ({
      delayPlayback: () => {
        if (!addBlock) {
          throw new Error("Tried to enable the buffering state, but a Remotion context was not found. This API can only be called in a component that was passed to the Remotion Player or a <Composition>. Or you might have experienced a version mismatch - run `npx remotion versions` and ensure all packages have the same version. This error is thrown by the buffer state https://remotion.dev/docs/player/buffer-state");
        }
        const { unblock } = addBlock({
          id: String(Math.random())
        });
        return { unblock };
      }
    }), [addBlock]);
  };
  var isSafariWebkit = () => {
    const isSafari2 = /^((?!chrome|android).)*safari/i.test(window.navigator.userAgent);
    return isSafari2;
  };
  var useBufferUntilFirstFrame = ({
    mediaRef,
    mediaType,
    onVariableFpsVideoDetected,
    pauseWhenBuffering,
    logLevel,
    mountTime
  }) => {
    const bufferingRef = (0, import_react41.useRef)(false);
    const { delayPlayback } = useBufferState();
    const bufferUntilFirstFrame = (0, import_react41.useCallback)((requestedTime) => {
      if (mediaType !== "video") {
        return;
      }
      if (!pauseWhenBuffering) {
        return;
      }
      const current = mediaRef.current;
      if (!current) {
        return;
      }
      if (current.readyState >= current.HAVE_FUTURE_DATA && !isSafariWebkit()) {
        playbackLogging({
          logLevel,
          message: `Not using buffer until first frame, because readyState is ${current.readyState} and is not Safari or Desktop Chrome`,
          mountTime,
          tag: "buffer"
        });
        return;
      }
      if (!current.requestVideoFrameCallback) {
        playbackLogging({
          logLevel,
          message: `Not using buffer until first frame, because requestVideoFrameCallback is not supported`,
          mountTime,
          tag: "buffer"
        });
        return;
      }
      bufferingRef.current = true;
      playbackLogging({
        logLevel,
        message: `Buffering ${mediaRef.current?.src} until the first frame is received`,
        mountTime,
        tag: "buffer"
      });
      const playback = delayPlayback();
      const unblock = () => {
        playback.unblock();
        current.removeEventListener("ended", unblock, {
          once: true
        });
        current.removeEventListener("pause", unblock, {
          once: true
        });
        bufferingRef.current = false;
      };
      const onEndedOrPauseOrCanPlay = () => {
        unblock();
      };
      current.requestVideoFrameCallback((_, info2) => {
        const differenceFromRequested = Math.abs(info2.mediaTime - requestedTime);
        if (differenceFromRequested > 0.5) {
          onVariableFpsVideoDetected();
        }
        unblock();
      });
      current.addEventListener("ended", onEndedOrPauseOrCanPlay, { once: true });
      current.addEventListener("pause", onEndedOrPauseOrCanPlay, { once: true });
      current.addEventListener("canplay", onEndedOrPauseOrCanPlay, {
        once: true
      });
    }, [
      delayPlayback,
      logLevel,
      mediaRef,
      mediaType,
      mountTime,
      onVariableFpsVideoDetected,
      pauseWhenBuffering
    ]);
    return (0, import_react41.useMemo)(() => {
      return {
        isBuffering: () => bufferingRef.current,
        bufferUntilFirstFrame
      };
    }, [bufferUntilFirstFrame]);
  };
  var useCurrentTimeOfMediaTagWithUpdateTimeStamp = (mediaRef) => {
    const lastUpdate = import_react44.default.useRef({
      time: mediaRef.current?.currentTime ?? 0,
      lastUpdate: performance.now()
    });
    const nowCurrentTime = mediaRef.current?.currentTime ?? null;
    if (nowCurrentTime !== null) {
      if (lastUpdate.current.time !== nowCurrentTime) {
        lastUpdate.current.time = nowCurrentTime;
        lastUpdate.current.lastUpdate = performance.now();
      }
    }
    return lastUpdate;
  };
  var seek = ({
    mediaRef,
    time,
    logLevel,
    why,
    mountTime
  }) => {
    const timeToSet = isIosSafari() ? Number(time.toFixed(1)) : time;
    playbackLogging({
      logLevel,
      tag: "seek",
      message: `Seeking from ${mediaRef.currentTime} to ${timeToSet}. src= ${mediaRef.src} Reason: ${why}`,
      mountTime
    });
    mediaRef.currentTime = timeToSet;
    return timeToSet;
  };
  var useMediaBuffering = ({
    element,
    shouldBuffer,
    isPremounting,
    isPostmounting,
    logLevel,
    mountTime,
    src
  }) => {
    const buffer = useBufferState();
    const [isBuffering, setIsBuffering] = (0, import_react45.useState)(false);
    (0, import_react45.useEffect)(() => {
      let cleanupFns = [];
      const { current } = element;
      if (!current) {
        return;
      }
      if (!shouldBuffer) {
        return;
      }
      if (isPremounting || isPostmounting) {
        if ((isPremounting || isPostmounting) && current.readyState < current.HAVE_FUTURE_DATA) {
          if (!navigator.userAgent.includes("Firefox/")) {
            playbackLogging({
              logLevel,
              message: `Calling .load() on ${current.src} because readyState is ${current.readyState} and it is not Firefox. Element is premounted ${current.playbackRate}`,
              tag: "load",
              mountTime
            });
            const previousPlaybackRate = current.playbackRate;
            current.load();
            current.playbackRate = previousPlaybackRate;
          }
        }
        return;
      }
      const cleanup = (reason) => {
        let didDoSomething = false;
        cleanupFns.forEach((fn) => {
          fn(reason);
          didDoSomething = true;
        });
        cleanupFns = [];
        setIsBuffering((previous) => {
          if (previous) {
            didDoSomething = true;
          }
          return false;
        });
        if (didDoSomething) {
          playbackLogging({
            logLevel,
            message: `Unmarking as buffering: ${current.src}. Reason: ${reason}`,
            tag: "buffer",
            mountTime
          });
        }
      };
      const blockMedia = (reason) => {
        setIsBuffering(true);
        playbackLogging({
          logLevel,
          message: `Marking as buffering: ${current.src}. Reason: ${reason}`,
          tag: "buffer",
          mountTime
        });
        const { unblock } = buffer.delayPlayback();
        const onCanPlay = () => {
          cleanup('"canplay" was fired');
          init();
        };
        const onError = () => {
          cleanup('"error" event was occurred');
          init();
        };
        current.addEventListener("canplay", onCanPlay, {
          once: true
        });
        cleanupFns.push(() => {
          current.removeEventListener("canplay", onCanPlay);
        });
        current.addEventListener("error", onError, {
          once: true
        });
        cleanupFns.push(() => {
          current.removeEventListener("error", onError);
        });
        cleanupFns.push((cleanupReason) => {
          playbackLogging({
            logLevel,
            message: `Unblocking ${current.src} from buffer. Reason: ${cleanupReason}`,
            tag: "buffer",
            mountTime
          });
          unblock();
        });
      };
      const init = () => {
        if (current.readyState < current.HAVE_FUTURE_DATA) {
          blockMedia(`readyState is ${current.readyState}, which is less than HAVE_FUTURE_DATA`);
          if (!navigator.userAgent.includes("Firefox/")) {
            playbackLogging({
              logLevel,
              message: `Calling .load() on ${src} because readyState is ${current.readyState} and it is not Firefox. ${current.playbackRate}`,
              tag: "load",
              mountTime
            });
            const previousPlaybackRate = current.playbackRate;
            current.load();
            current.playbackRate = previousPlaybackRate;
          }
        } else {
          const onWaiting = () => {
            blockMedia('"waiting" event was fired');
          };
          current.addEventListener("waiting", onWaiting);
          cleanupFns.push(() => {
            current.removeEventListener("waiting", onWaiting);
          });
        }
      };
      init();
      return () => {
        cleanup("element was unmounted or prop changed");
      };
    }, [
      buffer,
      src,
      element,
      isPremounting,
      isPostmounting,
      logLevel,
      shouldBuffer,
      mountTime
    ]);
    return isBuffering;
  };
  var useRequestVideoCallbackTime = ({
    mediaRef,
    mediaType,
    lastSeek,
    onVariableFpsVideoDetected
  }) => {
    const currentTime = (0, import_react46.useRef)(null);
    (0, import_react46.useEffect)(() => {
      const { current } = mediaRef;
      if (current) {
        currentTime.current = {
          time: current.currentTime,
          lastUpdate: performance.now()
        };
      } else {
        currentTime.current = null;
        return;
      }
      if (mediaType !== "video") {
        currentTime.current = null;
        return;
      }
      const videoTag = current;
      if (!videoTag.requestVideoFrameCallback) {
        return;
      }
      let cancel = () => {
        return;
      };
      const request = () => {
        if (!videoTag) {
          return;
        }
        const cb = videoTag.requestVideoFrameCallback((_, info2) => {
          if (currentTime.current !== null) {
            const difference = Math.abs(currentTime.current.time - info2.mediaTime);
            const differenceToLastSeek = Math.abs(lastSeek.current === null ? Infinity : info2.mediaTime - lastSeek.current);
            if (difference > 0.5 && differenceToLastSeek > 0.5 && info2.mediaTime > currentTime.current.time) {
              onVariableFpsVideoDetected();
            }
          }
          currentTime.current = {
            time: info2.mediaTime,
            lastUpdate: performance.now()
          };
          request();
        });
        cancel = () => {
          videoTag.cancelVideoFrameCallback(cb);
          cancel = () => {
            return;
          };
        };
      };
      request();
      return () => {
        cancel();
      };
    }, [lastSeek, mediaRef, mediaType, onVariableFpsVideoDetected]);
    return currentTime;
  };
  function interpolateFunction(input, inputRange, outputRange, options) {
    const { extrapolateLeft, extrapolateRight, easing } = options;
    let result = input;
    const [inputMin, inputMax] = inputRange;
    const [outputMin, outputMax] = outputRange;
    if (result < inputMin) {
      if (extrapolateLeft === "identity") {
        return result;
      }
      if (extrapolateLeft === "clamp") {
        result = inputMin;
      } else if (extrapolateLeft === "wrap") {
        const range = inputMax - inputMin;
        result = ((result - inputMin) % range + range) % range + inputMin;
      } else if (extrapolateLeft === "extend") {
      }
    }
    if (result > inputMax) {
      if (extrapolateRight === "identity") {
        return result;
      }
      if (extrapolateRight === "clamp") {
        result = inputMax;
      } else if (extrapolateRight === "wrap") {
        const range = inputMax - inputMin;
        result = ((result - inputMin) % range + range) % range + inputMin;
      } else if (extrapolateRight === "extend") {
      }
    }
    if (outputMin === outputMax) {
      return outputMin;
    }
    result = (result - inputMin) / (inputMax - inputMin);
    result = easing(result);
    result = result * (outputMax - outputMin) + outputMin;
    return result;
  }
  function findRange(input, inputRange) {
    let i;
    for (i = 1; i < inputRange.length - 1; ++i) {
      if (inputRange[i] >= input) {
        break;
      }
    }
    return i - 1;
  }
  function checkValidInputRange(arr) {
    for (let i = 1; i < arr.length; ++i) {
      if (!(arr[i] > arr[i - 1])) {
        throw new Error(`inputRange must be strictly monotonically increasing but got [${arr.join(",")}]`);
      }
    }
  }
  function checkInfiniteRange(name, arr) {
    if (arr.length < 2) {
      throw new Error(name + " must have at least 2 elements");
    }
    for (const element of arr) {
      if (typeof element !== "number") {
        throw new Error(`${name} must contain only numbers`);
      }
      if (!Number.isFinite(element)) {
        throw new Error(`${name} must contain only finite numbers, but got [${arr.join(",")}]`);
      }
    }
  }
  function interpolate(input, inputRange, outputRange, options) {
    if (typeof input === "undefined") {
      throw new Error("input can not be undefined");
    }
    if (typeof inputRange === "undefined") {
      throw new Error("inputRange can not be undefined");
    }
    if (typeof outputRange === "undefined") {
      throw new Error("outputRange can not be undefined");
    }
    if (inputRange.length !== outputRange.length) {
      throw new Error("inputRange (" + inputRange.length + ") and outputRange (" + outputRange.length + ") must have the same length");
    }
    checkInfiniteRange("inputRange", inputRange);
    checkInfiniteRange("outputRange", outputRange);
    checkValidInputRange(inputRange);
    const easing = options?.easing ?? ((num) => num);
    let extrapolateLeft = "extend";
    if (options?.extrapolateLeft !== void 0) {
      extrapolateLeft = options.extrapolateLeft;
    }
    let extrapolateRight = "extend";
    if (options?.extrapolateRight !== void 0) {
      extrapolateRight = options.extrapolateRight;
    }
    if (typeof input !== "number") {
      throw new TypeError("Cannot interpolate an input which is not a number");
    }
    const range = findRange(input, inputRange);
    return interpolateFunction(input, [inputRange[range], inputRange[range + 1]], [outputRange[range], outputRange[range + 1]], {
      easing,
      extrapolateLeft,
      extrapolateRight
    });
  }
  var getExpectedMediaFrameUncorrected = ({
    frame,
    playbackRate,
    startFrom
  }) => {
    return interpolate(frame, [-1, startFrom, startFrom + 1], [-1, startFrom, startFrom + playbackRate]);
  };
  var getMediaTime = ({
    fps,
    frame,
    playbackRate,
    startFrom
  }) => {
    const expectedFrame = getExpectedMediaFrameUncorrected({
      frame,
      playbackRate,
      startFrom
    });
    const msPerFrame = 1e3 / fps;
    return expectedFrame * msPerFrame / 1e3;
  };
  var alreadyWarned = {};
  var warnAboutNonSeekableMedia = (ref, type) => {
    if (ref === null) {
      return;
    }
    if (ref.seekable.length === 0) {
      return;
    }
    if (ref.seekable.length > 1) {
      return;
    }
    if (alreadyWarned[ref.src]) {
      return;
    }
    const range = { start: ref.seekable.start(0), end: ref.seekable.end(0) };
    if (range.start === 0 && range.end === 0) {
      const msg = [
        `The media ${ref.src} cannot be seeked. This could be one of few reasons:`,
        "1) The media resource was replaced while the video is playing but it was not loaded yet.",
        "2) The media does not support seeking.",
        "3) The media was loaded with security headers prventing it from being included.",
        "Please see https://remotion.dev/docs/non-seekable-media for assistance."
      ].join(`
`);
      if (type === "console-error") {
        console.error(msg);
      } else if (type === "console-warning") {
        console.warn(`The media ${ref.src} does not support seeking. The video will render fine, but may not play correctly in the Remotion Studio and in the <Player>. See https://remotion.dev/docs/non-seekable-media for an explanation.`);
      } else {
        throw new Error(msg);
      }
      alreadyWarned[ref.src] = true;
    }
  };
  var useMediaPlayback = ({
    mediaRef,
    src,
    mediaType,
    playbackRate: localPlaybackRate,
    onlyWarnForMediaSeekingError,
    acceptableTimeshift,
    pauseWhenBuffering,
    isPremounting,
    isPostmounting,
    onAutoPlayError
  }) => {
    const { playbackRate: globalPlaybackRate } = (0, import_react40.useContext)(TimelineContext);
    const frame = useCurrentFrame();
    const absoluteFrame = useTimelinePosition();
    const [playing] = usePlayingState();
    const buffering = (0, import_react40.useContext)(BufferingContextReact);
    const { fps } = useVideoConfig();
    const mediaStartsAt = useMediaStartsAt();
    const lastSeekDueToShift = (0, import_react40.useRef)(null);
    const lastSeek = (0, import_react40.useRef)(null);
    const logLevel = useLogLevel();
    const mountTime = useMountTime();
    if (!buffering) {
      throw new Error("useMediaPlayback must be used inside a <BufferingContext>");
    }
    const isVariableFpsVideoMap = (0, import_react40.useRef)({});
    const onVariableFpsVideoDetected = (0, import_react40.useCallback)(() => {
      if (!src) {
        return;
      }
      if (isVariableFpsVideoMap.current[src]) {
        return;
      }
      Log.verbose({ logLevel, tag: null }, `Detected ${src} as a variable FPS video. Disabling buffering while seeking.`);
      isVariableFpsVideoMap.current[src] = true;
    }, [logLevel, src]);
    const rvcCurrentTime = useRequestVideoCallbackTime({
      mediaRef,
      mediaType,
      lastSeek,
      onVariableFpsVideoDetected
    });
    const mediaTagCurrentTime = useCurrentTimeOfMediaTagWithUpdateTimeStamp(mediaRef);
    const desiredUnclampedTime = getMediaTime({
      frame,
      playbackRate: localPlaybackRate,
      startFrom: -mediaStartsAt,
      fps
    });
    const isMediaTagBuffering = useMediaBuffering({
      element: mediaRef,
      shouldBuffer: pauseWhenBuffering,
      isPremounting,
      isPostmounting,
      logLevel,
      mountTime,
      src: src ?? null
    });
    const { bufferUntilFirstFrame, isBuffering } = useBufferUntilFirstFrame({
      mediaRef,
      mediaType,
      onVariableFpsVideoDetected,
      pauseWhenBuffering,
      logLevel,
      mountTime
    });
    const playbackRate = localPlaybackRate * globalPlaybackRate;
    const acceptableTimeShiftButLessThanDuration = (() => {
      const DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_NORMAL_PLAYBACK = 0.45;
      const DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_AMPLIFICATION = DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_NORMAL_PLAYBACK + 0.2;
      const defaultAcceptableTimeshift = DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_AMPLIFICATION;
      if (mediaRef.current?.duration) {
        return Math.min(mediaRef.current.duration, acceptableTimeshift ?? defaultAcceptableTimeshift);
      }
      return acceptableTimeshift ?? defaultAcceptableTimeshift;
    })();
    const isPlayerBuffering = useIsPlayerBuffering(buffering);
    (0, import_react40.useEffect)(() => {
      if (mediaRef.current?.paused) {
        return;
      }
      if (!playing) {
        playbackLogging({
          logLevel,
          tag: "pause",
          message: `Pausing ${mediaRef.current?.src} because ${isPremounting ? "media is premounting" : isPostmounting ? "media is postmounting" : "Player is not playing"}`,
          mountTime
        });
        mediaRef.current?.pause();
        return;
      }
      const isMediaTagBufferingOrStalled = isMediaTagBuffering || isBuffering();
      const playerBufferingNotStateButLive = buffering.buffering.current;
      if (playerBufferingNotStateButLive && !isMediaTagBufferingOrStalled) {
        playbackLogging({
          logLevel,
          tag: "pause",
          message: `Pausing ${mediaRef.current?.src} because player is buffering but media tag is not`,
          mountTime
        });
        mediaRef.current?.pause();
      }
    }, [
      isBuffering,
      isMediaTagBuffering,
      buffering,
      isPlayerBuffering,
      isPremounting,
      logLevel,
      mediaRef,
      mediaType,
      mountTime,
      playing,
      isPostmounting
    ]);
    const env = useRemotionEnvironment();
    (0, import_react40.useLayoutEffect)(() => {
      const playbackRateToSet = Math.max(0, playbackRate);
      if (mediaRef.current && mediaRef.current.playbackRate !== playbackRateToSet) {
        mediaRef.current.playbackRate = playbackRateToSet;
      }
    }, [mediaRef, playbackRate]);
    (0, import_react40.useEffect)(() => {
      const tagName = mediaType === "audio" ? "<Html5Audio>" : "<Html5Video>";
      if (!mediaRef.current) {
        throw new Error(`No ${mediaType} ref found`);
      }
      if (!src) {
        throw new Error(`No 'src' attribute was passed to the ${tagName} element.`);
      }
      const { duration } = mediaRef.current;
      const shouldBeTime = !Number.isNaN(duration) && Number.isFinite(duration) ? Math.min(duration, desiredUnclampedTime) : desiredUnclampedTime;
      const mediaTagTime = mediaTagCurrentTime.current.time;
      const rvcTime = rvcCurrentTime.current?.time ?? null;
      const isVariableFpsVideo = isVariableFpsVideoMap.current[src];
      const timeShiftMediaTag = Math.abs(shouldBeTime - mediaTagTime);
      const timeShiftRvcTag = rvcTime ? Math.abs(shouldBeTime - rvcTime) : null;
      const mostRecentTimeshift = rvcCurrentTime.current?.lastUpdate && rvcCurrentTime.current.time > mediaTagCurrentTime.current.lastUpdate ? timeShiftRvcTag : timeShiftMediaTag;
      const timeShift = timeShiftRvcTag && !isVariableFpsVideo ? mostRecentTimeshift : timeShiftMediaTag;
      if (timeShift > acceptableTimeShiftButLessThanDuration && lastSeekDueToShift.current !== shouldBeTime) {
        lastSeek.current = seek({
          mediaRef: mediaRef.current,
          time: shouldBeTime,
          logLevel,
          why: `because time shift is too big. shouldBeTime = ${shouldBeTime}, isTime = ${mediaTagTime}, requestVideoCallbackTime = ${rvcTime}, timeShift = ${timeShift}${isVariableFpsVideo ? ", isVariableFpsVideo = true" : ""}, isPremounting = ${isPremounting}, isPostmounting = ${isPostmounting}, pauseWhenBuffering = ${pauseWhenBuffering}`,
          mountTime
        });
        lastSeekDueToShift.current = lastSeek.current;
        if (playing) {
          if (playbackRate > 0) {
            bufferUntilFirstFrame(shouldBeTime);
          }
          if (mediaRef.current.paused) {
            playAndHandleNotAllowedError({
              mediaRef,
              mediaType,
              onAutoPlayError,
              logLevel,
              mountTime,
              reason: "player is playing but media tag is paused, and just seeked",
              isPlayer: env.isPlayer
            });
          }
        }
        if (!onlyWarnForMediaSeekingError) {
          warnAboutNonSeekableMedia(mediaRef.current, onlyWarnForMediaSeekingError ? "console-warning" : "console-error");
        }
        return;
      }
      const seekThreshold = playing ? 0.15 : 0.01;
      const makesSenseToSeek = Math.abs(mediaRef.current.currentTime - shouldBeTime) > seekThreshold;
      const isMediaTagBufferingOrStalled = isMediaTagBuffering || isBuffering();
      const isSomethingElseBuffering = buffering.buffering.current && !isMediaTagBufferingOrStalled;
      if (!playing || isSomethingElseBuffering) {
        if (makesSenseToSeek) {
          lastSeek.current = seek({
            mediaRef: mediaRef.current,
            time: shouldBeTime,
            logLevel,
            why: `not playing or something else is buffering. time offset is over seek threshold (${seekThreshold})`,
            mountTime
          });
        }
        return;
      }
      if (!playing || buffering.buffering.current) {
        return;
      }
      const pausedCondition = mediaRef.current.paused && !mediaRef.current.ended;
      const firstFrameCondition = absoluteFrame === 0;
      if (pausedCondition || firstFrameCondition) {
        const reason = pausedCondition ? "media tag is paused" : "absolute frame is 0";
        if (makesSenseToSeek) {
          lastSeek.current = seek({
            mediaRef: mediaRef.current,
            time: shouldBeTime,
            logLevel,
            why: `is over timeshift threshold (threshold = ${seekThreshold}) and ${reason}`,
            mountTime
          });
        }
        playAndHandleNotAllowedError({
          mediaRef,
          mediaType,
          onAutoPlayError,
          logLevel,
          mountTime,
          reason: `player is playing and ${reason}`,
          isPlayer: env.isPlayer
        });
        if (!isVariableFpsVideo && playbackRate > 0) {
          bufferUntilFirstFrame(shouldBeTime);
        }
      }
    }, [
      absoluteFrame,
      acceptableTimeShiftButLessThanDuration,
      bufferUntilFirstFrame,
      buffering.buffering,
      rvcCurrentTime,
      logLevel,
      desiredUnclampedTime,
      isBuffering,
      isMediaTagBuffering,
      mediaRef,
      mediaType,
      onlyWarnForMediaSeekingError,
      playbackRate,
      playing,
      src,
      onAutoPlayError,
      isPremounting,
      isPostmounting,
      pauseWhenBuffering,
      mountTime,
      mediaTagCurrentTime,
      env.isPlayer
    ]);
  };
  var useMediaTag = ({
    mediaRef,
    id,
    mediaType,
    onAutoPlayError,
    isPremounting,
    isPostmounting
  }) => {
    const { audioAndVideoTags, imperativePlaying } = (0, import_react47.useContext)(TimelineContext);
    const logLevel = useLogLevel();
    const mountTime = useMountTime();
    const env = useRemotionEnvironment();
    (0, import_react47.useEffect)(() => {
      const tag = {
        id,
        play: (reason) => {
          if (!imperativePlaying.current) {
            return;
          }
          if (isPremounting || isPostmounting) {
            return;
          }
          return playAndHandleNotAllowedError({
            mediaRef,
            mediaType,
            onAutoPlayError,
            logLevel,
            mountTime,
            reason,
            isPlayer: env.isPlayer
          });
        }
      };
      audioAndVideoTags.current.push(tag);
      return () => {
        audioAndVideoTags.current = audioAndVideoTags.current.filter((a2) => a2.id !== id);
      };
    }, [
      audioAndVideoTags,
      id,
      mediaRef,
      mediaType,
      onAutoPlayError,
      imperativePlaying,
      isPremounting,
      isPostmounting,
      logLevel,
      mountTime,
      env.isPlayer
    ]);
  };
  var MediaVolumeContext = (0, import_react48.createContext)({
    mediaMuted: false,
    mediaVolume: 1
  });
  var SetMediaVolumeContext = (0, import_react48.createContext)({
    setMediaMuted: () => {
      throw new Error("default");
    },
    setMediaVolume: () => {
      throw new Error("default");
    }
  });
  var useMediaVolumeState = () => {
    const { mediaVolume } = (0, import_react48.useContext)(MediaVolumeContext);
    const { setMediaVolume } = (0, import_react48.useContext)(SetMediaVolumeContext);
    return (0, import_react48.useMemo)(() => {
      return [mediaVolume, setMediaVolume];
    }, [mediaVolume, setMediaVolume]);
  };
  var useMediaMutedState = () => {
    const { mediaMuted } = (0, import_react48.useContext)(MediaVolumeContext);
    const { setMediaMuted } = (0, import_react48.useContext)(SetMediaVolumeContext);
    return (0, import_react48.useMemo)(() => {
      return [mediaMuted, setMediaMuted];
    }, [mediaMuted, setMediaMuted]);
  };
  var warnAboutTooHighVolume = (volume) => {
    if (volume >= 100) {
      throw new Error(`Volume was set to ${volume}, but regular volume is 1, not 100. Did you forget to divide by 100? Set a volume of less than 100 to dismiss this error.`);
    }
  };
  var AudioForDevelopmentForwardRefFunction = (props, ref) => {
    const [initialShouldPreMountAudioElements] = (0, import_react33.useState)(props.shouldPreMountAudioTags);
    if (props.shouldPreMountAudioTags !== initialShouldPreMountAudioElements) {
      throw new Error("Cannot change the behavior for pre-mounting audio tags dynamically.");
    }
    const logLevel = useLogLevel();
    const {
      volume,
      muted,
      playbackRate,
      shouldPreMountAudioTags,
      src,
      onDuration,
      acceptableTimeShiftInSeconds,
      _remotionInternalNeedsDurationCalculation,
      _remotionInternalNativeLoopPassed,
      _remotionInternalStack,
      allowAmplificationDuringRender,
      name,
      pauseWhenBuffering,
      showInTimeline,
      loopVolumeCurveBehavior,
      stack,
      crossOrigin,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      toneFrequency,
      useWebAudioApi,
      onError,
      onNativeError,
      audioStreamIndex,
      ...nativeProps
    } = props;
    const _propsValid = true;
    if (!_propsValid) {
      throw new Error("typecheck error");
    }
    const [mediaVolume] = useMediaVolumeState();
    const [mediaMuted] = useMediaMutedState();
    const volumePropFrame = useFrameForVolumeProp(loopVolumeCurveBehavior ?? "repeat");
    const { hidden } = (0, import_react33.useContext)(SequenceVisibilityToggleContext);
    if (!src) {
      throw new TypeError("No 'src' was passed to <Html5Audio>.");
    }
    const preloadedSrc = usePreload(src);
    const sequenceContext = (0, import_react33.useContext)(SequenceContext);
    const [timelineId] = (0, import_react33.useState)(() => String(Math.random()));
    const isSequenceHidden = hidden[timelineId] ?? false;
    const userPreferredVolume = evaluateVolume({
      frame: volumePropFrame,
      volume,
      mediaVolume
    });
    warnAboutTooHighVolume(userPreferredVolume);
    const crossOriginValue = getCrossOriginValue({
      crossOrigin,
      requestsVideoFrame: false,
      isClientSideRendering: false
    });
    const propsToPass = (0, import_react33.useMemo)(() => {
      return {
        muted: muted || mediaMuted || isSequenceHidden || userPreferredVolume <= 0,
        src: preloadedSrc,
        loop: _remotionInternalNativeLoopPassed,
        crossOrigin: crossOriginValue,
        ...nativeProps
      };
    }, [
      _remotionInternalNativeLoopPassed,
      isSequenceHidden,
      mediaMuted,
      muted,
      nativeProps,
      preloadedSrc,
      userPreferredVolume,
      crossOriginValue
    ]);
    const id = (0, import_react33.useMemo)(() => `audio-${random(src ?? "")}-${sequenceContext?.relativeFrom}-${sequenceContext?.cumulatedFrom}-${sequenceContext?.durationInFrames}-muted:${props.muted}-loop:${props.loop}`, [
      src,
      sequenceContext?.relativeFrom,
      sequenceContext?.cumulatedFrom,
      sequenceContext?.durationInFrames,
      props.muted,
      props.loop
    ]);
    const {
      el: audioRef,
      mediaElementSourceNode,
      cleanupOnMediaTagUnmount
    } = useSharedAudio({
      aud: propsToPass,
      audioId: id,
      premounting: Boolean(sequenceContext?.premounting),
      postmounting: Boolean(sequenceContext?.postmounting)
    });
    useMediaInTimeline({
      volume,
      mediaVolume,
      src,
      mediaType: "audio",
      playbackRate: playbackRate ?? 1,
      displayName: name ?? null,
      id: timelineId,
      stack: _remotionInternalStack,
      showInTimeline,
      premountDisplay: sequenceContext?.premountDisplay ?? null,
      postmountDisplay: sequenceContext?.postmountDisplay ?? null,
      loopDisplay: void 0
    });
    useMediaPlayback({
      mediaRef: audioRef,
      src,
      mediaType: "audio",
      playbackRate: playbackRate ?? 1,
      onlyWarnForMediaSeekingError: false,
      acceptableTimeshift: acceptableTimeShiftInSeconds ?? null,
      isPremounting: Boolean(sequenceContext?.premounting),
      isPostmounting: Boolean(sequenceContext?.postmounting),
      pauseWhenBuffering,
      onAutoPlayError: null
    });
    useMediaTag({
      id: timelineId,
      isPostmounting: Boolean(sequenceContext?.postmounting),
      isPremounting: Boolean(sequenceContext?.premounting),
      mediaRef: audioRef,
      mediaType: "audio",
      onAutoPlayError: null
    });
    useVolume({
      logLevel,
      mediaRef: audioRef,
      source: mediaElementSourceNode,
      volume: userPreferredVolume,
      shouldUseWebAudioApi: useWebAudioApi ?? false
    });
    const effectToUse = import_react33.default.useInsertionEffect ?? import_react33.default.useLayoutEffect;
    effectToUse(() => {
      return () => {
        requestAnimationFrame(() => {
          cleanupOnMediaTagUnmount();
        });
      };
    }, [cleanupOnMediaTagUnmount]);
    (0, import_react33.useImperativeHandle)(ref, () => {
      return audioRef.current;
    }, [audioRef]);
    const currentOnDurationCallback = (0, import_react33.useRef)(onDuration);
    currentOnDurationCallback.current = onDuration;
    (0, import_react33.useEffect)(() => {
      const { current } = audioRef;
      if (!current) {
        return;
      }
      if (current.duration) {
        currentOnDurationCallback.current?.(current.src, current.duration);
        return;
      }
      const onLoadedMetadata = () => {
        currentOnDurationCallback.current?.(current.src, current.duration);
      };
      current.addEventListener("loadedmetadata", onLoadedMetadata);
      return () => {
        current.removeEventListener("loadedmetadata", onLoadedMetadata);
      };
    }, [audioRef, src]);
    if (initialShouldPreMountAudioElements) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime18.jsx)("audio", {
      ref: audioRef,
      preload: "metadata",
      crossOrigin: crossOriginValue,
      ...propsToPass
    });
  };
  var AudioForPreview = (0, import_react33.forwardRef)(AudioForDevelopmentForwardRefFunction);
  var AudioForRenderingRefForwardingFunction = (props, ref) => {
    const audioRef = (0, import_react49.useRef)(null);
    const {
      volume: volumeProp,
      playbackRate,
      allowAmplificationDuringRender,
      onDuration,
      toneFrequency,
      _remotionInternalNeedsDurationCalculation,
      _remotionInternalNativeLoopPassed,
      acceptableTimeShiftInSeconds,
      name,
      onNativeError,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      loopVolumeCurveBehavior,
      pauseWhenBuffering,
      audioStreamIndex,
      ...nativeProps
    } = props;
    const absoluteFrame = useTimelinePosition();
    const volumePropFrame = useFrameForVolumeProp(loopVolumeCurveBehavior ?? "repeat");
    const frame = useCurrentFrame();
    const sequenceContext = (0, import_react49.useContext)(SequenceContext);
    const { registerRenderAsset, unregisterRenderAsset } = (0, import_react49.useContext)(RenderAssetManager);
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    const id = (0, import_react49.useMemo)(() => `audio-${random(props.src ?? "")}-${sequenceContext?.relativeFrom}-${sequenceContext?.cumulatedFrom}-${sequenceContext?.durationInFrames}`, [
      props.src,
      sequenceContext?.relativeFrom,
      sequenceContext?.cumulatedFrom,
      sequenceContext?.durationInFrames
    ]);
    const volume = evaluateVolume({
      volume: volumeProp,
      frame: volumePropFrame,
      mediaVolume: 1
    });
    warnAboutTooHighVolume(volume);
    (0, import_react49.useImperativeHandle)(ref, () => {
      return audioRef.current;
    }, []);
    (0, import_react49.useEffect)(() => {
      if (!props.src) {
        throw new Error("No src passed");
      }
      if (!window.remotion_audioEnabled) {
        return;
      }
      if (props.muted) {
        return;
      }
      if (volume <= 0) {
        return;
      }
      registerRenderAsset({
        type: "audio",
        src: getAbsoluteSrc(props.src),
        id,
        frame: absoluteFrame,
        volume,
        mediaFrame: frame,
        playbackRate: props.playbackRate ?? 1,
        toneFrequency: toneFrequency ?? 1,
        audioStartFrame: Math.max(0, -(sequenceContext?.relativeFrom ?? 0)),
        audioStreamIndex: audioStreamIndex ?? 0
      });
      return () => unregisterRenderAsset(id);
    }, [
      props.muted,
      props.src,
      registerRenderAsset,
      absoluteFrame,
      id,
      unregisterRenderAsset,
      volume,
      volumePropFrame,
      frame,
      playbackRate,
      props.playbackRate,
      toneFrequency,
      sequenceContext?.relativeFrom,
      audioStreamIndex
    ]);
    const { src } = props;
    const needsToRenderAudioTag = ref || _remotionInternalNeedsDurationCalculation;
    (0, import_react49.useLayoutEffect)(() => {
      if (window.process?.env?.NODE_ENV === "test") {
        return;
      }
      if (!needsToRenderAudioTag) {
        return;
      }
      const newHandle = delayRender2("Loading <Html5Audio> duration with src=" + src, {
        retries: delayRenderRetries ?? void 0,
        timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
      });
      const { current } = audioRef;
      const didLoad = () => {
        if (current?.duration) {
          onDuration(current.src, current.duration);
        }
        continueRender2(newHandle);
      };
      if (current?.duration) {
        onDuration(current.src, current.duration);
        continueRender2(newHandle);
      } else {
        current?.addEventListener("loadedmetadata", didLoad, { once: true });
      }
      return () => {
        current?.removeEventListener("loadedmetadata", didLoad);
        continueRender2(newHandle);
      };
    }, [
      src,
      onDuration,
      needsToRenderAudioTag,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      continueRender2,
      delayRender2
    ]);
    if (!needsToRenderAudioTag) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime19.jsx)("audio", {
      ref: audioRef,
      ...nativeProps,
      onError: onNativeError
    });
  };
  var AudioForRendering = (0, import_react49.forwardRef)(AudioForRenderingRefForwardingFunction);
  var AudioRefForwardingFunction = (props, ref) => {
    const audioContext = (0, import_react28.useContext)(SharedAudioContext);
    const {
      startFrom,
      endAt,
      trimBefore,
      trimAfter,
      name,
      stack,
      pauseWhenBuffering,
      showInTimeline,
      onError: onRemotionError,
      ...otherProps
    } = props;
    const { loop, ...propsOtherThanLoop } = props;
    const { fps } = useVideoConfig();
    const environment = useRemotionEnvironment();
    if (environment.isClientSideRendering) {
      throw new Error("<Html5Audio> is not supported in @remotion/web-renderer. Use <Audio> from @remotion/media instead. See https://remotion.dev/docs/client-side-rendering/limitations");
    }
    const { durations, setDurations } = (0, import_react28.useContext)(DurationsContext);
    if (typeof props.src !== "string") {
      throw new TypeError(`The \`<Html5Audio>\` tag requires a string for \`src\`, but got ${JSON.stringify(props.src)} instead.`);
    }
    const preloadedSrc = usePreload(props.src);
    const onError = (0, import_react28.useCallback)((e) => {
      console.log(e.currentTarget.error);
      const errMessage = `Could not play audio with src ${preloadedSrc}: ${e.currentTarget.error}. See https://remotion.dev/docs/media-playback-error for help.`;
      if (loop) {
        if (onRemotionError) {
          onRemotionError(new Error(errMessage));
          return;
        }
        cancelRender(new Error(errMessage));
      } else {
        onRemotionError?.(new Error(errMessage));
        console.warn(errMessage);
      }
    }, [loop, onRemotionError, preloadedSrc]);
    const onDuration = (0, import_react28.useCallback)((src, durationInSeconds) => {
      setDurations({ type: "got-duration", durationInSeconds, src });
    }, [setDurations]);
    const durationFetched = durations[getAbsoluteSrc(preloadedSrc)] ?? durations[getAbsoluteSrc(props.src)];
    validateMediaTrimProps({ startFrom, endAt, trimBefore, trimAfter });
    const { trimBeforeValue, trimAfterValue } = resolveTrimProps({
      startFrom,
      endAt,
      trimBefore,
      trimAfter
    });
    if (loop && durationFetched !== void 0) {
      if (!Number.isFinite(durationFetched)) {
        return /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Html5Audio, {
          ...propsOtherThanLoop,
          ref,
          _remotionInternalNativeLoopPassed: true
        });
      }
      const duration = durationFetched * fps;
      return /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Loop, {
        layout: "none",
        durationInFrames: calculateMediaDuration({
          trimAfter: trimAfterValue,
          mediaDurationInFrames: duration,
          playbackRate: props.playbackRate ?? 1,
          trimBefore: trimBeforeValue
        }),
        children: /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Html5Audio, {
          ...propsOtherThanLoop,
          ref,
          _remotionInternalNativeLoopPassed: true
        })
      });
    }
    if (typeof trimBeforeValue !== "undefined" || typeof trimAfterValue !== "undefined") {
      return /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Sequence, {
        layout: "none",
        from: 0 - (trimBeforeValue ?? 0),
        showInTimeline: false,
        durationInFrames: trimAfterValue,
        name,
        children: /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(Html5Audio, {
          _remotionInternalNeedsDurationCalculation: Boolean(loop),
          pauseWhenBuffering: pauseWhenBuffering ?? false,
          ...otherProps,
          ref
        })
      });
    }
    validateMediaProps({ playbackRate: props.playbackRate, volume: props.volume }, "Html5Audio");
    if (environment.isRendering) {
      return /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(AudioForRendering, {
        onDuration,
        ...props,
        ref,
        onNativeError: onError,
        _remotionInternalNeedsDurationCalculation: Boolean(loop)
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime20.jsx)(AudioForPreview, {
      _remotionInternalNativeLoopPassed: props._remotionInternalNativeLoopPassed ?? false,
      _remotionInternalStack: stack ?? null,
      shouldPreMountAudioTags: audioContext !== null && audioContext.numberOfAudioTags > 0,
      ...props,
      ref,
      onNativeError: onError,
      onDuration,
      pauseWhenBuffering: pauseWhenBuffering ?? false,
      _remotionInternalNeedsDurationCalculation: Boolean(loop),
      showInTimeline: showInTimeline ?? true
    });
  };
  var Html5Audio = (0, import_react28.forwardRef)(AudioRefForwardingFunction);
  addSequenceStackTraces(Html5Audio);
  var getRegex = () => /^([a-zA-Z0-9-\u4E00-\u9FFF])+$/g;
  var invalidFolderNameErrorMessage = `Folder name must match ${String(getRegex())}`;
  var FolderContext = (0, import_react51.createContext)({
    folderName: null,
    parentName: null
  });
  var rotate = {
    transform: `rotate(90deg)`
  };
  var ICON_SIZE = 40;
  var label = {
    color: "white",
    fontSize: 14,
    fontFamily: "sans-serif"
  };
  var container = {
    justifyContent: "center",
    alignItems: "center"
  };
  var Loading = () => {
    return /* @__PURE__ */ (0, import_jsx_runtime22.jsxs)(AbsoluteFill, {
      style: container,
      id: "remotion-comp-loading",
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime22.jsx)("style", {
          type: "text/css",
          children: `
				@keyframes anim {
					from {
						opacity: 0
					}
					to {
						opacity: 1
					}
				}
				#remotion-comp-loading {
					animation: anim 2s;
					animation-fill-mode: forwards;
				}
			`
        }),
        /* @__PURE__ */ (0, import_jsx_runtime22.jsx)("svg", {
          width: ICON_SIZE,
          height: ICON_SIZE,
          viewBox: "-100 -100 400 400",
          style: rotate,
          children: /* @__PURE__ */ (0, import_jsx_runtime22.jsx)("path", {
            fill: "#555",
            stroke: "#555",
            strokeWidth: "100",
            strokeLinejoin: "round",
            d: "M 2 172 a 196 100 0 0 0 195 5 A 196 240 0 0 0 100 2.259 A 196 240 0 0 0 2 172 z"
          })
        }),
        /* @__PURE__ */ (0, import_jsx_runtime22.jsxs)("p", {
          style: label,
          children: [
            "Resolving ",
            "<Suspense>",
            "..."
          ]
        })
      ]
    });
  };
  var _portalNode = null;
  var portalNode = () => {
    if (!_portalNode) {
      if (typeof document === "undefined") {
        throw new Error("Tried to call an API that only works in the browser from outside the browser");
      }
      _portalNode = document.createElement("div");
      _portalNode.style.position = "absolute";
      _portalNode.style.top = "0px";
      _portalNode.style.left = "0px";
      _portalNode.style.right = "0px";
      _portalNode.style.bottom = "0px";
      _portalNode.style.width = "100%";
      _portalNode.style.height = "100%";
      _portalNode.style.display = "flex";
      _portalNode.style.flexDirection = "column";
      const containerNode = document.createElement("div");
      containerNode.style.position = "fixed";
      containerNode.style.top = "-999999px";
      containerNode.appendChild(_portalNode);
      document.body.appendChild(containerNode);
    }
    return _portalNode;
  };
  var useLazyComponent = ({
    compProps,
    componentName,
    noSuspense
  }) => {
    const lazy = (0, import_react52.useMemo)(() => {
      if ("component" in compProps) {
        if (typeof document === "undefined" || noSuspense) {
          return compProps.component;
        }
        if (typeof compProps.component === "undefined") {
          throw new Error(`A value of \`undefined\` was passed to the \`component\` prop. Check the value you are passing to the <${componentName}/> component.`);
        }
        return compProps.component;
      }
      if ("lazyComponent" in compProps && typeof compProps.lazyComponent !== "undefined") {
        if (typeof compProps.lazyComponent === "undefined") {
          throw new Error(`A value of \`undefined\` was passed to the \`lazyComponent\` prop. Check the value you are passing to the <${componentName}/> component.`);
        }
        return import_react52.default.lazy(compProps.lazyComponent);
      }
      throw new Error("You must pass either 'component' or 'lazyComponent'");
    }, [compProps.component, compProps.lazyComponent]);
    return lazy;
  };
  var getRegex2 = () => /^([a-zA-Z0-9-\u4E00-\u9FFF])+$/g;
  var isCompositionIdValid = (id) => id.match(getRegex2());
  var validateCompositionId = (id) => {
    if (!isCompositionIdValid(id)) {
      throw new Error(`Composition id can only contain a-z, A-Z, 0-9, CJK characters and -. You passed ${id}`);
    }
  };
  var invalidCompositionErrorMessage = `Composition ID must match ${String(getRegex2())}`;
  var validateDefaultAndInputProps = (defaultProps, name, compositionId) => {
    if (!defaultProps) {
      return;
    }
    if (typeof defaultProps !== "object") {
      throw new Error(`"${name}" must be an object, but you passed a value of type ${typeof defaultProps}`);
    }
    if (Array.isArray(defaultProps)) {
      throw new Error(`"${name}" must be an object, an array was passed ${compositionId ? `for composition "${compositionId}"` : ""}`);
    }
  };
  var Fallback = () => {
    const { continueRender: continueRender2, delayRender: delayRender2 } = useDelayRender();
    (0, import_react50.useEffect)(() => {
      const fallback = delayRender2("Waiting for Root component to unsuspend");
      return () => continueRender2(fallback);
    }, [continueRender2, delayRender2]);
    return null;
  };
  var InnerComposition = ({
    width,
    height,
    fps,
    durationInFrames,
    id,
    defaultProps,
    schema,
    ...compProps
  }) => {
    const compManager = (0, import_react50.useContext)(CompositionSetters);
    const { registerComposition, unregisterComposition } = compManager;
    const video = useVideo();
    const lazy = useLazyComponent({
      compProps,
      componentName: "Composition",
      noSuspense: false
    });
    const nonce = useNonce();
    const isPlayer = useIsPlayer();
    const environment = useRemotionEnvironment();
    const canUseComposition = (0, import_react50.useContext)(CanUseRemotionHooks);
    if (typeof window !== "undefined") {
      window.remotion_seenCompositionIds = Array.from(/* @__PURE__ */ new Set([...window.remotion_seenCompositionIds ?? [], id]));
    }
    if (canUseComposition) {
      if (isPlayer) {
        throw new Error("<Composition> was mounted inside the `component` that was passed to the <Player>. See https://remotion.dev/docs/wrong-composition-mount for help.");
      }
      throw new Error("<Composition> mounted inside another composition. See https://remotion.dev/docs/wrong-composition-mount for help.");
    }
    const { folderName, parentName } = (0, import_react50.useContext)(FolderContext);
    (0, import_react50.useEffect)(() => {
      if (!id) {
        throw new Error("No id for composition passed.");
      }
      validateCompositionId(id);
      validateDefaultAndInputProps(defaultProps, "defaultProps", id);
      registerComposition({
        durationInFrames: durationInFrames ?? void 0,
        fps: fps ?? void 0,
        height: height ?? void 0,
        width: width ?? void 0,
        id,
        folderName,
        component: lazy,
        defaultProps: serializeThenDeserializeInStudio(defaultProps ?? {}),
        nonce,
        parentFolderName: parentName,
        schema: schema ?? null,
        calculateMetadata: compProps.calculateMetadata ?? null
      });
      return () => {
        unregisterComposition(id);
      };
    }, [
      durationInFrames,
      fps,
      height,
      lazy,
      id,
      folderName,
      defaultProps,
      width,
      nonce,
      parentName,
      schema,
      compProps.calculateMetadata,
      registerComposition,
      unregisterComposition
    ]);
    (0, import_react50.useEffect)(() => {
      window.dispatchEvent(new CustomEvent(PROPS_UPDATED_EXTERNALLY, {
        detail: {
          resetUnsaved: id
        }
      }));
    }, [defaultProps, id]);
    const resolved = useResolvedVideoConfig(id);
    if (environment.isStudio && video && video.component === lazy && video.id === id) {
      const Comp = lazy;
      if (resolved === null || resolved.type !== "success" && resolved.type !== "success-and-refreshing") {
        return null;
      }
      return (0, import_react_dom.createPortal)(/* @__PURE__ */ (0, import_jsx_runtime23.jsx)(CanUseRemotionHooksProvider, {
        children: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(import_react50.Suspense, {
          fallback: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(Loading, {}),
          children: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(Comp, {
            ...resolved.result.props ?? {}
          })
        })
      }), portalNode());
    }
    if (environment.isRendering && video && video.component === lazy && video.id === id) {
      const Comp = lazy;
      if (resolved === null || resolved.type !== "success" && resolved.type !== "success-and-refreshing") {
        return null;
      }
      return (0, import_react_dom.createPortal)(/* @__PURE__ */ (0, import_jsx_runtime23.jsx)(CanUseRemotionHooksProvider, {
        children: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(import_react50.Suspense, {
          fallback: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(Fallback, {}),
          children: /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(Comp, {
            ...resolved.result.props ?? {}
          })
        })
      }), portalNode());
    }
    return null;
  };
  var Composition = (props2) => {
    const { onlyRenderComposition } = (0, import_react50.useContext)(CompositionSetters);
    if (onlyRenderComposition && onlyRenderComposition !== props2.id) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime23.jsx)(InnerComposition, {
      ...props2
    });
  };
  var NEWTON_ITERATIONS = 4;
  var NEWTON_MIN_SLOPE = 1e-3;
  var SUBDIVISION_PRECISION = 1e-7;
  var SUBDIVISION_MAX_ITERATIONS = 10;
  var kSplineTableSize = 11;
  var kSampleStepSize = 1 / (kSplineTableSize - 1);
  var float32ArraySupported = typeof Float32Array === "function";
  function a(aA1, aA2) {
    return 1 - 3 * aA2 + 3 * aA1;
  }
  function b(aA1, aA2) {
    return 3 * aA2 - 6 * aA1;
  }
  function c(aA1) {
    return 3 * aA1;
  }
  function calcBezier(aT, aA1, aA2) {
    return ((a(aA1, aA2) * aT + b(aA1, aA2)) * aT + c(aA1)) * aT;
  }
  function getSlope(aT, aA1, aA2) {
    return 3 * a(aA1, aA2) * aT * aT + 2 * b(aA1, aA2) * aT + c(aA1);
  }
  function binarySubdivide({
    aX,
    _aA,
    _aB,
    mX1,
    mX2
  }) {
    let currentX;
    let currentT;
    let i = 0;
    let aA = _aA;
    let aB = _aB;
    do {
      currentT = aA + (aB - aA) / 2;
      currentX = calcBezier(currentT, mX1, mX2) - aX;
      if (currentX > 0) {
        aB = currentT;
      } else {
        aA = currentT;
      }
    } while (Math.abs(currentX) > SUBDIVISION_PRECISION && ++i < SUBDIVISION_MAX_ITERATIONS);
    return currentT;
  }
  function newtonRaphsonIterate(aX, _aGuessT, mX1, mX2) {
    let aGuessT = _aGuessT;
    for (let i = 0; i < NEWTON_ITERATIONS; ++i) {
      const currentSlope = getSlope(aGuessT, mX1, mX2);
      if (currentSlope === 0) {
        return aGuessT;
      }
      const currentX = calcBezier(aGuessT, mX1, mX2) - aX;
      aGuessT -= currentX / currentSlope;
    }
    return aGuessT;
  }
  function bezier(mX1, mY1, mX2, mY2) {
    if (!(mX1 >= 0 && mX1 <= 1 && mX2 >= 0 && mX2 <= 1)) {
      throw new Error("bezier x values must be in [0, 1] range");
    }
    const sampleValues = float32ArraySupported ? new Float32Array(kSplineTableSize) : new Array(kSplineTableSize);
    if (mX1 !== mY1 || mX2 !== mY2) {
      for (let i = 0; i < kSplineTableSize; ++i) {
        sampleValues[i] = calcBezier(i * kSampleStepSize, mX1, mX2);
      }
    }
    function getTForX(aX) {
      let intervalStart = 0;
      let currentSample = 1;
      const lastSample = kSplineTableSize - 1;
      for (; currentSample !== lastSample && sampleValues[currentSample] <= aX; ++currentSample) {
        intervalStart += kSampleStepSize;
      }
      --currentSample;
      const dist = (aX - sampleValues[currentSample]) / (sampleValues[currentSample + 1] - sampleValues[currentSample]);
      const guessForT = intervalStart + dist * kSampleStepSize;
      const initialSlope = getSlope(guessForT, mX1, mX2);
      if (initialSlope >= NEWTON_MIN_SLOPE) {
        return newtonRaphsonIterate(aX, guessForT, mX1, mX2);
      }
      if (initialSlope === 0) {
        return guessForT;
      }
      return binarySubdivide({
        aX,
        _aA: intervalStart,
        _aB: intervalStart + kSampleStepSize,
        mX1,
        mX2
      });
    }
    return function(x) {
      if (mX1 === mY1 && mX2 === mY2) {
        return x;
      }
      if (x === 0) {
        return 0;
      }
      if (x === 1) {
        return 1;
      }
      return calcBezier(getTForX(x), mY1, mY2);
    };
  }
  var Easing = class _Easing {
    static step0(n) {
      return n > 0 ? 1 : 0;
    }
    static step1(n) {
      return n >= 1 ? 1 : 0;
    }
    static linear(t) {
      return t;
    }
    static ease(t) {
      return _Easing.bezier(0.42, 0, 1, 1)(t);
    }
    static quad(t) {
      return t * t;
    }
    static cubic(t) {
      return t * t * t;
    }
    static poly(n) {
      return (t) => t ** n;
    }
    static sin(t) {
      return 1 - Math.cos(t * Math.PI / 2);
    }
    static circle(t) {
      return 1 - Math.sqrt(1 - t * t);
    }
    static exp(t) {
      return 2 ** (10 * (t - 1));
    }
    static elastic(bounciness = 1) {
      const p = bounciness * Math.PI;
      return (t) => 1 - Math.cos(t * Math.PI / 2) ** 3 * Math.cos(t * p);
    }
    static back(s = 1.70158) {
      return (t) => t * t * ((s + 1) * t - s);
    }
    static bounce(t) {
      if (t < 1 / 2.75) {
        return 7.5625 * t * t;
      }
      if (t < 2 / 2.75) {
        const t2_ = t - 1.5 / 2.75;
        return 7.5625 * t2_ * t2_ + 0.75;
      }
      if (t < 2.5 / 2.75) {
        const t2_ = t - 2.25 / 2.75;
        return 7.5625 * t2_ * t2_ + 0.9375;
      }
      const t2 = t - 2.625 / 2.75;
      return 7.5625 * t2 * t2 + 0.984375;
    }
    static bezier(x1, y1, x2, y2) {
      return bezier(x1, y1, x2, y2);
    }
    static in(easing) {
      return easing;
    }
    static out(easing) {
      return (t) => 1 - easing(1 - t);
    }
    static inOut(easing) {
      return (t) => {
        if (t < 0.5) {
          return easing(t * 2) / 2;
        }
        return 1 - easing((1 - t) * 2) / 2;
      };
    }
  };
  var ENABLE_V5_BREAKING_CHANGES = false;
  var IFrameRefForwarding = ({
    onLoad,
    onError,
    delayRenderRetries,
    delayRenderTimeoutInMilliseconds,
    ...props2
  }, ref) => {
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    const [handle] = (0, import_react53.useState)(() => delayRender2(`Loading <IFrame> with source ${props2.src}`, {
      retries: delayRenderRetries ?? void 0,
      timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
    }));
    const didLoad = (0, import_react53.useCallback)((e) => {
      continueRender2(handle);
      onLoad?.(e);
    }, [handle, onLoad, continueRender2]);
    const didGetError = (0, import_react53.useCallback)((e) => {
      continueRender2(handle);
      if (onError) {
        onError(e);
      } else {
        console.error("Error loading iframe:", e, "Handle the event using the onError() prop to make this message disappear.");
      }
    }, [handle, onError, continueRender2]);
    return /* @__PURE__ */ (0, import_jsx_runtime24.jsx)("iframe", {
      referrerPolicy: "strict-origin-when-cross-origin",
      ...props2,
      ref,
      onError: didGetError,
      onLoad: didLoad
    });
  };
  var IFrame = (0, import_react53.forwardRef)(IFrameRefForwarding);
  function exponentialBackoff(errorCount) {
    return 1e3 * 2 ** (errorCount - 1);
  }
  var ImgRefForwarding = ({
    onError,
    maxRetries = 2,
    src,
    pauseWhenLoading,
    delayRenderRetries,
    delayRenderTimeoutInMilliseconds,
    onImageFrame,
    crossOrigin,
    ...props2
  }, ref) => {
    const imageRef = (0, import_react54.useRef)(null);
    const errors = (0, import_react54.useRef)({});
    const { delayPlayback } = useBufferState();
    const sequenceContext = (0, import_react54.useContext)(SequenceContext);
    if (!src) {
      throw new Error('No "src" prop was passed to <Img>.');
    }
    const _propsValid = true;
    if (!_propsValid) {
      throw new Error("typecheck error");
    }
    (0, import_react54.useImperativeHandle)(ref, () => {
      return imageRef.current;
    }, []);
    const actualSrc = usePreload(src);
    const retryIn = (0, import_react54.useCallback)((timeout) => {
      if (!imageRef.current) {
        return;
      }
      const currentSrc = imageRef.current.src;
      setTimeout(() => {
        if (!imageRef.current) {
          return;
        }
        const newSrc = imageRef.current?.src;
        if (newSrc !== currentSrc) {
          return;
        }
        imageRef.current.removeAttribute("src");
        imageRef.current.setAttribute("src", newSrc);
      }, timeout);
    }, []);
    const didGetError = (0, import_react54.useCallback)((e) => {
      if (!errors.current) {
        return;
      }
      errors.current[imageRef.current?.src] = (errors.current[imageRef.current?.src] ?? 0) + 1;
      if (onError && (errors.current[imageRef.current?.src] ?? 0) > maxRetries) {
        onError(e);
        return;
      }
      if ((errors.current[imageRef.current?.src] ?? 0) <= maxRetries) {
        const backoff = exponentialBackoff(errors.current[imageRef.current?.src] ?? 0);
        console.warn(`Could not load image with source ${imageRef.current?.src}, retrying again in ${backoff}ms`);
        retryIn(backoff);
        return;
      }
      cancelRender("Error loading image with src: " + imageRef.current?.src);
    }, [maxRetries, onError, retryIn]);
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    if (typeof window !== "undefined") {
      const isPremounting = Boolean(sequenceContext?.premounting);
      const isPostmounting = Boolean(sequenceContext?.postmounting);
      (0, import_react54.useLayoutEffect)(() => {
        if (window.process?.env?.NODE_ENV === "test") {
          if (imageRef.current) {
            imageRef.current.src = actualSrc;
          }
          return;
        }
        const { current } = imageRef;
        if (!current) {
          return;
        }
        const newHandle = delayRender2("Loading <Img> with src=" + actualSrc, {
          retries: delayRenderRetries ?? void 0,
          timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
        });
        const unblock = pauseWhenLoading && !isPremounting && !isPostmounting ? delayPlayback().unblock : () => {
          return;
        };
        let unmounted = false;
        const onComplete = () => {
          if (unmounted) {
            continueRender2(newHandle);
            return;
          }
          if ((errors.current[imageRef.current?.src] ?? 0) > 0) {
            delete errors.current[imageRef.current?.src];
            console.info(`Retry successful - ${imageRef.current?.src} is now loaded`);
          }
          if (current) {
            onImageFrame?.(current);
          }
          unblock();
          continueRender2(newHandle);
        };
        if (!imageRef.current) {
          onComplete();
          return;
        }
        current.src = actualSrc;
        current.decode().then(onComplete).catch((err) => {
          console.warn(err);
          if (current.complete) {
            onComplete();
          } else {
            current.addEventListener("load", onComplete);
          }
        });
        return () => {
          unmounted = true;
          current.removeEventListener("load", onComplete);
          unblock();
          continueRender2(newHandle);
        };
      }, [
        actualSrc,
        delayPlayback,
        delayRenderRetries,
        delayRenderTimeoutInMilliseconds,
        pauseWhenLoading,
        isPremounting,
        isPostmounting,
        onImageFrame,
        continueRender2,
        delayRender2
      ]);
    }
    const { isClientSideRendering } = useRemotionEnvironment();
    const crossOriginValue = getCrossOriginValue({
      crossOrigin,
      requestsVideoFrame: false,
      isClientSideRendering
    });
    return /* @__PURE__ */ (0, import_jsx_runtime25.jsx)("img", {
      ...props2,
      ref: imageRef,
      crossOrigin: crossOriginValue,
      onError: didGetError,
      decoding: "sync"
    });
  };
  var Img = (0, import_react54.forwardRef)(ImgRefForwarding);
  var compositionsRef = import_react56.default.createRef();
  var CompositionManagerProvider = ({
    children,
    onlyRenderComposition,
    currentCompositionMetadata,
    initialCompositions,
    initialCanvasContent
  }) => {
    const [folders, setFolders] = (0, import_react57.useState)([]);
    const [canvasContent, setCanvasContent] = (0, import_react57.useState)(initialCanvasContent);
    const [compositions, setCompositions] = (0, import_react57.useState)(initialCompositions);
    const currentcompositionsRef = (0, import_react57.useRef)(compositions);
    const updateCompositions = (0, import_react57.useCallback)((updateComps) => {
      setCompositions((comps) => {
        const updated = updateComps(comps);
        currentcompositionsRef.current = updated;
        return updated;
      });
    }, []);
    const registerComposition = (0, import_react57.useCallback)((comp) => {
      updateCompositions((comps) => {
        if (comps.find((c2) => c2.id === comp.id)) {
          throw new Error(`Multiple composition with id ${comp.id} are registered.`);
        }
        const value = [...comps, comp].slice().sort((a2, b2) => a2.nonce - b2.nonce);
        return value;
      });
    }, [updateCompositions]);
    const unregisterComposition = (0, import_react57.useCallback)((id) => {
      setCompositions((comps) => {
        return comps.filter((c2) => c2.id !== id);
      });
    }, []);
    const registerFolder = (0, import_react57.useCallback)((name, parent) => {
      setFolders((prevFolders) => {
        return [
          ...prevFolders,
          {
            name,
            parent
          }
        ];
      });
    }, []);
    const unregisterFolder = (0, import_react57.useCallback)((name, parent) => {
      setFolders((prevFolders) => {
        return prevFolders.filter((p) => !(p.name === name && p.parent === parent));
      });
    }, []);
    (0, import_react57.useImperativeHandle)(compositionsRef, () => {
      return {
        getCompositions: () => currentcompositionsRef.current
      };
    }, []);
    const updateCompositionDefaultProps = (0, import_react57.useCallback)((id, newDefaultProps) => {
      setCompositions((comps) => {
        const updated = comps.map((c2) => {
          if (c2.id === id) {
            return {
              ...c2,
              defaultProps: newDefaultProps
            };
          }
          return c2;
        });
        return updated;
      });
    }, []);
    const compositionManagerSetters = (0, import_react57.useMemo)(() => {
      return {
        registerComposition,
        unregisterComposition,
        registerFolder,
        unregisterFolder,
        setCanvasContent,
        updateCompositionDefaultProps,
        onlyRenderComposition
      };
    }, [
      registerComposition,
      registerFolder,
      unregisterComposition,
      unregisterFolder,
      updateCompositionDefaultProps,
      onlyRenderComposition
    ]);
    const compositionManagerContextValue = (0, import_react57.useMemo)(() => {
      return {
        compositions,
        folders,
        currentCompositionMetadata,
        canvasContent
      };
    }, [compositions, folders, currentCompositionMetadata, canvasContent]);
    return /* @__PURE__ */ (0, import_jsx_runtime26.jsx)(CompositionManager.Provider, {
      value: compositionManagerContextValue,
      children: /* @__PURE__ */ (0, import_jsx_runtime26.jsx)(CompositionSetters.Provider, {
        value: compositionManagerSetters,
        children
      })
    });
  };
  var exports_default_css = {};
  __export(exports_default_css, {
    makeDefaultPreviewCSS: () => makeDefaultPreviewCSS,
    injectCSS: () => injectCSS,
    OBJECTFIT_CONTAIN_CLASS_NAME: () => OBJECTFIT_CONTAIN_CLASS_NAME
  });
  var injected = {};
  var injectCSS = (css) => {
    if (typeof document === "undefined") {
      return () => {
      };
    }
    if (injected[css]) {
      return () => {
      };
    }
    const head = document.head || document.getElementsByTagName("head")[0];
    const style2 = document.createElement("style");
    style2.appendChild(document.createTextNode(css));
    head.prepend(style2);
    injected[css] = style2;
    return () => {
      const styleElement = injected[css];
      if (styleElement) {
        if (styleElement.parentNode) {
          styleElement.parentNode.removeChild(styleElement);
        }
        delete injected[css];
      }
    };
  };
  var OBJECTFIT_CONTAIN_CLASS_NAME = "__remotion_objectfitcontain";
  var makeDefaultPreviewCSS = (scope, backgroundColor) => {
    if (!scope) {
      return `
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
	    background-color: ${backgroundColor};
    }
    .${OBJECTFIT_CONTAIN_CLASS_NAME} {
      object-fit: contain;
    }
    `;
    }
    return `
    ${scope} * {
      box-sizing: border-box;
    }
    ${scope} *:-webkit-full-screen {
      width: 100%;
      height: 100%;
    }
    ${scope} .${OBJECTFIT_CONTAIN_CLASS_NAME} {
      object-fit: contain;
    }
  `;
  };
  var REMOTION_STUDIO_CONTAINER_ELEMENT = "__remotion-studio-container";
  var getPreviewDomElement = () => {
    return document.getElementById(REMOTION_STUDIO_CONTAINER_ELEMENT);
  };
  var MaxMediaCacheSizeContext = import_react58.default.createContext(null);
  var Root = null;
  var listeners = [];
  var getRoot = () => {
    return Root;
  };
  var waitForRoot = (fn) => {
    if (Root) {
      fn(Root);
      return () => {
        return;
      };
    }
    listeners.push(fn);
    return () => {
      listeners = listeners.filter((l) => l !== fn);
    };
  };
  var MediaEnabledContext = (0, import_react60.createContext)(null);
  var useVideoEnabled = () => {
    const context = (0, import_react60.useContext)(MediaEnabledContext);
    if (!context) {
      return window.remotion_videoEnabled;
    }
    if (context.videoEnabled === null) {
      return window.remotion_videoEnabled;
    }
    return context.videoEnabled;
  };
  var useAudioEnabled = () => {
    const context = (0, import_react60.useContext)(MediaEnabledContext);
    if (!context) {
      return window.remotion_audioEnabled;
    }
    if (context.audioEnabled === null) {
      return window.remotion_audioEnabled;
    }
    return context.audioEnabled;
  };
  var MediaEnabledProvider = ({
    children,
    videoEnabled,
    audioEnabled
  }) => {
    const value = (0, import_react60.useMemo)(() => ({ videoEnabled, audioEnabled }), [videoEnabled, audioEnabled]);
    return /* @__PURE__ */ (0, import_jsx_runtime27.jsx)(MediaEnabledContext.Provider, {
      value,
      children
    });
  };
  var RemotionRootContexts = ({
    children,
    numberOfAudioTags,
    logLevel,
    audioLatencyHint,
    videoEnabled,
    audioEnabled,
    frameState,
    nonceContextSeed
  }) => {
    const nonceContext = (0, import_react59.useMemo)(() => {
      let counter = 0;
      return {
        getNonce: () => counter++
      };
    }, [nonceContextSeed]);
    const logging = (0, import_react59.useMemo)(() => {
      return { logLevel, mountTime: Date.now() };
    }, [logLevel]);
    return /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(LogLevelContext.Provider, {
      value: logging,
      children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(NonceContext.Provider, {
        value: nonceContext,
        children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(TimelineContextProvider, {
          frameState,
          children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(MediaEnabledProvider, {
            videoEnabled,
            audioEnabled,
            children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(EditorPropsProvider, {
              children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(PrefetchProvider, {
                children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(SequenceManagerProvider, {
                  children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(SharedAudioContextProvider, {
                    numberOfAudioTags,
                    audioLatencyHint,
                    audioEnabled,
                    children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(DurationsContextProvider, {
                      children: /* @__PURE__ */ (0, import_jsx_runtime28.jsx)(BufferingProvider, {
                        children
                      })
                    })
                  })
                })
              })
            })
          })
        })
      })
    });
  };
  var validCodecs = [
    "h264",
    "h265",
    "vp8",
    "vp9",
    "mp3",
    "aac",
    "wav",
    "prores",
    "h264-mkv",
    "h264-ts",
    "gif"
  ];
  function validateCodec(defaultCodec, location, name) {
    if (typeof defaultCodec === "undefined") {
      return;
    }
    if (typeof defaultCodec !== "string") {
      throw new TypeError(`The "${name}" prop ${location} must be a string, but you passed a value of type ${typeof defaultCodec}.`);
    }
    if (!validCodecs.includes(defaultCodec)) {
      throw new Error(`The "${name}" prop ${location} must be one of ${validCodecs.join(", ")}, but you passed ${defaultCodec}.`);
    }
  }
  var validateCalculated = ({
    calculated,
    compositionId,
    compositionFps,
    compositionHeight,
    compositionWidth,
    compositionDurationInFrames
  }) => {
    const calculateMetadataErrorLocation = `calculated by calculateMetadata() for the composition "${compositionId}"`;
    const defaultErrorLocation = `of the "<Composition />" component with the id "${compositionId}"`;
    const width = calculated?.width ?? compositionWidth ?? void 0;
    validateDimension(width, "width", calculated?.width ? calculateMetadataErrorLocation : defaultErrorLocation);
    const height = calculated?.height ?? compositionHeight ?? void 0;
    validateDimension(height, "height", calculated?.height ? calculateMetadataErrorLocation : defaultErrorLocation);
    const fps = calculated?.fps ?? compositionFps ?? null;
    validateFps(fps, calculated?.fps ? calculateMetadataErrorLocation : defaultErrorLocation, false);
    const durationInFrames = calculated?.durationInFrames ?? compositionDurationInFrames ?? null;
    validateDurationInFrames(durationInFrames, {
      allowFloats: false,
      component: `of the "<Composition />" component with the id "${compositionId}"`
    });
    const defaultCodec = calculated?.defaultCodec;
    validateCodec(defaultCodec, calculateMetadataErrorLocation, "defaultCodec");
    const defaultOutName = calculated?.defaultOutName;
    const defaultVideoImageFormat = calculated?.defaultVideoImageFormat;
    const defaultPixelFormat = calculated?.defaultPixelFormat;
    const defaultProResProfile = calculated?.defaultProResProfile;
    return {
      width,
      height,
      fps,
      durationInFrames,
      defaultCodec,
      defaultOutName,
      defaultVideoImageFormat,
      defaultPixelFormat,
      defaultProResProfile
    };
  };
  var resolveVideoConfig = ({
    calculateMetadata,
    signal,
    defaultProps,
    inputProps: originalProps,
    compositionId,
    compositionDurationInFrames,
    compositionFps,
    compositionHeight,
    compositionWidth
  }) => {
    const calculatedProm = calculateMetadata ? calculateMetadata({
      defaultProps,
      props: originalProps,
      abortSignal: signal,
      compositionId,
      isRendering: getRemotionEnvironment().isRendering
    }) : null;
    if (calculatedProm !== null && typeof calculatedProm === "object" && "then" in calculatedProm) {
      return calculatedProm.then((c2) => {
        const {
          height,
          width,
          durationInFrames,
          fps,
          defaultCodec,
          defaultOutName,
          defaultVideoImageFormat,
          defaultPixelFormat,
          defaultProResProfile
        } = validateCalculated({
          calculated: c2,
          compositionDurationInFrames,
          compositionFps,
          compositionHeight,
          compositionWidth,
          compositionId
        });
        return {
          width,
          height,
          fps,
          durationInFrames,
          id: compositionId,
          defaultProps: serializeThenDeserializeInStudio(defaultProps),
          props: serializeThenDeserializeInStudio(c2.props ?? originalProps),
          defaultCodec: defaultCodec ?? null,
          defaultOutName: defaultOutName ?? null,
          defaultVideoImageFormat: defaultVideoImageFormat ?? null,
          defaultPixelFormat: defaultPixelFormat ?? null,
          defaultProResProfile: defaultProResProfile ?? null
        };
      });
    }
    const data = validateCalculated({
      calculated: calculatedProm,
      compositionDurationInFrames,
      compositionFps,
      compositionHeight,
      compositionWidth,
      compositionId
    });
    if (calculatedProm === null) {
      return {
        ...data,
        id: compositionId,
        defaultProps: serializeThenDeserializeInStudio(defaultProps ?? {}),
        props: serializeThenDeserializeInStudio(originalProps),
        defaultCodec: null,
        defaultOutName: null,
        defaultVideoImageFormat: null,
        defaultPixelFormat: null,
        defaultProResProfile: null
      };
    }
    return {
      ...data,
      id: compositionId,
      defaultProps: serializeThenDeserializeInStudio(defaultProps ?? {}),
      props: serializeThenDeserializeInStudio(calculatedProm.props ?? originalProps),
      defaultCodec: calculatedProm.defaultCodec ?? null,
      defaultOutName: calculatedProm.defaultOutName ?? null,
      defaultVideoImageFormat: calculatedProm.defaultVideoImageFormat ?? null,
      defaultPixelFormat: calculatedProm.defaultPixelFormat ?? null,
      defaultProResProfile: calculatedProm.defaultProResProfile ?? null
    };
  };
  var resolveVideoConfigOrCatch = (params) => {
    try {
      const promiseOrReturnValue = resolveVideoConfig(params);
      return {
        type: "success",
        result: promiseOrReturnValue
      };
    } catch (err) {
      return {
        type: "error",
        error: err
      };
    }
  };
  var getEnvVariables = () => {
    if (getRemotionEnvironment().isRendering) {
      const param = window.remotion_envVariables;
      if (!param) {
        return {};
      }
      return { ...JSON.parse(param), NODE_ENV: "production" };
    }
    if (false) {
    }
    return {
      NODE_ENV: "production"
    };
  };
  var setupEnvVariables = () => {
    const env = getEnvVariables();
    if (!window.process) {
      window.process = {};
    }
    if (!window.process.env) {
      window.process.env = {};
    }
    Object.keys(env).forEach((key) => {
      window.process.env[key] = env[key];
    });
  };
  var CurrentScaleContext = import_react61.default.createContext(null);
  var PreviewSizeContext = (0, import_react61.createContext)({
    setSize: () => {
      return;
    },
    size: { size: "auto", translation: { x: 0, y: 0 } }
  });
  var calculateScale = ({
    canvasSize,
    compositionHeight,
    compositionWidth,
    previewSize
  }) => {
    const heightRatio = canvasSize.height / compositionHeight;
    const widthRatio = canvasSize.width / compositionWidth;
    const ratio = Math.min(heightRatio, widthRatio);
    if (previewSize === "auto") {
      if (ratio === 0) {
        return 1;
      }
      return ratio;
    }
    return Number(previewSize);
  };
  var getOffthreadVideoSource = ({
    src,
    transparent,
    currentTime,
    toneMapped
  }) => {
    return `http://localhost:${window.remotion_proxyPort}/proxy?src=${encodeURIComponent(getAbsoluteSrc(src))}&time=${encodeURIComponent(Math.max(0, currentTime))}&transparent=${String(transparent)}&toneMapped=${String(toneMapped)}`;
  };
  var OffthreadVideoForRendering = ({
    onError,
    volume: volumeProp,
    playbackRate,
    src,
    muted,
    allowAmplificationDuringRender,
    transparent,
    toneMapped,
    toneFrequency,
    name,
    loopVolumeCurveBehavior,
    delayRenderRetries,
    delayRenderTimeoutInMilliseconds,
    onVideoFrame,
    crossOrigin,
    audioStreamIndex,
    ...props2
  }) => {
    const absoluteFrame = useTimelinePosition();
    const frame = useCurrentFrame();
    const volumePropsFrame = useFrameForVolumeProp(loopVolumeCurveBehavior);
    const videoConfig = useUnsafeVideoConfig();
    const sequenceContext = (0, import_react63.useContext)(SequenceContext);
    const mediaStartsAt = useMediaStartsAt();
    const { registerRenderAsset, unregisterRenderAsset } = (0, import_react63.useContext)(RenderAssetManager);
    if (!src) {
      throw new TypeError("No `src` was passed to <OffthreadVideo>.");
    }
    const id = (0, import_react63.useMemo)(() => `offthreadvideo-${random(src)}-${sequenceContext?.cumulatedFrom}-${sequenceContext?.relativeFrom}-${sequenceContext?.durationInFrames}`, [
      src,
      sequenceContext?.cumulatedFrom,
      sequenceContext?.relativeFrom,
      sequenceContext?.durationInFrames
    ]);
    if (!videoConfig) {
      throw new Error("No video config found");
    }
    const volume = evaluateVolume({
      volume: volumeProp,
      frame: volumePropsFrame,
      mediaVolume: 1
    });
    warnAboutTooHighVolume(volume);
    (0, import_react63.useEffect)(() => {
      if (!src) {
        throw new Error("No src passed");
      }
      if (!window.remotion_audioEnabled) {
        return;
      }
      if (muted) {
        return;
      }
      if (volume <= 0) {
        return;
      }
      registerRenderAsset({
        type: "video",
        src: getAbsoluteSrc(src),
        id,
        frame: absoluteFrame,
        volume,
        mediaFrame: frame,
        playbackRate,
        toneFrequency,
        audioStartFrame: Math.max(0, -(sequenceContext?.relativeFrom ?? 0)),
        audioStreamIndex
      });
      return () => unregisterRenderAsset(id);
    }, [
      muted,
      src,
      registerRenderAsset,
      id,
      unregisterRenderAsset,
      volume,
      frame,
      absoluteFrame,
      playbackRate,
      toneFrequency,
      sequenceContext?.relativeFrom,
      audioStreamIndex
    ]);
    const currentTime = (0, import_react63.useMemo)(() => {
      return getExpectedMediaFrameUncorrected({
        frame,
        playbackRate: playbackRate || 1,
        startFrom: -mediaStartsAt
      }) / videoConfig.fps;
    }, [frame, mediaStartsAt, playbackRate, videoConfig.fps]);
    const actualSrc = (0, import_react63.useMemo)(() => {
      return getOffthreadVideoSource({
        src,
        currentTime,
        transparent,
        toneMapped
      });
    }, [toneMapped, currentTime, src, transparent]);
    const [imageSrc, setImageSrc] = (0, import_react63.useState)(null);
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    (0, import_react63.useLayoutEffect)(() => {
      if (!window.remotion_videoEnabled) {
        return;
      }
      const cleanup = [];
      setImageSrc(null);
      const controller = new AbortController();
      const newHandle = delayRender2(`Fetching ${actualSrc} from server`, {
        retries: delayRenderRetries ?? void 0,
        timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
      });
      const execute = async () => {
        try {
          const res = await fetch(actualSrc, {
            signal: controller.signal,
            cache: "no-store"
          });
          if (res.status !== 200) {
            if (res.status === 500) {
              const json = await res.json();
              if (json.error) {
                const cleanedUpErrorMessage = json.error.replace(/^Error: /, "");
                throw new Error(cleanedUpErrorMessage);
              }
            }
            throw new Error(`Server returned status ${res.status} while fetching ${actualSrc}`);
          }
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          cleanup.push(() => URL.revokeObjectURL(url));
          setImageSrc({
            src: url,
            handle: newHandle
          });
        } catch (err) {
          if (err.message.includes("aborted")) {
            continueRender2(newHandle);
            return;
          }
          if (controller.signal.aborted) {
            continueRender2(newHandle);
            return;
          }
          if (err.message.includes("Failed to fetch")) {
            err = new Error(`Failed to fetch ${actualSrc}. This could be caused by Chrome rejecting the request because the disk space is low. Consider increasing the disk size of your environment.`, { cause: err });
          }
          if (onError) {
            onError(err);
          } else {
            cancelRender(err);
          }
        }
      };
      execute();
      cleanup.push(() => {
        if (controller.signal.aborted) {
          return;
        }
        controller.abort();
      });
      return () => {
        cleanup.forEach((c2) => c2());
      };
    }, [
      actualSrc,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      onError,
      continueRender2,
      delayRender2
    ]);
    const onErr = (0, import_react63.useCallback)(() => {
      if (onError) {
        onError?.(new Error("Failed to load image with src " + imageSrc));
      } else {
        cancelRender("Failed to load image with src " + imageSrc);
      }
    }, [imageSrc, onError]);
    const className2 = (0, import_react63.useMemo)(() => {
      return [OBJECTFIT_CONTAIN_CLASS_NAME, props2.className].filter(truthy).join(" ");
    }, [props2.className]);
    const onImageFrame = (0, import_react63.useCallback)((img) => {
      if (onVideoFrame) {
        onVideoFrame(img);
      }
    }, [onVideoFrame]);
    if (!imageSrc || !window.remotion_videoEnabled) {
      return null;
    }
    continueRender2(imageSrc.handle);
    return /* @__PURE__ */ (0, import_jsx_runtime29.jsx)(Img, {
      src: imageSrc.src,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      onImageFrame,
      ...props2,
      onError: onErr,
      className: className2
    });
  };
  var useEmitVideoFrame = ({
    ref,
    onVideoFrame
  }) => {
    (0, import_react65.useEffect)(() => {
      const { current } = ref;
      if (!current) {
        return;
      }
      if (!onVideoFrame) {
        return;
      }
      let handle = 0;
      const callback = () => {
        if (!ref.current) {
          return;
        }
        onVideoFrame(ref.current);
        handle = ref.current.requestVideoFrameCallback(callback);
      };
      callback();
      return () => {
        current.cancelVideoFrameCallback(handle);
      };
    }, [onVideoFrame, ref]);
  };
  var VideoForDevelopmentRefForwardingFunction = (props2, ref) => {
    const context = (0, import_react64.useContext)(SharedAudioContext);
    if (!context) {
      throw new Error("SharedAudioContext not found");
    }
    const videoRef = (0, import_react64.useRef)(null);
    const sharedSource = (0, import_react64.useMemo)(() => {
      if (!context.audioContext) {
        return null;
      }
      return makeSharedElementSourceNode({
        audioContext: context.audioContext,
        ref: videoRef
      });
    }, [context.audioContext]);
    const effectToUse = import_react64.default.useInsertionEffect ?? import_react64.default.useLayoutEffect;
    effectToUse(() => {
      return () => {
        requestAnimationFrame(() => {
          sharedSource?.cleanup();
        });
      };
    }, [sharedSource]);
    const {
      volume,
      muted,
      playbackRate,
      onlyWarnForMediaSeekingError,
      src,
      onDuration,
      acceptableTimeShift,
      acceptableTimeShiftInSeconds,
      toneFrequency,
      name,
      _remotionInternalNativeLoopPassed,
      _remotionInternalStack,
      style: style2,
      pauseWhenBuffering,
      showInTimeline,
      loopVolumeCurveBehavior,
      onError,
      onAutoPlayError,
      onVideoFrame,
      crossOrigin,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      allowAmplificationDuringRender,
      useWebAudioApi,
      audioStreamIndex,
      ...nativeProps
    } = props2;
    const _propsValid = true;
    if (!_propsValid) {
      throw new Error("typecheck error");
    }
    const volumePropFrame = useFrameForVolumeProp(loopVolumeCurveBehavior ?? "repeat");
    const { fps, durationInFrames } = useVideoConfig();
    const parentSequence = (0, import_react64.useContext)(SequenceContext);
    const { hidden } = (0, import_react64.useContext)(SequenceVisibilityToggleContext);
    const logLevel = useLogLevel();
    const mountTime = useMountTime();
    const [timelineId] = (0, import_react64.useState)(() => String(Math.random()));
    const isSequenceHidden = hidden[timelineId] ?? false;
    if (typeof acceptableTimeShift !== "undefined") {
      throw new Error("acceptableTimeShift has been removed. Use acceptableTimeShiftInSeconds instead.");
    }
    const [mediaVolume] = useMediaVolumeState();
    const [mediaMuted] = useMediaMutedState();
    const userPreferredVolume = evaluateVolume({
      frame: volumePropFrame,
      volume,
      mediaVolume
    });
    warnAboutTooHighVolume(userPreferredVolume);
    useMediaInTimeline({
      volume,
      mediaVolume,
      mediaType: "video",
      src,
      playbackRate: props2.playbackRate ?? 1,
      displayName: name ?? null,
      id: timelineId,
      stack: _remotionInternalStack,
      showInTimeline,
      premountDisplay: parentSequence?.premountDisplay ?? null,
      postmountDisplay: parentSequence?.postmountDisplay ?? null,
      loopDisplay: void 0
    });
    useMediaPlayback({
      mediaRef: videoRef,
      src,
      mediaType: "video",
      playbackRate: props2.playbackRate ?? 1,
      onlyWarnForMediaSeekingError,
      acceptableTimeshift: acceptableTimeShiftInSeconds ?? null,
      isPremounting: Boolean(parentSequence?.premounting),
      isPostmounting: Boolean(parentSequence?.postmounting),
      pauseWhenBuffering,
      onAutoPlayError: onAutoPlayError ?? null
    });
    useMediaTag({
      id: timelineId,
      isPostmounting: Boolean(parentSequence?.postmounting),
      isPremounting: Boolean(parentSequence?.premounting),
      mediaRef: videoRef,
      mediaType: "video",
      onAutoPlayError: onAutoPlayError ?? null
    });
    useVolume({
      logLevel,
      mediaRef: videoRef,
      volume: userPreferredVolume,
      source: sharedSource,
      shouldUseWebAudioApi: useWebAudioApi ?? false
    });
    const actualFrom = parentSequence ? parentSequence.relativeFrom : 0;
    const duration = parentSequence ? Math.min(parentSequence.durationInFrames, durationInFrames) : durationInFrames;
    const preloadedSrc = usePreload(src);
    const actualSrc = useAppendVideoFragment({
      actualSrc: preloadedSrc,
      actualFrom,
      duration,
      fps
    });
    (0, import_react64.useImperativeHandle)(ref, () => {
      return videoRef.current;
    }, []);
    (0, import_react64.useState)(() => playbackLogging({
      logLevel,
      message: `Mounting video with source = ${actualSrc}, v=${VERSION}, user agent=${typeof navigator === "undefined" ? "server" : navigator.userAgent}`,
      tag: "video",
      mountTime
    }));
    (0, import_react64.useEffect)(() => {
      const { current } = videoRef;
      if (!current) {
        return;
      }
      const errorHandler = () => {
        if (current.error) {
          console.error("Error occurred in video", current?.error);
          if (onError) {
            const err = new Error(`Code ${current.error.code}: ${current.error.message}`);
            onError(err);
            return;
          }
          throw new Error(`The browser threw an error while playing the video ${src}: Code ${current.error.code} - ${current?.error?.message}. See https://remotion.dev/docs/media-playback-error for help. Pass an onError() prop to handle the error.`);
        } else {
          if (onError) {
            const err = new Error(`The browser threw an error while playing the video ${src}`);
            onError(err);
            return;
          }
          throw new Error("The browser threw an error while playing the video");
        }
      };
      current.addEventListener("error", errorHandler, { once: true });
      return () => {
        current.removeEventListener("error", errorHandler);
      };
    }, [onError, src]);
    const currentOnDurationCallback = (0, import_react64.useRef)(onDuration);
    currentOnDurationCallback.current = onDuration;
    useEmitVideoFrame({ ref: videoRef, onVideoFrame });
    (0, import_react64.useEffect)(() => {
      const { current } = videoRef;
      if (!current) {
        return;
      }
      if (current.duration) {
        currentOnDurationCallback.current?.(src, current.duration);
        return;
      }
      const onLoadedMetadata = () => {
        currentOnDurationCallback.current?.(src, current.duration);
      };
      current.addEventListener("loadedmetadata", onLoadedMetadata);
      return () => {
        current.removeEventListener("loadedmetadata", onLoadedMetadata);
      };
    }, [src]);
    (0, import_react64.useEffect)(() => {
      const { current } = videoRef;
      if (!current) {
        return;
      }
      if (isIosSafari()) {
        current.preload = "metadata";
      } else {
        current.preload = "auto";
      }
    }, []);
    const actualStyle = (0, import_react64.useMemo)(() => {
      return {
        ...style2,
        opacity: isSequenceHidden ? 0 : style2?.opacity ?? 1
      };
    }, [isSequenceHidden, style2]);
    const crossOriginValue = getCrossOriginValue({
      crossOrigin,
      requestsVideoFrame: Boolean(onVideoFrame),
      isClientSideRendering: false
    });
    return /* @__PURE__ */ (0, import_jsx_runtime30.jsx)("video", {
      ref: videoRef,
      muted: muted || mediaMuted || isSequenceHidden || userPreferredVolume <= 0,
      playsInline: true,
      src: actualSrc,
      loop: _remotionInternalNativeLoopPassed,
      style: actualStyle,
      disableRemotePlayback: true,
      crossOrigin: crossOriginValue,
      ...nativeProps
    });
  };
  var VideoForPreview = (0, import_react64.forwardRef)(VideoForDevelopmentRefForwardingFunction);
  var InnerOffthreadVideo = (props2) => {
    const {
      startFrom,
      endAt,
      trimBefore,
      trimAfter,
      name,
      pauseWhenBuffering,
      stack,
      showInTimeline,
      ...otherProps
    } = props2;
    const environment = useRemotionEnvironment();
    if (environment.isClientSideRendering) {
      throw new Error("<OffthreadVideo> is not supported in @remotion/web-renderer. Use <Video> from @remotion/media instead. See https://remotion.dev/docs/client-side-rendering/limitations");
    }
    const onDuration = (0, import_react62.useCallback)(() => {
      return;
    }, []);
    if (typeof props2.src !== "string") {
      throw new TypeError(`The \`<OffthreadVideo>\` tag requires a string for \`src\`, but got ${JSON.stringify(props2.src)} instead.`);
    }
    validateMediaTrimProps({ startFrom, endAt, trimBefore, trimAfter });
    const { trimBeforeValue, trimAfterValue } = resolveTrimProps({
      startFrom,
      endAt,
      trimBefore,
      trimAfter
    });
    if (typeof trimBeforeValue !== "undefined" || typeof trimAfterValue !== "undefined") {
      return /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(Sequence, {
        layout: "none",
        from: 0 - (trimBeforeValue ?? 0),
        showInTimeline: false,
        durationInFrames: trimAfterValue,
        name,
        children: /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(InnerOffthreadVideo, {
          pauseWhenBuffering: pauseWhenBuffering ?? false,
          ...otherProps,
          trimAfter: void 0,
          name: void 0,
          showInTimeline,
          trimBefore: void 0,
          stack: void 0,
          startFrom: void 0,
          endAt: void 0
        })
      });
    }
    validateMediaProps(props2, "Video");
    if (environment.isRendering) {
      return /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(OffthreadVideoForRendering, {
        pauseWhenBuffering: pauseWhenBuffering ?? false,
        ...otherProps,
        trimAfter: void 0,
        name: void 0,
        showInTimeline,
        trimBefore: void 0,
        stack: void 0,
        startFrom: void 0,
        endAt: void 0
      });
    }
    const {
      transparent,
      toneMapped,
      onAutoPlayError,
      onVideoFrame,
      crossOrigin,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      ...propsForPreview
    } = otherProps;
    return /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(VideoForPreview, {
      _remotionInternalStack: stack ?? null,
      onDuration,
      onlyWarnForMediaSeekingError: true,
      pauseWhenBuffering: pauseWhenBuffering ?? false,
      showInTimeline: showInTimeline ?? true,
      onAutoPlayError: onAutoPlayError ?? void 0,
      onVideoFrame: onVideoFrame ?? null,
      crossOrigin,
      ...propsForPreview,
      _remotionInternalNativeLoopPassed: false
    });
  };
  var OffthreadVideo = ({
    src,
    acceptableTimeShiftInSeconds,
    allowAmplificationDuringRender,
    audioStreamIndex,
    className: className2,
    crossOrigin,
    delayRenderRetries,
    delayRenderTimeoutInMilliseconds,
    id,
    loopVolumeCurveBehavior,
    muted,
    name,
    onAutoPlayError,
    onError,
    onVideoFrame,
    pauseWhenBuffering,
    playbackRate,
    showInTimeline,
    style: style2,
    toneFrequency,
    toneMapped,
    transparent,
    trimAfter,
    trimBefore,
    useWebAudioApi,
    volume,
    _remotionInternalNativeLoopPassed,
    endAt,
    stack,
    startFrom,
    imageFormat
  }) => {
    if (imageFormat) {
      throw new TypeError(`The \`<OffthreadVideo>\` tag does no longer accept \`imageFormat\`. Use the \`transparent\` prop if you want to render a transparent video.`);
    }
    return /* @__PURE__ */ (0, import_jsx_runtime31.jsx)(InnerOffthreadVideo, {
      acceptableTimeShiftInSeconds,
      allowAmplificationDuringRender: allowAmplificationDuringRender ?? true,
      audioStreamIndex: audioStreamIndex ?? 0,
      className: className2,
      crossOrigin,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      id,
      loopVolumeCurveBehavior: loopVolumeCurveBehavior ?? "repeat",
      muted: muted ?? false,
      name,
      onAutoPlayError: onAutoPlayError ?? null,
      onError,
      onVideoFrame,
      pauseWhenBuffering: pauseWhenBuffering ?? true,
      playbackRate: playbackRate ?? 1,
      toneFrequency: toneFrequency ?? 1,
      showInTimeline: showInTimeline ?? true,
      src,
      stack,
      startFrom,
      _remotionInternalNativeLoopPassed: _remotionInternalNativeLoopPassed ?? false,
      endAt,
      style: style2,
      toneMapped: toneMapped ?? true,
      transparent: transparent ?? false,
      trimAfter,
      trimBefore,
      useWebAudioApi: useWebAudioApi ?? false,
      volume
    });
  };
  addSequenceStackTraces(OffthreadVideo);
  var WATCH_REMOTION_STATIC_FILES = "remotion_staticFilesChanged";
  function useRemotionContexts() {
    const compositionManagerCtx = import_react66.default.useContext(CompositionManager);
    const timelineContext = import_react66.default.useContext(TimelineContext);
    const setTimelineContext = import_react66.default.useContext(SetTimelineContext);
    const sequenceContext = import_react66.default.useContext(SequenceContext);
    const nonceContext = import_react66.default.useContext(NonceContext);
    const canUseRemotionHooksContext = import_react66.default.useContext(CanUseRemotionHooks);
    const preloadContext = import_react66.default.useContext(PreloadContext);
    const resolveCompositionContext = import_react66.default.useContext(ResolveCompositionContext);
    const renderAssetManagerContext = import_react66.default.useContext(RenderAssetManager);
    const sequenceManagerContext = import_react66.default.useContext(SequenceManager);
    const bufferManagerContext = import_react66.default.useContext(BufferingContextReact);
    const logLevelContext = import_react66.default.useContext(LogLevelContext);
    return (0, import_react66.useMemo)(() => ({
      compositionManagerCtx,
      timelineContext,
      setTimelineContext,
      sequenceContext,
      nonceContext,
      canUseRemotionHooksContext,
      preloadContext,
      resolveCompositionContext,
      renderAssetManagerContext,
      sequenceManagerContext,
      bufferManagerContext,
      logLevelContext
    }), [
      compositionManagerCtx,
      nonceContext,
      sequenceContext,
      setTimelineContext,
      timelineContext,
      canUseRemotionHooksContext,
      preloadContext,
      resolveCompositionContext,
      renderAssetManagerContext,
      sequenceManagerContext,
      bufferManagerContext,
      logLevelContext
    ]);
  }
  var RemotionContextProvider = (props2) => {
    const { children, contexts } = props2;
    return /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(LogLevelContext.Provider, {
      value: contexts.logLevelContext,
      children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(CanUseRemotionHooks.Provider, {
        value: contexts.canUseRemotionHooksContext,
        children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(NonceContext.Provider, {
          value: contexts.nonceContext,
          children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(PreloadContext.Provider, {
            value: contexts.preloadContext,
            children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(CompositionManager.Provider, {
              value: contexts.compositionManagerCtx,
              children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(SequenceManager.Provider, {
                value: contexts.sequenceManagerContext,
                children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(RenderAssetManager.Provider, {
                  value: contexts.renderAssetManagerContext,
                  children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(ResolveCompositionContext.Provider, {
                    value: contexts.resolveCompositionContext,
                    children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(TimelineContext.Provider, {
                      value: contexts.timelineContext,
                      children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(SetTimelineContext.Provider, {
                        value: contexts.setTimelineContext,
                        children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(SequenceContext.Provider, {
                          value: contexts.sequenceContext,
                          children: /* @__PURE__ */ (0, import_jsx_runtime32.jsx)(BufferingContextReact.Provider, {
                            value: contexts.bufferManagerContext,
                            children
                          })
                        })
                      })
                    })
                  })
                })
              })
            })
          })
        })
      })
    });
  };
  var compositionSelectorRef = (0, import_react55.createRef)();
  var Internals = {
    MaxMediaCacheSizeContext,
    useUnsafeVideoConfig,
    useFrameForVolumeProp,
    useTimelinePosition,
    evaluateVolume,
    getAbsoluteSrc,
    Timeline: exports_timeline_position_state,
    validateMediaTrimProps,
    validateMediaProps,
    resolveTrimProps,
    VideoForPreview,
    CompositionManager,
    CompositionSetters,
    SequenceManager,
    SequenceVisibilityToggleContext,
    RemotionRootContexts,
    CompositionManagerProvider,
    useVideo,
    getRoot,
    useMediaVolumeState,
    useMediaMutedState,
    useMediaInTimeline,
    useLazyComponent,
    truthy,
    SequenceContext,
    useRemotionContexts,
    RemotionContextProvider,
    CSSUtils: exports_default_css,
    setupEnvVariables,
    MediaVolumeContext,
    SetMediaVolumeContext,
    getRemotionEnvironment,
    SharedAudioContext,
    SharedAudioContextProvider,
    invalidCompositionErrorMessage,
    calculateMediaDuration,
    isCompositionIdValid,
    getPreviewDomElement,
    compositionsRef,
    portalNode,
    waitForRoot,
    SetTimelineContext,
    CanUseRemotionHooksProvider,
    CanUseRemotionHooks,
    PrefetchProvider,
    DurationsContextProvider,
    IsPlayerContextProvider,
    useIsPlayer,
    EditorPropsProvider,
    EditorPropsContext,
    usePreload,
    NonceContext,
    resolveVideoConfig,
    resolveVideoConfigOrCatch,
    ResolveCompositionContext,
    useResolvedVideoConfig,
    resolveCompositionsRef,
    REMOTION_STUDIO_CONTAINER_ELEMENT,
    RenderAssetManager,
    persistCurrentFrame,
    useTimelineSetFrame,
    isIosSafari,
    WATCH_REMOTION_STATIC_FILES,
    addSequenceStackTraces,
    useMediaStartsAt,
    BufferingProvider,
    BufferingContextReact,
    enableSequenceStackTraces,
    CurrentScaleContext,
    PreviewSizeContext,
    calculateScale,
    editorPropsProviderRef,
    PROPS_UPDATED_EXTERNALLY,
    validateRenderAsset,
    Log,
    LogLevelContext,
    useLogLevel,
    playbackLogging,
    timeValueRef,
    compositionSelectorRef,
    RemotionEnvironmentContext,
    warnAboutTooHighVolume,
    AudioForPreview,
    OBJECTFIT_CONTAIN_CLASS_NAME,
    InnerOffthreadVideo,
    useBasicMediaInTimeline,
    getInputPropsOverride,
    setInputPropsOverride,
    useVideoEnabled,
    useAudioEnabled,
    useIsPlayerBuffering,
    TimelinePosition: exports_timeline_position_state,
    DelayRenderContextType,
    TimelineContext,
    RenderAssetManagerProvider
  };
  var NUMBER = "[-+]?\\d*\\.?\\d+";
  var PERCENTAGE = NUMBER + "%";
  var flattenChildren = (children) => {
    const childrenArray = import_react68.default.Children.toArray(children);
    return childrenArray.reduce((flatChildren, child) => {
      if (child.type === import_react68.default.Fragment) {
        return flatChildren.concat(flattenChildren(child.props.children));
      }
      flatChildren.push(child);
      return flatChildren;
    }, []);
  };
  var IsInsideSeriesContext = (0, import_react69.createContext)(false);
  var IsInsideSeriesContainer = ({ children }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(IsInsideSeriesContext.Provider, {
      value: true,
      children
    });
  };
  var IsNotInsideSeriesProvider = ({ children }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime33.jsx)(IsInsideSeriesContext.Provider, {
      value: false,
      children
    });
  };
  var useRequireToBeInsideSeries = () => {
    const isInsideSeries = import_react69.default.useContext(IsInsideSeriesContext);
    if (!isInsideSeries) {
      throw new Error("This component must be inside a <Series /> component.");
    }
  };
  var SeriesSequenceRefForwardingFunction = ({ children }, _ref) => {
    useRequireToBeInsideSeries();
    return /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(IsNotInsideSeriesProvider, {
      children
    });
  };
  var SeriesSequence = (0, import_react67.forwardRef)(SeriesSequenceRefForwardingFunction);
  var Series = (props2) => {
    const childrenValue = (0, import_react67.useMemo)(() => {
      let startFrame = 0;
      const flattenedChildren = flattenChildren(props2.children);
      return import_react67.Children.map(flattenedChildren, (child, i) => {
        const castedChild = child;
        if (typeof castedChild === "string") {
          if (castedChild.trim() === "") {
            return null;
          }
          throw new TypeError(`The <Series /> component only accepts a list of <Series.Sequence /> components as its children, but you passed a string "${castedChild}"`);
        }
        if (castedChild.type !== SeriesSequence) {
          throw new TypeError(`The <Series /> component only accepts a list of <Series.Sequence /> components as its children, but got ${castedChild} instead`);
        }
        const debugInfo = `index = ${i}, duration = ${castedChild.props.durationInFrames}`;
        if (!castedChild?.props.children) {
          throw new TypeError(`A <Series.Sequence /> component (${debugInfo}) was detected to not have any children. Delete it to fix this error.`);
        }
        const durationInFramesProp = castedChild.props.durationInFrames;
        const {
          durationInFrames,
          children: _children,
          from,
          name,
          ...passedProps
        } = castedChild.props;
        if (i !== flattenedChildren.length - 1 || durationInFramesProp !== Infinity) {
          validateDurationInFrames(durationInFramesProp, {
            component: `of a <Series.Sequence /> component`,
            allowFloats: true
          });
        }
        const offset = castedChild.props.offset ?? 0;
        if (Number.isNaN(offset)) {
          throw new TypeError(`The "offset" property of a <Series.Sequence /> must not be NaN, but got NaN (${debugInfo}).`);
        }
        if (!Number.isFinite(offset)) {
          throw new TypeError(`The "offset" property of a <Series.Sequence /> must be finite, but got ${offset} (${debugInfo}).`);
        }
        if (offset % 1 !== 0) {
          throw new TypeError(`The "offset" property of a <Series.Sequence /> must be finite, but got ${offset} (${debugInfo}).`);
        }
        const currentStartFrame = startFrame + offset;
        startFrame += durationInFramesProp + offset;
        return /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(Sequence, {
          name: name || "<Series.Sequence>",
          from: currentStartFrame,
          durationInFrames: durationInFramesProp,
          ...passedProps,
          ref: castedChild.ref,
          children: child
        });
      });
    }, [props2.children]);
    if (ENABLE_V5_BREAKING_CHANGES) {
      return /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(IsInsideSeriesContainer, {
        children: /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(Sequence, {
          ...props2,
          children: childrenValue
        })
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime34.jsx)(IsInsideSeriesContainer, {
      children: childrenValue
    });
  };
  Series.Sequence = SeriesSequence;
  addSequenceStackTraces(SeriesSequence);
  var problematicCharacters = {
    "%3A": ":",
    "%2F": "/",
    "%3F": "?",
    "%23": "#",
    "%5B": "[",
    "%5D": "]",
    "%40": "@",
    "%21": "!",
    "%24": "$",
    "%26": "&",
    "%27": "'",
    "%28": "(",
    "%29": ")",
    "%2A": "*",
    "%2B": "+",
    "%2C": ",",
    "%3B": ";"
  };
  var didWarn2 = {};
  var warnOnce3 = (message) => {
    if (didWarn2[message]) {
      return;
    }
    console.warn(message);
    didWarn2[message] = true;
  };
  var includesHexOfUnsafeChar = (path) => {
    for (const key of Object.keys(problematicCharacters)) {
      if (path.includes(key)) {
        return { containsHex: true, hexCode: key };
      }
    }
    return { containsHex: false };
  };
  var trimLeadingSlash = (path) => {
    if (path.startsWith("/")) {
      return trimLeadingSlash(path.substring(1));
    }
    return path;
  };
  var inner = (path) => {
    if (typeof window !== "undefined" && window.remotion_staticBase) {
      if (path.startsWith(window.remotion_staticBase)) {
        throw new Error(`The value "${path}" is already prefixed with the static base ${window.remotion_staticBase}. You don't need to call staticFile() on it.`);
      }
      return `${window.remotion_staticBase}/${trimLeadingSlash(path)}`;
    }
    return `/${trimLeadingSlash(path)}`;
  };
  var encodeBySplitting = (path) => {
    const splitBySlash = path.split("/");
    const encodedArray = splitBySlash.map((element) => {
      return encodeURIComponent(element);
    });
    const merged = encodedArray.join("/");
    return merged;
  };
  var staticFile = (path) => {
    if (path === null) {
      throw new TypeError("null was passed to staticFile()");
    }
    if (typeof path === "undefined") {
      throw new TypeError("undefined was passed to staticFile()");
    }
    if (path.startsWith("http://") || path.startsWith("https://")) {
      throw new TypeError(`staticFile() does not support remote URLs - got "${path}". Instead, pass the URL without wrapping it in staticFile(). See: https://remotion.dev/docs/staticfile-remote-urls`);
    }
    if (path.startsWith("..") || path.startsWith("./")) {
      throw new TypeError(`staticFile() does not support relative paths - got "${path}". Instead, pass the name of a file that is inside the public/ folder. See: https://remotion.dev/docs/staticfile-relative-paths`);
    }
    if (path.startsWith("/Users") || path.startsWith("/home") || path.startsWith("/tmp") || path.startsWith("/etc") || path.startsWith("/opt") || path.startsWith("/var") || path.startsWith("C:") || path.startsWith("D:") || path.startsWith("E:")) {
      throw new TypeError(`staticFile() does not support absolute paths - got "${path}". Instead, pass the name of a file that is inside the public/ folder. See: https://remotion.dev/docs/staticfile-relative-paths`);
    }
    if (path.startsWith("public/")) {
      throw new TypeError(`Do not include the public/ prefix when using staticFile() - got "${path}". See: https://remotion.dev/docs/staticfile-relative-paths`);
    }
    const includesHex = includesHexOfUnsafeChar(path);
    if (includesHex.containsHex) {
      warnOnce3(`WARNING: You seem to pass an already encoded path (path contains ${includesHex.hexCode}). Since Remotion 4.0, the encoding is done by staticFile() itself. You may want to remove a encodeURIComponent() wrapping.`);
    }
    const preprocessed = encodeBySplitting(path);
    const preparsed = inner(preprocessed);
    if (!preparsed.startsWith("/")) {
      return `/${preparsed}`;
    }
    return preparsed;
  };
  var roundTo6Commas = (num) => {
    return Math.round(num * 1e5) / 1e5;
  };
  var seekToTime = ({
    element,
    desiredTime,
    logLevel,
    mountTime
  }) => {
    if (isApproximatelyTheSame(element.currentTime, desiredTime)) {
      return {
        wait: Promise.resolve(desiredTime),
        cancel: () => {
        }
      };
    }
    seek({
      logLevel,
      mediaRef: element,
      time: desiredTime,
      why: "Seeking during rendering",
      mountTime
    });
    let cancel;
    let cancelSeeked = null;
    const prom = new Promise((resolve) => {
      cancel = element.requestVideoFrameCallback((now, metadata) => {
        const displayIn = metadata.expectedDisplayTime - now;
        if (displayIn <= 0) {
          resolve(metadata.mediaTime);
          return;
        }
        setTimeout(() => {
          resolve(metadata.mediaTime);
        }, displayIn + 150);
      });
    });
    const waitForSeekedEvent = new Promise((resolve) => {
      const onDone = () => {
        resolve();
      };
      element.addEventListener("seeked", onDone, {
        once: true
      });
      cancelSeeked = () => {
        element.removeEventListener("seeked", onDone);
      };
    });
    return {
      wait: Promise.all([prom, waitForSeekedEvent]).then(([time]) => time),
      cancel: () => {
        cancelSeeked?.();
        element.cancelVideoFrameCallback(cancel);
      }
    };
  };
  var seekToTimeMultipleUntilRight = ({
    element,
    desiredTime,
    fps,
    logLevel,
    mountTime
  }) => {
    const threshold = 1 / fps / 2;
    let currentCancel = () => {
      return;
    };
    if (Number.isFinite(element.duration) && element.currentTime >= element.duration && desiredTime >= element.duration) {
      return {
        prom: Promise.resolve(),
        cancel: () => {
        }
      };
    }
    const prom = new Promise((resolve, reject) => {
      const firstSeek = seekToTime({
        element,
        desiredTime: desiredTime + threshold,
        logLevel,
        mountTime
      });
      firstSeek.wait.then((seekedTo) => {
        const difference = Math.abs(desiredTime - seekedTo);
        if (difference <= threshold) {
          return resolve();
        }
        const sign = desiredTime > seekedTo ? 1 : -1;
        const newSeek = seekToTime({
          element,
          desiredTime: seekedTo + threshold * sign,
          logLevel,
          mountTime
        });
        currentCancel = newSeek.cancel;
        newSeek.wait.then((newTime) => {
          const newDifference = Math.abs(desiredTime - newTime);
          if (roundTo6Commas(newDifference) <= roundTo6Commas(threshold)) {
            return resolve();
          }
          const thirdSeek = seekToTime({
            element,
            desiredTime: desiredTime + threshold,
            logLevel,
            mountTime
          });
          currentCancel = thirdSeek.cancel;
          return thirdSeek.wait.then(() => {
            resolve();
          }).catch((err) => {
            reject(err);
          });
        }).catch((err) => {
          reject(err);
        });
      });
      currentCancel = firstSeek.cancel;
    });
    return {
      prom,
      cancel: () => {
        currentCancel();
      }
    };
  };
  var VideoForRenderingForwardFunction = ({
    onError,
    volume: volumeProp,
    allowAmplificationDuringRender,
    playbackRate,
    onDuration,
    toneFrequency,
    name,
    acceptableTimeShiftInSeconds,
    delayRenderRetries,
    delayRenderTimeoutInMilliseconds,
    loopVolumeCurveBehavior,
    audioStreamIndex,
    onVideoFrame,
    ...props2
  }, ref) => {
    const absoluteFrame = useTimelinePosition();
    const frame = useCurrentFrame();
    const volumePropsFrame = useFrameForVolumeProp(loopVolumeCurveBehavior ?? "repeat");
    const videoConfig = useUnsafeVideoConfig();
    const videoRef = (0, import_react72.useRef)(null);
    const sequenceContext = (0, import_react72.useContext)(SequenceContext);
    const mediaStartsAt = useMediaStartsAt();
    const environment = useRemotionEnvironment();
    const logLevel = useLogLevel();
    const mountTime = useMountTime();
    const { delayRender: delayRender2, continueRender: continueRender2 } = useDelayRender();
    const { registerRenderAsset, unregisterRenderAsset } = (0, import_react72.useContext)(RenderAssetManager);
    const id = (0, import_react72.useMemo)(() => `video-${random(props2.src ?? "")}-${sequenceContext?.cumulatedFrom}-${sequenceContext?.relativeFrom}-${sequenceContext?.durationInFrames}`, [
      props2.src,
      sequenceContext?.cumulatedFrom,
      sequenceContext?.relativeFrom,
      sequenceContext?.durationInFrames
    ]);
    if (!videoConfig) {
      throw new Error("No video config found");
    }
    const volume = evaluateVolume({
      volume: volumeProp,
      frame: volumePropsFrame,
      mediaVolume: 1
    });
    warnAboutTooHighVolume(volume);
    (0, import_react72.useEffect)(() => {
      if (!props2.src) {
        throw new Error("No src passed");
      }
      if (props2.muted) {
        return;
      }
      if (volume <= 0) {
        return;
      }
      if (!window.remotion_audioEnabled) {
        return;
      }
      registerRenderAsset({
        type: "video",
        src: getAbsoluteSrc(props2.src),
        id,
        frame: absoluteFrame,
        volume,
        mediaFrame: frame,
        playbackRate: playbackRate ?? 1,
        toneFrequency: toneFrequency ?? 1,
        audioStartFrame: Math.max(0, -(sequenceContext?.relativeFrom ?? 0)),
        audioStreamIndex: audioStreamIndex ?? 0
      });
      return () => unregisterRenderAsset(id);
    }, [
      props2.muted,
      props2.src,
      registerRenderAsset,
      id,
      unregisterRenderAsset,
      volume,
      frame,
      absoluteFrame,
      playbackRate,
      toneFrequency,
      sequenceContext?.relativeFrom,
      audioStreamIndex
    ]);
    (0, import_react72.useImperativeHandle)(ref, () => {
      return videoRef.current;
    }, []);
    (0, import_react72.useEffect)(() => {
      if (!window.remotion_videoEnabled) {
        return;
      }
      const { current } = videoRef;
      if (!current) {
        return;
      }
      const currentTime = getMediaTime({
        frame,
        playbackRate: playbackRate || 1,
        startFrom: -mediaStartsAt,
        fps: videoConfig.fps
      });
      const handle = delayRender2(`Rendering <Html5Video /> with src="${props2.src}" at time ${currentTime}`, {
        retries: delayRenderRetries ?? void 0,
        timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
      });
      if (window.process?.env?.NODE_ENV === "test") {
        continueRender2(handle);
        return;
      }
      if (isApproximatelyTheSame(current.currentTime, currentTime)) {
        if (current.readyState >= 2) {
          continueRender2(handle);
          return;
        }
        const loadedDataHandler = () => {
          continueRender2(handle);
        };
        current.addEventListener("loadeddata", loadedDataHandler, { once: true });
        return () => {
          current.removeEventListener("loadeddata", loadedDataHandler);
        };
      }
      const endedHandler = () => {
        continueRender2(handle);
      };
      const seek2 = seekToTimeMultipleUntilRight({
        element: current,
        desiredTime: currentTime,
        fps: videoConfig.fps,
        logLevel,
        mountTime
      });
      seek2.prom.then(() => {
        continueRender2(handle);
      });
      current.addEventListener("ended", endedHandler, { once: true });
      const errorHandler = () => {
        if (current?.error) {
          console.error("Error occurred in video", current?.error);
          if (onError) {
            return;
          }
          throw new Error(`The browser threw an error while playing the video ${props2.src}: Code ${current.error.code} - ${current?.error?.message}. See https://remotion.dev/docs/media-playback-error for help. Pass an onError() prop to handle the error.`);
        } else {
          throw new Error("The browser threw an error");
        }
      };
      current.addEventListener("error", errorHandler, { once: true });
      return () => {
        seek2.cancel();
        current.removeEventListener("ended", endedHandler);
        current.removeEventListener("error", errorHandler);
        continueRender2(handle);
      };
    }, [
      volumePropsFrame,
      props2.src,
      playbackRate,
      videoConfig.fps,
      frame,
      mediaStartsAt,
      onError,
      delayRenderRetries,
      delayRenderTimeoutInMilliseconds,
      logLevel,
      mountTime,
      continueRender2,
      delayRender2
    ]);
    const { src } = props2;
    if (environment.isRendering) {
      (0, import_react72.useLayoutEffect)(() => {
        if (window.process?.env?.NODE_ENV === "test") {
          return;
        }
        const newHandle = delayRender2("Loading <Html5Video> duration with src=" + src, {
          retries: delayRenderRetries ?? void 0,
          timeoutInMilliseconds: delayRenderTimeoutInMilliseconds ?? void 0
        });
        const { current } = videoRef;
        const didLoad = () => {
          if (current?.duration) {
            onDuration(src, current.duration);
          }
          continueRender2(newHandle);
        };
        if (current?.duration) {
          onDuration(src, current.duration);
          continueRender2(newHandle);
        } else {
          current?.addEventListener("loadedmetadata", didLoad, { once: true });
        }
        return () => {
          current?.removeEventListener("loadedmetadata", didLoad);
          continueRender2(newHandle);
        };
      }, [
        src,
        onDuration,
        delayRenderRetries,
        delayRenderTimeoutInMilliseconds,
        continueRender2,
        delayRender2
      ]);
    }
    return /* @__PURE__ */ (0, import_jsx_runtime35.jsx)("video", {
      ref: videoRef,
      disableRemotePlayback: true,
      ...props2
    });
  };
  var VideoForRendering = (0, import_react72.forwardRef)(VideoForRenderingForwardFunction);
  var VideoForwardingFunction = (props2, ref) => {
    const {
      startFrom,
      endAt,
      trimBefore,
      trimAfter,
      name,
      pauseWhenBuffering,
      stack,
      _remotionInternalNativeLoopPassed,
      showInTimeline,
      onAutoPlayError,
      ...otherProps
    } = props2;
    const { loop, ...propsOtherThanLoop } = props2;
    const { fps } = useVideoConfig();
    const environment = useRemotionEnvironment();
    if (environment.isClientSideRendering) {
      throw new Error("<Html5Video> is not supported in @remotion/web-renderer. Use <Video> from @remotion/media instead. See https://remotion.dev/docs/client-side-rendering/limitations");
    }
    const { durations, setDurations } = (0, import_react71.useContext)(DurationsContext);
    if (typeof ref === "string") {
      throw new Error("string refs are not supported");
    }
    if (typeof props2.src !== "string") {
      throw new TypeError(`The \`<Html5Video>\` tag requires a string for \`src\`, but got ${JSON.stringify(props2.src)} instead.`);
    }
    const preloadedSrc = usePreload(props2.src);
    const onDuration = (0, import_react71.useCallback)((src, durationInSeconds) => {
      setDurations({ type: "got-duration", durationInSeconds, src });
    }, [setDurations]);
    const onVideoFrame = (0, import_react71.useCallback)(() => {
    }, []);
    const durationFetched = durations[getAbsoluteSrc(preloadedSrc)] ?? durations[getAbsoluteSrc(props2.src)];
    validateMediaTrimProps({ startFrom, endAt, trimBefore, trimAfter });
    const { trimBeforeValue, trimAfterValue } = resolveTrimProps({
      startFrom,
      endAt,
      trimBefore,
      trimAfter
    });
    if (loop && durationFetched !== void 0) {
      if (!Number.isFinite(durationFetched)) {
        return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(Html5Video, {
          ...propsOtherThanLoop,
          ref,
          _remotionInternalNativeLoopPassed: true
        });
      }
      const mediaDuration = durationFetched * fps;
      return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(Loop, {
        durationInFrames: calculateMediaDuration({
          trimAfter: trimAfterValue,
          mediaDurationInFrames: mediaDuration,
          playbackRate: props2.playbackRate ?? 1,
          trimBefore: trimBeforeValue
        }),
        layout: "none",
        name,
        children: /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(Html5Video, {
          ...propsOtherThanLoop,
          ref,
          _remotionInternalNativeLoopPassed: true
        })
      });
    }
    if (typeof trimBeforeValue !== "undefined" || typeof trimAfterValue !== "undefined") {
      return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(Sequence, {
        layout: "none",
        from: 0 - (trimBeforeValue ?? 0),
        showInTimeline: false,
        durationInFrames: trimAfterValue,
        name,
        children: /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(Html5Video, {
          pauseWhenBuffering: pauseWhenBuffering ?? false,
          ...otherProps,
          ref
        })
      });
    }
    validateMediaProps({ playbackRate: props2.playbackRate, volume: props2.volume }, "Html5Video");
    if (environment.isRendering) {
      return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(VideoForRendering, {
        onDuration,
        onVideoFrame: onVideoFrame ?? null,
        ...otherProps,
        ref
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime36.jsx)(VideoForPreview, {
      onlyWarnForMediaSeekingError: false,
      ...otherProps,
      ref,
      onVideoFrame: null,
      pauseWhenBuffering: pauseWhenBuffering ?? false,
      onDuration,
      _remotionInternalStack: stack ?? null,
      _remotionInternalNativeLoopPassed: _remotionInternalNativeLoopPassed ?? false,
      showInTimeline: showInTimeline ?? true,
      onAutoPlayError: onAutoPlayError ?? void 0
    });
  };
  var Html5Video = (0, import_react71.forwardRef)(VideoForwardingFunction);
  addSequenceStackTraces(Html5Video);
  checkMultipleRemotionVersions();
  var proxyObj = {};
  var Config = new Proxy(proxyObj, {
    get(_, prop) {
      if (prop === "Bundling" || prop === "Rendering" || prop === "Log" || prop === "Puppeteer" || prop === "Output") {
        return Config;
      }
      return () => {
        console.warn("\u26A0\uFE0F  The CLI configuration has been extracted from Remotion Core.");
        console.warn("Update the import from the config file:");
        console.warn();
        console.warn("- Delete:");
        console.warn('import {Config} from "remotion";');
        console.warn("+ Replace:");
        console.warn('import {Config} from "@remotion/cli/config";');
        console.warn();
        console.warn("For more information, see https://www.remotion.dev/docs/4-0-migration.");
        process.exit(1);
      };
    }
  });
  addSequenceStackTraces(Sequence);

  // node_modules/@remotion/player/dist/esm/index.mjs
  var import_react73 = __toESM(require_react(), 1);
  var import_react74 = __toESM(require_react(), 1);
  var import_react75 = __toESM(require_react(), 1);
  var import_jsx_runtime39 = __toESM(require_jsx_runtime(), 1);
  var import_react76 = __toESM(require_react(), 1);
  var import_react77 = __toESM(require_react(), 1);
  var import_react78 = __toESM(require_react(), 1);
  var import_react79 = __toESM(require_react(), 1);
  var import_react80 = __toESM(require_react(), 1);
  var import_react81 = __toESM(require_react(), 1);
  var import_react82 = __toESM(require_react(), 1);
  var import_react83 = __toESM(require_react(), 1);
  var import_react84 = __toESM(require_react(), 1);
  var import_react85 = __toESM(require_react(), 1);
  var import_jsx_runtime40 = __toESM(require_jsx_runtime(), 1);
  var import_react86 = __toESM(require_react(), 1);
  var import_react87 = __toESM(require_react(), 1);
  var import_jsx_runtime41 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime42 = __toESM(require_jsx_runtime(), 1);
  var import_react88 = __toESM(require_react(), 1);
  var import_react89 = __toESM(require_react(), 1);
  var import_jsx_runtime43 = __toESM(require_jsx_runtime(), 1);
  var import_react90 = __toESM(require_react(), 1);
  var import_jsx_runtime44 = __toESM(require_jsx_runtime(), 1);
  var import_react91 = __toESM(require_react(), 1);
  var import_jsx_runtime45 = __toESM(require_jsx_runtime(), 1);
  var import_react92 = __toESM(require_react(), 1);
  var import_jsx_runtime46 = __toESM(require_jsx_runtime(), 1);
  var import_react93 = __toESM(require_react(), 1);
  var import_jsx_runtime47 = __toESM(require_jsx_runtime(), 1);
  var import_react94 = __toESM(require_react(), 1);
  var import_jsx_runtime48 = __toESM(require_jsx_runtime(), 1);
  var import_react95 = __toESM(require_react(), 1);
  var import_react96 = __toESM(require_react(), 1);
  var import_jsx_runtime49 = __toESM(require_jsx_runtime(), 1);
  var import_react97 = __toESM(require_react(), 1);
  var import_jsx_runtime50 = __toESM(require_jsx_runtime(), 1);

  // node_modules/remotion/dist/esm/no-react.mjs
  function interpolateFunction2(input, inputRange, outputRange, options) {
    const { extrapolateLeft, extrapolateRight, easing } = options;
    let result = input;
    const [inputMin, inputMax] = inputRange;
    const [outputMin, outputMax] = outputRange;
    if (result < inputMin) {
      if (extrapolateLeft === "identity") {
        return result;
      }
      if (extrapolateLeft === "clamp") {
        result = inputMin;
      } else if (extrapolateLeft === "wrap") {
        const range = inputMax - inputMin;
        result = ((result - inputMin) % range + range) % range + inputMin;
      } else if (extrapolateLeft === "extend") {
      }
    }
    if (result > inputMax) {
      if (extrapolateRight === "identity") {
        return result;
      }
      if (extrapolateRight === "clamp") {
        result = inputMax;
      } else if (extrapolateRight === "wrap") {
        const range = inputMax - inputMin;
        result = ((result - inputMin) % range + range) % range + inputMin;
      } else if (extrapolateRight === "extend") {
      }
    }
    if (outputMin === outputMax) {
      return outputMin;
    }
    result = (result - inputMin) / (inputMax - inputMin);
    result = easing(result);
    result = result * (outputMax - outputMin) + outputMin;
    return result;
  }
  function findRange2(input, inputRange) {
    let i;
    for (i = 1; i < inputRange.length - 1; ++i) {
      if (inputRange[i] >= input) {
        break;
      }
    }
    return i - 1;
  }
  function checkValidInputRange2(arr) {
    for (let i = 1; i < arr.length; ++i) {
      if (!(arr[i] > arr[i - 1])) {
        throw new Error(`inputRange must be strictly monotonically increasing but got [${arr.join(",")}]`);
      }
    }
  }
  function checkInfiniteRange2(name, arr) {
    if (arr.length < 2) {
      throw new Error(name + " must have at least 2 elements");
    }
    for (const element of arr) {
      if (typeof element !== "number") {
        throw new Error(`${name} must contain only numbers`);
      }
      if (!Number.isFinite(element)) {
        throw new Error(`${name} must contain only finite numbers, but got [${arr.join(",")}]`);
      }
    }
  }
  function interpolate2(input, inputRange, outputRange, options) {
    if (typeof input === "undefined") {
      throw new Error("input can not be undefined");
    }
    if (typeof inputRange === "undefined") {
      throw new Error("inputRange can not be undefined");
    }
    if (typeof outputRange === "undefined") {
      throw new Error("outputRange can not be undefined");
    }
    if (inputRange.length !== outputRange.length) {
      throw new Error("inputRange (" + inputRange.length + ") and outputRange (" + outputRange.length + ") must have the same length");
    }
    checkInfiniteRange2("inputRange", inputRange);
    checkInfiniteRange2("outputRange", outputRange);
    checkValidInputRange2(inputRange);
    const easing = options?.easing ?? ((num) => num);
    let extrapolateLeft = "extend";
    if (options?.extrapolateLeft !== void 0) {
      extrapolateLeft = options.extrapolateLeft;
    }
    let extrapolateRight = "extend";
    if (options?.extrapolateRight !== void 0) {
      extrapolateRight = options.extrapolateRight;
    }
    if (typeof input !== "number") {
      throw new TypeError("Cannot interpolate an input which is not a number");
    }
    const range = findRange2(input, inputRange);
    return interpolateFunction2(input, [inputRange[range], inputRange[range + 1]], [outputRange[range], outputRange[range + 1]], {
      easing,
      extrapolateLeft,
      extrapolateRight
    });
  }
  function truthy2(value) {
    return Boolean(value);
  }
  if (typeof window !== "undefined") {
    window.remotion_renderReady = false;
    if (!window.remotion_delayRenderTimeouts) {
      window.remotion_delayRenderTimeouts = {};
    }
    window.remotion_delayRenderHandles = [];
  }
  var DELAY_RENDER_CALLSTACK_TOKEN2 = "The delayRender was called:";
  var DELAY_RENDER_RETRIES_LEFT2 = "Retries left: ";
  var DELAY_RENDER_RETRY_TOKEN2 = "- Rendering the frame will be retried.";
  var DELAY_RENDER_CLEAR_TOKEN2 = "handle was cleared after";
  var DATE_TOKEN2 = "remotion-date:";
  var FILE_TOKEN2 = "remotion-file:";
  var serializeJSONWithSpecialTypes2 = ({
    data,
    indent,
    staticBase
  }) => {
    let customDateUsed = false;
    let customFileUsed = false;
    let mapUsed = false;
    let setUsed = false;
    try {
      const serializedString = JSON.stringify(data, function(key, value) {
        const item = this[key];
        if (item instanceof Date) {
          customDateUsed = true;
          return `${DATE_TOKEN2}${item.toISOString()}`;
        }
        if (item instanceof Map) {
          mapUsed = true;
          return value;
        }
        if (item instanceof Set) {
          setUsed = true;
          return value;
        }
        if (typeof item === "string" && staticBase !== null && item.startsWith(staticBase)) {
          customFileUsed = true;
          return `${FILE_TOKEN2}${item.replace(staticBase + "/", "")}`;
        }
        return value;
      }, indent);
      return { serializedString, customDateUsed, customFileUsed, mapUsed, setUsed };
    } catch (err) {
      throw new Error("Could not serialize the passed input props to JSON: " + err.message);
    }
  };
  var deserializeJSONWithSpecialTypes2 = (data) => {
    return JSON.parse(data, (_, value) => {
      if (typeof value === "string" && value.startsWith(DATE_TOKEN2)) {
        return new Date(value.replace(DATE_TOKEN2, ""));
      }
      if (typeof value === "string" && value.startsWith(FILE_TOKEN2)) {
        return `${window.remotion_staticBase}/${value.replace(FILE_TOKEN2, "")}`;
      }
      return value;
    });
  };
  var NUMBER2 = "[-+]?\\d*\\.?\\d+";
  var PERCENTAGE2 = NUMBER2 + "%";
  function call(...args) {
    return "\\(\\s*(" + args.join(")\\s*,\\s*(") + ")\\s*\\)";
  }
  function getMatchers() {
    const cachedMatchers = {
      rgb: void 0,
      rgba: void 0,
      hsl: void 0,
      hsla: void 0,
      hex3: void 0,
      hex4: void 0,
      hex5: void 0,
      hex6: void 0,
      hex8: void 0
    };
    if (cachedMatchers.rgb === void 0) {
      cachedMatchers.rgb = new RegExp("rgb" + call(NUMBER2, NUMBER2, NUMBER2));
      cachedMatchers.rgba = new RegExp("rgba" + call(NUMBER2, NUMBER2, NUMBER2, NUMBER2));
      cachedMatchers.hsl = new RegExp("hsl" + call(NUMBER2, PERCENTAGE2, PERCENTAGE2));
      cachedMatchers.hsla = new RegExp("hsla" + call(NUMBER2, PERCENTAGE2, PERCENTAGE2, NUMBER2));
      cachedMatchers.hex3 = /^#([0-9a-fA-F]{1})([0-9a-fA-F]{1})([0-9a-fA-F]{1})$/;
      cachedMatchers.hex4 = /^#([0-9a-fA-F]{1})([0-9a-fA-F]{1})([0-9a-fA-F]{1})([0-9a-fA-F]{1})$/;
      cachedMatchers.hex6 = /^#([0-9a-fA-F]{6})$/;
      cachedMatchers.hex8 = /^#([0-9a-fA-F]{8})$/;
    }
    return cachedMatchers;
  }
  function hue2rgb(p, q, t) {
    if (t < 0) {
      t += 1;
    }
    if (t > 1) {
      t -= 1;
    }
    if (t < 1 / 6) {
      return p + (q - p) * 6 * t;
    }
    if (t < 1 / 2) {
      return q;
    }
    if (t < 2 / 3) {
      return p + (q - p) * (2 / 3 - t) * 6;
    }
    return p;
  }
  function hslToRgb(h, s, l) {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    const r = hue2rgb(p, q, h + 1 / 3);
    const g = hue2rgb(p, q, h);
    const b2 = hue2rgb(p, q, h - 1 / 3);
    return Math.round(r * 255) << 24 | Math.round(g * 255) << 16 | Math.round(b2 * 255) << 8;
  }
  function parse255(str) {
    const int = Number.parseInt(str, 10);
    if (int < 0) {
      return 0;
    }
    if (int > 255) {
      return 255;
    }
    return int;
  }
  function parse360(str) {
    const int = Number.parseFloat(str);
    return (int % 360 + 360) % 360 / 360;
  }
  function parse1(str) {
    const num = Number.parseFloat(str);
    if (num < 0) {
      return 0;
    }
    if (num > 1) {
      return 255;
    }
    return Math.round(num * 255);
  }
  function parsePercentage(str) {
    const int = Number.parseFloat(str);
    if (int < 0) {
      return 0;
    }
    if (int > 100) {
      return 1;
    }
    return int / 100;
  }
  var colorNames = {
    transparent: 0,
    aliceblue: 4042850303,
    antiquewhite: 4209760255,
    aqua: 16777215,
    aquamarine: 2147472639,
    azure: 4043309055,
    beige: 4126530815,
    bisque: 4293182719,
    black: 255,
    blanchedalmond: 4293643775,
    blue: 65535,
    blueviolet: 2318131967,
    brown: 2771004159,
    burlywood: 3736635391,
    burntsienna: 3934150143,
    cadetblue: 1604231423,
    chartreuse: 2147418367,
    chocolate: 3530104575,
    coral: 4286533887,
    cornflowerblue: 1687547391,
    cornsilk: 4294499583,
    crimson: 3692313855,
    cyan: 16777215,
    darkblue: 35839,
    darkcyan: 9145343,
    darkgoldenrod: 3095792639,
    darkgray: 2846468607,
    darkgreen: 6553855,
    darkgrey: 2846468607,
    darkkhaki: 3182914559,
    darkmagenta: 2332068863,
    darkolivegreen: 1433087999,
    darkorange: 4287365375,
    darkorchid: 2570243327,
    darkred: 2332033279,
    darksalmon: 3918953215,
    darkseagreen: 2411499519,
    darkslateblue: 1211993087,
    darkslategray: 793726975,
    darkslategrey: 793726975,
    darkturquoise: 13554175,
    darkviolet: 2483082239,
    deeppink: 4279538687,
    deepskyblue: 12582911,
    dimgray: 1768516095,
    dimgrey: 1768516095,
    dodgerblue: 512819199,
    firebrick: 2988581631,
    floralwhite: 4294635775,
    forestgreen: 579543807,
    fuchsia: 4278255615,
    gainsboro: 3705462015,
    ghostwhite: 4177068031,
    gold: 4292280575,
    goldenrod: 3668254975,
    gray: 2155905279,
    green: 8388863,
    greenyellow: 2919182335,
    grey: 2155905279,
    honeydew: 4043305215,
    hotpink: 4285117695,
    indianred: 3445382399,
    indigo: 1258324735,
    ivory: 4294963455,
    khaki: 4041641215,
    lavender: 3873897215,
    lavenderblush: 4293981695,
    lawngreen: 2096890111,
    lemonchiffon: 4294626815,
    lightblue: 2916673279,
    lightcoral: 4034953471,
    lightcyan: 3774873599,
    lightgoldenrodyellow: 4210742015,
    lightgray: 3553874943,
    lightgreen: 2431553791,
    lightgrey: 3553874943,
    lightpink: 4290167295,
    lightsalmon: 4288707327,
    lightseagreen: 548580095,
    lightskyblue: 2278488831,
    lightslategray: 2005441023,
    lightslategrey: 2005441023,
    lightsteelblue: 2965692159,
    lightyellow: 4294959359,
    lime: 16711935,
    limegreen: 852308735,
    linen: 4210091775,
    magenta: 4278255615,
    maroon: 2147483903,
    mediumaquamarine: 1724754687,
    mediumblue: 52735,
    mediumorchid: 3126187007,
    mediumpurple: 2473647103,
    mediumseagreen: 1018393087,
    mediumslateblue: 2070474495,
    mediumspringgreen: 16423679,
    mediumturquoise: 1221709055,
    mediumvioletred: 3340076543,
    midnightblue: 421097727,
    mintcream: 4127193855,
    mistyrose: 4293190143,
    moccasin: 4293178879,
    navajowhite: 4292783615,
    navy: 33023,
    oldlace: 4260751103,
    olive: 2155872511,
    olivedrab: 1804477439,
    orange: 4289003775,
    orangered: 4282712319,
    orchid: 3664828159,
    palegoldenrod: 4008225535,
    palegreen: 2566625535,
    paleturquoise: 2951671551,
    palevioletred: 3681588223,
    papayawhip: 4293907967,
    peachpuff: 4292524543,
    peru: 3448061951,
    pink: 4290825215,
    plum: 3718307327,
    powderblue: 2967529215,
    purple: 2147516671,
    rebeccapurple: 1714657791,
    red: 4278190335,
    rosybrown: 3163525119,
    royalblue: 1097458175,
    saddlebrown: 2336560127,
    salmon: 4202722047,
    sandybrown: 4104413439,
    seagreen: 780883967,
    seashell: 4294307583,
    sienna: 2689740287,
    silver: 3233857791,
    skyblue: 2278484991,
    slateblue: 1784335871,
    slategray: 1887473919,
    slategrey: 1887473919,
    snow: 4294638335,
    springgreen: 16744447,
    steelblue: 1182971135,
    tan: 3535047935,
    teal: 8421631,
    thistle: 3636451583,
    tomato: 4284696575,
    turquoise: 1088475391,
    violet: 4001558271,
    wheat: 4125012991,
    white: 4294967295,
    whitesmoke: 4126537215,
    yellow: 4294902015,
    yellowgreen: 2597139199
  };
  function normalizeColor(color) {
    const matchers = getMatchers();
    let match;
    if (matchers.hex6) {
      if (match = matchers.hex6.exec(color)) {
        return Number.parseInt(match[1] + "ff", 16) >>> 0;
      }
    }
    if (colorNames[color] !== void 0) {
      return colorNames[color];
    }
    if (matchers.rgb) {
      if (match = matchers.rgb.exec(color)) {
        return (parse255(match[1]) << 24 | parse255(match[2]) << 16 | parse255(match[3]) << 8 | 255) >>> 0;
      }
    }
    if (matchers.rgba) {
      if (match = matchers.rgba.exec(color)) {
        return (parse255(match[1]) << 24 | parse255(match[2]) << 16 | parse255(match[3]) << 8 | parse1(match[4])) >>> 0;
      }
    }
    if (matchers.hex3) {
      if (match = matchers.hex3.exec(color)) {
        return Number.parseInt(match[1] + match[1] + match[2] + match[2] + match[3] + match[3] + "ff", 16) >>> 0;
      }
    }
    if (matchers.hex8) {
      if (match = matchers.hex8.exec(color)) {
        return Number.parseInt(match[1], 16) >>> 0;
      }
    }
    if (matchers.hex4) {
      if (match = matchers.hex4.exec(color)) {
        return Number.parseInt(match[1] + match[1] + match[2] + match[2] + match[3] + match[3] + match[4] + match[4], 16) >>> 0;
      }
    }
    if (matchers.hsl) {
      if (match = matchers.hsl.exec(color)) {
        return (hslToRgb(parse360(match[1]), parsePercentage(match[2]), parsePercentage(match[3])) | 255) >>> 0;
      }
    }
    if (matchers.hsla) {
      if (match = matchers.hsla.exec(color)) {
        return (hslToRgb(parse360(match[1]), parsePercentage(match[2]), parsePercentage(match[3])) | parse1(match[4])) >>> 0;
      }
    }
    throw new Error(`invalid color string ${color} provided`);
  }
  function processColor(color) {
    const normalizedColor = normalizeColor(color);
    return (normalizedColor << 24 | normalizedColor >>> 8) >>> 0;
  }
  var proResProfileOptions = [
    "4444-xq",
    "4444",
    "hq",
    "standard",
    "light",
    "proxy"
  ];
  var ENABLE_V5_BREAKING_CHANGES2 = false;
  var validateFrame = ({
    allowFloats,
    durationInFrames,
    frame
  }) => {
    if (typeof frame === "undefined") {
      throw new TypeError(`Argument missing for parameter "frame"`);
    }
    if (typeof frame !== "number") {
      throw new TypeError(`Argument passed for "frame" is not a number: ${frame}`);
    }
    if (!Number.isFinite(frame)) {
      throw new RangeError(`Frame ${frame} is not finite`);
    }
    if (frame % 1 !== 0 && !allowFloats) {
      throw new RangeError(`Argument for frame must be an integer, but got ${frame}`);
    }
    if (frame < 0 && frame < -durationInFrames) {
      throw new RangeError(`Cannot use frame ${frame}: Duration of composition is ${durationInFrames}, therefore the lowest frame that can be rendered is ${-durationInFrames}`);
    }
    if (frame > durationInFrames - 1) {
      throw new RangeError(`Cannot use frame ${frame}: Duration of composition is ${durationInFrames}, therefore the highest frame that can be rendered is ${durationInFrames - 1}`);
    }
  };
  var validCodecs2 = [
    "h264",
    "h265",
    "vp8",
    "vp9",
    "mp3",
    "aac",
    "wav",
    "prores",
    "h264-mkv",
    "h264-ts",
    "gif"
  ];
  function validateCodec2(defaultCodec, location, name) {
    if (typeof defaultCodec === "undefined") {
      return;
    }
    if (typeof defaultCodec !== "string") {
      throw new TypeError(`The "${name}" prop ${location} must be a string, but you passed a value of type ${typeof defaultCodec}.`);
    }
    if (!validCodecs2.includes(defaultCodec)) {
      throw new Error(`The "${name}" prop ${location} must be one of ${validCodecs2.join(", ")}, but you passed ${defaultCodec}.`);
    }
  }
  var validateDefaultAndInputProps2 = (defaultProps, name, compositionId) => {
    if (!defaultProps) {
      return;
    }
    if (typeof defaultProps !== "object") {
      throw new Error(`"${name}" must be an object, but you passed a value of type ${typeof defaultProps}`);
    }
    if (Array.isArray(defaultProps)) {
      throw new Error(`"${name}" must be an object, an array was passed ${compositionId ? `for composition "${compositionId}"` : ""}`);
    }
  };
  function validateDimension2(amount, nameOfProp, location) {
    if (typeof amount !== "number") {
      throw new Error(`The "${nameOfProp}" prop ${location} must be a number, but you passed a value of type ${typeof amount}`);
    }
    if (isNaN(amount)) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must not be NaN, but is NaN.`);
    }
    if (!Number.isFinite(amount)) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be finite, but is ${amount}.`);
    }
    if (amount % 1 !== 0) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be an integer, but is ${amount}.`);
    }
    if (amount <= 0) {
      throw new TypeError(`The "${nameOfProp}" prop ${location} must be positive, but got ${amount}.`);
    }
  }
  function validateDurationInFrames2(durationInFrames, options) {
    const { allowFloats, component } = options;
    if (typeof durationInFrames === "undefined") {
      throw new Error(`The "durationInFrames" prop ${component} is missing.`);
    }
    if (typeof durationInFrames !== "number") {
      throw new Error(`The "durationInFrames" prop ${component} must be a number, but you passed a value of type ${typeof durationInFrames}`);
    }
    if (durationInFrames <= 0) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be positive, but got ${durationInFrames}.`);
    }
    if (!allowFloats && durationInFrames % 1 !== 0) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be an integer, but got ${durationInFrames}.`);
    }
    if (!Number.isFinite(durationInFrames)) {
      throw new TypeError(`The "durationInFrames" prop ${component} must be finite, but got ${durationInFrames}.`);
    }
  }
  function validateFps2(fps, location, isGif) {
    if (typeof fps !== "number") {
      throw new Error(`"fps" must be a number, but you passed a value of type ${typeof fps} ${location}`);
    }
    if (!Number.isFinite(fps)) {
      throw new Error(`"fps" must be a finite, but you passed ${fps} ${location}`);
    }
    if (isNaN(fps)) {
      throw new Error(`"fps" must not be NaN, but got ${fps} ${location}`);
    }
    if (fps <= 0) {
      throw new TypeError(`"fps" must be positive, but got ${fps} ${location}`);
    }
    if (isGif && fps > 50) {
      throw new TypeError(`The FPS for a GIF cannot be higher than 50. Use the --every-nth-frame option to lower the FPS: https://remotion.dev/docs/render-as-gif`);
    }
  }
  var getExpectedMediaFrameUncorrected2 = ({
    frame,
    playbackRate,
    startFrom
  }) => {
    return interpolate2(frame, [-1, startFrom, startFrom + 1], [-1, startFrom, startFrom + playbackRate]);
  };
  var getAbsoluteSrc2 = (relativeSrc) => {
    if (typeof window === "undefined") {
      return relativeSrc;
    }
    if (relativeSrc.startsWith("http://") || relativeSrc.startsWith("https://") || relativeSrc.startsWith("file://") || relativeSrc.startsWith("blob:") || relativeSrc.startsWith("data:")) {
      return relativeSrc;
    }
    return new URL(relativeSrc, window.origin).href;
  };
  var getOffthreadVideoSource2 = ({
    src,
    transparent,
    currentTime,
    toneMapped
  }) => {
    return `http://localhost:${window.remotion_proxyPort}/proxy?src=${encodeURIComponent(getAbsoluteSrc2(src))}&time=${encodeURIComponent(Math.max(0, currentTime))}&transparent=${String(transparent)}&toneMapped=${String(toneMapped)}`;
  };
  var NoReactInternals = {
    processColor,
    truthy: truthy2,
    validateFps: validateFps2,
    validateDimension: validateDimension2,
    validateDurationInFrames: validateDurationInFrames2,
    validateDefaultAndInputProps: validateDefaultAndInputProps2,
    validateFrame,
    serializeJSONWithSpecialTypes: serializeJSONWithSpecialTypes2,
    bundleName: "bundle.js",
    bundleMapName: "bundle.js.map",
    deserializeJSONWithSpecialTypes: deserializeJSONWithSpecialTypes2,
    DELAY_RENDER_CALLSTACK_TOKEN: DELAY_RENDER_CALLSTACK_TOKEN2,
    DELAY_RENDER_RETRY_TOKEN: DELAY_RENDER_RETRY_TOKEN2,
    DELAY_RENDER_CLEAR_TOKEN: DELAY_RENDER_CLEAR_TOKEN2,
    DELAY_RENDER_ATTEMPT_TOKEN: DELAY_RENDER_RETRIES_LEFT2,
    getOffthreadVideoSource: getOffthreadVideoSource2,
    getExpectedMediaFrameUncorrected: getExpectedMediaFrameUncorrected2,
    ENABLE_V5_BREAKING_CHANGES: ENABLE_V5_BREAKING_CHANGES2,
    MIN_NODE_VERSION: ENABLE_V5_BREAKING_CHANGES2 ? 18 : 16,
    MIN_BUN_VERSION: ENABLE_V5_BREAKING_CHANGES2 ? "1.1.3" : "1.0.3",
    colorNames,
    DATE_TOKEN: DATE_TOKEN2,
    FILE_TOKEN: FILE_TOKEN2,
    validateCodec: validateCodec2,
    proResProfileOptions
  };

  // node_modules/@remotion/player/dist/esm/index.mjs
  var import_jsx_runtime51 = __toESM(require_jsx_runtime(), 1);
  var import_react98 = __toESM(require_react(), 1);
  var import_react99 = __toESM(require_react(), 1);
  var import_react100 = __toESM(require_react(), 1);
  var import_jsx_runtime52 = __toESM(require_jsx_runtime(), 1);
  var import_jsx_runtime53 = __toESM(require_jsx_runtime(), 1);
  var ICON_SIZE2 = 25;
  var fullscreenIconSize = 16;
  var PlayIcon = () => {
    return /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("svg", {
      width: ICON_SIZE2,
      height: ICON_SIZE2,
      viewBox: "0 0 25 25",
      fill: "none",
      children: /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
        d: "M8 6.375C7.40904 8.17576 7.06921 10.2486 7.01438 12.3871C6.95955 14.5255 7.19163 16.6547 7.6875 18.5625C9.95364 18.2995 12.116 17.6164 14.009 16.5655C15.902 15.5147 17.4755 14.124 18.6088 12.5C17.5158 10.8949 15.9949 9.51103 14.1585 8.45082C12.3222 7.3906 10.2174 6.68116 8 6.375Z",
        fill: "white",
        stroke: "white",
        strokeWidth: "6.25",
        strokeLinejoin: "round"
      })
    });
  };
  var PauseIcon = () => {
    return /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)("svg", {
      viewBox: "0 0 100 100",
      width: ICON_SIZE2,
      height: ICON_SIZE2,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("rect", {
          x: "25",
          y: "20",
          width: "20",
          height: "60",
          fill: "#fff",
          ry: "5",
          rx: "5"
        }),
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("rect", {
          x: "55",
          y: "20",
          width: "20",
          height: "60",
          fill: "#fff",
          ry: "5",
          rx: "5"
        })
      ]
    });
  };
  var FullscreenIcon = ({
    isFullscreen
  }) => {
    const strokeWidth = 6;
    const viewSize = 32;
    const out = isFullscreen ? 0 : strokeWidth / 2;
    const middleInset = isFullscreen ? strokeWidth * 1.6 : strokeWidth / 2;
    const inset = isFullscreen ? strokeWidth * 1.6 : strokeWidth * 2;
    return /* @__PURE__ */ (0, import_jsx_runtime37.jsxs)("svg", {
      viewBox: `0 0 ${viewSize} ${viewSize}`,
      height: fullscreenIconSize,
      width: fullscreenIconSize,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
          d: `
				M ${out} ${inset}
				L ${middleInset} ${middleInset}
				L ${inset} ${out}
				`,
          stroke: "#fff",
          strokeWidth,
          fill: "none"
        }),
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
          d: `
				M ${viewSize - out} ${inset}
				L ${viewSize - middleInset} ${middleInset}
				L ${viewSize - inset} ${out}
				`,
          stroke: "#fff",
          strokeWidth,
          fill: "none"
        }),
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
          d: `
				M ${out} ${viewSize - inset}
				L ${middleInset} ${viewSize - middleInset}
				L ${inset} ${viewSize - out}
				`,
          stroke: "#fff",
          strokeWidth,
          fill: "none"
        }),
        /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
          d: `
				M ${viewSize - out} ${viewSize - inset}
				L ${viewSize - middleInset} ${viewSize - middleInset}
				L ${viewSize - inset} ${viewSize - out}
				`,
          stroke: "#fff",
          strokeWidth,
          fill: "none"
        })
      ]
    });
  };
  var VolumeOffIcon = () => {
    return /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("svg", {
      width: ICON_SIZE2,
      height: ICON_SIZE2,
      viewBox: "0 0 24 24",
      children: /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
        d: "M3.63 3.63a.996.996 0 000 1.41L7.29 8.7 7 9H4c-.55 0-1 .45-1 1v4c0 .55.45 1 1 1h3l3.29 3.29c.63.63 1.71.18 1.71-.71v-4.17l4.18 4.18c-.49.37-1.02.68-1.6.91-.36.15-.58.53-.58.92 0 .72.73 1.18 1.39.91.8-.33 1.55-.77 2.22-1.31l1.34 1.34a.996.996 0 101.41-1.41L5.05 3.63c-.39-.39-1.02-.39-1.42 0zM19 12c0 .82-.15 1.61-.41 2.34l1.53 1.53c.56-1.17.88-2.48.88-3.87 0-3.83-2.4-7.11-5.78-8.4-.59-.23-1.22.23-1.22.86v.19c0 .38.25.71.61.85C17.18 6.54 19 9.06 19 12zm-8.71-6.29l-.17.17L12 7.76V6.41c0-.89-1.08-1.33-1.71-.7zM16.5 12A4.5 4.5 0 0014 7.97v1.79l2.48 2.48c.01-.08.02-.16.02-.24z",
        fill: "#fff"
      })
    });
  };
  var VolumeOnIcon = () => {
    return /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("svg", {
      width: ICON_SIZE2,
      height: ICON_SIZE2,
      viewBox: "0 0 24 24",
      children: /* @__PURE__ */ (0, import_jsx_runtime37.jsx)("path", {
        d: "M3 10v4c0 .55.45 1 1 1h3l3.29 3.29c.63.63 1.71.18 1.71-.71V6.41c0-.89-1.08-1.34-1.71-.71L7 9H4c-.55 0-1 .45-1 1zm13.5 2A4.5 4.5 0 0014 7.97v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 4.45v.2c0 .38.25.71.6.85C17.18 6.53 19 9.06 19 12s-1.82 5.47-4.4 6.5c-.36.14-.6.47-.6.85v.2c0 .63.63 1.07 1.21.85C18.6 19.11 21 15.84 21 12s-2.4-7.11-5.79-8.4c-.58-.23-1.21.22-1.21.85z",
        fill: "#fff"
      })
    });
  };
  var className = "__remotion_buffering_indicator";
  var remotionBufferingAnimation = "__remotion_buffering_animation";
  var playerStyle = {
    width: ICON_SIZE2,
    height: ICON_SIZE2,
    overflow: "hidden",
    lineHeight: "normal",
    fontSize: "inherit"
  };
  var studioStyle = {
    width: 14,
    height: 14,
    overflow: "hidden",
    lineHeight: "normal",
    fontSize: "inherit"
  };
  var BufferingIndicator = ({ type }) => {
    const style2 = type === "player" ? playerStyle : studioStyle;
    return /* @__PURE__ */ (0, import_jsx_runtime38.jsxs)(import_jsx_runtime38.Fragment, {
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("style", {
          type: "text/css",
          children: `
				@keyframes ${remotionBufferingAnimation} {
          0% {
            rotate: 0deg;
          }
          100% {
            rotate: 360deg;
          }
        }
        
        .${className} {
            animation: ${remotionBufferingAnimation} 1s linear infinite;
        }        
			`
        }),
        /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("div", {
          style: style2,
          children: /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("svg", {
            viewBox: type === "player" ? "0 0 22 22" : "0 0 18 18",
            style: style2,
            className,
            children: /* @__PURE__ */ (0, import_jsx_runtime38.jsx)("path", {
              d: type === "player" ? "M 11 4 A 7 7 0 0 1 15.1145 16.66312" : "M 9 2 A 7 7 0 0 1 13.1145 14.66312",
              stroke: "white",
              strokeLinecap: "round",
              fill: "none",
              strokeWidth: 3
            })
          })
        })
      ]
    });
  };
  var calculatePlayerSize = ({
    currentSize,
    width,
    height,
    compositionWidth,
    compositionHeight
  }) => {
    if (width !== void 0 && height === void 0) {
      return {
        aspectRatio: [compositionWidth, compositionHeight].join("/")
      };
    }
    if (height !== void 0 && width === void 0) {
      return {
        aspectRatio: [compositionWidth, compositionHeight].join("/")
      };
    }
    if (!currentSize) {
      return {
        width: compositionWidth,
        height: compositionHeight
      };
    }
    return {
      width: compositionWidth,
      height: compositionHeight
    };
  };
  var calculateCanvasTransformation = ({
    previewSize,
    compositionWidth,
    compositionHeight,
    canvasSize
  }) => {
    const scale = Internals.calculateScale({
      canvasSize,
      compositionHeight,
      compositionWidth,
      previewSize
    });
    const correction = 0 - (1 - scale) / 2;
    const xCorrection = correction * compositionWidth;
    const yCorrection = correction * compositionHeight;
    const width = compositionWidth * scale;
    const height = compositionHeight * scale;
    const centerX = canvasSize.width / 2 - width / 2;
    const centerY = canvasSize.height / 2 - height / 2;
    return {
      centerX,
      centerY,
      xCorrection,
      yCorrection,
      scale
    };
  };
  var calculateOuterStyle = ({
    config,
    style: style2,
    canvasSize,
    overflowVisible,
    layout
  }) => {
    if (!config) {
      return {};
    }
    return {
      position: "relative",
      overflow: overflowVisible ? "visible" : "hidden",
      ...calculatePlayerSize({
        compositionHeight: config.height,
        compositionWidth: config.width,
        currentSize: canvasSize,
        height: style2?.height,
        width: style2?.width
      }),
      opacity: layout ? 1 : 0,
      ...style2
    };
  };
  var calculateContainerStyle = ({
    config,
    layout,
    scale,
    overflowVisible
  }) => {
    if (!config) {
      return {};
    }
    if (!layout) {
      return {
        position: "absolute",
        width: config.width,
        height: config.height,
        display: "flex",
        transform: `scale(${scale})`,
        overflow: overflowVisible ? "visible" : "hidden"
      };
    }
    return {
      position: "absolute",
      width: config.width,
      height: config.height,
      display: "flex",
      transform: `scale(${scale})`,
      marginLeft: layout.xCorrection,
      marginTop: layout.yCorrection,
      overflow: overflowVisible ? "visible" : "hidden"
    };
  };
  var calculateOuter = ({
    layout,
    scale,
    config,
    overflowVisible
  }) => {
    if (!config) {
      return {};
    }
    if (!layout) {
      return {
        width: config.width * scale,
        height: config.height * scale,
        display: "flex",
        flexDirection: "column",
        position: "absolute",
        overflow: overflowVisible ? "visible" : "hidden"
      };
    }
    const { centerX, centerY } = layout;
    return {
      width: config.width * scale,
      height: config.height * scale,
      display: "flex",
      flexDirection: "column",
      position: "absolute",
      left: centerX,
      top: centerY,
      overflow: overflowVisible ? "visible" : "hidden"
    };
  };
  var PlayerEventEmitterContext = import_react73.default.createContext(void 0);
  var ThumbnailEmitterContext = import_react73.default.createContext(void 0);
  var PlayerEmitter = class {
    constructor() {
      __publicField(this, "listeners", {
        ended: [],
        error: [],
        pause: [],
        play: [],
        ratechange: [],
        scalechange: [],
        seeked: [],
        timeupdate: [],
        frameupdate: [],
        fullscreenchange: [],
        volumechange: [],
        mutechange: [],
        waiting: [],
        resume: []
      });
      __publicField(this, "dispatchSeek", (frame) => {
        this.dispatchEvent("seeked", {
          frame
        });
      });
      __publicField(this, "dispatchVolumeChange", (volume) => {
        this.dispatchEvent("volumechange", {
          volume
        });
      });
      __publicField(this, "dispatchPause", () => {
        this.dispatchEvent("pause", void 0);
      });
      __publicField(this, "dispatchPlay", () => {
        this.dispatchEvent("play", void 0);
      });
      __publicField(this, "dispatchEnded", () => {
        this.dispatchEvent("ended", void 0);
      });
      __publicField(this, "dispatchRateChange", (playbackRate) => {
        this.dispatchEvent("ratechange", {
          playbackRate
        });
      });
      __publicField(this, "dispatchScaleChange", (scale) => {
        this.dispatchEvent("scalechange", {
          scale
        });
      });
      __publicField(this, "dispatchError", (error2) => {
        this.dispatchEvent("error", {
          error: error2
        });
      });
      __publicField(this, "dispatchTimeUpdate", (event) => {
        this.dispatchEvent("timeupdate", event);
      });
      __publicField(this, "dispatchFrameUpdate", (event) => {
        this.dispatchEvent("frameupdate", event);
      });
      __publicField(this, "dispatchFullscreenChange", (event) => {
        this.dispatchEvent("fullscreenchange", event);
      });
      __publicField(this, "dispatchMuteChange", (event) => {
        this.dispatchEvent("mutechange", event);
      });
      __publicField(this, "dispatchWaiting", (event) => {
        this.dispatchEvent("waiting", event);
      });
      __publicField(this, "dispatchResume", (event) => {
        this.dispatchEvent("resume", event);
      });
    }
    addEventListener(name, callback) {
      this.listeners[name].push(callback);
    }
    removeEventListener(name, callback) {
      this.listeners[name] = this.listeners[name].filter((l) => l !== callback);
    }
    dispatchEvent(dispatchName, context) {
      this.listeners[dispatchName].forEach((callback) => {
        callback({ detail: context });
      });
    }
  };
  var ThumbnailEmitter = class {
    constructor() {
      __publicField(this, "listeners", {
        error: [],
        waiting: [],
        resume: []
      });
      __publicField(this, "dispatchError", (error2) => {
        this.dispatchEvent("error", {
          error: error2
        });
      });
      __publicField(this, "dispatchWaiting", (event) => {
        this.dispatchEvent("waiting", event);
      });
      __publicField(this, "dispatchResume", (event) => {
        this.dispatchEvent("resume", event);
      });
    }
    addEventListener(name, callback) {
      this.listeners[name].push(callback);
    }
    removeEventListener(name, callback) {
      this.listeners[name] = this.listeners[name].filter((l) => l !== callback);
    }
    dispatchEvent(dispatchName, context) {
      this.listeners[dispatchName].forEach((callback) => {
        callback({ detail: context });
      });
    }
  };
  var useBufferStateEmitter = (emitter) => {
    const bufferManager = (0, import_react75.useContext)(Internals.BufferingContextReact);
    if (!bufferManager) {
      throw new Error("BufferingContextReact not found");
    }
    (0, import_react75.useLayoutEffect)(() => {
      const clear1 = bufferManager.listenForBuffering(() => {
        bufferManager.buffering.current = true;
        emitter.dispatchWaiting({});
      });
      const clear2 = bufferManager.listenForResume(() => {
        bufferManager.buffering.current = false;
        emitter.dispatchResume({});
      });
      return () => {
        clear1.remove();
        clear2.remove();
      };
    }, [bufferManager, emitter]);
  };
  var PlayerEmitterProvider = ({ children, currentPlaybackRate }) => {
    const [emitter] = (0, import_react74.useState)(() => new PlayerEmitter());
    const bufferManager = (0, import_react74.useContext)(Internals.BufferingContextReact);
    if (!bufferManager) {
      throw new Error("BufferingContextReact not found");
    }
    (0, import_react74.useEffect)(() => {
      if (currentPlaybackRate) {
        emitter.dispatchRateChange(currentPlaybackRate);
      }
    }, [emitter, currentPlaybackRate]);
    useBufferStateEmitter(emitter);
    return /* @__PURE__ */ (0, import_jsx_runtime39.jsx)(PlayerEventEmitterContext.Provider, {
      value: emitter,
      children
    });
  };
  var useHoverState = (ref, hideControlsWhenPointerDoesntMove) => {
    const [hovered, setHovered] = (0, import_react77.useState)(false);
    (0, import_react77.useEffect)(() => {
      const { current } = ref;
      if (!current) {
        return;
      }
      let hoverTimeout;
      const addHoverTimeout = () => {
        if (hideControlsWhenPointerDoesntMove) {
          clearTimeout(hoverTimeout);
          hoverTimeout = setTimeout(() => {
            setHovered(false);
          }, hideControlsWhenPointerDoesntMove === true ? 3e3 : hideControlsWhenPointerDoesntMove);
        }
      };
      const onHover = () => {
        setHovered(true);
        addHoverTimeout();
      };
      const onLeave = () => {
        setHovered(false);
        clearTimeout(hoverTimeout);
      };
      const onMove = () => {
        setHovered(true);
        addHoverTimeout();
      };
      current.addEventListener("mouseenter", onHover);
      current.addEventListener("mouseleave", onLeave);
      current.addEventListener("mousemove", onMove);
      return () => {
        current.removeEventListener("mouseenter", onHover);
        current.removeEventListener("mouseleave", onLeave);
        current.removeEventListener("mousemove", onMove);
        clearTimeout(hoverTimeout);
      };
    }, [hideControlsWhenPointerDoesntMove, ref]);
    return hovered;
  };
  var usePlayer = () => {
    const [playing, setPlaying, imperativePlaying] = Internals.Timeline.usePlayingState();
    const [hasPlayed, setHasPlayed] = (0, import_react80.useState)(false);
    const frame = Internals.Timeline.useTimelinePosition();
    const playStart = (0, import_react80.useRef)(frame);
    const setFrame = Internals.Timeline.useTimelineSetFrame();
    const setTimelinePosition = Internals.Timeline.useTimelineSetFrame();
    const audioContext = (0, import_react80.useContext)(Internals.SharedAudioContext);
    const { audioAndVideoTags } = (0, import_react80.useContext)(Internals.TimelineContext);
    const frameRef = (0, import_react80.useRef)(frame);
    frameRef.current = frame;
    const video = Internals.useVideo();
    const config = Internals.useUnsafeVideoConfig();
    const emitter = (0, import_react80.useContext)(PlayerEventEmitterContext);
    const lastFrame = (config?.durationInFrames ?? 1) - 1;
    const isLastFrame = frame === lastFrame;
    const isFirstFrame = frame === 0;
    if (!emitter) {
      throw new TypeError("Expected Player event emitter context");
    }
    const bufferingContext = (0, import_react80.useContext)(Internals.BufferingContextReact);
    if (!bufferingContext) {
      throw new Error("Missing the buffering context. Most likely you have a Remotion version mismatch.");
    }
    const { buffering } = bufferingContext;
    const seek2 = (0, import_react80.useCallback)((newFrame) => {
      if (video?.id) {
        setTimelinePosition((c2) => ({ ...c2, [video.id]: newFrame }));
      }
      frameRef.current = newFrame;
      emitter.dispatchSeek(newFrame);
    }, [emitter, setTimelinePosition, video?.id]);
    const play = (0, import_react80.useCallback)((e) => {
      if (imperativePlaying.current) {
        return;
      }
      setHasPlayed(true);
      if (isLastFrame) {
        seek2(0);
      }
      audioContext?.audioContext?.resume();
      if (audioContext && audioContext.numberOfAudioTags > 0 && e) {
        audioContext.playAllAudios();
      }
      audioAndVideoTags.current.forEach((a2) => a2.play("player play() was called and playing audio from a click"));
      imperativePlaying.current = true;
      setPlaying(true);
      playStart.current = frameRef.current;
      emitter.dispatchPlay();
    }, [
      imperativePlaying,
      isLastFrame,
      audioContext,
      setPlaying,
      emitter,
      seek2,
      audioAndVideoTags
    ]);
    const pause = (0, import_react80.useCallback)(() => {
      if (imperativePlaying.current) {
        imperativePlaying.current = false;
        setPlaying(false);
        emitter.dispatchPause();
        audioContext?.audioContext?.suspend();
      }
    }, [emitter, imperativePlaying, setPlaying, audioContext]);
    const pauseAndReturnToPlayStart = (0, import_react80.useCallback)(() => {
      if (imperativePlaying.current) {
        imperativePlaying.current = false;
        frameRef.current = playStart.current;
        if (config) {
          setTimelinePosition((c2) => ({
            ...c2,
            [config.id]: playStart.current
          }));
          setPlaying(false);
          emitter.dispatchPause();
        }
      }
    }, [config, emitter, imperativePlaying, setPlaying, setTimelinePosition]);
    const videoId = video?.id;
    const frameBack = (0, import_react80.useCallback)((frames) => {
      if (!videoId) {
        return null;
      }
      if (imperativePlaying.current) {
        return;
      }
      setFrame((c2) => {
        const prevFrame = c2[videoId] ?? window.remotion_initialFrame ?? 0;
        const newFrame = Math.max(0, prevFrame - frames);
        if (prevFrame === newFrame) {
          return c2;
        }
        return {
          ...c2,
          [videoId]: newFrame
        };
      });
    }, [imperativePlaying, setFrame, videoId]);
    const frameForward = (0, import_react80.useCallback)((frames) => {
      if (!videoId) {
        return null;
      }
      if (imperativePlaying.current) {
        return;
      }
      setFrame((c2) => {
        const prevFrame = c2[videoId] ?? window.remotion_initialFrame ?? 0;
        const newFrame = Math.min(lastFrame, prevFrame + frames);
        if (prevFrame === newFrame) {
          return c2;
        }
        return {
          ...c2,
          [videoId]: newFrame
        };
      });
    }, [videoId, imperativePlaying, lastFrame, setFrame]);
    const toggle = (0, import_react80.useCallback)((e) => {
      if (imperativePlaying.current) {
        pause();
      } else {
        play(e);
      }
    }, [imperativePlaying, pause, play]);
    const isPlaying = (0, import_react80.useCallback)(() => {
      return imperativePlaying.current;
    }, [imperativePlaying]);
    const getCurrentFrame = (0, import_react80.useCallback)(() => {
      return frameRef.current;
    }, [frameRef]);
    const isBuffering = (0, import_react80.useCallback)(() => {
      return buffering.current;
    }, [buffering]);
    const returnValue = (0, import_react80.useMemo)(() => {
      return {
        frameBack,
        frameForward,
        isLastFrame,
        emitter,
        playing,
        play,
        pause,
        seek: seek2,
        isFirstFrame,
        getCurrentFrame,
        isPlaying,
        isBuffering,
        pauseAndReturnToPlayStart,
        hasPlayed,
        toggle
      };
    }, [
      emitter,
      frameBack,
      frameForward,
      hasPlayed,
      isFirstFrame,
      isLastFrame,
      getCurrentFrame,
      pause,
      pauseAndReturnToPlayStart,
      play,
      playing,
      seek2,
      toggle,
      isPlaying,
      isBuffering
    ]);
    return returnValue;
  };
  var useBrowserMediaSession = ({
    browserMediaControlsBehavior,
    videoConfig,
    playbackRate
  }) => {
    const { playing, pause, play, emitter, getCurrentFrame, seek: seek2 } = usePlayer();
    (0, import_react79.useEffect)(() => {
      if (!navigator.mediaSession) {
        return;
      }
      if (browserMediaControlsBehavior.mode === "do-nothing") {
        return;
      }
      if (playing) {
        navigator.mediaSession.playbackState = "playing";
      } else {
        navigator.mediaSession.playbackState = "paused";
      }
    }, [browserMediaControlsBehavior.mode, playing]);
    (0, import_react79.useEffect)(() => {
      if (!navigator.mediaSession) {
        return;
      }
      if (browserMediaControlsBehavior.mode === "do-nothing") {
        return;
      }
      const onTimeUpdate = () => {
        if (!videoConfig) {
          return;
        }
        if (navigator.mediaSession) {
          navigator.mediaSession.setPositionState({
            duration: videoConfig.durationInFrames / videoConfig.fps,
            playbackRate,
            position: getCurrentFrame() / videoConfig.fps
          });
        }
      };
      emitter.addEventListener("timeupdate", onTimeUpdate);
      return () => {
        emitter.removeEventListener("timeupdate", onTimeUpdate);
      };
    }, [
      browserMediaControlsBehavior.mode,
      emitter,
      getCurrentFrame,
      playbackRate,
      videoConfig
    ]);
    (0, import_react79.useEffect)(() => {
      if (!navigator.mediaSession) {
        return;
      }
      if (browserMediaControlsBehavior.mode === "do-nothing") {
        return;
      }
      navigator.mediaSession.setActionHandler("play", () => {
        if (browserMediaControlsBehavior.mode === "register-media-session") {
          play();
        }
      });
      navigator.mediaSession.setActionHandler("pause", () => {
        if (browserMediaControlsBehavior.mode === "register-media-session") {
          pause();
        }
      });
      navigator.mediaSession.setActionHandler("seekto", (event) => {
        if (browserMediaControlsBehavior.mode === "register-media-session" && event.seekTime !== void 0 && videoConfig) {
          seek2(Math.round(event.seekTime * videoConfig.fps));
        }
      });
      navigator.mediaSession.setActionHandler("seekbackward", () => {
        if (browserMediaControlsBehavior.mode === "register-media-session" && videoConfig) {
          seek2(Math.max(0, Math.round((getCurrentFrame() - 10) * videoConfig.fps)));
        }
      });
      navigator.mediaSession.setActionHandler("seekforward", () => {
        if (browserMediaControlsBehavior.mode === "register-media-session" && videoConfig) {
          seek2(Math.max(videoConfig.durationInFrames - 1, Math.round((getCurrentFrame() + 10) * videoConfig.fps)));
        }
      });
      navigator.mediaSession.setActionHandler("previoustrack", () => {
        if (browserMediaControlsBehavior.mode === "register-media-session") {
          seek2(0);
        }
      });
      return () => {
        navigator.mediaSession.metadata = null;
        navigator.mediaSession.setActionHandler("play", null);
        navigator.mediaSession.setActionHandler("pause", null);
        navigator.mediaSession.setActionHandler("seekto", null);
        navigator.mediaSession.setActionHandler("seekbackward", null);
        navigator.mediaSession.setActionHandler("seekforward", null);
        navigator.mediaSession.setActionHandler("previoustrack", null);
      };
    }, [
      browserMediaControlsBehavior.mode,
      getCurrentFrame,
      pause,
      play,
      seek2,
      videoConfig
    ]);
  };
  var calculateNextFrame = ({
    time,
    currentFrame: startFrame,
    playbackSpeed,
    fps,
    actualLastFrame,
    actualFirstFrame,
    framesAdvanced,
    shouldLoop
  }) => {
    const op = playbackSpeed < 0 ? Math.ceil : Math.floor;
    const framesToAdvance = op(time * playbackSpeed / (1e3 / fps)) - framesAdvanced;
    const nextFrame = framesToAdvance + startFrame;
    const isCurrentFrameOutside = startFrame > actualLastFrame || startFrame < actualFirstFrame;
    const isNextFrameOutside = nextFrame > actualLastFrame || nextFrame < actualFirstFrame;
    const hasEnded = !shouldLoop && isNextFrameOutside && !isCurrentFrameOutside;
    if (playbackSpeed > 0) {
      if (isNextFrameOutside) {
        return {
          nextFrame: actualFirstFrame,
          framesToAdvance,
          hasEnded
        };
      }
      return { nextFrame, framesToAdvance, hasEnded };
    }
    if (isNextFrameOutside) {
      return { nextFrame: actualLastFrame, framesToAdvance, hasEnded };
    }
    return { nextFrame, framesToAdvance, hasEnded };
  };
  var getIsBackgrounded = () => {
    if (typeof document === "undefined") {
      return false;
    }
    return document.visibilityState === "hidden";
  };
  var useIsBackgrounded = () => {
    const isBackgrounded = (0, import_react81.useRef)(getIsBackgrounded());
    (0, import_react81.useEffect)(() => {
      const onVisibilityChange = () => {
        isBackgrounded.current = getIsBackgrounded();
      };
      document.addEventListener("visibilitychange", onVisibilityChange);
      return () => {
        document.removeEventListener("visibilitychange", onVisibilityChange);
      };
    }, []);
    return isBackgrounded;
  };
  var usePlayback = ({
    loop,
    playbackRate,
    moveToBeginningWhenEnded,
    inFrame,
    outFrame,
    browserMediaControlsBehavior,
    getCurrentFrame
  }) => {
    const config = Internals.useUnsafeVideoConfig();
    const frame = Internals.Timeline.useTimelinePosition();
    const { playing, pause, emitter, isPlaying } = usePlayer();
    const setFrame = Internals.Timeline.useTimelineSetFrame();
    const isBackgroundedRef = useIsBackgrounded();
    const lastTimeUpdateEvent = (0, import_react78.useRef)(null);
    const context = (0, import_react78.useContext)(Internals.BufferingContextReact);
    if (!context) {
      throw new Error("Missing the buffering context. Most likely you have a Remotion version mismatch.");
    }
    useBrowserMediaSession({
      browserMediaControlsBehavior,
      playbackRate,
      videoConfig: config
    });
    (0, import_react78.useEffect)(() => {
      if (!config) {
        return;
      }
      if (!playing) {
        return;
      }
      let hasBeenStopped = false;
      let reqAnimFrameCall = null;
      let startedTime = performance.now();
      let framesAdvanced = 0;
      const cancelQueuedFrame = () => {
        if (reqAnimFrameCall !== null) {
          if (reqAnimFrameCall.type === "raf") {
            cancelAnimationFrame(reqAnimFrameCall.id);
          } else {
            clearTimeout(reqAnimFrameCall.id);
          }
        }
      };
      const stop = () => {
        hasBeenStopped = true;
        cancelQueuedFrame();
      };
      const callback = () => {
        if (hasBeenStopped) {
          return;
        }
        if (!isPlaying()) {
          return;
        }
        const time = performance.now() - startedTime;
        const actualLastFrame = outFrame ?? config.durationInFrames - 1;
        const actualFirstFrame = inFrame ?? 0;
        const currentFrame = getCurrentFrame();
        const { nextFrame, framesToAdvance, hasEnded } = calculateNextFrame({
          time,
          currentFrame,
          playbackSpeed: playbackRate,
          fps: config.fps,
          actualFirstFrame,
          actualLastFrame,
          framesAdvanced,
          shouldLoop: loop
        });
        framesAdvanced += framesToAdvance;
        if (nextFrame !== getCurrentFrame() && (!hasEnded || moveToBeginningWhenEnded)) {
          setFrame((c2) => ({ ...c2, [config.id]: nextFrame }));
        }
        if (hasEnded) {
          stop();
          pause();
          emitter.dispatchEnded();
          return;
        }
        queueNextFrame();
      };
      const queueNextFrame = () => {
        if (context.buffering.current) {
          const stopListening = context.listenForResume(() => {
            stopListening.remove();
            startedTime = performance.now();
            framesAdvanced = 0;
            queueNextFrame();
          });
          return;
        }
        if (isBackgroundedRef.current) {
          reqAnimFrameCall = {
            type: "timeout",
            id: setTimeout(callback, 1e3 / config.fps)
          };
          return;
        }
        reqAnimFrameCall = { type: "raf", id: requestAnimationFrame(callback) };
      };
      queueNextFrame();
      const onVisibilityChange = () => {
        if (document.visibilityState === "visible") {
          return;
        }
        cancelQueuedFrame();
        callback();
      };
      window.addEventListener("visibilitychange", onVisibilityChange);
      return () => {
        window.removeEventListener("visibilitychange", onVisibilityChange);
        stop();
      };
    }, [
      config,
      loop,
      pause,
      playing,
      setFrame,
      emitter,
      playbackRate,
      inFrame,
      outFrame,
      moveToBeginningWhenEnded,
      isBackgroundedRef,
      getCurrentFrame,
      context,
      isPlaying
    ]);
    (0, import_react78.useEffect)(() => {
      const interval = setInterval(() => {
        if (lastTimeUpdateEvent.current === getCurrentFrame()) {
          return;
        }
        emitter.dispatchTimeUpdate({ frame: getCurrentFrame() });
        lastTimeUpdateEvent.current = getCurrentFrame();
      }, 250);
      return () => clearInterval(interval);
    }, [emitter, getCurrentFrame]);
    (0, import_react78.useEffect)(() => {
      emitter.dispatchFrameUpdate({ frame });
    }, [emitter, frame]);
  };
  var elementSizeHooks = [];
  var useElementSize = (ref, options) => {
    const [size, setSize] = (0, import_react82.useState)(() => {
      if (!ref.current) {
        return null;
      }
      const rect = ref.current.getClientRects();
      if (!rect[0]) {
        return null;
      }
      return {
        width: rect[0].width,
        height: rect[0].height,
        left: rect[0].x,
        top: rect[0].y,
        windowSize: {
          height: window.innerHeight,
          width: window.innerWidth
        }
      };
    });
    const observer = (0, import_react82.useMemo)(() => {
      if (typeof ResizeObserver === "undefined") {
        return null;
      }
      return new ResizeObserver((entries) => {
        const { contentRect, target } = entries[0];
        const newSize = target.getClientRects();
        if (!newSize?.[0]) {
          setSize(null);
          return;
        }
        const probableCssParentScale = contentRect.width === 0 ? 1 : newSize[0].width / contentRect.width;
        const width = options.shouldApplyCssTransforms || probableCssParentScale === 0 ? newSize[0].width : newSize[0].width * (1 / probableCssParentScale);
        const height = options.shouldApplyCssTransforms || probableCssParentScale === 0 ? newSize[0].height : newSize[0].height * (1 / probableCssParentScale);
        setSize((prevState) => {
          const isSame = prevState && prevState.width === width && prevState.height === height && prevState.left === newSize[0].x && prevState.top === newSize[0].y && prevState.windowSize.height === window.innerHeight && prevState.windowSize.width === window.innerWidth;
          if (isSame) {
            return prevState;
          }
          return {
            width,
            height,
            left: newSize[0].x,
            top: newSize[0].y,
            windowSize: {
              height: window.innerHeight,
              width: window.innerWidth
            }
          };
        });
      });
    }, [options.shouldApplyCssTransforms]);
    const updateSize = (0, import_react82.useCallback)(() => {
      if (!ref.current) {
        return;
      }
      const rect = ref.current.getClientRects();
      if (!rect[0]) {
        setSize(null);
        return;
      }
      setSize((prevState) => {
        const isSame = prevState && prevState.width === rect[0].width && prevState.height === rect[0].height && prevState.left === rect[0].x && prevState.top === rect[0].y && prevState.windowSize.height === window.innerHeight && prevState.windowSize.width === window.innerWidth;
        if (isSame) {
          return prevState;
        }
        return {
          width: rect[0].width,
          height: rect[0].height,
          left: rect[0].x,
          top: rect[0].y,
          windowSize: {
            height: window.innerHeight,
            width: window.innerWidth
          }
        };
      });
    }, [ref]);
    (0, import_react82.useEffect)(() => {
      if (!observer) {
        return;
      }
      const { current } = ref;
      if (current) {
        observer.observe(current);
      }
      return () => {
        if (current) {
          observer.unobserve(current);
        }
      };
    }, [observer, ref, updateSize]);
    (0, import_react82.useEffect)(() => {
      if (!options.triggerOnWindowResize) {
        return;
      }
      window.addEventListener("resize", updateSize);
      return () => {
        window.removeEventListener("resize", updateSize);
      };
    }, [options.triggerOnWindowResize, updateSize]);
    (0, import_react82.useEffect)(() => {
      elementSizeHooks.push(updateSize);
      return () => {
        elementSizeHooks = elementSizeHooks.filter((e) => e !== updateSize);
      };
    }, [updateSize]);
    return (0, import_react82.useMemo)(() => {
      if (!size) {
        return null;
      }
      return { ...size, refresh: updateSize };
    }, [size, updateSize]);
  };
  var DefaultPlayPauseButton = ({ playing, buffering }) => {
    if (playing && buffering) {
      return /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(BufferingIndicator, {
        type: "player"
      });
    }
    if (playing) {
      return /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(PauseIcon, {});
    }
    return /* @__PURE__ */ (0, import_jsx_runtime40.jsx)(PlayIcon, {});
  };
  var KNOB_SIZE = 12;
  var BAR_HEIGHT = 5;
  var DefaultVolumeSlider = ({
    volume,
    isVertical,
    onBlur,
    inputRef,
    setVolume
  }) => {
    const sliderContainer = (0, import_react87.useMemo)(() => {
      const paddingLeft = 5;
      const common = {
        paddingLeft,
        height: ICON_SIZE2,
        width: VOLUME_SLIDER_WIDTH,
        display: "inline-flex",
        alignItems: "center"
      };
      if (isVertical) {
        return {
          ...common,
          position: "absolute",
          transform: `rotate(-90deg) translateX(${VOLUME_SLIDER_WIDTH / 2 + ICON_SIZE2 / 2}px)`
        };
      }
      return {
        ...common
      };
    }, [isVertical]);
    const randomId = typeof import_react87.default.useId === "undefined" ? "volume-slider" : import_react87.default.useId();
    const [randomClass] = (0, import_react87.useState)(() => `__remotion-volume-slider-${random(randomId)}`.replace(".", ""));
    const onVolumeChange = (0, import_react87.useCallback)((e) => {
      setVolume(parseFloat(e.target.value));
    }, [setVolume]);
    const inputStyle2 = (0, import_react87.useMemo)(() => {
      const commonStyle = {
        WebkitAppearance: "none",
        backgroundColor: "rgba(255, 255, 255, 0.5)",
        borderRadius: BAR_HEIGHT / 2,
        cursor: "pointer",
        height: BAR_HEIGHT,
        width: VOLUME_SLIDER_WIDTH,
        backgroundImage: `linear-gradient(
				to right,
				white ${volume * 100}%, rgba(255, 255, 255, 0) ${volume * 100}%
			)`
      };
      if (isVertical) {
        return {
          ...commonStyle,
          bottom: ICON_SIZE2 + VOLUME_SLIDER_WIDTH / 2
        };
      }
      return commonStyle;
    }, [isVertical, volume]);
    const sliderStyle = `
	.${randomClass}::-webkit-slider-thumb {
		-webkit-appearance: none;
		background-color: white;
		border-radius: ${KNOB_SIZE / 2}px;
		box-shadow: 0 0 2px black;
		height: ${KNOB_SIZE}px;
		width: ${KNOB_SIZE}px;
	}

	.${randomClass}::-moz-range-thumb {
		-webkit-appearance: none;
		background-color: white;
		border-radius: ${KNOB_SIZE / 2}px;
		box-shadow: 0 0 2px black;
		height: ${KNOB_SIZE}px;
		width: ${KNOB_SIZE}px;
	}
`;
    return /* @__PURE__ */ (0, import_jsx_runtime41.jsxs)("div", {
      style: sliderContainer,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("style", {
          dangerouslySetInnerHTML: {
            __html: sliderStyle
          }
        }),
        /* @__PURE__ */ (0, import_jsx_runtime41.jsx)("input", {
          ref: inputRef,
          "aria-label": "Change volume",
          className: randomClass,
          max: 1,
          min: 0,
          onBlur,
          onChange: onVolumeChange,
          step: 0.01,
          type: "range",
          value: volume,
          style: inputStyle2
        })
      ]
    });
  };
  var renderDefaultVolumeSlider = (props) => {
    return /* @__PURE__ */ (0, import_jsx_runtime41.jsx)(DefaultVolumeSlider, {
      ...props
    });
  };
  var VOLUME_SLIDER_WIDTH = 100;
  var MediaVolumeSlider = ({ displayVerticalVolumeSlider, renderMuteButton, renderVolumeSlider }) => {
    const [mediaMuted, setMediaMuted] = Internals.useMediaMutedState();
    const [mediaVolume, setMediaVolume] = Internals.useMediaVolumeState();
    const [focused, setFocused] = (0, import_react86.useState)(false);
    const parentDivRef = (0, import_react86.useRef)(null);
    const inputRef = (0, import_react86.useRef)(null);
    const hover = useHoverState(parentDivRef, false);
    const onBlur = (0, import_react86.useCallback)(() => {
      setTimeout(() => {
        if (inputRef.current && document.activeElement !== inputRef.current) {
          setFocused(false);
        }
      }, 10);
    }, []);
    const isVolume0 = mediaVolume === 0;
    const onClick = (0, import_react86.useCallback)(() => {
      if (isVolume0) {
        setMediaVolume(1);
        setMediaMuted(false);
        return;
      }
      setMediaMuted((mute) => !mute);
    }, [isVolume0, setMediaMuted, setMediaVolume]);
    const parentDivStyle = (0, import_react86.useMemo)(() => {
      return {
        display: "inline-flex",
        background: "none",
        border: "none",
        justifyContent: "center",
        alignItems: "center",
        touchAction: "none",
        ...displayVerticalVolumeSlider && { position: "relative" }
      };
    }, [displayVerticalVolumeSlider]);
    const volumeContainer = (0, import_react86.useMemo)(() => {
      return {
        display: "inline",
        width: ICON_SIZE2,
        height: ICON_SIZE2,
        cursor: "pointer",
        appearance: "none",
        background: "none",
        border: "none",
        padding: 0
      };
    }, []);
    const renderDefaultMuteButton = (0, import_react86.useCallback)(({ muted, volume }) => {
      const isMutedOrZero = muted || volume === 0;
      return /* @__PURE__ */ (0, import_jsx_runtime42.jsx)("button", {
        "aria-label": isMutedOrZero ? "Unmute sound" : "Mute sound",
        title: isMutedOrZero ? "Unmute sound" : "Mute sound",
        onClick,
        onBlur,
        onFocus: () => setFocused(true),
        style: volumeContainer,
        type: "button",
        children: isMutedOrZero ? /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(VolumeOffIcon, {}) : /* @__PURE__ */ (0, import_jsx_runtime42.jsx)(VolumeOnIcon, {})
      });
    }, [onBlur, onClick, volumeContainer]);
    const muteButton = (0, import_react86.useMemo)(() => {
      return renderMuteButton ? renderMuteButton({ muted: mediaMuted, volume: mediaVolume }) : renderDefaultMuteButton({ muted: mediaMuted, volume: mediaVolume });
    }, [mediaMuted, mediaVolume, renderDefaultMuteButton, renderMuteButton]);
    const volumeSlider = (0, import_react86.useMemo)(() => {
      return (focused || hover) && !mediaMuted && !Internals.isIosSafari() ? (renderVolumeSlider ?? renderDefaultVolumeSlider)({
        isVertical: displayVerticalVolumeSlider,
        volume: mediaVolume,
        onBlur: () => setFocused(false),
        inputRef,
        setVolume: setMediaVolume
      }) : null;
    }, [
      displayVerticalVolumeSlider,
      focused,
      hover,
      mediaMuted,
      mediaVolume,
      renderVolumeSlider,
      setMediaVolume
    ]);
    return /* @__PURE__ */ (0, import_jsx_runtime42.jsxs)("div", {
      ref: parentDivRef,
      style: parentDivStyle,
      children: [
        muteButton,
        volumeSlider
      ]
    });
  };
  function useComponentVisible(initialIsVisible) {
    const [isComponentVisible, setIsComponentVisible] = (0, import_react89.useState)(initialIsVisible);
    const ref = (0, import_react89.useRef)(null);
    (0, import_react89.useEffect)(() => {
      const handleClickOutside = (event) => {
        if (ref.current && !ref.current.contains(event.target)) {
          setIsComponentVisible(false);
        }
      };
      document.addEventListener("pointerup", handleClickOutside, true);
      return () => {
        document.removeEventListener("pointerup", handleClickOutside, true);
      };
    }, []);
    return { ref, isComponentVisible, setIsComponentVisible };
  }
  var BOTTOM = 35;
  var THRESHOLD = 70;
  var rateDiv = {
    height: 30,
    paddingRight: 15,
    paddingLeft: 12,
    display: "flex",
    flexDirection: "row",
    alignItems: "center"
  };
  var checkmarkContainer = {
    width: 22,
    display: "flex",
    alignItems: "center"
  };
  var checkmarkStyle = {
    width: 14,
    height: 14,
    color: "black"
  };
  var Checkmark = () => /* @__PURE__ */ (0, import_jsx_runtime43.jsx)("svg", {
    viewBox: "0 0 512 512",
    style: checkmarkStyle,
    children: /* @__PURE__ */ (0, import_jsx_runtime43.jsx)("path", {
      fill: "currentColor",
      d: "M435.848 83.466L172.804 346.51l-96.652-96.652c-4.686-4.686-12.284-4.686-16.971 0l-28.284 28.284c-4.686 4.686-4.686 12.284 0 16.971l133.421 133.421c4.686 4.686 12.284 4.686 16.971 0l299.813-299.813c4.686-4.686 4.686-12.284 0-16.971l-28.284-28.284c-4.686-4.686-12.284-4.686-16.97 0z"
    })
  });
  var formatPlaybackRate = (rate) => {
    const str = rate.toString();
    return str.includes(".") ? str : str + ".0";
  };
  var PlaybackrateOption = ({ rate, onSelect, selectedRate, keyboardSelectedRate }) => {
    const onClick = (0, import_react88.useCallback)((e) => {
      e.stopPropagation();
      e.preventDefault();
      onSelect(rate);
    }, [onSelect, rate]);
    const [hovered, setHovered] = (0, import_react88.useState)(false);
    const onMouseEnter = (0, import_react88.useCallback)(() => {
      setHovered(true);
    }, []);
    const onMouseLeave = (0, import_react88.useCallback)(() => {
      setHovered(false);
    }, []);
    const isFocused = keyboardSelectedRate === rate;
    const actualStyle = (0, import_react88.useMemo)(() => {
      return {
        ...rateDiv,
        backgroundColor: hovered || isFocused ? "#eee" : "transparent"
      };
    }, [hovered, isFocused]);
    return /* @__PURE__ */ (0, import_jsx_runtime43.jsxs)("div", {
      onPointerEnter: onMouseEnter,
      onPointerLeave: onMouseLeave,
      tabIndex: 0,
      style: actualStyle,
      onClick,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime43.jsx)("div", {
          style: checkmarkContainer,
          children: rate === selectedRate ? /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(Checkmark, {}) : null
        }),
        formatPlaybackRate(rate),
        "x"
      ]
    }, rate);
  };
  var PlaybackPopup = ({ setIsComponentVisible, playbackRates, canvasSize }) => {
    const { setPlaybackRate, playbackRate } = (0, import_react88.useContext)(Internals.TimelineContext);
    const [keyboardSelectedRate, setKeyboardSelectedRate] = (0, import_react88.useState)(playbackRate);
    (0, import_react88.useEffect)(() => {
      const listener = (e) => {
        e.preventDefault();
        if (e.key === "ArrowUp") {
          const currentIndex = playbackRates.findIndex((rate) => rate === keyboardSelectedRate);
          if (currentIndex === 0) {
            return;
          }
          if (currentIndex === -1) {
            setKeyboardSelectedRate(playbackRates[0]);
          } else {
            setKeyboardSelectedRate(playbackRates[currentIndex - 1]);
          }
        } else if (e.key === "ArrowDown") {
          const currentIndex = playbackRates.findIndex((rate) => rate === keyboardSelectedRate);
          if (currentIndex === playbackRates.length - 1) {
            return;
          }
          if (currentIndex === -1) {
            setKeyboardSelectedRate(playbackRates[playbackRates.length - 1]);
          } else {
            setKeyboardSelectedRate(playbackRates[currentIndex + 1]);
          }
        } else if (e.key === "Enter") {
          setPlaybackRate(keyboardSelectedRate);
          setIsComponentVisible(false);
        }
      };
      window.addEventListener("keydown", listener);
      return () => {
        window.removeEventListener("keydown", listener);
      };
    }, [
      playbackRates,
      keyboardSelectedRate,
      setPlaybackRate,
      setIsComponentVisible
    ]);
    const onSelect = (0, import_react88.useCallback)((rate) => {
      setPlaybackRate(rate);
      setIsComponentVisible(false);
    }, [setIsComponentVisible, setPlaybackRate]);
    const playbackPopup = (0, import_react88.useMemo)(() => {
      return {
        position: "absolute",
        right: 0,
        width: 125,
        maxHeight: canvasSize.height - THRESHOLD - BOTTOM,
        bottom: 35,
        background: "#fff",
        borderRadius: 4,
        overflow: "auto",
        color: "black",
        textAlign: "left"
      };
    }, [canvasSize.height]);
    return /* @__PURE__ */ (0, import_jsx_runtime43.jsx)("div", {
      style: playbackPopup,
      children: playbackRates.map((rate) => {
        return /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(PlaybackrateOption, {
          selectedRate: playbackRate,
          onSelect,
          rate,
          keyboardSelectedRate
        }, rate);
      })
    });
  };
  var label2 = {
    fontSize: 13,
    fontWeight: "bold",
    color: "white",
    border: "2px solid white",
    borderRadius: 20,
    paddingLeft: 8,
    paddingRight: 8,
    paddingTop: 2,
    paddingBottom: 2
  };
  var playerButtonStyle = {
    appearance: "none",
    backgroundColor: "transparent",
    border: "none",
    cursor: "pointer",
    paddingLeft: 0,
    paddingRight: 0,
    paddingTop: 6,
    paddingBottom: 6,
    height: 37,
    display: "inline-flex",
    marginBottom: 0,
    marginTop: 0,
    alignItems: "center"
  };
  var button = {
    ...playerButtonStyle,
    position: "relative"
  };
  var PlaybackrateControl = ({ playbackRates, canvasSize }) => {
    const { ref, isComponentVisible, setIsComponentVisible } = useComponentVisible(false);
    const { playbackRate } = (0, import_react88.useContext)(Internals.TimelineContext);
    const onClick = (0, import_react88.useCallback)((e) => {
      e.stopPropagation();
      e.preventDefault();
      setIsComponentVisible((prevIsComponentVisible) => !prevIsComponentVisible);
    }, [setIsComponentVisible]);
    return /* @__PURE__ */ (0, import_jsx_runtime43.jsx)("div", {
      ref,
      children: /* @__PURE__ */ (0, import_jsx_runtime43.jsxs)("button", {
        type: "button",
        "aria-label": "Change playback rate",
        style: button,
        onClick,
        children: [
          /* @__PURE__ */ (0, import_jsx_runtime43.jsxs)("div", {
            style: label2,
            children: [
              playbackRate,
              "x"
            ]
          }),
          isComponentVisible && /* @__PURE__ */ (0, import_jsx_runtime43.jsx)(PlaybackPopup, {
            canvasSize,
            playbackRates,
            setIsComponentVisible
          })
        ]
      })
    });
  };
  var getFrameFromX = (clientX, durationInFrames, width) => {
    const pos = clientX;
    const frame = Math.round(interpolate(pos, [0, width], [0, durationInFrames - 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    }));
    return frame;
  };
  var BAR_HEIGHT2 = 5;
  var KNOB_SIZE2 = 12;
  var VERTICAL_PADDING = 4;
  var containerStyle = {
    userSelect: "none",
    WebkitUserSelect: "none",
    paddingTop: VERTICAL_PADDING,
    paddingBottom: VERTICAL_PADDING,
    boxSizing: "border-box",
    cursor: "pointer",
    position: "relative",
    touchAction: "none"
  };
  var barBackground = {
    height: BAR_HEIGHT2,
    backgroundColor: "rgba(255, 255, 255, 0.25)",
    width: "100%",
    borderRadius: BAR_HEIGHT2 / 2
  };
  var findBodyInWhichDivIsLocated = (div) => {
    let current = div;
    while (current.parentElement) {
      current = current.parentElement;
    }
    return current;
  };
  var PlayerSeekBar = ({ durationInFrames, onSeekEnd, onSeekStart, inFrame, outFrame }) => {
    const containerRef = (0, import_react90.useRef)(null);
    const barHovered = useHoverState(containerRef, false);
    const size = useElementSize(containerRef, {
      triggerOnWindowResize: true,
      shouldApplyCssTransforms: true
    });
    const { seek: seek2, play, pause, playing } = usePlayer();
    const frame = Internals.Timeline.useTimelinePosition();
    const [dragging, setDragging] = (0, import_react90.useState)({
      dragging: false
    });
    const width = size?.width ?? 0;
    const onPointerDown = (0, import_react90.useCallback)((e) => {
      if (e.button !== 0) {
        return;
      }
      const posLeft = containerRef.current?.getBoundingClientRect().left;
      const _frame = getFrameFromX(e.clientX - posLeft, durationInFrames, width);
      pause();
      seek2(_frame);
      setDragging({
        dragging: true,
        wasPlaying: playing
      });
      onSeekStart();
    }, [durationInFrames, width, pause, seek2, playing, onSeekStart]);
    const onPointerMove = (0, import_react90.useCallback)((e) => {
      if (!size) {
        throw new Error("Player has no size");
      }
      if (!dragging.dragging) {
        return;
      }
      const posLeft = containerRef.current?.getBoundingClientRect().left;
      const _frame = getFrameFromX(e.clientX - posLeft, durationInFrames, size.width);
      seek2(_frame);
    }, [dragging.dragging, durationInFrames, seek2, size]);
    const onPointerUp = (0, import_react90.useCallback)(() => {
      setDragging({
        dragging: false
      });
      if (!dragging.dragging) {
        return;
      }
      if (dragging.wasPlaying) {
        play();
      } else {
        pause();
      }
      onSeekEnd();
    }, [dragging, onSeekEnd, pause, play]);
    (0, import_react90.useEffect)(() => {
      if (!dragging.dragging) {
        return;
      }
      const body = findBodyInWhichDivIsLocated(containerRef.current);
      body.addEventListener("pointermove", onPointerMove);
      body.addEventListener("pointerup", onPointerUp);
      return () => {
        body.removeEventListener("pointermove", onPointerMove);
        body.removeEventListener("pointerup", onPointerUp);
      };
    }, [dragging.dragging, onPointerMove, onPointerUp]);
    const knobStyle = (0, import_react90.useMemo)(() => {
      return {
        height: KNOB_SIZE2,
        width: KNOB_SIZE2,
        borderRadius: KNOB_SIZE2 / 2,
        position: "absolute",
        top: VERTICAL_PADDING - KNOB_SIZE2 / 2 + 5 / 2,
        backgroundColor: "white",
        left: Math.max(0, frame / Math.max(1, durationInFrames - 1) * width - KNOB_SIZE2 / 2),
        boxShadow: "0 0 2px black",
        opacity: Number(barHovered || dragging.dragging)
      };
    }, [barHovered, dragging.dragging, durationInFrames, frame, width]);
    const fillStyle = (0, import_react90.useMemo)(() => {
      return {
        height: BAR_HEIGHT2,
        backgroundColor: "rgba(255, 255, 255, 1)",
        width: (frame - (inFrame ?? 0)) / (durationInFrames - 1) * width,
        marginLeft: (inFrame ?? 0) / (durationInFrames - 1) * width,
        borderRadius: BAR_HEIGHT2 / 2
      };
    }, [durationInFrames, frame, inFrame, width]);
    const active = (0, import_react90.useMemo)(() => {
      return {
        height: BAR_HEIGHT2,
        backgroundColor: "rgba(255, 255, 255, 0.25)",
        width: ((outFrame ?? durationInFrames - 1) - (inFrame ?? 0)) / (durationInFrames - 1) * 100 + "%",
        marginLeft: (inFrame ?? 0) / (durationInFrames - 1) * 100 + "%",
        borderRadius: BAR_HEIGHT2 / 2,
        position: "absolute"
      };
    }, [durationInFrames, inFrame, outFrame]);
    return /* @__PURE__ */ (0, import_jsx_runtime44.jsxs)("div", {
      ref: containerRef,
      onPointerDown,
      style: containerStyle,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime44.jsxs)("div", {
          style: barBackground,
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", {
              style: active
            }),
            /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", {
              style: fillStyle
            })
          ]
        }),
        /* @__PURE__ */ (0, import_jsx_runtime44.jsx)("div", {
          style: knobStyle
        })
      ]
    });
  };
  var formatTime = (timeInSeconds) => {
    const minutes = Math.floor(timeInSeconds / 60);
    const seconds = Math.floor(timeInSeconds - minutes * 60);
    return `${String(minutes)}:${String(seconds).padStart(2, "0")}`;
  };
  var PlayerTimeLabel = ({ durationInFrames, maxTimeLabelWidth, fps }) => {
    const frame = Internals.Timeline.useTimelinePosition();
    const timeLabel = (0, import_react91.useMemo)(() => {
      return {
        color: "white",
        fontFamily: "sans-serif",
        fontSize: 14,
        maxWidth: maxTimeLabelWidth === null ? void 0 : maxTimeLabelWidth,
        overflow: "hidden",
        textOverflow: "ellipsis"
      };
    }, [maxTimeLabelWidth]);
    const isLastFrame = frame === durationInFrames - 1;
    const frameToDisplay = isLastFrame ? frame + 1 : frame;
    return /* @__PURE__ */ (0, import_jsx_runtime45.jsxs)("div", {
      style: timeLabel,
      children: [
        formatTime(frameToDisplay / fps),
        " / ",
        formatTime(durationInFrames / fps)
      ]
    });
  };
  var X_SPACER = 10;
  var X_PADDING = 12;
  var useVideoControlsResize = ({
    allowFullscreen: allowFullScreen,
    playerWidth
  }) => {
    const resizeInfo = (0, import_react92.useMemo)(() => {
      const playPauseIconSize = ICON_SIZE2;
      const volumeIconSize = ICON_SIZE2;
      const _fullscreenIconSize = allowFullScreen ? fullscreenIconSize : 0;
      const elementsSize = volumeIconSize + playPauseIconSize + _fullscreenIconSize + X_PADDING * 2 + X_SPACER * 2;
      const maxTimeLabelWidth = playerWidth - elementsSize;
      const maxTimeLabelWidthWithoutNegativeValue = Math.max(maxTimeLabelWidth, 0);
      const availableTimeLabelWidthIfVolumeOpen = maxTimeLabelWidthWithoutNegativeValue - VOLUME_SLIDER_WIDTH;
      const computedLabelWidth = availableTimeLabelWidthIfVolumeOpen < VOLUME_SLIDER_WIDTH ? maxTimeLabelWidthWithoutNegativeValue : availableTimeLabelWidthIfVolumeOpen;
      const minWidthForHorizontalDisplay = computedLabelWidth + elementsSize + VOLUME_SLIDER_WIDTH;
      const displayVerticalVolumeSlider = playerWidth < minWidthForHorizontalDisplay;
      return {
        maxTimeLabelWidth: maxTimeLabelWidthWithoutNegativeValue === 0 ? null : maxTimeLabelWidthWithoutNegativeValue,
        displayVerticalVolumeSlider
      };
    }, [allowFullScreen, playerWidth]);
    return resizeInfo;
  };
  var gradientSteps = [
    0,
    0.013,
    0.049,
    0.104,
    0.175,
    0.259,
    0.352,
    0.45,
    0.55,
    0.648,
    0.741,
    0.825,
    0.896,
    0.951,
    0.987
  ];
  var gradientOpacities = [
    0,
    8.1,
    15.5,
    22.5,
    29,
    35.3,
    41.2,
    47.1,
    52.9,
    58.8,
    64.7,
    71,
    77.5,
    84.5,
    91.9
  ];
  var globalGradientOpacity = 1 / 0.7;
  var containerStyle2 = {
    boxSizing: "border-box",
    position: "absolute",
    bottom: 0,
    width: "100%",
    paddingTop: 40,
    paddingBottom: 10,
    backgroundImage: `linear-gradient(to bottom,${gradientSteps.map((g, i) => {
      return `hsla(0, 0%, 0%, ${g}) ${gradientOpacities[i] * globalGradientOpacity}%`;
    }).join(", ")}, hsl(0, 0%, 0%) 100%)`,
    backgroundSize: "auto 145px",
    display: "flex",
    paddingRight: X_PADDING,
    paddingLeft: X_PADDING,
    flexDirection: "column",
    transition: "opacity 0.3s"
  };
  var controlsRow = {
    display: "flex",
    flexDirection: "row",
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    userSelect: "none",
    WebkitUserSelect: "none"
  };
  var leftPartStyle = {
    display: "flex",
    flexDirection: "row",
    userSelect: "none",
    WebkitUserSelect: "none",
    alignItems: "center"
  };
  var xSpacer = {
    width: 12
  };
  var ySpacer = {
    height: 8
  };
  var flex1 = {
    flex: 1
  };
  var fullscreen = {};
  var Controls = ({
    durationInFrames,
    isFullscreen,
    fps,
    showVolumeControls,
    onFullscreenButtonClick,
    allowFullscreen,
    onExitFullscreenButtonClick,
    spaceKeyToPlayOrPause,
    onSeekEnd,
    onSeekStart,
    inFrame,
    outFrame,
    initiallyShowControls,
    canvasSize,
    renderPlayPauseButton,
    renderFullscreenButton,
    alwaysShowControls,
    showPlaybackRateControl,
    containerRef,
    buffering,
    hideControlsWhenPointerDoesntMove,
    onPointerDown,
    onDoubleClick,
    renderMuteButton,
    renderVolumeSlider,
    playing,
    toggle,
    renderCustomControls
  }) => {
    const playButtonRef = (0, import_react85.useRef)(null);
    const [supportsFullscreen, setSupportsFullscreen] = (0, import_react85.useState)(false);
    const hovered = useHoverState(containerRef, hideControlsWhenPointerDoesntMove);
    const { maxTimeLabelWidth, displayVerticalVolumeSlider } = useVideoControlsResize({
      allowFullscreen,
      playerWidth: canvasSize?.width ?? 0
    });
    const [shouldShowInitially, setInitiallyShowControls] = (0, import_react85.useState)(() => {
      if (typeof initiallyShowControls === "boolean") {
        return initiallyShowControls;
      }
      if (typeof initiallyShowControls === "number") {
        if (initiallyShowControls % 1 !== 0) {
          throw new Error("initiallyShowControls must be an integer or a boolean");
        }
        if (Number.isNaN(initiallyShowControls)) {
          throw new Error("initiallyShowControls must not be NaN");
        }
        if (!Number.isFinite(initiallyShowControls)) {
          throw new Error("initiallyShowControls must be finite");
        }
        if (initiallyShowControls <= 0) {
          throw new Error("initiallyShowControls must be a positive integer");
        }
        return initiallyShowControls;
      }
      throw new TypeError("initiallyShowControls must be a number or a boolean");
    });
    const containerCss = (0, import_react85.useMemo)(() => {
      const shouldShow = hovered || !playing || shouldShowInitially || alwaysShowControls;
      return {
        ...containerStyle2,
        opacity: Number(shouldShow)
      };
    }, [hovered, shouldShowInitially, playing, alwaysShowControls]);
    (0, import_react85.useEffect)(() => {
      if (playButtonRef.current && spaceKeyToPlayOrPause) {
        playButtonRef.current.focus({
          preventScroll: true
        });
      }
    }, [playing, spaceKeyToPlayOrPause]);
    (0, import_react85.useEffect)(() => {
      setSupportsFullscreen((typeof document !== "undefined" && (document.fullscreenEnabled || document.webkitFullscreenEnabled)) ?? false);
    }, []);
    (0, import_react85.useEffect)(() => {
      if (shouldShowInitially === false) {
        return;
      }
      const time = shouldShowInitially === true ? 2e3 : shouldShowInitially;
      const timeout = setTimeout(() => {
        setInitiallyShowControls(false);
      }, time);
      return () => {
        clearInterval(timeout);
      };
    }, [shouldShowInitially]);
    const playbackRates = (0, import_react85.useMemo)(() => {
      if (showPlaybackRateControl === true) {
        return [0.5, 0.8, 1, 1.2, 1.5, 1.8, 2, 2.5, 3];
      }
      if (Array.isArray(showPlaybackRateControl)) {
        for (const rate of showPlaybackRateControl) {
          if (typeof rate !== "number") {
            throw new Error("Every item in showPlaybackRateControl must be a number");
          }
          if (rate <= 0) {
            throw new Error("Every item in showPlaybackRateControl must be positive");
          }
        }
        return showPlaybackRateControl;
      }
      return null;
    }, [showPlaybackRateControl]);
    const customControlsElement = renderCustomControls ? renderCustomControls() : null;
    const ref = (0, import_react85.useRef)(null);
    const flexRef = (0, import_react85.useRef)(null);
    const onPointerDownIfContainer = (0, import_react85.useCallback)((e) => {
      if (e.target === ref.current || e.target === flexRef.current) {
        onPointerDown?.(e);
      }
    }, [onPointerDown]);
    const onDoubleClickIfContainer = (0, import_react85.useCallback)((e) => {
      if (e.target === ref.current || e.target === flexRef.current) {
        onDoubleClick?.(e);
      }
    }, [onDoubleClick]);
    return /* @__PURE__ */ (0, import_jsx_runtime46.jsxs)("div", {
      ref,
      style: containerCss,
      onPointerDown: onPointerDownIfContainer,
      onDoubleClick: onDoubleClickIfContainer,
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime46.jsxs)("div", {
          ref: flexRef,
          style: controlsRow,
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime46.jsxs)("div", {
              style: leftPartStyle,
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("button", {
                  ref: playButtonRef,
                  type: "button",
                  style: playerButtonStyle,
                  onClick: toggle,
                  "aria-label": playing ? "Pause video" : "Play video",
                  title: playing ? "Pause video" : "Play video",
                  children: renderPlayPauseButton === null ? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(DefaultPlayPauseButton, {
                    buffering,
                    playing
                  }) : renderPlayPauseButton({
                    playing,
                    isBuffering: buffering
                  }) ?? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(DefaultPlayPauseButton, {
                    buffering,
                    playing
                  })
                }),
                showVolumeControls ? /* @__PURE__ */ (0, import_jsx_runtime46.jsxs)(import_jsx_runtime46.Fragment, {
                  children: [
                    /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
                      style: xSpacer
                    }),
                    /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(MediaVolumeSlider, {
                      renderMuteButton,
                      renderVolumeSlider,
                      displayVerticalVolumeSlider
                    })
                  ]
                }) : null,
                /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
                  style: xSpacer
                }),
                /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(PlayerTimeLabel, {
                  durationInFrames,
                  fps,
                  maxTimeLabelWidth
                }),
                /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
                  style: xSpacer
                })
              ]
            }),
            /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
              style: flex1
            }),
            customControlsElement,
            customControlsElement && playbackRates && canvasSize ? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
              style: xSpacer
            }) : null,
            playbackRates && canvasSize && /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(PlaybackrateControl, {
              canvasSize,
              playbackRates
            }),
            playbackRates && supportsFullscreen && allowFullscreen ? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
              style: xSpacer
            }) : null,
            /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
              style: fullscreen,
              children: supportsFullscreen && allowFullscreen ? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("button", {
                type: "button",
                "aria-label": isFullscreen ? "Exit fullscreen" : "Enter Fullscreen",
                title: isFullscreen ? "Exit fullscreen" : "Enter Fullscreen",
                style: playerButtonStyle,
                onClick: isFullscreen ? onExitFullscreenButtonClick : onFullscreenButtonClick,
                children: renderFullscreenButton === null ? /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(FullscreenIcon, {
                  isFullscreen
                }) : renderFullscreenButton({ isFullscreen })
              }) : null
            })
          ]
        }),
        /* @__PURE__ */ (0, import_jsx_runtime46.jsx)("div", {
          style: ySpacer
        }),
        /* @__PURE__ */ (0, import_jsx_runtime46.jsx)(PlayerSeekBar, {
          onSeekEnd,
          onSeekStart,
          durationInFrames,
          inFrame,
          outFrame
        })
      ]
    });
  };
  var errorStyle = {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    flex: 1,
    height: "100%",
    width: "100%"
  };
  var ErrorBoundary = class extends import_react93.default.Component {
    constructor() {
      super(...arguments);
      __publicField(this, "state", { hasError: null });
    }
    static getDerivedStateFromError(error2) {
      return { hasError: error2 };
    }
    componentDidCatch(error2) {
      this.props.onError(error2);
    }
    render() {
      if (this.state.hasError) {
        return /* @__PURE__ */ (0, import_jsx_runtime47.jsx)("div", {
          style: errorStyle,
          children: this.props.errorFallback({
            error: this.state.hasError
          })
        });
      }
      return this.props.children;
    }
  };
  var getHashOfDomain = async () => {
    if (typeof window === "undefined") {
      return null;
    }
    if (typeof window.crypto === "undefined") {
      return null;
    }
    if (typeof window.crypto.subtle === "undefined") {
      return null;
    }
    try {
      const hashBuffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(window.location.hostname));
      return Array.from(new Uint8Array(hashBuffer)).map((b2) => b2.toString(16).padStart(2, "0")).join("");
    } catch {
      return null;
    }
  };
  var style = {
    backgroundColor: "red",
    position: "absolute",
    padding: 12,
    fontFamily: "Arial"
  };
  var DOMAIN_BLACKLIST = [
    "28d262b44cc61fa750f1686b16ad0604dabfe193fbc263eec05c89b7ad4c2cd6",
    "4db1b0a94be33165dfefcb3ba03d04c7a2666dd27c496d3dc9fa41858e94925e",
    "fbc48530bbf245da790f63675e84e06bab38c3b114fab07eb350025119922bdc",
    "7baf10a8932757b1b3a22b3fce10a048747ac2f8eaf638603487e3705b07eb83",
    "8a6c21a598d8c667272b5207c051b85997bf5b45d5fb712378be3f27cd72c6a6",
    "a2f7aaac9c50a9255e7fc376110c4e0bfe153722dc66ed3c5d3bf2a135f65518"
  ];
  var ran = false;
  var RenderWarningIfBlacklist = () => {
    const [unlicensed, setUnlicensed] = import_react94.default.useState(false);
    (0, import_react94.useEffect)(() => {
      if (ran) {
        return;
      }
      ran = true;
      getHashOfDomain().then((hash) => {
        if (hash && DOMAIN_BLACKLIST.includes(hash)) {
          setUnlicensed(true);
        }
      }).catch(() => {
      });
    }, []);
    (0, import_react94.useEffect)(() => {
      if (!unlicensed) {
        return;
      }
      const ensureBanner = () => {
        const banner = document.querySelector(".warning-banner");
        if (!banner) {
          const div = document.createElement("div");
          div.className = "warning-banner";
          Object.assign(div.style, style, {
            zIndex: "9999",
            cssText: `${style.cssText} !important;`
          });
          div.innerHTML = `
	        <a href="https://github.com/remotion-dev/remotion/pull/4589" style="color: white;">
	          Remotion Unlicensed \u2013 Contact hi@remotion.dev
	        </a>
	      `;
          document.body.appendChild(div);
        }
      };
      const observer = new MutationObserver(() => ensureBanner());
      observer.observe(document.body, { childList: true, subtree: true });
      return () => {
        observer.disconnect();
      };
    }, [unlicensed]);
    if (!unlicensed) {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime48.jsx)("div", {
      style,
      className: "warning-banner",
      children: /* @__PURE__ */ (0, import_jsx_runtime48.jsx)("a", {
        style: { color: "white" },
        href: "https://github.com/remotion-dev/remotion/pull/4589",
        children: "Remotion Unlicensed \u2013 Contact hi@remotion.dev"
      })
    });
  };
  var playerCssClassname = (override) => {
    return override ?? "__remotion-player";
  };
  var IS_NODE = typeof document === "undefined";
  var cancellablePromise = (promise) => {
    let isCanceled = false;
    const wrappedPromise = new Promise((resolve, reject) => {
      promise.then((value) => {
        if (isCanceled) {
          reject({ isCanceled, value });
          return;
        }
        resolve(value);
      }).catch((error2) => {
        reject({ isCanceled, error: error2 });
      });
    });
    return {
      promise: wrappedPromise,
      cancel: () => {
        isCanceled = true;
      }
    };
  };
  var delay = (n) => new Promise((resolve) => setTimeout(resolve, n));
  var useCancellablePromises = () => {
    const pendingPromises = (0, import_react96.useRef)([]);
    const appendPendingPromise = (0, import_react96.useCallback)((promise) => {
      pendingPromises.current = [...pendingPromises.current, promise];
    }, []);
    const removePendingPromise = (0, import_react96.useCallback)((promise) => {
      pendingPromises.current = pendingPromises.current.filter((p) => p !== promise);
    }, []);
    const clearPendingPromises = (0, import_react96.useCallback)(() => pendingPromises.current.map((p) => p.cancel()), []);
    const api = (0, import_react96.useMemo)(() => ({
      appendPendingPromise,
      removePendingPromise,
      clearPendingPromises
    }), [appendPendingPromise, clearPendingPromises, removePendingPromise]);
    return api;
  };
  var useClickPreventionOnDoubleClick = (onClick, onDoubleClick, doubleClickToFullscreen) => {
    const api = useCancellablePromises();
    const handleClick = (0, import_react95.useCallback)(async (e) => {
      if (e instanceof PointerEvent ? e.pointerType === "touch" : e.nativeEvent.pointerType === "touch") {
        onClick(e);
        return;
      }
      api.clearPendingPromises();
      const waitForClick = cancellablePromise(delay(200));
      api.appendPendingPromise(waitForClick);
      try {
        await waitForClick.promise;
        api.removePendingPromise(waitForClick);
        onClick(e);
      } catch (errorInfo) {
        const info2 = errorInfo;
        api.removePendingPromise(waitForClick);
        if (!info2.isCanceled) {
          throw info2.error;
        }
      }
    }, [api, onClick]);
    const handlePointerDown = (0, import_react95.useCallback)(() => {
      document.addEventListener("pointerup", (newEvt) => {
        handleClick(newEvt);
      }, {
        once: true
      });
    }, [handleClick]);
    const handleDoubleClick = (0, import_react95.useCallback)(() => {
      api.clearPendingPromises();
      onDoubleClick();
    }, [api, onDoubleClick]);
    const returnValue = (0, import_react95.useMemo)(() => {
      if (!doubleClickToFullscreen) {
        return { handlePointerDown: onClick, handleDoubleClick: () => {
          return;
        } };
      }
      return { handlePointerDown, handleDoubleClick };
    }, [doubleClickToFullscreen, handleDoubleClick, handlePointerDown, onClick]);
    return returnValue;
  };
  var reactVersion = import_react84.default.version.split(".")[0];
  if (reactVersion === "0") {
    throw new Error(`Version ${reactVersion} of "react" is not supported by Remotion`);
  }
  var doesReactVersionSupportSuspense = parseInt(reactVersion, 10) >= 18;
  var PlayerUI = ({
    controls,
    style: style2,
    loop,
    autoPlay,
    allowFullscreen,
    inputProps,
    clickToPlay,
    showVolumeControls,
    doubleClickToFullscreen,
    spaceKeyToPlayOrPause,
    errorFallback,
    playbackRate,
    renderLoading,
    renderPoster,
    className: className2,
    moveToBeginningWhenEnded,
    showPosterWhenUnplayed,
    showPosterWhenEnded,
    showPosterWhenPaused,
    showPosterWhenBuffering,
    showPosterWhenBufferingAndPaused,
    inFrame,
    outFrame,
    initiallyShowControls,
    renderFullscreen: renderFullscreenButton,
    renderPlayPauseButton,
    renderMuteButton,
    renderVolumeSlider,
    renderCustomControls,
    alwaysShowControls,
    showPlaybackRateControl,
    posterFillMode,
    bufferStateDelayInMilliseconds,
    hideControlsWhenPointerDoesntMove,
    overflowVisible,
    browserMediaControlsBehavior,
    overrideInternalClassName,
    noSuspense
  }, ref) => {
    const config = Internals.useUnsafeVideoConfig();
    const video = Internals.useVideo();
    const container2 = (0, import_react84.useRef)(null);
    const canvasSize = useElementSize(container2, {
      triggerOnWindowResize: false,
      shouldApplyCssTransforms: false
    });
    const [hasPausedToResume, setHasPausedToResume] = (0, import_react84.useState)(false);
    const [shouldAutoplay, setShouldAutoPlay] = (0, import_react84.useState)(autoPlay);
    const [isFullscreen, setIsFullscreen] = (0, import_react84.useState)(() => false);
    const [seeking, setSeeking] = (0, import_react84.useState)(false);
    const supportsFullScreen = (0, import_react84.useMemo)(() => {
      if (typeof document === "undefined") {
        return false;
      }
      return Boolean(document.fullscreenEnabled || document.webkitFullscreenEnabled);
    }, []);
    const player = usePlayer();
    const playerToggle = player.toggle;
    usePlayback({
      loop,
      playbackRate,
      moveToBeginningWhenEnded,
      inFrame,
      outFrame,
      getCurrentFrame: player.getCurrentFrame,
      browserMediaControlsBehavior
    });
    (0, import_react84.useEffect)(() => {
      if (hasPausedToResume && !player.playing) {
        setHasPausedToResume(false);
        player.play();
      }
    }, [hasPausedToResume, player]);
    (0, import_react84.useEffect)(() => {
      const { current } = container2;
      if (!current) {
        return;
      }
      const onFullscreenChange = () => {
        const newValue = document.fullscreenElement === current || document.webkitFullscreenElement === current;
        setIsFullscreen(newValue);
      };
      document.addEventListener("fullscreenchange", onFullscreenChange);
      document.addEventListener("webkitfullscreenchange", onFullscreenChange);
      return () => {
        document.removeEventListener("fullscreenchange", onFullscreenChange);
        document.removeEventListener("webkitfullscreenchange", onFullscreenChange);
      };
    }, []);
    const toggle = (0, import_react84.useCallback)((e) => {
      playerToggle(e);
    }, [playerToggle]);
    const requestFullscreen = (0, import_react84.useCallback)(() => {
      if (!allowFullscreen) {
        throw new Error("allowFullscreen is false");
      }
      if (!supportsFullScreen) {
        throw new Error("Browser doesnt support fullscreen");
      }
      if (!container2.current) {
        throw new Error("No player ref found");
      }
      if (container2.current.webkitRequestFullScreen) {
        container2.current.webkitRequestFullScreen();
      } else {
        container2.current.requestFullscreen();
      }
    }, [allowFullscreen, supportsFullScreen]);
    const exitFullscreen = (0, import_react84.useCallback)(() => {
      if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else {
        document.exitFullscreen();
      }
    }, []);
    (0, import_react84.useEffect)(() => {
      const { current } = container2;
      if (!current) {
        return;
      }
      const fullscreenChange = () => {
        const element = document.webkitFullscreenElement ?? document.fullscreenElement;
        if (element && element === container2.current) {
          player.emitter.dispatchFullscreenChange({
            isFullscreen: true
          });
        } else {
          player.emitter.dispatchFullscreenChange({
            isFullscreen: false
          });
        }
      };
      current.addEventListener("webkitfullscreenchange", fullscreenChange);
      current.addEventListener("fullscreenchange", fullscreenChange);
      return () => {
        current.removeEventListener("webkitfullscreenchange", fullscreenChange);
        current.removeEventListener("fullscreenchange", fullscreenChange);
      };
    }, [player.emitter]);
    const durationInFrames = config?.durationInFrames ?? 1;
    const layout = (0, import_react84.useMemo)(() => {
      if (!config || !canvasSize) {
        return null;
      }
      return calculateCanvasTransformation({
        canvasSize,
        compositionHeight: config.height,
        compositionWidth: config.width,
        previewSize: "auto"
      });
    }, [canvasSize, config]);
    const scale = layout?.scale ?? 1;
    const initialScaleIgnored = (0, import_react84.useRef)(false);
    (0, import_react84.useEffect)(() => {
      if (!initialScaleIgnored.current) {
        initialScaleIgnored.current = true;
        return;
      }
      player.emitter.dispatchScaleChange(scale);
    }, [player.emitter, scale]);
    const { setMediaVolume, setMediaMuted } = (0, import_react84.useContext)(Internals.SetMediaVolumeContext);
    const { mediaMuted, mediaVolume } = (0, import_react84.useContext)(Internals.MediaVolumeContext);
    (0, import_react84.useEffect)(() => {
      player.emitter.dispatchVolumeChange(mediaVolume);
    }, [player.emitter, mediaVolume]);
    const isMuted = mediaMuted || mediaVolume === 0;
    (0, import_react84.useEffect)(() => {
      player.emitter.dispatchMuteChange({
        isMuted
      });
    }, [player.emitter, isMuted]);
    const [showBufferIndicator, setShowBufferState] = (0, import_react84.useState)(false);
    (0, import_react84.useEffect)(() => {
      let timeout = null;
      let stopped = false;
      const onBuffer = () => {
        stopped = false;
        requestAnimationFrame(() => {
          if (bufferStateDelayInMilliseconds === 0) {
            setShowBufferState(true);
          } else {
            timeout = setTimeout(() => {
              if (!stopped) {
                setShowBufferState(true);
              }
            }, bufferStateDelayInMilliseconds);
          }
        });
      };
      const onResume = () => {
        requestAnimationFrame(() => {
          stopped = true;
          setShowBufferState(false);
          if (timeout) {
            clearTimeout(timeout);
          }
        });
      };
      player.emitter.addEventListener("waiting", onBuffer);
      player.emitter.addEventListener("resume", onResume);
      return () => {
        player.emitter.removeEventListener("waiting", onBuffer);
        player.emitter.removeEventListener("resume", onResume);
        setShowBufferState(false);
        if (timeout) {
          clearTimeout(timeout);
        }
        stopped = true;
      };
    }, [bufferStateDelayInMilliseconds, player.emitter]);
    (0, import_react84.useImperativeHandle)(ref, () => {
      const methods = {
        play: player.play,
        pause: () => {
          setHasPausedToResume(false);
          player.pause();
        },
        toggle,
        getContainerNode: () => container2.current,
        getCurrentFrame: player.getCurrentFrame,
        isPlaying: player.isPlaying,
        seekTo: (f) => {
          const lastFrame = durationInFrames - 1;
          const frameToSeekTo = Math.max(0, Math.min(lastFrame, f));
          if (player.isPlaying()) {
            const pauseToResume = frameToSeekTo !== lastFrame || loop;
            setHasPausedToResume(pauseToResume);
            player.pause();
          }
          if (frameToSeekTo === lastFrame && !loop) {
            player.emitter.dispatchEnded();
          }
          player.seek(frameToSeekTo);
        },
        isFullscreen: () => {
          const { current } = container2;
          if (!current) {
            return false;
          }
          return document.fullscreenElement === current || document.webkitFullscreenElement === current;
        },
        requestFullscreen,
        exitFullscreen,
        getVolume: () => {
          if (mediaMuted) {
            return 0;
          }
          return mediaVolume;
        },
        setVolume: (vol) => {
          if (typeof vol !== "number") {
            throw new TypeError(`setVolume() takes a number, got value of type ${typeof vol}`);
          }
          if (isNaN(vol)) {
            throw new TypeError(`setVolume() got a number that is NaN. Volume must be between 0 and 1.`);
          }
          if (vol < 0 || vol > 1) {
            throw new TypeError(`setVolume() got a number that is out of range. Must be between 0 and 1, got ${typeof vol}`);
          }
          setMediaVolume(vol);
        },
        isMuted: () => isMuted,
        mute: () => {
          setMediaMuted(true);
        },
        unmute: () => {
          setMediaMuted(false);
        },
        getScale: () => scale,
        pauseAndReturnToPlayStart: () => {
          player.pauseAndReturnToPlayStart();
        }
      };
      return Object.assign(player.emitter, methods);
    }, [
      durationInFrames,
      exitFullscreen,
      loop,
      mediaMuted,
      isMuted,
      mediaVolume,
      player,
      requestFullscreen,
      setMediaMuted,
      setMediaVolume,
      toggle,
      scale
    ]);
    const VideoComponent = video ? video.component : null;
    const outerStyle = (0, import_react84.useMemo)(() => {
      return calculateOuterStyle({
        canvasSize,
        config,
        style: style2,
        overflowVisible,
        layout
      });
    }, [canvasSize, config, layout, overflowVisible, style2]);
    const outer = (0, import_react84.useMemo)(() => {
      return calculateOuter({ config, layout, scale, overflowVisible });
    }, [config, layout, overflowVisible, scale]);
    const containerStyle3 = (0, import_react84.useMemo)(() => {
      return calculateContainerStyle({
        config,
        layout,
        scale,
        overflowVisible
      });
    }, [config, layout, overflowVisible, scale]);
    const playerPause = player.pause;
    const playerDispatchError = player.emitter.dispatchError;
    const onError = (0, import_react84.useCallback)((error2) => {
      playerPause();
      playerDispatchError(error2);
    }, [playerDispatchError, playerPause]);
    const onFullscreenButtonClick = (0, import_react84.useCallback)((e) => {
      e.stopPropagation();
      requestFullscreen();
    }, [requestFullscreen]);
    const onExitFullscreenButtonClick = (0, import_react84.useCallback)((e) => {
      e.stopPropagation();
      exitFullscreen();
    }, [exitFullscreen]);
    const onSingleClick = (0, import_react84.useCallback)((e) => {
      const rightClick = e instanceof MouseEvent ? e.button === 2 : e.nativeEvent.button;
      if (rightClick) {
        return;
      }
      toggle(e);
    }, [toggle]);
    const onSeekStart = (0, import_react84.useCallback)(() => {
      setSeeking(true);
    }, []);
    const onSeekEnd = (0, import_react84.useCallback)(() => {
      setSeeking(false);
    }, []);
    const onDoubleClick = (0, import_react84.useCallback)(() => {
      if (isFullscreen) {
        exitFullscreen();
      } else {
        requestFullscreen();
      }
    }, [exitFullscreen, isFullscreen, requestFullscreen]);
    const { handlePointerDown, handleDoubleClick } = useClickPreventionOnDoubleClick(onSingleClick, onDoubleClick, doubleClickToFullscreen && allowFullscreen && supportsFullScreen);
    (0, import_react84.useEffect)(() => {
      if (shouldAutoplay) {
        player.play();
        setShouldAutoPlay(false);
      }
    }, [shouldAutoplay, player]);
    const loadingMarkup = (0, import_react84.useMemo)(() => {
      return renderLoading ? renderLoading({
        height: outerStyle.height,
        width: outerStyle.width,
        isBuffering: showBufferIndicator
      }) : null;
    }, [outerStyle.height, outerStyle.width, renderLoading, showBufferIndicator]);
    const currentScale = (0, import_react84.useMemo)(() => {
      return {
        type: "scale",
        scale
      };
    }, [scale]);
    if (!config) {
      return null;
    }
    const poster = renderPoster ? renderPoster({
      height: posterFillMode === "player-size" ? outerStyle.height : config.height,
      width: posterFillMode === "player-size" ? outerStyle.width : config.width,
      isBuffering: showBufferIndicator
    }) : null;
    if (poster === void 0) {
      throw new TypeError("renderPoster() must return a React element, but undefined was returned");
    }
    const shouldShowPoster = poster && [
      showPosterWhenPaused && !player.isPlaying() && !seeking,
      showPosterWhenEnded && player.isLastFrame && !player.isPlaying(),
      showPosterWhenUnplayed && !player.hasPlayed && !player.isPlaying(),
      showPosterWhenBuffering && showBufferIndicator && player.isPlaying(),
      showPosterWhenBufferingAndPaused && showBufferIndicator && !player.isPlaying()
    ].some(Boolean);
    const { left, top, width, height, ...outerWithoutScale } = outer;
    const content = /* @__PURE__ */ (0, import_jsx_runtime49.jsxs)(import_jsx_runtime49.Fragment, {
      children: [
        /* @__PURE__ */ (0, import_jsx_runtime49.jsxs)("div", {
          style: outer,
          onPointerDown: clickToPlay ? handlePointerDown : void 0,
          onDoubleClick: doubleClickToFullscreen ? handleDoubleClick : void 0,
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime49.jsxs)("div", {
              style: containerStyle3,
              className: playerCssClassname(overrideInternalClassName),
              children: [
                VideoComponent ? /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(ErrorBoundary, {
                  onError,
                  errorFallback,
                  children: /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(Internals.CurrentScaleContext.Provider, {
                    value: currentScale,
                    children: /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(VideoComponent, {
                      ...video?.props ?? {},
                      ...inputProps ?? {}
                    })
                  })
                }) : null,
                shouldShowPoster && posterFillMode === "composition-size" ? /* @__PURE__ */ (0, import_jsx_runtime49.jsx)("div", {
                  style: {
                    ...outerWithoutScale,
                    width: config.width,
                    height: config.height
                  },
                  onPointerDown: clickToPlay ? handlePointerDown : void 0,
                  onDoubleClick: doubleClickToFullscreen ? handleDoubleClick : void 0,
                  children: poster
                }) : null
              ]
            }),
            /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(RenderWarningIfBlacklist, {})
          ]
        }),
        shouldShowPoster && posterFillMode === "player-size" ? /* @__PURE__ */ (0, import_jsx_runtime49.jsx)("div", {
          style: outer,
          onPointerDown: clickToPlay ? handlePointerDown : void 0,
          onDoubleClick: doubleClickToFullscreen ? handleDoubleClick : void 0,
          children: poster
        }) : null,
        controls ? /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(Controls, {
          fps: config.fps,
          playing: player.playing,
          toggle: player.toggle,
          durationInFrames: config.durationInFrames,
          containerRef: container2,
          onFullscreenButtonClick,
          isFullscreen,
          allowFullscreen,
          showVolumeControls,
          onExitFullscreenButtonClick,
          spaceKeyToPlayOrPause,
          onSeekEnd,
          onSeekStart,
          inFrame,
          outFrame,
          initiallyShowControls,
          canvasSize,
          renderFullscreenButton,
          renderPlayPauseButton,
          alwaysShowControls,
          showPlaybackRateControl,
          buffering: showBufferIndicator,
          hideControlsWhenPointerDoesntMove,
          onDoubleClick: doubleClickToFullscreen ? handleDoubleClick : void 0,
          onPointerDown: clickToPlay ? handlePointerDown : void 0,
          renderMuteButton,
          renderVolumeSlider,
          renderCustomControls
        }) : null
      ]
    });
    if (noSuspense || IS_NODE && !doesReactVersionSupportSuspense) {
      return /* @__PURE__ */ (0, import_jsx_runtime49.jsx)("div", {
        ref: container2,
        style: outerStyle,
        className: className2,
        children: content
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime49.jsx)("div", {
      ref: container2,
      style: outerStyle,
      className: className2,
      children: /* @__PURE__ */ (0, import_jsx_runtime49.jsx)(import_react84.Suspense, {
        fallback: loadingMarkup,
        children: content
      })
    });
  };
  var PlayerUI_default = (0, import_react84.forwardRef)(PlayerUI);
  var DEFAULT_VOLUME_PERSISTANCE_KEY = "remotion.volumePreference";
  var persistVolume = (volume, logLevel, volumePersistenceKey) => {
    if (typeof window === "undefined") {
      return;
    }
    try {
      window.localStorage.setItem(volumePersistenceKey ?? DEFAULT_VOLUME_PERSISTANCE_KEY, String(volume));
    } catch (e) {
      Internals.Log.error({ logLevel, tag: null }, "Could not persist volume", e);
    }
  };
  var getPreferredVolume = (volumePersistenceKey) => {
    if (typeof window === "undefined") {
      return 1;
    }
    try {
      const val = window.localStorage.getItem(volumePersistenceKey ?? DEFAULT_VOLUME_PERSISTANCE_KEY);
      return val ? Number(val) : 1;
    } catch {
      return 1;
    }
  };
  var PLAYER_COMP_ID = "player-comp";
  var SharedPlayerContexts = ({
    children,
    timelineContext,
    fps,
    compositionHeight,
    compositionWidth,
    durationInFrames,
    component,
    numberOfSharedAudioTags,
    initiallyMuted,
    logLevel,
    audioLatencyHint,
    volumePersistenceKey,
    inputProps,
    audioEnabled
  }) => {
    const compositionManagerContext = (0, import_react97.useMemo)(() => {
      const context = {
        compositions: [
          {
            component,
            durationInFrames,
            height: compositionHeight,
            width: compositionWidth,
            fps,
            id: PLAYER_COMP_ID,
            nonce: 777,
            folderName: null,
            parentFolderName: null,
            schema: null,
            calculateMetadata: null
          }
        ],
        folders: [],
        currentCompositionMetadata: {
          defaultCodec: null,
          defaultOutName: null,
          defaultPixelFormat: null,
          defaultProResProfile: null,
          defaultVideoImageFormat: null,
          durationInFrames,
          fps,
          height: compositionHeight,
          width: compositionWidth,
          props: inputProps
        },
        canvasContent: { type: "composition", compositionId: "player-comp" }
      };
      return context;
    }, [
      component,
      durationInFrames,
      compositionHeight,
      compositionWidth,
      fps,
      inputProps
    ]);
    const [mediaMuted, setMediaMuted] = (0, import_react97.useState)(() => initiallyMuted);
    const [mediaVolume, setMediaVolume] = (0, import_react97.useState)(() => getPreferredVolume(volumePersistenceKey ?? null));
    const mediaVolumeContextValue = (0, import_react97.useMemo)(() => {
      return {
        mediaMuted,
        mediaVolume
      };
    }, [mediaMuted, mediaVolume]);
    const setMediaVolumeAndPersist = (0, import_react97.useCallback)((vol) => {
      setMediaVolume(vol);
      persistVolume(vol, logLevel, volumePersistenceKey ?? null);
    }, [logLevel, volumePersistenceKey]);
    const setMediaVolumeContextValue = (0, import_react97.useMemo)(() => {
      return {
        setMediaMuted,
        setMediaVolume: setMediaVolumeAndPersist
      };
    }, [setMediaVolumeAndPersist]);
    const logLevelContext = (0, import_react97.useMemo)(() => {
      return {
        logLevel,
        mountTime: Date.now()
      };
    }, [logLevel]);
    const env = (0, import_react97.useMemo)(() => {
      return {
        isPlayer: true,
        isRendering: false,
        isStudio: false,
        isClientSideRendering: false,
        isReadOnlyStudio: false
      };
    }, []);
    return /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.RemotionEnvironmentContext.Provider, {
      value: env,
      children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.LogLevelContext.Provider, {
        value: logLevelContext,
        children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.CanUseRemotionHooksProvider, {
          children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.TimelineContext.Provider, {
            value: timelineContext,
            children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.CompositionManager.Provider, {
              value: compositionManagerContext,
              children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.PrefetchProvider, {
                children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.DurationsContextProvider, {
                  children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.MediaVolumeContext.Provider, {
                    value: mediaVolumeContextValue,
                    children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.SetMediaVolumeContext.Provider, {
                      value: setMediaVolumeContextValue,
                      children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.SharedAudioContextProvider, {
                        numberOfAudioTags: numberOfSharedAudioTags,
                        audioLatencyHint,
                        audioEnabled,
                        children: /* @__PURE__ */ (0, import_jsx_runtime50.jsx)(Internals.BufferingProvider, {
                          children
                        })
                      })
                    })
                  })
                })
              })
            })
          })
        })
      })
    });
  };
  var warningShown = false;
  var acknowledgeRemotionLicenseMessage = (acknowledge, logLevel) => {
    if (acknowledge) {
      return;
    }
    if (warningShown) {
      return;
    }
    warningShown = true;
    Internals.Log.warn({ logLevel, tag: null }, "Note: Some companies are required to obtain a license to use Remotion. See: https://remotion.dev/license\nPass the `acknowledgeRemotionLicense` prop to `<Player />` function to make this message disappear.");
  };
  var validateSingleFrame = (frame, variableName) => {
    if (typeof frame === "undefined" || frame === null) {
      return frame ?? null;
    }
    if (typeof frame !== "number") {
      throw new TypeError(`"${variableName}" must be a number, but is ${JSON.stringify(frame)}`);
    }
    if (Number.isNaN(frame)) {
      throw new TypeError(`"${variableName}" must not be NaN, but is ${JSON.stringify(frame)}`);
    }
    if (!Number.isFinite(frame)) {
      throw new TypeError(`"${variableName}" must be finite, but is ${JSON.stringify(frame)}`);
    }
    if (frame % 1 !== 0) {
      throw new TypeError(`"${variableName}" must be an integer, but is ${JSON.stringify(frame)}`);
    }
    return frame;
  };
  var validateInOutFrames = ({
    inFrame,
    durationInFrames,
    outFrame
  }) => {
    const validatedInFrame = validateSingleFrame(inFrame, "inFrame");
    const validatedOutFrame = validateSingleFrame(outFrame, "outFrame");
    if (validatedInFrame === null && validatedOutFrame === null) {
      return;
    }
    if (validatedInFrame !== null && validatedInFrame > durationInFrames - 1) {
      throw new Error("inFrame must be less than (durationInFrames - 1), but is " + validatedInFrame);
    }
    if (validatedOutFrame !== null && validatedOutFrame > durationInFrames - 1) {
      throw new Error("outFrame must be less than (durationInFrames - 1), but is " + validatedOutFrame);
    }
    if (validatedInFrame !== null && validatedInFrame < 0) {
      throw new Error("inFrame must be greater than 0, but is " + validatedInFrame);
    }
    if (validatedOutFrame !== null && validatedOutFrame <= 0) {
      throw new Error(`outFrame must be greater than 0, but is ${validatedOutFrame}. If you want to render a single frame, use <Thumbnail /> instead.`);
    }
    if (validatedOutFrame !== null && validatedInFrame !== null && validatedOutFrame <= validatedInFrame) {
      throw new Error("outFrame must be greater than inFrame, but is " + validatedOutFrame + " <= " + validatedInFrame);
    }
  };
  var validateInitialFrame = ({
    initialFrame,
    durationInFrames
  }) => {
    if (typeof durationInFrames !== "number") {
      throw new Error(`\`durationInFrames\` must be a number, but is ${JSON.stringify(durationInFrames)}`);
    }
    if (typeof initialFrame === "undefined") {
      return;
    }
    if (typeof initialFrame !== "number") {
      throw new Error(`\`initialFrame\` must be a number, but is ${JSON.stringify(initialFrame)}`);
    }
    if (Number.isNaN(initialFrame)) {
      throw new Error(`\`initialFrame\` must be a number, but is NaN`);
    }
    if (!Number.isFinite(initialFrame)) {
      throw new Error(`\`initialFrame\` must be a number, but is Infinity`);
    }
    if (initialFrame % 1 !== 0) {
      throw new Error(`\`initialFrame\` must be an integer, but is ${JSON.stringify(initialFrame)}`);
    }
    if (initialFrame > durationInFrames - 1) {
      throw new Error(`\`initialFrame\` must be less or equal than \`durationInFrames - 1\`, but is ${JSON.stringify(initialFrame)}`);
    }
  };
  var validatePlaybackRate = (playbackRate) => {
    if (playbackRate === void 0) {
      return;
    }
    if (playbackRate > 4) {
      throw new Error(`The highest possible playback rate is 4. You passed: ${playbackRate}`);
    }
    if (playbackRate < -4) {
      throw new Error(`The lowest possible playback rate is -4. You passed: ${playbackRate}`);
    }
    if (playbackRate === 0) {
      throw new Error(`A playback rate of 0 is not supported.`);
    }
  };
  var validateFps3 = NoReactInternals.validateFps;
  var validateDimension3 = NoReactInternals.validateDimension;
  var validateDurationInFrames3 = NoReactInternals.validateDurationInFrames;
  var validateDefaultAndInputProps3 = NoReactInternals.validateDefaultAndInputProps;
  var componentOrNullIfLazy = (props) => {
    if ("component" in props) {
      return props.component;
    }
    return null;
  };
  var PlayerFn = ({
    durationInFrames,
    compositionHeight,
    compositionWidth,
    fps,
    inputProps,
    style: style2,
    controls = false,
    loop = false,
    autoPlay = false,
    showVolumeControls = true,
    allowFullscreen = true,
    clickToPlay,
    doubleClickToFullscreen = false,
    spaceKeyToPlayOrPause = true,
    moveToBeginningWhenEnded = true,
    numberOfSharedAudioTags = 5,
    errorFallback = () => "\u26A0\uFE0F",
    playbackRate = 1,
    renderLoading,
    className: className2,
    showPosterWhenUnplayed,
    showPosterWhenEnded,
    showPosterWhenPaused,
    showPosterWhenBuffering,
    showPosterWhenBufferingAndPaused,
    initialFrame,
    renderPoster,
    inFrame,
    outFrame,
    initiallyShowControls,
    renderFullscreenButton,
    renderPlayPauseButton,
    renderVolumeSlider,
    renderCustomControls,
    alwaysShowControls = false,
    initiallyMuted = false,
    showPlaybackRateControl = false,
    posterFillMode = "player-size",
    bufferStateDelayInMilliseconds,
    hideControlsWhenPointerDoesntMove = true,
    overflowVisible = false,
    renderMuteButton,
    browserMediaControlsBehavior: passedBrowserMediaControlsBehavior,
    overrideInternalClassName,
    logLevel = "info",
    noSuspense,
    acknowledgeRemotionLicense,
    audioLatencyHint = "interactive",
    volumePersistenceKey,
    ...componentProps
  }, ref) => {
    if (typeof window !== "undefined") {
      window.remotion_isPlayer = true;
    }
    if (componentProps.defaultProps !== void 0) {
      throw new Error("The <Player /> component does not accept `defaultProps`, but some were passed. Use `inputProps` instead.");
    }
    const componentForValidation = componentOrNullIfLazy(componentProps);
    if (componentForValidation?.type === Composition) {
      throw new TypeError(`'component' should not be an instance of <Composition/>. Pass the React component directly, and set the duration, fps and dimensions as separate props. See https://www.remotion.dev/docs/player/examples for an example.`);
    }
    if (componentForValidation === Composition) {
      throw new TypeError(`'component' must not be the 'Composition' component. Pass your own React component directly, and set the duration, fps and dimensions as separate props. See https://www.remotion.dev/docs/player/examples for an example.`);
    }
    (0, import_react83.useState)(() => acknowledgeRemotionLicenseMessage(Boolean(acknowledgeRemotionLicense), logLevel));
    const component = Internals.useLazyComponent({
      compProps: componentProps,
      componentName: "Player",
      noSuspense: Boolean(noSuspense)
    });
    validateInitialFrame({ initialFrame, durationInFrames });
    const [frame, setFrame] = (0, import_react83.useState)(() => ({
      [PLAYER_COMP_ID]: initialFrame ?? 0
    }));
    const [playing, setPlaying] = (0, import_react83.useState)(false);
    const [rootId] = (0, import_react83.useState)("player-comp");
    const rootRef = (0, import_react83.useRef)(null);
    const audioAndVideoTags = (0, import_react83.useRef)([]);
    const imperativePlaying = (0, import_react83.useRef)(false);
    const [currentPlaybackRate, setCurrentPlaybackRate] = (0, import_react83.useState)(playbackRate);
    if (typeof compositionHeight !== "number") {
      throw new TypeError(`'compositionHeight' must be a number but got '${typeof compositionHeight}' instead`);
    }
    if (typeof compositionWidth !== "number") {
      throw new TypeError(`'compositionWidth' must be a number but got '${typeof compositionWidth}' instead`);
    }
    validateDimension3(compositionHeight, "compositionHeight", "of the <Player /> component");
    validateDimension3(compositionWidth, "compositionWidth", "of the <Player /> component");
    validateDurationInFrames3(durationInFrames, {
      component: "of the <Player/> component",
      allowFloats: false
    });
    validateFps3(fps, "as a prop of the <Player/> component", false);
    validateDefaultAndInputProps3(inputProps, "inputProps", null);
    validateInOutFrames({
      durationInFrames,
      inFrame,
      outFrame
    });
    if (typeof controls !== "boolean" && typeof controls !== "undefined") {
      throw new TypeError(`'controls' must be a boolean or undefined but got '${typeof controls}' instead`);
    }
    if (typeof autoPlay !== "boolean" && typeof autoPlay !== "undefined") {
      throw new TypeError(`'autoPlay' must be a boolean or undefined but got '${typeof autoPlay}' instead`);
    }
    if (typeof loop !== "boolean" && typeof loop !== "undefined") {
      throw new TypeError(`'loop' must be a boolean or undefined but got '${typeof loop}' instead`);
    }
    if (typeof doubleClickToFullscreen !== "boolean" && typeof doubleClickToFullscreen !== "undefined") {
      throw new TypeError(`'doubleClickToFullscreen' must be a boolean or undefined but got '${typeof doubleClickToFullscreen}' instead`);
    }
    if (typeof showVolumeControls !== "boolean" && typeof showVolumeControls !== "undefined") {
      throw new TypeError(`'showVolumeControls' must be a boolean or undefined but got '${typeof showVolumeControls}' instead`);
    }
    if (typeof allowFullscreen !== "boolean" && typeof allowFullscreen !== "undefined") {
      throw new TypeError(`'allowFullscreen' must be a boolean or undefined but got '${typeof allowFullscreen}' instead`);
    }
    if (typeof clickToPlay !== "boolean" && typeof clickToPlay !== "undefined") {
      throw new TypeError(`'clickToPlay' must be a boolean or undefined but got '${typeof clickToPlay}' instead`);
    }
    if (typeof spaceKeyToPlayOrPause !== "boolean" && typeof spaceKeyToPlayOrPause !== "undefined") {
      throw new TypeError(`'spaceKeyToPlayOrPause' must be a boolean or undefined but got '${typeof spaceKeyToPlayOrPause}' instead`);
    }
    if (typeof numberOfSharedAudioTags !== "number" || numberOfSharedAudioTags % 1 !== 0 || !Number.isFinite(numberOfSharedAudioTags) || Number.isNaN(numberOfSharedAudioTags) || numberOfSharedAudioTags < 0) {
      throw new TypeError(`'numberOfSharedAudioTags' must be an integer but got '${numberOfSharedAudioTags}' instead`);
    }
    validatePlaybackRate(currentPlaybackRate);
    (0, import_react83.useEffect)(() => {
      setCurrentPlaybackRate(playbackRate);
    }, [playbackRate]);
    (0, import_react83.useImperativeHandle)(ref, () => rootRef.current, []);
    (0, import_react83.useState)(() => {
      Internals.playbackLogging({
        logLevel,
        message: `[player] Mounting <Player>. User agent = ${typeof navigator === "undefined" ? "server" : navigator.userAgent}`,
        tag: "player",
        mountTime: Date.now()
      });
    });
    const timelineContextValue = (0, import_react83.useMemo)(() => {
      return {
        frame,
        playing,
        rootId,
        playbackRate: currentPlaybackRate,
        imperativePlaying,
        setPlaybackRate: (rate) => {
          setCurrentPlaybackRate(rate);
        },
        audioAndVideoTags
      };
    }, [frame, currentPlaybackRate, playing, rootId]);
    const setTimelineContextValue = (0, import_react83.useMemo)(() => {
      return {
        setFrame,
        setPlaying
      };
    }, [setFrame]);
    if (typeof window !== "undefined") {
      (0, import_react83.useLayoutEffect)(() => {
        Internals.CSSUtils.injectCSS(Internals.CSSUtils.makeDefaultPreviewCSS(`.${playerCssClassname(overrideInternalClassName)}`, "#fff"));
      }, [overrideInternalClassName]);
    }
    const actualInputProps = (0, import_react83.useMemo)(() => inputProps ?? {}, [inputProps]);
    const browserMediaControlsBehavior = (0, import_react83.useMemo)(() => {
      return passedBrowserMediaControlsBehavior ?? {
        mode: "prevent-media-session"
      };
    }, [passedBrowserMediaControlsBehavior]);
    return /* @__PURE__ */ (0, import_jsx_runtime51.jsx)(Internals.IsPlayerContextProvider, {
      children: /* @__PURE__ */ (0, import_jsx_runtime51.jsx)(SharedPlayerContexts, {
        timelineContext: timelineContextValue,
        component,
        compositionHeight,
        compositionWidth,
        durationInFrames,
        fps,
        numberOfSharedAudioTags,
        initiallyMuted,
        logLevel,
        audioLatencyHint,
        volumePersistenceKey,
        inputProps: actualInputProps,
        audioEnabled: true,
        children: /* @__PURE__ */ (0, import_jsx_runtime51.jsx)(Internals.SetTimelineContext.Provider, {
          value: setTimelineContextValue,
          children: /* @__PURE__ */ (0, import_jsx_runtime51.jsx)(PlayerEmitterProvider, {
            currentPlaybackRate,
            children: /* @__PURE__ */ (0, import_jsx_runtime51.jsx)(PlayerUI_default, {
              ref: rootRef,
              posterFillMode,
              renderLoading,
              autoPlay: Boolean(autoPlay),
              loop: Boolean(loop),
              controls: Boolean(controls),
              errorFallback,
              style: style2,
              inputProps: actualInputProps,
              allowFullscreen: Boolean(allowFullscreen),
              moveToBeginningWhenEnded: Boolean(moveToBeginningWhenEnded),
              clickToPlay: typeof clickToPlay === "boolean" ? clickToPlay : Boolean(controls),
              showVolumeControls: Boolean(showVolumeControls),
              doubleClickToFullscreen: Boolean(doubleClickToFullscreen),
              spaceKeyToPlayOrPause: Boolean(spaceKeyToPlayOrPause),
              playbackRate: currentPlaybackRate,
              className: className2 ?? void 0,
              showPosterWhenUnplayed: Boolean(showPosterWhenUnplayed),
              showPosterWhenEnded: Boolean(showPosterWhenEnded),
              showPosterWhenPaused: Boolean(showPosterWhenPaused),
              showPosterWhenBuffering: Boolean(showPosterWhenBuffering),
              showPosterWhenBufferingAndPaused: Boolean(showPosterWhenBufferingAndPaused),
              renderPoster,
              inFrame: inFrame ?? null,
              outFrame: outFrame ?? null,
              initiallyShowControls: initiallyShowControls ?? true,
              renderFullscreen: renderFullscreenButton ?? null,
              renderPlayPauseButton: renderPlayPauseButton ?? null,
              renderMuteButton: renderMuteButton ?? null,
              renderVolumeSlider: renderVolumeSlider ?? null,
              renderCustomControls: renderCustomControls ?? null,
              alwaysShowControls,
              showPlaybackRateControl,
              bufferStateDelayInMilliseconds: bufferStateDelayInMilliseconds ?? 300,
              hideControlsWhenPointerDoesntMove,
              overflowVisible,
              browserMediaControlsBehavior,
              overrideInternalClassName: overrideInternalClassName ?? void 0,
              noSuspense: Boolean(noSuspense)
            })
          })
        })
      })
    });
  };
  var forward = import_react83.forwardRef;
  var Player = forward(PlayerFn);
  var useThumbnail = () => {
    const emitter = (0, import_react100.useContext)(ThumbnailEmitterContext);
    if (!emitter) {
      throw new TypeError("Expected Player event emitter context");
    }
    const returnValue = (0, import_react100.useMemo)(() => {
      return {
        emitter
      };
    }, [emitter]);
    return returnValue;
  };
  var reactVersion2 = import_react99.default.version.split(".")[0];
  if (reactVersion2 === "0") {
    throw new Error(`Version ${reactVersion2} of "react" is not supported by Remotion`);
  }
  var doesReactVersionSupportSuspense2 = parseInt(reactVersion2, 10) >= 18;
  var ThumbnailUI = ({
    style: style2,
    inputProps,
    errorFallback,
    renderLoading,
    className: className2,
    overflowVisible,
    noSuspense,
    overrideInternalClassName
  }, ref) => {
    const config = Internals.useUnsafeVideoConfig();
    const video = Internals.useVideo();
    const container2 = (0, import_react99.useRef)(null);
    const canvasSize = useElementSize(container2, {
      triggerOnWindowResize: false,
      shouldApplyCssTransforms: false
    });
    const layout = (0, import_react99.useMemo)(() => {
      if (!config || !canvasSize) {
        return null;
      }
      return calculateCanvasTransformation({
        canvasSize,
        compositionHeight: config.height,
        compositionWidth: config.width,
        previewSize: "auto"
      });
    }, [canvasSize, config]);
    const scale = layout?.scale ?? 1;
    const thumbnail = useThumbnail();
    useBufferStateEmitter(thumbnail.emitter);
    (0, import_react99.useImperativeHandle)(ref, () => {
      const methods = {
        getContainerNode: () => container2.current,
        getScale: () => scale
      };
      return Object.assign(thumbnail.emitter, methods);
    }, [scale, thumbnail.emitter]);
    const VideoComponent = video ? video.component : null;
    const outerStyle = (0, import_react99.useMemo)(() => {
      return calculateOuterStyle({
        config,
        style: style2,
        canvasSize,
        overflowVisible,
        layout
      });
    }, [canvasSize, config, layout, overflowVisible, style2]);
    const outer = (0, import_react99.useMemo)(() => {
      return calculateOuter({ config, layout, scale, overflowVisible });
    }, [config, layout, overflowVisible, scale]);
    const containerStyle3 = (0, import_react99.useMemo)(() => {
      return calculateContainerStyle({
        config,
        layout,
        scale,
        overflowVisible
      });
    }, [config, layout, overflowVisible, scale]);
    const onError = (0, import_react99.useCallback)((error2) => {
      thumbnail.emitter.dispatchError(error2);
    }, [thumbnail.emitter]);
    const loadingMarkup = (0, import_react99.useMemo)(() => {
      return renderLoading ? renderLoading({
        height: outerStyle.height,
        width: outerStyle.width,
        isBuffering: false
      }) : null;
    }, [outerStyle.height, outerStyle.width, renderLoading]);
    const currentScaleContext = (0, import_react99.useMemo)(() => {
      return {
        type: "scale",
        scale
      };
    }, [scale]);
    if (!config) {
      return null;
    }
    const content = /* @__PURE__ */ (0, import_jsx_runtime52.jsx)("div", {
      style: outer,
      children: /* @__PURE__ */ (0, import_jsx_runtime52.jsx)("div", {
        style: containerStyle3,
        className: playerCssClassname(overrideInternalClassName),
        children: VideoComponent ? /* @__PURE__ */ (0, import_jsx_runtime52.jsx)(ErrorBoundary, {
          onError,
          errorFallback,
          children: /* @__PURE__ */ (0, import_jsx_runtime52.jsx)(Internals.CurrentScaleContext.Provider, {
            value: currentScaleContext,
            children: /* @__PURE__ */ (0, import_jsx_runtime52.jsx)(VideoComponent, {
              ...video?.props ?? {},
              ...inputProps ?? {}
            })
          })
        }) : null
      })
    });
    if (noSuspense || IS_NODE && !doesReactVersionSupportSuspense2) {
      return /* @__PURE__ */ (0, import_jsx_runtime52.jsx)("div", {
        ref: container2,
        style: outerStyle,
        className: className2,
        children: content
      });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime52.jsx)("div", {
      ref: container2,
      style: outerStyle,
      className: className2,
      children: /* @__PURE__ */ (0, import_jsx_runtime52.jsx)(import_react99.Suspense, {
        fallback: loadingMarkup,
        children: content
      })
    });
  };
  var ThumbnailUI_default = (0, import_react99.forwardRef)(ThumbnailUI);
  var ThumbnailFn = ({
    frameToDisplay,
    style: style2,
    inputProps,
    compositionHeight,
    compositionWidth,
    durationInFrames,
    fps,
    className: className2,
    errorFallback = () => "\u26A0\uFE0F",
    renderLoading,
    overflowVisible = false,
    overrideInternalClassName,
    logLevel = "info",
    noSuspense,
    ...componentProps
  }, ref) => {
    if (typeof window !== "undefined") {
      (0, import_react98.useLayoutEffect)(() => {
        window.remotion_isPlayer = true;
      }, []);
    }
    const [thumbnailId] = (0, import_react98.useState)(() => String(random(null)));
    const rootRef = (0, import_react98.useRef)(null);
    const timelineState = (0, import_react98.useMemo)(() => {
      const value = {
        playing: false,
        frame: {
          [PLAYER_COMP_ID]: frameToDisplay
        },
        rootId: thumbnailId,
        imperativePlaying: {
          current: false
        },
        playbackRate: 1,
        setPlaybackRate: () => {
          throw new Error("thumbnail");
        },
        audioAndVideoTags: { current: [] }
      };
      return value;
    }, [frameToDisplay, thumbnailId]);
    (0, import_react98.useImperativeHandle)(ref, () => rootRef.current, []);
    const Component = Internals.useLazyComponent({
      compProps: componentProps,
      componentName: "Thumbnail",
      noSuspense: Boolean(noSuspense)
    });
    const [emitter] = (0, import_react98.useState)(() => new ThumbnailEmitter());
    const passedInputProps = (0, import_react98.useMemo)(() => {
      return inputProps ?? {};
    }, [inputProps]);
    return /* @__PURE__ */ (0, import_jsx_runtime53.jsx)(Internals.IsPlayerContextProvider, {
      children: /* @__PURE__ */ (0, import_jsx_runtime53.jsx)(SharedPlayerContexts, {
        timelineContext: timelineState,
        component: Component,
        compositionHeight,
        compositionWidth,
        durationInFrames,
        fps,
        numberOfSharedAudioTags: 0,
        initiallyMuted: true,
        logLevel,
        audioLatencyHint: "playback",
        inputProps: passedInputProps,
        audioEnabled: false,
        children: /* @__PURE__ */ (0, import_jsx_runtime53.jsx)(ThumbnailEmitterContext.Provider, {
          value: emitter,
          children: /* @__PURE__ */ (0, import_jsx_runtime53.jsx)(ThumbnailUI_default, {
            ref: rootRef,
            className: className2,
            errorFallback,
            inputProps: passedInputProps,
            renderLoading,
            style: style2,
            overflowVisible,
            overrideInternalClassName,
            noSuspense: Boolean(noSuspense)
          })
        })
      })
    });
  };
  var forward2 = import_react98.forwardRef;
  var Thumbnail = forward2(ThumbnailFn);

  // src/simple/CreativeScene.tsx
  var import_react101 = __toESM(require_react());
  var import_jsx_runtime54 = __toESM(require_jsx_runtime());
  var resolveAsset = (path) => path.startsWith("http://") || path.startsWith("https://") ? path : staticFile(path);
  var VALID_LAYOUTS = /* @__PURE__ */ new Set([
    "headline_only",
    "items_grid",
    "items_list",
    "person_card",
    "counter",
    "quote",
    "split",
    "bar",
    "logo_grid",
    "pie",
    "line",
    "flow",
    "timeline",
    "metric_spotlight",
    "metric_wall",
    "rank_list",
    "comparison_table",
    "before_after",
    "icon_stat",
    "stacked_progress",
    "card_carousel",
    "hero_with_context",
    "quote_portrait",
    "annotated_chart",
    "cinematic"
  ]);
  function resolveLayout(data, creative) {
    if (creative.layout && VALID_LAYOUTS.has(creative.layout)) {
      return creative.layout;
    }
    if (creative.displayMode === "logo_grid") return "logo_grid";
    const chartType = data.chartConfig?.type || creative.chartConfig?.type;
    if (creative.displayMode === "pie_chart" || chartType === "pie") return "pie";
    if (creative.displayMode === "line_chart" || chartType === "line") return "line";
    if (chartType === "bar") return "bar";
    return inferFromDataStructure(data, creative);
  }
  function inferFromDataStructure(data, creative) {
    const reveal = creative.reveal || "fade_in";
    const emphasis = creative.emphasis || "none";
    const items = data.items || [];
    const values = data.values || [];
    const headline = creative.headline || "";
    if (emphasis === "quote" || items.length === 1 && /["""']/.test(items[0])) {
      return "quote";
    }
    if (reveal === "split_reveal") return "split";
    if (emphasis === "contrast" && items.length === 2) return "split";
    if (emphasis === "person" && items.length >= 2) return "person_card";
    if (emphasis === "number" || emphasis === "count") {
      const accentMatch = headline.match(/\{\{([^}]+)\}\}/);
      if (accentMatch) {
        const num = (void 0)(accentMatch[1]);
        if (num > 0) return "counter";
      }
    }
    if (emphasis === "sequence" && items.length >= 2) return "items_list";
    if (items.length >= 3 && values.length >= 3 && items.length === values.length && emphasis !== "keyword" && emphasis !== "sequence") {
      return "bar";
    }
    if (items.length >= 3) {
      const headlineLower = headline.toLowerCase();
      const itemsAreData = items.some(
        (item) => item.length > 1 && !headlineLower.includes(item.toLowerCase())
      );
      if (itemsAreData) {
        return items.length >= 6 ? "items_grid" : "items_list";
      }
    }
    if (items.length === 2 && values.length >= 2) return "items_list";
    return "headline_only";
  }
  var MOOD_CONFIGS = {
    dramatic: {
      accent: "#F59E0B",
      accentRgb: "245,158,11",
      speed: 1.2,
      glow: 0.6
    },
    urgent: {
      accent: "#EF4444",
      accentRgb: "239,68,68",
      speed: 1.5,
      glow: 0.8
    },
    somber: {
      accent: "#71717A",
      accentRgb: "113,113,122",
      speed: 0.7,
      glow: 0.2
    },
    informative: {
      accent: "#3B82F6",
      accentRgb: "59,130,246",
      speed: 1,
      glow: 0.3
    },
    contemplative: {
      accent: "#3B82F6",
      accentRgb: "59,130,246",
      speed: 0.6,
      glow: 0.2
    },
    suspense: {
      accent: "#F59E0B",
      accentRgb: "245,158,11",
      speed: 0.8,
      glow: 0.5
    },
    triumphant: {
      accent: "#10B981",
      accentRgb: "16,185,129",
      speed: 1,
      glow: 0.5
    }
  };
  var MOOD_GRADIENTS = {
    dramatic: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a1005 0%, #0A0A0A 70%)",
    urgent: "radial-gradient(ellipse 80% 60% at 50% 40%, #1a0808 0%, #0A0A0A 70%)",
    somber: "radial-gradient(ellipse 80% 60% at 50% 40%, #0d0d0e 0%, #0A0A0A 70%)",
    informative: "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)",
    contemplative: "radial-gradient(ellipse 80% 60% at 50% 40%, #080d1a 0%, #0A0A0A 70%)",
    suspense: "radial-gradient(ellipse 80% 60% at 50% 40%, #14100a 0%, #0A0A0A 70%)",
    triumphant: "radial-gradient(ellipse 80% 60% at 50% 40%, #081a10 0%, #0A0A0A 70%)"
  };
  var MOOD_GRADIENTS_WHITE = {
    dramatic: "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF7E6 0%, #FAFAFA 70%)",
    urgent: "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF1F0 0%, #FAFAFA 70%)",
    somber: "radial-gradient(ellipse 80% 60% at 50% 40%, #F0F0F2 0%, #FAFAFA 70%)",
    informative: "radial-gradient(ellipse 80% 60% at 50% 40%, #EFF4FF 0%, #FAFAFA 70%)",
    contemplative: "radial-gradient(ellipse 80% 60% at 50% 40%, #EFF4FF 0%, #FAFAFA 70%)",
    suspense: "radial-gradient(ellipse 80% 60% at 50% 40%, #FFF8F0 0%, #FAFAFA 70%)",
    triumphant: "radial-gradient(ellipse 80% 60% at 50% 40%, #EFFFEF 0%, #FAFAFA 70%)"
  };
  function hexToRgb(hex) {
    const h = hex.replace("#", "");
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b2 = parseInt(h.substring(4, 6), 16);
    return `${r},${g},${b2}`;
  }
  function getMoodConfig(mood, themeAccent) {
    const base = MOOD_CONFIGS[mood] || MOOD_CONFIGS.informative;
    if (themeAccent && (mood === "dramatic" || mood === "suspense") && base.accent === "#F59E0B") {
      return { ...base, accent: themeAccent, accentRgb: hexToRgb(themeAccent) };
    }
    return base;
  }
  function computeSubtitleDelays(subtitles, count, fps) {
    if (!subtitles.length || count <= 0) return Array(count).fill(0);
    const subCount = subtitles.length;
    return Array.from({ length: count }, (_, i) => {
      const subIdx = Math.min(
        Math.floor(i * subCount / count),
        subCount - 1
      );
      return Math.round(subtitles[subIdx].startSec * fps);
    });
  }
  function computeItemSubtitleDelays(subtitles, items, fps) {
    if (!subtitles.length || !items.length) return items.map(() => 0);
    const itemSubIdx = items.map((item) => {
      const words = item.toLowerCase().replace(/[()（）\[\]'"]/g, " ").split(/\s+/).filter((w) => w.length > 1);
      let bestIdx = 0;
      let bestScore = 0;
      for (let si = 0; si < subtitles.length; si++) {
        const subText = subtitles[si].text.toLowerCase();
        const score = words.filter((w) => subText.includes(w)).length;
        if (score > bestScore) {
          bestScore = score;
          bestIdx = si;
        }
      }
      return bestIdx;
    });
    const groups = /* @__PURE__ */ new Map();
    itemSubIdx.forEach((si, i) => {
      if (!groups.has(si)) groups.set(si, []);
      groups.get(si).push(i);
    });
    const delays = new Array(items.length).fill(0);
    for (const [si, indices] of groups) {
      const startFrame = Math.round(subtitles[si].startSec * fps);
      const endFrame = Math.round(subtitles[si].endSec * fps);
      const available = endFrame - startFrame;
      const staggerGap = indices.length > 1 ? Math.min(Math.round(available / (indices.length + 1)), 30) : 0;
      const offset = Math.min(5, Math.round(available * 0.05));
      indices.forEach((idx, j) => {
        delays[idx] = startFrame + offset + staggerGap * j;
      });
    }
    return delays;
  }
  function computeFixedDelays(reveal, count, speed) {
    const s = (f) => Math.round(f / speed);
    const base = s(8);
    const gap = s(12);
    switch (reveal) {
      case "fade_in":
      case "parallel":
      case "zoom_in":
        return Array(count).fill(base);
      case "stagger":
      case "typewriter":
        return Array.from({ length: count }, (_, i) => base + i * gap);
      case "cascade":
        return Array.from(
          { length: count },
          (_, i) => base + i * Math.round(gap * 1.5)
        );
      case "build_up":
        return Array.from(
          { length: count },
          (_, i) => base + (count - 1 - i) * gap
        );
      case "stagger_then_flash":
        return Array.from(
          { length: count },
          (_, i) => base + i * Math.round(gap * 0.7)
        );
      case "count_up":
      case "dramatic_pause":
        return Array.from(
          { length: count },
          (_, i) => i === 0 ? base : base + s(30)
        );
      case "spotlight":
        return Array.from({ length: count }, (_, i) => s(25) + i * gap);
      case "split_reveal":
        return Array.from({ length: count }, () => s(25));
      default:
        return Array(count).fill(base);
    }
  }
  function getAccentFontSize(emphasis) {
    switch (emphasis) {
      case "number":
        return 80;
      case "keyword":
        return 80;
      case "count":
        return 80;
      default:
        return 80;
    }
  }
  function getBaseFontSize(emphasis) {
    switch (emphasis) {
      case "number":
      case "count":
        return 48;
      case "quote":
        return 48;
      default:
        return 48;
    }
  }
  var EmphasisAccentText = ({
    text,
    emphasis,
    moodCfg,
    countedValues,
    glowOpacity,
    accentFontSizeOverride,
    accentStartIndex = 0
  }) => {
    const C = (void 0)();
    const isCountEmphasis = emphasis === "number" || emphasis === "count";
    const accentSize = accentFontSizeOverride || getAccentFontSize(emphasis);
    const baseSize = getBaseFontSize(emphasis);
    const sizeDiff = accentSize - baseSize;
    const parts = text.split(/(\{\{[^}]+\}\})/g);
    const nonEmpty = parts.filter((p) => p.trim());
    const hasAccent = nonEmpty.some((p) => p.startsWith("{{"));
    const hasNormal = nonEmpty.some((p) => !p.startsWith("{{"));
    const hasMixed = hasAccent && hasNormal;
    let accentIdx = accentStartIndex;
    const renderAccent = (part, pi) => {
      const content = part.slice(2, -2);
      const num = (void 0)(content);
      const isNum = !isNaN(num) && num > 0;
      const currentCountIdx = accentIdx;
      accentIdx++;
      const counted = countedValues[currentCountIdx] || 0;
      const shouldCountUp = isCountEmphasis && isNum && num >= 100;
      const displayText = shouldCountUp ? (void 0)(content, counted) : content;
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        "span",
        {
          style: {
            fontSize: accentSize,
            fontWeight: 800,
            color: moodCfg.accent,
            lineHeight: 1.2,
            textShadow: shouldCountUp ? `0 0 60px rgba(${moodCfg.accentRgb},${glowOpacity})` : void 0
          },
          children: displayText
        },
        pi
      );
    };
    const accentMargin = hasMixed && sizeDiff >= 6 ? "0 12px" : void 0;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(import_jsx_runtime54.Fragment, { children: parts.map((part, pi) => {
      if (part.startsWith("{{") && part.endsWith("}}")) {
        const content = part.slice(2, -2);
        const num = (void 0)(content);
        const isNum = !isNaN(num) && num > 0;
        const currentCountIdx = accentIdx;
        accentIdx++;
        const counted = countedValues[currentCountIdx] || 0;
        const shouldCountUp = isCountEmphasis && isNum && num >= 100;
        const displayText = shouldCountUp ? (void 0)(content, counted) : content;
        return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
          "span",
          {
            style: {
              fontSize: accentSize,
              fontWeight: 800,
              color: moodCfg.accent,
              lineHeight: 1.2,
              verticalAlign: "baseline",
              margin: accentMargin,
              textShadow: shouldCountUp ? `0 0 60px rgba(${moodCfg.accentRgb},${glowOpacity})` : void 0
            },
            children: displayText
          },
          pi
        );
      }
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("span", { style: { color: C.textMuted }, children: part }, pi);
    }) });
  };
  var MoodBackground = ({ mood, transparent }) => {
    const C = (void 0)();
    const isWhite = C.bg === "#FAFAFA";
    const gradients = isWhite ? MOOD_GRADIENTS_WHITE : MOOD_GRADIENTS;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          position: "absolute",
          inset: 0,
          background: transparent ? isWhite ? "rgba(250,250,250,0.45)" : "rgba(10,10,10,0.45)" : gradients[mood] || gradients.informative,
          zIndex: 0
        }
      }
    );
  };
  var SpotlightOverlay = ({ speed }) => {
    const C = (void 0)();
    const isWhite = C.bg === "#FAFAFA";
    const frame = useCurrentFrame();
    const s = (f) => Math.round(f / speed);
    const overlayOpacity = interpolate(
      frame,
      [0, s(30), s(50)],
      isWhite ? [0.6, 0.3, 0.1] : [0.95, 0.7, 0.3],
      void 0
    );
    const size = interpolate(frame, [s(10), s(45)], [100, 600], {
      ...void 0,
      easing: void 0
    });
    const overlayColor = isWhite ? `rgba(200,200,200,${overlayOpacity})` : `rgba(0,0,0,${overlayOpacity})`;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          position: "absolute",
          inset: 0,
          zIndex: 1,
          pointerEvents: "none",
          background: `radial-gradient(circle ${size}px at 50% 45%, transparent 0%, ${overlayColor} 100%)`
        }
      }
    );
  };
  var FlashOverlay = ({ flashAt, accentRgb }) => {
    const frame = useCurrentFrame();
    const flash = interpolate(
      frame,
      [flashAt, flashAt + 4, flashAt + 25],
      [0, 0.15, 0],
      void 0
    );
    return flash > 0 ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          position: "absolute",
          inset: 0,
          zIndex: 10,
          pointerEvents: "none",
          background: `radial-gradient(ellipse at 50% 50%, rgba(${accentRgb},${flash}) 0%, transparent 70%)`
        }
      }
    ) : null;
  };
  var SplitLayout = ({
    lines,
    delays,
    emphasis,
    moodCfg,
    countedValues,
    glowOpacity,
    source,
    mood,
    hasImageBg,
    images,
    descriptions
  }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const leftRef = (0, import_react101.useRef)(null);
    const rightRef = (0, import_react101.useRef)(null);
    const [boxWidth, setBoxWidth] = (0, import_react101.useState)(void 0);
    (0, import_react101.useLayoutEffect)(() => {
      const lw = leftRef.current?.scrollWidth || 0;
      const rw = rightRef.current?.scrollWidth || 0;
      const max = Math.max(lw, rw) + 10;
      if (max > 10) setBoxWidth(max);
    }, []);
    const leftDelay = delays[0] || 0;
    const rightDelay = delays[1] || delays[0] || 0;
    const leftOpacity = interpolate(
      frame,
      [leftDelay, leftDelay + 18],
      [0, 1],
      void 0
    );
    const leftSlide = interpolate(
      frame,
      [leftDelay, leftDelay + 18],
      [-40, 0],
      { ...void 0, easing: void 0 }
    );
    const rightOpacity = interpolate(
      frame,
      [rightDelay, rightDelay + 18],
      [0, 1],
      void 0
    );
    const rightSlide = interpolate(
      frame,
      [rightDelay, rightDelay + 18],
      [40, 0],
      { ...void 0, easing: void 0 }
    );
    const divHeight = interpolate(
      frame,
      [
        Math.min(leftDelay, rightDelay) + 5,
        Math.min(leftDelay, rightDelay) + 30
      ],
      [0, 100],
      { ...void 0, easing: void 0 }
    );
    const vsScale = (void 0)(Math.max(leftDelay, rightDelay) + 10, 15);
    const sourceFade = (void 0)(Math.max(leftDelay, rightDelay) + 40, 15, 0.8);
    const descDelay = Math.max(leftDelay, rightDelay) + 35;
    const descOpacity = interpolate(frame, [descDelay, descDelay + 15], [0, 1], void 0);
    const descSlideY = interpolate(frame, [descDelay, descDelay + 15], [12, 0], { ...void 0, easing: void 0 });
    const winnerIdx = descriptions ? descriptions.findIndex((d) => d?.includes("\uC2B9\uB9AC")) : -1;
    const stampDelay = descDelay + 20;
    const stampEasing = Easing.bezier(0.34, 1.56, 0.64, 1);
    const stampScaleVal = interpolate(frame, [stampDelay, stampDelay + 10], [3, 1], { ...void 0, easing: stampEasing });
    const stampOpacity = interpolate(frame, [stampDelay, stampDelay + 5], [0, 1], void 0);
    const stampRotation = interpolate(frame, [stampDelay, stampDelay + 10], [-15, -5], { ...void 0, easing: void 0 });
    const stampFlash = interpolate(frame, [stampDelay, stampDelay + 3, stampDelay + 12], [0, 0.6, 0], void 0);
    const hasVs = lines.some((l) => /^\s*vs\s*$/i.test(l));
    const leftImg = images?.[0] || null;
    const rightImg = images?.[1] || null;
    const rawLeftDesc = descriptions?.[0] || null;
    const rawRightDesc = descriptions?.[1] || null;
    const leftDesc = rawLeftDesc?.replace(/\s*승리\s*/, "").trim() || rawLeftDesc;
    const rightDesc = rawRightDesc?.replace(/\s*승리\s*/, "").trim() || rawRightDesc;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 1,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "80px 40px"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
              "div",
              {
                style: {
                  display: "grid",
                  gridTemplateColumns: hasImageBg ? "1fr auto 1fr" : "1fr auto 1fr",
                  width: "100%",
                  alignItems: "center"
                },
                children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    "div",
                    {
                      style: {
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        opacity: leftOpacity,
                        transform: `translateX(${leftSlide}px)`
                      },
                      children: /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                        "div",
                        {
                          ref: leftRef,
                          style: {
                            position: "relative",
                            display: "inline-flex",
                            flexDirection: "column",
                            alignItems: "center",
                            textAlign: "center",
                            fontSize: getBaseFontSize(emphasis),
                            fontWeight: 600,
                            lineHeight: 1.6,
                            padding: hasImageBg ? "40px 48px" : "40px 24px",
                            ...hasImageBg ? {
                              backgroundColor: "rgba(0,0,0,0.65)",
                              borderRadius: 16,
                              ...boxWidth ? { width: boxWidth } : {}
                            } : {}
                          },
                          children: [
                            leftImg && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { imageUrl: leftImg, size: 120, style: { margin: "0 auto 16px" } }),
                            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                              EmphasisAccentText,
                              {
                                text: lines[0] || "",
                                emphasis,
                                moodCfg,
                                countedValues,
                                glowOpacity
                              }
                            ),
                            leftDesc && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 30, color: C.textDim, marginTop: 12, fontWeight: 400, opacity: descOpacity, transform: `translateY(${descSlideY}px)` }, children: leftDesc }),
                            winnerIdx === 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(import_jsx_runtime54.Fragment, { children: [
                              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                                position: "absolute",
                                inset: 0,
                                borderRadius: 16,
                                backgroundColor: `rgba(${moodCfg.accentRgb},${stampFlash})`,
                                pointerEvents: "none"
                              } }),
                              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                                position: "absolute",
                                top: -20,
                                right: -20,
                                opacity: stampOpacity,
                                transform: `scale(${stampScaleVal}) rotate(${stampRotation}deg)`,
                                fontSize: 28,
                                fontWeight: 900,
                                color: "#fff",
                                backgroundColor: "#EF4444",
                                padding: "8px 20px",
                                borderRadius: 8,
                                border: "3px solid #fff",
                                boxShadow: "0 4px 20px rgba(239,68,68,0.5)",
                                zIndex: 10,
                                whiteSpace: "nowrap"
                              }, children: "\uC2B9\uB9AC" })
                            ] })
                          ]
                        }
                      )
                    }
                  ),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                    "div",
                    {
                      style: {
                        position: "relative",
                        width: hasVs ? 60 : 24,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0
                      },
                      children: [
                        /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              position: "absolute",
                              width: 2,
                              height: `${divHeight}%`,
                              backgroundColor: moodCfg.accent,
                              opacity: 1
                            }
                          }
                        ),
                        hasVs && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              ...vsScale,
                              fontSize: 30,
                              fontWeight: 800,
                              color: moodCfg.accent,
                              backgroundColor: C.bg,
                              padding: "16px 24px",
                              borderRadius: 8,
                              border: `1px solid ${moodCfg.accent}33`,
                              position: "relative",
                              zIndex: 1
                            },
                            children: "VS"
                          }
                        )
                      ]
                    }
                  ),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    "div",
                    {
                      style: {
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        opacity: rightOpacity,
                        transform: `translateX(${rightSlide}px)`
                      },
                      children: /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                        "div",
                        {
                          ref: rightRef,
                          style: {
                            position: "relative",
                            display: "inline-flex",
                            flexDirection: "column",
                            alignItems: "center",
                            textAlign: "center",
                            fontSize: getBaseFontSize(emphasis),
                            fontWeight: 600,
                            lineHeight: 1.6,
                            padding: hasImageBg ? "40px 48px" : "40px 24px",
                            ...hasImageBg ? {
                              backgroundColor: "rgba(0,0,0,0.65)",
                              borderRadius: 16,
                              ...boxWidth ? { width: boxWidth } : {}
                            } : {}
                          },
                          children: [
                            rightImg && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { imageUrl: rightImg, size: 120, style: { margin: "0 auto 16px" } }),
                            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                              EmphasisAccentText,
                              {
                                text: lines.length > 2 ? lines[2] : lines[1] || "",
                                emphasis,
                                moodCfg,
                                countedValues,
                                glowOpacity
                              }
                            ),
                            rightDesc && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 30, color: C.textDim, marginTop: 12, fontWeight: 400, opacity: descOpacity, transform: `translateY(${descSlideY}px)` }, children: rightDesc }),
                            winnerIdx === 1 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(import_jsx_runtime54.Fragment, { children: [
                              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                                position: "absolute",
                                inset: 0,
                                borderRadius: 16,
                                backgroundColor: `rgba(${moodCfg.accentRgb},${stampFlash})`,
                                pointerEvents: "none"
                              } }),
                              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                                position: "absolute",
                                top: -20,
                                right: -20,
                                opacity: stampOpacity,
                                transform: `scale(${stampScaleVal}) rotate(${stampRotation}deg)`,
                                fontSize: 28,
                                fontWeight: 900,
                                color: "#fff",
                                backgroundColor: "#EF4444",
                                padding: "8px 20px",
                                borderRadius: 8,
                                border: "3px solid #fff",
                                boxShadow: "0 4px 20px rgba(239,68,68,0.5)",
                                zIndex: 10,
                                whiteSpace: "nowrap"
                              }, children: "\uC2B9\uB9AC" })
                            ] })
                          ]
                        }
                      )
                    }
                  )
                ]
              }
            ),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  opacity: sourceFade,
                  fontSize: 18,
                  color: C.textDim,
                  marginTop: 16
                },
                children: source
              }
            )
          ]
        }
      )
    ] });
  };
  var ItemsGrid = ({ items, delays, headlineDelays, moodCfg, reveal, itemIcons, itemFlags }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const cols = items.length === 4 ? items.some((it) => it.length > 8) ? 2 : 4 : items.length >= 5 ? 3 : items.length >= 3 ? 3 : 2;
    const isFlash = reveal === "stagger_then_flash";
    const allDone = Math.max(...delays, ...headlineDelays) + 20;
    const flashGlow = isFlash ? interpolate(frame, [allDone, allDone + 4, allDone + 30], [0, 1, 0.3], void 0) : 0;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: 16,
          width: "100%",
          maxWidth: 1040,
          marginTop: 32
        },
        children: items.map((item, i) => {
          const d = delays[i] || 0;
          const opacity = interpolate(frame, [d, d + 15], [0, 1], void 0);
          const rise = interpolate(frame, [d, d + 15], [12, 0], {
            ...void 0,
            easing: void 0
          });
          const borderGlow = flashGlow > 0 ? `0 0 20px rgba(${moodCfg.accentRgb},${flashGlow})` : "none";
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
            "div",
            {
              style: {
                opacity,
                transform: `translateY(${rise}px)`,
                padding: "14px 16px",
                borderRadius: 10,
                border: `1px solid ${moodCfg.accent}${flashGlow > 0 ? "88" : "33"}`,
                backgroundColor: `rgba(${moodCfg.accentRgb},0.06)`,
                textAlign: "center",
                fontSize: 28,
                fontWeight: 600,
                color: C.text,
                boxShadow: borderGlow,
                transition: "box-shadow 0.1s",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6
              },
              children: itemFlags?.[i] ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { countryCode: itemFlags[i], label: item, width: items.length > 6 ? 120 : 160 }) : /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(import_jsx_runtime54.Fragment, { children: [
                itemIcons?.[i] && (() => {
                  const Ic = (void 0)(itemIcons[i]);
                  return Ic ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { icon: Ic, size: items.length > 6 ? 20 : 24, color: moodCfg.accent }) : null;
                })(),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("span", { children: item })
              ] })
            },
            i
          );
        })
      }
    );
  };
  var PersonCardRow = ({ items, delays, moodCfg, images, itemStatuses }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const count = items.length;
    const cardW = count <= 3 ? 280 : count <= 4 ? 240 : 200;
    const imgH = count <= 3 ? 280 : 240;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "flex",
          gap: 20,
          justifyContent: "center",
          marginTop: 28
        },
        children: items.map((item, i) => {
          const d = delays[i] || 0;
          const opacity = interpolate(frame, [d, d + 18], [0, 1], void 0);
          const slideY = interpolate(frame, [d, d + 18], [30, 0], {
            ...void 0,
            easing: void 0
          });
          const img = images?.[i];
          const imgSrc = img ? resolveAsset(img) : null;
          const status = itemStatuses?.[i];
          const isNegative = status === "negative";
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
            "div",
            {
              style: {
                opacity,
                transform: `translateY(${slideY}px)`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                width: cardW,
                borderRadius: 14,
                backgroundColor: "rgba(255,255,255,0.04)",
                border: `1px solid ${isNegative ? "#EF444455" : moodCfg.accent + "33"}`,
                overflow: "hidden"
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  "div",
                  {
                    style: {
                      width: "100%",
                      height: imgH,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      backgroundColor: isNegative ? "rgba(239,68,68,0.08)" : "rgba(255,255,255,0.02)",
                      overflow: "hidden"
                    },
                    children: imgSrc ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                      Img,
                      {
                        src: imgSrc,
                        style: {
                          width: "100%",
                          height: "100%",
                          objectFit: "cover",
                          objectPosition: "center 20%",
                          filter: isNegative ? "grayscale(0.6)" : "none"
                        }
                      }
                    ) : /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                      "svg",
                      {
                        width: imgH * 0.5,
                        height: imgH * 0.5,
                        viewBox: "0 0 24 24",
                        fill: "none",
                        children: [
                          /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                            "circle",
                            {
                              cx: "12",
                              cy: "8",
                              r: "4",
                              fill: isNegative ? "rgba(239,68,68,0.25)" : "rgba(255,255,255,0.15)"
                            }
                          ),
                          /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                            "path",
                            {
                              d: "M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8",
                              fill: isNegative ? "rgba(239,68,68,0.15)" : "rgba(255,255,255,0.1)"
                            }
                          )
                        ]
                      }
                    )
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                  "div",
                  {
                    style: {
                      padding: "14px 10px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: 6,
                      width: "100%"
                    },
                    children: [
                      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                        "span",
                        {
                          style: {
                            fontSize: count <= 3 ? 24 : 22,
                            fontWeight: 600,
                            color: C.text,
                            textAlign: "center",
                            lineHeight: 1.3
                          },
                          children: item
                        }
                      ),
                      isNegative && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                        "span",
                        {
                          style: {
                            fontSize: 26,
                            fontWeight: 700,
                            color: "#EF4444",
                            letterSpacing: 2
                          },
                          children: "\u2715 \uD3ED\uC0AC"
                        }
                      )
                    ]
                  }
                )
              ]
            },
            i
          );
        })
      }
    );
  };
  var ItemsList = ({ items, delays, headlineDelays, moodCfg, emphasis, concept, images, itemIcons, itemFlags, itemStatuses }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const showBadge = emphasis === "sequence" || emphasis === "person";
    const hasImages = images && images.length > 0;
    const conceptLower = concept.toLowerCase();
    const hasSpotlightHint = conceptLower.includes("spotlight") || conceptLower.includes("\uAC15\uC870") || conceptLower.includes("\uB9C8\uC9C0\uB9C9");
    if (hasImages) {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        "div",
        {
          style: {
            display: "flex",
            gap: 16,
            width: "100%",
            justifyContent: "center",
            flexWrap: "wrap",
            marginTop: 32
          },
          children: items.map((item, i) => {
            const d = delays[i] || 0;
            const opacity = interpolate(frame, [d, d + 18], [0, 1], void 0);
            const slideY = interpolate(frame, [d, d + 18], [24, 0], {
              ...void 0,
              easing: void 0
            });
            const img = images[i] || null;
            const isLast = i === items.length - 1;
            const spotlight = hasSpotlightHint && isLast;
            const imgSrc = img ? resolveAsset(img) : null;
            return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
              "div",
              {
                style: {
                  opacity,
                  transform: `translateY(${slideY}px)`,
                  display: "flex",
                  flexDirection: "column",
                  borderRadius: 12,
                  backgroundColor: spotlight ? `rgba(${moodCfg.accentRgb},0.12)` : "rgba(255,255,255,0.04)",
                  border: `1px solid ${spotlight ? moodCfg.accent : moodCfg.accent + "33"}`,
                  width: items.length <= 3 ? 260 : 200,
                  overflow: "hidden"
                },
                children: [
                  imgSrc && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { width: "100%", height: items.length <= 3 ? 140 : 110, overflow: "hidden" }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    Img,
                    {
                      src: imgSrc,
                      style: {
                        width: "100%",
                        height: "100%",
                        objectFit: "cover"
                      }
                    }
                  ) }),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    "span",
                    {
                      style: {
                        fontSize: 28,
                        fontWeight: spotlight ? 700 : 600,
                        color: spotlight ? moodCfg.accent : C.text,
                        textAlign: "center",
                        lineHeight: 1.3,
                        padding: "14px 12px"
                      },
                      children: item
                    }
                  )
                ]
              },
              i
            );
          })
        }
      );
    }
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "flex",
          flexDirection: "column",
          gap: 12,
          width: "100%",
          maxWidth: 940,
          marginTop: 32
        },
        children: items.map((item, i) => {
          const d = delays[i] || 0;
          const opacity = interpolate(frame, [d, d + 15], [0, 1], void 0);
          const slideX = interpolate(frame, [d, d + 15], [-20, 0], {
            ...void 0,
            easing: void 0
          });
          const isLast = i === items.length - 1;
          const spotlight = hasSpotlightHint && isLast;
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
            "div",
            {
              style: {
                opacity,
                transform: `translateX(${slideX}px)`,
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "12px 20px",
                borderRadius: 10,
                backgroundColor: spotlight ? `rgba(${moodCfg.accentRgb},0.12)` : "rgba(255,255,255,0.03)",
                borderLeft: `3px solid ${spotlight ? moodCfg.accent : moodCfg.accent + "44"}`
              },
              children: [
                itemFlags?.[i] ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { countryCode: itemFlags[i], width: 100 }) : itemIcons?.[i] ? (() => {
                  const Ic = (void 0)(itemIcons[i]);
                  return Ic ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { icon: Ic, size: 36 }) : null;
                })() : null,
                itemStatuses?.[i] && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { status: itemStatuses[i] }),
                showBadge && !itemIcons?.[i] && !itemFlags?.[i] && !itemStatuses?.[i] && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  void 0,
                  {
                    text: emphasis === "person" ? item.charAt(0) : String(i + 1),
                    size: 36,
                    filled: spotlight
                  }
                ),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  "span",
                  {
                    style: {
                      fontSize: 28,
                      fontWeight: spotlight ? 700 : 500,
                      color: spotlight ? moodCfg.accent : C.text,
                      flex: 1
                    },
                    children: item
                  }
                )
              ]
            },
            i
          );
        })
      }
    );
  };
  var QuoteDisplay = ({ items, source, moodCfg, reveal, speed, mood, hasImageBg, portrait }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const s = (f) => Math.round(f / speed);
    const quoteText = items[0] || "";
    const isTypewriter = reveal === "typewriter";
    const charCount = quoteText.length;
    const typeLen = Math.max(charCount * 2, 1);
    const visibleChars = isTypewriter ? Math.floor(
      interpolate(frame, [s(10), s(10) + typeLen], [0, charCount], void 0)
    ) : charCount;
    const displayText = isTypewriter ? quoteText.slice(0, visibleChars) : quoteText;
    const quoteOpacity = interpolate(frame, [s(5), s(15)], [0, 1], void 0);
    const quoteRise = interpolate(frame, [s(5), s(15)], [15, 0], {
      ...void 0,
      easing: void 0
    });
    const markOpacity = interpolate(frame, [s(3), s(10)], [0, 0.25], void 0);
    const sourceOpacity = interpolate(
      frame,
      [s(10) + (isTypewriter ? charCount * 2 + 10 : 25), s(10) + (isTypewriter ? charCount * 2 + 25 : 40)],
      [0, 0.6],
      void 0
    );
    const portraitSrc = portrait ? resolveAsset(portrait) : null;
    const portraitOpacity = interpolate(frame, [0, 20], [0, 1], void 0);
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg || !!portrait }),
      portraitSrc && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "absolute",
            inset: 0,
            zIndex: 0,
            opacity: portraitOpacity * 0.3,
            overflow: "hidden"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              Img,
              {
                src: portraitSrc,
                style: {
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  filter: "blur(2px) grayscale(0.4)"
                }
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  position: "absolute",
                  inset: 0,
                  background: `radial-gradient(ellipse at center, transparent 30%, ${C.bg} 80%)`
                }
              }
            )
          ]
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 1,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "80px 60px"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  fontSize: 120,
                  fontWeight: 800,
                  color: moodCfg.accent,
                  opacity: markOpacity,
                  lineHeight: 1,
                  marginBottom: -30,
                  userSelect: "none"
                },
                children: "\u201C"
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
              "div",
              {
                style: {
                  opacity: quoteOpacity,
                  transform: `translateY(${quoteRise}px)`,
                  fontSize: 44,
                  fontWeight: 600,
                  color: C.text,
                  textAlign: "center",
                  maxWidth: "80%",
                  lineHeight: 1.7,
                  fontStyle: "italic",
                  whiteSpace: "pre-line"
                },
                children: [
                  displayText,
                  isTypewriter && visibleChars < charCount && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    "span",
                    {
                      style: {
                        display: "inline-block",
                        width: 3,
                        height: "1em",
                        backgroundColor: moodCfg.accent,
                        marginLeft: 2,
                        opacity: frame % 20 < 10 ? 1 : 0
                      }
                    }
                  )
                ]
              }
            ),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
              "div",
              {
                style: {
                  opacity: sourceOpacity,
                  fontSize: 18,
                  color: moodCfg.accent,
                  marginTop: 16,
                  fontWeight: 500
                },
                children: [
                  "\u2014 ",
                  source
                ]
              }
            )
          ]
        }
      )
    ] });
  };
  var BRAND_COLORS = {
    apple: "#A2AAAD",
    microsoft: "#00A4EF",
    nvidia: "#76B900",
    amazon: "#FF9900",
    alphabet: "#4285F4",
    google: "#4285F4",
    meta: "#0668E1",
    tesla: "#CC0000"
  };
  var LOGO_IMAGE_PATH = {
    amazon: "logos/amazon.svg",
    microsoft: "logos/microsoft.svg"
  };
  var LogoGridLayout = ({
    items,
    values,
    unit,
    headline,
    moodCfg,
    source,
    mood,
    emphasis,
    countedValues,
    glowOpacity,
    hasImageBg,
    logoMap
  }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const maxVal = Math.max(...values, 1);
    const lines = headline.split("\n").filter((l) => l.trim());
    const headlineFade = (void 0)(5, 15, 0.8);
    const sourceFade = (void 0)(items.length * 8 + 40, 15, 0.8);
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 2,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px 60px",
            gap: 32
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: headlineFade, textAlign: "center", maxWidth: "90%" }, children: lines.map((line, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  fontSize: 48,
                  fontWeight: 700,
                  color: C.text,
                  lineHeight: 1.3
                },
                children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { text: line, baseColor: C.text })
              },
              i
            )) }),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  display: "grid",
                  gridTemplateColumns: items.length <= 4 ? `repeat(${items.length}, 1fr)` : items.length <= 6 ? "repeat(3, 1fr)" : "repeat(4, 1fr)",
                  gap: 24,
                  width: "100%",
                  maxWidth: 1100
                },
                children: items.map((item, i) => {
                  const delay2 = 10 + i * 8;
                  const itemFade = interpolate(frame, [delay2, delay2 + 12], [0, 1], void 0);
                  const itemScale = interpolate(frame, [delay2, delay2 + 12], [0.85, 1], void 0);
                  const key = (logoMap?.[item] || item).toLowerCase().replace(/\s+/g, "");
                  const brandColor = BRAND_COLORS[key] || moodCfg.accent;
                  const logoPath = LOGO_IMAGE_PATH[key];
                  const LogoComp = (void 0)(logoMap?.[item] || item);
                  const val = values[i];
                  return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                    "div",
                    {
                      style: {
                        opacity: itemFade,
                        transform: `scale(${itemScale})`,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: 12,
                        padding: "20px 12px",
                        borderRadius: 16,
                        backgroundColor: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)"
                      },
                      children: [
                        /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              width: 64,
                              height: 64,
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            },
                            children: logoPath ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                              Img,
                              {
                                src: resolveAsset(logoPath),
                                style: { width: 52, height: 52, objectFit: "contain" }
                              }
                            ) : LogoComp ? /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(LogoComp, { size: 52, color: brandColor }) : /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                              "div",
                              {
                                style: {
                                  width: 52,
                                  height: 52,
                                  borderRadius: 12,
                                  backgroundColor: brandColor,
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  fontSize: 24,
                                  fontWeight: 700,
                                  color: "#FFF"
                                },
                                children: item.charAt(0)
                              }
                            )
                          }
                        ),
                        /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              fontSize: 22,
                              fontWeight: 600,
                              color: C.text,
                              textAlign: "center",
                              lineHeight: 1.2
                            },
                            children: item
                          }
                        ),
                        val !== void 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                          "div",
                          {
                            style: {
                              fontSize: 26,
                              fontWeight: 700,
                              color: brandColor
                            },
                            children: [
                              val,
                              unit
                            ]
                          }
                        )
                      ]
                    },
                    i
                  );
                })
              }
            ),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  opacity: sourceFade,
                  fontSize: 18,
                  color: C.textDim,
                  marginTop: 16
                },
                children: source
              }
            )
          ]
        }
      )
    ] });
  };
  var BarDisplay = ({
    items,
    values,
    unit,
    headline,
    moodCfg,
    source,
    mood,
    emphasis,
    countedValues,
    glowOpacity,
    hasImageBg
  }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const hasNegative = values.some((v) => v < 0);
    const maxVal = Math.max(...values, 1);
    const NEG_COLOR = "#EF4444";
    const rangeMin = Math.min(...values, 0);
    const rangeMax = Math.max(...values, 0);
    const totalRange = rangeMax - rangeMin || 1;
    const zeroPos = hasNegative ? Math.abs(rangeMin) / totalRange * 100 : 0;
    const headlineOpacity = interpolate(frame, [5, 18], [0, 1], void 0);
    const headlineRise = interpolate(frame, [5, 18], [15, 0], {
      ...void 0,
      easing: void 0
    });
    const sourceFade = interpolate(
      frame,
      [15 + items.length * 10 + 20, 15 + items.length * 10 + 35],
      [0, 0.4],
      void 0
    );
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 1,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px 80px"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  opacity: headlineOpacity,
                  transform: `translateY(${headlineRise}px)`,
                  fontSize: 48,
                  fontWeight: 600,
                  marginBottom: 32,
                  textAlign: "center",
                  lineHeight: 1.4
                },
                children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  EmphasisAccentText,
                  {
                    text: headline,
                    emphasis,
                    moodCfg,
                    countedValues,
                    glowOpacity,
                    accentFontSizeOverride: 80
                  }
                )
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  width: "100%",
                  maxWidth: 800,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12
                },
                children: items.map((label3, i) => {
                  const d = 15 + i * 10;
                  const val = values[i] || 0;
                  const isNeg = val < 0;
                  const barProgress = interpolate(
                    frame,
                    [d, d + 25],
                    [0, 1],
                    { ...void 0, easing: void 0 }
                  );
                  const labelOpacity = interpolate(frame, [d, d + 12], [0, 1], void 0);
                  const valOpacity = interpolate(
                    frame,
                    [d + 15, d + 25],
                    [0, 1],
                    void 0
                  );
                  const barWidthPct = hasNegative ? Math.abs(val) / totalRange * 100 * barProgress : val / maxVal * 100 * barProgress;
                  return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                    "div",
                    {
                      style: {
                        display: "flex",
                        alignItems: "center",
                        gap: 16,
                        opacity: labelOpacity
                      },
                      children: [
                        /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              width: 200,
                              textAlign: "right",
                              fontSize: 24,
                              fontWeight: 500,
                              color: C.textMuted,
                              flexShrink: 0
                            },
                            children: label3
                          }
                        ),
                        hasNegative ? (
                          /* 마이너스 포함: 0축 기준 양방향 바 */
                          /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                            "div",
                            {
                              style: {
                                flex: 1,
                                height: 32,
                                backgroundColor: "rgba(255,255,255,0.05)",
                                borderRadius: 6,
                                position: "relative"
                              },
                              children: [
                                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                                  "div",
                                  {
                                    style: {
                                      position: "absolute",
                                      left: `${zeroPos}%`,
                                      top: -4,
                                      bottom: -4,
                                      width: 2,
                                      backgroundColor: "rgba(255,255,255,0.3)",
                                      zIndex: 2
                                    }
                                  }
                                ),
                                isNeg ? (
                                  /* 마이너스 바: 0축에서 왼쪽으로 */
                                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                                    "div",
                                    {
                                      style: {
                                        position: "absolute",
                                        right: `${100 - zeroPos}%`,
                                        top: 0,
                                        height: "100%",
                                        width: `${barWidthPct}%`,
                                        backgroundColor: NEG_COLOR,
                                        borderRadius: "6px 0 0 6px"
                                      }
                                    }
                                  )
                                ) : (
                                  /* 플러스 바: 0축에서 오른쪽으로 */
                                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                                    "div",
                                    {
                                      style: {
                                        position: "absolute",
                                        left: `${zeroPos}%`,
                                        top: 0,
                                        height: "100%",
                                        width: `${barWidthPct}%`,
                                        backgroundColor: moodCfg.accent,
                                        borderRadius: "0 6px 6px 0"
                                      }
                                    }
                                  )
                                )
                              ]
                            }
                          )
                        ) : (
                          /* 양수만: 기존 레이아웃 */
                          /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                            "div",
                            {
                              style: {
                                flex: 1,
                                height: 32,
                                backgroundColor: "rgba(255,255,255,0.05)",
                                borderRadius: 6,
                                overflow: "hidden",
                                position: "relative"
                              },
                              children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                                "div",
                                {
                                  style: {
                                    width: `${barWidthPct}%`,
                                    height: "100%",
                                    backgroundColor: moodCfg.accent,
                                    borderRadius: 6
                                  }
                                }
                              )
                            }
                          )
                        ),
                        /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                          "div",
                          {
                            style: {
                              opacity: valOpacity,
                              width: 120,
                              fontSize: 28,
                              fontWeight: 700,
                              color: isNeg ? NEG_COLOR : moodCfg.accent,
                              textAlign: "left",
                              flexShrink: 0
                            },
                            children: (() => {
                              const sign = hasNegative && !isNeg ? "+" : "";
                              const prefix = unit === "$" || unit === "\u20A9" ? unit : "";
                              const suffix = prefix ? "" : unit;
                              return `${prefix}${sign}${val.toLocaleString()}${suffix}`;
                            })()
                          }
                        )
                      ]
                    },
                    i
                  );
                })
              }
            ),
            unit && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  opacity: sourceFade,
                  fontSize: 30,
                  color: C.textMuted,
                  marginTop: 16
                },
                children: unit
              }
            ),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: { opacity: sourceFade, fontSize: 18, color: C.textDim, marginTop: 16 },
                children: source
              }
            )
          ]
        }
      )
    ] });
  };
  var PIE_COLORS = ["#F59E0B", "#3B82F6", "#10B981", "#EF4444", "#8B5CF6", "#6B7280", "#EC4899", "#14B8A6"];
  var PieChartDisplay = ({ items, values, unit, headline, moodCfg, source, mood, hasImageBg, chartConfig }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const lines = headline.split("\n").filter((l) => l.trim());
    const headlineFade = (void 0)(5, 15, 0.8);
    const sourceFade = (void 0)(items.length * 6 + 60, 15, 0.8);
    const maxSlices = chartConfig?.maxSlices ?? 8;
    const displayItems = items.slice(0, maxSlices);
    const displayValues = values.slice(0, maxSlices);
    const total = displayValues.reduce((a2, b2) => a2 + b2, 0);
    const cx = 200, cy = 200, r = 150, strokeW = 60;
    const circumference = 2 * Math.PI * r;
    const sweepProgress = interpolate(frame, [10, 70], [0, 1], { ...void 0, easing: void 0 });
    let accumulated = 0;
    const slices = displayValues.map((val, i) => {
      const fraction = total > 0 ? val / total : 0;
      const startAngle = accumulated;
      accumulated += fraction;
      return { fraction, startAngle, color: PIE_COLORS[i % PIE_COLORS.length] };
    });
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 2,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px 60px",
            gap: 24
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: headlineFade, textAlign: "center", maxWidth: "90%" }, children: lines.map((line, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 48, fontWeight: 700, color: C.text, lineHeight: 1.3 }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { text: line, baseColor: C.text }) }, i)) }),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", alignItems: "center", gap: 48, width: "100%", maxWidth: 1100, justifyContent: "center" }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("svg", { width: 400, height: 400, viewBox: "0 0 400 400", style: { flexShrink: 0 }, children: [
                [...slices].map((_, ri) => {
                  const i = slices.length - 1 - ri;
                  const slice = slices[i];
                  const sliceEnd = slice.startAngle + slice.fraction;
                  let visibleFraction = 0;
                  if (sweepProgress >= sliceEnd) {
                    visibleFraction = slice.fraction;
                  } else if (sweepProgress > slice.startAngle) {
                    visibleFraction = sweepProgress - slice.startAngle;
                  }
                  if (visibleFraction <= 0) return null;
                  const visibleLen = circumference * visibleFraction;
                  return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    "circle",
                    {
                      cx,
                      cy,
                      r,
                      fill: "none",
                      stroke: slice.color,
                      strokeWidth: strokeW,
                      strokeLinecap: "butt",
                      strokeDasharray: `${visibleLen} ${circumference - visibleLen}`,
                      strokeDashoffset: -circumference * slice.startAngle,
                      transform: `rotate(-90 ${cx} ${cy})`,
                      style: { transition: "none" }
                    },
                    i
                  );
                }),
                chartConfig?.showTotal !== false && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("text", { x: cx, y: cy + 8, textAnchor: "middle", fontSize: 32, fontWeight: 700, fill: C.text, children: [
                  total,
                  unit
                ] })
              ] }),
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 12 }, children: displayItems.map((item, i) => {
                const delay2 = 20 + i * 6;
                const labelFade = interpolate(frame, [delay2, delay2 + 12], [0, 1], void 0);
                return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { opacity: labelFade, display: "flex", alignItems: "center", gap: 12 }, children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { width: 20, height: 20, borderRadius: 4, backgroundColor: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 } }),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("span", { style: { fontSize: 22, color: C.text, fontWeight: 500 }, children: item }),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("span", { style: { fontSize: 22, color: PIE_COLORS[i % PIE_COLORS.length], fontWeight: 700, marginLeft: 8 }, children: [
                    displayValues[i],
                    unit
                  ] })
                ] }, i);
              }) })
            ] }),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: sourceFade, fontSize: 18, color: C.textDim, marginTop: 16 }, children: source })
          ]
        }
      )
    ] });
  };
  var LineChartDisplay = ({ items, values, unit, headline, moodCfg, source, mood, hasImageBg, chartConfig }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const lines = headline.split("\n").filter((l) => l.trim());
    const headlineFade = (void 0)(5, 15, 0.8);
    const sourceFade = (void 0)(items.length * 4 + 60, 15, 0.8);
    const showGrid = chartConfig?.showGrid !== false;
    const showDots = chartConfig?.showDots !== false;
    const showArea = chartConfig?.showArea !== false;
    const W = 860, H = 440;
    const padL = 80, padR = 80, padT = 50, padB = 60;
    const chartW = W - padL - padR;
    const chartH = H - padT - padB;
    const maxVal = Math.max(...values, 1);
    const minVal = Math.min(...values, 0);
    const range = maxVal - minVal || 1;
    const points = values.map((v, i) => ({
      x: padL + (items.length > 1 ? i / (items.length - 1) * chartW : chartW / 2),
      y: padT + chartH - (v - minVal) / range * chartH
    }));
    const pathD = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
    const areaD = `${pathD} L${points[points.length - 1].x},${padT + chartH} L${points[0].x},${padT + chartH} Z`;
    const drawProgress = interpolate(frame, [15, 70], [0, 1], { ...void 0, easing: void 0 });
    const clipX = padL + drawProgress * chartW;
    const gridLines = showGrid ? [0, 0.25, 0.5, 0.75, 1].map((frac) => ({
      y: padT + chartH * (1 - frac),
      label: Math.round(minVal + range * frac)
    })) : [];
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBg }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 2,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px 40px",
            gap: 24,
            overflow: "visible"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: headlineFade, textAlign: "center", maxWidth: "90%" }, children: lines.map((line, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 48, fontWeight: 700, color: C.text, lineHeight: 1.3 }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { text: line, baseColor: C.text }) }, i)) }),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, style: { overflow: "visible", flexShrink: 0 }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("defs", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("clipPath", { id: "line-clip", children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("rect", { x: 0, y: 0, width: clipX + 10, height: H + 20 }) }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("linearGradient", { id: "area-grad", x1: "0", y1: "0", x2: "0", y2: "1", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("stop", { offset: "0%", stopColor: moodCfg.accent, stopOpacity: 0.4 }),
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("stop", { offset: "100%", stopColor: moodCfg.accent, stopOpacity: 0.02 })
                ] })
              ] }),
              gridLines.map((gl, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("g", { children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("line", { x1: padL, y1: gl.y, x2: W - padR, y2: gl.y, stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("text", { x: padL - 10, y: gl.y + 5, textAnchor: "end", fontSize: 22, fill: "rgba(255,255,255,0.5)", children: [
                  gl.label,
                  unit
                ] })
              ] }, i)),
              items.map((label3, i) => {
                const x = padL + (items.length > 1 ? i / (items.length - 1) * chartW : chartW / 2);
                const labelFade = interpolate(frame, [15 + i * 3, 20 + i * 3], [0, 1], void 0);
                return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("text", { x, y: H - 10, textAnchor: "middle", fontSize: 22, fill: `rgba(255,255,255,${labelFade * 0.7})`, children: label3 }, i);
              }),
              /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("g", { clipPath: "url(#line-clip)", children: [
                showArea && points.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("path", { d: areaD, fill: "url(#area-grad)" }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("path", { d: pathD, fill: "none", stroke: moodCfg.accent, strokeWidth: 4, strokeLinecap: "round", strokeLinejoin: "round" }),
                showDots && points.map((p, i) => {
                  const dotDelay = 15 + i / (points.length - 1 || 1) * 55;
                  const dotScale = interpolate(frame, [dotDelay, dotDelay + 8], [0, 1], void 0);
                  return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("g", { children: [
                    /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("circle", { cx: p.x, cy: p.y, r: 7 * dotScale, fill: moodCfg.accent, stroke: C.bg, strokeWidth: 2 }),
                    dotScale > 0.5 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
                      "text",
                      {
                        x: p.x,
                        y: p.y - 16,
                        textAnchor: i === points.length - 1 ? "end" : i === 0 ? "start" : "middle",
                        fontSize: 20,
                        fontWeight: 700,
                        fill: C.text,
                        children: [
                          values[i],
                          unit
                        ]
                      }
                    )
                  ] }, i);
                })
              ] })
            ] }),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: sourceFade, fontSize: 18, color: C.textDim, marginTop: 16 }, children: source })
          ]
        }
      )
    ] });
  };
  var BadgeRow = ({ badges, delay: delay2 }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const overshoot = Easing.out(Easing.back(1.7));
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "flex",
          gap: 24,
          justifyContent: "center",
          alignItems: "center",
          marginBottom: 24
        },
        children: badges.map((badge, i) => {
          const d = delay2 + i * 6;
          const f = frame - d;
          const opacity = interpolate(f, [0, 8], [0, 1], {
            ...void 0,
            easing: void 0
          });
          const scale = interpolate(f, [0, 20], [0.5, 1], {
            ...void 0,
            easing: overshoot
          });
          const IconComp = badge.type === "icon" && badge.name ? (void 0)(badge.name) : null;
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
            "div",
            {
              style: {
                opacity,
                transform: `scale(${scale})`,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 8
              },
              children: [
                badge.type === "flag" && badge.code && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { countryCode: badge.code, label: badge.label, width: 100 }),
                badge.type === "icon" && IconComp && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { icon: IconComp, size: 56 }),
                badge.type === "logo" && badge.name && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { logo: badge.name, size: 56 }),
                badge.label && badge.type !== "flag" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  "span",
                  {
                    style: {
                      fontSize: 24,
                      color: C.textMuted,
                      fontWeight: 500
                    },
                    children: badge.label
                  }
                )
              ]
            },
            i
          );
        })
      }
    );
  };
  var StatusDotList = ({ dots, delay: delay2 }) => {
    const frame = useCurrentFrame();
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "flex",
          flexDirection: "column",
          gap: 10,
          marginTop: 24,
          maxWidth: 600
        },
        children: dots.map((dot, i) => {
          const d = delay2 + i * 8;
          const opacity = interpolate(frame, [d, d + 15], [0, 1], void 0);
          const slideX = interpolate(frame, [d, d + 15], [-15, 0], {
            ...void 0,
            easing: void 0
          });
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
            "div",
            {
              style: {
                opacity,
                transform: `translateX(${slideX}px)`
              },
              children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { status: dot.status, label: dot.label })
            },
            i
          );
        })
      }
    );
  };
  var TagRow = ({ tags, delay: delay2 }) => {
    const frame = useCurrentFrame();
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          justifyContent: "center",
          marginTop: 16,
          marginBottom: 8
        },
        children: tags.map((tag, i) => {
          const d = delay2 + i * 5;
          const opacity = interpolate(frame, [d, d + 12], [0, 1], void 0);
          const rise = interpolate(frame, [d, d + 12], [10, 0], {
            ...void 0,
            easing: void 0
          });
          return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
            "div",
            {
              style: { opacity, transform: `translateY(${rise}px)` },
              children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { text: tag.text, active: tag.active, size: "md" })
            },
            i
          );
        })
      }
    );
  };
  var CreativeScene = ({
    data,
    subtitles,
    fps = 30,
    hasImageBackground,
    imageAssetPlacement
  }) => {
    const C = (void 0)();
    const frame = useCurrentFrame();
    const creative = data.creative || {};
    const headline = creative.headline || data.title || "";
    const reveal = creative.reveal || "fade_in";
    const emphasis = creative.emphasis || "none";
    const mood = creative.mood || "informative";
    const source = data.source || "";
    const items = data.items || [];
    const values = data.values || [];
    const unit = data.unit || "";
    const concept = creative.concept || "";
    const badges = data.badges || [];
    const statusDots = data.statusDots || [];
    const tags = data.tags || [];
    const moodCfg = getMoodConfig(mood, C.accent);
    const layout = resolveLayout(data, creative);
    const lines = headline.split("\n").filter((l) => l.trim());
    const headlineLineCount = lines.length;
    const itemCount = layout === "items_grid" || layout === "items_list" ? items.length : 0;
    const LINE_ANIM_DUR = 18;
    const ITEM_ANIM_DUR = 15;
    const headlineSubtitleStarts = subtitles && subtitles.length > 0 ? computeSubtitleDelays(subtitles, headlineLineCount, fps) : computeFixedDelays(reveal, headlineLineCount, moodCfg.speed);
    const headlineDelays = headlineSubtitleStarts.map(
      (d) => Math.max(d - LINE_ANIM_DUR, 0)
    );
    let itemDelays;
    if (itemCount === 0) {
      itemDelays = [];
    } else if (subtitles && subtitles.length > 0) {
      const rawItemDelays = computeItemSubtitleDelays(subtitles, items, fps);
      itemDelays = rawItemDelays.map((d) => Math.max(d - ITEM_ANIM_DUR, 0));
    } else {
      const headlineDone = Math.max(...headlineDelays, 0) + 15;
      itemDelays = computeFixedDelays(reveal, itemCount, moodCfg.speed).map(
        (d) => d + headlineDone
      );
    }
    const allDelays = [...headlineDelays, ...itemDelays];
    const accentMatches = [...headline.matchAll(/\{\{([^}]+)\}\}/g)];
    const numTargets = accentMatches.map((m) => (void 0)(m[1]));
    const isCountEmphasis = emphasis === "number" || emphasis === "count";
    const COUNT_UP_DURATION = 35;
    const accentLineDelays = (() => {
      if (!isCountEmphasis) return [9999, 9999, 9999, 9999];
      let accentI = 0;
      const delays = [];
      for (let li = 0; li < lines.length; li++) {
        const lineAccents = [...lines[li].matchAll(/\{\{[^}]+\}\}/g)];
        for (let _j = 0; _j < lineAccents.length; _j++) {
          const ttsStart = headlineSubtitleStarts[li] || 0;
          delays.push(Math.max(ttsStart - COUNT_UP_DURATION, 0));
          accentI++;
        }
      }
      while (delays.length < 4) delays.push(9999);
      return delays;
    })();
    const counted0 = (void 0)(
      isCountEmphasis && (numTargets[0] || 0) >= 100 ? accentLineDelays[0] : 9999,
      COUNT_UP_DURATION,
      numTargets[0] || 1
    );
    const counted1 = (void 0)(
      isCountEmphasis && (numTargets[1] || 0) >= 100 ? accentLineDelays[1] : 9999,
      COUNT_UP_DURATION,
      numTargets[1] || 1
    );
    const counted2 = (void 0)(
      isCountEmphasis && (numTargets[2] || 0) >= 100 ? accentLineDelays[2] : 9999,
      COUNT_UP_DURATION,
      numTargets[2] || 1
    );
    const counted3 = (void 0)(
      isCountEmphasis && (numTargets[3] || 0) >= 100 ? accentLineDelays[3] : 9999,
      COUNT_UP_DURATION,
      numTargets[3] || 1
    );
    const countedValues = [counted0, counted1, counted2, counted3];
    const earliestCountDelay = Math.min(...accentLineDelays.filter((d) => d < 9999), 9999);
    const glowOpacity = interpolate(
      frame,
      [earliestCountDelay, earliestCountDelay + 40],
      [0, moodCfg.glow],
      void 0
    );
    const sourceFade = (void 0)(Math.max(...allDelays, 0) + 50, 15, 0.8);
    if (layout === "quote") {
      const headlineClean = headline.replace(/\{\{|\}\}/g, "");
      const headlineHasBreak = headline.includes("\n") || headline.includes("\\n");
      const rawQuoteItems = items.length > 0 ? items : data.quote ? [data.quote] : [];
      const isNameOnly = rawQuoteItems.length === 1 && rawQuoteItems[0].length <= 10 && !rawQuoteItems[0].includes(" ");
      const quoteItems = rawQuoteItems.length === 0 || isNameOnly ? [headlineClean] : headlineHasBreak ? [headlineClean] : rawQuoteItems;
      const effectiveSource = isNameOnly && !source ? rawQuoteItems[0] : source;
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        QuoteDisplay,
        {
          items: quoteItems,
          source: effectiveSource,
          moodCfg,
          reveal,
          speed: moodCfg.speed,
          mood,
          hasImageBg: hasImageBackground,
          portrait: data.images?.[0]
        }
      );
    }
    if (layout === "split" && lines.length >= 2) {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        SplitLayout,
        {
          lines,
          delays: headlineDelays,
          emphasis,
          moodCfg,
          countedValues,
          glowOpacity,
          source,
          mood,
          hasImageBg: hasImageBackground,
          images: data.images,
          descriptions: data.descriptions
        }
      );
    }
    if (layout === "pie") {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        PieChartDisplay,
        {
          items,
          values,
          unit,
          headline,
          moodCfg,
          source,
          mood,
          hasImageBg: hasImageBackground,
          chartConfig: creative.chartConfig
        }
      );
    }
    if (layout === "line") {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        LineChartDisplay,
        {
          items,
          values,
          unit,
          headline,
          moodCfg,
          source,
          mood,
          hasImageBg: hasImageBackground,
          chartConfig: creative.chartConfig
        }
      );
    }
    if (layout === "logo_grid") {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        LogoGridLayout,
        {
          items,
          values,
          unit,
          headline,
          moodCfg,
          source,
          mood,
          emphasis,
          countedValues,
          glowOpacity,
          hasImageBg: hasImageBackground,
          logoMap: creative.logoMap
        }
      );
    }
    if (layout === "bar") {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
        BarDisplay,
        {
          items,
          values,
          unit,
          headline,
          moodCfg,
          source,
          mood,
          emphasis,
          countedValues,
          glowOpacity,
          hasImageBg: hasImageBackground
        }
      );
    }
    if (layout === "cinematic") {
      return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(AbsoluteFill, { children: !hasImageBackground && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: false }) });
    }
    const isFlash = reveal === "stagger_then_flash";
    const flashAt = isFlash ? Math.max(...allDelays) + 20 : 9999;
    const hasAssetSide = imageAssetPlacement === "left" || imageAssetPlacement === "right";
    const useFullWidth = hasImageBackground || hasAssetSide || imageAssetPlacement === "fullscreen" || imageAssetPlacement === "center";
    const contentWidth = useFullWidth ? "100%" : "78%";
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(AbsoluteFill, { style: { backgroundColor: hasImageBackground ? "transparent" : C.bg, fontFamily: "inherit" }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { width: contentWidth, height: "100%", margin: "0 auto", position: "relative" }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(MoodBackground, { mood, transparent: hasImageBackground }),
      reveal === "spotlight" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(SpotlightOverlay, { speed: moodCfg.speed }),
      isFlash && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(FlashOverlay, { flashAt, accentRgb: moodCfg.accentRgb }),
      emphasis === "quote" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { position: "relative", zIndex: 2 }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(QuoteMark, { color: moodCfg.accent, delay: headlineDelays[0] || 0 }) }),
      /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
        "div",
        {
          style: {
            position: "relative",
            zIndex: 2,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "60px 48px"
          },
          children: [
            badges.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              BadgeRow,
              {
                badges,
                delay: Math.max((headlineDelays[0] || 0) - 10, 0)
              }
            ),
            /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  textAlign: "center",
                  maxWidth: "95%"
                },
                children: lines.map((line, i) => {
                  const accentOffset = lines.slice(0, i).reduce((sum, l) => sum + [...l.matchAll(/\{\{[^}]+\}\}/g)].length, 0);
                  return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                    LineReveal,
                    {
                      line,
                      delay: headlineDelays[i] || 0,
                      reveal,
                      emphasis,
                      moodCfg,
                      countedValues,
                      glowOpacity,
                      lineIndex: i,
                      totalLines: lines.length,
                      accentOffset
                    },
                    i
                  );
                })
              }
            ),
            tags.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              TagRow,
              {
                tags,
                delay: Math.max(...headlineDelays, 0) + 15
              }
            ),
            layout === "person_card" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              PersonCardRow,
              {
                items,
                delays: itemDelays,
                moodCfg,
                images: data.images,
                itemStatuses: data.itemStatuses
              }
            ),
            layout === "items_grid" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              ItemsGrid,
              {
                items,
                delays: itemDelays,
                headlineDelays,
                moodCfg,
                reveal,
                itemIcons: data.itemIcons,
                itemFlags: data.itemFlags
              }
            ),
            layout === "items_list" && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              ItemsList,
              {
                items,
                delays: itemDelays,
                headlineDelays,
                moodCfg,
                emphasis,
                concept,
                images: data.images,
                itemIcons: data.itemIcons,
                itemFlags: data.itemFlags,
                itemStatuses: data.itemStatuses
              }
            ),
            layout === "flow" && items.length >= 2 && (() => {
              const isHorizontal = items.length <= 4;
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                display: "flex",
                flexDirection: isHorizontal ? "row" : "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 0,
                width: "100%"
              }, children: items.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(import_react101.default.Fragment, { children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { ...(void 0)((void 0)(i, 10, 15), 15) }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { step: i + 1, label: item, active: i === items.length - 1 }) }),
                i < items.length - 1 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: (void 0)((void 0)(i, 10, 15) + 8, 10) }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { direction: isHorizontal ? "right" : "down", length: isHorizontal ? 48 : 32, color: moodCfg.accent }) })
              ] }, i)) });
            })(),
            layout === "timeline" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 4, width: "100%", paddingLeft: 24 }, children: items.map((item, i) => {
              const desc = (data.descriptions || [])[i] || "";
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", gap: 16, alignItems: "flex-start", ...(void 0)((void 0)(i, 12, 15), 15) }, children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 0 }, children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { label: "", active: i === items.length - 1 }),
                  i < items.length - 1 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { width: 2, height: 36, backgroundColor: C.cardBorder } })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 28, fontWeight: 700, color: i === items.length - 1 ? moodCfg.accent : C.text }, children: item }),
                  desc && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 20, color: C.textMuted, marginTop: 4 }, children: desc })
                ] })
              ] }, i);
            }) }),
            layout === "metric_spotlight" && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 16, ...(void 0)(15) }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  label: items[0] || data.title || "",
                  value: values.length > 0 ? `${values[0]}${data.unit || ""}` : "",
                  change: items[1],
                  trend: values.length > 1 ? values[1] > 0 ? "up" : "down" : void 0
                }
              ),
              values.length > 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: (void 0)(30, 15) }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { data: values, width: 200, height: 40, color: moodCfg.accent }) })
            ] }),
            layout === "metric_wall" && items.length >= 2 && (() => {
              const maxLabelLen = Math.max(...items.map((it) => it.length));
              const maxValueLen = Math.max(...values.map((v, i) => `${v}${data.unit || ""}`.length), 0);
              const cardMinW = Math.max(maxLabelLen * 14, maxValueLen * 28) + 48;
              const cols = Math.min(items.length, Math.max(1, Math.floor(1824 / (cardMinW + 24))));
              const gridW = cols * cardMinW + (cols - 1) * 24;
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
                display: "grid",
                gridTemplateColumns: `repeat(${cols}, ${cardMinW}px)`,
                gap: 24,
                width: gridW,
                margin: "0 auto",
                justifyContent: "center"
              }, children: items.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 8, 12), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  label: item,
                  value: values[i] != null ? `${values[i]}${data.unit || ""}` : "",
                  style: { width: "100%" }
                }
              ) }, i)) });
            })(),
            layout === "rank_list" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 16, width: "100%" }, children: items.map((item, i) => {
              const maxVal = Math.max(...values.length ? values : [1]);
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", alignItems: "center", gap: 16, ...(void 0)((void 0)(i, 10, 12), 15) }, children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { rank: i + 1 }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { flex: 1 }, children: [
                  /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 24, fontWeight: 600, color: C.text, marginBottom: 6 }, children: item }),
                  values[i] != null && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { value: values[i], maxValue: maxVal, color: i === 0 ? moodCfg.accent : C.cardBorder })
                ] }),
                values[i] != null && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("span", { style: { fontSize: 24, fontWeight: 700, color: i === 0 ? moodCfg.accent : C.textMuted }, children: [
                  values[i],
                  data.unit || ""
                ] })
              ] }, i);
            }) }),
            layout === "before_after" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", alignItems: "center", gap: 24, justifyContent: "center" }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)(15, 15, -30), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  label: "BEFORE",
                  value: items[0],
                  sublabel: values[0] != null ? `${values[0]}${data.unit || ""}` : void 0,
                  variant: "before",
                  style: { minWidth: 200 }
                }
              ) }),
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: (void 0)(25, 10) }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { direction: "right", length: 48, color: moodCfg.accent }) }),
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)(35, 15, 30), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  label: "AFTER",
                  value: items[1],
                  sublabel: values[1] != null ? `${values[1]}${data.unit || ""}` : void 0,
                  variant: "after",
                  style: { minWidth: 200 }
                }
              ) })
            ] }),
            layout === "comparison_table" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: {
              display: "grid",
              gridTemplateColumns: `repeat(${Math.min(items.length, 4)}, 1fr)`,
              gap: 16,
              width: "100%"
            }, children: items.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 8, 12), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              void 0,
              {
                label: item,
                value: values[i] != null ? `${values[i]}${data.unit || ""}` : "",
                style: { width: "100%" }
              }
            ) }, i)) }),
            layout === "icon_stat" && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 20, ...(void 0)(15) }, children: [
              data.itemIcons?.[0] && (void 0)(data.itemIcons[0]) && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { icon: (void 0)(data.itemIcons[0]), size: 72, filled: true }),
              values[0] != null && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { fontSize: 60, fontWeight: 800, color: moodCfg.accent }, children: [
                values[0],
                data.unit || ""
              ] }),
              items[0] && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 24, color: C.textMuted }, children: items[0] })
            ] }),
            layout === "stacked_progress" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 20, width: "100%", maxWidth: 600 }, children: items.map((item, i) => {
              const maxVal = Math.max(...values.length ? values : [100]);
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 10, 12), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  progress: values[i] != null ? values[i] / maxVal : 0,
                  label: `${item} \u2014 ${values[i] != null ? values[i] : 0}${data.unit || ""}`,
                  color: i === 0 ? moodCfg.accent : `${moodCfg.accent}88`
                }
              ) }, i);
            }) }),
            layout === "card_carousel" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", gap: 20, justifyContent: "center", flexWrap: "wrap" }, children: items.map((item, i) => {
              const desc = (data.descriptions || [])[i] || "";
              return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 10, 15), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(void 0, { style: { minWidth: 200, maxWidth: 280, textAlign: "center" }, children: [
                data.itemIcons?.[i] && (void 0)(data.itemIcons[i]) && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { marginBottom: 12 }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { icon: (void 0)(data.itemIcons[i]), size: 48 }) }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 28, fontWeight: 700, color: C.text, marginBottom: desc ? 8 : 0 }, children: item }),
                desc && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 20, color: C.textMuted }, children: desc })
              ] }) }, i);
            }) }),
            layout === "hero_with_context" && items.length >= 1 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 24, width: "100%", alignItems: "center" }, children: items.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }, children: items.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 8, 30), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { style: { padding: "12px 20px" }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("span", { style: { fontSize: 22, color: C.textMuted }, children: item }) }) }, i)) }) }),
            layout === "quote_portrait" && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", alignItems: "center", gap: 32, ...(void 0)(15, 20) }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                void 0,
                {
                  imageUrl: data.images?.[0],
                  size: 120
                }
              ),
              /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { flex: 1 }, children: [
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { size: 48, color: moodCfg.accent }),
                /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { fontSize: 28, fontWeight: 500, color: C.text, lineHeight: 1.5, fontStyle: "italic" }, children: items[0] || "" }),
                data.source && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { fontSize: 18, color: C.textMuted, marginTop: 16 }, children: [
                  "\u2014 ",
                  data.source
                ] })
              ] })
            ] }),
            layout === "annotated_chart" && items.length >= 2 && /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)("div", { style: { display: "flex", flexDirection: "column", gap: 16, width: "100%" }, children: [
              /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { display: "flex", flexDirection: "column", gap: 12, width: "100%" }, children: items.map((item, i) => {
                const maxVal = Math.max(...values.length ? values : [1]);
                return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: (void 0)((void 0)(i, 10, 12), 15), children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
                  void 0,
                  {
                    value: values[i] || 0,
                    maxValue: maxVal,
                    label: `${item}  ${values[i] != null ? values[i] : ""}${data.unit || ""}`,
                    color: moodCfg.accent,
                    height: 10
                  }
                ) }, i);
              }) }),
              data.annotations?.map((ann, i) => /* @__PURE__ */ (0, import_jsx_runtime54.jsx)("div", { style: { opacity: (void 0)((void 0)(i, 8, 40), 12), paddingLeft: 48 }, children: /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(void 0, { text: ann.text, width: 80, color: moodCfg.accent }) }, i))
            ] }),
            statusDots.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              StatusDotList,
              {
                dots: statusDots,
                delay: itemDelays.length > 0 ? Math.max(...itemDelays) + 15 : Math.max(...headlineDelays, 0) + 30
              }
            ),
            source && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
              "div",
              {
                style: {
                  opacity: sourceFade,
                  fontSize: 18,
                  color: C.textDim,
                  marginTop: 16
                },
                children: source
              }
            )
          ]
        }
      )
    ] }) });
  };
  var LineReveal = ({
    line,
    delay: delay2,
    reveal,
    emphasis,
    moodCfg,
    countedValues,
    glowOpacity,
    lineIndex,
    totalLines,
    accentOffset = 0
  }) => {
    const frame = useCurrentFrame();
    const dur = 18;
    let opacity;
    let transform;
    if (reveal === "zoom_in") {
      opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
      const s = interpolate(frame, [delay2, delay2 + dur], [0.6, 1], {
        ...void 0,
        easing: Easing.out(Easing.exp)
      });
      transform = `scale(${s})`;
    } else if (reveal === "build_up") {
      opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
      const rise = interpolate(frame, [delay2, delay2 + dur], [30, 0], {
        ...void 0,
        easing: void 0
      });
      transform = `translateY(${rise}px)`;
    } else if (reveal === "dramatic_pause") {
      if (lineIndex === 0) {
        opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
        const rise = interpolate(frame, [delay2, delay2 + dur], [20, 0], {
          ...void 0,
          easing: void 0
        });
        transform = `translateY(${rise}px)`;
      } else {
        opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
        const s = interpolate(frame, [delay2, delay2 + 20], [1.3, 1], {
          ...void 0,
          easing: Easing.out(Easing.exp)
        });
        transform = `scale(${s})`;
      }
    } else if (reveal === "stagger_then_flash") {
      opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
      const rise = interpolate(frame, [delay2, delay2 + dur], [15, 0], {
        ...void 0,
        easing: void 0
      });
      transform = `translateY(${rise}px)`;
    } else {
      opacity = interpolate(frame, [delay2, delay2 + dur], [0, 1], void 0);
      const rise = interpolate(frame, [delay2, delay2 + dur], [20, 0], {
        ...void 0,
        easing: void 0
      });
      transform = `translateY(${rise}px)`;
    }
    const isChapterLabel = /^CHAPTER\s*\d/i.test(line.trim());
    const baseFontSize = isChapterLabel ? 30 : getBaseFontSize(emphasis);
    const showBadge = false;
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsxs)(
      "div",
      {
        style: {
          opacity,
          transform,
          fontSize: baseFontSize,
          fontWeight: 600,
          lineHeight: emphasis === "number" || emphasis === "count" ? 2.4 : 1.6,
          marginBottom: lineIndex < totalLines - 1 ? 8 : 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: showBadge ? 16 : 0
        },
        children: [
          showBadge && /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
            void 0,
            {
              text: String(lineIndex + 1),
              size: 40,
              filled: lineIndex === totalLines - 1
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
            EmphasisAccentText,
            {
              text: line,
              emphasis,
              moodCfg,
              countedValues,
              glowOpacity,
              accentStartIndex: accentOffset
            }
          )
        ]
      }
    );
  };
  var QuoteMark = ({
    color,
    delay: delay2
  }) => {
    const qFade = (void 0)(delay2, 15, 10);
    return /* @__PURE__ */ (0, import_jsx_runtime54.jsx)(
      "div",
      {
        style: {
          ...qFade,
          fontSize: 120,
          fontWeight: 800,
          color,
          opacity: qFade.opacity * 0.3,
          lineHeight: 1,
          marginBottom: -20,
          position: "relative",
          zIndex: 2
        },
        children: "\u201C"
      }
    );
  };

  // src/map/MapSceneRenderer.tsx
  var import_react106 = __toESM(require_react());

  // src/visualizations/vizStyles.ts
  var STYLE = {
    background: "#FFFEF8",
    border: "#3D3B2F",
    text: "#3D3B2F",
    subtitle: "#5D5B4F",
    source: "#8D8B7F",
    grid: "#E8E5DC",
    colors: [
      "#F7D94C",
      "#FF8A5C",
      "#5BA8A0",
      "#FF6B8A",
      "#9B8FD9",
      "#6BCB77",
      "#FFB347",
      "#87CEEB",
      "#DDA0DD",
      "#98D8C8"
    ],
    gradients: [
      ["#F7D94C", "#FFE88A"],
      ["#FF8A5C", "#FFB899"],
      ["#5BA8A0", "#8CCCC5"],
      ["#FF6B8A", "#FF9EB2"],
      ["#9B8FD9", "#C2B9EC"],
      ["#6BCB77", "#9EE0A5"]
    ],
    cardBg: "#FFFFFF",
    cardShadow: "0 4px 20px rgba(61,59,47,0.08)",
    cardRadius: 16,
    accentIndex: 0,
    semantic: {
      positive: "#2E7D32",
      positiveBg: "#E8F5E9",
      negative: "#C62828",
      negativeBg: "#FFEBEE"
    }
  };
  var FONT_DEFS = [
    { family: "GriunPolFairness", file: "fonts/Griun_PolFairness-Rg.ttf", weight: "normal" },
    { family: "Pretendard", file: "fonts/Pretendard-Regular.otf", weight: "400" },
    { family: "Pretendard", file: "fonts/Pretendard-Bold.otf", weight: "700" },
    { family: "SBAggroB", file: "fonts/SBAggroB.otf", weight: "700" },
    { family: "SBAggroL", file: "fonts/SBAggroL.otf", weight: "300" }
  ];

  // src/map/MapThemeContext.tsx
  var import_react102 = __toESM(require_react());

  // src/map/mapTheme.ts
  var VINTAGE_PARCHMENT = {
    name: "vintage_parchment",
    surface: {
      ocean: "#D4C5A9",
      land: "#F5E6C8",
      landStroke: "#5E4830",
      landStrokeWidth: 1.8,
      borderStroke: "#3E2E18",
      borderStrokeWidth: 1,
      borderDash: "4,2",
      adminStroke: "#7A6A4C",
      adminStrokeWidth: 0.7,
      adminOpacity: 0.6,
      coastlineStroke: "#5E4830",
      coastlineStrokeWidth: 1.2,
      riverStroke: "#7A6A4C",
      riverStrokeWidth: 1,
      riverOpacity: 0.6,
      lakeFill: "#CFC0A6",
      lakeStroke: "#7A6A4C",
      lakeStrokeWidth: 0.6
    },
    marker: {
      shape: "drop_pin",
      size: 28,
      dotSize: 14,
      borderWidth: 2,
      borderColor: "#F5E6C8",
      shadow: "0 2px 6px rgba(107,91,69,0.4)",
      pulseAmplitude: 0.06,
      labelBg: "transparent",
      labelRadius: 6,
      labelFontSize: 20,
      labelFontWeight: 700,
      labelColor: "#5A4A3A",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(245,230,200,0.92)",
      borderRadius: 10,
      padding: "12px 32px",
      fontSize: 42,
      fontWeight: 700,
      color: "#4A3A2A",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 3px 12px rgba(107,91,69,0.2)",
      letterSpacing: "-0.01em",
      border: "1px solid rgba(139,115,85,0.3)",
      source: {
        fontSize: 16,
        color: "#8B7355",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 8, fadeInEnd: 22, slideDistance: 20, slideDirection: "down" }
    },
    route: {
      style: "dashed",
      defaultColor: "#8B5E3C",
      defaultWidth: 4,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.85,
      dashArray: "10,6"
    },
    label: {
      style: "tag",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 22,
      fontWeight: 600,
      color: "#5A4A3A",
      textShadow: "none",
      badgeBg: "rgba(245,230,200,0.88)",
      badgeRadius: 4,
      badgePadding: "3px 10px",
      badgeShadow: "0 1px 4px rgba(107,91,69,0.2)",
      badgeBorder: "1px solid rgba(139,115,85,0.25)",
      fadeInFrames: 16
    },
    territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.3,
      vignetteColor: "#8B7355",
      grain: 0.12,
      borderDecoration: "ornate",
      borderColor: "#8B7355",
      borderWidth: 2
    },
    animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 16, routeDrawDelay: 15 }
  };
  var MINIMAL_LIGHT = {
    name: "minimal_light",
    surface: {
      ocean: "#E8EDF2",
      land: "#FAFAFA",
      landStroke: "#708090",
      landStrokeWidth: 1.2,
      borderStroke: "#7A8898",
      borderStrokeWidth: 0.8,
      adminStroke: "#8A96A8",
      adminStrokeWidth: 0.6,
      adminOpacity: 0.5,
      coastlineStroke: "#708090",
      coastlineStrokeWidth: 0.8,
      riverStroke: "#7888A0",
      riverStrokeWidth: 0.7,
      riverOpacity: 0.55,
      lakeFill: "#C8D4E0",
      lakeStroke: "#7888A0",
      lakeStrokeWidth: 0.5
    },
    marker: {
      shape: "circle",
      size: 16,
      dotSize: 10,
      borderWidth: 2.5,
      borderColor: "#FFFFFF",
      shadow: "0 1px 4px rgba(0,0,0,0.12)",
      pulseAmplitude: 0.05,
      labelBg: "transparent",
      labelRadius: 20,
      labelFontSize: 18,
      labelFontWeight: 600,
      labelColor: "#3A4450",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(255,255,255,0.85)",
      borderRadius: 10,
      padding: "12px 32px",
      fontSize: 36,
      fontWeight: 700,
      color: "#2A3440",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 3px 12px rgba(0,0,0,0.06)",
      letterSpacing: "-0.01em",
      source: {
        fontSize: 14,
        color: "#8A95A2",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 6, fadeInEnd: 16, slideDistance: 15, slideDirection: "down" }
    },
    route: {
      style: "solid",
      defaultColor: "#4A8FE7",
      defaultWidth: 3.5,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9
    },
    label: {
      style: "pill",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 20,
      fontWeight: 600,
      color: "#3A4450",
      textShadow: "none",
      badgeBg: "rgba(255,255,255,0.88)",
      badgeRadius: 16,
      badgePadding: "4px 14px",
      badgeShadow: "0 1px 4px rgba(0,0,0,0.08)",
      fadeInFrames: 10
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0,
      grain: 0,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 }
  };
  var DARK_ELEGANT = {
    name: "dark_elegant",
    surface: {
      ocean: "#1A1A2E",
      land: "#2D2D44",
      landStroke: "#8888BB",
      landStrokeWidth: 1.4,
      borderStroke: "#9999CC",
      borderStrokeWidth: 1.2,
      adminStroke: "#60608A",
      adminStrokeWidth: 0.6,
      adminOpacity: 0.5,
      coastlineStroke: "#7272A0",
      coastlineStrokeWidth: 1,
      riverStroke: "#60608A",
      riverStrokeWidth: 0.7,
      riverOpacity: 0.55,
      lakeFill: "#22223A",
      lakeStroke: "#60608A",
      lakeStrokeWidth: 0.5
    },
    marker: {
      shape: "ring",
      size: 26,
      dotSize: 14,
      borderWidth: 3,
      borderColor: "#D4AF37",
      shadow: "0 0 12px rgba(212,175,55,0.4)",
      pulseAmplitude: 0.07,
      labelBg: "transparent",
      labelRadius: 8,
      labelFontSize: 20,
      labelFontWeight: 600,
      labelColor: "#E8DCC8",
      labelShadow: "none",
      labelFontFamily: "'Pretendard', sans-serif"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(26,26,46,0.75)",
      borderRadius: 14,
      padding: "14px 36px",
      fontSize: 42,
      fontWeight: 700,
      color: "#E8DCC8",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 4px 20px rgba(0,0,0,0.3)",
      letterSpacing: "-0.01em",
      border: "1px solid rgba(212,175,55,0.2)",
      backdropFilter: "blur(12px)",
      source: {
        fontSize: 15,
        color: "#B0B0CC",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 10, fadeInEnd: 24, slideDistance: 20, slideDirection: "down" }
    },
    route: {
      style: "glow",
      defaultColor: "#D4AF37",
      defaultWidth: 3.5,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9,
      glow: { color: "#D4AF37", width: 12, opacity: 0.25 }
    },
    label: {
      style: "floating",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 22,
      fontWeight: 600,
      color: "#E8DCC8",
      textShadow: "0 0 10px rgba(212,175,55,0.3), 0 1px 3px rgba(0,0,0,0.5)",
      fadeInFrames: 14
    },
    territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.5,
      vignetteColor: "#0A0A1A",
      grain: 0.05,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 14, routeDrawDelay: 18 }
  };
  var BLUEPRINT = {
    name: "blueprint",
    surface: {
      ocean: "#0F2942",
      land: "#1B3A5C",
      landStroke: "#3A6FA5",
      landStrokeWidth: 1,
      borderStroke: "#5A8FBF",
      borderStrokeWidth: 0.6,
      adminStroke: "#2A5A85",
      adminStrokeWidth: 0.3,
      adminOpacity: 0.5,
      coastlineStroke: "#3A6FA5",
      coastlineStrokeWidth: 0.7,
      riverStroke: "#2A5A85",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.5,
      lakeFill: "#143252",
      lakeStroke: "#2A5A85",
      lakeStrokeWidth: 0.3
    },
    marker: {
      shape: "crosshair",
      size: 28,
      dotSize: 16,
      borderWidth: 0,
      borderColor: "transparent",
      shadow: "0 0 8px rgba(122,176,218,0.5)",
      pulseAmplitude: 0.06,
      labelBg: "transparent",
      labelRadius: 3,
      labelFontSize: 18,
      labelFontWeight: 600,
      labelColor: "#7AB0DA",
      labelShadow: "none",
      labelFontFamily: "'Pretendard', monospace"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(15,41,66,0.92)",
      borderRadius: 6,
      padding: "12px 32px",
      fontSize: 36,
      fontWeight: 600,
      color: "#A0D0F0",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 2px 8px rgba(0,0,0,0.3)",
      letterSpacing: "0.01em",
      border: "1px solid rgba(90,143,191,0.35)",
      source: {
        fontSize: 14,
        color: "#8AB8D8",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 4, fadeInEnd: 14, slideDistance: 15, slideDirection: "down" }
    },
    route: {
      style: "dashed",
      defaultColor: "#7AB0DA",
      defaultWidth: 3,
      lineCap: "butt",
      lineJoin: "miter",
      opacity: 0.85,
      dashArray: "8,5"
    },
    label: {
      style: "underline",
      fontFamily: "'Pretendard', monospace",
      fontSize: 20,
      fontWeight: 500,
      color: "#9AC0E0",
      textShadow: "0 1px 2px rgba(0,0,0,0.5)",
      badgeBorder: "2px solid #5A8FBF",
      fadeInFrames: 8
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.25,
      vignetteColor: "#0A1E33",
      grain: 0.08,
      borderDecoration: "corner_marks",
      borderColor: "#3A6FA5",
      borderWidth: 2
    },
    animation: { markerFadeIn: 10, markerScaleFrom: 0.5, labelFadeIn: 8, routeDrawDelay: 10 }
  };
  var WARM_EARTH = {
    name: "warm_earth",
    surface: {
      ocean: "#E8DDD3",
      land: "#F0E8DE",
      landStroke: "#706048",
      landStrokeWidth: 1.2,
      borderStroke: "#806848",
      borderStrokeWidth: 0.6,
      adminStroke: "#8A7A60",
      adminStrokeWidth: 0.4,
      adminOpacity: 0.6,
      coastlineStroke: "#706048",
      coastlineStrokeWidth: 0.8,
      riverStroke: "#8A7A60",
      riverStrokeWidth: 0.6,
      riverOpacity: 0.55,
      lakeFill: "#D5CCC0",
      lakeStroke: "#8A7A60",
      lakeStrokeWidth: 0.4
    },
    marker: {
      shape: "drop_pin",
      size: 26,
      dotSize: 14,
      borderWidth: 2.5,
      borderColor: "#FFFFFF",
      shadow: "0 2px 8px rgba(106,90,74,0.3)",
      pulseAmplitude: 0.07,
      labelBg: "transparent",
      labelRadius: 10,
      labelFontSize: 20,
      labelFontWeight: 700,
      labelColor: "#5A4A3A",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(255,255,250,0.9)",
      borderRadius: 14,
      padding: "12px 32px",
      fontSize: 42,
      fontWeight: 700,
      color: "#4A3A2A",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 3px 14px rgba(106,90,74,0.15)",
      letterSpacing: "-0.01em",
      source: {
        fontSize: 15,
        color: "#A89078",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 8, fadeInEnd: 20, slideDistance: 18, slideDirection: "down" }
    },
    route: {
      style: "solid",
      defaultColor: "#A0522D",
      defaultWidth: 5,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.85
    },
    label: {
      style: "card",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 22,
      fontWeight: 600,
      color: "#5A4A3A",
      textShadow: "none",
      badgeBg: "rgba(255,255,250,0.9)",
      badgeRadius: 8,
      badgePadding: "4px 12px",
      badgeShadow: "0 2px 6px rgba(106,90,74,0.15)",
      fadeInFrames: 12
    },
    territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.2,
      vignetteColor: "#8A7A6A",
      grain: 0,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 15, markerScaleFrom: 0.3, labelFadeIn: 12, routeDrawDelay: 15 }
  };
  var MODERN_CLEAN = {
    name: "modern_clean",
    surface: {
      ocean: "#E8EDF2",
      land: "#FAFAFA",
      landStroke: "#B0B8C4",
      landStrokeWidth: 0.8,
      borderStroke: "#CCD3DC",
      borderStrokeWidth: 0.5,
      adminStroke: "#D8DFE8",
      adminStrokeWidth: 0.3,
      adminOpacity: 0.5,
      coastlineStroke: "#B0B8C4",
      coastlineStrokeWidth: 0.6,
      riverStroke: "#B8C8DC",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.4,
      lakeFill: "#D8E4F0",
      lakeStroke: "#C0D0E0",
      lakeStrokeWidth: 0.3
    },
    marker: {
      shape: "circle",
      size: 20,
      dotSize: 12,
      borderWidth: 3,
      borderColor: "#FFFFFF",
      shadow: "0 2px 8px rgba(0,0,0,0.25)",
      pulseAmplitude: 0.08,
      labelBg: "transparent",
      labelRadius: 8,
      labelFontSize: 22,
      labelFontWeight: 700,
      labelColor: "#2A3440",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(255,255,255,0.88)",
      borderRadius: 12,
      padding: "12px 32px",
      fontSize: 44,
      fontWeight: 700,
      color: "#3D3B2F",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 4px 16px rgba(0,0,0,0.12)",
      letterSpacing: "-0.01em",
      source: {
        fontSize: 16,
        color: "#8D8B7F",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 8, fadeInEnd: 20, slideDistance: 20, slideDirection: "down" }
    },
    route: {
      style: "solid",
      defaultColor: "#FF6B6B",
      defaultWidth: 4.5,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9
    },
    label: {
      style: "card",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 24,
      fontWeight: 600,
      color: "#2A3440",
      textShadow: "none",
      badgeBg: "rgba(255,255,255,0.9)",
      badgeRadius: 8,
      badgePadding: "4px 12px",
      badgeShadow: "0 2px 8px rgba(0,0,0,0.12)",
      fadeInFrames: 12
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0,
      grain: 0,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 15, markerScaleFrom: 0.3, labelFadeIn: 12, routeDrawDelay: 15 }
  };
  var HISTORICAL = {
    name: "historical",
    surface: {
      ocean: "#E8DDD3",
      land: "#F0E8DE",
      landStroke: "#A89078",
      landStrokeWidth: 1,
      borderStroke: "#B8A088",
      borderStrokeWidth: 0.5,
      adminStroke: "#C8B8A8",
      adminStrokeWidth: 0.3,
      adminOpacity: 0.6,
      coastlineStroke: "#A89078",
      coastlineStrokeWidth: 0.7,
      riverStroke: "#C0B0A0",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.45,
      lakeFill: "#DDD4C8",
      lakeStroke: "#C0B0A0",
      lakeStrokeWidth: 0.3,
      cssFilter: "sepia(0.25) saturate(0.8) brightness(0.95)"
    },
    marker: {
      shape: "drop_pin",
      size: 24,
      dotSize: 14,
      borderWidth: 2.5,
      borderColor: "#F5E6C8",
      shadow: "0 2px 6px rgba(90,74,58,0.35)",
      pulseAmplitude: 0.06,
      labelBg: "transparent",
      labelRadius: 6,
      labelFontSize: 20,
      labelFontWeight: 700,
      labelColor: "#5A4A3A",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(245,230,200,0.9)",
      borderRadius: 10,
      padding: "12px 32px",
      fontSize: 42,
      fontWeight: 700,
      color: "#4A3A2A",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 3px 12px rgba(90,74,58,0.18)",
      letterSpacing: "-0.01em",
      source: {
        fontSize: 15,
        color: "#8B7355",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 8, fadeInEnd: 22, slideDistance: 20, slideDirection: "down" }
    },
    route: {
      style: "dashed",
      defaultColor: "#7A5C3C",
      defaultWidth: 4,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.85,
      dashArray: "8,5"
    },
    label: {
      style: "tag",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 22,
      fontWeight: 600,
      color: "#5A4A3A",
      textShadow: "none",
      badgeBg: "rgba(245,230,200,0.85)",
      badgeRadius: 4,
      badgePadding: "3px 10px",
      badgeShadow: "0 1px 4px rgba(90,74,58,0.18)",
      badgeBorder: "1px solid rgba(139,115,85,0.2)",
      fadeInFrames: 14
    },
    territory: { strokeWidth: 1.5, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.2,
      vignetteColor: "#8B7355",
      grain: 0.08,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 18, markerScaleFrom: 0.3, labelFadeIn: 14, routeDrawDelay: 15 }
  };
  var DARK_CYBER = {
    name: "dark_cyber",
    surface: {
      ocean: "#0A0E17",
      land: "#141B2A",
      landStroke: "#2A3A50",
      landStrokeWidth: 0.8,
      borderStroke: "#3A4A60",
      borderStrokeWidth: 0.5,
      adminStroke: "#1E2A3C",
      adminStrokeWidth: 0.3,
      adminOpacity: 0.5,
      coastlineStroke: "#2A3A50",
      coastlineStrokeWidth: 0.6,
      riverStroke: "#1A2A3C",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.4,
      lakeFill: "#0E1420",
      lakeStroke: "#1A2A3C",
      lakeStrokeWidth: 0.3
    },
    marker: {
      shape: "diamond",
      size: 22,
      dotSize: 14,
      borderWidth: 0,
      borderColor: "transparent",
      shadow: "0 0 14px rgba(0,255,210,0.5)",
      pulseAmplitude: 0.08,
      labelBg: "transparent",
      labelRadius: 4,
      labelFontSize: 18,
      labelFontWeight: 600,
      labelColor: "#00FFD2",
      labelShadow: "none",
      labelFontFamily: "'Pretendard', sans-serif"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(10,14,23,0.85)",
      borderRadius: 8,
      padding: "12px 32px",
      fontSize: 38,
      fontWeight: 700,
      color: "#E0F0FF",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 4px 16px rgba(0,0,0,0.4)",
      letterSpacing: "0.01em",
      border: "1px solid rgba(0,255,210,0.2)",
      source: {
        fontSize: 14,
        color: "#8AB0C8",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 4, fadeInEnd: 14, slideDistance: 15, slideDirection: "down" }
    },
    route: {
      style: "glow",
      defaultColor: "#00FFD2",
      defaultWidth: 3,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9,
      glow: { color: "#00FFD2", width: 14, opacity: 0.3 }
    },
    label: {
      style: "pill",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 20,
      fontWeight: 600,
      color: "#00FFD2",
      textShadow: "0 0 6px rgba(0,255,210,0.3)",
      badgeBg: "rgba(10,14,23,0.8)",
      badgeRadius: 14,
      badgePadding: "3px 14px",
      badgeBorder: "1px solid rgba(0,255,210,0.3)",
      fadeInFrames: 8
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.4,
      vignetteColor: "#000510",
      grain: 0,
      borderDecoration: "thin_line",
      borderColor: "#00FFD2",
      borderWidth: 1
    },
    animation: { markerFadeIn: 10, markerScaleFrom: 0.5, labelFadeIn: 8, routeDrawDelay: 10 }
  };
  var CLEAN_WHITE = {
    name: "clean_white",
    surface: {
      ocean: "#D6E6F5",
      land: "#FFFFFF",
      landStroke: "#C0C8D4",
      landStrokeWidth: 0.8,
      borderStroke: "#A0AAB8",
      borderStrokeWidth: 0.7,
      adminStroke: "#C8D0DC",
      adminStrokeWidth: 0.4,
      adminOpacity: 0.5,
      coastlineStroke: "#A0B4C8",
      coastlineStrokeWidth: 0.7,
      riverStroke: "#A0C0E0",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.5,
      lakeFill: "#D0E4F8",
      lakeStroke: "#A0C0E0",
      lakeStrokeWidth: 0.4
    },
    marker: {
      shape: "circle",
      size: 20,
      dotSize: 12,
      borderWidth: 3,
      borderColor: "#FFFFFF",
      shadow: "0 2px 8px rgba(0,0,0,0.18)",
      pulseAmplitude: 0.06,
      labelBg: "transparent",
      labelRadius: 8,
      labelFontSize: 22,
      labelFontWeight: 700,
      labelColor: "#1A2030",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(255,255,255,0.95)",
      borderRadius: 12,
      padding: "12px 32px",
      fontSize: 42,
      fontWeight: 700,
      color: "#1A2030",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 2px 12px rgba(0,0,0,0.08)",
      letterSpacing: "-0.01em",
      border: "1px solid rgba(0,0,0,0.06)",
      source: {
        fontSize: 15,
        color: "#7A8494",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 6, fadeInEnd: 18, slideDistance: 16, slideDirection: "down" }
    },
    route: {
      style: "solid",
      defaultColor: "#F59E0B",
      defaultWidth: 4.5,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9
    },
    label: {
      style: "card",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 22,
      fontWeight: 600,
      color: "#1A2030",
      textShadow: "none",
      badgeBg: "rgba(255,255,255,0.95)",
      badgeRadius: 8,
      badgePadding: "4px 14px",
      badgeShadow: "0 1px 6px rgba(0,0,0,0.08)",
      badgeBorder: "1px solid rgba(0,0,0,0.06)",
      fadeInFrames: 10
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0,
      grain: 0,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 }
  };
  var MATTE_SLATE = {
    name: "matte_slate",
    surface: {
      ocean: "#15171C",
      land: "#1E2028",
      landStroke: "#3A3D48",
      landStrokeWidth: 1,
      borderStroke: "#4A4D58",
      borderStrokeWidth: 0.8,
      adminStroke: "#2A2D38",
      adminStrokeWidth: 0.4,
      adminOpacity: 0.5,
      coastlineStroke: "#3A3D48",
      coastlineStrokeWidth: 0.8,
      riverStroke: "#2A2D38",
      riverStrokeWidth: 0.5,
      riverOpacity: 0.4,
      lakeFill: "#1A1C24",
      lakeStroke: "#2A2D38",
      lakeStrokeWidth: 0.4
    },
    marker: {
      shape: "circle",
      size: 20,
      dotSize: 12,
      borderWidth: 2.5,
      borderColor: "#FFFFFF",
      shadow: "0 2px 8px rgba(0,0,0,0.4)",
      pulseAmplitude: 0.06,
      labelBg: "transparent",
      labelRadius: 6,
      labelFontSize: 20,
      labelFontWeight: 600,
      labelColor: "#E8E8EC",
      labelShadow: "none"
    },
    title: {
      layout: "top_center_card",
      background: "rgba(30,32,40,0.92)",
      borderRadius: 10,
      padding: "12px 32px",
      fontSize: 40,
      fontWeight: 700,
      color: "#F0F0F4",
      fontFamily: "'Pretendard', sans-serif",
      shadow: "0 4px 16px rgba(0,0,0,0.3)",
      letterSpacing: "-0.01em",
      border: "1px solid rgba(255,255,255,0.08)",
      source: {
        fontSize: 15,
        color: "#8A8D98",
        fontFamily: "'Pretendard', sans-serif"
      },
      animation: { fadeInStart: 6, fadeInEnd: 18, slideDistance: 15, slideDirection: "down" }
    },
    route: {
      style: "solid",
      defaultColor: "#5C6BC0",
      defaultWidth: 4,
      lineCap: "round",
      lineJoin: "round",
      opacity: 0.9
    },
    label: {
      style: "card",
      fontFamily: "'Pretendard', sans-serif",
      fontSize: 20,
      fontWeight: 600,
      color: "#E8E8EC",
      textShadow: "none",
      badgeBg: "rgba(30,32,40,0.9)",
      badgeRadius: 6,
      badgePadding: "4px 12px",
      badgeShadow: "0 2px 6px rgba(0,0,0,0.3)",
      badgeBorder: "1px solid rgba(255,255,255,0.06)",
      fadeInFrames: 10
    },
    territory: { strokeWidth: 1, strokeOpacityMultiplier: 2 },
    atmosphere: {
      vignette: 0.2,
      vignetteColor: "#0A0A10",
      grain: 0,
      borderDecoration: "none"
    },
    animation: { markerFadeIn: 12, markerScaleFrom: 0.4, labelFadeIn: 10, routeDrawDelay: 12 }
  };
  var MAP_THEMES = {
    vintage_parchment: VINTAGE_PARCHMENT,
    minimal_light: MINIMAL_LIGHT,
    dark_elegant: DARK_ELEGANT,
    blueprint: BLUEPRINT,
    warm_earth: WARM_EARTH,
    modern_clean: MODERN_CLEAN,
    historical: HISTORICAL,
    dark_cyber: DARK_CYBER,
    matte_slate: MATTE_SLATE,
    clean_white: CLEAN_WHITE
  };
  function resolveMapTheme(name) {
    if (!name) return MODERN_CLEAN;
    return MAP_THEMES[name] ?? MODERN_CLEAN;
  }

  // src/map/MapThemeContext.tsx
  var import_jsx_runtime55 = __toESM(require_jsx_runtime());
  var MapThemeCtx = (0, import_react102.createContext)(null);
  var MapThemeProvider = ({ theme, children }) => {
    const resolved = (0, import_react102.useMemo)(
      () => typeof theme === "string" ? resolveMapTheme(theme) : theme,
      [theme]
    );
    return /* @__PURE__ */ (0, import_jsx_runtime55.jsx)(MapThemeCtx.Provider, { value: resolved, children });
  };
  var useMapTheme = () => {
    const ctx = (0, import_react102.useContext)(MapThemeCtx);
    if (!ctx) throw new Error("useMapTheme must be used within MapThemeProvider");
    return ctx;
  };

  // src/map/RemotionMap.tsx
  var import_react103 = __toESM(require_react());
  var import_maplibre_gl = __toESM(__require("maplibre-gl"));

  // src/map/mapStyles.ts
  function applyLayerOverrides(map, overrides) {
    const style2 = map.getStyle();
    if (!style2?.layers) return;
    for (const override of overrides) {
      const isPrefix = override.match.endsWith("*");
      const prefix = isPrefix ? override.match.slice(0, -1) : "";
      for (const layer of style2.layers) {
        const matched = isPrefix ? layer.id.startsWith(prefix) : layer.id === override.match;
        if (!matched) continue;
        if (override.paint) {
          for (const [prop, val] of Object.entries(override.paint)) {
            try {
              map.setPaintProperty(layer.id, prop, val);
            } catch {
            }
          }
        }
        if (override.layout) {
          for (const [prop, val] of Object.entries(override.layout)) {
            try {
              map.setLayoutProperty(layer.id, prop, val);
            } catch {
            }
          }
        }
      }
    }
  }
  var VINTAGE_PARCHMENT_OVERRIDES = [
    { match: "background", paint: { "background-color": "#F5E6C8" } },
    { match: "water", paint: { "fill-color": "#C4B08A" } },
    { match: "waterway*", paint: { "line-color": "#B0996E" } },
    { match: "landcover*", paint: { "fill-color": "#E8D8B8", "fill-opacity": 0.5 } },
    { match: "landuse*", paint: { "fill-color": "#E8D8B8", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#D8CCA8", "fill-opacity": 0.4 } },
    { match: "boundary*", paint: { "line-color": "#7A5C38", "line-width": 1.8, "line-opacity": 0.9 } },
    { match: "road*", paint: { "line-color": "#C0A878", "line-opacity": 0.7 } },
    { match: "building*", paint: { "fill-color": "#E0D0B4", "fill-opacity": 0.4 } }
  ];
  var MINIMAL_LIGHT_OVERRIDES = [
    { match: "background", paint: { "background-color": "#F8F8FA" } },
    { match: "water", paint: { "fill-color": "#C8D8EC" } },
    { match: "waterway*", paint: { "line-color": "#A8C0DA" } },
    { match: "landcover*", paint: { "fill-color": "#EEF2EE", "fill-opacity": 0.4 } },
    { match: "landuse*", paint: { "fill-color": "#F2F2F4", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#E0EAE0", "fill-opacity": 0.4 } },
    { match: "boundary*", paint: { "line-color": "#8890A0", "line-width": 1.4, "line-opacity": 0.8 } },
    { match: "road*", paint: { "line-color": "#C8CCD2", "line-opacity": 0.8 } },
    { match: "building*", paint: { "fill-color": "#E8E8EA", "fill-opacity": 0.4 } }
  ];
  var DARK_ELEGANT_OVERRIDES = [
    { match: "background", paint: { "background-color": "#1A1A2E" } },
    { match: "water", paint: { "fill-color": "#14142A" } },
    { match: "waterway*", paint: { "line-color": "#20203A" } },
    { match: "landcover*", paint: { "fill-color": "#252540", "fill-opacity": 0.3 } },
    { match: "landuse*", paint: { "fill-color": "#222238", "fill-opacity": 0.2 } },
    { match: "park*", paint: { "fill-color": "#202038", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#9999CC", "line-width": 1.2, "line-opacity": 0.7 } },
    { match: "road*", paint: { "line-color": "#3A3A5A", "line-opacity": 0.5 } },
    { match: "building*", paint: { "fill-color": "#2A2A44", "fill-opacity": 0.3 } }
  ];
  var BLUEPRINT_OVERRIDES = [
    { match: "background", paint: { "background-color": "#0F2942" } },
    { match: "water", paint: { "fill-color": "#081828" } },
    { match: "waterway*", paint: { "line-color": "#1A3E60" } },
    { match: "landcover*", paint: { "fill-color": "#163050", "fill-opacity": 0.4 } },
    { match: "landuse*", paint: { "fill-color": "#143050", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#123048", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#68A0D0", "line-width": 1.4, "line-opacity": 0.9 } },
    { match: "road*", paint: { "line-color": "#2E6090", "line-opacity": 0.6 } },
    { match: "building*", paint: { "fill-color": "#1A3A5C", "fill-opacity": 0.3 } }
  ];
  var WARM_EARTH_OVERRIDES = [
    { match: "background", paint: { "background-color": "#F0E8DE" } },
    { match: "water", paint: { "fill-color": "#C8BAA0" } },
    { match: "waterway*", paint: { "line-color": "#B8A888" } },
    { match: "landcover*", paint: { "fill-color": "#E4DCC8", "fill-opacity": 0.5 } },
    { match: "landuse*", paint: { "fill-color": "#E8DDCC", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#D4CCB8", "fill-opacity": 0.5 } },
    { match: "boundary*", paint: { "line-color": "#8A6E48", "line-width": 1.6, "line-opacity": 0.9 } },
    { match: "road*", paint: { "line-color": "#C8B498", "line-opacity": 0.7 } },
    { match: "building*", paint: { "fill-color": "#E0D6C8", "fill-opacity": 0.4 } }
  ];
  var MATTE_SLATE_OVERRIDES = [
    { match: "background", paint: { "background-color": "#1A1C22" } },
    { match: "water", paint: { "fill-color": "#0E1018" } },
    { match: "waterway*", paint: { "line-color": "#1E2030" } },
    { match: "landcover*", paint: { "fill-color": "#22242E", "fill-opacity": 0.4 } },
    { match: "landuse*", paint: { "fill-color": "#20222C", "fill-opacity": 0.3 } },
    { match: "park*", paint: { "fill-color": "#1E2028", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#6A6E7C", "line-width": 1.4, "line-opacity": 0.8 } },
    { match: "road*", paint: { "line-color": "#383C48", "line-opacity": 0.6 } },
    { match: "building*", paint: { "fill-color": "#24262E", "fill-opacity": 0.3 } }
  ];
  var HISTORICAL_OVERRIDES = [
    { match: "boundary*", paint: { "line-color": "#8B7355", "line-width": 1.6, "line-opacity": 0.9 } },
    { match: "water", paint: { "fill-color": "#B8CCD8" } },
    { match: "waterway*", paint: { "line-color": "#9AB0C0" } }
  ];
  var CLEAN_WHITE_OVERRIDES = [
    { match: "background", paint: { "background-color": "#FFFFFF" } },
    { match: "water", paint: { "fill-color": "#D6E6F5" } },
    { match: "waterway*", paint: { "line-color": "#B0D0F0" } },
    { match: "landcover*", paint: { "fill-color": "#F0F4F0", "fill-opacity": 0.3 } },
    { match: "landuse*", paint: { "fill-color": "#F8F8FA", "fill-opacity": 0.2 } },
    { match: "park*", paint: { "fill-color": "#E8F2E8", "fill-opacity": 0.3 } },
    { match: "boundary*", paint: { "line-color": "#A0AAB8", "line-width": 1.2, "line-opacity": 0.8 } },
    { match: "road*", paint: { "line-color": "#D8DCE4", "line-opacity": 0.7 } },
    { match: "building*", paint: { "fill-color": "#F0F0F4", "fill-opacity": 0.3 } }
  ];
  var DARK_CYBER_OVERRIDES = [
    { match: "boundary*", paint: { "line-color": "#4A8080", "line-width": 1.2, "line-opacity": 0.8 } },
    { match: "water", paint: { "fill-color": "#18202A" } },
    { match: "road*", paint: { "line-color": "#2A3540", "line-opacity": 0.6 } }
  ];
  var BRIGHT_URL = "https://tiles.openfreemap.org/styles/bright";
  var DARK_URL = "https://tiles.openfreemap.org/styles/dark";
  var MAP_STYLES = {
    /* ── 기존 MapLibre 테마 (변경 없음) ── */
    modern_clean: {
      url: BRIGHT_URL,
      description: "\uAE54\uB054\uD55C \uD604\uB300\uD48D \uC9C0\uB3C4",
      recommended: "\uD604\uB300 \uB3C4\uC2DC, \uC815\uBCF4 \uCF58\uD150\uCE20, \uB274\uC2A4"
    },
    historical: {
      url: BRIGHT_URL,
      cssFilter: "sepia(0.2) saturate(0.85) brightness(0.95)",
      layerOverrides: HISTORICAL_OVERRIDES,
      description: "\uC138\uD53C\uC544 \uBE48\uD2F0\uC9C0 \uC9C0\uB3C4 (\uD0C0\uC77C \uAE30\uBC18)",
      recommended: "\uC5ED\uC0AC \uCF58\uD150\uCE20 (\uB3C4\uB85C/\uC9C0\uD615 \uB514\uD14C\uC77C \uD544\uC694 \uC2DC)"
    },
    dark_cyber: {
      url: DARK_URL,
      layerOverrides: DARK_CYBER_OVERRIDES,
      description: "\uC5B4\uB450\uC6B4 \uC0AC\uC774\uBC84 \uD1A4 \uC9C0\uB3C4",
      recommended: "\uD14C\uD06C, \uC0AC\uC774\uBC84, \uBBF8\uB798"
    },
    /* ── 레이어 오버라이드 테마 ── */
    vintage_parchment: {
      url: BRIGHT_URL,
      layerOverrides: VINTAGE_PARCHMENT_OVERRIDES,
      description: "\uC591\uD53C\uC9C0/\uACE0\uC9C0\uB3C4 \uB290\uB08C, \uB530\uB73B\uD55C \uD1A4",
      recommended: "\uC5ED\uC0AC \uB2E4\uD050, \uACE0\uC804, \uD0D0\uD5D8"
    },
    minimal_light: {
      url: BRIGHT_URL,
      layerOverrides: MINIMAL_LIGHT_OVERRIDES,
      description: "\uBC1D\uACE0 \uAE54\uB054\uD55C \uBBF8\uB2C8\uBA40 \uC9C0\uB3C4",
      recommended: "\uAD50\uC721, \uC124\uBA85, \uC778\uD3EC\uADF8\uB798\uD53D"
    },
    dark_elegant: {
      url: DARK_URL,
      layerOverrides: DARK_ELEGANT_OVERRIDES,
      description: "\uC5B4\uB450\uC6B4 \uBC30\uACBD + \uC6B0\uC544\uD55C \uACE8\uB4DC \uB77C\uC778",
      recommended: "\uACE0\uAE09\uC2A4\uB7EC\uC6B4 \uB2E4\uD050, \uBC24 \uBD84\uC704\uAE30"
    },
    blueprint: {
      url: DARK_URL,
      layerOverrides: BLUEPRINT_OVERRIDES,
      description: "\uCCAD\uC0AC\uC9C4/\uC124\uACC4\uB3C4 \uB290\uB08C",
      recommended: "\uAD70\uC0AC, \uC804\uB7B5, \uAC74\uCD95"
    },
    warm_earth: {
      url: BRIGHT_URL,
      layerOverrides: WARM_EARTH_OVERRIDES,
      description: "\uB530\uB73B\uD55C \uB300\uC9C0\uC0C9 \uD1A4",
      recommended: "\uC790\uC5F0, \uC5EC\uD589, \uC9C0\uB9AC"
    },
    matte_slate: {
      url: DARK_URL,
      layerOverrides: MATTE_SLATE_OVERRIDES,
      description: "\uB274\uD2B8\uB7F4 \uB2E4\uD06C \u2014 \uB370\uC774\uD130 \uC2DC\uAC01\uD654 \uC911\uB9BD \uCE94\uBC84\uC2A4",
      recommended: "\uB274\uC2A4, \uC120\uAC70, \uC778\uD3EC\uADF8\uB798\uD53D, \uCF54\uB85C\uD50C\uB808\uC2A4"
    },
    clean_white: {
      url: BRIGHT_URL,
      layerOverrides: CLEAN_WHITE_OVERRIDES,
      description: "\uC21C\uBC31 \uAE54\uB054\uD55C \uD604\uB300\uD48D \uC9C0\uB3C4",
      recommended: "\uAE08\uC735, \uAD50\uC721, \uBE44\uC988\uB2C8\uC2A4, \uB77C\uC774\uD2B8 \uBAA8\uB4DC \uCF58\uD150\uCE20"
    }
  };
  function resolveMapStyle(styleOrUrl) {
    if (!styleOrUrl) return MAP_STYLES.modern_clean;
    if (styleOrUrl in MAP_STYLES) {
      return MAP_STYLES[styleOrUrl];
    }
    return {
      url: styleOrUrl,
      description: "\uCEE4\uC2A4\uD140 URL",
      recommended: ""
    };
  }

  // src/map/RemotionMap.tsx
  var import_jsx_runtime56 = __toESM(require_jsx_runtime());
  var MAP_CSS = `
.maplibregl-canvas { outline: none; }
.maplibregl-ctrl-bottom-left, .maplibregl-ctrl-bottom-right { display: none !important; }
`;
  var RemotionMap = ({
    mapStyle,
    cameraState,
    onMapReady,
    onFrameUpdate,
    hideBaseLabels = true,
    width = 1920,
    height = 1080,
    children
  }) => {
    const containerRef = (0, import_react103.useRef)(null);
    const mapRef = (0, import_react103.useRef)(null);
    const readyRef = (0, import_react103.useRef)(false);
    const [mapVisible, setMapVisible] = (0, import_react103.useState)(false);
    const [handle] = (0, import_react103.useState)(() => delayRender("Loading map tiles"));
    const latestCameraRef = (0, import_react103.useRef)(cameraState);
    latestCameraRef.current = cameraState;
    const styleConfig = resolveMapStyle(mapStyle);
    (0, import_react103.useEffect)(() => {
      if (!containerRef.current) return;
      const map = new import_maplibre_gl.default.Map({
        container: containerRef.current,
        style: styleConfig.url ?? "https://tiles.openfreemap.org/styles/bright",
        center: cameraState.center,
        zoom: cameraState.zoom,
        bearing: cameraState.bearing,
        pitch: cameraState.pitch,
        interactive: false,
        fadeDuration: 0,
        attributionControl: false,
        antialias: true,
        // preserveDrawingBuffer: WebGL 캡처용 — MapOptions 타입에 없지만 런타임 지원
        ...{ preserveDrawingBuffer: true }
      });
      map.on("styleimagemissing", ({ id }) => {
        if (!map.hasImage(id)) {
          map.addImage(id, { width: 1, height: 1, data: new Uint8Array(4) });
        }
      });
      map.on("load", () => {
        if (styleConfig.layerOverrides?.length) {
          applyLayerOverrides(map, styleConfig.layerOverrides);
        }
        if (hideBaseLabels) {
          const style2 = map.getStyle();
          if (style2?.layers) {
            for (const layer of style2.layers) {
              if (layer.type === "symbol") {
                map.setLayoutProperty(layer.id, "visibility", "none");
              }
            }
          }
        }
        readyRef.current = true;
        mapRef.current = map;
        const cam = latestCameraRef.current;
        map.jumpTo({
          center: cam.center,
          zoom: cam.zoom,
          bearing: cam.bearing,
          pitch: cam.pitch
        });
        setMapVisible(true);
        onMapReady?.(map);
        map.once("idle", () => {
          onFrameUpdate?.(map);
          continueRender(handle);
        });
      });
      return () => {
        map.remove();
        mapRef.current = null;
        readyRef.current = false;
      };
    }, []);
    (0, import_react103.useEffect)(() => {
      const map = mapRef.current;
      if (!map || !readyRef.current) return;
      const frameHandle = delayRender("Updating map frame");
      map.jumpTo({
        center: cameraState.center,
        zoom: cameraState.zoom,
        bearing: cameraState.bearing,
        pitch: cameraState.pitch
      });
      map.triggerRepaint();
      const onIdle = () => {
        onFrameUpdate?.(map);
        continueRender(frameHandle);
      };
      map.once("idle", onIdle);
      return () => {
        map.off("idle", onIdle);
        try {
          continueRender(frameHandle);
        } catch {
        }
      };
    }, [cameraState.center[0], cameraState.center[1], cameraState.zoom, cameraState.bearing, cameraState.pitch, onFrameUpdate, mapVisible]);
    return /* @__PURE__ */ (0, import_jsx_runtime56.jsxs)("div", { style: { position: "relative", width, height, overflow: "hidden" }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime56.jsx)("style", { children: MAP_CSS }),
      /* @__PURE__ */ (0, import_jsx_runtime56.jsx)(
        "div",
        {
          ref: containerRef,
          style: {
            width,
            height,
            filter: styleConfig.cssFilter || void 0,
            opacity: mapVisible ? 1 : 0
            // load 전 라벨 깜빡임 방지
          }
        }
      ),
      children && mapVisible && /* @__PURE__ */ (0, import_jsx_runtime56.jsx)(
        "div",
        {
          style: {
            position: "absolute",
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: "none"
          },
          children
        }
      )
    ] });
  };

  // src/map/MapBase.tsx
  var import_jsx_runtime57 = __toESM(require_jsx_runtime());
  var MapBase = ({
    mapStyle,
    cameraState,
    onMapReady,
    onFrameUpdate,
    width = 1920,
    height = 1080,
    children
  }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime57.jsx)(
      RemotionMap,
      {
        mapStyle,
        cameraState,
        onMapReady,
        onFrameUpdate,
        width,
        height,
        children
      }
    );
  };

  // src/map/PrerenderedMapBg.tsx
  var import_jsx_runtime58 = __toESM(require_jsx_runtime());
  var resolveAsset2 = (p) => p.startsWith("http") ? p : staticFile(p);
  var PrerenderedMapBg = ({
    imagePath,
    width = 1920,
    height = 1080,
    brightness = 1,
    children
  }) => {
    return /* @__PURE__ */ (0, import_jsx_runtime58.jsxs)("div", { style: { position: "relative", width, height, overflow: "hidden" }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime58.jsx)(
        Img,
        {
          src: resolveAsset2(imagePath),
          style: {
            width,
            height,
            objectFit: "cover",
            filter: brightness !== 1 ? `brightness(${brightness})` : void 0
          }
        }
      ),
      children && /* @__PURE__ */ (0, import_jsx_runtime58.jsx)(
        "div",
        {
          style: {
            position: "absolute",
            top: 0,
            left: 0,
            width,
            height,
            pointerEvents: "none"
          },
          children
        }
      )
    ] });
  };

  // src/map/MapOverlays.tsx
  var import_jsx_runtime59 = __toESM(require_jsx_runtime());
  function lngLatToPixel(lngLat, camera, width, height) {
    const scale = Math.pow(2, camera.zoom) * 512;
    const toMerc = (lng, lat) => {
      const x = (lng + 180) / 360 * scale;
      const latRad = lat * Math.PI / 180;
      const y = (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * scale;
      return { x, y };
    };
    const center = toMerc(camera.center[0], camera.center[1]);
    const point2 = toMerc(lngLat[0], lngLat[1]);
    return {
      x: width / 2 + (point2.x - center.x),
      y: height / 2 + (point2.y - center.y)
    };
  }
  var MarkerPin = ({ shape, size, color, borderWidth, borderColor }) => {
    const s = size;
    const half = s / 2;
    switch (shape) {
      case "drop_pin":
        return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)("svg", { width: s, height: s * 1.4, viewBox: `0 0 ${s} ${s * 1.4}`, children: [
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
            "path",
            {
              d: `M${half},${s * 1.35} C${half},${s * 1.35} ${s * 0.92},${s * 0.7} ${s * 0.92},${half}
                A${half * 0.84},${half * 0.84} 0 1,0 ${s * 0.08},${half}
                C${s * 0.08},${s * 0.7} ${half},${s * 1.35} ${half},${s * 1.35}Z`,
              fill: color,
              stroke: borderColor,
              strokeWidth: borderWidth
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("circle", { cx: half, cy: half, r: s * 0.18, fill: borderColor })
        ] });
      case "crosshair":
        return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)("svg", { width: s, height: s, viewBox: `0 0 ${s} ${s}`, children: [
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("line", { x1: half, y1: 2, x2: half, y2: s - 2, stroke: color, strokeWidth: 1.5 }),
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("line", { x1: 2, y1: half, x2: s - 2, y2: half, stroke: color, strokeWidth: 1.5 }),
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("circle", { cx: half, cy: half, r: s * 0.15, fill: color }),
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("circle", { cx: half, cy: half, r: s * 0.32, fill: "none", stroke: color, strokeWidth: 1.5 })
        ] });
      case "diamond":
        return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("svg", { width: s, height: s, viewBox: `0 0 ${s} ${s}`, children: /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
          "rect",
          {
            x: half * 0.3,
            y: half * 0.3,
            width: s * 0.7,
            height: s * 0.7,
            fill: color,
            stroke: borderWidth > 0 ? borderColor : "none",
            strokeWidth: borderWidth,
            transform: `rotate(45 ${half} ${half})`
          }
        ) });
      case "ring":
        return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)("svg", { width: s, height: s, viewBox: `0 0 ${s} ${s}`, children: [
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
            "circle",
            {
              cx: half,
              cy: half,
              r: half * 0.7,
              fill: "none",
              stroke: borderColor,
              strokeWidth: borderWidth + 1
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("circle", { cx: half, cy: half, r: s * 0.12, fill: borderColor })
        ] });
      case "circle":
      default:
        return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
          "div",
          {
            style: {
              width: s,
              height: s,
              borderRadius: "50%",
              backgroundColor: color,
              border: `${borderWidth}px solid ${borderColor}`
            }
          }
        );
    }
  };
  var MarkerOverlay = ({
    markers,
    camera,
    width,
    height
  }) => {
    const frame = useCurrentFrame();
    const theme = useMapTheme();
    const mt = theme.marker;
    const anim = theme.animation;
    const accentIdx = STYLE.accentIndex ?? 0;
    const accentColor = `var(--viz-color-${accentIdx})`;
    const positions = markers.map((m) => lngLatToPixel(m.coordinates, camera, width, height));
    const labelDirs = (() => {
      const LABEL_W = 100;
      const LABEL_H = 36;
      const MARKER_R = 22;
      const PAD = 4;
      const dirs = [];
      const placedRects = [];
      const makeRect = (px, py, dir) => {
        switch (dir) {
          case "bottom":
            return { x1: px - LABEL_W / 2, y1: py + MARKER_R, x2: px + LABEL_W / 2, y2: py + MARKER_R + LABEL_H };
          case "top":
            return { x1: px - LABEL_W / 2, y1: py - MARKER_R - LABEL_H, x2: px + LABEL_W / 2, y2: py - MARKER_R };
          case "right":
            return { x1: px + MARKER_R, y1: py - LABEL_H / 2, x2: px + MARKER_R + LABEL_W, y2: py + LABEL_H / 2 };
          case "left":
            return { x1: px - MARKER_R - LABEL_W, y1: py - LABEL_H / 2, x2: px - MARKER_R, y2: py + LABEL_H / 2 };
        }
      };
      const rectsOverlap = (a2, b2) => a2.x1 - PAD < b2.x2 && a2.x2 + PAD > b2.x1 && a2.y1 - PAD < b2.y2 && a2.y2 + PAD > b2.y1;
      for (let i = 0; i < markers.length; i++) {
        if (markers[i].labelPosition) {
          const dir = markers[i].labelPosition;
          dirs.push(dir);
          placedRects.push(makeRect(positions[i].x, positions[i].y, dir));
          continue;
        }
        const tryDirs = ["bottom", "top", "right", "left"];
        let bestDir = "bottom";
        for (const dir of tryDirs) {
          const rect = makeRect(positions[i].x, positions[i].y, dir);
          let hasCollision = false;
          for (let j = 0; j < markers.length; j++) {
            if (j === i) continue;
            if (positions[j].x > rect.x1 && positions[j].x < rect.x2 && positions[j].y > rect.y1 && positions[j].y < rect.y2) {
              hasCollision = true;
              break;
            }
          }
          if (!hasCollision) {
            for (const placed of placedRects) {
              if (rectsOverlap(rect, placed)) {
                hasCollision = true;
                break;
              }
            }
          }
          if (!hasCollision) {
            bestDir = dir;
            break;
          }
        }
        dirs.push(bestDir);
        placedRects.push(makeRect(positions[i].x, positions[i].y, bestDir));
      }
      return dirs;
    })();
    return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(import_jsx_runtime59.Fragment, { children: markers.map((marker, i) => {
      const pos = positions[i];
      const appearAt = marker.appearAtFrame ?? 0;
      const fadeIn = anim.markerFadeIn;
      const markerOpacity = interpolate(frame, [appearAt, appearAt + fadeIn], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp"
      });
      const labelOpacity = interpolate(frame, [appearAt + fadeIn, appearAt + fadeIn + 10], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp"
      });
      const markerSize = marker.style === "dot" ? mt.dotSize : mt.size;
      const dir = labelDirs[i];
      const labelOffset = (() => {
        const gap = 6;
        const half = markerSize / 2;
        switch (dir) {
          case "bottom":
            return { left: "50%", top: markerSize / 2 + gap, transform: "translateX(-50%)" };
          case "top":
            return { left: "50%", bottom: markerSize / 2 + gap, transform: "translateX(-50%)" };
          case "right":
            return { left: half + gap, top: "50%", transform: "translateY(-50%)" };
          case "left":
            return { right: half + gap, top: "50%", transform: "translateY(-50%)" };
        }
      })();
      return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)(
        "div",
        {
          style: {
            position: "absolute",
            left: pos.x,
            top: pos.y,
            transform: "translate(-50%, -50%)",
            opacity: markerOpacity,
            pointerEvents: "none",
            width: markerSize,
            height: markerSize
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("div", { style: {
              filter: mt.shadow ? `drop-shadow(${mt.shadow})` : void 0,
              width: markerSize,
              height: markerSize
            }, children: /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
              MarkerPin,
              {
                shape: mt.shape,
                size: markerSize,
                color: accentColor,
                borderWidth: mt.borderWidth,
                borderColor: mt.borderColor
              }
            ) }),
            marker.label && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
              "div",
              {
                style: {
                  position: "absolute",
                  ...labelOffset,
                  padding: "4px 12px",
                  backgroundColor: mt.labelBg,
                  borderRadius: mt.labelRadius,
                  fontSize: mt.labelFontSize,
                  fontWeight: mt.labelFontWeight,
                  color: mt.labelColor,
                  fontFamily: mt.labelFontFamily ?? "'Pretendard', sans-serif",
                  whiteSpace: "nowrap",
                  boxShadow: mt.labelShadow,
                  textShadow: "none",
                  opacity: labelOpacity
                },
                children: marker.label
              }
            )
          ]
        },
        i
      );
    }) });
  };
  var LabelOverlay = ({
    labels,
    camera,
    width,
    height
  }) => {
    const frame = useCurrentFrame();
    const theme = useMapTheme();
    const lt = theme.label;
    const badgeStyle = (labelStyle2) => {
      const base = {
        fontFamily: lt.fontFamily,
        fontSize: lt.fontSize,
        fontWeight: lt.fontWeight,
        color: lt.color,
        whiteSpace: "nowrap",
        pointerEvents: "none"
      };
      switch (labelStyle2) {
        case "card":
          return {
            ...base,
            backgroundColor: lt.badgeBg,
            borderRadius: lt.badgeRadius ?? 8,
            padding: lt.badgePadding ?? "4px 12px",
            boxShadow: lt.badgeShadow
          };
        case "pill":
          return {
            ...base,
            backgroundColor: lt.badgeBg,
            borderRadius: lt.badgeRadius ?? 16,
            padding: lt.badgePadding ?? "3px 14px",
            boxShadow: lt.badgeShadow,
            border: lt.badgeBorder
          };
        case "tag":
          return {
            ...base,
            backgroundColor: lt.badgeBg,
            borderRadius: lt.badgeRadius ?? 4,
            padding: lt.badgePadding ?? "3px 10px",
            boxShadow: lt.badgeShadow,
            border: lt.badgeBorder
          };
        case "underline":
          return {
            ...base,
            borderBottom: lt.badgeBorder ?? `2px solid ${lt.color}`,
            paddingBottom: 2
          };
        case "floating":
        default:
          return {
            ...base
          };
      }
    };
    return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(import_jsx_runtime59.Fragment, { children: labels.map((label3, i) => {
      const pos = lngLatToPixel(label3.coordinates, camera, width, height);
      const appearAt = label3.appearAtFrame ?? 0;
      const opacity = interpolate(frame, [appearAt, appearAt + lt.fadeInFrames], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp"
      });
      return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
        "div",
        {
          style: {
            position: "absolute",
            left: pos.x,
            top: pos.y,
            transform: "translate(-50%, -50%)",
            opacity,
            ...badgeStyle(lt.style),
            fontSize: label3.fontSize ?? lt.fontSize,
            color: label3.color ?? lt.color
          },
          children: label3.text
        },
        i
      );
    }) });
  };
  var MapTitleOverlay = ({ title, source }) => {
    const frame = useCurrentFrame();
    const theme = useMapTheme();
    const tt = theme.title;
    const anim = tt.animation;
    const titleOpacity = interpolate(frame, [anim.fadeInStart, anim.fadeInEnd], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    });
    const slideVal = interpolate(frame, [anim.fadeInStart, anim.fadeInEnd], [anim.slideDistance, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    });
    const slideTransform = (() => {
      switch (anim.slideDirection) {
        case "down":
          return `translateY(${slideVal}px)`;
        case "up":
          return `translateY(${-slideVal}px)`;
        case "left":
          return `translateX(${-slideVal}px)`;
        case "right":
          return `translateX(${slideVal}px)`;
      }
    })();
    if (!title && !source) return null;
    const sourceEl = source ? /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
      "div",
      {
        style: {
          position: "absolute",
          top: 10,
          right: 40,
          opacity: titleOpacity,
          fontSize: tt.source.fontSize,
          fontWeight: 400,
          color: tt.source.color,
          fontFamily: tt.source.fontFamily
        },
        children: `\uCD9C\uCC98 : ${source}`
      }
    ) : null;
    const cardStyle = {
      opacity: titleOpacity,
      transform: slideTransform,
      background: tt.background,
      borderRadius: tt.borderRadius,
      padding: tt.padding,
      fontSize: tt.fontSize,
      fontWeight: tt.fontWeight,
      color: tt.color,
      fontFamily: tt.fontFamily,
      boxShadow: tt.shadow,
      letterSpacing: tt.letterSpacing,
      border: tt.border,
      backdropFilter: tt.backdropFilter,
      WebkitBackdropFilter: tt.backdropFilter
    };
    const renderLayout = (layout) => {
      switch (layout) {
        /* ── 상단 중앙 카드 ── */
        case "top_center_card":
          return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)(
            "div",
            {
              style: {
                position: "absolute",
                top: 40,
                left: 0,
                right: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                pointerEvents: "none"
              },
              children: [
                title && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("div", { style: cardStyle, children: title }),
                sourceEl
              ]
            }
          );
        /* ── 하단 바 ── */
        case "bottom_bar":
          return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)(
            "div",
            {
              style: {
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                pointerEvents: "none"
              },
              children: [
                title && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("div", { style: { ...cardStyle, width: "100%", textAlign: "center" }, children: title }),
                sourceEl
              ]
            }
          );
        /* ── 글래스모피즘 (상단 중앙) ── */
        case "floating_glass":
          return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)(
            "div",
            {
              style: {
                position: "absolute",
                top: 40,
                left: 0,
                right: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                pointerEvents: "none"
              },
              children: [
                title && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("div", { style: cardStyle, children: title }),
                sourceEl
              ]
            }
          );
        /* ── 좌상단 배지 ── */
        case "corner_badge":
          return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)("div", { style: { position: "absolute", top: 32, left: 40, pointerEvents: "none" }, children: [
            title && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)("div", { style: cardStyle, children: title }),
            sourceEl
          ] });
        /* ── 좌측 배너 (네온 좌측 보더) ── */
        case "left_banner":
          return /* @__PURE__ */ (0, import_jsx_runtime59.jsxs)("div", { style: { position: "absolute", top: 40, left: 0, pointerEvents: "none" }, children: [
            title && /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(
              "div",
              {
                style: {
                  ...cardStyle,
                  borderLeft: `4px solid ${theme.route.defaultColor}`,
                  borderRadius: `0 ${tt.borderRadius}px ${tt.borderRadius}px 0`
                },
                children: title
              }
            ),
            sourceEl
          ] });
        default:
          return null;
      }
    };
    return /* @__PURE__ */ (0, import_jsx_runtime59.jsx)(import_jsx_runtime59.Fragment, { children: renderLayout(tt.layout) });
  };

  // src/map/LocationReveal.tsx
  var import_jsx_runtime60 = __toESM(require_jsx_runtime());
  var resolveAsset3 = (p) => p.startsWith("http") ? p : staticFile(p);
  var ZOOM_FRAMES = 15;
  var MARKER_STAGGER = 5;
  var ZOOM_EASING = Easing.bezier(0.8, 0, 0.2, 1);
  var LocationReveal = ({
    data,
    durationInFrames,
    fps
  }) => {
    const frame = useCurrentFrame();
    const kfs = data.camera?.keyframes ?? [];
    if (kfs.length === 0) return null;
    const start = kfs[0];
    const end = kfs[kfs.length - 1] ?? start;
    const t = interpolate(frame, [0, ZOOM_FRAMES], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ZOOM_EASING
    });
    const camera = start ? {
      center: [
        start.center[0] + (end.center[0] - start.center[0]) * t,
        start.center[1] + (end.center[1] - start.center[1]) * t
      ],
      zoom: start.zoom + (end.zoom - start.zoom) * t,
      bearing: (start.bearing ?? 0) + ((end.bearing ?? 0) - (start.bearing ?? 0)) * t,
      pitch: (start.pitch ?? 0) + ((end.pitch ?? 0) - (start.pitch ?? 0)) * t
    } : { center: [53, 32], zoom: 5, bearing: 0, pitch: 0 };
    const zoomDone = frame >= ZOOM_FRAMES;
    const renderOverlays = (cam) => /* @__PURE__ */ (0, import_jsx_runtime60.jsxs)(import_jsx_runtime60.Fragment, { children: [
      zoomDone && data.markers && /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
        MarkerOverlay,
        {
          markers: data.markers.map((m, i) => ({
            ...m,
            appearAtFrame: ZOOM_FRAMES + i * MARKER_STAGGER
          })),
          camera: cam,
          width: 1920,
          height: 1080
        }
      ),
      zoomDone && data.labels && /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
        LabelOverlay,
        {
          labels: data.labels,
          camera: cam,
          width: 1920,
          height: 1080
        }
      )
    ] });
    if (data.prerenderedBg) {
      const bg = data.prerenderedBg;
      const captureCam = {
        center: bg.cameraState.center,
        zoom: bg.cameraState.zoom,
        bearing: bg.cameraState.bearing,
        pitch: bg.cameraState.pitch
      };
      return /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(AbsoluteFill, { children: /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
        PrerenderedMapBg,
        {
          imagePath: bg.imagePath,
          captureCamera: captureCam,
          width: 1920,
          height: 1080,
          children: renderOverlays(captureCam)
        }
      ) });
    }
    if (data.prerenderedFramesDir) {
      const frameImagePath = `${data.prerenderedFramesDir}/frame_${String(frame).padStart(4, "0")}.png`;
      return /* @__PURE__ */ (0, import_jsx_runtime60.jsxs)(AbsoluteFill, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
          Img,
          {
            src: resolveAsset3(frameImagePath),
            style: {
              width: 1920,
              height: 1080,
              objectFit: "cover",
              filter: "brightness(1.6)"
            }
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
          "div",
          {
            style: {
              position: "absolute",
              top: 0,
              left: 0,
              width: 1920,
              height: 1080,
              pointerEvents: "none"
            },
            children: renderOverlays(camera)
          }
        )
      ] });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(AbsoluteFill, { children: /* @__PURE__ */ (0, import_jsx_runtime60.jsx)(
      MapBase,
      {
        mapStyle: data.mapStyle,
        cameraState: camera,
        width: 1920,
        height: 1080,
        children: renderOverlays(camera)
      }
    ) });
  };

  // src/map/RouteAnimation.tsx
  var import_react104 = __toESM(require_react());

  // node_modules/@turf/helpers/dist/esm/index.js
  var earthRadius = 63710088e-1;
  var factors = {
    centimeters: earthRadius * 100,
    centimetres: earthRadius * 100,
    degrees: 360 / (2 * Math.PI),
    feet: earthRadius * 3.28084,
    inches: earthRadius * 39.37,
    kilometers: earthRadius / 1e3,
    kilometres: earthRadius / 1e3,
    meters: earthRadius,
    metres: earthRadius,
    miles: earthRadius / 1609.344,
    millimeters: earthRadius * 1e3,
    millimetres: earthRadius * 1e3,
    nauticalmiles: earthRadius / 1852,
    radians: 1,
    yards: earthRadius * 1.0936
  };
  function feature(geom, properties, options = {}) {
    const feat = { type: "Feature" };
    if (options.id === 0 || options.id) {
      feat.id = options.id;
    }
    if (options.bbox) {
      feat.bbox = options.bbox;
    }
    feat.properties = properties || {};
    feat.geometry = geom;
    return feat;
  }
  function point(coordinates, properties, options = {}) {
    if (!coordinates) {
      throw new Error("coordinates is required");
    }
    if (!Array.isArray(coordinates)) {
      throw new Error("coordinates must be an Array");
    }
    if (coordinates.length < 2) {
      throw new Error("coordinates must be at least 2 numbers long");
    }
    if (!isNumber(coordinates[0]) || !isNumber(coordinates[1])) {
      throw new Error("coordinates must contain numbers");
    }
    const geom = {
      type: "Point",
      coordinates
    };
    return feature(geom, properties, options);
  }
  function lineString(coordinates, properties, options = {}) {
    if (coordinates.length < 2) {
      throw new Error("coordinates must be an array of two or more positions");
    }
    const geom = {
      type: "LineString",
      coordinates
    };
    return feature(geom, properties, options);
  }
  function radiansToLength(radians, units = "kilometers") {
    const factor = factors[units];
    if (!factor) {
      throw new Error(units + " units is invalid");
    }
    return radians * factor;
  }
  function lengthToRadians(distance2, units = "kilometers") {
    const factor = factors[units];
    if (!factor) {
      throw new Error(units + " units is invalid");
    }
    return distance2 / factor;
  }
  function radiansToDegrees(radians) {
    const normalisedRadians = radians % (2 * Math.PI);
    return normalisedRadians * 180 / Math.PI;
  }
  function degreesToRadians(degrees) {
    const normalisedDegrees = degrees % 360;
    return normalisedDegrees * Math.PI / 180;
  }
  function isNumber(num) {
    return !isNaN(num) && num !== null && !Array.isArray(num);
  }
  function isObject(input) {
    return input !== null && typeof input === "object" && !Array.isArray(input);
  }

  // node_modules/@turf/invariant/dist/esm/index.js
  function getCoord(coord) {
    if (!coord) {
      throw new Error("coord is required");
    }
    if (!Array.isArray(coord)) {
      if (coord.type === "Feature" && coord.geometry !== null && coord.geometry.type === "Point") {
        return [...coord.geometry.coordinates];
      }
      if (coord.type === "Point") {
        return [...coord.coordinates];
      }
    }
    if (Array.isArray(coord) && coord.length >= 2 && !Array.isArray(coord[0]) && !Array.isArray(coord[1])) {
      return [...coord];
    }
    throw new Error("coord must be GeoJSON Point or an Array of numbers");
  }

  // node_modules/@turf/bearing/dist/esm/index.js
  function bearing(start, end, options = {}) {
    if (options.final === true) {
      return calculateFinalBearing(start, end);
    }
    const coordinates1 = getCoord(start);
    const coordinates2 = getCoord(end);
    const lon1 = degreesToRadians(coordinates1[0]);
    const lon2 = degreesToRadians(coordinates2[0]);
    const lat1 = degreesToRadians(coordinates1[1]);
    const lat2 = degreesToRadians(coordinates2[1]);
    const a2 = Math.sin(lon2 - lon1) * Math.cos(lat2);
    const b2 = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(lon2 - lon1);
    return radiansToDegrees(Math.atan2(a2, b2));
  }
  function calculateFinalBearing(start, end) {
    let bear = bearing(end, start);
    bear = (bear + 180) % 360;
    return bear;
  }

  // node_modules/@turf/destination/dist/esm/index.js
  function destination(origin, distance2, bearing2, options = {}) {
    const coordinates1 = getCoord(origin);
    const longitude1 = degreesToRadians(coordinates1[0]);
    const latitude1 = degreesToRadians(coordinates1[1]);
    const bearingRad = degreesToRadians(bearing2);
    const radians = lengthToRadians(distance2, options.units);
    const latitude2 = Math.asin(
      Math.sin(latitude1) * Math.cos(radians) + Math.cos(latitude1) * Math.sin(radians) * Math.cos(bearingRad)
    );
    const longitude2 = longitude1 + Math.atan2(
      Math.sin(bearingRad) * Math.sin(radians) * Math.cos(latitude1),
      Math.cos(radians) - Math.sin(latitude1) * Math.sin(latitude2)
    );
    const lng = radiansToDegrees(longitude2);
    const lat = radiansToDegrees(latitude2);
    if (coordinates1[2] !== void 0) {
      return point([lng, lat, coordinates1[2]], options.properties);
    }
    return point([lng, lat], options.properties);
  }

  // node_modules/@turf/distance/dist/esm/index.js
  function distance(from, to, options = {}) {
    var coordinates1 = getCoord(from);
    var coordinates2 = getCoord(to);
    var dLat = degreesToRadians(coordinates2[1] - coordinates1[1]);
    var dLon = degreesToRadians(coordinates2[0] - coordinates1[0]);
    var lat1 = degreesToRadians(coordinates1[1]);
    var lat2 = degreesToRadians(coordinates2[1]);
    var a2 = Math.pow(Math.sin(dLat / 2), 2) + Math.pow(Math.sin(dLon / 2), 2) * Math.cos(lat1) * Math.cos(lat2);
    return radiansToLength(
      2 * Math.atan2(Math.sqrt(a2), Math.sqrt(1 - a2)),
      options.units
    );
  }

  // node_modules/@turf/meta/dist/esm/index.js
  function coordEach(geojson, callback, excludeWrapCoord) {
    if (geojson === null) return;
    var j, k, l, geometry, stopG, coords, geometryMaybeCollection, wrapShrink = 0, coordIndex = 0, isGeometryCollection, type = geojson.type, isFeatureCollection = type === "FeatureCollection", isFeature = type === "Feature", stop = isFeatureCollection ? geojson.features.length : 1;
    for (var featureIndex = 0; featureIndex < stop; featureIndex++) {
      geometryMaybeCollection = isFeatureCollection ? (
        // @ts-expect-error: Known type conflict
        geojson.features[featureIndex].geometry
      ) : isFeature ? (
        // @ts-expect-error: Known type conflict
        geojson.geometry
      ) : geojson;
      isGeometryCollection = geometryMaybeCollection ? geometryMaybeCollection.type === "GeometryCollection" : false;
      stopG = isGeometryCollection ? geometryMaybeCollection.geometries.length : 1;
      for (var geomIndex = 0; geomIndex < stopG; geomIndex++) {
        var multiFeatureIndex = 0;
        var geometryIndex = 0;
        geometry = isGeometryCollection ? geometryMaybeCollection.geometries[geomIndex] : geometryMaybeCollection;
        if (geometry === null) continue;
        coords = geometry.coordinates;
        var geomType = geometry.type;
        wrapShrink = excludeWrapCoord && (geomType === "Polygon" || geomType === "MultiPolygon") ? 1 : 0;
        switch (geomType) {
          case null:
            break;
          case "Point":
            if (
              // @ts-expect-error: Known type conflict
              callback(
                coords,
                coordIndex,
                featureIndex,
                multiFeatureIndex,
                geometryIndex
              ) === false
            )
              return false;
            coordIndex++;
            multiFeatureIndex++;
            break;
          case "LineString":
          case "MultiPoint":
            for (j = 0; j < coords.length; j++) {
              if (
                // @ts-expect-error: Known type conflict
                callback(
                  coords[j],
                  coordIndex,
                  featureIndex,
                  multiFeatureIndex,
                  geometryIndex
                ) === false
              )
                return false;
              coordIndex++;
              if (geomType === "MultiPoint") multiFeatureIndex++;
            }
            if (geomType === "LineString") multiFeatureIndex++;
            break;
          case "Polygon":
          case "MultiLineString":
            for (j = 0; j < coords.length; j++) {
              for (k = 0; k < coords[j].length - wrapShrink; k++) {
                if (
                  // @ts-expect-error: Known type conflict
                  callback(
                    coords[j][k],
                    coordIndex,
                    featureIndex,
                    multiFeatureIndex,
                    geometryIndex
                  ) === false
                )
                  return false;
                coordIndex++;
              }
              if (geomType === "MultiLineString") multiFeatureIndex++;
              if (geomType === "Polygon") geometryIndex++;
            }
            if (geomType === "Polygon") multiFeatureIndex++;
            break;
          case "MultiPolygon":
            for (j = 0; j < coords.length; j++) {
              geometryIndex = 0;
              for (k = 0; k < coords[j].length; k++) {
                for (l = 0; l < coords[j][k].length - wrapShrink; l++) {
                  if (
                    // @ts-expect-error: Known type conflict
                    callback(
                      coords[j][k][l],
                      coordIndex,
                      featureIndex,
                      multiFeatureIndex,
                      geometryIndex
                    ) === false
                  )
                    return false;
                  coordIndex++;
                }
                geometryIndex++;
              }
              multiFeatureIndex++;
            }
            break;
          case "GeometryCollection":
            for (j = 0; j < geometry.geometries.length; j++)
              if (
                // @ts-expect-error: Known type conflict
                coordEach(geometry.geometries[j], callback, excludeWrapCoord) === false
              )
                return false;
            break;
          default:
            throw new Error("Unknown Geometry Type");
        }
      }
    }
  }
  function geomEach(geojson, callback) {
    var i, j, g, geometry, stopG, geometryMaybeCollection, isGeometryCollection, featureProperties, featureBBox, featureId, featureIndex = 0, isFeatureCollection = geojson.type === "FeatureCollection", isFeature = geojson.type === "Feature", stop = isFeatureCollection ? geojson.features.length : 1;
    for (i = 0; i < stop; i++) {
      geometryMaybeCollection = isFeatureCollection ? (
        // @ts-expect-error: Known type conflict
        geojson.features[i].geometry
      ) : isFeature ? (
        // @ts-expect-error: Known type conflict
        geojson.geometry
      ) : geojson;
      featureProperties = isFeatureCollection ? (
        // @ts-expect-error: Known type conflict
        geojson.features[i].properties
      ) : isFeature ? (
        // @ts-expect-error: Known type conflict
        geojson.properties
      ) : {};
      featureBBox = isFeatureCollection ? (
        // @ts-expect-error: Known type conflict
        geojson.features[i].bbox
      ) : isFeature ? (
        // @ts-expect-error: Known type conflict
        geojson.bbox
      ) : void 0;
      featureId = isFeatureCollection ? (
        // @ts-expect-error: Known type conflict
        geojson.features[i].id
      ) : isFeature ? (
        // @ts-expect-error: Known type conflict
        geojson.id
      ) : void 0;
      isGeometryCollection = geometryMaybeCollection ? geometryMaybeCollection.type === "GeometryCollection" : false;
      stopG = isGeometryCollection ? geometryMaybeCollection.geometries.length : 1;
      for (g = 0; g < stopG; g++) {
        geometry = isGeometryCollection ? geometryMaybeCollection.geometries[g] : geometryMaybeCollection;
        if (geometry === null) {
          if (
            // @ts-expect-error: Known type conflict
            callback(
              // @ts-expect-error: Known type conflict
              null,
              featureIndex,
              featureProperties,
              featureBBox,
              featureId
            ) === false
          )
            return false;
          continue;
        }
        switch (geometry.type) {
          case "Point":
          case "LineString":
          case "MultiPoint":
          case "Polygon":
          case "MultiLineString":
          case "MultiPolygon": {
            if (
              // @ts-expect-error: Known type conflict
              callback(
                geometry,
                featureIndex,
                featureProperties,
                featureBBox,
                featureId
              ) === false
            )
              return false;
            break;
          }
          case "GeometryCollection": {
            for (j = 0; j < geometry.geometries.length; j++) {
              if (
                // @ts-expect-error: Known type conflict
                callback(
                  geometry.geometries[j],
                  featureIndex,
                  featureProperties,
                  featureBBox,
                  featureId
                ) === false
              )
                return false;
            }
            break;
          }
          default:
            throw new Error("Unknown Geometry Type");
        }
      }
      featureIndex++;
    }
  }
  function flattenEach(geojson, callback) {
    geomEach(geojson, function(geometry, featureIndex, properties, bbox, id) {
      var type = geometry === null ? null : geometry.type;
      switch (type) {
        case null:
        case "Point":
        case "LineString":
        case "Polygon":
          if (
            // @ts-expect-error: Known type conflict
            callback(
              feature(geometry, properties, { bbox, id }),
              featureIndex,
              0
            ) === false
          )
            return false;
          return;
      }
      var geomType;
      switch (type) {
        case "MultiPoint":
          geomType = "Point";
          break;
        case "MultiLineString":
          geomType = "LineString";
          break;
        case "MultiPolygon":
          geomType = "Polygon";
          break;
      }
      for (
        var multiFeatureIndex = 0;
        // @ts-expect-error: Known type conflict
        multiFeatureIndex < geometry.coordinates.length;
        multiFeatureIndex++
      ) {
        var coordinate = geometry.coordinates[multiFeatureIndex];
        var geom = {
          type: geomType,
          coordinates: coordinate
        };
        if (
          // @ts-expect-error: Known type conflict
          callback(feature(geom, properties), featureIndex, multiFeatureIndex) === false
        )
          return false;
      }
    });
  }
  function segmentEach(geojson, callback) {
    flattenEach(geojson, function(feature2, featureIndex, multiFeatureIndex) {
      var segmentIndex = 0;
      if (!feature2.geometry) return;
      var type = feature2.geometry.type;
      if (type === "Point" || type === "MultiPoint") return;
      var previousCoords;
      var previousFeatureIndex = 0;
      var previousMultiIndex = 0;
      var prevGeomIndex = 0;
      if (
        // @ts-expect-error: Known type conflict
        coordEach(
          feature2,
          function(currentCoord, coordIndex, featureIndexCoord, multiPartIndexCoord, geometryIndex) {
            if (
              // @ts-expect-error: Known type conflict
              previousCoords === void 0 || featureIndex > previousFeatureIndex || multiPartIndexCoord > previousMultiIndex || geometryIndex > prevGeomIndex
            ) {
              previousCoords = currentCoord;
              previousFeatureIndex = featureIndex;
              previousMultiIndex = multiPartIndexCoord;
              prevGeomIndex = geometryIndex;
              segmentIndex = 0;
              return;
            }
            var currentSegment = lineString(
              // @ts-expect-error: Known type conflict
              [previousCoords, currentCoord],
              feature2.properties
            );
            if (
              // @ts-expect-error: Known type conflict
              callback(
                // @ts-expect-error: Known type conflict
                currentSegment,
                featureIndex,
                multiFeatureIndex,
                geometryIndex,
                segmentIndex
              ) === false
            )
              return false;
            segmentIndex++;
            previousCoords = currentCoord;
          }
        ) === false
      )
        return false;
    });
  }
  function segmentReduce(geojson, callback, initialValue) {
    var previousValue = initialValue;
    var started = false;
    segmentEach(
      geojson,
      function(currentSegment, featureIndex, multiFeatureIndex, geometryIndex, segmentIndex) {
        if (started === false && initialValue === void 0)
          previousValue = currentSegment;
        else
          previousValue = callback(
            previousValue,
            // @ts-expect-error: Known type conflict
            currentSegment,
            featureIndex,
            multiFeatureIndex,
            geometryIndex,
            segmentIndex
          );
        started = true;
      }
    );
    return previousValue;
  }

  // node_modules/@turf/length/dist/esm/index.js
  function length(geojson, options = {}) {
    return segmentReduce(
      geojson,
      (previousValue, segment) => {
        const coords = segment.geometry.coordinates;
        return previousValue + distance(coords[0], coords[1], options);
      },
      0
    );
  }

  // node_modules/@turf/line-slice-along/dist/esm/index.js
  function lineSliceAlong(line, startDist, stopDist, options = {}) {
    if (!isObject(options)) throw new Error("options is invalid");
    const { units = "kilometers" } = options;
    var coords;
    var slice = [];
    if (line.type === "Feature") coords = line.geometry.coordinates;
    else if (line.type === "LineString") coords = line.coordinates;
    else throw new Error("input must be a LineString Feature or Geometry");
    const origCoordsLength = coords.length;
    let travelled = 0;
    let overshot, direction, interpolated;
    for (let i = 0; i < coords.length; i++) {
      if (startDist >= travelled && i === coords.length - 1) break;
      else if (travelled > startDist && slice.length === 0) {
        let overshot2 = startDist - travelled;
        if (!overshot2) {
          slice.push(coords[i]);
          return lineString(slice);
        }
        direction = bearing(coords[i], coords[i - 1]) - 180;
        interpolated = destination(coords[i], overshot2, direction, { units });
        slice.push(interpolated.geometry.coordinates);
      }
      if (travelled >= stopDist) {
        overshot = stopDist - travelled;
        if (!overshot) {
          slice.push(coords[i]);
          return lineString(slice);
        }
        direction = bearing(coords[i], coords[i - 1]) - 180;
        interpolated = destination(coords[i], overshot, direction, { units });
        slice.push(interpolated.geometry.coordinates);
        return lineString(slice);
      }
      if (travelled >= startDist) {
        slice.push(coords[i]);
      }
      if (i === coords.length - 1) {
        return lineString(slice);
      }
      travelled += distance(coords[i], coords[i + 1], { units });
    }
    if (travelled < startDist && coords.length === origCoordsLength)
      throw new Error("Start position is beyond line");
    var last = coords[coords.length - 1];
    return lineString([last, last]);
  }

  // src/utils/easingMap.ts
  var EASING_MAP = {
    linear: (t) => t,
    easeInQuad: Easing.in(Easing.quad),
    easeOutQuad: Easing.out(Easing.quad),
    easeInOutQuad: Easing.inOut(Easing.quad),
    easeInCubic: Easing.in(Easing.cubic),
    easeOutCubic: Easing.out(Easing.cubic),
    easeInOutCubic: Easing.inOut(Easing.cubic),
    easeInQuart: Easing.in(Easing.poly(4)),
    easeOutQuart: Easing.out(Easing.poly(4)),
    easeInOutQuart: Easing.inOut(Easing.poly(4)),
    easeOutBack: Easing.out(Easing.back(1.5)),
    easeOutElastic: Easing.out(Easing.elastic(1)),
    easeOutBounce: Easing.out(Easing.bounce),
    easeInExpo: Easing.in(Easing.exp),
    easeOutExpo: Easing.out(Easing.exp),
    easeInOutExpo: Easing.inOut(Easing.exp)
  };
  function resolveEasing(name) {
    if (!name || name === "linear") return (t) => t;
    return EASING_MAP[name] ?? ((t) => t);
  }

  // src/map/cameraInterpolation.ts
  var PAN_LEAD_RATIO = 0.88;
  function compressLastSegment(frames, ratio) {
    if (frames.length < 2) return frames;
    const result = [...frames];
    const lastIdx = result.length - 1;
    const secondLast = result[lastIdx - 1];
    const lastSpan = result[lastIdx] - secondLast;
    result[lastIdx] = secondLast + lastSpan * ratio;
    return result;
  }
  function interpolateCamera(frame, keyframes, easingName) {
    if (keyframes.length === 0) {
      return { center: [126.977, 37.566], zoom: 10, bearing: 0, pitch: 0 };
    }
    if (keyframes.length === 1) {
      const kf = keyframes[0];
      return {
        center: kf.center,
        zoom: kf.zoom,
        bearing: kf.bearing ?? 0,
        pitch: kf.pitch ?? 0
      };
    }
    const easingFn = resolveEasing(easingName);
    const frames = keyframes.map((kf) => kf.frame);
    const hasZoomChange = keyframes.some(
      (kf, i) => i > 0 && Math.abs(kf.zoom - keyframes[i - 1].zoom) > 0.5
    );
    const panFrames = hasZoomChange ? compressLastSegment(frames, PAN_LEAD_RATIO) : frames;
    const lng = interpolate(frame, panFrames, keyframes.map((kf) => kf.center[0]), {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn
    });
    const lat = interpolate(frame, panFrames, keyframes.map((kf) => kf.center[1]), {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn
    });
    const zoom = interpolate(frame, frames, keyframes.map((kf) => kf.zoom), {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: easingFn
    });
    const bearing2 = interpolate(
      frame,
      frames,
      keyframes.map((kf) => kf.bearing ?? 0),
      { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn }
    );
    const pitch = interpolate(
      frame,
      frames,
      keyframes.map((kf) => kf.pitch ?? 0),
      { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: easingFn }
    );
    return { center: [lng, lat], zoom, bearing: bearing2, pitch };
  }

  // src/map/AtmosphereOverlay.tsx
  var import_jsx_runtime61 = __toESM(require_jsx_runtime());
  var AtmosphereOverlay = ({
    width = 1920,
    height = 1080
  }) => {
    const theme = useMapTheme();
    const atm = theme.atmosphere;
    if (atm.vignette <= 0 && atm.grain <= 0 && atm.borderDecoration === "none") {
      return null;
    }
    return /* @__PURE__ */ (0, import_jsx_runtime61.jsxs)(
      "div",
      {
        style: {
          position: "absolute",
          top: 0,
          left: 0,
          width,
          height,
          pointerEvents: "none",
          zIndex: 5
        },
        children: [
          atm.vignette > 0 && /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
            "div",
            {
              style: {
                position: "absolute",
                inset: 0,
                background: `radial-gradient(ellipse at center, transparent 50%, ${atm.vignetteColor ?? "rgba(0,0,0,0.8)"} 100%)`,
                opacity: atm.vignette
              }
            }
          ),
          atm.grain > 0 && /* @__PURE__ */ (0, import_jsx_runtime61.jsxs)(import_jsx_runtime61.Fragment, { children: [
            /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("svg", { width: 0, height: 0, style: { position: "absolute" }, children: /* @__PURE__ */ (0, import_jsx_runtime61.jsxs)("filter", { id: "map-grain", children: [
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("feTurbulence", { type: "fractalNoise", baseFrequency: "0.65", numOctaves: "3", stitchTiles: "stitch" }),
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("feColorMatrix", { type: "saturate", values: "0" })
            ] }) }),
            /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
              "div",
              {
                style: {
                  position: "absolute",
                  inset: 0,
                  filter: "url(#map-grain)",
                  opacity: atm.grain,
                  mixBlendMode: "overlay"
                }
              }
            )
          ] }),
          atm.borderDecoration !== "none" && /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
            BorderDecoration,
            {
              type: atm.borderDecoration,
              color: atm.borderColor ?? "#888",
              lineWidth: atm.borderWidth ?? 1,
              width,
              height
            }
          )
        ]
      }
    );
  };
  var BorderDecoration = ({
    type,
    color,
    lineWidth,
    width,
    height
  }) => {
    const m = 24;
    const c2 = 40;
    switch (type) {
      case "thin_line":
        return /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
          "svg",
          {
            width,
            height,
            style: { position: "absolute", inset: 0 },
            children: /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
              "rect",
              {
                x: m,
                y: m,
                width: width - m * 2,
                height: height - m * 2,
                fill: "none",
                stroke: color,
                strokeWidth: lineWidth,
                strokeOpacity: 0.5
              }
            )
          }
        );
      case "corner_marks":
        return /* @__PURE__ */ (0, import_jsx_runtime61.jsxs)(
          "svg",
          {
            width,
            height,
            style: { position: "absolute", inset: 0 },
            children: [
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("path", { d: `M${m},${m + c2} L${m},${m} L${m + c2},${m}`, fill: "none", stroke: color, strokeWidth: lineWidth }),
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("path", { d: `M${width - m - c2},${m} L${width - m},${m} L${width - m},${m + c2}`, fill: "none", stroke: color, strokeWidth: lineWidth }),
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("path", { d: `M${m},${height - m - c2} L${m},${height - m} L${m + c2},${height - m}`, fill: "none", stroke: color, strokeWidth: lineWidth }),
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)("path", { d: `M${width - m - c2},${height - m} L${width - m},${height - m} L${width - m},${height - m - c2}`, fill: "none", stroke: color, strokeWidth: lineWidth })
            ]
          }
        );
      case "ornate":
        return /* @__PURE__ */ (0, import_jsx_runtime61.jsxs)(
          "svg",
          {
            width,
            height,
            style: { position: "absolute", inset: 0 },
            children: [
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
                "rect",
                {
                  x: m,
                  y: m,
                  width: width - m * 2,
                  height: height - m * 2,
                  fill: "none",
                  stroke: color,
                  strokeWidth: lineWidth,
                  strokeOpacity: 0.4
                }
              ),
              /* @__PURE__ */ (0, import_jsx_runtime61.jsx)(
                "rect",
                {
                  x: m + 6,
                  y: m + 6,
                  width: width - (m + 6) * 2,
                  height: height - (m + 6) * 2,
                  fill: "none",
                  stroke: color,
                  strokeWidth: lineWidth * 0.6,
                  strokeOpacity: 0.25
                }
              )
            ]
          }
        );
      default:
        return null;
    }
  };

  // src/map/RouteAnimation.tsx
  var import_jsx_runtime62 = __toESM(require_jsx_runtime());
  var ROUTE_SOURCE_ID = "route-source";
  var ROUTE_LAYER_ID = "route-layer";
  var RouteAnimation = ({
    data,
    durationInFrames,
    fps
  }) => {
    const frame = useCurrentFrame();
    const keyframes = data.camera?.keyframes ?? [];
    if (keyframes.length === 0) return null;
    const camera = interpolateCamera(
      frame,
      keyframes,
      data.camera?.easing
    );
    const route = data.route;
    const drawStart = 15;
    const drawDuration = route?.drawDurationFrames ?? Math.floor(durationInFrames * 0.6);
    const drawEnd = drawStart + drawDuration;
    const progress = interpolate(frame, [drawStart, drawEnd], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp"
    });
    const visibleCoords = (0, import_react104.useMemo)(() => {
      if (!route || route.coordinates.length < 2) return [];
      const fullLine = lineString(route.coordinates);
      const totalLength = length(fullLine, { units: "kilometers" });
      if (progress <= 0) return [route.coordinates[0]];
      if (progress >= 1) return route.coordinates;
      const sliced = lineSliceAlong(fullLine, 0, totalLength * progress, {
        units: "kilometers"
      });
      return sliced.geometry.coordinates;
    }, [route, progress]);
    const overlays = (cam) => /* @__PURE__ */ (0, import_jsx_runtime62.jsxs)(import_jsx_runtime62.Fragment, { children: [
      data.markers && /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(MarkerOverlay, { markers: data.markers, camera: cam, width: 1920, height: 1080 }),
      data.labels && /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(LabelOverlay, { labels: data.labels, camera: cam, width: 1920, height: 1080 })
    ] });
    if (data.prerenderedBg) {
      const bg = data.prerenderedBg;
      const captureCam = {
        center: bg.cameraState.center,
        zoom: bg.cameraState.zoom,
        bearing: bg.cameraState.bearing,
        pitch: bg.cameraState.pitch
      };
      const pixelCoords = visibleCoords.map(
        (coord) => lngLatToPixel(coord, captureCam, 1920, 1080)
      );
      const pathD = pixelCoords.length > 1 ? pixelCoords.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ") : "";
      return /* @__PURE__ */ (0, import_jsx_runtime62.jsxs)(AbsoluteFill, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime62.jsxs)(
          PrerenderedMapBg,
          {
            imagePath: bg.imagePath,
            captureCamera: captureCam,
            width: 1920,
            height: 1080,
            children: [
              pathD && /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(
                "svg",
                {
                  width: 1920,
                  height: 1080,
                  style: { position: "absolute", top: 0, left: 0, pointerEvents: "none" },
                  children: /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(
                    "path",
                    {
                      d: pathD,
                      fill: "none",
                      stroke: route?.color ?? "#FF6B6B",
                      strokeWidth: route?.width ?? 5,
                      strokeLinecap: "round",
                      strokeLinejoin: "round",
                      strokeOpacity: 0.9
                    }
                  )
                }
              ),
              overlays(captureCam)
            ]
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(AtmosphereOverlay, {}),
        /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
      ] });
    }
    if (!route || route.coordinates.length < 2) {
      return /* @__PURE__ */ (0, import_jsx_runtime62.jsxs)(AbsoluteFill, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(RemotionMap, { mapStyle: data.mapStyle, cameraState: camera, width: 1920, height: 1080, children: overlays(camera) }),
        /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
      ] });
    }
    const visibleGeoJSON = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: visibleCoords
          }
        }
      ]
    };
    const handleMapReady = (map) => {
      if (!map.getSource(ROUTE_SOURCE_ID)) {
        map.addSource(ROUTE_SOURCE_ID, {
          type: "geojson",
          data: visibleGeoJSON
        });
        map.addLayer({
          id: ROUTE_LAYER_ID,
          type: "line",
          source: ROUTE_SOURCE_ID,
          paint: {
            "line-color": route.color ?? "#FF6B6B",
            "line-width": route.width ?? 5,
            "line-opacity": 0.9
          },
          layout: {
            "line-cap": "round",
            "line-join": "round"
          }
        });
      }
    };
    const handleFrameUpdate = (map) => {
      const source = map.getSource(ROUTE_SOURCE_ID);
      if (source) {
        source.setData(visibleGeoJSON);
      }
    };
    return /* @__PURE__ */ (0, import_jsx_runtime62.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(
        RemotionMap,
        {
          mapStyle: data.mapStyle,
          cameraState: camera,
          onMapReady: handleMapReady,
          onFrameUpdate: handleFrameUpdate,
          width: 1920,
          height: 1080,
          children: overlays(camera)
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(AtmosphereOverlay, {}),
      /* @__PURE__ */ (0, import_jsx_runtime62.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
    ] });
  };

  // src/map/TerritoryOverlay.tsx
  var import_react105 = __toESM(require_react());
  var import_jsx_runtime63 = __toESM(require_jsx_runtime());
  var resolveAsset4 = (p) => p.startsWith("http") ? p : staticFile(p);
  var TerritoryOverlay = ({
    data,
    durationInFrames,
    fps
  }) => {
    const frame = useCurrentFrame();
    const keyframes = data.camera?.keyframes ?? [];
    if (keyframes.length === 0) return null;
    const camera = interpolateCamera(
      frame,
      keyframes,
      data.camera?.easing
    );
    const territories = data.territories ?? [];
    const overlays = (cam) => /* @__PURE__ */ (0, import_jsx_runtime63.jsxs)(import_jsx_runtime63.Fragment, { children: [
      data.markers && /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(MarkerOverlay, { markers: data.markers, camera: cam, width: 1920, height: 1080 }),
      data.labels && /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(LabelOverlay, { labels: data.labels, camera: cam, width: 1920, height: 1080 })
    ] });
    if (data.prerenderedBg) {
      const bg = data.prerenderedBg;
      const captureCam = {
        center: bg.cameraState.center,
        zoom: bg.cameraState.zoom,
        bearing: bg.cameraState.bearing,
        pitch: bg.cameraState.pitch
      };
      return /* @__PURE__ */ (0, import_jsx_runtime63.jsxs)(AbsoluteFill, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(
          PrerenderedMapBg,
          {
            imagePath: bg.imagePath,
            captureCamera: captureCam,
            width: 1920,
            height: 1080,
            children: overlays(captureCam)
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(AtmosphereOverlay, {}),
        /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
      ] });
    }
    const [loadedGeoJSON, setLoadedGeoJSON] = (0, import_react105.useState)({});
    const [loadHandle] = (0, import_react105.useState)(() => {
      const hasExternalFiles = territories.some((t) => t.geojsonPath && !t.geojsonInline);
      return hasExternalFiles ? delayRender("Loading GeoJSON files") : null;
    });
    import_react105.default.useEffect(() => {
      const loadFiles = async () => {
        const loaded = {};
        for (let i = 0; i < territories.length; i++) {
          const t = territories[i];
          if (t.geojsonPath && !t.geojsonInline) {
            try {
              const url = resolveAsset4(t.geojsonPath);
              const res = await fetch(url);
              loaded[i] = await res.json();
            } catch (err) {
              console.error(`GeoJSON load failed: ${t.geojsonPath}`, err);
            }
          }
        }
        setLoadedGeoJSON(loaded);
        if (loadHandle) continueRender(loadHandle);
      };
      loadFiles();
    }, []);
    const handleMapReady = (0, import_react105.useCallback)(
      (map) => {
        territories.forEach((territory, i) => {
          const sourceId = `territory-source-${i}`;
          const fillLayerId = `territory-fill-${i}`;
          const lineLayerId = `territory-line-${i}`;
          const geojson = territory.geojsonInline ?? loadedGeoJSON[i];
          if (!geojson) return;
          if (!map.getSource(sourceId)) {
            map.addSource(sourceId, {
              type: "geojson",
              data: geojson
            });
            map.addLayer({
              id: fillLayerId,
              type: "fill",
              source: sourceId,
              paint: {
                "fill-color": territory.fillColor,
                "fill-opacity": 0
              }
            });
            if (territory.strokeColor) {
              map.addLayer({
                id: lineLayerId,
                type: "line",
                source: sourceId,
                paint: {
                  "line-color": territory.strokeColor,
                  "line-width": 2,
                  "line-opacity": 0
                }
              });
            }
          }
        });
      },
      [loadedGeoJSON]
      // eslint-disable-line react-hooks/exhaustive-deps
    );
    const handleFrameUpdate = (0, import_react105.useCallback)(
      (map) => {
        territories.forEach((territory, i) => {
          const fillLayerId = `territory-fill-${i}`;
          const lineLayerId = `territory-line-${i}`;
          const appearAt = territory.appearAtFrame ?? 0;
          const fadeIn = territory.fadeInFrames ?? 20;
          const opacity = interpolate(
            frame,
            [appearAt, appearAt + fadeIn],
            [0, territory.fillOpacity],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          if (map.getLayer(fillLayerId)) {
            map.setPaintProperty(fillLayerId, "fill-opacity", opacity);
          }
          if (map.getLayer(lineLayerId)) {
            map.setPaintProperty(
              lineLayerId,
              "line-opacity",
              Math.min(opacity * 2, 1)
            );
          }
        });
      },
      [frame]
      // eslint-disable-line react-hooks/exhaustive-deps
    );
    return /* @__PURE__ */ (0, import_jsx_runtime63.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(
        RemotionMap,
        {
          mapStyle: data.mapStyle,
          cameraState: camera,
          onMapReady: handleMapReady,
          onFrameUpdate: handleFrameUpdate,
          width: 1920,
          height: 1080,
          children: overlays(camera)
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(AtmosphereOverlay, {}),
      /* @__PURE__ */ (0, import_jsx_runtime63.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
    ] });
  };

  // src/map/FlyThrough.tsx
  var import_jsx_runtime64 = __toESM(require_jsx_runtime());
  var FlyThrough = ({
    data,
    durationInFrames,
    fps
  }) => {
    const frame = useCurrentFrame();
    const keyframes = data.camera?.keyframes ?? [];
    if (keyframes.length === 0) return null;
    const camera = interpolateCamera(
      frame,
      keyframes,
      data.camera?.easing
    );
    if (data.prerenderedBg) {
      const bg = data.prerenderedBg;
      const captureCam = {
        center: bg.cameraState.center,
        zoom: bg.cameraState.zoom,
        bearing: bg.cameraState.bearing,
        pitch: bg.cameraState.pitch
      };
      return /* @__PURE__ */ (0, import_jsx_runtime64.jsxs)(AbsoluteFill, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime64.jsxs)(
          PrerenderedMapBg,
          {
            imagePath: bg.imagePath,
            captureCamera: captureCam,
            width: 1920,
            height: 1080,
            children: [
              data.markers && /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(MarkerOverlay, { markers: data.markers, camera: captureCam, width: 1920, height: 1080 }),
              data.labels && /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(LabelOverlay, { labels: data.labels, camera: captureCam, width: 1920, height: 1080 })
            ]
          }
        ),
        /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(AtmosphereOverlay, {}),
        /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
      ] });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime64.jsxs)(AbsoluteFill, { children: [
      /* @__PURE__ */ (0, import_jsx_runtime64.jsxs)(
        MapBase,
        {
          mapStyle: data.mapStyle,
          cameraState: camera,
          width: 1920,
          height: 1080,
          children: [
            data.markers && /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(MarkerOverlay, { markers: data.markers, camera, width: 1920, height: 1080 }),
            data.labels && /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(LabelOverlay, { labels: data.labels, camera, width: 1920, height: 1080 })
          ]
        }
      ),
      /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(AtmosphereOverlay, {}),
      /* @__PURE__ */ (0, import_jsx_runtime64.jsx)(MapTitleOverlay, { title: data.title, source: data.source })
    ] });
  };

  // src/map/MapSceneRenderer.tsx
  var import_jsx_runtime65 = __toESM(require_jsx_runtime());
  var resolveAsset5 = (p) => p.startsWith("http") ? p : staticFile(p);
  var useFonts = () => {
    const [handle] = (0, import_react106.useState)(() => delayRender("Loading map fonts"));
    (0, import_react106.useEffect)(() => {
      const loadAll = async () => {
        const promises = FONT_DEFS.map(async (f) => {
          const url = resolveAsset5(f.file);
          const descriptors = {
            weight: f.weight,
            style: "normal"
          };
          const face = new FontFace(f.family, `url('${url}')`, descriptors);
          const loaded = await face.load();
          document.fonts.add(loaded);
        });
        await Promise.all(promises);
        continueRender(handle);
      };
      loadAll().catch((err) => {
        console.error("Font loading failed:", err);
        continueRender(handle);
      });
    }, [handle]);
  };
  var MapSceneRenderer = ({
    data,
    durationInFrames,
    fps
  }) => {
    useFonts();
    const commonProps = { data, durationInFrames, fps };
    return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(AbsoluteFill, { style: { filter: "brightness(1.0)" }, children: /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(MapThemeProvider, { theme: data.mapStyle ?? "modern_clean", children: (() => {
      switch (data.mapType) {
        case "location_reveal":
          return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(LocationReveal, { ...commonProps });
        case "route_animation":
          return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(RouteAnimation, { ...commonProps });
        case "territory_overlay":
          return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(TerritoryOverlay, { ...commonProps });
        case "fly_through":
          return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(FlyThrough, { ...commonProps });
        default:
          return /* @__PURE__ */ (0, import_jsx_runtime65.jsx)(LocationReveal, { ...commonProps });
      }
    })() }) });
  };

  // src/editor/SingleScenePlayer.tsx
  var import_jsx_runtime66 = __toESM(require_jsx_runtime());
  var resolveUrl = (path) => {
    if (!path) return "";
    if (path.startsWith("http://") || path.startsWith("https://")) return path;
    return path;
  };
  var ImageBg = ({ src, opacity }) => /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(AbsoluteFill, { style: { zIndex: 0, overflow: "hidden" }, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(Img, { src: resolveUrl(src), style: { width: "100%", height: "100%", objectFit: "cover", opacity } }) });
  var SideLayout = ({ src, placement, opacity, children }) => {
    const isLeft = placement === "left";
    return /* @__PURE__ */ (0, import_jsx_runtime66.jsxs)(AbsoluteFill, { style: { display: "flex", flexDirection: isLeft ? "row" : "row-reverse" }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime66.jsx)("div", { style: {
        flex: "0 0 40%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        position: "relative"
      }, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(Img, { src: resolveUrl(src), style: {
        maxWidth: "100%",
        maxHeight: "80%",
        objectFit: "contain",
        opacity,
        borderRadius: 16,
        filter: "drop-shadow(0 4px 24px rgba(0,0,0,0.5))"
      } }) }),
      /* @__PURE__ */ (0, import_jsx_runtime66.jsx)("div", { style: { flex: 1, position: "relative" }, children })
    ] });
  };
  var CenterLayout = ({ src, opacity, children }) => /* @__PURE__ */ (0, import_jsx_runtime66.jsxs)(AbsoluteFill, { style: { display: "flex", flexDirection: "column" }, children: [
    /* @__PURE__ */ (0, import_jsx_runtime66.jsx)("div", { style: {
      flex: "0 0 45%",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "16px 40px",
      position: "relative"
    }, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(Img, { src: resolveUrl(src), style: {
      maxWidth: "70%",
      maxHeight: "100%",
      objectFit: "contain",
      opacity,
      borderRadius: 16,
      filter: "drop-shadow(0 8px 32px rgba(0,0,0,0.6))"
    } }) }),
    /* @__PURE__ */ (0, import_jsx_runtime66.jsx)("div", { style: { flex: 1, position: "relative" }, children })
  ] });
  var SingleScenePlayer = ({ scene, meta }) => {
    const themeName = meta?.videoTheme ?? "dark";
    const artStyle = meta?.artStyle;
    const C = (void 0)(themeName, artStyle);
    const fontFamily = `'${meta?.vizFont || "Pretendard"}', sans-serif`;
    const fps = meta?.fps || 30;
    const durationInFrames = scene.audioDurationSec ? Math.max(Math.ceil(scene.audioDurationSec * fps), 1) : 150;
    if (scene.mapScene) {
      return /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(void 0, { theme: themeName, artStyle, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(AbsoluteFill, { style: { backgroundColor: C.bg, fontFamily }, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(
        MapSceneRenderer,
        {
          data: scene.mapScene,
          durationInFrames,
          fps
        }
      ) }) });
    }
    const hasImage = !!(scene.imagePath || scene.vizBackgroundPath);
    const placement = scene.imageAsset?.placement ?? "background";
    const imgOpacity = scene.imageAsset?.opacity ?? 0.4;
    const imgSrc = scene.vizBackgroundPath || scene.imagePath;
    const creativeEl = /* @__PURE__ */ (0, import_jsx_runtime66.jsx)("div", { style: { width: "100%", height: "100%", position: "relative" }, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(
      CreativeScene,
      {
        data: scene.visualization,
        subtitles: scene.subtitles || [],
        fps,
        hasImageBackground: hasImage && (placement === "background" || placement === "fullscreen"),
        imageAssetPlacement: placement
      }
    ) });
    let content;
    if (hasImage && placement === "fullscreen") {
      content = /* @__PURE__ */ (0, import_jsx_runtime66.jsxs)(import_jsx_runtime66.Fragment, { children: [
        /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(ImageBg, { src: imgSrc, opacity: imgOpacity >= 0.8 ? imgOpacity : 0.9 }),
        creativeEl
      ] });
    } else if (hasImage && placement === "center") {
      content = /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(CenterLayout, { src: imgSrc, opacity: imgOpacity, children: creativeEl });
    } else if (hasImage && (placement === "left" || placement === "right")) {
      content = /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(SideLayout, { src: imgSrc, placement, opacity: imgOpacity, children: creativeEl });
    } else {
      content = /* @__PURE__ */ (0, import_jsx_runtime66.jsxs)(import_jsx_runtime66.Fragment, { children: [
        hasImage && /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(ImageBg, { src: imgSrc, opacity: imgOpacity }),
        creativeEl
      ] });
    }
    return /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(void 0, { theme: themeName, artStyle, children: /* @__PURE__ */ (0, import_jsx_runtime66.jsx)(AbsoluteFill, { style: { backgroundColor: C.bg, fontFamily }, children: content }) });
  };

  // src/editor/ItemsEditor.tsx
  var import_react107 = __toESM(require_react());
  var import_jsx_runtime67 = __toESM(require_jsx_runtime());
  var ItemsEditor = ({
    items,
    values,
    descriptions = [],
    unit = "",
    onChange,
    maxItems = 10,
    minItems = 0,
    accent = "#F59E0B"
  }) => {
    const [dragIdx, setDragIdx] = (0, import_react107.useState)(null);
    const [overIdx, setOverIdx] = (0, import_react107.useState)(null);
    const handleDragStart = (e, i) => {
      setDragIdx(i);
      e.dataTransfer.effectAllowed = "move";
    };
    const handleDragOver = (e, i) => {
      e.preventDefault();
      setOverIdx(i);
    };
    const handleDrop = (e, dropIdx) => {
      e.preventDefault();
      if (dragIdx === null || dragIdx === dropIdx) return;
      const newItems = [...items];
      const newVals = [...values];
      const newDescs = [...descriptions];
      const [movedItem] = newItems.splice(dragIdx, 1);
      newItems.splice(dropIdx, 0, movedItem);
      if (newVals.length > 0) {
        const [movedVal] = newVals.splice(dragIdx, 1);
        newVals.splice(dropIdx, 0, movedVal);
      }
      if (newDescs.length > 0) {
        const [movedDesc] = newDescs.splice(dragIdx, 1);
        newDescs.splice(dropIdx, 0, movedDesc);
      }
      onChange(newItems, newVals, newDescs.length > 0 ? newDescs : void 0);
      setDragIdx(null);
      setOverIdx(null);
    };
    const updateItem = (i, text) => {
      const newItems = [...items];
      newItems[i] = text;
      onChange(newItems, values, descriptions.length > 0 ? descriptions : void 0);
    };
    const updateValue = (i, val) => {
      const newVals = [...values];
      newVals[i] = parseFloat(val) || 0;
      onChange(items, newVals, descriptions.length > 0 ? descriptions : void 0);
    };
    const removeItem = (i) => {
      if (items.length <= minItems) return;
      const newItems = items.filter((_, idx) => idx !== i);
      const newVals = values.filter((_, idx) => idx !== i);
      const newDescs = descriptions.filter((_, idx) => idx !== i);
      onChange(newItems, newVals, newDescs.length > 0 ? newDescs : void 0);
    };
    const addItem = () => {
      if (items.length >= maxItems) return;
      onChange([...items, "\uC0C8 \uD56D\uBAA9"], [...values, 0], descriptions.length > 0 ? [...descriptions, ""] : void 0);
    };
    return /* @__PURE__ */ (0, import_jsx_runtime67.jsxs)("div", { style: { display: "flex", flexDirection: "column", gap: 4 }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime67.jsxs)("div", { style: { fontSize: 11, color: "#999", marginBottom: 2 }, children: [
        "Items (",
        items.length,
        maxItems < 10 ? `/${maxItems}` : "",
        ") \u2014 \uB4DC\uB798\uADF8\uB85C \uC21C\uC11C \uBCC0\uACBD"
      ] }),
      items.map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime67.jsxs)(
        "div",
        {
          draggable: true,
          onDragStart: (e) => handleDragStart(e, i),
          onDragOver: (e) => handleDragOver(e, i),
          onDrop: (e) => handleDrop(e, i),
          onDragEnd: () => {
            setDragIdx(null);
            setOverIdx(null);
          },
          style: {
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "4px 6px",
            background: overIdx === i ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.03)",
            borderRadius: 4,
            border: dragIdx === i ? `1px solid ${accent}` : "1px solid transparent",
            cursor: "grab",
            transition: "background 0.15s"
          },
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime67.jsx)("span", { style: { color: "#666", fontSize: 10, cursor: "grab", userSelect: "none" }, children: "\u283F" }),
            /* @__PURE__ */ (0, import_jsx_runtime67.jsx)("span", { style: { color: accent, fontSize: 11, fontWeight: 700, minWidth: 16 }, children: i + 1 }),
            /* @__PURE__ */ (0, import_jsx_runtime67.jsx)(
              "input",
              {
                type: "text",
                value: item,
                onChange: (e) => updateItem(i, e.target.value),
                style: {
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  borderBottom: "1px solid rgba(255,255,255,0.1)",
                  color: "#E4E4E7",
                  fontSize: 12,
                  padding: "2px 4px",
                  outline: "none"
                }
              }
            ),
            values.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime67.jsx)(
              "input",
              {
                type: "text",
                value: values[i] ?? "",
                onChange: (e) => updateValue(i, e.target.value),
                style: {
                  width: 50,
                  background: "transparent",
                  border: "none",
                  borderBottom: "1px solid rgba(255,255,255,0.1)",
                  color: accent,
                  fontSize: 12,
                  fontWeight: 700,
                  textAlign: "right",
                  padding: "2px 4px",
                  outline: "none"
                }
              }
            ),
            items.length > minItems && /* @__PURE__ */ (0, import_jsx_runtime67.jsx)(
              "button",
              {
                onClick: () => removeItem(i),
                style: {
                  background: "transparent",
                  border: "none",
                  color: "#666",
                  cursor: "pointer",
                  fontSize: 14,
                  padding: "0 2px",
                  lineHeight: 1
                },
                children: "\xD7"
              }
            )
          ]
        },
        i
      )),
      items.length < maxItems && /* @__PURE__ */ (0, import_jsx_runtime67.jsx)(
        "button",
        {
          onClick: addItem,
          style: {
            background: "transparent",
            border: "1px dashed rgba(255,255,255,0.15)",
            borderRadius: 4,
            color: "#999",
            cursor: "pointer",
            fontSize: 11,
            padding: "4px 8px",
            textAlign: "center"
          },
          children: "+ \uD56D\uBAA9 \uCD94\uAC00"
        }
      )
    ] });
  };

  // src/editor/ImageSelector.tsx
  var import_react108 = __toESM(require_react());
  var import_jsx_runtime68 = __toESM(require_jsx_runtime());
  var TYPE_LABELS = {
    search: "\uAC80\uC0C9",
    generated: "\uC0DD\uC131",
    viz_bg: "\uBC30\uACBD",
    final: "\uCD5C\uC885"
  };
  var ImageSelector = ({
    slug,
    sceneNum,
    currentUrl,
    accent,
    onSelect,
    forceExpanded
  }) => {
    const [candidates, setCandidates] = (0, import_react108.useState)([]);
    const [loading, setLoading] = (0, import_react108.useState)(true);
    const [expanded, setExpanded] = (0, import_react108.useState)(false);
    const [saving, setSaving] = (0, import_react108.useState)(false);
    (0, import_react108.useEffect)(() => {
      if (forceExpanded) setExpanded(true);
    }, [forceExpanded]);
    (0, import_react108.useEffect)(() => {
      setLoading(true);
      fetch(`/api/p/${slug}/editor/scenes/${sceneNum}/images`).then((r) => r.json()).then((data) => {
        setCandidates(data.candidates || []);
        setLoading(false);
      }).catch(() => setLoading(false));
    }, [slug, sceneNum]);
    if (loading) {
      return /* @__PURE__ */ (0, import_jsx_runtime68.jsx)("div", { style: { fontSize: 11, color: "#71717A" }, children: "\uC774\uBBF8\uC9C0 \uB85C\uB529..." });
    }
    if (candidates.length === 0) {
      return /* @__PURE__ */ (0, import_jsx_runtime68.jsx)("div", { style: { fontSize: 11, color: "#71717A" }, children: "\uC774\uBBF8\uC9C0 \uD6C4\uBCF4 \uC5C6\uC74C" });
    }
    const handleSelect = async (url) => {
      onSelect(url);
      setSaving(true);
      try {
        await fetch(`/api/p/${slug}/editor/scenes/${sceneNum}/select-image`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ image_url: url })
        });
      } catch {
      } finally {
        setSaving(false);
      }
    };
    const currentMatch = candidates.find((c2) => c2.url === currentUrl);
    return /* @__PURE__ */ (0, import_jsx_runtime68.jsxs)("div", { children: [
      /* @__PURE__ */ (0, import_jsx_runtime68.jsxs)(
        "label",
        {
          style: {
            fontSize: 11,
            color: "#71717A",
            marginBottom: 3,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            cursor: "pointer"
          },
          onClick: () => setExpanded(!expanded),
          children: [
            /* @__PURE__ */ (0, import_jsx_runtime68.jsxs)("span", { children: [
              "\uC774\uBBF8\uC9C0 (",
              candidates.length,
              "\uAC1C)",
              saving && /* @__PURE__ */ (0, import_jsx_runtime68.jsx)("span", { style: { color: accent, marginLeft: 4 }, children: "\uC800\uC7A5\uC911..." })
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime68.jsx)("span", { style: { fontSize: 10 }, children: expanded ? "\u25B2" : "\u25BC" })
          ]
        }
      ),
      currentUrl && !expanded && /* @__PURE__ */ (0, import_jsx_runtime68.jsx)(
        "div",
        {
          onClick: () => setExpanded(true),
          style: {
            width: "100%",
            height: 48,
            borderRadius: 4,
            overflow: "hidden",
            cursor: "pointer",
            border: `1px solid rgba(255,255,255,0.1)`
          },
          children: /* @__PURE__ */ (0, import_jsx_runtime68.jsx)(
            "img",
            {
              src: currentUrl,
              style: {
                width: "100%",
                height: "100%",
                objectFit: "cover"
              }
            }
          )
        }
      ),
      expanded && /* @__PURE__ */ (0, import_jsx_runtime68.jsx)(
        "div",
        {
          style: {
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 4,
            maxHeight: 200,
            overflowY: "auto"
          },
          children: candidates.map((c2) => {
            const isSelected = c2.url === currentUrl;
            return /* @__PURE__ */ (0, import_jsx_runtime68.jsxs)(
              "div",
              {
                onClick: () => handleSelect(c2.url),
                style: {
                  position: "relative",
                  aspectRatio: "16/9",
                  borderRadius: 4,
                  overflow: "hidden",
                  cursor: "pointer",
                  border: isSelected ? `2px solid ${accent}` : "2px solid transparent",
                  opacity: isSelected ? 1 : 0.7,
                  transition: "all 0.15s"
                },
                title: `${c2.file_name} (${TYPE_LABELS[c2.type] || c2.type})`,
                children: [
                  /* @__PURE__ */ (0, import_jsx_runtime68.jsx)(
                    "img",
                    {
                      src: c2.url,
                      style: {
                        width: "100%",
                        height: "100%",
                        objectFit: "cover"
                      }
                    }
                  ),
                  /* @__PURE__ */ (0, import_jsx_runtime68.jsxs)(
                    "div",
                    {
                      style: {
                        position: "absolute",
                        bottom: 0,
                        left: 0,
                        right: 0,
                        padding: "1px 3px",
                        background: "rgba(0,0,0,0.7)",
                        fontSize: 9,
                        color: isSelected ? accent : "#aaa",
                        textAlign: "center"
                      },
                      children: [
                        TYPE_LABELS[c2.type] || c2.type,
                        isSelected && " \u2713"
                      ]
                    }
                  )
                ]
              },
              c2.id
            );
          })
        }
      )
    ] });
  };

  // src/editor/SceneEditorPanel.tsx
  var import_jsx_runtime69 = __toESM(require_jsx_runtime());
  var LAYOUT_OPTIONS = [
    "headline_only",
    "items_grid",
    "items_list",
    "person_card",
    "counter",
    "quote",
    "split",
    "bar",
    "logo_grid",
    "pie",
    "line",
    "flow",
    "timeline",
    "metric_spotlight",
    "metric_wall",
    "rank_list",
    "comparison_table",
    "before_after",
    "icon_stat",
    "stacked_progress",
    "card_carousel",
    "hero_with_context",
    "quote_portrait",
    "annotated_chart"
  ];
  var MOOD_OPTIONS = [
    "dramatic",
    "contemplative",
    "urgent",
    "triumphant",
    "somber",
    "informative",
    "suspense"
  ];
  var REVEAL_OPTIONS = [
    "fade_in",
    "stagger",
    "stagger_then_flash",
    "cascade",
    "count_up",
    "typewriter",
    "spotlight",
    "split_reveal",
    "zoom_in",
    "build_up",
    "dramatic_pause",
    "parallel"
  ];
  var EMPHASIS_OPTIONS = [
    "number",
    "keyword",
    "count",
    "contrast",
    "sequence",
    "person",
    "quote",
    "none"
  ];
  var PLACEMENT_OPTIONS = [
    "background",
    "fullscreen",
    "center",
    "left",
    "right",
    "inline"
  ];
  var PANEL_BG = "#18181B";
  var FORM_BG = "#1E1E22";
  var INPUT_BG = "rgba(255,255,255,0.05)";
  var BORDER = "rgba(255,255,255,0.1)";
  var TEXT = "#E4E4E7";
  var MUTED = "#71717A";
  var ACCENT = "#F59E0B";
  var labelStyle = {
    fontSize: 11,
    color: MUTED,
    marginBottom: 3,
    display: "block"
  };
  var selectStyle = {
    width: "100%",
    background: INPUT_BG,
    border: `1px solid ${BORDER}`,
    borderRadius: 4,
    color: TEXT,
    fontSize: 12,
    padding: "5px 8px",
    outline: "none",
    cursor: "pointer"
  };
  var inputStyle = {
    width: "100%",
    background: INPUT_BG,
    border: `1px solid ${BORDER}`,
    borderRadius: 4,
    color: TEXT,
    fontSize: 12,
    padding: "5px 8px",
    outline: "none",
    boxSizing: "border-box"
  };
  var SceneEditorPanel = ({ scene: initialScene, meta, slug, onSaved }) => {
    const [scene, setScene] = (0, import_react109.useState)(() => structuredClone(initialScene));
    const [saving, setSaving] = (0, import_react109.useState)(false);
    const [status, setStatus] = (0, import_react109.useState)("");
    const playerRef = (0, import_react109.useRef)(null);
    const [showImagePicker, setShowImagePicker] = (0, import_react109.useState)(false);
    const viz = scene.visualization || {};
    const creative = viz.creative || {};
    const fps = meta?.fps || 30;
    const canvasW = meta?.resolution?.width || 1920;
    const canvasH = meta?.resolution?.height || 1080;
    const rawDuration = scene.audioDurationSec ? Math.ceil(scene.audioDurationSec * fps) : scene.durationFrames || fps * 5;
    const durationInFrames = Math.max(1, rawDuration);
    const updateViz = (0, import_react109.useCallback)((patch) => {
      setScene((prev) => ({
        ...prev,
        visualization: { ...prev.visualization || {}, ...patch }
      }));
    }, []);
    const updateCreative = (0, import_react109.useCallback)((patch) => {
      setScene((prev) => {
        const oldViz = prev.visualization || {};
        const oldCreative = oldViz.creative || {};
        return {
          ...prev,
          visualization: { ...oldViz, creative: { ...oldCreative, ...patch } }
        };
      });
    }, []);
    const updateImageAsset = (0, import_react109.useCallback)((patch) => {
      setScene((prev) => ({
        ...prev,
        imageAsset: { ...prev.imageAsset || { placement: "background", opacity: 0.4 }, ...patch }
      }));
    }, []);
    const handleSave = async () => {
      setSaving(true);
      setStatus("");
      try {
        const resp = await fetch(`/api/p/${slug}/editor/scenes/${scene.sceneNumber}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scene_data: scene, mode: "save" })
        });
        const result = await resp.json();
        if (result.ok) {
          setStatus("\uC800\uC7A5 \uC644\uB8CC");
          fetch(`/api/p/${slug}/rebuild-manifest`, { method: "POST" }).catch(() => {
          });
          onSaved?.();
        } else {
          setStatus(`\uC624\uB958: ${result.error || "\uC800\uC7A5 \uC2E4\uD328"}`);
        }
      } catch (e) {
        setStatus(`\uC624\uB958: ${e.message}`);
      } finally {
        setSaving(false);
      }
    };
    return /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { display: "flex", gap: 0, height: "100%", background: PANEL_BG, color: TEXT, fontFamily: "'Inter', sans-serif" }, children: [
      /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { flex: "1 1 55%", display: "flex", flexDirection: "column", padding: 12, minWidth: 0 }, children: [
        /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }, children: /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { fontSize: 13, fontWeight: 600, color: ACCENT }, children: [
          "Scene ",
          scene.sceneNumber,
          scene.title && /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("span", { style: { color: MUTED, fontWeight: 400, marginLeft: 8, fontSize: 12 }, children: scene.title })
        ] }) }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("div", { style: {
          flex: 1,
          borderRadius: 8,
          overflow: "hidden",
          background: "#000",
          position: "relative",
          aspectRatio: `${canvasW}/${canvasH}`,
          maxHeight: "70vh"
        }, children: /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
          Player,
          {
            ref: playerRef,
            component: SingleScenePlayer,
            inputProps: { scene, meta },
            durationInFrames,
            compositionWidth: canvasW,
            compositionHeight: canvasH,
            fps,
            style: { width: "100%", height: "100%" },
            controls: true,
            loop: true,
            autoPlay: true,
            initialFrame: Math.min(Math.floor(durationInFrames * 0.4), durationInFrames - 1),
            acknowledgeRemotionLicense: true
          }
        ) }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("div", { style: { fontSize: 10, color: MUTED, marginTop: 6, textAlign: "center" }, children: "\uC6B0\uCE21 \uD3FC\uC5D0\uC11C \uC18D\uC131\uC744 \uBCC0\uACBD\uD558\uBA74 \uC2E4\uC2DC\uAC04 \uBC18\uC601\uB429\uB2C8\uB2E4" })
      ] }),
      /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: {
        flex: "0 0 320px",
        background: FORM_BG,
        borderLeft: `1px solid ${BORDER}`,
        overflowY: "auto",
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 14
      }, children: [
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Layout" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)(
            "select",
            {
              style: selectStyle,
              value: creative.layout || "",
              onChange: (e) => updateCreative({ layout: e.target.value }),
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "", children: "\uC790\uB3D9 (\uB370\uC774\uD130 \uAE30\uBC18)" }),
                LAYOUT_OPTIONS.map((l) => /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: l, children: l }, l))
              ]
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Headline" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "textarea",
            {
              style: { ...inputStyle, minHeight: 56, resize: "vertical", lineHeight: 1.4 },
              value: creative.headline || "",
              onChange: (e) => updateCreative({ headline: e.target.value }),
              placeholder: "\uD5E4\uB4DC\uB77C\uC778 \uC785\uB825... ({{\uAC15\uC870}} \uAC00\uB2A5)\nEnter\uB85C \uC904\uBC14\uAFC8",
              rows: 2
            }
          ),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { fontSize: 9, color: MUTED, marginTop: 2 }, children: [
            "{{\uD14D\uC2A4\uD2B8}}",
            " \uAC15\uC870 \uC0C9\uC0C1 \xA0|\xA0 Enter \uC904\uBC14\uAFC8"
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Title" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "input",
            {
              type: "text",
              style: inputStyle,
              value: viz.title || "",
              onChange: (e) => updateViz({ title: e.target.value }),
              placeholder: "\uC2DC\uAC01\uD654 \uD0C0\uC774\uD2C0..."
            }
          )
        ] }),
        !["headline_only", "counter", "quote", "icon_stat", "quote_portrait"].includes(creative.layout || "") && /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("label", { style: labelStyle, children: [
            "Items (",
            (viz.items || []).length,
            ")"
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            ItemsEditor,
            {
              items: viz.items || [],
              values: viz.values || [],
              descriptions: viz.descriptions,
              unit: viz.unit,
              accent: ACCENT,
              onChange: (items, values, descriptions) => updateViz({ items, values, descriptions })
            }
          )
        ] }),
        (viz.items || []).length > 0 && /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("label", { style: labelStyle, children: [
            "Item Icons",
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("span", { style: { fontSize: 9, color: MUTED, marginLeft: 6 }, children: "\uBAA8\uB450 \uC9C0\uC815\uD558\uAC70\uB098 \uBAA8\uB450 \uBE44\uC6CC\uC57C \uD1B5\uC77C\uB428" })
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("div", { style: { display: "flex", flexWrap: "wrap", gap: 4 }, children: (viz.items || []).map((item, i) => /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)(
            "select",
            {
              style: { ...selectStyle, width: "auto", minWidth: 80, fontSize: 10, padding: "3px 4px" },
              value: (viz.itemIcons || [])[i] || "",
              onChange: (e) => {
                const icons = [...viz.itemIcons || []];
                while (icons.length < (viz.items || []).length) icons.push("");
                icons[i] = e.target.value;
                updateViz({ itemIcons: icons });
              },
              children: [
                /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "", children: "\uC5C6\uC74C" }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uC804\uC7C1/\uAD70\uC0AC", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Swords", children: "Swords" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Crosshair", children: "Crosshair" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Shield", children: "Shield" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Bomb", children: "Bomb" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Flag", children: "Flag" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uBE44\uC988\uB2C8\uC2A4", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "DollarSign", children: "DollarSign" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "BarChart3", children: "BarChart3" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Target", children: "Target" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "TrendingUp", children: "TrendingUp" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uC0AC\uB78C/\uC870\uC9C1", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Users", children: "Users" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "User", children: "User" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Building", children: "Building" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Crown", children: "Crown" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Landmark", children: "Landmark" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uAE30\uC220", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Brain", children: "Brain" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Cpu", children: "Cpu" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Globe", children: "Globe" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Network", children: "Network" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uC2DC\uAC04", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Clock", children: "Clock" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Calendar", children: "Calendar" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "History", children: "History" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uAC10\uC815/\uC5D0\uB108\uC9C0", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Zap", children: "Zap" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Flame", children: "Flame" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Heart", children: "Heart" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Rocket", children: "Rocket" })
                ] }),
                /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("optgroup", { label: "\uAE30\uD0C0", children: [
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Star", children: "Star" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Award", children: "Award" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "CheckCircle", children: "CheckCircle" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "AlertTriangle", children: "AlertTriangle" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Lightbulb", children: "Lightbulb" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "BookOpen", children: "BookOpen" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Map", children: "Map" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "MapPin", children: "MapPin" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Plane", children: "Plane" }),
                  /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: "Ship", children: "Ship" })
                ] })
              ]
            },
            i
          )) })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Mood" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "select",
            {
              style: selectStyle,
              value: creative.mood || "informative",
              onChange: (e) => updateCreative({ mood: e.target.value }),
              children: MOOD_OPTIONS.map((m) => /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: m, children: m }, m))
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Reveal" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "select",
            {
              style: selectStyle,
              value: creative.reveal || "fade_in",
              onChange: (e) => updateCreative({ reveal: e.target.value }),
              children: REVEAL_OPTIONS.map((r) => /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: r, children: r }, r))
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Emphasis" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "select",
            {
              style: selectStyle,
              value: creative.emphasis || "none",
              onChange: (e) => updateCreative({ emphasis: e.target.value }),
              children: EMPHASIS_OPTIONS.map((em) => /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: em, children: em }, em))
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
          ImageSelector,
          {
            slug,
            sceneNum: scene.sceneNumber,
            currentUrl: scene.imagePath || scene.vizBackgroundPath || "",
            accent: ACCENT,
            forceExpanded: showImagePicker,
            onSelect: (url) => {
              setScene((prev) => ({
                ...prev,
                imagePath: url,
                vizBackgroundPath: prev.visualization ? url : prev.vizBackgroundPath
              }));
              setShowImagePicker(false);
            }
          }
        ),
        scene.imageAsset && /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)(import_jsx_runtime69.Fragment, { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Image Placement" }),
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
              "select",
              {
                style: selectStyle,
                value: scene.imageAsset?.placement || "background",
                onChange: (e) => updateImageAsset({ placement: e.target.value }),
                children: PLACEMENT_OPTIONS.map((p) => /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("option", { value: p, children: p }, p))
              }
            )
          ] }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
            /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("label", { style: labelStyle, children: [
              "Image Opacity (",
              ((scene.imageAsset?.opacity ?? 0.4) * 100).toFixed(0),
              "%)"
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
              "input",
              {
                type: "range",
                min: "0",
                max: "1",
                step: "0.05",
                value: scene.imageAsset?.opacity ?? 0.4,
                onChange: (e) => updateImageAsset({ opacity: parseFloat(e.target.value) }),
                style: { width: "100%", accentColor: ACCENT }
              }
            )
          ] })
        ] }),
        scene.kenBurns && /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("label", { style: { ...labelStyle, display: "flex", alignItems: "center", gap: 6 }, children: [
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
              "input",
              {
                type: "checkbox",
                checked: scene.kenBurns.enabled,
                onChange: (e) => setScene((prev) => ({
                  ...prev,
                  kenBurns: { ...prev.kenBurns, enabled: e.target.checked }
                })),
                style: { accentColor: ACCENT }
              }
            ),
            "Ken Burns"
          ] }),
          scene.kenBurns.enabled && /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { marginTop: 4 }, children: [
            /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("label", { style: labelStyle, children: [
              "Zoom Factor (",
              scene.kenBurns.zoomFactor.toFixed(2),
              ")"
            ] }),
            /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
              "input",
              {
                type: "range",
                min: "1",
                max: "1.5",
                step: "0.01",
                value: scene.kenBurns.zoomFactor,
                onChange: (e) => setScene((prev) => ({
                  ...prev,
                  kenBurns: { ...prev.kenBurns, zoomFactor: parseFloat(e.target.value) }
                })),
                style: { width: "100%", accentColor: ACCENT }
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("label", { style: labelStyle, children: "Source" }),
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "input",
            {
              type: "text",
              style: inputStyle,
              value: viz.source || "",
              onChange: (e) => updateViz({ source: e.target.value }),
              placeholder: "\uCD9C\uCC98..."
            }
          )
        ] }),
        /* @__PURE__ */ (0, import_jsx_runtime69.jsxs)("div", { style: { marginTop: "auto", paddingTop: 12, borderTop: `1px solid ${BORDER}` }, children: [
          /* @__PURE__ */ (0, import_jsx_runtime69.jsx)(
            "button",
            {
              onClick: handleSave,
              disabled: saving,
              style: {
                width: "100%",
                padding: "8px 16px",
                background: ACCENT,
                color: "#000",
                border: "none",
                borderRadius: 6,
                fontWeight: 700,
                fontSize: 13,
                cursor: saving ? "wait" : "pointer",
                opacity: saving ? 0.6 : 1
              },
              children: saving ? "\uC800\uC7A5 \uC911..." : "\uC800\uC7A5"
            }
          ),
          status && /* @__PURE__ */ (0, import_jsx_runtime69.jsx)("div", { style: { fontSize: 11, color: status.startsWith("\uC624\uB958") ? "#EF4444" : "#22C55E", marginTop: 6, textAlign: "center" }, children: status })
        ] })
      ] })
    ] });
  };

  // src/editor/EditorApp.tsx
  var import_jsx_runtime70 = __toESM(require_jsx_runtime());
  var currentRoot = null;
  function mount(el) {
    const data = window.__SCENE_EDITOR_DATA__;
    if (!data) {
      el.innerHTML = '<div style="padding:24px;color:#666;text-align:center">\uC52C \uB370\uC774\uD130 \uC5C6\uC74C</div>';
      return;
    }
    if (currentRoot) {
      currentRoot.unmount();
    }
    currentRoot = (0, import_client.createRoot)(el);
    currentRoot.render(
      /* @__PURE__ */ (0, import_jsx_runtime70.jsx)(
        SceneEditorPanel,
        {
          scene: data.scene,
          meta: data.meta,
          slug: data.slug,
          onSaved: () => {
            const evt = new CustomEvent("scene-editor-saved", { detail: { sceneNumber: data.scene.sceneNumber } });
            document.dispatchEvent(evt);
          }
        }
      )
    );
  }
  function unmount() {
    if (currentRoot) {
      currentRoot.unmount();
      currentRoot = null;
    }
  }
  window.mountSceneEditor = mount;
  window.unmountSceneEditor = unmount;
  var autoRoot = document.getElementById("scene-editor-root");
  if (autoRoot && window.__SCENE_EDITOR_DATA__) {
    mount(autoRoot);
  }
})();
/*! Bundled license information:

react/cjs/react.production.min.js:
  (**
   * @license React
   * react.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

scheduler/cjs/scheduler.production.min.js:
  (**
   * @license React
   * scheduler.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react-dom/cjs/react-dom.production.min.js:
  (**
   * @license React
   * react-dom.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)

react/cjs/react-jsx-runtime.production.min.js:
  (**
   * @license React
   * react-jsx-runtime.production.min.js
   *
   * Copyright (c) Facebook, Inc. and its affiliates.
   *
   * This source code is licensed under the MIT license found in the
   * LICENSE file in the root directory of this source tree.
   *)
*/
