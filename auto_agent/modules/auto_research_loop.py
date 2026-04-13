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

### 선정 규칙 (매일 새로 + 옵션 C)
- **매일 0에서 새로 시작** — 어제 결과는 "참고"로만 제공됨
- 어제 결과 중 시의성 지난 주제(deadline 경과)는 자동 제거
- evergreen 주제(시의성 무관)는 별도 "후보 풀"로 보관
- **선정 사유(selection_reason)**를 반드시 포함 — 왜 이 주제인지, 어제 대비 변화
- Top 5 이내 진입 기준으로 경쟁
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

    def build_loop_prompt(self, provider: str = "claude") -> str:
        """전체 루프를 실행하는 에이전트 프롬프트 생성."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        directive = self._load_directive()
        skill_content = self._load_skill("agents/trend-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["market-analysis"])
        existing_candidates = self._load_existing_candidates()
        provider = (provider or "claude").strip().lower()
        if provider == "codex":
            loop_protocol = f"""## Codex Vault-Only Ratchet Protocol

당신은 자율 주제 탐색 에이전트입니다. 외부 웹 검색 없이 **볼트 안의 자료만** 사용하세요.
아래 루프를 {self._max_rounds}회 반복하세요.

### 매 라운드 수행 절차:
1. **스캔**: `market/trends/`, `insights/feedback/`, `channels/{self._channel}/videos/`, `channels/competitors/`를 읽어 핵심 신호를 정리
2. **후보 생성**: 3-5개 주제 후보를 생성 (제목 + 차별화 각도 + 핵심 훅)
3. **증거 연결**: 각 후보에 대해 볼트 파일 근거를 붙임
4. **점수 산정**: 아래 기준으로 topic_score 계산
5. **Top 5 선정**: 점수 상위 5개 선정 + 각각 selection_reason 작성
6. **다음 라운드**: 이전 라운드 고득점 영역만 더 정밀하게 다듬음

### 라운드 간 전략:
- 라운드 1: 넓게 스캔
- 라운드 2-3: 고점수 영역 정교화
- 라운드 4-5: 최고 후보의 채널 적합성/차별화 문장 정제
"""
            skill_tail = """## 핵심 운영 규칙
- 볼트 안의 파일만 읽고 판단하세요.
- 주제 후보는 3-5개만 남기세요.
- 각 후보는 topic_score, selection_reason, creative_brief를 포함해야 합니다.
- 마크다운 기획안은 원고가 아니라 방향 제시여야 합니다.
- 필수 에피소드는 4-5개만 유지하고 연결 이유를 명시하세요.
"""
        else:
            loop_protocol = f"""## 카파시 AutoResearch 프로토콜

당신은 자율 주제 탐색 에이전트입니다. 아래 루프를 {self._max_rounds}회 반복하세요.

### 매 라운드 수행 절차:
1. **스캔**: WebSearch로 최신 트렌드 검색 (YouTube 인기, 뉴스, 커뮤니티)
2. **후보 생성**: 3-5개 주제 후보를 생성 (제목 + 차별화 각도 + 핵심 훅)
3. **경쟁 분석**: 각 후보에 대해 YouTube 검색으로 기존 영상 확인
4. **점수 산정**: 아래 기준으로 topic_score 계산
5. **Top 5 선정**: 점수 상위 5개 선정 + 각각 selection_reason(선정 사유) 작성
6. **다음 라운드**: 이전 라운드에서 높은 점수 영역을 더 깊이 탐색

### 라운드 간 전략:
- 라운드 1: 넓게 스캔 (다양한 카테고리)
- 라운드 2-3: 고점수 영역 심화 (관련 키워드 파생)
- 라운드 4-5: 최고 후보 정밀 검증 (경쟁 영상 실제 조회수 확인)
"""
            skill_tail = f"""{skill_content}

{shared_skills}"""

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

{loop_protocol}
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

## 최종 출력 — 옵션 C 규칙

결과 파일: `insights/planning/{today}-{self._channel}-autoresearch.json`

**매일 새로 생성합니다. 어제 파일은 건드리지 마세요.**
- 오늘 탐색한 후보만 포함
- 시의성 지난 주제(deadline 경과)는 포함하지 않음
- 각 후보에 `selection_reason`(선정 사유) 필수
- 각 후보에 `topic_type`: "timely"(시의성) 또는 "evergreen"(상시) 분류

**제거된 주제도 기록:**
```json
"removed": [
  {{"title": "WGBI 75조원", "reason": "D+3 시의성 소멸", "original_score": 900}}
]
```

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
      "topic_type": "timely | evergreen",
      "selection_reason": "왜 이 주제를 선정했는지 (어제 대비 변화, 트렌드 근거, 경쟁 상황 등)",
      "creative_brief": {{
        "core_angle": "이 주제를 왜 이 각도로 다뤄야 하는지 한 줄",
        "tone": "영상 톤 (긴박감/유머/감동/분석적 등)",
        "target_audience": "타겟 시청자 (연령/관심사)",
        "differentiation": "경쟁 채널과 어떻게 차별화하는지",
        "story_points": [
          "1막: 도입 — 시청자를 끌어당기는 핵심 장면/팩트 (구체적으로)",
          "2막: 전개 — 핵심 갈등/반전/데이터 포인트 3~5개 나열",
          "3막: 결론 — 시청자에게 남길 인사이트/여운"
        ],
        "must_include_episodes": [
          "반드시 다뤄야 할 에피소드/일화 (구체적 사건명, 연도, 인물)",
          "예: '2008년 리먼브라더스 파산 당일 트레이딩 플로어 장면'",
          "예: '빈 살만이 리츠칼튼 호텔에 왕자 200명을 가둔 사건'"
        ],
        "recommended_structure": "추천 구성 (3막/연대기/미스터리 등)",
        "recommended_length": "추천 영상 길이",
        "key_data_points": ["반드시 포함해야 할 핵심 데이터/팩트 (수치 필수)"],
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

  📖 이야기 포인트 (구체적으로):
  - 1막 도입: [시청자를 끌어당기는 장면/팩트. 예: "2024년 3월, 구다이글로벌 매출이 1조를 돌파했다"]
  - 2막 전개: [핵심 에피소드 3~5개. 예: "3억에 조선미녀 인수 → 틱톡 바이럴 → 연매출 400억"]
  - 3막 결론: [시청자에게 남길 인사이트. 예: "K뷰티의 다음 전쟁터는 M&A다"]

  🎬 반드시 다뤄야 할 에피소드:
  - [구체적 사건명 + 연도 + 인물. 예: "2019년 조선미녀 3억 인수", "2023년 티르티르 350억 인수"]

  - 추천 구성: 몇 막, 어떤 흐름
  - 추천 길이: 몇 분
  - 핵심 데이터: 반드시 포함할 수치
  - 긴급도: 언제까지 발행해야 유효한지
```
이 브리프가 있으면 Stage 1 리서치가 방향을 잃지 않고, Stage 2 원고가 구체적 에피소드를 포함합니다.

{skill_tail}
"""

    def build_codex_round_prompt(
        self,
        round_number: int,
        current_candidates: List[Dict],
        ratchet_score: float,
        packet_path: Path,
    ) -> str:
        """Codex용 라운드별 compact prompt."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        directive = self._load_directive()
        seed_instruction = f'시드 키워드: "{self._seed}"\n' if self._seed else ""
        current_summary = self._summarize_candidates(current_candidates)

        return f"""# Stage 0 Codex Ratchet Round {round_number}

날짜: {today}
채널: {self._channel}
라운드: {round_number}/{self._max_rounds}
현재 ratchet_score: {ratchet_score}
{seed_instruction}

## 목표
볼트 자료만 읽고, 이 채널에 맞는 주제 후보 3-5개를 뽑아 점수화하세요.
단순 인기 키워드 나열이 아니라 `trigger_keyword -> knowledge_anchor -> bridge_reason` 구조로 후보를 만드세요.
이번 라운드는 **최종 응답으로 JSON만 반환**하면 됩니다.

## 읽을 입력 파일
아래 실제 vault 패킷 파일 **하나만** 읽으세요.
`{packet_path}`

## 파일 사용 규칙
- 위 패킷 파일 외 추가 파일 읽기 금지
- raw 디렉터리 탐색 금지
- 외부 웹 검색 금지

## 채널 지시문
{directive}

## 현재까지의 상위 후보
{current_summary}

## 점수 기준
{SCORING_PROMPT}

## 작성 규칙
- 볼트 요약에 나온 파일 경로를 `sources`에 남길 것
- 후보는 3-5개만
- 같은 의미의 후보를 중복으로 만들지 말 것
- `trigger_keyword`, `knowledge_anchor`, `bridge_reason`, `timing_window`를 모두 채울 것
- `selection_reason`은 한 문장 이상
- `creative_brief.story_points`는 3개 이상
- `must_include_episodes`는 2개 이상

## 최종 응답 형식
설명 없이 JSON만 반환:
{{
  "round": {round_number},
  "channel": "{self._channel}",
  "candidates": [
    {{
      "title": "주제 제목",
      "trigger_keyword": "실시간 화제 키워드",
      "knowledge_anchor": "깊이 있게 설명할 대상",
      "bridge_reason": "왜 이 트리거에서 이 앵커로 넘어오는지",
      "timing_window": "지금 바로 | 3일 내 | 1주 내 | evergreen",
      "angle": "차별화 각도",
      "hook": "핵심 훅",
      "trend_velocity": 8,
      "competition_gap": 7,
      "channel_fit": 9,
      "topic_score": 504,
      "topic_type": "timely",
      "selection_reason": "왜 이번 라운드에서 유효한 후보인지",
      "sources": ["볼트 파일명 또는 경로"],
      "creative_brief": {{
        "core_angle": "핵심 앵글",
        "tone": "톤",
        "story_points": ["1막", "2막", "3막"],
        "must_include_episodes": ["에피소드 A", "에피소드 B"],
        "recommended_length": "추천 영상 길이",
        "urgency": "긴급도"
      }}
    }}
  ]
}}
"""

    def _summarize_candidates(self, current_candidates: List[Dict]) -> str:
        if not current_candidates:
            return "없음"
        lines = []
        for idx, candidate in enumerate(current_candidates[:5], start=1):
            title = candidate.get("title", "")
            score = candidate.get("topic_score", 0)
            reason = candidate.get("selection_reason", "")
            lines.append(f"{idx}. [{score}] {title} — {reason[:120]}")
        return "\n".join(lines)

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

        # 어제 결과를 "참고"로 제공 (NAS NFD 인코딩 대응)
        import unicodedata
        from datetime import timedelta
        channel_nfc = unicodedata.normalize("NFC", self._channel)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        yesterday_candidates = []
        evergreen_pool = []

        for f in sorted(
            [x for x in planning_dir.glob("*-autoresearch.json")
             if channel_nfc in unicodedata.normalize("NFC", x.name)],
            reverse=True,
        ):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                file_date = data.get("date", "")
                if file_date == today:
                    continue  # 오늘 파일은 스킵

                for c in data.get("candidates", []):
                    score = c.get("topic_score", 0)
                    title = c.get("title", "")
                    brief = c.get("creative_brief", {})
                    urgency = brief.get("urgency", c.get("urgent_flag", ""))
                    reason = c.get("selection_reason", "")

                    # 시의성 감쇠: deadline 지난 주제 제거
                    if urgency and ("D-" in str(urgency) or "발행 필수" in str(urgency)):
                        yesterday_candidates.append(
                            f"- ⏰ [{score}점] {title} — 시의성 주제 (확인 필요: {urgency})"
                        )
                    else:
                        evergreen_pool.append(
                            f"- 🌿 [{score}점] {title}"
                        )
                break  # 최근 1개만
            except (json.JSONDecodeError, KeyError):
                continue

        # 래칫은 0에서 시작 (매일 새로)
        self._ratchet_score = 0

        parts = []
        if yesterday_candidates or evergreen_pool:
            parts.append("## 어제 결과 (참고용 — 새로 판단하세요)")
            if yesterday_candidates:
                parts.append("### 시의성 주제 (deadline 확인 후 유효하면 유지, 지났으면 제거)")
                parts.extend(yesterday_candidates[:5])
            if evergreen_pool:
                parts.append("### Evergreen 후보 풀 (시의성 무관, 필요 시 재선정)")
                parts.extend(evergreen_pool[:5])
            parts.append("\n**⚠️ 오늘은 0에서 새로 시작합니다. 어제 결과는 참고만 하세요.**")

        return "\n".join(parts)

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
