import json
from pathlib import Path
from auto_agent.research.asset_observer import AssetObserver

def observation(data,mime):return {'observation':'실사. 손이 식품 포장을 들고 있음. 날짜는 읽을 수 없음.','usage':{'input_tokens':30,'output_tokens':20}}
def fetch(url):return (b'image-bytes','image/jpeg',320,240)
def entry(url='https://example.com/a.jpg'):
    return {'asset_kind':'search_image','candidates':[{'image_url':url,'thumbnail_url':'https://example.com/thumb.jpg'}]}

def test_observation_from_pixels_and_reused_on_disk(tmp_path):
    calls=[]
    def see(data,mime):calls.append(data);return observation(data,mime)
    store={};o=AssetObserver(tmp_path,store,fetcher=fetch,observe=see)
    o.enrich(entry());assert store['https://example.com/a.jpg']['scope']=='thumbnail'
    assert calls==[b'image-bytes'];o.save()
    stored=json.loads((tmp_path/'asset_observations.json').read_text())['observations']
    other=AssetObserver(tmp_path,stored,fetcher=lambda u: (_ for _ in ()).throw(AssertionError()),observe=see)
    other.enrich(entry());assert len(calls)==1

def test_same_bytes_deduplicated_across_urls(tmp_path):
    calls=[]
    def see(data,mime):calls.append(data);return observation(data,mime)
    o=AssetObserver(tmp_path,{},fetcher=fetch,observe=see)
    o.enrich(entry());o.enrich(entry('https://example.com/b.jpg'))
    assert len(calls)==1 and len(o.observations)==2

def test_limit_and_failure_do_not_create_observation(tmp_path):
    def fail(*args):raise ValueError('secret')
    store={};o=AssetObserver(tmp_path,store,fetcher=fetch,observe=fail,max_calls=1)
    o.enrich(entry());o.enrich(entry('https://example.com/b.jpg'))
    assert not store and o.calls==1 and 'secret' not in json.dumps(o.events)

def test_preserve_manual_observation(tmp_path):
    store={'https://example.com/a.jpg':{'kind':'image','observation':'manual'}}
    o=AssetObserver(tmp_path,store,fetcher=lambda u:1/0,observe=observation)
    o.enrich(entry());assert store['https://example.com/a.jpg']['observation']=='manual'

def test_video_thumbnail_never_becomes_video_observation(tmp_path):
    o=AssetObserver(tmp_path,{},fetcher=fetch,observe=observation)
    e=entry();e['asset_kind']='video';o.enrich(e)
    assert not o.observations and o.calls==0

def test_malformed_output_not_cached(tmp_path):
    o=AssetObserver(tmp_path,{},fetcher=fetch,observe=lambda *a:{'observation':''})
    o.enrich(entry());assert not o.observations

def test_no_keys_or_disabled_preserves_legacy(tmp_path,monkeypatch):
    for k in ['TYPESAFE_API_KEY','GOOGLE_API_KEY','GEMINI_API_KEY']:monkeypatch.delenv(k,raising=False)
    assert AssetObserver.from_project(tmp_path,{}) is None
    monkeypatch.setenv('TYPESAFE_API_KEY','fake');monkeypatch.setenv('GOOGLE_API_KEY','fake');monkeypatch.setenv('JEV_AUTO_OBSERVE','0')
    assert AssetObserver.from_project(tmp_path,{}) is None

def test_observer_connected_before_jev_selection(tmp_path):
    from auto_agent.research.jev_scene import SceneJudge
    class Judge:
        def decide(self,state,questions):
            assert state['observed_candidates']['c0']['observation'].startswith('실사')
            return {'layout':'single','representation':'photo','c0':'partial','select':'none'}
    scene={'narration':'읽히는 날짜','imageAsset':{'source':'search'}}
    observations={};engine=SceneJudge(Judge(),observations)
    engine.observer=AssetObserver(tmp_path,observations,fetcher=fetch,observe=observation)
    e=entry();e['scene_index']=0;e['auto_selected']=False
    engine.apply(scene,e,dict(scene))
    assert e['jev']['status']=='review' and engine.observer.calls==1

def test_expired_automatic_record_not_used_after_failure(tmp_path):
    store={'https://example.com/a.jpg':{'kind':'image','observation':'stale','producer':'gemini_auto','created_at':0}}
    o=AssetObserver(tmp_path,store,fetcher=lambda u:1/0,observe=observation)
    o.enrich(entry());assert not store

def test_malformed_cache_timestamp_is_refreshed(tmp_path):
    store={'https://example.com/a.jpg':{'kind':'image','observation':'old','producer':'gemini_auto','version':'asset-observer-v1','model':'gemini-2.5-flash','fetched_url':'https://example.com/thumb.jpg','created_at':'invalid'}}
    o=AssetObserver(tmp_path,store,fetcher=fetch,observe=observation)
    o.enrich(entry());assert o.calls==1

def test_observer_unexpected_failure_does_not_block_legacy_scene():
    from auto_agent.research.jev_scene import SceneJudge
    class Judge:
        def decide(self,state,questions):return {'layout':'single','representation':'photo'}
    class Broken:
        def enrich(self,entry):raise ValueError('secret')
    engine=SceneJudge(Judge(),{});engine.observer=Broken()
    scene={'imageAsset':{'url':'existing'}};e=entry();e['scene_index']=0
    engine.apply(scene,e,dict(scene))
    assert scene['imageAsset']['url']=='existing' and 'secret' not in json.dumps(e)

def test_subscription_factory_needs_no_google_key(tmp_path,monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY','fake')
    monkeypatch.delenv('GOOGLE_API_KEY',raising=False);monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.delenv('JEV_AUTO_OBSERVE',raising=False)
    monkeypatch.setenv('JEV_OBSERVER_PROVIDER','codex')
    monkeypatch.setattr('auto_agent.research.asset_observer.shutil.which',lambda x:x)
    o=AssetObserver.from_project(tmp_path,{})
    assert o is not None and o.model=='gpt-5.6-sol'

def test_claude_option_uses_opus(tmp_path,monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY','fake');monkeypatch.setenv('JEV_OBSERVER_PROVIDER','claude')
    monkeypatch.delenv('JEV_OBSERVER_MODEL',raising=False)
    monkeypatch.setattr('auto_agent.research.asset_observer.shutil.which',lambda x:x)
    assert AssetObserver.from_project(tmp_path,{}).model=='opus'
