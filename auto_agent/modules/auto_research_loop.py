"""카파시 AutoResearch 패턴 적용 — Stage 0 자율 주제 탐색 루프.

핵심 원칙 (Karpathy Loop):
1. program.md → research_directive.md (채널 정체성/방향)
2. 단일 지표 → topic_score (trend_velocity × competition_gap × channel_fit)
3. 래칫 → 기존 최고 점수 이상만 후보 풀에 추가
4. 고정 예산 → 라운드당 시간 제한
5. 에러→재시도 → 검색 실패 시 다른 각도로 재탐색
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_vault_dir, get_data_dir

logger = logging.getLogger(__name__)

DEFAULT_DIRECTIVE = """# Research Directive

## 채널 정체성
- 이로미즘: 경제/시사 심층 분석, 데이터 기반, 10-15분 포맷
- 세모지: 교양/퀴즈, 가벼운 톤, 5-10분 포맷

## 선호 주제
- 시의성 높은 경제/시사 이슈
- 데이터로 검증 가능한 주장
- 대중적 관심사와 전문 분석의 교차점

## 금지 주제
- 정치적 편향이 강한 주제
- 검증 불가능한 루머/추측
- 저작권 침해 소지가 있는 콘텐츠

## 차별화 원칙
- "모두가 아는 사실"이 아닌 "새로운 시각" 제공
- 숫자와 데이터로 뒷받침
- 결론이 아닌 사고 과정을 보여주기
"""

SCORING_PROMPT = """## 주제 점수 산정 기준

각 주제 후보에 대해 아래 3가지 축으로 1-10점 평가 후 곱셈 점수를 산출하세요.

### 1. trend_velocity (트렌드 속도) — 1~10
- 10: 검색량 급등 초기 (전주 대비 +100%), 아직 경쟁자 없음
- 7-9: 상승 추세, 일부 매체 보도 시작
- 4-6: 안정적 관심, 롱테일 가치
- 1-3: 하락 추세 또는 이미 피크 지남

### 2. competition_gap (경쟁 갭) — 1~10
- 10: 한국어 YouTube에 관련 영상 0개
- 7-9: 1-3개 존재하나 깊이 부족
- 4-6: 5-10개 존재, 차별화 각도 필요
- 1-3: 이미 포화, 차별화 어려움

### 3. channel_fit (채널 적합도) — 1~10
- 10: 채널 핵심 포지셔닝과 완벽 일치 + 과거 유사 주제 고성과
- 7-9: 포지셔닝 일치 + 시청층 관심사 부합
- 4-6: 약간 벗어나지만 가능
- 1-3: 채널 정체성과 불일치

### 최종 점수
topic_score = trend_velocity × competition_gap × channel_fit (최대 1000)

### 래칫 규칙
- 현재 라운드 최고 점수(ratchet_score)보다 높은 후보만 풀에 추가
- 초기 ratchet_score = 0
- 각 라운드 후 최고 점수로 ratchet 갱신
"""


class AutoResearchLoop:
    """카파시 AutoResearch 패턴 기반 Stage 0 자율 루프."""

    def __init__(self, channel: str, max_rounds: int = 5, seed: Optional[str] = None):
        self._channel = channel
        self._max_rounds = max_rounds
        self._seed = seed
        self._vault_dir = get_vault_dir()
        self._data_dir = get_data_dir()
        self._candidates: List[Dict] = []
        self._ratchet_score: float = 0
        self._round = 0

    def build_loop_prompt(self) -> str:
        """전체 루프를 실행하는 에이전트 프롬프트 생성."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        directive = self._load_directive()
        skill_content = self._load_skill("agents/trend-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["market-analysis"])
        existing_candidates = self._load_existing_candidates()

        seed_instruction = ""
        if self._seed:
            seed_instruction = f"""
## 시드 키워드
"{self._seed}" — 이 키워드를 출발점으로 관련 주제를 탐색하되,
파생 주제와 다른 각도도 포함하세요."""

        return f"""# AutoResearch Loop — Stage 0 주제 탐색

날짜: {today}
채널: {self._channel}
최대 라운드: {self._max_rounds}

## 카파시 AutoResearch 프로토콜

당신은 자율 주제 탐색 에이전트입니다. 아래 루프를 {self._max_rounds}회 반복하세요.

### 매 라운드 수행 절차:
1. **스캔**: WebSearch로 최신 트렌드 검색 (YouTube 인기, 뉴스, 커뮤니티)
2. **후보 생성**: 3-5개 주제 후보를 생성 (제목 + 차별화 각도 + 핵심 훅)
3. **경쟁 분석**: 각 후보에 대해 YouTube 검색으로 기존 영상 확인
4. **점수 산정**: 아래 기준으로 topic_score 계산
5. **래칫 필터**: ratchet_score({self._ratchet_score}) 이상만 후보 풀에 추가
6. **다음 라운드**: 이전 라운드에서 높은 점수 영역을 더 깊이 탐색

### 라운드 간 전략:
- 라운드 1: 넓게 스캔 (다양한 카테고리)
- 라운드 2-3: 고점수 영역 심화 (관련 키워드 파생)
- 라운드 4-5: 최고 후보 정밀 검증 (경쟁 영상 실제 조회수 확인)
{seed_instruction}

{SCORING_PROMPT}

## Research Directive
{directive}

## 볼트 내 기존 데이터
- 채널 성과: channels/{self._channel}/videos/
- 경쟁 채널: channels/competitors/
- 기존 피드백: insights/feedback/
- 트렌드: market/trends/

{f"## 기존 후보 (이전 실행에서 발견)" if existing_candidates else ""}
{existing_candidates}

## 최종 출력 — MERGE 규칙 (중요!)

모든 라운드 완료 후 결과를 저장하세요.

**⚠️ 기존 파일이 있으면 반드시 먼저 읽고, 기존 candidates에 새 candidates를 병합(merge)하세요.**
- 기존 파일: `insights/planning/{today}-{self._channel}-autoresearch.json`
- 있으면: 기존 JSON을 읽고, 기존 candidates + 새 candidates 합침
- 중복 제거: 같은 title이면 점수가 높은 쪽 유지
- ratchet_score: 기존과 새 것 중 높은 값 유지
- 없으면: 새로 생성

1. **insights/planning/{today}-{self._channel}-autoresearch.json** — 구조화된 후보 데이터 (누적)
```json
{{
  "date": "{today}",
  "channel": "{self._channel}",
  "rounds_completed": N,
  "ratchet_score": 최종래칫점수,
  "candidates": [
    {{
      "rank": 1,
      "title": "주제 제목",
      "angle": "차별화 각도",
      "hook": "핵심 훅 (시청자를 끌어당기는 한 줄)",
      "trend_velocity": 8,
      "competition_gap": 7,
      "channel_fit": 9,
      "topic_score": 504,
      "sources": ["검색에서 발견한 근거 URL"],
      "competition_videos": ["경쟁 영상 제목 + 채널 + 조회수"],
      "round_discovered": 1
    }}
  ]
}}
```

2. **insights/planning/{today}-{self._channel}-기획안.md** — 상위 3개 기획안 (마크다운, 병합된 전체 후보 기준 재정렬)

{skill_content}

{shared_skills}
"""

    def _load_directive(self) -> str:
        """채널별 research_directive.md 로드. 없으면 기본값."""
        path = self._vault_dir / "channels" / self._channel / "research_directive.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        # 기본 directive 생성
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_DIRECTIVE, encoding="utf-8")
        logger.info("기본 research_directive.md 생성: %s", path)
        return DEFAULT_DIRECTIVE

    def _load_existing_candidates(self) -> str:
        """이전 실행의 후보 데이터가 있으면 로드."""
        planning_dir = self._vault_dir / "insights" / "planning"
        if not planning_dir.exists():
            return ""

        # 최근 7일간의 autoresearch 결과 검색
        candidates = []
        for f in sorted(planning_dir.glob(f"*-{self._channel}-autoresearch.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for c in data.get("candidates", [])[:3]:
                    candidates.append(f"- [{c['topic_score']}점] {c['title']} — {c['angle']}")
                if candidates:
                    self._ratchet_score = max(
                        self._ratchet_score,
                        max(c.get("topic_score", 0) for c in data.get("candidates", [{"topic_score": 0}]))
                    )
                break  # 최근 1개만
            except (json.JSONDecodeError, KeyError):
                continue

        if candidates:
            return "이전 고점수 후보:\n" + "\n".join(candidates) + f"\n\n래칫 점수: {self._ratchet_score} (이 점수 이상만 추가)"
        return ""

    def _load_skill(self, relative_path: str) -> str:
        path = self._data_dir / "skills" / relative_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def _load_shared_skills(self, skill_names: List[str]) -> str:
        parts = []
        for name in skill_names:
            content = self._load_skill(f"shared/{name}.md")
            if content:
                parts.append(content)
        return "\n\n---\n\n".join(parts)
