"""
Remotion 렌더링 브릿지

auto_kairos의 remotion_bridge.py에서 이관.
Python 파이프라인과 Remotion(Node.js) 사이의 인터페이스.
storyboard + narration + subtitles → remotion_manifest.json → 영상 렌더링.
"""
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class RemotionResult:
    """Remotion 렌더링 결과"""
    topic: str
    total_scenes: int
    total_duration: float
    resolution: str
    fps: int
    output_path: str
    manifest_path: str
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "total_scenes": self.total_scenes,
            "total_duration": self.total_duration,
            "resolution": self.resolution,
            "fps": self.fps,
            "output_path": self.output_path,
            "manifest_path": self.manifest_path,
            "created_at": self.created_at,
        }

    def save(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class RemotionBridge:
    """Remotion 렌더링 브릿지"""

    def __init__(
        self,
        remotion_dir: Optional[Path] = None,
        resolution: str = "1920x1080",
        fps: int = 30,
        crf: int = 18,
    ):
        # Remotion 프로젝트 디렉토리 (kairos-agent/remotion/)
        if remotion_dir:
            self.remotion_dir = Path(remotion_dir)
        else:
            self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"

        self.resolution = resolution
        self.width, self.height = map(int, resolution.split("x"))
        self.fps = fps
        self.crf = crf

        self._node_bin_dir = self._find_node_bin_dir()
        self.npx_path = self._find_bin("npx")
        self.npm_path = self._find_bin("npm")
        self.ffprobe_path = self._find_local_bin("ffprobe") or shutil.which("ffprobe")

    def _find_node_bin_dir(self) -> Optional[str]:
        base_dir = self.remotion_dir.parent
        bin_dir = base_dir / "bin"
        if bin_dir.exists():
            candidates = sorted(bin_dir.glob("node-v*/bin"), key=lambda p: p.parent.name, reverse=True)
            for candidate in candidates:
                if (candidate / "npx").exists():
                    return str(candidate)
        return None

    def _find_local_bin(self, name: str) -> Optional[str]:
        """프로젝트 bin/ 디렉토리에서 바이너리 검색"""
        base_dir = self.remotion_dir.parent
        local = base_dir / "bin" / name
        if local.exists():
            return str(local)
        return None

    def _find_bin(self, name: str) -> Optional[str]:
        if self._node_bin_dir:
            local = Path(self._node_bin_dir) / name
            if local.exists():
                return str(local)
        return shutil.which(name)

    def _get_node_env(self) -> dict:
        env = dict(os.environ)
        if self._node_bin_dir:
            env["PATH"] = self._node_bin_dir + ":" + env.get("PATH", "")
        return env

    def _get_audio_duration(self, audio_path: Path) -> float:
        probe = self.ffprobe_path or "ffprobe"
        cmd = [
            probe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return float(result.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            return 0.0

    def _load_subtitles_json(self, output_dir: Path) -> Dict[int, List[Dict]]:
        json_path = output_dir / "subtitles.json"
        if not json_path.exists():
            return {}
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {}
        for scene_data in data.get("scenes", []):
            scene_num = scene_data["scene_number"]
            entries = [
                {"text": e["text"], "startSec": round(e["start"], 3), "endSec": round(e["end"], 3)}
                for e in scene_data.get("entries", [])
            ]
            result[scene_num] = entries
        return result

    def _load_subtitles_srt(self, subtitles_dir: Path, scene_num: int) -> List[Dict]:
        srt_path = subtitles_dir / f"scene_{scene_num:03d}.srt"
        if not srt_path.exists():
            return []
        entries = []
        content = srt_path.read_text(encoding="utf-8")
        for block in content.strip().split("\n\n"):
            lines = block.strip().split("\n")
            if len(lines) < 3:
                continue
            try:
                start_str, end_str = lines[1].split(" --> ")
                entries.append({
                    "text": " ".join(lines[2:]),
                    "startSec": round(self._srt_to_sec(start_str.strip()), 3),
                    "endSec": round(self._srt_to_sec(end_str.strip()), 3),
                })
            except (ValueError, IndexError):
                continue
        return entries

    def _srt_to_sec(self, time_str: str) -> float:
        time_str = time_str.replace(",", ".")
        h, m, s = time_str.split(":")
        return float(h) * 3600 + float(m) * 60 + float(s)

    def _map_viz_type(self, viz_type: str) -> str:
        """vizType → Remotion 컴포넌트 매핑.

        sceneType(18종)은 visual-composer가 vizType으로 변환한 뒤
        scene_specs.json에 기록. 여기서는 vizType → Remotion 컴포넌트 매핑만 담당.

        sceneType → vizType 매핑 (visual-composer 담당):
          title_card    → slide_highlight    icon_grid    → slide_statistic
          text_highlight→ slide_highlight    icon_flow    → slide_process
          quote_card    → slide_quote        icon_stat    → slide_statistic
          bar_chart     → bar_chart          narration_only → (없음)
          line_chart    → line_chart         image_scene  → (없음)
          pie_chart     → pie_chart          compare_card → compare
          timeline      → timeline           list_card    → slide_list
          table_view    → table              numbered_list→ slide_numbered
          tech_tree     → tech_tree          diagram      → slide_process
        """
        mapping = {
            # 차트
            "bar_chart": "bar_chart",
            "line_chart": "line_chart",
            "pie_chart": "pie_chart",
            # 구조
            "tech_tree": "tech_tree",
            "table": "table",
            "timeline": "timeline",
            "compare": "compare",
            "diagram": "compare",           # 하위호환
            "slide_compare": "compare",     # 하위호환
            # 슬라이드
            "slide_quote": "slide_quote",
            "slide_list": "slide_list",
            "slide_numbered": "slide_numbered",
            "slide_highlight": "slide_highlight",
            "slide_statistic": "slide_statistic",
            "slide_process": "slide_process",
            "slide_proscons": "slide_proscons",
            "slide_definition": "slide_definition",
            "slide_summary": "slide_summary",
            "slide_profile": "slide_profile",
            "slide_ranking": "slide_ranking",
            "slide_checklist": "slide_checklist",
            "slide_qna": "slide_qna",
            "slide_countdown": "slide_countdown",
            # 레거시 별칭
            "graph": "bar_chart",
            "chart": "pie_chart",
        }
        return mapping.get(viz_type, viz_type)

    def build_manifest(
        self,
        storyboard_path: Path,
        output_dir: Path,
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.1,
        design_spec: Optional[Dict] = None,
        design_tokens: Optional[Dict] = None,
    ) -> Path:
        """storyboard + narration + subtitles → remotion_manifest.json"""
        with open(storyboard_path, "r", encoding="utf-8") as f:
            storyboard = json.load(f)

        topic = storyboard.get("topic", "Untitled")
        scenes_dir = output_dir / "scenes"
        audio_dir = output_dir / "audio"
        subtitles_dir = output_dir / "subtitles"

        subtitles_map = self._load_subtitles_json(output_dir)
        scene_entries = []
        last_image_path = None

        for scene in storyboard.get("scenes", []):
            # scene_number 또는 scene_id에서 번호 추출
            scene_num = scene.get("scene_number")
            if scene_num is None:
                scene_id = scene.get("scene_id", "")
                try:
                    scene_num = int(scene_id.split("_")[-1])
                except (ValueError, IndexError):
                    continue
            viz_type = scene.get("visualization_type")
            viz_data = scene.get("visualization_data")

            # 이미지
            image_path = scenes_dir / f"scene_{scene_num:03d}.png"
            if image_path.exists() and not viz_type:
                last_image_path = image_path
            elif not image_path.exists() and last_image_path and not viz_type:
                image_path = last_image_path

            # 오디오
            audio_mp3 = audio_dir / f"scene_{scene_num:03d}.mp3"
            audio_wav = audio_dir / f"scene_{scene_num:03d}.wav"
            audio_path = audio_mp3 if audio_mp3.exists() else audio_wav

            audio_duration = 0.0
            if audio_path.exists():
                audio_duration = self._get_audio_duration(audio_path)
            if audio_duration <= 0 and viz_type:
                audio_duration = 5.0

            # 자막
            subtitles = subtitles_map.get(scene_num) or self._load_subtitles_srt(subtitles_dir, scene_num)

            # 시각화
            visualization = None
            if viz_type and viz_data:
                raw_items = viz_data.get("items", [])
                # items가 객체 리스트인 경우 문자열로 변환
                # e.g. {year, event, detail} → "event — detail"
                flat_items = []
                flat_values = viz_data.get("values", [])
                for item in raw_items:
                    if isinstance(item, dict):
                        # timeline용: year→values, event+detail→items
                        year = item.get("year", "")
                        event = item.get("event", "")
                        detail = item.get("detail", "")
                        label = item.get("label", "")
                        value = item.get("value", "")
                        if year and event:
                            flat_items.append(f"{event} — {detail}" if detail else event)
                            if not flat_values or len(flat_values) < len(flat_items):
                                flat_values.append(str(year))
                        elif label:
                            flat_items.append(label)
                            if value and (not flat_values or len(flat_values) < len(flat_items)):
                                flat_values.append(value)
                        else:
                            flat_items.append(" / ".join(str(v) for v in item.values()))
                    else:
                        flat_items.append(str(item))

                visualization = {
                    "vizType": self._map_viz_type(viz_type),
                    "title": viz_data.get("title", ""),
                    "items": flat_items,
                    "values": flat_values,
                    "unit": viz_data.get("unit", ""),
                    "source": viz_data.get("source", ""),
                }
                for extra_key in ("left", "right", "relations", "descriptions"):
                    if viz_data.get(extra_key):
                        visualization[extra_key] = viz_data[extra_key]

            entry = {
                "sceneNumber": scene_num,
                "imagePath": str(image_path.resolve()) if image_path.exists() else "",
                "audioPath": str(audio_path.resolve()) if audio_path.exists() else "",
                "audioDurationSec": round(audio_duration, 3),
                "subtitles": subtitles,
                "visualization": visualization,
                "kenBurns": {"enabled": not bool(viz_type), "zoomFactor": 1.08},
                "transition": {"type": "cut", "durationFrames": 0},
            }
            scene_entries.append(entry)

        # design_spec에서 씬별 오버라이드 적용
        if design_spec and "scenes" in design_spec:
            for ds_scene in design_spec["scenes"]:
                sn = ds_scene.get("scene_number")
                for entry in scene_entries:
                    if entry["sceneNumber"] == sn:
                        if "kenBurns" in ds_scene:
                            entry["kenBurns"].update(ds_scene["kenBurns"])
                        if "transition" in ds_scene:
                            entry["transition"].update(ds_scene["transition"])
                        if "subtitleConfig" in ds_scene:
                            entry["subtitleConfig"] = ds_scene["subtitleConfig"]

        bgm = None
        if bgm_path:
            bgm_resolved = Path(bgm_path)
            if not bgm_resolved.exists():
                # 폴백: remotion/public/assets/ 디렉토리에서 검색
                assets_dir = self.remotion_dir / "public" / "assets"
                candidate = assets_dir / bgm_resolved.name.replace(" ", "_")
                if candidate.exists():
                    bgm_resolved = candidate
            if bgm_resolved.exists():
                bgm = {"path": str(bgm_resolved.resolve()), "volume": bgm_volume, "loop": True}

        # designTokens 로드: 파라미터 > design_tokens.json 파일 > 없음
        resolved_tokens = design_tokens
        if not resolved_tokens:
            tokens_file = output_dir / "design_tokens.json"
            if tokens_file.exists():
                with open(tokens_file, "r", encoding="utf-8") as f:
                    resolved_tokens = json.load(f)

        meta = {
            "topic": topic,
            "resolution": {"width": self.width, "height": self.height},
            "fps": self.fps,
            "subtitleFont": "NotoSansKR",
            "vizFont": "GriunPolFairness",
        }
        if resolved_tokens:
            meta["designTokens"] = resolved_tokens

        manifest = {
            "meta": meta,
            "scenes": scene_entries,
            "bgm": bgm,
            "subtitleConfig": {
                "visible": True,
                "fontFamily": "'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif",
                "fontSize": 44,
                "fontWeight": 700,
                "color": "white",
                "strokeColor": "#3D3B2F",
                "strokeWidth": 0,
                "keywordColor": "#F7D94C",
                "keywordStrokeColor": "#5A4B00",
                "bottomOffset": 80,
                "maxWidth": "85%",
                "lineHeight": 1.5,
            },
        }

        manifest_path = output_dir / "remotion_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        total_duration = sum(e["audioDurationSec"] for e in scene_entries)
        print(f"  Remotion manifest: {len(scene_entries)}씬, {total_duration:.1f}초")
        return manifest_path

    def render(self, manifest_path: Path, output_path: Path, concurrency: int = 2) -> bool:
        """npx remotion render 호출"""
        if not self.npx_path:
            print("npx를 찾을 수 없습니다.")
            return False
        if not self.remotion_dir.exists():
            print(f"Remotion 디렉토리 없음: {self.remotion_dir}")
            return False

        node_env = self._get_node_env()

        if not (self.remotion_dir / "node_modules").exists():
            npm_path = self.npm_path or "npm"
            subprocess.run(
                [npm_path, "install"], cwd=str(self.remotion_dir),
                capture_output=True, text=True, timeout=120, env=node_env,
            )

        # public/project 심볼릭 링크 (레거시 호환 + 프로젝트별)
        public_dir = self.remotion_dir / "public"
        public_dir.mkdir(exist_ok=True)
        output_dir = manifest_path.parent

        # 프로젝트별 심링크: public/{slug} → output/{slug}/
        project_slug = output_dir.name
        slug_link = public_dir / project_slug
        if not slug_link.exists():
            slug_link.symlink_to(output_dir.resolve())

        # 레거시 호환: public/project → output/{slug}/
        project_link = public_dir / "project"
        if project_link.is_symlink() or project_link.exists():
            project_link.unlink()
        project_link.symlink_to(output_dir.resolve())

        # 상대경로 manifest 생성
        with open(manifest_path, "r", encoding="utf-8") as f:
            render_manifest = json.load(f)

        output_abs = str(output_dir.resolve())

        def _to_relative(abs_path: str) -> str:
            if abs_path and abs_path.startswith(output_abs):
                return "project" + abs_path[len(output_abs):]
            return abs_path

        for scene in render_manifest.get("scenes", []):
            for key in ("imagePath", "audioPath"):
                scene[key] = _to_relative(scene.get(key, ""))

        public_abs = str(public_dir.resolve())

        def _to_public_relative(abs_path: str) -> str:
            """public/ 디렉토리 기준 상대경로 변환"""
            if abs_path and abs_path.startswith(public_abs):
                return abs_path[len(public_abs) + 1:]  # "assets/file.mp3"
            return _to_relative(abs_path)

        bgm = render_manifest.get("bgm")
        if bgm and bgm.get("path"):
            bgm["path"] = _to_public_relative(bgm["path"])

        # 레거시 경로
        render_manifest_path = public_dir / "manifest.json"
        with open(render_manifest_path, "w", encoding="utf-8") as f:
            json.dump(render_manifest, f, ensure_ascii=False, indent=2)

        # 프로젝트별 매니페스트 (manifests/{slug}.json)
        manifests_dir = public_dir / "manifests"
        manifests_dir.mkdir(exist_ok=True)
        slug_manifest = manifests_dir / f"{project_slug}.json"
        with open(slug_manifest, "w", encoding="utf-8") as f:
            json.dump(render_manifest, f, ensure_ascii=False, indent=2)

        cmd = [
            self.npx_path, "remotion", "render",
            "KairosVideo", str(output_path.resolve()),
            "--props", str(render_manifest_path.resolve()),
            "--codec", "h264",
            "--crf", str(self.crf),
            "--concurrency", str(concurrency),
        ]

        try:
            result = subprocess.run(
                cmd, cwd=str(self.remotion_dir),
                capture_output=True, text=True, timeout=1800, env=node_env,
            )
            if result.returncode == 0:
                print(f"  Remotion 렌더링 완료: {output_path}")
                return True
            else:
                print(f"  Remotion 렌더링 실패: {result.stderr[:300]}")
                return False
        except subprocess.TimeoutExpired:
            print("  Remotion 렌더링 타임아웃")
            return False
        except Exception as e:
            print(f"  Remotion 렌더링 오류: {e}")
            return False

    def create_video(
        self, storyboard_path: Path, output_dir: Path,
        output_filename: str = "final_video.mp4",
        bgm_path: Optional[str] = None, bgm_volume: float = 0.1,
        design_spec: Optional[Dict] = None,
        design_tokens: Optional[Dict] = None,
    ) -> RemotionResult:
        """매니페스트 생성 + 렌더링"""
        with open(storyboard_path, "r", encoding="utf-8") as f:
            storyboard = json.load(f)
        topic = storyboard.get("topic", "Untitled")

        manifest_path = self.build_manifest(
            storyboard_path, output_dir,
            bgm_path=bgm_path, bgm_volume=bgm_volume,
            design_spec=design_spec,
            design_tokens=design_tokens,
        )

        output_path = output_dir / output_filename
        success = self.render(manifest_path, output_path)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        total_duration = sum(s["audioDurationSec"] for s in manifest["scenes"])

        result = RemotionResult(
            topic=topic,
            total_scenes=len(manifest["scenes"]),
            total_duration=total_duration,
            resolution=self.resolution,
            fps=self.fps,
            output_path=str(output_path),
            manifest_path=str(manifest_path),
        )

        result_path = output_dir / "video_result.json"
        result.save(result_path)
        return result
