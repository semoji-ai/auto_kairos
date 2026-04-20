"""Research vault entity-hub audit and canonical slug resolution."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import shutil
from pathlib import Path
from typing import Optional


STANDARD_WIKI_FILES = {
    "overview.md",
    "claims.md",
    "entities.md",
    "timeline.md",
    "questions.md",
    "images.md",
    "index.md",
    "log.md",
}

SECTION_KEYWORDS = [
    "역사",
    "효능",
    "제조",
    "성분",
    "원리",
    "화학",
    "시장",
    "논란",
    "세금",
    "브랜드",
    "전략",
    "비교",
    "전망",
    "영향",
    "사용법",
    "부작용",
    "특징",
    "구조",
    "사례",
    "문제",
    "위험",
]


def _looks_like_test_slug(slug: str) -> bool:
    slug_l = _normalize_text(slug).lower()
    return "test" in slug_l or slug_l.endswith("_v2") or slug_l.endswith("_v3") or slug_l.endswith("_v4")


@dataclass(frozen=True)
class AliasResolution:
    entity_slug: str
    section_slug: str = ""
    source_slug: str = ""
    canonical_slug: str = ""


def _normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").strip()


def _slug_variants(slug: str) -> list[str]:
    slug = _normalize_text(slug)
    if not slug:
        return []
    alt = slug.replace("-", "_") if "-" in slug else slug.replace("_", "-")
    variants = []
    for value in [slug, alt]:
        if value and value not in variants:
            variants.append(value)
    return variants


def _humanize_slug(slug: str) -> str:
    return re.sub(r"[-_]+", " ", _normalize_text(slug)).strip()


def _read_overview_signals(entity_dir: Path) -> tuple[str, str]:
    overview = entity_dir / "overview.md"
    if not overview.exists():
        return "", ""
    text = overview.read_text(encoding="utf-8")

    topic = ""
    heading = ""

    topic_match = re.search(r'^topic:\s*"?(.*?)"?\s*$', text, re.MULTILINE)
    if topic_match:
        topic = _normalize_text(topic_match.group(1))

    heading_match = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
    if heading_match:
        heading = _normalize_text(heading_match.group(1))

    return topic, heading


def infer_entity_section_from_text(*candidates: str) -> tuple[str, str]:
    for raw in candidates:
        text = _normalize_text(raw)
        if not text:
            continue
        text = text.replace("—", " ").replace("–", " ")
        text = re.sub(r"\([^)]*\)", "", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\b(overview|index|summary)\b", "", text, flags=re.IGNORECASE).strip()

        for section in SECTION_KEYWORDS:
            patterns = [
                rf"^(?P<entity>.+?)(?:의|\s+의)?\s*(?P<section>{re.escape(section)})(?:$|\s|와|과|및|,)",
                rf"^(?P<entity>.+?)\s+(?P<section>{re.escape(section)})(?:$|\s|와|과|및|,)",
            ]
            for pattern in patterns:
                m = re.match(pattern, text)
                if not m:
                    continue
                entity = m.group("entity").strip(" -_")
                if entity:
                    entity = re.sub(r"\s+", "_", entity)
                    return entity, section
    return "", ""


def infer_entity_section_from_dir(entity_dir: Path) -> tuple[str, str]:
    topic, heading = _read_overview_signals(entity_dir)
    section_pages = sorted(
        p.stem for p in entity_dir.glob("*.md")
        if p.name not in STANDARD_WIKI_FILES
    )

    entity_slug, section_slug = infer_entity_section_from_text(
        heading,
        topic,
        *section_pages,
        _humanize_slug(entity_dir.name),
    )

    if not entity_slug:
        if section_pages:
            entity_slug = _normalize_text(entity_dir.name)
            section_slug = section_pages[0]
        else:
            entity_slug = _normalize_text(entity_dir.name)

    if entity_slug == _normalize_text(entity_dir.name) and section_pages and not section_slug:
        section_slug = section_pages[0]

    return entity_slug, section_slug


def _load_alias_map(research_root: Path) -> dict[str, AliasResolution]:
    alias_file = research_root / "manifests" / "_entity_hub" / "entity_aliases.json"
    if not alias_file.exists():
        return {}
    data = json.loads(alias_file.read_text(encoding="utf-8"))
    aliases: dict[str, AliasResolution] = {}
    for alias_slug, payload in data.items():
        aliases[_normalize_text(alias_slug)] = AliasResolution(
            entity_slug=_normalize_text(payload.get("entity_slug", "")),
            section_slug=_normalize_text(payload.get("section_slug", "")),
            source_slug=_normalize_text(payload.get("source_slug", alias_slug)),
            canonical_slug=_normalize_text(payload.get("canonical_slug", payload.get("entity_slug", ""))),
        )
    return aliases


def resolve_entity_alias(research_root: Path, slug: str) -> Optional[AliasResolution]:
    aliases = _load_alias_map(research_root)
    for candidate in _slug_variants(slug):
        hit = aliases.get(_normalize_text(candidate))
        if hit:
            return hit
    return None


def resolve_existing_entity_slug(research_root: Path, slug: str) -> str:
    alias = resolve_entity_alias(research_root, slug)
    if alias and alias.entity_slug:
        return alias.entity_slug
    for candidate in _slug_variants(slug):
        if (research_root / "wiki" / candidate).exists():
            return candidate
    return _normalize_text(slug)


def resolve_topic_to_entity_section(
    research_root: Path,
    topic_slug: str,
    entity_slug: str = "",
    section_slug: str = "",
) -> AliasResolution:
    if entity_slug:
        canonical = resolve_existing_entity_slug(research_root, entity_slug)
        return AliasResolution(
            entity_slug=canonical,
            section_slug=_normalize_text(section_slug),
            source_slug=_normalize_text(entity_slug),
            canonical_slug=canonical,
        )

    alias = resolve_entity_alias(research_root, topic_slug)
    if alias:
        return alias

    resolved = resolve_existing_entity_slug(research_root, topic_slug)
    entity, inferred_section = infer_entity_section_from_text(_humanize_slug(topic_slug))
    return AliasResolution(
        entity_slug=entity or resolved,
        section_slug=inferred_section or _normalize_text(section_slug),
        source_slug=_normalize_text(topic_slug),
        canonical_slug=entity or resolved,
    )


def build_entity_hub_audit(research_root: Path) -> dict:
    wiki_root = research_root / "wiki"
    manifests_root = research_root / "manifests"
    raw_root = research_root / "raw"

    wiki_slugs = {p.name for p in wiki_root.iterdir() if p.is_dir()} if wiki_root.exists() else set()
    manifest_slugs = {
        p.name for p in manifests_root.iterdir() if p.is_dir() and not p.name.startswith("_")
    } if manifests_root.exists() else set()
    raw_slugs = {p.name for p in raw_root.iterdir() if p.is_dir()} if raw_root.exists() else set()

    slug_names = wiki_slugs | manifest_slugs | raw_slugs

    records = []
    groups: dict[str, list[dict]] = defaultdict(list)

    for slug in sorted(slug_names):
        wiki_dir = wiki_root / slug
        manifest_dir = manifests_root / slug
        raw_dir = raw_root / slug
        entity_slug, section_slug = infer_entity_section_from_dir(wiki_dir) if wiki_dir.exists() else infer_entity_section_from_text(_humanize_slug(slug))
        section_pages = []
        wiki_files = []
        manifest_files = []
        if wiki_dir.exists():
            wiki_files = sorted(p.name for p in wiki_dir.glob("*.md"))
            section_pages = sorted(p.stem for p in wiki_dir.glob("*.md") if p.name not in STANDARD_WIKI_FILES)
        if manifest_dir.exists():
            manifest_files = sorted(p.name for p in manifest_dir.iterdir() if p.is_file())

        record = {
            "slug": slug,
            "entity_slug": entity_slug or slug,
            "section_slug": section_slug,
            "wiki_exists": wiki_dir.exists(),
            "manifest_exists": manifest_dir.exists(),
            "raw_exists": raw_dir.exists(),
            "wiki_files": wiki_files,
            "manifest_files": manifest_files,
            "section_pages": section_pages,
        }
        records.append(record)
        groups[record["entity_slug"]].append(record)

    entity_groups = []
    alias_map = {}
    duplicate_groups = []

    for entity_slug, items in sorted(groups.items()):
        canonical_slug = ""
        for item in items:
            if item["slug"] == entity_slug:
                canonical_slug = item["slug"]
                break
        if not canonical_slug:
            if items and all(_looks_like_test_slug(item["slug"]) for item in items):
                canonical_slug = entity_slug
            else:
                canonical_slug = sorted(items, key=lambda r: (len(r["slug"]), r["slug"]))[0]["slug"]

        for item in items:
            if item["slug"] == canonical_slug:
                continue
            alias_map[item["slug"]] = {
                "entity_slug": entity_slug,
                "section_slug": item.get("section_slug", ""),
                "source_slug": item["slug"],
                "canonical_slug": canonical_slug,
            }

        group_info = {
            "entity_slug": entity_slug,
            "canonical_slug": canonical_slug,
            "records": items,
            "duplicate_count": max(len(items) - 1, 0),
        }
        entity_groups.append(group_info)
        if len(items) > 1:
            duplicate_groups.append(group_info)

    return {
        "research_root": str(research_root),
        "wiki_dir_count": sum(1 for p in wiki_root.iterdir() if p.is_dir()) if wiki_root.exists() else 0,
        "manifest_dir_count": sum(1 for p in manifests_root.iterdir() if p.is_dir() and not p.name.startswith("_")) if manifests_root.exists() else 0,
        "raw_dir_count": sum(1 for p in raw_root.iterdir() if p.is_dir()) if raw_root.exists() else 0,
        "records": records,
        "entity_groups": entity_groups,
        "duplicate_groups": duplicate_groups,
        "alias_map": alias_map,
    }


def write_entity_hub_audit(research_root: Path) -> dict[str, Path]:
    audit = build_entity_hub_audit(research_root)
    out_dir = research_root / "manifests" / "_entity_hub"
    out_dir.mkdir(parents=True, exist_ok=True)

    audit_json = out_dir / "entity_hub_audit.json"
    alias_json = out_dir / "entity_aliases.json"
    report_md = out_dir / "entity_hub_audit.md"

    audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    alias_json.write_text(json.dumps(audit["alias_map"], ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Research Entity Hub Audit",
        "",
        f"- research_root: `{research_root}`",
        f"- wiki_dirs: {audit['wiki_dir_count']}",
        f"- manifest_dirs: {audit['manifest_dir_count']}",
        f"- raw_dirs: {audit['raw_dir_count']}",
        f"- duplicate_groups: {len(audit['duplicate_groups'])}",
        "",
        "## Duplicate Groups",
        "",
    ]

    if not audit["duplicate_groups"]:
        lines.append("- none")
    else:
        for group in audit["duplicate_groups"]:
            lines.append(f"### {group['entity_slug']}")
            lines.append(f"- canonical_slug: `{group['canonical_slug']}`")
            for item in group["records"]:
                sec = item.get("section_slug", "")
                lines.append(
                    f"- `{item['slug']}`"
                    f" | section=`{sec}`"
                    f" | wiki={item['wiki_exists']}"
                    f" | manifests={item['manifest_exists']}"
                    f" | raw={item['raw_exists']}"
                )
            lines.append("")

    report_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "audit_json": audit_json,
        "alias_json": alias_json,
        "report_md": report_md,
    }

def _merge_jsonl(src: Path, dst: Path):
    seen = set()
    merged = []
    for path in [dst, src]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw in seen:
                continue
            seen.add(raw)
            merged.append(raw)
    if merged:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text("\n".join(merged) + "\n", encoding="utf-8")


def _merge_latest_run(src: Path, dst: Path):
    values = []
    for path in [dst, src]:
        if path.exists():
            values.append(path.read_text(encoding="utf-8").strip())
    if values:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(sorted(v for v in values if v)[-1] + "\n", encoding="utf-8")


def _merge_markdown(src: Path, dst: Path):
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    src_text = src.read_text(encoding="utf-8")
    dst_text = dst.read_text(encoding="utf-8")
    if src_text == dst_text:
        return
    if len(src_text) > len(dst_text):
        backup = dst.with_name(dst.stem + ".pre_merge" + dst.suffix)
        if not backup.exists():
            backup.write_text(dst_text, encoding="utf-8")
        dst.write_text(src_text, encoding="utf-8")


def _copy_raw_tree(src: Path, dst: Path, alias_slug: str):
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dst / child.name
        if target.exists():
            target = dst / f"{child.name}__from_{alias_slug}"
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def migrate_entity_hubs(research_root: Path, dry_run: bool = False, include_test_like: bool = False) -> dict:
    audit = build_entity_hub_audit(research_root)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_root = research_root / "manifests" / "_entity_hub" / "backups" / timestamp

    migrated = []
    skipped = []

    for alias_slug, payload in audit["alias_map"].items():
        canonical_slug = payload.get("canonical_slug") or payload.get("entity_slug")
        section_slug = payload.get("section_slug", "")
        if not canonical_slug or canonical_slug == alias_slug:
            skipped.append({"alias_slug": alias_slug, "reason": "no_canonical"})
            continue
        if not include_test_like and (_looks_like_test_slug(alias_slug) or _looks_like_test_slug(canonical_slug)):
            skipped.append({"alias_slug": alias_slug, "reason": "test_like_slug"})
            continue

        wiki_src = research_root / "wiki" / alias_slug
        wiki_dst = research_root / "wiki" / canonical_slug
        manifest_src = research_root / "manifests" / alias_slug
        manifest_dst = research_root / "manifests" / canonical_slug
        raw_src = research_root / "raw" / alias_slug
        raw_dst = research_root / "raw" / canonical_slug

        if dry_run:
            migrated.append({
                "alias_slug": alias_slug,
                "canonical_slug": canonical_slug,
                "section_slug": section_slug,
                "dry_run": True,
            })
            continue

        if wiki_src.exists():
            wiki_dst.mkdir(parents=True, exist_ok=True)
            for src_file in wiki_src.glob("*.md"):
                target_name = src_file.name
                if src_file.name == "overview.md" and section_slug:
                    target_name = f"{section_slug}.md"
                _merge_markdown(src_file, wiki_dst / target_name)

        if manifest_src.exists():
            manifest_dst.mkdir(parents=True, exist_ok=True)
            for src_file in manifest_src.iterdir():
                if not src_file.is_file():
                    continue
                dst_file = manifest_dst / src_file.name
                if src_file.name.endswith(".jsonl"):
                    _merge_jsonl(src_file, dst_file)
                elif src_file.name == "latest_run.txt":
                    _merge_latest_run(src_file, dst_file)
                elif not dst_file.exists():
                    shutil.copy2(src_file, dst_file)

        if raw_src.exists():
            _copy_raw_tree(raw_src, raw_dst, alias_slug)

        for src_dir, kind in [(wiki_src, "wiki"), (manifest_src, "manifests"), (raw_src, "raw")]:
            if not src_dir.exists():
                continue
            dest = backup_root / kind / alias_slug
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(src_dir), str(dest))

        migrated.append({
            "alias_slug": alias_slug,
            "canonical_slug": canonical_slug,
            "section_slug": section_slug,
        })

    outputs = write_entity_hub_audit(research_root)
    migration_report = research_root / "manifests" / "_entity_hub" / "migration_report.json"
    migration_report.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "backup_root": str(backup_root),
                "migrated": migrated,
                "skipped": skipped,
                "audit_files": {k: str(v) for k, v in outputs.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "backup_root": backup_root,
        "migration_report": migration_report,
        **outputs,
    }
