"""wiki_compile 멱등성 + 프로바이더 검증.

docs/token-waste-audit.md 5번 항목 — 재실행마다 전 토픽을 재합성하고,
모델 미지정으로 사용자 기본 모델(opus/fable)을 상속하던 문제.
"""
import json
import time
from pathlib import Path

import pytest

from auto_agent.research import wiki_compiler as wc


def _seed_topic(research_dir: Path, slug: str) -> None:
    """manifest + raw 발췌를 갖춘 최소 토픽 구성."""
    man = research_dir / "manifests" / slug
    man.mkdir(parents=True, exist_ok=True)
    (man / "sources.jsonl").write_text(
        json.dumps({"source_id": "s1", "title": "t", "source_url": "http://x"}) + "\n",
        encoding="utf-8",
    )
    (man / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c1", "text": "주장"}) + "\n", encoding="utf-8"
    )
    notes = research_dir / "raw" / slug / "run1" / "source_notes"
    notes.mkdir(parents=True, exist_ok=True)
    (notes / "s1.md").write_text("본문 내용입니다.", encoding="utf-8")


@pytest.fixture
def research_dir(tmp_path):
    d = tmp_path / "research"
    d.mkdir()
    _seed_topic(d, "토픽-가")
    return d


def test_first_compile_calls_llm(research_dir):
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return json.dumps({"overview": "개요 본문", "entities": "인물 본문", "timeline": "연표 본문"}, ensure_ascii=False)

    r = wc.compile_topic("토픽-가", research_dir, invoker=fake)
    assert len(calls) == 1
    assert "overview.md" in r["written"]


def test_second_compile_skips_llm(research_dir):
    """이미 합성된 토픽은 LLM을 다시 부르지 않는다 (멱등성)."""
    def fake(prompt):
        return json.dumps({"overview": "개요 본문", "entities": "인물 본문", "timeline": "연표 본문"}, ensure_ascii=False)

    wc.compile_topic("토픽-가", research_dir, invoker=fake)

    calls = []

    def counting(prompt):
        calls.append(prompt)
        return json.dumps({"overview": "X", "entities": "X", "timeline": "X"}, ensure_ascii=False)

    r = wc.compile_topic("토픽-가", research_dir, invoker=counting)
    assert calls == [], "재컴파일 시 LLM 호출이 발생하면 안 됨"
    assert r.get("reused") is True


def test_force_recompiles(research_dir):
    def fake(prompt):
        return json.dumps({"overview": "개요 본문", "entities": "인물 본문", "timeline": "연표 본문"}, ensure_ascii=False)

    wc.compile_topic("토픽-가", research_dir, invoker=fake)

    calls = []

    def counting(prompt):
        calls.append(prompt)
        return json.dumps({"overview": "X", "entities": "X", "timeline": "X"}, ensure_ascii=False)

    wc.compile_topic("토픽-가", research_dir, invoker=counting, force=True)
    assert len(calls) == 1, "force=True면 재합성해야 함"


def test_stale_wiki_recompiles(research_dir):
    """manifest가 wiki보다 새로우면 재합성한다."""
    def fake(prompt):
        return json.dumps({"overview": "개요 본문", "entities": "인물 본문", "timeline": "연표 본문"}, ensure_ascii=False)

    wc.compile_topic("토픽-가", research_dir, invoker=fake)

    time.sleep(0.01)
    (research_dir / "manifests" / "토픽-가" / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c2", "text": "새 주장"}) + "\n", encoding="utf-8"
    )

    calls = []

    def counting(prompt):
        calls.append(prompt)
        return json.dumps({"overview": "X", "entities": "X", "timeline": "X"}, ensure_ascii=False)

    wc.compile_topic("토픽-가", research_dir, invoker=counting)
    assert len(calls) == 1, "manifest 갱신 시 재합성해야 함"


def test_default_invoker_is_not_user_default_model():
    """기본 합성 호출이 사용자 기본 모델을 상속하지 않아야 한다.

    codex 사용 또는 claude CLI에 --model 명시 중 하나여야 한다.
    """
    import inspect

    src = inspect.getsource(wc)
    assert ("codex" in src) or ('"--model"' in src), \
        "모델이 코드에 고정되지 않으면 사용자 기본 모델(opus/fable)을 상속한다"
