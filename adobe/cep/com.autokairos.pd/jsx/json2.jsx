/* json2.jsx — JSON.parse 폴리필(파싱만, 경량판).
   Douglas Crockford json2.js(퍼블릭 도메인)의 검증 후 eval 방식.
   ExtendScript(ES3) 호환 — var/function만 사용. */

if (typeof JSON !== "object") {
    JSON = {};
}

(function () {
    "use strict";

    if (typeof JSON.parse !== "function") {
        var rx_one = /^[\],:{}\s]*$/;
        var rx_two = /\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g;
        var rx_three = /"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g;
        var rx_four = /(?:^|:|,)(?:\s*\[)+/g;
        var rx_dangerous = /[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g;

        JSON.parse = function (text, reviver) {
            var j;

            function walk(holder, key) {
                var k;
                var v;
                var value = holder[key];
                if (value && typeof value === "object") {
                    for (k in value) {
                        if (Object.prototype.hasOwnProperty.call(value, k)) {
                            v = walk(value, k);
                            if (v !== undefined) {
                                value[k] = v;
                            } else {
                                delete value[k];
                            }
                        }
                    }
                }
                return reviver.call(holder, key, value);
            }

            text = String(text);
            rx_dangerous.lastIndex = 0;
            if (rx_dangerous.test(text)) {
                text = text.replace(rx_dangerous, function (a) {
                    return "\\u" + ("0000" + a.charCodeAt(0).toString(16)).slice(-4);
                });
            }

            if (
                rx_one.test(
                    text.replace(rx_two, "@").replace(rx_three, "]").replace(rx_four, "")
                )
            ) {
                j = eval("(" + text + ")");
                return typeof reviver === "function" ? walk({ "": j }, "") : j;
            }

            throw new SyntaxError("JSON.parse");
        };
    }
}());
