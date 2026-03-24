---
name: image-generation
description: Use when generating scene images via AI image APIs with art style consistency and prompt engineering
---

# 이미지 생성 스킬 (Image Generation Skill)

> FAL AI nano-banana-pro 모델 기반 이미지 생성 규칙.
> 캐릭터, 씬 생성 시 아트스타일 적용 방법을 정의한다.

---

## 1. 아트스타일 시스템

### 스타일 파일 위치
```
artstyle/styles/
├── semoji.json          + semoji_base.jpg        # 세모지 (2D 플랫, 메인)
├── lego.json            + lego_base.png          # 레고 미니피규어 (포토리얼)
├── quirky_cartoon.json  + quirky_cartoon_base.jpg # 낙서 카툰 (90년대 미국)
└── stickman_cute.json   + stickman_style.jpg     # 스틱맨 (귀여운 손그림)
```

### 스타일 JSON 구조
```json
{
  "name": "스타일 이름",
  "reference_image": "artstyle/styles/xxx_base.jpg",
  "scene_style_description": "프롬프트 앞에 붙는 스타일 설명문",
  "style": { "art_style", "linework", "shapes", "color_palette", "shading", "character_design" },
  "technical": { "no_text": true, "critical_requirements": [...] }
}
```

---

## 2. API 엔드포인트

모든 이미지 생성은 **FAL AI nano-banana-2** 모델 사용.

| 용도 | 엔드포인트 | 조건 |
|------|-----------|------|
| 텍스트→이미지 | `fal-ai/nano-banana-2` | 참조 이미지 없을 때 |
| 캐릭터 생성 | `fal-ai/nano-banana-2/edit` | 스타일 base + 선택적 인물 사진 |
| 씬 생성 | `fal-ai/nano-banana-2/edit` | 캐릭터 ref 또는 스타일 base 이미지 |
| 이미지 편집 | `fal-ai/nano-banana-2/edit` | 소스 이미지 기반 |

### nano-banana-2 파라미터
```python
{
    "prompt": str,           # 최종 프롬프트 (최대 50,000자)
    "image_urls": [str],     # 1~14개 참조 이미지 (data URI 또는 URL)
    "aspect_ratio": str,     # "auto", "1:1", "16:9", "4:3", "9:16" 등
    "resolution": "1K",      # "0.5K", "1K", "2K", "4K"
    "output_format": "png",  # png, jpeg, webp
    "num_images": 1,         # 1~4
    "safety_tolerance": "4", # 1(엄격)~6(느슨)
    "seed": null             # 재현용 시드 (선택)
}
```

### 가격
- 1K: $0.08/장
- 2K: $0.12/장 (1.5x)
- 4K: $0.16/장 (2x)
```

---

## 3. 프롬프트 구성 규칙

### 3.1 프롬프트 구조 (순서 중요)

```
1. scene_style_description (스타일 JSON에서) ← 맨 앞, 톤 세팅
2. style + technical JSON 스펙
3. critical_requirements (있으면)
4. 참조 이미지 스타일 매칭 지시 ← 장면/캐릭터 묘사 전에
5. 실제 장면/캐릭터 묘사
6. 카메라/배경/캐릭터 구조화 정보 (씬 생성 시)
7. 컴포지션 규칙 (씬 생성 시)
8. NO TEXT 규칙 ← 간결하게, 맨 끝에
```

### 3.2 참조 이미지 스타일 매칭 규칙 (절대 규칙)

> **핵심 원칙**: 스타일 참조 지시는 자연스러운 톤으로.
> "MUST exactly copy" 같은 과도한 강제 표현은 모델이 특정 요소(눈 등)를
> 과도하게 덧그리는 부작용을 유발한다.
> → **"Match this style"** 수준의 자연스러운 지시를 사용할 것.

#### 캐릭터 생성 시 → 스타일 base_image를 reference
```
- base_image의 눈 스타일, 선 굵기, 비율, 컬러를 따를 것
- base_image의 특정 인물은 복사하지 않되, 그리기 스타일은 매칭
- ANATOMY_RULES 사용 금지 (카툰 스타일과 충돌)
- NO_TEXT는 끝에 한 줄로 간결하게
```

#### 캐릭터 이미지가 있을 때 (씬 생성) → 캐릭터 이미지만 reference
```
- 스타일 base_image는 제외 (캐릭터 블리드스루 방지)
- 캐릭터 ref의 얼굴/복장만 참고
- 포즈는 절대 복사 금지 → 장면 묘사에서 결정
```

#### 캐릭터 이미지가 없을 때 (씬 생성) → 스타일 base_image를 reference
```
- base_image는 색감/질감/분위기/기법만 참고
- base_image의 캐릭터/인물은 절대 복사 금지
- 캐릭터는 텍스트 묘사로 새로 생성
```

### 3.3 스타일별 프롬프트 프리펜드

| 스타일 | scene_style_description |
|--------|------------------------|
| **세모지** | "The attached image is a 2D flat design with no border in style." |
| **레고** | "LEGO cinema style, characters must be in the form of LEGO head blocks, and elements must be in the form of combinations of existing LEGO blocks." |
| **낙서카툰** | "1990s American comic book style, exaggerated proportions, bold lines." |
| **스틱맨** | "Clean and charming hand-drawn stick figure illustration style with friendly, symmetric characters and positive, lighthearted mood." |

---

## 4. 스타일별 핵심 제약

### 세모지 (SEMOJI)
- **절대 금지**: 3D 렌더링, 외곽선, 그라디언트, 하이라이트, 그림자
- **필수**: 플랫 2D, 단색 채우기, 뮤트 파스텔, 보더리스
- 둥글고 통통한 체형, 점/타원형 눈, 두꺼운 눈썹

### 레고 (LEGO)
- **절대 금지**: 비레고 형태의 캐릭터
- **필수**: 머리는 반드시 레고 헤드블록, 모든 요소는 레고 블록 조합
- 포토리얼 플라스틱 질감, 레고 무비 스타일 3D 렌더링

### 낙서 카툰 (QUIRKY CARTOON)
- **절대 금지**: 매끈한 선, 정교한 디테일
- **필수**: 두껍고 불균일한 검은 선, 의도적 왜곡, 과장된 비율
- 비정상적 안면 배치 (비뚤어진 입, 어긋난 코/귀)

### 스틱맨 (STICKMAN CUTE)
- **절대 금지**: 복잡한 디테일, 그로테스크한 표정, 거친 스크래치
- **필수**: 매끄러운 검은 잉크선, 큰 원형 머리, 대칭적 친근한 표정
- 순백 또는 미니멀 배경, 펠트펜 느낌

---

## 5. CLI 사용법

```bash
# 캐릭터 생성 (스타일 base + 선택적 인물 사진)
python src/tools/image_generate.py character \
  --prompt "30대 한국 남성, 짧은 검은 머리, 회색 정장" \
  --style artstyle/styles/semoji.json \
  --output output/project/characters/character_name.png \
  --person-photo ref_photos/person.jpg \
  --aspect-ratio 1:1

# 씬 생성 (cinematic, 캐릭터 ref 포함)
python src/tools/image_generate.py scene \
  --prompt "두 남자가 회의실에서 심각한 표정으로 대화하는 장면. 창밖으로 도시 야경." \
  --style artstyle/styles/semoji.json \
  --characters output/project/characters/char_a.png,output/project/characters/char_b.png \
  --characters-info "김대리(손으로 테이블 치며 - image1), 박과장(고개 숙이며 - image2)" \
  --background "현대식 사무실 회의실, 밤, 형광등 조명" \
  --camera "미디엄샷, 3/4 앵글" \
  --output output/project/images/scene_001.png

# 씬 생성 (flat staging, 세모지 등 2D 스타일)
python src/tools/image_generate.py scene-flat \
  --prompt "세 명의 캐릭터가 나란히 서서 정면을 바라보는 장면" \
  --style artstyle/styles/semoji.json \
  --characters output/project/characters/a.png,output/project/characters/b.png,output/project/characters/c.png \
  --background "학교 운동장, 맑은 날" \
  --output output/project/images/scene_002.png

# 이미지 편집 (Gemini)
python src/tools/image_generate.py edit \
  --source output/project/images/scene_001.png \
  --prompt "배경을 밤에서 낮으로 변경" \
  --output output/project/images/scene_001_day.png
```

---

## 6. 이미지 생성 워크플로우

### 캐릭터 생성 플로우
```
1. scene_specs.json에서 등장인물 목록 추출
2. 각 캐릭터별:
   a. 프롬프트 작성 (성별, 나이, 외모, 의상, 시대)
   b. 실존 인물이면 참조 사진 준비
   c. generate_character() 호출
   d. 결과를 output/{slug}/characters/캐릭터명.png 저장
```

### 씬 이미지 생성 플로우
```
1. scene_specs.json에서 각 씬 정보 추출
2. 씬별:
   a. 등장 캐릭터 이미지 경로 매핑
   b. 장면 묘사 프롬프트 작성
   c. 2D 플랫 스타일 → generate_scene_flat()
      시네마틱 스타일 → generate_scene()
   d. 결과를 output/{slug}/images/scene_NNN.png 저장
```

---

## 7. 공통 절대 규칙

1. **NO TEXT**: 모든 이미지에 텍스트, 글자, 숫자, 캡션, 워터마크 절대 금지
2. **참조 이미지 포즈 복사 금지**: 얼굴/복장만 참고, 포즈는 장면 묘사에서 결정
3. **스타일 base_image ≠ 캐릭터 소스**: base_image의 인물은 절대 복사하지 않음
4. **카메라 다양성**: 동일 구도 반복 금지, 앵글/샷 사이즈 다양하게
5. **해부학 규칙**: 팔 2개, 다리 2개, 손가락 5개 (리얼리스틱 스타일의 경우)
