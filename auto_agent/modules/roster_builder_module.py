"""roster_builder_module — 원고 + scene_specs에서 캐릭터 roster.json 생성.

semoji-animating(codex 레이어) 경로의 주춧돌. `scene_layer_v2.py` / `scene_layer_animate.py`
가 요구하는 `characters/roster.json`을 생성한다. FAL 경로의 `character_plan.json`과는
별개다 — 이쪽은 **씬별 캐스팅(scene_casts)** + 스프라이트용 **en/ko 외모 묘사**가 필요하다.

roster.json 스키마:
{
  "characters": [
    {"name": "주인공", "description_en": "...", "description_ko": "...", "sheet_path": null}
  ],
  "scene_casts": {"1": ["주인공"], "2": [], ...}   # 키=씬번호(문자열), 값=등장인물 이름
}

CLI:
  python3 -m auto_agent.modules.roster_builder_module --project <slug|id|abs> [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]


def _call_claude_cli(prompt: str, *, timeout: int = 180) -> str:
    """Claude CLI subprocess 호출 — 프로젝트 표준 패턴 (stdin, anthropic SDK 대신)."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)  # 중첩 세션 방지
    result = subprocess.run(
        [claude_bin, "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    return result.stdout


def resolve_project_dir(project_arg: str) -> Path:
    """프로젝트 디렉토리 해석 — v3(output/<uuid>_<slug>) + v4(projects/<id>) 호환.

    macOS NFC/NFD 한글 정규화 양방향 비교.
    """
    p = Path(project_arg)
    if p.is_absolute() and p.exists():
        return p
    v4 = ROOT / "projects" / project_arg
    if v4.exists():
        return v4
    v3_root = ROOT / "output"
    v3_exact = v3_root / project_arg
    if v3_exact.exists():
        return v3_exact
    nfc = unicodedata.normalize("NFC", project_arg)
    nfd = unicodedata.normalize("NFD", project_arg)
    if v3_root.exists():
        for entry in v3_root.iterdir():
            e_nfc = unicodedata.normalize("NFC", entry.name)
            e_nfd = unicodedata.normalize("NFD", entry.name)
            for needle in (nfc, nfd):
                if (e_nfc.endswith(f"_{needle}") or e_nfd.endswith(f"_{needle}")
                        or e_nfc.startswith(f"{needle}_") or e_nfd.startswith(f"{needle}_")):
                    return entry
    raise FileNotFoundError(f"project not found in projects/ or output/: {project_arg}")


def _load_inputs(pdir: Path) -> tuple[list, str, list]:
    """scene_specs(필수) + final_manuscript(선택) + character_plan(선택) 로드."""
    spec_path = pdir / "scene_specs.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"scene_specs.json 없음: {spec_path}")
    scenes = json.loads(spec_path.read_text(encoding="utf-8")).get("scenes", [])

    manuscript = ""
    for cand in ("final_manuscript.md", "draft.md"):
        mp = pdir / cand
        if mp.exists():
            manuscript = mp.read_text(encoding="utf-8")
            break

    existing_chars: list = []
    cp = pdir / "character_plan.json"
    if cp.exists():
        try:
            existing_chars = json.loads(cp.read_text(encoding="utf-8")).get("characters", [])
        except Exception:
            existing_chars = []
    return scenes, manuscript, existing_chars


def _scene_digest(scenes: list) -> str:
    """LLM에 줄 씬 요약 — 번호 + 제목 + 나레이션 + 엔티티."""
    lines = []
    for s in scenes:
        num = s.get("sceneNumber")
        title = s.get("title") or s.get("headline") or ""
        narr = (s.get("narration") or "")[:300]
        ents = ", ".join(str(e) for e in (s.get("entities") or [])[:6])
        lines.append(f"[씬 {num}] {title}\n  나레이션: {narr}\n  엔티티: {ents}")
    return "\n".join(lines)


def _build_prompt(scenes: list, manuscript: str, existing_chars: list) -> str:
    digest = _scene_digest(scenes)
    existing_hint = ""
    if existing_chars:
        names = [c.get("name", "") for c in existing_chars]
        existing_hint = (
            "\n참고: 기존 character_plan.json의 인물 목록(재사용 가능, 이름 일관성 유지):\n"
            + ", ".join(n for n in names if n) + "\n"
        )
    manuscript_hint = ""
    if manuscript:
        manuscript_hint = f"\n원고 발췌(맥락용, 일부):\n{manuscript[:3000]}\n"

    return f"""당신은 영상의 캐릭터 캐스팅 디렉터입니다.
아래 씬 목록과 원고를 바탕으로, 화면에 반복 등장하는 **캐릭터 roster**와 **씬별 캐스팅**을 만드세요.

규칙:
- 화면에 인물/캐릭터로 등장하는 대상만 포함 (나레이터 목소리만 있는 추상 개념은 제외).
- 같은 인물은 모든 씬에서 동일한 name으로 일관되게 지칭.
- description_en: 스프라이트 생성용 영문 외모 묘사 (이로미즘 3등신 캐리커처 기준, 의상·헤어·체형·표정 특징).
- description_ko: 같은 내용의 한국어 묘사 (가타카나/한자 금지, 순수 한국어/영어만).
- scene_casts: 각 씬번호(문자열)에 등장하는 인물 이름 배열. 인물 없으면 빈 배열 [].
- scene_casts의 모든 이름은 characters 목록의 name과 정확히 일치해야 함.
{existing_hint}{manuscript_hint}
씬 목록:
{digest}

출력: 아래 스키마의 **JSON만** 출력 (설명/코드펜스 없이):
{{
  "characters": [
    {{"name": "주인공", "description_en": "...", "description_ko": "...", "sheet_path": null}}
  ],
  "scene_casts": {{"1": ["주인공"], "2": []}}
}}"""


def _parse_json(text: str) -> dict:
    """LLM 출력에서 JSON 추출 (코드펜스/잡음 제거)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


def _normalize(roster: dict, scenes: list) -> dict:
    """스키마 정규화 + 무결성 보정 — scene_casts 이름은 characters에 존재해야 함."""
    chars = roster.get("characters") or []
    valid_names = {c.get("name") for c in chars if c.get("name")}
    for c in chars:
        c.setdefault("description_en", "")
        c.setdefault("description_ko", "")
        c.setdefault("sheet_path", None)

    casts_in = roster.get("scene_casts") or {}
    casts: dict = {}
    for s in scenes:
        key = str(s.get("sceneNumber"))
        names = casts_in.get(key) or casts_in.get(s.get("sceneNumber")) or []
        # characters에 없는 이름은 드롭
        casts[key] = [n for n in names if n in valid_names]
    return {"characters": chars, "scene_casts": casts}


def build_roster(project_dir, *, force: bool = False, timeout: int = 180) -> Path:
    """roster.json 생성 후 경로 반환. resume: 존재 시 skip(force=False)."""
    pdir = Path(project_dir)
    out_dir = pdir / "characters"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "roster.json"

    if out_path.exists() and not force:
        print(f"[skip] roster.json 이미 존재: {out_path} (강제: --force)")
        return out_path

    scenes, manuscript, existing = _load_inputs(pdir)
    if not scenes:
        raise ValueError("scene_specs.json에 scenes 없음")

    prompt = _build_prompt(scenes, manuscript, existing)
    raw = _call_claude_cli(prompt, timeout=timeout)
    roster = _normalize(_parse_json(raw), scenes)

    out_path.write_text(json.dumps(roster, ensure_ascii=False, indent=2), encoding="utf-8")
    n_chars = len(roster["characters"])
    n_cast_scenes = sum(1 for v in roster["scene_casts"].values() if v)
    print(f"[ok] roster.json → {out_path}")
    print(f"  캐릭터 {n_chars}명 / 캐스팅 있는 씬 {n_cast_scenes}개")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="원고+scene_specs → characters/roster.json")
    ap.add_argument("--project", required=True, help="slug | id | 절대경로")
    ap.add_argument("--force", action="store_true", help="기존 roster.json 덮어쓰기")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    pdir = resolve_project_dir(args.project)
    build_roster(pdir, force=args.force, timeout=args.timeout)


if __name__ == "__main__":
    main()
