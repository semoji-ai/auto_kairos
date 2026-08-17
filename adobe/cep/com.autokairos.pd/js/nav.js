/* 뷰/탭 전환 — 목록 뷰 ↔ 상세 뷰, 기획/스토리보드 탭.
   SELECTED_PROJECT는 main.js의 전역(var)을 공유한다. main.js → nav.js 순 로드. */

function _$(id) { return document.getElementById(id); }

function showListView() {
  _$("view-detail").hidden = true;
  _$("view-list").hidden = false;
}

function enterProject(pid, label) {
  SELECTED_PROJECT = pid;            // main.js 전역
  _$("detailTitle").textContent = label || pid;
  _$("view-list").hidden = true;
  _$("view-detail").hidden = false;
  switchTab("planning");
  if (typeof loadPlanningFiles === "function") loadPlanningFiles();
  if (typeof loadStepper === "function") loadStepper();
}

function exitProject() {
  showListView();
}

function switchTab(name) {
  var planning = name === "planning";
  _$("tab-planning").hidden = !planning;
  _$("tab-storyboard").hidden = planning;
  _$("btnTabPlanning").classList.toggle("active", planning);
  _$("btnTabStoryboard").classList.toggle("active", !planning);
  if (!planning && typeof loadSheet === "function") loadSheet();
  if (!planning && typeof loadGallery === "function") loadGallery();
}

document.addEventListener("DOMContentLoaded", function () {
  _$("btnBackToList").addEventListener("click", exitProject);
  _$("btnTabPlanning").addEventListener("click", function () { switchTab("planning"); });
  _$("btnTabStoryboard").addEventListener("click", function () { switchTab("storyboard"); });
});
