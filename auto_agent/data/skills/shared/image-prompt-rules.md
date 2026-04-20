---
name: image-prompt-rules
description: 씬 이미지 프롬프트 생성 규칙. kairos-ai-main에서 이식.
---

# 씬 이미지 프롬프트 규칙

## 1. 핵심 원칙: 스틸컷 이미지

프롬프트는 **비디오의 첫 프레임이 될 스틸컷 이미지**를 생성하기 위한 것.

### 금지 표현 (동작/움직임)
- "~로 전환", "~가 움직이며", "~하는 모습", "~가 펼쳐지며"
- "walking", "running", "transitioning", "revealing"

### 권장 표현 (정적 상태)
- "~한 자세로", "~를 배경으로", "~가 놓인", "~한 표정의", "~가 배치된"
- "standing in front of", "placed on", "positioned at", "facing toward"

## 2. 프롬프트 구성 요소

### 필수 요소
1. **주체**: 인물/캐릭터/피사체 (누가/무엇이 화면 중심인가)
2. **배경**: 장소/시대/환경 (어디서)
3. **구도**: 카메라 앵글/프레임 (어떤 시점으로)
4. **분위기**: 색감/조명/무드 (어떤 느낌으로)

### 선택 요소
- 소품: 캐릭터보다 중요한 설명 요소일 때만
- 텍스트: **절대 금지** (이미지 생성 시 깨짐)
- 지도: **사용 금지** (정확도 낮음)

## 3. 씬 타입별 프롬프트 패턴

| 씬 타입 | 프롬프트 패턴 | 예시 |
|---------|-------------|------|
| 인물 소개 | 인물 + 직업/역할 + 환경 | "Elon Musk in a dark suit, standing in front of a semiconductor factory, dramatic side lighting" |
| 장소/시설 | 시설 + 특징 + 분위기 | "Aerial view of Tesla Gigafactory, massive white building in Nevada desert, golden hour" |
| 사건/역사 | 상황 정적 묘사 + 시대 배경 | "1973 gas station with long queue of cars, empty fuel pumps, worried people waiting" |
| 데이터/개념 | 추상적 시각화 + 색감 | "Abstract visualization of semiconductor chips floating in space, glowing circuits, dark blue background" |
| 감정/분위기 | 감정 표현 + 환경 + 색감 | "Empty stock exchange trading floor, red numbers on screens, dim lighting, tense atmosphere" |

## 4. 아트스타일 연동

프롬프트에 아트스타일 키워드를 직접 넣지 않음.
아트스타일은 FAL.ai 호출 시 reference image + style_prompt로 별도 적용.

프롬프트는 **내용만** 담고, **스타일은 도구가 처리**.

## 5. 언어

프롬프트는 영어 또는 한국어 모두 가능. 이미지 생성 모델이 이해하기 쉬운 언어로 작성.

## 6. 품질 체크리스트

프롬프트 생성 후 확인:
- [ ] 동작/움직임 표현 없음
- [ ] 텍스트 요소 없음
- [ ] 영어로 작성됨
- [ ] 주체 + 배경 + 분위기 포함
- [ ] 16:9 화면에 적합한 구도
- [ ] 아트스타일 키워드 미포함 (도구가 처리)
