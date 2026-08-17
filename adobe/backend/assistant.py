"""실행형 제작 비서 — 자연어 지시를 안전한 액션 카탈로그로 매핑(codex)해 순차 실행.
LLM은 ACTION_HANDLERS의 enum 안에서만 선택한다(임의 실행 불가)."""
from __future__ import annotations

import json
from pathlib import Path

from backend import scenes, imagegen, tts, manifest, llm, motion
from backend import jobs as jobs_mod
from backend.codex_runner import run_skill

_PLAN_SCHEMA = Path(__file__).resolve().parent / "schemas" / "assistant_plan.schema.json"


# ---- 액션 핸들러(각 (proj_dir, on_event=None, targets=None, should_cancel=None) -> result dict) ----

def _target_scenes(data: dict, targets) -> list:
    """targets(씬 번호 목록)로 대상 씬을 좁힌다. 비었으면 전체.

    '1씬만 만들어줘'가 전 씬 생성으로 번지지 않게 하는 지점 — 여기서 좁히지 않으면
    핸들러는 언제나 프로젝트 전체를 순회한다."""
    ss = data.get("scenes", [])
    if not targets:
        return ss
    want = set()
    for t in targets:
        try:
            want.add(float(t))
        except (TypeError, ValueError):
            continue
    picked = []
    for s in ss:
        try:
            if float(s.get("sceneNumber")) in want:
                picked.append(s)
        except (TypeError, ValueError):
            continue
    return picked


def _check(should_cancel, done: int):
    """취소 요청이 있으면 루프를 끊는다(각 항목 사이에서만 — 진행 중 항목은 마무리)."""
    if should_cancel and should_cancel():
        raise jobs_mod.JobCancelled(f"{done}개 처리 후 취소")


def _h_generate_missing_images(proj_dir: Path, on_event=None, targets=None, should_cancel=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in _target_scenes(data, targets):
        _check(should_cancel, n)
        if s.get("_image"):
            continue
        prompt = (s.get("image_prompt") or s.get("visual_summary") or "").strip()
        if not prompt:
            continue
        name = scenes.new_scene_image_name(s.get("sceneId"))
        res = imagegen.generate_one(proj_dir, name, prompt, subdir="storyboard")
        if res.get("status") == "completed":
            rel = Path(res["path"]).relative_to(proj_dir).as_posix()
            scenes.set_image_ref(proj_dir, s.get("sceneNumber"), rel)
            n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} 이미지: {res.get('status')}")
    return {"generated": n}


def _h_split_layers(proj_dir: Path, on_event=None, targets=None, should_cancel=None) -> dict:
    from backend import vault
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in _target_scenes(data, targets):
        _check(should_cancel, n)
        if not s.get("_image") or s.get("_layers"):
            continue
        img = str(proj_dir / s["_image"])
        ctx = f"제목: {s.get('title', '')} / 요약: {s.get('visual_summary', '')}"
        els = imagegen.analyze_scene_layers(
            proj_dir, img,
            narration=s.get("narration", "") or "", context=ctx,
            image_prompt=s.get("image_prompt", "") or "",
            neighbors=scenes.neighbor_context(data.get("scenes", []), s.get("sceneNumber")),
            briefing=vault.read_context(proj_dir),
        ).get("elements", [])
        if not els:
            continue
        imagegen.split_scene_to_elements(proj_dir, img, s.get("sceneId"), els)
        n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} 레이어 {len(els)}개")
    return {"split_scenes": n}


def _h_tts_all(proj_dir: Path, on_event=None, targets=None, should_cancel=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in _target_scenes(data, targets):
        _check(should_cancel, n)
        text = scenes.tts_text(s)
        if not text.strip():
            continue
        res = tts.generate_scene_tts(proj_dir, s.get("sceneId"), text)
        if res.get("status") == "completed":
            scenes.update_texts(proj_dir, s.get("sceneNumber"), narration_tts=text)
            n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} TTS: {res.get('status')}")
    return {"generated": n}


def _h_plan_motion(proj_dir: Path, on_event=None, targets=None, should_cancel=None) -> dict:
    data = scenes.load_scenes(proj_dir)
    n = 0
    for s in _target_scenes(data, targets):
        _check(should_cancel, n)
        if not s.get("_layers"):
            continue
        if motion.motion_path(proj_dir, s.get("sceneId")).is_file():
            continue
        res = motion.plan_scene_motion(proj_dir, s.get("sceneNumber"))
        if "error" not in res:
            n += 1
        if on_event:
            on_event(f"S{s.get('sceneNumber')} 모션: {'완료' if 'error' not in res else res.get('error')}")
    return {"planned": n}


def _h_assemble(proj_dir: Path, on_event=None, targets=None, should_cancel=None) -> dict:
    return manifest.build_manifest(proj_dir, only_scenes=list(targets) if targets else None)


ACTION_HANDLERS = {
    "generate_missing_images": _h_generate_missing_images,
    "split_layers": _h_split_layers,
    "tts_all": _h_tts_all,
    "plan_motion": _h_plan_motion,
    "assemble": _h_assemble,
}

_CATALOG_DESC = (
    "- generate_missing_images: 이미지가 없는 씬에 씬 이미지를 생성한다.\n"
    "- split_layers: 이미지가 있고 레이어가 없는 씬을 캐릭터/움직임 기준으로 레이어 분리한다.\n"
    "- tts_all: 내레이션이 있는 모든 씬의 음성을 생성한다.\n"
    "- plan_motion: 레이어가 분리된 씬에 모션 플랜을 설계한다.\n"
    "- assemble: 매니페스트를 빌드해 AE 조립을 준비한다(보통 마지막).\n"
)


def project_status(proj_dir: Path) -> str:
    """집계 + 씬별 한 줄 현황(질문/상담 답변에 필요한 맥락)."""
    data = scenes.load_scenes(proj_dir)
    ss = data.get("scenes", [])
    img = sum(1 for s in ss if s.get("_image"))
    lay = sum(1 for s in ss if s.get("_layers"))
    aud = sum(1 for s in ss if s.get("_audio"))
    lines = [f"총 {len(ss)}씬 / 이미지 {img} / 레이어 {lay} / TTS {aud}"]
    for s in ss[:20]:                       # 씬별 현황(과도 방지 20씬 캡)
        st = s.get("_status") or {}
        nar = (s.get("narration") or "")[:40]
        lines.append(
            f"- 씬{s.get('sceneNumber')} '{s.get('title', '')}': "
            f"이미지 {'O' if st.get('image') else 'X'} / 레이어 {len(s.get('_layers') or [])}개 / "
            f"TTS {'O' if st.get('tts') else 'X'} / 모션 {'O' if st.get('motion') else 'X'} — {nar}")
    if len(ss) > 20:
        lines.append(f"(외 {len(ss) - 20}씬 생략)")
    return "\n".join(lines)


def _history_path(proj_dir: Path) -> Path:
    return Path(proj_dir) / "assistant_chat.jsonl"


def append_history(proj_dir: Path, role: str, text: str) -> None:
    """대화 이력 적재(user/assistant) — 비서가 맥락을 이어가게."""
    try:
        with _history_path(proj_dir).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"role": role, "text": (text or "")[:1000]}, ensure_ascii=False) + "\n")
    except Exception:
        pass


def history_text(proj_dir: Path, limit: int = 8, max_chars: int = 2500) -> str:
    """최근 대화를 프롬프트용 텍스트로. 없으면 ''."""
    p = _history_path(proj_dir)
    if not p.is_file():
        return ""
    turns = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            turns.append(json.loads(line))
        except Exception:
            continue
    turns = turns[-limit:]
    if not turns:
        return ""
    who = {"user": "사용자", "assistant": "비서"}
    return "\n".join(f"{who.get(t.get('role'), t.get('role'))}: {t.get('text', '')}" for t in turns)[:max_chars]


_SESSION_FILE = ".assistant_session.json"


def _load_session(proj_dir: Path) -> dict:
    try:
        return json.loads((Path(proj_dir) / _SESSION_FILE).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_session(proj_dir: Path, engine: str, session_id: str) -> None:
    try:
        (Path(proj_dir) / _SESSION_FILE).write_text(
            json.dumps({"engine": engine, "session_id": session_id}), encoding="utf-8")
    except Exception:
        pass


_DISTILL_MIN_TURNS = 6      # 이 이상 새 대화가 쌓였으면 새 세션 시작 전에 볼트로 증류


def _distill_to_vault(proj_dir: Path, *, on_line=None) -> None:
    """대화·작업을 context.md로 증류(증분) — 새 세션이 프로젝트를 다시 이해하는 브리핑.
    실패해도 무해(기존 context 유지)."""
    from backend import vault
    new_turns = vault.undistilled_turns(proj_dir)
    if len(new_turns) < _DISTILL_MIN_TURNS:
        return
    who = {"user": "사용자", "assistant": "비서"}
    convo = "\n".join(f"{who.get(t.get('role'), '?')}: {t.get('text', '')}" for t in new_turns)
    prev = vault.read_context(proj_dir)
    prompt = (
        "다음은 영상 제작 프로젝트의 기존 브리핑과 그 이후의 대화·작업 기록이다. "
        "이를 통합해 '프로젝트 브리핑'을 갱신하라 — 새로 투입된 비서가 이것만 읽고 "
        "맥락을 이어갈 수 있어야 한다.\n"
        "포함: 결정된 연출 방향/규칙, 진행 상황, 미해결 문제, 사용자 선호. "
        "마크다운, 600자 이내, 본문만 출력.\n\n"
        f"## 기존 브리핑\n{prev or '(없음)'}\n\n"
        f"## 새 대화\n{convo}\n\n"
        f"## 최근 작업 이력\n{vault.worklog_text(proj_dir)}"
    )
    out = proj_dir / ".vault_distill.md"
    res = llm.run_orchestrator(prompt, proj_dir, output_last=str(out), on_line=on_line)
    if res.get("returncode") == 0 and out.is_file():
        text = out.read_text(encoding="utf-8").strip()
        if text:
            vault.write_context(proj_dir, text)
            vault.mark_distilled(proj_dir, vault.total_turns(proj_dir))


def _full_prompt(proj_dir: Path, instruction: str) -> str:
    """새 세션 시작 프롬프트 — 규칙·기준·상태 + 볼트 브리핑·작업 이력·최근 대화(맥락 복원)."""
    from backend import edits, vault
    recent = edits.recent_edits_text(proj_dir, limit=2, max_chars=1500)
    hist = history_text(proj_dir)
    ctx = vault.read_context(proj_dir)
    work = vault.worklog_text(proj_dir)
    return (
        "너는 영상 제작 파트너(제작 비서)다. 사용자와 제작에 관해 자유롭게 상의하고, 필요할 때만 작업을 실행한다. "
        "이 세션은 계속 이어진다 — 이전 대화를 기억하고 맥락을 유지해라.\n\n"
        "## 응답 규칙\n"
        "1) 기본은 '대화'다 — reply에 한국어 존댓말로 답한다(질문·고민·아이디어·평가 요청 모두). "
        "프로젝트 상태와 제작 기준을 근거로 구체적으로, 필요하면 다음 단계를 제안한다.\n"
        "2) actions는 사용자가 '명확하게 실행을 지시'했을 때만 채운다(예: ~해줘, ~실행해, 진행해, 돌려줘). "
        "모호하면 실행하지 말고 reply로 '~를 실행할까요?'라고 제안만 한다.\n"
        "2-1) **모든 액션에 targets(대상 씬 번호 배열)를 반드시 넣는다.** 사용자가 특정 씬을 말했으면 "
        "그 번호만 넣어라('1씬 이미지 하나' → targets:[1]). targets를 빈 배열로 두면 프로젝트 전체에 "
        "실행되므로, '전부/모든 씬/일괄'처럼 전체를 분명히 지시했을 때만 비운다. "
        "대상이 불분명하면 실행하지 말고 reply로 어느 씬인지 되물어라.\n"
        "3) 실행할 때도 reply에 무엇을 왜 하는지 한 줄 설명을 함께 담아라.\n"
        "4) 목록 외 동작은 만들지 말고, 보통 assemble은 마지막.\n\n"
        "## 제작 기준(상담 근거)\n"
        "- 레이어 분리: 1순위 캐릭터 전원, 2순위 캐릭터를 가리는 전경, 3순위 내용상 필요 요소, 그 외 배경 잔류\n"
        "- 모션: 현재 캐릭터만(bob 까딱임+선택 fade_in), 사물·배경 모션은 규칙 미정으로 금지\n"
        "- TTS: ElevenLabs(스타일별 voice), 워크플로우: 이미지→레이어→TTS→모션→컴프\n\n"
        f"## 가능한 액션\n{_CATALOG_DESC}\n## 현재 프로젝트 상태\n{project_status(proj_dir)}\n"
        + (f"\n## 프로젝트 볼트 브리핑(이전 세션들의 결정·진행 요약)\n{ctx}\n" if ctx else "")
        + (f"\n## 최근 작업 이력\n{work}\n" if work else "")
        + (f"\n## 최근 대화(원문 일부)\n{hist}\n" if hist else "")
        + (f"\n{recent}\n" if recent else "")
        + f"\n## 사용자 입력\n{instruction}"
    )


def _resume_prompt(proj_dir: Path, instruction: str) -> str:
    """이어지는 세션 프롬프트 — 규칙은 세션이 기억하므로 상태 갱신 + 입력만(가볍게)."""
    from backend import edits
    recent = edits.recent_edits_text(proj_dir, limit=1, max_chars=800)
    return (
        f"## 현재 프로젝트 상태(갱신)\n{project_status(proj_dir)}\n"
        + (f"\n{recent}\n" if recent else "")
        + f"\n## 사용자 입력\n{instruction}\n"
        "(규칙 동일: 기본은 reply 대화, 명확한 실행 지시만 actions.)"
    )


def plan_actions(proj_dir: Path, instruction: str, *, on_line=None) -> dict:
    """NL 입력 → {actions, reply}. 프로젝트별 지속 LLM 세션(resume)으로 대화 전체를 기억.
    세션이 끊기거나 엔진이 바뀌면 새 세션(텍스트 이력으로 맥락 이어줌)."""
    proj_dir = Path(proj_dir)
    engine = llm.get_orchestrator()
    sess = _load_session(proj_dir)
    sid = sess.get("session_id") if sess.get("engine") == engine else None
    out = proj_dir / ".assistant_plan.json"

    def _call(session_id, prompt):
        return llm.run_orchestrator(prompt, proj_dir, session_id=session_id,
                                    output_schema=str(_PLAN_SCHEMA), output_last=str(out),
                                    on_line=on_line)

    if not sid:
        _distill_to_vault(proj_dir, on_line=on_line)    # 새 세션 — 쌓인 대화를 볼트 브리핑으로 증류
    res = _call(sid, _resume_prompt(proj_dir, instruction) if sid else _full_prompt(proj_dir, instruction))
    if sid and (res.get("returncode") != 0 or not out.is_file()):
        # 세션 만료/유실 — 볼트 증류 후 새 세션으로 1회 재시도(브리핑이 맥락 복원)
        sid = None
        _distill_to_vault(proj_dir, on_line=on_line)
        res = _call(None, _full_prompt(proj_dir, instruction))
    if res.get("session_id"):
        _save_session(proj_dir, engine, res["session_id"])
    if res.get("returncode") != 0 or not out.is_file():
        return {"actions": [], "reply": None}
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        return {"actions": data.get("actions", []), "reply": data.get("reply")}
    except Exception:
        return {"actions": [], "reply": None}


def run_assistant(proj_dir: Path, instruction: str, *,
                  planner=None, handlers=None, on_event=None, should_cancel=None) -> dict:
    """plan_actions로 계획 → 핸들러 순차 실행 → 결과 수집. planner/handlers 주입 가능(테스트)."""
    proj_dir = Path(proj_dir)
    planner = planner or plan_actions
    handlers = handlers if handlers is not None else ACTION_HANDLERS
    append_history(proj_dir, "user", instruction)       # 대화 이력 — 비서가 맥락 유지
    planned = planner(proj_dir, instruction, on_line=on_event) if _accepts_on_line(planner) else planner(proj_dir, instruction)
    if isinstance(planned, dict):                       # 신형 {actions, reply}
        actions, reply = planned.get("actions", []), planned.get("reply")
    else:                                               # 구형 list 플래너(테스트 주입) 호환
        actions, reply = planned, None
    if reply:
        append_history(proj_dir, "assistant", reply)
    elif actions:
        append_history(proj_dir, "assistant", "[실행] " + ", ".join(a.get("action", "") for a in actions))
    results = []
    for a in actions:
        name = a.get("action")
        targets = a.get("targets") or []
        if on_event:
            scope = f"씬 {','.join(str(t) for t in targets)}" if targets else "조건에 맞는 전체 씬"
            on_event(f"▶ {name} ({scope}): {a.get('reason', '')}")
        h = handlers.get(name)
        if h is None:
            results.append({"action": name, "reason": a.get("reason"), "result": {"status": "skipped"}})
            continue
        try:
            r = h(proj_dir, on_event=on_event, targets=targets, should_cancel=should_cancel)
        except TypeError:                       # 구형/테스트 핸들러 호환
            try:
                r = h(proj_dir, on_event=on_event)
            except TypeError:
                r = h(proj_dir)
        results.append({"action": name, "reason": a.get("reason"), "targets": targets, "result": r})
        from backend import vault
        vault.log_work(proj_dir, name, json.dumps(r, ensure_ascii=False)[:200])   # 볼트 작업 이력
    return {"plan": actions, "results": results, "reply": reply}


def _accepts_on_line(fn) -> bool:
    try:
        import inspect
        return "on_line" in inspect.signature(fn).parameters
    except (ValueError, TypeError):
        return False
