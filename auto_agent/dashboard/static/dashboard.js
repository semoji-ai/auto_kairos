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
