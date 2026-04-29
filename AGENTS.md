# Auto Kairos v3 Codex Guide

이 저장소에서는 한국어 존댓말로 답변하고, 기존 Claude용 운영 규칙을 존중합니다.

## 작업 경계

- `auto-agent run`의 Stage 1/2 핵심 에이전트 실행부는 아직 Claude CLI/Anthropic SDK에 강하게 결합되어 있습니다.
- Codex에서 완전한 Stage 1 -> Stage 3 작업을 진행하려면 `/Users/jleavens_macmini/LocalProjects/auto_kairos_codex`의 Codex-native 파이프라인을 우선 검토하세요.
- 이 v3 저장소 안에서 Codex로 바로 다루기 좋은 영역은 로컬 CLI, DB/대시보드 보조 기능, Stage 0/4의 `AgentRunner(provider="codex")`, Remotion/에셋/검증 스크립트입니다.

## 기본 명령

```bash
/Users/jleavens_macmini/LocalProjects/auto_kairos_v3/.venv/bin/python -m auto_agent.cli --version
/Users/jleavens_macmini/LocalProjects/auto_kairos_v3/.venv/bin/python -m auto_agent.cli project list
/Users/jleavens_macmini/LocalProjects/auto_kairos_v3/.venv/bin/python -m pytest -q tests/test_agent_runner.py
```

대시보드는 `fastapi` extra가 설치되어 있어야 합니다.

```bash
/Users/jleavens_macmini/LocalProjects/auto_kairos_v3/.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8080
```

## 안전 규칙

- 이미지 파일은 삭제하지 마세요. 새 버전 파일을 만들고 선택 상태만 바꾸세요.
- Remotion 소스를 바꾸면 `remotion/src/`와 `auto_agent/remotion_template/src/`를 함께 동기화하세요.
- 프로젝트 경로는 하드코딩하지 말고 `auto_agent.paths.get_workspace_dir()` 또는 `pathlib.Path` 기반으로 처리하세요.
- 사용자가 명시하지 않은 기존 작업물, 세션 파일, DB, 출력 폴더는 되돌리거나 정리하지 마세요.
- `scene_specs.json`은 flat schema를 유지하고, legacy v3 필드는 기존 normalizer/validator를 우선 사용하세요.

## Codex 전환 메모

- v3의 `auto_agent/modules/agent_runner.py`에는 Stage 0/4용 Codex provider가 이미 있습니다.
- v3의 `auto_agent/orchestrator/runner.py`, `context_memory.py`, `agent_loop.py`, `claude_client.py`는 Claude/Anthropic 의존도가 높습니다.
- Codex 앱에서 v3 전체 파이프라인을 안정적으로 돌리려면 Claude CLI 호출을 직접 치환하기보다, `auto_kairos_codex`의 file-system-first task contract 방식으로 단계별 이관하는 편이 안전합니다.
