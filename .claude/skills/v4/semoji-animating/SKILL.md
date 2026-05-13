---
name: semoji-animating
description: 4K 씬 이미지를 codex imagegen으로 생성한 뒤 배경+캐릭터 레이어로 분리하고, 캐릭터별 발끝 까딱 + 카메라 무빙으로 Remotion 애니메이션화. 이로미즘/세모지 스타일 씬을 비디오 생성 비용 없이 동영상화하는 파이프라인.
---

# semoji-animating

씬을 비디오 생성 모델 없이 **레이어 분리 + 단순 모션**으로 동영상화한다.

## 흐름

```
[1] 씬 합성 이미지 생성 (codex imagegen, 4K 3840x2160)
        ↓
[2] 레이어 분리 (scene_layer_v2.py)
    - bg.png   : 인물 제거, 환경·구도 보존
    - characters.png : 인물만, 원래 포즈·위치 그대로, magenta chroma-key
    - layers.json : intrinsic_size + placement (좌표계)
        ↓
[3] 캐릭터 컴포넌트 분리 (split_characters.py)
    - connected components → char_NN.png + source_bbox
    - 캐릭터별 다른 bob period·phase
        ↓
[4] Remotion 합성·렌더
    - bg에 카메라 push-in/pan
    - 각 캐릭터 발끝 까딱 (transform-origin: bottom, scaleY sin)
    - TTS 오디오 동기
```

## 산출물

각 씬 디렉토리 `remotion/public/images/scene_NNN_v2/`:

```
background.png       # 4K, 인물 없는 환경
characters.png       # 4K, 인물만 (chroma-key 제거됨)
characters_raw.png   # chroma 전 원본 백업
characters/
  char_00.png        # 컴포넌트별 cropped
  char_01.png
  ...
layers.json          # 좌표·모션 메타
```

## layers.json 스키마

```json
{
  "scene_number": 5,
  "canvas": {"width": 1920, "height": 1080},
  "fps": 30,
  "background": {
    "src": "scene_005_v2/background.png",
    "intrinsic_size": {"width": 3840, "height": 2160},
    "placement": {"x": 0, "y": 0, "width": 1920, "height": 1080},
    "z": 0
  },
  "characters": [
    {
      "name": "char_0",
      "kind": "from_scene_split",
      "src": "scene_005_v2/characters/char_00.png",
      "intrinsic_size": {"width": 719, "height": 1338},
      "source_canvas_size": {"width": 3840, "height": 2160},
      "source_bbox": {"x": 1527, "y": 531, "width": 719, "height": 1338},
      "z": 10,
      "motion": {
        "type": "feet_bob",
        "amplitude_pct": 2,
        "period_s": 1.4,
        "phase_offset_s": 0.0
      }
    }
  ]
}
```

## 도구

- `scripts/scene_layer_v2.py` — 레이어 분리 생성 (codex imagegen 호출)
- `scripts/split_characters.py` — characters.png → 캐릭터별 cropped + bbox 메타
- `scripts/extract_extras.py` — narration 기반 엑스트라 추출 (cast 없는 씬용)
- `projects/{id}/remotion/` — Remotion 합성 (Scene.tsx에서 카메라·bob 적용)

## 사용 (PD)

```bash
# 1. 씬 레이어 분리 (단일 씬)
python3 scripts/scene_layer_v2.py --project f793a99b --scene 5

# 2. 캐릭터 컴포넌트 분리
python3 scripts/split_characters.py --project f793a99b --scenes 5

# 3. Remotion 렌더
cd projects/f793a99b/remotion && npx remotion render Scene005 out/scene_005.mp4
```

## 적용 가능 씬

- `imageAsset.source = generate` 씬만 적용 (이로미즘 일러스트 씬)
- `search` / `provided` (실사진) 씬은 레이어 추출 의미 없음 — 원본 그대로 사용
- `none` 씬은 별도 처리 필요

## 모션 옵션

- **feet_bob** : transform-origin bottom + scaleY 1±amp sin — 발끝 고정 까딱
- **camera push_in / pan** : bg 컨테이너에 transform scale·translate 보간
- **overshoot_scale** : 자산(로고) 발생 효과 — 0→overshoot→1 (Remotion 컴포넌트로 향후 확장)

## 제약

- gpt-image-2 사이즈: 16배수, 총 픽셀 ≤ 8.29M, 비율 ≤ 3:1
- 4K(3840x2160) = max 한도, 이미지당 ~10MB
- chroma-key는 `--key-color #FF00FF --tolerance 40 --soft-matte` (auto-key·despill 사용 금지 — 얼굴 색 손실)

## 의존성

- codex CLI + imagegen skill (`/Users/jleavens_macmini/.codex/skills/.system/imagegen/scripts/`)
- Python: PIL, numpy, openai
- Node: Remotion v4

## v3 환경 주의사항 (이 스킬 전용)

- **아트스타일**: `auto_agent/data/artstyle/styles_v4/` (v4 에서 재설정된 art style 이식본) 우선 사용. v3 의 일반 파이프라인 `styles/` 와는 별개 — 영상 톤을 v4 디자인 결정에 맞춤
  - 로딩 우선순위: `styles_v4/iromism.json` → `styles_v4/quirky_cartoon.json` → `styles/quirky_cartoon.json` (fallback)
- **프로젝트 디렉토리**: 스크립트의 `--project <id>` 인자는 v3 의 `output/<uuid>_<slug>/` 자동 매칭 (NFC/NFD 한글 정규화 포함)
  - 예시: `--project 통조림의_역사`, `--project 96dbc8e9`, `--project 96dbc8e9_통조림의_역사`, 절대경로 모두 OK
- **이미지 생성 호출**: codex CLI 로 imagegen 스킬 실행. v3 의 일반 `image_batch_module` (fal.ai) 과는 별개 경로
