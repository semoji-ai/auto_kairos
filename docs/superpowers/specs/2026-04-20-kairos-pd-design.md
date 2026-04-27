# kairos-pd 설계 문서

**날짜:** 2026-04-20  
**상태:** 승인됨  
**위치:** `/Volumes/kairos/CC_projects/kairos-pd/`

---

## 개요

auto_kairos_v3의 파이프라인을 태스크 기반으로 재설계한 독립 프로젝트. v3의 견고한 파이프라인 흐름을 유지하면서, "한 곳 깨지면 전체 중단"이라는 취약점을 태스크화로 해결한다. superpowers의 스킬 기반 접근 방식을 참고하여, `/kairos-pd` 슬래시 커맨드로 시작하는 기획 인터뷰부터 영상 완성까지 태스크 단위로 관리한다.

---

## Section 1: 전체 구조

```
/kairos-pd (슬래시 커맨드 또는 CLI)
  ↓
[기획 스킬] — 채널/방향/분량/아트스타일 인터뷰 (브레인스토밍 방식)
  ↓
project_id = uuid4() 자동 생성
slug = 주제에서 자동 추출 (예: "포켓몬_30주년")
프로젝트 폴더: output/{project_id}_{slug}/
  ↓
editorial_brief.json 저장 + 태스크 목록 생성
  ↓
[태스크 엔진] DAG 기반 실행
  ├─ task: preflight
  ├─ task: research.skeleton      ← 독립 재실행 가능
  ├─ task: research.strategy      ← 독립 재실행 가능
  ├─ task: research.ingest        ← 독립 재실행 가능
  ├─ task: research.projection    ← 독립 재실행 가능 (ingest와 병렬 가능)
  ├─ task: manuscript.draft
  ├─ task: manuscript.target
  ├─ task: manuscript.write
  ├─ task: scene.chapters         ← 챕터별 병렬 실행
  ├─ task: scene.data
  ├─ task: scene.review
  ├─ task: assembly
  └─ task: release
```

v3 파이프라인 14개 스텝을 1:1로 태스크화. 태스크 DAG는 `tasks/pipeline.json`에 선언.

---

## Section 2: 태스크 엔진 핵심 동작

### 태스크 상태 머신

```
pending → running → completed
                 → failed → [gate: retry | skip | abort]
                              retry → running
                              skip  → skipped
                              abort → 전체 중단
```

### DAG 실행 규칙

- `depends_on`이 모두 `completed`인 태스크만 실행 가능
- `skipped`도 의존성 충족으로 취급 (다운스트림 태스크 계속 진행)
- 병렬 실행: 동시에 `running` 가능한 태스크는 스레드로 동시 실행
- 독립 실행: `kairos-pd run --project <id> --only <task_id>` 로 단일 태스크 강제 실행

### SQLite 스키마

```sql
CREATE TABLE projects (
  id         INTEGER PRIMARY KEY,
  project_id TEXT UNIQUE NOT NULL,  -- uuid4
  slug       TEXT NOT NULL,         -- 가독성용, 중복 허용
  status     TEXT NOT NULL,         -- pending | running | completed | failed | aborted
  config     TEXT,                  -- JSON (editorial_brief 포함)
  created_at TEXT NOT NULL
);

CREATE TABLE tasks (
  id          INTEGER PRIMARY KEY,
  project_id  TEXT NOT NULL,
  task_id     TEXT NOT NULL,        -- "research.skeleton" 등
  status      TEXT NOT NULL,        -- pending | running | completed | failed | skipped
  attempt     INTEGER DEFAULT 1,
  error       TEXT,
  started_at  TEXT,
  finished_at TEXT
);
```

### 실패 게이트

실패 시 **터미널 알림 + 대시보드 표시**:

```
[FAILED] task: research.ingest
Error: SERPER_API_KEY 미설정
> (r)etry  (s)kip  (a)bort ?
```

- `retry` — 같은 태스크 재실행
- `skip` — 해당 태스크 skipped 처리, 다운스트림 계속
- `abort` — 프로젝트 전체 중단

---

## Section 3: 기획 스킬 (`/kairos-pd`)

### 인터뷰 흐름

1. **채널 선택** — 이로미즘 / 세모지 / 신규
2. **주제/방향 탐색** — 대화로 핵심 각도 결정 (주제 없이 시작해도 됨)
3. **분량 결정** — 1 / 3 / 5 / 10 / 15분
4. **아트스타일 선택** — 생성형 이미지 그림체 톤앤매너
   - 등록된 커스텀 스타일 목록에서 선택 (있는 경우)
   - 내장 기본 3종:
     - `realistic` — 시네마틱 실사풍
     - `illustration` — 깔끔한 일러스트풍
     - `cinematic-dark` — 어두운 영화적 분위기
   - 선택 안 하면 `realistic` 기본 적용
5. **확정** → `editorial_brief.json` + 태스크 목록 생성

### 출력 스키마

```json
{
  "project_id": "a1b2c3d4-...",
  "slug": "포켓몬_30주년",
  "channel": "이로미즘",
  "duration_minutes": 10,
  "art_style": "realistic",
  "core_angle": "...",
  "must_include": [],
  "excluded_angles": [],
  "editorial_brief": { ... }
}
```

### 진입점

| 진입점 | 방식 | Claude 필요 |
|--------|------|------------|
| `/kairos-pd` | Claude Code 슬래시 커맨드 | ✅ (기획 인터뷰) |
| `kairos-pd new` | 터미널 CLI | ✅ (기획 인터뷰) |
| `kairos-pd run` | 터미널 CLI | ✅ (에이전트 실행) |
| `kairos-pd status` | 터미널 CLI | ❌ (DB 조회만) |
| `kairos-pd retry/skip` | 터미널 CLI | ❌ (DB 상태 변경만) |
| 대시보드 | 브라우저 | 혼합 |

---

## Section 4: 파일 구조 및 기술 스택

```
/Volumes/kairos/CC_projects/kairos-pd/
├── core/
│   ├── engine.py          # DAG 순회 + 태스크 스케줄링
│   ├── task_db.py         # SQLite CRUD
│   ├── task_runner.py     # 에이전트/모듈 실행
│   └── gate.py            # 실패 게이트 (retry/skip/abort)
├── skills/
│   ├── agents/            # v3에서 복사 후 독립 진화
│   └── shared/
├── tasks/
│   └── pipeline.json      # 전체 태스크 DAG 선언
├── dashboard/             # v3에서 복사 후 독립 운영
├── artstyles/
│   ├── realistic.json
│   ├── illustration.json
│   └── cinematic-dark.json
├── cli.py                 # Click 기반 CLI
├── output/                # {project_id}_{slug}/
└── projects.db            # SQLite
```

**기술 스택:**
- Python — 코어 엔진, CLI (Click)
- SQLite — 프로젝트/태스크 상태
- FastAPI — 대시보드 API (v3 패턴)
- Claude Code 슬래시 스킬 — `/kairos-pd` 진입점

---

## Section 5: CLI 인터페이스

```bash
# 기획 인터뷰 시작
kairos-pd new
kairos-pd new "포켓몬 30주년"   # 주제 힌트 (인터뷰로 구체화)

# 프로젝트 실행
kairos-pd run --project <project_id>
kairos-pd run --project <project_id> --from research.ingest
kairos-pd run --project <project_id> --only scene.chapters

# 태스크 상태 확인
kairos-pd status --project <project_id>

# 실패 태스크 처리
kairos-pd retry --project <project_id> --task research.ingest
kairos-pd skip  --project <project_id> --task research.ingest

# 프로젝트 목록
kairos-pd list

# 대시보드 실행
kairos-pd dashboard
```

**Claude Code 슬래시 커맨드:**
```
/kairos-pd         → 기획 인터뷰 시작
/kairos-pd status  → 진행 중 프로젝트 현황
```

---

## 변경 범위 요약

| 항목 | v3 대비 |
|------|---------|
| 파이프라인 → 태스크 DAG | 14개 스텝을 독립 태스크로 분리 |
| 실패 처리 | 전체 중단 → 게이트에서 retry/skip/abort 선택 |
| 기획 스킬 | `/auto-kairos` 인터뷰 방식 강화, 브레인스토밍 구조화 |
| 프로젝트 식별 | slug만 → project_id(uuid) + slug 조합 |
| 코드베이스 | v3와 완전 독립, 스킬/대시보드 복사 후 독립 진화 |

v3의 에이전트 스킬, 모듈 로직, Remotion 렌더링 파이프라인은 그대로 재사용.
