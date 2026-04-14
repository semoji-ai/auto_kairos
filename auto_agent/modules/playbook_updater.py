"""
Playbook Updater — 영상 성과 데이터를 channel_playbook.json에 반영.

성과 피드백 흐름:
  upload_info.json  →  (업로드 후 video_id 기입)
  youtube_analytics →  views/likes/comments 수집
  playbook_updater  →  channel_playbook.json 학습 데이터 갱신
  release-manager   →  다음 영상에서 learned_patterns 참조

CLI:
  python3 -m auto_agent.modules.playbook_updater \\
      --channel quirky_cartoon \\
      --video-id dQw4w9WgXcQ \\
      --title "전기차가 먼저였다" \\
      --title-type reversal_hook \\
      --views-7d 12400 \\
      --views-28d 31000 \\
      [--ctr-7d 6.2] [--ctr-28d 5.8] \\
      [--avg-view-duration-pct 48] \\
      [--tags "#전기차 #자동차역사"] \\
      [--notes "반전형 제목이 초기 CTR 높음"]
"""
import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from auto_agent.paths import get_package_dir

logger = logging.getLogger(__name__)

PLAYBOOK_PATH = get_package_dir() / "data" / "channel_playbook.json"
ROLLING_WINDOW = 20  # 학습에 반영할 최근 영상 수


def load_playbook() -> dict:
    if not PLAYBOOK_PATH.exists():
        raise FileNotFoundError(f"channel_playbook.json 없음: {PLAYBOOK_PATH}")
    return json.loads(PLAYBOOK_PATH.read_text(encoding="utf-8"))


def save_playbook(playbook: dict):
    playbook["_last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    PLAYBOOK_PATH.write_text(
        json.dumps(playbook, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info("channel_playbook.json 저장 완료")


def record_performance(
    channel: str,
    video_id: str,
    title: str,
    title_type: str,
    views_7d: int,
    views_28d: Optional[int] = None,
    ctr_7d: Optional[float] = None,
    ctr_28d: Optional[float] = None,
    avg_view_duration_pct: Optional[float] = None,
    top_tags: Optional[list] = None,
    notes: str = "",
):
    """새 영상 성과 데이터를 플레이북에 기록하고 패턴을 갱신한다."""
    playbook = load_playbook()

    channels = playbook.get("channels", {})
    if channel not in channels:
        raise ValueError(f"플레이북에 채널 없음: {channel}")

    ch = channels[channel]

    # ── 1. 성과 레코드 추가 ──────────────────────────────────
    record = {
        "video_id": video_id,
        "title": title,
        "title_type": title_type,
        "views_7d": views_7d,
        "views_28d": views_28d,
        "ctr_7d": ctr_7d,
        "ctr_28d": ctr_28d,
        "avg_view_duration_pct": avg_view_duration_pct,
        "top_tags": top_tags or [],
        "notes": notes,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    ts = ch["title_strategy"]
    learned = ts.setdefault("learned_patterns", [])
    learned.append(record)

    # 롤링 윈도우 유지
    if len(learned) > ROLLING_WINDOW:
        ts["learned_patterns"] = learned[-ROLLING_WINDOW:]

    # ── 2. 제목 타입별 성과 집계 갱신 ──────────────────────────
    perf_by_type = ts.setdefault("performance_by_type", {})
    _update_type_stats(perf_by_type, title_type, views_7d, views_28d, ctr_7d, ctr_28d)

    # ── 3. 고성과 해시태그 갱신 ─────────────────────────────────
    if top_tags and views_7d > _channel_avg_views(ts["learned_patterns"], "views_7d"):
        ht = ch["hashtag_strategy"].setdefault("learned_high_performance_tags", [])
        for tag in top_tags:
            if tag not in ht:
                ht.append(tag)
        # 최대 30개 유지
        ch["hashtag_strategy"]["learned_high_performance_tags"] = ht[-30:]

    # ── 4. 썸네일 패턴 메모 ─────────────────────────────────────
    if notes:
        thumb_patterns = ch["thumbnail_strategy"].setdefault("learned_patterns", [])
        thumb_patterns.append({
            "video_id": video_id,
            "note": notes,
            "views_7d": views_7d,
            "recorded_at": record["recorded_at"],
        })
        ch["thumbnail_strategy"]["learned_patterns"] = thumb_patterns[-10:]

    save_playbook(playbook)

    # ── 5. 요약 출력 ─────────────────────────────────────────────
    _print_summary(channel, ch, title_type, views_7d, ctr_7d)


def _update_type_stats(perf_by_type: dict, title_type: str,
                       views_7d: int, views_28d: Optional[int],
                       ctr_7d: Optional[float], ctr_28d: Optional[float]):
    """타입별 평균 성과 누적 갱신 (이동 평균)."""
    entry = perf_by_type.setdefault(title_type, {
        "count": 0,
        "avg_views_7d": 0,
        "avg_views_28d": 0,
        "avg_ctr_7d": None,
        "avg_ctr_28d": None,
    })
    n = entry["count"]
    n_new = n + 1

    entry["avg_views_7d"] = round((entry["avg_views_7d"] * n + views_7d) / n_new)

    if views_28d is not None:
        prev = entry["avg_views_28d"] or 0
        entry["avg_views_28d"] = round((prev * n + views_28d) / n_new)

    if ctr_7d is not None:
        prev = entry["avg_ctr_7d"] or 0
        entry["avg_ctr_7d"] = round((prev * n + ctr_7d) / n_new, 2)

    if ctr_28d is not None:
        prev = entry["avg_ctr_28d"] or 0
        entry["avg_ctr_28d"] = round((prev * n + ctr_28d) / n_new, 2)

    entry["count"] = n_new


def _channel_avg_views(learned: list, key: str) -> float:
    vals = [r[key] for r in learned if r.get(key) is not None]
    return sum(vals) / max(len(vals), 1)


def _print_summary(channel: str, ch: dict, title_type: str, views_7d: int, ctr_7d: Optional[float]):
    perf = ch["title_strategy"].get("performance_by_type", {})
    print(f"\n{'='*50}")
    print(f"📊 채널 플레이북 갱신 완료 — {ch['channel_name']}")
    print(f"  기록된 제목 타입: {title_type}")
    print(f"  7일 조회수: {views_7d:,}")
    if ctr_7d is not None:
        print(f"  7일 CTR: {ctr_7d}%")
    print(f"\n  📈 제목 타입별 평균 성과 (누적):")
    for t, stat in sorted(perf.items(), key=lambda x: -x[1].get("avg_views_7d", 0)):
        ctr_str = f", CTR {stat['avg_ctr_7d']}%" if stat.get("avg_ctr_7d") else ""
        print(f"    {t}: 평균 {stat['avg_views_7d']:,}회 (n={stat['count']}){ctr_str}")
    print(f"{'='*50}\n")


def get_best_title_type(channel: str) -> Optional[str]:
    """성과 데이터 기준으로 가장 좋은 제목 타입 반환. 데이터 없으면 None."""
    try:
        playbook = load_playbook()
        ch = playbook["channels"].get(channel, {})
        perf = ch.get("title_strategy", {}).get("performance_by_type", {})

        if not perf:
            return None

        # CTR 데이터 있으면 CTR 우선, 없으면 조회수 기준
        has_ctr = any(v.get("avg_ctr_7d") is not None for v in perf.values())
        key = "avg_ctr_7d" if has_ctr else "avg_views_7d"

        best = max(perf.items(), key=lambda x: x[1].get(key) or 0)
        return best[0] if best[1].get("count", 0) >= 3 else None  # 최소 3개 이상일 때만 신뢰
    except Exception:
        return None


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="채널 플레이북 성과 기록")
    parser.add_argument("--channel", required=True, help="채널 ID (quirky_cartoon / semoji)")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--title", required=True, help="실제 업로드한 제목")
    parser.add_argument("--title-type", required=True,
                        choices=["numeric_hook", "reversal_hook", "empathy_hook", "curiosity_hook"])
    parser.add_argument("--views-7d", type=int, required=True)
    parser.add_argument("--views-28d", type=int, default=None)
    parser.add_argument("--ctr-7d", type=float, default=None)
    parser.add_argument("--ctr-28d", type=float, default=None)
    parser.add_argument("--avg-view-duration-pct", type=float, default=None)
    parser.add_argument("--tags", default="", help="공백 구분 해시태그 목록")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    tags = [t for t in args.tags.split() if t.startswith("#")] if args.tags else []

    record_performance(
        channel=args.channel,
        video_id=args.video_id,
        title=args.title,
        title_type=args.title_type,
        views_7d=args.views_7d,
        views_28d=args.views_28d,
        ctr_7d=args.ctr_7d,
        ctr_28d=args.ctr_28d,
        avg_view_duration_pct=args.avg_view_duration_pct,
        top_tags=tags,
        notes=args.notes,
    )


if __name__ == "__main__":
    main()
