"""
auto-agent — AI 영상 제작 파이프라인 CLI

사용법:
  auto-agent --version                          # 버전
  auto-agent init <workspace>                   # 워크스페이스 초기화
  auto-agent run --project <slug> [옵션]         # 파이프라인 실행
  auto-agent project list|create|active|info    # 프로젝트 관리
  auto-agent config get|set|set-json|delete     # 프로젝트 설정
  auto-agent studio --project <slug>            # Remotion 스튜디오
  auto-agent version list|rollback              # 버전 관리
  auto-agent assets [--type audio]              # 에셋 조회
  auto-agent cleanup [--execute]                # 클린업
  auto-agent costs                              # 비용 요약
  auto-agent dashboard [--port 8080]            # 웹 대시보드
"""
import shutil
import subprocess
import sys
from pathlib import Path

from auto_agent import __version__
from auto_agent.paths import get_package_dir, get_data_dir, get_workspace_dir


def cmd_init(args):
    """워크스페이스 초기화."""
    if not args:
        print("Usage: auto-agent init <workspace-path>")
        print("Example: auto-agent init ~/my-project")
        sys.exit(1)

    workspace = Path(args[0]).resolve()
    template_dir = get_package_dir() / "remotion_template"

    print(f"Initializing workspace: {workspace}")

    # 1. 디렉토리 생성
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)
    (workspace / "RESEARCH").mkdir(exist_ok=True)

    # 2. Remotion 템플릿 복사
    remotion_dest = workspace / "remotion"
    if remotion_dest.exists():
        print(f"  [SKIP] remotion/ already exists")
    else:
        print(f"  [COPY] remotion/ template")
        shutil.copytree(template_dir, remotion_dest, dirs_exist_ok=True)

    # 3. .env.example 생성
    env_example = workspace / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            "# Auto Agent 환경 변수\n"
            "# 필요한 API 키를 설정하고 .env로 이름 변경하세요.\n\n"
            "# 필수\n"
            "ANTHROPIC_API_KEY=\n"
            "ELEVENLABS_API_KEY=\n"
            "OPENAI_API_KEY=\n\n"
            "# 선택 (이미지 생성)\n"
            "FAL_API_KEY=\n"
            "SERPER_API_KEY=\n\n"
            "# 선택 (팩트체크)\n"
            "GOOGLE_API_KEY=\n",
            encoding="utf-8",
        )
        print(f"  [CREATE] .env.example")

    # 4. DB 초기화
    db_path = workspace / "auto_agent.db"
    if not db_path.exists():
        import os
        os.environ["AUTO_AGENT_WORKSPACE"] = str(workspace)
        from auto_agent.db.connection import init_db
        init_db()
        print(f"  [CREATE] auto_agent.db")
    else:
        print(f"  [SKIP] auto_agent.db already exists")

    # 5. npm install
    remotion_pkg = remotion_dest / "package.json"
    remotion_nm = remotion_dest / "node_modules"
    if remotion_pkg.exists() and not remotion_nm.exists():
        print(f"  [NPM] Installing Remotion dependencies...")
        try:
            result = subprocess.run(
                ["npm", "install"],
                cwd=str(remotion_dest),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  [OK] npm install complete")
            else:
                print(f"  [WARN] npm install failed: {result.stderr[:200]}")
                print(f"         Run manually: cd {remotion_dest} && npm install")
        except FileNotFoundError:
            print(f"  [WARN] npm not found. Install Node.js first.")
            print(f"         Then run: cd {remotion_dest} && npm install")

    print(f"\nWorkspace ready: {workspace}")
    print(f"Next steps:")
    print(f"  1. cp {workspace}/.env.example {workspace}/.env")
    print(f"  2. Edit .env with your API keys")
    print(f"  3. cd {workspace}")
    print(f"  4. auto-agent project create \"My Project\"")
    print(f"  5. auto-agent run --project my-project")


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
        print(f"ERROR: Remotion directory not found: {remotion_dir}")
        print(f"Run 'auto-agent init {workspace}' first.")
        sys.exit(1)

    env = {}
    if parsed.project:
        env["PROJECT_NAME"] = parsed.project

    print(f"Starting Remotion Studio in {remotion_dir}")
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
}


def main():
    args = sys.argv[1:]

    # --version 플래그
    if not args or "--version" in args:
        if "--version" in args:
            print(f"auto-agent {__version__}")
            return
        print(__doc__)
        return

    if args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        print(f"\nRun 'auto-agent --help' for usage.")
        sys.exit(1)

    COMMANDS[cmd](args[1:])


if __name__ == "__main__":
    main()
