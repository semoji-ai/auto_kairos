/* 갤러리 패널 — 프로젝트 미디어 탐색 + 검색(serper/pixabay) + 드래그→시트.
   BACKEND/$/SELECTED_PROJECT는 main.js 전역. */

function _gesc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/* 소스 목록 — 종류로 거르고, 작게 깐다. 자세히는 눌러서 본다.
   천 장이 한 줄에 하나씩 크게 깔리면 찾는 것이 일이 된다. */
var GAL_ITEMS = [];
var GAL_FILTER = "전체";

/* 소스 칸이 무엇을 보이는가 — "fav"(즐겨찾기) 또는 "proj"(프로젝트).

   전에는 프로젝트 이미지를 통째로 깔았다. 디아지오편 1044장이고 그중 565장이
   내용이 같은 사본이다(1.3GB) — 개발 과정에서 두 벌씩 남았다. 그 안에서 자주
   쓰는 배경 한 장을 찾는 것은 일이다.

   담아 둔 것만 깔고, 프로젝트 소스는 **폴더를 열어 끌어다 쓴다.** */
var SRC_VIEW = "fav";
var FAV_MD5 = {};        // 이미 담긴 것 — 별을 채워 보이려고

function srcView(v) {
  SRC_VIEW = v;
  var b = document.querySelectorAll("#srcTabs .srct");
  for (var i = 0; i < b.length; i++) {
    b[i].classList.toggle("on", b[i].getAttribute("data-v") === v);
  }
  var fd = $("srcFolders");
  if (fd) { fd.hidden = (v !== "proj"); }
  if (v === "fav") { loadFavorites(); } else { loadGallery(); }
}

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
          + '담아 둔 것이 없습니다.<br>「📁 프로젝트」에서 ☆ 를 눌러 담으세요.<br>'
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

function loadGallery() {
  if (!SELECTED_PROJECT) { $("gallery-panel").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("gallery-panel").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/media?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      GAL_ITEMS = j.items || [];
      if (!GAL_ITEMS.length) { $("gallery-panel").textContent = "(소스 없음)"; return; }
      GAL_FILTER = "전체";
      _renderGallery();
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

function _galGroups() {
  var c = {}, order = [];
  for (var i = 0; i < GAL_ITEMS.length; i++) {
    var g = GAL_ITEMS[i].group || "기타";
    if (!(g in c)) { c[g] = 0; order.push(g); }
    c[g]++;
  }
  return { counts: c, order: order };
}

function _renderGallery() {
  var g = _galGroups();
  var chips = '<div class="gal-filter">'
    + '<button class="galf' + (GAL_FILTER === "전체" ? " on" : "") + '" data-g="전체">'
    + '전체 ' + GAL_ITEMS.length + '</button>'
    + g.order.map(function (k) {
        return '<button class="galf' + (GAL_FILTER === k ? " on" : "") + '" data-g="' + _gesc(k) + '">'
             + _gesc(k) + ' ' + g.counts[k] + '</button>';
      }).join("")
    + '</div>';

  var list = GAL_ITEMS.filter(function (it) {
    return GAL_FILTER === "전체" || (it.group || "기타") === GAL_FILTER;
  });

  var body = '<div class="gal-grid">' + list.map(function (it) {
    var src = "file://" + it.dir + "/" + it.rel;
    if (it.type === "video") {
      return '<div class="gal-item" data-rel="' + _gesc(it.rel) + '" data-dir="' + _gesc(it.dir) + '"'
        + ' data-kind="video" title="' + _gesc(it.rel) + '">'
        + '<div class="gal-vid">🎞</div>'
        + '<button class="gal-ae" data-rel="' + _gesc(it.rel) + '" data-dir="' + _gesc(it.dir) + '" title="AE 프로젝트로 가져오기">↧</button>'
        + '</div>';
    }
    return '<div class="gal-item" data-rel="' + _gesc(it.rel) + '" data-dir="' + _gesc(it.dir) + '"'
      + ' data-kind="image" title="' + _gesc(it.rel) + '">'
      + '<img src="' + src + '" draggable="true"'
      + ' ondragstart="event.dataTransfer.setData(\'text/plain\', this.parentNode.getAttribute(\'data-rel\'))"'
      + ' class="gal-thumb">'
      + '<button class="gal-ae" data-rel="' + _gesc(it.rel) + '" data-dir="' + _gesc(it.dir) + '" title="AE 프로젝트로 가져오기">↧</button>'
      + '<button class="fav-star" data-rel="' + _gesc(it.rel) + '" title="즐겨찾기에 담습니다 — 편이 바뀌어도 남습니다">☆</button>'
      + '</div>';
  }).join("") + '</div>';

  $("gallery-panel").innerHTML = chips + body;

  var fb = $("gallery-panel").querySelectorAll("button.galf");
  for (var k = 0; k < fb.length; k++) {
    fb[k].addEventListener("click", function () {
      GAL_FILTER = this.getAttribute("data-g");
      _renderGallery();
    });
  }
  var stars = $("gallery-panel").querySelectorAll("button.fav-star");
  for (var si = 0; si < stars.length; si++) {
    stars[si].addEventListener("click", function (ev) {
      ev.stopPropagation(); ev.preventDefault();
      var rel = this.getAttribute("data-rel");
      favAdd(rel, rel.split("/").pop(), this);
    });
  }
  var aebtns = $("gallery-panel").querySelectorAll("button.gal-ae");
  for (var i = 0; i < aebtns.length; i++) {
    aebtns[i].addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (typeof importToAE === "function") {
        importToAE(this.getAttribute("data-dir"), [this.getAttribute("data-rel")], "gallery", "gallery-panel");
      }
    });
  }
  // 누르면 크게 본다 — 썸네일이 작아진 만큼 이쪽이 있어야 한다
  var cells = $("gallery-panel").querySelectorAll(".gal-item");
  for (var c = 0; c < cells.length; c++) {
    cells[c].addEventListener("click", function (ev) {
      if (ev.target.closest("button")) { return; }
      var rel = this.getAttribute("data-rel"), dir = this.getAttribute("data-dir");
      var src = "file://" + dir + "/" + rel;
      var html = (this.getAttribute("data-kind") === "video")
        ? '<video src="' + src + '" controls autoplay style="max-width:100%"></video>'
        : '<img class="main" src="' + src + '">';
      if (typeof pvZoom === "function") { pvZoom(html, rel); }
    });
  }
}

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
      .then(function () { done++; if (hint) hint.textContent = "불러오는 중… " + done + "/" + total;
        if (done === total) loadGallery(); })       // 모두 끝나면 소스 목록으로 갱신
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
      if (j.result && j.result.status === "completed") loadGallery();  // 소스 목록 갱신
      else $("gallery-panel").textContent = "저장 실패: " + JSON.stringify(j);
    })
    .catch(function (e) { $("gallery-panel").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  // 새로고침은 **지금 보이는 쪽**을 다시 읽는다 — 즐겨찾기를 보는데 프로젝트를
  // 새로 읽으면 화면이 통째로 바뀐다.
  $("btnGalRefresh").addEventListener("click", function () { srcView(SRC_VIEW); });
  $("btnGalSearch").addEventListener("click", searchGallery);
  srcView("fav");        // 열면 즐겨찾기부터 — 1044장을 깔지 않는다
});
