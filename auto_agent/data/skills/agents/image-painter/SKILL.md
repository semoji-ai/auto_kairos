---
name: image-painter
description: FAL.ai 이미지 생성 에이전트. source=generate 씬의 캐릭터 분석→캐릭터 생성→씬 이미지 생성.
---

# Image Painter Agent

`scene_specs.json`에서 `imageAsset.source === "generate"` 씬의 이미지를 FAL.ai로 생성합니다.

## 워크플로우

### Phase A: 캐릭터 분석 (선행 작업)

`scene_specs.json`에서 `imageAsset.source === "generate"` 씬을 분석하여 2씬 이상 등장하는 캐릭터를 식별하고 `character_plan.json`을 생성합니다.

- character-planner 스킬 규칙에 따라 변이(Variant) 분석 및 생성 프롬프트 작성
- 캐릭터가 없거나 모든 캐릭터가 1회만 등장하는 경우 Phase A 생략 가능

### Phase B: 캐릭터 이미지 생성

`character_plan.json`에 정의된 캐릭터를 먼저 생성합니다.

```bash
python3 -m auto_agent.tools.image_generate character \
  --prompt "캐릭터 묘사 (영어)" \
  --style "art_style.json" \
  --output "characters/캐릭터명.png" \
  --aspect-ratio 1:1
```

실존 인물은 `--person-photo` 옵션으로 참조 사진 첨부:
```bash
python3 -m auto_agent.tools.image_generate character \
  --prompt "캐릭터 묘사 (영어)" \
  --style "art_style.json" \
  --output "characters/캐릭터명.png" \
  --person-photo "ref_photos/person.jpg" \
  --aspect-ratio 1:1
```

### Phase C: 씬 이미지 생성

씬별로 이미지를 생성합니다. **반드시 Bash 도구로 직접 호출하세요.**

#### 기본 씬 생성 (캐릭터 없음):
```bash
python3 -m auto_agent.tools.image_generate scene \
  --prompt "장면 묘사 (영어)" \
  --output "images/scene_NNN_gen_01.png" \
  --style "art_style.json"
```

#### 캐릭터 포함 씬:
```bash
python3 -m auto_agent.tools.image_generate scene \
  --prompt "장면 묘사 (영어)" \
  --output "images/scene_NNN_gen_01.png" \
  --style "art_style.json" \
  --characters "characters/char_a.png,characters/char_b.png" \
  --characters-info "김대리(손으로 테이블 치며 - image1), 박과장(고개 숙이며 - image2)"
```

#### 2D 플랫 스타일 씬 (세모지 등):
```bash
python3 -m auto_agent.tools.image_generate scene-flat \
  --prompt "장면 묘사 (영어)" \
  --output "images/scene_NNN_gen_01.png" \
  --style "art_style.json" \
  --characters "characters/a.png,characters/b.png" \
  --background "배경 설명"
```

#### 시각화 배경:
```bash
python3 -m auto_agent.tools.image_generate viz-background \
  --title "차트 제목" --type "bar" --context "맥락" \
  --output "images/scene_NNN_gen_01.png" \
  --style "art_style.json"
```

## 프롬프트 작성 규칙

1. `art_style.json`의 `scene_style_description`을 프롬프트 맨 앞에 배치
2. 장면 묘사는 **영어**로 작성
3. `image_assets.json`의 `full_prompt` 필드가 있으면 참고하되, 영어로 변환
4. 카메라 앵글, 배경, 조명 정보를 구체적으로 포함

## 파일명 규칙

**반드시** `scene_NNN_gen_NN` 형식:
- `images/scene_001_gen_01.png`
- `images/scene_002_gen_01.png`
- 재생성 시: `images/scene_001_gen_02.png` (기존 파일 삭제 금지)

## 결과 저장

### 1. scene_specs.json 업데이트
각 씬의 `imageAsset.src`에 생성된 이미지 경로 설정:
```json
"imageAsset": {
  "source": "generate",
  "src": "images/scene_001_gen_01.png",
  "placement": "fullscreen"
}
```

### 2. image_assets.json 업데이트
생성 결과를 `image_assets.json`에 반영 (status, src 필드 추가).

## 절대 규칙

1. **NO TEXT**: 모든 이미지에 텍스트, 글자, 숫자, 캡션, 워터마크 절대 금지
2. **아트스타일 필수**: `art_style.json`을 반드시 `--style` 인자로 전달
3. **참조 이미지 포즈 복사 금지**: 얼굴/복장만 참고, 포즈는 장면 묘사에서 결정
4. **카메라 다양성**: 동일 구도 반복 금지, 앵글/샷 사이즈 다양하게
5. **기존 이미지 삭제 금지**: 재생성 시 `_gen_02`, `_gen_03` 등 버전 번호로 생성

## 절대 금지

- **Python 스크립트 작성 금지** — .py 파일을 Write로 작성하고 Bash로 실행하는 방식 금지
- **자동화 스크립트 금지** — 반복문, 배치 처리용 스크립트 작성 금지
- **반드시 Bash 도구로 직접 호출** — 씬 하나씩 `python3 -m auto_agent.tools.image_generate ...` 호출
- 한 번에 하나의 씬만 처리하고, 결과 확인 후 다음 씬 진행
