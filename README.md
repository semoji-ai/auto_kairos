# Auto Kairos

AI Video Production Pipeline — 리서치부터 렌더링까지 자동화

Claude Code + Remotion 기반 영상 제작 파이프라인. 주제만 입력하면 리서치, 원고, 씬 설계, TTS, 이미지, 자막, 렌더링까지 자동으로 처리합니다.

## 설치

### macOS / Linux / WSL

```bash
git clone https://github.com/jleavens01/auto_kairos.git
cd auto_kairos
./install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/jleavens01/auto_kairos.git
cd auto_kairos
.\install.ps1
```

### 필요 환경

| 도구 | 버전 | 용도 | 설치 스크립트가 자동 설치 |
|------|------|------|:---:|
| Python | 3.10+ | 파이프라인 엔진 | O |
| Node.js | 18+ | Remotion 렌더링 | O |
| ffmpeg | - | 오디오/비디오 처리 | O |
| Claude Code | 최신 | AI 에이전트 실행 | 수동 |

## 워크스페이스 설정

### 새 프로젝트

```bash
auto-kairos init ~/my-video-project
cd ~/my-video-project
```

### 기존 v2 워크스페이스 업그레이드

```bash
auto-kairos init ~/my-video-project --upgrade
```

기존 `output/`, `.env`, `auto_agent.db`는 보존됩니다. Remotion 컴포넌트와 CLAUDE.md만 v3로 업데이트됩니다.

### API 키 설정

```bash
cd ~/my-video-project
cp .env.example .env
# .env 파일을 편집하여 API 키를 입력하세요
```

| API | 용도 | 필수 |
|-----|------|:---:|
| `ELEVENLABS_API_KEY` | TTS 음성 생성 | O |
| `OPENAI_API_KEY` | 자막 동기화 (Whisper) | O |
| `FAL_API_KEY` | AI 이미지 생성 | 선택 |
| `SERPER_API_KEY` | 웹 리서치 검색 | 선택 |
| `GOOGLE_API_KEY` | 팩트체크 (Gemini) | 선택 |

## 사용법

### Claude Code로 실행 (권장)

```bash
cd ~/my-video-project
claude
```

Claude Code가 CLAUDE.md를 읽고 파이프라인 실행 방법을 자동으로 안내합니다.

### CLI 직접 실행

```bash
# 프로젝트 생성
auto-kairos project create "나스닥100 투자 가이드" --topic "나스닥100 ETF 투자 전략"

# 아트스타일/음성 설정
auto-kairos style list
auto-kairos config set art_style semoji --project 나스닥100_투자_가이드
auto-kairos voice list
auto-kairos config set voice "차분한 남성" --project 나스닥100_투자_가이드

# 파이프라인 실행 (에셋 생산~렌더링)
auto-kairos run --project 나스닥100_투자_가이드 --from step_7

# 대시보드
auto-kairos dashboard --port 8080
```

## 파이프라인 구조

```
Phase 0: 프로젝트 설정 (CLI)
Phase 1: 리서치 → 원고 → 팩트체크 (Claude Code)
Phase 2: 씬 설계 + Creative Direction (Claude Code)
Phase 3: TTS → 이미지 → 자막 → 매니페스트 (auto-kairos run)
Phase 4: Remotion 렌더링 → 최종 영상 (auto-kairos run)
```

### 에이전트 구성

| 에이전트 | 역할 | 모델 |
|---------|------|------|
| research-orchestrator | 심층 리서치 + 보고서 | Opus |
| write-manuscript | 아웃라인 + 나레이션 원고 | Opus |
| fact-verifier | 팩트체크 | Sonnet |
| visual-composer | 씬 설계 + 에셋 추천 + 모션 | Opus |
| character-planner | 캐릭터 추출 + 변이 분석 | Sonnet |
| qa-reviewer | 최종 품질 검수 | Sonnet |

## 대시보드

```bash
auto-kairos dashboard --port 8080
```

웹 브라우저에서 `http://localhost:8080`으로 접속합니다.

- **Overview**: 파이프라인 진행률, 에셋 현황
- **Storyboard**: 씬별 미리보기, 편집
- **Studio**: Remotion Studio + 씬 편집 모달
- **Design**: 테마/컬러/애니메이션 프리셋 관리

## 업데이트

```bash
cd auto_kairos
git pull
pip install -e .[all]

# 워크스페이스 Remotion 업데이트
auto-kairos init ~/my-video-project --upgrade
```

## 프로젝트 구조

```
auto_kairos/
├── auto_agent/              # Python 패키지
│   ├── cli.py               # CLI 엔트리포인트
│   ├── data/
│   │   ├── skills/          # AI 에이전트 스킬 (19개)
│   │   ├── pipeline.json    # 파이프라인 정의
│   │   └── agents.json      # 에이전트 설정
│   ├── dashboard/           # 웹 대시보드 (FastAPI)
│   ├── orchestrator/        # 파이프라인 오케스트레이터
│   ├── scripts/             # 빌드/생성 스크립트
│   └── remotion_template/   # Remotion 프로젝트 템플릿
│       └── src/
│           ├── simple/      # CreativeScene + BuildingBlocks
│           ├── map/         # MapSceneRenderer + 10개 테마
│           └── editor/      # 씬 에디터 (React)
├── install.sh               # macOS/Linux 설치
├── install.ps1              # Windows 설치
└── pyproject.toml           # 패키지 설정
```

## 라이선스

MIT
