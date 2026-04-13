from pathlib import Path

import pytest

from auto_agent.modules.source_ingest_module import (
    _build_outline_requirements,
    _resolve_research_agent_paths,
    _seed_from_vault,
    _validate_ingest_completion,
)


def _make_agent_dir(base: Path) -> Path:
    scripts = base / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "research_launcher.py").write_text("# launcher\n", encoding="utf-8")
    (scripts / "research_vault.py").write_text("# vault\n", encoding="utf-8")
    return base


def test_resolve_research_agent_paths_accepts_capitalized_dir(tmp_path):
    capitalized = _make_agent_dir(tmp_path / "ResearchAgent")
    _, launcher, vault_script = _resolve_research_agent_paths(candidate_dirs=[capitalized, tmp_path / "researchagent"])
    assert launcher == (capitalized / "scripts" / "research_launcher.py").resolve()
    assert vault_script == (capitalized / "scripts" / "research_vault.py").resolve()


def test_resolve_research_agent_paths_accepts_lowercase_dir(tmp_path):
    lowercase = _make_agent_dir(tmp_path / "researchagent")
    research_agent_dir, launcher, vault_script = _resolve_research_agent_paths(candidate_dirs=[tmp_path / "missing-research-agent", lowercase])
    assert research_agent_dir == lowercase.resolve()
    assert launcher == (lowercase / "scripts" / "research_launcher.py").resolve()
    assert vault_script == (lowercase / "scripts" / "research_vault.py").resolve()


def test_resolve_research_agent_paths_reports_checked_candidates(tmp_path):
    with pytest.raises(FileNotFoundError) as excinfo:
        _resolve_research_agent_paths(candidate_dirs=[tmp_path / "ResearchAgent", tmp_path / "researchagent"])
    message = str(excinfo.value)
    assert "ResearchAgent launcher를 찾지 못했습니다" in message
    assert str(tmp_path / "ResearchAgent" / "scripts" / "research_launcher.py") in message
    assert str(tmp_path / "researchagent" / "scripts" / "research_launcher.py") in message


def test_seed_from_vault_copies_wiki_and_manifests(tmp_path):
    """볼트에 wiki/manifests가 있으면 output/research로 복사한다."""
    vault_root = tmp_path / "vault_research"
    output_root = tmp_path / "output_research"
    (vault_root / "wiki" / "우주_여행").mkdir(parents=True)
    (vault_root / "wiki" / "우주_여행" / "overview.md").write_text("# 우주 여행", encoding="utf-8")
    (vault_root / "manifests" / "우주_여행").mkdir(parents=True)
    (vault_root / "manifests" / "우주_여행" / "claims.jsonl").write_text('{"claim":"test"}\n', encoding="utf-8")

    _seed_from_vault(output_root, vault_root, ["우주_여행"])

    assert (output_root / "wiki" / "우주_여행" / "overview.md").exists()
    assert (output_root / "manifests" / "우주_여행" / "claims.jsonl").exists()


def test_seed_from_vault_graceful_when_vault_missing(tmp_path):
    """볼트가 없거나 slug가 없으면 경고만 출력하고 계속 진행한다."""
    vault_root = tmp_path / "nonexistent_vault"
    output_root = tmp_path / "output_research"

    _seed_from_vault(output_root, vault_root, ["없는_slug"])
    assert True


def test_seed_from_vault_skips_raw_directory(tmp_path):
    """볼트 raw/ 폴더는 복사하지 않는다."""
    vault_root = tmp_path / "vault_research"
    (vault_root / "raw" / "우주_여행").mkdir(parents=True)
    (vault_root / "raw" / "우주_여행" / "run1").mkdir()
    output_root = tmp_path / "output_research"

    _seed_from_vault(output_root, vault_root, ["우주_여행"])

    assert not (output_root / "raw").exists()


def test_validate_ingest_completion_fails_when_claims_missing(tmp_path):
    research_root = tmp_path / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"
    wiki_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# overview\n" + ("x" * 600), encoding="utf-8")
    (wiki_dir / "timeline.md").write_text("# timeline\n", encoding="utf-8")
    (wiki_dir / "entities.md").write_text("# entities\n", encoding="utf-8")
    (wiki_dir / "claims.md").write_text("# claims\n", encoding="utf-8")
    (manifest_dir / "claims.jsonl").write_text("", encoding="utf-8")

    result = _validate_ingest_completion(
        research_root=research_root,
        topic_slug="바세린의_역사",
        entity_slug="바세린",
        section_slug="역사",
        finalize_payload={
            "run_state": {"stage": "quality-assurance", "status": "blocked"},
            "snapshot": {"specialist_readiness": "seed_only"},
            "status": {"recommended_next_step": "strengthen-claim-set"},
        },
    )

    assert result["success"] is False
    assert result["claim_count"] == 0
    assert any("claim_count=0 < 4" in issue for issue in result["issues"])
    assert any("finalize-session not completed" in issue for issue in result["issues"])


def test_build_outline_requirements_generates_chapter_slots():
    outline = {
        "chapters": [
            {
                "chapter_number": 1,
                "title": "1972년 창업",
                "purpose": "사업의 출발점 설명",
                "time_period": "1972",
                "research_focus": ["창업 배경은 무엇인가?"],
            }
        ]
    }

    requirements = _build_outline_requirements(outline)

    assert len(requirements) == 1
    prompts = requirements[0]["research_focus"]
    assert any("전환점" in prompt for prompt in prompts)
    assert any("날짜" in prompt or "수치" in prompt for prompt in prompts)
    assert any("인물" in prompt or "기관" in prompt for prompt in prompts)
    assert any("왜 중요" in prompt or "어떻게" in prompt for prompt in prompts)


def test_validate_ingest_completion_requires_chapter_coverage(tmp_path):
    research_root = tmp_path / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"
    wiki_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# overview\n" + ("x" * 600), encoding="utf-8")
    (wiki_dir / "timeline.md").write_text("# timeline\n" + ("x" * 300), encoding="utf-8")
    (wiki_dir / "entities.md").write_text("# entities\n창업자\n대표이사\n" + ("x" * 120), encoding="utf-8")
    (wiki_dir / "claims.md").write_text("# claims\n" + ("x" * 300), encoding="utf-8")
    (manifest_dir / "claims.jsonl").write_text(
        "\n".join(
            [
                '{"claim_id":"c1","claim":"1972년 창업이 출발점이었다","evidence":"1972년 창업","source_ids":["s1"]}',
                '{"claim_id":"c2","claim":"창업자는 야노 히로타케였다","evidence":"창업자 야노 히로타케","source_ids":["s1"]}',
                '{"claim_id":"c3","claim":"초기 전략은 생활용품 판매였다","evidence":"사업 전략","source_ids":["s2"]}',
                '{"claim_id":"c4","claim":"1987년 상설점 전환이 있었다","evidence":"1987년 전환","source_ids":["s2"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (manifest_dir / "sources.jsonl").write_text(
        '{"source_id":"s1","title":"공식 연혁","summary":"1972 창업과 창업자 설명"}\n'
        '{"source_id":"s2","title":"보조 자료","summary":"1987 전환 설명"}\n',
        encoding="utf-8",
    )
    outline_requirements = _build_outline_requirements(
        {
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "1972년 창업",
                    "purpose": "출발점 설명",
                    "research_focus": ["창업 배경과 전략은 무엇인가?"],
                },
                {
                    "chapter_number": 2,
                    "title": "2001년 해외 확장",
                    "purpose": "대만 진출과 해외 확장 설명",
                    "research_focus": ["해외 확장은 어떻게 이뤄졌는가?"],
                },
            ]
        }
    )

    result = _validate_ingest_completion(
        research_root=research_root,
        topic_slug="바세린의_역사",
        entity_slug="바세린",
        section_slug="역사",
        finalize_payload={
            "run_state": {"stage": "packaging", "status": "completed"},
            "snapshot": {"specialist_readiness": "usable"},
            "status": {"recommended_next_step": "complete"},
        },
        outline_requirements=outline_requirements,
    )

    assert result["success"] is False
    assert result["draft_ready"] is False
    assert any("chapter coverage not draft-ready" in issue for issue in result["issues"])
    assert result["chapter_readiness"][1]["draft_ready"] is False


def test_validate_ingest_completion_succeeds_with_packaged_run(tmp_path):
    research_root = tmp_path / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"
    wiki_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# 역사\n" + ("x" * 600), encoding="utf-8")
    (wiki_dir / "timeline.md").write_text("# timeline\n1972 창업\n1977 법인화\n1987 상설점 전환\n" + ("x" * 180), encoding="utf-8")
    (wiki_dir / "entities.md").write_text("# entities\n야노 히로타케\n다이소산업\n" + ("x" * 180), encoding="utf-8")
    (wiki_dir / "claims.md").write_text("# claims\n" + ("x" * 400), encoding="utf-8")
    (manifest_dir / "claims.jsonl").write_text(
        "\n".join(
            [
                '{"claim_id":"c1","claim":"1972년 창업이 출발점이었다","evidence":"1972년 창업과 배경","source_ids":["s1"]}',
                '{"claim_id":"c2","claim":"창업자는 야노 히로타케였다","evidence":"핵심 인물 설명","source_ids":["s1"]}',
                '{"claim_id":"c3","claim":"초기 전략은 생활용품 판매였다","evidence":"사업 전략과 의미","source_ids":["s2"]}',
                '{"claim_id":"c4","claim":"1987년 상설점 전환이 있었다","evidence":"1987년 전환점","source_ids":["s2"]}',
                '{"claim_id":"c5","claim":"2001년 해외 확장이 본격화됐다","evidence":"2001년 대만 진출과 확장","source_ids":["s3"]}',
                '{"claim_id":"c6","claim":"해외 확장은 브랜드 전략 변화였다","evidence":"왜 중요했는지 설명","source_ids":["s3"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (manifest_dir / "sources.jsonl").write_text(
        '{"source_id":"s1","title":"공식 연혁","summary":"1972 창업, 창업자, 배경"}\n'
        '{"source_id":"s2","title":"전환 자료","summary":"1987 상설점 전환과 전략"}\n'
        '{"source_id":"s3","title":"해외 확장 자료","summary":"2001 해외 확장과 의미"}\n',
        encoding="utf-8",
    )
    outline_requirements = _build_outline_requirements(
        {
            "chapters": [
                {
                    "chapter_number": 1,
                    "title": "1972년 창업",
                    "purpose": "출발점 설명",
                    "research_focus": ["창업 배경과 전략은 무엇인가?"],
                },
                {
                    "chapter_number": 2,
                    "title": "2001년 해외 확장",
                    "purpose": "대만 진출과 해외 확장 설명",
                    "research_focus": ["해외 확장은 어떻게 이뤄졌는가?"],
                },
            ]
        }
    )

    result = _validate_ingest_completion(
        research_root=research_root,
        topic_slug="바세린의_역사",
        entity_slug="바세린",
        section_slug="역사",
        finalize_payload={
            "run_state": {"stage": "packaging", "status": "completed"},
            "snapshot": {"specialist_readiness": "usable"},
            "status": {"recommended_next_step": "complete"},
        },
        outline_requirements=outline_requirements,
    )

    assert result["success"] is True
    assert result["claim_count"] == 6
    assert result["source_count"] == 3
    assert result["draft_ready"] is True
    assert result["must_answer_coverage"] >= 0.6
