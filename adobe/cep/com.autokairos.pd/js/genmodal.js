/* 이미지 생성 모달 — 카테고리별 폼 + 엔드포인트 라우팅. 전역 $/BACKEND/SELECTED_PROJECT.
   완료 후 loadGallery/loadSheet 갱신(있으면). */

function openGenModal() {
  if (!SELECTED_PROJECT) { alert("프로젝트를 먼저 선택하세요."); return; }
  $("genStatus").textContent = "—";
  $("genModal").hidden = false;
  _genOnCategory();
}

function closeGenModal() { $("genModal").hidden = true; }

function _genOnCategory() {
  var cat = $("genCategory").value;
  $("genFieldName").hidden = (cat === "scene");
  $("genFieldScene").hidden = (cat !== "scene");
  // 기준 캐릭터(스타일): 씬·배경·소품에서 노출(캐릭터 생성 시엔 숨김)
  $("genFieldChar").hidden = (cat === "character");
  $("genPromptLabel").textContent =
    cat === "character" ? "헤어·의상" :
    cat === "scene" ? "프롬프트(비우면 원고 기반)" : "장면 설명 / 프롬프트";
  if (cat === "scene") _genLoadScenes();
  if (cat !== "character") _genLoadChars();
}

function _genLoadScenes() {
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var opts = (j.scenes || []).map(function (s) {
        return '<option value="' + s.sceneNumber + '">#' + s.sceneNumber + " " + (s.title || "") + '</option>';
      }).join("");
      $("genScene").innerHTML = opts || '<option value="">(씬 없음)</option>';
    });
}

function _genLoadChars() {
  fetch(BACKEND + "/api/characters/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var sel = SELECTED_CHARACTER || "";
      $("genChar").innerHTML = '<option value="">(없음)</option>' + (j.images || []).map(function (n) {
        var nm = n.replace(/^char_/, "").replace(/\.png$/, "");
        return '<option value="' + nm + '"' + (nm === sel ? " selected" : "") + '>' + nm + '</option>';
      }).join("");
    });
}

function submitGen() {
  var cat = $("genCategory").value;
  var prompt = ($("genPrompt").value || "").trim();
  var name = ($("genName").value || "").trim();
  $("genStatus").textContent = "생성 중... (codex, 수십 초)";
  var url, payload;
  if (cat === "character") {
    if (!name || !prompt) { $("genStatus").textContent = "이름과 헤어·의상을 입력하세요."; return; }
    url = "/api/characters/generate"; payload = { project_id: SELECTED_PROJECT, name: name, looks: prompt };
  } else if (cat === "scene") {
    url = "/api/scenes/image";
    payload = { project_id: SELECTED_PROJECT, sceneNumber: parseInt($("genScene").value, 10),
                character: $("genChar").value || "", prompt: prompt, style: $("genStyle").value };
  } else { // background / prop — 선택 캐릭터의 스타일로(인물은 안 그림)
    if (!prompt) { $("genStatus").textContent = "장면 설명을 입력하세요."; return; }
    url = "/api/assets/generate";
    payload = { project_id: SELECTED_PROJECT, category: cat, name: name, prompt: prompt,
                character: $("genChar").value || "", style: $("genStyle").value };
  }
  fetch(BACKEND + url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var res = j.result || j.character || j;
      var ok = res && (res.status === "completed" || res.ok || j.character);
      $("genStatus").textContent = ok ? "생성 완료 ✓" : ("실패: " + JSON.stringify(j));
      if (ok) {
        if (typeof loadGallery === "function") loadGallery();
        if (typeof loadSheet === "function") loadSheet();
      }
    })
    .catch(function (e) { $("genStatus").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnOpenGenModal").addEventListener("click", openGenModal);
  $("genClose").addEventListener("click", closeGenModal);
  $("genCancel").addEventListener("click", closeGenModal);
  $("genCategory").addEventListener("change", _genOnCategory);
  $("genSubmit").addEventListener("click", submitGen);
});
