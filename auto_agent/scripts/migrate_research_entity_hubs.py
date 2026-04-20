#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from auto_agent.modules.research_entity_hub import migrate_entity_hubs


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge duplicate research vault slugs into canonical entity hubs.")
    parser.add_argument("--research-root", required=True, help="Path to 02-research root")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--include-test-like", action="store_true", help="Also migrate test-like duplicate slugs")
    args = parser.parse_args()

    research_root = Path(args.research_root).expanduser().resolve()
    outputs = migrate_entity_hubs(
        research_root,
        dry_run=args.dry_run,
        include_test_like=args.include_test_like,
    )
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
