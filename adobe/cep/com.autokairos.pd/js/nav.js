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
  // 소스 칸은 **즐겨찾기만** 보인다. 프로젝트 이미지를 여기 깔지 않는다 —
  // 1044장이고 그중 565장이 같은 내용의 사본이라, 다 깔면 정작 자주 쓰는
  // 배경 한 장을 못 찾는다. 씬 이미지와 에셋은 이미 왼쪽 시트에 있다.
  if (!planning && typeof loadFavorites === "function") loadFavorites();
}

document.addEventListener("DOMContentLoaded", function () {
  _$("btnBackToList").addEventListener("click", exitProject);
  _$("btnTabPlanning").addEventListener("click", function () { switchTab("planning"); });
  _$("btnTabStoryboard").addEventListener("click", function () { switchTab("storyboard"); });
});
