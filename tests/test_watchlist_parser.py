"""watchlist 파서 테스트 — _watchlist.md 마크다운 파싱."""
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser


@pytest.fixture
def watchlist_file(tmp_path):
    vault = tmp_path / "vault"
    (vault / "channels").mkdir(parents=True)
    path = vault / "channels" / "_watchlist.md"
    path.write_text("""---
max_trial: 3
last_review: 2026-03-25
next_review: 2026-04-01
---

## Active
| 채널 | 채널ID | 카테고리 | 추가일 | 관련도 |
|------|--------|---------|--------|--------|
| 슈카월드 | UCsJ6RuBiTVNyF3f6rY5K_g | 경제/시사 | 2026-01-15 | ★★★★★ |
| 지식한입 | UCxyz123 | 교양/지식 | 2026-02-01 | ★★★★☆ |

## Trial
| 채널 | 채널ID | 추가일 | 추가 사유 | 관련도 |
|------|--------|--------|-----------|--------|
| 어쩌다어른 | UCtrial1 | 2026-03-22 | 교양 포맷 유사 | ★★★☆☆ |

## Proposed Remove
| 채널 | 채널ID | 제안일 | 사유 |
|------|--------|--------|------|
| 예시채널 | UCremove1 | 2026-03-25 | 6주간 관련 콘텐츠 없음 |

## Archived
| 채널 | 채널ID | 제거일 | 사유 |
|------|--------|--------|------|
""", encoding="utf-8")
    return vault


class TestParse:
    def test_parse_active(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["active"]) == 2
        assert result["active"][0]["name"] == "슈카월드"
        assert result["active"][0]["channel_id"] == "UCsJ6RuBiTVNyF3f6rY5K_g"

    def test_parse_trial(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["trial"]) == 1
        assert result["trial"][0]["name"] == "어쩌다어른"

    def test_parse_proposed_remove(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        result = parser.parse()
        assert len(result["proposed_remove"]) == 1

    def test_get_trackable(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        trackable = parser.get_trackable()
        assert len(trackable) == 3  # active 2 + trial 1

    def test_empty_watchlist(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "channels").mkdir(parents=True)
        parser = WatchlistParser(vault)
        result = parser.parse()
        assert result == {"active": [], "trial": [], "proposed_remove": [], "archived": []}


class TestModify:
    def test_approve_trial(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        parser.approve("어쩌다어른")
        result = parser.parse()
        assert len(result["active"]) == 3
        assert len(result["trial"]) == 0

    def test_remove_channel(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        parser.remove("예시채널")
        result = parser.parse()
        assert len(result["proposed_remove"]) == 0
        assert len(result["archived"]) == 1

    def test_approve_nonexistent_raises(self, watchlist_file):
        parser = WatchlistParser(watchlist_file)
        with pytest.raises(ValueError):
            parser.approve("존재하지않는채널")
