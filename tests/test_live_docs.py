from auto_agent.dashboard.live_docs import reduce_doc_events


def test_reduce_doc_events_builds_manuscript_snapshot():
    events = [
        {
            "kind": "doc_update",
            "project": "demo",
            "data": {
                "doc_type": "manuscript",
                "doc_id": "stage2-manuscript",
                "op": "snapshot",
                "value": {"raw_text": "", "chapters": []},
                "meta": {"status": "streaming"},
            },
        },
        {
            "kind": "doc_update",
            "project": "demo",
            "data": {
                "doc_type": "manuscript",
                "doc_id": "stage2-manuscript",
                "op": "append_text",
                "value": "첫 문장입니다.\n",
                "meta": {"chapter": 1},
            },
        },
    ]

    snapshot = reduce_doc_events(events, doc_type="manuscript")
    assert snapshot["doc_type"] == "manuscript"
    assert snapshot["content"]["raw_text"] == "첫 문장입니다.\n"
    assert snapshot["status"] == "streaming"
