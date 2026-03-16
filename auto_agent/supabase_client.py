"""
Supabase 클라이언트 싱글톤.

환경변수:
  SUPABASE_URL  — 프로젝트 URL (https://xxx.supabase.co)
  SUPABASE_KEY  — anon 또는 service_role 키
"""
from __future__ import annotations

import os
from typing import Optional

_client: Optional["Client"] = None


def get_supabase():
    """Supabase Client 싱글톤. 첫 호출 시 초기화."""
    global _client
    if _client is not None:
        return _client

    try:
        from supabase import create_client, Client
    except ImportError:
        raise ImportError(
            "supabase 패키지가 필요합니다: pip install supabase"
        )

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL 및 SUPABASE_KEY 환경변수를 설정하세요."
        )

    _client = create_client(url, key)
    return _client


def supabase_enabled() -> bool:
    """Supabase 동기화가 가능한 환경인지 확인."""
    return bool(
        os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")
    )


# Storage 버킷 이름
BUCKET_NAME = os.environ.get("SUPABASE_BUCKET", "kairos-assets")
