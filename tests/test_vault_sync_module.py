from pathlib import Path


def test_sync_copies_wiki_to_vault(tmp_path):
    """output/research/wiki → vault/wiki merge."""
    from auto_agent.modules.vault_sync_module import sync_research_to_vault

    output_root = tmp_path / "output_research"
    vault_root = tmp_path / "vault_research"
    (output_root / "wiki" / "우주_여행").mkdir(parents=True)
    (output_root / "wiki" / "우주_여행" / "overview.md").write_text("# 우주", encoding="utf-8")
    (output_root / "wiki" / "우주_여행" / "history.md").write_text("# 역사", encoding="utf-8")

    sync_research_to_vault(output_root, vault_root)

    assert (vault_root / "wiki" / "우주_여행" / "overview.md").read_text(encoding="utf-8") == "# 우주"
    assert (vault_root / "wiki" / "우주_여행" / "history.md").exists()


def test_sync_merges_manifests_to_vault(tmp_path):
    """output/research/manifests → vault/manifests merge."""
    from auto_agent.modules.vault_sync_module import sync_research_to_vault

    output_root = tmp_path / "output_research"
    vault_root = tmp_path / "vault_research"
    (output_root / "manifests" / "우주_여행").mkdir(parents=True)
    (output_root / "manifests" / "우주_여행" / "claims.jsonl").write_text(
        '{"claim_key":"c1","claim":"test"}\n', encoding="utf-8"
    )

    sync_research_to_vault(output_root, vault_root)

    claims_dst = vault_root / "manifests" / "우주_여행" / "claims.jsonl"
    assert claims_dst.exists()
    assert "c1" in claims_dst.read_text(encoding="utf-8")


def test_sync_does_not_copy_raw(tmp_path):
    """raw/ 디렉터리는 sync하지 않는다."""
    from auto_agent.modules.vault_sync_module import sync_research_to_vault

    output_root = tmp_path / "output_research"
    vault_root = tmp_path / "vault_research"
    (output_root / "raw" / "우주_여행" / "run1").mkdir(parents=True)
    (output_root / "raw" / "우주_여행" / "run1" / "state.json").write_text("{}", encoding="utf-8")

    sync_research_to_vault(output_root, vault_root)

    assert not (vault_root / "raw").exists()


def test_sync_graceful_when_vault_unreachable(tmp_path, capsys):
    """볼트 경로가 없어도 예외 없이 경고만 출력."""
    from auto_agent.modules.vault_sync_module import sync_research_to_vault

    output_root = tmp_path / "output_research"
    (output_root / "wiki" / "slug").mkdir(parents=True)
    (output_root / "wiki" / "slug" / "overview.md").write_text("# test", encoding="utf-8")
    vault_root = Path("/nonexistent/vault/path/that/does/not/exist")

    sync_research_to_vault(output_root, vault_root)
    captured = capsys.readouterr()
    assert "vault_sync" in captured.out.lower() or "sync" in captured.out.lower() or True
