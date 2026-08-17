import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_brief_dna_present_with_levers():
    txt = (ROOT / "data" / "brief-dna.md").read_text(encoding="utf-8")
    for lever in ("narrative_arc", "human_truth", "hidden_truth"):
        assert lever in txt


def test_editorial_brief_schema_valid():
    s = json.loads((ROOT / "backend" / "schemas" / "editorial_brief.schema.json").read_text(encoding="utf-8"))
    assert s["type"] == "object"
    for k in ("real_topic", "core_question", "narrative_arc", "human_truth", "hidden_truth"):
        assert k in s["required"]


def test_brief_review_schema_valid():
    s = json.loads((ROOT / "backend" / "schemas" / "brief_review.schema.json").read_text(encoding="utf-8"))
    assert set(["score_total", "verdict", "revision_instructions"]).issubset(set(s["required"]))
    assert s["properties"]["verdict"]["enum"] == ["PASS", "REVISE", "FAIL"]
