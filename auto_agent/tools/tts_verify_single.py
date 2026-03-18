"""
단일 씬 TTS 검증 도구.

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.tts_verify_single {scene_number}

Gemini로 TTS 오디오를 트랜스크립션하고 원본과 비교.
"""
import json
import os
import sys
from pathlib import Path
from difflib import SequenceMatcher

from dotenv import load_dotenv


def verify_scene(project_dir: Path, scene_number: int) -> dict:
    """단일 씬의 TTS 검증."""
    load_dotenv(project_dir.parent / ".env")

    # 원본 나레이션 읽기
    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        return {"scene": scene_number, "error": "scene_specs.json 없음"}

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scene = None
    for s in specs.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            scene = s
            break
    if not scene:
        return {"scene": scene_number, "error": f"씬 {scene_number} 없음"}

    original = scene.get("narration_tts", scene.get("narration", ""))
    if not original:
        return {"scene": scene_number, "verdict": "skip", "reason": "나레이션 없음"}

    # 오디오 파일 확인
    audio_path = project_dir / "audio" / f"scene_{scene_number:03d}.mp3"
    if not audio_path.exists():
        return {"scene": scene_number, "error": f"오디오 없음: {audio_path.name}"}

    # Gemini 트랜스크립션
    transcribed = _transcribe_with_gemini(audio_path)
    if transcribed is None:
        return {"scene": scene_number, "error": "Gemini 트랜스크립션 실패"}

    # 비교
    ratio = SequenceMatcher(None, original, transcribed).ratio()
    errors = _find_errors(original, transcribed)
    verdict = "pass" if ratio >= 0.90 else "fail"

    return {
        "scene": scene_number,
        "original": original,
        "transcribed": transcribed,
        "match_ratio": round(ratio, 4),
        "errors": errors,
        "verdict": verdict,
    }


def _transcribe_with_gemini(audio_path: Path) -> str:
    """Gemini로 오디오 트랜스크립션."""
    try:
        import google.genai as genai

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        # 오디오 파일 업로드
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "parts": [
                        {"text": "이 한국어 오디오를 정확하게 받아쓰기해주세요. 텍스트만 출력하고 다른 설명은 하지 마세요."},
                        {"inline_data": {"mime_type": "audio/mpeg", "data": __import__("base64").b64encode(audio_data).decode()}},
                    ]
                }
            ],
        )

        return response.text.strip()
    except Exception as e:
        print(f"Gemini 에러: {e}", file=sys.stderr)
        return None


def _find_errors(original: str, transcribed: str) -> list:
    """원본과 트랜스크립션 차이 분석."""
    errors = []
    sm = SequenceMatcher(None, original, transcribed)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            errors.append({
                "type": "mispronunciation",
                "original": original[i1:i2],
                "heard": transcribed[j1:j2],
                "position": i1,
            })
        elif tag == "delete":
            errors.append({
                "type": "omission",
                "original": original[i1:i2],
                "position": i1,
            })
        elif tag == "insert":
            errors.append({
                "type": "addition",
                "heard": transcribed[j1:j2],
                "position": i1,
            })
    return errors


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: tts_verify_single <scene_number>"}))
        sys.exit(1)

    scene_num = int(sys.argv[1])
    project_name = os.environ.get("PROJECT_NAME", "")

    # 프로젝트 디렉토리 찾기
    from auto_agent.paths import get_workspace_dir
    workspace = get_workspace_dir()
    project_dir = workspace / "output" / project_name
    if not project_dir.exists():
        print(json.dumps({"error": f"프로젝트 디렉토리 없음: {project_dir}"}))
        sys.exit(1)

    result = verify_scene(project_dir, scene_num)
    print(json.dumps(result, ensure_ascii=False, indent=2))
