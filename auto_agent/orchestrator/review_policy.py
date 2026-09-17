"""Shared stopping criteria; a plateau stops spending, never turns failure into PASS."""
from __future__ import annotations


def blocking_issues(review: dict) -> bool:
    block = review.get("spine_blocking") or review.get("score_breakdown", {}).get("spine_blocking") or {}
    if isinstance(block, dict):
        return bool(block.get("failed_gates"))
    return bool(block)


def review_rank(review: dict) -> tuple:
    return (not blocking_issues(review), review.get("verdict") == "PASS",
            float(review.get("score", review.get("score_total", 0))))


def stop_reason(review: dict, previous_best: dict | None, threshold: float) -> str | None:
    score = float(review.get("score", review.get("score_total", 0)))
    if review.get("verdict") == "PASS" and score >= threshold and not blocking_issues(review):
        return "quality_pass"
    if review.get("review_unavailable") or review.get("scorer") == "heuristic":
        return "review_unavailable"
    if previous_best is not None and review_rank(review) <= review_rank(previous_best):
        return "no_quality_gain"
    if not review.get("revision_instructions"):
        return "no_actionable_revision"
    return None
