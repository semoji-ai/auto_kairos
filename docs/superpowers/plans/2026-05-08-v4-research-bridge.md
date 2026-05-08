# v4 Research Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v4의 리서치/원고 작성 스킬을 v3 워크트리에 이식하고, v4 산출물(`final_manuscript.md` 등)을 v3 Stage 2 입력 4종으로 변환하는 어댑터를 구축해 v3 Stage 3 렌더링까지 무수정 연결한다.

**Architecture:** v4 본가 `~/Projects/auto_kairos_v4/skills/`에서 리서치/원고 스킬 11종을 워크트리 `.claude/skills/v4/`로 rsync 이식. 새 패키지 `auto_agent/modules/v4_bridge/`가 어댑터 책임을 진다 — 결정론적 빌더 3종(outline.json, research_report.json, art_style.json) + LLM 에이전트 1종(chapter_marker_agent). 어댑터 산출물은 `output/{slug}/_bridge/`에 쓰고 v3가 기대하는 위치로 복사한다.

**Tech Stack:** Python 3.11, pathlib, Claude CLI(stdin), rsync, pytest, v3 기존 `auto_agent.runner` 호출 패턴

**Spec:** `docs/superpowers/specs/2026-05-08-v4-research-bridge-design.md`

---

## Task 0: 워크트리 생성 + v3 스키마 잠금

**Files:**
- Create: `scripts/sync_v4_skills.sh`
- Create: `.claude/skills/v4/VERSION.txt`
- Create: `auto_agent/modules/v4_bridge/__init__.py`
- Create: `auto_agent/modules/v4_bridge/schema_samples/outline.example.json`
- Create: `auto_agent/modules/v4_bridge/schema_samples/research_report.example.json`
- Create: `auto_agent/modules/v4_bridge/schema_samples/art_style.example.json`

- [ ] **Step 1: 워크트리 생성**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3
git worktree add -b v4-research-bridge ../auto_kairos_v3-v4bridge main
cd ../auto_kairos_v3-v4bridge
```

확인: `git branch --show-current` → `v4-research-bridge`

- [ ] **Step 2: v3 outline.json/research_report.json/art_style.json 스키마 추출**

`script-director` SKILL.md, `auto_agent/data/agents.json`, `auto_agent/runner.py`에서 outline.json/research_report.json/art_style.json 키 목록을 grep으로 추출한다.

```bash
grep -rn "outline.json\|research_report.json\|art_style.json" auto_agent/ | grep -v ".pyc" | head -50
grep -rn "\"chapters\":\|\"claims\":\|\"sources\":\|\"creative_brief\":" auto_agent/data/skills/agents/ | head -20
```

각 파일의 필수 키를 직접 작성한 example JSON 3개를 `auto_agent/modules/v4_bridge/schema_samples/`에 저장한다. 형식 추정 시 다음 우선순위: (1) JSON Schema 또는 pydantic 모델이 코드에 있으면 그것, (2) script-director SKILL.md의 출력 예시, (3) runner.py가 읽는 키들.

이 example 파일들이 Task 2~4의 빌더가 생성할 JSON의 ground truth가 된다.

- [ ] **Step 3: v4 스킬 동기화 스크립트 작성**

```bash
#!/usr/bin/env bash
# scripts/sync_v4_skills.sh
set -euo pipefail
V4_ROOT="${V4_ROOT:-$HOME/Projects/auto_kairos_v4}"
DEST=".claude/skills/v4"
SKILLS=(
  strategy-explore fresh-research deep-research wiki-organize
  draft-write target-research review-research
  fact-check proofread vault-search vault-absorb shared
)
mkdir -p "$DEST"
for s in "${SKILLS[@]}"; do
  rsync -av --delete "$V4_ROOT/skills/$s/" "$DEST/$s/"
done
git -C "$V4_ROOT" rev-parse HEAD > "$DEST/VERSION.txt"
echo "Synced v4 skills @ $(cat $DEST/VERSION.txt)"
```

```bash
chmod +x scripts/sync_v4_skills.sh
ls ~/Projects/auto_kairos_v4 || ls ~/LocalProjects/auto_kairos_v4
```

`V4_ROOT` 경로 확인 후 실제 위치(`~/LocalProjects/auto_kairos_v4`)로 스크립트 수정.

- [ ] **Step 4: 첫 동기화 실행**

```bash
V4_ROOT=$HOME/LocalProjects/auto_kairos_v4 bash scripts/sync_v4_skills.sh
ls .claude/skills/v4/
cat .claude/skills/v4/VERSION.txt
```

기대 출력: 12개 디렉토리 + VERSION.txt에 v4 git hash.

- [ ] **Step 5: v4_bridge 패키지 골격**

```python
# auto_agent/modules/v4_bridge/__init__.py
"""v4 research/script artifacts → v3 Stage 2 input adapter."""
from .adapter import run_adapter

__all__ = ["run_adapter"]
```

- [ ] **Step 6: 커밋**

```bash
git add scripts/sync_v4_skills.sh .claude/skills/v4 auto_agent/modules/v4_bridge
git commit -m "chore(v4-bridge): 워크트리 + v4 스킬 동기화 + 스키마 샘플"
```

---

## Task 1: outline.json 빌더 ~~[REVERTED]~~

> **폐기 이유:** PD가 원고를 작성하는 시점에 챕터 구조를 이미 알고 있으므로, plan.md에서 LLM/정규식으로 역파싱할 필요가 없다. PD가 `finalize-for-bridge` 스킬 따라 `outline.json`을 직접 작성한다. `build_outline.py`와 관련 테스트/픽스처는 git rm으로 제거됨.

**Files:**
- ~~Create: `auto_agent/modules/v4_bridge/build_outline.py`~~ (삭제됨)
- ~~Create: `tests/v4_bridge/test_build_outline.py`~~ (삭제됨)
- ~~Create: `tests/v4_bridge/fixtures/plan.md`~~ (삭제됨)

- [ ] **Step 1: 픽스처 작성** — v4 plan.md 샘플

```markdown
<!-- tests/v4_bridge/fixtures/plan.md -->
# 영상 기획안

## 핵심 질문
다이소가 어떻게 1500원으로 살아남는가?

## 챕터 구조
1. **Ch 1. 가격의 비밀** — 1000원/2000원/3000원/5000원 4가격 정책
2. **Ch 2. 매입의 힘** — 직매입 + 대량 발주
3. **Ch 3. 회전율** — 일 단위 재고 회전

## 크리에이티브 브리프
- 톤: 차분한 교양
- 분량: 1분
- 핵심 인식: "싸구려가 아니라 효율의 결과"
```

- [ ] **Step 2: 실패 테스트 작성**

```python
# tests/v4_bridge/test_build_outline.py
import json
from pathlib import Path
from auto_agent.modules.v4_bridge.build_outline import build_outline

FIXTURE = Path(__file__).parent / "fixtures" / "plan.md"

def test_build_outline_extracts_chapters():
    result = build_outline(FIXTURE.read_text())
    assert len(result["chapters"]) == 3
    assert result["chapters"][0]["title"] == "가격의 비밀"
    assert "1000원" in result["chapters"][0]["beats"][0]

def test_build_outline_extracts_brief():
    result = build_outline(FIXTURE.read_text())
    assert result["creative_brief"]["tone"] == "차분한 교양"
    assert result["creative_brief"]["duration"] == "1분"
    assert "효율" in result["creative_brief"]["core_takeaway"]
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_v3-v4bridge
pytest tests/v4_bridge/test_build_outline.py -v
```

기대: ImportError (`build_outline` 미정의).

- [ ] **Step 4: 최소 구현**

`schema_samples/outline.example.json`을 참고해서 정확한 키를 맞춘다. 아래는 일반 골격 — 실제 키 이름은 Task 0 Step 2에서 잠근 것을 사용.

```python
# auto_agent/modules/v4_bridge/build_outline.py
"""plan.md (v4) → outline.json (v3) deterministic builder."""
import re
from typing import Any

CHAPTER_LINE_RE = re.compile(r"^\s*\d+\.\s+\*\*Ch\s+\d+\.\s+([^*]+?)\*\*\s*[—-]\s*(.+)$", re.MULTILINE)
BRIEF_FIELD_RE = re.compile(r"^-\s*([^:]+):\s*(.+)$", re.MULTILINE)
SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

def build_outline(plan_md: str) -> dict[str, Any]:
    chapters = []
    for m in CHAPTER_LINE_RE.finditer(plan_md):
        title, beats_inline = m.group(1).strip(), m.group(2).strip()
        chapters.append({
            "title": title,
            "beats": [b.strip() for b in beats_inline.split("+")],
        })

    brief_section = _extract_section(plan_md, "크리에이티브 브리프")
    brief = {}
    for m in BRIEF_FIELD_RE.finditer(brief_section or ""):
        key = m.group(1).strip()
        val = m.group(2).strip()
        if key == "톤": brief["tone"] = val
        elif key == "분량": brief["duration"] = val
        elif key == "핵심 인식": brief["core_takeaway"] = val

    core_q = _extract_section(plan_md, "핵심 질문")
    return {
        "core_question": (core_q or "").strip(),
        "chapters": chapters,
        "creative_brief": brief,
    }

def _extract_section(text: str, heading: str) -> str | None:
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else None
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/v4_bridge/test_build_outline.py -v
```

기대: 2 passed.

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/modules/v4_bridge/build_outline.py tests/v4_bridge/
git commit -m "feat(v4-bridge): plan.md → outline.json 빌더"
```

---

## Task 2: research_report.json 빌더

**Files:**
- Create: `auto_agent/modules/v4_bridge/build_research_report.py`
- Create: `tests/v4_bridge/test_build_research_report.py`
- Create: `tests/v4_bridge/fixtures/research_reports/report_01.md`
- Create: `tests/v4_bridge/fixtures/research_targeted/targeted_01.md`

- [ ] **Step 1: 픽스처 작성**

`tests/v4_bridge/fixtures/research_reports/report_01.md`:

```markdown
# 다이소 가격 정책 리서치

## 주장
- 다이소는 1000원/2000원/3000원/5000원 4가격 정책 운영. [출처: 박정부 회장 인터뷰, 매일경제 2018-03-12]
- 직매입 비중 70% 이상. [출처: 다이소 공시자료 2022]

## 인용
> "균일가는 약속입니다." — 박정부 회장, 매일경제 2018-03-12

## 출처
1. 매일경제 2018-03-12 — 박정부 회장 단독 인터뷰
2. 다이소 2022 사업보고서
```

`tests/v4_bridge/fixtures/research_targeted/targeted_01.md` — 비슷한 형식.

- [ ] **Step 2: 실패 테스트 작성**

```python
# tests/v4_bridge/test_build_research_report.py
from pathlib import Path
from auto_agent.modules.v4_bridge.build_research_report import build_research_report

FIXTURE_DIR = Path(__file__).parent / "fixtures"

def test_build_research_report_merges_sources():
    result = build_research_report(
        reports_dir=FIXTURE_DIR / "research_reports",
        targeted_dir=FIXTURE_DIR / "research_targeted",
    )
    assert len(result["claims"]) >= 2
    assert any("4가격 정책" in c["text"] for c in result["claims"])
    assert len(result["sources"]) >= 2
    assert len(result["quotes"]) >= 1
    assert "균일가는 약속" in result["quotes"][0]["text"]
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
pytest tests/v4_bridge/test_build_research_report.py -v
```

기대: ImportError.

- [ ] **Step 4: 최소 구현**

```python
# auto_agent/modules/v4_bridge/build_research_report.py
"""v4 research_reports/ + research_targeted/ → research_report.json (v3)."""
import re
from pathlib import Path
from typing import Any

CLAIM_RE = re.compile(r"^-\s+(.+?)\s*\[출처:\s*([^\]]+)\]\s*$", re.MULTILINE)
QUOTE_RE = re.compile(r"^>\s+\"([^\"]+)\"\s*[—-]\s*(.+)$", re.MULTILINE)
SOURCE_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)

def build_research_report(reports_dir: Path, targeted_dir: Path) -> dict[str, Any]:
    claims, quotes, sources = [], [], []
    for d in (reports_dir, targeted_dir):
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            text = md.read_text()
            for m in CLAIM_RE.finditer(text):
                claims.append({"text": m.group(1).strip(), "source": m.group(2).strip()})
            for m in QUOTE_RE.finditer(text):
                quotes.append({"text": m.group(1).strip(), "attribution": m.group(2).strip()})
            src_section = _extract_section(text, "출처")
            if src_section:
                for m in SOURCE_RE.finditer(src_section):
                    sources.append({"citation": m.group(1).strip()})
    return {"claims": claims, "quotes": quotes, "sources": _dedupe(sources)}

def _extract_section(text: str, heading: str) -> str | None:
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    m = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else None

def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        key = it.get("citation") or it.get("text")
        if key in seen: continue
        seen.add(key); out.append(it)
    return out
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/v4_bridge/test_build_research_report.py -v
```

기대: 1 passed.

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/modules/v4_bridge/build_research_report.py tests/v4_bridge/
git commit -m "feat(v4-bridge): v4 research → research_report.json 빌더"
```

---

## Task 3: art_style.json 빌더

**Files:**
- Create: `auto_agent/modules/v4_bridge/build_art_style.py`
- Create: `tests/v4_bridge/test_build_art_style.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/v4_bridge/test_build_art_style.py
from auto_agent.modules.v4_bridge.build_art_style import build_art_style

def test_build_art_style_default():
    result = build_art_style(style_id="quirky_cartoon", theme="dark")
    assert result["style_id"] == "quirky_cartoon"
    assert result["theme"] == "dark"
    assert result["voice_id"]  # 디폴트 보이스 ID 채워짐

def test_build_art_style_with_overrides():
    result = build_art_style(style_id="semoji", theme="light", voice_id="custom-voice")
    assert result["style_id"] == "semoji"
    assert result["voice_id"] == "custom-voice"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/v4_bridge/test_build_art_style.py -v
```

- [ ] **Step 3: 최소 구현**

```python
# auto_agent/modules/v4_bridge/build_art_style.py
"""art_style.json (v3 스키마) 빌더 — PD 결정값 또는 워크트리 디폴트."""
from typing import Any

DEFAULT_VOICE_BY_STYLE = {
    "quirky_cartoon": "iromism-default",
    "semoji": "semoji-default",
    "lego": "neutral-default",
    "stickman_cute": "neutral-default",
}

def build_art_style(style_id: str = "quirky_cartoon", theme: str = "dark", voice_id: str | None = None) -> dict[str, Any]:
    return {
        "style_id": style_id,
        "theme": theme,
        "voice_id": voice_id or DEFAULT_VOICE_BY_STYLE.get(style_id, "neutral-default"),
    }
```

실제 art_style.json은 추가 키(design_tokens 참조 등)가 더 있을 수 있다. Task 0 Step 2에서 잠근 example에 맞춰 키 추가. 추가 키도 디폴트값으로 채운다.

- [ ] **Step 4: 테스트 통과**

```bash
pytest tests/v4_bridge/test_build_art_style.py -v
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/v4_bridge/build_art_style.py tests/v4_bridge/test_build_art_style.py
git commit -m "feat(v4-bridge): art_style.json 빌더"
```

---

## Task 4: chapter_marker_agent (LLM 호출) ~~[REVERTED]~~

> **폐기 이유:** LLM이 narration을 변경하거나 챕터 경계를 잘못 자르는 위험이 있다. PD가 원고 작성 시점에 챕터 경계를 이미 파악하고 있으므로, LLM 에이전트 없이 PD가 `finalize-for-bridge` 스킬 따라 직접 마커를 삽입한다. `chapter_marker.py`, `chapter-marker` 에이전트 항목, 관련 테스트는 git rm으로 제거됨.

**Files:**
- ~~Create: `auto_agent/modules/v4_bridge/chapter_marker.py`~~ (삭제됨)
- ~~Create: `auto_agent/data/skills/agents/chapter-marker/SKILL.md`~~ (삭제됨)
- ~~Modify: `auto_agent/data/agents.json`~~ (chapter-marker 항목 제거됨)
- ~~Create: `tests/v4_bridge/test_chapter_marker.py`~~ (삭제됨)
- ~~Create: `tests/v4_bridge/fixtures/final_manuscript.md`~~ (테스트 어댑터에서 계속 사용, 유지)

- [ ] **Step 1: 에이전트 SKILL.md 작성**

```markdown
<!-- auto_agent/data/skills/agents/chapter-marker/SKILL.md -->
# chapter-marker

## 역할
v4 final_manuscript.md(마커 없는 한 호흡 prose)에 v3 script-director (chapters) 모드가 요구하는 마커를 삽입한다. **narration 본문은 한 글자도 수정하지 않는다.**

## 입력
- `final_manuscript.md` — 인라인
- `outline.json` — 챕터 구조 (인라인)

## 출력
- `final_manuscript_marked.md` — 마커 삽입된 manuscript

## 마커 규칙
1. 챕터 시작 위치에 `# Ch N. <제목>` 라인 삽입 (outline.json `chapters[].title` 사용)
2. 8~15초(약 60~120자) 의미 단위마다 `---` 라인 삽입
3. 캐릭터 등장 단락 바로 앞에 `<!-- chars: ID1, ID2 -->` 주석 (outline.json/wiki에 캐릭터 ID가 있을 때만)

## 절대 금지
- narration 문장 변경/추가/삭제
- 챕터 경계를 outline과 다르게 자르기
```

- [ ] **Step 2: agents.json에 에이전트 등록**

```bash
# auto_agent/data/agents.json 수정 — 기존 에이전트 항목 형식을 그대로 따라
```

기존 항목(예: `script-director`)을 참고해 `chapter-marker` 항목 추가:

```json
{
  "name": "chapter-marker",
  "model": "sonnet",
  "max_turns": 8,
  "skill": "chapter-marker",
  "allowed_tools": ["Read", "Write"]
}
```

- [ ] **Step 3: 호출 wrapper 작성 (실패 테스트 우선)**

```python
# tests/v4_bridge/fixtures/final_manuscript.md
다이소가 1500원짜리 물건을 어떻게 팔까요. 비결은 직매입과 회전율입니다.
박정부 회장은 균일가가 약속이라고 말합니다. 4가격 정책은 30년째 지켜진 원칙입니다.
하루 세 번 진열을 바꾸는 매장도 있습니다. 회전율이 곧 마진입니다.
```

```python
# tests/v4_bridge/test_chapter_marker.py
import pytest
from pathlib import Path
from auto_agent.modules.v4_bridge.chapter_marker import insert_markers

FIXTURE = Path(__file__).parent / "fixtures" / "final_manuscript.md"

@pytest.mark.integration
def test_insert_markers_preserves_substring(tmp_path):
    """LLM 호출 통합 테스트 — narration substring 무결성 검증."""
    manuscript = FIXTURE.read_text()
    outline = {
        "chapters": [
            {"title": "가격의 비밀", "beats": ["4가격 정책"]},
            {"title": "회전율", "beats": ["하루 세 번 진열"]},
        ]
    }
    marked = insert_markers(manuscript, outline, project_dir=tmp_path)
    # 본문 substring 유지: 마커/주석/공백 제거 후 원본과 일치
    stripped = "\n".join(
        line for line in marked.splitlines()
        if not line.startswith("#") and line.strip() != "---" and not line.startswith("<!--")
    )
    assert manuscript.strip() in stripped.strip().replace("\n\n", "\n")
    assert "# Ch 1." in marked
    assert "# Ch 2." in marked
    assert "---" in marked
```

- [ ] **Step 4: 실패 확인**

```bash
pytest tests/v4_bridge/test_chapter_marker.py -v -m integration
```

기대: ImportError.

- [ ] **Step 5: 호출 wrapper 구현**

```python
# auto_agent/modules/v4_bridge/chapter_marker.py
"""chapter-marker agent caller — narration substring 보존하며 마커 삽입."""
import json
from pathlib import Path
from auto_agent.runner import run_agent  # v3 기존 stdin 호출 패턴

def insert_markers(manuscript: str, outline: dict, project_dir: Path) -> str:
    """
    chapter-marker 에이전트를 호출해 manuscript에 # Ch N. / --- / <!-- chars --> 마커 삽입.
    narration 본문은 절대 수정 안 됨(에이전트 SKILL.md 제약 + post-validation).
    """
    payload = {
        "final_manuscript": manuscript,
        "outline": outline,
    }
    workdir = project_dir / "_bridge"
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "_chapter_marker_input.json").write_text(json.dumps(payload, ensure_ascii=False))

    out_path = workdir / "final_manuscript_marked.md"
    run_agent(
        agent_name="chapter-marker",
        stdin=json.dumps(payload, ensure_ascii=False),
        cwd=workdir,
        output_files=[out_path],
        timeout_s=600,
    )

    marked = out_path.read_text()
    _validate_substring(manuscript, marked)
    return marked

def _validate_substring(original: str, marked: str) -> None:
    """마커/주석/공백 제거 후 원본 본문이 그대로 들어 있는지 확인."""
    stripped_lines = [
        line for line in marked.splitlines()
        if not line.startswith("#") and line.strip() != "---" and not line.startswith("<!--")
    ]
    stripped = "\n".join(stripped_lines).strip()
    # 정규화 — 빈 줄 압축
    norm = lambda s: "\n".join(l for l in s.splitlines() if l.strip())
    if norm(original) not in norm(stripped):
        raise ValueError(
            "chapter-marker가 narration을 변경했습니다. "
            "manuscript와 marked의 본문이 substring 관계가 아닙니다."
        )
```

`run_agent`의 정확한 시그니처는 `auto_agent/runner.py`를 보고 맞춘다 — 이름·인자가 다르면 실제 시그니처에 맞게 수정한다. v3가 다른 에이전트를 호출하는 코드(예: script-director 호출부)를 참고하는 것이 가장 안전.

- [ ] **Step 6: integration 테스트 통과 확인 (LLM 호출 비용 발생)**

```bash
pytest tests/v4_bridge/test_chapter_marker.py -v -m integration
```

기대: PASS. 실패 시 SKILL.md 프롬프트를 더 엄격하게 조정 후 재실행.

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/modules/v4_bridge/chapter_marker.py \
        auto_agent/data/skills/agents/chapter-marker/ \
        auto_agent/data/agents.json \
        tests/v4_bridge/test_chapter_marker.py tests/v4_bridge/fixtures/final_manuscript.md
git commit -m "feat(v4-bridge): chapter-marker 에이전트 + narration substring 보존 검증"
```

---

## Task 4-bis: finalize-for-bridge 스킬 (신규)

> Task 1 + Task 4 폐기로 인한 대체. PD가 직접 outline.json + final_manuscript_marked.md를 작성할 때 따르는 가이드 스킬.

**Files:**
- Create: `.claude/skills/v4/finalize-for-bridge/SKILL.md`

- [x] **Step 1: SKILL.md 작성** — 작성 완료. 규칙: 마커 삽입 방법, outline.json 스키마, 절차, 금지 사항, 한국어 규칙.

---

## Task 5: adapter.py — CLI + 통합 (단순화됨)

> **변경 (리팩터):** adapter.py는 더 이상 build_outline / chapter_marker를 호출하지 않는다. PD 작성 파일(outline.json + final_manuscript_marked.md) 존재 확인 + substring 검증 + research_report 빌드 + art_style 빌드 + 복사만 수행한다.

**Files:**
- Modify: `auto_agent/modules/v4_bridge/adapter.py`
- Modify: `tests/v4_bridge/test_adapter.py`

- [ ] **Step 1: 실패 테스트**

```python
# tests/v4_bridge/test_adapter.py
import json
from pathlib import Path
import shutil
from auto_agent.modules.v4_bridge.adapter import run_adapter

FIXTURE = Path(__file__).parent / "fixtures"

def test_run_adapter_produces_4_artifacts(tmp_path, monkeypatch):
    project = tmp_path / "abc12345_test"
    project.mkdir()
    shutil.copy(FIXTURE / "plan.md", project / "plan.md")
    shutil.copy(FIXTURE / "final_manuscript.md", project / "final_manuscript.md")
    (project / "research_reports").mkdir()
    shutil.copy(FIXTURE / "research_reports" / "report_01.md", project / "research_reports" / "report_01.md")
    (project / "research_targeted").mkdir()
    shutil.copy(FIXTURE / "research_targeted" / "targeted_01.md", project / "research_targeted" / "targeted_01.md")

    # chapter-marker LLM 호출 mock — substring 보존만 확인
    def fake_insert_markers(manuscript, outline, project_dir):
        return f"# Ch 1. 가격의 비밀\n\n{manuscript}\n\n---\n"
    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        fake_insert_markers,
    )

    run_adapter(project_dir=project)

    # 4개 산출물이 _bridge/ + 프로젝트 루트 양쪽에 존재
    for fname in ["final_manuscript_marked.md", "outline.json", "research_report.json", "art_style.json"]:
        assert (project / "_bridge" / fname).exists(), f"_bridge/{fname} missing"
        assert (project / fname).exists(), f"root/{fname} missing (copy)"

    outline = json.loads((project / "outline.json").read_text())
    assert len(outline["chapters"]) == 3
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/v4_bridge/test_adapter.py -v
```

- [ ] **Step 3: 어댑터 구현**

```python
# auto_agent/modules/v4_bridge/adapter.py
"""v4 산출물 → v3 Stage 2 입력 변환 어댑터 (CLI 진입점)."""
import argparse
import json
import shutil
import sys
from pathlib import Path

from auto_agent.modules.v4_bridge.build_outline import build_outline
from auto_agent.modules.v4_bridge.build_research_report import build_research_report
from auto_agent.modules.v4_bridge.build_art_style import build_art_style
from auto_agent.modules.v4_bridge.chapter_marker import insert_markers

V3_ARTIFACTS = ["final_manuscript_marked.md", "outline.json", "research_report.json", "art_style.json"]

def run_adapter(project_dir: Path, style_id: str = "quirky_cartoon", theme: str = "dark") -> dict:
    project_dir = Path(project_dir).resolve()
    bridge = project_dir / "_bridge"
    bridge.mkdir(parents=True, exist_ok=True)

    plan_md = (project_dir / "plan.md").read_text()
    manuscript = (project_dir / "final_manuscript.md").read_text()

    outline = build_outline(plan_md)
    (bridge / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2))

    research = build_research_report(
        reports_dir=project_dir / "research_reports",
        targeted_dir=project_dir / "research_targeted",
    )
    (bridge / "research_report.json").write_text(json.dumps(research, ensure_ascii=False, indent=2))

    art_style = build_art_style(style_id=style_id, theme=theme)
    (bridge / "art_style.json").write_text(json.dumps(art_style, ensure_ascii=False, indent=2))

    marked = insert_markers(manuscript, outline, project_dir)
    (bridge / "final_manuscript_marked.md").write_text(marked)

    # v3가 기대하는 위치(프로젝트 루트)로 복사
    for f in V3_ARTIFACTS:
        shutil.copy(bridge / f, project_dir / f)

    return {"artifacts": [str(project_dir / f) for f in V3_ARTIFACTS]}

def _resolve_project(slug: str) -> Path:
    """slug로 output/{uuid}_{slug}/ 디렉토리 찾기."""
    output = Path("output")
    matches = [d for d in output.iterdir() if d.is_dir() and d.name.endswith(f"_{slug}")]
    if not matches:
        raise FileNotFoundError(f"output/*_{slug}/ 디렉토리를 찾을 수 없습니다.")
    if len(matches) > 1:
        raise ValueError(f"slug {slug}와 매칭되는 디렉토리 {len(matches)}개. uuid 접두사로 구분 필요.")
    return matches[0]

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="v4 → v3 Stage 2 입력 어댑터")
    p.add_argument("--project", required=True, help="프로젝트 slug 또는 절대경로")
    p.add_argument("--style-id", default="quirky_cartoon")
    p.add_argument("--theme", default="dark")
    args = p.parse_args(argv)

    project_dir = Path(args.project) if Path(args.project).is_absolute() else _resolve_project(args.project)
    result = run_adapter(project_dir, style_id=args.style_id, theme=args.theme)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/v4_bridge/test_adapter.py -v
```

기대: 1 passed (chapter-marker는 mock 처리).

- [ ] **Step 5: 전체 v4_bridge 테스트 묶음 실행**

```bash
pytest tests/v4_bridge/ -v -m "not integration"
```

기대: 4~5 passed (integration 마커 제외).

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/modules/v4_bridge/adapter.py tests/v4_bridge/test_adapter.py
git commit -m "feat(v4-bridge): adapter CLI — 4개 산출물 통합 생성"
```

---

## Task 6: WORKTREE.md + 진입점 안내

**Files:**
- Create: `WORKTREE.md`

- [ ] **Step 1: WORKTREE.md 작성**

```markdown
# v4-research-bridge 워크트리 운영 안내

이 워크트리는 v4의 리서치/원고 방식을 v3에 이식해 검증하는 실험 환경입니다.

## 운영 모드: PD 대화형

메인 Claude는 v4 CLAUDE.md의 PD(프로듀서) 운영 방식을 따릅니다 — 매 단계 사용자 합의 + 서브에이전트 위임.

리서치/원고 스킬은 `.claude/skills/v4/` 에서 호출합니다(strategy-explore, fresh-research, deep-research, wiki-organize, draft-write, target-research, fact-check, proofread 등).

## 프로젝트 폴더

v3 컨벤션 그대로: `output/{uuid}_{slug}/`. v4 스킬에는 `--project-root output/{uuid}_{slug}` 인자로 경로를 주입합니다.

## 단계

1. PD 대화로 `plan.md` 확정 → `output/{slug}/plan.md`
2. 리서치 → `research_reports/`, `research_targeted/`
3. (선택) 위키 정리 → `wiki/`
4. 드래프트 → `drafts/draft_v1.md`
5. 타겟 리서치 + 보완 → `drafts/draft_v2.md`
6. fact-check + proofread → `final_manuscript.md`

## 어댑터 실행

`final_manuscript.md` 확정 후:

\`\`\`bash
python -m auto_agent.modules.v4_bridge.adapter --project <slug>
\`\`\`

이 시점에 `output/{slug}/` 안에 다음이 생성됩니다:
- `_bridge/` (작업 산출물)
- `final_manuscript_marked.md`, `outline.json`, `research_report.json`, `art_style.json` (v3 Stage 2 입력)

## Stage 3 진입

\`\`\`bash
auto-agent run --project <slug> --from step_2
\`\`\`

이후 step_2 (script-director chapters) → step_2_consistency → step_2_data → step_2b/c/d → step_3b → step_3c. **Stage 3 코드는 무수정**.

## v4 스킬 동기화

v4 본가 업데이트 반영:

\`\`\`bash
V4_ROOT=$HOME/LocalProjects/auto_kairos_v4 bash scripts/sync_v4_skills.sh
\`\`\`

## 검증 끝나면

main으로 머지하면서 v3의 step_1/step_2 파이프라인을 v4 방식으로 점진 대체합니다.
```

- [ ] **Step 2: 커밋**

```bash
git add WORKTREE.md
git commit -m "docs(v4-bridge): 워크트리 운영 안내 추가"
```

---

## Task 7: 1차 검증 — 1분 영상 end-to-end

이 태스크는 **사용자와의 대화로 진행되는 PD 운영 단계**입니다. 코드 작성이 아니라 실제 영상을 만드는 검증입니다.

- [ ] **Step 1: 검증 주제 합의**

사용자에게: "검증 주제를 무엇으로 할까요? 짧고 단순한 1분 분량을 추천합니다(예: '다이소의 가격 비밀', '카카오톡 출시 비화 1분 요약')."

- [ ] **Step 2: 프로젝트 생성**

```bash
auto-agent project create
# 프롬프트에 따라 slug 입력 → output/{uuid}_{slug}/ 생성됨
```

- [ ] **Step 3: PD 대화 — plan.md 확정**

`.claude/skills/v4/strategy-explore`로 옵션 발산 → 사용자 합의 → `output/{slug}/plan.md` 작성. PD가 `pd_notebook.md`에 워크플로우 플랜 + 결정 로그 기록.

- [ ] **Step 4: 리서치 → final_manuscript.md**

light 경로(1분 영상은 deep까지 안 감): `fresh-research → draft-write → target-research → draft-revise → fact-check → proofread`. 각 단계 산출물을 PD가 게이트 통과시킴.

- [ ] **Step 5: 어댑터 실행**

```bash
python -m auto_agent.modules.v4_bridge.adapter --project <slug>
```

산출물 4개 존재 확인. `final_manuscript_marked.md`를 사람 눈으로 검토 — 챕터 경계 + narration substring 보존 확인.

- [ ] **Step 6: Stage 3 실행**

```bash
auto-agent run --project <slug> --from step_2
```

진행 모니터링: dashboard `python -m uvicorn app:app --host 0.0.0.0 --port 8080` → http://localhost:8080.

각 step의 통과 여부 기록:
- step_2 (script-director chapters): narration substring hook 통과?
- step_2_consistency, step_2_data
- step_2b (fact-verifier), step_2c (fact-fixer), step_2d (scene_enricher)
- step_3b (assembly-director): TTS + 이미지 + 자막 + 매니페스트
- step_3c (release-manager)

- [ ] **Step 7: 최종 mp4 확인**

`output/{slug}/{slug}_final.mp4` 생성 확인. 재생 후 다음 항목 평가:
- 사실 정확성
- 톤이 plan.md 의도와 일치하는가
- 씬 분할이 자연스러운가
- 이미지/자막 버그 없음

- [ ] **Step 8: 측정 결과를 docs에 기록**

```bash
# docs/superpowers/specs/2026-05-08-v4-research-bridge-design.md 8장 위험 항목 각각에 측정 결과 추가 후 커밋
```

- [ ] **Step 9: 커밋**

```bash
git add docs/superpowers/specs/2026-05-08-v4-research-bridge-design.md
git commit -m "docs(v4-bridge): 1차 검증 측정 결과 — 위험 항목 정량화"
```

---

## Task 8: 위험 항목 보정 (조건부)

Task 7의 측정 결과에 따라 다음 중 필요한 것만 진행. 각 보정은 별도 커밋.

- [ ] **8a: outline.json 빌더 키 보강** — step_2_consistency에서 키 누락으로 실패하면 `build_outline.py` + example JSON 수정.
- [ ] **8b: research_report.json LLM 추출 폴백** — 정규식 추출 정확도가 낮으면 작은 LLM 추출 호출 추가.
- [ ] **8c: chapter_marker_agent 프롬프트 강화** — narration 변경 또는 챕터 오분할이 발생하면 SKILL.md 제약을 더 엄격하게.
- [ ] **8d: editorial_brief 매핑 추가** — step_1c, step_2_target_deepen이 `editorial_brief.md`를 요구한다고 판명되면 `build_editorial_brief.py` 추가.
- [ ] **8e: vendor 충돌 해소** — v4 `shared/lib/_vendor`가 v3 본체와 충돌하면 import shim 추가.

각 보정 후 Task 7 Step 6~7을 다시 실행해 회귀 확인.

---

## Self-Review

**Spec 커버리지:**
- 설계 1장(범위) → Task 0 (이식), Task 1~5 (어댑터). ✅
- 설계 2장(폴더 구조) → Task 0, Task 5(adapter), Task 6(WORKTREE.md). ✅
- 설계 3장(데이터 흐름) → Task 5 어댑터 + Task 7 검증. ✅
- 설계 4장(어댑터 책임 4종) → Task 1, 2, 3, 4. ✅
- 설계 5장(호출 진입점) → Task 5 CLI + Task 6 WORKTREE.md. ✅
- 설계 6장(이식 정책) → Task 0 sync_v4_skills.sh + VERSION.txt. ✅
- 설계 7장(테스트 전략) → Task 7 + 비교 검증은 Task 7 Step 7에서 수동. ✅
- 설계 8장(위험 5건) → Task 8 (조건부 보정). ✅
- 설계 9장(단계 분해) → Task 0~8 그대로 매핑. ✅

**Placeholder 스캔:** 없음. 모든 코드 step에 실코드. Task 0 Step 2의 "schema 잠금"은 example JSON 작성으로 구체화. Task 4 Step 5의 `run_agent` 시그니처는 "v3 다른 에이전트 호출부 참고"로 fallback 명시.

**타입 일관성:** `build_outline` → dict, `build_research_report` → dict, `build_art_style` → dict, `insert_markers` → str. `run_adapter` → dict("artifacts"). 일관됨. CLI `--project` 인자는 slug 또는 절대경로 둘 다 받음 (`_resolve_project` 분기).
