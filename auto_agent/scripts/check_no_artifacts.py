"""커밋에 산출물이 섞였는지 본다. pre-commit 훅이 부른다.

    python -m auto_agent.scripts.check_no_artifacts        # 스테이징된 것 검사
    python -m auto_agent.scripts.check_no_artifacts <경로…>

## 왜 무시 규칙만으로 안 되나

`adobe/projects/_archive` 2.9GB(1,802 파일)가 통째로 커밋돼 있었다. 원인은
`adobe/.gitignore` 패턴이 **깊이 하나만** 맞기 때문이다.

    projects/*/images/   →  projects/7184ea44/images/       잡힘
                         →  projects/_archive/<편>/images/  안 잡힘

규칙을 고쳐도 다음에 또 다른 깊이·다른 폴더가 생기면 같은 일이 난다. 규칙은
「내가 아는 자리」만 막고, 이 관문은 **자리를 몰라도** 막는다.

## 무엇을 산출물로 보나

프로젝트 폴더(`output/`, `adobe/projects/`) **아래에 있는 바이너리**만이다.
저장소 자산 — 아트스타일 기준 시트, 폰트, 차트 테스트 케이스, 앱 아이콘 —
은 프로젝트 폴더 밖이라 걸리지 않는다. 원고·기획·표석 같은 텍스트도 통과한다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# 프로젝트가 만들어 내는 것들. 텍스트(.md/.json/.jsonl)는 기록이라 뺀다.
ARTIFACT_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff",
    ".svg", ".psd", ".ai",
    ".mp3", ".wav", ".m4a", ".aac", ".flac",
    ".mp4", ".mov", ".webm", ".mkv",
    ".zip", ".tar", ".gz",
}

# 이 아래는 「작업 산출물이 쌓이는 자리」다. 저장소 자산은 여기 두지 않는다.
PROJECT_DIRS = ("output/", "adobe/projects/", "_imggen/")

MAX_BYTES = 20 * 1024 * 1024      # 프로젝트 폴더 밖이어도 이만한 파일은 물어본다


def _in_project_dir(path: str) -> bool:
    return any(path.startswith(d) for d in PROJECT_DIRS)


def find_artifacts(paths: list[str]) -> list[str]:
    """산출물로 보이는 경로만 돌려준다."""
    out = []
    for p in paths:
        if not p:
            continue
        suffix = Path(p).suffix.lower()
        if _in_project_dir(p) and suffix in ARTIFACT_SUFFIXES:
            out.append(p)
    return out


def find_oversized(paths: list[str], root: Path) -> list[tuple[str, int]]:
    """자리와 무관하게 너무 큰 파일. 실수로 들어온 산출물을 한 번 더 거른다."""
    out = []
    for p in paths:
        f = root / p
        if f.is_file() and f.stat().st_size > MAX_BYTES:
            out.append((p, f.stat().st_size))
    return out


def _staged(root: Path) -> list[str]:
    """스테이징된 경로. **`-z` 로 받는다.**

    `-z` 없이 받으면 git 이 비ASCII 경로를 따옴표로 감싸고 8진수로 이스케이프한다.

        "adobe/projects/\\354\\213\\234\\355\\227\\230\\355\\216\\270/images/x.png"

    그러면 `"` 로 시작해 접두 검사가 전부 빗나간다. **이 저장소의 프로젝트는 전부
    한글 이름**이라(`f772e15c_디아지오_…`) 관문이 통째로 무력해진다 — 실제로
    그렇게 새는 것을 확인하고 고쳤다.
    """
    r = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", "-z"],
        capture_output=True, cwd=str(root),
    )
    return [p for p in r.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True).stdout.strip() or "."
    )
    paths = argv or _staged(root)
    if not paths:
        return 0

    arts = find_artifacts(paths)
    big = find_oversized(paths, root)
    if not arts and not big:
        return 0

    print("\n  ✗ 커밋에 산출물이 섞였습니다.\n", file=sys.stderr)
    if arts:
        print("  프로젝트 폴더 아래의 바이너리:", file=sys.stderr)
        for p in arts[:20]:
            print(f"    {p}", file=sys.stderr)
        if len(arts) > 20:
            print(f"    … 외 {len(arts)-20}개", file=sys.stderr)
    if big:
        print(f"\n  {MAX_BYTES // 2**20}MiB 를 넘는 파일:", file=sys.stderr)
        for p, n in big[:10]:
            print(f"    {p}  ({n/2**20:.1f} MiB)", file=sys.stderr)
    print(
        "\n  산출물은 저장소에 두지 않습니다. 완성한 편은 보관 워크스페이스로 보내세요:\n"
        "    python -m auto_agent.scripts.archive_project <프로젝트>\n\n"
        "  정말 올려야 하는 저장소 자산이면 스테이징에서 빼고 무시 규칙을 손보거나,\n"
        "  이번만 넘기려면  git commit --no-verify  를 쓰세요.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
