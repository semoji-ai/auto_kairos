import copy,json
import pytest
from auto_agent.research.jev_scene import SceneJudge
class Judge:
    def __init__(self, answer):self.answer=answer;self.calls=0
    def decide(self,state,questions):self.calls+=1;return {k:self.answer[k] for k in questions}
    def metrics(self):return {'calls':self.calls}

def sample():
    original={'narration':'마트에서 날짜를 확인합니다','imageAsset':{'source':'search','query':'expiry'}}
    scene=copy.deepcopy(original);scene['imageAsset']['url']='https://a'
    entry={'scene_index':0,'asset_kind':'search_image','auto_selected':True,'candidates':[
        {'image_url':'https://a','source':'wikimedia','width':1920,'license':'cc'},
        {'image_url':'https://b','source':'wikimedia','width':1920,'license':'cc'}]}
    return original,scene,entry

def answers(**kwargs):return dict(layout='single',representation='photo',**kwargs)
def test_no_observations_never_invents_visual_selection():
    old,scene,entry=sample();judge=Judge(answers());engine=SceneJudge(judge,{})
    engine.apply(scene,entry,old)
    assert scene['imageAsset']['url']=='https://a'
    assert entry['jev']['status']=='needs_observation'
    assert len(engine.observation_requests)==2

def test_observed_better_candidate_replaces_top():
    old,scene,entry=sample();j=Judge(answers(c0='fail',c1='pass',select='c1'))
    engine=SceneJudge(j,{'https://a':{'kind':'image','observation':'bottle only'},'https://b':{'kind':'image','observation':'real hand food date store'}})
    engine.apply(scene,entry,old)
    assert scene['imageAsset']['url']=='https://b' and entry['auto_selected']

def test_no_fit_restores_scene_and_queues_review():
    old,scene,entry=sample();j=Judge(answers(c0='fail',select='none'))
    SceneJudge(j,{'https://a':{'kind':'image','observation':'bottle'}}).apply(scene,entry,old)
    assert scene==old and not entry['auto_selected'] and entry['status']=='needs_review'

def test_partial_or_unknown_never_auto_accepts():
    old,scene,entry=sample();j=Judge(answers(c0='partial',select='c0'))
    SceneJudge(j,{'https://a':{'kind':'image','observation':'date unreadable'}}).apply(scene,entry,old)
    assert scene==old and not entry['auto_selected']

def test_license_resolution_gate_still_applies():
    old,scene,entry=sample();entry['candidates'][1]['license']='unknown'
    j=Judge(answers(c1='pass',select='c1'))
    SceneJudge(j,{'https://b':{'kind':'image','observation':'right contents'}}).apply(scene,entry,old)
    assert not entry['auto_selected'] and scene==old

def test_api_failure_preserves_legacy():
    old,scene,entry=sample()
    class Broken:
        def decide(self,*a):raise ValueError('secret')
    SceneJudge(Broken(),{}).apply(scene,entry,old)
    assert scene['imageAsset']['url']=='https://a' and entry['jev']['status']=='error'
    assert 'secret' not in json.dumps(entry)

def test_image_observation_not_used_as_video_evidence():
    old,scene,entry=sample();entry.update(asset_kind='video',candidates=[{'url':'https://a'}])
    SceneJudge(Judge(answers()),{'https://a':{'kind':'image','observation':'thumbnail'}}).apply(scene,entry,old)
    assert entry['jev']['status']=='needs_observation'

def test_enrichment_runs_optional_judge_and_persists_queue(tmp_path,monkeypatch):
    from auto_agent.modules import scene_enricher_module as m
    old,scene,entry=sample()
    old['visual_kind']='search_image'
    (tmp_path/'scene_specs.json').write_text(json.dumps({'scenes':[old]}))
    monkeypatch.setattr(m,'_enrich_image_scene',lambda *args,**kw:copy.deepcopy(entry))
    engine=SceneJudge(Judge(answers(c0='fail',select='none')),{'https://a':{'kind':'image','observation':'wrong'}})
    monkeypatch.setattr(SceneJudge,'from_project',lambda p:engine)
    result=m.enrich_project(tmp_path)
    assert result['summary']['needs_review']==1
    assert (tmp_path/'scene_judgements.json').exists()
    assert result['queue'][0]['jev']['status']=='review'

def test_disabled_or_keyless_does_not_call(monkeypatch,tmp_path):
    monkeypatch.delenv('TYPESAFE_API_KEY',raising=False)
    assert SceneJudge.from_project(tmp_path) is None
    monkeypatch.setenv('TYPESAFE_API_KEY','fake');monkeypatch.setenv('JEV_SCENE_REVIEW','0')
    assert SceneJudge.from_project(tmp_path) is None

def test_generated_scene_gets_advisory_analysis_without_mutation():
    scene={'narration':'여러 시대와 장소를 한 컷에 설명','visual_kind':'generate_image'}
    old=copy.deepcopy(scene);entry={'scene_index':0,'asset_kind':'plan','candidates':[]}
    engine=SceneJudge(Judge({'layout':'split','representation':'diagram'}),{})
    engine.apply(scene,entry,old)
    assert scene==old and entry['jev']['status']=='analysis_only'

def test_candidate_questions_explicitly_name_candidate():
    old,scene,entry=sample()
    class Inspector(Judge):
        def decide(self,state,questions):
            for key,options in questions.items():
                if key.startswith('c'):
                    assert all(key in text for text in options.values())
            return super().decide(state,questions)
    engine=SceneJudge(Inspector(answers(c0='pass',select='c0')),{'https://a':{'kind':'image','observation':'Observed source'}})
    engine.apply(scene,entry,old)
    assert entry['jev']['status']!='error'
