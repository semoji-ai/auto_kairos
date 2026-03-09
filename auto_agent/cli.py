"""
auto-agent — AI 영상 제작 파이프라인 CLI

사용법:
  auto-agent --version                          # 버전
  auto-agent init <workspace>                   # 워크스페이스 초기화
  auto-agent run --project <slug> [옵션]         # 파이프라인 실행
  auto-agent project list|create|active|info    # 프로젝트 관리
  auto-agent config get|set|set-json|delete     # 프로젝트 설정
  auto-agent studio --project <slug>            # Remotion 스튜디오
  auto-agent style list|add|remove              # 아트스타일 관리
  auto-agent voice list|add|remove              # 음성 프리셋 관리
  auto-agent version list|rollback              # 버전 관리
  auto-agent assets [--type audio]              # 에셋 조회
  auto-agent cleanup [--execute]                # 클린업
  auto-agent costs                              # 비용 요약
  auto-agent dashboard [--port 8080]            # 웹 대시보드
  auto-agent update                             # 최신 버전으로 업데이트
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from auto_agent import __version__
from auto_agent.paths import get_package_dir, get_data_dir, get_workspace_dir
from auto_agent.ui import (
    console,
    print_error,
    print_success,
    print_warning,
    print_header,
    is_non_interactive,
    style_table,
    voice_table,
)


def cmd_init(args):
    """워크스페이스 초기화."""
    if not args:
        print_error("Usage: auto-agent init <workspace-path>")
        console.print("  예시: auto-agent init ~/my-project")
        sys.exit(1)

    workspace = Path(args[0]).resolve()
    template_dir = get_package_dir() / "remotion_template"

    print_header(f"auto-agent — 워크스페이스 초기화")
    console.print(f"  경로: [accent]{workspace}[/accent]\n")

    # 1. 디렉토리 생성
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "RESEARCH").mkdir(exist_ok=True)

    # 2. Remotion 템플릿 복사
    remotion_dest = workspace / "remotion"
    if remotion_dest.exists():
        console.print("  [dim]SKIP[/dim] remotion/ (이미 존재)")
    else:
        console.print("  [accent]COPY[/accent] remotion/ 템플릿")
        shutil.copytree(template_dir, remotion_dest, dirs_exist_ok=True)

    # 3. .env.example 생성
    env_example = workspace / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# Auto Agent 환경 변수\n"
            "# 필요한 API 키를 설정하고 .env로 이름 변경하세요.\n\n"
            "# 필수\n"
            "ELEVENLABS_API_KEY=\n"
            "OPENAI_API_KEY=\n\n"
            "# 선택 (Claude Code 구독 대신 API 직접 사용 시)\n"
            "# ANTHROPIC_API_KEY=\n\n"
            "# 선택 (이미지 생성)\n"
            "FAL_API_KEY=\n"
            "SERPER_API_KEY=\n\n"
            "# 선택 (팩트체크)\n"
            "GOOGLE_API_KEY=\n",
            encoding="utf-8",
        )
        console.print("  [accent]CREATE[/accent] .env.example")

    # 4. CLAUDE.md 생성 (Claude Code 연동 — 템플릿 복사)
    claude_md = workspace / "CLAUDE.md"
    if not claude_md.exists():
        template = get_data_dir() / "CLAUDE.md.template"
        if template.exists():
            shutil.copy2(template, claude_md)
        else:
            claude_md.write_text("# Auto Agent 워크스페이스\n", encoding="utf-8")
        console.print("  [accent]CREATE[/accent] CLAUDE.md")
    else:
        console.print("  [dim]SKIP[/dim] CLAUDE.md (이미 존재)")

    # 5. DB 초기화
    db_path = workspace / "auto_agent.db"
    if not db_path.exists():
        import os
        os.environ["AUTO_AGENT_WORKSPACE"] = str(workspace)
        from auto_agent.db.connection import init_db
        init_db()
        console.print("  [accent]CREATE[/accent] auto_agent.db")
    else:
        console.print("  [dim]SKIP[/dim] auto_agent.db (이미 존재)")

    # 5. npm install
    remotion_pkg = remotion_dest / "package.json"
    remotion_nm = remotion_dest / "node_modules"
    if remotion_pkg.exists() and not remotion_nm.exists():
        console.print("  [accent]NPM[/accent] Remotion 의존성 설치 중...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(remotion_dest),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print_success("npm install 완료")
            else:
                print_warning(f"npm install 실패: {result.stderr[:200]}")
                console.print(f"  수동 실행: cd {remotion_dest} && npm install")
        except FileNotFoundError:
            print_warning("npm을 찾을 수 없습니다. Node.js를 먼저 설치하세요.")
            console.print(f"  설치 후: cd {remotion_dest} && npm install")

    console.print(f"\n[accent]워크스페이스 준비 완료![/accent]")
    console.print(f"\n  다음 단계:")
    console.print(f"    1. cp {workspace}/.env.example {workspace}/.env")
    console.print(f"    2. .env 파일에 API 키 입력")
    console.print(f"    3. cd {workspace}")
    console.print(f"    4. [accent]auto-agent project create[/accent]")


def cmd_run(args):
    """파이프라인 실행."""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent run")
    parser.add_argument("--project", required=True, help="프로젝트 slug")
    parser.add_argument("--from", dest="from_step", help="이 step부터 실행")
    parser.add_argument("--only", dest="only_step", help="이 step만 실행")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 계획만 출력")
    parser.add_argument("--workspace", help="워크스페이스 경로")
    parsed = parser.parse_args(args)

    from auto_agent.orchestrator.runner import PipelineRunner
    runner = PipelineRunner(parsed.project)
    runner.run(
        from_step=parsed.from_step,
        only_step=parsed.only_step,
        dry_run=parsed.dry_run,
    )


def cmd_studio(args):
    """Remotion 스튜디오 실행."""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent studio")
    parser.add_argument("--project", help="프로젝트 slug (manifest 자동 로드)")
    parser.add_argument("--workspace", help="워크스페이스 경로")
    parsed = parser.parse_args(args)

    workspace = get_workspace_dir()
    remotion_dir = workspace / "remotion"

    if not remotion_dir.exists():
        print_error(f"Remotion 디렉토리를 찾을 수 없습니다: {remotion_dir}")
        console.print(f"  'auto-agent init {workspace}' 를 먼저 실행하세요.")
        sys.exit(1)

    env = {}
    if parsed.project:
        env["PROJECT_NAME"] = parsed.project

    print_success(f"Remotion Studio 시작: {remotion_dir}")
    subprocess.run(
        ["npx", "remotion", "studio"],
        cwd=str(remotion_dir),
        env={**__import__("os").environ, **env},
    )


def cmd_project(args):
    """프로젝트 관리 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_project as _cmd_project
    _cmd_project(args)


def cmd_config(args):
    """프로젝트 설정 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_config as _cmd_config
    _cmd_config(args)


def cmd_version(args):
    """버전 관리 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_version as _cmd_version
    _cmd_version(args)


def cmd_assets(args):
    """에셋 조회 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_assets as _cmd_assets
    _cmd_assets(args)


def cmd_cleanup(args):
    """클린업 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_cleanup as _cmd_cleanup
    _cmd_cleanup(args)


def cmd_costs(args):
    """비용 요약 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_costs as _cmd_costs
    _cmd_costs(args)


def cmd_dashboard(args):
    """웹 대시보드 — db.cli에 위임."""
    from auto_agent.db.cli import cmd_dashboard as _cmd_dashboard
    _cmd_dashboard(args)


# ── 아트스타일 관리 ─────────────────────────────

def cmd_style(args):
    """아트스타일 관리: list, add, remove."""
    from auto_agent.ui.prompts import _scan_art_styles

    if not args or args[0] == "list":
        styles = _scan_art_styles()
        if not styles:
            print_warning("등록된 아트스타일이 없습니다.")
            return
        console.print(style_table(styles))

    elif args[0] == "add":
        try:
            from auto_agent.ui.prompts import prompt_style_add
            data = prompt_style_add()
        except KeyboardInterrupt:
            console.print("\n[dim]취소됨[/dim]")
            return

        # 워크스페이스에 JSON 저장
        styles_dir = get_workspace_dir() / "artstyle" / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)

        filename = data["name"].replace(" ", "_").lower() + ".json"
        filepath = styles_dir / filename

        style_json = {
            "name": data["name"],
            "description": data["description"],
            "reference_image": "",
            "scene_style_description": data["art_style"],
            "style": {
                "art_style": data["art_style"],
                "color_palette": data["color_palette"],
                "mood_and_tone": data["mood_and_tone"],
            },
            "technical": {
                "no_text": True,
                "resolution": "1024x1024",
            },
        }

        filepath.write_text(
            json.dumps(style_json, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print_success(f"아트스타일 추가됨: [accent]{data['name']}[/accent] → {filepath}")

    elif args[0] == "remove":
        if len(args) < 2:
            print_error("Usage: style remove <파일명 또는 스타일명>")
            return

        target = args[1]
        styles = _scan_art_styles()
        matched = None
        for s in styles:
            if s["filename"] == target or s["name"] == target or s["filename"] == target + ".json":
                matched = s
                break

        if not matched:
            print_error(f"스타일 '{target}' 을 찾을 수 없습니다.")
            return

        # 워크스페이스 스타일만 삭제 가능
        ws_styles = str(get_workspace_dir() / "artstyle" / "styles")
        if not matched["path"].startswith(ws_styles):
            print_error("기본 내장 스타일은 삭제할 수 없습니다. 워크스페이스에 추가한 스타일만 삭제 가능합니다.")
            return

        Path(matched["path"]).unlink()
        print_success(f"스타일 삭제됨: {matched['name']}")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, add, remove <이름>")


# ── 음성 프리셋 관리 ────────────────────────────

def cmd_voice(args):
    """음성 프리셋 관리: list, add, remove."""
    from auto_agent.voice_manager import VoiceManager
    vm = VoiceManager()

    if not args or args[0] == "list":
        voices = vm.list_voices()
        if not voices:
            print_warning("등록된 음성 프리셋이 없습니다.")
            return
        console.print(voice_table(voices))

    elif args[0] == "add":
        try:
            from auto_agent.ui.prompts import prompt_voice_add
            data = prompt_voice_add()
        except KeyboardInterrupt:
            console.print("\n[dim]취소됨[/dim]")
            return

        vm.add_voice(
            name=data["name"],
            voice_id=data["voice_id"],
            description=data["description"],
        )
        print_success(f"음성 프리셋 추가됨: [accent]{data['name']}[/accent]")

    elif args[0] == "remove":
        if len(args) < 2:
            print_error("Usage: voice remove <이름>")
            return
        name = args[1]
        if vm.remove_voice(name):
            print_success(f"음성 프리셋 삭제됨: {name}")
        else:
            print_error(f"프리셋 '{name}' 을 찾을 수 없습니다.")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, add, remove <이름>")


def cmd_update(args):
    """최신 버전으로 업데이트."""
    import importlib.metadata

    print_header("auto-agent — 업데이트")

    # 패키지 설치 위치에서 Git repo 경로 탐색
    pkg_dir = get_package_dir()
    repo_dir = pkg_dir.parent  # auto_agent/ → repo root

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        # pip install git+... 로 설치한 경우 (site-packages에 위치)
        console.print("  [dim]Git 저장소가 아닌 환경에서 설치되었습니다.[/dim]\n")
        console.print("  업데이트 방법:")
        console.print("  [accent]pip install --upgrade git+ssh://git@github.com/jleavens01/kairos-agent.git[/accent]")
        return

    current = __version__

    # 1. git pull
    console.print(f"  현재 버전: [accent]v{current}[/accent]")
    console.print("  [accent]git pull[/accent] 실행 중...")

    result = subprocess.run(
        ["git", "pull"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print_error(f"git pull 실패: {result.stderr.strip()}")
        return

    if "Already up to date" in result.stdout:
        print_success("이미 최신 버전입니다.")
        return

    console.print(f"  {result.stdout.strip()}")

    # 2. pip install -e . (editable) 또는 pip install . 재설치
    console.print("  [accent]pip install[/accent] 재설치 중...")

    # editable 설치 여부 확인
    try:
        dist = importlib.metadata.distribution("auto-agent")
        direct_url = dist.read_text("direct_url.json")
        is_editable = direct_url and '"editable": true' in direct_url
    except Exception:
        is_editable = False

    pip_cmd = [sys.executable, "-m", "pip", "install", "-q"]
    if is_editable:
        pip_cmd += ["-e", str(repo_dir)]
    else:
        pip_cmd += [str(repo_dir)]

    result = subprocess.run(pip_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print_error(f"pip install 실패: {result.stderr.strip()[:300]}")
        return

    # 3. 업데이트 후 버전 확인
    result = subprocess.run(
        [sys.executable, "-c", "from auto_agent import __version__; print(__version__)"],
        capture_output=True,
        text=True,
    )
    new_version = result.stdout.strip() if result.returncode == 0 else "?"

    if new_version != current:
        print_success(f"업데이트 완료! v{current} → [accent]v{new_version}[/accent]")
    else:
        print_success(f"재설치 완료 (v{new_version})")


COMMANDS = {
    "init": cmd_init,
    "run": cmd_run,
    "studio": cmd_studio,
    "project": cmd_project,
    "config": cmd_config,
    "version": cmd_version,
    "assets": cmd_assets,
    "cleanup": cmd_cleanup,
    "costs": cmd_costs,
    "dashboard": cmd_dashboard,
    "style": cmd_style,
    "voice": cmd_voice,
    "update": cmd_update,
    "skill-path": lambda args: print(get_data_dir()),
}


def _print_banner():
    """브랜드 배너 + 사용법 출력."""
    print_header(f"auto-agent v{__version__}")
    console.print()
    cmds = [
        ("init <workspace>", "워크스페이스 초기화"),
        ("project create", "새 프로젝트 (인터랙티브)"),
        ("project list", "프로젝트 목록"),
        ("run --project <slug>", "파이프라인 실행"),
        ("studio --project <slug>", "Remotion 스튜디오"),
        ("config get|set", "프로젝트 설정"),
        ("style list|add|remove", "아트스타일 관리"),
        ("voice list|add|remove", "음성 프리셋 관리"),
        ("version list|rollback", "버전 관리"),
        ("assets", "에셋 조회"),
        ("costs", "비용 요약"),
        ("dashboard", "웹 대시보드"),
        ("update", "최신 버전으로 업데이트"),
    ]
    for cmd, desc in cmds:
        console.print(f"  [accent]auto-agent {cmd:<28}[/accent] {desc}")


def main():
    # 워크스페이스 .env 로드 (API 키 등)
    try:
        from dotenv import load_dotenv
        load_dotenv(get_workspace_dir() / ".env")
    except ImportError:
        pass

    args = sys.argv[1:]

    # --version 플래그
    if not args or "--version" in args:
        if "--version" in args:
            console.print(f"[accent]auto-agent[/accent] v{__version__}")
            return
        _print_banner()
        return

    if args[0] in ("-h", "--help", "help"):
        _print_banner()
        return

    cmd = args[0]
    if cmd not in COMMANDS:
        print_error(f"알 수 없는 명령어: {cmd}")
        console.print(f"  사용 가능: [accent]{', '.join(COMMANDS.keys())}[/accent]")
        sys.exit(1)

    COMMANDS[cmd](args[1:])


if __name__ == "__main__":
    main()
