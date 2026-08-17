import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_draft_schema_valid():
    s = json.loads((ROOT / "backend/schemas/manuscript_draft.schema.json").read_text(encoding="utf-8"))
    assert "draft_markdown" in s["required"] and "questions" in s["required"]


def test_manuscript_review_schema_valid():
    s = json.loads((ROOT / "backend/schemas/manuscript_review.schema.json").read_text(encoding="utf-8"))
    assert set(["score_total", "verdict", "revision_instructions"]).issubset(set(s["required"]))
    assert s["properties"]["verdict"]["enum"] == ["PASS", "REVISE", "FAIL"]
