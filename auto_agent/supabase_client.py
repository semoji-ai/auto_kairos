"""
Supabase 클라이언트 — 비활성화됨.

Supabase 동기화는 제거되었습니다.
이 모듈은 기존 import를 유지하기 위한 스텁입니다.
"""
from __future__ import annotations

# Storage 버킷 이름 (호환성 유지)
BUCKET_NAME = "kairos-assets"


def get_supabase():
    """항상 None 반환 — Supabase 비활성화됨."""
    return None


def supabase_enabled() -> bool:
    """항상 False — Supabase 비활성화됨."""
    return False
