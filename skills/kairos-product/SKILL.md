---
name: kairos-product
description: Use when users say "/kairos-product", "/kairos_product", "카이로스 프로덕션", "스테이지3", or want to run Auto Kairos Stage 3 (asset assembly + rendering) for a video project
---

# Kairos Product (Stage 3)

> Auto Kairos 영상 파이프라인의 Stage 3 — 에셋 조립 + 렌더링을 실행합니다.

## Trigger Conditions

```
- "/kairos-product [project_slug]"
- "/kairos_product [project_slug]"
- "카이로스 프로덕션 [프로젝트]"
- "스테이지3 [프로젝트]"
- "에셋 조립 [프로젝트]"
- "렌더링 [프로젝트]"
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
ls output/*_<slug>/scene_specs.json
```
scene_specs.json이 없으면: "Stage 2(원고+연출)가 아직 완료되지 않았습니다. `/kairos-write <slug>`를 먼저 실행하세요."

3. **Stage 3 실행**:
```bash
python3 -m auto_agent.cli bg start --project <slug> --from step_3
```

assembly-director가 5단계로 에셋을 조립합니다:
- **Phase A**: scene_specs 분석 → TTS 파라미터 + 이미지 전략 수립
- **Phase B**: TTS 생성 + 이미지 생성/검색 + 자막 정렬 (병렬)
- **Phase C**: 검수 + 보정 (품질 평가, 타이밍 조정)
- **Phase D**: 매니페스트 빌드
- **Phase E**: Remotion 렌더링 + 최종 검수

4. **로그 모니터링** — 60초 간격 (Stage 3은 시간이 오래 걸림):
```bash
tail -20 $KAIROS_HOME/output/*_<slug>/logs/pipeline_*.log
```

5. **대시보드에서 실시간 확인**:
대시보드(http://localhost:8080)의 에이전트 메신저에서 assembly-director의 진행 상황을 실시간으로 볼 수 있습니다.

6. **완료 확인** — 로그에 `Pipeline Complete` 메시지가 나오면 완료.

7. **결과 보고**:
```bash
python3 -c "
import json, os
from pathlib import Path
out = list(Path('$KAIROS_HOME/output').glob('*_<slug>'))[0]
# 에셋 현황
images = list((out / 'images' / 'generated').glob('*.png')) + list((out / 'images').glob('scene_*.jpg'))
audio = list((out / 'audio').glob('*.mp3'))
print(f'이미지: {len(images)}개')
print(f'오디오: {len(audio)}개')
# 최종 영상
mp4 = list(out.glob('*.mp4'))
if mp4:
    size_mb = mp4[0].stat().st_size / 1024 / 1024
    print(f'영상: {mp4[0].name} ({size_mb:.1f}MB)')
else:
    print('영상: 미생성')
"
```

8. **결과 안내**:
> Stage 3 완료.
> - 대시보드(localhost:8080)에서 스토리보드 + 에셋을 확인하세요.
> - 리모션 스튜디오(localhost:3000)에서 영상을 미리보기할 수 있습니다.
> - 최종 영상: output/{project_dir}/{video}.mp4

## 주의사항

- assembly-director는 opus 모델을 사용하며, 이미지 생성에 FAL.ai API, TTS에 ElevenLabs API가 필요합니다.
- `imageAsset.source`에 따라 generate(AI 생성) 또는 search(실사 검색)를 구분합니다.
- 참조 이미지는 아트스타일만 참조하며, 얼굴/의상/포즈를 복사하지 않습니다.
- 이미지는 `images/generated/`에 저장되며, 기존 이미지는 절대 삭제하지 않습니다.
