# 세모지 스타일 이미지 생성 규칙 (codex / codex-fleet 용)

다른 머신에서 세모지 스타일로 이미지를 생성할 때 필요한 전부.
**필수 동반 파일: `semoji_base.jpg`** (원본: `auto_kairos_adobe/data/artstyle/semoji_base.jpg`) — 이 파일 없이는 세모지 비율이 재현되지 않는다.

## 핵심 원칙 3가지

1. **`semoji_base.jpg`를 모든 생성에 항상 첨부한다.**
   비율·체형·얼굴 구조는 첨부 이미지가 정한다. 텍스트로 비율(머리 등신, AR 비율 등)을 지정하면
   첨부 이미지와 충돌해 정체성·비율이 깨진다(실측 검증됨). 프롬프트 끝 AR 토큰도 쓰지 않는다.
2. **캐릭터는 새로 그리지 않고 베이스를 리스타일한다.**
   "첨부된 1번 이미지의 캐릭터를 '이름'으로 변경 — 비율·체형·얼굴 구조·그림체·포즈·배경 유지,
   헤어와 의상만 변경: (묘사)" 형태로만 만든다. 이렇게 만든 시트가 이후 씬의 캐릭터 레퍼런스가 된다.
3. **씬에 캐릭터가 나오면 첨부 순서 고정**: 1번 = 캐릭터 시트(정체성 100% 유지),
   마지막 = 세모지 베이스(그림체·색감 기준, 베이스 인물 복사 금지).

## 스타일 블록 (프롬프트 맨 위에 전문 붙여넣기)

```
# semoji 아트스타일 (이미지 생성용)

Modern editorial flat-design illustration. Friendly, approachable, professional clean.

CRITICAL — borderless: NO black ink outlines. Forms defined by flat color shapes meeting. Clean crisp vector edges.

CHARACTER FACE/FEATURES: Eyes = small black dot ovals (no iris). Subtle nose implied with a single soft shadow line. Thick simple eyebrows. Thin curved line mouth (small smile or neutral). Optional soft pink cheek blush.

PROPORTIONS: Defined ONLY by the attached semoji_base reference — do NOT specify a head-count or numeric ratio in text. Always attach semoji_base.jpg and restyle it ("change image-1's character into <name>"); the base supplies the body proportions. Text-specified proportions fight the attached image and break identity/proportion (proven).

COLOR & SHADING: Flat solid block colors. At most ONE soft cell-shadow tone per surface. NO gradients, NO painterly blending, NO 3D, NO photorealistic.

SURFACE — CRITICAL: Perfectly smooth, clean flat fills. Each color region is one uniform solid tone. NO film grain, NO noise, NO speckle, NO paper/canvas/fabric texture, NO halftone or dithering, NO stippling, NO grunge. Digital-clean vector look — fills must be 100% even with zero added surface detail.

BACKGROUND: Single solid muted color (sage green, off-white, dusty rose, cream) or extremely simplified flat shapes. Generous negative space.

PALETTE: Muted warm — dusty pastels, sage green, off-white, dusty blue, soft beige.

EXPLICITLY NOT: Disney/Pixar, painterly, comic-book outlines, 3D, photorealistic, film grain, noise, texture, halftone, grunge. NO text, NO captions, NO logos.
```

> 이 스타일 블록의 NO~ 조항은 세모지 경로(이미지 첨부 리스타일)에서 검증된 원문 그대로 유지한다.
> 공냥 킷의 "네거티브 금지·6섹션·끝 AR 토큰" 규격은 텍스트 단독(t2i) 생성용이라 여기엔 적용하지 않는다.

## 프롬프트 템플릿

### A. 씬 이미지 (캐릭터 있음) — 첨부: 캐릭터시트, semoji_base.jpg (이 순서)

```
<위 스타일 블록 전문>

## 장면
(누가·무엇이·어디서·무엇을. 배경은 단색 뮤트 컬러, 여백 넉넉히.)

[첨부 이미지]
- 1번 캐릭터 시트: 이 인물을 그대로 사용 — 신체 비율·체형·얼굴·헤어·의상을
  100% 동일하게 유지하고, 비율을 바꾸거나 새로 디자인하지 말 것.
- 2번(마지막) 세모지 베이스: 이미지 전체의 그림체·색감 기준(베이스 인물 정체성 복사 금지).

## 생성 지시
image_gen 도구로 위 아트스타일을 적용한 이미지 1장을 생성해 현재 폴더의 images/scene01.png 로 저장.
비율을 텍스트로 새로 지정하지 말 것(비율은 첨부 이미지가 정함). 텍스트 없음. 저장되면 'OK'만 답해.
```

### B. 씬 이미지 (캐릭터 없음) — 첨부: semoji_base.jpg만

[첨부 이미지] 섹션만 교체:

```
[첨부 이미지]
- 첨부 이미지(세모지 베이스)는 그림체·색감 참고용이다 —
  베이스의 인물(사람)은 사용하거나 포함하지 말 것.
```

### C. 캐릭터 시트 생성 — 첨부: semoji_base.jpg만

```
첨부된 1번 이미지의 캐릭터를 '(이름)'(이)라는 캐릭터로 변경해서 새로 그려줘.
- 신체 비율·체형·얼굴 구조·그림체·포즈·배경은 1번 이미지 그대로 유지.
- 헤어와 의상만 변경: (외모 묘사)
비율을 텍스트로 새로 지정하지 말 것. 글자·로고 없음.
image_gen으로 생성 후 현재 폴더의 characters/(이름).png 로 저장. 저장되면 'OK'만 답해.
```

## codex-fleet 배치 실행 규칙

- 잡 1개 = 이미지 1장. `codex exec --sandbox workspace-write` + 잡마다 `-i` 첨부:
  캐릭터 씬은 `-i 캐릭터시트.png -i semoji_base.jpg`, 무캐릭터 씬은 `-i semoji_base.jpg`만.
- **동시 실행 3개 제한** (그 이상은 rate limit로 우수수 실패). 초과분은 큐잉.
- rate limit 감지 시 백오프 재시도: 20초 × 시도횟수, 최대 2회 재시도.
- 성공 판정은 codex의 "OK" 답변이 아니라 **출력 파일 존재 확인**으로 한다.
- 같은 파일명 재생성 시 덮어쓰지 말고 `_v2`, `_v3` 버저닝.
