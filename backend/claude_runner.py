"""claude CLI(헤드리스) 어댑터 — 텍스트 추론용. CLAUDECODE 등 중첩 변수 pop.
프롬프트는 stdin. 멀티모달(이미지)은 헤드리스에서 행이 걸려 미지원 → 비전은 codex가 담당.
주의: `--json-schema`는 이 claude(헤드리스)에서 행이 걸려(검증됨) 사용하지 않는다.
구조화 출력은 프롬프트 지시('JSON만 출력') + 결과에서 JSON 추출(_extract_json)로 처리한다."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")
_JSON_RE = re.compile(r"(\{[\s\S]*\}|\[[\s\S]*\])")


def _clean_env() -> dict:
    e = dict(os.environ)
    for k in _NEST_ENV:
        e.pop(k, None)          # 중첩 세션 방지(안 하면 claude -p 가 행)
    return e


def _extract_json(text: str) -> str:
    """결과 텍스트에서 JSON 블록만 추출. ```json 펜스/머리말 제거. 못 찾으면 원문."""
    t = (text or "").strip()
    if t.startswith("```"):                       # ```json ... ``` 펜스 제거
        t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", t).strip()
    m = _JSON_RE.search(t)
    return m.group(1) if m else t


def run_claude(prompt: str, cwd, *, session_id=None, output_schema=None, output_last=None,
               sandbox=None, images=None, model=None, on_line=None) -> dict:
    """codex run_skill과 동일 시그니처/반환. session_id 있으면 --resume(대화 연속).
    images/sandbox는 무시(헤드리스 텍스트 전용)."""
    if shutil.which("claude") is None:
        return {"returncode": 127, "session_id": None, "output_last": output_last}
    cmd = ["claude", "-p", "--output-format", "json"]
    if session_id:
        cmd += ["--resume", str(session_id)]
    # --json-schema는 헤드리스 claude에서 행 → 사용 안 함. JSON은 프롬프트 지시 + 결과 추출로.
    if model:
        cmd += ["--model", str(model)]
    try:
        r = subprocess.run(cmd, input=prompt, cwd=str(cwd), env=_clean_env(),
                           capture_output=True, text=True, timeout=1200)
    except Exception:
        return {"returncode": 1, "session_id": None, "output_last": output_last}
    if on_line and r.stdout:
        on_line(r.stdout[:500])
    result_text = r.stdout
    found_session = None
    try:                        # --output-format json 엔벨로프면 result/session_id 추출
        env = json.loads(r.stdout)
        if isinstance(env, dict):
            if "result" in env:
                result_text = env["result"]
            found_session = env.get("session_id") or env.get("sessionId")
    except Exception:
        pass
    if output_schema and result_text:        # 구조화 출력 요청 → JSON만 추출(펜스/머리말 제거)
        result_text = _extract_json(result_text)
    if output_last and result_text:
        Path(output_last).write_text(result_text, encoding="utf-8")
    return {"returncode": r.returncode, "session_id": found_session, "output_last": output_last}
