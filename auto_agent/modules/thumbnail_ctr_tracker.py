"""썸네일/제목 CTR 추적 + 래칫 학습 시스템.

Stage 3에서 썸네일 A/B/C 생성 → 업로드 후 Stage 4에서 CTR 추적
→ 어떤 패턴이 성과 좋은지 래칫으로 학습.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ThumbnailCTRTracker:
    """썸네일/제목 CTR 추적 + 래칫 학습."""

    def __init__(self, vault_dir: Path):
        self._vault_dir = vault_dir
        self._study_dir = vault_dir / "channels" / "thumbnails"
        self._study_dir.mkdir(parents=True, exist_ok=True)
        self._ratchet_path = self._study_dir / "thumbnail_ratchet.json"
        self._ratchet = self._load_ratchet()

    def _load_ratchet(self) -> Dict:
        if self._ratchet_path.exists():
            return json.loads(self._ratchet_path.read_text(encoding="utf-8"))
        return {
            "last_updated": "",
            "best_patterns": [],
            "title_patterns": {"number": 0, "question": 0, "reversal": 0, "empathy": 0},
            "design_patterns": {"text_position": {}, "font_size": {}, "overlay_opacity": {}},
            "total_tracked": 0,
        }

    def _save_ratchet(self):
        self._ratchet["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._ratchet_path.write_text(
            json.dumps(self._ratchet, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def record_upload(self, project: str, variant: str,
                       title: str, title_type: str,
                       design: Dict) -> Dict:
        """업로드 시 썸네일 정보 기록.

        Args:
            project: 프로젝트 slug
            variant: "A", "B", "C"
            title: 썸네일 제목 텍스트
            title_type: "number" | "question" | "reversal" | "empathy"
            design: {"text_position", "font_size", "overlay_opacity", ...}
        """
        record = {
            "project": project,
            "variant": variant,
            "title": title,
            "title_type": title_type,
            "design": design,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "ctr_1d": None,
            "ctr_3d": None,
            "ctr_7d": None,
            "impressions_7d": None,
            "status": "uploaded",
        }

        # 프로젝트별 기록 저장
        records_path = self._study_dir / f"{project}_thumbnails.json"
        records = []
        if records_path.exists():
            records = json.loads(records_path.read_text(encoding="utf-8"))
        records.append(record)
        records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

        return record

    def update_ctr(self, project: str, variant: str,
                    ctr: float, impressions: int, day: int = 7):
        """CTR 업데이트 (Stage 4에서 호출).

        Args:
            day: 1, 3, 7 (업로드 후 경과일)
        """
        records_path = self._study_dir / f"{project}_thumbnails.json"
        if not records_path.exists():
            return

        records = json.loads(records_path.read_text(encoding="utf-8"))
        for r in records:
            if r["variant"] == variant:
                r[f"ctr_{day}d"] = ctr
                if day == 7:
                    r["impressions_7d"] = impressions
                    r["status"] = "tracked"
                break

        records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

        # 래칫 업데이트
        if day == 7:
            self._update_ratchet(records)

    def _update_ratchet(self, records: List[Dict]):
        """7일 CTR 기반 래칫 업데이트."""
        tracked = [r for r in records if r.get("ctr_7d") is not None]
        if not tracked:
            return

        # 최고 CTR 기록
        best = max(tracked, key=lambda x: x["ctr_7d"])
        self._ratchet["total_tracked"] += 1

        # 패턴 점수 누적
        title_type = best.get("title_type", "")
        if title_type in self._ratchet["title_patterns"]:
            self._ratchet["title_patterns"][title_type] += 1

        design = best.get("design", {})
        for key in ["text_position", "font_size", "overlay_opacity"]:
            val = str(design.get(key, ""))
            if val:
                if val not in self._ratchet["design_patterns"][key]:
                    self._ratchet["design_patterns"][key][val] = 0
                self._ratchet["design_patterns"][key][val] += 1

        # best_patterns 업데이트 (최근 20개 유지)
        self._ratchet["best_patterns"].append({
            "project": best["project"],
            "title": best["title"],
            "title_type": title_type,
            "ctr_7d": best["ctr_7d"],
            "design": design,
        })
        self._ratchet["best_patterns"] = self._ratchet["best_patterns"][-20:]

        self._save_ratchet()
        logger.info("썸네일 래칫 업데이트: best CTR=%.2f%%, type=%s",
                     best["ctr_7d"], title_type)

    def get_recommendations(self) -> Dict:
        """현재 래칫 기반 추천 — 다음 썸네일 생성 시 참고."""
        patterns = self._ratchet["title_patterns"]
        design = self._ratchet["design_patterns"]

        # 가장 성과 좋은 제목 유형
        best_title_type = max(patterns, key=patterns.get) if any(patterns.values()) else "number"

        # 가장 성과 좋은 디자인
        best_position = max(design["text_position"], key=design["text_position"].get) if design["text_position"] else "bottom-left"
        best_font = max(design["font_size"], key=design["font_size"].get) if design["font_size"] else "72"

        return {
            "recommended_title_type": best_title_type,
            "recommended_position": best_position,
            "recommended_font_size": best_font,
            "total_tracked": self._ratchet["total_tracked"],
            "recent_best": self._ratchet["best_patterns"][-3:] if self._ratchet["best_patterns"] else [],
        }

    def analyze_competitor_thumbnails(self, study_data_path: Path) -> Dict:
        """경쟁 채널 썸네일 데이터에서 패턴 추출."""
        import re

        if not study_data_path.exists():
            return {}

        data = json.loads(study_data_path.read_text(encoding="utf-8"))
        analysis = {}

        for channel, videos in data.items():
            title_patterns = {"has_number": 0, "has_question": 0, "has_exclamation": 0, "total": len(videos)}
            top_titles = []

            for v in videos:
                title = v.get("title", "")
                ratio = v.get("view_sub_ratio", 0)

                if re.search(r"\d", title):
                    title_patterns["has_number"] += 1
                if "?" in title:
                    title_patterns["has_question"] += 1
                if "!" in title:
                    title_patterns["has_exclamation"] += 1

                top_titles.append({"title": title[:50], "ratio": round(ratio, 2)})

            # 비율로 변환
            n = max(len(videos), 1)
            analysis[channel] = {
                "number_rate": round(title_patterns["has_number"] / n * 100, 1),
                "question_rate": round(title_patterns["has_question"] / n * 100, 1),
                "exclamation_rate": round(title_patterns["has_exclamation"] / n * 100, 1),
                "top_3": sorted(top_titles, key=lambda x: x["ratio"], reverse=True)[:3],
            }

        return analysis
