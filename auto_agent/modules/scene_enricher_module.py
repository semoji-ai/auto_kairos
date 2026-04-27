"""
scene_enricher_module — 씬별 시각자료 자동·반자동 보강 (세모지/세모지3D 한정).

워크플로:
1. scene_specs.json 의 asset_strategy 라벨된 씬 추출
2. video → video_search 워터폴 / search_image → image_search 워터폴
3. 적합도 임계 통과 시 자동 채택 → scene_specs 주입
4. 미달 시 enrichment_queue.json에 후보 목록 보관 (사람이 대시보드에서 검토)

산출:
- scene_specs.json (자동 채택된 항목 patched)
- enrichment_queue.json (사람 검토 대기열)
- enrichment_summary.json (통계)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_agent.tools import video_search

logger = logging.getLogger(__name__)


# 자동 채택 임계값 — 미달 시 사람 검토 대기열로 이동
VIDEO_AUTO_THRESHOLD = 5.0      # video_search _relevance_score
IMAGE_AUTO_THRESHOLD = 55.0     # image_search resolution+aspect+license 점수 (만점 60)


def _scene_query_for_video(scene: dict[str, Any]) -> tuple[str, list[str]]:
    """video 씬의 쿼리·키워드 결정 — videoAsset.query/keywords 우선, 없으면 자동 추출."""
    va = scene.get("videoAsset") or {}
    if va.get("query"):
        return va["query"], list(va.get("keywords") or [])
    q, kw = video_search._scene_to_query(scene)
    return q, sorted(list(kw))


def _scene_query_for_image(scene: dict[str, Any]) -> str:
    """search_image 씬의 쿼리 결정 — imageAsset.query 우선, 없으면 headline."""
    ia = scene.get("imageAsset") or {}
    if ia.get("query"):
        return ia["query"]
    head = (scene.get("headline") or "").strip().replace("{{", "").replace("}}", "")
    if head:
        return head
    narr = (scene.get("narration") or "").strip()
    return narr[:80]


def _enrich_video_scene(scene: dict[str, Any], scene_index: int,
                       limit: int = 5) -> dict[str, Any]:
    query, keywords = _scene_query_for_video(scene)
    if not query:
        return {"scene_index": scene_index, "status": "skipped", "reason": "쿼리 추출 실패"}
    try:
        candidates = video_search.search(
            query, limit=limit,
            max_duration=1800, min_duration=30,
            keywords=set(keywords) if keywords else None,
        )
    except Exception as e:
        logger.warning(f"video search 실패 idx={scene_index}: {e}")
        return {"scene_index": scene_index, "status": "error", "reason": str(e)}

    if not candidates:
        return {"scene_index": scene_index, "status": "no_candidates",
                "query": query, "asset_kind": "video"}

    top = candidates[0]
    top_score = top.get("_relevance_score") or 0
    auto = top_score >= VIDEO_AUTO_THRESHOLD

    entry = {
        "scene_index": scene_index,
        "asset_kind": "video",
        "query": query,
        "keywords": keywords,
        "top_score": top_score,
        "auto_selected": auto,
        "candidates": [
            {
                "video_id": c.get("video_id"),
                "title": c.get("title"),
                "channel": c.get("channel"),
                "duration_sec": c.get("duration_sec"),
                "view_count": c.get("view_count"),
                "url": c.get("url"),
                "thumbnail": c.get("thumbnail"),
                "license": c.get("license"),
                "score": c.get("_relevance_score"),
                "description": c.get("description_snippet"),
            }
            for c in candidates
        ],
    }
    if auto:
        # scene_specs에 selected 정보 주입 (segment는 후속 analyze에서 채움)
        va = scene.get("videoAsset") or {}
        va["query"] = query
        va["keywords"] = keywords
        va["selected_video_id"] = top.get("video_id")
        va["selected_url"] = top.get("url")
        va["selected_title"] = top.get("title")
        va["selected_channel"] = top.get("channel")
        va["license"] = top.get("license")
        va["selection_status"] = "auto"
        va["selection_score"] = top_score
        scene["videoAsset"] = va
    else:
        entry["status"] = "needs_review"
    return entry


def _enrich_image_scene(scene: dict[str, Any], scene_index: int,
                       limit: int = 5) -> dict[str, Any]:
    query = _scene_query_for_image(scene)
    if not query:
        return {"scene_index": scene_index, "status": "skipped", "reason": "쿼리 추출 실패"}
    # 다운로드 없이 메타데이터·URL만 — search_waterfall은 다운로드까지 시도해
    # 사이트 hotlink 차단 시 0건이 됨. 대시보드 미리보기는 thumbnail_url만으로 충분.
    try:
        from auto_agent.tools.image_search import (
            ImageSearcher, WATERMARK_DOMAINS, rank_images,
        )
        searcher = ImageSearcher()
        all_candidates = []
        try:
            all_candidates.extend(searcher.search_wikimedia(query, limit * 3).images)
        except Exception:
            pass
        try:
            all_candidates.extend(searcher.search_serper(query, limit * 3).images)
        except Exception:
            pass
        try:
            all_candidates.extend(searcher.search_pixabay(query, limit * 2).images)
        except Exception:
            pass
        if not all_candidates:
            return {"scene_index": scene_index, "status": "no_candidates",
                    "query": query, "asset_kind": "search_image"}
        filtered = [
            img for img in all_candidates
            if not any(wd in img.source_domain for wd in WATERMARK_DOMAINS)
        ] or all_candidates
        results = rank_images(filtered, query, preferred_aspect="16:9")[:limit]
    except Exception as e:
        logger.warning(f"image search 실패 idx={scene_index}: {e}")
        return {"scene_index": scene_index, "status": "error", "reason": str(e)}

    if not results:
        return {"scene_index": scene_index, "status": "no_candidates",
                "query": query, "asset_kind": "search_image"}

    # search_waterfall은 점수 정렬되어 있다고 가정 (image_search 내부 정렬)
    # SearchedImage는 score를 직접 노출하지 않으므로 보수적으로 임계 + 인기 도메인 신뢰
    top = results[0]
    # 라이선스 + 해상도 휴리스틱
    pixels = max(top.width or 0, top.height or 0)
    license_low = (top.license or "").lower()
    has_cc = any(tag in license_low for tag in ("cc", "pd", "pixabay", "public domain"))
    pseudo_score = (
        (30.0 if pixels >= 1280 else 20.0 if pixels >= 800 else 10.0)
        + (20.0 if has_cc else 5.0)
        + (10.0 if top.source in ("wikimedia", "pixabay") else 5.0)
    )
    auto = pseudo_score >= IMAGE_AUTO_THRESHOLD

    entry = {
        "scene_index": scene_index,
        "asset_kind": "search_image",
        "query": query,
        "top_score": pseudo_score,
        "auto_selected": auto,
        "candidates": [
            {
                "title": r.title,
                "image_url": r.image_url,
                "thumbnail_url": r.thumbnail_url or r.image_url,
                "source": r.source,
                "source_domain": r.source_domain,
                "source_page": r.source_page,
                "width": r.width,
                "height": r.height,
                "license": r.license,
                "description": r.description,
            }
            for r in results
        ],
    }
    if auto:
        ia = scene.get("imageAsset") or {}
        ia["source"] = "search"
        ia["query"] = query
        ia["url"] = top.image_url
        ia["thumbnail_url"] = top.thumbnail_url
        ia["license"] = top.license
        ia["source_domain"] = top.source_domain
        ia["selection_status"] = "auto"
        ia["selection_score"] = pseudo_score
        scene["imageAsset"] = ia
    else:
        entry["status"] = "needs_review"
    return entry


def enrich_project(project_output_dir: Path, *, dry_run: bool = False,
                   limit_per_scene: int = 5) -> dict[str, Any]:
    """프로젝트 디렉토리에서 scene_specs.json을 로드해 enrichment 실행."""
    project_output_dir = Path(project_output_dir)
    spec_path = project_output_dir / "scene_specs.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"scene_specs.json 없음: {spec_path}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    scenes = spec.get("scenes", [])

    queue: list[dict[str, Any]] = []
    summary = {
        "total_scenes": len(scenes),
        "video_scenes": 0,
        "search_image_scenes": 0,
        "generate_scenes": 0,
        "auto_selected": 0,
        "needs_review": 0,
        "no_candidates": 0,
        "errors": 0,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }

    for i, scene in enumerate(scenes):
        strategy = scene.get("asset_strategy")
        ia_source = (scene.get("imageAsset") or {}).get("source")

        # 글로벌 분류 — 채널·art_style 무관
        target_kind: str | None = None
        if strategy == "video":
            target_kind = "video"
        elif strategy == "search_image":
            target_kind = "search_image"
        elif strategy == "generate":
            summary["generate_scenes"] += 1
            continue
        elif ia_source == "search":
            # asset_strategy 미부여 채널 (이로미즘 등) — imageAsset.source 기준 라우팅
            target_kind = "search_image"
        elif ia_source == "generate":
            summary["generate_scenes"] += 1
            continue

        if target_kind is None:
            # 자료 자체가 필요 없는 씬 (headline-only, 데이터 카드 등)
            continue

        if target_kind == "video":
            summary["video_scenes"] += 1
            entry = _enrich_video_scene(scene, i, limit=limit_per_scene)
        else:
            summary["search_image_scenes"] += 1
            entry = _enrich_image_scene(scene, i, limit=limit_per_scene)

        if entry.get("auto_selected"):
            summary["auto_selected"] += 1
        elif entry.get("status") == "needs_review":
            summary["needs_review"] += 1
            queue.append(entry)
        elif entry.get("status") == "no_candidates":
            summary["no_candidates"] += 1
            queue.append(entry)
        elif entry.get("status") == "error":
            summary["errors"] += 1
            queue.append(entry)

    if not dry_run:
        spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        (project_output_dir / "enrichment_queue.json").write_text(
            json.dumps({"summary": summary, "queue": queue}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (project_output_dir / "enrichment_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {"summary": summary, "queue": queue}


def apply_user_selection(project_output_dir: Path, scene_index: int,
                         selected_candidate: dict[str, Any]) -> None:
    """대시보드에서 사용자가 선택한 후보를 scene_specs에 주입."""
    project_output_dir = Path(project_output_dir)
    spec_path = project_output_dir / "scene_specs.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    scenes = spec.get("scenes", [])
    if not (0 <= scene_index < len(scenes)):
        raise IndexError(f"scene_index 범위 초과: {scene_index}")
    scene = scenes[scene_index]
    strategy = scene.get("asset_strategy")

    if strategy == "video":
        va = scene.get("videoAsset") or {}
        va["selected_video_id"] = selected_candidate.get("video_id")
        va["selected_url"] = selected_candidate.get("url")
        va["selected_title"] = selected_candidate.get("title")
        va["selected_channel"] = selected_candidate.get("channel")
        va["license"] = selected_candidate.get("license")
        va["selection_status"] = "user_picked"
        va["selection_score"] = selected_candidate.get("score")
        scene["videoAsset"] = va
    elif strategy == "search_image":
        ia = scene.get("imageAsset") or {}
        ia["source"] = "search"
        ia["url"] = selected_candidate.get("image_url")
        ia["thumbnail_url"] = selected_candidate.get("thumbnail_url")
        ia["license"] = selected_candidate.get("license")
        ia["source_domain"] = selected_candidate.get("source_domain")
        ia["selection_status"] = "user_picked"
        scene["imageAsset"] = ia
    else:
        raise ValueError(f"asset_strategy={strategy} 는 enrichment 대상 아님")

    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    # enrichment_queue에서 해당 항목 제거
    queue_path = project_output_dir / "enrichment_queue.json"
    if queue_path.exists():
        data = json.loads(queue_path.read_text(encoding="utf-8"))
        data["queue"] = [q for q in data.get("queue", []) if q.get("scene_index") != scene_index]
        data["summary"]["needs_review"] = max(0, data["summary"].get("needs_review", 0) - 1)
        queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    # PipelineRunner 호출용 CLI 진입점
    import os
    import sys

    project_dir = Path(os.environ.get("PROJECT_DIR", ""))
    if not project_dir or not project_dir.exists():
        print(f"[scene_enricher] PROJECT_DIR 미설정 또는 미존재: {project_dir}", flush=True)
        sys.exit(2)

    print(f"[scene_enricher] 시작 — {project_dir}", flush=True)
    try:
        result = enrich_project(project_dir, dry_run=False)
    except FileNotFoundError as e:
        print(f"[scene_enricher] 입력 파일 없음: {e}", flush=True)
        sys.exit(2)
    except Exception as e:
        print(f"[scene_enricher] 실패: {e}", flush=True)
        sys.exit(1)

    s = result["summary"]
    print(f"[scene_enricher] 완료 — auto={s['auto_selected']} review={s['needs_review']} "
          f"no_cand={s['no_candidates']} err={s['errors']}", flush=True)

    # 검토 대기 항목이 있으면 파이프라인 정지 — Stage 3는 검토 후 진입
    # (--auto-enrich 같은 환경변수로 우회 가능, 기본은 정지)
    if s["needs_review"] > 0 and os.environ.get("AUTO_ENRICH_SKIP_WAIT") != "1":
        print(f"[scene_enricher] ⚠️ 사람 검토 대기 {s['needs_review']}건 — "
              f"대시보드 '자료 검토' 탭에서 처리 후 'auto-agent run --project ... --from step_3b' 재개", flush=True)
        sys.exit(2)
    sys.exit(0)
