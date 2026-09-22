"""Provider-neutral sentence inventory and lossless scene-split gate.

Markdown headings, horizontal rules and HTML production comments are metadata.
Everything else remains spoken text; ambiguous annotations fail closed rather
than being silently discarded. Scene grouping remains the director's decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


# Chapter markers and production blocks are shared by inventory and runner routing.
CHAPTER_HEADING = re.compile(r"^\s*#{1,6}\s*(?:Ch(?:apter)?\s*|챕터\s*)(\d+)(?=[.\s:：]|$)", re.I)


def inventory(text: str) -> dict:
    rows, block = [], []
    chapter = 0

    def flush():
        raw = "\n".join(block)
        comments = re.findall(r"<!--(.*?)-->", raw, re.S)
        cast, captions, notes = [], [], []
        for comment in comments:
            key, _, value = comment.strip().partition(":")
            if key.strip() == "chars":
                cast.extend(c.strip() for c in value.split(",") if c.strip())
            elif key.strip() == "caption":
                captions.append(value.strip())
            else:
                notes.append(comment.strip())
        body = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        if "<!--" in body or "-->" in body:
            raise ValueError("닫히지 않은 제작 주석")
        body = re.sub(r"\s+", " ", body.replace("**", "")).strip()
        caption_anchor = len(rows) + 1
        # Closing quotes belong to the sentence. Decimal periods have no space.
        for part in re.findall(r'.+?(?:[.!?。！？][”’"\'」』)]*(?=\s|$)|$)', body):
            sentence = part.strip()
            if sentence:
                rows.append({"id": len(rows) + 1, "chapter": chapter, "text": sentence,
                             "characters": list(dict.fromkeys(cast)), "captions": captions[:],
                             "productionNotes": notes[:], "captionAnchor": caption_anchor})
        block.clear()

    # Do not interpret headings or separators inside multiline comments.
    in_comment = False
    for line in text.splitlines():
        if not in_comment and (re.match(r"^\s*#{1,6}\s", line) or re.fullmatch(r"\s*[-*_]{3,}\s*", line)):
            flush()
            match = CHAPTER_HEADING.match(line)
            if match:
                chapter = int(match[1])
            continue
        block.append(line)
        if "<!--" in line:
            in_comment = True
        if "-->" in line:
            in_comment = False
    flush()
    if not rows:
        raise ValueError("원고 본문이 비어 있습니다")
    return {"source_sha256": hashlib.sha256(text.encode()).hexdigest(), "sentences": rows}


def validate(ledger: dict, manuscript: str, specs: dict) -> dict:
    errors = []
    if ledger["source_sha256"] != hashlib.sha256(manuscript.encode()).hexdigest():
        errors.append("원고가 문장 목록 생성 후 변경됨: prepare 재실행 필요")
    fresh = inventory(manuscript)
    if ledger != fresh:
        errors.append("문장 목록이 현재 원고와 일치하지 않음: prepare 재실행 필요")
    scene_list = specs.get("scenes") if isinstance(specs, dict) else None
    if not isinstance(scene_list, list) or not scene_list or any(
        not isinstance(s, dict) or not isinstance(s.get("narration"), str)
        or not normalized(s["narration"]) or type(s.get("chapter")) is not int
        for s in scene_list
    ):
        return {"ok": False, "errors": errors + ["빈 씬 또는 잘못된 내레이션/챕터"],
                "sentence_count": len(fresh["sentences"]), "scene_count": len(scene_list or [])}
    expected = normalized("".join(r["text"] for r in fresh["sentences"]))
    actual = normalized("".join(s.get("narration") or "" for s in specs["scenes"]))
    if expected != actual:
        pos = next((i for i, (a, b) in enumerate(zip(expected, actual)) if a != b), min(len(expected), len(actual)))
        errors.append({"kind": "coverage_mismatch", "offset": pos,
                       "expected": expected[max(0, pos-25):pos+65],
                       "actual": actual[max(0, pos-25):pos+65],
                       "expected_length": len(expected), "actual_length": len(actual)})
    # A chapter change may not be hidden by globally matching narration.
    expected_chapters = []
    for row in fresh["sentences"]:
        expected_chapters.extend([row["chapter"]] * len(normalized(row["text"])))
    actual_chapters = []
    for scene in specs["scenes"]:
        actual_chapters.extend([scene.get("chapter")] * len(normalized(scene.get("narration") or "")))
    if expected_chapters != actual_chapters:
        errors.append("챕터 경계/소속 불일치")
    return {"ok": not errors, "errors": errors, "sentence_count": len(ledger["sentences"]), "scene_count": len(specs["scenes"])}


def allocate(rows: list[dict], decisions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Accept a complete ordered partition of sentence IDs or code-point spans.

    sourceSpans offsets are Python string indices in inventory text, [start, end).
    A scene uses either sourceSentences or sourceSpans, never both.
    """
    if not rows or not isinstance(decisions, list) or not decisions:
        raise ValueError("빈 문장 목록 또는 씬 배분")
    by_id = {r["id"]: r for r in rows}
    skeleton, directions = [], []
    row_index, offset = 0, 0
    for i, decision in enumerate(decisions, 1):
        if not isinstance(decision, dict):
            raise ValueError("씬 배분은 객체여야 합니다")
        if ("sourceSentences" in decision) == ("sourceSpans" in decision):
            raise ValueError("sourceSentences 또는 sourceSpans 중 하나 필요")
        if decision.get("cuts"):
            raise ValueError("하위 cuts 대신 각 컷을 독립 flat scene으로 배분해야 합니다")
        spans = decision.get("sourceSpans")
        if "sourceSentences" in decision:
            ids = decision["sourceSentences"]
            if not isinstance(ids, list) or any(type(n) is not int or n not in by_id for n in ids):
                raise ValueError("잘못된 sourceSentences")
            spans = [{"id": n, "start": 0, "end": len(by_id[n]["text"])} for n in ids]
        if not isinstance(spans, list) or not spans:
            raise ValueError("빈 씬 또는 잘못된 sourceSpans")
        group, parts, anchored_captions = [], [], []
        for span in spans:
            if not isinstance(span, dict) or any(type(span.get(k)) is not int for k in ("id", "start", "end")):
                raise ValueError("문자 구간은 id/start/end 정수가 필요합니다")
            if row_index >= len(rows):
                raise ValueError("문장 배분 중복·추가")
            row = rows[row_index]
            start, end = span["start"], span["end"]
            if span["id"] != row["id"] or start != offset or not start < end <= len(row["text"]):
                raise ValueError("문장 배분 누락·중복·재정렬 또는 잘못된 문자 구간")
            if start == 0 and row["id"] == row.get("captionAnchor"):
                anchored_captions.extend(row.get("captions", []))
            parts.append(row["text"][start:end])
            group.append(row)
            offset = end
            if end == len(row["text"]):
                row_index += 1
                offset = 0
        if len({r["chapter"] for r in group}) != 1 or not normalized("".join(parts)):
            raise ValueError("빈 씬 또는 챕터를 넘는 병합")
        skeleton.append({"sceneNumber": i, "chapter": group[0]["chapter"],
                         "narration": " ".join(parts), "sourceSpans": spans,
                         "sourceSentences": list(dict.fromkeys(r["id"] for r in group)),
                         "characters": list(dict.fromkeys(c for r in group for c in r.get("characters", []))),
                         "_captions": list(dict.fromkeys(anchored_captions)),
                         "productionNotes": list(dict.fromkeys(c for r in group for c in r.get("productionNotes", [])))})
        directions.append({**decision, "sceneNumber": i})
    if row_index != len(rows) or offset:
        raise ValueError("문장 배분 누락: 원고 끝까지 포함해야 합니다")
    return skeleton, directions


def prepare(root: Path) -> dict:
    ledger = inventory((root / "final_manuscript.md").read_text(encoding="utf-8"))
    (root / "sentence_inventory.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    return ledger


def check_project(root: Path) -> dict:
    """Read-only with respect to the manuscript/scenes; always save a diagnostic."""
    try:
        result = validate(json.loads((root / "sentence_inventory.json").read_text(encoding="utf-8")),
                          (root / "final_manuscript.md").read_text(encoding="utf-8"),
                          json.loads((root / "scene_specs.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    (root / "scene_coverage_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "validate"])
    parser.add_argument("--project-dir", type=Path, default=os.environ.get("PROJECT_DIR"))
    args = parser.parse_args()
    if not args.project_dir:
        parser.error("--project-dir 또는 PROJECT_DIR 필요")
    root = Path(args.project_dir)
    path = root / ("sentence_inventory.json" if args.mode == "prepare" else "scene_coverage_report.json")
    if args.mode == "prepare":
        try:
            result = prepare(root)
        except (OSError, ValueError) as exc:
            print(str(exc))
            return 1
    else:
        result = check_project(root)
    print(json.dumps({"artifact": str(path), "ok": result.get("ok", True)}, ensure_ascii=False))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
