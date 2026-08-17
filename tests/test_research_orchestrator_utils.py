from backend.research import orchestrator


def test_explorer_count_scales_by_duration():
    assert orchestrator._explorer_count("1분") == 3
    assert orchestrator._explorer_count("3분") == 4
    assert orchestrator._explorer_count("5분") == 5
    assert orchestrator._explorer_count("10분") == 6
    assert orchestrator._explorer_count("") == 3


def test_digest_counts_sources_and_notes():
    sources = [{"title": "A", "lane": "wikipedia", "tier_hint": "A"},
               {"title": "B", "lane": "crossref", "tier_hint": "B"}]
    notes = ["note1", "", "note3"]
    d = orchestrator._digest(sources, notes)
    assert d["source_count"] == 2
    assert d["web_note_count"] == 2
    assert d["lanes"]["wikipedia"] == 1


def test_load_sources_reads_manifests(tmp_path):
    man = tmp_path / "research" / "manifests" / "t"
    man.mkdir(parents=True)
    (man / "sources.jsonl").write_text(
        '{"title":"A","url":"u","lane":"wikipedia","tier_hint":"A","snippet":"s"}\n',
        encoding="utf-8")
    src = orchestrator._load_sources(tmp_path)
    assert len(src) == 1 and src[0]["title"] == "A"
