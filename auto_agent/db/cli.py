"""
프로젝트 관리 CLI.

사용법:
  auto-agent project list                      # 프로젝트 목록
  auto-agent project create                    # 신규 프로젝트 (인터랙티브)
  auto-agent project create "프로젝트명"         # 신규 프로젝트 (비인터랙티브)
  auto-agent project active                    # 활성 프로젝트 확인
  auto-agent project info <slug>               # 프로젝트 상세
  auto-agent config get                        # 프로젝트 config 조회
  auto-agent config set <key> <value>          # config 키-값 설정
  auto-agent config set-json '{"art_style":..}'# config JSON 전체 설정
  auto-agent version list <file_type>          # 버전 목록
  auto-agent version rollback <file_type> <N>  # v(N)으로 롤백
  auto-agent assets [--type audio]             # 에셋 목록
  auto-agent cleanup [--execute]               # 클린업 (기본: dry-run)
  auto-agent costs                             # 비용 요약
  auto-agent dashboard [--port 8080]           # 웹 대시보드 실행
"""
import sys
import os

from auto_agent.ui import (
    console,
    print_error,
    print_success,
    print_warning,
    print_header,
    is_non_interactive,
    project_table,
    config_panel,
    project_info_panel,
    voice_table,
    style_table,
    cost_table,
    version_table,
    asset_table,
)


def _get_pm():
    """로컬 SQLite ProjectManager 반환."""
    from auto_agent.db.project_manager import ProjectManager
    from auto_agent.db.connection import db_exists, init_db
    if not db_exists():
        init_db()
    return ProjectManager()


def cmd_init(args):
    """워크스페이스 초기화 (로컬 DB 확인)."""
    pm = _get_pm()
    projects = pm.list_projects()
    print_success(f"로컬 DB 연결 완료. 프로젝트 {len(projects)}개 확인.")


def cmd_migrate(args):
    """기존 로컬 프로젝트 마이그레이션."""
    from auto_agent.db.migrate_existing import main
    main()


def cmd_project(args):
    """프로젝트 관리 서브커맨드."""
    pm = _get_pm()

    if not args or args[0] == "list":
        projects = pm.list_projects()
        if not projects:
            print_warning("프로젝트가 없습니다.")
            return
        console.print(project_table(projects))

    elif args[0] == "create":
        if len(args) < 2 and not is_non_interactive():
            # ── 인터랙티브 모드 ──
            try:
                from auto_agent.ui.prompts import prompt_project_create
                data = prompt_project_create()
            except KeyboardInterrupt:
                console.print("\n[dim]취소됨[/dim]")
                return

            config = {}
            if data.get("art_style"):
                config["art_style"] = data["art_style"]
            if data.get("voice_id"):
                config["voice_id"] = data["voice_id"]
            if data.get("voice_settings"):
                config["voice_settings"] = data["voice_settings"]

            pid = pm.create_project(
                name=data["name"],
                slug=data["slug"],
                topic=data["topic"],
                theme=data["theme"],
                config=config or None,
            )
            console.print()
            print_success(f"프로젝트 생성 완료: [accent]{data['name']}[/accent] (slug={data['slug']})")
            console.print(f"\n  다음 단계: [accent]auto-agent run --project {data['slug']}[/accent]")
        else:
            # ── 비인터랙티브 모드 ──
            if len(args) < 2:
                print_error("Usage: project create <name> [--topic <topic>]")
                return
            name = args[1]
            if name.startswith("-"):
                print_error("Usage: project create <name> [--topic <topic>]")
                return
            from auto_agent.scripts.project_paths import slugify
            slug = slugify(name)
            topic = None
            if "--topic" in args:
                idx = args.index("--topic")
                if idx + 1 < len(args):
                    topic = args[idx + 1]
            pid = pm.create_project(name=name, slug=slug, topic=topic)
            print_success(f"프로젝트 생성 완료: slug={slug}")

    elif args[0] == "active":
        p = pm.get_active_project()
        if p:
            assets = pm.get_asset_counts(p["id"])
            console.print(project_info_panel(p, assets))
        else:
            print_warning("활성 프로젝트가 없습니다.")

    elif args[0] == "info":
        if len(args) < 2:
            print_error("Usage: project info <slug>")
            return
        p = pm.get_project(slug=args[1])
        if not p:
            print_error(f"프로젝트 '{args[1]}' 을 찾을 수 없습니다.")
            return
        assets = pm.get_asset_counts(p["id"])
        console.print(project_info_panel(p, assets))

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: list, create, active, info")


def cmd_config(args):
    """프로젝트 config 관리 (art_style, voice_id, voice_settings 등)."""
    import json

    pm = _get_pm()

    # --project <slug> 옵션 처리
    project = None
    remaining = list(args)
    if "--project" in remaining:
        idx = remaining.index("--project")
        if idx + 1 < len(remaining):
            slug = remaining[idx + 1]
            remaining = remaining[:idx] + remaining[idx + 2:]
            project = pm.get_project(slug=slug)
            if not project:
                print_error(f"프로젝트 '{slug}' 을 찾을 수 없습니다.")
                sys.exit(1)

    if not project:
        project = pm.get_active_project()
    if not project:
        print_warning("활성 프로젝트가 없습니다. --project <slug> 로 지정하세요.")
        return

    args = remaining

    if not args or args[0] == "get":
        config = pm.get_config(project["id"])
        console.print(config_panel(config, project["name"]))

    elif args[0] == "set":
        if len(args) < 3:
            console.print("[accent]Usage:[/accent] config set <key> <value>")
            console.print("  [dim]예시:[/dim]")
            console.print("    config set art_style artstyle/styles/semoji.json")
            console.print("    config set voice_id 9Sj8ugvpK1DmcAXyvi3a")
            console.print('    config set voice_settings \'{"stability":1.0,"speed":1.1}\'')
            return
        key = args[1]
        value = args[2]
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass

        # voice 프리셋 이름 → voice_id + voice_settings 자동 해석
        if key == "voice" and isinstance(value, str):
            from auto_agent.voice_manager import VoiceManager
            vm = VoiceManager()
            preset = vm.get_voice(value)
            if preset:
                updates = {"voice_id": preset["voice_id"]}
                if preset.get("voice_settings"):
                    updates["voice_settings"] = preset["voice_settings"]
                pm.update_config(project["id"], **updates)
                print_success(f"voice = {value}  (프로젝트: {project['name']})")
                print_success(f"  → voice_id = {preset['voice_id']}")
                if preset.get("voice_settings"):
                    print_success(f"  → voice_settings = {json.dumps(preset['voice_settings'])}")
                return
            else:
                print_error(f"음성 프리셋 '{value}'을 찾을 수 없습니다.")
                console.print("  [dim]사용 가능한 프리셋: auto-agent voice list[/dim]")
                return

        pm.update_config(project["id"], **{key: value})
        print_success(f"{key} = {value}  (프로젝트: {project['name']})")

        # art_style 설정 시 → JSON + 참조 이미지를 프로젝트 폴더에 복사
        if key == "art_style":
            dest = pm.provision_art_style(project["id"])
            if dest:
                print_success(f"  → 프로젝트 폴더에 복사 완료: {dest}")
            else:
                print_error(f"  → 아트스타일 파일을 찾을 수 없습니다: {value}")

    elif args[0] == "set-json":
        if len(args) < 2:
            print_error("Usage: config set-json '<json>'")
            return
        try:
            config = json.loads(args[1])
        except json.JSONDecodeError as e:
            print_error(f"잘못된 JSON: {e}")
            sys.exit(1)
        pm.set_config(project["id"], config)
        print_success(f"Config 교체 완료: {project['name']}")
        console.print(config_panel(config, project["name"]))

    elif args[0] == "delete":
        if len(args) < 2:
            print_error("Usage: config delete <key>")
            return
        key = args[1]
        config = pm.get_config(project["id"])
        if key in config:
            del config[key]
            pm.set_config(project["id"], config)
            print_success(f"키 삭제됨: {key}")
        else:
            print_warning(f"키 '{key}' 가 config에 없습니다.")

    else:
        print_error(f"알 수 없는 서브커맨드: {args[0]}")
        console.print("  사용 가능: get, set <key> <value>, set-json '<json>', delete <key>")


def cmd_version(args):
    """버전 관리."""
    pm = _get_pm()
    project = pm.get_active_project()
    if not project:
        print_warning("활성 프로젝트가 없습니다.")
        return

    if not args or args[0] == "list":
        file_type = args[1] if len(args) > 1 else "scene_specs"
        versions = pm.get_versions(project["id"], file_type)
        if not versions:
            print_warning(f"{file_type}의 버전이 없습니다.")
            return
        console.print(version_table(versions, file_type))

    elif args[0] == "rollback":
        if len(args) < 3:
            print_error("Usage: version rollback <file_type> <version_number>")
            return
        file_type = args[1]
        version = int(args[2])
        path = pm.rollback_version(project["id"], file_type, version)
        print_success(f"{file_type} → v{version} 롤백 완료: {path}")

    else:
        console.print("  사용 가능: list [file_type], rollback <file_type> <version>")


def cmd_assets(args):
    """에셋 조회."""
    pm = _get_pm()
    project = pm.get_active_project()
    if not project:
        print_warning("활성 프로젝트가 없습니다.")
        return

    asset_type = None
    if "--type" in args:
        idx = args.index("--type")
        if idx + 1 < len(args):
            asset_type = args[idx + 1]

    assets = pm.get_assets(project["id"], asset_type=asset_type)
    counts = pm.get_asset_counts(project["id"])

    console.print(asset_table(assets, counts))


def cmd_cleanup(args):
    """클린업."""
    from auto_agent.db.cleanup import CleanupManager

    pm = _get_pm()
    project = pm.get_active_project()
    if not project:
        print_warning("활성 프로젝트가 없습니다.")
        return

    dry_run = "--execute" not in args
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project["id"], dry_run=dry_run)

    mode = "[warning]DRY RUN[/warning]" if dry_run else "[success]실행됨[/success]"
    console.print(f"\nCleanup [{mode}] — {project['name']}")

    if result["backups_found"]:
        console.print(f"\n  [accent]백업 파일[/accent] ({len(result['backups_found'])}개):")
        for f in result["backups_found"]:
            tag = "[red]삭제됨[/red]" if not dry_run else "[dim]발견[/dim]"
            console.print(f"    {tag} {f}")

    if result["orphans_found"]:
        console.print(f"\n  [accent]고아 에셋:[/accent]")
        for category, files in result["orphans_found"].items():
            console.print(f"    {category}: {len(files)}개")
            for f in files[:5]:
                tag = "[red]삭제됨[/red]" if not dry_run else "[dim]발견[/dim]"
                console.print(f"      {tag} {f}")
            if len(files) > 5:
                console.print(f"      [dim]... 외 {len(files) - 5}개[/dim]")

    if result["temp_dirs_found"]:
        console.print(f"\n  [accent]임시 디렉토리[/accent] ({len(result['temp_dirs_found'])}개):")
        for d in result["temp_dirs_found"]:
            tag = "[red]삭제됨[/red]" if not dry_run else "[dim]발견[/dim]"
            console.print(f"    {tag} {d}")

    if result["versions_cleaned"]:
        console.print(f"\n  [accent]버전 정리:[/accent]")
        for ft, files in result["versions_cleaned"].items():
            console.print(f"    {ft}: {len(files)}개 이전 버전 제거")

    total = (
        len(result["backups_found"])
        + sum(len(v) for v in result["orphans_found"].values())
        + len(result["temp_dirs_found"])
    )
    if total == 0:
        print_success("정리할 항목이 없습니다.")
    elif dry_run:
        console.print(f"\n  [dim]총 {total}개 발견. --execute 로 삭제 실행[/dim]")


def cmd_costs(args):
    """비용 요약."""
    pm = _get_pm()

    total = pm.get_cost_summary()
    projects = pm.list_projects()
    project_costs = []
    if projects:
        for p in projects:
            cost = pm.get_cost_summary(p["id"])
            if cost.get("total_runs", 0) > 0:
                project_costs.append((p["name"], cost))

    console.print(cost_table(total, project_costs))


def cmd_dashboard(args):
    """웹 대시보드 실행."""
    port = 8080
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = int(args[idx + 1])

    print_success(f"대시보드 실행: http://localhost:{port}")
    try:
        import uvicorn
        uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
    except ImportError:
        print_error("uvicorn 미설치. 실행: pip install fastapi uvicorn jinja2")
        sys.exit(1)


COMMANDS = {
    "init": cmd_init,
    "migrate": cmd_migrate,
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
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0]
    if cmd not in COMMANDS:
        print_error(f"알 수 없는 명령어: {cmd}")
        console.print(f"  사용 가능: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[cmd](args[1:])


if __name__ == "__main__":
    main()
