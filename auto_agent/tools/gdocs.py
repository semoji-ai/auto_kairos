"""Google Docs / Drive 연동 — 문서 생성·수정·삭제·댓글.

MCP 커넥터는 생성과 읽기만 지원해서, 오타 하나를 고치려 해도 문서를 새로 만들어야 했다.
Docs API의 batchUpdate와 Drive API의 files.delete / comments.create를 직접 쓰면
수정·삭제·댓글이 전부 가능하다.

인증: 기존 YouTube OAuth 클라이언트(.env의 YOUTUBE_CLIENT_ID/SECRET)를 재사용하되
Drive·Docs 스코프로 별도 토큰을 받는다. 최초 1회 브라우저 동의가 필요하다.

    python -m auto_agent.tools.gdocs auth          # 최초 1회 인증
    python -m auto_agent.tools.gdocs ls <폴더ID>
    python -m auto_agent.tools.gdocs create <폴더ID> <제목> <본문파일>
    python -m auto_agent.tools.gdocs replace <문서ID> <본문파일>
    python -m auto_agent.tools.gdocs rm <파일ID>
    python -m auto_agent.tools.gdocs comment <문서ID> <앵커문구> <댓글내용>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
CREDENTIALS_DIR = Path(__file__).resolve().parents[2] / ".credentials"
TOKEN_PATH = CREDENTIALS_DIR / "gdocs.json"
DOC_MIME = "application/vnd.google-apps.document"


def _client_config() -> dict:
    """OAuth 클라이언트 설정. GDOCS_* 우선, 없으면 YOUTUBE_* 재사용.

    유튜브 자격증명이 속한 GCP 프로젝트에 접근 권한이 없으면
    별도 프로젝트에서 클라이언트를 만들어 GDOCS_CLIENT_ID/SECRET로 넣으면 된다.
    """
    cid = os.environ.get("GDOCS_CLIENT_ID") or os.environ.get("YOUTUBE_CLIENT_ID")
    csec = os.environ.get("GDOCS_CLIENT_SECRET") or os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not cid or not csec:
        raise SystemExit(
            "OAuth 자격증명이 필요합니다. .env에 다음 중 하나를 설정하세요:\n"
            "  GDOCS_CLIENT_ID / GDOCS_CLIENT_SECRET  (권장, 전용 프로젝트)\n"
            "  YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET  (기존 재사용)"
        )
    return {
        "installed": {
            "client_id": cid,
            "client_secret": csec,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def get_credentials(interactive: bool = False) -> Credentials:
    creds: Optional[Credentials] = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    if not creds or not creds.valid:
        if not interactive:
            raise SystemExit(
                "인증 토큰이 없습니다. 먼저 실행하세요:\n"
                "  python -m auto_agent.tools.gdocs auth"
            )
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        flow = InstalledAppFlow.from_client_config(_client_config(), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _services(interactive: bool = False):
    creds = get_credentials(interactive)
    return (build("docs", "v1", credentials=creds, cache_discovery=False),
            build("drive", "v3", credentials=creds, cache_discovery=False))


# ── 기본 동작 ───────────────────────────────────────────────

def list_folder(folder_id: str) -> list[dict]:
    _, drive = _services()
    res = drive.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id,name,mimeType,modifiedTime)",
        pageSize=200,
    ).execute()
    return res.get("files", [])


def create_doc(folder_id: str, title: str, body: str) -> str:
    docs, drive = _services()
    meta = {"name": title, "mimeType": DOC_MIME, "parents": [folder_id]}
    doc_id = drive.files().create(body=meta, fields="id").execute()["id"]
    if body:
        docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": body}}]},
        ).execute()
    return doc_id


def replace_doc(doc_id: str, body: str) -> None:
    """본문 전체 교체. 문서 ID와 공유 링크가 유지된다."""
    docs, _ = _services()
    doc = docs.documents().get(documentId=doc_id).execute()
    end = doc["body"]["content"][-1]["endIndex"]
    requests = []
    if end > 2:  # 본문이 있으면 먼저 비운다 (마지막 개행은 삭제 불가)
        requests.append({"deleteContentRange":
                         {"range": {"startIndex": 1, "endIndex": end - 1}}})
    if body:
        requests.append({"insertText": {"location": {"index": 1}, "text": body}})
    if requests:
        docs.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def delete_file(file_id: str) -> None:
    _, drive = _services()
    drive.files().delete(fileId=file_id).execute()


def add_comment(doc_id: str, quoted: str, content: str) -> str:
    """⚠️ 이 댓글은 구글 문서 화면에 표시되지 않는다.

    Drive API comments.create는 kix 내부 앵커를 만들지 못해 '무앵커 댓글'이 되고,
    문서 UI에서는 보이지 않는다. 원고에 댓글을 달아야 하면
    docx_comments.build_docx로 .docx를 만들어 Drive에 덮어쓸 것.
    (scripts/push_to_gdocs.py 참고)
    """
    """문서의 특정 문구에 앵커 댓글을 단다.

    Drive API 댓글은 anchor 좌표 규격이 문서 리비전에 묶여 있어 까다롭다.
    여기서는 quotedFileContent로 대상 문구를 지정한다 — 구글 문서 UI에서
    해당 문구에 연결된 댓글로 표시된다.
    """
    _, drive = _services()
    body = {"content": content}
    if quoted:
        body["quotedFileContent"] = {"value": quoted}
    res = drive.comments().create(
        fileId=doc_id, body=body, fields="id"
    ).execute()
    return res["id"]


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    cmd = args[0]

    if cmd == "auth":
        get_credentials(interactive=True)
        print(f"✅ 인증 완료 → {TOKEN_PATH}")
    elif cmd == "ls":
        for f in list_folder(args[1]):
            print(f"{f['id']}  {f['modifiedTime'][:10]}  {f['name']}")
    elif cmd == "create":
        body = Path(args[3]).read_text(encoding="utf-8") if len(args) > 3 else ""
        print(create_doc(args[1], args[2], body))
    elif cmd == "replace":
        replace_doc(args[1], Path(args[2]).read_text(encoding="utf-8"))
        print("✅ 본문 교체 완료")
    elif cmd == "rm":
        delete_file(args[1])
        print("✅ 삭제 완료")
    elif cmd == "comment":
        print(add_comment(args[1], args[2], args[3]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
