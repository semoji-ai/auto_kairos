"""Promote a reviewed sentence/cut plan to independent canonical scenes.

Usage: python scripts/promote_cuts_to_scenes.py PROJECT_DIR --apply
Original plans and image files are retained; current registry is backed up.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
from uuid import NAMESPACE_URL, uuid5


def build_flat_scenes(specs, cuts, reviews):
    parents = {s['sceneNumber']: s for s in specs['scenes']}
    review_map = {r['cutId']:r for r in reviews}
    scenes, mapping = [], []
    for number, cut in enumerate(cuts, 1):
        parent = parents[cut['sceneNumber']]
        scene = deepcopy(parent)
        for key in ['cutIds','cut_count','cut_plan_file','cut_review_decisions','visual_modes_by_cut',
                    'merge_reason','lg_review_file','lg_review_category','direction_v2_file',
                    'legacy_provided_assets','provided_asset_mapping','provided_asset_ids',
                    'durationFrames','duration','tts_duration','audioFile','videoFile']:
            scene.pop(key, None)
        r = review_map.get(cut['cutId'], {})
        cid = cut['cutId']
        sid = str(uuid5(NAMESPACE_URL, str(parent['sceneId']) + '/independent-scene/' + cid))
        link = r.get('link', cut.get('lg_continuity','new'))
        reference = r.get('existing_image') or cut.get('reference_image')
        mode = r.get('planned_mode', 'scene')
        scene.update({
            'sceneNumber':number, 'sceneId':sid, 'sourceCutId':cid,
            'previousGroupedSceneNumber':cut['sceneNumber'],
            'narrationExact':cut['narrationExact'],
            'narration':'' if cut.get('non_spoken') else cut.get('spokenText',cut['narrationExact']),
            'sourceStart':cut.get('sourceStart'), 'sourceEnd':cut.get('sourceEnd'),
            'sentenceIds':cut.get('sentenceIds', []), 'non_spoken':cut.get('non_spoken',False),
            'non_spoken_captions':cut.get('captions', []),
            'title':cut.get('subject',''), 'concept':cut.get('direction',''),
            'shot_size':r.get('size',cut.get('shot_size','')),
            'camera_angle':r.get('camera',cut.get('angle','')),
            'continuity':link, 'continuity_previous_scene':number-1 if number>1 and link in ['continuous','hold'] else None,
            'continuity_reason':'앞 씬과 공간·인물·제품을 유지하는 독립 씬' if link=='continuous' else '앞 씬 화면 유지' if link=='hold' else '새 장면 전환',
            'is_first_of_background':link=='new',
            'visual_kind':'search_image' if mode=='archive' else 'generate_image',
            'visual_kind_reason':'독립 씬의 화면 유형; 도해 후보는 렌더 비교 후 확정',
            'visual_mode':mode, 'review_decision':r.get('decision','pending'),
            'review_reason':r.get('reason','검토 필요'),
            'review_reference_image':reference, 'review_people':r.get('people',[]),
            'review_source_package':r.get('source_package'),
            'reference_image_candidates':[reference] if reference else [],
            'analysis_status':'independent_scene_v4', 'asset_status':'scene_asset_pending',
            'analysis_version':'independent_scene_v4', 'direction_plan_file':'scene_analysis_v4/scene_plan.json',
            'render_ready':False, 'visual_requirements':[cut.get('direction',''),r.get('reason','')],
            'production_notes':['각 항목이 독립 씬이다. 연속성은 씬 사이 관계로 유지한다.', '다른 구도를 크롭·확대로 대체하지 않는다.'],
            'motion_and_edit':'독립 씬 단위로 제작·편집. 타이밍은 TTS 확정 후 배정.',
        })
        scene['imageAsset'] = {'source':'search' if mode=='archive' else 'generate',
            'placement':'fullscreen', 'prompt':cut.get('direction',''),
            'assetStatus':'pending', 'selection_status':'review_reference_only',
            'enable_web_search':mode=='archive'}
        scenes.append(scene)
        mapping.append({'sceneNumber':number,'sceneId':sid,'sourceCutId':cid,'previousGroupedSceneNumber':cut['sceneNumber']})
    result = {k:deepcopy(v) for k,v in specs.items() if k not in ['scenes','cut_plan_file']}
    result.update(scenes=scenes, analysis_version='independent_scene_v4',
                  direction_plan_file='scene_analysis_v4/scene_plan.json', render_ready=False)
    return result, mapping


def migrate(root):
    root = root.resolve()
    def read(name):return json.loads((root/name).read_text())
    specs = read('scene_specs.json')
    if specs.get('analysis_version')=='independent_scene_v4':
        raise SystemExit('Already migrated; no changes made.')
    cuts = read('scene_analysis_v3/cut_plan.json')['cuts']
    reviews = read('scene_analysis_v3/lg_review/cut_review.json')['cuts']
    source = (root/'scene_analysis_v3/source_manuscript_verbatim.md').read_text()
    assert all(source[c['sourceStart']:c['sourceEnd']]==c['narrationExact'] for c in cuts)
    assert all(a['sourceEnd']<=b['sourceStart'] for a,b in zip(cuts,cuts[1:]))
    result, mapping = build_flat_scenes(specs,cuts,reviews)
    registry = read('images/image_assets.json')
    old_assets = {s['sceneNumber']:s for s in registry['scenes']}
    new_assets=[]
    for scene in result['scenes']:
        assets=deepcopy(old_assets.get(scene['previousGroupedSceneNumber'],{}).get('images',[]))
        for a in assets:
            a['selected']=False
            a['v4_status']='reference_candidate_only'
        new_assets.append({'sceneNumber':scene['sceneNumber'],'sceneId':scene['sceneId'],
            'images':[] if scene['review_decision']=='remake' else assets,
            'reference_images':assets if scene['review_decision']=='remake' else []})
    direction = {'totalBlocks':len(cuts),'sceneCount':len(cuts),'active_analysis':'independent_scene_v4',
                 'analysis_method':'One reviewed cut is one canonical scene; source spans preserved.',
                 'blocks':[{'n':s['sceneNumber'],'sceneNumber':s['sceneNumber'],'sceneId':s['sceneId'],
                     'narrationExact':s['narrationExact'],'sourceStart':s['sourceStart'],'sourceEnd':s['sourceEnd'],
                     'sentenceIds':s['sentenceIds'],'direction':s['concept'],'mergeWithPrev':False,
                     'continuity':s['continuity'],'continuity_previous_scene':s['continuity_previous_scene']}
                     for s in result['scenes']]}
    backup=root/'drafts'/('before_independent_scenes_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    for name in ['scene_specs.json','direction_plan.json','images/image_assets.json']:
        dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,dest)
    changes={'scene_specs.json':result,'direction_plan.json':direction,
             'images/image_assets.json':{**registry,'scenes':new_assets},
             'scene_analysis_v4/scene_plan.json':result,
             'scene_analysis_v4/number_mapping.json':{'scenes':mapping},
             'scene_analysis_v4/verification.json':{'scene_count':len(cuts),'unique_scene_ids':len({s['sceneId'] for s in result['scenes']}),
                 'original_source_spans_preserved':True,'overlaps':0,'backup':str(backup.relative_to(root)),
                 'manuscript_sha256':hashlib.sha256((root/'final_manuscript.md').read_bytes()).hexdigest()}}
    for name,value in changes.items():
        dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
        temp=dest.with_suffix(dest.suffix+'.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2));temp.replace(dest)
    (root/'scene_analysis_v4/README.md').write_text('# 현재 제작 기준\n\n227개 독립 씬. scene_specs.json이 현재 기준이며 씬 아래 컷을 묶지 않는다. 연속성은 continuity_previous_scene로 연결한다. number_mapping.json은 기존 131씬·227컷 번호와 새 씬 번호의 대응표다. scene_analysis_v3는 이전 검토 기록이다. 원고와 이미지 파일은 변경하지 않았다.\n')
    print(json.dumps(changes['scene_analysis_v4/verification.json'],ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('project_dir',type=Path);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if not args.apply:parser.error('--apply required')
    migrate(args.project_dir)
