import json
from pathlib import Path

from auto_agent.dashboard.storyboard_cuts import attach_storyboard_cuts


def dump(root, name, value):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))


def fixture(root):
    (root / 'image.png').write_bytes(b'png')
    scenes = [{'sceneNumber': 1, 'cutIds': ['a', 'b'], 'narration': '원문', 'narrationExact': '원문'}]
    dump(root, 'scene_analysis_v3/cut_plan.json', {'cuts': [
        {'cutId': key, 'sceneNumber': 1, 'narrationExact': '원문', 'direction': '방향', 'shot_size': '중경'}
        for key in ['a', 'b']]})
    dump(root, 'scene_analysis_v3/lg_review/cut_review.json', {'cuts': [
        {'cutId': 'a', 'sceneNumber': 1, 'narrationExact': '원문', 'decision': 'keep', 'reason': '<script>x</script>', 'existing_image': 'image.png', 'link': 'new'},
        {'cutId': 'b', 'sceneNumber': 1, 'narrationExact': '원문', 'decision': 'remake', 'existing_image': '../private.png', 'link': 'continuous'}]})
    return scenes


def test_join_and_safe_images(tmp_path):
    scenes = fixture(tmp_path)
    summary = attach_storyboard_cuts(scenes, tmp_path)
    assert summary['total'] == 2
    assert summary['counts']['remake'] == 1
    a, b = scenes[0]['_cuts']
    assert a['image_url'].endswith('/image.png')
    assert b['image_url'] is None
    assert b['link_label'] == '연속 컷'
    assert 'selected' not in a
    assert scenes[0]['_cut_review_stale'] is False


def test_no_data_leaves_legacy_scenes_unchanged(tmp_path):
    scenes = [{'sceneNumber': 1, 'narration': 'legacy'}]
    assert attach_storyboard_cuts(scenes, tmp_path) is None
    assert scenes == [{'sceneNumber': 1, 'narration': 'legacy'}]


def test_mismatch_is_not_a_valid_review(tmp_path):
    scenes = fixture(tmp_path)
    scenes[0]['narration'] = '수정 원고'
    attach_storyboard_cuts(scenes, tmp_path)
    assert scenes[0]['_cut_review_stale'] is True


def test_cross_scene_review_not_attached(tmp_path):
    scenes = fixture(tmp_path)
    f = tmp_path / 'scene_analysis_v3/lg_review/cut_review.json'
    data = json.loads(f.read_text()); data['cuts'][0]['sceneNumber'] = 99
    f.write_text(json.dumps(data))
    attach_storyboard_cuts(scenes, tmp_path)
    assert scenes[0]['_cuts'][0]['decision'] == 'pending'


def test_partial_escapes_review_text_and_shows_original(tmp_path):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    scenes = fixture(tmp_path)
    attach_storyboard_cuts(scenes, tmp_path)
    env = Environment(loader=FileSystemLoader('auto_agent/dashboard/templates'), autoescape=select_autoescape())
    text = env.get_template('partials/_storyboard_cuts.html').render(scene=scenes[0])
    assert '&lt;script&gt;' in text and '<script>x' not in text
    assert 'data-cut-id="a"' in text and '원문' in text
    assert '최종 선택' in text


def test_unspoken_title_is_not_stale(tmp_path):
    scenes = fixture(tmp_path)
    scenes[0]['narration'] = ''
    scenes[0]['narrationExact'] = '(타이틀)'
    f = tmp_path / 'scene_analysis_v3/cut_plan.json'
    d = json.loads(f.read_text())
    for cut in d['cuts']:
        cut['non_spoken'] = True
    f.write_text(json.dumps(d))
    attach_storyboard_cuts(scenes, tmp_path)
    assert scenes[0]['_cut_review_stale'] is False


def test_outside_symlink_not_served(tmp_path):
    scenes = fixture(tmp_path)
    (tmp_path / 'image.png').unlink()
    (tmp_path / 'image.png').symlink_to(Path(__file__).resolve())
    attach_storyboard_cuts(scenes, tmp_path)
    assert scenes[0]['_cuts'][0]['image_url'] is None


def test_flat_review_has_no_nested_cuts(tmp_path):
    scenes=[{'sceneNumber':1,'analysis_version':'independent_scene_v4',
             'review_decision':'remake','review_reason':'새 앵글 필요',
             'narration':'본문','narrationExact':'본문','continuity':'continuous',
             'continuity_previous_scene':None}]
    summary=attach_storyboard_cuts(scenes,tmp_path)
    assert summary['flat'] is True and summary['total']==1
    assert '_cuts' not in scenes[0]
    assert scenes[0]['_scene_review']['decision']=='remake'


def test_remake_scene_does_not_display_old_reference(tmp_path):
    (tmp_path/'old.png').write_bytes(b'png')
    scenes=[{'sceneNumber':1,'analysis_version':'independent_scene_v4',
             'review_decision':'remake','review_reference_image':'old.png',
             'narration':'본문','narrationExact':'본문'}]
    attach_storyboard_cuts(scenes,tmp_path)
    assert scenes[0]['_scene_review']['image_url'] is None
    assert scenes[0]['review_reference_image']=='old.png'
    # A newly produced, explicitly selected image may be displayed later.
    scenes[0]['_image_url']='/output/project/new.png'
    attach_storyboard_cuts(scenes,tmp_path)
    assert scenes[0]['_scene_review']['image_url']=='/output/project/new.png'


def test_flat_scene_old_reference_is_link_only_without_selection(tmp_path):
    (tmp_path/'old.png').write_bytes(b'png')
    scenes=[{'sceneNumber':1,'analysis_version':'independent_scene_v4',
             'review_decision':'archive','review_reference_image':'old.png',
             'narration':'본문','narrationExact':'본문'}]
    attach_storyboard_cuts(scenes,tmp_path)
    review=scenes[0]['_scene_review']
    assert review['image_url'] is None
    assert review['reference_url'].endswith('/old.png')


def test_flat_provided_image_is_labeled_as_uncomposed_source(tmp_path):
    scenes=[{'sceneNumber':1,'analysis_version':'independent_scene_v4',
             '_image_url':'/output/p/images/provided/a.jpg',
             'imageAsset':{'source':'provided'},
             'narration':'본문','narrationExact':'본문'}]
    attach_storyboard_cuts(scenes,tmp_path)
    assert scenes[0]['_scene_review']['selected_label']=='자료 원본 선택 · 화면 합성 전'


def test_flat_scene_displays_content_first_plan_without_treating_editorial_link_as_frame_reuse(tmp_path):
    dump(tmp_path, 'scene_visual_review_v7/screen_plan_227.json', {'scenes': [
        {'sceneNumber': 1, 'sceneId': 's1', 'narrationExact': '왜일까요?',
         'screen_mode': 'typing_transition',
         'screen_direction': '질문을 타이핑하고 다음 장면으로 전환한다.'}
    ]})
    scenes = [{'sceneNumber': 1, 'sceneId': 's1', 'analysis_version': 'independent_scene_v4',
               'narration': '왜일까요?', 'narrationExact': '왜일까요?',
               'continuity': 'hold', 'continuity_previous_scene': 4,
               'shot_size': '클로즈업', 'camera_angle': '정면'}]
    attach_storyboard_cuts(scenes, tmp_path)
    review = scenes[0]['_scene_review']
    assert review['screen_mode_label'] == '타이핑 전환'
    assert review['screen_direction'] == '질문을 타이핑하고 다음 장면으로 전환한다.'
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(loader=FileSystemLoader('auto_agent/dashboard/templates'), autoescape=select_autoescape())
    html = env.get_template('partials/_storyboard_scene_review.html').render(scene=scenes[0])
    assert '타이핑 전환' in html and '질문을 타이핑하고' in html
    assert 'Scene 4에서 이어짐' not in html
