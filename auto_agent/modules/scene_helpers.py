"""
scene_specs.json v5 — 단일 진입 헬퍼.

플랫 스키마 원칙:
- 각 씬은 visual_kind 필드 1개로 primary visual을 선언 (Layer 1 단일성)
- text/data overlay (headline, items 등)는 자유 조합 (Layer 2)
- 모든 읽기 주체는 get_visual_kind() 만 호출, 다른 시각 객체 직접 검사 금지

이 모듈만이 legacy 필드(imageAsset.source, mapScene 존재 등)에서
visual_kind를 유추하는 fallback 책임을 가진다. 다른 모듈은 이 함수만 호출.
"""
from __future__ import annotations

from typing import Any, Iterable

VALID_VISUAL_KINDS = {
    "map", "chart", "video", "search_image", "generate_image", "none",
}

# Layer 2 — overlay 필드 (visual_kind 무관, 어떤 visual_kind와도 조합 가능)
OVERLAY_FIELDS = {
    "headline", "subtitle", "items", "values", "unit", "source", "captions", "narration",
}

# 각 visual_kind가 사용하는 Layer 1 객체 (단 1개)
PRIMARY_OBJECT_FOR_KIND = {
    "map": "mapScene",
    "chart": "chartConfig",
    "video": "videoAsset",
    "search_image": "imageAsset",
    "generate_image": "imageAsset",
    "none": None,
}

# 각 visual_kind에서 절대 같이 있으면 안 되는 객체 (Layer 1 단일성)
FORBIDDEN_PRIMARIES_FOR_KIND = {
    "map": ("imageAsset", "videoAsset", "chartConfig"),
    "chart": ("imageAsset", "videoAsset", "mapScene"),
    "video": ("imageAsset", "mapScene", "chartConfig"),
    "search_image": ("videoAsset", "mapScene", "chartConfig"),
    "generate_image": ("videoAsset", "mapScene", "chartConfig"),
    "none": ("imageAsset", "videoAsset", "mapScene", "chartConfig"),
}

# Layout이 visual_kind를 강제하는 경우 (mismatch면 위반)
LAYOUT_REQUIRES_KIND = {
    "bar": "chart",
    "pie": "chart",
    "line": "chart",
    "area": "chart",
    "map_scene": "map",
}

# visual_kind=map은 다음 layout과 부조화 — 자동 의심 (false-positive 패턴)
MAP_FORBIDDEN_LAYOUTS = {
    "headline_only", "cinematic", "metric_spotlight", "metric_wall",
    "before_after", "flow", "timeline",
}

# visual_kind=chart는 chart layout 외에서 부조화 (chartConfig 있어도 차트 layout 아니면 의미 없음)
CHART_REQUIRED_LAYOUTS = {"bar", "pie", "line", "area"}


def get_visual_kind(scene: dict[str, Any]) -> str:
    """씬의 primary visual 종류를 반환. 단일 진입점.

    우선순위:
    1. scene["visual_kind"]가 명시되어 있으면 그대로
    2. legacy fallback (mapScene 있으면 map, chartConfig 있으면 chart, ...)
    3. 모두 해당 없으면 "none"
    """
    explicit = scene.get("visual_kind")
    if explicit in VALID_VISUAL_KINDS:
        return explicit

    # legacy fallback — 새 스키마 마이그레이션 전 데이터 호환
    if scene.get("mapScene"):
        return "map"
    if scene.get("chartConfig"):
        return "chart"
    if scene.get("videoAsset"):
        return "video"

    ia = scene.get("imageAsset") or {}
    src = ia.get("source")
    if src == "search":
        return "search_image"
    if src == "generate":
        return "generate_image"

    # asset_strategy fallback (전환기 호환)
    legacy_strategy = scene.get("asset_strategy")
    if legacy_strategy in ("video", "search_image", "generate"):
        return "generate_image" if legacy_strategy == "generate" else legacy_strategy
    return "none"


def get_primary_object(scene: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """현재 visual_kind에 해당하는 primary 객체 (필드명, 객체 dict)를 반환."""
    kind = get_visual_kind(scene)
    obj_field = PRIMARY_OBJECT_FOR_KIND.get(kind)
    if obj_field is None:
        return ("", None)
    return (obj_field, scene.get(obj_field))


def is_visual_only_kind(kind: str) -> bool:
    """이미지/비디오 처리 모듈이 작업해야 하는 종류 여부."""
    return kind in ("search_image", "generate_image", "video")


def validate_scene(scene: dict[str, Any]) -> list[str]:
    """단일 씬 무결성 검증. 위반 사항 메시지 리스트 반환 (빈 리스트면 통과)."""
    issues: list[str] = []
    kind = get_visual_kind(scene)
    if kind not in VALID_VISUAL_KINDS:
        issues.append(f"unknown visual_kind: {kind!r}")
        return issues

    # Layer 1 단일성 — 금지 객체가 같이 있으면 안 됨
    forbidden = FORBIDDEN_PRIMARIES_FOR_KIND.get(kind, ())
    for f in forbidden:
        if scene.get(f):
            issues.append(
                f"visual_kind={kind} 인데 {f} 가 함께 존재 (Layer 1 단일성 위반)"
            )

    # 필수 객체 존재 — visual_kind 가 객체를 요구하는데 비어 있으면 안 됨
    required = PRIMARY_OBJECT_FOR_KIND.get(kind)
    if required and not scene.get(required):
        issues.append(f"visual_kind={kind} 인데 {required} 가 비어 있음")

    # imageAsset.source vs visual_kind 일관성
    if kind in ("search_image", "generate_image"):
        ia_source = (scene.get("imageAsset") or {}).get("source")
        expected = "search" if kind == "search_image" else "generate"
        if ia_source and ia_source != expected:
            issues.append(
                f"visual_kind={kind} 인데 imageAsset.source={ia_source!r} 불일치 (예상 {expected!r})"
            )

    # Layout × visual_kind 호환 검증
    layout = scene.get("layout") or ""
    required_kind = LAYOUT_REQUIRES_KIND.get(layout)
    if required_kind and kind != required_kind:
        issues.append(
            f"layout={layout!r}는 visual_kind={required_kind!r}를 요구하지만 현재 {kind!r}"
        )

    # map 부조화 layout (false-positive 패턴 — 위치가 subject가 아닐 가능성)
    if kind == "map" and layout in MAP_FORBIDDEN_LAYOUTS:
        issues.append(
            f"visual_kind=map + layout={layout!r}는 부조화 패턴 — 위치가 subject가 아닐 가능성 높음. "
            f"narration을 검토하고 generate_image 또는 search_image로 재분류 권장"
        )

    return issues


def suggest_visual_kind_from_layout(scene: dict[str, Any]) -> str | None:
    """layout 기반 visual_kind 제안 (오분류 자동 정정용 휴리스틱).

    layout이 visual_kind를 강제하는 경우 그 종류 반환, 그 외 None.
    """
    layout = scene.get("layout") or ""
    return LAYOUT_REQUIRES_KIND.get(layout)


def validate_scene_specs(spec: dict[str, Any]) -> dict[str, Any]:
    """전체 scene_specs 검증 결과 요약."""
    scenes = spec.get("scenes", [])
    per_scene_issues: list[dict[str, Any]] = []
    kind_counts: dict[str, int] = {}

    for i, scene in enumerate(scenes):
        kind = get_visual_kind(scene)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        issues = validate_scene(scene)
        if issues:
            per_scene_issues.append({
                "scene_index": i,
                "sceneNumber": scene.get("sceneNumber"),
                "visual_kind": kind,
                "issues": issues,
            })

    return {
        "total_scenes": len(scenes),
        "kind_counts": kind_counts,
        "violation_count": len(per_scene_issues),
        "violations": per_scene_issues,
    }


# Layer 1 객체와 부속 경로 — convert_visual_kind에서 정리 대상
_ALL_LAYER1_OBJECTS = ("imageAsset", "videoAsset", "mapScene", "chartConfig")
_IMAGE_PATH_FIELDS = ("imagePath", "vizBackgroundPath")


def convert_visual_kind(
    scene: dict[str, Any],
    target: str,
    *,
    default_prompt: str | None = None,
) -> dict[str, Any]:
    """씬을 target visual_kind로 정규화 변환.

    - 금지 Layer 1 객체 제거
    - visual_kind 필드 설정
    - 이미지 종류: imageAsset.source/prompt 보장
    - map/chart: 비어 있으면 최소 스켈레톤 시드
    - layout이 target과 충돌 시 layout 비움 (사용자가 다시 고를 수 있도록)
    - imagePath/vizBackgroundPath: 이미지 종류가 아니면 제거

    같은 dict를 in-place 수정 후 반환.
    """
    if target not in VALID_VISUAL_KINDS:
        raise ValueError(f"unknown target visual_kind: {target!r}")

    # 1) 금지 객체 제거
    forbidden = FORBIDDEN_PRIMARIES_FOR_KIND.get(target, ())
    for f in forbidden:
        scene.pop(f, None)

    # 2) 이미지 경로 — 이미지 종류가 아니면 제거
    if target not in ("search_image", "generate_image"):
        for f in _IMAGE_PATH_FIELDS:
            scene.pop(f, None)

    # 3) 종류별 primary 객체 보장
    if target in ("search_image", "generate_image"):
        ia = scene.get("imageAsset") or {}
        ia["source"] = "search" if target == "search_image" else "generate"
        prompt = ia.get("prompt") or default_prompt or scene.get("headline") or scene.get("narration") or ""
        if prompt and not ia.get("prompt"):
            ia["prompt"] = prompt
        scene["imageAsset"] = ia
    elif target == "map":
        if not scene.get("mapScene"):
            scene["mapScene"] = {
                "mapStyle": "modern_clean",
                "markers": [],
                "labels": [],
            }
    elif target == "chart":
        if not scene.get("chartConfig"):
            scene["chartConfig"] = {
                "type": "bar",
                "data": [],
            }
    elif target == "video":
        # videoAsset은 사용자가 업로드/지정해야 채워짐 — 자동 시드하지 않음
        pass
    # target == "none" — 모두 제거됨

    # 4) layout 충돌 정리 — layout이 다른 종류를 강제하면 비움
    layout = scene.get("layout") or ""
    required_kind = LAYOUT_REQUIRES_KIND.get(layout)
    if required_kind and required_kind != target:
        scene["layout"] = ""
    # map → 일반 이미지 전환 시 map_scene 잔재 방지
    if target != "map" and layout == "map_scene":
        scene["layout"] = ""

    # 5) visual_kind 명시
    scene["visual_kind"] = target
    return scene


def iter_scenes_of_kind(scene_list: Iterable[dict[str, Any]],
                       kinds: tuple[str, ...]) -> Iterable[tuple[int, dict[str, Any]]]:
    """특정 visual_kind에 해당하는 씬만 필터링하는 헬퍼."""
    for i, sc in enumerate(scene_list):
        if get_visual_kind(sc) in kinds:
            yield i, sc
