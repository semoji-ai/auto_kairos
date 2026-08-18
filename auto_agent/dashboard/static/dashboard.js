/* Auto Agent Dashboard JS */

// headline의 {{텍스트}} 를 accent 색상으로 변환
document.addEventListener('DOMContentLoaded', convertHeadlines);
document.addEventListener('htmx:afterSwap', convertHeadlines);

function convertHeadlines() {
  document.querySelectorAll('[data-headline]').forEach(function(el) {
    var text = el.textContent;
    if (text.indexOf('{{') !== -1) {
      el.innerHTML = text.replace(/\{\{(.+?)\}\}/g, '<span class="accent-text">$1</span>');
    }
  });
}

// ─── Terminal Panel Toggle ───
function toggleTerminal() {
  var panel = document.getElementById('terminal-panel');
  var toggle = document.getElementById('terminal-toggle');
  var isOpen = panel.classList.toggle('open');

  document.body.classList.toggle('terminal-open', isOpen);

  var icon = toggle.querySelector('.terminal-icon');
  if (isOpen) {
    if (icon) icon.innerHTML = '&#9724;';
    toggle.classList.add('active');
    if (typeof initTerminal === 'function') {
      initTerminal();
    }
    setTimeout(function() {
      if (typeof fitTerminal === 'function') fitTerminal();
    }, 300);
  } else {
    if (icon) icon.innerHTML = '&#9654;';
    toggle.classList.remove('active');
  }
}

/* ── 대화상자 대체 ─────────────────────────────────────
   데스크톱 앱(Tauri) 창에서는 브라우저 기본 대화상자가 막혀 있다.
   alert는 아무것도 안 뜨고, confirm은 undefined를 돌려준다 — 그래서
   `if (!confirm(...)) return;` 이 항상 걸려 버튼이 죽은 것처럼 보였다.
   실제로 「레이어 나누기」가 눌러도 아무 일이 없던 원인이 이것이다.

   alert는 토스트로 갈음하고, 확인이 필요한 자리는 akConfirm으로 바꾼다.
   confirm은 동기로 답을 내야 해서 화면으로 대체할 수 없다 — 부르는 쪽을
   콜백으로 고치는 편이 맞다. */
(function () {
  function toast(msg, kind) {
    var box = document.getElementById("ak-toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "ak-toasts";
      document.body.appendChild(box);
    }
    var el = document.createElement("div");
    el.className = "ak-toast" + (kind ? " " + kind : "");
    el.textContent = String(msg);
    box.appendChild(el);
    setTimeout(function () { el.classList.add("out"); }, 4000);
    setTimeout(function () { el.remove(); }, 4400);
  }
  window.akToast = toast;
  window.alert = function (m) { toast(m); };

  /* akConfirm(메시지, 예를 눌렀을 때) — 화면 안에서 묻는다. */
  window.akConfirm = function (msg, onYes) {
    var back = document.createElement("div");
    back.className = "ak-modal-back";
    var box = document.createElement("div");
    box.className = "ak-modal";
    var p = document.createElement("p");
    p.textContent = String(msg);
    var row = document.createElement("div");
    row.className = "ak-modal-row";
    var no = document.createElement("button");
    no.textContent = "취소"; no.className = "ghost";
    var yes = document.createElement("button");
    yes.textContent = "진행";
    row.appendChild(no); row.appendChild(yes);
    box.appendChild(p); box.appendChild(row);
    back.appendChild(box);
    document.body.appendChild(back);
    function close() { back.remove(); }
    no.addEventListener("click", close);
    back.addEventListener("click", function (e) { if (e.target === back) close(); });
    yes.addEventListener("click", function () { close(); onYes(); });
    yes.focus();
  };
})();
