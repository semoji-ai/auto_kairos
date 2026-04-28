"""HTTP helpers — urllib 기반. requests/httpx 의존 없음."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen

USER_AGENT = "auto-kairos/3.0 (research-collector)"
DEFAULT_TIMEOUT = 20

JsonFetcher = Callable[[str], dict[str, Any]]
TextFetcher = Callable[[str], str]


def fetch_json(url: str, *, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> dict[str, Any]:
    h = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(url: str, *, timeout: int = DEFAULT_TIMEOUT, headers: dict | None = None) -> str:
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")
