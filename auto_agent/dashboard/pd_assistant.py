"""PD 비서 — 대화하면서 이 저장소 안의 일을 시킨다.

말로 물어보면 답하고(경로·개수·원고 내용·사실 확인), 실제로 무언가를 만들거나
바꿔야 하면 **할 일을 세워 보여 준 뒤 승인을 받아** 돌린다.

두 갈래인 이유가 있다. 찾아 보고 답하는 일은 되돌릴 것이 없지만, 이미지를
새로 뽑거나 레이어를 나누는 일은 몇 분과 비용이 든다. 그건 사람이 보고
결정할 일이다.

읽기는 클로드가 도구(Read·Grep·Glob·WebSearch)로 직접 한다. 실행은 우리가
가진 스크립트로만 한다 — 모델이 아무 명령이나 돌리지는 못한다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from auto_agent.paths import get_package_dir

# 돌릴 수 있는 일. 여기 없는 것은 못 한다.
ACTIONS = {
    "layer_plan": ("층 계획 세우기", True,
                   "고른 씬의 그림을 훑어 어떤 층으로 가를지 정한다 (나누지는 않는다)"),
    "layer_split": ("레이어 나누기", True,
                    "세워 둔 계획대로 씬 이미지를 층으로 가른다"),
    "images": ("이미지 만들기", True,
               "고른 씬의 그림을 다시 그린다 (인물 시트를 붙여서)"),
    "srt": ("자막 만들기", False,
            "씬 음성 길이를 재서 SRT 자막 파일을 만든다"),
    "info_assets": ("인포그래픽 에셋 만들기", False,
                    "이 편의 인포그래픽 씬 요소들을 그린다"),
    "visual_mode": ("시각화 방식 다시 정하기", False,
                    "씬마다 재연·인포그래픽·실물·콜라주·지도 중 무엇으로 보여줄지 다시 정한다"),
}

SYSTEM = """당신은 다큐멘터리 제작 PD의 비서입니다. 감독과 대화하며 일을 돕습니다.

## 지금 보고 있는 프로젝트

{context}

프로젝트 폴더: {proj_dir}
저장소: {root}
레이어 폴더: {layer_dir}

## 할 수 있는 일

**바로 답하는 일** — 도구(Read·Grep·Glob·WebSearch)로 직접 찾아서 답하세요.
- 파일이 어디 있는지, 몇 개인지, 어떤 씬이 어떤 상태인지
- 원고 내용을 찾아 주거나 문장을 다듬어 제안하기
- 사실 확인 (필요하면 웹을 찾아보고, 출처를 함께 적으세요)

**승인을 받아 돌리는 일** — 아래 목록에 있는 것만.

{catalog}

이 일이 필요하면 답 끝에 아래 형식의 블록을 붙이세요. 감독이 버튼을 눌러야
실제로 돕니다.

```plan
[{{"action":"layer_split","scenes":[3,4],"why":"계획만 서 있고 아직 안 나눈 씬"}}]
```

## 규칙

- 원고를 고치는 일은 직접 하지 말고 **어떻게 고칠지 제안**하세요. 감독이
  스토리보드나 원고 탭에서 문장을 눌러 고칩니다.
- 파일을 만들거나 지우지 마세요. 읽기만 합니다.
- 사실이 확인되지 않으면 확인되지 않았다고 적으세요. 지어내지 않습니다.
- 한국어로, 존댓말로 짧게 답합니다.

## 지금까지 나눈 이야기

{history}

## 감독의 말

{instruction}
"""


def history_path(project: dict) -> Path:
    return Path(project.get("output_dir") or ".") / "pd_chat.jsonl"


def load_history(project: dict, limit: int = 40) -> list[dict]:
    f = history_path(project)
    if not f.exists():
        return []
    rows = []
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows[-limit:]


def append_history(project: dict, role: str, text: str, plan=None) -> None:
    f = history_path(project)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"role": role, "text": text, "plan": plan or []},
                                ensure_ascii=False) + "\n")
    except Exception:
        pass


def _context(project: dict, health: dict) -> str:
    lines = [f"{health.get('episode') or '?'} · {project.get('name') or project.get('slug')}"]
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


def _history_text(project: dict, limit: int = 8) -> str:
    rows = load_history(project, limit)
    if not rows:
        return "(처음 나누는 이야기입니다)"
    out = []
    for r in rows:
        who = "감독" if r.get("role") == "user" else "비서"
        out.append(f"{who}: {(r.get('text') or '')[:600]}")
    return "\n".join(out)


def ask(project: dict, health: dict, instruction: str) -> dict:
    """감독의 말에 답한다. 돌릴 일이 있으면 계획을 함께 낸다."""
    root = get_package_dir().parent
    ep = health.get("episode") or ""
    catalog = "\n".join(
        f"- `{k}` {v[0]} — {v[2]}" + ("  (씬을 지정합니다)" if v[1] else "")
        for k, v in ACTIONS.items())
    prompt = SYSTEM.format(
        context=_context(project, health),
        proj_dir=project.get("output_dir") or "",
        root=root,
        layer_dir=(root / "_imggen" / f"{ep.lower()}_anim") if ep else "(없음)",
        catalog=catalog,
        history=_history_text(project),
        instruction=instruction.strip(),
    )

    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(
            ["claude", "--allowedTools", "Read,Grep,Glob,WebSearch,WebFetch",
             "--output-format", "text"],
            input=prompt, capture_output=True, text=True, timeout=900,
            cwd=str(root), env=env)
    except Exception as e:
        return {"reply": f"비서를 부르지 못했습니다: {e}", "plan": []}

    text = (r.stdout or "").strip()
    if not text:
        return {"reply": "답을 받지 못했습니다.", "plan": []}

    plan = []
    m = re.search(r"```plan\s*(.+?)```", text, re.S)
    if m:
        try:
            raw = json.loads(m.group(1).strip())
            for s in raw if isinstance(raw, list) else []:
                a = s.get("action")
                if a not in ACTIONS:
                    continue
                scenes = []
                for x in s.get("scenes") or []:
                    try:
                        scenes.append(int(x))
                    except (TypeError, ValueError):
                        continue
                plan.append({"action": a, "label": ACTIONS[a][0],
                             "scenes": scenes, "why": s.get("why", "")})
        except json.JSONDecodeError:
            pass
        text = text[:m.start()].strip() + text[m.end():].strip()

    return {"reply": text, "plan": plan}


def command(action: str, ep: str, scenes: list[int]) -> list[list[str]] | None:
    """이 동작을 실제로 돌릴 명령."""
    root = get_package_dir().parent
    py = str(root / ".venv/bin/python")
    if action == "layer_plan":
        return [[py, "scripts/plan_scene_layers.py", ep, str(n)] for n in scenes]
    if action == "layer_split":
        return [[py, "scripts/animate_scene.py", ep, str(n)] for n in scenes]
    if action == "srt":
        return [[py, "scripts/build_srt.py", ep]]
    if action == "visual_mode":
        return [[py, "scripts/run_visual_mode.py", ep]]
    if action == "info_assets":
        f = root / "_imggen" / f"{ep}_mode.json"
        if not f.exists():
            return None
        mode = json.loads(f.read_text(encoding="utf-8"))
        ns = [str(s["n"]) for s in mode.get("scenes", []) if s.get("mode") == "infographic"]
        return [[py, "scripts/gen_info_assets.py", ep, "--scenes", ",".join(ns), "-j", "3"]] if ns else None
    if action == "images":
        # 씬 이미지 생성은 프롬프트 폴더와 프로젝트 경로를 받는다
        import json as _json

        emap = _json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
        proj = next((v["dir"] for k, v in emap.items() if k.startswith(ep)), None)
        if not proj or not scenes:
            return None
        prompts = root / "_imggen" / ep.lower()
        out = root / "_imggen" / f"{ep.lower()}_regen"
        return [[py, "scripts/gen_scenes.py", proj, str(prompts), "-o", str(out),
                 "--only", ",".join(str(n) for n in scenes)]]
    return None
