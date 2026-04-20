"""
캐릭터 이미지 생성/재생성 스크립트

character_plan.json을 기반으로 캐릭터 이미지를 생성한다.
특정 캐릭터만 지정하거나 전체를 생성할 수 있다.

사용법:
  # 전체 생성 (이미 있는 파일은 스킵)
  python3.12 -m auto_agent.scripts.generate_characters --slug <slug>

  # 특정 캐릭터만 (이름 일부 매칭)
  python3.12 -m auto_agent.scripts.generate_characters --slug <slug> --name 타지리

  # 강제 재생성 (기존 파일 덮어쓰기)
  python3.12 -m auto_agent.scripts.generate_characters --slug <slug> --name 타지리 --force

  # 기존 파일을 bak으로 백업 후 재생성
  python3.12 -m auto_agent.scripts.generate_characters --slug <slug> --name 타지리 --force --backup

  # 전체 재생성
  python3.12 -m auto_agent.scripts.generate_characters --slug <slug> --force
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from dotenv import load_dotenv

load_dotenv(get_workspace_dir() / ".env")

from auto_agent.tools.image_generate import generate_character

DATA_DIR = get_workspace_dir() / "auto_agent" / "data"
DEFAULT_STYLE = str(DATA_DIR / "artstyle" / "styles" / "semoji_3D.json")


def _find_output_path(ch: dict, output_dir: Path) -> Path:
    """캐릭터의 출력 파일 경로 결정.

    variants가 있으면 첫 번째 variant의 output 사용.
    없으면 characters/ 폴더에서 캐릭터 ID 기준으로 기존 파일 탐색 (semoji_3D 포함).
    없으면 새 경로 생성.
    """
    variants = ch.get("variants", [])
    if variants and variants[0].get("output"):
        return output_dir / variants[0]["output"]

    char_dir = output_dir / "characters"
    char_id = ch["id"]  # e.g. "타지리_사토시"
    char_name = ch["name"]  # e.g. "타지리 사토시(게임프리크 대표, 20대)"
    safe_name = char_name.replace(" ", "_")

    # 기존 파일 탐색: 이름에 char_id 포함 + semoji_3D 포함 파일 우선
    if char_dir.exists():
        import unicodedata
        char_id_nfc = unicodedata.normalize("NFC", char_id)
        candidates = []
        for f in char_dir.iterdir():
            if f.suffix.lower() not in (".png", ".jpg", ".webp"):
                continue
            stem_nfc = unicodedata.normalize("NFC", f.stem)
            if char_id_nfc in stem_nfc and "semoji_3D" in stem_nfc and "_bak" not in stem_nfc:
                candidates.append(f)
        if candidates:
            return sorted(candidates)[0]

    # 새 파일명 생성
    import hashlib
    h = hashlib.md5(char_name.encode()).hexdigest()[:8]
    fname = f"{safe_name}__semoji_3D__{h}.png"
    return char_dir / fname


def _extract_age_tag(ch: dict) -> str:
    """tags 또는 name에서 나이 정보를 추출 ('20대', '30대', '40대' 등)."""
    import re
    age_pattern = re.compile(r"\d+대")
    for tag in ch.get("tags", []):
        m = age_pattern.search(tag)
        if m:
            return m.group()
    m = age_pattern.search(ch.get("name", ""))
    if m:
        return m.group()
    return ""


def _get_prompt(ch: dict) -> str:
    """캐릭터 프롬프트 반환. 나이 정보가 있으면 나이대 지시 추가."""
    variants = ch.get("variants", [])
    base = ""
    if variants:
        base = variants[0].get("prompt_base") or variants[0].get("prompt") or ch.get("description", ch["name"])
    else:
        base = ch.get("prompt_base") or ch.get("description") or ch["name"]

    age_tag = _extract_age_tag(ch)
    if age_tag and ch.get("person_photo"):
        # 참조 이미지가 있는 실존 인물: 나이대 맞게 그려달라고 명시
        base = f"{base}, drawn as a person in their {age_tag} (young {age_tag} version)"
    elif age_tag:
        base = f"{base}, {age_tag} appearance"

    return base


def _find_project_dir(slug: str) -> Path | None:
    """output/ 폴더에서 slug가 포함된 프로젝트 디렉토리를 찾는다."""
    output_root = get_workspace_dir() / "output"
    if not output_root.exists():
        return None
    for d in sorted(output_root.iterdir()):
        if d.is_dir() and slug in d.name:
            return d
    return None


def generate(slug: str, name_filter: str, force: bool, backup: bool, style_path: str):
    project_dir = _find_project_dir(slug)
    if not project_dir:
        print(f"[오류] 프로젝트를 찾을 수 없음: {slug}")
        sys.exit(1)
    print(f"프로젝트: {project_dir.name}")

    plan_path = project_dir / "character_plan.json"
    if not plan_path.exists():
        print(f"[오류] character_plan.json 없음: {plan_path}")
        sys.exit(1)

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    characters = plan.get("characters", [])

    # 필터링
    if name_filter:
        characters = [c for c in characters if name_filter in c["name"] or name_filter in c["id"]]
        if not characters:
            print(f"[오류] '{name_filter}'에 해당하는 캐릭터 없음")
            sys.exit(1)

    print(f"대상 캐릭터: {len(characters)}명")

    ok_count = 0
    fail_count = 0

    for ch in characters:
        name = ch["name"]
        out_path = _find_output_path(ch, project_dir)
        prompt = _get_prompt(ch)

        person_photo = None
        if ch.get("person_photo"):
            pp = project_dir / ch["person_photo"]
            if pp.exists():
                person_photo = str(pp)
            else:
                print(f"  [경고] 참조 이미지 없음: {pp}")

        # 파일 존재 처리
        if out_path.exists():
            if not force:
                print(f"  [스킵] {name} → {out_path.name}")
                continue
            if backup:
                # _bak, _bak2, ... 형식으로 백업
                bak_base = out_path.with_suffix("")
                bak_idx = 1
                while True:
                    suffix = "_bak" if bak_idx == 1 else f"_bak{bak_idx}"
                    bak_path = bak_base.parent / f"{bak_base.name}{suffix}{out_path.suffix}"
                    if not bak_path.exists():
                        break
                    bak_idx += 1
                shutil.move(str(out_path), str(bak_path))
                print(f"  [백업] {out_path.name} → {bak_path.name}")
            else:
                out_path.unlink()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  [생성] {name}", end="", flush=True)
        if person_photo:
            print(f" (참조: {Path(person_photo).name})", end="", flush=True)
        print()

        t0 = time.time()
        result = generate_character(
            prompt=prompt,
            output_path=str(out_path),
            style_path=style_path,
            person_photo=person_photo,
        )
        elapsed = time.time() - t0

        if result.get("success"):
            print(f"    ✅ 완료 ({elapsed:.1f}s) → {out_path.name}")
            ok_count += 1
        else:
            print(f"    ❌ 실패 ({elapsed:.1f}s): {result.get('error', '')}")
            fail_count += 1

    print(f"\n완료: {ok_count}명 생성, {fail_count}명 실패")


def main():
    parser = argparse.ArgumentParser(description="캐릭터 이미지 생성")
    parser.add_argument("--slug", required=True, help="프로젝트 slug (UUID 또는 이름 일부)")
    parser.add_argument("--name", default="", help="특정 캐릭터 이름 필터 (부분 매칭)")
    parser.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    parser.add_argument("--backup", action="store_true", help="덮어쓰기 전 _bak으로 백업 (--force와 함께)")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="artstyle JSON 경로")
    args = parser.parse_args()

    generate(
        slug=args.slug,
        name_filter=args.name,
        force=args.force,
        backup=args.backup,
        style_path=args.style,
    )


if __name__ == "__main__":
    main()
