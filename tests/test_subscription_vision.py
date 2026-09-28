import json
from types import SimpleNamespace
import pytest
from auto_agent.research.subscription_vision import observe_subscription, subscription_env

def test_env_excludes_paid_api_routes(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','secret');monkeypatch.setenv('ANTHROPIC_API_KEY','secret')
    monkeypatch.setenv('CLAUDE_CODE_USE_VERTEX','1')
    e=subscription_env()
    assert 'OPENAI_API_KEY' not in e and 'ANTHROPIC_API_KEY' not in e and 'CLAUDE_CODE_USE_VERTEX' not in e

def test_codex_image_argument_and_subscription_guard(monkeypatch,tmp_path):
    seen=[]
    def run(cmd,**kwargs):
        seen.append(cmd)
        if cmd[1:]==['login','status']:return SimpleNamespace(returncode=0,stdout='',stderr='Logged in using ChatGPT')
        assert cmd.index('-i')>cmd.index('Observe ONLY the supplied image pixels. Return JSON.')
        assert kwargs['env'].get('OPENAI_API_KEY') is None
        from pathlib import Path
        Path(cmd[cmd.index('-o')+1]).write_text('{"observation":"사진 관찰"}')
        return SimpleNamespace(returncode=0,stdout=json.dumps({'type':'turn.completed','usage':{'input_tokens':100}}),stderr='')
    monkeypatch.setattr('auto_agent.research.subscription_vision.subprocess.run',run)
    monkeypatch.setattr('auto_agent.research.subscription_vision.shutil.which',lambda x:x)
    r=observe_subscription(b'image','image/jpeg','Observe ONLY the supplied image pixels. Return JSON.',provider='codex',model='gpt-5.6-sol',archive_dir=tmp_path)
    assert r['observation']=='사진 관찰' and len(seen)==2

def test_claude_receives_inline_pixels_without_tools(monkeypatch,tmp_path):
    def run(cmd,**kwargs):
        if cmd[1:]==['auth','status']:return SimpleNamespace(returncode=0,stdout=json.dumps({'loggedIn':True,'authMethod':'claude.ai','apiProvider':'firstParty'}),stderr='')
        assert cmd[cmd.index('--output-format')+1]=='stream-json'
        msg=json.loads(kwargs['input']);assert msg['message']['content'][0]['type']=='image'
        assert cmd[cmd.index('--tools')+1]==''
        return SimpleNamespace(returncode=0,stdout=json.dumps({'type':'result','result':'{"observation":"관찰"}','usage':{'input_tokens':50},'total_cost_usd':.01}),stderr='')
    monkeypatch.setattr('auto_agent.research.subscription_vision.subprocess.run',run)
    monkeypatch.setattr('auto_agent.research.subscription_vision.shutil.which',lambda x:x)
    assert observe_subscription(b'image','image/jpeg','prompt',provider='claude',model='opus',archive_dir=tmp_path)['observation']=='관찰'

def test_api_auth_refused_before_model_call(monkeypatch,tmp_path):
    calls=[]
    def run(cmd,**kwargs):calls.append(cmd);return SimpleNamespace(returncode=0,stdout='Logged in using an API key',stderr='')
    monkeypatch.setattr('auto_agent.research.subscription_vision.subprocess.run',run)
    monkeypatch.setattr('auto_agent.research.subscription_vision.shutil.which',lambda x:x)
    with pytest.raises(RuntimeError):observe_subscription(b'image','image/jpeg','prompt',provider='codex',model='gpt-5.6-sol',archive_dir=tmp_path)
    assert len(calls)==1
