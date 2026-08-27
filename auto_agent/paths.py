"""
이중 루트 경로 해석 (Dual Root Path Resolution)

PACKAGE_DIR:  패키지 설치 위치 (읽기 전용 — skills, pipeline.json, agents.json 등)
WORKSPACE_DIR: 사용자 워크스페이스 (읽기/쓰기 — output, .env, DB, remotion)

워크스페이스 결정 우선순위:
  1. --workspace <path> CLI 인자
  2. AUTO_AGENT_WORKSPACE 환경 변수
  3. 패키지 위치 기반 (auto_agent/ 의 부모 디렉토리)
"""
import os
import sys
from pathlib import Path
from typing import Optional


def get_package_dir() -> Path:
    """패키지 루트 디렉토리 (auto_agent/)."""
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """번들 데이터 디렉토리 (pipeline.json, agents.json, skills/ 등)."""
    return get_package_dir() / "data"


def get_charsheet_dir() -> Optional[Path]:
    """인물 시트가 있는 **한 폴더**. 기본은 `_imggen/characters/sheets`.

    폴더를 나누지 않는다. 예전에는 `final_v2`(원본)와 `final_v2_up`(업스케일)로
    갈라 두어, 대시보드는 앞쪽을 보고 생성기는 뒤쪽을 봤다. 새 시트를 한쪽에만
    넣으면 화면에서 「시트 없음」으로 떴다 — 구평회가 그랬다.

    **규칙은 파일 이름에 둔다.**

        <id>_sheet.png       기본
        <id>_sheet_up.png    업스케일 (있으면 이것을 쓴다)
        _try/…               시도본은 하위 폴더로 물린다

    워크스페이스(NAS)와 코드 루트가 갈릴 수 있어 둘 다 본다. 시트는 저장소에
    함께 들어 있어 워크스페이스만 보면 못 찾는다.

    옛 폴더 이름(`final_v2`·`final_v2_up`)도 뒤에서 찾아 준다 — 아직 옮기지
    않은 프로젝트가 깨지지 않게.
    """
    env = os.getenv("KAIROS_CHARSHEET_DIR")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p

    names = ("sheets", "final_v2_up", "final_v2")   # 앞이 정본, 뒤는 옛 이름
    fallback = None
    for base in (get_package_dir().parent, get_workspace_dir()):
        for name in names:
            p = base / "_imggen" / "characters" / name
            if not p.is_dir():
                continue
            if any(p.glob("*_sheet.png")):
                return p
            if fallback is None:
                fallback = p
    return fallback


def charsheet_path(char_id: str, *, upscaled: bool = True) -> Optional[Path]:
    """인물 시트 한 장의 경로. **여기 말고 다른 데서 경로를 짜지 않는다.**

    업스케일본은 파일 이름의 `_up` 으로 가른다. 폴더를 나누지 않는다.

        upscaled=True   `<id>_sheet_up.png` → 없으면 `<id>_sheet.png`
        upscaled=False  `<id>_sheet.png`

    없으면 None. 부르는 쪽이 「시트 없음」을 판단한다.
    """
    d = get_charsheet_dir()
    if not d:
        return None
    if upscaled:
        up = d / f"{char_id}_sheet_up.png"
        if up.is_file():
            return up
    base = d / f"{char_id}_sheet.png"
    return base if base.is_file() else None


def get_workspace_dir() -> Path:
    """사용자 워크스페이스 디렉토리 (output, .env, DB)."""
    # 1. --workspace CLI 인자
    for i, arg in enumerate(sys.argv):
        if arg == "--workspace" and i + 1 < len(sys.argv):
            p = Path(sys.argv[i + 1]).resolve()
            if p.exists():
                return p
            raise FileNotFoundError(f"Workspace not found: {p}")

    # 2. AUTO_AGENT_WORKSPACE 환경 변수
    env = os.getenv("AUTO_AGENT_WORKSPACE")
    if env:
        p = Path(env).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Workspace not found: {p}")

    # 3. 패키지 위치 기반 — auto_agent/ 의 부모가 프로젝트 루트
    return get_package_dir().parent


# 모듈 레벨 상수 (자주 쓰이므로 미리 해석)
PACKAGE_DIR = get_package_dir()
DATA_DIR = get_data_dir()


def episode_label(slug: str) -> str:
    """슬러그 → 편 번호 라벨(EP05 …).

    슬러그 꼬리를 그대로 쓰면 안 된다. 5편의 슬러그는 ep06b이고 6편은 ep05다
    — 원고를 다시 쓰면서 어긋난 것이라 지도(_imggen/ep_map.json)가 정본이다.
    레이어 폴더를 이 라벨로 잡으므로 여기서 어긋나면 서로 다른 곳을 본다.
    """
    import json
    import re

    f = get_package_dir().parent / "_imggen" / "ep_map.json"
    try:
        emap = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return ""
    for key, v in emap.items():
        if v.get("slug") == slug:
            m = re.match(r"(EP\d+)", key)
            if m:
                return m.group(1)
    return ""


def layer_sets(slug: str, scene_num: int) -> list[Path]:
    """이 씬에 분리해 둔 레이어 폴더들."""
    ep = episode_label(slug)
    if not ep:
        return []
    base = get_package_dir().parent / "_imggen" / f"{ep.lower()}_anim"
    return [d for d in sorted(base.glob(f"s{scene_num:03d}*"))
            if (d / "layers.json").is_file()]


def resolve_project(token: str) -> tuple[Path, str]:
    """`EP01` 같은 편 라벨이나 프로젝트 slug 를 받아 (프로젝트 폴더, 라벨).

    시리즈 편은 `_imggen/ep_map.json`이 편 번호를 들고 있다. 하지만 그 지도는
    LG 12부작을 위해 만든 것이라, 다른 프로젝트를 돌리면 여기서 막혔다.
    지도에 없으면 slug 로 DB를 찾는다 — 지도는 있으면 쓰고 없으면 없는 대로.

    돌려주는 라벨은 파일 이름에 쓴다(`_imggen/<라벨>_mode.json` 등).
    """
    import json
    import re

    root = get_package_dir().parent
    f = root / "_imggen" / "ep_map.json"
    if f.exists():
        try:
            emap = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            emap = {}
        for key, v in emap.items():
            m = re.match(r"(EP\d+)", key)
            label = m.group(1) if m else key
            if token.upper() == label.upper() or token == v.get("slug"):
                return Path(v["dir"]), label

    # 지도 밖 — slug 로 찾는다
    from auto_agent.db.project_manager import ProjectManager

    p = ProjectManager().get_project(slug=token)
    if not p:
        raise SystemExit(f"프로젝트를 찾을 수 없습니다: {token}")
    # 라벨은 **되돌아올 수 있어야 한다.** 하류 스크립트가 이 라벨을 인자로 받아
    # 다시 resolve_project 를 부르기 때문이다. 한글을 지우면 순수 한글 slug 가
    # 통째로 빈 문자열이 되어 "PROJECT" 로 떨어지고, 그 이름으로는 DB 에서
    # 프로젝트를 찾을 수 없다 — 디아지오편에서 하류 6개가 전부 그렇게 죽었다.
    label = re.sub(r"[^0-9A-Za-z가-힣]+", "_", token).strip("_")[:40] or "PROJECT"
    return Path(p["output_dir"]), label


def get_vault_dir() -> Path:
    """Obsidian 볼트 디렉토리 (KAIROS_VAULT_DIR 환경변수)."""
    env = os.getenv("KAIROS_VAULT_DIR")
    if not env:
        raise EnvironmentError(
            "KAIROS_VAULT_DIR 환경변수가 설정되지 않았습니다. "
            ".env 파일에 KAIROS_VAULT_DIR=/path/to/kairos-vault 를 추가하세요."
        )
    p = Path(env).resolve()
    if not p.exists():
        raise FileNotFoundError(f"볼트 디렉토리를 찾을 수 없습니다: {p}")
    return p
