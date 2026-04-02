"""캐릭터 라이브러리 — 아트스타일별 캐릭터 이미지 관리 + 프로젝트 간 재활용.

구조:
  $KAIROS_VAULT_DIR/character-library/
  ├── {art_style}/
  │   ├── {이름}({역할},{나이대}).png
  │   └── ...
  └── index.json

사용:
  from auto_agent.modules.character_library import CharacterLibrary
  lib = CharacterLibrary()

  # 검색
  result = lib.find("천주혁", "대표", "30대", art_style="semoji")
  # → {"path": "/vault/character-library/semoji/천주혁(대표,30대).png", "found": True}

  # 등록
  lib.register("천주혁(대표,30대)", "/project/images/characters/천주혁.png", art_style="semoji")
"""
import json
import logging
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Optional

logger = logging.getLogger(__name__)


def _normalize_path(p) -> str:
    """Windows backslash → forward slash (JSON/index 저장용)."""
    return str(p).replace("\\", "/")


class CharacterLibrary:
    """아트스타일별 캐릭터 이미지 라이브러리."""

    def __init__(self, library_dir: Optional[str] = None):
        # 우선순위: 인자 → CHARACTER_LIBRARY_DIR → KAIROS_VAULT_DIR/character-library
        if library_dir:
            self._lib_dir = Path(library_dir)
        elif os.environ.get("CHARACTER_LIBRARY_DIR"):
            self._lib_dir = Path(os.environ["CHARACTER_LIBRARY_DIR"])
        else:
            vault = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
            self._lib_dir = vault / "character-library"
        self._index_path = self._lib_dir / "index.json"
        self._index = self._load_index()

    @property
    def enabled(self) -> bool:
        return self._lib_dir.exists()

    def _load_index(self) -> dict:
        if self._index_path.exists():
            try:
                return json.loads(self._index_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"characters": []}

    def _save_index(self):
        self._lib_dir.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def find(self, name: str, role: str = "", age_group: str = "",
             art_style: str = "") -> Optional[dict]:
        """캐릭터 검색 — 이름 + 아트스타일 매칭.

        Returns:
            {"path": str, "name": str, "role": str, "age_group": str, "art_style": str}
            또는 None
        """
        # 정규화
        name_base = name.split("(")[0].strip()

        for entry in self._index.get("characters", []):
            if entry.get("name_base") != name_base:
                continue
            if art_style and entry.get("art_style") != art_style:
                continue
            if age_group and entry.get("age_group") != age_group:
                continue

            img_path = Path(entry.get("path", ""))
            if img_path.exists():
                logger.info("캐릭터 라이브러리 hit: %s (%s)", name_base, art_style)
                return entry

        # 파일시스템 직접 검색 (인덱스에 없을 수 있음)
        if art_style:
            style_dir = self._lib_dir / art_style
            if style_dir.exists():
                for f in style_dir.glob(f"*{name_base}*"):
                    if f.suffix.lower() in (".png", ".jpg", ".webp"):
                        # 인덱스에 추가
                        entry = self._parse_filename(f, art_style)
                        if entry:
                            self._index["characters"].append(entry)
                            self._save_index()
                            return entry

        return None

    def find_for_scene(self, char_full_name: str, art_style: str) -> Optional[str]:
        """씬의 characters 배열 항목에서 라이브러리 이미지 경로 반환.

        char_full_name: "천주혁(구다이글로벌 대표, 38세)" 형식
        Returns: 이미지 경로 또는 None
        """
        name_base = char_full_name.split("(")[0].strip()

        # 나이대 추출 (38세 → 30대, 45세 → 40대)
        age_match = re.search(r'(\d+)세', char_full_name)
        if age_match:
            age = int(age_match.group(1))
            age_group = f"{(age // 10) * 10}대"
        else:
            age_match = re.search(r'(\d+)대', char_full_name)
            age_group = age_match.group(0) if age_match else ""

        result = self.find(name_base, age_group=age_group, art_style=art_style)
        return result.get("path") if result else None

    def register(self, char_full_name: str, image_path: str,
                 art_style: str, project: str = "") -> str:
        """캐릭터 이미지를 라이브러리에 등록.

        char_full_name: "천주혁(구다이글로벌 대표, 30대)"
        Returns: 라이브러리 내 경로
        """
        name_base = char_full_name.split("(")[0].strip()

        # 나이대 추출
        age_match = re.search(r'(\d+)대', char_full_name)
        age_group = age_match.group(0) if age_match else ""
        if not age_group:
            age_match = re.search(r'(\d+)세', char_full_name)
            if age_match:
                age = int(age_match.group(1))
                age_group = f"{(age // 10) * 10}대"

        # 역할 추출
        role_match = re.search(r'\(([^,)]+)', char_full_name)
        role = role_match.group(1).strip() if role_match else ""

        # 파일명 생성
        filename = f"{name_base}({role},{age_group})" if role and age_group else \
                   f"{name_base}({role})" if role else name_base
        ext = Path(image_path).suffix or ".png"

        style_dir = self._lib_dir / art_style
        style_dir.mkdir(parents=True, exist_ok=True)
        dest = style_dir / f"{filename}{ext}"

        # 복사 (덮어쓰지 않음 — 기존 버전 유지)
        if not dest.exists():
            shutil.copy2(image_path, dest)
            logger.info("캐릭터 라이브러리 등록: %s → %s", char_full_name, dest)
        else:
            logger.info("캐릭터 라이브러리 이미 존재: %s", dest)

        # 인덱스 업데이트
        entry = {
            "name_base": name_base,
            "full_name": char_full_name,
            "role": role,
            "age_group": age_group,
            "art_style": art_style,
            "path": _normalize_path(dest),
            "source_project": project,
        }

        # 중복 제거 후 추가
        self._index["characters"] = [
            e for e in self._index.get("characters", [])
            if not (e.get("name_base") == name_base and
                    e.get("art_style") == art_style and
                    e.get("age_group") == age_group)
        ]
        self._index["characters"].append(entry)
        self._save_index()

        return _normalize_path(dest)

    def get_project_characters(self, project_dir: str, art_style: str) -> dict:
        """프로젝트의 scene_specs에서 2씬+ 캐릭터를 추출하고 라이브러리에서 매칭.

        Returns: {char_full_name: {"path": str or None, "count": int, "library": bool}}
        """
        specs_path = Path(project_dir) / "scene_specs.json"
        if not specs_path.exists():
            return {}

        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        char_counts = {}
        for scene in specs.get("scenes", []):
            for char in scene.get("characters", []):
                if isinstance(char, str):
                    char_counts[char] = char_counts.get(char, 0) + 1

        result = {}
        for char, count in char_counts.items():
            if count < 2:
                continue

            # 프로젝트 로컬에서 먼저 검색
            local_dir = Path(project_dir) / "images" / "characters"
            name_base = char.split("(")[0].strip()
            local_matches = list(local_dir.glob(f"*{name_base}*")) if local_dir.exists() else []

            if local_matches:
                result[char] = {"path": str(local_matches[0]), "count": count, "library": False}
            else:
                # 라이브러리에서 검색
                lib_path = self.find_for_scene(char, art_style)
                result[char] = {"path": lib_path, "count": count, "library": bool(lib_path)}

        return result

    @staticmethod
    def _parse_filename(path: Path, art_style: str) -> Optional[dict]:
        """파일명에서 캐릭터 정보 추출."""
        stem = path.stem  # "천주혁(대표,30대)"
        name_base = stem.split("(")[0].strip()
        role_match = re.search(r'\(([^,)]+)', stem)
        role = role_match.group(1).strip() if role_match else ""
        age_match = re.search(r'(\d+대)', stem)
        age_group = age_match.group(1) if age_match else ""

        return {
            "name_base": name_base,
            "full_name": stem,
            "role": role,
            "age_group": age_group,
            "art_style": art_style,
            "path": _normalize_path(path),
        }
