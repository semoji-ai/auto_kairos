# Subtitle Editor Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스튜디오 씬 편집 모달에 자막 패널을 추가해 SRT 블록을 Enter로 분리하고 Backspace로 병합하며 저장하면 .srt 파일에 직접 반영된다.

**Architecture:** 씬 편집 모달 우측에 자막 패널 탭을 추가한다. 백엔드 두 개의 API(`GET /api/p/{slug}/subtitles/{scene_num}`, `POST /api/p/{slug}/subtitles/{scene_num}`)가 SRT 파싱/저장을 담당하고, `timestamps.json` 단어 데이터를 같이 반환해 프론트엔드가 분리 타이밍을 계산한다. 프론트엔드는 순수 JS(React 없음, 기존 `_studio.html` 패턴 유지)로 구현한다.

**Tech Stack:** Python/FastAPI (백엔드 API), 순수 JS (프론트엔드 패널), 기존 `parse_srt` / `format_srt_time` / `parse_srt_time` 함수 재사용

---

## File Structure

| 파일 | 역할 |
|---|---|
| `app.py` | `GET/POST /api/p/{slug}/subtitles/{scene_num}` 2개 엔드포인트 추가 |
| `auto_agent/dashboard/templates/partials/_studio.html` | 편집 모달에 자막 패널 탭 + SubtitleEditor JS 클래스 추가 |

---

### Task 1: 백엔드 — 자막 GET/POST API

**Files:**
- Modify: `app.py` (기존 `/api/p/{slug}/tts/text/{scene_num}` 엔드포인트 아래에 추가)

자막 데이터 구조:
```json
{
  "entries": [
    {"index": 1, "startSec": 0.0, "endSec": 2.1, "text": "자동차가 처음 세상에"},
    {"index": 2, "startSec": 2.1, "endSec": 4.2, "text": "나온 해 아십니까?"}
  ],
  "words": [
    {"word": "자동차가", "start": 0.0, "end": 0.6},
    {"word": "처음", "start": 0.65, "end": 1.0},
    ...
  ]
}
```
`words`는 `timestamps.json`이 있으면 `chars_to_words()` 결과, 없으면 `[]`.

- [ ] **Step 1: GET 엔드포인트 추가**

`app.py`의 `@app.get("/api/p/{slug}/tts/text/{scene_num}")` 블록 바로 아래에 추가:

```python
@app.get("/api/p/{slug}/subtitles/{scene_num}")
async def get_subtitles(slug: str, scene_num: int):
    """씬의 SRT 엔트리 + timestamps.json 단어 데이터 반환."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    srt_path = Path(out_dir) / "subtitles" / f"scene_{scene_num:03d}.srt"
    ts_path = Path(out_dir) / "audio" / f"scene_{scene_num:03d}.timestamps.json"

    entries = []
    if srt_path.exists():
        from auto_agent.scripts.generate_subtitles import parse_srt
        entries = parse_srt(srt_path.read_text(encoding="utf-8"))

    words = []
    if ts_path.exists():
        try:
            sidecar = _json.loads(ts_path.read_text(encoding="utf-8"))
            from auto_agent.scripts.generate_subtitles import chars_to_words
            words = chars_to_words(sidecar)
        except Exception:
            words = []

    return JSONResponse({"entries": entries, "words": words})
```

- [ ] **Step 2: POST 엔드포인트 추가**

바로 아래에 추가:

```python
@app.post("/api/p/{slug}/subtitles/{scene_num}")
async def save_subtitles(request: Request, slug: str, scene_num: int):
    """편집된 SRT 엔트리를 .srt 파일로 저장."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    body = await request.json()
    entries = body.get("entries", [])
    if not entries:
        return JSONResponse({"error": "entries required"}, 400)

    out_dir = project.get("output_dir", "")
    srt_path = Path(out_dir) / "subtitles" / f"scene_{scene_num:03d}.srt"
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    from auto_agent.scripts.generate_subtitles import format_srt_time
    lines = []
    for i, e in enumerate(entries, 1):
        lines.append(str(i))
        lines.append(f"{format_srt_time(e['startSec'])} --> {format_srt_time(e['endSec'])}")
        lines.append(e["text"])
        lines.append("")
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return JSONResponse({"ok": True, "count": len(entries)})
```

- [ ] **Step 3: 수동 테스트**

대시보드 서버 실행 후:
```bash
curl http://localhost:8080/api/p/자동차의_역사/subtitles/1
# → {"entries": [...], "words": [...]} 확인
```

- [ ] **Step 4: 커밋**

```bash
git add app.py
git commit -m "feat: subtitle GET/POST API 추가 (/api/p/{slug}/subtitles/{scene_num})"
```

---

### Task 2: 프론트엔드 — 자막 패널 UI

**Files:**
- Modify: `auto_agent/dashboard/templates/partials/_studio.html`

편집 모달(`edit-modal-body`) 안에 탭을 추가한다. 기존 `scene-editor-root`는 "씬 편집" 탭, 새로 추가되는 `subtitle-panel`은 "자막" 탭.

**자막 패널 동작 규칙:**
- 각 SRT 블록 = `<div class="srt-block">` — `contenteditable="true"`
- 블록 안 텍스트 편집 가능
- `Enter` 키: 커서 위치의 단어 경계에서 블록 분리 (words 배열로 타이밍 계산)
- `Backspace` (블록 첫 글자에서): 앞 블록과 병합 (앞 블록 startSec + 뒷 블록 endSec)
- 저장 버튼: `POST /api/p/{slug}/subtitles/{scene_num}` 호출
- 자막 없음(SRT 미존재): "자막 없음 — TTS 생성 후 자막을 먼저 생성하세요" 안내 메시지

- [ ] **Step 1: 편집 모달에 탭 구조 추가**

`_studio.html`의 `.edit-modal-body` 내부를 교체:

```html
<!-- 기존 -->
<div class="edit-modal-body">
  <div id="scene-editor-root" class="scene-editor-root"></div>
</div>

<!-- 변경 후 -->
<div class="edit-modal-body">
  <div class="edit-modal-tabs">
    <button class="edit-tab active" data-tab="scene">씬 편집</button>
    <button class="edit-tab" data-tab="subtitle">자막</button>
  </div>
  <div class="edit-tab-content" id="tab-scene">
    <div id="scene-editor-root" class="scene-editor-root"></div>
  </div>
  <div class="edit-tab-content" id="tab-subtitle" style="display:none;">
    <div id="subtitle-panel" class="subtitle-panel"></div>
  </div>
</div>
```

- [ ] **Step 2: 탭 스타일 추가**

`_studio.html`의 `<style>` 블록 안에 추가:

```css
/* ── 편집 모달 탭 ── */
.edit-modal-tabs {
  display: flex; gap: 4px; padding: 8px 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.08); flex-shrink: 0;
}
.edit-tab {
  background: none; border: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; padding: 4px 12px 8px;
  cursor: pointer; border-bottom: 2px solid transparent; transition: color 0.15s;
}
.edit-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.edit-tab:hover:not(.active) { color: var(--text); }

/* ── 자막 패널 ── */
.subtitle-panel {
  display: flex; flex-direction: column; height: 100%;
  padding: 12px; gap: 8px; overflow-y: auto; box-sizing: border-box;
}
.subtitle-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  flex-shrink: 0;
}
.subtitle-hint { font-size: 11px; color: var(--text-muted); }
.srt-blocks { display: flex; flex-direction: column; gap: 6px; flex: 1; overflow-y: auto; }
.srt-block {
  display: flex; gap: 8px; align-items: flex-start;
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 8px;
  transition: border-color 0.15s;
}
.srt-block:focus-within { border-color: var(--accent); }
.srt-timecode {
  font-size: 10px; color: var(--text-muted); white-space: nowrap;
  font-family: monospace; min-width: 110px; padding-top: 2px;
}
.srt-text {
  flex: 1; font-size: 14px; color: var(--text); outline: none;
  white-space: pre-wrap; word-break: break-all; min-height: 20px;
}
.subtitle-empty { color: var(--text-muted); font-size: 13px; padding: 24px; text-align: center; }
.subtitle-save-ok { color: var(--success); font-size: 11px; }
.subtitle-save-err { color: var(--error); font-size: 11px; }
```

- [ ] **Step 3: SubtitleEditor JS 클래스 추가**

`_studio.html` `<script>` 블록의 `(function() { ... var SLUG = ...` 섹션 앞에 삽입:

```javascript
// ── SubtitleEditor ──────────────────────────────────
var SubtitleEditor = (function() {
  var _slug = '', _sceneNum = 0, _words = [], _entries = [], _panel = null;

  function fmtTime(sec) {
    var h = Math.floor(sec / 3600);
    var m = Math.floor((sec % 3600) / 60);
    var s = Math.floor(sec % 60);
    var ms = Math.round((sec % 1) * 1000);
    return (h < 10 ? '0' : '') + h + ':' +
           (m < 10 ? '0' : '') + m + ':' +
           (s < 10 ? '0' : '') + s + ',' +
           (ms < 100 ? (ms < 10 ? '00' : '0') : '') + ms;
  }

  // 커서 위치(글자 offset)를 words 배열 기준으로 가장 가까운 단어 경계로 매핑
  // → 그 경계의 {endSec, nextStartSec} 반환
  function findSplitTiming(blockText, cursorOffset, blockStartSec, blockEndSec) {
    // words 배열에서 이 블록에 해당하는 단어들을 찾음 (텍스트 매칭)
    var blockWords = _words.filter(function(w) {
      return w.start >= blockStartSec - 0.01 && w.end <= blockEndSec + 0.01;
    });
    if (!blockWords.length) {
      // fallback: 글자 수 비례로 시간 분할
      var ratio = cursorOffset / (blockText.length || 1);
      var splitSec = blockStartSec + (blockEndSec - blockStartSec) * ratio;
      return { firstEnd: Math.round(splitSec * 1000) / 1000, secondStart: Math.round(splitSec * 1000) / 1000 };
    }
    // 커서 앞 텍스트 길이로 단어 경계 찾기
    var textBefore = blockText.substring(0, cursorOffset).trim();
    var accumulated = '';
    var bestEnd = blockStartSec;
    for (var i = 0; i < blockWords.length; i++) {
      accumulated += (accumulated ? ' ' : '') + blockWords[i].word;
      if (accumulated.length >= textBefore.length) {
        bestEnd = blockWords[i].end;
        var nextStart = i + 1 < blockWords.length ? blockWords[i + 1].start : blockWords[i].end;
        return { firstEnd: Math.round(bestEnd * 1000) / 1000, secondStart: Math.round(nextStart * 1000) / 1000 };
      }
      bestEnd = blockWords[i].end;
    }
    return { firstEnd: blockEndSec, secondStart: blockEndSec };
  }

  function renderBlocks() {
    var blocksEl = _panel.querySelector('.srt-blocks');
    if (!blocksEl) return;
    blocksEl.innerHTML = '';
    if (!_entries.length) {
      blocksEl.innerHTML = '<div class="subtitle-empty">자막 없음 — TTS 생성 후 자막을 먼저 생성하세요.</div>';
      return;
    }
    _entries.forEach(function(entry, idx) {
      var block = document.createElement('div');
      block.className = 'srt-block';
      block.dataset.idx = idx;

      var tc = document.createElement('div');
      tc.className = 'srt-timecode';
      tc.textContent = fmtTime(entry.startSec) + '\n→ ' + fmtTime(entry.endSec);

      var txt = document.createElement('div');
      txt.className = 'srt-text';
      txt.contentEditable = 'true';
      txt.spellcheck = false;
      txt.textContent = entry.text;

      // 텍스트 변경 → entries 동기화
      txt.addEventListener('input', function() {
        _entries[idx].text = txt.textContent || '';
      });

      // Enter → 분리
      txt.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter') return;
        e.preventDefault();
        var sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;
        var range = sel.getRangeAt(0);
        var preRange = document.createRange();
        preRange.setStart(txt, 0);
        preRange.setEnd(range.startContainer, range.startOffset);
        var cursorOffset = preRange.toString().length;

        var entry = _entries[idx];
        var timing = findSplitTiming(entry.text, cursorOffset, entry.startSec, entry.endSec);
        var textBefore = entry.text.substring(0, cursorOffset).trim();
        var textAfter = entry.text.substring(cursorOffset).trim();
        if (!textBefore || !textAfter) return; // 양쪽 텍스트 있어야 분리

        var newEntry = { index: 0, startSec: timing.secondStart, endSec: entry.endSec, text: textAfter };
        _entries[idx] = { index: 0, startSec: entry.startSec, endSec: timing.firstEnd, text: textBefore };
        _entries.splice(idx + 1, 0, newEntry);
        // index 재번호
        _entries.forEach(function(e, i) { e.index = i + 1; });
        renderBlocks();
        // 커서를 새 블록 첫 글자로 이동
        setTimeout(function() {
          var nextBlock = blocksEl.querySelectorAll('.srt-text')[idx + 1];
          if (nextBlock) { nextBlock.focus(); var r = document.createRange(); r.setStart(nextBlock.firstChild || nextBlock, 0); r.collapse(true); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }
        }, 0);
      });

      // Backspace at start → 병합
      txt.addEventListener('keydown', function(e) {
        if (e.key !== 'Backspace' || idx === 0) return;
        var sel = window.getSelection();
        if (!sel || !sel.rangeCount) return;
        var range = sel.getRangeAt(0);
        var preRange = document.createRange();
        preRange.setStart(txt, 0);
        preRange.setEnd(range.startContainer, range.startOffset);
        if (preRange.toString().length !== 0) return; // 첫 글자 위치가 아님
        e.preventDefault();
        var prev = _entries[idx - 1];
        var curr = _entries[idx];
        prev.text = (prev.text + ' ' + curr.text).trim();
        prev.endSec = curr.endSec;
        _entries.splice(idx, 1);
        _entries.forEach(function(e, i) { e.index = i + 1; });
        renderBlocks();
        // 커서를 이전 블록 병합 위치로
        setTimeout(function() {
          var prevBlock = blocksEl.querySelectorAll('.srt-text')[idx - 1];
          if (prevBlock && prevBlock.firstChild) {
            var r = document.createRange();
            var textNode = prevBlock.firstChild;
            var pos = Math.max(0, (prev.text.length - curr.text.length - 1));
            r.setStart(textNode, Math.min(pos, textNode.length));
            r.collapse(true);
            var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
          }
        }, 0);
      });

      block.appendChild(tc);
      block.appendChild(txt);
      blocksEl.appendChild(block);
    });
  }

  function load(slug, sceneNum, panel) {
    _slug = slug;
    _sceneNum = sceneNum;
    _panel = panel;
    panel.innerHTML = '<div class="subtitle-toolbar"><span class="subtitle-hint">Enter: 분리 | Backspace(줄 처음): 병합</span><button class="btn btn-sm btn-accent" id="btn-subtitle-save">저장</button></div><div class="srt-blocks"><div class="subtitle-empty">로딩 중...</div></div>';

    panel.querySelector('#btn-subtitle-save').addEventListener('click', save);

    fetch('/api/p/' + slug + '/subtitles/' + sceneNum)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        _entries = data.entries || [];
        _words = data.words || [];
        renderBlocks();
      })
      .catch(function() {
        panel.querySelector('.srt-blocks').innerHTML = '<div class="subtitle-empty">로딩 실패</div>';
      });
  }

  function save() {
    var btn = _panel.querySelector('#btn-subtitle-save');
    btn.disabled = true;
    btn.textContent = '저장 중...';
    fetch('/api/p/' + _slug + '/subtitles/' + _sceneNum, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ entries: _entries })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
      btn.disabled = false;
      btn.textContent = '저장';
      if (data.ok) {
        var ok = document.createElement('span');
        ok.className = 'subtitle-save-ok';
        ok.textContent = ' ✓ 저장됨';
        btn.parentNode.appendChild(ok);
        setTimeout(function() { ok.remove(); }, 2000);
      }
    })
    .catch(function() {
      btn.disabled = false;
      btn.textContent = '저장';
    });
  }

  return { load: load };
})();
// ── SubtitleEditor END ──────────────────────────────
```

- [ ] **Step 4: 탭 전환 + openModal에 자막 로드 연동**

기존 `openModal` 함수 안에서 `elOverlay.classList.add('open');` 바로 위에 추가:

```javascript
    // 탭 초기화 (씬 편집 탭 활성)
    _switchTab('scene');
```

`(function() {` 블록 안 초기화 부분(`autoStart(); loadScenes();` 위) 에 추가:

```javascript
  // ── 탭 전환 ──
  var _activeTab = 'scene';
  function _switchTab(name) {
    _activeTab = name;
    document.querySelectorAll('.edit-tab').forEach(function(btn) {
      btn.classList.toggle('active', btn.dataset.tab === name);
    });
    document.getElementById('tab-scene').style.display = name === 'scene' ? '' : 'none';
    document.getElementById('tab-subtitle').style.display = name === 'subtitle' ? '' : 'none';
    if (name === 'subtitle') {
      var sceneNum = (_scenes[_currentIdx] || {}).sceneNumber || (_currentIdx + 1);
      SubtitleEditor.load(SLUG, sceneNum, document.getElementById('subtitle-panel'));
    }
  }
  document.querySelectorAll('.edit-tab').forEach(function(btn) {
    btn.addEventListener('click', function() { _switchTab(btn.dataset.tab); });
  });
```

- [ ] **Step 5: edit-modal-body 높이 보정**

기존 CSS에서:
```css
/* 기존 */
.edit-modal-body { flex: 1; overflow: hidden; }
.edit-modal-body .scene-editor-root { width: 100%; height: 100%; }

/* 변경 */
.edit-modal-body { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.edit-tab-content { flex: 1; overflow: hidden; }
.edit-tab-content#tab-scene { display: flex; flex-direction: column; }
.edit-tab-content#tab-scene .scene-editor-root { width: 100%; height: 100%; }
.subtitle-panel { height: 100%; }
```

- [ ] **Step 6: 수동 테스트**

1. `python -m uvicorn app:app --host 0.0.0.0 --port 8080` 실행
2. 대시보드 → 프로젝트 선택 → 스튜디오 탭
3. 씬 번호 입력 → 편집 버튼 → 모달 열기
4. "자막" 탭 클릭 → 자막 블록 목록 표시 확인
5. 블록 텍스트 중간에 커서 → Enter → 두 블록으로 분리 확인
6. 두 번째 블록 처음에 커서 → Backspace → 병합 확인
7. 저장 버튼 → "✓ 저장됨" 표시 후 `output/{slug}/subtitles/scene_001.srt` 파일 내용 확인

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/dashboard/templates/partials/_studio.html
git commit -m "feat: 자막 에디터 패널 — 씬 편집 모달에 자막 탭 추가 (Enter 분리, Backspace 병합)"
```

---

### Task 3: 저장 후 매니페스트 리빌드 연동

자막을 수정하면 Remotion 매니페스트에도 반영되어야 Studio가 즉시 최신 자막으로 렌더링된다.

**Files:**
- Modify: `app.py` — POST `/api/p/{slug}/subtitles/{scene_num}` 엔드포인트에 매니페스트 리빌드 추가

- [ ] **Step 1: POST 엔드포인트에 매니페스트 리빌드 추가**

`save_subtitles` 함수에서 `srt_path.write_text(...)` 아래에 추가:

```python
    # subtitles.json 갱신 (매니페스트 연동)
    try:
        from auto_agent.scripts.generate_subtitles import parse_srt
        subtitles_json_path = Path(out_dir) / "subtitles.json"
        if subtitles_json_path.exists():
            subtitles_data = _json.loads(subtitles_json_path.read_text(encoding="utf-8"))
        else:
            subtitles_data = {"scenes": []}
        # 해당 씬 업데이트
        scenes_list = subtitles_data.get("scenes", [])
        updated = False
        new_entry = {
            "sceneNumber": scene_num,
            "audioDurationSec": round(entries[-1]["endSec"], 3) if entries else 0,
            "entries": entries,
            "wordCount": sum(len(e["text"].split()) for e in entries),
            "source": "manual_edit",
        }
        for i, s in enumerate(scenes_list):
            if s.get("sceneNumber") == scene_num:
                scenes_list[i] = new_entry
                updated = True
                break
        if not updated:
            scenes_list.append(new_entry)
        subtitles_data["scenes"] = sorted(scenes_list, key=lambda x: x.get("sceneNumber", 0))
        subtitles_json_path.write_text(_json.dumps(subtitles_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] subtitles.json 갱신 실패: {e}", flush=True)

    # 매니페스트 리빌드
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        dir_name = Path(out_dir).name
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        print(f"[WARN] 매니페스트 리빌드 실패: {e}", flush=True)
```

- [ ] **Step 2: 수동 테스트**

1. 자막 패널에서 블록 분리 후 저장
2. `output/{slug}/subtitles.json` 확인 — 해당 씬 entries 업데이트됐는지
3. Studio iframe 새로고침 → Remotion에서 자막이 바뀌었는지 확인

- [ ] **Step 3: 커밋**

```bash
git add app.py
git commit -m "feat: 자막 저장 시 subtitles.json + 매니페스트 자동 리빌드"
git push
```
