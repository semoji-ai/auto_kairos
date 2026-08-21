#!/usr/bin/env python3
"""시기별 자료 도서관을 씬에 붙인다 — 그 씬이 서 있는 연대의 모습으로.

씬별 조사는 씬 하나에 자료 하나를 찾는다. 그것만으로는 부족하다. 같은 증류소도
1900년과 오늘이 다르고, 같은 위스키도 병과 라벨이 시대마다 바뀐다. 1908년 왕실
공급 장면에 현행 병을 그리면 시대가 어긋난다.

그래서 대상×시기로 모은 도서관을 **씬의 연대에 맞춰** 붙인다.

  ① 대상 — 씬 텍스트에 그 대상의 낱말이 있는가
  ② 연대 — 씬이 말하는 해와 자료의 시기가 가까운가

연대는 나레이션의 네 자리 연도에서 읽는다. 없으면 그 씬은 현재형으로 본다.
가장 가까운 시기 자료를 먼저 붙이고, 편차가 크면 note 에 적어 둔다.

    python3 scripts/map_timeline_refs.py <project_dir> --library <timeline.json>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 대상 → 그 대상을 가리키는 낱말. 씬 텍스트에서 찾는다.
SUBJECT_KEYS = {
    "클라이넬리쉬(구) = 현 브로라": ["브로라", "원조", "클라이넬리쉬 B", "옛 클라이넬리쉬"],
    "클라이넬리쉬(신)": ["클라이넬리쉬"],
    "탈리스커 증류소·카보스트·해안·부두": ["탈리스커", "카보스트", "스카이섬", "부두"],
    "더프타운(싱글톤) 증류소": ["더프타운", "싱글톤"],
    "라가불린 증류소·아일라 남쪽 해안·만": ["라가불린", "아일라"],
    "탈리스커 증류기 — U자 라인암·정화기·웜텁·2+3 배치":
        ["웜텁", "라인암", "워시 스틸", "스피릿 스틸", "환류", "콘덴서", "증류기"],
    "클라이넬리쉬 포트 스틸과 리시버": ["증류기를 운전", "받아 모으", "왁시", "리시버"],
    "라가불린 증류기·나무 워시백 10기": ["워시백", "발효"],
    "옛 석탄 직화 가열 방식": ["석탄불", "직접 가열", "밸브", "화재", "불길"],
    "클라이넬리쉬 14년": ["클라이넬리쉬 14년"],
    "탈리스커 10년": ["탈리스커 10년"],
    "싱글톤 더프타운 15년": ["싱글톤 더프타운 15년", "싱글톤 15년"],
    "싱글톤 53년(1964년 증류, 117병)": ["53년", "117병", "호그스헤드"],
    "라가불린 16년": ["라가불린 16년"],
    "조니워커 골드 라벨": ["골드 라벨", "조니워커 골드"],
    "조니워커 블랙 라벨": ["블랙 라벨"],
    "화이트 홀스 병·라벨·광고": ["화이트 홀스", "백마"],
    "화이트 홀스 신문 광고(영국, 19세기말~20세기초)": ["화이트 홀스", "백마", "왕실", "영국군"],
    "하이랜드 클리어런스 / 서덜랜드 강제이주 회화·판화·지도":
        ["클리어런스", "강제 이주", "쫓아냈", "쫓겨난", "밀려났", "서덜랜드 영지"],
}

YEAR = re.compile(r"(1[6-9]\d{2}|20[0-2]\d)")

# 시대 민감도 — 병과 광고는 그 시점의 것이어야 한다. 1908년 왕실 공급 장면에
# 현행 병을 붙이면 시대가 어긋난다. 건물과 설비는 형태가 오래 가므로 느슨하다.
STRICT = 20    # 병·광고·회화: 이 이상 벌어지면 붙이지 않는다
LOOSE = 200    # 건물·설비: 형태 참고용으로 허용
SUBJECT_TOL = {
    "클라이넬리쉬 14년": STRICT, "탈리스커 10년": STRICT,
    "싱글톤 더프타운 15년": STRICT, "싱글톤 53년(1964년 증류, 117병)": STRICT,
    "라가불린 16년": STRICT, "조니워커 골드 라벨": STRICT,
    "조니워커 블랙 라벨": STRICT, "화이트 홀스 병·라벨·광고": STRICT,
    "화이트 홀스 신문 광고(영국, 19세기말~20세기초)": STRICT,
}


def era_year(era: str) -> int | None:
    """자료 시기를 대표 연도 하나로 환산한다. 현재형은 2024로 본다."""
    s = str(era or "")
    if "현재" in s or "2020년대" in s:
        return 2024
    ys = YEAR.findall(s)
    if ys:
        return int(ys[0])
    m = re.search(r"(\d{4})년대", s)
    if m:
        return int(m.group(1)) + 5
    return None


def scene_year(sc: dict) -> int | None:
    text = " ".join(str(sc.get(f) or "") for f in ("narration", "headline", "background_context"))
    ys = YEAR.findall(text)
    return int(ys[0]) if ys else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--library", required=True, type=Path)
    ap.add_argument("--max-per-scene", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    p = a.project / "scene_specs.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    lib = [x for x in json.loads(a.library.read_text(encoding="utf-8"))["assets"]
           if x.get("found")]

    for x in lib:
        x["_y"] = era_year(x.get("era"))

    stat = {"scenes": 0, "refs": 0, "gap": 0}
    for sc in scenes:
        text = " ".join(str(sc.get(f) or "") for f in
                        ("narration", "headline", "background_context", "concept", "title"))
        sy = scene_year(sc)
        hits = []
        for x in lib:
            keys = SUBJECT_KEYS.get(x.get("subject"), [])
            if not any(k in text for k in keys):
                continue
            # 연대 거리 — 씬에 연도가 없으면 현재형으로 본다
            want = sy if sy else 2024
            gap = abs((x["_y"] or want) - want)
            if gap > SUBJECT_TOL.get(x.get("subject"), LOOSE):
                continue
            hits.append((gap, x))
        if not hits:
            continue
        hits.sort(key=lambda t: t[0])
        ia = sc.setdefault("imageAsset", {})
        refs = ia.setdefault("refAssets", [])
        added = 0
        for gap, x in hits:
            if added >= a.max_per_scene:
                break
            if any(r.get("url") == x.get("image_url") for r in refs):
                continue
            note = f"{x.get('subject')} / {x.get('era')}"
            if gap >= 40:
                # 시대가 멀면 그대로 그리면 안 된다. 형태 참고용이라고 적어 둔다
                note += f" ⚠ 씬 연대와 {gap}년 차 — 형태만 참고"
                stat["gap"] += 1
            refs.append({
                "desc": x.get("what", ""), "url": x.get("image_url", ""),
                "page": x.get("page_url", ""), "holder": x.get("holder", ""),
                "license": x.get("license", ""), "era": x.get("era", ""),
                "subject": x.get("subject", ""), "note": note,
            })
            added += 1
            stat["refs"] += 1
        if added:
            stat["scenes"] += 1

    print(f"  레퍼런스 붙은 씬 {stat['scenes']} / 전체 {len(scenes)}")
    print(f"  붙은 자료 {stat['refs']}건  (시대 차 40년 이상 경고 {stat['gap']}건)")
    if a.dry_run:
        print("  (dry-run — 저장하지 않음)")
        return 0
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
