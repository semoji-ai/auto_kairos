---
name: kairos-research
description: Use when users say "/kairos-research", "/kairos_research", "카이로스 리서치", "스테이지1", or want to run Auto Kairos Stage 1 (research) for a video project
---

# Kairos Research (Stage 1)

> Auto Kairos 영상 파이프라인의 Stage 1 — 심층 리서치를 실행합니다.

## Trigger Conditions

```
- "/kairos-research [project_slug]"
- "/kairos_research [project_slug]"
- "카이로스 리서치 [프로젝트]"
- "스테이지1 [프로젝트]"
- "리서치 파이프라인 [프로젝트]"
```

---

## WHEN TRIGGERED - EXECUTE IMMEDIATELY

**DO NOT just display this documentation. EXECUTE the pipeline immediately.**

### On Trigger Action:

1. **프로젝트 확인** — 인자에서 project_slug 추출. 없으면 사용자에게 질문.

2. **환경 설정**:
```bash
set -a; source $KAIROS_HOME/.env; set +a
export PATH="$NODE_DIR:$PATH"
cd $KAIROS_HOME
```

3. **프로젝트 존재 확인**:
```bash
python3 -m auto_agent.cli project info --project <slug>
```

프로젝트가 없으면 생성을 제안하세요:
```bash
python3 -m auto_agent.cli project create "<name>" --topic "<topic>"
```

4. **Stage 1 실행** (백그라운드):
```bash
python3 -m auto_agent.cli bg start --project <slug>
```

파이프라인이 step_0(환경검증) → step_1(리서치)를 순차 실행합니다.

5. **로그 모니터링** — 30초 간격으로 확인:
```bash
tail -20 $KAIROS_HOME/output/*_<slug>/logs/pipeline_*.log
```

6. **완료 확인** — 로그에 `[검증] 리서치:` 메시지가 나오면 Stage 1 완료.

7. **결과 보고**:
```bash
python3 -c "
import json
data = json.load(open('$KAIROS_HOME/output/*_<slug>/research_report.json'))
print(f'섹션: {len(data.get(\"sections\", []))}')
print(f'소스: {len(data.get(\"sources\", []))}')
for s in data.get('sections', []):
    print(f'  - {s.get(\"title\", \"\")}')
"
```

8. **다음 단계 안내**:
> Stage 1 완료. `/kairos-write <slug>` 로 Stage 2(원고+연출)를 진행할 수 있습니다.

## 주의사항

- 파이프라인은 자동으로 Stage 2, 3까지 이어집니다. Stage 1만 보려면 로그에서 Stage 1 완료를 확인하세요.
- 이미 research_report.json이 있으면 자동 스킵됩니다.
- 프로젝트 config(art_style, voice_id, duration_minutes)가 미설정이면 Stage 2에서 문제가 생길 수 있으니 미리 설정을 확인하세요.
