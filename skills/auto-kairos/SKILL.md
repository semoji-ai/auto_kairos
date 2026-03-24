---
name: auto-kairos
description: Use when users say "/auto-kairos", "/auto_kairos", "카이로스 전체", "영상 만들어줘", or want to run the full Auto Kairos pipeline (Stage 1→2→3) for a video project
---

# Auto Kairos (전체 파이프라인)

> Auto Kairos 영상 파이프라인 전체 — 리서치 → 원고+연출 → 에셋조립+렌더링을 한 번에 실행합니다.

## Trigger Conditions

```
- "/auto-kairos [project_slug 또는 주제]"
- "/auto_kairos [project_slug 또는 주제]"
- "카이로스 전체 [프로젝트]"
- "영상 만들어줘 [주제]"
- "파이프라인 실행 [프로젝트]"
```

---

## WHEN TRIGGERED - EXECUTE IMMEDIATELY

### On Trigger Action:

1. **인자 파악** — project_slug인지, 새 주제인지 판단.

2. **환경 설정**:
```bash
set -a; source $KAIROS_HOME/.env; set +a
export PATH="$NODE_DIR:$PATH"
cd $KAIROS_HOME
```

3. **프로젝트 준비**:

기존 프로젝트 slug가 주어진 경우:
```bash
python3 -m auto_agent.cli project info --project <slug>
```

새 주제가 주어진 경우 — 사용자에게 설정을 확인합니다:
- 프로젝트 이름/slug
- 영상 길이 (기본 1분)
- 아트스타일 (기본 quirky_cartoon)
- 채널 (iromism/semoji)

```bash
python3 -m auto_agent.cli project create "<name>" --topic "<topic>"
python3 -m auto_agent.cli config set --project <slug> art_style quirky_cartoon
python3 -m auto_agent.cli config set --project <slug> voice_id 9Sj8ugvpK1DmcAXyvi3a
python3 -m auto_agent.cli config set --project <slug> writing_style iromism
python3 -m auto_agent.cli config set --project <slug> duration_minutes 1
```

4. **전체 파이프라인 실행**:
```bash
python3 -m auto_agent.cli bg start --project <slug>
```

이 명령은 Stage 1 → Stage 2 → Stage 3을 자동으로 순차 실행합니다.

5. **진행 모니터링** — 로그를 주기적으로 확인하고 사용자에게 진행 상황을 알려주세요:

```bash
tail -20 $KAIROS_HOME/output/*_<slug>/logs/pipeline_*.log
```

주요 체크포인트:
- `[검증] 리서치:` → Stage 1 완료
- `[검증] 원고+연출:` → Stage 2 완료
- `[팩트체크]` → 팩트체크 완료
- `Pipeline Complete` → 전체 완료

6. **각 Stage 완료 시 사용자에게 보고**:

**Stage 1 완료 시:**
> 리서치 완료 — N섹션, N소스. Stage 2(원고+연출) 진행 중...

**Stage 2 완료 시:**
> 원고+연출 완료 — N씬. 대시보드(localhost:8080)에서 스토리보드를 확인할 수 있습니다. Stage 3(에셋 조립) 진행 중...

**전체 완료 시:**
```bash
python3 -c "
import json
from pathlib import Path
out = list(Path('$KAIROS_HOME/output').glob('*_<slug>'))[0]
state = json.load(open(out / 'pipeline_state.json'))
print(f'완료: {state.get(\"completed_steps\", [])}')
print(f'실패: {state.get(\"failed_steps\", [])}')
images = list((out / 'images' / 'generated').glob('*.png')) + list((out / 'images').glob('scene_*.jpg'))
audio = list((out / 'audio').glob('*.mp3'))
mp4 = list(out.glob('*.mp4'))
print(f'에셋: 이미지 {len(images)}개, 오디오 {len(audio)}개')
if mp4: print(f'영상: {mp4[0].name}')
"
```

## 개별 Stage 실행

전체가 아닌 특정 Stage만 실행하려면:
- `/kairos-research <slug>` — Stage 1(리서치)만
- `/kairos-write <slug>` — Stage 2(원고+연출)만
- `/kairos-product <slug>` — Stage 3(에셋조립)만

## 주의사항

- 전체 파이프라인은 2분 영상 기준 약 20~30분 소요됩니다.
- 중간에 중단하려면: `python3 -m auto_agent.cli bg stop --project <slug>`
- 대시보드(localhost:8080)에서 실시간 진행 상황을 확인할 수 있습니다.
