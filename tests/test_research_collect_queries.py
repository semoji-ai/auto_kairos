import json
from pathlib import Path
from backend.research import collector


def _patch_lanes(monkeypatch):
    monkeypatch.setattr(collector, "collect_lanes_parallel", lambda q, **k: {
        "wikipedia": [{"title": "W", "url": "https://ko.wikipedia.org/wiki/W",
                       "lane": "wikipedia", "tier_hint": "A", "kind": "reference",
                       "snippet": "s"}],
        "crossref": [{"error": "boom", "lane": "crossref"}],
    })


def test_collect_queries_writes_notes_and_manifests(tmp_path, monkeypatch):
    _patch_lanes(monkeypatch)
    events = []
    out = collector.collect_queries(tmp_path, ["유한양행"], on_event=events.append)
    assert out["sources"] == 1
    notes = list((tmp_path / "research" / "raw").rglob("*.md"))
    assert len(notes) == 1
    manifest = Path(out["manifest"])
    assert manifest.is_file()
    rows = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["title"] == "W" and rows[0]["tier_hint"] == "A"
    runs = (tmp_path / "research" / "manifests" / collector._slug("유한양행") / "runs.jsonl")
    assert runs.is_file()
    assert events


def test_collect_queries_skips_blank_and_counts(tmp_path, monkeypatch):
    _patch_lanes(monkeypatch)
    out = collector.collect_queries(tmp_path, ["", "  ", "주제"])
    assert len(out["runs"]) == 1
    assert out["sources"] == 1
