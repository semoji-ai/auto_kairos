"""_watchlist.md 마크다운 파싱 + 수정."""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


SECTIONS = ["active", "trial", "proposed_remove", "archived"]
SECTION_HEADERS = {
    "## Active": "active",
    "## Trial": "trial",
    "## Proposed Remove": "proposed_remove",
    "## Archived": "archived",
}

# 각 섹션의 테이블 컬럼 정의 (name, channel_id는 공통 앞 2개)
SECTION_COLUMNS = {
    "active": ["name", "channel_id", "category", "added", "relevance"],
    "trial": ["name", "channel_id", "added", "reason", "relevance"],
    "proposed_remove": ["name", "channel_id", "proposed_date", "reason"],
    "archived": ["name", "channel_id", "removed_date", "reason"],
}


class WatchlistParser:
    """_watchlist.md 파싱 및 수정."""

    def __init__(self, vault_dir: Path):
        self._vault_dir = vault_dir
        self._path = vault_dir / "channels" / "_watchlist.md"
        self._frontmatter: Dict[str, str] = {}

    def parse(self) -> Dict[str, List[Dict]]:
        """워치리스트 파싱. 섹션별 채널 목록 반환."""
        result = {s: [] for s in SECTIONS}
        if not self._path.exists():
            return result

        content = self._path.read_text(encoding="utf-8")
        self._parse_frontmatter(content)
        current_section = None
        column_keys: List[str] = []

        for line in content.split("\n"):
            stripped = line.strip()

            # 섹션 헤더 감지
            for header, section in SECTION_HEADERS.items():
                if stripped.startswith(header):
                    current_section = section
                    column_keys = SECTION_COLUMNS.get(section, [])
                    break

            if not current_section or not stripped.startswith("|"):
                continue

            # 구분선 스킵
            if re.match(r"^\|[-\s|]+\|$", stripped):
                continue

            cells = [c.strip() for c in stripped.split("|")[1:-1]]

            # 헤더 행 스킵
            if len(cells) >= 1 and cells[0] == "채널":
                continue

            if len(cells) >= 2:
                entry: Dict[str, str] = {}
                for i, key in enumerate(column_keys):
                    entry[key] = cells[i] if i < len(cells) else ""
                result[current_section].append(entry)

        return result

    def _parse_frontmatter(self, content: str):
        """frontmatter (---...---) 파싱해서 보존."""
        self._frontmatter = {}
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            for line in match.group(1).split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    self._frontmatter[key.strip()] = val.strip()

    def get_trackable(self) -> List[Dict]:
        """수집 대상 채널 (active + trial) 반환."""
        data = self.parse()
        channels = []
        for status in ["active", "trial"]:
            for ch in data[status]:
                channels.append({**ch, "status": status})
        return channels

    def approve(self, channel_name: str):
        """trial → active 승격."""
        data = self.parse()
        target = None
        for ch in data["trial"]:
            if ch["name"] == channel_name:
                target = ch
                break
        if not target:
            raise ValueError(f"Trial 채널을 찾을 수 없습니다: {channel_name}")

        data["trial"] = [ch for ch in data["trial"] if ch["name"] != channel_name]
        # trial → active 변환: 컬럼 매핑
        active_entry = {
            "name": target["name"],
            "channel_id": target["channel_id"],
            "category": "",
            "added": target.get("added", ""),
            "relevance": target.get("relevance", ""),
        }
        data["active"].append(active_entry)
        self._write(data)

    def remove(self, channel_name: str):
        """proposed_remove → archived 이동."""
        data = self.parse()
        target = None
        for ch in data["proposed_remove"]:
            if ch["name"] == channel_name:
                target = ch
                break
        if not target:
            raise ValueError(f"제거 대상 채널을 찾을 수 없습니다: {channel_name}")

        data["proposed_remove"] = [
            ch for ch in data["proposed_remove"] if ch["name"] != channel_name
        ]
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        archived_entry = {
            "name": target["name"],
            "channel_id": target["channel_id"],
            "removed_date": today,
            "reason": target.get("reason", ""),
        }
        data["archived"].append(archived_entry)
        self._write(data)

    def _write(self, data: Dict[str, List[Dict]]):
        """파싱된 데이터를 _watchlist.md로 재작성. 기존 frontmatter 보존."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # frontmatter 보존 — 기존 값 유지, last_review만 갱신
        fm = dict(self._frontmatter)
        fm["last_review"] = today
        fm_lines = ["---"]
        for k, v in fm.items():
            fm_lines.append(f"{k}: {v}")
        fm_lines.append("---")

        lines = fm_lines + [""]

        # 각 섹션 출력
        for section in SECTIONS:
            header_name = {
                "active": "Active",
                "trial": "Trial",
                "proposed_remove": "Proposed Remove",
                "archived": "Archived",
            }[section]
            cols = SECTION_COLUMNS[section]
            col_headers = {
                "name": "채널",
                "channel_id": "채널ID",
                "category": "카테고리",
                "added": "추가일",
                "relevance": "관련도",
                "reason": "추가 사유" if section == "trial" else "사유",
                "proposed_date": "제안일",
                "removed_date": "제거일",
            }

            lines.append(f"## {header_name}")
            header_row = "| " + " | ".join(col_headers.get(c, c) for c in cols) + " |"
            sep_row = "|" + "|".join("------" for _ in cols) + "|"
            lines.append(header_row)
            lines.append(sep_row)

            for ch in data.get(section, []):
                row = "| " + " | ".join(ch.get(c, "") for c in cols) + " |"
                lines.append(row)
            lines.append("")

        self._path.write_text("\n".join(lines), encoding="utf-8")
