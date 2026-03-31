"""Stage 3-1: 업로드 정보 생성 — 썸네일 3종 + 제목 3종 + 더보기란 + 타임스탬프."""
import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class UploadInfoGenerator:
    """본편 완성 후 YouTube 업로드 정보 자동 생성."""

    def __init__(self, project_dir: Path):
        self._project_dir = project_dir

    def generate(self) -> Dict:
        """upload_info.json 생성."""
        scene_specs = self._load_scene_specs()
        manifest = self._load_manifest()

        if not scene_specs:
            return {"status": "error", "message": "scene_specs.json 없음"}

        # 타임스탬프 계산
        timestamps = self._calculate_timestamps(scene_specs, manifest)

        # 제목 3종 생성
        titles = self._generate_titles(scene_specs)

        # 더보기란 생성
        description = self._generate_description(scene_specs, timestamps)

        # 해시태그
        hashtags = self._generate_hashtags(scene_specs)

        upload_info = {
            "titles": titles,
            "description": description,
            "timestamps": timestamps,
            "hashtags": hashtags,
            "thumbnails": self._generate_thumbnail_specs(scene_specs),
        }

        # 저장
        output = self._project_dir / "upload_info.json"
        output.write_text(json.dumps(upload_info, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("upload_info.json 생성: %s", output)

        return {"status": "success", "path": str(output), "data": upload_info}

    def _load_scene_specs(self) -> List[Dict]:
        """scene_specs.json 로드."""
        path = self._project_dir / "scene_specs.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("scenes", [])

    def _load_manifest(self) -> Optional[Dict]:
        """manifest.json 로드."""
        path = self._project_dir / "manifest.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _calculate_timestamps(self, scenes: List[Dict],
                                manifest: Optional[Dict]) -> List[Dict]:
        """씬별 시작 시간 계산 → 타임스탬프 생성.

        manifest.json의 durationFrames + fps에서 계산.
        없으면 scene_specs의 estimatedDuration에서 추정.
        """
        timestamps = [{"time": "0:00", "label": "오프닝"}]
        current_sec = 0
        fps = 30  # 기본 fps

        if manifest:
            fps = manifest.get("fps", 30)
            manifest_scenes = manifest.get("scenes", [])
        else:
            manifest_scenes = []

        prev_chapter = None
        for i, scene in enumerate(scenes):
            # 챕터 변경 감지
            chapter = scene.get("chapter", scene.get("headline", ""))
            if chapter and chapter != prev_chapter and i > 0:
                time_str = self._sec_to_timestamp(current_sec)
                timestamps.append({"time": time_str, "label": chapter[:30]})
            prev_chapter = chapter

            # 시간 누적
            if i < len(manifest_scenes):
                frames = manifest_scenes[i].get("durationFrames", 150)
                current_sec += frames / fps
            else:
                # manifest 없으면 씬당 30초 추정
                est = scene.get("estimatedDuration", 30)
                current_sec += est

        # 마무리 타임스탬프
        time_str = self._sec_to_timestamp(current_sec - 30 if current_sec > 30 else current_sec)
        timestamps.append({"time": time_str, "label": "마무리"})

        return timestamps

    def _sec_to_timestamp(self, seconds: float) -> str:
        """초 → MM:SS 변환."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def _generate_titles(self, scenes: List[Dict]) -> List[Dict]:
        """제목 3종 (A/B/C) — 씬 데이터에서 추출."""
        # 핵심 headline 추출
        headlines = [s.get("headline", "") for s in scenes if s.get("headline")]
        topic = scenes[0].get("topic", headlines[0] if headlines else "")

        return [
            {"type": "A_숫자형", "title": f"{topic}"},
            {"type": "B_반전형", "title": f"당신이 몰랐던 {topic}의 진실"},
            {"type": "C_공감형", "title": f"{topic}, 왜 지금 중요한가"},
        ]

    def _generate_description(self, scenes: List[Dict],
                                timestamps: List[Dict]) -> str:
        """더보기란 — 요약 + 타임스탬프 + 해시태그."""
        # 요약: 첫 씬의 narration에서 추출
        first_narration = ""
        for s in scenes:
            if s.get("narration"):
                first_narration = s["narration"][:200]
                break

        # 타임스탬프 문자열
        ts_lines = "\n".join(f"{t['time']} {t['label']}" for t in timestamps)

        return f"""{first_narration}...

📌 타임스탬프
{ts_lines}
"""

    def _generate_hashtags(self, scenes: List[Dict]) -> List[str]:
        """해시태그 자동 생성."""
        tags = set()
        for s in scenes:
            for item in s.get("items", []):
                if isinstance(item, dict):
                    label = item.get("label", "")
                    if label and len(label) < 15:
                        tags.add(f"#{label.replace(' ', '')}")
            headline = s.get("headline", "")
            if headline:
                # 핵심 키워드 추출 (간단하게)
                for word in headline.split():
                    if len(word) >= 2 and not word.startswith("#"):
                        tags.add(f"#{word}")
                        if len(tags) >= 10:
                            break
        return list(tags)[:10]

    def _generate_thumbnail_specs(self, scenes: List[Dict]) -> List[Dict]:
        """썸네일 3종 스펙 — Remotion 렌더링용."""
        # 가장 임팩트 있는 씬 찾기
        impact_scenes = sorted(
            [s for s in scenes if s.get("imageAsset", {}).get("path")],
            key=lambda x: x.get("trend_velocity", 5),
            reverse=True,
        )[:3]

        specs = []
        for i, scene in enumerate(impact_scenes):
            specs.append({
                "variant": chr(65 + i),  # A, B, C
                "scene_index": scenes.index(scene),
                "image_path": scene.get("imageAsset", {}).get("path", ""),
                "headline": scene.get("headline", ""),
                "resolution": {"width": 1280, "height": 720},
            })
        return specs
