import json
import subprocess
import sys
from pathlib import Path

import pytest

from auto_agent.modules.scene_coverage_module import allocate, inventory, validate


TEXT = '# Ch 1. 시작\n<!-- chars: A -->\n첫 문장입니다. 둘째는 3.1%입니다.\n---\n# Ch 2. 다음\n**끝입니다.**'


def scenes(*pairs):
    return {'scenes': [{'chapter': ch, 'narration': text} for ch, text in pairs]}


def test_inventory_retains_all_sentences_and_decimal():
    rows = inventory(TEXT)['sentences']
    assert [r['text'] for r in rows] == ['첫 문장입니다.', '둘째는 3.1%입니다.', '끝입니다.']
    assert [r['chapter'] for r in rows] == [1, 1, 2]
    assert rows[0]['characters'] == ['A']


def test_context_allocation_reconstructs_not_model_narration():
    sk, directions = allocate(inventory(TEXT)['sentences'], [
        {'sourceSentences': [1, 2], 'narration': 'invented', 'layout': 'cinematic'},
        {'sourceSentences': [3], 'layout': 'flow'}])
    assert sk[0]['characters'] == ['A']
    assert sk[0]['narration'] == '첫 문장입니다. 둘째는 3.1%입니다.'
    assert validate(inventory(TEXT), TEXT, {'scenes': sk})['ok']
    assert directions[1]['sceneNumber'] == 2


@pytest.mark.parametrize('groups', [[[1],[3]], [[1,2],[2,3]], [[2,1],[3]], [[1,2,3]], [[1,2],[],[3]]])
def test_allocation_rejects_invalid_partition(groups):
    with pytest.raises(ValueError):
        allocate(inventory(TEXT)['sentences'], [{'sourceSentences': g} for g in groups])


def test_contextual_merge_and_inside_sentence_split_allowed():
    assert validate(inventory(TEXT), TEXT, scenes((1, '첫 문장입니다. 둘째는'), (1, '3.1%입니다.'), (2, '끝입니다.')))['ok']


@pytest.mark.parametrize('body', [
    '첫 문장입니다.',  # omission
    '첫 문장입니다. 첫 문장입니다. 둘째는 3.1%입니다.',  # duplicate
    '둘째는 3.1%입니다. 첫 문장입니다.',  # reordering
    '첫 문장입니다. 둘째는 31%입니다.',  # numbers/punctuation
    '첫 문장입니다. 둘째는 3.1%입니다. 새 말입니다.',
])
def test_rejects_loss_or_rewriting(body):
    assert not validate(inventory(TEXT), TEXT, scenes((1, body), (2, '끝입니다.')))['ok']


def test_chapter_and_stale_source_rejected():
    assert not validate(inventory(TEXT), TEXT, scenes((2, '첫 문장입니다. 둘째는 3.1%입니다. 끝입니다.')))['ok']
    assert not validate(inventory(TEXT), TEXT + '\n', scenes((1, '첫 문장입니다. 둘째는 3.1%입니다.'), (2, '끝입니다.')))['ok']


def test_cli_blocks_and_never_rewrites_source(tmp_path):
    (tmp_path / 'final_manuscript.md').write_text(TEXT)
    specs = scenes((1, '첫 문장입니다.'))
    (tmp_path / 'scene_specs.json').write_text(json.dumps(specs))
    cmd = [sys.executable, '-m', 'auto_agent.modules.scene_coverage_module']
    assert subprocess.run(cmd + ['prepare', '--project-dir', str(tmp_path)]).returncode == 0
    assert subprocess.run(cmd + ['validate', '--project-dir', str(tmp_path)]).returncode == 1
    assert json.loads((tmp_path / 'scene_specs.json').read_text()) == specs
    assert (tmp_path / 'final_manuscript.md').read_text() == TEXT


def test_pipeline_gates_surround_chapter_generation():
    data = json.loads(Path('auto_agent/data/pipeline.json').read_text())
    def steps(obj):
        if isinstance(obj, dict):
            if 'id' in obj: yield obj
            for v in obj.values(): yield from steps(v)
        elif isinstance(obj, list):
            for v in obj: yield from steps(v)
    all_steps = list(steps(data)); ids = [s['id'] for s in all_steps]
    assert ids.index('step_2_sentences') < ids.index('step_2_plan') < ids.index('step_2') < ids.index('step_2_coverage') < ids.index('step_2_review')
    for s in all_steps:
        if s['id'] in ('step_2_sentences', 'step_2_coverage'):
            assert s['blocking'] and s['skip_resume']


def test_multiline_quote_and_block_metadata():
    text = '  ## Chapter 1: 시작\n<!-- chars: A, B -->\n<!-- caption: 수익 / 3.1% -->\n그는\n“정말일까요?” 다음입니다.\n<!-- note: 넓은 샷 -->\n---\n## 챕터 2\n끝입니다.'
    rows = inventory(text)['sentences']
    assert [r['text'] for r in rows] == ['그는 “정말일까요?”', '다음입니다.', '끝입니다.']
    assert [r['chapter'] for r in rows] == [1, 1, 2]
    assert rows[0]['characters'] == ['A', 'B']
    assert rows[1]['captions'] == ['수익 / 3.1%']
    assert rows[0]['productionNotes'] == ['note: 넓은 샷']
    assert rows[2]['characters'] == []


def test_offset_partition_reconstructs_sentence():
    rows = inventory('첫 절이고 다음 절입니다.')['sentences']
    n = len(rows[0]['text'])
    sk, _ = allocate(rows, [
        {'sourceSpans': [{'id': 1, 'start': 0, 'end': 6}]},
        {'sourceSpans': [{'id': 1, 'start': 6, 'end': n}]},
    ])
    assert ''.join(s['narration'] for s in sk) == rows[0]['text']
    assert validate(inventory(rows[0]['text']), rows[0]['text'], {'scenes': sk})['ok']


@pytest.mark.parametrize('start,end', [(7, 15), (5, 15), (6, 99), (True, 15), (6, 6)])
def test_offset_partition_rejects_gap_overlap_and_invalid_ranges(start, end):
    rows = inventory('첫 절이고 다음 절입니다.')['sentences']
    with pytest.raises(ValueError):
        allocate(rows, [
            {'sourceSpans': [{'id': 1, 'start': 0, 'end': 6}]},
            {'sourceSpans': [{'id': 1, 'start': start, 'end': end}]},
        ])


def test_empty_scene_and_tampered_inventory_rejected():
    text = '원문입니다.'
    ledger = inventory(text)
    assert not validate(ledger, text, scenes((0, ''), (0, text)))['ok']
    ledger['sentences'][0]['text'] = '조작입니다.'
    assert not validate(ledger, text, scenes((0, '조작입니다.')))['ok']


@pytest.mark.parametrize('decisions', [None, [None], [{'sourceSentences': None}], [{'sourceSentences': '1'}]])
def test_malformed_allocation_is_a_validation_error(decisions):
    with pytest.raises(ValueError):
        allocate(inventory('원문.')['sentences'], decisions)


def runner_for_project(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from auto_agent.orchestrator.runner import PipelineRunner
    r = PipelineRunner.__new__(PipelineRunner)
    r.project_dir, r.project_slug = tmp_path, 'coverage-test'
    r.project = {'id': 'coverage-test'}
    r.state = SimpleNamespace(config={}, current_phase='stage_2', current_step='')
    r.pm = Mock()
    r.context_memory = Mock()
    r.context_memory.build_context_prompt.return_value = ''
    for name in ('_warm_chapter_cache', '_auto_build_and_capture'):
        monkeypatch.setattr(r, name, lambda *a, **kw: None)
    monkeypatch.setattr('auto_agent.orchestrator.runner._notify', lambda *a, **kw: None)
    monkeypatch.setattr(r, '_load_agent_skill', lambda *a: '')
    monkeypatch.setattr(r, '_load_agents_config', lambda: {'subagents': {}})
    monkeypatch.setattr(r, '_plan_slice_for_chapter', lambda *a: '')
    monkeypatch.setattr(r, '_get_agent_timeout', lambda *a: 30)
    return r


def fake_allocation_cli(step, prompt, **kwargs):
    from types import SimpleNamespace
    import re
    rows = json.loads(prompt.split('<sentence_inventory>')[1].split('</sentence_inventory>')[0])
    path = re.search(r'(/[^\n]+\.json) 에 JSON', prompt)[1]
    Path(path).write_text(json.dumps({'scenes': [
        {'sourceSentences': [r['id']], 'layout': 'cinematic', 'motion': 'fade',
         'narration': '모델이 쓴 잘못된 원고'} for r in rows
    ]}))
    return SimpleNamespace(returncode=0, text='', error='', usage={}, duration_sec=0)


def test_only_split_without_headings_and_existing_force_path(tmp_path, monkeypatch):
    r = runner_for_project(tmp_path, monkeypatch)
    monkeypatch.setattr(r, '_run_selected_cli', fake_allocation_cli)
    (tmp_path / 'final_manuscript.md').write_text('첫 문장입니다. 다음 문장입니다.')
    old = '{"scenes": [{"narration": "보존 대상"}], "title": "기존 제목"}'
    (tmp_path / 'scene_specs.json').write_text(old)
    r._force = True
    result = r._run_chunked_parallel({'id': 'step_2', 'mode': 'chapters'})
    assert result.status == 'completed', result.error
    specs = json.loads((tmp_path / 'scene_specs.json').read_text())
    assert [s['narration'] for s in specs['scenes']] == ['첫 문장입니다.', '다음 문장입니다.']
    assert specs['title'] == '기존 제목'
    assert any(p.read_text() == old for p in (tmp_path / 'scene_split_backups').glob('*.json'))


def test_resume_stale_scenes_fails_without_overwrite(tmp_path, monkeypatch):
    r = runner_for_project(tmp_path, monkeypatch)
    (tmp_path / 'final_manuscript.md').write_text('변경된 원고입니다.')
    old = '{"scenes": [{"chapter": 0, "narration": "예전 원고입니다."}]}'
    (tmp_path / 'scene_specs.json').write_text(old)
    result = r._run_chunked_parallel({'id': 'step_2', 'mode': 'chapters'})
    assert result.status == 'failed'
    assert (tmp_path / 'scene_specs.json').read_text() == old


def test_incomplete_chapter_never_replaces_existing_specs_even_legacy(tmp_path, monkeypatch):
    from auto_agent.orchestrator.runner import ChapterResult
    r = runner_for_project(tmp_path, monkeypatch)
    (tmp_path / 'final_manuscript.md').write_text('# Ch 1\n하나.\n# Ch 2\n둘.')
    old = '{"scenes": [{"chapter": 0, "narration": "예전 원고입니다."}]}'
    (tmp_path / 'scene_specs.json').write_text(old)
    r._force = True
    r.state.config = {'execution': {'profile': 'legacy'}}
    monkeypatch.setattr(r, '_execute_manuscript_chapter', lambda step, ch, text: ChapterResult(
        chapter=ch, status='completed' if ch == 1 else 'failed',
        scenes=[{'sceneNumber': 1, 'chapter': 1, 'narration': '하나.'}] if ch == 1 else [], error='invalid allocation'))
    result = r._run_chunked_parallel({'id': 'step_2', 'mode': 'chapters'})
    assert result.status == 'failed'
    assert (tmp_path / 'scene_specs.json').read_text() == old


def test_review_mutation_blocks_next_stage_even_nonblocking(tmp_path, monkeypatch):
    from auto_agent.orchestrator.runner import StepResult
    from auto_agent.modules.scene_coverage_module import prepare
    r = runner_for_project(tmp_path, monkeypatch)
    (tmp_path / 'final_manuscript.md').write_text('원문입니다.')
    prepare(tmp_path)
    target = tmp_path / 'scene_specs.json'
    target.write_text(json.dumps(scenes((0, '원문입니다.'))))
    def mutate(step):
        target.write_text(json.dumps(scenes((0, '바뀌었습니다.'))))
        return StepResult(step_id=step['id'], status='completed')
    monkeypatch.setattr(r, '_execute_step_unchecked', mutate, raising=False)
    result = r._execute_step({'id': 'step_2_review', 'input': ['scene_specs.json'], 'blocking': False})
    assert result.status == 'failed' and result.error.startswith('FATAL:')


def test_allocation_preserves_direction_fields_and_production_metadata(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from auto_agent.modules.scene_coverage_module import prepare
    r = runner_for_project(tmp_path, monkeypatch)
    text = '<!-- chars: A --><!-- caption: 연도 / 장소 -->\n본문입니다.'
    (tmp_path / 'final_manuscript.md').write_text(text)
    prepare(tmp_path)
    def cli(*args, **kw):
        return SimpleNamespace(returncode=0, text=json.dumps({'scenes': [{
            'sourceSentences': [1], 'infoStructure': 'scene', 'beat': 'hook',
            'keyVisual': True, 'characters': ['WRONG'], 'layout': 'cinematic', 'motion': 'fade'
        }]}), error='', usage={}, duration_sec=0)
    monkeypatch.setattr(r, '_run_selected_cli', cli)
    result = r._execute_manuscript_chapter({'id': 'step_2'}, 0, text)
    assert result.status == 'completed'
    assert result.scenes[0]['characters'] == ['A']
    assert result.scenes[0]['items'] == ['연도', '장소']
    assert result.scenes[0]['infoStructure'] == 'scene'
    assert result.scenes[0]['beat'] == 'hook'
    assert result.scenes[0]['keyVisual'] is True


@pytest.mark.parametrize('provider', ['claude', 'codex'])
def test_selected_cli_error_does_not_fall_back_or_replace_scenes(tmp_path, monkeypatch, provider):
    from auto_agent.modules.scene_coverage_module import prepare
    from auto_agent.orchestrator.execution import ExecutionResult
    r = runner_for_project(tmp_path, monkeypatch)
    r.state.config = {'execution': {'provider': provider}}
    (tmp_path / 'final_manuscript.md').write_text('원문입니다.')
    prepare(tmp_path)
    old = '{"scenes": []}'
    (tmp_path / 'scene_specs.json').write_text(old)
    calls = []
    def fail(spec, *args, **kw):
        calls.append(spec.provider)
        return ExecutionResult(returncode=1, error='fixture CLI failure')
    monkeypatch.setattr('auto_agent.orchestrator.runner.run_cli', fail)
    result = r._execute_manuscript_chapter({'id': 'step_2'}, 0, '원문입니다.')
    assert result.status == 'failed' and result.error == 'fixture CLI failure'
    assert calls == [provider]
    assert (tmp_path / 'scene_specs.json').read_text() == old


def test_block_caption_is_not_repeated_on_every_split_scene():
    text = '<!-- caption: 1968년 -->\n시작했습니다. 다음 해 커졌습니다.'
    rows = inventory(text)['sentences']
    sk, _ = allocate(rows, [{'sourceSentences': [1]}, {'sourceSentences': [2]}])
    assert sk[0]['_captions'] == ['1968년']
    assert sk[1]['_captions'] == []
    assert rows[1]['captions'] == ['1968년']  # Still available as direction context.


def test_nested_cuts_rejected_instead_of_silently_creating_nonflat_scenes():
    with pytest.raises(ValueError):
        allocate(inventory('원문.')['sentences'], [{'sourceSentences': [1], 'cuts': [{'angle': 'wide'}]}])
