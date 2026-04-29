"""vault_sync + vault_sync_queue 단위 테스트."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from auto_agent.research.vault_sync import (
    SyncOptions,
    _dedup_claims_append,
    _fallback_slug,
    _parse_normalizer_response,
    normalize_to_entity_slug,
    sync_project_to_vault,
    sync_topic,
)
from auto_agent.research import vault_sync_queue as q
from auto_agent.research.vault_sync_queue import (
    VaultSyncLock,
    dispose,
    enqueue,
    list_queue,
    mark_stale,
    pop_next,
)


# ─────────────────────────────────────────────
# Slug 정규화 — 파싱
# ─────────────────────────────────────────────

def test_parse_normalizer_response_valid():
    raw = '{"entity_slug": "유한양행", "match_type": "exact", "confidence": 0.95, "rationale": "정확 일치"}'
    out = _parse_normalizer_response(raw)
    assert out["entity_slug"] == "유한양행"
    assert out["match_type"] == "exact"
    assert out["confidence"] == 0.95


def test_parse_normalizer_response_clamps_long_slug():
    raw = json.dumps({"entity_slug": "x" * 100, "match_type": "new", "confidence": 0.9})
    out = _parse_normalizer_response(raw)
    assert len(out["entity_slug"]) == 50


def test_parse_normalizer_response_no_json():
    with pytest.raises(ValueError):
        _parse_normalizer_response("no json")


def test_parse_normalizer_response_missing_slug():
    with pytest.raises(ValueError):
        _parse_normalizer_response('{"match_type": "exact"}')


# ─────────────────────────────────────────────
# normalize_to_entity_slug 통합
# ─────────────────────────────────────────────

def test_normalize_with_mock_invoker():
    def mock(prompt: str) -> str:
        assert "project_slug" in prompt
        return json.dumps({"entity_slug": "유한양행", "match_type": "exact", "confidence": 0.98})

    out = normalize_to_entity_slug("유한양행_100주년_1부터", ["유한양행", "유일한"], invoker=mock)
    assert out["entity_slug"] == "유한양행"
    assert out["confidence"] == 0.98


def test_normalize_falls_back_on_invoker_error():
    def boom(prompt: str) -> str:
        raise RuntimeError("CLI not found")

    out = normalize_to_entity_slug("유한양행_100주년_test", ["유한양행"], invoker=boom)
    assert out["match_type"] == "fallback"
    assert out["confidence"] == 0.5
    assert out["entity_slug"]  # 슬러그 첫 토큰


def test_fallback_slug_extracts_first_token():
    assert _fallback_slug("유한양행_100주년_1부터") == "유한양행"
    assert _fallback_slug("pepsi_history") == "pepsi"
    assert _fallback_slug("") == "unknown"


# ─────────────────────────────────────────────
# Claims dedup-append
# ─────────────────────────────────────────────

def test_dedup_claims_append_writes_new_only(tmp_path: Path):
    vault_path = tmp_path / "claims.jsonl"
    # vault에 이미 있는 claim
    vault_path.write_text(
        json.dumps({"claim_id": "c1", "claim": "기존"}) + "\n",
        encoding="utf-8",
    )
    project_claims = [
        {"claim_id": "c1", "claim": "중복"},  # 중복
        {"claim_id": "c2", "claim": "신규"},
        {"claim_id": "c3", "claim": "또 신규"},
    ]
    appended, skipped = _dedup_claims_append(project_claims, vault_path)
    assert appended == 2
    assert skipped == 1
    # 결과 확인
    lines = vault_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3  # 기존 1 + 신규 2


def test_dedup_claims_append_empty_input(tmp_path: Path):
    vault_path = tmp_path / "claims.jsonl"
    appended, skipped = _dedup_claims_append([], vault_path)
    assert appended == 0
    assert skipped == 0


# ─────────────────────────────────────────────
# sync_topic 통합
# ─────────────────────────────────────────────

def test_sync_topic_dry_run_doesnt_write(tmp_path: Path, monkeypatch):
    # 가짜 vault
    fake_vault = tmp_path / "vault" / "02-research"
    fake_vault.mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))

    # 프로젝트
    proj_research = tmp_path / "proj" / "research"
    (proj_research / "manifests" / "유한양행").mkdir(parents=True)
    (proj_research / "manifests" / "유한양행" / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c1", "claim": "X"}) + "\n",
        encoding="utf-8",
    )
    (proj_research / "wiki" / "유한양행").mkdir(parents=True)
    (proj_research / "wiki" / "유한양행" / "overview.md").write_text("# Overview", encoding="utf-8")

    def mock_norm(prompt: str) -> str:
        return json.dumps({"entity_slug": "유한양행", "match_type": "exact", "confidence": 0.95})

    record = sync_topic(
        proj_research, "유한양행", fake_vault,
        invoker=mock_norm,
        options=SyncOptions(dry_run=True),
    )
    assert record["vault_entity_slug"] == "유한양행"
    assert record["claims_appended"] == 1  # dry-run이지만 카운트는 보고
    # 실제 파일은 안 쓰여야 함
    assert not (fake_vault / "manifests" / "유한양행" / "claims.jsonl").exists()
    assert not (fake_vault / "wiki" / "유한양행" / "overview.md").exists()


def test_sync_topic_real_write(tmp_path: Path, monkeypatch):
    fake_vault = tmp_path / "vault" / "02-research"
    fake_vault.mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))

    proj_research = tmp_path / "proj" / "research"
    (proj_research / "manifests" / "pepsi").mkdir(parents=True)
    (proj_research / "manifests" / "pepsi" / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c1", "claim": "Pepsi est. 1898"}) + "\n",
        encoding="utf-8",
    )
    (proj_research / "wiki" / "pepsi").mkdir(parents=True)
    (proj_research / "wiki" / "pepsi" / "overview.md").write_text("# Overview", encoding="utf-8")

    def mock_norm(prompt: str) -> str:
        return json.dumps({"entity_slug": "pepsi", "match_type": "exact", "confidence": 0.95})

    record = sync_topic(
        proj_research, "pepsi", fake_vault,
        invoker=mock_norm,
        options=SyncOptions(),
    )
    assert record["claims_appended"] == 1
    assert (fake_vault / "manifests" / "pepsi" / "claims.jsonl").exists()
    assert (fake_vault / "wiki" / "pepsi" / "overview.md").exists()


def test_sync_topic_low_confidence_blocked(tmp_path: Path, monkeypatch):
    fake_vault = tmp_path / "vault" / "02-research"
    fake_vault.mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))

    proj_research = tmp_path / "proj" / "research"
    (proj_research / "manifests" / "x").mkdir(parents=True)

    def low_conf(prompt: str) -> str:
        return json.dumps({"entity_slug": "x", "match_type": "fuzzy", "confidence": 0.5})

    record = sync_topic(
        proj_research, "x", fake_vault,
        invoker=low_conf,
        options=SyncOptions(),  # force=False
    )
    assert any("confidence" in str(e.get("reason", "")) for e in record["errors"])


def test_sync_topic_force_overrides_low_confidence(tmp_path: Path, monkeypatch):
    fake_vault = tmp_path / "vault" / "02-research"
    fake_vault.mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))

    proj_research = tmp_path / "proj" / "research"
    (proj_research / "manifests" / "x").mkdir(parents=True)

    def low_conf(prompt: str) -> str:
        return json.dumps({"entity_slug": "x", "match_type": "fuzzy", "confidence": 0.5})

    record = sync_topic(
        proj_research, "x", fake_vault,
        invoker=low_conf,
        options=SyncOptions(force=True),
    )
    assert not record["errors"]  # force는 confidence 무시


# ─────────────────────────────────────────────
# sync_project_to_vault 상위
# ─────────────────────────────────────────────

def test_sync_project_queues_when_vault_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "nonexistent"))
    proj = tmp_path / "abc12345_펩시"
    proj.mkdir()
    result = sync_project_to_vault(proj)
    assert result.queued is True
    assert "vault" in result.queue_reason


def test_sync_project_queue_only_option(tmp_path: Path, monkeypatch):
    fake_vault = tmp_path / "vault" / "02-research"
    fake_vault.mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))
    proj = tmp_path / "abc12345_펩시"
    proj.mkdir()
    result = sync_project_to_vault(proj, options=SyncOptions(queue_only=True))
    assert result.queued is True
    assert "queue_only" in result.queue_reason


# ─────────────────────────────────────────────
# Queue
# ─────────────────────────────────────────────

@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    yield tmp_path


def test_enqueue_creates_file(temp_home: Path):
    fpath = enqueue("펩시의_역사", {"reason": "NAS 단절"})
    assert fpath.exists()
    item = json.loads(fpath.read_text(encoding="utf-8"))
    assert item["project_slug"] == "펩시의_역사"
    assert item["payload"]["reason"] == "NAS 단절"


def test_pop_next_returns_oldest(temp_home: Path):
    enqueue("first")
    time.sleep(1.01)  # timestamp 차이 (초 단위)
    enqueue("second")
    nxt = pop_next()
    assert nxt is not None
    item = json.loads(nxt.read_text(encoding="utf-8"))
    assert item["project_slug"] == "first"


def test_dispose_removes_item(temp_home: Path):
    p = enqueue("test")
    assert p.exists()
    dispose(p)
    assert not p.exists()


def test_pop_next_empty(temp_home: Path):
    assert pop_next() is None


def test_mark_stale_filters_old(temp_home: Path):
    p = enqueue("old_item")
    # mtime을 25시간 전으로 조작
    old = time.time() - 25 * 3600
    os.utime(p, (old, old))

    enqueue("fresh_item")
    marked = mark_stale(max_age_hours=24)
    assert len(marked) == 1
    assert "stale" in str(marked[0])


# ─────────────────────────────────────────────
# Lock
# ─────────────────────────────────────────────

def test_lock_acquires_when_free(temp_home: Path):
    with VaultSyncLock(timeout=1) as locked:
        assert locked


def test_lock_blocks_when_held(temp_home: Path):
    lock1 = VaultSyncLock(timeout=0)
    acquired1 = lock1.__enter__()
    assert acquired1
    try:
        # 두 번째 시도는 즉시 실패
        with VaultSyncLock(timeout=0) as locked:
            assert not locked
    finally:
        lock1.__exit__(None, None, None)


def test_lock_releases_on_exit(temp_home: Path):
    with VaultSyncLock(timeout=0):
        pass
    # 풀렸으니 다음 acquire 성공해야
    with VaultSyncLock(timeout=0) as locked:
        assert locked
