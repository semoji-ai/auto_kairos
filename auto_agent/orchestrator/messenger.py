"""
messenger.py
============
파이프라인 메신저 메시지 빌더.

step_labels.json의 메타데이터를 활용해:
- 사용자 친화적 한글 라벨
- step별 핵심 결과 추출
- phase 시작 요약
- 실패 원인 분류 + 복구 명령
- pipeline 완료 카드

호출 예:
    from auto_agent.orchestrator.messenger import Messenger
    m = Messenger(project_dir, project_slug)
    text = m.step_done("step_0d", elapsed_sec=237.2)
    _notify("Director", text, ...)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auto_agent.paths import DATA_DIR

_LABELS_CACHE: dict | None = None


def _load_labels() -> dict:
    global _LABELS_CACHE
    if _LABELS_CACHE is None:
        path = DATA_DIR / "step_labels.json"
        if path.exists():
            _LABELS_CACHE = json.loads(path.read_text(encoding="utf-8"))
        else:
            _LABELS_CACHE = {"phases": {}, "steps": {}, "failure_patterns": {}}
    return _LABELS_CACHE


def _fmt_duration(seconds: float) -> str:
    """초 → 사람이 읽기 좋은 형식."""
    s = int(seconds)
    if s < 60:
        return f"{seconds:.1f}초"
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}분 {sec}초" if sec else f"{m}분"
    h, rem = divmod(s, 3600)
    m = rem // 60
    return f"{h}시간 {m}분" if m else f"{h}시간"


class Messenger:
    """프로젝트 컨텍스트가 있는 메시지 빌더."""

    def __init__(self, project_dir: Path, project_slug: str):
        self.project_dir = Path(project_dir)
        self.project_slug = project_slug
        self.labels = _load_labels()

    # ── 라벨 조회 ─────────────────────────────────────────────────────

    def step_meta(self, step_id: str) -> dict:
        """step의 라벨/아이콘/예상시간 등 메타데이터."""
        return self.labels.get("steps", {}).get(step_id, {})

    def phase_meta(self, phase_id: str) -> dict:
        return self.labels.get("phases", {}).get(phase_id, {})

    def step_label(self, step_id: str, fallback: str = "") -> str:
        """예: `📝 기획안 생성` 또는 fallback (보통 step name)."""
        meta = self.step_meta(step_id)
        if meta:
            return f"{meta.get('icon', '')} {meta.get('label', step_id)}".strip()
        return fallback or step_id

    # ── 시작 메시지 ───────────────────────────────────────────────────

    def pipeline_start(self, topic: str, art_style: str, base_theme: str,
                       writing_style: str, duration_min, brief_loaded: str,
                       phases_count: int) -> str:
        """파이프라인 호출 직후 알림."""
        return (
            f"🎬 **{topic}** — {duration_min}분 영상 제작 시작\n"
            f"📋 진행 단계: {phases_count}개 phase 순차 실행\n"
            f"🎨 아트스타일: `{art_style}` ({base_theme})  /  문체: `{writing_style}`\n"
            f"기획안 사전 로드: {brief_loaded}"
        )

    def phase_start(self, phase_id: str, phase_name: str, steps: list[dict]) -> str:
        """phase 진입 시 단계 목록 + 예상 시간."""
        ph_meta = self.phase_meta(phase_id)
        icon = ph_meta.get("icon", "")
        what = ph_meta.get("what", "")
        # 예상 총 시간
        total_sec = sum(self.step_meta(s["id"]).get("expected_seconds", 30) for s in steps)
        eta = _fmt_duration(total_sec)
        # 단계 목록
        lines = []
        for i, s in enumerate(steps, 1):
            label = self.step_label(s["id"], s.get("name", s["id"]))
            lines.append(f"  {i}. {label}")
        return (
            f"{icon} **{phase_name}** — {len(steps)}개 작업, 예상 {eta}\n"
            f"{what}\n" + "\n".join(lines)
        )

    def step_start(self, step_id: str, step_name: str = "") -> str | None:
        """긴 작업(>30초)만 시작 알림. 짧은 작업은 None 반환."""
        meta = self.step_meta(step_id)
        expected = meta.get("expected_seconds", 0)
        if expected < 30:
            return None
        label = self.step_label(step_id, step_name)
        what = meta.get("what", "")
        eta = _fmt_duration(expected)
        return f"{label} 시작 — {what} (예상 {eta})"

    # ── 완료 메시지 (핵심 결과 포함) ──────────────────────────────────

    def step_done(self, step_id: str, elapsed_sec: float,
                  step_name: str = "", cost_usd: float = 0.0) -> str:
        """완료 메시지 — 산출물에서 핵심 결과 추출."""
        label = self.step_label(step_id, step_name)
        elapsed_str = _fmt_duration(elapsed_sec)
        cost_str = f", ${cost_usd:.4f}" if cost_usd > 0 else ""

        summary = self._extract_summary(step_id)
        if summary:
            return f"{label} 완료 ({elapsed_str}{cost_str})\n{summary}"
        return f"{label} 완료 ({elapsed_str}{cost_str})"

    # ── 실패 메시지 (원인 + 복구) ─────────────────────────────────────

    def step_failed(self, step_id: str, error: str,
                    step_name: str = "", is_blocking: bool = True) -> str:
        """실패 메시지 — 원인 분류 + 복구 명령."""
        label = self.step_label(step_id, step_name)
        category, hint = self._diagnose_failure(error)
        recovery = (
            f"`auto-agent run --project {self.project_slug} --from {step_id}`"
        )
        block_note = "" if is_blocking else " (non-blocking, 파이프라인 계속됨)"
        return (
            f"❌ **{label} 실패**{block_note}\n"
            f"분류: {category}\n"
            f"원인: {error[:120]}\n"
            f"💡 {hint}\n"
            f"🔄 재시도: {recovery}"
        )

    # ── Pipeline 완료 카드 ────────────────────────────────────────────

    def pipeline_done(self, completed: int, total: int, failed: int,
                      cost_usd: float, total_elapsed_sec: float = 0) -> str:
        """전체 완료 요약 — 산출물 + 비용."""
        success = failed == 0
        icon = "✅" if success else "⚠️"
        head = f"{icon} **{self.project_slug}** "
        head += "완성!" if success else f"종료 (실패 {failed}건)"

        lines = [head, "━━━━━━━━━━━━━━━━━━━━━"]

        # 핵심 산출물
        outputs = self._collect_final_outputs()
        if outputs:
            lines.append("📁 산출물:")
            for o in outputs:
                lines.append(f"  • {o}")

        # 점수 요약
        scores = self._collect_scores()
        if scores:
            lines.append(f"📊 품질: {scores}")

        # 통계
        stats = f"📈 {completed}/{total} 완료"
        if total_elapsed_sec > 0:
            stats += f", {_fmt_duration(total_elapsed_sec)} 소요"
        if cost_usd > 0:
            stats += f", ${cost_usd:.2f}"
        lines.append(stats)

        # 다음 단계 힌트
        if success and (self.project_dir / "scene_specs.json").exists():
            lines.append(f"🚀 다음: `auto-agent multi-contents --project {self.project_slug}` (쇼츠/블로그)")

        return "\n".join(lines)

    # ── 내부: 결과 추출기 ────────────────────────────────────────────

    def _extract_summary(self, step_id: str) -> str:
        """step별 산출물에서 핵심 정보 한 줄 추출."""
        extractor = self.step_meta(step_id).get("result_extractor")
        if not extractor:
            return ""
        try:
            fn = getattr(self, f"_extract_{extractor}", None)
            if fn:
                return fn() or ""
        except Exception:
            pass
        return ""

    def _read_json(self, *names) -> dict | None:
        for name in names:
            p = self.project_dir / name
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return None

    def _extract_editorial_brief(self) -> str:
        d = self._read_json("editorial_brief.v1.json", "editorial_brief.json")
        if not d:
            return ""
        cq = d.get("core_question", "")[:80]
        return f'> "{cq}..."' if cq else ""

    def _extract_brief_review(self) -> str:
        d = self._read_json("brief_review_feedback.v1.json")
        if not d:
            return ""
        score = d.get("score_total") or d.get("final_score", 0)
        verdict = d.get("verdict") or d.get("final_verdict", "")
        rounds = d.get("round") or d.get("rounds_count") or len(d.get("rounds", []) or []) or 1
        verdict_emoji = "✅" if verdict == "PASS" else ("🔄" if verdict == "REVISE" else "❌")
        return f"{verdict_emoji} `{score}점 {verdict}` (라운드 {rounds}회)"

    def _extract_config_check(self) -> str:
        d = self._read_json("config_check.json")
        if not d:
            return ""
        status = d.get("status", "")
        fixes = d.get("fixes_applied", [])
        warns = d.get("warnings", [])
        if fixes or warns:
            return f"상태 `{status}` — 자동보정 {len(fixes)}건, 경고 {len(warns)}건"
        return f"상태 `{status}`"

    def _extract_skeleton(self) -> str:
        d = self._read_json("skeleton.json")
        if not d:
            return ""
        chapters = d.get("chapters") or d.get("outline") or []
        return f"📐 {len(chapters)}개 챕터 골격"

    def _extract_source_ingest(self) -> str:
        d = self._read_json("source_ingest_status.json")
        if not d:
            return ""
        claims = d.get("claim_count", 0)
        sources = d.get("source_count", 0)
        return f"📚 {claims}개 사실, {sources}개 출처 확보"

    def _extract_chapter_facts(self) -> str:
        # chapter_facts/ 디렉토리 파일 수
        d = self.project_dir / "chapter_facts"
        if not d.is_dir():
            return ""
        n = len(list(d.glob("*.json")))
        return f"🔗 {n}개 챕터 사실 매핑"

    def _extract_brief_deepen_v2(self) -> str:
        d = self._read_json("brief_deepen_log.v2.json")
        if not d:
            return ""
        delta = d.get("score_delta", 0)
        new_score = d.get("new_score", 0)
        sign = "+" if delta >= 0 else ""
        return f"📊 v2 점수 `{new_score}` ({sign}{delta})"

    def _extract_brief_deepen_v3(self) -> str:
        d = self._read_json("brief_deepen_log.v3.json")
        if not d:
            return ""
        delta = d.get("score_delta", 0)
        new_score = d.get("new_score", 0)
        sign = "+" if delta >= 0 else ""
        return f"📊 v3 점수 `{new_score}` ({sign}{delta})"

    def _extract_draft(self) -> str:
        p = self.project_dir / "draft.md"
        if not p.exists():
            return ""
        chars = len(p.read_text(encoding="utf-8"))
        # research_questions.json 카운트
        q = self._read_json("research_questions.json") or {}
        n_q = len(q.get("questions", [])) if isinstance(q, dict) else 0
        if n_q:
            return f"✏️ 초고 {chars:,}자, 질문 {n_q}개"
        return f"✏️ 초고 {chars:,}자"

    def _extract_targeted_claims(self) -> str:
        d = self._read_json("targeted_claims.json")
        if not d:
            return ""
        claims = d.get("claims", [])
        return f"🎯 정밀 사실 {len(claims)}건"

    def _extract_manuscript(self) -> str:
        p = self.project_dir / "final_manuscript.md"
        if not p.exists():
            return ""
        chars = len(p.read_text(encoding="utf-8"))
        return f"📜 최종 원고 {chars:,}자"

    def _extract_scene_specs(self) -> str:
        d = self._read_json("scene_specs.json")
        if not d:
            return ""
        scenes = d.get("scenes", [])
        return f"🎞️ {len(scenes)}개 씬"

    def _extract_scene_data(self) -> str:
        d = self._read_json("scene_specs.json")
        if not d:
            return ""
        scenes = d.get("scenes", [])
        filled = sum(1 for s in scenes if s.get("items") or s.get("values") or s.get("headline"))
        return f"📊 데이터 채움 {filled}/{len(scenes)}씬"

    def _extract_factcheck(self) -> str:
        d = self._read_json("factcheck_report.json")
        if not d:
            return ""
        passed = d.get("passed", 0)
        failed = d.get("failed", 0)
        return f"🔬 PASS {passed}, FAIL {failed}"

    def _extract_assembly(self) -> str:
        # audio/, images/ 디렉토리 파일 수
        a = len(list((self.project_dir / "audio").glob("*"))) if (self.project_dir / "audio").is_dir() else 0
        i = len(list((self.project_dir / "images").rglob("scene_*.png"))) if (self.project_dir / "images").is_dir() else 0
        return f"🎨 음성 {a}개, 이미지 {i}개"

    def _extract_upload_info(self) -> str:
        d = self._read_json("upload_info.json")
        if not d:
            return ""
        titles = d.get("titles") or []
        return f"🚀 제목 {len(titles)}종 + 업로드 패키지 완성"

    # ── 최종 산출물 수집 ──────────────────────────────────────────────

    def _collect_final_outputs(self) -> list[str]:
        outs = []
        # 영상
        for p in self.project_dir.glob("*_final.mp4"):
            outs.append(f"`{p.name}`")
            break
        # 매니페스트
        if (self.project_dir / "remotion" / "manifest.json").exists():
            outs.append("`remotion/manifest.json`")
        # 씬 specs
        if (self.project_dir / "scene_specs.json").exists():
            outs.append("`scene_specs.json`")
        return outs

    def _collect_scores(self) -> str:
        scores = []
        d = self._read_json("brief_review_feedback.v1.json")
        if d:
            s = d.get("score_total") or d.get("final_score", 0)
            if s:
                scores.append(f"기획 `{s}점`")
        d = self._read_json("review_feedback.json")
        if d:
            s = d.get("score_total", 0)
            if s:
                scores.append(f"원고 `{s}점`")
        d = self._read_json("factcheck_report.json")
        if d:
            v = d.get("overall_verdict") or d.get("verdict", "")
            if v:
                scores.append(f"팩트 `{v}`")
        return " / ".join(scores)

    # ── 실패 분류 ────────────────────────────────────────────────────

    def _diagnose_failure(self, error: str) -> tuple[str, str]:
        patterns = self.labels.get("failure_patterns", {})
        for key, p in patterns.items():
            if key == "unknown":
                continue
            for matcher in p.get("matchers", []):
                if matcher in error:
                    return p.get("category", key), p.get("hint", "")
        unknown = patterns.get("unknown", {})
        return unknown.get("category", "기타 오류"), unknown.get("hint", "로그 확인 후 재시도")
