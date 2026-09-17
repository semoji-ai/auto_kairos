"""Summarize recorded CLI attempts without model calls or project mutations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize(project: Path) -> dict:
    groups = {}
    invalid = []
    for path in sorted((project / ".execution").glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            key = f"{record['provider']}/{record['model']}/{record['profile']}"
            usage = record.get("usage", {})
            row = groups.setdefault(key, {"calls": 0, "failed_calls": 0, "input_tokens": 0,
                                          "output_tokens": 0, "cached_input_tokens": 0,
                                          "prompt_chars": 0, "duration_sec": 0.0})
            row["calls"] += 1
            row["failed_calls"] += int(record["returncode"] != 0)
            row["input_tokens"] += usage.get("tokens_in", 0)
            row["output_tokens"] += usage.get("tokens_out", 0)
            row["cached_input_tokens"] += usage.get("cache_read_tokens", 0)
            row["prompt_chars"] += record.get("prompt_chars", 0)
            row["duration_sec"] += record.get("duration_sec", 0)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            invalid.append(str(path))
    return {"project": str(project), "groups": groups, "invalid_records": invalid,
            "note": "Includes failed attempts. Duration sums worker time, not parallel wall time. "
                    "Token counts are provider-reported; missing usage is not proof of zero cost."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.project), ensure_ascii=False, indent=2))
