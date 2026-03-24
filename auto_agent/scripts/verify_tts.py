"""
TTS Verification Script
Uses Google Gemini to transcribe TTS audio and compare with original narration.
Detects pronunciation errors by finding mismatches.
"""
import json
import os
import sys
import re
import time
from pathlib import Path
from difflib import SequenceMatcher

from dotenv import load_dotenv

from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")

from auto_agent.scripts.project_paths import get_project_dir


# 영어->한국어 발음 동의어 (비교 시 동일한 것으로 취급)
EQUIV_MAP = {
    's&p': '에스앤피', 's&p500': '에스앤피오백', 'snp': '에스앤피',
    'snp500': '에스앤피오백', 'sp': '에스앤피', 'sp500': '에스앤피오백',
    'spiva': '스피바',
    'etf': '이티에프', 'tiger': '타이거', 'kodex': '코덱스',
    'fomo': '포모', 'morgan': '모건', 'jpmorgan': '제이피모건',
    'vanguard': '뱅가드', 'voo': '브이오오',
    'tr': '티알', 'isa': '아이에스에이', 'irp': '아이알피',
    'it': '아이티', 'ai': '에이아이', 'gpt': '지피티',
    '100': '백', '200': '이백', '300': '삼백', '400': '사백',
    '500': '오백', '600': '육백', '700': '칠백', '800': '팔백',
    '900': '구백', '1000': '천',
}


def normalize_text(text: str) -> str:
    """정규화: 영어->한국어 동의어 변환 + 공백/구두점 제거."""
    text = text.lower()
    # 영어 표현을 한국어 발음으로 치환
    for eng, kor in sorted(EQUIV_MAP.items(), key=lambda x: -len(x[0])):
        text = text.replace(eng, kor)
    text = re.sub(r'[.,!?"\'\-\u2014\u2026:;\u00B7\u201C\u201D\u300C\u300D~+]', '', text)
    text = re.sub(r'\s+', '', text)
    return text


def find_mismatches(original: str, transcribed: str) -> list:
    """두 텍스트를 비교해서 불일치 구간을 추출."""
    orig_norm = normalize_text(original)
    trans_norm = normalize_text(transcribed)

    matcher = SequenceMatcher(None, orig_norm, trans_norm)
    mismatches = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ('replace', 'insert', 'delete'):
            orig_chunk = orig_norm[i1:i2] if tag != 'insert' else ''
            trans_chunk = trans_norm[j1:j2] if tag != 'delete' else ''
            # 너무 짧은 차이는 무시 (1글자 차이 = 사소한 차이)
            if len(orig_chunk) <= 1 and len(trans_chunk) <= 1:
                continue
            mismatches.append({
                'type': tag,
                'original': orig_chunk,
                'transcribed': trans_chunk,
                'position': i1,
            })

    return mismatches


def compute_similarity(original: str, transcribed: str) -> float:
    """두 텍스트의 유사도 (0~1)."""
    orig_norm = normalize_text(original)
    trans_norm = normalize_text(transcribed)
    return SequenceMatcher(None, orig_norm, trans_norm).ratio()


def transcribe_with_gemini(client, audio_path: Path, narration: str) -> str:
    """Gemini로 오디오 파일을 트랜스크립션."""
    from google.genai import types

    # 오디오 파일 업로드
    uploaded = client.files.upload(file=audio_path)

    prompt = f"""이 한국어 오디오를 정확하게 받아적어주세요.
- 들리는 그대로 한국어로 적어주세요.
- 숫자, 영어 발음도 들리는 대로 한국어로 적어주세요.
- 문장부호 없이 텍스트만 적어주세요.

참고용 원본 텍스트 (발음이 다를 수 있으니 실제 들리는 소리를 우선해서 적어주세요):
{narration}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=uploaded.uri)),
                    types.Part(text=prompt),
                ]
            )
        ],
    )

    return response.text.strip()


def main(project_dir=None):
    from google import genai

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    if project_dir is None:
        project_dir = get_project_dir()
    else:
        project_dir = Path(project_dir)
    scene_specs_path = project_dir / "scene_specs.json"
    if not scene_specs_path.exists():
        print(f"ERROR: {scene_specs_path} 없음")
        sys.exit(1)

    AUDIO_DIR = project_dir / "audio"

    with open(scene_specs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data["scenes"]
    total = len(scenes)

    results = []
    error_scenes = []

    print(f"Verifying TTS for {total} scenes with Gemini...\n")

    for i, scene in enumerate(scenes):
        num = scene.get("sceneNumber") or scene["scene_number"]
        narration = scene.get("narration", "")
        audio_path = AUDIO_DIR / f"scene_{num:03d}.mp3"

        if not narration.strip() or not audio_path.exists():
            print(f"  [{i+1}/{total}] Scene {num}: SKIP")
            continue

        try:
            transcribed = transcribe_with_gemini(client, audio_path, narration)
            similarity = compute_similarity(narration, transcribed)
            mismatches = find_mismatches(narration, transcribed)

            result = {
                "sceneNumber": num,
                "similarity": round(similarity, 4),
                "mismatches": mismatches,
                "narration": narration,
                "transcribed": transcribed,
            }
            results.append(result)

            status = "OK" if similarity >= 0.95 else "WARN" if similarity >= 0.85 else "ERROR"
            if status != "OK":
                error_scenes.append(num)

            mismatch_summary = ""
            if mismatches:
                mismatch_summary = " | " + ", ".join(
                    f"'{m['original']}'->'{m['transcribed']}'" for m in mismatches[:3]
                )

            print(f"  [{i+1}/{total}] Scene {num}: {status} (sim={similarity:.2%}){mismatch_summary}")

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"  [{i+1}/{total}] Scene {num}: ERROR - {e}")
            time.sleep(2)

    # 결과 저장
    output_path = project_dir / "tts_verification.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(results),
            "errors": error_scenes,
            "results": results,
        }, f, ensure_ascii=False, indent=2)

    # 요약 출력
    print(f"\n{'='*60}")
    print(f"TTS Verification Complete")
    print(f"{'='*60}")
    print(f"Total: {len(results)} scenes")

    ok = sum(1 for r in results if r["similarity"] >= 0.95)
    warn = sum(1 for r in results if 0.85 <= r["similarity"] < 0.95)
    err = sum(1 for r in results if r["similarity"] < 0.85)
    print(f"  OK (>=95%): {ok}")
    print(f"  WARN (85-95%): {warn}")
    print(f"  ERROR (<85%): {err}")

    if error_scenes:
        print(f"\nProblem scenes: {error_scenes}")

    # 불일치 상세 출력
    problem_results = [r for r in results if r["mismatches"]]
    if problem_results:
        print(f"\n{'='*60}")
        print("Mismatch Details:")
        print(f"{'='*60}")
        for r in problem_results:
            if r["similarity"] >= 0.95:
                continue
            print(f"\n  Scene {r['sceneNumber']} (sim={r['similarity']:.2%}):")
            for m in r["mismatches"]:
                print(f"    {m['type']}: '{m['original']}' -> '{m['transcribed']}'")

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    project_dir = os.environ.get("PROJECT_DIR")
    if not project_dir:
        project_name = os.environ.get("PROJECT_NAME", "")
        if project_name:
            try:
                from auto_agent.db.project_manager import ProjectManager
                pm = ProjectManager()
                project = pm.resolve_project(project_name)
                if project:
                    project_dir = project["output_dir"]
            except Exception:
                pass
            if not project_dir:
                from auto_agent.paths import get_workspace_dir
                project_dir = str(get_workspace_dir() / "output" / project_name)
    if project_dir:
        main(project_dir)
    else:
        print("Usage: verify_tts.py (set PROJECT_DIR or PROJECT_NAME)")
        sys.exit(1)
