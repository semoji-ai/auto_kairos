import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_collect_name_mismatch_adjustments_detects_near_miss_korean_name():
    from auto_agent.orchestrator.runner import _collect_name_mismatch_adjustments

    scene_specs = {
        "scenes": [
            {
                "sceneNumber": 11,
                "narration": "타지리 사토시 옆에는 스가모리 켄이 합류해 첫 비주얼 감각을 더했다.",
                "characters": [
                    {"name": "타지리 사토시", "canonical_name": "타지리 사토시"},
                    {"name": "스기모리 켄", "canonical_name": "스기모리 켄", "aliases": ["Sugimori Ken"]},
                ],
            }
        ]
    }

    adjustments = _collect_name_mismatch_adjustments(scene_specs)

    assert len(adjustments) == 1
    item = adjustments[0]
    assert item["scene"] == 11
    assert item["status"] == "adjusted"
    assert item["original_text"] == "스가모리 켄"
    assert item["corrected_text"] == "스기모리 켄"
    assert item["type"] == "proper_noun"


def test_merge_name_mismatch_adjustments_updates_factcheck_report_summary():
    from auto_agent.orchestrator.runner import _merge_name_mismatch_adjustments_into_report

    report = {
        "claims": [],
        "total_claims": 0,
        "adjusted": 0,
        "failed": 0,
        "summary": {"recommendations": []},
    }
    scene_specs = {
        "scenes": [
            {
                "sceneNumber": 4,
                "narration": "스가모리 켄은 팀의 시각적 인상을 만들었다.",
                "characters": [
                    {"name": "스기모리 켄", "canonical_name": "스기모리 켄"}
                ],
            }
        ]
    }

    merged = _merge_name_mismatch_adjustments_into_report(report, scene_specs)

    assert merged["total_claims"] == 1
    assert merged["adjusted"] == 1
    assert merged["failed"] == 1
    assert merged["claims"][0]["corrected_text"] == "스기모리 켄"
    assert any("스가모리 켄" in rec and "스기모리 켄" in rec for rec in merged["summary"]["recommendations"])
