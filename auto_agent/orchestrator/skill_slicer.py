"""에이전트 SKILL.md 모드별 슬라이싱.

배경: script-director SKILL.md(44.5k자)는 씬 분할 스텝에서 챕터 수만큼(6~8회)
병렬 호출될 때마다 전문이 재주입됐다. 모드별로 실제 필요한 섹션만 남겨
편당 중복 주입량을 크게 줄인다. 상세 근거는 docs/token-waste-audit.md.

SKILL.md는 단일 소스로 유지하고 주입 시점에만 잘라낸다 (되돌리기 쉬움).
"""
from __future__ import annotations

# 모드별 정책.
#   mode_marker  : "다단계 실행 모드" 섹션에서 남길 하위 모드 헤더의 식별 문자열
#   drop_sections: 통째로 제거할 "## " 섹션 (접두 일치)
#   keep_steps   : "작업 흐름" 섹션에서 남길 "### Step N" (None이면 섹션 전체 유지)
_POLICY: dict[str, dict] = {
    "manuscript": {
        # SKILL.md 모드 1.5가 "layout/motion/mood/imageAsset/headline은
        # 이 모드의 책임이 아니다"라고 명시 → 연출 섹션 전부 제거.
        "mode_marker": "모드 1.5",
        "drop_sections": [
            "## 작업 흐름",
            "## 씬 스키마",
            "## 씬 분할 규칙",
            "## 아트스타일별 분기",
            "## 모션 프리셋 사용법",
            "## headline 규칙",
            "## 데이터 매핑 규칙",
            "## 에셋 결정 규칙",
            "## 챕터별 병렬 처리",
        ],
        "keep_steps": None,
    },
    "plan": {
        # 모드 1.8은 편 전체를 읽고 구조(beat/infoStructure/병합)만 정한다.
        # 이미지 프롬프트·헤드라인 문구·차트 설정은 모드 2 소관이므로 전부 제거.
        "mode_marker": "모드 1.8",
        "drop_sections": [
            "## 씬 스키마",
            "## 에셋 결정 규칙",
            "## 모션 프리셋 사용법",
            "## headline 규칙",
            "## 데이터 매핑 규칙",
            "## 아트스타일별 분기",
            "## 챕터별 병렬 처리",
        ],
        "keep_steps": [],
    },
    "chapters": {
        "mode_marker": "모드 2",
        "drop_sections": [],
        "keep_steps": ["Step 2"],  # 씬 작성 실무만. 구조 설계/전체 검증은 타 모드 소관
    },
    "consistency": {
        "mode_marker": "모드 3",
        "drop_sections": [],
        "keep_steps": ["Step 3"],  # 전체 검증
    },
    "outline": {
        "mode_marker": "모드 1:",
        "drop_sections": [
            "## 씬 스키마",
            "## 에셋 결정 규칙",
            "## 모션 프리셋 사용법",
        ],
        "keep_steps": ["Step 1"],
    },
}

_MODE_SECTION = "## 다단계 실행 모드"
_WORKFLOW_SECTION = "## 작업 흐름"


def _split_blocks(lines: list[str], prefix: str) -> list[tuple[int, int, str]]:
    """prefix로 시작하는 헤더 기준 블록 분할 → [(start, end, header), ...]."""
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    blocks = []
    for n, i in enumerate(idx):
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        blocks.append((i, end, lines[i]))
    return blocks


def _filter_subsections(
    section_lines: list[str], keep_predicate
) -> list[str]:
    """섹션 내 '### ' 하위 블록을 keep_predicate로 걸러낸다.

    첫 '### ' 이전의 도입부는 항상 보존한다.
    """
    subs = _split_blocks(section_lines, "### ")
    if not subs:
        return section_lines
    out = list(section_lines[: subs[0][0]])  # 섹션 헤더 + 도입부
    for start, end, header in subs:
        if keep_predicate(header):
            out.extend(section_lines[start:end])
    return out


def slice_agent_skill(skill_text: str, agent_name: str, mode: str | None) -> str:
    """모드에 필요한 섹션만 남긴 SKILL 텍스트를 반환.

    script-director 외의 에이전트, 또는 정책이 없는 모드는 원본을 그대로 돌려준다.
    """
    if agent_name != "script-director":
        return skill_text
    policy = _POLICY.get(mode or "")
    if not policy:
        return skill_text

    lines = skill_text.split("\n")
    sections = _split_blocks(lines, "## ")
    if not sections:
        return skill_text

    out: list[str] = list(lines[: sections[0][0]])  # frontmatter/프리앰블

    for start, end, header in sections:
        if any(header.startswith(d) for d in policy["drop_sections"]):
            continue

        block = lines[start:end]

        if header.startswith(_MODE_SECTION):
            marker = policy["mode_marker"]
            block = _filter_subsections(block, lambda h: marker in h)

        elif header.startswith(_WORKFLOW_SECTION) and policy["keep_steps"] is not None:
            keep = policy["keep_steps"]
            block = _filter_subsections(block, lambda h: any(k in h for k in keep))

        out.extend(block)

    return "\n".join(out)
