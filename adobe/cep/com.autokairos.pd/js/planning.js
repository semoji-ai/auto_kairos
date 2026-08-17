/* 기획 탭 — 산출물 파일 목록(그룹) + 미리보기. BACKEND/$/SELECTED_PROJECT는 main.js 전역. */

function loadPlanningFiles() {
  if (!SELECTED_PROJECT) { $("planFiles").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("planFiles").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/projects/files?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var groups = j.groups || [];
      if (!groups.length) { $("planFiles").textContent = "(문서 없음)"; return; }
      $("planFiles").innerHTML = groups.map(function (g) {
        var items = g.files.map(function (n) {
          return '<a href="#" data-file="' + n + '" style="display:inline-block;margin:2px 8px 2px 0;color:#7ab0ff;">' + n + '</a>';
        }).join("");
        return '<div style="margin:4px 0"><span style="color:#9aa0a6">' + g.label + '</span><br>' + items + '</div>';
      }).join("");
      var links = $("planFiles").querySelectorAll("a[data-file]");
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", function (e) {
          e.preventDefault();
          viewPlanningFile(this.getAttribute("data-file"));
        });
      }
    })
    .catch(function (e) { $("planFiles").textContent = "오류: " + e; });
}

var PLAN_EDIT_FILE = null;    // 현재 편집 중 파일명

function viewPlanningFile(name) {
  $("planEditStatus").textContent = "불러오는 중... (" + name + ")";
  fetch(BACKEND + "/api/projects/file?project_id=" + encodeURIComponent(SELECTED_PROJECT) +
        "&name=" + encodeURIComponent(name))
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      if (res.ok && res.j.content != null) {
        PLAN_EDIT_FILE = name;
        $("planEditName").textContent = name;
        $("planEdit").value = res.j.content;
        $("planEditStatus").textContent = "수정 후 💾 저장 — 수정 내역은 LLM이 인지합니다.";
      } else {
        $("planEditStatus").textContent = "(열 수 없음) " + JSON.stringify(res.j);
      }
    })
    .catch(function (e) { $("planEditStatus").textContent = "오류: " + e; });
}

function savePlanningFile() {
  if (!PLAN_EDIT_FILE) { $("planEditStatus").textContent = "먼저 파일을 선택하세요."; return; }
  $("planEditStatus").textContent = "저장 중...";
  fetch(BACKEND + "/api/projects/file/save", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, name: PLAN_EDIT_FILE,
                           content: $("planEdit").value }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      $("planEditStatus").textContent = j.ok
        ? (j.changed ? ("💾 저장됨 — " + j.changed + "줄 변경 기록(이후 LLM 단계가 이 수정을 존중)") : "변경 없음")
        : ("저장 실패: " + (j.error || JSON.stringify(j)));
    })
    .catch(function (e) { $("planEditStatus").textContent = "오류: " + e; });
}

/* ===== 단계별 게이트 스텝퍼 =====
   /api/pipeline/status 로 단계별 완료 상태를 그리고, 단계 하나씩 실행 →
   산출물이 편집기에 자동 오픈 → 검토 후 사용자가 다음 단계를 직접 실행. */
var STAGE_LABELS = { "plan-explore": "① 기획탐색", "deep-research": "② 딥리서치",
                     "draft-write": "③ 초안", "target-research": "④ 타겟리서치",
                     "finalize-manuscript": "⑤ 원고확정", "review-refine": "⑥ 검수" };
var _STAGE_RUNNING = null;

function loadStepper() {
  if (!SELECTED_PROJECT) { $("pipeStepper").textContent = "프로젝트를 먼저 선택하세요."; return; }
  fetch(BACKEND + "/api/pipeline/status?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var stages = j.stages || [];
      var firstPending = -1;
      for (var i = 0; i < stages.length; i++) if (firstPending < 0 && !stages[i].done) firstPending = i;
      $("pipeStepper").innerHTML = stages.map(function (s, i) {
        var running = _STAGE_RUNNING === s.name;
        var icon = running ? "⏳" : (s.done ? "✅" : "○");
        var runnable = !_STAGE_RUNNING && (s.done || i === firstPending || firstPending < 0);
        var label = (STAGE_LABELS[s.name] || s.name) + " " + icon;
        return runnable
          ? '<button class="mini alt" data-stage="' + s.name + '" title="' +
            (s.done ? "재실행(산출물 덮어씀)" : "이 단계 실행") + '">' + label + "</button>"
          : '<span style="opacity:.55;margin:0 4px">' + label + "</span>";
      }).join(" → ");
      var btns = $("pipeStepper").querySelectorAll("button[data-stage]");
      for (var b = 0; b < btns.length; b++) {
        btns[b].addEventListener("click", function () { runStage(this.getAttribute("data-stage")); });
      }
    })
    .catch(function (e) { $("pipeStepper").textContent = "오류: " + e; });
}

function runStage(stage) {
  if (_STAGE_RUNNING) return;
  _STAGE_RUNNING = stage;
  $("pipelineStatus").textContent = (STAGE_LABELS[stage] || stage) + " 실행 중…";
  loadStepper();
  fetch(BACKEND + "/api/pipeline/run-stage", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, stage: stage }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) {
        _STAGE_RUNNING = null; loadStepper();
        $("pipelineStatus").textContent = "시작 실패: " + JSON.stringify(j); return;
      }
      _awaitJob(j.job_id, function (job) {
        _STAGE_RUNNING = null;
        loadStepper(); loadPlanningFiles();
        if (job.status === "completed") {
          var out = (job.artifact_paths || [])[0] || "";
          var name = out.split("/").slice(-2).join("/");
          $("pipelineStatus").textContent = "✅ " + (STAGE_LABELS[stage] || stage) +
            " 완료 — 산출물을 검토·수정한 뒤 다음 단계를 실행하세요.";
          if (name) viewPlanningFile(name.indexOf("/") > 0 && out.indexOf(SELECTED_PROJECT) > 0
            ? out.split(SELECTED_PROJECT + "/")[1] : name);
        } else {
          $("pipelineStatus").textContent = "❌ " + (STAGE_LABELS[stage] || stage) +
            " 실패: " + (job.error || "") + " — 같은 단계를 재실행해 복구하세요.";
        }
      }, function (logs) {
        if (logs && logs.length) $("pipelineStatus").textContent = logs[logs.length - 1];
      }, 2400);
    })
    .catch(function (e) { _STAGE_RUNNING = null; loadStepper(); $("pipelineStatus").textContent = "오류: " + e; });
}

/* 기획→리서치→원고 6단계 파이프라인 — 비동기 잡 + 폴링(스테이지 로그 표시) */
function runPipeline() {
  if (!SELECTED_PROJECT) { $("pipelineStatus").textContent = "프로젝트를 먼저 선택하세요."; return; }
  if (!confirm("기획→리서치→원고 6단계를 자동 실행합니다(LLM, 수십 분 소요 가능). 진행할까요?")) return;
  $("pipelineStatus").textContent = "파이프라인 시작…";
  fetch(BACKEND + "/api/pipeline/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) { $("pipelineStatus").textContent = "시작 실패: " + JSON.stringify(j); return; }
      _awaitJob(j.job_id, function (job) {
        if (job.status === "completed") {
          $("pipelineStatus").textContent = "✅ 완료 — final_manuscript.md 생성. 스토리보드 탭에서 씬 분해를 진행하세요.";
          loadPlanningFiles();
        } else {
          $("pipelineStatus").textContent = "실패: " + (job.error || JSON.stringify(job));
        }
      }, function (logs) {
        if (logs && logs.length) $("pipelineStatus").textContent = logs[logs.length - 1];
      }, 2400);   // 1시간 한도(파이프라인은 수십 분 소요 가능)
    })
    .catch(function (e) { $("pipelineStatus").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnReloadFiles").addEventListener("click", function () { loadPlanningFiles(); loadStepper(); });
  $("btnRunPipeline").addEventListener("click", runPipeline);
  $("btnSavePlanFile").addEventListener("click", savePlanningFile);
});
