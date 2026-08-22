"""이미지 생성 — codex CLI image_gen.py(실 gpt-image) 호출 + 재시도 + 복사가드 + 버전.
⚠️ 헤드리스 codex exec의 built-in image_gen은 실제 생성을 안 함(stale 복사/코드드로잉) → CLI만 사용.
참조 메모리 [[feedback_codex_image_generation_cli_rule]]."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend import env
from backend import fal_api
from backend import llm
from backend.codex_runner import run_skill  # noqa: F401 — 하위 호환 재export

STYLE_FILE = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "semoji.md"
BASE_IMG = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "semoji_base.jpg"


def load_style() -> str:
    return STYLE_FILE.read_text(encoding="utf-8") if STYLE_FILE.exists() else ""


def base_img() -> Path | None:
    """세모지 베이스 이미지 경로(있으면). scene-image/character-sheet 규칙의 스타일·비율 앵커."""
    return BASE_IMG if BASE_IMG.exists() else None


def versioned_path(images_dir: Path, name: str) -> Path:
    """name이 이미 있으면 _v2,_v3... 으로 (무삭제)."""
    base = images_dir / name
    if not base.exists():
        return base
    stem, ext = name.rsplit(".", 1)
    n = 2
    while (images_dir / f"{stem}_v{n}.{ext}").exists():
        n += 1
    return images_dir / f"{stem}_v{n}.{ext}"


def is_rate_limited(text: str) -> bool:
    t = (text or "").lower()
    return ("rate limit" in t or "rate_limit" in t or "too many requests" in t
            or "429" in t)


def build_image_prompt(image_prompt: str, style_desc: str, rel_out: str,
                       *, has_character_ref: bool = False) -> str:
    """씬 이미지 프롬프트. 세모지 베이스가 항상 첨부된다는 전제(scene-image 규칙).
    has_character_ref=True → 캐릭터 시트(1번)+베이스(2번) / False → 베이스만(인물 사용 금지)."""
    if has_character_ref:
        explainer = (
            "[첨부 이미지]\n"
            "- 1번 캐릭터 시트: 이 인물을 그대로 사용 — 신체 비율·체형·얼굴·헤어·의상을 "
            "100% 동일하게 유지하고, 비율을 바꾸거나 새로 디자인하지 말 것.\n"
            "- 2번(마지막) 세모지 베이스: 이미지 전체의 그림체·색감 기준(베이스 인물 정체성 복사 금지)."
        )
    else:
        explainer = (
            "[첨부 이미지]\n"
            "- 첨부 이미지(세모지 베이스)는 그림체·색감 참고용이다 — "
            "베이스의 인물(사람)은 사용하거나 포함하지 말 것."
        )
    return (
        f"{style_desc}\n\n## 장면\n{image_prompt}\n\n{explainer}\n\n## 생성 지시\n"
        f"image_gen 도구로 위 아트스타일을 적용한 이미지 1장을 생성해 현재 폴더의 {rel_out} 로 저장.\n"
        f"비율을 텍스트로 새로 지정하지 말 것(비율은 첨부 이미지가 정함). "
        f"텍스트 없음. 저장되면 'OK'만 답해."
    )


def build_character_prompt(name: str, looks: str, rel_out: str) -> str:
    """기준 캐릭터 시트 — 세모지 베이스(1번 첨부)를 리스타일(character-sheet 규칙).
    비율·체형·얼굴 구조는 베이스가 정함 — 텍스트로 비율을 지시하지 않는다."""
    return (
        f"첨부된 1번 이미지의 캐릭터를 '{name}'(이)라는 캐릭터로 변경해서 새로 그려줘.\n"
        f"- 신체 비율·체형·얼굴 구조·그림체·포즈·배경은 1번 이미지 그대로 유지.\n"
        f"- 헤어와 의상만 변경: {looks}\n"
        f"비율을 텍스트로 새로 지정하지 말 것. 글자·로고 없음. "
        f"image_gen으로 생성 후 현재 폴더의 {rel_out} 로 저장. 저장되면 'OK'만 답해."
    )


# 전역 동시 이미지 생성 상한 — codex CLI 동시 폭주(rate limit) 방지 큐잉
_GEN_SEMA = threading.BoundedSemaphore(max(1, int(os.environ.get("AK_GEN_CONCURRENCY", "3"))))

# codex CLI image_gen.py 경로(환경변수로 재정의 가능)
_CLI_SCRIPT = Path(os.environ.get("AK_IMAGEGEN_CLI")
                   or (Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
                       / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"))
# 코덱스 exec용 잔존 지시문(저장/‘OK’ 응답 등)을 CLI 프롬프트에서 제거하는 패턴
_BOILERPLATE_RE = re.compile(
    r"(##\s*생성 지시.*$)|(image_gen[^\n]*저장[^\n]*\.?)|(현재 폴더의[^\n]*저장[^\n]*\.?)"
    r"|(저장되면\s*['\"]?OK['\"]?만[^\n]*\.?)",
    re.MULTILINE | re.DOTALL)


def _image_python() -> str:
    """image_gen.py를 돌릴 파이썬(openai 설치 필요). AK_IMAGE_PYTHON > 현재 인터프리터."""
    return os.environ.get("AK_IMAGE_PYTHON") or sys.executable


def _clean_image_prompt(prompt: str) -> str:
    """codex exec 시절 프롬프트의 도구·저장 지시문 제거(CLI는 출력 경로를 인자로 받음)."""
    cleaned = _BOILERPLATE_RE.sub("", prompt or "").strip()
    return cleaned or (prompt or "").strip()


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _run_codex_image(proj_dir: Path, out: Path, prompt: str, *,
                     images=None, retries: int = 2, on_line=None, post=None,
                     size: str = "auto") -> dict:
    """codex CLI image_gen.py로 실제 gpt-image 생성. images 있으면 edit, 없으면 generate.
    출력이 첨부 이미지와 동일(복사)이면 실패 처리(헤드리스 built-in image_gen의 가짜 생성 방지).
    전역 세마포어로 동시 실행 제한."""
    key = env.get_key("OPENAI_API_KEY")
    if not key:
        return {"status": "failed", "error": "OPENAI_API_KEY 없음(auto_kairos .env)"}
    if not _CLI_SCRIPT.is_file():
        return {"status": "failed", "error": f"image_gen CLI 없음: {_CLI_SCRIPT}"}
    out.parent.mkdir(parents=True, exist_ok=True)
    img_list = [str(i) for i in (images or []) if Path(i).is_file()]
    in_md5 = {_md5(Path(i)) for i in img_list}
    clean = _clean_image_prompt(prompt)
    cmd = [_image_python(), str(_CLI_SCRIPT)]
    if img_list:
        cmd += ["edit", "--prompt", clean, "--out", str(out), "--size", size, "--force"]
        for img in img_list:
            cmd += ["--image", img]
    else:
        cmd += ["generate", "--prompt", clean, "--out", str(out), "--size", size, "--force"]
    cenv = dict(os.environ)
    cenv["OPENAI_API_KEY"] = key
    last = ""
    for attempt in range(retries + 1):
        with _GEN_SEMA:
            proc = subprocess.run(cmd, env=cenv, capture_output=True, text=True)
        last = (proc.stdout or "") + "\n" + (proc.stderr or "")
        if on_line:
            for ln in last.splitlines():
                if ln.strip():
                    on_line(ln)
        if proc.returncode == 0 and out.exists():
            if in_md5 and _md5(out) in in_md5:
                last += "\n[copy-guard] 출력이 첨부 이미지와 동일(복사) — 실패 처리"
            else:
                if post:
                    post(out)
                return {"status": "completed", "path": str(out)}
        if is_rate_limited(last) and attempt < retries:
            time.sleep(20 * (attempt + 1))
            continue
        if attempt < retries:
            continue
        break
    reason = "rate_limit" if is_rate_limited(last) else "no_file"
    return {"status": "failed", "error": reason, "log_tail": last[-300:]}


def generate_one(proj_dir: Path, rel_out: str, image_prompt: str,
                 *, subdir: str = "images", retries: int = 2, on_line=None,
                 character_ref=None, extra_refs=None) -> dict:
    """씬/레퍼런스 1장 생성. 세모지 베이스를 항상 첨부(있으면).
    character_ref를 주면 캐릭터 분기(시트+베이스), 없으면 무캐릭터 분기(베이스만, 인물 금지).

    `extra_refs` 는 사람이 모달에서 고른 참조들이다 — 인물 시트 여러 장이나
    앞서 만든 씬 이미지. 캐릭터 분기 판단은 이것들도 함께 본다.
    """
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = versioned_path(out_base, Path(rel_out).name)
    rel = out.relative_to(proj_dir).as_posix()
    images = []
    if character_ref:
        images.append(str(character_ref))
    for r in (extra_refs or []):
        if str(r) not in images:
            images.append(str(r))
    character_ref = character_ref or bool(extra_refs)
    base = base_img()
    if base:
        images.append(str(base))
    prompt = build_image_prompt(image_prompt, load_style(), rel,
                                has_character_ref=bool(character_ref))
    return _run_codex_image(proj_dir, out, prompt, images=images,
                            retries=retries, on_line=on_line)


EDIT_PROMPT = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러와 대화 맥락에 넣으세요.**
경로를 읽고 말로 옮기지 마세요 — 그림 자체가 맥락에 있어야 합니다.

## 고칠 그림

{src}

## 바꿀 것

{instruction}

## 지켜야 할 것

**바꿀 것은 위에 적은 것뿐입니다.** 나머지는 첨부한 그림 그대로 둡니다 —
구도, 인물의 자세와 몸 비율, 얼굴, 옷, 배경, 색, 빛의 방향, 화면 크기까지
전부 원본과 같습니다. 다시 그리는 것이 아니라 **그 그림을 고치는 것**입니다.

말로 그림체를 설명하지 않습니다. 첨부한 그림이 그림체의 기준입니다.

## 가려져 있던 곳이 드러날 때

무언가를 걷어내면 그 아래를 새로 그려야 합니다. **거기서 그림체가 어긋납니다** —
안경을 뺀 자리에 사실적인 눈이 그려져 인물이 딴사람이 된 적이 있습니다(씬 112).

- **눈은 검은 점 하나로만 그립니다.** 흰자와 홍채를 나누지 않습니다
- 주름은 선이 아니라 같은 색의 한 단계 어두운 면으로 넣습니다
- 머리카락은 가닥을 세지 않고 한 덩어리 색면으로 둡니다

드러난 자리는 **같은 그림 안의 다른 인물**이 어떻게 그려졌는지 보고 맞춥니다.

size는 1792x1024입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


def _run_codex_imagegen(out: Path, prompt: str, *, timeout: int = 1200,
                        on_line=None) -> dict:
    """코덱스 내장 `$imagegen` 으로 그린다.

    OpenAI API 를 직접 부르는 CLI 경로(`_run_codex_image`)와 다르다. v3 의
    `scripts/gen_scenes.py` 가 536컷을 이 방식으로 뽑았고, 그림체 기준 시트를
    첨부해 편집하는 흐름이 여기서만 제대로 돈다.

    코덱스가 `$CODEX_HOME/generated_images/` 에 떨어뜨린 것을 프롬프트 지시대로
    목적지에 복사한다 — 경로 인자에 기대지 않는다.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return {"status": "failed", "error": "codex 명령을 찾을 수 없습니다"}
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": f"{timeout}초 초과"}
    log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if on_line:
        for ln in log.splitlines():
            if ln.strip():
                on_line(ln)
    if out.is_file():
        return {"status": "completed", "path": str(out)}
    return {"status": "failed", "error": "no_file", "log_tail": log[-400:]}


def edit_one(proj_dir: Path, rel_out: str, src_rel: str, instruction: str,
             *, subdir: str = "storyboard", retries: int = 2, on_line=None) -> dict:
    """이미 있는 그림을 **참조로 붙여** 지시한 곳만 고친다.

    새로 그리는 것(`generate_one`)과 다르다. 원본을 첨부하고 「바꿀 것 하나」만
    말하므로 구도·자세·화풍이 흔들리지 않는다. 인물 시트를 만들 때 확인된
    방식이다 — 말로 묘사하면 매번 재해석되지만, 그림을 붙여 고치면 그대로 남는다.

    「안경만 빼 줘」처럼 **한 곳만 고치고 싶은데 재생성밖에 없어** 화면이 통째로
    바뀌던 자리를 메운다.
    """
    src = (proj_dir / src_rel).resolve()
    if not src.is_file():
        return {"status": "failed", "error": f"원본 없음: {src_rel}"}
    if not (instruction or "").strip():
        return {"status": "failed", "error": "무엇을 바꿀지 적어야 합니다"}
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = versioned_path(out_base, Path(rel_out).name)
    prompt = EDIT_PROMPT.format(src=str(src), instruction=instruction.strip(),
                                out=str(out))
    return _run_codex_imagegen(out, prompt, on_line=on_line)


def generate_character(proj_dir: Path, name: str, looks: str,
                       *, rel_out: str | None = None, subdir: str = "characters",
                       retries: int = 2, on_line=None) -> dict:
    """기준 캐릭터 시트 생성 — 세모지 베이스를 1번으로 첨부해 리스타일(character-sheet 규칙).
    looks = '갈색 헝클 머리, 크림 오버셔츠+청록 티, 베이지 바지, 흰 운동화, 살짝 미소' 형태."""
    base = base_img()
    if not base:
        return {"status": "failed", "error": "semoji_base.jpg 없음 — 캐릭터 리스타일 불가"}
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = versioned_path(out_base, Path(rel_out or f"char_{name}.png").name)
    rel = out.relative_to(proj_dir).as_posix()
    prompt = build_character_prompt(name, looks, rel)
    return _run_codex_image(proj_dir, out, prompt, images=[str(base)],
                            retries=retries, on_line=on_line)


def build_asset_prompt(image_prompt: str, style_desc: str, rel_out: str,
                       *, has_char_ref: bool = False) -> str:
    """배경/소품 — 첨부 이미지는 그림체 참고용, 인물(사람)·캐릭터는 그리지 않음."""
    refs = "세모지 베이스" + ("와 기준 캐릭터 시트" if has_char_ref else "")
    return (
        f"{style_desc}\n\n## 장면(인물 없음)\n{image_prompt}\n\n"
        f"[첨부 이미지]\n- 첨부 이미지({refs})는 그림체·색감 참고용이다 — "
        f"인물(사람)·캐릭터는 절대 그리지 말 것. 사물/배경만 그린다.\n\n## 생성 지시\n"
        f"image_gen 도구로 위 아트스타일을 적용한 이미지 1장을 생성해 현재 폴더의 {rel_out} 로 저장.\n"
        f"비율을 텍스트로 새로 지정하지 말 것. 텍스트 없음. 저장되면 'OK'만 답해."
    )


def generate_asset(proj_dir: Path, rel_out: str, image_prompt: str,
                   *, char_ref=None, subdir: str = "images",
                   retries: int = 2, on_line=None) -> dict:
    """배경/소품 생성 — 세모지 베이스(+선택 캐릭터 시트)를 스타일 참고로 첨부, 인물은 안 그림."""
    out_base = proj_dir / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    out = versioned_path(out_base, Path(rel_out).name)
    rel = out.relative_to(proj_dir).as_posix()
    images = []
    base = base_img()
    if base:
        images.append(str(base))
    if char_ref:
        images.append(str(char_ref))
    prompt = build_asset_prompt(image_prompt, load_style(), rel, has_char_ref=bool(char_ref))
    return _run_codex_image(proj_dir, out, prompt, images=images or None,
                            retries=retries, on_line=on_line)


_LAYER_SCHEMA = Path(__file__).resolve().parent / "schemas" / "layer_elements.schema.json"


MIN_ELEMENTS = 2        # 씬당 요소 레이어 권장 하한 — 프롬프트가 지시(강제는 안 함: 없는 요소를 지어낼 수 없다).
MAX_ELEMENTS = 10       # 씬당 요소 레이어 상한. 배경 1장을 더해 최대 11레이어.


def apply_element_budget(elements: list) -> dict:
    """요소를 MAX_ELEMENTS개로 자른다. 분석 프롬프트는 요소를 앞→뒤(최상위부터)로 주므로,
    이 절단은 가장 뒤쪽(배경에 가까운) 요소부터 잘라낸다 — 앞을 가리는 요소일수록
    분리 가치가 크므로 우선순위와도 맞는다. 잘린 요소는 배경에 그대로 남는다.
    잘린 것은 dropped로 함께 돌려준다 — 패널이 '예산 초과로 제외'를 보여주고,
    배경 프롬프트는 채택된 것만 제거 대상으로 삼는다(잘린 요소는 배경에 남아야 한다)."""
    els = list(elements or [])
    return {"elements": els[:MAX_ELEMENTS], "dropped": els[MAX_ELEMENTS:]}


def build_layer_analysis_prompt(*, narration: str = "", context: str = "",
                                image_prompt: str = "", neighbors: str = "",
                                briefing: str = "") -> str:
    """레이어 분석 프롬프트 — 사물 분류가 아니라 '이 장면을 어떻게 움직일 것인가'에서 역산한다.

    씬 이미지는 image_prompt로 생성됐고 그 프롬프트는 나레이션을 표현하려고 쓰였다.
    즉 연출 의도가 거기 이미 적혀 있으므로, 그것을 판단의 출발점으로 삼는다."""
    from backend import motion
    return (
        "너는 모션그래픽 연출가다. 첨부한 씬 이미지를 레이어로 분리하려 한다.\n"
        "분류가 목적이 아니다 — **이 장면을 효과적으로 연출하려면 무엇이 따로 떨어져 있어야 하는가**를 판단해라.\n\n"
        f"## 이 그림을 만든 연출 의도(이미지 생성 프롬프트)\n{image_prompt or '(없음)'}\n\n"
        f"## 내레이션\n{narration or '(없음)'}\n\n"
        f"## 씬 맥락\n{context or '(없음)'}\n\n"
        f"## 앞뒤 씬\n{neighbors or '(없음)'}\n\n"
        f"## 프로젝트 브리핑\n{briefing or '(없음)'}\n\n"
        "## 판단 순서\n"
        "1) 이 씬의 연출 의도는 무엇인가 — 위 이미지 생성 프롬프트가 노린 것.\n"
        "2) 그 의도를 살리려면 무엇이 움직이거나 깊이(앞뒤)를 가져야 하는가.\n"
        "3) 그 움직임을 만들려면 어떤 요소가 따로 떨어져 있어야 하는가. 그것만 목록에 넣는다.\n\n"
        f"## 사용 가능한 레이어 모션\n{motion.PRESET_GUIDE}\n"
        f"## 사용 가능한 카메라\n{motion.CAMERA_GUIDE}\n"
        "여기 없는 동작은 구현할 수 없다. 목록 안에서만 연출을 구상해라.\n"
        "**종류별로 실제 적용되는 프리셋:** 인물 레이어는 bob(까딱임 idle)과 zoom_emphasis만 받는다. "
        "사물 레이어는 등장(slide_in/pop/stamp)·강조(zoom_emphasis/shake/wiggle)·지속(drift)·퇴장(exit_fade)을 받는다. "
        "따라서 사물을 분리하는 근거는 셋이다 — 내레이션이 요구하는 등장/제거/움직임, 인물을 가리는 전경(원근 겹침), "
        "카메라가 밀 때의 앞뒤 분리. 이 중 하나도 대지 못하면 배경에 남긴다.\n\n"
        "## 최소성(중요)\n"
        f"요소는 최소 {MIN_ELEMENTS}개, 최대 {MAX_ELEMENTS}개다. 상한은 목표가 아니다 — "
        "연출에 필요한 만큼만 나눈다. 단순한 씬도 인물과 함께 의미 있는 소품·전경 하나는 분리해 "
        "깊이를 만든다. 복잡한 씬(군중·소품 많은 실내)은 내레이션이 요구하는 것부터 채워 "
        "상한 안에서 고른다.\n"
        "각 요소에 intent(그 레이어로 무엇을 할 것인가)를 쓸 수 없다면 분리 근거가 없는 것이므로 "
        "목록에서 빼고 배경에 남긴다.\n\n"
        "## 항상 지키는 규칙\n"
        "- 인물(사람·캐릭터·생명체)은 움직일 것이 없어 보여도 각각 분리한다 — 까딱임(bob)으로 화면이 죽지 않게 한다. "
        "다른 것에 가려져 일부만 보여도 포함한다.\n"
        "- 인물을 앞에서 가리는 전경은 분리해야 앞뒤 겹침이 유지된다.\n"
        "- **내레이션에서 발생(새로 등장)하거나 제거(사라짐)되거나 움직여야 하는 소품은 분리한다** — "
        "등장은 slide_in/pop/stamp, 제거는 exit_fade, 강조는 zoom_emphasis/shake/wiggle로 받는다. "
        "그 동작을 intent에 쓴다.\n"
        "- 정적인 배경·장식은 분리하지 않고 배경에 남긴다.\n"
        "- 앞 씬과 이어지는 샷(continue)이면 레이어 구성을 앞 씬과 맞춰 연결이 끊기지 않게 한다.\n"
        "- 요소는 '가장 앞(최상위)'에서 '가장 뒤' 순서로 나열한다(앞→뒤). **순번 1이 최상위 레이어다.** "
        "인물을 가리는 전경 사물이 그 인물보다 먼저 온다.\n\n"
        "## 각 요소에 쓸 것\n"
        "- name: 짧은 한국어 이름\n"
        "- name_en: 짧은 영어 이름(레이어 분리 모델 프롬프트에 쓴다)\n"
        "- location: 화면 내 위치\n"
        "- kind: 'character' 또는 'object'\n"
        "- reason: 왜 이것이 따로 떨어져야 하는가 — 연출 관점으로 한 줄\n"
        "- intent: 이 레이어로 무엇을 할 것인가 — 위 어휘와 위 제약 안에서. 예: '인물 — bob로 idle', "
        "'앞쪽 책상 — 카메라 푸시인 때 앞뒤 분리'"
    )


def analyze_scene_layers(proj_dir: Path, scene_image: str, *,
                         narration: str = "", context: str = "", image_prompt: str = "",
                         neighbors: str = "", briefing: str = "", on_line=None) -> dict:
    """씬 이미지+연출 맥락을 분석해 '연출에 필요한' 레이어만 선별.
    {elements:[{name,name_en,location,kind,reason,intent}], dropped:[...]} 또는 error."""
    prompt = build_layer_analysis_prompt(narration=narration, context=context,
                                         image_prompt=image_prompt, neighbors=neighbors,
                                         briefing=briefing)
    out_json = proj_dir / ".layer_analysis.json"
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_LAYER_SCHEMA),
                               output_last=str(out_json), images=[scene_image], on_line=on_line)
    if res.get("returncode") != 0 or not out_json.is_file():
        return {"error": "분석 실패", "elements": [], "dropped": []}
    try:
        data = json.loads(out_json.read_text(encoding="utf-8"))
    except Exception:
        return {"error": "분석 결과 파싱 실패", "elements": [], "dropped": []}
    return {**apply_element_budget(data.get("elements", []))}


def _layer_slug(name: str) -> str:
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "_", name).strip("_")
    return s[:24] or "el"


def _archive_prev_layers(out_base: Path, sid: str) -> int:
    """재분리 전, 같은 sid의 기존 레이어(PNG+SVG)를 layers/_prev/ 로 이동(무삭제). 옮긴 개수 반환.
    load_scenes의 _layers glob(layers/*{sid}*.png, 비재귀)은 _prev/ 를 보지 않는다.
    같은 stem의 .svg(Recraft 벡터화 결과)를 남겨두면 재분리 후에도 매니페스트가
    옛 SVG를 새 PNG보다 우선해 골라 낡은 그림이 내보내진다 — PNG와 함께 옮긴다."""
    if not sid:
        return 0
    existing = [p for p in out_base.glob(f"*{sid}*.png") if p.is_file()]
    if not existing:
        return 0
    svgs = [p.with_suffix(".svg") for p in existing]
    svgs = [p for p in svgs if p.is_file()]
    prev = out_base / "_prev"
    prev.mkdir(exist_ok=True)
    moved = 0
    for p in existing + svgs:
        dest = prev / p.name
        n = 2
        while dest.exists():
            dest = prev / f"{p.stem}_p{n}{p.suffix}"
            n += 1
        shutil.move(str(p), str(dest))
        moved += 1
    return moved


ELEMENTS_SIDECAR = "{sid}__elements.json"
KINDS_SIDECAR = "{sid}__kinds.json"


def write_element_specs(out_base: Path, sid: str, specs: list) -> None:
    """요소 명세 사이드카 저장(실패해도 분리 자체는 유효 — 낱개 재생성만 품질이 떨어진다)."""
    try:
        (Path(out_base) / ELEMENTS_SIDECAR.format(sid=sid)).write_text(
            json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _specs_from_filenames(out_base: Path, sid: str) -> list:
    """사이드카가 없는 옛 프로젝트 복원 — 파일명 {sid}__{i}_{슬러그}[_char] + kinds.json.
    location은 복원할 수 없어 빈 문자열(프롬프트 품질만 조금 떨어진다)."""
    kinds = {}
    kp = Path(out_base) / KINDS_SIDECAR.format(sid=sid)
    if kp.is_file():
        try:
            kinds = json.loads(kp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            kinds = {}
    specs = []
    for path in sorted(Path(out_base).glob(f"{sid}__*.png")):
        stem = path.stem
        tail = stem[len(sid) + 2:]                  # "{i}_{슬러그}[_char]" 또는 "bg"
        if tail == "bg" or not tail:
            continue
        num, _, rest = tail.partition("_")
        if not num.isdigit():
            continue
        rest = re.sub(r"_v\d+$", "", rest)          # versioned_path 접미사 제거
        kind = kinds.get(stem) or ("character" if rest.endswith("_char") else "object")
        name = rest[:-5] if rest.endswith("_char") else rest
        name_en = name.replace("_", " ").strip()     # 재분리(regenerate_layer)가 쓸 영문 이름 복원
        specs.append({"layer": stem, "index": int(num), "name": name.replace("_", " ").strip(),
                      "name_en": name_en, "location": "", "kind": kind})
    return specs


def load_element_specs(out_base: Path, sid: str) -> list:
    """요소 명세 목록. 사이드카 우선, 없으면 파일명에서 복원."""
    fp = Path(out_base) / ELEMENTS_SIDECAR.format(sid=sid)
    if fp.is_file():
        try:
            specs = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(specs, list) and specs:
                return specs
        except (json.JSONDecodeError, OSError):
            pass
    return _specs_from_filenames(out_base, sid)


def _stem_of(layer: str) -> str:
    """'layers/ab__0_x.png' | 'ab__0_x.png' | 'ab__0_x' → 'ab__0_x'."""
    return Path(str(layer)).stem


def is_background_layer(layer: str) -> bool:
    return _stem_of(layer).endswith("__bg") or "__bg_v" in _stem_of(layer)


def set_layer_state(proj_dir: Path, sid: str, layer: str, *, hidden=None, removed=None,
                    subdir: str = "layers") -> dict:
    """레이어의 hidden/removed 플래그를 사이드카에 기록한다. 파일은 옮기지 않는다.

    hidden은 패널 미리보기 전용이고 removed만 매니페스트에서 빠진다.
    파일을 그대로 두므로 복구가 플래그를 끄는 것으로 끝난다.
    반환 {ok, layer, hidden, removed} 또는 {error}."""
    out_base = Path(proj_dir) / subdir
    stem = _stem_of(layer)
    if removed and is_background_layer(stem):
        return {"error": "배경 레이어는 제거할 수 없습니다 — 합성의 바탕입니다"}
    if not (out_base / f"{stem}.png").is_file():
        return {"error": f"레이어 없음: {stem}"}
    specs = load_element_specs(out_base, sid)
    target = None
    for s in specs:
        if s.get("layer") == stem:
            target = s
            break
    if target is None:              # 배경 또는 사이드카에 없는 레거시 레이어
        target = {"layer": stem}
        specs.append(target)
    if hidden is not None:
        target["hidden"] = bool(hidden)
    if removed is not None:
        target["removed"] = bool(removed)
    write_element_specs(out_base, sid, specs)
    return {"ok": True, "layer": stem,
            "hidden": bool(target.get("hidden")), "removed": bool(target.get("removed"))}


def regenerate_layer(proj_dir: Path, scene_image: str, sid: str, layer: str, *,
                     subdir: str = "layers", on_event=None) -> dict:
    """레이어 재생성 — layerize는 씬 단위 호출이라 그 씬을 통째로 다시 분리한다.
    기존 요소 명세(이름·종류·의도)를 그대로 다시 써서 같은 구성으로 뽑는다."""
    out_base = Path(proj_dir) / subdir
    specs = load_element_specs(out_base, sid)
    if not specs:
        return {"error": f"요소 명세 없음 — 먼저 레이어 분리 필요: {sid}"}
    # 제거된 요소는 다시 만들지 않는다 — 새 배경판에 그대로 녹아든다.
    # name_en이 없는 항목(배경의 hidden 기록 등)은 분리 대상이 아니다.
    live = [s for s in specs if not s.get("removed") and (s.get("name_en") or "").strip()]
    if not live:
        return {"error": f"분리할 요소가 없습니다 — 모두 제거되었습니다: {sid}"}
    elements = [{"name": s.get("name", ""), "name_en": s.get("name_en", ""),
                 "location": s.get("location", ""), "kind": s.get("kind", "object"),
                 "reason": "", "intent": s.get("intent", "")} for s in live]
    res = split_scene_to_elements(proj_dir, scene_image, sid, elements,
                                  subdir=subdir, on_event=on_event)
    return {"layer": {"name": "씬 재분리", "status": "completed"},
            "layers": res.get("layers", []), "unexpected": res.get("unexpected", [])}


def split_scene_to_elements(proj_dir: Path, scene_image: str, sid: str, elements: list,
                            *, subdir: str = "layers", concurrency: int = 1,
                            prompt: str | None = None, on_event=None) -> dict:
    """씬 이미지를 layerize로 분리해 투명 PNG 여러 장을 저장한다.

    모델이 프롬프트에 적은 이름대로 오려내므로 다시 그리지 않는다 — 원위치가 어긋날 수 없다.
    z_index 0은 요소가 지워지고 메워진 배경판이라 그대로 배경 레이어로 쓴다.
    concurrency는 호출 1회 구조라 쓰지 않으며, 기존 호출부 호환을 위해 남긴다.

    실패 시 기존 레이어를 보존한다 — layerize()가 성공을 반환하기 전까지는 아카이브(이동)하지
    않는다. name_en이 비어 있어 분리 자체가 불가능한 경우도 layerize 호출 전에 걸러낸다 —
    그래야 실패한 재분리가 이미 있던 레이어를 지우지 않는다."""
    out_base = Path(proj_dir) / subdir
    out_base.mkdir(parents=True, exist_ok=True)
    picked = apply_element_budget(elements)["elements"]
    names = [(e.get("name_en") or "").strip() for e in picked]
    names = [n for n in names if n]
    if not names:
        raise fal_api.FalError("분리할 요소 이름 없음 — name_en이 비어 있습니다")
    layers = fal_api.layerize(scene_image, names, prompt=prompt)
    _archive_prev_layers(out_base, sid)     # layerize 성공 후에만 기존 레이어 아카이브(무삭제)

    by_name = {}
    for i, el in enumerate(picked):
        key = (el.get("name_en") or "").strip().lower()
        if key:
            by_name[key] = (i, el)

    matched_keys = set()
    results, specs, kinds, unexpected = [], [], {}, []
    for L in layers:
        nm = L.get("name")
        if nm is None:                       # z0 — 인페인팅된 배경판
            out = versioned_path(out_base, f"{sid}__bg.png")
            out.write_bytes(L["data"])
            results.append({"name": "배경", "rel": out.relative_to(proj_dir).as_posix(),
                            "status": "completed", "z": L["z"], "bbox": None})
            if on_event:
                on_event(results[-1])
            continue
        key = nm.strip().lower()
        hit = by_name.get(key)
        if hit is None or key in matched_keys:
            # 요청 목록에 없거나(모델이 임의로 쪼갬), 이미 매칭된 이름이 중복 반환됨
            # — 어느 쪽이든 두 번째 요소로 취급하지 않는다(사이드카 덮어쓰기 방지)
            unexpected.append(nm)
            if on_event:
                on_event({"name": nm, "status": "unexpected"})
            continue
        matched_keys.add(key)
        i, el = hit
        tag = "_char" if el.get("kind") == "character" else ""
        out = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(nm)}{tag}.png")
        out.write_bytes(L["data"])
        stem = out.stem
        kinds[stem] = el.get("kind", "object")
        specs.append({"layer": stem, "index": i, "name": el.get("name", ""),
                      "name_en": nm, "location": el.get("location", ""),
                      "kind": el.get("kind", "object"), "intent": el.get("intent", ""),
                      "bbox": L.get("bbox"), "z": L.get("z")})
        results.append({"name": el.get("name", nm), "rel": out.relative_to(proj_dir).as_posix(),
                        "status": "completed", "z": L.get("z"), "bbox": L.get("bbox")})
        if on_event:
            on_event(results[-1])

    missing = []
    for key, (i, el) in by_name.items():
        if key not in matched_keys:
            name_en = (el.get("name_en") or "").strip()
            missing.append(name_en)
            if on_event:
                on_event({"name": name_en, "status": "missing"})

    if kinds:   # 빈 kinds로 기존(legacy) kinds.json을 덮어써 자동 bob 근거를 지우지 않는다
        (out_base / KINDS_SIDECAR.format(sid=sid)).write_text(
            json.dumps(kinds, ensure_ascii=False, indent=2), encoding="utf-8")
    write_element_specs(out_base, sid, specs)
    return {"layers": results, "unexpected": unexpected, "missing": missing}


def generate_many(proj_dir: Path, items: list, *, subdir: str = "images",
                  concurrency: int = 4, on_event=None, character_ref=None) -> dict:
    """items=[(rel_out, image_prompt), ...] 를 동시에 생성. 각자 generate_one(백오프 내장).
    character_ref를 주면 모든 항목을 캐릭터 분기로(시트+베이스) 생성.
    반환: {rel_out: result_dict}. concurrency는 최소 1."""
    workers = max(1, int(concurrency))
    results = {}

    def _work(item):
        rel, prompt = item
        res = generate_one(proj_dir, rel, prompt, subdir=subdir, character_ref=character_ref)
        if on_event:
            on_event(rel, res)
        return rel, res

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for rel, res in ex.map(_work, items):
            results[rel] = res
    return results


def split_more_from_bg(proj_dir: Path, sid: str, elements: list, *,
                       subdir: str = "layers", on_event=None) -> dict:
    """**남은 배경판에서 못 뗀 요소를 더 떼어낸다.**

    씨드림은 한 번에 여러 요소를 겨루게 하면 옅거나 바닥에 이어진 것을 놓친다
    — 연기, 전경의 바위·풀밭이 그랬고, 경쟁이 심하면 인물마저 빠진다
    (씬 103·106).

    이때 원본을 다시 돌리는 것은 손해다. 같은 경쟁이 그대로라 또 떨어질 공산이
    크고, **이미 잘 나온 레이어까지 덮어쓴다.** 배경판에는 뗀 것이 이미 빠져
    있으므로 남은 것끼리만 겨루고, 못 뗀 부분은 원본 화소 그대로 남아 있어
    화질 손해도 없다. 프레임 크기가 같아 좌표도 그대로 맞는다.

    기존 요소 레이어는 건드리지 않는다. 배경판만 새것으로 바뀌고(옛것은
    아카이브로 옮긴다 — 지우지 않는다) 요소가 뒤에 더해진다.
    """
    out_base = Path(proj_dir) / subdir
    bg = out_base / f"{sid}__bg.png"
    if not bg.is_file():
        raise fal_api.FalError(f"배경판이 없습니다: {bg.name}")
    picked = [e for e in (elements or []) if (e.get("name_en") or "").strip()]
    if not picked:
        raise fal_api.FalError("분리할 요소 이름 없음 — name_en이 비어 있습니다")

    layers = fal_api.layerize(str(bg), [(e["name_en"]).strip() for e in picked])

    old = load_element_specs(out_base, sid)
    used = {(s.get("name_en") or "").strip().lower() for s in old}
    next_i = max([int(s.get("index", -1)) for s in old] + [-1]) + 1
    by_name = {}
    for k, el in enumerate(picked):
        key = (el.get("name_en") or "").strip().lower()
        if key and key not in used:
            by_name[key] = el

    kinds_fp = out_base / KINDS_SIDECAR.format(sid=sid)
    try:
        kinds = json.loads(kinds_fp.read_text(encoding="utf-8"))
    except Exception:
        kinds = {}

    matched, results, added = set(), [], []
    for L in layers:
        nm = L.get("name")
        if nm is None:                          # 새 배경판 — 옛것은 아카이브로
            box = out_base / "_archive"
            box.mkdir(exist_ok=True)
            keep = versioned_path(box, bg.name)
            shutil.move(str(bg), str(keep))
            bg.write_bytes(L["data"])
            results.append({"name": "배경", "rel": bg.relative_to(proj_dir).as_posix(),
                            "status": "completed", "z": L.get("z"), "bbox": None})
            if on_event:
                on_event(results[-1])
            continue
        key = (nm or "").strip().lower()
        el = by_name.get(key)
        if el is None or key in matched:
            if on_event:
                on_event({"name": nm, "status": "unexpected"})
            continue
        matched.add(key)
        i = next_i + len(added)
        tag = "_char" if el.get("kind") == "character" else ""
        out = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(nm)}{tag}.png")
        out.write_bytes(L["data"])
        kinds[out.stem] = el.get("kind", "object")
        added.append({"layer": out.stem, "index": i, "name": el.get("name", ""),
                      "name_en": nm, "location": el.get("location", ""),
                      "kind": el.get("kind", "object"), "intent": el.get("intent", ""),
                      "bbox": L.get("bbox"), "z": L.get("z")})
        results.append({"name": el.get("name", nm), "rel": out.relative_to(proj_dir).as_posix(),
                        "status": "completed", "z": L.get("z"), "bbox": L.get("bbox")})
        if on_event:
            on_event(results[-1])

    missing = [e.get("name_en") for k, e in by_name.items() if k not in matched]
    for m in missing:
        if on_event:
            on_event({"name": m, "status": "missing"})
    if kinds:
        kinds_fp.write_text(json.dumps(kinds, ensure_ascii=False, indent=2), encoding="utf-8")
    if added:
        write_element_specs(out_base, sid, old + added)
    return {"layers": results, "added": len(added), "missing": missing}
