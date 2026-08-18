"""PD 비서 — 말로 시키면 정해진 동작만 골라 돌린다.

터미널에서 스크립트 이름과 인자를 외워 치는 대신 「5편에서 인물 나오는 씬
레이어 나눠」라고 적으면 된다. 다만 **임의 실행은 하지 않는다.** 모델은
아래 카탈로그 안에서 고르기만 하고, 무엇을 할지는 사람이 보고 승인한다.

adobe 패널의 비서와 같은 원리다(그쪽은 ACTION_HANDLERS enum). 여기서는
v3가 실제로 가진 스크립트에 맞춰 다시 짰다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from auto_agent.paths import episode_label, get_package_dir

# 할 수 있는 일. 여기 없는 것은 못 한다 — 그게 안전장치다.
ACTIONS = {
    "layer_plan": {
        "label": "층 계획 세우기",
        "needs_scenes": True,
        "desc": "고른 씬의 그림을 훑어 어떤 층으로 가를지 정한다 (나누지는 않는다)",
    },
    "layer_split": {
        "label": "레이어 나누기",
        "needs_scenes": True,
        "desc": "세워 둔 계획대로 씬 이미지를 층으로 가른다",
    },
    "tts": {
        "label": "음성 만들기",
        "needs_scenes": True,
        "desc": "고른 씬의 나레이션으로 음성을 만든다",
    },
    "info_assets": {
        "label": "인포그래픽 에셋 만들기",
        "needs_scenes": False,
        "desc": "이 편의 인포그래픽 씬 요소들을 그린다",
    },
    "visual_mode": {
        "label": "시각화 방식 다시 정하기",
        "needs_scenes": False,
        "desc": "씬마다 재연·인포그래픽·실물·콜라주·지도 중 무엇으로 보여줄지 다시 정한다",
    },
    "status": {
        "label": "상태 보기",
        "needs_scenes": False,
        "desc": "얼마나 됐는지, 다음에 뭘 해야 하는지 알려 준다",
    },
}

PROMPT = """당신은 영상 제작 비서입니다. 감독의 말을 **할 수 있는 일** 중에서 고릅니다.

## 할 수 있는 일

{catalog}

## 이 프로젝트

{context}

## 감독의 말

{instruction}

## 규칙

- 목록에 없는 일은 고르지 않습니다. 애매하면 아무것도 고르지 말고 무엇이
  필요한지 되물으세요.
- 씬을 지정하는 일은 `scenes`에 번호를 적습니다. 「인물 나오는 씬」처럼
  조건으로 말하면 위 목록에서 해당하는 번호를 골라 적습니다.
- 씬을 특정할 수 없으면 `scenes`를 비우고 `ask`에 무엇을 물어야 하는지 적습니다.
- 한 번에 여러 일을 시키면 순서대로 적습니다.

## 낼 것 — JSON만

{{"plan":[{{"action":"", "scenes":[], "why":"이 일을 고른 이유 한 문장"}}],
  "say":"감독에게 할 말 한두 문장",
  "ask":""}}
"""


def _context(project: dict, health: dict) -> str:
    """모델이 씬을 고를 수 있도록 최소한의 사실만 준다."""
    lines = [f"편: {health.get('episode') or '?'} · {project.get('name') or project.get('slug')}"]
    for p in health.get("progress", []):
        lines.append(f"  {p['name']}: {p['done']}/{p['total']}")
    for t in health.get("todos", []):
        s = t.get("scenes") or []
        lines.append(f"  할 일 — {t['text']}" + (f" (씬 {', '.join(map(str, s))})" if s else ""))
    for s in health.get("suspects", []):
        sc = s.get("scenes") or []
        lines.append(f"  의심 — {s['kind']}: {s['text']}"
                     + (f" (씬 {', '.join(map(str, sc))})" if sc else ""))
    return "\n".join(lines)


def _ask_claude(prompt: str) -> dict | None:
    """클로드에게 묻고 JSON을 받는다.

    도구를 주지 않는다 — 여기서 할 일은 고르는 것뿐이고, 실행은 우리가 한다.
    """
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=300, env=env)
    except Exception:
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError:
        return None


def plan(project: dict, health: dict, instruction: str) -> dict:
    """감독의 말 → 할 일 목록. 아직 실행하지 않는다."""
    catalog = "\n".join(
        f"- `{k}` {v['label']} — {v['desc']}"
        + ("  (씬을 지정합니다)" if v["needs_scenes"] else "")
        for k, v in ACTIONS.items())
    d = _ask_claude(PROMPT.format(catalog=catalog,
                                  context=_context(project, health),
                                  instruction=instruction.strip()))
    if not d:
        return {"plan": [], "say": "무슨 말인지 잡지 못했습니다. 다시 적어 주세요.", "ask": ""}

    steps = []
    for s in d.get("plan") or []:
        a = s.get("action")
        if a not in ACTIONS:                     # 목록 밖은 버린다
            continue
        scenes = []
        for x in s.get("scenes") or []:
            try:
                scenes.append(int(x))
            except (TypeError, ValueError):
                continue
        steps.append({"action": a, "label": ACTIONS[a]["label"],
                      "scenes": scenes, "why": s.get("why", "")})
    return {"plan": steps, "say": d.get("say", ""), "ask": d.get("ask", "")}


def command(action: str, ep: str, scenes: list[int]) -> list[list[str]] | None:
    """이 동작을 실제로 돌릴 명령. 없으면 None."""
    root = get_package_dir().parent
    py = str(root / ".venv/bin/python")
    if action == "layer_plan":
        return [[py, "scripts/plan_scene_layers.py", ep, str(n)] for n in scenes]
    if action == "layer_split":
        return [[py, "scripts/animate_scene.py", ep, str(n)] for n in scenes]
    if action == "info_assets":
        f = root / "_imggen" / f"{ep}_mode.json"
        if not f.exists():
            return None
        mode = json.loads(f.read_text(encoding="utf-8"))
        ns = [str(s["n"]) for s in mode.get("scenes", []) if s.get("mode") == "infographic"]
        if not ns:
            return None
        return [[py, "scripts/gen_info_assets.py", ep, "--scenes", ",".join(ns), "-j", "3"]]
    if action == "visual_mode":
        return [[py, "scripts/run_visual_mode.py", ep]]
    return None
