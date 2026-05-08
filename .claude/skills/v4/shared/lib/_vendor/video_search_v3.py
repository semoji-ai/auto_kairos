"""
씬 연출용 비디오 검색 + Gemini 분석.

워크플로 (2단계, 사용자 개입):
  1. search(query)  → yt-dlp로 후보 리스트 + 라이선스 표기
  2. 사용자가 video_id 선택
  3. analyze(video_id) → 다운로드 + Gemini 분석 + 캐시

캐시: $KAIROS_VAULT_DIR/cache/video/
  searches/<query_hash>.json
  clips/<video_id>/{video_id}.mp4 + metadata.json + gemini_analysis.json
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_vault_dir() -> Path:
    """v4 vendored get_vault_dir — KAIROS_VAULT_DIR 환경 변수 그대로 사용.

    원본: auto_kairos_v3/auto_agent/paths.py
    """
    env = os.getenv("KAIROS_VAULT_DIR")
    if not env:
        raise EnvironmentError(
            "KAIROS_VAULT_DIR 환경변수가 설정되지 않았습니다. "
            ".env 또는 셸 환경에 KAIROS_VAULT_DIR=/path/to/kairos-vault 를 추가하세요."
        )
    p = Path(env).resolve()
    if not p.exists():
        raise FileNotFoundError(f"볼트 디렉토리를 찾을 수 없습니다: {p}")
    return p


logger = logging.getLogger(__name__)


def _cache_root() -> Path:
    root = get_vault_dir() / "cache" / "video"
    (root / "searches").mkdir(parents=True, exist_ok=True)
    (root / "clips").mkdir(parents=True, exist_ok=True)
    return root


def _query_hash(query: str) -> str:
    return hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]


def _classify_license(raw: str | None) -> dict[str, str]:
    """yt-dlp의 license 필드를 정책 라벨로 변환. 판단은 사용자 몫이며, risk·note만 표기."""
    if not raw:
        return {
            "label": "youtube_standard",
            "risk": "high",
            "note": "유튜브 기본 라이선스 — 인용·페어유즈 외 재사용 시 저작권 리스크",
        }
    low = raw.lower()
    if "creative commons" in low or low.startswith("cc"):
        return {
            "label": "creative_commons",
            "risk": "low",
            "note": f"{raw} — 출처 표기 필요",
        }
    return {
        "label": raw,
        "risk": "unknown",
        "note": "라이선스 미상 — 사용자 판단 필요",
    }


_TOKEN_RE = __import__("re").compile(r"[가-힣A-Za-z0-9]{2,}")


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _score_candidate(cand: dict[str, Any], keywords: set[str]) -> float:
    """씬 키워드와 제목·설명의 토큰 겹침 + 길이·라이선스 보정."""
    if not keywords:
        return 0.0
    title_toks = _tokenize(cand.get("title") or "")
    desc_toks = _tokenize(cand.get("description_snippet") or "")
    title_hits = len(keywords & title_toks)
    desc_hits = len(keywords & desc_toks)
    score = title_hits * 2.0 + desc_hits * 0.5
    # 라이선스 가산
    risk = (cand.get("license") or {}).get("risk")
    if risk == "low":
        score += 0.5
    return score


def search(
    query: str,
    limit: int = 10,
    max_duration: int | None = None,
    min_duration: int | None = None,
    keywords: set[str] | list[str] | None = None,
    channel_cap: int = 2,
    overfetch: int = 3,
) -> list[dict[str, Any]]:
    """yt-dlp ytsearch로 후보 영상 메타데이터 조회 + 적합도 재정렬.

    - 캐시: 동일 query + limit 시 재사용 (필터·재정렬은 후처리이므로 캐시 그대로 활용)
    - 필터: max_duration / min_duration (sec)
    - 재정렬: keywords 토큰과 title·desc 겹침 점수
    - channel_cap: 한 채널당 최대 N개 (기본 2)
    """
    import yt_dlp

    fetch_n = max(limit * overfetch, limit)
    cache_path = _cache_root() / "searches" / f"{_query_hash(query)}_{fetch_n}.json"

    raw: list[dict[str, Any]] = []
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("query") == query and cached.get("limit", 0) >= fetch_n:
                raw = cached["results"]
        except Exception:
            raw = []

    if not raw:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "playlistend": fetch_n,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{fetch_n}:{query}", download=False)
            for entry in (info.get("entries") or []):
                if not entry:
                    continue
                license_info = _classify_license(entry.get("license"))
                vid = entry.get("id")
                raw.append({
                    "video_id": vid,
                    "title": entry.get("title"),
                    "channel": entry.get("channel") or entry.get("uploader"),
                    "channel_id": entry.get("channel_id"),
                    "duration_sec": entry.get("duration"),
                    "view_count": entry.get("view_count"),
                    "upload_date": entry.get("upload_date"),
                    "url": entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": entry.get("thumbnail"),
                    "license": license_info,
                    "description_snippet": (entry.get("description") or "")[:600],
                })
        cache_path.write_text(
            json.dumps({
                "query": query,
                "limit": fetch_n,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "results": raw,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 1. 길이 필터
    filtered = []
    for c in raw:
        d = c.get("duration_sec") or 0
        if max_duration is not None and d > max_duration:
            continue
        if min_duration is not None and d < min_duration:
            continue
        filtered.append(c)

    # 2. 적합도 점수
    kw_set = set(k.lower() for k in keywords) if keywords else set()
    if not kw_set:
        # query에서 토큰 자동 추출 (fallback)
        kw_set = _tokenize(query)
    for c in filtered:
        c["_relevance_score"] = _score_candidate(c, kw_set)

    # 3. 정렬: score desc, then view_count desc
    filtered.sort(key=lambda c: (-(c.get("_relevance_score") or 0), -(c.get("view_count") or 0)))

    # 4. 채널당 N개 제한
    capped: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for c in filtered:
        ch = c.get("channel_id") or c.get("channel") or ""
        if seen.get(ch, 0) >= channel_cap:
            continue
        seen[ch] = seen.get(ch, 0) + 1
        capped.append(c)
        if len(capped) >= limit:
            break
    return capped


def _download_clip(video_id: str, out_dir: Path) -> Path:
    """저화질 mp4 다운로드 — 360p 우선, fallback 480p."""
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / f"{video_id}.%(ext)s")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bv*[height<=360]+ba/b[height<=360]/best[height<=480]",
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

    for ext in ("mp4", "webm", "mkv"):
        candidate = out_dir / f"{video_id}.{ext}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"다운로드 결과 파일 미발견: {video_id}")


def _ensure_metadata(video_id: str, clip_dir: Path) -> dict[str, Any]:
    """metadata.json 없으면 yt-dlp로 채워넣음."""
    import yt_dlp

    metadata_path = clip_dir / "metadata.json"
    if metadata_path.exists():
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

    license_info = _classify_license(info.get("license"))
    payload = {
        "video_id": video_id,
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "channel_id": info.get("channel_id"),
        "duration_sec": info.get("duration"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
        "url": info.get("webpage_url"),
        "license": license_info,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def analyze(video_id: str, force: bool = False) -> dict[str, Any]:
    """video_id로 다운로드 + Gemini 분석. 결과는 gemini_analysis.json에 캐시.

    Gemini 분석은 v3 의존(`auto_agent.tools.video_analyzer`). v3 부재 시 fallback.
    """
    try:
        from auto_agent.tools.video_analyzer import analyze_video
    except ImportError:
        raise NotImplementedError(
            "Gemini 영상 분석은 auto_kairos_v3 의 video_analyzer 모듈에 의존합니다. "
            "v3 폴더가 PYTHONPATH 에 없으면 본 기능은 사용할 수 없습니다. "
            "기본 yt-dlp 검색·다운로드는 정상 동작."
        )

    clip_dir = _cache_root() / "clips" / video_id
    clip_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = clip_dir / "gemini_analysis.json"

    if analysis_path.exists() and not force:
        return json.loads(analysis_path.read_text(encoding="utf-8"))

    metadata = _ensure_metadata(video_id, clip_dir)

    mp4_path = next(
        (p for p in clip_dir.glob(f"{video_id}.*")
         if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}),
        None,
    )
    if mp4_path is None:
        mp4_path = _download_clip(video_id, clip_dir)

    analysis = analyze_video(mp4_path)
    payload = {
        "video_id": video_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "clip_path": str(mp4_path),
        "metadata": metadata,
        "analysis": analysis,
    }
    analysis_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _load_scene(project_slug: str | None, scene_specs_path: str | None,
                scene_id: str | None, scene_index: int | None) -> dict[str, Any]:
    """프로젝트 slug 또는 scene_specs 경로에서 씬 하나 추출."""
    if scene_specs_path:
        sp = Path(scene_specs_path)
    else:
        try:
            from auto_agent.db.project_manager import ProjectManager
        except ImportError:
            raise NotImplementedError(
                "project_slug 기반 조회는 auto_kairos_v3 의 ProjectManager 의존. "
                "v3 부재 시 scene_specs_path 를 직접 지정하세요."
            )
        pm = ProjectManager()
        proj = pm.get_project(slug=project_slug)
        if not proj:
            raise ValueError(f"프로젝트 없음: {project_slug}")
        sp = Path(proj["output_dir"]) / "scene_specs.json"
    if not sp.exists():
        raise FileNotFoundError(f"scene_specs.json 없음: {sp}")
    data = json.loads(sp.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    if scene_id:
        for sc in scenes:
            if sc.get("scene_id") == scene_id or sc.get("id") == scene_id:
                return sc
        raise ValueError(f"scene_id {scene_id} 미발견")
    if scene_index is not None:
        return scenes[scene_index]
    raise ValueError("scene_id 또는 scene_index 필요")


_KOREAN_STOPWORDS = {
    "있는", "있습니다", "그리고", "이런", "그것", "그런", "되었", "사람", "정도",
    "이름", "이름은", "모델", "모델이었습니다", "라디오였죠", "당시", "방식",
    "이었습니다", "였습니다", "있었", "되었습니다", "있었습니다", "보면", "였죠",
    "겁니다", "된다", "된다는", "이라는", "라는", "라고", "이라고", "그래서",
    "그러나", "하지만", "그런데", "물론", "정말", "다시", "이제", "지금",
}

# 의미 있는 토큰 추출 (고유명·연도·핵심 명사). 한자 차단(CLAUDE.md 한국어 규칙).
_ENTITY_RE = __import__("re").compile(r"[A-Za-z][A-Za-z0-9-]+|\d{2,4}년?|[가-힣]{2,}")


def _scene_to_query(scene: dict[str, Any]) -> tuple[str, set[str]]:
    """씬 → (짧은 검색 쿼리, 적합도 키워드 셋).

    - 쿼리: headline에서 placeholder 제거 + chapter context 키워드 1~2개 추가 (yt-dlp는 짧은 쿼리에 강함)
    - 키워드: narration·items·imageAsset.prompt 통합 토큰 셋 (재정렬용)
    """
    import re

    # 키워드 셋 (재정렬용 — 풍부할수록 좋음)
    parts: list[str] = []
    for k in ("headline", "narration", "subtitle"):
        v = scene.get(k)
        if v:
            parts.append(str(v))
    items = scene.get("items") or []
    if isinstance(items, list):
        parts.extend([str(x) for x in items if x])
    image_prompt = (scene.get("imageAsset") or {}).get("prompt")
    if image_prompt:
        parts.append(str(image_prompt))
    bg = (scene.get("imageAsset") or {}).get("background")
    if bg:
        parts.append(str(bg))
    full_text = re.sub(r"\{\{|\}\}", " ", " ".join(parts))
    keywords = _tokenize(full_text) - _KOREAN_STOPWORDS

    # 쿼리: headline + narration에서 명사·고유명·연도 핵심만 추출 (~6 단어)
    head = re.sub(r"\{\{|\}\}", " ", (scene.get("headline") or "")).strip()
    narr = re.sub(r"\{\{|\}\}", " ", (scene.get("narration") or "")).strip()

    # headline 우선, 없으면 narration 첫 문장
    if head:
        seed = head
    else:
        seed = re.split(r"[.!?]", narr, maxsplit=1)[0]
    seed_tokens = [t for t in _ENTITY_RE.findall(seed) if t.lower() not in _KOREAN_STOPWORDS]

    # narration에서 추가 entity (특히 연도, 영문 약어, 사람·기업명) — 최대 3개
    narr_tokens = [t for t in _ENTITY_RE.findall(narr) if t.lower() not in _KOREAN_STOPWORDS]
    extras = []
    for t in narr_tokens:
        if t in seed_tokens or t in extras:
            continue
        # 연도/영문 약어/긴 한글 명사 우선
        if re.match(r"^\d{4}년?$", t) or re.match(r"^[A-Za-z][A-Za-z0-9-]{1,}$", t) or len(t) >= 3:
            extras.append(t)
        if len(extras) >= 3:
            break

    query_tokens = seed_tokens[:5] + extras
    query = " ".join(query_tokens).strip()
    return query, keywords


def search_for_scene(
    project_slug: str | None = None,
    scene_specs_path: str | None = None,
    scene_id: str | None = None,
    scene_index: int | None = None,
    limit: int = 10,
    max_duration: int | None = 1800,  # 30분 컷오프 기본
    min_duration: int | None = 30,
    extra_query: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """씬 메타데이터 → 자동 쿼리 + 키워드 → search() 호출.

    extra_query가 주어지면 자동 쿼리에 OR 조합으로 덧붙인다.
    반환: (씬 dict, 후보 리스트)
    """
    scene = _load_scene(project_slug, scene_specs_path, scene_id, scene_index)
    auto_query, keywords = _scene_to_query(scene)
    query = f"{auto_query} {extra_query}".strip() if extra_query else auto_query
    if not query:
        raise ValueError("씬에서 쿼리를 추출하지 못했습니다")
    results = search(
        query, limit=limit,
        max_duration=max_duration,
        min_duration=min_duration,
        keywords=keywords,
    )
    return scene, results


def list_cached() -> list[dict[str, Any]]:
    """이미 다운로드/분석된 클립 목록."""
    clips_root = _cache_root() / "clips"
    items: list[dict[str, Any]] = []
    for clip_dir in sorted(clips_root.iterdir()):
        if not clip_dir.is_dir():
            continue
        meta_path = clip_dir / "metadata.json"
        analysis_path = clip_dir / "gemini_analysis.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        items.append({
            "video_id": clip_dir.name,
            "title": meta.get("title"),
            "channel": meta.get("channel"),
            "duration_sec": meta.get("duration_sec"),
            "license_label": (meta.get("license") or {}).get("label"),
            "license_risk": (meta.get("license") or {}).get("risk"),
            "analyzed": analysis_path.exists(),
        })
    return items
