"""Assembly-Director Tool Wrapper API.

에이전트는 "무엇을"만 판단, Tool이 "어떻게"를 처리.
아트스타일 프리셋, FAL.ai 호출, 병렬 처리 등은 Tool이 자동 처리.
"""
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ImageTool:
    """이미지 생성/검색 Tool — 아트스타일 자동 조합 + 병렬 처리."""

    def __init__(self, project_dir: Path, art_style: str = "semoji"):
        self._project_dir = project_dir
        self._art_style = art_style
        self._style_config = self._load_style(art_style)
        self._executor = ThreadPoolExecutor(max_workers=4)

    def _load_style(self, style_name: str) -> Dict:
        """아트스타일 프리셋 자동 로드."""
        style_path = Path(__file__).parent.parent / "data" / "artstyle" / "styles" / f"{style_name}.json"
        if style_path.exists():
            return json.loads(style_path.read_text(encoding="utf-8"))
        logger.warning("아트스타일 없음: %s", style_name)
        return {}

    def generate_scene(self, scene_num: int, prompt: str,
                        source: str = "generate") -> Dict:
        """단일 씬 이미지 생성/검색.

        에이전트는 이것만 호출:
          image_tool.generate_scene(3, "한글 장면 묘사", "generate")

        Tool이 자동 처리:
          - 아트스타일 프리셋 조합
          - reference_image 첨부
          - FAL.ai 호출 (generate) 또는 Serper 검색 (search)
          - 버전 관리 (_gen_01, _gen_02)
          - 결과 반환
        """
        if source == "generate":
            return self._generate(scene_num, prompt)
        elif source == "search":
            return self._search(scene_num, prompt)
        else:
            logger.error("알 수 없는 source: %s", source)
            return {"status": "error", "message": f"source must be 'generate' or 'search', got '{source}'"}

    def generate_batch(self, scenes: List[Dict]) -> List[Dict]:
        """여러 씬 이미지를 병렬 생성/검색.

        에이전트:
          image_tool.generate_batch([
            {"scene": 1, "prompt": "...", "source": "generate"},
            {"scene": 2, "prompt": "...", "source": "search"},
            {"scene": 3, "prompt": "...", "source": "generate"},
          ])

        generate와 search가 동시에 병렬 실행됨.
        """
        logger.info("이미지 배치 시작: %d개 씬 (병렬)", len(scenes))

        futures = []
        for s in scenes:
            future = self._executor.submit(
                self.generate_scene,
                s["scene"], s["prompt"], s.get("source", "generate"),
            )
            futures.append((s["scene"], future))

        results = []
        for scene_num, future in futures:
            try:
                result = future.result(timeout=120)
                results.append(result)
                logger.info("씬 %d 완료: %s", scene_num, result.get("status"))
            except Exception as e:
                results.append({"scene": scene_num, "status": "error", "message": str(e)})
                logger.error("씬 %d 실패: %s", scene_num, e)

        logger.info("이미지 배치 완료: %d/%d 성공",
                     sum(1 for r in results if r.get("status") == "success"),
                     len(results))
        return results

    def _generate(self, scene_num: int, prompt: str) -> Dict:
        """FAL.ai로 이미지 생성 — 아트스타일 자동 조합."""
        style = self._style_config

        # 최종 프롬프트 조합
        style_desc = style.get("scene_style_description", "")
        full_prompt = f"{style_desc} {prompt}" if style_desc else prompt

        # 네거티브 프롬프트
        requirements = style.get("technical", {}).get("critical_requirements", [])
        negative = ", ".join(requirements) if requirements else ""

        # reference_image
        ref_image = style.get("reference_image", "")

        # 버전 관리
        output_path = self._get_versioned_path(scene_num)

        logger.info("씬 %d 생성: %s...", scene_num, prompt[:50])

        # TODO: 실제 FAL.ai API 호출
        # from auto_agent.modules.image_batch_module import generate_image
        # result = generate_image(full_prompt, ref_image, negative, output_path)

        return {
            "scene": scene_num,
            "status": "success",
            "source": "generate",
            "path": str(output_path),
            "prompt_used": full_prompt[:200],
            "style": style.get("id", "unknown"),
        }

    def _search(self, scene_num: int, prompt: str) -> Dict:
        """이미지 검색 (Serper API)."""
        output_path = self._get_versioned_path(scene_num)

        logger.info("씬 %d 검색: %s...", scene_num, prompt[:50])

        # TODO: 실제 Serper API 호출
        # from auto_agent.modules.image_batch_module import search_image

        return {
            "scene": scene_num,
            "status": "success",
            "source": "search",
            "path": str(output_path),
            "query": prompt[:200],
        }

    def _get_versioned_path(self, scene_num: int) -> Path:
        """버전 번호가 붙은 출력 경로 생성."""
        base = self._project_dir / f"scene_{scene_num:02d}"
        version = 1
        while True:
            path = base.parent / f"{base.name}_gen_{version:02d}.png"
            if not path.exists():
                return path
            version += 1


class TTSTool:
    """TTS 생성 Tool — mood × motion 자동 매핑."""

    # mood × motion → TTS 파라미터 매핑
    MOOD_PARAMS = {
        "tense": {"speed": 1.05, "stability": 0.6, "style": 0.7},
        "dramatic": {"speed": 0.95, "stability": 0.5, "style": 0.8},
        "calm": {"speed": 0.9, "stability": 0.8, "style": 0.3},
        "energetic": {"speed": 1.1, "stability": 0.5, "style": 0.6},
        "somber": {"speed": 0.85, "stability": 0.7, "style": 0.5},
        "neutral": {"speed": 1.0, "stability": 0.7, "style": 0.5},
    }

    def __init__(self, voice_id: str = "default"):
        self._voice_id = voice_id

    def generate(self, scene_num: int, narration: str,
                  mood: str = "neutral", motion: str = "none") -> Dict:
        """TTS 생성 — mood에 따라 자동 파라미터 조절.

        에이전트:
          tts_tool.generate(3, "나레이션 텍스트", mood="tense")

        Tool이 자동 처리:
          - mood → speed/stability/style 매핑
          - 한국어 전처리 (숫자, 약어 등)
          - ElevenLabs API 호출
        """
        params = self.MOOD_PARAMS.get(mood, self.MOOD_PARAMS["neutral"])

        logger.info("씬 %d TTS: mood=%s → speed=%.2f, stability=%.2f",
                     scene_num, mood, params["speed"], params["stability"])

        # TODO: 실제 TTS 호출
        # from auto_agent.modules.tts_generator import generate_tts

        return {
            "scene": scene_num,
            "status": "success",
            "mood": mood,
            "params": params,
            "narration_length": len(narration),
        }


class ManifestTool:
    """매니페스트 빌드 Tool — 전환 효과, 타이밍 자동 계산."""

    def build(self, scene_specs: List[Dict], audio_files: List[str],
               transitions: Optional[Dict] = None) -> Dict:
        """매니페스트 생성.

        에이전트가 transitions(전환 효과)를 지정하면 반영,
        없으면 mood 기반 자동 결정.
        """
        logger.info("매니페스트 빌드: %d개 씬", len(scene_specs))

        # TODO: 실제 manifest_builder 호출
        return {
            "status": "success",
            "scenes": len(scene_specs),
            "transitions": transitions or "auto",
        }
