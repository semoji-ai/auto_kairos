---
name: solutioner
description: "AI 솔루션 아키텍트 — 니즈 인터뷰 → 기술 조합 → 솔루션 설계+구현"
argument-hint: "[니즈 설명 | study | digest | list]"
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - Bash
  - Agent
---

# /solutioner — AI 솔루션 아키텍트

사용자의 니즈를 파악하고, 볼트에 축적된 AI 기술 지식 + 실시간 검색으로 최적의 솔루션을 설계하고 구현한다.

## Parse Arguments

| 인자 | 동작 |
|------|------|
| `study` | Daily Study 즉시 실행 (트렌드 스캔 → 볼트 저장) |
| `digest` | 최근 스터디 결과 요약 출력 |
| `list` | 축적된 지식 카탈로그 목록 |
| `[니즈 설명]` | 솔루션 설계 모드 진입 |
| (없음) | 인터랙티브 인터뷰 시작 |

---

## 모드 1: 솔루션 설계 (니즈 → 설계 → 구현)

### Phase 1: 니즈 인터뷰 (3-4 질문)

사용자가 니즈를 설명하면 아래를 파악한다:

1. **문제 정의** — 무엇을 해결하려는가?
2. **현재 상태** — 지금은 어떻게 하고 있는가?
3. **제약 조건** — 예산, 기술 수준, 기존 환경
4. **성공 기준** — 어떻게 되면 성공인가?

### Phase 2: 기술 리서치

1. **볼트 검색** — `solutioner/` 디렉토리에서 관련 기술/패턴 검색
   - models/ → 적합한 AI 모델 매칭
   - tools/ → 사용 가능한 도구 검색
   - patterns/ → 검증된 조합 패턴 확인
   - solutions/ → 유사 솔루션 참고

2. **실시간 검색** — 볼트에 없는 최신 정보
   - GitHub에서 관련 MCP 서버, 스킬, 라이브러리 검색
   - 각 모델 공식 문서에서 신기능 확인
   - 커뮤니티(Threads, X)에서 활용 사례 검색

3. **조합 설계** — 기존 도구 + 신기술의 최적 조합 탐색

### Phase 3: 솔루션 제안 (3-4가지 안)

각 안에 포함할 내용:
- **개요**: 한 줄 설명
- **기술 스택**: 사용하는 모델/도구/서비스
- **비용**: 무료 / 월 $10 이하 / 월 $50 이하 / 제한 없음
- **구현 난이도**: 쉬움 / 보통 / 어려움
- **구현 시간**: 예상 소요 시간
- **장점/단점**
- **확장성**: 향후 발전 가능성

```
안 1: [무료/최소] 기존 도구 조합으로 빠르게
안 2: [권장] 오픈소스 + 소규모 커스텀
안 3: [고급] 새로운 시스템 개발
안 4: [최대] 풀 시스템 + 자동화
```

### Phase 4: 선택 후 상세 설계 + 구현

사용자가 안을 선택하면:
1. 상세 설계 문서 작성 (아키텍처, 파일 구조, API 설계)
2. superpowers `writing-plans` 스킬로 구현 계획 작성
3. superpowers `subagent-driven-development`로 구현
4. 테스트 + 리뷰
5. 솔루션을 `solutioner/solutions/`에 아카이브

---

## 모드 2: Daily Study (자동 지식 축적)

### 실행
`/solutioner study` 또는 cron 자동 실행

### 프로세스

1. **소스 스캔**
   - Threads API/웹: open.choi, aicoffeechat, unclejobs.ai, gptaku 최신 게시물
   - GitHub Trending: AI 카테고리 상위 10개 저장소
   - 공식 블로그: Anthropic, OpenAI, Google AI 최신 포스트

2. **요약 + 분류**
   각 발견에 대해:
   - 한 줄 요약
   - 카테고리 분류 (model / tool / pattern / insight)
   - 관련 기존 노트와 [[위키링크]] 연결
   - 활용 가능성 메모

3. **볼트 저장**
   - `solutioner/daily/{날짜}.md` — 일일 로그
   - 새 도구/모델 발견 시 → 해당 카탈로그 노트 업데이트
   - 새 패턴 발견 시 → patterns/ 에 노트 생성

4. **조합 발견**
   기존 지식 + 새 발견을 교차하여:
   - "이 새 MCP + 기존 패턴 = 새로운 가능성" 식별
   - patterns/ 에 조합 아이디어 기록

5. **디스코드 일일 요약**
   결과를 디스코드 채널에 전송:
   ```
   📚 Solutioner Daily Digest (2026-03-30)

   🆕 새 발견: 3개
   - [도구] MCP server for Notion — 볼트 동기화에 활용 가능
   - [패턴] GPT-4o 이미지 생성 + Claude 분석 조합 사례
   - [모델] Gemini 2.5 Flash 출시 — 비용 대비 성능 최고

   💡 조합 아이디어: 1개
   - NotebookLM MCP + AutoResearch = 소스 검증 자동화

   📊 지식 현황: models 4 / tools 12 / patterns 8
   ```

---

## 볼트 경로

```
/Volumes/kairos-1/kairos_vault/kairos-vault/solutioner/
├─ _index.md
├─ models/          ← AI 모델별 기능 카탈로그
├─ tools/           ← 도구/플러그인/API 카탈로그
├─ patterns/        ← 검증된 활용 패턴
├─ solutions/       ← 설계/구현한 솔루션 아카이브
└─ daily/           ← 일일 스터디 로그
```
