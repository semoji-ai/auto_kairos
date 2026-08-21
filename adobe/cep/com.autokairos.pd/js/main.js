/* auto_kairos PD 패널 — PoC 로직.
   - 백엔드 /health 로 연결 확인 (#3)
   - build_scene.jsx 를 evalScript 로 AE에 실행해 컴프 생성 (#4)
   CSInterface 전체 라이브러리 대신 window.__adobe_cep__ 직접 사용(최소). */

var BACKEND = "http://127.0.0.1:8765";
var PROJECTS_ROOT = "";   // /health 응답의 root — 머신 경로 하드코딩 대신 백엔드가 알려줌

function $(id) { return document.getElementById(id); }

/* ===== 잡 완료 통지 — SSE 푸시(기본) + 폴링(폴백) =====
   백엔드 /api/events 가 잡 로그·완료를 밀어줌 → 한도 없음. SSE 불가 시에만 _pollJob. */
var _SSE = null;
var _JOB_WAITERS = {};   // {job_id: {onDone, onLog, logs[]}}

function connectEvents() {
  if (_SSE) return;
  try {
    _SSE = new EventSource(BACKEND + "/api/events");
    _SSE.onmessage = function (e) {
      var ev; try { ev = JSON.parse(e.data); } catch (_) { return; }
      var w = _JOB_WAITERS[ev.job_id];
      if (!w) return;
      if (ev.type === "log") {
        w.logs.push(ev.line);
        if (w.onLog) w.onLog(w.logs);          // 폴링과 동일하게 누적 배열 전달
      } else if (ev.type === "status" && ev.status !== "running") {
        delete _JOB_WAITERS[ev.job_id];
        fetch(BACKEND + "/api/jobs/" + ev.job_id)
          .then(function (r) { return r.json(); })
          .then(w.onDone)
          .catch(function () { w.onDone({ status: ev.status, error: ev.error }); });
      }
    };
    _SSE.onerror = function () {                // 연결 끊김 — 닫고 다음 잡부터 폴링 폴백
      try { _SSE.close(); } catch (_) {}
      _SSE = null;
    };
  } catch (e) { _SSE = null; }
}

/* 잡 완료 대기 — SSE 연결돼 있으면 푸시, 아니면 폴링. 시그니처는 _pollJob과 동일. */
function _awaitJob(jid, onDone, onLog, maxTries) {
  if (_SSE && _SSE.readyState !== 2) {
    _JOB_WAITERS[jid] = { onDone: onDone, onLog: onLog, logs: [] };
    // 레이스 가드: 등록 전에 이미 끝난 잡이면 즉시 처리
    fetch(BACKEND + "/api/jobs/" + jid).then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.status && j.status !== "running" && _JOB_WAITERS[jid]) {
          delete _JOB_WAITERS[jid];
          onDone(j);
        }
      }).catch(function () {});
    return;
  }
  _pollJob(jid, onDone, onLog, maxTries);
}

/* 잡 폴링(폴백) — 1.5s 간격, onLog(logs)/onDone(job). 기본 5분 한도(maxTries로 연장 가능). */
function _pollJob(jid, onDone, onLog, maxTries) {
  maxTries = maxTries || 200;
  var tries = 0;
  var t = setInterval(function () {
    if (++tries > maxTries) { clearInterval(t); onDone({ status: "failed", error: "타임아웃" }); return; }
    fetch(BACKEND + "/api/jobs/" + jid).then(function (r) { return r.json(); })
      .then(function (j) {
        if (onLog && j.logs) onLog(j.logs);
        if (j.status !== "running") { clearInterval(t); onDone(j); }
      })
      .catch(function () { /* 일시 오류 — 다음 틱 */ });
  }, 1500);
}

function evalScript(script) {
  return new Promise(function (resolve) {
    window.__adobe_cep__.evalScript(script, function (r) { resolve(r); });
  });
}

/* 로컬 파일(확장 내부 jsx) 동기 읽기 — file:// 에서 fetch가 막혀도 XHR은 동작 */
function readLocal(relPath) {
  var x = new XMLHttpRequest();
  // 캐시 무력화 — CEF가 jsx를 캐시해 옛 버전을 로드하는 것 방지(항상 최신 파일)
  var bust = relPath + (relPath.indexOf("?") < 0 ? "?" : "&") + "_=" + (new Date()).getTime();
  x.open("GET", bust, false);
  x.send();
  return x.responseText;
}

function _setHealth(ok, text) {
  var dot = $("healthDot"); if (dot) dot.className = "dot " + (ok ? "ok" : "bad");
  if ($("healthText")) $("healthText").textContent = text;
  var rc = $("btnReconnect"); if (rc) rc.hidden = ok;     // 연결되면 버튼 숨김
}

/* ===== 백엔드 자동 시작 =====
   health 실패 시 CEP createProcess 로 python3 -m backend.app 스폰.
   확장이 심링크로 설치돼 있어 cd -P 로 실제 레포 루트를 해석. */
var _BACKEND_SPAWNED = false;

function _spawnBackend() {
  if (_BACKEND_SPAWNED) return false;
  var cep = window.cep;
  var adobe = window.__adobe_cep__;
  if (!cep || !cep.process || !adobe) return false;
  var extDir = decodeURI(adobe.getSystemPath("extension") || "").replace(/^file:\/\//, "");
  if (!extDir) return false;
  var cmd = 'cd -P "' + extDir + '" && cd ../.. && exec /usr/bin/env python3 -m backend.app';
  var res = cep.process.createProcess("/bin/zsh", "-lc", cmd);
  _BACKEND_SPAWNED = !(res && res.err);
  return _BACKEND_SPAWNED;
}

function checkBackend(retriesLeft) {
  if (typeof retriesLeft !== "number") retriesLeft = 0;
  _setHealth(false, "백엔드 확인 중…");
  fetch(BACKEND + "/health")
    .then(function (r) { return r.json(); })
    .then(function (j) {
      _setHealth(true, "백엔드 연결됨 · codex " + j.codex_status + " · v" + j.version);
      PROJECTS_ROOT = j.root || "";
      connectEvents();                                    // SSE 푸시 연결(잡 완료·로그 실시간)
      loadProjects();                                     // 연결되면 목록 자동 로드
      loadLlmSetting();                                   // 오케스트레이터 LLM 선택값 로드
    })
    .catch(function () {
      if (retriesLeft > 0) {
        _setHealth(false, "백엔드 시작 대기 중… (" + retriesLeft + ")");
        setTimeout(function () { checkBackend(retriesLeft - 1); }, 800);
        return;
      }
      if (_spawnBackend()) {                              // 자동 스폰 후 재시도
        _setHealth(false, "백엔드 자동 시작 중…");
        setTimeout(function () { checkBackend(5); }, 800);
        return;
      }
      _setHealth(false, "백엔드 연결 안 됨 — python3 -m backend.app 실행 후 [연결]");
    });
}

function loadLlmSetting() {
  fetch(BACKEND + "/api/llm/settings").then(function (r) { return r.json(); })
    .then(function (j) {
      var sel = $("llmSelect"); if (!sel) return;
      sel.innerHTML = (j.choices || ["claude", "codex"]).map(function (c) {
        return '<option value="' + c + '"' + (c === j.orchestrator ? " selected" : "") + '>' + c + '</option>';
      }).join("");
    }).catch(function () {});
}

function saveLlmSetting() {
  fetch(BACKEND + "/api/llm/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orchestrator: $("llmSelect").value }),
  }).then(function (r) { return r.json(); }).then(function (j) {
    if ($("llmHint")) $("llmHint").textContent = "추론=" + j.orchestrator + " / 이미지=codex";
  });
}

function buildComp() { _assemble(null); }

/* Final 컴프를 AE 렌더 큐에 추가 — 출력은 프로젝트 render/ 폴더(MP4 인코딩은 OM 템플릿/AME). */
function queueRender() {
  if (!SELECTED_PROJECT) { $("aeresult").textContent = "프로젝트를 먼저 선택하세요."; return; }
  if (!PROJECTS_ROOT) { $("aeresult").textContent = "백엔드 연결 필요(/health root)."; return; }
  var outPath = PROJECTS_ROOT + "/" + SELECTED_PROJECT + "/render/final.mov";
  var jsx;
  try { jsx = readLocal("./jsx/render_queue.jsx"); }
  catch (e) { $("aeresult").textContent = "jsx 로드 실패: " + e; return; }
  $("aeresult").textContent = "렌더 큐 추가 중...";
  var call = "\nakQueueRender(" + JSON.stringify("Final") + ", " + JSON.stringify(outPath)
    + ", \"\", \"0\");";   // 템플릿 기본·즉시 렌더 안 함(사용자가 AE에서 Render)
  evalScript(jsx + call).then(function (r) {
    $("aeresult").textContent = r || "(빈 응답 — AE 콘솔 확인)";
  });
}

/* 말자막 — 백엔드가 SRT/JSON 빌드 → Final 컴프에 자막 레이어 1개(Source Text 키프레임) 생성.
   sceneNumbers 배열을 주면 그 씬들의 자막만(시각은 전체 기준 그대로). */
function buildSubtitles(sceneNumbers, statusFn) {
  var setS = statusFn || function (m) { $("aeresult").textContent = m; };
  if (!SELECTED_PROJECT) { setS("프로젝트를 먼저 선택하세요."); return; }
  setS("말자막 빌드 중...");
  var bodyObj = { project_id: SELECTED_PROJECT };
  if (sceneNumbers instanceof Array && sceneNumbers.length) bodyObj.sceneNumbers = sceneNumbers;
  return fetch(BACKEND + "/api/subtitles/build", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodyObj),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error || !j.json) { setS("실패: " + JSON.stringify(j)); return; }
      var warn = (j.scenes_no_ts && j.scenes_no_ts.length)
        ? " (타임스탬프 없는 씬 " + j.scenes_no_ts.join(",") + " — 균등 분배)" : "";
      var jsx;
      try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/subtitle_layers.jsx"); }
      catch (e) { setS("jsx 로드 실패: " + e); return; }
      var call = "\nakBuildSubtitles(" + JSON.stringify(j.json) + ", " + JSON.stringify(j.ae_tokens || "") + ");";
      return evalScript(jsx + call).then(function (r) {
        setS((r || "") + " — " + j.lines + "줄" + warn + " / SRT: " + j.srt);
      });
    })
    .catch(function (e) { setS("오류: " + e); });
}

/* AE 컴프 조립. scope=null이면 전체, 숫자면 그 씬, 배열이면 그 씬들만(한 번의 호출로).
   여러 씬을 한 번에 넘겨야 매니페스트 빌드·jsx 실행이 씬 수만큼 반복되지 않는다. */
function _assemble(scope, statusFn) {
  if (!SELECTED_PROJECT) { (statusFn || function (m) { $("aeresult").textContent = m; })("프로젝트를 먼저 선택하세요."); return; }
  var setS = statusFn || function (m) { $("aeresult").textContent = m; };
  setS("매니페스트 빌드 중...");
  var bodyObj = { project_id: SELECTED_PROJECT };
  if (scope instanceof Array) { bodyObj.sceneNumbers = scope; }
  else if (scope != null) { bodyObj.sceneNumber = scope; }
  return fetch(BACKEND + "/api/assembly/manifest", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodyObj),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error || !j.path) { setS("매니페스트 실패: " + JSON.stringify(j)); return; }
      var jsx;
      try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/layouts.jsx")
                  + "\n" + readLocal("./jsx/build_scene.jsx"); }
      catch (e) { setS("jsx 로드 실패: " + e); return; }
      setS("AE 조립 중... (씬 " + j.scenes + "개)");
      var call = "\nakBuildScene(" + JSON.stringify(j.path) + ");";
      return evalScript(jsx + call).then(function (r) { setS(r || "(빈 응답 — AE 콘솔 확인)"); });
    })
    .catch(function (e) { setS("오류: " + e); });
}

/* 시트 행의 '컴프' 버튼 — 한 씬만 AE 컴프로. 행 상태에 결과 표시. */
function buildSceneComp(n) {
  _assemble(parseInt(n, 10), function (m) {
    if (typeof _rowStatus === "function") _rowStatus(n, m); else $("aeresult").textContent = m;
  });
}

var SELECTED_PROJECT = null;
var SELECTED_CHARACTER = null;  // char_<name>.png 의 <name> — 스토리보드 생성 시 character_ref로 사용

function genCharacter() {
  if (!SELECTED_PROJECT) { $("characters").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var name = ($("charName").value || "").trim();
  var looks = ($("charLooks").value || "").trim();
  if (!name || !looks) { $("characters").textContent = "이름과 헤어·의상을 입력하세요."; return; }
  $("characters").textContent = "캐릭터 생성 중... (베이스 리스타일, codex)";
  fetch(BACKEND + "/api/characters/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, name: name, looks: looks }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (!j.character || j.character.status !== "completed") {
        $("characters").textContent = "실패: " + JSON.stringify(j); return;
      }
      SELECTED_CHARACTER = name;
      return showCharacters();
    })
    .catch(function (e) { $("characters").textContent = "오류: " + e; });
}

function showCharacters() {
  if (!SELECTED_PROJECT) { $("characters").textContent = "프로젝트를 먼저 선택하세요."; return; }
  fetch(BACKEND + "/api/characters/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", imgs = j.images || [];
      if (!imgs.length) { $("characters").textContent = "(캐릭터 없음)"; return; }
      $("characters").innerHTML = imgs.map(function (n) {
        var nm = n.replace(/^char_/, "").replace(/\.png$/, "");
        var sel = (nm === SELECTED_CHARACTER) ? "border:2px solid #4A90D9;" : "border:2px solid transparent;";
        // data-name은 되읽는 속성 — encodeURIComponent 왕복(SELECTED_CHARACTER는 원본 이름 유지)
        return '<img src="file://' + dir + '/' + n + '" data-name="' + encodeURIComponent(nm) + '" style="width:90px;height:auto;margin:3px;border-radius:4px;cursor:pointer;' + sel + '" title="' + _esc(nm) + ' — 클릭하면 씬 생성 기준 캐릭터로 선택">';
      }).join("");
      var ci = $("characters").querySelectorAll("img");
      for (var x = 0; x < ci.length; x++) {
        ci[x].addEventListener("click", function () {
          SELECTED_CHARACTER = decodeURIComponent(this.getAttribute("data-name") || "");
          showCharacters();  // 선택 테두리 갱신
        });
      }
    });
}

function loadProjects() {
  $("projects").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/projects").then(function (r) { return r.json(); })
    .then(function (j) {
      var rows = j.projects || [];
      if (!rows.length) { $("projects").textContent = "(프로젝트 없음)"; return; }
      $("projects").innerHTML = rows.map(function (p) {
        // data-label은 클릭 시 되읽는 속성 — encodeURIComponent 왕복(따옴표 깨짐 방지)
        return '<div class="proj-item" data-pid="' + p.project_id + '" data-label="'
          + encodeURIComponent(p.title + ' (' + p.project_id + ') [' + p.status + ']') + '">'
          + '<span class="pid">' + p.project_id + '</span>' + _esc(p.title)
          + '<span class="st">' + _esc(p.status) + '</span>'
          /* 잘못 가져온 프로젝트가 쌓여 헷갈린다. 목록에서 뺄 수 있게 한다 —
             지우는 것이 아니라 `_archive/` 로 옮기므로 되돌릴 수 있다. */
          + '<button class="proj-x" data-pid="' + p.project_id + '"'
          + ' title="목록에서 뺍니다 (파일은 _archive 로 옮겨 보관)">✕</button>'
          + '</div>';
      }).join("");
      var links = $("projects").querySelectorAll(".proj-item");
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", function (e) {
          if (e.target && e.target.classList.contains("proj-x")) return;   // ✕ 는 열지 않는다
          enterProject(this.getAttribute("data-pid"), decodeURIComponent(this.getAttribute("data-label") || ""));
        });
      }
      var xs = $("projects").querySelectorAll(".proj-x");
      for (var k = 0; k < xs.length; k++) {
        xs[k].addEventListener("click", function (e) {
          e.stopPropagation();
          var pid = this.getAttribute("data-pid"), row = this.parentNode;
          row.style.opacity = "0.5";
          fetch(BACKEND + "/api/projects/archive", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ project_id: pid }),
          }).then(function (r) { return r.json(); })
            .then(function (j) {
              if (j.ok) loadProjects();
              else { row.style.opacity = "1"; row.title = "빼지 못했습니다: " + JSON.stringify(j); }
            })
            .catch(function (err) { row.style.opacity = "1"; row.title = "오류: " + err; });
        });
      }
    })
    .catch(function (e) { $("projects").textContent = "실패: " + e; });
}

function decompose() {
  if (!SELECTED_PROJECT) { $("scenes").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("scenes").textContent = "씬 분해 중... (codex)";
  fetch(BACKEND + "/api/skills/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, skill_name: "scene-decompose" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "completed") { $("scenes").textContent = "실패: " + JSON.stringify(j); return; }
      return renderScenes();
    })
    .catch(function (e) { $("scenes").textContent = "오류: " + e; });
}

function renderScenes() {
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (doc) {
      $("scenes").innerHTML = (doc.scenes || []).map(function (s) {
        return "<div>#" + s.sceneNumber + " <b>" + _esc(s.title || "") + "</b> — " +
          _esc((s.narration || "").slice(0, 40)) + "...</div>";
      }).join("") || "(씬 없음)";
    })
    .catch(function (e) { $("scenes").textContent = "오류: " + e; });
}

function makeReferences() {
  if (!SELECTED_PROJECT) { $("gallery").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery").textContent = "레퍼런스 목록 생성 중...";
  fetch(BACKEND + "/api/skills/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, skill_name: "reference-list" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) { $("gallery").textContent = "레퍼런스 목록: " + j.status + " — 이제 [이미지 생성]"; })
    .catch(function (e) { $("gallery").textContent = "오류: " + e; });
}

function genImages() {
  if (!SELECTED_PROJECT) { $("gallery").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery").textContent = "이미지 생성 중... (codex, 수십 초)";
  fetch(BACKEND + "/api/images/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) { $("gallery").textContent = "실패: " + JSON.stringify(j); return; }
      _awaitJob(j.job_id, function (job) {
        if (job.status !== "completed") { $("gallery").textContent = "실패: " + JSON.stringify(job.error || job); return; }
        showGallery();
      }, function (logs) {
        if (logs.length) $("gallery").textContent = "이미지 생성 중... " + logs[logs.length - 1];
      });
    })
    .catch(function (e) { $("gallery").textContent = "오류: " + e; });
}

function showGallery() {
  fetch(BACKEND + "/api/images/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "";
      var imgs = j.images || [];
      if (!imgs.length) { $("gallery").textContent = "(이미지 없음)"; return; }
      $("gallery").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:90px;height:auto;margin:3px;border-radius:4px;cursor:pointer;" title="' + _esc(n) + '">';
      }).join("");
      $("gallery").setAttribute("data-dir", dir);
      $("gallery").setAttribute("data-names", imgs.join(","));
      var gi = $("gallery").querySelectorAll("img");
      for (var x = 0; x < gi.length; x++) {
        gi[x].addEventListener("click", function () {
          importToAE($("gallery").getAttribute("data-dir"),
                     [this.getAttribute("title")], "references", "gallery");
        });
      }
    });
}

function genStoryboard() {
  if (!SELECTED_PROJECT) { $("storyboard").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var charNote = SELECTED_CHARACTER ? " (기준 캐릭터: " + SELECTED_CHARACTER + ")" : " (무캐릭터)";
  $("storyboard").textContent = "스토리보드 생성 중... (씬별 codex, 수 분)" + charNote;
  fetch(BACKEND + "/api/storyboard/generate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, character: SELECTED_CHARACTER || "" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) { $("storyboard").textContent = "실패: " + JSON.stringify(j); return; }
      _awaitJob(j.job_id, function (job) {
        if (job.status !== "completed") { $("storyboard").textContent = "실패/일부: " + JSON.stringify(job.error || job); }
        showStoryboard();
      }, function (logs) {
        if (logs.length) $("storyboard").textContent = "스토리보드 생성 중... " + logs[logs.length - 1];
      });
    })
    .catch(function (e) { $("storyboard").textContent = "오류: " + e; });
}

function showStoryboard() {
  if (!SELECTED_PROJECT) { $("storyboard").textContent = "프로젝트를 먼저 선택하세요."; return; }
  fetch(BACKEND + "/api/storyboard/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", imgs = j.images || [];
      if (!imgs.length) { $("storyboard").textContent = "(스토리보드 없음)"; return; }
      $("storyboard").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:120px;height:auto;margin:3px;border-radius:4px;cursor:pointer;" title="' + _esc(n) + '">';
      }).join("");
      $("storyboard").setAttribute("data-dir", dir);
      $("storyboard").setAttribute("data-names", imgs.join(","));
      var si = $("storyboard").querySelectorAll("img");
      for (var x = 0; x < si.length; x++) {
        si[x].addEventListener("click", function () {
          importToAE($("storyboard").getAttribute("data-dir"),
                     [this.getAttribute("title")], "storyboard", "storyboard");
        });
      }
    });
}

function showLayers() {
  if (!SELECTED_PROJECT) { $("layers").textContent = "프로젝트를 먼저 선택하세요."; return; }
  fetch(BACKEND + "/api/layers/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", imgs = j.images || [];
      if (!imgs.length) { $("layers").textContent = "(레이어 없음)"; return; }
      $("layers").innerHTML = imgs.map(function (n) {
        return '<img src="file://' + dir + '/' + n + '" style="width:100px;height:auto;margin:3px;border:1px solid #444;border-radius:4px;background:#666;cursor:pointer;" title="' + _esc(n) + '">';
      }).join("");
      $("layers").setAttribute("data-dir", dir);
      $("layers").setAttribute("data-names", imgs.join(","));
      var li = $("layers").querySelectorAll("img");
      for (var x = 0; x < li.length; x++) {
        li[x].addEventListener("click", function () {
          importToAE($("layers").getAttribute("data-dir"),
                     [this.getAttribute("title")], "layers", "layers");
        });
      }
    });
}

function importToAE(dir, names, folderName, statusElId) {
  if (!names || !names.length) { return; }
  var paths = names.map(function (n) { return dir + "/" + n; });
  var jsx;
  try { jsx = readLocal("./jsx/import_to_ae.jsx"); }
  catch (e) { $(statusElId).textContent = "jsx 로드 실패: " + e; return; }
  var call = "\nakImportToProject(" + JSON.stringify(JSON.stringify(paths)) + ", " +
             JSON.stringify(folderName) + ");";
  evalScript(jsx + call).then(function (r) {
    var note = document.getElementById(statusElId + "_note");
    if (!note) {
      note = document.createElement("div");
      note.id = statusElId + "_note";
      note.style.cssText = "color:#7fd17f;font-size:11px;margin:4px 0;";
      var el = $(statusElId);
      if (!el) { return; }
      el.parentNode.insertBefore(note, el);
    }
    note.textContent = "AE 가져오기: " + r;
  });
}

function importAllImages() {
  importToAE($("gallery").getAttribute("data-dir") || "",
             ($("gallery").getAttribute("data-names") || "").split(",").filter(Boolean),
             "references", "gallery");
}

function importAllStoryboard() {
  importToAE($("storyboard").getAttribute("data-dir") || "",
             ($("storyboard").getAttribute("data-names") || "").split(",").filter(Boolean),
             "storyboard", "storyboard");
}

function importAllLayers() {
  importToAE($("layers").getAttribute("data-dir") || "",
             ($("layers").getAttribute("data-names") || "").split(",").filter(Boolean),
             "layers", "layers");
}

function createProject() {
  $("current").hidden = false;
  var title = ($("newTitle").value || "").trim();
  if (!title) { $("current").textContent = "제목을 입력하세요."; return; }
  fetch(BACKEND + "/api/projects/create", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title, channel: $("newStyle").value,
                           duration: (parseInt($("newDuration").value, 10) || 3) + "분" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (!j.project_id) { $("current").textContent = "생성 실패: " + JSON.stringify(j); return; }
      SELECTED_PROJECT = j.project_id;
      enterProject(j.project_id, j.title + " (" + j.project_id + ") [planned]");
      $("current").textContent = "현재 프로젝트: " + j.title + " (" + j.project_id + ") [planned]";
      $("newTitle").value = "";
      loadProjects();
    })
    .catch(function (e) { $("current").textContent = "오류: " + e; });
}

function importV3() {
  var path = ($("v3Path").value || "").trim();
  if (!path) { $("v3Status").textContent = "경로를 입력하세요."; return; }
  $("v3Status").textContent = "가져오는 중...";
  fetch(BACKEND + "/api/projects/import-v3", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: path }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { $("v3Status").textContent = "실패: " + j.error; return; }
      $("v3Status").textContent = "완료 — 씬 " + j.scenes + "개, 이미지 " + j.images + "개";
      loadProjects();
    })
    .catch(function (e) { $("v3Status").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnCreate").addEventListener("click", createProject);
  var durBtns = document.querySelectorAll("button[data-dur]");
  for (var di = 0; di < durBtns.length; di++) {
    durBtns[di].addEventListener("click", function () {
      $("newDuration").value = this.getAttribute("data-dur");
    });
  }
  $("btnImportV3").addEventListener("click", importV3);
  $("btnReconnect").addEventListener("click", checkBackend);
  $("btnBuild").addEventListener("click", buildComp);
  $("btnBuildAll").addEventListener("click", buildComp);
  var btl = $("btnTimelineAll");
  if (btl) btl.addEventListener("click", function () { exportToTimeline(null); });
  $("btnQueueRender").addEventListener("click", queueRender);
  $("btnSubtitles").addEventListener("click", function () { buildSubtitles(null); });
  $("btnProjects").addEventListener("click", loadProjects);
  $("btnNewProject").addEventListener("click", function () {
    var f = $("newProjectForm"); f.hidden = !f.hidden;
  });
  var ls = $("llmSelect"); if (ls) ls.addEventListener("change", saveLlmSetting);
  checkBackend();          // 열면 자동 백엔드 확인 → 연결 시 프로젝트 목록 자동 로드
  $("btnDecompose").addEventListener("click", decompose);
  $("btnGenCharacter").addEventListener("click", genCharacter);
  $("btnRefreshCharacters").addEventListener("click", showCharacters);
  $("btnRefList").addEventListener("click", makeReferences);
  $("btnGenImages").addEventListener("click", genImages);
  $("btnRefreshGallery").addEventListener("click", showGallery);
  $("btnGenStoryboard").addEventListener("click", genStoryboard);
  $("btnRefreshStoryboard").addEventListener("click", showStoryboard);
  $("btnRefreshLayers").addEventListener("click", showLayers);
  $("btnImportImages").addEventListener("click", importAllImages);
  $("btnImportStoryboard").addEventListener("click", importAllStoryboard);
  $("btnImportLayers").addEventListener("click", importAllLayers);
});
