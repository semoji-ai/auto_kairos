"""Auto Kairos — AI Video Production Pipeline."""
try:
    from importlib.metadata import version
    __version__ = version("auto-kairos")
except Exception:
    try:
        __version__ = version("auto-agent")
    except Exception:
        __version__ = "3.0.0"
