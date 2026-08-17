/* 제작 비서 — NL 지시를 /api/assistant 로 보내 플랜·결과를 로그에 표시. main.js 전역 사용. */
function _chatAppend(html) {
  var log = $("chatLog");
  log.innerHTML += '<div class="chat-msg">' + html + '</div>';
  log.scrollTop = log.scrollHeight;
}

var CHAT_JOB = null;      // 실행 중인 비서 잡 — 중단 버튼이 대상으로 삼는다

/* 실행 중인 비서 작업 중단 요청. 현재 항목까지만 끝내고 멈춘다. */
function stopChatJob() {
  if (!CHAT_JOB) return;
  fetch(BACKEND + "/api/jobs/" + encodeURIComponent(CHAT_JOB) + "/cancel", { method: "POST" })
    .then(function (r) { return r.json(); })
    .then(function (j) {
      _chatAppend(j.ok ? "⏹ 중단 요청 — 진행 중인 항목까지만 끝냅니다." : "중단 실패: " + _esc(JSON.stringify(j)));
    })
    .catch(function (e) { _chatAppend("중단 오류: " + _esc(String(e))); });
}

function _chatBusy(on, jobId) {
  CHAT_JOB = on ? jobId : null;
  var send = $("btnChatSend"), stop = $("btnChatStop");
  if (send) send.disabled = on;             // 실행 중 재전송 금지(같은 작업 두 번 도는 것 방지)
  if (stop) stop.hidden = !on;
}

function sendChat() {
  if (!SELECTED_PROJECT) { _chatAppend("⚠ 프로젝트를 먼저 선택하세요."); return; }
  if (CHAT_JOB) { _chatAppend("⚠ 이전 작업이 아직 실행 중입니다 — 끝나거나 중단한 뒤에 보내세요."); return; }
  var inp = $("chatInput");
  var msg = (inp.value || "").trim();
  if (!msg) return;
  _chatAppend("🧑 " + _esc(msg));
  inp.value = "";
  _chatAppend("🤖 계획 세우는 중…");
  fetch(BACKEND + "/api/assistant", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, instruction: msg }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { _chatAppend("실패: " + _esc(j.error)); return; }
      if (j.status !== "running" || !j.job_id) { _chatAppend("실패: " + _esc(JSON.stringify(j))); return; }
      _chatAppend("🤖 실행 중… (작업 " + j.job_id + ")");
      _chatBusy(true, j.job_id);
      var seenLogs = 0;
      _awaitJob(j.job_id, function (job) {
        _chatBusy(false, null);
        if (job.status === "cancelled") {
          _chatAppend("⏹ 중단됨" + (job.result && job.result.stopped_at ? " — " + _esc(job.result.stopped_at) : ""));
          if (typeof loadSheet === "function") loadSheet();
          return;
        }
        if (job.status !== "completed") { _chatAppend("실패: " + _esc(job.error || JSON.stringify(job))); return; }
        var out = job.result || {};
        if (out.reply) {                                 // 질문/상담 → 답변 모드
          _chatAppend("🤖 " + _esc(out.reply).replace(/\n/g, "<br>"));
          if (!(out.plan || []).length) return;          // 답변만(실행 없음)
        }
        if (!(out.plan || []).length) {
          _chatAppend("🤖 실행할 액션을 찾지 못했습니다. 실행 지시(예: \"음성 입혀서 합쳐줘\") 또는 질문으로 다시 말씀해 주세요.");
          return;
        }
        var plan = (out.plan || []).map(function (a) {
          var scope = (a.targets && a.targets.length) ? "씬 " + a.targets.join(",") : "전체";
          return "• " + a.action + " [" + scope + "] — " + _esc(a.reason || "");
        }).join("<br>");
        _chatAppend("📋 계획:<br>" + plan);
        (out.results || []).forEach(function (res) {
          _chatAppend("✓ " + res.action + ": " + _esc(JSON.stringify(res.result)));
        });
        _chatAppend("완료. 시트/AE를 확인하세요.");
        if (typeof loadSheet === "function") loadSheet();
      }, function (logs) {
        for (; seenLogs < logs.length; seenLogs++) _chatAppend("… " + _esc(logs[seenLogs]));
      }, 2400);   // 60분 한도 — 비서가 무거운 액션(분리·이미지) 실행 시 대비
    })
    .catch(function (e) { _chatBusy(false, null); _chatAppend("오류: " + _esc(String(e))); });
}

document.addEventListener("DOMContentLoaded", function () {
  var b = $("btnChatSend"); if (b) b.addEventListener("click", sendChat);
  var s = $("btnChatStop"); if (s) s.addEventListener("click", stopChatJob);
  var i = $("chatInput");
  if (i) i.addEventListener("keydown", function (e) { if (e.key === "Enter") sendChat(); });
});
