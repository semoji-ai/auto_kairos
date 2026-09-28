import json
from pathlib import Path
import pytest
from auto_agent.research.jev_targeted import JevJudge, TargetedPrefilter, prepare_targeted_context

class Judge:
    def __init__(self, choices): self.choices=iter(choices); self.calls=[]
    def decide(self, state, questions):
        self.calls.append(state)
        return {k: next(self.choices) for k in questions}
    def metrics(self): return {'calls':len(self.calls),'estimated_usd':0}

def test_selected_evidence_replaces_search_loop():
    searches=[]
    judge=Judge(['s0','p0','enough'])
    flow=TargetedPrefilter(judge, lambda q: searches.append(q) or [{'title':'source','url':'https://example.com/a','snippet':'mechanism'}], lambda u: 'The supported mechanism is described here. '*20)
    packet=flow.run([{'id':'q1','question':'How does it work?','priority':'high'}])
    q=packet['questions'][0]
    assert q['status']=='ready' and len(searches)==1
    assert q['evidence'][0]['url']=='https://example.com/a'
    assert 'supported mechanism' in q['evidence'][0]['text']

def test_insufficient_retries_once_and_preserves_question():
    judge=Judge(['s0','p0','more','s0','p0','more'])
    searches=[]
    flow=TargetedPrefilter(judge,lambda q: searches.append(q) or [{'url':'https://example.com/'+str(len(searches))}],lambda u:'Evidence text. '*40)
    q=flow.run([{'id':'q1','question':'Why?'}])['questions'][0]
    assert q['status']=='fallback' and len(searches)==2 and searches[0]!=searches[1]

def test_judge_error_does_not_drop_question():
    class Broken(Judge):
        def decide(self,*args): raise RuntimeError('secret must not be logged')
    packet=TargetedPrefilter(Broken([]),lambda q:[{'url':'https://example.com'}],lambda u:'x').run([{'id':'q1','question':'Why?'}])
    assert packet['questions'][0]['status']=='fallback'
    assert 'secret' not in json.dumps(packet)

def test_no_snippet_as_evidence():
    judge=Judge(['s0'])
    flow=TargetedPrefilter(judge,lambda q:[{'url':'https://example.com','snippet':'Looks sufficient'}],lambda u:'')
    q=flow.run([{'id':'q1','question':'Why?'}])['questions'][0]
    assert q['status']=='fallback' and not q['evidence']

def test_question_limit_preserves_unprocessed_questions():
    f=TargetedPrefilter(Judge([]),lambda q:[],lambda u:'',max_questions=0)
    assert f.run([{'id':'q1','question':'Why?'}])['questions'][0]['status']=='fallback'

def test_disabled_does_not_read_or_call(tmp_path,monkeypatch):
    monkeypatch.setenv('JEV_TARGETED_RESEARCH','0')
    assert prepare_targeted_context(tmp_path)==''

def test_budget_blocks_before_network(monkeypatch):
    j=JevJudge('fake',budget_usd=0)
    with pytest.raises(RuntimeError,match='budget'): j.decide({}, {'q':{'a':'A'}})

def test_invalid_choice_rejected(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'usage':{'input_tokens':100},'answers':{'q':{'choice':'invented'}}}
    monkeypatch.setattr('auto_agent.research.jev_targeted.requests.post',lambda *a,**k:Response())
    with pytest.raises(ValueError): JevJudge('fake').decide({}, {'q':{'a':'A'}})

def test_pipeline_injects_only_targeted_agent(tmp_path, monkeypatch):
    from unittest.mock import MagicMock
    from auto_agent.orchestrator.runner import PipelineRunner
    prepare = MagicMock(return_value='SELECTED_EVIDENCE_ONLY')
    monkeypatch.setattr('auto_agent.research.jev_targeted.prepare_targeted_context', prepare)
    runner = MagicMock()
    runner.project_dir=tmp_path; runner.project_slug='test'; runner.project={'topic':'topic'}
    runner.state.config={'duration_minutes':1}; runner.vault.enabled=False
    runner._load_agent_skill.return_value='skill'; runner._load_agents_config.return_value={}
    runner._resolve_style_skills.return_value=[]
    runner._load_editorial_brief.return_value=''; runner._load_creative_brief.return_value=''
    for agent in ['targeted-researcher','draft-writer']:
        prompt=PipelineRunner._build_agent_prompt(runner,{'id':'step','agent':agent})
        assert ('SELECTED_EVIDENCE_ONLY' in prompt)==(agent=='targeted-researcher')
    prepare.assert_called_once_with(tmp_path)

def test_cache_reuse_and_draft_invalidation(tmp_path, monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY','fake');monkeypatch.setenv('SERPER_API_KEY','fake')
    monkeypatch.delenv('JEV_TARGETED_RESEARCH',raising=False)
    (tmp_path/'research_questions.json').write_text(json.dumps({'questions':[{'id':'q1','question':'Why?'}]}))
    (tmp_path/'draft.md').write_text('draft1')
    calls=[]
    def run(self, questions):
        import time
        calls.append(questions)
        return {'questions':[{'question_id':'q1','status':'fallback','evidence':[]}],'created_at':time.time(),'metrics':{}}
    monkeypatch.setattr(TargetedPrefilter,'run',run)
    assert 'fallback' in prepare_targeted_context(tmp_path)
    prepare_targeted_context(tmp_path);assert len(calls)==1
    (tmp_path/'draft.md').write_text('draft2')
    prepare_targeted_context(tmp_path);assert len(calls)==2

def test_uncertain_api_failure_reserves_budget(monkeypatch):
    def fail(*args,**kwargs): raise TimeoutError()
    monkeypatch.setattr('auto_agent.research.jev_targeted.requests.post',fail)
    j=JevJudge('fake',budget_usd=.003)
    with pytest.raises(TimeoutError):j.decide({}, {'q':{'a':'A'}})
    with pytest.raises(RuntimeError,match='budget'):j.decide({}, {'q':{'a':'A'}})

def test_unreadable_source_uses_remaining_search():
    judge=Judge(['s0','s0','p0','enough'])
    calls=[]
    def search(q):
        calls.append(q)
        return [{'url':'https://example.com/'+str(len(calls))}]
    def fetch(u):
        if u.endswith('/1'): raise ValueError('blocked')
        return 'Useful original evidence. '*30
    result=TargetedPrefilter(judge,search,fetch).run([{'id':'q1','question':'Why?'}])
    assert result['questions'][0]['status']=='ready' and len(calls)==2

def test_valid_api_response_accounts_usage_without_secret(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self):return {'usage':{'input_tokens':123},'answers':{'q':{'type':'choice','choice':'a','probabilities':{'a':1.0}}}}
    monkeypatch.setattr('auto_agent.research.jev_targeted.requests.post',lambda *a,**k:Response())
    j=JevJudge('sensitive-key');assert j.decide({}, {'q':{'a':'A'}})=={'q':'a'}
    assert j.tokens==123 and j.reserved_tokens==0
    assert 'sensitive-key' not in json.dumps(j.trace)

def test_missing_keys_preserves_original_path(tmp_path,monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY',raising=False)
    assert prepare_targeted_context(tmp_path)==''
