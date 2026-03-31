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
            chapter_str = str(chapter) if chapter is not None else ""
            if chapter_str and chapter_str != str(prev_chapter) and i > 0:
                time_str = self._sec_to_timestamp(current_sec)
                # 챕터가 숫자면 headline에서 라벨 추출
                label = scene.get("headline", "") or f"챕터 {chapter_str}"
                timestamps.append({"time": time_str, "label": str(label)[:30]})
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
        import re

        # 핵심 headline 추출 ({{변수}} 제거, 빈 값 제외)
        clean_headlines = []
        for s in scenes:
            h = s.get("headline", "")
            if h and not h.startswith("{{"):
                cleaned = re.sub(r"\{\{.*?\}\}", "", h).strip()
                if cleaned and len(cleaned) > 2:
                    clean_headlines.append(cleaned)

        # headline이 없으면 narration 첫 문장에서 추출
        if not clean_headlines:
            for s in scenes:
                narr = s.get("narration", "")
                if narr:
                    first_sentence = narr.split(".")[0].split("?")[0].split("!")[0]
                    if len(first_sentence) > 5:
                        clean_headlines.append(first_sentence[:40])
                        break

        # 프로젝트 제목 추출
        topic = clean_headlines[0] if clean_headlines else "주제"

        # manuscript에서 프로젝트 제목 찾기
        manuscript_path = self._project_dir / "final_manuscript.md"
        if manuscript_path.exists():
            first_line = manuscript_path.read_text(encoding="utf-8").split("\n")[0]
            if first_line.startswith("#"):
                topic = first_line.lstrip("# ").strip()[:40]

        return [
            {"type": "A_숫자형", "title": topic},
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
        """해시태그 자동 생성 — {{변수}} 필터링."""
        import re
        tags = set()

        for s in scenes:
            # items에서 추출
            for item in s.get("items", []):
                if isinstance(item, dict):
                    label = item.get("label", "")
                    if label and len(label) < 15 and "{{" not in label:
                        tags.add(f"#{label.replace(' ', '')}")

            # headline에서 추출 ({{변수}} 제외)
            headline = s.get("headline", "")
            if headline:
                cleaned = re.sub(r"\{\{.*?\}\}", "", headline).strip()
                for word in cleaned.split():
                    if len(word) >= 2 and "{{" not in word and "}}" not in word:
                        tags.add(f"#{word}")
                        if len(tags) >= 10:
                            break

        # narration에서 핵심 키워드 보충
        if len(tags) < 5:
            for s in scenes:
                narr = s.get("narration", "")
                # 따옴표 안의 고유명사 추출
                quoted = re.findall(r"['\"]([^'\"]{2,10})['\"]", narr)
                for q in quoted:
                    if "{{" not in q:
                        tags.add(f"#{q.replace(' ', '')}")

        # manuscript 제목에서 추가
        manuscript_path = self._project_dir / "final_manuscript.md"
        if manuscript_path.exists() and len(tags) < 5:
            first_line = manuscript_path.read_text(encoding="utf-8").split("\n")[0]
            for word in first_line.lstrip("# ").split():
                if len(word) >= 2:
                    tags.add(f"#{word}")

        return list(tags)[:10]

    def _generate_thumbnail_specs(self, scenes: List[Dict]) -> List[Dict]:
        """썸네일 3종 스펙 — 실제 이미지 파일에서 찾기."""
        import re
        specs = []

        # 1. images/ 디렉토리에서 실제 이미지 파일 찾기
        images_dir = self._project_dir / "images"
        image_files = []
        if images_dir.exists():
            for subdir in ["generated", "search"]:
                sub = images_dir / subdir
                if sub.exists():
                    for f in sorted(sub.iterdir()):
                        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                            image_files.append(f)

        # 2. scene_specs의 imageAsset.path에서도 찾기
        for s in scenes:
            img = s.get("imageAsset")
            if isinstance(img, dict) and img.get("path"):
                p = self._project_dir / img["path"]
                if p.exists() and p not in image_files:
                    image_files.append(p)

        # 3. 상위 3개 선택 (가운데 씬들이 보통 핵심)
        if image_files:
            # 첫 번째, 가운데, 마지막에서 선택
            selected = []
            if len(image_files) >= 3:
                selected = [
                    image_files[0],
                    image_files[len(image_files) // 2],
                    image_files[-1],
                ]
            else:
                selected = image_files[:3]

            for i, img_path in enumerate(selected):
                # 해당 이미지의 씬 번호 추출
                match = re.search(r"scene_(\d+)", img_path.name)
                scene_idx = int(match.group(1)) - 1 if match else i
                headline = scenes[scene_idx].get("headline", "") if scene_idx < len(scenes) else ""

                specs.append({
                    "variant": chr(65 + i),  # A, B, C
                    "scene_index": scene_idx,
                    "image_path": str(img_path),
                    "headline": headline,
                    "resolution": {"width": 1280, "height": 720},
                })

        return specs
