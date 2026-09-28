"""Read-only storyboard view of sentence/cut plans and their asset reviews.

Candidate images never become selected render assets through this adapter.
"""
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

LABELS = {
    'keep': '현재 이미지 유지', 'edit': '기존 화면 편집·보완',
    'remake': '장면 신규·재제작', 'archive': '실제 자료로 교체·확보',
    'compare': '도해 비교 후 확정', 'pending': '검토 필요',
}
LINKS = {'new': '새 장면', 'continuous': '연속 컷', 'hold': '앞 컷 유지'}
MODES = {'scene': '장면', 'archive': '실제 자료', 'scene_overlay': '장면 위 설명',
         'text_overlay': '텍스트 합성', 'infographic_candidate': '도해 비교 후보', 'title': '타이틀'}
SCREEN_MODES = {'drawn_scene': '장면 그림', 'real_source': '실제 자료',
                'diagram_title_or_edited_montage': '도해·타이틀·편집 구성',
                'typing_transition': '타이핑 전환'}


def _rows(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        rows = data.get('cuts', []) if isinstance(data, dict) else []
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


def _image_url(root, raw):
    if not raw or not isinstance(raw, str):
        return None
    try:
        image = (root / raw).resolve()
        relative = image.relative_to(root)
        if not image.is_file() or image.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp'}:
            return None
        return '/output/' + quote(root.name, safe='') + '/' + quote(relative.as_posix(), safe='/')
    except (OSError, ValueError):
        return None


def _spoken(text):
    return re.sub(r'\[자사 발표 기준 표시\]', '', text or '').strip()


def _content_screen_plan(root):
    path = root / 'scene_visual_review_v7/screen_plan_227.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    rows = data.get('scenes', []) if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return {}
    return {row['sceneNumber']: row for row in rows
            if isinstance(row, dict) and isinstance(row.get('sceneNumber'), int)}


def attach_storyboard_cuts(scenes, output_dir):
    """Join only cuts named by the current scene; return optional review summary."""
    if output_dir and any(s.get('analysis_version') == 'independent_scene_v4' for s in scenes):
        root = Path(output_dir).resolve()
        content_plan = _content_screen_plan(root)
        counts = Counter()
        for scene in scenes:
            decision = scene.get('review_decision', 'pending')
            if decision not in LABELS:
                decision = 'pending'
            scene['_cut_decisions'] = decision
            scene['_cut_review_stale'] = (not scene.get('non_spoken') and
                _spoken(scene.get('narration')) != _spoken(scene.get('narrationExact')))
            planned = content_plan.get(scene.get('sceneNumber'), {})
            if (planned.get('sceneId') != scene.get('sceneId') or
                    _spoken(planned.get('narrationExact')) != _spoken(scene.get('narrationExact'))):
                planned = {}
            scene['_scene_review'] = {
                'decision': decision, 'decision_label': LABELS[decision],
                'reason': scene.get('review_reason', ''),
                # A reference from an older grouped scene is evidence for review,
                # never the selected image of this independent scene.
                'image_url': scene.get('_image_url'),
                'reference_url': _image_url(root, scene.get('review_reference_image')),
                'is_selected_image': bool(scene.get('_image_url')),
                'selected_label': ('자료 원본 선택 · 화면 합성 전'
                                   if (scene.get('imageAsset') or {}).get('source') == 'provided'
                                   else '선택된 씬 이미지'),
                'link_label': LINKS.get(scene.get('continuity'), '새 장면'),
                'mode_label': MODES.get(scene.get('visual_mode'), ''),
                'screen_mode_label': SCREEN_MODES.get(planned.get('screen_mode'), ''),
                'screen_direction': planned.get('screen_direction', ''),
            }
            counts[decision] += 1
        return {'flat': True, 'total': len(scenes), 'scene_count': len(scenes),
                'counts': dict(counts), 'labels': LABELS}
    if not output_dir or not any(s.get('cutIds') for s in scenes):
        return None
    root = Path(output_dir).resolve()
    plans = {r.get('cutId'): r for r in _rows(root / 'scene_analysis_v3/cut_plan.json')}
    reviews = {r.get('cutId'): r for r in _rows(root / 'scene_analysis_v3/lg_review/cut_review.json')}
    counts = Counter()
    stale_count = 0
    for scene in scenes:
        if not scene.get('cutIds'):
            continue
        cuts = []
        stale = ('narrationExact' in scene and
                 _spoken(scene.get('narration')) != _spoken(scene['narrationExact']))
        for cid in dict.fromkeys(scene['cutIds']):
            plan = plans.get(cid, {})
            if plan.get('sceneNumber') != scene['sceneNumber']:
                plan = {}
            review = reviews.get(cid, {})
            if (not plan or review.get('sceneNumber') != scene['sceneNumber'] or
                    review.get('narrationExact') != plan.get('narrationExact')):
                review = {}
            decision = review.get('decision', 'pending')
            if decision not in LABELS:
                decision = 'pending'
            image = review.get('existing_image') or plan.get('reference_image')
            link = review.get('link', plan.get('lg_continuity', ''))
            cuts.append({
                'cutId': cid, 'decision': decision, 'decision_label': LABELS[decision],
                'narration': plan.get('narrationExact', '컷 원문 연결을 확인해야 합니다.'),
                'sentence_ids': plan.get('sentenceIds', []),
                'direction': plan.get('direction', ''),
                'reason': review.get('reason', '현재 씬과 일치하는 검토 결과가 없습니다.'),
                'shot': review.get('size', plan.get('shot_size', '')),
                'angle': review.get('camera', plan.get('angle', '')),
                'link_label': LINKS.get(link, '연결 확인 필요'),
                'mode_label': MODES.get(review.get('planned_mode'), ''),
                'people': review.get('people', plan.get('people', [])),
                'image_url': _image_url(root, image),
                'source_package': review.get('source_package'),
            })
            counts[decision] += 1
        if cuts and all(plans.get(c['cutId'], {}).get('non_spoken') for c in cuts):
            stale = False
        scene['_cuts'] = cuts
        scene['_cut_decisions'] = ' '.join(sorted({c['decision'] for c in cuts}))
        scene['_cut_review_stale'] = stale
        stale_count += int(stale)
    return {'total': sum(counts.values()), 'counts': dict(counts), 'labels': LABELS,
            'scene_count': sum(bool(s.get('_cuts')) for s in scenes), 'stale_count': stale_count}
