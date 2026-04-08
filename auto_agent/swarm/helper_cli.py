"""Swarm workspace CLI helper.

writer agent가 Bash 도구로 호출할 수 있는 안전한 helper.
LLM이 Python 코드를 작성하지 않아도 race-free하게 workspace를 수정 가능.

사용법 (Bash 한 줄):

    python3 -m auto_agent.swarm.helper_cli add-character \\
        --workspace /path/to/workspace \\
        --id pemberton \\
        --name-ko "존 펨버튼" \\
        --name-en "John Pemberton" \\
        --role "약사, 코카콜라 발명자" \\
        --first-chapter 1 \\
        --discovered-by writer

이렇게 하면 prompt에 `{workspace_path}` 같은 placeholder를 박을 필요 없음 —
writer.py가 빌드하는 prompt에 실제 워크스페이스 경로를 박아주기만 하면 됨.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .workspace import SwarmWorkspace


def cmd_add_character(args: argparse.Namespace) -> int:
    ws = SwarmWorkspace(Path(args.workspace))
    character = {
        "id": args.id,
        "name_ko": args.name_ko,
        "name_en": args.name_en or "",
        "role": args.role or "",
        "is_real_person": not args.fictional,
        "first_mention_chapter": args.first_chapter,
        "discovered_by": args.discovered_by or "writer",
        "needs_research": args.needs_research,
    }
    added = ws.append_character(character)
    if added:
        ws.emit_event(
            args.discovered_by or "writer",
            "character_appended",
            level="info",
            char_id=args.id,
            name_ko=args.name_ko,
        )
        print(f"OK: appended {args.id} ({args.name_ko})")
        return 0
    else:
        print(f"SKIP: {args.id} already exists in character_register.json")
        return 0  # exit 0 — idempotent


def cmd_add_query(args: argparse.Namespace) -> int:
    """research_queue.jsonl에 새 query append. writer가 발견한 fact 부족 query."""
    ws = SwarmWorkspace(Path(args.workspace))
    record = {
        "id": args.id,
        "target": args.target,
        "question": args.question,
        "priority": args.priority,
        "requested_by": args.requested_by or "writer",
    }
    if args.angle:
        record["angle"] = args.angle
    if args.target_id:
        record["target_id"] = args.target_id
    ws.append_jsonl("research_queue.jsonl", record)
    ws.emit_event(
        args.requested_by or "writer",
        "query_appended",
        level="info",
        q_id=args.id,
        target=args.target,
    )
    print(f"OK: appended query {args.id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Swarm workspace helper — race-free file ops for agents",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add-character
    pc = sub.add_parser("add-character", help="character_register.json에 인물 atomic append")
    pc.add_argument("--workspace", required=True)
    pc.add_argument("--id", required=True)
    pc.add_argument("--name-ko", required=True)
    pc.add_argument("--name-en", default="")
    pc.add_argument("--role", default="")
    pc.add_argument("--first-chapter", type=int, default=1)
    pc.add_argument("--discovered-by", default="writer")
    pc.add_argument("--needs-research", action="store_true")
    pc.add_argument("--fictional", action="store_true", help="실존 인물 아니면 추가")
    pc.set_defaults(func=cmd_add_character)

    # add-query
    pq = sub.add_parser("add-query", help="research_queue.jsonl에 query append")
    pq.add_argument("--workspace", required=True)
    pq.add_argument("--id", required=True)
    pq.add_argument("--target", required=True)
    pq.add_argument("--question", required=True)
    pq.add_argument("--priority", default="high")
    pq.add_argument("--requested-by", default="writer")
    pq.add_argument("--angle", default="")
    pq.add_argument("--target-id", default="")
    pq.set_defaults(func=cmd_add_query)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
