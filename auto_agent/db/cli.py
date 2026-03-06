"""
프로젝트 관리 CLI.

사용법:
  python -m db.cli init                              # DB 초기화
  python -m db.cli migrate                           # 기존 프로젝트 마이그레이션
  python -m db.cli project list                      # 프로젝트 목록
  python -m db.cli project create "프로젝트명"         # 신규 프로젝트
  python -m db.cli project active                    # 활성 프로젝트 확인
  python -m db.cli project info <slug>               # 프로젝트 상세
  python -m db.cli config get                        # 프로젝트 config 조회
  python -m db.cli config set <key> <value>          # config 키-값 설정
  python -m db.cli config set-json '{"art_style":..}'# config JSON 전체 설정
  python -m db.cli version list <file_type>          # 버전 목록
  python -m db.cli version rollback <file_type> <N>  # v(N)으로 롤백
  python -m db.cli assets [--type audio]             # 에셋 목록
  python -m db.cli cleanup [--execute]               # 클린업 (기본: dry-run)
  python -m db.cli costs                             # 비용 요약
  python -m db.cli dashboard [--port 8080]           # 웹 대시보드 실행
"""
import sys
import os


def cmd_init(args):
    """DB 초기화."""
    from auto_agent.db.connection import init_db, get_db_path
    path = init_db()
    print(f"DB initialized: {path}")


def cmd_migrate(args):
    """기존 프로젝트 마이그레이션."""
    from auto_agent.db.migrate_existing import main
    main()


def cmd_project(args):
    """프로젝트 관리 서브커맨드."""
    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized. Run 'python -m db.cli init' first.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()

    if not args or args[0] == "list":
        projects = pm.list_projects()
        if not projects:
            print("No projects found.")
            return
        print(f"{'ID':>4}  {'Status':<12}  {'Scenes':>6}  {'Name'}")
        print("-" * 60)
        for p in projects:
            print(f"{p['id']:>4}  {p['status']:<12}  {p['scene_count']:>6}  {p['name']}")

    elif args[0] == "create":
        if len(args) < 2:
            print("Usage: project create <name> [--topic <topic>]")
            return
        name = args[1]
        from auto_agent.scripts.project_paths import slugify
        slug = slugify(name)
        topic = None
        if "--topic" in args:
            idx = args.index("--topic")
            if idx + 1 < len(args):
                topic = args[idx + 1]
        pid = pm.create_project(name=name, slug=slug, topic=topic)
        print(f"Project created: id={pid}, slug={slug}")

    elif args[0] == "active":
        p = pm.get_active_project()
        if p:
            print(f"Active: {p['name']} (id={p['id']}, slug={p['slug']})")
            print(f"  Status: {p['status']}")
            print(f"  Scenes: {p['scene_count']}")
            print(f"  Topic: {p['topic']}")
            print(f"  Output: {p['output_dir']}")
        else:
            print("No active project.")

    elif args[0] == "info":
        if len(args) < 2:
            print("Usage: project info <slug>")
            return
        p = pm.get_project(slug=args[1])
        if not p:
            print(f"Project '{args[1]}' not found.")
            return
        print(f"Project: {p['name']}")
        print(f"  ID: {p['id']}")
        print(f"  Slug: {p['slug']}")
        print(f"  Status: {p['status']}")
        print(f"  Topic: {p['topic']}")
        print(f"  Theme: {p['theme']}")
        print(f"  Scenes: {p['scene_count']}")
        print(f"  Duration: {p['total_duration_sec']:.1f}s")
        print(f"  Output: {p['output_dir']}")
        print(f"  Created: {p['created_at']}")
        print(f"  Updated: {p['updated_at']}")

        assets = pm.get_asset_counts(p["id"])
        if assets:
            print(f"\n  Assets:")
            for atype, count in sorted(assets.items()):
                print(f"    {atype}: {count}")

    else:
        print(f"Unknown subcommand: {args[0]}")
        print("Available: list, create, active, info")


def cmd_config(args):
    """프로젝트 config 관리 (art_style, voice_id, voice_settings 등)."""
    import json

    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized. Run 'python -m db.cli init' first.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()

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
                print(f"ERROR: Project '{slug}' not found.")
                sys.exit(1)

    if not project:
        project = pm.get_active_project()
    if not project:
        print("No active project. Use --project <slug> to specify.")
        return

    args = remaining

    if not args or args[0] == "get":
        config = pm.get_config(project["id"])
        print(f"Config for: {project['name']} ({project['slug']})")
        if not config:
            print("  (empty)")
        else:
            print(json.dumps(config, ensure_ascii=False, indent=2))

    elif args[0] == "set":
        if len(args) < 3:
            print("Usage: config set <key> <value>")
            print("  Examples:")
            print("    config set art_style artstyle/styles/semoji.json")
            print("    config set voice_id 9Sj8ugvpK1DmcAXyvi3a")
            print('    config set voice_settings \'{"stability":1.0,"speed":1.1}\'')
            return
        key = args[1]
        value = args[2]
        # JSON 파싱 시도 (voice_settings 등 dict/list)
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass  # 문자열로 유지
        pm.update_config(project["id"], **{key: value})
        print(f"Set {key} = {value}")
        print(f"  Project: {project['name']}")

    elif args[0] == "set-json":
        if len(args) < 2:
            print("Usage: config set-json '<json>'")
            return
        try:
            config = json.loads(args[1])
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}")
            sys.exit(1)
        pm.set_config(project["id"], config)
        print(f"Config replaced for: {project['name']}")
        print(json.dumps(config, ensure_ascii=False, indent=2))

    elif args[0] == "delete":
        if len(args) < 2:
            print("Usage: config delete <key>")
            return
        key = args[1]
        config = pm.get_config(project["id"])
        if key in config:
            del config[key]
            pm.set_config(project["id"], config)
            print(f"Deleted key: {key}")
        else:
            print(f"Key '{key}' not found in config.")

    else:
        print(f"Unknown subcommand: {args[0]}")
        print("Available: get, set <key> <value>, set-json '<json>', delete <key>")


def cmd_version(args):
    """버전 관리."""
    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    project = pm.get_active_project()
    if not project:
        print("No active project.")
        return

    if not args or args[0] == "list":
        file_type = args[1] if len(args) > 1 else "scene_specs"
        versions = pm.get_versions(project["id"], file_type)
        if not versions:
            print(f"No versions for {file_type}.")
            return
        print(f"Versions of {file_type} ({project['name']}):")
        print(f"{'Ver':>4}  {'Size':>10}  {'Created':>20}  {'Description'}")
        print("-" * 70)
        for v in versions:
            size_kb = v["file_size"] / 1024 if v["file_size"] else 0
            print(f"  v{v['version']:03d}  {size_kb:>8.1f}KB  {v['created_at']:>20}  {v['description'] or ''}")

    elif args[0] == "rollback":
        if len(args) < 3:
            print("Usage: version rollback <file_type> <version_number>")
            return
        file_type = args[1]
        version = int(args[2])
        path = pm.rollback_version(project["id"], file_type, version)
        print(f"Rolled back {file_type} to v{version}: {path}")

    else:
        print("Available: list [file_type], rollback <file_type> <version>")


def cmd_assets(args):
    """에셋 조회."""
    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    project = pm.get_active_project()
    if not project:
        print("No active project.")
        return

    asset_type = None
    if "--type" in args:
        idx = args.index("--type")
        if idx + 1 < len(args):
            asset_type = args[idx + 1]

    assets = pm.get_assets(project["id"], asset_type=asset_type)
    counts = pm.get_asset_counts(project["id"])

    print(f"Assets for: {project['name']}")
    print(f"  Total: {sum(counts.values())} files")
    for atype, count in sorted(counts.items()):
        print(f"  {atype}: {count}")

    if asset_type:
        print(f"\n{asset_type} files:")
        for a in assets:
            size_kb = a["file_size"] / 1024 if a["file_size"] else 0
            scene_str = f"scene {a['scene_number']:03d}" if a["scene_number"] else "project"
            print(f"  [{scene_str}] {a['file_name']} ({size_kb:.1f}KB)")


def cmd_cleanup(args):
    """클린업."""
    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    from auto_agent.db.cleanup import CleanupManager

    pm = ProjectManager()
    project = pm.get_active_project()
    if not project:
        print("No active project.")
        return

    dry_run = "--execute" not in args
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project["id"], dry_run=dry_run)

    mode = "DRY RUN" if dry_run else "EXECUTED"
    print(f"Cleanup [{mode}] for: {project['name']}")

    if result["backups_found"]:
        print(f"\n  Backup files ({len(result['backups_found'])}):")
        for f in result["backups_found"]:
            print(f"    {'[DELETE]' if not dry_run else '[FOUND]'} {f}")

    if result["orphans_found"]:
        print(f"\n  Orphaned assets:")
        for category, files in result["orphans_found"].items():
            print(f"    {category}: {len(files)} files")
            for f in files[:5]:
                print(f"      {'[DELETE]' if not dry_run else '[FOUND]'} {f}")
            if len(files) > 5:
                print(f"      ... and {len(files) - 5} more")

    if result["temp_dirs_found"]:
        print(f"\n  Temp directories ({len(result['temp_dirs_found'])}):")
        for d in result["temp_dirs_found"]:
            print(f"    {'[DELETE]' if not dry_run else '[FOUND]'} {d}")

    if result["versions_cleaned"]:
        print(f"\n  Versions cleaned:")
        for ft, files in result["versions_cleaned"].items():
            print(f"    {ft}: {len(files)} old versions removed")

    total = (
        len(result["backups_found"])
        + sum(len(v) for v in result["orphans_found"].values())
        + len(result["temp_dirs_found"])
    )
    if total == 0:
        print("\n  Nothing to clean up.")
    elif dry_run:
        print(f"\n  Total: {total} items found. Use --execute to delete.")


def cmd_costs(args):
    """비용 요약."""
    from auto_agent.db.connection import db_exists
    if not db_exists():
        print("ERROR: DB not initialized.")
        sys.exit(1)

    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()

    # 전체 비용
    total = pm.get_cost_summary()
    print("Cost Summary (All Projects)")
    print(f"  Total runs: {total.get('total_runs', 0)}")
    print(f"  Input tokens: {total.get('total_tokens_in', 0):,}")
    print(f"  Output tokens: {total.get('total_tokens_out', 0):,}")
    print(f"  Total USD: ${total.get('total_usd', 0):.4f}")

    # 프로젝트별
    projects = pm.list_projects()
    if projects:
        print(f"\nBy Project:")
        for p in projects:
            cost = pm.get_cost_summary(p["id"])
            if cost.get("total_runs", 0) > 0:
                print(f"  {p['name']}: {cost['total_runs']} runs, ${cost.get('total_usd', 0):.4f}")


def cmd_dashboard(args):
    """웹 대시보드 실행."""
    port = 8080
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = int(args[idx + 1])

    print(f"Starting dashboard on http://localhost:{port}")
    try:
        import uvicorn
        uvicorn.run("dashboard.app:app", host="0.0.0.0", port=port, reload=True)
    except ImportError:
        print("ERROR: uvicorn not installed. Run: pip install fastapi uvicorn jinja2")
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
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[cmd](args[1:])


if __name__ == "__main__":
    main()
