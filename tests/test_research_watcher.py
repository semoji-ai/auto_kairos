from pathlib import Path

from auto_agent.orchestrator.research_watcher import ResearchManifestWatcher


def _make_watcher(project_dir: Path):
    sent: list[dict] = []

    def notifier(**kw):
        sent.append(kw)

    return ResearchManifestWatcher(
        project_dir=project_dir,
        project_slug="demo",
        notifier=notifier,
        poll_interval=0.05,
    ), sent


def test_emits_doc_update_for_new_claim(tmp_path: Path):
    topic_dir = tmp_path / "research" / "manifests" / "topic_a"
    topic_dir.mkdir(parents=True)
    (topic_dir / "claims.jsonl").write_text(
        '{"claim_id":"c1","claim":"첫 클레임","kind":"fact"}\n',
        encoding="utf-8",
    )

    w, sent = _make_watcher(tmp_path)
    w._scan_once()

    assert len(sent) == 1
    msg = sent[0]
    assert msg["kind"] == "doc_update"
    assert msg["data"]["doc_type"] == "research"
    assert msg["data"]["op"] == "upsert"
    assert msg["data"]["path"] == "claims.c1"
    assert msg["data"]["meta"]["topic"] == "topic_a"
    assert msg["data"]["value"]["claim"] == "첫 클레임"


def test_offset_tracking_skips_already_seen_lines(tmp_path: Path):
    topic_dir = tmp_path / "research" / "manifests" / "topic_a"
    topic_dir.mkdir(parents=True)
    claims_file = topic_dir / "claims.jsonl"
    claims_file.write_text('{"claim_id":"c1","claim":"first"}\n', encoding="utf-8")

    w, sent = _make_watcher(tmp_path)
    w._scan_once()
    w._scan_once()

    assert len(sent) == 1


def test_appended_claim_emits_after_offset(tmp_path: Path):
    topic_dir = tmp_path / "research" / "manifests" / "topic_a"
    topic_dir.mkdir(parents=True)
    claims_file = topic_dir / "claims.jsonl"
    claims_file.write_text('{"claim_id":"c1","claim":"first"}\n', encoding="utf-8")

    w, sent = _make_watcher(tmp_path)
    w._scan_once()

    with open(claims_file, "a", encoding="utf-8") as f:
        f.write('{"claim_id":"c2","claim":"second"}\n')
    w._scan_once()

    assert len(sent) == 2
    assert sent[1]["data"]["path"] == "claims.c2"


def test_dedup_by_claim_id_across_topics(tmp_path: Path):
    for topic in ("topic_a", "topic_b"):
        d = tmp_path / "research" / "manifests" / topic
        d.mkdir(parents=True)
        (d / "claims.jsonl").write_text(
            '{"claim_id":"shared","claim":"dup"}\n',
            encoding="utf-8",
        )

    w, sent = _make_watcher(tmp_path)
    w._scan_once()

    assert len(sent) == 1


def test_missing_manifests_dir_is_safe(tmp_path: Path):
    w, sent = _make_watcher(tmp_path)
    w._scan_once()
    assert sent == []


def test_malformed_line_is_skipped(tmp_path: Path):
    topic_dir = tmp_path / "research" / "manifests" / "topic_a"
    topic_dir.mkdir(parents=True)
    (topic_dir / "claims.jsonl").write_text(
        'NOT_JSON\n{"claim_id":"c1","claim":"valid"}\n',
        encoding="utf-8",
    )

    w, sent = _make_watcher(tmp_path)
    w._scan_once()

    assert len(sent) == 1
    assert sent[0]["data"]["path"] == "claims.c1"
