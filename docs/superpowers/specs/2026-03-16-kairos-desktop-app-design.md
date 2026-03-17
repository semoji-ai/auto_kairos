# Kairos App — AI 에이전트 팀 기반 영상 제작 스튜디오

> 크로스플랫폼 데스크톱 앱. 전문가 에이전트와 기획부터 함께하고,
> 상설 기획팀/제작팀/유통팀이 파이프라인을 실행하며,
> WYSIWYG 스튜디오에서 결과물을 다듬는다.
> 자체 렌더 엔진과 토큰 기반 디자인 시스템으로,
> 템플릿 교체만으로 영상 톤이 바뀌고,
> 하나의 소스에서 블로그·카드뉴스·쇼츠·웹툰 등 멀티포맷으로 파생된다.

**날짜**: 2026-03-16
**상태**: 설계 완료, 구현 대기

---

## 1. 사용자 범위

- **1단계**: 본인용 (개인 도구)
- **2단계**: 크리에이터/유튜버에게 배포하는 프로덕트

---

## 2. 전체 아키텍처

```
Electron App (Vite + React 18 + TypeScript)
│
├── 렌더러 프로세스 (React)
│   ├── 대시보드
│   │   ├── 컨설팅룸 (전문가와 주제 기획, 프로젝트 생성 전)
│   │   ├── 프로젝트 관리
│   │   ├── 원고/스토리보드 에디터
│   │   ├── 파이프라인 모니터 + 에이전트 오피스 (픽셀 캐릭터)
│   │   └── 에셋/비용 관리
│   │
│   ├── 스튜디오
│   │   ├── 씬 캔버스 (WYSIWYG + 속성 패널)
│   │   ├── 타임라인 (씬 클릭 → 캔버스에서 바로 편집)
│   │   └── 편집 모드 3단계 (타임라인/씬/슬롯)
│   │
│   └── 템플릿 마켓
│       └── 레이아웃 + 테마 + 모션 조합
│
├── 메인 프로세스 (Node.js)
│   ├── KairosEngine (자체 렌더 엔진)
│   ├── LLM CLI 매니저 (subprocess)
│   ├── Pipeline Bridge (Python ↔ Node.js)
│   └── Asset Manager
│
└── Python 서브프로세스 (기존 auto_agent 파이프라인 그대로)
```

### 핵심 원칙

- **3계층 분리**: React UI → Node.js 메인 → Python 파이프라인
- **기존 Python 파이프라인은 건드리지 않음**: subprocess로 호출
- **Pipeline Bridge**: JSON stdout/stderr + 파일시스템 통신 (기존 방식 활용)

---

## 3. 에이전트 시스템

### 3.1 팀 구조

```
┌──────────────────────────────────────────────────┐
│  💼 컨설팅룸 (프로젝트 생성 전)                    │
│     사용자 + 외부 전문가 → 주제 기획               │
│         ↓                                         │
│  🏢 기획팀 (상설)                                  │
│  ├── 리서치 오케스트레이터                          │
│  ├── 작가                                         │
│  ├── 팩트체커                                      │
│  └── + 외부 전문가 (도메인 지식 + 검증)             │
│         ↓                                         │
│  🎬 제작팀 (상설)                                  │
│  ├── 비주얼 컴포저                                 │
│  ├── 캐릭터 플래너                                 │
│  └── QA 리뷰어                                    │
│         ↓                                         │
│  📡 유통팀 (상설)                                  │
│  ├── 포맷 어댑터 (원본 → 각 포맷 변환 전략)         │
│  ├── 카피라이터 (포맷별 카피, 썸네일, 훅)           │
│  └── 스케줄러 (플랫폼별 최적 발행 타이밍)           │
└──────────────────────────────────────────────────┘
```

### 3.2 외부 전문가

- **프로젝트 기획 단계부터 참여** (컨설팅룸에서 주제 탐색, 방향 설정)
- 기획팀 리서치에 합류하여 도메인 지식 + 팩트체크 수행
- 에이전트 = 시스템 프롬프트 + 스킬셋 + 도구 권한 + 페르소나(픽셀 스프라이트)
- 예: 투자전문가, 역사학자, 의학전문가, 과학해설가 등

### 3.3 에이전트 오피스 UI

- 파이프라인 모니터 아래에 픽셀아트 사무실 배치
- 상설팀 = 실선 박스, 투입된 전문가 = 점선 박스
- 에이전트 상태: 작업중(애니메이션), 대기(idle), 완료(체크)
- 에이전트 클릭 → 해당 로그/진행상황 펼침
- 실시간 메시지 버블 표시

---

## 4. KairosEngine (자체 렌더 엔진)

### 4.1 Remotion에서 계승하는 것

| 원리 | 설명 |
|---|---|
| `useCurrentFrame()` | 프레임 번호로 모든 것을 계산 |
| React 컴포넌트 = 씬 | 선언적 UI |
| `Sequence`, `Composition` | 씬 시퀀싱, 컴포지션 구조 |

### 4.2 Remotion에서 개선하는 것

| 문제 | 해결 |
|---|---|
| 레이아웃을 CSS로 하드코딩 → 코드 비대화 | 슬롯 기반 레이아웃 시스템 |
| manifest ↔ 컴포넌트 타입 불일치 | 단일 스키마에서 양쪽 자동 생성 |
| Remotion Studio 별도 프로세스 | 앱 내장 에디터 |
| 씬 편집하려면 코드 에디터 필요 | WYSIWYG 캔버스에서 직접 편집 |
| 전체 영상 매번 렌더 | 씬 단위 독립 재생/렌더 |

### 4.3 슬롯 기반 레이아웃

```json
{
  "layout": "split-left",
  "slots": {
    "visual": { "x": 0, "y": 0, "w": "50%", "h": "100%" },
    "headline": { "x": "55%", "y": "10%", "w": "40%", "h": "auto" },
    "items": { "x": "55%", "y": "40%", "w": "40%", "h": "50%" },
    "source": { "x": "55%", "y": "92%", "w": "40%", "h": "auto" }
  }
}
```

에디터에서 슬롯 드래그 → 레이아웃 JSON 자동 업데이트 → 즉시 프리뷰 반영.

### 4.4 렌더링 파이프라인

```
manifest.json → KairosEngine (React 프레임 시퀀서)
                    ↓ useCurrentFrame() 기반
              React DOM → 프레임별 스냅샷 (Playwright)
                    ↓
              ffmpeg (프레임 시퀀스 → MP4 + 오디오 믹스)
                    ↓
              output.mp4
```

### 4.5 포맷별 렌더러 (유통팀 연동)

```
KairosEngine
├── VideoRenderer    → MP4 (롱폼, 쇼츠, 릴스)
├── ImageRenderer    → PNG 시퀀스 (카드뉴스, 썸네일)
├── TextRenderer     → Markdown/HTML (블로그, 뉴스레터)
├── ThreadRenderer   → 스레드 포맷 (트위터/X 체인)
└── ComicRenderer    → 웹툰 패널 레이아웃
```

같은 씬 데이터를 각 렌더러가 포맷에 맞게 재해석.

---

## 5. 디자인 시스템 (Pencil 원리 차용)

### 5.1 토큰 3단계

```
primitive   → #FF6B35, 16px, 400 (원시값)
semantic    → accent, body-size, normal (의미 부여)
component   → headline-color, chart-bar-fill, item-spacing (컴포넌트 바인딩)
```

- 토큰 변경 → 전체 영상에 즉시 반영
- 컴포넌트 코드는 토큰만 참조, 값을 직접 참조하지 않음

### 5.2 템플릿 = 3레이어 조합

```
템플릿 = 레이아웃 + 테마 + 모션

레이아웃: centered, split-left, grid-2x2, full-visual, data-dashboard
테마:     세모지(파스텔), 다큐(진지), 투자리포트(깔끔), 이로미즘(quirky)
모션:     fade, slide, bounce, cinematic, minimal
```

각 레이어가 독립적 → 레이아웃 유지하면서 테마만 교체, 테마 유지하면서 모션만 변경 가능.

### 5.3 에디터에서의 토큰 편집

- 씬 캔버스에서 요소 선택 → 속성 패널에 토큰 표시
- 토큰 값 변경 → 모든 씬에 즉시 반영
- 특정 씬만 오버라이드 가능

---

## 6. 타입 안전 시스템

### 6.1 단일 스키마 (kairos-schema.ts)

```typescript
type Scene = {
  sceneNumber: number
  layout: LayoutType
  slots: Record<SlotName, SlotContent>
  motion: MotionPreset
  audio: { src: string; duration_ms: number }
  subtitle?: { src: string }
}

type SlotContent =
  | { type: "headline"; text: string; style: TextStyle }
  | { type: "items"; items: BulletItem[] }
  | { type: "viz"; vizType: VizType; data: VizData }
  | { type: "image"; src: string; crop: CropRect }
```

### 6.2 양쪽 자동 생성

```
kairos-schema.ts (단일 진실)
    ├── → Python 검증기 (JSON Schema export)
    └── → React 컴포넌트 타입 (TypeScript)
```

파이프라인이 잘못된 씬 생성 → Python 검증기에서 즉시 거부. 런타임 에러 원천 차단.

---

## 7. LLM CLI 통합

### 7.1 구조

- 앱은 LLM을 직접 호출하지 않음
- 사용자가 설치한 CLI (Claude Code / Gemini / Codex)를 subprocess로 호출
- 사용자 본인 구독, 본인 인증 → 정책 문제 없음

### 7.2 설정

```json
{
  "llm": {
    "provider": "claude-code",
    "binary": "/usr/local/bin/claude",
    "verified": true
  }
}
```

앱 시작 시 `which claude` → 바이너리 존재 확인 → stdout/stderr 스트리밍으로 실시간 모니터.

---

## 8. 스튜디오 인터랙션

### 8.1 레이아웃

```
┌────────────────────────────────┬─────────────┐
│  씬 캔버스 (실시간 프리뷰)      │ 속성 패널    │
│  - 텍스트 더블클릭 → 인라인 편집│ - 텍스트 내용│
│  - 요소 드래그 → 위치 이동      │ - 폰트/크기 │
│  - 슬롯 경계 드래그 → 크기 조절 │ - 색상/토큰 │
│                                │ - 레이아웃  │
│                                │ - 모션 프리셋│
├────────────────────────────────┴─────────────┤
│  타임라인                                      │
│  [S1][S2][S3][S4 ✎][S5][S6][S7]               │
│  🔊 오디오 웨이브폼                             │
│  💬 자막 트랙                                   │
│  [◀] [▶ 재생] [S4만 재생] [전체 프리뷰]         │
└────────────────────────────────────────────────┘
```

### 8.2 편집 모드 3단계

1. **타임라인 모드** — 씬 순서, 길이 조절, 전체 흐름 확인
2. **씬 편집 모드** — 씬 클릭하면 진입, 슬롯 내 콘텐츠 편집
3. **슬롯 편집 모드** — 레이아웃 자체 변경 (슬롯 위치/크기/추가)

ESC로 상위 모드 복귀. 타임라인을 벗어나지 않고 클릭 깊이로 편집 범위 전환.

---

## 9. 유통 시스템

### 9.1 멀티포맷 파생

하나의 프로젝트 소스(리서치 + 원고 + 에셋)에서:

| 포맷 | 출력 | 설명 |
|---|---|---|
| 롱폼 | MP4 (10~15분) | 유튜브 본편 |
| 쇼츠/릴스 | MP4 (60초) | 하이라이트 추출 |
| 블로그 | Markdown/HTML | 원고 기반 텍스트 |
| 카드뉴스 | PNG 시퀀스 | 핵심 장면 추출 |
| 스레드 | 텍스트 체인 | 요약 → 트윗 체인 |
| 뉴스레터 | HTML | 구독자용 요약 |
| 웹툰 | 이미지 시퀀스 | 캐릭터 + 스토리 재구성 |

### 9.2 유통팀 에이전트

- **포맷 어댑터**: 원본 콘텐츠를 각 포맷 요구사항에 맞게 변환 전략 수립
- **카피라이터**: 포맷별 카피 (썸네일 제목, 스레드 훅, 블로그 SEO 등)
- **스케줄러**: 플랫폼별 최적 발행 타이밍 추천

---

## 10. 에러 시스템

### 10.1 방어 계층

1. **스키마 검증** — 저장 시 즉시 경고 (렌더 전 차단)
2. **에디터 시각 경고** — 빈 슬롯, 누락 에셋 시각 표시 + 대체 자동 제안
3. **에이전트 오피스 알림** — 무한루프/타임아웃 → 원클릭 중단
4. **API 실패 복구** — 에셋 상태 표시 + 자동 재시도/스킵 선택

### 10.2 에러 수집 서버

- Supabase Edge Functions 기반
- 익명화 옵트인 (에러 타입, manifest 구조, OS/앱 버전만 수집)
- 콘텐츠 내용, API 키, 사용자 정보 수집하지 않음
- 에러 패턴 분석 → 스키마 검증 규칙 추가 → 앱 업데이트에 반영

---

## 11. 기술 스택

| 영역 | 기술 | 이유 |
|---|---|---|
| 데스크톱 프레임워크 | Electron + Vite | 빠른 빌드, React 생태계 |
| UI | React 18 + TypeScript | 기존 Remotion 코드 재활용 |
| 상태관리 | Zustand | 가볍고 에디터 상태에 적합 |
| 에디터 캔버스 | React + DOM 기반 | HTML/CSS 렌더링 (Remotion 원리 계승) |
| 타임라인 | Canvas 2D | 성능, 오디오 웨이브폼 |
| 프레임 캡처 | Playwright | 크로스플랫폼, 안정적 |
| 영상 인코딩 | ffmpeg (번들) | 프레임 → MP4 |
| DB | SQLite (better-sqlite3) | 기존 스키마 호환 |
| 에러 수집 | Supabase | 이미 사용 중 |
| 파이프라인 | Python (기존 그대로) | 건드리지 않음 |
| 빌드/배포 | electron-builder | Mac DMG + Windows NSIS |

---

## 12. 모노레포 구조

```
kairos-app/
├── package.json                  (모노레포 루트, npm workspaces)
│
├── packages/
│   ├── engine/                   KairosEngine (자체 렌더 엔진)
│   │   ├── core/                 useCurrentFrame, Sequence, Composition
│   │   ├── renderer/             Playwright 프레임 캡처 + ffmpeg
│   │   ├── schema/               kairos-schema.ts (단일 진실)
│   │   └── formats/              VideoRenderer, ImageRenderer, TextRenderer...
│   │
│   ├── editor/                   씬 에디터 + 타임라인
│   │   ├── canvas/               WYSIWYG 씬 캔버스
│   │   ├── timeline/             타임라인 + 오디오 트랙
│   │   ├── properties/           우측 속성 패널
│   │   └── slots/                슬롯 드래그/리사이즈
│   │
│   ├── templates/                레이아웃 + 테마 + 모션 프리셋
│   │   ├── layouts/
│   │   ├── themes/
│   │   └── motions/
│   │
│   ├── dashboard/                프로젝트 관리 + 파이프라인 모니터
│   │   ├── projects/
│   │   ├── consulting/           전문가 컨설팅룸
│   │   ├── manuscript/           원고 에디터
│   │   ├── storyboard/
│   │   ├── pipeline/             파이프라인 모니터
│   │   └── office/               에이전트 오피스 (픽셀 UI)
│   │
│   └── core/                     공유 유틸
│       ├── cli-manager/          LLM CLI subprocess 관리
│       ├── pipeline-bridge/      Python ↔ Node.js 통신
│       ├── error-reporter/       에러 수집 + 서버 전송
│       └── db/                   SQLite 래퍼
│
├── electron/                     Electron 메인 프로세스
│   ├── main.ts
│   ├── preload.ts
│   └── ipc/
│
├── pipeline/                     기존 Python 파이프라인 (심볼릭 링크)
│
└── server/                       에러 수집 서버 (Supabase Edge Functions)
```

---

## 13. 마이그레이션 경로

```
현재  → CLI + 웹 대시보드로 영상 계속 제작 (변화 없음)
1단계 → Electron 껍질 + 기존 파이프라인 연결
2단계 → 대시보드 React 재작성 + 에이전트 오피스
3단계 → 스튜디오 (타임라인 + 씬 에디터)
4단계 → KairosEngine (자체 렌더, Remotion 제거)
5단계 → 토큰 디자인 시스템 + 템플릿 마켓
6단계 → 유통팀 + 멀티포맷 렌더러
7단계 → 전문가 마켓플레이스 + 에러 수집 서버
```

어느 단계에서든 기존 CLI 방식으로 영상 제작 가능. 새 앱과 기존 CLI가 같은 워크스페이스 공유.

---

## 14. 테스트 전략

### 단위 테스트
- KairosEngine: 프레임 시퀀싱, 타이밍 계산
- 스키마 검증기: 유효/무효 manifest 케이스
- 슬롯 레이아웃: 배치 계산, 오버플로우 처리
- 토큰 시스템: 3단계 해석, 오버라이드

### 통합 테스트
- CLI 매니저 → subprocess 호출 → 결과 파싱
- Pipeline Bridge → Python ↔ Node.js 통신
- manifest 생성 → 렌더 엔진 → 프레임 출력
- 포맷별 렌더러 → 동일 소스 → 각 포맷 출력 검증

### E2E 테스트 (Playwright)
- 프로젝트 생성 → 파이프라인 실행 → 결과 확인
- 에디터에서 씬 수정 → 프리뷰 반영 확인
- 타임라인 씬 순서 변경 → 렌더 출력 검증
- 토큰 변경 → 전체 씬 반영 확인
