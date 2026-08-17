# P14 — 씬 레이아웃 타입: v3 구성(차트·타이포·아이템)을 AE 셰이프/텍스트로 Implementation Plan

**Goal:** 씬 분해가 모든 씬을 이미지로 만들지 않고 **레이아웃 타입**을 부여 — v3 실사용 상위 6종을 AE에서 **JSON→결정적 렌더**(셰이프·텍스트 레이어). Remotion 없이 같은 구성 철학 적용.

**v1 레이아웃(v3 실측 분포 기준):**
| layout | 내용 | AE 렌더 |
|---|---|---|
| `cinematic` | 이미지 씬(기존 경로) | 기존 이미지+레이어 파이프라인 |
| `headline_only` | 큰 타이포 한 줄(+서브) | 텍스트 레이어 |
| `items_list` | 불릿 목록(제목+3~5항목) | 텍스트 스택 + 액센트 바 |
| `metric_spotlight` | 큰 숫자 1개+라벨(counter 통합) | 대형 숫자 텍스트 + 라벨 |
| `bar` | 막대 차트(3~6개) | 셰이프 사각형 + 라벨 |
| `quote` | 인용문+출처(quote_portrait 단순화) | 따옴표 장식 + 텍스트 |

**Architecture:** scene-decompose 스키마에 `layout`(enum, 기본 cinematic) + 플랫 데이터 필드(`headline`,`sub`,`items[]`,`value`,`label`,`chart{labels,values,unit}`,`quote{text,who}`) 추가(v3 플랫 스키마 규칙). manifest가 layout/data 통과 + 이미지 없는 씬도 컴프 생성(1920×1080). `data/artstyle/ae_tokens.json`(semoji 토큰: accent #4A90D9, 폰트 SB어그로체/카페24써라운드, 다크 bg #23262b 계열). `build_scene.jsx`에 레이아웃 빌더 5종 — 텍스트는 `comp.layers.addText`, 막대는 셰이프 레이어. 시트는 이미지 없는 레이아웃 씬에 (없음) 대신 **레이아웃 뱃지** 표시.

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`. jsx는 문자열 검사.

**현재 사실(확인됨):**
- `skills/scene-decompose/` 에 skill.json + SKILL.md + schema(파일명은 skill.json의 `schema` 키 — 확인 후 그 파일 수정). 현 씬 필드: sceneNumber/title/narration/characters/visual_summary/image_prompt/duration_estimate_sec.
- scenes.load_scenes는 미지 필드 보존(통과). manifest 씬: ae_comp_name/width/height/image/layers/audio/subtitle/duration(+camera/moves).
- jsx akBuildScene: 씬 루프에서 layers/image → 자막 → 오디오. JSON.parse 폴리필. `addLayerObj`, `applyMoves`, `addBobNull`, `applyCamera` 존재.
- 시트 renderRow: `media = s._image ? <img> : (없음)`.
- AE 텍스트: `comp.layers.addText(str)` 후 `Source Text` TextDocument(fontSize/fillColor/font/justification, tracking). 셰이프: `comp.layers.addShape()` → Contents에 ADBE Vector Group → Rect/Fill. ExtendScript ES3.
- semoji 토큰: accent #4A90D9, body 'SB 어그로체'(PS명 SBAggroOTF-M 추정), headline '카페24 써라운드'(Cafe24Ssurround). 폰트 미설치 시 AE 기본 폰트 — try/catch.

---

## Task 1: 스키마 + 디자인 토큰

**Files:** Modify `skills/scene-decompose/`(skill schema·SKILL.md); Create `data/artstyle/ae_tokens.json`; Test `tests/test_scene_layouts.py`

- [ ] **Step 1: ae_tokens.json**:

```json
{
  "colors": {
    "bg": "#23262b", "bgRgb": [35, 38, 43],
    "text": "#E8EAED", "textRgb": [232, 234, 237],
    "muted": "#9AA0A6", "mutedRgb": [154, 160, 166],
    "accent": "#4A90D9", "accentRgb": [74, 144, 217],
    "accentSoftRgb": [74, 144, 217]
  },
  "fonts": {
    "headline": "Cafe24Ssurround", "body": "SBAggroM", "number": "Cafe24Ssurround",
    "fallback": "AppleSDGothicNeo-Bold"
  },
  "type": { "headline": 110, "sub": 48, "item": 52, "metric": 220, "metricLabel": 54,
            "quote": 64, "quoteWho": 40, "barLabel": 36, "barValue": 40 }
}
```

- [ ] **Step 2: scene-decompose 스키마 확장** — 씬 items에 추가(전부 nullable·required 포함 — codex strict 모드 규칙):
  - `layout`: enum ["cinematic","headline_only","items_list","metric_spotlight","bar","quote"]
  - `headline`: string|null, `sub`: string|null
  - `items`: array(string)|null
  - `value`: string|null(예 "1,200만"), `label`: string|null
  - `chart`: object|null {labels: array(string), values: array(number), unit: string|null} (object도 required 전 키+nullable)
  - `quote_text`: string|null, `quote_who`: string|null (중첩 회피 — 플랫)
- [ ] **Step 3: SKILL.md 지침 추가**:

```
## 레이아웃 선택(씬마다)
- 모든 씬을 이미지(cinematic)로 만들지 마라. 내용에 맞는 레이아웃을 고른다:
  - cinematic: 장면 묘사가 필요한 스토리텔링 씬(이미지 생성) — image_prompt 필수
  - headline_only: 한 문장 선언/전환(헤드라인 타이포) — headline 필수, sub 선택
  - items_list: 나열(3~5개) — headline+items 필수
  - metric_spotlight: 핵심 수치 강조 — value+label 필수
  - bar: 수치 비교(3~6개) — headline+chart{labels,values,unit} 필수
  - quote: 인용 — quote_text+quote_who 필수
- 비율 감각: 이미지 씬 40~60%, 나머지를 내용에 맞게 섞어라. 연속 2씬 같은 비-이미지 레이아웃 지양.
- cinematic이 아닌 씬은 image_prompt를 빈 문자열로.
```

- [ ] **Step 4: 테스트**(`tests/test_scene_layouts.py`) — 스키마 JSON 유효 + layout enum 6종 + ae_tokens 키 존재 + (스키마가 codex strict 규칙 충족: items의 required에 신규 필드 포함 확인).
- [ ] **커밋** `feat(layout): 씬 레이아웃 6종 스키마 + AE 디자인 토큰(semoji)`

---

## Task 2: manifest 통과 + 비이미지 씬 컴프

**Files:** Modify `backend/manifest.py`; Test `tests/test_manifest.py`

- [ ] manifest 씬 dict에 추가: `"layout": s.get("layout") or "cinematic"`, 그리고 데이터 필드 통과: headline/sub/items/value/label/chart/quote_text/quote_who (None 아닌 것만).
- [ ] 비이미지 레이아웃 씬: `_image` 없어도 정상 — width/height는 기본 1920×1080(기존 W,H), `image: None`, `layers: []`. `tokens` 경로도 매니페스트 루트에 추가: `"ae_tokens": str(data/artstyle/ae_tokens.json 절대경로)` (jsx가 읽음).
- [ ] 테스트: layout/데이터 통과, cinematic 기본값, ae_tokens 경로 포함.
- [ ] **커밋** `feat(manifest): layout·데이터 필드 통과 + ae_tokens 경로`

---

## Task 3: jsx 레이아웃 빌더 5종

**Files:** Modify `cep/com.autokairos.pd/jsx/build_scene.jsx`; Test `tests/test_panel_structure.py`

- [ ] **토큰 로드**(akBuildScene 시작부, manifest 파싱 후):

```javascript
        var TK = { colors: { bgRgb: [35,38,43], textRgb: [232,234,237], mutedRgb: [154,160,166], accentRgb: [74,144,217] },
                   fonts: { headline: "", body: "", number: "" },
                   type: { headline: 110, sub: 48, item: 52, metric: 220, metricLabel: 54, quote: 64, quoteWho: 40, barLabel: 36, barValue: 40 } };
        try {
            if (m.ae_tokens) { var tf = new File(m.ae_tokens); if (tf.exists) { tf.open("r"); var tr = tf.read(); tf.close();
                var tj = (typeof JSON === "object" && JSON.parse) ? JSON.parse(tr) : eval("(" + tr + ")");
                if (tj.colors) TK.colors = tj.colors; if (tj.fonts) TK.fonts = tj.fonts; if (tj.type) TK.type = tj.type; } }
        } catch (e) { }
        function C(rgb) { return [rgb[0] / 255, rgb[1] / 255, rgb[2] / 255]; }
```

- [ ] **헬퍼**(addLayerObj 인근):

```javascript
    // 배경 솔리드 + 텍스트/셰이프 빌더 — 레이아웃 씬(JSON→결정적 렌더)
    function addBgSolid(comp, W, H, rgb) {
        return comp.layers.addSolid([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255], "bg", W, H, 1.0);
    }
    function addTextL(comp, str, opts) {   // opts: {x,y,size,rgb,font,just,track}
        var tl = comp.layers.addText(String(str));
        var td = tl.property("Source Text").value;
        td.fontSize = opts.size; td.fillColor = [opts.rgb[0] / 255, opts.rgb[1] / 255, opts.rgb[2] / 255];
        try { if (opts.font) td.font = opts.font; } catch (e) { }
        try { td.justification = opts.just || ParagraphJustification.CENTER_JUSTIFY; } catch (e) { }
        try { if (opts.track) td.tracking = opts.track; } catch (e) { }
        tl.property("Source Text").setValue(td);
        tl.property("Position").setValue([opts.x, opts.y]);
        return tl;
    }
    function addRectL(comp, name, x, y, w, h, rgb) {   // 좌상단 기준 사각형 셰이프
        var sl = comp.layers.addShape(); sl.name = name;
        var grp = sl.property("Contents").addProperty("ADBE Vector Group");
        var rect = grp.property("Contents").addProperty("ADBE Vector Shape - Rect");
        rect.property("Size").setValue([w, h]);
        var fill = grp.property("Contents").addProperty("ADBE Vector Graphic - Fill");
        fill.property("Color").setValue([rgb[0] / 255, rgb[1] / 255, rgb[2] / 255]);
        sl.property("Position").setValue([x + w / 2, y + h / 2]);
        return sl;
    }
```

- [ ] **레이아웃 렌더러**:

```javascript
    function renderLayout(comp, s, W, H) {
        var c = TK.colors, t = TK.type;
        addBgSolid(comp, W, H, c.bgRgb);
        if (s.layout === "headline_only") {
            addTextL(comp, s.headline || "", { x: W / 2, y: H * 0.5, size: t.headline, rgb: c.textRgb, font: TK.fonts.headline });
            if (s.sub) addTextL(comp, s.sub, { x: W / 2, y: H * 0.62, size: t.sub, rgb: c.mutedRgb, font: TK.fonts.body });
        } else if (s.layout === "items_list") {
            addTextL(comp, s.headline || "", { x: W / 2, y: H * 0.18, size: t.sub * 1.4, rgb: c.textRgb, font: TK.fonts.headline });
            var items = s.items || [], y0 = H * 0.34, gap = Math.min(110, (H * 0.55) / Math.max(1, items.length));
            for (var ii = 0; ii < items.length; ii++) {
                addRectL(comp, "bullet" + ii, W * 0.16, y0 + ii * gap - 14, 14, 42, c.accentRgb);
                var il2 = addTextL(comp, items[ii], { x: W * 0.2, y: y0 + ii * gap + t.item * 0.35, size: t.item, rgb: c.textRgb, font: TK.fonts.body, just: ParagraphJustification.LEFT_JUSTIFY });
                var op = il2.property("Opacity");                     // 순차 등장
                op.setValueAtTime(0.2 + ii * 0.35, 0); op.setValueAtTime(0.5 + ii * 0.35, 100);
            }
        } else if (s.layout === "metric_spotlight") {
            addTextL(comp, s.value || "", { x: W / 2, y: H * 0.48, size: t.metric, rgb: c.accentRgb, font: TK.fonts.number });
            addTextL(comp, s.label || "", { x: W / 2, y: H * 0.66, size: t.metricLabel, rgb: c.textRgb, font: TK.fonts.body });
        } else if (s.layout === "bar") {
            addTextL(comp, s.headline || "", { x: W / 2, y: H * 0.14, size: t.sub * 1.3, rgb: c.textRgb, font: TK.fonts.headline });
            var ch = s.chart || {}, labels = ch.labels || [], vals = ch.values || [];
            var n = Math.max(1, vals.length), maxV = 0;
            for (var vi = 0; vi < vals.length; vi++) if (vals[vi] > maxV) maxV = vals[vi];
            var areaW = W * 0.7, baseY = H * 0.78, maxH = H * 0.45;
            var bw = Math.min(140, areaW / n * 0.55), gap2 = areaW / n;
            for (var bi = 0; bi < n; bi++) {
                var bh = maxV ? (vals[bi] / maxV) * maxH : 0;
                var bx = W * 0.15 + gap2 * bi + (gap2 - bw) / 2;
                var bar = addRectL(comp, "bar" + bi, bx, baseY - bh, bw, bh, c.accentRgb);
                var sc2 = bar.property("Scale");                       // 자라나는 막대
                bar.property("Anchor Point").setValue([0, bh / 2]);    // 하단 고정 성장 위해 앵커 보정
                bar.property("Position").setValue([bx, baseY - bh / 2]);
                sc2.setValueAtTime(0.2 + bi * 0.15, [100, 0]); sc2.setValueAtTime(0.7 + bi * 0.15, [100, 100]);
                addTextL(comp, labels[bi] || "", { x: bx + bw / 2, y: baseY + 50, size: t.barLabel, rgb: c.mutedRgb, font: TK.fonts.body });
                addTextL(comp, String(vals[bi]) + (ch.unit || ""), { x: bx + bw / 2, y: baseY - bh - 24, size: t.barValue, rgb: c.textRgb, font: TK.fonts.body });
            }
        } else if (s.layout === "quote") {
            addTextL(comp, "“", { x: W * 0.2, y: H * 0.3, size: t.headline * 1.6, rgb: c.accentRgb, font: TK.fonts.headline });
            addTextL(comp, s.quote_text || "", { x: W / 2, y: H * 0.5, size: t.quote, rgb: c.textRgb, font: TK.fonts.headline });
            addTextL(comp, "— " + (s.quote_who || ""), { x: W / 2, y: H * 0.68, size: t.quoteWho, rgb: c.mutedRgb, font: TK.fonts.body });
        }
    }
```

(주의: bar의 앵커/포지션 — addRectL이 중앙 포지션을 잡으므로 성장 애니메이션 위해 위처럼 보정. 구현 시 단순화 가능: 앵커를 셰이프 하단으로 두고 Scale Y 0→100.)
- [ ] **씬 루프 분기** — 레이어/이미지 처리 앞에:

```javascript
            var isLayoutScene = s.layout && s.layout !== "cinematic";
            if (isLayoutScene) {
                renderLayout(comp, s, cw, ch);
            } else if (s.layers && s.layers.length) { ... 기존 ... }
```

(자막·오디오·Final 배치는 공통 유지.)
- [ ] 구조 테스트: `function renderLayout`·5종 분기 문자열·`ae_tokens` 존재.
- [ ] **커밋** `feat(jsx): 레이아웃 렌더러 5종 — 셰이프/텍스트 결정적 렌더(+막대 성장·아이템 순차 등장)`

---

## Task 4: 시트 표시 + 통합 검증

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`; Test 구조 + 전체

- [ ] renderRow: 이미지 없고 `s.layout && s.layout !== "cinematic"`이면 `(없음)` 대신 레이아웃 뱃지:

```javascript
  var media = s._image
    ? '<img class="main" src="file://' + dir + '/' + s._image + '">'
    : (s.layout && s.layout !== "cinematic"
       ? '<div class="layout-badge">' + _esc(s.layout) + '</div>'
       : '<div style="color:#666;font-size:11px">(없음)</div>');
```

CSS: `.col-img .layout-badge { padding:24px 8px; text-align:center; background:#2c2f36; border:1px dashed #4A90D9; border-radius:6px; color:#7ab0ff; font-size:12px; }`
- [ ] 전체 테스트 멱등 2회 + JS 7파일 node 문법.
- [ ] 라이브: tesla 복사본에 레이아웃 씬 수동 추가(scenes.json에 headline_only·bar 씬 2개 삽입) → manifest 빌드 → layout/데이터/ae_tokens 포함 확인 → 복사본 제거. (AE 렌더 확인은 사용자 몫 — 보고에 명시.)
- [ ] **커밋** `feat(panel): 레이아웃 씬 뱃지 + 검증`

---

## Self-Review

- **v3 철학 이식**: 플랫 스키마(중첩 금지), 디자인 토큰 단일 소스(ae_tokens.json), 레이아웃 enum — v3 규칙과 정렬.
- **결정적 렌더**: 레이아웃 씬은 LLM 없이 JSON→jsx. 막대 성장·아이템 순차 등장은 고정 패턴(모션 규칙과 충돌 없음 — 레이아웃 씬은 레이어/캐릭터 없음).
- **하위호환**: layout 미지정=cinematic(기존 경로 그대로). 기존 프로젝트 무영향.
- **codex strict**: 스키마 신규 필드 전부 required+nullable.
- **한계(정직)**: 폰트는 설치돼 있어야(미설치 시 AE 기본 폰트 폴백 — try/catch). pie/timeline/map 등 나머지 타입은 v2. 자막 오버레이는 기존 그대로(레이아웃 씬과 겹침 가능 — headline 씬은 내레이션 자막과 중복될 수 있어 SKILL.md에서 headline은 내레이션 요지와 다르게 쓰도록 지시 권장). 씬 분해 재실행 전까지 기존 씬엔 layout 없음(=cinematic).
