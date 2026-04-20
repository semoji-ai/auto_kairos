import json
from pathlib import Path


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_entity_hub_audit_detects_duplicate_topic_slugs(tmp_path):
    from auto_agent.modules.research_entity_hub import build_entity_hub_audit

    research_root = tmp_path / "02-research"
    _write(
        research_root / "wiki" / "바세린" / "overview.md",
        '---\ntopic: "바세린의_역사"\n---\n# 바세린의 역사 — Overview\n',
    )
    _write(research_root / "wiki" / "바세린" / "역사.md", "# 바세린 역사\n")
    _write(research_root / "manifests" / "바세린" / "claims.jsonl", "{}\n")

    _write(
        research_root / "wiki" / "바세린의_역사" / "overview.md",
        '---\ntopic: "바세린의_역사"\n---\n# 바세린의 역사 — Overview\n',
    )
    _write(research_root / "manifests" / "바세린의_역사" / "claims.jsonl", "{}\n")
    _write(
        research_root / "wiki" / "바세린-석유젤리-의-역사와-화학적-원리" / "overview.md",
        '---\ntopic: "바세린(석유젤리)의 역사와 화학적 원리"\n---\n# 바세린(석유젤리)의 역사와 화학적 원리 Overview\n',
    )
    _write(research_root / "manifests" / "바세린-석유젤리-의-역사와-화학적-원리" / "claims.jsonl", "{}\n")

    audit = build_entity_hub_audit(research_root)

    assert len(audit["duplicate_groups"]) == 1
    group = audit["duplicate_groups"][0]
    assert group["entity_slug"] == "바세린"
    assert group["canonical_slug"] == "바세린"
    assert "바세린의_역사" in audit["alias_map"]
    assert audit["alias_map"]["바세린의_역사"]["entity_slug"] == "바세린"
    assert audit["alias_map"]["바세린의_역사"]["section_slug"] == "역사"
    assert "바세린-석유젤리-의-역사와-화학적-원리" in audit["alias_map"]
    assert audit["alias_map"]["바세린-석유젤리-의-역사와-화학적-원리"]["entity_slug"] == "바세린"


def test_resolve_existing_entity_slug_prefers_alias_map(tmp_path):
    from auto_agent.modules.research_entity_hub import resolve_existing_entity_slug

    research_root = tmp_path / "02-research"
    _write(research_root / "wiki" / "바세린" / "overview.md", "# 바세린\n")
    _write(research_root / "wiki" / "바세린의_역사" / "overview.md", "# 바세린의 역사\n")
    _write(
        research_root / "manifests" / "_entity_hub" / "entity_aliases.json",
        json.dumps(
            {
                "바세린의_역사": {
                    "entity_slug": "바세린",
                    "section_slug": "역사",
                    "source_slug": "바세린의_역사",
                    "canonical_slug": "바세린",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    resolved = resolve_existing_entity_slug(research_root, "바세린의_역사")
    assert resolved == "바세린"


def test_write_entity_hub_audit_outputs_manifest_files(tmp_path):
    from auto_agent.modules.research_entity_hub import write_entity_hub_audit

    research_root = tmp_path / "02-research"
    _write(
        research_root / "wiki" / "바세린" / "overview.md",
        '---\ntopic: "바세린의_역사"\n---\n# 바세린의 역사 — Overview\n',
    )
    _write(research_root / "manifests" / "바세린" / "claims.jsonl", "{}\n")

    outputs = write_entity_hub_audit(research_root)
    assert outputs["audit_json"].exists()
    assert outputs["alias_json"].exists()
    assert outputs["report_md"].exists()


def test_migrate_entity_hubs_merges_alias_into_canonical(tmp_path):
    from auto_agent.modules.research_entity_hub import migrate_entity_hubs

    research_root = tmp_path / "02-research"
    _write(
        research_root / "wiki" / "바세린" / "overview.md",
        "# 바세린 overview\n",
    )
    _write(
        research_root / "wiki" / "바세린의_역사" / "overview.md",
        "# 바세린의 역사\n더 긴 내용\n",
    )
    _write(research_root / "manifests" / "바세린" / "claims.jsonl", '{"id":"a"}\n')
    _write(research_root / "manifests" / "바세린의_역사" / "claims.jsonl", '{"id":"b"}\n')
    _write(research_root / "raw" / "바세린의_역사" / "run1" / "note.md", "note\n")
    _write(
        research_root / "manifests" / "_entity_hub" / "entity_aliases.json",
        json.dumps(
            {
                "바세린의_역사": {
                    "entity_slug": "바세린",
                    "section_slug": "역사",
                    "source_slug": "바세린의_역사",
                    "canonical_slug": "바세린",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    outputs = migrate_entity_hubs(research_root)

    assert (research_root / "wiki" / "바세린" / "역사.md").exists()
    merged_claims = (research_root / "manifests" / "바세린" / "claims.jsonl").read_text(encoding="utf-8")
    assert '{"id":"a"}' in merged_claims
    assert '{"id":"b"}' in merged_claims
    assert not (research_root / "wiki" / "바세린의_역사").exists()
    assert (outputs["backup_root"] / "wiki" / "바세린의_역사").exists()


def test_build_entity_hub_audit_prefers_clean_entity_slug_for_test_duplicates(tmp_path):
    from auto_agent.modules.research_entity_hub import build_entity_hub_audit

    research_root = tmp_path / "02-research"
    _write(research_root / "raw" / "배의역사_test_v2" / "run1" / "note.md", "v2\n")
    _write(research_root / "raw" / "배의역사_test_v3" / "run2" / "note.md", "v3\n")
    _write(research_root / "raw" / "배의역사_test_v4" / "run3" / "note.md", "v4\n")

    audit = build_entity_hub_audit(research_root)

    group = next(g for g in audit["duplicate_groups"] if g["entity_slug"] == "배")
    assert group["canonical_slug"] == "배"
    assert audit["alias_map"]["배의역사_test_v2"]["canonical_slug"] == "배"
    assert audit["alias_map"]["배의역사_test_v3"]["canonical_slug"] == "배"
    assert audit["alias_map"]["배의역사_test_v4"]["canonical_slug"] == "배"


def test_migrate_entity_hubs_can_merge_test_like_raw_duplicates(tmp_path):
    from auto_agent.modules.research_entity_hub import migrate_entity_hubs

    research_root = tmp_path / "02-research"
    _write(research_root / "raw" / "배의역사_test_v2" / "20260407_150234" / "run_summary.md", "v2\n")
    _write(research_root / "raw" / "배의역사_test_v3" / "20260407_161637" / "run_summary.md", "v3\n")

    outputs = migrate_entity_hubs(research_root, include_test_like=True)

    assert (research_root / "raw" / "배" / "20260407_150234" / "run_summary.md").exists()
    assert (research_root / "raw" / "배" / "20260407_161637" / "run_summary.md").exists()
    assert not (research_root / "raw" / "배의역사_test_v2").exists()
    assert not (research_root / "raw" / "배의역사_test_v3").exists()
    assert (outputs["backup_root"] / "raw" / "배의역사_test_v2").exists()
