# kairos-pd 에이전트 주도 아키텍처 설계

**날짜:** 2026-04-23  
**상태:** 승인됨  
**위치:** `/Volumes/kairos/CC_projects/kairos-pd/`  
**이전 스펙:** `2026-04-20-kairos-pd-design.md` (코어 엔진 구조 — 유효하나 이 문서로 아키텍처 전면 개정)

---

## 개요

kairos-pd는 콘텐츠 제작 전 과정을 **Claude 에이전트가 주도**하는 태스크 기반 파이프라인이다. Python은 SQLite 상태 저장과 CLI 진입점만 담당하고, DAG 판단·서브에이전트 스폰·실패 게이트·결과 검증은 모두 Claude Orchestrator Agent가 수행한다.

superpowers 스킬 시스템이 브레인스토밍→플랜→실행을 스킬 단위로 순차 처리하듯, kairos-pd는 기획 인터뷰→리서치→원고→조립을 태스크 단위로 Claude가 직접 운용한다.

---

## Section 1: 전체 아키텍처

```
kairos-pd new / run
  ↓
Python CLI (cli.py)          — SQLite 접근 + Claude CLI 실행 트리거만
  ↓
Claude Orchestrator Agent    — 장수 단일 세션, 전체 파이프라인 관장
  │
  ├─ [루프 시작]
  │   ├─ read_db()           → 현재 태스크 상태 조회
  │   ├─ pipeline.json 파싱  → 실행 가능한 태스크 판단 (DAG)
  │   ├─ Sub-agent 호출      → 태스크별 SKILL.md 주입
  │   ├─ update_task()       → 결과를 DB에 기록
  │   ├─ 실패 시 게이트 대화  → retry / skip / abort
  │   └─ 전체 완료 시 루프 종료
  │
  └─ [서브에이전트 목록]
      ├─ research.skeleton   → skills/agents/skeleton/SKILL.md
      ├─ research.strategy   → skills/agents/research-strategist/SKILL.md
      ├─ research.ingest     → skills/agents/source-ingest/SKILL.md
      ├─ research.projection → skills/agents/chapter-projection/SKILL.md
      ├─ manuscript.draft    → skills/agents/draft-writer/SKILL.md
      ├─ manuscript.target   → skills/agents/targeted-researcher/SKILL.md
      ├─ manuscript.write    → skills/agents/script-director/SKILL.md
      ├─ scene.chapters      → plugins/fontagent/SKILL.md
      ├─ scene.data          → plugins/chartagent/SKILL.md
      ├─ scene.review        → skills/agents/script-reviewer/SKILL.md
      ├─ assembly            → skills/agents/assembly-director/SKILL.md
      └─ release             → skills/agents/release-manager/SKILL.md
```

---

## Section 2: Python의 역할 (최소화)

Python 코드는 세 가지만 담당한다.

### task_db.py — SQLite CRUD

Orchestrator가 tool call로 호출하는 DB 인터페이스.

```sql
-- projects 테이블
CREATE TABLE projects (
  project_id TEXT UNIQUE NOT NULL,
  slug       TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'pending',
  config     TEXT,          -- editorial_brief JSON 포함
  created_at TEXT NOT NULL
);

-- tasks 테이블
CREATE TABLE tasks (
  project_id  TEXT NOT NULL,
  task_id     TEXT NOT NULL,  -- "research.skeleton" 등
  status      TEXT NOT NULL DEFAULT 'pending',
  attempt     INTEGER DEFAULT 1,
  error       TEXT,
  started_at  TEXT,
  finished_at TEXT
);
```

**상태 머신:** `pending → running → completed | failed | skipped`

### cli.py — 진입점

```bash
kairos-pd new [주제]          # 기획 인터뷰 → Orchestrator 진입
kairos-pd run --project <id>  # Orchestrator 실행
kairos-pd status [--project]  # DB 조회만 (Claude 불필요)
kairos-pd retry --project --task
kairos-pd skip  --project --task
kairos-pd plugin update [name|--all]
kairos-pd plugin status
kairos-pd list
```

### plugin_manager.py — 플러그인 동기화

원본 SKILL.md를 `plugins/` 하위로 복사하고 버전을 추적한다.

---

## Section 3: Claude Orchestrator Agent

### 역할

| 책임 | 방법 |
|------|------|
| DAG 순회 | pipeline.json + DB 상태 읽어서 다음 실행 가능 태스크 판단 |
| 서브에이전트 스폰 | 해당 태스크의 SKILL.md를 주입해 Claude CLI 호출 |
| 결과 검증 | 출력 파일 존재 여부 + 내용 샘플 확인 |
| 실패 게이트 | 사용자에게 retry / skip / abort 대화로 물음 |
| DB 업데이트 | update_task tool로 상태 기록 |

### Orchestrator 프롬프트 구조

```
당신은 kairos-pd Orchestrator입니다.
주어진 pipeline.json과 현재 DB 상태를 읽어,
실행 가능한 태스크를 순서대로 서브에이전트로 실행하고
결과를 DB에 기록합니다.

[tools]
- read_project(project_id) → projects 행
- read_tasks(project_id) → tasks 행 목록
- update_task(project_id, task_id, status, error?)
- run_agent(task_id, skill_path, inputs) → 서브에이전트 실행

[rules]
- depends_on 이 모두 completed|skipped 인 태스크만 실행
- 실패 시 사용자에게 retry/skip/abort 질문
- 전체 completed|skipped 이면 종료
```

### 실패 게이트 흐름

```
[FAILED] task: research.ingest
Error: SERPER_API_KEY 미설정

어떻게 할까요?
  r) 재시도
  s) 이 태스크 건너뛰기 (다운스트림 계속)
  a) 파이프라인 중단
```

`skipped` 태스크는 의존성 충족으로 취급 — 다운스트림 태스크가 계속 진행된다.

---

## Section 4: 플러그인 시스템

### 구조

```
kairos-pd/
  plugins/
    fontagent/
      SKILL.md        ← auto_kairos_v3 원본에서 복사
      version.json
    chartagent/
      SKILL.md
      version.json
```

### version.json 스키마

```json
{
  "plugin": "fontagent",
  "source_path": "auto_agent/data/skills/agents/fontagent/SKILL.md",
  "source_root": "/Users/jleavens_macmini/LocalProjects/auto_kairos_v3",
  "synced_at": "2026-04-23T10:00:00Z",
  "note": ""
}
```

### 업데이트 명령

```bash
kairos-pd plugin update fontagent   # 원본에서 최신 SKILL.md 복사
kairos-pd plugin update --all       # 전체 플러그인 업데이트
kairos-pd plugin status             # 원본과 diff 비교 (변경 여부 표시)
```

### pipeline.json 연결

```json
{
  "id": "scene.chapters",
  "name": "씬 분할 + 연출",
  "type": "plugin",
  "plugin": "fontagent",
  "depends_on": ["manuscript.write"]
}
```

`type: "plugin"` 태스크는 Orchestrator가 `plugins/{plugin}/SKILL.md`를 읽어 서브에이전트에 주입한다.

---

## Section 5: 파일 구조

```
/Volumes/kairos/CC_projects/kairos-pd/
├── core/
│   ├── task_db.py         # SQLite CRUD
│   └── plugin_manager.py  # 플러그인 update/status
├── skills/
│   └── agents/            # 태스크별 SKILL.md
│       ├── orchestrator/SKILL.md
│       ├── skeleton/SKILL.md
│       ├── draft-writer/SKILL.md
│       └── ...
├── plugins/               # 외부 플러그인 (버전 관리)
│   ├── fontagent/
│   │   ├── SKILL.md
│   │   └── version.json
│   └── chartagent/
│       ├── SKILL.md
│       └── version.json
├── tasks/
│   └── pipeline.json      # 태스크 DAG 선언
├── cli.py                 # Click CLI (진입점)
├── pyproject.toml
├── projects.db            # 런타임 생성
└── output/                # {project_id}_{slug}/
```

---

## Section 6: 이전 설계(2026-04-20)와의 차이

| 항목 | 2026-04-20 설계 | 이 설계 |
|------|----------------|---------|
| DAG 순회 | Python `engine.py` | Claude Orchestrator |
| 태스크 실행 | Python `task_runner.py` | Claude sub-agent |
| 실패 게이트 | Python `gate.py` | Orchestrator 대화 |
| 병렬 실행 | Python 스레드 | Orchestrator 판단 후 병렬 스폰 |
| Python 역할 | 엔진 + 실행 + 게이트 | SQLite + CLI 진입점만 |
| 플러그인 | 없음 | fontagent / chartagent 내장 |

`engine.py`, `gate.py`, `task_runner.py`, `runner.py`는 **불필요** — 제거.  
`task_db.py`, `cli.py`, `plugin_manager.py`만 Python으로 구현.

---

## Section 7: 스타일 매니저

파이프라인 밖에서 채널별 스타일을 사전 등록·관리하는 독립 레이어. 파이프라인은 읽기만 한다.

### 파일 구조

```
kairos-pd/
  styles/
    이로미즘/
      style_bundle.json    ← 스타일 규칙 통합 (writing은 파일 참조)
      writing_style.md     ← 문체 규칙 (자유 형식 마크다운)
      characters/
        base_ref_01.png    ← 기준 캐릭터 이미지
        base_ref_02.png
    세모지/
      style_bundle.json
      writing_style.md
      characters/
```

### style_bundle.json 스키마

```json
{
  "channel": "이로미즘",
  "version": "1.0",
  "updated_at": "2026-04-24T...",

  "artstyle": {
    "preset": "iromism_cinematic",
    "prompt_positive": "...",
    "prompt_negative": "...",
    "reference_images": ["characters/base_ref_01.png"]
  },

  "voice": {
    "id": "EXAVITQu4vr4xnSDxMaL",
    "name": "이로미",
    "provider": "elevenlabs"
  },

  "writing": {
    "style_file": "writing_style.md"
  },

  "tts": {
    "pre": ["숫자 한글 변환", "영어 발음 표기"],
    "post": ["묵음 제거", "0.3s 페이드인"]
  },

  "image_rules": {
    "character_extract": "...",
    "character_generate": "...",
    "scene_generate": "..."
  }
}
```

### writing_style.md

문체 톤, 금지 표현, 문장 구조, 예시 문장 등을 자유롭게 마크다운으로 작성.  
Orchestrator가 서브에이전트 실행 시 이 파일을 읽어 프롬프트에 주입한다.

### CLI

```bash
kairos-pd style new 이로미즘              # 인터뷰로 신규 생성 (Claude)
kairos-pd style list                      # 등록된 채널 목록
kairos-pd style show 이로미즘             # 스타일 번들 출력
kairos-pd style set 이로미즘 voice.id EXAVITQu4vr4xnSDxMaL
kairos-pd style edit 이로미즘             # style_bundle.json 에디터로 열기
kairos-pd style edit 이로미즘 --writing   # writing_style.md 에디터로 열기
```

### 파이프라인 연결

Orchestrator가 `editorial_brief.json`의 `channel` 필드로 `styles/{channel}/style_bundle.json`과 `writing_style.md`를 로드해서, 모든 서브에이전트 실행 시 컨텍스트로 주입한다.

---

## 구현 순서 (Plan 단위)

| Plan | 내용 |
|------|------|
| Plan 1 | 스캐폴드 + task_db.py + cli.py 뼈대 + plugin_manager.py |
| Plan 2 | Orchestrator SKILL.md + pipeline.json + 기획 인터뷰 스킬 |
| Plan 3 | 스타일 매니저 (style_bundle.json + writing_style.md + style CLI) |
| Plan 4 | 태스크별 SKILL.md 이식 (v3 → kairos-pd) |
| Plan 5 | 플러그인 초기 세트 (fontagent, chartagent) + update 명령 |
| Plan 6 | 대시보드 + 엔드투엔드 테스트 |
