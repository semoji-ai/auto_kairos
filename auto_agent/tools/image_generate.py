"""
FAL 이미지 생성 통합 CLI

auto_kairos_v2/src/tools/fal_image.py에서 이식.
캐릭터, 씬(cinematic/flat), 시각화 배경, 편집 기능 제공.

서브커맨드:
  character      - 캐릭터 이미지 생성 (art_style reference_image 기반)
  scene          - 장면 이미지 생성 (카이로스 구조화된 양식)
  scene-flat     - 평면 연출 장면 이미지 생성
  viz-background - 시각화 배경 이미지 생성
  edit           - 소스 이미지 편집 (Gemini)
"""
import argparse
import base64
import json
import os
import re
import sys
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any


from auto_agent.paths import get_workspace_dir

# .env 자동 로딩 (CLI 실행 시 환경변수 설정)
def _load_dotenv():
    """프로젝트 루트의 .env 파일에서 환경변수를 로드"""
    env_path = get_workspace_dir() / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if key and not os.environ.get(key):
                        os.environ[key] = value

_load_dotenv()

# FAL 클라이언트
try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    FAL_AVAILABLE = False

# FAL_API_KEY → FAL_KEY 자동 매핑 (.env 호환)
if not os.environ.get("FAL_KEY") and os.environ.get("FAL_API_KEY"):
    os.environ["FAL_KEY"] = os.environ["FAL_API_KEY"]


# ── 상수 ──

ENDPOINT_GENERATE = "fal-ai/nano-banana-2"
ENDPOINT_EDIT = "fal-ai/nano-banana-2/edit"
ENDPOINT_CHARACTER = "fal-ai/nano-banana-2/edit"

PROJECT_ROOT = get_workspace_dir()  # 하위 호환

NO_TEXT_RULES = (
    "**CRITICAL: NO TEXT IN IMAGE**\n"
    "- ZERO text: NO Korean, NO English, NO Chinese, NO Japanese, NO alphabet\n"
    "- ZERO captions, subtitles, titles, labels, signs, banners, text overlays\n"
    "- ZERO speech bubbles, dialogue boxes, thought bubbles\n"
    "- ZERO watermarks, signatures, logos with text, credits\n"
    "- ZERO random numbers or percentages\n"
    "- ZERO book covers, documents, screens, newspapers with text\n"
    "- All surfaces must be blank or contain abstract patterns only\n\n"
)

ANATOMY_RULES = (
    "**ANATOMY RULES:**\n"
    "- Each person MUST have exactly 2 arms, 2 legs, 5 fingers per hand\n"
    "- NO extra limbs, NO missing limbs, NO merged body parts\n"
    "- Faces clear, symmetrical, anatomically correct\n"
    "- NO distorted faces, NO melted features, NO extra eyes\n"
    "- Proper human proportions\n"
    "- If drawing crowds, keep them as simple silhouettes in background\n"
    "- Focus detail on 1-3 main characters only\n\n"
)



# ── 유틸리티 ──

def _image_to_data_uri(image_path: str) -> str:
    """이미지 파일을 Data URI로 변환"""
    with open(image_path, "rb") as f:
        image_data = f.read()
    ext = Path(image_path).suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"
    b64 = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _load_art_style(style_path: str) -> Dict[str, Any]:
    """art_style.json 로드. reference_image 상대경로를 절대경로로 해석."""
    with open(style_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # reference_image가 상대경로이면 art_style.json 위치 기준 → 패키지 data 기준 순서로 해석
    ref = data.get("reference_image", "")
    if ref and not Path(ref).is_absolute():
        # 1) art_style.json이 있는 디렉토리 기준
        style_dir = Path(style_path).resolve().parent
        candidate = style_dir / Path(ref).name  # semoji_base.jpg 등
        if candidate.exists():
            data["reference_image"] = str(candidate)
        else:
            # 2) 패키지 데이터 디렉토리 기준
            from auto_agent.paths import get_data_dir
            pkg_candidate = get_data_dir() / ref
            if pkg_candidate.exists():
                data["reference_image"] = str(pkg_candidate)
            else:
                # 3) 워크스페이스 기준 (하위 호환)
                data["reference_image"] = str(PROJECT_ROOT / ref)
    return data


def _get_style_json_str(art_style: dict) -> str:
    """style + technical 객체를 JSON 문자열로 변환 (프롬프트 임베딩용)"""
    style_info = art_style.get("style", {})
    technical = art_style.get("technical", {"no_text": True})
    return json.dumps({"style": style_info, "technical": technical}, ensure_ascii=False)


def _filter_text_descriptions(prompt: str) -> str:
    """텍스트 관련 설명 필터링 — 이미지에 텍스트가 렌더링되지 않도록"""
    logo_protected = {}
    placeholder_idx = [0]

    def protect_logo_text(match):
        start = max(0, match.start() - 20)
        end = min(len(prompt), match.end() + 20)
        context = prompt[start:end]
        if '로고' in context or 'logo' in context.lower():
            ph = f"__LOGO_PROTECTED_{placeholder_idx[0]}__"
            logo_protected[ph] = match.group(0)
            placeholder_idx[0] += 1
            return ph
        return match.group(0)

    filtered = re.sub(r"['\"][^'\"]+['\"]", protect_logo_text, prompt)
    filtered = re.sub(r"['\"][^'\"]+['\"]", "", filtered)

    text_patterns = [
        r"[^.]*글씨[가이]?\s*[^.]*\.",
        r"[^.]*문구[가이]?\s*[^.]*\.",
        r"[^.]*스탬프[가이]?\s*[^.]*\.",
        r"[^.]*적혀\s*있[^.]*\.",
        r"[^.]*쓰[여인]?\s*있[^.]*\.",
        r"[^.]*자막[이가]?\s*[^.]*\.",
        r"[^.]*텍스트[가이]?\s*[^.]*\.",
        r"[^.]*인용문[이가]?\s*[^.]*\.",
    ]
    for pattern in text_patterns:
        filtered = re.sub(pattern, "", filtered, flags=re.IGNORECASE)

    for ph, original in logo_protected.items():
        filtered = filtered.replace(ph, original)

    filtered = re.sub(r"\s+", " ", filtered)
    return filtered.strip()


def _translate_to_english(text: str) -> str:
    """한국어 프롬프트를 영어로 번역 (Gemini API 사용)"""
    try:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            return text

        import google.genai as genai
        client = genai.Client(api_key=google_api_key)

        prompt = (
            "Translate the following Korean image generation prompt to English.\n"
            "Keep the technical terms and style descriptions accurate.\n"
            "Maintain the structure and formatting.\n"
            "Output ONLY the translated text, no explanations.\n\n"
            f"Korean prompt:\n{text}\n\nEnglish translation:"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        translated = response.text.strip()
        if translated:
            return translated
    except Exception:
        pass

    return text


def _enrich_historical_context(prompt: str, historical_period: str) -> str:
    """Gemini로 프롬프트에 시대 고증 디테일을 보강"""
    if not historical_period:
        return prompt

    try:
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            return prompt

        import google.genai as genai
        client = genai.Client(api_key=google_api_key)

        enrichment_prompt = (
            f"You are a historical visual consultant. Given an image generation prompt "
            f"and a historical period, ADD specific period-accurate visual details.\n\n"
            f"Historical period: {historical_period}\n\n"
            f"Original prompt:\n{prompt}\n\n"
            f"RULES:\n"
            f"- ADD period-accurate clothing details (fabric, color, style, accessories)\n"
            f"- ADD period-accurate architecture/furniture/props if background is mentioned\n"
            f"- ADD period-accurate hairstyles and grooming\n"
            f"- ADD 'NO anachronistic objects' constraint\n"
            f"- Keep ALL original prompt instructions intact\n"
            f"- Keep the same language as the original prompt\n"
            f"- Do NOT remove any existing instructions\n"
            f"- Output ONLY the enriched prompt, no explanations\n\n"
            f"Enriched prompt:"
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=enrichment_prompt
        )

        enriched = response.text.strip()
        if enriched:
            return enriched
    except Exception:
        pass

    return prompt


def _save_fal_result(result: dict, output_path: str) -> dict:
    """FAL API 결과에서 이미지를 다운로드하여 저장"""
    images = result.get("images", [])
    if not images:
        return {"success": False, "error": "이미지 생성 결과 없음"}

    image_url = images[0].get("url", "")
    if not image_url:
        return {"success": False, "error": "이미지 URL 없음"}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(image_url, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(resp.content)

    width = images[0].get("width", 0)
    height = images[0].get("height", 0)

    return {
        "success": True,
        "output_path": output_path,
        "width": width,
        "height": height,
    }


def _call_fal(endpoint: str, fal_input: dict) -> dict:
    """FAL API 호출 (subscribe 패턴)"""
    if not FAL_AVAILABLE:
        return {"error": "fal_client 미설치. pip install fal-client"}

    fal_key = os.getenv("FAL_API_KEY", "") or os.getenv("FAL_KEY", "")
    if fal_key:
        os.environ["FAL_KEY"] = fal_key

    result = fal_client.subscribe(endpoint, arguments=fal_input)
    return result


# ── 캐릭터 생성 ──

def generate_character(
    prompt: str,
    output_path: str,
    style_path: str,
    person_photo: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> dict:
    """캐릭터 이미지 생성

    art_style.json의 reference_image를 항상 스타일 베이스로 사용.
    실존 인물이면 person_photo를 두 번째 참조로 추가.

    프롬프트 우선순위:
      1. scene_style_description (스타일 톤)
      2. style JSON 스펙
      3. critical_requirements
      4. 스타일 복사 지시 (눈, 선, 비율 = 반드시 따를 것)
      5. 캐릭터 묘사
      6. NO TEXT (간결하게, 끝에)
    """
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    historical_period = art_style.get("historical_period", "")
    critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

    prompt = _enrich_historical_context(prompt, historical_period)

    # IP-Adapter 이미지 구성
    image_urls = []

    # 1. 스타일 베이스 (항상 포함)
    ref_image = art_style.get("reference_image", "")
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))

    # 2. 인물 참조 (선택)
    if person_photo and Path(person_photo).exists():
        image_urls.append(_image_to_data_uri(person_photo))

    # 프롬프트 구성 — 스타일 우선, NO TEXT는 끝에
    parts = []

    # 1) 스타일 톤 세팅
    if scene_style_desc:
        parts.append(scene_style_desc + "\n\n")

    # 2) 스타일 JSON 스펙
    parts.append(f"Style specification: {style_json_str}\n\n")

    # 3) critical_requirements
    if critical_reqs:
        parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs) + "\n\n")

    # 4) 스타일 복사 지시 — 기준 이미지의 전체 느낌을 자연스럽게 따를 것
    if len(image_urls) >= 2:
        parts.append(
            "**REFERENCE IMAGE GUIDE:**\n"
            "- FIRST image = ART STYLE reference. Match this style:\n"
            "  • Same eye drawing style, line weight, and body proportions\n"
            "  • Same color palette and flat shading approach\n"
            "- SECOND image = PERSON reference for facial features only\n"
            "- Draw the person from the second image IN THE STYLE of the first image\n\n"
        )
    elif len(image_urls) == 1:
        parts.append(
            "**STYLE REFERENCE:**\n"
            "The attached image defines the art style. Match this style:\n"
            "- Same eye drawing style, line weight, and body proportions\n"
            "- Same color palette and flat shading approach\n"
            "- Create a NEW character drawn in this same style\n\n"
        )

    # 5) 캐릭터 묘사
    parts.append(f"Character illustration:\n{prompt}\n\n")

    # 6) NO TEXT (간결하게, 끝에)
    parts.append(
        "No text, letters, numbers, captions, watermarks, or speech bubbles in the image."
    )

    full_prompt = "".join(parts)

    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
    }
    if image_urls:
        fal_input["image_urls"] = image_urls

    result = _call_fal(endpoint, fal_input)
    return _save_fal_result(result, output_path)


def _build_character_fal_input(
    prompt: str,
    style_path: str,
    person_photo: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> tuple[str, dict]:
    """캐릭터 FAL 입력 빌드. generate_character()와 동일한 로직, _call_fal 직전에서 중단.

    Returns:
        (endpoint, fal_input) — fal_queue.submit_batch()에 전달할 값
    """
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    historical_period = art_style.get("historical_period", "")
    critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

    prompt = _enrich_historical_context(prompt, historical_period)
    image_urls = []

    ref_image = art_style.get("reference_image", "")
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))
    if person_photo and Path(person_photo).exists():
        image_urls.append(_image_to_data_uri(person_photo))

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc + "\n\n")
    parts.append(f"Style specification: {style_json_str}\n\n")
    if critical_reqs:
        parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs) + "\n\n")
    if len(image_urls) >= 2:
        parts.append(
            "**REFERENCE IMAGE GUIDE:**\n"
            "- FIRST image = ART STYLE reference. Match this style:\n"
            "  • Same eye drawing style, line weight, and body proportions\n"
            "  • Same color palette and flat shading approach\n"
            "- SECOND image = PERSON reference for facial features only\n"
            "- Draw the person from the second image IN THE STYLE of the first image\n\n"
        )
    elif len(image_urls) == 1:
        parts.append(
            "**STYLE REFERENCE:**\n"
            "The attached image defines the art style. Match this style:\n"
            "- Same eye drawing style, line weight, and body proportions\n"
            "- Same color palette and flat shading approach\n"
            "- Create a NEW character drawn in this same style\n\n"
        )
    parts.append(f"Character illustration:\n{prompt}\n\n")
    parts.append("No text, letters, numbers, captions, watermarks, or speech bubbles in the image.")

    full_prompt = "".join(parts)
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return endpoint, fal_input


# ── 장면 생성 (cinematic) ──

def generate_scene(
    prompt: str,
    output_path: str,
    style_path: str,
    characters: Optional[List[str]] = None,
    characters_info: Optional[str] = None,
    background: Optional[str] = None,
    camera: Optional[str] = None,
    aspect_ratio: str = "16:9",
) -> dict:
    """장면 이미지 생성 (cinematic staging)

    Args:
        prompt: 장면 묘사 (scene_description - 150자+ 인물+동작+배경+분위기)
        characters: 캐릭터 이미지 경로 리스트 (IP-Adapter용)
        characters_info: 구조화된 캐릭터 정보
        background: 배경 정보
        camera: 카메라 정보
    """
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    historical_period = art_style.get("historical_period", "")
    ref_image = art_style.get("reference_image", "")
    critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

    # IP-Adapter 이미지 구성
    image_urls = []
    has_character_refs = False

    if characters and any(Path(c).exists() for c in characters):
        for char_path in characters:
            if Path(char_path).exists():
                image_urls.append(_image_to_data_uri(char_path))
        has_character_refs = True
    if not has_character_refs and ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))

    # 고증 보강 + 텍스트 필터링
    prompt = _enrich_historical_context(prompt, historical_period)
    scene_description = _filter_text_descriptions(prompt)

    # 프롬프트 구성
    parts = []

    # 스타일 scene_style_description 프리펜드 (kairos 방식)
    if scene_style_desc:
        parts.append(scene_style_desc)

    parts.append(style_json_str)

    # critical_requirements 추가 (semoji 등)
    if critical_reqs:
        parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs))

    parts.append(scene_description)

    if has_character_refs:
        parts.append(
            "**Character Reference Rules:**\n"
            "- Use reference images ONLY for face and clothing appearance\n"
            "- Do NOT copy the pose from reference images!\n"
            "- Pose and action must follow the scene description above\n"
            "- Maintain consistent eye, nose, mouth, and body proportions"
        )
    elif image_urls:
        parts.append(
            "**⚠️ IMPORTANT: DO NOT COPY THE CHARACTER FROM THE REFERENCE!**\n"
            "[STYLE ONLY] The attached reference image is ONLY for art style reference.\n"
            "- ✅ COPY: Color palette, line style, lighting, texture, shading\n"
            "- ❌ NEVER COPY: Any person, character, figure, face from the reference\n"
            "- Create entirely NEW characters based on the scene description"
        )

    structured_lines = []
    if characters_info:
        structured_lines.append(f"Character: {characters_info}")
    if background:
        structured_lines.append(f"Background: {background}")
    if camera:
        structured_lines.append(f"Camera: {camera}")
    if structured_lines:
        if has_character_refs:
            structured_lines.append(
                "**Important: Maintain character body proportions, natural human body proportions, "
                "refer to reference image for each character's face, "
                "pose/action is based on scene description"
            )
        else:
            structured_lines.append(
                "**Important: Maintain natural human body proportions, "
                "pose/action is based on scene description"
            )
        parts.append("\n".join(structured_lines))

    parts.append(
        "**Composition rules:**\n"
        "- Do NOT repeat the same composition (e.g., sitting at table facing camera)\n"
        "- Vary gaze direction (window, door, other characters)\n"
        "- Show character interaction (talking, gesturing, looking at each other)"
    )

    if has_character_refs:
        parts.append(
            f"aspect ratio {aspect_ratio}\n"
            "No text or speech bubbles.\n"
            "Draw characters with consistent proportions.\n"
            "Match the overall drawing style to the character reference images."
        )
    else:
        parts.append(
            f"aspect ratio {aspect_ratio}\n"
            "No text or speech bubbles.\n"
            "Draw characters with consistent proportions.\n"
            "Match the overall drawing style to the attached reference image."
        )

    parts.append(
        "IMPORTANT: Do NOT include any text, letters, numbers, words, captions, watermarks, "
        "signatures, or any written characters in the image. The image must be completely text-free."
    )

    full_prompt = "\n\n".join(parts)
    full_prompt = _translate_to_english(full_prompt)

    # nano-banana: 캐릭터 ref가 있으면 /edit, 없으면 기본 /generate
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
    }
    if image_urls:
        fal_input["image_urls"] = image_urls

    result = _call_fal(endpoint, fal_input)
    return _save_fal_result(result, output_path)


# generate_scene_flat은 cinematic으로 통일 — 하위 호환용 alias
generate_scene_flat = generate_scene


def _build_scene_fal_input(
    scene: dict,
    project_dir: Path,
    char_paths: Optional[Dict[str, Optional[Path]]] = None,
    style_path: Optional[str] = None,
) -> tuple[str, dict]:
    """씬 FAL 입력 빌드. (endpoint, fal_input) 반환.

    Args:
        scene: scene_specs.json의 씬 딕셔너리
        project_dir: 프로젝트 디렉토리 (art_style.json 경로 탐색용)
        char_paths: {char_id: Path | None} — None이면 해당 캐릭터 참조 없이 생성
        style_path: art_style.json 경로. None이면 project_dir/art_style.json 사용.
    """
    if style_path is None:
        style_path = str(project_dir / "art_style.json")

    image_asset = scene.get("imageAsset") or {}
    scene_type  = image_asset.get("sceneType", "")

    # viz_background 타입: 배경 전용 빌드
    if scene_type == "viz_background":
        creative = scene.get("creative") or {}
        viz      = scene.get("visualization") or {}
        return _build_viz_fal_input(
            viz_title=image_asset.get("prompt") or creative.get("headline", scene.get("title", "")),
            viz_type=viz.get("type", ""),
            thematic_context=scene.get("narration", ""),
            style_path=style_path,
            aspect_ratio=image_asset.get("aspectRatio", "16:9"),
        )

    # 일반 씬
    _ia = scene.get("imageAsset") or {}
    prompt          = _ia.get("prompt") or _ia.get("query") or scene.get("narration", "")
    characters_info = _ia.get("charactersInfo", "")
    background      = _ia.get("background", "")
    camera          = _ia.get("camera", "")
    aspect_ratio    = image_asset.get("aspectRatio", "16:9")

    # 유효한 캐릭터 경로만 추출
    char_path_strs: list[str] = []
    if char_paths:
        for cid, cp in char_paths.items():
            if cp and Path(cp).exists():
                char_path_strs.append(str(cp))

    # cinematic 통일 (flat staging 제거됨)
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    historical_period = art_style.get("historical_period", "")
    critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])
    ref_image = art_style.get("reference_image", "")

    image_urls = [_image_to_data_uri(cp) for cp in char_path_strs]
    is_base_ref = False
    if not image_urls and ref_image and Path(ref_image).exists():
        image_urls = [_image_to_data_uri(ref_image)]
        is_base_ref = True

    prompt = _enrich_historical_context(prompt, historical_period)
    scene_desc = _filter_text_descriptions(prompt)

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc)
    parts.append(style_json_str)
    if critical_reqs:
        parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs))
    parts.append(scene_desc)
    if is_base_ref:
        parts.append(
            "**🚫 CRITICAL: Reference Image Restrictions 🚫**\n"
            "The attached reference image is ONLY for art style reference.\n"
            "- ✅ COPY: Color palette, lighting, texture, brush strokes, mood, art technique\n"
            "- ❌ NEVER COPY: Any person, character, hairstyle, clothing, face, or body from the reference image\n"
            "- ❌ ABSOLUTELY FORBIDDEN: Do NOT use the reference image character's hairstyle, outfit, or appearance\n"
            "- Create completely NEW characters based on the scene description"
        )
    elif char_path_strs:
        parts.append(
            "**Character Reference Rules:**\n"
            "- Use reference images for face and clothing appearance\n"
            "- Do NOT copy the pose from reference images!\n"
            "- Maintain consistent eye, nose, mouth, and body proportions"
        )
    struct = []
    if characters_info:
        struct.append(f"Character: {characters_info}")
    if background:
        struct.append(f"Background: {background}")
    if camera:
        struct.append(f"Camera: {camera}")
    if struct:
        if char_path_strs:
            struct.append(
                "**Important: Maintain character body proportions, "
                "refer to reference image for each character's face"
            )
        parts.append("\n".join(struct))
    parts.append(
        "IMPORTANT: Do NOT include any text, letters, numbers, words, captions, "
        "watermarks, signatures, or any written characters in the image."
    )
    full_prompt = _translate_to_english("\n\n".join(parts))
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return endpoint, fal_input


def _build_viz_fal_input(
    viz_title: str,
    viz_type: str,
    thematic_context: str,
    style_path: str,
    aspect_ratio: str = "16:9",
) -> tuple[str, dict]:
    """viz_background 씬 FAL 입력 빌드. generate_viz_background()와 동일 로직."""
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    ref_image = art_style.get("reference_image", "")

    image_urls = []
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))

    viz_mood = {
        "bar_chart": "abstract shapes suggesting comparison and scale",
        "line_chart": "flowing lines and gradual progression",
        "pie_chart": "circular patterns and proportional segments",
        "timeline": "sequential flow and historical progression",
        "table_view": "organized grid-like patterns",
        "tech_tree": "branching connections and nodes",
        "compare_card": "balanced duality, two sides",
        "quote_card": "contemplative, open space for text",
        "list_card": "organized, structured layout atmosphere",
        "numbered_list": "sequential, step-by-step visual rhythm",
        "icon_grid": "organized grid with thematic elements",
        "icon_flow": "flowing process, connected steps",
    }.get(viz_type, "abstract decorative background")

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc)
    parts.append(style_json_str)
    parts.append(
        f"Create a decorative BACKGROUND illustration for a data visualization.\n\n"
        f"**Topic:** {viz_title}\n"
        f"**Context:** {thematic_context}\n"
        f"**Visual mood:** {viz_mood}\n\n"
        "**CRITICAL BACKGROUND REQUIREMENTS:**\n"
        "- This is a BACKGROUND image — data/charts will be overlaid on top\n"
        "- Use SOFT, MUTED, slightly desaturated colors\n"
        "- Keep the CENTER area relatively EMPTY and SIMPLE\n"
        "- Place decorative elements toward EDGES and CORNERS\n"
        "- NO specific characters in focus, NO faces\n"
        "- Think of it like a soft, blurred backdrop or wallpaper"
    )
    if image_urls:
        parts.append(
            "**STYLE REFERENCE ONLY:**\n"
            "The attached reference image is ONLY for art style.\n"
            "- COPY: Color palette, texture, rendering style\n"
            "- NEVER COPY: Any character, person, figure"
        )
    parts.append(
        f"aspect ratio {aspect_ratio}\n"
        "IMPORTANT: Do NOT include any text, letters, numbers in the image."
    )
    full_prompt = _translate_to_english("\n\n".join(parts))
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return ENDPOINT_EDIT, fal_input


# ── Gemini 편집 ──

def generate_gemini_edit(
    source_path: str,
    output_path: str,
    edit_prompt: str,
    aspect_ratio: str = "16:9",
) -> dict:
    """소스 이미지를 기반으로 edit_prompt에 따라 장면을 변형"""
    if not Path(source_path).exists():
        return {"success": False, "error": f"소스 이미지 없음: {source_path}"}

    source_data_uri = _image_to_data_uri(source_path)

    full_prompt = _translate_to_english(edit_prompt)
    full_prompt += (
        "\n\nIMPORTANT: Do NOT include any text, letters, numbers, words, "
        "captions, watermarks, or any written characters in the image."
    )

    fal_input = {
        "prompt": full_prompt,
        "image_urls": [source_data_uri],
        "aspect_ratio": aspect_ratio,
    }

    result = _call_fal(ENDPOINT_EDIT, fal_input)
    return _save_fal_result(result, output_path)


# ── 시각화 배경 이미지 ──

def generate_viz_background(
    viz_title: str,
    viz_type: str,
    thematic_context: str,
    output_path: str,
    style_path: str,
    aspect_ratio: str = "16:9",
) -> dict:
    """시각화 씬의 아트스타일 배경 이미지 생성

    차트/타임라인 씬에 아트스타일에 맞는 분위기 있는
    배경 이미지를 생성한다. 텍스트/수치는 Remotion이 오버레이.
    """
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    ref_image = art_style.get("reference_image", "")

    image_urls = []
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))

    viz_mood = {
        "bar_chart": "abstract shapes suggesting comparison and scale",
        "line_chart": "flowing lines and gradual progression",
        "pie_chart": "circular patterns and proportional segments",
        "timeline": "sequential flow and historical progression",
        "table_view": "organized grid-like patterns",
        "tech_tree": "branching connections and nodes",
        "compare_card": "balanced duality, two sides",
        "quote_card": "contemplative, open space for text",
        "list_card": "organized, structured layout atmosphere",
        "numbered_list": "sequential, step-by-step visual rhythm",
        "icon_grid": "organized grid with thematic elements",
        "icon_flow": "flowing process, connected steps",
    }.get(viz_type, "abstract decorative background")

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc)
    parts.append(style_json_str)
    parts.append(
        f"Create a decorative BACKGROUND illustration for a data visualization.\n\n"
        f"**Topic:** {viz_title}\n"
        f"**Context:** {thematic_context}\n"
        f"**Visual mood:** {viz_mood}\n\n"
        "**CRITICAL BACKGROUND REQUIREMENTS:**\n"
        "- This is a BACKGROUND image — data/charts will be overlaid on top\n"
        "- Use SOFT, MUTED, slightly desaturated colors\n"
        "- Keep the CENTER area relatively EMPTY and SIMPLE\n"
        "- Place decorative elements toward EDGES and CORNERS\n"
        "- Abstract, atmospheric, or environmental scene related to the topic\n"
        "- NO specific characters in focus, NO faces\n"
        "- Think of it like a soft, blurred backdrop or wallpaper\n"
        "- Overall mood: calm, professional, thematic"
    )

    if image_urls:
        parts.append(
            "**⚠️ STYLE REFERENCE ONLY:**\n"
            "The attached reference image is ONLY for art style.\n"
            "- ✅ COPY: Color palette, texture, rendering style, artistic technique\n"
            "- ❌ NEVER COPY: Any character, person, figure, or specific scene\n"
            "- Create an entirely NEW atmospheric background in this art style"
        )

    parts.append(
        f"aspect ratio {aspect_ratio}\n"
        "IMPORTANT: Do NOT include any text, letters, numbers, words, captions, "
        "watermarks, signatures, or any written characters in the image. "
        "The image must be completely text-free."
    )

    full_prompt = "\n\n".join(parts)
    full_prompt = _translate_to_english(full_prompt)

    fal_input = {
        "prompt": full_prompt,
        "aspect_ratio": aspect_ratio,
    }
    if image_urls:
        fal_input["image_urls"] = image_urls

    result = _call_fal(ENDPOINT_EDIT, fal_input)
    return _save_fal_result(result, output_path)


# ── CLI 진입점 ──

def _cli_main():
    parser = argparse.ArgumentParser(
        description="FAL 이미지 생성 통합 CLI (character/scene/viz-background/edit)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # character
    p_char = subparsers.add_parser("character", help="캐릭터 이미지 생성")
    p_char.add_argument("--prompt", required=True, help="캐릭터 프롬프트")
    p_char.add_argument("--output", required=True, help="출력 파일 경로")
    p_char.add_argument("--style", required=True, help="art_style.json 경로")
    p_char.add_argument("--person-photo", default=None, help="실존 인물 참조 사진 경로")
    p_char.add_argument("--aspect-ratio", default="1:1", help="종횡비 (기본 1:1)")

    # scene
    p_scene = subparsers.add_parser("scene", help="장면 이미지 생성 (cinematic)")
    p_scene.add_argument("--prompt", required=True, help="장면 묘사 (scene_description)")
    p_scene.add_argument("--output", required=True, help="출력 파일 경로")
    p_scene.add_argument("--style", required=True, help="art_style.json 경로")
    p_scene.add_argument("--characters", default=None,
                         help="캐릭터 이미지 경로 (쉼표 구분)")
    p_scene.add_argument("--characters-info", default=None,
                         help='구조화된 캐릭터 정보. 예: "Santiago(raising hand - image1)"')
    p_scene.add_argument("--background", default=None, help="배경 정보")
    p_scene.add_argument("--camera", default=None, help="카메라 정보")
    p_scene.add_argument("--aspect-ratio", default="16:9", help="종횡비 (기본 16:9)")

    # scene-flat
    p_flat = subparsers.add_parser("scene-flat", help="평면 연출 장면 이미지 생성")
    p_flat.add_argument("--prompt", required=True, help="장면 묘사")
    p_flat.add_argument("--output", required=True, help="출력 파일 경로")
    p_flat.add_argument("--style", required=True, help="art_style.json 경로")
    p_flat.add_argument("--characters", default=None, help="캐릭터 이미지 경로 (쉼표 구분)")
    p_flat.add_argument("--characters-info", default=None, help="구조화된 캐릭터 정보")
    p_flat.add_argument("--background", default=None, help="배경 정보")
    p_flat.add_argument("--aspect-ratio", default="16:9", help="종횡비")

    # viz-background
    p_viz = subparsers.add_parser("viz-background", help="시각화 배경 이미지 생성")
    p_viz.add_argument("--title", required=True, help="시각화 제목")
    p_viz.add_argument("--type", required=True, help="시각화 유형 (bar_chart, timeline 등)")
    p_viz.add_argument("--context", required=True, help="주제 맥락")
    p_viz.add_argument("--output", required=True, help="출력 파일 경로")
    p_viz.add_argument("--style", required=True, help="art_style.json 경로")
    p_viz.add_argument("--aspect-ratio", default="16:9", help="종횡비")

    # edit
    p_edit = subparsers.add_parser("edit", help="소스 이미지 편집 (Gemini)")
    p_edit.add_argument("--source", required=True, help="소스 이미지 경로")
    p_edit.add_argument("--output", required=True, help="출력 파일 경로")
    p_edit.add_argument("--prompt", required=True, help="편집 프롬프트")
    p_edit.add_argument("--aspect-ratio", default="16:9", help="종횡비")

    args = parser.parse_args()

    if args.command == "character":
        result = generate_character(
            prompt=args.prompt, output_path=args.output,
            style_path=args.style, person_photo=args.person_photo,
            aspect_ratio=args.aspect_ratio,
        )
    elif args.command == "scene":
        char_list = [c.strip() for c in args.characters.split(",")] if args.characters else None
        result = generate_scene(
            prompt=args.prompt, output_path=args.output,
            style_path=args.style, characters=char_list,
            characters_info=args.characters_info, background=args.background,
            camera=args.camera, aspect_ratio=args.aspect_ratio,
        )
    elif args.command == "scene-flat":
        char_list = [c.strip() for c in args.characters.split(",")] if args.characters else None
        result = generate_scene_flat(
            prompt=args.prompt, output_path=args.output,
            style_path=args.style, characters=char_list,
            characters_info=args.characters_info, background=args.background,
            aspect_ratio=args.aspect_ratio,
        )
    elif args.command == "viz-background":
        result = generate_viz_background(
            viz_title=args.title, viz_type=args.type,
            thematic_context=args.context, output_path=args.output,
            style_path=args.style, aspect_ratio=args.aspect_ratio,
        )
    elif args.command == "edit":
        result = generate_gemini_edit(
            source_path=args.source, output_path=args.output,
            edit_prompt=args.prompt, aspect_ratio=args.aspect_ratio,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("success", False):
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
