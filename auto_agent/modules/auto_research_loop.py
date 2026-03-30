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

### 래칫 규칙 (Top 5 교체 방식)
- 기존 후보 풀의 **Top 5 중 최저 점수**가 래칫 기준
- 새 후보가 래칫 이상이면 Top 5에 진입 (최저 점수 후보를 밀어냄)
- 래칫은 새로운 Top 5의 최저 점수로 갱신
- 초기 ratchet_score = 0 (후보가 5개 미만이면 무조건 추가)
- 이 방식으로 후반 라운드에서도 Top 5가 계속 갱신됨
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
5. **래칫 필터**: Top 5 최저 점수({self._ratchet_score}) 이상이면 Top 5에 진입 (최저를 밀어냄)
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

## 최종 출력 — MERGE 규칙 (간결하게!)

결과 파일: `insights/planning/{today}-{self._channel}-autoresearch.json`

**기존 파일이 있으면:** 읽고 → 기존 candidates + 새 candidates 합침 → 같은 title은 높은 점수 유지 → Top 10만 남기고 나머지 삭제 → 저장
**없으면:** 새로 생성

1. **insights/planning/{today}-{self._channel}-autoresearch.json**
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
      "round_discovered": 1,
      "creative_brief": {{
        "core_angle": "이 주제를 왜 이 각도로 다뤄야 하는지 한 줄",
        "tone": "영상 톤 (긴박감/유머/감동/분석적 등)",
        "target_audience": "타겟 시청자 (연령/관심사)",
        "differentiation": "경쟁 채널과 어떻게 차별화하는지",
        "recommended_structure": "추천 구성 (3막/연대기/미스터리 등)",
        "recommended_length": "추천 영상 길이",
        "key_data_points": ["반드시 포함해야 할 핵심 데이터/팩트"],
        "urgency": "시의성 (D-N, 언제까지 발행해야 유효한지)"
      }}
    }}
  ]
}}
```

2. **insights/planning/{today}-{self._channel}-기획안.md** — 상위 3개 기획안 (마크다운, 병합된 전체 후보 기준 재정렬)

각 기획안에 반드시 **크리에이티브 브리프** 포함:
```
📋 크리에이티브 브리프:
  - 핵심 앵글: 왜 이 각도인지
  - 톤: 채널 성격에 맞는 톤 지정
  - 타겟 시청자: 연령/관심사
  - 차별화: 경쟁 채널 대비 우리만의 포인트
  - 추천 구성: 몇 막, 어떤 흐름
  - 추천 길이: 몇 분
  - 핵심 데이터: 반드시 포함할 팩트/수치
  - 긴급도: 언제까지 발행해야 유효한지
```
이 브리프가 있으면 팀원이 Stage 1~3을 돌릴 때 방향성을 잃지 않습니다.

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

        # 최근 7일간의 autoresearch 결과 검색 (NAS NFD 인코딩 대응)
        import unicodedata
        channel_nfc = unicodedata.normalize("NFC", self._channel)
        candidates = []
        all_scores = []
        for f in sorted(
            [x for x in planning_dir.glob("*-autoresearch.json")
             if channel_nfc in unicodedata.normalize("NFC", x.name)],
            reverse=True,
        ):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                for c in data.get("candidates", []):
                    score = c.get("topic_score", 0)
                    all_scores.append(score)
                    candidates.append(f"- [{score}점] {c['title']} — {c.get('angle', '')}")
                break  # 최근 1개만
            except (json.JSONDecodeError, KeyError):
                continue

        # Top 5 최저 점수를 래칫으로 설정
        if all_scores:
            top5_scores = sorted(all_scores, reverse=True)[:5]
            self._ratchet_score = top5_scores[-1] if len(top5_scores) >= 5 else 0

        if candidates:
            top5_text = "\n".join(candidates[:5])
            return (
                f"이전 Top 5 후보:\n{top5_text}\n\n"
                f"래칫 점수: {self._ratchet_score} (Top 5 최저 — 이 점수 이상이면 진입 가능)"
            )
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
