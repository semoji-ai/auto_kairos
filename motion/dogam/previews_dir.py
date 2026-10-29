"""도감 미리보기(mp4·jpg) 위치 — 저장소에는 넣지 않는다(약 92MB, NAS 보관).

찾는 순서
  1. 환경변수 DOGAM_PREVIEWS_DIR
  2. motion/dogam/previews  (로컬 캐시 또는 NAS 로 가는 심볼릭 링크, .gitignore)
  3. NAS 백업 기본 경로 NAS_PREVIEWS (마운트돼 있을 때)
아무것도 없으면 2번 경로를 돌려준다(빌더는 '미리보기 없음'으로 계속 진행).

AE 패널이 쓰는 12개 미리보기는 별도로 adobe/data/semoji-motion/dogam/previews 에 번들돼 있다.
"""
import os
from pathlib import Path

DOGAM = Path(__file__).resolve().parent
LOCAL = DOGAM / "previews"
NAS_PREVIEWS = Path("/Volumes/jleavens/007_AI_Projects/semoji-motion_backup_20261007/dogam/previews")


def previews_dir() -> Path:
    env = os.environ.get("DOGAM_PREVIEWS_DIR")
    if env:
        return Path(env).expanduser()
    for d in (LOCAL, NAS_PREVIEWS):
        if d.is_dir():
            return d
    return LOCAL


if __name__ == "__main__":
    print(previews_dir())
