# 채널 인텔리전스 루프 Phase 1b — 에이전트 + 자동화 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** trend-analyst / performance-analyst 에이전트 + 에이전트 스킬 + watchlist 파서 + CLI 명령 + cron 자동화

**Architecture:** 에이전트는 Claude CLI로 실행하며, 볼트 디렉토리를 작업 경로로 사용. 에이전트 스킬이 분석 방법론을 주입하고, CLI가 실행을 트리거한다. cron이 매일/주간 자동 실행을 담당.

**Tech Stack:** Claude CLI, Python 3.12, cron (launchd), agents.json, SKILL.md

**Spec:** `docs/superpowers/specs/2026-03-25-stage0-stage4-intelligence-loop-design.md`

**Depends on:** Phase 1a 완료 (data_collector 모듈, vault_writer, dedup, youtube_collector, discord_notifier)

### 리뷰 반영 사항 (구현 시 주의)

1. **watchlist parse/write round-trip 데이터 보존** — `parse()`에서 섹션별 모든 컬럼을 추출해야 함. `_write()` 시 카테고리, 관련도, 날짜, 사유 등이 유실되지 않도록. (Critical)
2. **_watchlist.md 테이블에 채널ID 컬럼 추가** — Spec에는 없지만 API 호출에 필수. Spec과의 차이를 인지하고 진행. (Critical)
3. **`_write()`에서 기존 frontmatter 보존** — `max_trial`, `next_review` 등 하드코딩 대신 파싱된 원본 유지. (Critical)
4. **cron 타임존 가드** — Mac Mini 시스템 타임존 확인 후, KST면 KST 시간 사용, UTC면 UTC 변환 적용. `TZ` 환경변수 명시. (Important)
5. **agent_runner.py 위치** — `data_collector/` 안이 아닌 `auto_agent/modules/agent_runner.py`로 분리 (관심사 분리). (Important)
6. **Discord 웹훅 환경변수 통일** — `DISCORD_WEBHOOK_URL` 하나로 통일. `KAIROS_DISCORD_WEBHOOK_URL` 폴백 제거. (Important)
7. **`--from-plan` slug 생성** — 기존 프로젝트 slug 생성 로직 재사용 + 충돌 체크 추가. (Important)

---

## File Structure

### 신규 생성

| 파일 | 역할 |
|------|------|
| `auto_agent/modules/data_collector/watchlist_parser.py` | _watchlist.md 마크다운 파싱 |
| `auto_agent/modules/agent_runner.py` | trend-analyst / performance-analyst Claude CLI 실행 래퍼 |
| `auto_agent/data/skills/shared/market-analysis.md` | 트렌드 교차 분석 방법론 스킬 |
| `auto_agent/data/skills/shared/channel-metrics.md` | YouTube Analytics 지표 해석 스킬 |
| `auto_agent/data/skills/agents/trend-analyst/SKILL.md` | trend-analyst 에이전트 역할/프롬프트 |
| `auto_agent/data/skills/agents/performance-analyst/SKILL.md` | performance-analyst 에이전트 역할/프롬프트 |
| `tests/test_watchlist_parser.py` | watchlist 파서 테스트 |
| `tests/test_agent_runner.py` | agent_runner 테스트 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `auto_agent/data/agents.json` | trend-analyst, performance-analyst 에이전트 정의 추가 |
| `auto_agent/modules/data_collector/collector.py` | `_load_watchlist()` stub → 실제 파싱 구현 |
| `auto_agent/cli.py` | `plan`, `analyze` 명령어 추가 + `watchlist` approve/remove 구현 |
| `auto_agent/orchestrator/rule_manager.py` | RULE_MANIFEST에 신규 스킬 등록 |

---

## Chunk 1: Watchlist 파서 + Collector 연동

### Task 1: Watchlist 파서 (watchlist_parser.py)

**Files:**
- Create: `auto_agent/modules/data_collector/watchlist_parser.py`
- Create: `tests/test_watchlist_parser.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_watchlist_parser.py
"""watchlist 파서 테스트 — _watchlist.md 마크다운 파싱."""
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser


@pytest.fixture
def watchlist_file(tmp_path):
    vault = tmp_path / "vault"
    (vault / "channels").mkdir(parents=True)
    path = vault / "channels" / "_watchlist.md"
    path.write_text("""---
max_trial: 3
last_review: 2026-03-25
next_review: 2026-04-01
---

## Active
| 채널 | 채널ID | 카테고리 | 추가일 | 관련도 |
|------|--------|---------|--------|--------|
| 슈카월드 | UCsJ6RuBiTVNyF3f6rY5K_g | 경제/시사 | 2026-01-15 | ★★★★★ |
| 지식한입 | UCxyz123 | 교양/지식 | 2026-02-01 | ★★★★☆ |

## Trial
| 채널 | 채널ID | 추가일 | 추가 사유 | 관련도 |
|------|--------|--------|-----------|--------|
| 어쩌다어른 | UCtrial1 | 2026-03-22 | 교양 포맷 유사 | ★★★☆☆ |

## Proposed Remove
| 채널 | 채널ID | 제안일 | 사유 |
|------|--------|--------|------|
| 예시채널 | UCremove1 | 2026-03-25 | 6주간 관련 콘텐츠 없음 |

## Archived
| 채널 | 채널ID | 제거일 | 사유 |
|------|--------|--------|------|
""", encoding="utf-8")
    return vault


class TestParse:
    def test_parse_active(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["active"]) == 2
        assert result["active"][0]["name"] == "슈카월드"
        assert result["active"][0]["channel_id"] == "UCsJ6RuBiTVNyF3f6rY5K_g"

    def test_parse_trial(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["trial"]) == 1
        assert result["trial"][0]["name"] == "어쩌다어른"

    def test_parse_proposed_remove(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["proposed_remove"]) == 1

    def test_get_trackable(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        trackable = parser.get_trackable()
        assert len(trackable) == 3  # active 2 + trial 1

    def test_empty_watchlist(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "channels").mkdir(parents=True)
        parser = WatchlistParser(vault)
        result = parser.parse()
        assert result == {"active": [], "trial": [], "proposed_remove": [], "archived": []}


class TestModify:
    def test_approve_trial(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        parser.approve("어쩌다어른")
        result = parser.parse()
        assert len(result["active"]) == 3
        assert len(result["trial"]) == 0

    def test_remove_channel(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        parser.remove("예시채널")
        result = parser.parse()
        assert len(result["proposed_remove"]) == 0
        assert len(result["archived"]) == 1

    def test_approve_nonexistent_raises(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        with pytest.raises(ValueError):
            parser.approve("존재하지않는채널")
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python3 -m pytest tests/test_watchlist_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: watchlist_parser.py 구현**

```python
# auto_agent/modules/data_collector/watchlist_parser.py
"""_watchlist.md 마크다운 파싱 + 수정."""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


SECTIONS = ["active", "trial", "proposed_remove", "archived"]
SECTION_HEADERS = {
    "## Active": "active",
    "## Trial": "trial",
    "## Proposed Remove": "proposed_remove",
    "## Archived": "archived",
}


class WatchlistParser:
    """_watchlist.md 파싱 및 수정."""

    def __init__(self, vault_dir: Path):
        self._vault_dir = vault_dir
        self._path = vault_dir / "channels" / "_watchlist.md"

    def parse(self) -> Dict[str, List[Dict]]:
        """워치리스트 파싱. 섹션별 채널 목록 반환."""
        result = {s: [] for s in SECTIONS}
        if not self._path.exists():
            return result

        content = self._path.read_text(encoding="utf-8")
        current_section = None

        for line in content.split("\n"):
            stripped = line.strip()

            # 섹션 헤더 감지
            for header, section in SECTION_HEADERS.items():
                if stripped.startswith(header):
                    current_section = section
                    break

            # 테이블 행 파싱 (| 로 시작, 구분선 제외)
            if current_section and stripped.startswith("|") and not re.match(r"^\|[-\s|]+\|$", stripped):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if len(cells) >= 2 and cells[0] != "채널":  # 헤더 행 스킵
                    entry = {"name": cells[0], "channel_id": cells[1]}
                    result[current_section].append(entry)

        return result

    def get_trackable(self) -> List[Dict]:
        """수집 대상 채널 (active + trial) 반환."""
        data = self.parse()
        channels = []
        for status in ["active", "trial"]:
            for ch in data[status]:
                channels.append({**ch, "status": status})
        return channels

    def approve(self, channel_name: str):
        """trial → active 승격."""
        data = self.parse()
        target = None
        for ch in data["trial"]:
            if ch["name"] == channel_name:
                target = ch
                break
        if not target:
            raise ValueError(f"Trial 채널을 찾을 수 없습니다: {channel_name}")

        # trial에서 제거, active에 추가
        data["trial"] = [ch for ch in data["trial"] if ch["name"] != channel_name]
        data["active"].append(target)
        self._write(data)

    def remove(self, channel_name: str):
        """proposed_remove → archived 이동."""
        data = self.parse()
        target = None
        for ch in data["proposed_remove"]:
            if ch["name"] == channel_name:
                target = ch
                break
        if not target:
            raise ValueError(f"제거 대상 채널을 찾을 수 없습니다: {channel_name}")

        data["proposed_remove"] = [ch for ch in data["proposed_remove"] if ch["name"] != channel_name]
        data["archived"].append(target)
        self._write(data)

    def _write(self, data: Dict[str, List[Dict]]):
        """파싱된 데이터를 _watchlist.md로 재작성."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = [
            "---",
            "max_trial: 3",
            f"last_review: {today}",
            "---",
            "",
        ]

        # Active
        lines += [
            "## Active",
            "| 채널 | 채널ID | 카테고리 | 추가일 | 관련도 |",
            "|------|--------|---------|--------|--------|",
        ]
        for ch in data.get("active", []):
            cat = ch.get("category", "")
            date = ch.get("added", today)
            rel = ch.get("relevance", "")
            lines.append(f"| {ch['name']} | {ch['channel_id']} | {cat} | {date} | {rel} |")
        lines.append("")

        # Trial
        lines += [
            "## Trial",
            "| 채널 | 채널ID | 추가일 | 추가 사유 | 관련도 |",
            "|------|--------|--------|-----------|--------|",
        ]
        for ch in data.get("trial", []):
            date = ch.get("added", today)
            reason = ch.get("reason", "")
            rel = ch.get("relevance", "")
            lines.append(f"| {ch['name']} | {ch['channel_id']} | {date} | {reason} | {rel} |")
        lines.append("")

        # Proposed Remove
        lines += [
            "## Proposed Remove",
            "| 채널 | 채널ID | 제안일 | 사유 |",
            "|------|--------|--------|------|",
        ]
        for ch in data.get("proposed_remove", []):
            date = ch.get("proposed_date", today)
            reason = ch.get("reason", "")
            lines.append(f"| {ch['name']} | {ch['channel_id']} | {date} | {reason} |")
        lines.append("")

        # Archived
        lines += [
            "## Archived",
            "| 채널 | 채널ID | 제거일 | 사유 |",
            "|------|--------|--------|------|",
        ]
        for ch in data.get("archived", []):
            date = ch.get("removed_date", today)
            reason = ch.get("reason", "")
            lines.append(f"| {ch['name']} | {ch['channel_id']} | {date} | {reason} |")
        lines.append("")

        self._path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python3 -m pytest tests/test_watchlist_parser.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/watchlist_parser.py tests/test_watchlist_parser.py
git commit -m "feat: watchlist 파서 — _watchlist.md 마크다운 파싱 + approve/remove"
```

---

### Task 2: collector._load_watchlist() 연동

**Files:**
- Modify: `auto_agent/modules/data_collector/collector.py`

- [ ] **Step 1: _load_watchlist() stub를 실제 구현으로 교체**

기존 코드 (라인 ~213):
```python
def _load_watchlist(self) -> List[Dict]:
    """_watchlist.md에서 active + trial 채널 목록 추출. Phase 1b에서 구현."""
    return []
```

교체:
```python
def _load_watchlist(self) -> List[Dict]:
    """_watchlist.md에서 active + trial 채널 목록 추출."""
    from .watchlist_parser import WatchlistParser
    parser = WatchlistParser(self._vault_dir)
    return parser.get_trackable()
```

- [ ] **Step 2: cmd_watchlist approve/remove 구현**

`auto_agent/cli.py`의 `cmd_watchlist` 함수에서 stub 경고를 실제 로직으로 교체:

```python
def cmd_watchlist(args):
    """경쟁 채널 워치리스트 관리."""
    from auto_agent.paths import get_vault_dir
    from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser

    vault = get_vault_dir()
    parser = WatchlistParser(vault)

    if not args:
        watchlist_path = vault / "channels" / "_watchlist.md"
        if watchlist_path.exists():
            console.print(watchlist_path.read_text(encoding="utf-8"))
        else:
            print_warning("워치리스트가 없습니다. channels/_watchlist.md를 생성하세요.")
        return

    subcmd = args[0]
    if subcmd == "approve" and len(args) > 1:
        channel_name = args[1]
        try:
            parser.approve(channel_name)
            print_success(f"채널 승격 완료: {channel_name} (trial → active)")
        except ValueError as e:
            print_error(str(e))
    elif subcmd == "remove" and len(args) > 1:
        channel_name = args[1]
        try:
            parser.remove(channel_name)
            print_success(f"채널 제거 완료: {channel_name} → archived")
        except ValueError as e:
            print_error(str(e))
    else:
        print_error("Usage: auto-agent watchlist [approve|remove] <채널명>")
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/modules/data_collector/collector.py auto_agent/cli.py
git commit -m "feat: watchlist 파서 연동 — collector + CLI approve/remove"
```

---

## Chunk 2: 에이전트 스킬 + agents.json

### Task 3: 에이전트 스킬 생성

**Files:**
- Create: `auto_agent/data/skills/shared/market-analysis.md`
- Create: `auto_agent/data/skills/shared/channel-metrics.md`
- Create: `auto_agent/data/skills/agents/trend-analyst/SKILL.md`
- Create: `auto_agent/data/skills/agents/performance-analyst/SKILL.md`

- [ ] **Step 1: market-analysis.md 생성**

```markdown
# 시장 분석 스킬 (Market Analysis)

## 역할
YouTube 트렌드, 검색량 데이터, 경쟁 채널 공개 데이터를 교차 분석하여
주제의 시장성과 타이밍을 평가한다.

## 분석 프레임워크

### 1. 트렌드 신호 감지
- `market/trends/` 디렉토리의 일일 트렌드 노트 확인
- 검색량 급등 키워드 (전주 대비 +50% 이상) 식별
- 지속적 상승 트렌드 vs 일시적 스파이크 구분

### 2. 경쟁 채널 갭 분석
- `channels/competitors/` 노트에서 최근 영상 주제 확인
- 트렌드 키워드를 다룬 경쟁 채널이 있는지 확인
- 미진입 주제 = 선점 기회 (높은 우선순위)
- 이미 다수가 다룬 주제 = 차별화 앵글 필수

### 3. 채널 적합성 평가
- `channels/{채널}/videos/` 에서 유사 주제 과거 성과 확인
- 조회수, CTR 평균 대비 비교
- 채널 포지셔닝과의 일치도 (이로미즘: 경제/시사 심층, 세모지: 교양/퀴즈)

### 4. 타이밍 판단
- 트렌드 피크 전 선점 (검색량 상승 초기) = 최적
- 피크 도달 후 = 후발, 차별화 필수
- 하락 추세 = 비추천 (이미 늦음)

## 출력 규칙
- 주제별로 **왜 지금인가**, **채널 적합성**, **경쟁 상황** 3가지를 반드시 포함
- 위키링크(`[[노트명]]`)로 근거 연결
- 예상 조회수는 유사 영상 성과 기반으로 범위 제시 (단정 금지)
```

- [ ] **Step 2: channel-metrics.md 생성**

```markdown
# 채널 지표 분석 스킬 (Channel Metrics)

## 역할
YouTube Analytics 데이터를 해석하고 영상/채널 성과를 평가한다.

## 핵심 지표 해석

### 조회수 (Views)
- 7일 조회수: 초기 반응 지표
- 28일 조회수: 중기 성과 (알고리즘 추천 효과 반영)
- 90일 조회수: 롱테일 검색 유입 판단

### CTR (클릭률)
- 채널 평균 대비 비교 (±2%p 이상이면 유의미)
- 8% 이상: 우수 / 4~8%: 보통 / 4% 미만: 개선 필요
- 썸네일/제목 조합의 효과 판단

### 평균 시청 지속 시간
- 영상 길이의 50% 이상: 우수
- 30~50%: 보통
- 30% 미만: 초반 이탈 문제
- 이탈 구간 분석 → 다음 영상의 구성 피드백

### 유입 경로
- 검색: 롱테일 가치 (시간이 지나도 조회수 유지)
- 추천: 알고리즘 노출 (초기 급등, 이후 감소)
- 탐색: 홈/구독 피드 (구독자 충성도)

## 경쟁 채널 지표 (공개 데이터만)
- 조회수, 좋아요: 직접 비교 가능
- 업로드 빈도: 채널 활동성 판단
- **CTR, 시청지속, 유입경로는 수집 불가** — 추정하지 않음

## 성과 평가 기준
- 기획안의 "예상 성과" 대비 실제 달성률
- 채널 최근 10개 영상 평균 대비 상대 평가
- 주제 카테고리별 평균과 비교 (경제 vs 시사 vs 교양)

## 출력 규칙
- 숫자는 반드시 비교 기준과 함께 제시 (단독 수치 금지)
- 개선 제안은 구체적 행동으로 (예: "초반 30초에 핵심 질문 배치")
- 위키링크로 관련 영상/인사이트 노트 연결
```

- [ ] **Step 3: trend-analyst SKILL.md 생성**

```markdown
# trend-analyst 에이전트

## 역할
채널 데이터 + 시장 트렌드를 교차 분석하여 주제 기획안을 생성한다.

## 실행 모드

### 자율 모드 (매일 KST 06:00)
1. `insights/feedback/` 에서 최신 피드백 확인
2. `market/trends/` 에서 최근 트렌드 확인
3. `channels/{채널}/videos/` 에서 채널 성과 패턴 파악
4. `channels/competitors/` 에서 경쟁 상황 확인
5. 주제 후보 3~5개 순위화
6. `insights/planning/{date}-{topic}.md`로 기획안 저장

### 시드 모드 (사용자 키워드 제공)
1. 사용자 키워드를 기반으로 볼트 탐색
2. 트렌드 적합성 + 채널 적합성 검증
3. 기획안 1개로 구체화

## 기획안 출력 포맷

```yaml
---
type: planning
mode: autonomous | seeded
channel: 이로미즘 | 세모지
created: YYYY-MM-DD
status: proposed
seed: null | "키워드"
---
```

### 필수 섹션
1. **주제**: 한 줄 제목
2. **왜 지금인가**: 트렌드 데이터 + 위키링크 근거
3. **채널 적합성**: 과거 유사 영상 성과 + 시청층 겹침
4. **경쟁 분석**: 경쟁 채널 동향 + 차별화 포인트
5. **추천 앵글**: 2~3개 제목 후보
6. **예상 성과**: 조회수 범위 + 추천 길이

## 규칙
- 볼트 내 파일만 읽기 (외부 API 직접 호출 금지 — 수집은 data-collector가 담당)
- 위키링크로 근거 연결 필수
- 기획안의 status는 항상 "proposed"로 생성 (승인은 사용자)
- 채널별로 별도 기획안 생성 (이로미즘/세모지 혼합 금지)
```

- [ ] **Step 4: performance-analyst SKILL.md 생성**

```markdown
# performance-analyst 에이전트

## 역할
업로드된 영상 성과를 분석하고, 시장 동향과 교차하여 인사이트를 도출한다.
Stage 0(trend-analyst)에 피드백을 제공한다.

## 실행 모드

### 영상 성과 분석 (업로드 후 +1/3/7/28일)
1. `channels/{채널}/videos/{영상}.md` 에서 현재 성과 확인
2. 기획안(`insights/planning/`)의 예상 성과와 비교
3. 채널 평균 대비 상대 평가
4. 영상 노트에 분석 결과 추가

### 주간 종합 리뷰 (매주 일요일)
1. 해당 주 전체 성과 집계
2. 경쟁 채널 동향 분석
3. 패턴 발견 → `insights/performance/` 에 인사이트 노트 생성
4. 경쟁 채널 watchlist 리뷰 (trial 추가/제거 제안)
5. Stage 0 피드백 → `insights/feedback/` 에 저장

## 주간 리뷰 출력 포맷

```yaml
---
type: weekly-review
channel: 이로미즘 | 세모지
period: YYYY-WNN (MM-DD ~ MM-DD)
created: YYYY-MM-DD
---
```

### 필수 섹션
1. **채널 성과 요약**: 총 조회수, 구독 변화, 최고/최저 영상
2. **패턴 발견**: 주제/길이/썸네일 등 유의미한 상관관계
3. **경쟁 채널 동향**: 주목할 변화 + trial 추가/제거 제안
4. **Stage 0 피드백**: 다음 주 기획에 반영할 교훈

## 규칙
- 볼트 내 파일만 읽기
- 경쟁 채널은 공개 데이터만 분석 (CTR/시청지속 추정 금지)
- 위키링크로 근거 연결 필수
- trial 채널 추가 시 최대 3개 슬롯 확인
- 제거 제안은 사유를 반드시 기재
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/data/skills/shared/market-analysis.md \
        auto_agent/data/skills/shared/channel-metrics.md \
        auto_agent/data/skills/agents/trend-analyst/SKILL.md \
        auto_agent/data/skills/agents/performance-analyst/SKILL.md
git commit -m "feat: 에이전트 스킬 — market-analysis, channel-metrics, trend-analyst, performance-analyst"
```

---

### Task 4: agents.json 업데이트

**Files:**
- Modify: `auto_agent/data/agents.json`

- [ ] **Step 1: agents.json에 에이전트 정의 추가**

기존 `agents` 블록 안에 추가:

```json
"trend-analyst": {
  "description": "채널 데이터 + 시장 트렌드 교차 분석으로 주제 기획안 생성",
  "model": "sonnet",
  "max_turns": 40,
  "budget": "$2.0",
  "max_duration_minutes": 15,
  "allowed_tools": ["Read", "Write", "Glob", "Grep"],
  "skill_file": "agents/trend-analyst/SKILL.md",
  "shared_skills": [
    "shared/writing-style-iromism",
    "shared/writing-style-semoji",
    "shared/market-analysis"
  ],
  "notes": "Stage 0. 파이프라인 외부 독립 실행. 볼트를 working_dir로 사용."
},

"performance-analyst": {
  "description": "영상 성과 + 시장 동향 분석, Stage 0 피드백 생성",
  "model": "sonnet",
  "max_turns": 50,
  "budget": "$1.5",
  "max_duration_minutes": 20,
  "allowed_tools": ["Read", "Write", "Glob", "Grep"],
  "skill_file": "agents/performance-analyst/SKILL.md",
  "shared_skills": [
    "shared/channel-metrics",
    "shared/market-analysis"
  ],
  "notes": "Stage 4. 파이프라인 외부 독립 실행. 볼트를 working_dir로 사용."
}
```

`summary` 블록도 업데이트:

```json
"summary": {
  "agents": [
    "research-orchestrator (Stage 1: 리서치)",
    "script-director (Stage 2: 원고+연출)",
    "assembly-director (Stage 3: 에셋 조립+렌더링)",
    "trend-analyst (Stage 0: 주제 기획)",
    "performance-analyst (Stage 4: 성과 분석)"
  ],
  "architecture": "5 에이전트 × 6 모듈(도구). Stage 0/4는 볼트 기반 독립 실행."
}
```

- [ ] **Step 2: rule_manager.py RULE_MANIFEST 업데이트**

기존 RULE_MANIFEST에 추가:

```python
"skills/shared/market-analysis": "skill",
"skills/shared/channel-metrics": "skill",
"skills/agents/trend-analyst/SKILL": "skill",
"skills/agents/performance-analyst/SKILL": "skill",
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/agents.json auto_agent/orchestrator/rule_manager.py
git commit -m "feat: agents.json에 trend-analyst + performance-analyst 정의 추가"
```

---

## Chunk 3: 에이전트 실행 래퍼 + CLI

### Task 5: 에이전트 실행 래퍼 (agent_runner.py)

**Files:**
- Create: `auto_agent/modules/data_collector/agent_runner.py`
- Create: `tests/test_agent_runner.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_agent_runner.py
"""에이전트 실행 래퍼 테스트."""
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.agent_runner import AgentRunner


@pytest.fixture
def runner(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "insights" / "planning").mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    return AgentRunner()


class TestBuildPrompt:
    def test_trend_analyst_autonomous(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed=None)
        assert "이로미즘" in prompt
        assert "자율 모드" in prompt
        assert "기획안" in prompt

    def test_trend_analyst_seeded(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed="희토류 전쟁")
        assert "희토류 전쟁" in prompt
        assert "시드 모드" in prompt

    def test_performance_analyst_video(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="video", channel="이로미즘", video_id="abc123"
        )
        assert "abc123" in prompt
        assert "영상 성과" in prompt

    def test_performance_analyst_weekly(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="weekly", channel="이로미즘"
        )
        assert "주간 리뷰" in prompt


class TestBuildCommand:
    def test_build_claude_cmd(self, runner):
        cmd = runner._build_claude_cmd(model="sonnet", max_turns=40)
        assert "claude" in cmd[0] or "claude" in str(cmd)
        assert "--model" in cmd
        assert "sonnet" in cmd
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

- [ ] **Step 3: agent_runner.py 구현**

```python
# auto_agent/modules/data_collector/agent_runner.py
"""trend-analyst / performance-analyst Claude CLI 실행 래퍼."""
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_vault_dir, get_data_dir
from auto_agent.utils.platform import subprocess_kwargs

logger = logging.getLogger(__name__)


class AgentRunner:
    """에이전트 실행 래퍼 — Claude CLI로 에이전트 호출."""

    def __init__(self):
        self._vault_dir = get_vault_dir()
        self._data_dir = get_data_dir()
        self._agents_config = self._load_agents_config()

    def run_trend_analyst(self, channel: str, seed: Optional[str] = None) -> Dict:
        """trend-analyst 에이전트 실행."""
        prompt = self.build_trend_analyst_prompt(channel, seed)
        config = self._agents_config.get("agents", {}).get("trend-analyst", {})
        return self._run_agent(prompt, config)

    def run_performance_analyst(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> Dict:
        """performance-analyst 에이전트 실행."""
        prompt = self.build_performance_analyst_prompt(mode, channel, video_id)
        config = self._agents_config.get("agents", {}).get("performance-analyst", {})
        return self._run_agent(prompt, config)

    # ── 프롬프트 빌더 ──

    def build_trend_analyst_prompt(self, channel: str, seed: Optional[str] = None) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/trend-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["market-analysis"])

        if seed:
            mode_text = f"""## 실행 모드: 시드 모드
사용자 키워드: "{seed}"
이 키워드를 기반으로 볼트에서 관련 데이터를 탐색하고,
트렌드 적합성 + 채널 적합성을 검증하여 기획안 1개를 구체화하세요."""
        else:
            mode_text = """## 실행 모드: 자율 모드
볼트의 트렌드, 채널 성과, 경쟁 채널 데이터를 교차 분석하여
주제 후보 3~5개를 순위화한 기획안을 생성하세요."""

        return f"""# trend-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 트렌드: market/trends/
- 채널 성과: channels/{channel}/videos/
- 경쟁 채널: channels/competitors/
- 기존 피드백: insights/feedback/
- 기존 기획안: insights/planning/

## 출력
기획안을 insights/planning/{today}-기획안.md 로 저장하세요.

{skill_content}

{shared_skills}
"""

    def build_performance_analyst_prompt(
        self, mode: str, channel: str, video_id: Optional[str] = None
    ) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        skill_content = self._load_skill("agents/performance-analyst/SKILL.md")
        shared_skills = self._load_shared_skills(["channel-metrics", "market-analysis"])

        if mode == "video" and video_id:
            mode_text = f"""## 실행 모드: 영상 성과 분석
영상 ID: {video_id}
channels/{channel}/videos/ 에서 해당 영상 노트를 찾아 성과를 분석하세요.
기획안의 예상 성과 대비 실제 달성률을 평가하세요."""
        else:
            mode_text = f"""## 실행 모드: 주간 종합 리뷰
이번 주 {channel} 채널의 전체 성과를 분석하세요.
경쟁 채널 동향을 확인하고 watchlist 리뷰를 수행하세요.
Stage 0 피드백을 insights/feedback/ 에 저장하세요."""

        return f"""# performance-analyst 에이전트 실행

날짜: {today}
채널: {channel}

{mode_text}

## 볼트 구조
- 채널 성과: channels/{channel}/videos/
- 채널 Analytics: channels/{channel}/analytics/
- 경쟁 채널: channels/competitors/
- 트렌드: market/trends/
- 기존 인사이트: insights/performance/
- 피드백 출력: insights/feedback/

{skill_content}

{shared_skills}
"""

    # ── Claude CLI 실행 ──

    def _run_agent(self, prompt: str, config: Dict) -> Dict:
        """Claude CLI로 에이전트 실행."""
        model = config.get("model", "sonnet")
        max_turns = config.get("max_turns", 30)
        timeout = config.get("max_duration_minutes", 15) * 60

        cmd = self._build_claude_cmd(model=model, max_turns=max_turns)

        env = os.environ.copy()
        env.pop("CLAUDECODE", None)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self._vault_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                **subprocess_kwargs(),
            )
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)

            return {
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout", "returncode": -1, "stdout": "", "stderr": "timeout"}
        except Exception as e:
            return {"status": "error", "returncode": -1, "stdout": "", "stderr": str(e)}

    def _build_claude_cmd(self, model: str, max_turns: int) -> List[str]:
        """Claude CLI 명령어 빌드."""
        cli_path = self._find_claude_cli()
        tools = ["Read", "Write", "Glob", "Grep"]
        cmd = [
            cli_path, "--print", "--output-format", "json",
            "--model", model, "--max-turns", str(max_turns),
        ]
        for tool in tools:
            cmd += ["--allowedTools", tool]
        return cmd

    def _find_claude_cli(self) -> str:
        """Claude CLI 바이너리 경로."""
        import shutil
        path = shutil.which("claude")
        if path:
            return path
        raise FileNotFoundError("Claude CLI를 찾을 수 없습니다. 'claude'가 PATH에 있는지 확인하세요.")

    # ── 스킬 로딩 ──

    def _load_skill(self, relative_path: str) -> str:
        path = self._data_dir / "skills" / relative_path
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning("스킬 파일 없음: %s", path)
        return ""

    def _load_shared_skills(self, skill_names: List[str]) -> str:
        parts = []
        for name in skill_names:
            content = self._load_skill(f"shared/{name}.md")
            if content:
                parts.append(content)
        return "\n\n---\n\n".join(parts)

    def _load_agents_config(self) -> Dict:
        path = self._data_dir / "agents.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python3 -m pytest tests/test_agent_runner.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/agent_runner.py tests/test_agent_runner.py
git commit -m "feat: 에이전트 실행 래퍼 — Claude CLI로 trend/performance-analyst 호출"
```

---

### Task 6: CLI plan / analyze 명령어

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: cmd_plan 함수 추가**

```python
def cmd_plan(args):
    """주제 기획 (Stage 0 — trend-analyst)."""
    from auto_agent.modules.data_collector.agent_runner import AgentRunner
    from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier

    channel = "이로미즘"  # 기본값
    seed = None

    for i, arg in enumerate(args):
        if arg == "--channel" and i + 1 < len(args):
            channel = args[i + 1]
        elif arg == "--seed" and i + 1 < len(args):
            seed = args[i + 1]

    mode = "시드 모드" if seed else "자율 모드"
    print_header(f"Auto Agent — 주제 기획 ({mode})")
    console.print(f"  채널: [accent]{channel}[/accent]")
    if seed:
        console.print(f"  시드: [accent]{seed}[/accent]")

    runner = AgentRunner()
    result = runner.run_trend_analyst(channel=channel, seed=seed)

    if result["status"] == "success":
        print_success("기획안 생성 완료")
        # Discord 알림
        import os
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "") or os.getenv("KAIROS_DISCORD_WEBHOOK_URL", "")
        if webhook:
            notifier = DiscordNotifier(webhook_url=webhook)
            notifier.send(f"📋 **{channel} 기획안 생성 완료** ({mode})\n→ 볼트 insights/planning/ 확인")
    else:
        print_error(f"기획안 생성 실패: {result.get('stderr', '')[:200]}")
```

- [ ] **Step 2: cmd_analyze 함수 추가**

```python
def cmd_analyze(args):
    """성과 분석 (Stage 4 — performance-analyst)."""
    from auto_agent.modules.data_collector.agent_runner import AgentRunner
    from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier

    channel = "이로미즘"
    video_id = None
    weekly = False

    for i, arg in enumerate(args):
        if arg == "--channel" and i + 1 < len(args):
            channel = args[i + 1]
        elif arg == "--video" and i + 1 < len(args):
            video_id = args[i + 1]
        elif arg == "--weekly":
            weekly = True

    if not video_id and not weekly:
        print_error("Usage: auto-agent analyze [--video <id> | --weekly] --channel <name>")
        sys.exit(1)

    mode = "weekly" if weekly else "video"
    label = "주간 리뷰" if weekly else f"영상 분석 ({video_id})"
    print_header(f"Auto Agent — {label}")
    console.print(f"  채널: [accent]{channel}[/accent]")

    runner = AgentRunner()
    result = runner.run_performance_analyst(mode=mode, channel=channel, video_id=video_id)

    if result["status"] == "success":
        print_success(f"{label} 완료")
        import os
        webhook = os.getenv("DISCORD_WEBHOOK_URL", "") or os.getenv("KAIROS_DISCORD_WEBHOOK_URL", "")
        if webhook:
            notifier = DiscordNotifier(webhook_url=webhook)
            notifier.send(f"📊 **{channel} {label} 완료**\n→ 볼트 확인")
    else:
        print_error(f"분석 실패: {result.get('stderr', '')[:200]}")
```

- [ ] **Step 3: COMMANDS 딕셔너리에 등록**

```python
"plan": cmd_plan,
"analyze": cmd_analyze,
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat: CLI plan/analyze 명령어 — trend-analyst + performance-analyst 실행"
```

---

### Task 7: project create --from-plan 연동

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: cmd_project_create에 --from-plan 옵션 추가**

기존 `cmd_project` 함수 (또는 프로젝트 생성 로직)을 찾아서, `--from-plan` 플래그가 있으면:

1. 기획안 마크다운 파일의 frontmatter에서 `channel`, 본문에서 주제 추출
2. `auto-agent project create` 로직으로 프로젝트 생성
3. config에 channel 자동 세팅
4. 기획안의 `status`를 `approved`로 업데이트

```python
def _create_from_plan(plan_path_str: str):
    """기획안 마크다운에서 프로젝트 자동 생성."""
    from auto_agent.paths import get_vault_dir

    vault = get_vault_dir()
    plan_path = vault / plan_path_str if not Path(plan_path_str).is_absolute() else Path(plan_path_str)

    if not plan_path.exists():
        print_error(f"기획안을 찾을 수 없습니다: {plan_path}")
        sys.exit(1)

    content = plan_path.read_text(encoding="utf-8")

    # frontmatter 파싱
    channel = "이로미즘"
    topic = ""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            for line in fm.split("\n"):
                if line.startswith("channel:"):
                    channel = line.split(":", 1)[1].strip()

    # 주제 추출 (## 주제: 라인)
    for line in content.split("\n"):
        if line.startswith("## 주제:"):
            topic = line.replace("## 주제:", "").strip()
            break

    if not topic:
        print_error("기획안에서 주제를 찾을 수 없습니다 (## 주제: 형식 필요)")
        sys.exit(1)

    # 프로젝트 생성 (기존 create 로직 재사용)
    slug = topic.replace(" ", "_").replace("/", "_")[:50]
    console.print(f"  주제: [accent]{topic}[/accent]")
    console.print(f"  채널: [accent]{channel}[/accent]")
    console.print(f"  슬러그: [accent]{slug}[/accent]")

    # 기획안 status 업데이트
    updated = content.replace("status: proposed", "status: approved")
    plan_path.write_text(updated, encoding="utf-8")
    print_success(f"기획안 승인됨: {plan_path.name}")

    return topic, channel, slug
```

- [ ] **Step 2: cmd_project에서 --from-plan 분기 추가**

기존 `project create` 명령 내에서:
```python
if "--from-plan" in args:
    idx = args.index("--from-plan")
    if idx + 1 < len(args):
        plan_path = args[idx + 1]
        topic, channel, slug = _create_from_plan(plan_path)
        # 이후 기존 프로젝트 생성 로직 연결
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat: project create --from-plan — 기획안에서 프로젝트 자동 생성"
```

---

### Task 8: cron 스케줄 설정 스크립트

**Files:**
- Create: `auto_agent/scripts/setup_cron.py`

- [ ] **Step 1: cron 설정 스크립트 작성**

```python
# auto_agent/scripts/setup_cron.py
"""cron 스케줄 자동 설정 — Mac Mini용."""
import subprocess
import sys
from pathlib import Path


CRON_ENTRIES = [
    # KST 05:30 = UTC 20:30 (전일)
    '30 20 * * * cd {workspace} && {python} -m auto_agent.cli collect --all >> {log_dir}/collect.log 2>&1',
    # KST 06:00 이로미즘 = UTC 21:00 (전일)
    '0 21 * * * cd {workspace} && {python} -m auto_agent.cli plan --channel 이로미즘 >> {log_dir}/plan-iromism.log 2>&1',
    # KST 06:10 세모지 = UTC 21:10 (전일)
    '10 21 * * * cd {workspace} && {python} -m auto_agent.cli plan --channel 세모지 >> {log_dir}/plan-semoji.log 2>&1',
    # 일요일 KST 06:00 이로미즘 주간 리뷰 = UTC 21:00 (토요일)
    '0 21 * * 6 cd {workspace} && {python} -m auto_agent.cli analyze --weekly --channel 이로미즘 >> {log_dir}/weekly-iromism.log 2>&1',
    # 일요일 KST 06:10 세모지 주간 리뷰 = UTC 21:10 (토요일)
    '10 21 * * 6 cd {workspace} && {python} -m auto_agent.cli analyze --weekly --channel 세모지 >> {log_dir}/weekly-semoji.log 2>&1',
]


def setup_cron(workspace: str, python: str = "python3"):
    """cron 엔트리 등록."""
    log_dir = Path(workspace) / "logs" / "intelligence"
    log_dir.mkdir(parents=True, exist_ok=True)

    # 기존 crontab 가져오기
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    # 마커로 기존 인텔리전스 루프 항목 제거
    marker_start = "# === KAIROS INTELLIGENCE LOOP START ==="
    marker_end = "# === KAIROS INTELLIGENCE LOOP END ==="

    lines = existing.split("\n")
    filtered = []
    skip = False
    for line in lines:
        if marker_start in line:
            skip = True
            continue
        if marker_end in line:
            skip = False
            continue
        if not skip:
            filtered.append(line)

    # 새 항목 추가
    filtered.append("")
    filtered.append(marker_start)
    for entry in CRON_ENTRIES:
        filtered.append(
            entry.format(
                workspace=workspace,
                python=python,
                log_dir=str(log_dir),
            )
        )
    filtered.append(marker_end)

    # crontab 등록
    new_crontab = "\n".join(filtered).strip() + "\n"
    proc = subprocess.run(
        ["crontab", "-"],
        input=new_crontab,
        text=True,
        capture_output=True,
    )
    if proc.returncode == 0:
        print(f"✅ cron 등록 완료 ({len(CRON_ENTRIES)}개 스케줄)")
        for entry in CRON_ENTRIES:
            print(f"  {entry.split('{')[0].strip()}")
    else:
        print(f"❌ cron 등록 실패: {proc.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    workspace = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    python = sys.argv[2] if len(sys.argv) > 2 else "python3"
    setup_cron(workspace, python)
```

- [ ] **Step 2: CLI에 cron setup 명령 추가**

```python
def cmd_cron(args):
    """cron 스케줄 설정 (인텔리전스 루프)."""
    from auto_agent.paths import get_workspace_dir

    if not args or args[0] == "setup":
        workspace = str(get_workspace_dir())
        python = sys.executable
        from auto_agent.scripts.setup_cron import setup_cron
        setup_cron(workspace, python)
    elif args[0] == "list":
        import subprocess
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        console.print(result.stdout if result.returncode == 0 else "crontab 비어있음")
    elif args[0] == "remove":
        from auto_agent.scripts.setup_cron import setup_cron
        # 마커 사이만 제거하는 로직
        print_warning("인텔리전스 루프 cron 항목을 제거합니다.")
    else:
        print_error("Usage: auto-agent cron [setup|list|remove]")
```

COMMANDS에 등록:
```python
"cron": cmd_cron,
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/setup_cron.py auto_agent/cli.py
git commit -m "feat: cron 스케줄 설정 — 매일 수집+기획, 주간 리뷰 자동화"
```

---

## 완료 체크

Phase 1b 완료 시 사용 가능한 전체 명령어:

```bash
# Phase 1a
auto-agent collect --all               # 데이터 수집
auto-agent collect --youtube            # YouTube만
auto-agent link --project <slug> --video-id <id>  # 영상 연결

# Phase 1b
auto-agent plan --channel 이로미즘      # 자율 기획
auto-agent plan --channel 이로미즘 --seed "희토류"  # 시드 기획
auto-agent analyze --video <id> --channel 이로미즘  # 영상 분석
auto-agent analyze --weekly --channel 이로미즘      # 주간 리뷰
auto-agent watchlist                    # 목록 확인
auto-agent watchlist approve <채널명>   # trial→active
auto-agent watchlist remove <채널명>    # proposed_remove→archived
auto-agent project create --from-plan <기획안.md>   # 기획안→프로젝트
auto-agent cron setup                   # cron 등록
auto-agent cron list                    # cron 확인
```

전체 자동화 흐름:
```
cron 05:30 → collect --all (수집)
cron 06:00 → plan --channel 이로미즘 (기획)
cron 06:10 → plan --channel 세모지 (기획)
→ Discord 푸시 → 아침에 확인 → 승인
→ project create --from-plan → run → link → 추적
일요일 → analyze --weekly (주간 리뷰) → 피드백 루프
```
