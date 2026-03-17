"""
규칙 중앙 관리 CLI.

사용법:
    python -m auto_agent.scripts.rules_cli push_all          # 로컬 전체 → 중앙
    python -m auto_agent.scripts.rules_cli push <key>        # 단일 파일 push
    python -m auto_agent.scripts.rules_cli fetch             # 중앙 → 로컬 캐시
    python -m auto_agent.scripts.rules_cli list <key>        # 버전 히스토리
    python -m auto_agent.scripts.rules_cli rollback <key> <version>
    python -m auto_agent.scripts.rules_cli diff <key>        # 로컬 vs 중앙 비교
"""
import argparse
import sys
from pathlib import PurePosixPath

from auto_agent.rule_manager import RuleManager, DATA_DIR, _checksum, _normalize


def main():
    parser = argparse.ArgumentParser(description="Kairos Rule Store CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("push_all", help="로컬 규칙 전체를 중앙에 push")
    sub.add_parser("fetch", help="중앙 규칙을 로컬 캐시로 fetch")

    p_push = sub.add_parser("push", help="단일 규칙 파일 push")
    p_push.add_argument("key", help="규칙 key (예: prompts/single-call/creative-direction.md)")

    p_list = sub.add_parser("list", help="버전 히스토리 조회")
    p_list.add_argument("key", help="규칙 key")

    p_rb = sub.add_parser("rollback", help="특정 버전으로 롤백")
    p_rb.add_argument("key")
    p_rb.add_argument("version", type=int)

    p_diff = sub.add_parser("diff", help="로컬 vs 중앙 비교")
    p_diff.add_argument("key")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    rm = RuleManager()

    if args.command == "push_all":
        result = rm.push_all(updated_by="cli")
        print(f"Push 완료: {result['pushed']}개 업데이트, "
              f"{result['unchanged']}개 변경 없음, "
              f"{result['missing']}개 파일 없음")

    elif args.command == "fetch":
        changed = rm.fetch_all()
        print(f"Fetch 완료: {changed}개 파일 갱신")

    elif args.command == "push":
        local_path = DATA_DIR / PurePosixPath(args.key)
        if not local_path.exists():
            print(f"ERROR: 파일 없음 — {local_path}")
            sys.exit(1)
        content = local_path.read_text(encoding="utf-8")
        result = rm.push(args.key, content, updated_by="cli")
        print(f"{result['status']}: {args.key}")

    elif args.command == "list":
        versions = rm.list_versions(args.key)
        if not versions:
            print("버전 히스토리 없음")
            return
        for v in versions:
            print(f"  v{v['version']}  {v['created_at'][:19]}  "
                  f"{v['created_by']:<10}  {v.get('description', '')}")

    elif args.command == "rollback":
        result = rm.rollback(args.key, args.version)
        print(f"롤백 완료: {args.key} → v{args.version}")

    elif args.command == "diff":
        local_path = DATA_DIR / PurePosixPath(args.key)
        if not local_path.exists():
            print(f"로컬 파일 없음: {local_path}")
            sys.exit(1)
        local_content = _normalize(local_path.read_text(encoding="utf-8"))
        try:
            remote_content = rm.load(args.key)
        except FileNotFoundError:
            print("중앙에 등록되지 않은 규칙")
            sys.exit(1)
        if _checksum(local_content) == _checksum(remote_content):
            print("동일 (변경 없음)")
        else:
            local_lines = local_content.splitlines()
            remote_lines = remote_content.splitlines()
            print(f"차이 있음: 로컬 {len(local_lines)}줄 vs 중앙 {len(remote_lines)}줄")


if __name__ == "__main__":
    main()
