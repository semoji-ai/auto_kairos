from scripts.promote_cuts_to_scenes import build_flat_scenes


def test_each_cut_becomes_one_scene_with_distinct_identity():
    specs = {'scenes': [{'sceneNumber': 1, 'sceneId': 'old', 'narration': '첫째 둘째', 'chapter': 1, 'cutIds': ['a','b'], 'imageAsset': {'source':'generate'}}]}
    cuts = [{'cutId':c, 'sceneNumber':1, 'sceneId':'old', 'narrationExact':text, 'spokenText':text, 'sourceStart':start, 'sourceEnd':start+2, 'sentenceIds':[c], 'subject':text, 'direction':'연출', 'non_spoken':False} for c,text,start in [('a','첫째',0),('b','둘째',3)]]
    reviews = [{'cutId':c,'decision':decision,'link':link,'reason':'이유','planned_mode':'scene'} for c,decision,link in [('a','keep','new'),('b','remake','continuous')]]
    result, mapping = build_flat_scenes(specs, cuts, reviews)
    scenes = result['scenes']
    assert [s['sceneNumber'] for s in scenes] == [1,2]
    assert [s['narration'] for s in scenes] == ['첫째','둘째']
    assert len({s['sceneId'] for s in scenes}) == 2
    assert all('cutIds' not in s for s in scenes)
    assert scenes[1]['continuity_previous_scene'] == 1
    assert scenes[1]['review_decision'] == 'remake'
    assert mapping[1]['sourceCutId'] == 'b'


def test_title_does_not_turn_into_speech():
    specs={'scenes':[{'sceneNumber':1,'sceneId':'old'}]}
    cut={'cutId':'a','sceneNumber':1,'narrationExact':'(타이틀)','spokenText':'','non_spoken':True}
    result,_=build_flat_scenes(specs,[cut],[])
    assert result['scenes'][0]['narration'] == ''
    assert result['scenes'][0]['narrationExact'] == '(타이틀)'
