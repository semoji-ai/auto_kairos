"""
단일 씬 TTS 재생성 도구.

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.tts_regenerate {scene_number} [corrected_text]

해당 씬의 TTS만 재생성. corrected_text가 있으면 발음 교정된 텍스트로 생성.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def regenerate_tts(project_dir: Path, scene_number: int, corrected_text: str = None) -> dict:
    """단일 씬 TTS 재생성."""
    load_dotenv(project_dir.parent / ".env")

    # scene_specs에서 나레이션 텍스트 가져오기
    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        return {"success": False, "error": "scene_specs.json 없음"}

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scene = None
    for s in specs.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            scene = s
            break
    if not scene:
        return {"success": False, "error": f"씬 {scene_number} 없음"}

    text = corrected_text or scene.get("narration_tts", scene.get("narration", ""))
    if not text:
        return {"success": False, "error": "나레이션 텍스트 없음"}

    # corrected_text가 제공되면 scene_specs 업데이트
    if corrected_text:
        scene["narration_tts"] = corrected_text
        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    # ElevenLabs TTS 생성
    try:
        from auto_agent.tools.elevenlabs_tts import generate_speech

        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")
        if not voice_id:
            return {"success": False, "error": "ELEVENLABS_VOICE_ID 미설정"}

        output_path = project_dir / "audio" / f"scene_{scene_number:03d}.mp3"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 기존 파일 백업
        if output_path.exists():
            backup = output_path.with_suffix(".mp3.bak")
            output_path.rename(backup)

        result = generate_speech(
            text=text,
            voice_id=voice_id,
            output_path=str(output_path),
        )

        if output_path.exists():
            size = output_path.stat().st_size
            return {
                "success": True,
                "scene": scene_number,
                "text_used": text[:100] + "..." if len(text) > 100 else text,
                "output_path": str(output_path),
                "size_bytes": size,
            }
        else:
            return {"success": False, "error": "TTS 파일 생성 실패"}

    except ImportError:
        # elevenlabs_tts 모듈이 없으면 generate_tts.py의 함수 사용
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.generate_tts",
                 "--scene", str(scene_number)],
                cwd=str(project_dir.parent),
                env={**os.environ, "PROJECT_NAME": project_dir.name},
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                return {"success": True, "scene": scene_number, "method": "generate_tts script"}
            else:
                return {"success": False, "error": result.stderr[:200]}
        except Exception as e:
            return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tts_regenerate <scene_number> [corrected_text]"}))
        sys.exit(1)

    scene_num = int(sys.argv[1])
    corrected = sys.argv[2] if len(sys.argv) > 2 else None
    project_name = os.environ.get("PROJECT_NAME", "")

    from auto_agent.paths import get_workspace_dir
    workspace = get_workspace_dir()
    project_dir = workspace / "output" / project_name
    if not project_dir.exists():
        print(json.dumps({"error": f"프로젝트 디렉토리 없음: {project_dir}"}))
        sys.exit(1)

    result = regenerate_tts(project_dir, scene_num, corrected)
    print(json.dumps(result, ensure_ascii=False, indent=2))
