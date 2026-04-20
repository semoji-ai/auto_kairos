# 세션 체크포인트 — 포켓몬스터 1편 이미지 재생성

작성일: 2026-04-20

---

## 현재 상황 요약

포켓몬스터 30주년 브랜드백과사전 1편 프로젝트의 이미지 재생성을 준비 중.
**이미지/비디오를 초기화한 상태**로 대화를 종료했고, NAS로 폴더 이전 후 재개 예정.

프로젝트 slug: `9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편`

---

## 이번 세션에서 완료한 작업

### 1. 버그 수정 (즉시 적용됨)
- **카운터 소수점 버그** (`BuildingBlocks.tsx` 양쪽): `Math.round(value)` → target이 소수점이면 `parseFloat(value.toFixed(dp))` 사용. 3.65배 카운터가 4로 튀었다 돌아오는 현상 수정.
- **자막 소수점 분할 버그** (`generate_subtitles.py`): `r'[.!?](?!\d)'` → `r'(?<!\d)[.!?](?!\d)'` + `find_natural_split_points`에서 `before_digit`만으로 소수점 제외. "3.65배가" → "3." / "65배가" 로 분리되던 버그 수정.
- Vite 빌드 양쪽 완료 (thumb + editor config).

### 2. 파이프라인 개선 (다음 프로젝트부터 적용)
- **`runner.py` pre_step 훅 추가** (`step_3b` 시작 전): scene_specs에서 2씬+ 등장 캐릭터를 자동으로 `character_plan.json` draft 생성. LLM이 B-1을 건너뛰더라도 캐릭터 참조 이미지 생성이 보장됨.
- **`SKILL.md` 수정** (assembly-director): "character_plan.json 직접 작성" → "훅이 자동 생성한 draft의 description을 실제 외모 묘사로 보강"으로 변경.

### 3. 이미지 현황 파악
- 생성 이미지 49개, 생성 비디오 23개를 `_backup_v1_images_videos/` 폴더에 백업
- 원본 `images/generated/`, `images/generated_video/` 비움 (0개)
- 백업 위치: `output/9f202fb4_.../  _backup_v1_images_videos/generated/` (49개) + `generated_video/` (23개)
- 매니페스트 재빌드 완료 → 현재 32씬만 이미지 있음 (search 이미지만 남음)

### 4. character_plan.json 자동 생성됨
위치: `output/9f202fb4_.../character_plan.json`

| id | 이름 | 등장씬 |
|----|------|--------|
| 타지리_사토시 | 타지리 사토시(게임프리크 대표, 20대) | 5, 8, 9, 11, 14, 21 |
| 스가모리_켄 | 스가모리 켄(일러스트레이터, 20대) | 9, 14 |
| 피카츄 | 피카츄(포켓몬, 전기 타입) | 32, 44 |
| 노먼_그로스펠드 | 노먼 그로스펠드(4Kids 프로덕션 사장, 40대) | 57, 60 |
| 이와타_사토루 | 이와타 사토루(HAL 연구소 사장, 30대) | 73, 74, 77, 78 |

⚠️ 모든 항목이 `_auto_generated: true` — 실제 외모 묘사로 description 보강 필요 (아래 참고)

---

## 다음 세션에서 해야 할 일

### Step 1. character_plan.json description 보강
각 캐릭터의 `description` 필드를 실제 외모 묘사로 교체.

권장 묘사 방향:
- **타지리 사토시** (20대): 일본 남성, 짧고 약간 부스스한 검정 머리, 동글동글한 얼굴, 안경 없음, 캐주얼 티셔츠(주로 녹색/파란색), 호기심 넘치는 표정. 통통한 체형.
- **스가모리 켄** (20대): 일본 남성, 단정한 검정 머리, 조용하고 집중된 표정, 스케치북/펜을 자주 든 일러스트레이터 느낌.
- **피카츄**: 노란 쥐 포켓몬, 빨간 볼 패치, 번개 모양 꼬리, 큰 검정 눈.
- **노먼 그로스펠드** (40대): 서양 남성, 비즈니스 정장, 중년 외모.
- **이와타 사토루** (30대): 일본 남성, 단정한 검정 머리, 안경 착용, 부드러운 미소, 넥타이 없는 캐주얼 정장.

### Step 2. 캐릭터 레퍼런스 이미지 생성
```bash
cd /path/to/auto_kairos_v3
python3.12 -m auto_agent.modules.image_batch_module \
  --project-dir output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편 \
  --characters-only
```
→ `images/characters/{id}.png` 생성 확인

### Step 3. 씬 이미지 재생성
```bash
python3.12 -m auto_agent.modules.image_batch_module \
  --project-dir output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```
캐릭터 등장 씬(5, 8, 9, 11, 14, 21 등)은 캐릭터 이미지를 참조해서 일관성 있게 생성됨.

### Step 4. 품질 확인 후 문제 씬 재생성
이전 세션에서 문제로 파악된 씬들:
- 씬 017 (반전의 순간): 타지리답지 않은 힙합 스타일 → 재생성
- 씬 019 (예상 밖의 난관): 여성스러운 캐릭터 → 재생성
- 씬 045 (신경세포): 사실적 렌더링 → 3D clay 스타일로 재생성
- 씬 042, 071: 씬 내용 재확인 후 판단

### Step 5. 비디오 생성 (Seedance 1.5 Pro)
백업에 있는 비디오들 중 재활용 가능한 것 확인 후,
새 이미지 기반으로 Freepik Pikaso에서 비디오 재생성.
대상 씬 (이전 작업 완료분): 005, 006, 011, 012, 013, 014, 021, 040, 052, 060, 066, 068, 084
씬 053은 미생성 상태 (추가 필요)

### Step 6. 매니페스트 재빌드 + 스튜디오 확인
```bash
python3.12 -m auto_agent.scripts.build_manifest --local output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

---

## 파일 위치 참고

| 파일 | 경로 |
|------|------|
| scene_specs.json | `output/9f202fb4_.../scene_specs.json` |
| character_plan.json | `output/9f202fb4_.../character_plan.json` |
| image_assets.json | `output/9f202fb4_.../images/image_assets.json` |
| 백업 이미지 | `output/9f202fb4_.../_backup_v1_images_videos/generated/` (49개) |
| 백업 비디오 | `output/9f202fb4_.../_backup_v1_images_videos/generated_video/` (23개) |
| art_style.json | `output/9f202fb4_.../art_style.json` |

---

## NAS 이전 시 주의사항

- `auto_agent/` 코드 폴더와 `output/` 폴더 중 **`output/`만 NAS로 이전** 권장
- 또는 프로젝트 전체를 NAS로 이전 후 심볼릭 링크로 연결
- `.env` 파일의 경로 환경변수 업데이트 필요 (특히 `KAIROS_HOME`, `AUTO_AGENT_DB`)
- `remotion/public/project` 심볼릭 링크가 새 경로를 가리키도록 재설정 필요
- `build_manifest.py --local <새경로>` 실행으로 링크 재생성 가능
