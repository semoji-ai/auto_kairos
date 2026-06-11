import json

import pytest

from auto_agent.modules.skeleton_from_vault_module import build_skeleton_and_outline


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_build_skeleton_and_outline_from_vault(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    research_root = tmp_path / "vault" / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"

    _write(
        wiki_dir / "overview.md",
        """---
doc_type: wiki-page
---
# 바세린 — Overview

## Summary
- 바세린은 19세기 석유 젤리 브랜드다.
- 로드왁스 발견과 극적 시연 마케팅이 성장의 핵심이었다.
""",
    )
    _write(
        wiki_dir / "timeline.md",
        """# Timeline
- **1859** — 타이터스빌에서 로드왁스 발견. 산업 전환의 출발점.
- **1870** — 브루클린 공장에서 바세린 출시. 브랜드 탄생의 순간.
- **1875** — Chesebrough Manufacturing Company 설립. 대량 생산 체제 확립.
""",
    )
    _write(
        wiki_dir / "entities.md",
        """# Entities
## 인물
### Robert Augustus Chesebrough (1837–1933)
- **역할**: 발명가이자 창업자
- **경력 요약**: 로드왁스를 정제해 바세린 브랜드를 만들었다.
""",
    )
    _write(
        manifest_dir / "claims.jsonl",
        "\n".join(
            [
                json.dumps(
                    {
                        "claim_id": "c1",
                        "claim": "1859년 로드왁스가 발견되었다.",
                        "kind": "historical",
                        "evidence": "근거1",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "claim_id": "c2",
                        "claim": "1870년 바세린 브랜드가 출시되었다.",
                        "kind": "marketing-history",
                        "evidence": "근거2",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
    )
    _write(
        manifest_dir / "sources.jsonl",
        json.dumps({"id": "s1", "title": "Wikipedia: Vaseline", "url": "https://example.com", "quality_grade": "high"}, ensure_ascii=False),
    )

    (project_dir / "source_ingest_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "topic": "바세린의 역사",
                "topic_slug": "바세린의_역사",
                "entity_slug": "바세린",
                "section_slug": "역사",
                "research_root": str(research_root),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "editorial_brief.json").write_text(
        json.dumps(
            {
                "real_topic": "바세린의 역사",
                "core_question": "왜 바세린은 오래 살아남았는가?",
                "entity_slug": "바세린",
                "section_slug": "역사",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "project_config.json").write_text(
        json.dumps({"topic": "바세린의 역사", "duration_minutes": 5}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "vault"))

    # outline 생성은 research-strategist 에이전트로 이관됨 — 이 함수는 skeleton만 반환
    skeleton = build_skeleton_and_outline(project_dir)

    assert skeleton["entity_slug"] == "바세린"
    assert len(skeleton["timeline"]) >= 3
    assert skeleton["key_figures"][0]["name"] == "Robert Augustus Chesebrough"
    assert skeleton["source_mode"] == "vault"


def test_build_skeleton_without_vault_falls_back_to_research_first(tmp_path, monkeypatch):
    """legacy ingest 완료 요구는 제거됨 — 볼트 자료 없이도 skeleton 폴백 생성."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "source_ingest_status.json").write_text(
        json.dumps({"status": "collecting"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (project_dir / "project_config.json").write_text(
        json.dumps({"topic": "바세린의 역사"}, ensure_ascii=False),
        encoding="utf-8",
    )
    # env를 지우면 repo .env의 실제 NAS 볼트로 폴백하므로, 빈 tmp 볼트를 명시
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(tmp_path / "empty_vault"))
    # 볼트 부재 시 lane 라이브 리서치 폴백이 돌므로 네트워크 차단을 위해 mock
    monkeypatch.setattr(
        "auto_agent.modules.skeleton_from_vault_module._build_seed_research",
        lambda **kwargs: ([], [], [], []),
    )

    skeleton = build_skeleton_and_outline(project_dir)

    assert skeleton["topic"] == "바세린의 역사"
    assert skeleton["source_mode"] == "skeleton_research_first"
    # 자료가 없으면 brief 기반 뼈대 리서치 프레임으로 timeline을 채움
    assert skeleton["timeline"]
    assert all(item["year"] == "" for item in skeleton["timeline"])
