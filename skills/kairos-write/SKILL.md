---
name: kairos-write
description: Use when users say "/kairos-write", "/kairos_write", "카이로스 원고", "스테이지2", or want to run Auto Kairos Stage 2 (script + direction + fact-check) for a video project
---

# Kairos Write (Stage 2)

> Auto Kairos 영상 파이프라인의 Stage 2 — 원고 작성 + 시각 연출 + 팩트체크를 실행합니다.

## Trigger Conditions

```
- "/kairos-write [project_slug]"
- "/kairos_write [project_slug]"
- "카이로스 원고 [프로젝트]"
- "스테이지2 [프로젝트]"
- "원고 작성 [프로젝트]"
```

---

## WHEN TRIGGERED - EXECUTE IMMEDIATELY

### On Trigger Action:

1. **프로젝트 확인** — 인자에서 project_slug 추출.

2. **전제 조건 확인**:
```bash
set -a; source $KAIROS_HOME/.env; set +a
export PATH="$NODE_DIR:$PATH"
cd $KAIROS_HOME
ls output/*_<slug>/research_report.json
```
research_report.json이 없으면: "Stage 1(리서치)이 아직 완료되지 않았습니다. `/kairos-research <slug>`를 먼저 실행하세요."

3. **대시보드 확인 + 자동 실행**:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null
```
- 200이면: 대시보드 이미 실행 중
- 아니면: 백그라운드로 시작
```bash
nohup python3 -m auto_agent.cli dashboard > /tmp/kairos-dashboard.log 2>&1 &
```
사용자에게 알려주세요: "대시보드를 시작했습니다: http://localhost:8080"

4. **Stage 2 실행**:
```bash
python3 -m auto_agent.cli bg start --project <slug> --from step_2
```

Stage 2는 두 스텝을 실행합니다:
- `step_2` (script-director): 원고 + 씬 분할 + 시각 연출 + 모션 설계 → scene_specs.json
- `step_2b` (fact-verifier): 나레이션의 주요 주장 교차 검증 → factcheck_report.json (비차단)

4. **로그 모니터링** — 30초 간격:
```bash
tail -20 $KAIROS_HOME/output/*_<slug>/logs/pipeline_*.log
```

5. **완료 확인** — 로그에 `[검증] 원고+연출:` 메시지가 나오면 Stage 2 완료.

6. **결과 보고**:
```bash
python3 -c "
import json
from collections import Counter
data = json.load(open('$KAIROS_HOME/output/*_<slug>/scene_specs.json'))
scenes = data['scenes']
print(f'총 {len(scenes)}씬')
layouts = Counter(s.get('layout','?') for s in scenes)
motions = Counter(s.get('motion','?') for s in scenes)
print('레이아웃:', dict(layouts))
print('모션:', dict(motions))
for s in scenes:
    n = s['sceneNumber']
    print(f'  #{n}: {s.get(\"layout\")}/{s.get(\"motion\")}/{s.get(\"mood\")} — {(s.get(\"narration\") or \"\")[:40]}...')
"
```

7. **팩트체크 결과**:
```bash
cat $KAIROS_HOME/output/*_<slug>/factcheck_report.json | python3 -m json.tool | head -20
```

8. **매니페스트 빌드** (Stage 2 완료 후 자동 빌드되지만 수동 필요 시):
```bash
python3 -m auto_agent.scripts.build_manifest --local output/*_<slug>
```

9. **다음 단계 안내**:
> Stage 2 완료. 대시보드(localhost:8080)에서 스토리보드를 확인하세요.
> `/kairos-product <slug>` 로 Stage 3(에셋 조립+렌더링)을 진행할 수 있습니다.

## 주의사항

- scene_specs.json이 이미 있으면 삭제 후 재실행해야 합니다.
- script-director는 opus 모델, fact-verifier는 sonnet 모델을 사용합니다.
- art_style에 따라 문체(writing-style-iromism 등)와 레이아웃 규칙이 달라집니다.
