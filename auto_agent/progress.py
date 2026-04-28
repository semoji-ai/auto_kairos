# -*- coding: utf-8 -*-
"""
모듈 스크립트용 진행 상황 보고 헬퍼.

사용법 (Python 스크립트에서):
    from auto_agent.progress import report

    report("TTS Generator", "씬 1/5 음성 생성 중")
    report("TTS Generator", "씬 1 완료 (3.2초, 512자)", level="success")
    report("Image Generator", "캐릭터 이미지 생성: 존 펨버턴")

환경변수 PROGRESS_FILE이 설정되면 해당 파일에 JSONL로 append.
미설정이면 Agent Messenger에 직접 전송 시도, 그것도 안되면 stdout 출력.
"""
import json
import os
import time


def _emit(msg: dict):
    # 1순위: PROGRESS_FILE (runner.py가 모니터링)
    progress_file = os.environ.get("PROGRESS_FILE")
    if progress_file:
        try:
            with open(progress_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            return
        except Exception:
            pass

    # 2순위: HTTP POST to dashboard messenger
    try:
        import urllib.request
        payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:8080/api/agent-messages/send",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
        return
    except Exception:
        pass

    # 3순위: stdout
    print(f"[{msg.get('agent', 'System')}] {msg.get('text', '')}")


def report(agent: str, text: str, level: str = "info", phase: str = "", data: dict = None):
    """진행 상황을 메신저로 전달."""
    msg = {
        "kind": "message",
        "agent": agent,
        "text": text,
        "level": level,
        "project": os.environ.get("PROJECT_NAME", ""),
        "timestamp": time.time(),
    }
    if phase:
        msg["phase"] = phase
    if data:
        msg["data"] = data

    _emit(msg)


def report_doc(
    agent: str,
    project: str,
    doc_type: str,
    doc_id: str,
    op: str,
    value=None,
    path: str = "",
    phase: str = "",
    text: str = "",
    level: str = "info",
    meta: dict = None,
):
    """문서 스트리밍 이벤트를 메신저로 전달."""
    msg = {
        "kind": "doc_update",
        "agent": agent,
        "text": text or f"{doc_type} 문서 업데이트",
        "level": level,
        "project": project,
        "timestamp": time.time(),
        "data": {
            "doc_type": doc_type,
            "doc_id": doc_id,
            "op": op,
            "path": path,
            "value": value,
            "meta": meta or {},
        },
    }
    if phase:
        msg["phase"] = phase

    _emit(msg)
