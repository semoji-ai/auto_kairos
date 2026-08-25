/* 생성되는 익스프레션이 **문법적으로 유효한 JS 인가**를 본다.
 *
 * 식을 문자열 조각으로 이어 붙여 만들기 때문에, 따옴표 하나가 어긋나면
 * AE 에서 「Expression Disabled」 로만 뜨고 왜 그런지는 안 알려준다.
 * 그 실패를 AE 없이 미리 잡는다.
 *
 * motion_fx.jsx 의 식 **생성** 부분은 AE API 를 전혀 안 쓰는 순수 함수라
 * node 에서 그대로 부를 수 있다. 그래서 사본을 두지 않고 원본을 읽어 돌린다 —
 * 사본을 두면 갈린다.
 *
 * 그리고 만들어진 식을 AE 환경(value, time, effect, marker …)을 흉내 낸
 * 껍데기 위에서 **실제로 돌려** 값이 나오는지까지 본다.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const JSX = path.join(__dirname, "..", "cep", "com.autokairos.pd", "jsx", "motion_fx.jsx");
const src = fs.readFileSync(JSX, "utf8");

// 식 생성에 필요한 부분만 돌린다 — AE API 를 만지는 함수는 부르지 않는다.
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(src, sandbox, { filename: "motion_fx.jsx" });

const KINDS = Object.keys(sandbox.AK_DEFAULTS);

// **그 계열이 실제로 거는 식만** 본다. akFxApplyOne 이 위치 계열엔 위치식을,
// 나머지엔 크기식을 걸고, 투명도는 늘 건다. 안 거는 조합까지 검사하면
// 있지도 않은 실패를 쫓게 된다(처음에 그렇게 해서 15건이 떴다).
function makersFor(kind) {
  const m = { opacity: sandbox.akFxOpacityExpr };
  if (sandbox.akFxIsPos(kind)) m.position = sandbox.akFxPositionExpr;
  else if (kind !== "fade") m.scale = sandbox.akFxScaleExpr;
  return m;
}

let fail = 0;
const say = (ok, msg) => { if (!ok) fail++; console.log((ok ? "  ok   " : "  FAIL ") + msg); };

for (const kind of KINDS) {
  const d = sandbox.AK_DEFAULTS[kind];
  for (const [which, make] of Object.entries(makersFor(kind))) {
    const text = make(d);

    // 1) 문법. **AE 는 `return` 이 아니라 마지막 문장의 값을 쓴다**(completion
    //    value). 그래서 `new Function(text)` 로 감싸면 안 된다 — 감쌌더니 전부
    //    undefined 가 나와 식이 깨진 줄 알았다. `vm.runInNewContext` 가
    //    eval 과 같은 의미라 AE 와 맞는다.
    const run = (ctx) => vm.runInNewContext(text, vm.createContext(ctx),
                                            { filename: `${kind}.${which}.expr` });
    try {
      new vm.Script(text, { filename: `${kind}.${which}.expr` });
    } catch (e) {
      say(false, `${kind}/${which} 문법: ${e.message}`);
      continue;
    }
    say(true, `${kind}/${which} 문법`);

    // 2) 실행 — 컨트롤이 **전부 있을 때**와 **전부 없을 때** 둘 다 돌아야 한다.
    //    없을 때 죽으면 사용자가 슬라이더 하나 지웠을 때 레이어가 사라진다.
    const comp = { frameDuration: 1 / 30, width: 1920, height: 1080 };
    const noMarker = { numKeys: 0, key: () => { throw new Error("no marker"); } };

    const withCtl = (name) => {
      const n = name.replace(/^AK /, "");
      const v = { "시작 크기 %": d.start, "오버슛 %": d.over, "정점 %": d.peak,
                  "되돌림": d.back, "부드러움": d.smooth, "등장 프레임": d.inF,
                  "퇴장 프레임": d.outF, "이동 %": d.move }[n];
      const get = () => (v === undefined ? 1 : v);
      const f = (k) => (k === 1 ? (d.dir || 1) : get());
      f.active = true;
      return f;
    };
    const noCtl = () => { throw new Error("effect deleted"); };

    const base = () => (which === "opacity" ? 100
                      : which === "position" ? [960, 540] : [100, 100]);
    const ctxAt = (t, eff) => ({
      value: base(), time: t, inPoint: 0, outPoint: 2,
      thisComp: comp, effect: eff, marker: noMarker, Math,
    });

    for (const [label, eff] of [["컨트롤 있음", withCtl], ["컨트롤 지움", noCtl]]) {
      let bad = null;
      for (let f = 0; f <= 60 && !bad; f++) {
        try {
          const r = run(ctxAt(f / 30, eff));
          const arr = Array.isArray(r) ? r : [r];
          for (const x of arr) {
            if (typeof x !== "number" || !isFinite(x)) { bad = `f${f} → ${x}`; break; }
          }
        } catch (e) { bad = `f${f} 예외: ${e.message}`; }
      }
      say(!bad, `${kind}/${which} 실행 (${label})` + (bad ? ` — ${bad}` : ""));
    }

    // 3) 정착 지점에서 제자리 — 등장이 끝나면 정확히 원래 값이어야 한다.
    //    **outPoint 에서 재면 안 된다** — 거긴 이미 퇴장이 끝난 자리라
    //    시작값(도장이면 300%)으로 돌아가 있는 게 맞다. 처음에 거기서 재고
    //    「끝값이 300 이다」라고 잘못 잡았다.
    if (which !== "opacity") {
      const settle = (d.inF + 2) / 30;          // 등장 완료 직후, 퇴장 시작 전
      const r = run(ctxAt(settle, withCtl));
      const want = base()[0];
      say(Math.abs(r[0] - want) < 1e-6,
          `${kind}/${which} 정착값 ${want} (실제 ${r[0].toFixed(6)})`);
    }
  }
}

console.log(fail ? `\n실패 ${fail}건` : "\n전부 통과");
process.exit(fail ? 1 : 0);
