from pathlib import Path
import json

from auto_agent.progress import report_doc


def test_report_doc_writes_structured_event(monkeypatch, tmp_path: Path):
    progress_file = tmp_path / ".progress.jsonl"
    monkeypatch.setenv("PROGRESS_FILE", str(progress_file))

    report_doc(
        agent="홍탐정",
        project="demo",
        doc_type="research",
        doc_id="stage1-research",
        op="snapshot",
        value={"summary": "초기 리서치 스냅샷"},
        phase="stage_1",
        text="리서치 문서 초기화",
    )

    rows = [json.loads(line) for line in progress_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "doc_update"
    assert rows[0]["project"] == "demo"
    assert rows[0]["data"]["doc_type"] == "research"
    assert rows[0]["data"]["op"] == "snapshot"
    assert rows[0]["data"]["value"]["summary"] == "초기 리서치 스냅샷"
