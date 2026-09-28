import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "auto_agent/data/skills/agents/manuscript-reviewer/SKILL.md"


def test_reviewer_has_cross_chapter_gate_and_listener_lens():
    text = SKILL.read_text(encoding="utf-8")
    assert "G6 챕터 간 정합" in text
    assert "listener_pass" in text and "viewer-personas" in text
    assert "원고 전체에 다시 건다" in text  # 재심 규칙 예외


def test_manuscript_review_step_loads_viewer_personas():
    pipeline = json.loads((ROOT / "auto_agent/data/pipeline.json").read_text(encoding="utf-8"))
    step = next(s for ph in pipeline["phases"] for s in ph["steps"] if s["id"] == "step_2_manuscript_review")
    assert "shared/viewer-personas" in step["skills"]


def test_youtube_eval_reads_the_same_personas():
    sys.path.insert(0, str(ROOT / "scripts"))
    import youtube_eval
    md = (ROOT / "auto_agent/data/skills/shared/viewer-personas.md").read_text(encoding="utf-8")
    assert youtube_eval.PERSONAS.startswith("## 보는 사람 넷")
    assert youtube_eval.PERSONAS.strip() in md
