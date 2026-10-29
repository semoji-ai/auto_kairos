"""기법 도감 뷰어 생성 — techniques.json 을 index.html 에 넣어 오프라인에서 바로 열리게 한다(file:// 은 fetch 불가).
    python3 motion/dogam/build_viewer.py  →  motion/dogam/index.html

미리보기 위치는 previews_dir.py 규칙(DOGAM_PREVIEWS_DIR → dogam/previews → NAS)으로 찾는다.
뷰어는 항상 상대 경로 previews/ 를 읽으므로, NAS 를 쓸 때는 dogam/previews 를 NAS 로 심볼릭 링크한다.
"""
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from previews_dir import LOCAL, previews_dir  # noqa: E402

PV = previews_dir()
if not PV.is_dir():
    print(f"⚠ 미리보기 폴더 없음: {PV} — 모든 카드가 '미리보기 준비 중'으로 나옵니다 (DOGAM_PREVIEWS_DIR 또는 NAS 마운트)")
elif PV.resolve() != LOCAL.resolve():
    print(f"미리보기: {PV}  (뷰어에서 보려면: ln -s '{PV}' '{LOCAL}')")
tech = json.loads((D / "techniques.json").read_text())
for t in tech:
    pv = t.get("preview")
    t["_hasPreview"] = bool(pv and (PV / f"{pv}.mp4").exists())

HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>세모지 기법 도감</title>
<style>
:root{--bg:#f6f3ee;--card:#fff;--ink:#1d1b19;--sub:#6b655e;--line:#e4ddd3;--accent:#9a3b2e;--chip:#efe8dd;--ban:#b3261e;--ana:#8a6d1d;--ok:#2e7d4f}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17161a;--card:#222126;--ink:#f1eee9;--sub:#a39d95;--line:#34323a;--accent:#e08a74;--chip:#2c2a31;--ban:#ff8a80;--ana:#e0c070;--ok:#7fd3a0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 16px}
h1{margin:0 0 10px;font-size:20px}h1 small{color:var(--sub);font-weight:500;font-size:13px;margin-left:8px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
input[type=search]{flex:1 1 240px;min-width:0;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font-size:15px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.chip{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:999px;padding:5px 11px;font-size:13px;cursor:pointer}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
main{padding:16px;display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column}
.thumb{aspect-ratio:16/9;background:#111;position:relative}
.thumb img,.thumb video{width:100%;height:100%;object-fit:cover;display:block}
.thumb .none{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#aaa;font-size:13px;padding:12px;text-align:center}
.body{padding:10px 12px 12px}.name{font-weight:700}.sum{color:var(--sub);font-size:13px;margin-top:3px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.tag{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--chip);color:var(--sub)}
.st-구현{color:var(--ok)}.st-분석만{color:var(--ana)}.st-금지{color:var(--ban)}
dialog{border:none;border-radius:16px;padding:0;width:min(980px,96vw);background:var(--card);color:var(--ink)}
dialog::backdrop{background:rgba(0,0,0,.6)}
.dv video{width:100%;display:block;background:#000}.dv .in{padding:16px 18px 18px}
.dv h2{margin:0 0 4px;font-size:20px}.dv p{margin:6px 0}.dv .k{color:var(--sub);font-size:13px;margin-top:12px}
.dv code,.dv pre{font:13px/1.45 ui-monospace,Menlo,monospace;background:var(--chip);border-radius:8px}
.dv pre{padding:10px 12px;white-space:pre-wrap;word-break:break-all;margin:6px 0}
.dv a{color:var(--accent)}.x{float:right;border:none;background:none;color:var(--sub);font-size:22px;cursor:pointer}
.pt{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0}.pt th,.pt td{text-align:left;padding:5px 6px;border-bottom:1px solid var(--line)}.pt th{color:var(--sub);font-weight:600}
.g{font-size:10px;padding:1px 6px;border-radius:6px;background:var(--chip);color:var(--sub);margin-right:4px}.sw{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-1px;margin-right:4px;border:1px solid var(--line)}
.pc{font-size:11px;color:var(--accent)}
.empty{grid-column:1/-1;color:var(--sub);text-align:center;padding:40px}
@media (max-width:520px){main{grid-template-columns:1fr}}
</style></head><body>
<header>
  <h1>세모지 기법 도감<small id="count"></small></h1>
  <div class="bar"><input id="q" type="search" placeholder="기법 이름·설명·컴포넌트 검색"></div>
  <div class="chips" id="cats"></div>
  <div class="chips" id="stats"></div>
  <div class="chips" id="refs"></div>
</header>
<main id="grid"></main>
<dialog id="dlg"><div class="dv" id="dv"></div></dialog>
<script>
const T = __DATA__;
const CATS = ["전체", ...Array.from(new Set(T.map(t => t.category)))];
const STATS = ["전체", "구현", "분석만", "금지"];
const RNAME = {"ref1":"중식 4대문파","ref2":"마이크로소프트","ref3":"리뉴얼 포맷","ref4-apple":"애플","ref4-hyundai":"현대","ref4-samsung":"삼성","ref4-cocacola":"코카콜라","ref_explainer_editorial":"설명형 편집 레퍼런스"};
const REFS = ["전체", ...Array.from(new Set(T.flatMap(t => (t.sources || []).map(s => s.ref)))).sort()];
let cat = "전체", stat = "전체", ref = "전체", q = "";
try { const s = JSON.parse(localStorage.getItem("dogam") || "{}"); cat = s.cat || cat; stat = s.stat || stat; } catch (e) {}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function chips(el, list, cur, set){ el.innerHTML = ""; list.forEach(v => { const b = document.createElement("button"); b.className = "chip" + (v === cur ? " on" : "");
  const n = v === "전체" ? "" : " " + T.filter(t => (el.id === "cats" ? t.category : t.status) === v).length; b.textContent = v + n; b.onclick = () => { set(v); render(); }; el.appendChild(b); }); }
function render(){
  try { localStorage.setItem("dogam", JSON.stringify({cat, stat})); } catch (e) {}
  chips(document.getElementById("cats"), CATS, cat, v => cat = v);
  chips(document.getElementById("stats"), STATS, stat, v => stat = v);
  { const el = document.getElementById("refs"); el.innerHTML = ""; REFS.forEach(v => { const b = document.createElement("button"); b.className = "chip" + (v === ref ? " on" : "");
    b.textContent = v === "전체" ? "레퍼런스 전체" : (RNAME[v] || v) + " " + T.filter(t => (t.sources || []).some(s => s.ref === v)).length; b.onclick = () => { ref = v; render(); }; el.appendChild(b); }); }
  const ql = q.trim().toLowerCase();
  const list = T.filter(t => (cat === "전체" || t.category === cat) && (stat === "전체" || t.status === stat) && (ref === "전체" || (t.sources || []).some(s => s.ref === ref)) &&
    (!ql || [t.name, t.summary, t.component, t.spec, (t.tags || []).join(" ")].join(" ").toLowerCase().includes(ql)));
  document.getElementById("count").textContent = list.length + " / " + T.length + "개";
  const g = document.getElementById("grid"); g.innerHTML = "";
  if (!list.length) { g.innerHTML = '<div class="empty">조건에 맞는 기법이 없습니다</div>'; return; }
  list.forEach(t => {
    const c = document.createElement("div"); c.className = "card";
    const th = t._hasPreview ? `<img loading="lazy" src="previews/${t.preview}.jpg" alt="">` : `<div class="none">${t.status === "금지" ? "사용 금지 기법" : t.status === "분석만" ? "미리보기 없음 (분석만)" : "미리보기 준비 중"}</div>`;
    c.innerHTML = `<div class="thumb">${th}</div><div class="body"><div class="name">${esc(t.name)}</div><div class="sum">${esc(t.summary)}</div>
      <div class="meta"><span class="tag">${esc(t.category)}</span><span class="tag st-${esc(t.status)}">${esc(t.status)}</span>${t.component ? `<span class="tag">${esc(t.component)}</span>` : ""}${t.params && t.params.length ? `<span class="tag pc">변수 ${t.params.length}</span>` : ""}</div></div>`;
    if (t._hasPreview) { const box = c.querySelector(".thumb"); let v;
      c.onmouseenter = () => { v = document.createElement("video"); v.src = `previews/${t.preview}.mp4`; v.muted = true; v.loop = true; v.playsInline = true; v.autoplay = true; box.innerHTML = ""; box.appendChild(v); };
      c.onmouseleave = () => { box.innerHTML = `<img src="previews/${t.preview}.jpg" alt="">`; }; }
    c.onclick = () => open_(t); g.appendChild(c); });
}
function open_(t){
  const src = (t.sources || []).map(s => `<li>${esc(s.ref)} ${s.video ? `<a href="${esc(s.video)}${s.time && /^\d/.test(s.time) ? "" : ""}" target="_blank" rel="noopener">${esc(s.video)}</a>` : ""} ${esc(s.time || "")} ${esc(s.note || "")}</li>`).join("");
  const use = t.component ? `import { ${t.component} } from "${(t.file || "").replace(/^video\/src\//, "./").replace(/\.tsx$/, "")}";` : "";
  document.getElementById("dv").innerHTML = `${t._hasPreview ? `<video src="previews/${t.preview}.mp4" controls autoplay loop muted playsinline></video>` : ""}
    <div class="in"><button class="x" onclick="dlg.close()" aria-label="닫기">×</button><h2>${esc(t.name)}</h2>
    <div class="meta"><span class="tag">${esc(t.category)}</span><span class="tag st-${esc(t.status)}">${esc(t.status)}</span>${(t.tags || []).map(x => `<span class="tag">${esc(x)}</span>`).join("")}</div>
    <p>${esc(t.summary)}</p><div class="k">측정 사양</div><pre>${esc(t.spec || "—")}</pre>
    ${(t.params && t.params.length) ? `<div class="k">변수 ${t.params.length}개 — 바꾸면 움직임·길이·크기가 달라집니다</div><table class="pt"><tr><th>이름</th><th>키</th><th>기본</th><th>범위</th></tr>${t.params.map(v => `<tr><td><span class="g g-${esc(v.group)}">${({timing:"시간",motion:"움직임",size:"크기",look:"모양"})[v.group] || ""}</span> ${esc(v.label)}</td><td><code>${esc(v.key)}</code></td><td>${v.type === "color" ? `<span class="sw" style="background:${esc(v.default)}"></span>` : ""}${esc(v.default)}${esc(v.unit || "")}</td><td>${v.min !== undefined ? esc(v.min) + " ~ " + esc(v.max) : (v.options || []).join(" / ")}</td></tr>`).join("")}</table>
    <div class="k">직접 조절</div><pre>cd motion/video && npx remotion studio\n→ 왼쪽 params 폴더의 Param-${esc(t.preview)} 를 열면 오른쪽에 슬라이더
코드에서: &lt;${esc(t.component)} ... p={{ ${esc(t.params[0].key)}: ${esc(JSON.stringify(t.params[0].default))} }} /&gt;</pre>` : ""}
    ${t.component ? `<div class="k">컴포넌트</div><pre>${esc(use)}\n// 파일: ${esc(t.file)}   미리보기 id: ${esc(t.preview || "—")}</pre>` : ""}
    ${src ? `<div class="k">레퍼런스</div><ul>${src}</ul>` : ""}</div>`;
  dlg.showModal();
}
const dlg = document.getElementById("dlg"); dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
document.getElementById("q").addEventListener("input", e => { q = e.target.value; render(); });
render();
</script></body></html>"""

(D / "index.html").write_text(HTML.replace("__DATA__", json.dumps(tech, ensure_ascii=False)), encoding="utf-8")
print("index.html", len(tech), "개,", sum(t["_hasPreview"] for t in tech), "개 미리보기")
