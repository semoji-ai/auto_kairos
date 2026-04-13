#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from auto_agent.modules.research_entity_hub import write_entity_hub_audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit research vault slugs and generate entity-hub alias map.")
    parser.add_argument("--research-root", required=True, help="Path to 02-research root")
    args = parser.parse_args()

    research_root = Path(args.research_root).expanduser().resolve()
    outputs = write_entity_hub_audit(research_root)
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
