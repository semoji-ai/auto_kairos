"""
백그라운드 파이프라인 세션 매니저.

프로젝트별로 파이프라인을 백그라운드 프로세스로 실행하고,
메인 세션에서 상태 확인, 로그 조회, 중지 등을 관리한다.

세션 상태는 {workspace}/.sessions/ 디렉토리에 JSON으로 저장.
로그는 output/{project}/logs/ 디렉토리에 기록.
"""

import json
import os
import platform
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from auto_agent.paths import get_workspace_dir


def _sessions_dir() -> Path:
    """세션 상태 디렉토리."""
    d = get_workspace_dir() / ".sessions"
    d.mkdir(exist_ok=True)
    return d


def _session_file(project_slug: str) -> Path:
    """프로젝트별 세션 상태 파일."""
    return _sessions_dir() / f"{project_slug}.json"


def _logs_dir(project_slug: str) -> Path:
    """로그 디렉토리. DB에서 output_dir 조회, 없으면 fallback."""
    try:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.resolve_project(project_slug)
        if project:
            d = Path(project["output_dir"]) / "logs"
            d.mkdir(parents=True, exist_ok=True)
            return d
    except Exception:
        pass
    # fallback for non-DB projects
    d = get_workspace_dir() / "output" / project_slug / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path(project_slug: str) -> Path:
    """pipeline_state.json 경로. DB에서 output_dir 조회, 없으면 fallback."""
    try:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.resolve_project(project_slug)
        if project:
            return Path(project["output_dir"]) / "pipeline_state.json"
    except Exception:
        pass
    return get_workspace_dir() / "output" / project_slug / "pipeline_state.json"


def _is_process_alive(pid: int) -> bool:
    """PID가 실행 중인지 확인 (크로스플랫폼)."""
    try:
        if platform.system() == "Windows":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                exit_code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                kernel32.CloseHandle(handle)
                return exit_code.value == 259  # STILL_ACTIVE
            return False
        else:
            os.kill(pid, 0)  # 신호 없이 존재 확인
            return True
    except (OSError, ProcessLookupError):
        return False


class SessionManager:
    """백그라운드 파이프라인 세션 관리."""

    def start(
        self,
        project_slug: str,
        from_step: Optional[str] = None,
        only_step: Optional[str] = None,
    ) -> dict:
        """파이프라인을 백그라운드로 시작.

        Returns:
            세션 정보 dict
        """
        # 이미 실행 중인 세션이 있는지 확인
        existing = self.get_session(project_slug)
        if existing and existing["status"] == "running":
            if _is_process_alive(existing["pid"]):
                raise RuntimeError(
                    f"프로젝트 '{project_slug}'의 파이프라인이 이미 실행 중입니다 "
                    f"(PID: {existing['pid']})"
                )
            # 프로세스가 죽었으면 상태 업데이트
            self._mark_dead(project_slug, existing)

        # 로그 파일 준비
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = _logs_dir(project_slug) / f"pipeline_{timestamp}.log"

        # auto-agent run 명령어 구성
        cmd = [sys.executable, "-m", "auto_agent.cli", "run", "--project", project_slug]
        if from_step:
            cmd += ["--from", from_step]
        if only_step:
            cmd += ["--only", only_step]

        # 환경변수: 워크스페이스 경로 전달
        env = os.environ.copy()
        env["AUTO_AGENT_WORKSPACE"] = str(get_workspace_dir())

        # 백그라운드 프로세스 시작
        log_fh = open(log_file, "w", encoding="utf-8")

        kwargs = {
            "stdout": log_fh,
            "stderr": subprocess.STDOUT,
            "env": env,
            "cwd": str(get_workspace_dir()),
        }

        if platform.system() == "Windows":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            )
        else:
            kwargs["start_new_session"] = True

        process = subprocess.Popen(cmd, **kwargs)

        # 세션 상태 저장
        session = {
            "project_slug": project_slug,
            "pid": process.pid,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
            "log_file": str(log_file),
            "from_step": from_step,
            "only_step": only_step,
            "exit_code": None,
        }
        self._save_session(project_slug, session)
        return session

    def stop(self, project_slug: str) -> Optional[dict]:
        """실행 중인 세션 중지.

        Returns:
            업데이트된 세션 정보, 없으면 None
        """
        session = self.get_session(project_slug)
        if not session:
            return None

        pid = session["pid"]
        if not _is_process_alive(pid):
            self._mark_dead(project_slug, session)
            return self.get_session(project_slug)

        # 프로세스 종료
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                )
            else:
                # SIGTERM → 2초 대기 → SIGKILL
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(2)
                if _is_process_alive(pid):
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

        session["status"] = "stopped"
        session["finished_at"] = datetime.now().isoformat()
        self._save_session(project_slug, session)
        return session

    def get_session(self, project_slug: str) -> Optional[dict]:
        """프로젝트의 현재 세션 정보 조회."""
        path = _session_file(project_slug)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # 실행 중으로 기록되어 있지만 프로세스가 죽은 경우 상태 갱신
            if data["status"] == "running" and not _is_process_alive(data["pid"]):
                self._mark_dead(project_slug, data)
                data = json.loads(path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    def list_sessions(self) -> list[dict]:
        """모든 세션 목록 반환 (최신순)."""
        sessions = []
        sessions_dir = _sessions_dir()
        for f in sessions_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                # 실행 중 상태인데 프로세스가 죽은 경우 갱신
                if data["status"] == "running" and not _is_process_alive(data["pid"]):
                    self._mark_dead(data["project_slug"], data)
                    data = json.loads(f.read_text(encoding="utf-8"))
                sessions.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        sessions.sort(key=lambda s: s.get("started_at", ""), reverse=True)
        return sessions

    def get_log_tail(self, project_slug: str, lines: int = 50) -> str:
        """세션 로그의 마지막 N줄 반환."""
        session = self.get_session(project_slug)
        if not session or not session.get("log_file"):
            return ""

        log_path = Path(session["log_file"])
        if not log_path.exists():
            return ""

        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            all_lines = content.splitlines()
            return "\n".join(all_lines[-lines:])
        except OSError:
            return ""

    def follow_log(self, project_slug: str):
        """로그를 실시간으로 출력 (tail -f 방식). Generator."""
        session = self.get_session(project_slug)
        if not session or not session.get("log_file"):
            return

        log_path = Path(session["log_file"])
        if not log_path.exists():
            return

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            # 기존 내용은 마지막 20줄만 출력
            f.seek(0, 2)  # EOF로 이동
            file_size = f.tell()
            if file_size > 0:
                # 마지막 20줄 찾기
                f.seek(max(0, file_size - 4096))
                tail = f.read()
                tail_lines = tail.splitlines()[-20:]
                for line in tail_lines:
                    yield line

            # 새 내용을 계속 읽기
            while True:
                line = f.readline()
                if line:
                    yield line.rstrip("\n")
                else:
                    # 프로세스가 아직 살아있으면 대기
                    if session["status"] == "running" and _is_process_alive(session["pid"]):
                        time.sleep(0.3)
                    else:
                        # 프로세스 종료 — 남은 내용 읽고 끝
                        remaining = f.read()
                        if remaining:
                            for l in remaining.splitlines():
                                yield l
                        break

    def cleanup_finished(self, keep_days: int = 7) -> int:
        """완료/실패/중지된 오래된 세션 정리.

        Returns:
            정리된 세션 수
        """
        import datetime as dt

        cutoff = datetime.now() - dt.timedelta(days=keep_days)
        cleaned = 0
        for f in _sessions_dir().glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data["status"] in ("completed", "failed", "stopped"):
                    finished = data.get("finished_at", "")
                    if finished and datetime.fromisoformat(finished) < cutoff:
                        f.unlink()
                        cleaned += 1
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        return cleaned

    def _save_session(self, project_slug: str, session: dict):
        """세션 상태 파일 저장."""
        path = _session_file(project_slug)
        path.write_text(
            json.dumps(session, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _mark_dead(self, project_slug: str, session: dict):
        """프로세스가 죽었는데 running으로 남은 세션을 정리."""
        # pipeline_state.json에서 최종 상태 판단
        state_path = _state_path(project_slug)
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if state.get("failed_steps"):
                    session["status"] = "failed"
                else:
                    session["status"] = "completed"
            except (json.JSONDecodeError, KeyError):
                session["status"] = "failed"
        else:
            session["status"] = "failed"

        session["finished_at"] = session.get("finished_at") or datetime.now().isoformat()

        # exit code 확인 시도
        log_path = Path(session.get("log_file", ""))
        if log_path.exists():
            try:
                tail = log_path.read_text(encoding="utf-8", errors="replace")[-500:]
                if "Pipeline completed" in tail or "파이프라인 완료" in tail:
                    session["status"] = "completed"
            except OSError:
                pass

        self._save_session(project_slug, session)
