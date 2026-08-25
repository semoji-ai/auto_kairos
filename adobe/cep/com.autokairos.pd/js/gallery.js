/* 갤러리 패널 — 프로젝트 미디어 탐색 + 검색(serper/pixabay) + 드래그→시트.
   BACKEND/$/SELECTED_PROJECT는 main.js 전역. */

function _gesc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* 소스 목록 — 종류로 거르고, 작게 깐다. 자세히는 눌러서 본다.
   천 장이 한 줄에 하나씩 크게 깔리면 찾는 것이 일이 된다. */

/* 소스 칸이 무엇을 보이는가 — "fav"(즐겨찾기) 또는 "proj"(프로젝트).

   전에는 프로젝트 이미지를 통째로 깔았다. 디아지오편 1044장이고 그중 565장이
   내용이 같은 사본이다(1.3GB) — 개발 과정에서 두 벌씩 남았다. 그 안에서 자주
   쓰는 배경 한 장을 찾는 것은 일이다.

   담아 둔 것만 깔고, 프로젝트 소스는 **폴더를 열어 끌어다 쓴다.** */
var FAV_MD5 = {};        // 이미 담긴 것 — 별을 채워 보이려고

/* 소스 칸은 **즐겨찾기만** 보인다.

   프로젝트 이미지를 여기 깔지 않는다. 디아지오편 1044장이고 그중 565장이 같은
   내용의 사본이다 — 다 깔아 두면 정작 자주 쓰는 배경 한 장을 못 찾는다.
   씬 이미지와 에셋은 **이미 왼쪽 시트에 있다.**

   담는 길은 둘이다.
     · 왼쪽 시트의 씬 이미지·레이어에서 ☆
     · 파인더에서 이 칸에 끌어다 놓기

   프로젝트 소스는 「폴더 열기」로 간다. */
function loadFavorites() {
  var box = $("gallery-panel");
  box.textContent = "불러오는 중...";
  fetch(BACKEND + "/api/favorites").then(function (r) { return r.json(); })
    .then(function (j) {
      FAV_MD5 = {};
      var its = j.items || [];
      for (var i = 0; i < its.length; i++) { FAV_MD5[its[i].md5] = its[i].name; }
      if (!its.length) {
        box.innerHTML = '<div style="font-size:11px;color:#8b9098;line-height:1.7">'
          + '담아 둔 것이 없습니다.<br><br>'
          + '· 왼쪽 시트의 씬 이미지·레이어에서 <b>☆</b><br>'
          + '· 파인더에서 이 칸에 <b>끌어다 놓기</b><br><br>'
          + '자주 쓰는 배경은 편이 바뀌어도 여기 남습니다.</div>';
        return;
      }
      var h = '<div class="gal-grid">';
      for (var k = 0; k < its.length; k++) {
        var it = its[k];
        h += '<div class="gal-item" draggable="true" data-abs="' + _gesc(it.path) + '">'
          + '<img src="file://' + _gesc(it.path) + '" loading="lazy">'
          + '<span class="cap">' + _gesc(it.label || it.name) + '</span>'
          + '<button class="fav-star on" data-name="' + _gesc(it.name) + '" title="즐겨찾기에서 뺍니다">★</button>'
          + '</div>';
      }
      box.innerHTML = h + "</div>";
      _wireFavRemove();
    })
    .catch(function (e) { box.textContent = "오류: " + e; });
}

/* 파인더에서 끌어다 놓으면 담는다 — 프로젝트 밖의 소스도 이렇게 들인다. */
function wireFavDrop() {
  var box = $("gallery-panel");
  if (!box || box.__favDrop) { return; }
  box.__favDrop = true;
  box.addEventListener("dragover", function (e) {
    if (e.dataTransfer && e.dataTransfer.types.indexOf("Files") !== -1) {
      e.preventDefault(); box.classList.add("fav-drop");
    }
  });
  box.addEventListener("dragleave", function () { box.classList.remove("fav-drop"); });
  box.addEventListener("drop", function (e) {
    box.classList.remove("fav-drop");
    var fs = e.dataTransfer && e.dataTransfer.files;
    if (!fs || !fs.length) { return; }
    e.preventDefault();
    var left = fs.length;
    for (var i = 0; i < fs.length; i++) {
      // CEP 는 파일의 실제 경로를 준다(브라우저와 다르다)
      var p = fs[i].path || fs[i].name;
      fetch(BACKEND + "/api/favorites/add", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: p, label: String(p).split("/").pop() }),
      }).then(function () { if (--left <= 0) { loadFavorites(); } })
        .catch(function () { if (--left <= 0) { loadFavorites(); } });
    }
  });
}

function _wireFavRemove() {
  var b = $("gallery-panel").querySelectorAll(".fav-star");
  for (var i = 0; i < b.length; i++) {
    b[i].addEventListener("click", function (ev) {
      ev.stopPropagation(); ev.preventDefault();
      var n = this.getAttribute("data-name");
      fetch(BACKEND + "/api/favorites/remove", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: n }),
      }).then(function () { loadFavorites(); });
    });
  }
}

/* 프로젝트 소스에서 담기 — 파일을 **복사한다.** 원본을 가리키기만 하면
   그 프로젝트를 지웠을 때 즐겨찾기가 통째로 깨진다. */
function favAdd(rel, label, btn) {
  fetch(BACKEND + "/api/favorites/add", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, rel: rel, label: label || "" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.ok && btn) { btn.classList.add("on"); btn.textContent = "★"; }
    })
    .catch(function () { });
}

/* 탐색기에서 폴더 열기 — 맥·윈도우가 각각 다르다(백엔드가 가른다). */
function revealFolder(rel) {
  if (!SELECTED_PROJECT) { return; }
  fetch(BACKEND + "/api/reveal", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, rel: rel || "" }),
  });
}

/* 프로젝트 이미지를 훑어 까는 코드는 걷어냈다.

   소스 칸이 즐겨찾기만 보이게 되면서 부르는 곳이 없어졌는데, 남겨 두면
   누군가(나 포함) 다시 부른다 — 실제로 `nav.js` 가 프로젝트를 열 때마다
   부르고 있어서, 화면을 바꾸고도 씬 이미지가 계속 떴다. 되살릴 일이 있으면
   git 에서 꺼내면 된다(1f15ebb 이전).

   프로젝트 소스는 「폴더 열기」로 간다 — 파인더에서 끌어다 놓는 편이 빠르다. */

function searchGallery() {
  if (!SELECTED_PROJECT) { $("gallery-panel").textContent = "프로젝트를 먼저 선택하세요."; return; }
  var q = ($("galSearch").value || "").trim();
  if (!q) { $("gallery-panel").textContent = "검색어를 입력하세요."; return; }
  var engine = $("galEngine").value;
  $("gallery-panel").textContent = "검색 중... (" + engine + ")";
  fetch(BACKEND + "/api/search-images?project_id=" + encodeURIComponent(SELECTED_PROJECT) +
        "&q=" + encodeURIComponent(q) + "&engine=" + encodeURIComponent(engine))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.error) { $("gallery-panel").textContent = "검색 오류: " + j.error; return; }
      var imgs = j.images || [];
      if (!imgs.length) { $("gallery-panel").textContent = "(결과 없음)"; return; }
      _galSel = {};   // 선택 초기화
      $("gallery-panel").innerHTML =
        '<div class="gal-selbar"><button id="btnGalImport" class="mini">선택 불러오기 (0)</button>'
        + '<span class="gal-hint">이미지를 클릭해 선택 → 프로젝트 소스로 저장</span></div>'
        + imgs.map(function (im, idx) {
          return '<img src="' + _gesc(im.thumb) + '" data-url="' + _gesc(im.url) + '" data-idx="' + idx
            + '" title="' + _gesc(im.title) + '" class="gal-thumb gal-pick" style="cursor:pointer;">';
        }).join("");
      var gi = $("gallery-panel").querySelectorAll("img[data-url]");
      for (var i = 0; i < gi.length; i++) {
        gi[i].addEventListener("click", function () {
          var idx = this.getAttribute("data-idx");
          if (_galSel[idx]) { delete _galSel[idx]; this.classList.remove("sel"); }
          else { _galSel[idx] = this.getAttribute("data-url"); this.classList.add("sel"); }
          _updateGalImportBtn();
        });
      }
      $("btnGalImport").addEventListener("click", importSelectedToProject);
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

var _galSel = {};   // {idx: url} — 검색 결과 선택분

function _updateGalImportBtn() {
  var n = Object.keys(_galSel).length;
  var b = $("btnGalImport");
  if (b) b.textContent = "선택 불러오기 (" + n + ")";
}

function importSelectedToProject() {
  var idxs = Object.keys(_galSel);
  if (!idxs.length) { return; }
  var hint = $("gallery-panel").querySelector(".gal-hint");
  var done = 0, total = idxs.length;
  if (hint) hint.textContent = "불러오는 중… 0/" + total;
  idxs.forEach(function (idx) {
    fetch(BACKEND + "/api/search-images/save", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, url: _galSel[idx], name: "search_" + idx + ".jpg" }),
    }).then(function (r) { return r.json(); })
      .then(function (j) {
        done++;
        if (hint) { hint.textContent = "불러오는 중… " + done + "/" + total; }
        // **골라서 받은 것은 즐겨찾기에 담는다.** 검색해서 고른 것은 쓰려고
        // 받은 것이다. 프로젝트에만 떨어뜨리면 1044장 속에 묻힌다.
        var rel = j && j.result && j.result.rel;
        if (rel) { favAdd(rel, String(rel).split("/").pop()); }
        if (done === total) { loadFavorites(); }
      })
      .catch(function () { done++; });
  });
}

function saveSearchResult(url, name) {
  $("gallery-panel").innerHTML = "<div>저장 중... " + _gesc(name) + "</div>" + $("gallery-panel").innerHTML;
  fetch(BACKEND + "/api/search-images/save", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, url: url, name: name }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.result && j.result.status === "completed") {
        // 골라서 받은 것이니 즐겨찾기에 담는다
        if (j.result.rel) { favAdd(j.result.rel, name); }
        loadFavorites();
      }
      else $("gallery-panel").textContent = "저장 실패: " + JSON.stringify(j);
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  // 새로고침은 **지금 보이는 쪽**을 다시 읽는다 — 즐겨찾기를 보는데 프로젝트를
  // 새로 읽으면 화면이 통째로 바뀐다.
  $("btnGalRefresh").addEventListener("click", loadFavorites);
  $("btnGalSearch").addEventListener("click", searchGallery);
  wireFavDrop();
  loadFavorites();       // 소스 칸은 즐겨찾기만 — 1044장을 깔지 않는다
});
