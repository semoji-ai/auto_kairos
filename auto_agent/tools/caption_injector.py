"""원고의 `<!-- caption: ... -->` 마커를 scene_specs의 items로 결정적 주입.

배경: caption 마커는 "나레이션에서 뺐지만 화면에는 남겨야 할 용어·수치"다.
script-director에게 맡기면 의역하거나 누락해서(실측 반영률 5/9) 정작 보존하려던
숫자가 사라진다. 그래서 LLM 판단이 아니라 텍스트 매칭으로 확정 주입한다.

사용: python -m auto_agent.tools.caption_injector <project_dir> [--dry-run]
"""
from __future__ import annotations

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

CAPTION_RE = re.compile(r'<!--\s*caption:\s*(.*?)\s*-->', re.S)


def _norm(text: str) -> str:
    """비교용 정규화 — 공백/기호 제거."""
    return re.sub(r'[\s\.,·"\'“”‘’!?()\[\]*—-]', '', text)


def parse_captions(manuscript: str) -> list[tuple[str, list[str]]]:
    """(선행 나레이션 텍스트, [자막 항목...]) 목록을 원고 순서대로 반환."""
    out: list[tuple[str, list[str]]] = []
    for m in CAPTION_RE.finditer(manuscript):
        items = [p.strip() for p in m.group(1).split('/') if p.strip()]
        if not items:
            continue
        # 마커 앞쪽 텍스트에서 주석·구분자를 걷어낸 마지막 대목을 앵커로 쓴다
        before = manuscript[:m.start()]
        before = re.sub(r'<!--.*?-->', '', before, flags=re.S)
        chunk = re.split(r'\n---\n|\n# Ch', before)[-1]
        anchor = ' '.join(chunk.split())
        out.append((anchor, items))
    return out


def _best_scene(anchor: str, scenes: list[dict]) -> int | None:
    """앵커 텍스트와 가장 잘 맞는 씬 index. 임계값 미만이면 None."""
    a = _norm(anchor)[-160:]
    if not a:
        return None
    best_i, best_score = None, 0.0
    for i, s in enumerate(scenes):
        n = _norm(s.get('narration') or '')
        if not n:
            continue
        # 앵커 꼬리가 나레이션에 포함되면 확실한 매칭
        tail = a[-40:]
        if tail and tail in n:
            return i
        score = SequenceMatcher(None, a, n[-len(a):] if len(n) > len(a) else n).ratio()
        if score > best_score:
            best_i, best_score = i, score
    return best_i if best_score >= 0.45 else None


ITEMS_LAYOUTS = {'items_list', 'items_grid'}

# 의역 판정 임계값. "현금 보상" vs "현금 425달러" = 0.36,
# "재구매 할인" vs "새 LG폰 구매 시 700달러 할인" = 0.44 를 모두 잡되
# 무관한 항목("F1.8 조리개" vs "레이저 오토포커스")은 걸리지 않는 수준.
_PARAPHRASE_THRESHOLD = 0.35


def _find_paraphrase(existing: list[str], caption_item: str) -> str | None:
    """기존 items 중 caption_item과 같은 대상을 가리키는 의역을 찾는다."""
    target = _norm(caption_item)
    if not target:
        return None
    best, best_score = None, 0.0
    for c in existing:
        n = _norm(c)
        if not n:
            continue
        if n in target or target in n:
            return c
        score = SequenceMatcher(None, n, target).ratio()
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= _PARAPHRASE_THRESHOLD else None


def inject(manuscript: str, spec: dict) -> dict:
    """scene_specs dict에 caption 항목을 주입한 새 dict 반환."""
    scenes = spec.get('scenes') if isinstance(spec, dict) else spec
    if not isinstance(scenes, list):
        return spec

    report = {'total': 0, 'injected': 0, 'unmatched': []}
    for anchor, items in parse_captions(manuscript):
        report['total'] += len(items)
        idx = _best_scene(anchor, scenes)
        if idx is None:
            report['unmatched'].extend(items)
            continue
        sc = scenes[idx]
        cur = list(sc.get('items') or [])
        for it in items:
            # 에이전트가 의역해 넣은 항목("현금 보상")은 원문("현금 425달러")으로 교체한다.
            # 의역을 남겨두면 자막으로 보존하려던 수치가 화면에서 사라진다.
            dup = _find_paraphrase(cur, it)
            if dup is not None:
                cur[cur.index(dup)] = it
            else:
                cur.append(it)
            report['injected'] += 1
        sc['items'] = cur
        # items가 보이지 않는 레이아웃이면 노출 가능한 레이아웃으로 승격
        if sc.get('layout') not in ITEMS_LAYOUTS and len(cur) >= 2:
            sc['layout'] = 'items_list'
    spec['_caption_injection'] = report
    return spec


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    proj = Path(sys.argv[1])
    dry = '--dry-run' in sys.argv
    ms = proj / 'final_manuscript.md'
    sp = proj / 'scene_specs.json'
    if not ms.exists() or not sp.exists():
        print(f'[caption] 파일 없음: {ms.name} 또는 {sp.name}')
        return 1

    manuscript = ms.read_text(encoding='utf-8')
    spec = json.loads(sp.read_text(encoding='utf-8'))
    spec = inject(manuscript, spec)
    rep = spec.get('_caption_injection', {})
    print(f"[caption] {proj.name}: {rep.get('injected')}/{rep.get('total')} 주입"
          + (f", 미매칭 {rep['unmatched']}" if rep.get('unmatched') else ''))

    if not dry:
        bak = proj / 'scene_specs.pre_caption.json'
        if not bak.exists():
            bak.write_text(json.dumps(json.loads(sp.read_text(encoding='utf-8')),
                                      ensure_ascii=False, indent=2), encoding='utf-8')
        sp.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
