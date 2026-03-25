# Stage 0/4 — 채널 인텔리전스 루프 설계

> 기획(Stage 0)과 결과분석(Stage 4)을 기존 3단계 파이프라인에 추가하여,
> 데이터 기반 피드백 루프를 완성하는 설계 문서.

## 1. 배경 및 목표

### 현재 상태
- 3단계 파이프라인 안정화 완료: Stage 1(리서치) → Stage 2(원고/연출) → Stage 3(제작)
- YouTube 연동 없음 — 로컬 .mp4 생성까지만 지원
- 주제 선정 및 결과 분석은 수동

### 목표
- **Stage 0 (기획)**: 채널 분석 + 시장 트렌드 교차 분석으로 주제 선정 자동화
- **Stage 4 (결과분석)**: 업로드된 영상 성과 + 시장 동향을 분석하여 Stage 0에 피드백
- **피드백 루프**: Stage 4 → Stage 0 → Stage 1~3 → Stage 4 순환 구조

### 전체 사이클

```
         ┌──── Stage 4 피드백 (볼트 위키링크) ────┐
         ▼                                        │
    [Stage 0] plan                                │
         │ 기획안 승인                              │
         ▼                                        │
    [Stage 1] research                            │
         │                                        │
         ▼                                        │
    [Stage 2] script + fact-check                 │
         │                                        │
         ▼                                        │
    [Stage 3] assembly → .mp4                     │
         │                                        │
         │ 수동 업로드 + link                      │
         ▼                                        │
    [Stage 4] analyze ─────────────────────────────┘
```

### 스텝 ID 체계

기존 `step_0`(Preflight)과 충돌을 피하기 위해 새 스텝은 별도 네이밍 사용.

| 스텝 ID | 이름 | 에이전트 | 파이프라인 위치 |
|---------|------|---------|---------------|
| `step_0` | environment_check | preflight (모듈) | 기존 유지 |
| `step_plan` | topic_planning | trend-analyst | Stage 0 (파이프라인 외부, 독립 실행) |
| `step_1` | deep_research | research-orchestrator | 기존 유지 |
| `step_2` | script_and_direct | script-director | 기존 유지 |
| `step_2b` | fact_check | fact-verifier | 기존 유지 |
| `step_3` | assembly | assembly-director | 기존 유지 |
| `step_analyze` | performance_analysis | performance-analyst | Stage 4 (파이프라인 외부, 독립 실행) |

> **설계 결정**: Stage 0/4는 기존 `pipeline.json`의 순차 실행 구조에 포함하지 않는다.
> 독립적인 cron/CLI 명령으로 실행되며, 볼트를 통해 데이터를 주고받는다.
> `pipeline.json`에는 등록하지 않고, `agents.json`에만 에이전트 정의를 추가한다.

### 볼트와 프로젝트 디렉토리의 관계

```
kairos-vault/ (NAS)              output/{uuid}_{slug}/ (로컬)
├── 채널 분석, 트렌드, 인사이트      ├── research_report.json
├── 기획안, 피드백                   ├── scene_specs.json
└── 영상 성과 노트                   ├── manifest.json
     ↕ 연결점                        └── final.mp4

auto-agent link 실행 시:
  1. projects DB에 video_id 저장
  2. 볼트에 videos/{영상제목}.md 생성 (project_slug로 로컬 디렉토리 참조)

auto-agent project create --from-plan 실행 시:
  1. 기획안.md에서 topic, channel 추출
  2. projects DB에 프로젝트 생성 + config 세팅
  3. 기획안.md의 status를 approved로 업데이트
```

## 2. 아키텍처

### 구성 요소

```
┌─────────────────────────────────────────────────────┐
│                  kairos-vault/ (NAS)                 │
│   Obsidian 마크다운 + 위키링크                        │
│   Phase 2: + LanceDB 벡터 인덱스 (.lance/)           │
└──────────┬──────────────────────┬────────────────────┘
           │                      │
     읽기/쓰기                  읽기/쓰기
           │                      │
    ┌──────▼──────┐       ┌───────▼───────┐
    │ Stage 0     │       │ Stage 4       │
    │ trend-      │◄──────│ performance-  │
    │ analyst     │피드백  │ analyst       │
    └──────┬──────┘루프    └───────▲───────┘
           │                      │
           ▼                      │
  [Stage 1→2→3 기존 파이프라인]────┘
                            업로드 후 YouTube ID 연결

┌─────────────────────────────────────┐
│  data-collector (Python 모듈/cron)  │
│  YouTube API · Google/Naver Trends  │
│  Reddit · X · 커뮤니티 크롤링        │
│  → 볼트에 마크다운 노트 생성/갱신     │
└─────────────────────────────────────┘
```

### 역할 분담

| 도구 | 역할 | 시점 |
|------|------|------|
| **Claude CLI** | data-collector + 에이전트 자동 실행 (cron) | 새벽 자동 |
| **Claudian** | 볼트 내 수동 탐색, 분석, 기획안 검토 | 한나님이 직접 |
| **볼트** | 공유 디렉토리 — 양쪽 모두 읽기/쓰기 | 상시 |

### 핵심 원칙

1. **데이터 수집**은 Python 모듈이 cron으로 수행 → LLM 비용 없음
2. **분석/기획**은 에이전트가 볼트를 탐색하며 수행 (Claude CLI)
3. **볼트는 단일 소스** — 에이전트도 분석 결과를 볼트에 마크다운으로 저장
4. **위키링크**로 주제↔영상↔트렌드↔인사이트가 자연스럽게 연결
5. **벡터 검색은 단계적 도입** — Phase 1은 CLI 직접 탐색, Phase 2에서 LanceDB 추가
6. **경로 참조** — 볼트 경로는 `KAIROS_VAULT_DIR` 환경변수로 참조 (하드코딩 금지)

## 3. 볼트 디렉토리 구조

```
kairos-vault/
├── .lance/                          # Phase 2: LanceDB 벡터 인덱스
├── .collector/                       # ⚠ .obsidianignore에 추가 필수
│   ├── state.json                   # 수집 워터마크 (소스별 마지막 수집 시점)
│   ├── hashes.db                    # SQLite — 콘텐츠 해시로 중복 판별
│   └── video_tracking.json          # 영상 성과 추적 스케줄
├── channels/
│   ├── _watchlist.md                # 경쟁 채널 추적 목록 + 상태
│   ├── 이로미즘/
│   │   ├── _channel.md              # 채널 프로필, 구독자, 포지셔닝
│   │   ├── analytics/
│   │   │   ├── 2026-W12-weekly.md   # 주간 성과 요약
│   │   │   └── 2026-03-monthly.md   # 월간 종합
│   │   └── videos/
│   │       └── 미국-이란 전쟁.md     # 개별 영상 성과
│   ├── 세모지/
│   │   └── (동일 구조)
│   └── competitors/                 # 경쟁 채널 프로필 + 공개 데이터
│       ├── 슈카월드.md
│       └── ...
├── market/
│   ├── trends/
│   │   └── 2026-03-25-daily.md      # 일일 트렌드 스냅샷
│   └── social/
│       └── 2026-03-25-buzz.md       # 소셜 화제성 수집
├── topics/
│   └── 미국-이란.md                  # 주제 노트: 위키링크로 연결
├── insights/
│   ├── performance/
│   │   └── 조회수-패턴-분석.md       # Stage 4 성과 인사이트
│   ├── planning/
│   │   └── 2026-03-25-기획안.md     # Stage 0 기획 제안
│   └── feedback/
│       └── 2026-W12-feedback.md     # Stage 4 → Stage 0 피드백
└── templates/
    ├── video-note.md
    ├── trend-daily.md
    ├── weekly-report.md
    └── topic-note.md
```

### 영상 노트 예시

```markdown
---
video_id: "abc123"
channel: 이로미즘
project_slug: us-iran-war
published: 2026-03-20
duration: "12:34"
---

## 성과
| 지표 | 7일 | 28일 | 현재 |
|------|-----|------|------|
| 조회수 | 15,200 | 42,000 | 58,300 |
| CTR | 8.2% | 7.1% | 6.8% |
| 평균 시청 지속 | 6:12 | 5:48 | 5:42 |

## 유입 경로
- 검색 42% · 추천 35% · 탐색 18%

## 연결
- 주제: [[미국-이란]]
- 트렌드: [[2026-03-20-daily]]
- 인사이트: [[조회수-패턴-분석]]
```

### 위키링크 연결 규칙

- 영상 → 주제, 트렌드, 인사이트
- 주제 → 관련 영상들, 경쟁 채널의 유사 영상, 트렌드
- 인사이트 → 근거가 된 영상들, 트렌드
- 기획안 → 참고한 인사이트들, 주제, 트렌드

## 4. 중복 방지 메커니즘

### 3단계 중복 방지

**1단계: 워터마크 — "어디까지 수집했는지"**

```json
// .collector/state.json
{
  "youtube_analytics": {
    "이로미즘": { "last_fetch": "2026-03-25T09:00:00", "last_date": "2026-03-24" },
    "세모지": { "last_fetch": "2026-03-25T09:00:00", "last_date": "2026-03-24" }
  },
  "youtube_videos": {
    "이로미즘": { "last_video_id": "abc123", "last_published": "2026-03-20" }
  },
  "google_trends": { "last_fetch": "2026-03-25T06:00:00" },
  "social_buzz": { "last_fetch": "2026-03-25T12:00:00" },
  "competitors": { "last_fetch": "2026-03-23T00:00:00" }
}
```

**2단계: 콘텐츠 해시 — "같은 내용을 또 쓰지 않기"**

```sql
-- .collector/hashes.db
CREATE TABLE collected (
    source    TEXT,     -- 'youtube_video', 'trend', 'social'
    source_id TEXT,     -- video_id, trend keyword, post URL
    hash      TEXT,     -- 콘텐츠 SHA-256
    note_path TEXT,     -- 볼트 내 저장된 노트 경로
    created   TEXT,
    updated   TEXT,
    PRIMARY KEY (source, source_id)
);
```

**3단계: 노트 레벨 upsert**

- **신규** (source_id 없음) → 노트 생성, 해시 저장
- **기존 + 내용 변경** (해시 불일치) → 노트 업데이트, 해시 갱신
- **기존 + 내용 동일** (해시 일치) → 스킵

### 소스별 적용

| 소스 | source_id | 수집 주기 | 중복 판단 |
|------|-----------|-----------|-----------|
| 영상 메타 | `video_id` | 새 영상 발행 시 | ID 기반, 성과는 주기적 갱신 |
| Analytics | `channel_id + date` | 일 1회 | 날짜 워터마크 |
| 트렌드 | `keyword + date` | 일 1회 | 날짜 기반 스냅샷 (누적) |
| 경쟁 채널 | `channel_id` | 주 1회 | 해시로 변경 감지 |
| 소셜 | `post_url` | 일 2회 | URL 기반 중복 제거 |

## 5. 경쟁 채널 관리

### 운영 규칙

| 동작 | 권한 | 설명 |
|------|------|------|
| 초기 세팅 | 사용자 | 10개 직접 지정 |
| 임시 추가 | 에이전트 자동 | 최대 3개, `trial` 상태로 추가 |
| trial → active 승격 | 사용자 승인 | CLI 또는 대시보드에서 승인 |
| 제거 | 사용자 승인 | 에이전트가 제안 + 사유 첨부 |

### 상태 관리

| 상태 | 의미 | 최대 수 |
|------|------|---------|
| `active` | 정규 추적 (사용자 승인) | 10 (초기) + 승격분 |
| `trial` | 에이전트가 임시 추가 | 최대 3 |
| `proposed_remove` | 에이전트가 제거 제안 | - |
| `archived` | 제거됨 (이력 보존) | - |

### `_watchlist.md` 구조

```markdown
---
max_trial: 3
last_review: 2026-03-25
next_review: 2026-04-01
---

## Active
| 채널 | 카테고리 | 추가일 | 추가 사유 | 관련도 |
|------|---------|--------|-----------|--------|
| [[슈카월드]] | 경제/시사 | 2026-01-15 | 유사 주제, 높은 조회수 | ★★★★★ |

## Trial
| 채널 | 추가일 | 추가 사유 | 관련도 |
|------|--------|-----------|--------|
| [[어쩌다어른]] | 2026-03-22 | 교양 포맷 유사, 성장세 | ★★★☆☆ |

## Proposed Remove
| 채널 | 제안일 | 사유 |
|------|--------|------|
| [[예시채널]] | 2026-03-25 | 6주간 관련 콘텐츠 없음 |

## Archived
| 채널 | 제거일 | 사유 |
|------|--------|------|
```

### trial 슬롯 규칙

- trial 3개 찬 상태에서 새로 추가하려면, 기존 trial 하나를 승격 요청하거나 포기한 뒤 추가
- 무분별한 확장 방지

## 6. Stage 0 — trend-analyst 에이전트

### 역할
채널 데이터 + 시장 트렌드를 교차 분석하여 주제 기획안 생성.

### 실행 모드

**자율 모드** — 매일 KST 06:00 cron 실행
```
볼트 탐색 → 트렌드 + 채널 성과 + 경쟁 채널 교차 분석
→ 주제 후보 3~5개 순위화 → insights/planning/ 저장 → Discord 푸시
```

**시드 모드** — 사용자가 키워드/아이디어 제공
```
시드 입력 → 볼트에서 관련 데이터 탐색
→ 트렌드 적합성 + 채널 적합성 검증
→ 기획안 1개로 구체화 → insights/planning/ 저장
```

### 기획안 출력 포맷

```markdown
---
type: planning
mode: autonomous | seeded
channel: 이로미즘
created: 2026-03-25
status: proposed | approved | rejected
seed: null | "사용자 입력 키워드"
---

## 주제: 중국 희토류 전쟁의 숨겨진 승자

### 왜 지금인가 (타이밍)
- [[2026-03-24-daily]]: "희토류" 검색량 3주간 +180%
- [[슈카월드]]: 관련 영상 없음 — 선점 기회

### 채널 적합성
- 이로미즘 과거 유사 주제: [[중국-반도체-규제]] (조회수 82K, CTR 9.1%)
- 예상 시청층 겹침: 85%

### 경쟁 분석
- 유사 주제 다룬 채널: [[지식한입]] (3일 전, 조회수 45K)
- 차별화 포인트: 경제적 수혜국 분석 → 이로미즘 스타일에 적합

### 추천 앵글
1. "희토류 전쟁에서 웃는 나라는 따로 있다"
2. "중국이 희토류를 무기화하면 벌어지는 일"

### 예상 성과
- 예상 조회수 범위: 40K~90K (유사 영상 기반)
- 추천 길이: 10~12분
```

### 에이전트 설정

```json
{
  "trend-analyst": {
    "model": "opus",
    "max_turns": 40,
    "budget_usd": 2.0,
    "max_duration_min": 15,
    "tools": ["Read", "Write", "Glob", "Grep"],
    "shared_skills": ["writing-style-iromism", "writing-style-semoji", "market-analysis"],
    "working_dir": "$KAIROS_VAULT_DIR",
    "output": "insights/planning/{date}-{topic}.md"
  }
}
```

### 기획안 → 프로젝트 전환

```bash
auto-agent project create --from-plan insights/planning/2026-03-25-희토류.md
# → topic, channel, config 자동 세팅 → Stage 1 시작 가능
```

## 7. Stage 4 — performance-analyst 에이전트

### 실행 모드

**영상 단위 추적** — 업로드 등록 시 트리거
```
YouTube URL/ID 연결 → +1일, +3일, +7일, +28일 시점에 성과 수집
→ videos/ 노트 업데이트 → 위키링크 연결
→ 기대 대비 성과 평가 노트 생성
```

**주간 종합 리뷰** — 매주 일요일 KST 06:00
```
볼트 전체 탐색 → 채널 성과 + 경쟁 채널 + 시장 트렌드 종합
→ 주간 인사이트 리포트 생성
→ 경쟁 채널 watchlist 리뷰 (trial 추가/제거 제안)
→ Stage 0 피드백 정리
```

### 영상 성과 추적 타임라인

```
업로드 등록 (auto-agent link)
  │
  ├─ +1일 ─→ 초기 반응 (CTR, 초반 조회수, 이탈 구간)
  ├─ +3일 ─→ 추천 알고리즘 반응 (추천 유입률, 성장 곡선)
  ├─ +7일 ─→ 1주 성과 확정 (비교군 대비 평가)
  └─ +28일 ─→ 최종 성과 (롱테일 여부, 검색 유입 비중)
```

### 영상 추적 스케줄러 메커니즘

`auto-agent link` 실행 시 `.collector/video_tracking.json`에 추적 대상 등록.
매일 data-collector cron(KST 05:30)이 "오늘 추적 대상"을 계산하여 수집 실행.

```json
// .collector/video_tracking.json
{
  "tracking": [
    {
      "video_id": "abc123",
      "project_slug": "us-iran-war",
      "channel": "이로미즘",
      "linked_at": "2026-03-20T10:00:00",
      "checkpoints": {
        "1d": { "due": "2026-03-21", "status": "done", "collected_at": "2026-03-21T05:30:00" },
        "3d": { "due": "2026-03-23", "status": "done", "collected_at": "2026-03-23T05:30:00" },
        "7d": { "due": "2026-03-27", "status": "pending" },
        "28d": { "due": "2026-04-17", "status": "pending" }
      }
    }
  ]
}
```

**수집 로직:**
1. 매일 05:30 cron → `video_tracking.json` 읽기
2. `due <= today && status == pending` 인 체크포인트 필터링
3. 해당 영상의 YouTube Analytics 수집 → 볼트 노트 업데이트
4. 체크포인트 status를 `done`으로 갱신
5. 수집 실패 시 status를 `retry`로 표시, 다음 날 재시도 (최대 3회)
6. 모든 체크포인트 완료 시 tracking에서 제거하지 않음 (이력 보존)

### 주간 리뷰 출력 포맷

```markdown
---
type: weekly-review
channel: 이로미즘
period: 2026-W12 (03-18 ~ 03-24)
created: 2026-03-25
---

## 채널 성과 요약
- 총 조회수: 125K (+12% vs W11)
- 신규 구독: +340
- 최고 성과: [[미국-이란 전쟁]] — 58K views, CTR 8.2%

## 패턴 발견
- 경제 주제가 시사 주제 대비 CTR +2.1%p 높음
- 12분 이상 영상의 평균 시청 지속 시간 하락 추세
- 썸네일에 숫자 포함 시 CTR 유의미하게 높음 ([[조회수-패턴-분석]])

## 경쟁 채널 동향
- [[슈카월드]]: AI 주제 3연속 → 시장 AI 관심 지속
- [[지식한입]]: 역사 주제 조회수 하락 추세
- trial 추가: [[어쩌다어른]] — 교양 포맷 유사, 최근 성장세

## 제거 제안
- [[예시채널]]: 6주간 관련 콘텐츠 없음, 카테고리 이탈

## Stage 0 피드백
- 경제 앵글 우선 추천
- 영상 길이 8~11분 타겟 권장
- [[희토류]] 주제 타이밍 여전히 유효
```

### 에이전트 설정

```json
{
  "performance-analyst": {
    "model": "sonnet",
    "max_turns": 50,
    "budget_usd": 1.5,
    "max_duration_min": 20,
    "tools": ["Read", "Write", "Glob", "Grep"],
    "shared_skills": ["channel-metrics", "market-analysis"],
    "working_dir": "$KAIROS_VAULT_DIR",
    "schedules": {
      "video_track": "업로드 등록 시 트리거 (+1d, +3d, +7d, +28d)",
      "weekly_review": "매주 일요일 KST 06:00"
    }
  }
}
```

### Stage 4 → Stage 0 피드백 루프

```
주간 리뷰의 "Stage 0 피드백" 섹션
    │
    ▼
insights/feedback/2026-W12-feedback.md
    │
    ▼
trend-analyst가 매일 기획 시 볼트에서 최신 피드백 탐색
→ 기획안에 자동 반영
```

피드백이 볼트 안의 위키링크 네트워크를 통해 자연스럽게 흐르는 구조.

## 8. data-collector 모듈

### 모듈 구조

```
auto_agent/modules/data_collector/
├── __init__.py
├── collector.py              # 메인 오케스트레이터
├── youtube_collector.py      # YouTube Data + Analytics API
├── trend_collector.py        # Google Trends + Naver DataLab
├── social_collector.py       # Reddit + X + 커뮤니티
├── vault_writer.py           # 수집 데이터 → 마크다운 노트 변환
├── dedup.py                  # 중복 방지 (state.json + hashes.db)
└── discord_notifier.py       # Discord 웹훅 푸시
```

### 수집 소스

| 소스 | API/도구 | 수집 항목 | 비용 |
|------|----------|-----------|------|
| 내 채널 Analytics | YouTube Analytics API (OAuth) | CTR, 시청지속, 유입경로, 구독 전환 | 무료 |
| 내 채널 영상 목록 | YouTube Data API | 신규 영상, 조회수, 좋아요 | 무료 |
| 경쟁 채널 (공개만) | YouTube Data API | 영상 목록, 조회수, 좋아요, 업로드 빈도 | 무료 |
| Google Trends | pytrends (폴백: SerpAPI) | 검색량 추이, 관련 키워드 | 무료/유료 |
| Naver DataLab | Naver API | 한국 검색량 추이 | 무료 |
| 소셜 | Reddit API + X API + 웹 크롤 | 언급량, 감성, 화제 키워드 | 무료/저가 |

### 경쟁 채널에서 수집 가능/불가능한 데이터

| 지표 | 내 채널 (Analytics API) | 경쟁 채널 (Data API) |
|------|------------------------|---------------------|
| 조회수 | ✅ | ✅ |
| 좋아요 | ✅ | ✅ |
| 영상 목록/업로드 빈도 | ✅ | ✅ |
| 구독자 수 | ✅ | ✅ (대략적) |
| CTR | ✅ | ❌ |
| 시청 지속 시간 | ✅ | ❌ |
| 유입 경로 | ✅ | ❌ |
| 구독 전환율 | ✅ | ❌ |
| 이탈 구간 | ✅ | ❌ |

> 경쟁 채널 분석은 공개 데이터(조회수, 업로드 패턴, 주제 선택)로 한정.
> 경쟁 채널의 CTR/시청지속 등은 추정 불가하므로 리포트에 포함하지 않는다.

### cron 스케줄

```
KST 05:30  data-collector 전체 수집 (영상 추적 포함)
KST 06:00  trend-analyst × 2채널 (이로미즘 → 세모지 순차 실행)
일요일 06:00  performance-analyst × 2채널 (채널별 주간 리뷰)
```

> 듀얼 채널 처리: 각 채널별로 순차 실행. Discord 알림도 채널별로 구분하여 발송.

### 실행 흐름

```
cron KST 05:30
    │
    ├─ 1. youtube_collector.py
    │     ├─ 내 채널 Analytics (전일분)
    │     ├─ 내 채널 신규 영상 체크
    │     └─ 경쟁 채널 (active + trial) 공개 데이터
    │
    ├─ 2. trend_collector.py
    │     ├─ Google Trends (관심 키워드 + 자동 탐색)
    │     └─ Naver DataLab
    │
    ├─ 3. social_collector.py
    │     ├─ Reddit (관련 서브레딧)
    │     ├─ X/Twitter (키워드 모니터링)
    │     └─ 커뮤니티 크롤링
    │
    ├─ 4. vault_writer.py
    │     ├─ 수집 데이터 → 마크다운 노트 변환
    │     ├─ 위키링크 자동 생성
    │     └─ 중복 체크 (state.json + hashes.db)
    │
    └─ 5. (Phase 2) indexer.py
          └─ 변경된 노트 → LanceDB 벡터 재인덱싱
```

## 9. Discord 알림

### 알림 타입별 포맷

**일일 기획안:**
```
📋 이로미즘 일일 기획안 (03-25)

1. 중국 희토류 전쟁의 숨겨진 승자
   검색량 +180% · 경쟁 채널 미진입 · 예상 50~90K

2. 일본 반도체 보조금의 진짜 목적
   채널 적합도 ★★★★★ · 유사 영상 CTR 9.1%

3. 테슬라 로보택시 지연의 내막
   소셜 화제성 높음 · 경제 앵글 가능

→ 전문: vault/insights/planning/2026-03-25.md
```

**영상 성과 (+7일):**
```
📊 미국-이란 전쟁 7일 성과

조회수: 42,000 (예상 대비 +15%)
CTR: 7.1% (채널 평균 6.2%)
평균 시청: 5:48 / 12:34 (46%)
유입: 검색 42% · 추천 35%

→ 전문: vault/channels/이로미즘/videos/미국-이란 전쟁.md
```

**주간 리뷰:**
```
📈 이로미즘 주간 리뷰 (W12)

총 조회수: 125K (+12%)
최고 성과: 미국-이란 전쟁 (58K)
패턴: 경제 주제 CTR +2.1%p ↑

⚡ 승인 필요
• trial→정규: [[어쩌다어른]] 승격?
• 제거: [[예시채널]] — 6주 무관련

→ 전문: vault/channels/이로미즘/analytics/2026-W12-weekly.md
```

## 10. CLI 통합

### 새 명령어

```bash
# 데이터 수집
auto-agent collect --all                    # 전체 수집
auto-agent collect --youtube                # YouTube만
auto-agent collect --trends                 # 트렌드만
auto-agent collect --social                 # 소셜만

# Stage 0 — 기획
auto-agent plan --channel 이로미즘          # 자율 모드
auto-agent plan --channel 이로미즘 --seed "희토류 전쟁"  # 시드 모드

# Stage 4 — 분석
auto-agent analyze --video <video_id>       # 영상 단위 분석
auto-agent analyze --weekly --channel 이로미즘  # 주간 리뷰

# 영상 연결
auto-agent link --project <slug> --video-id <id>  # YouTube ID 연결

# 경쟁 채널 관리
auto-agent watchlist                        # 목록 확인
auto-agent watchlist approve <채널명>       # trial → active 승격
auto-agent watchlist remove <채널명>        # 제거 승인

# 기획안 → 프로젝트 전환
auto-agent project create --from-plan <기획안.md>
```

### 전체 워크플로

```bash
# 1. 새벽 자동: 수집 + 기획
# cron 05:30 → auto-agent collect --all
# cron 06:00 → auto-agent plan --channel 이로미즘

# 2. 아침: Discord에서 기획안 확인 → 승인
auto-agent project create --from-plan insights/planning/2026-03-25-희토류.md

# 3. 파이프라인 실행
auto-agent run --project rare-earth-war

# 4. 수동 업로드 후 연결
auto-agent link --project rare-earth-war --video-id abc123

# 5. 자동: 성과 추적 (+1/3/7/28일)
# cron → auto-agent analyze --video abc123

# 6. 주간: 종합 리뷰 + 피드백 루프
# cron 일요일 06:00 → auto-agent analyze --weekly --channel 이로미즘
```

## 11. 에러 처리 및 장애 복구

### 수집 실패 정책

| 상황 | 동작 |
|------|------|
| YouTube API 할당량 초과 | 수집 중단, Discord 경고 알림, 다음 날 재시도 |
| pytrends 차단 (429/CAPTCHA) | SerpAPI 폴백 시도, 실패 시 트렌드 수집 스킵 |
| 볼트(NAS) 접근 불가 | 수집 중단, Discord 긴급 알림, 재시도 안 함 |
| 소셜 API 오류 | 해당 소스만 스킵, 나머지 정상 수집 |
| 에이전트 예산/시간 초과 | 부분 결과 저장, Discord 경고 알림 |
| 영상 추적 수집 실패 | `retry` 표시, 다음 날 재시도 (최대 3회) |

### graceful degradation

- 각 수집 소스는 독립적 — 하나 실패해도 나머지는 정상 진행
- trend-analyst는 수집 데이터가 부족해도 기존 볼트 데이터로 기획안 생성 시도
- 에러 발생 시 `~/Desktop/kairos-vault/08-dev/errors/`에 에러 노트 자동 생성 (기존 에러 볼트 워크플로우 연계)

### .obsidianignore 설정

볼트 내 비마크다운 파일의 Obsidian 인덱싱 충돌 방지:

```
.collector/
.lance/
```

## 12. 신규 스킬 체크리스트

Stage 0/4 에이전트에 필요한 신규 스킬 (CLAUDE.md 스킬 추가 규칙 준수):

| 스킬 | 에이전트 | 내용 |
|------|---------|------|
| `market-analysis.md` | trend-analyst, performance-analyst | 트렌드 교차 분석 방법론, 데이터 해석 가이드 |
| `channel-metrics.md` | performance-analyst | YouTube Analytics 지표 해석, 성과 평가 기준 |

각 스킬 추가 시:
- [ ] 스킬 .md 파일 생성 (`auto_agent/data/skills/shared/`)
- [ ] `agents.json` 해당 에이전트 `shared_skills` 배열에 추가
- [ ] `rule_manager.py` `RULE_MANIFEST`에 등록

## 13. 단계적 구현 계획

### Phase 1a — 데이터 기반 (먼저)
- 볼트 디렉토리 구조 셋업 + 템플릿
- `.obsidianignore` 설정
- data-collector 모듈 (YouTube API만)
- vault_writer + 중복 방지 메커니즘 (dedup)
- `auto-agent collect` CLI 명령
- `auto-agent link` CLI 명령 + video_tracking.json
- 환경변수 추가 (`KAIROS_VAULT_DIR`, YouTube OAuth, Discord)

### Phase 1b — 에이전트 + 알림
- trend-analyst 에이전트 (자율 + 시드 모드)
- performance-analyst 에이전트 (영상 추적 + 주간 리뷰)
- 신규 스킬 생성 (market-analysis, channel-metrics)
- agents.json에 에이전트 정의 추가
- Discord 웹훅 알림
- `auto-agent plan` / `auto-agent analyze` CLI 명령
- `auto-agent watchlist` CLI 명령
- `auto-agent project create --from-plan` 연동
- cron 스케줄 설정

### Phase 2 — 확장
- LanceDB 벡터 인덱스 추가
- Google Trends + Naver DataLab 연동
- 소셜 크롤링 (Reddit, X)
- 자동 업로드 기능 (선택)

### Phase 3 — 고도화
- 기획안 품질 개선 (예측 모델)
- A/B 테스트 제안 (썸네일, 제목)
- 채널 성장 전략 리포트

## 14. 기술 의존성

### 새로 추가되는 의존성

```
# YouTube API
google-api-python-client
google-auth-oauthlib

# 트렌드
pytrends            # Google Trends (비공식, 차단 리스크 있음)
# 폴백: SerpAPI Google Trends 엔드포인트 (유료, 안정적)
# Naver DataLab → requests로 직접 호출

# 소셜
praw                # Reddit API
# X API → requests로 직접 호출

# 알림
discord-webhook     # Discord 웹훅

# Phase 2
lancedb             # 벡터 DB
sentence-transformers  # 임베딩 (또는 로컬 모델)
```

### 환경 변수 (.env.example 추가)

```
# YouTube
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

# 소셜
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
X_BEARER_TOKEN=

# 네이버
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# 알림
DISCORD_WEBHOOK_URL=

# 볼트
KAIROS_VAULT_DIR=/path/to/kairos-vault
```
