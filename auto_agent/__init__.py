"""Auto Agent — AI 영상 제작 파이프라인."""
try:
    from importlib.metadata import version
    __version__ = version("auto-agent")
except Exception:
    __version__ = "0.0.0"
