# auto-agent CLI 매뉴얼

> **경로:** `/Volumes/jleavens/Projects/auto_kairos_v3`  
> **실행:** `python -m auto_agent.cli <command>` 또는 `auto-agent <command>`  
> **소스:** `auto_agent/cli.py`

---

## 핵심 워크플로우 명령어

### TTS 생성 + 자막 동기화
```bash
# TTS 전처리 → 생성 → 자막 동기화 (전체)
auto-agent tts --project <slug>

# 전체 재생성 (기존 파일 무시)
auto-agent tts --project <slug> --force

# TTS만 (자막 스킵)
auto-agent tts --project <slug> --tts-only

# 자막만 (TTS 스킵)
auto-agent tts --project <slug> --subtitle-only

# 병렬 워커 수 조정 (기본 3)
auto-agent tts --project <slug> --workers 5
```

### 파이프라인 실행
```bash
# 전체 파이프라인
auto-agent run --project <slug>

# 특정 스텝부터
auto-agent run --project <slug> --from tts_generation

# 특정 스텝까지만
auto-agent run --project <slug> --until subtitle_sync

# 특정 스텝부터 특정 스텝까지
auto-agent run --project <slug> --from tts_generation --until subtitle_sync

# 한 스텝만
auto-agent run --project <slug> --only manifest_building
```

**파이프라인 스텝 순서:**
```
deep_research_and_synthesis → outline_and_manuscript → duplicate_check
→ data_mapping → fact_check → image_batch → scene_decomposition
→ creative_direction → data_enrichment_and_motion
→ tts_generation → image_asset_sourcing → subtitle_sync
→ tts_verification → data_validation → manifest_building
→ still_capture → qa_pre_render → video_assembly → qa_post_render
```

### 매니페스트 빌드
```bash
# 대시보드 API (권장)
curl -X POST http://localhost:5050/api/p/<slug>/manifest/build

# 직접 실행
python -m auto_agent.scripts.build_manifest --project-id <id> --storage-key <slug>
```

### 스튜디오
```bash
auto-agent studio --project <slug>
# 기본 포트: 3100 (충돌 시 3101, 3102...)
```

---

## 프로젝트 관리

```bash
auto-agent project list          # 프로젝트 목록
auto-agent project create        # 새 프로젝트 (인터랙티브)
auto-agent config get            # 현재 설정 조회
auto-agent config set <key> <val> # 설정 변경
auto-agent assets                # 에셋 목록
auto-agent costs                 # 비용 요약
```

---

## 에셋 관리

```bash
auto-agent style list            # 아트스타일 목록
auto-agent voice list            # 음성 프리셋 목록
auto-agent font list             # 폰트 목록
auto-agent bg start/stop/status/logs  # 백그라운드 파이프라인
```

---

## 동기화

```bash
auto-agent sync --project <slug>  # 로컬 → Supabase
auto-agent pull --project <slug>  # Supabase → 로컬
```

---

## 환경변수 직접 실행 (DB 없이)

DB 조회가 실패할 때 `PROJECT_DIR`로 직접 경로 지정:

```bash
PROJECT_DIR="/Volumes/jleavens/Projects/auto_kairos_v3/output/<폴더명>" \
  python -m auto_agent.scripts.generate_tts

PROJECT_DIR="/Volumes/jleavens/Projects/auto_kairos_v3/output/<폴더명>" \
  python -m auto_agent.scripts.generate_subtitles
```

---

## 슬러그 규칙

- DB에 저장된 슬러그: `포켓몬스터_30주년_브랜드백과사전_1편` (uuid 없음)
- 출력 폴더명: `9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편` (uuid 포함)
- CLI `--project` 인수: **uuid 없는 슬러그** 사용

---

## 자주 쓰는 패턴

```bash
# 오디오 전체 재생성 후 매니페스트 빌드
auto-agent tts --project 포켓몬스터_30주년_브랜드백과사전_1편 --force
curl -X POST http://localhost:5050/api/p/포켓몬스터_30주년_브랜드백과사전_1편/manifest/build

# 씬분할 후 매니페스트만 갱신 (대시보드에서도 가능)
curl -X POST http://localhost:5050/api/p/<slug>/manifest/build
```
