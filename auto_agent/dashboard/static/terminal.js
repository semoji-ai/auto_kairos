/* xterm.js WebSocket Terminal — lazy initialization */
var _terminalInitialized = false;
var _termFitAddon = null;

function fitTerminal() {
  if (_termFitAddon) {
    _termFitAddon.fit();
  }
}

function initTerminal() {
  if (_terminalInitialized) {
    // 이미 초기화됨 — fit만 재호출
    fitTerminal();
    return;
  }

  var container = document.getElementById('terminal');
  if (!container) return;

  _terminalInitialized = true;

  var term = new Terminal({
    theme: {
      background: '#0A0A0A',
      foreground: '#F5F5F5',
      cursor: '#F59E0B',
      cursorAccent: '#0A0A0A',
      selectionBackground: 'rgba(245,158,11,0.3)',
    },
    fontFamily: "'Pretendard', 'Menlo', 'Monaco', monospace",
    fontSize: 14,
    cursorBlink: true,
    scrollback: 5000,
  });

  _termFitAddon = new FitAddon.FitAddon();
  term.loadAddon(_termFitAddon);
  term.open(container);
  // fit은 여기서 호출하지 않음 — 패널 트랜지션 완료 후 호출됨

  // WebSocket 연결
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var ws = new WebSocket(protocol + '//' + location.host + '/ws/terminal');

  ws.onopen = function() {
    term.writeln('\x1b[33mAuto Agent Terminal Connected\x1b[0m');
    term.writeln('');
  };

  ws.onmessage = function(e) {
    term.write(e.data);
  };

  ws.onclose = function() {
    term.writeln('\r\n\x1b[31mConnection closed.\x1b[0m');
  };

  ws.onerror = function() {
    term.writeln('\r\n\x1b[31mWebSocket error.\x1b[0m');
  };

  term.onData(function(data) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(data);
    }
  });

  // 창 리사이즈 시 터미널 맞춤 (보이는 상태일 때만)
  window.addEventListener('resize', function() {
    if (_termFitAddon && container.offsetParent !== null) {
      _termFitAddon.fit();
    }
  });
}
