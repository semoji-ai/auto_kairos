---
name: auto-kairos
description: 영상 제작 파이프라인 실행. 주제/분량/아트스타일을 인터뷰로 입력받고 파이프라인을 자동 실행한다.
user-invocable: true
---

# /auto-kairos — 영상 제작 파이프라인

## 실행 흐름

### 0단계: 환경 + 대시보드 확인

```bash
set -a; source $KAIROS_HOME/.env; set +a
export PATH="$NODE_DIR:$PATH"
cd $KAIROS_HOME
```

대시보드(8080)가 떠 있는지 확인하고, 없으면 백그라운드로 시작:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null
# 200이 아니면:
nohup python3 -m auto_agent.cli dashboard > /tmp/kairos-dashboard.log 2>&1 &
```
사용자에게 알림: "대시보드: http://localhost:8080"

### 1단계: 기획안 선택 또는 주제 직접 입력

먼저 볼트에 기획안이 있는지 확인한다:
```bash
ls $KAIROS_VAULT_DIR/insights/planning/*기획안.md 2>/dev/null | tail -10
```

**기획안이 있으면:**
```
📋 오늘의 기획안:
  [1] [세모지 900점] 구다이글로벌 — 3억→10조 M&A 전략 (추천 12~15분)
  [2] [세모지 729점] 무신사 — 고3이 만든 패션 제국 (추천 10분)
  [3] [이로미즘 900점] 48시간 슈퍼위크 — WGBI+추경 (추천 13~15분)
  [0] 직접 주제 입력

기획안 번호를 선택하세요:
```

선택하면 기획안에서 자동 추출:
- 주제 (title)
- 채널 (channel → writing_style + art_style 매핑)
- 추천 분량 (duration)

**기획안이 없거나 [0] 선택 시:**
- "어떤 영상을 만들까요? (주제/제목)"

### 2단계: 분량 선택

```
분량을 선택하세요:
  1) 1분 (숏폼)
  2) 3분
  3) 5분
  4) 10분 (롱폼)
```

### 3단계: 아트스타일 프리셋 선택

아트스타일 목록을 보여주기 전에 `auto_agent/data/artstyle/styles/` 디렉토리를 Glob으로 스캔해서 사용 가능한 프리셋을 확인한다.

```
아트스타일을 선택하세요:
  1) quirky_cartoon (이로미즘) -- 낙서 카툰, cinematic, 극적 내러티브
  2) semoji (세모지) -- 2D 플랫, flat staging, 정보 전달 중심
  3) lego -- 레고 미니피규어, cinematic
  4) stickman_cute -- 스틱맨 손그림, flat
```

각 프리셋의 JSON을 읽어서 channel, image.staging, guidelines의 첫 문장을 표시한다.

### 4단계: Editorial Brief 인터뷰 (spine 게이트 통과)

아트스타일 선택 후, 파이프라인 시작 전에 **기획 의도를 고정**한다. 반드시 `shared/brief-dna.md`의 **Lever 6 (coherence_spine)**을 만족시켜야 한다 — 한 영상이 여러 질문에 동시 답변하려는 분열을 막기 위함.

⚠️ **사용자가 "인터뷰 건너뛰기" 같은 명시적 표현을 쓴 경우에만 생략**한다. 평소엔 무조건 진행.

5개 질문을 순서대로 받는다. 1번이 가장 중요(척추):

```
📋 기획 의도를 명확히 해둘게요 (5개 질문, 빠르게):

1) [척추] 이 영상이 답하는 단 하나의 질문은? (한 문장, 단답 가능)
   ⚠️ 두 질문을 and/또는으로 묶지 말 것 — 묶으면 영상이 두 개로 분열됨
   (예: "10억원 성과급을 받으면 실제 얼마를 손에 쥐는가?")

2) 이 콘텐츠의 진짜 주제는? (hook 사례 말고 실제 설명 대상)
   (예: "대한민국 근로소득세와 실수령 구조")

3) 어떤 사례/기사/장면으로 도입부를 열 건가요?
   (예: "하이닉스 성과급 10억 예측 기사")

4) 이 영상이 절대 이쪽으로 흘러가면 안 되는 방향은?
   (예: "SK하이닉스 기업사 / 반도체 산업 서사 중심")

5) 시청자가 다 보고 나서 가져가야 할 핵심 인식은? (1번 답변과 정렬)
   (예: "성과급은 세전 숫자와 실수령 체감이 완전히 다르다")
```

#### Spine 자가 검증 (전부 YES여야 진행)

답변을 받은 직후 사용자에게 보여주기 전에 다음 체크를 통과해야 한다:

- [ ] 1번 spine_question에 한 문장 답이 가능한가?
- [ ] 2단계에서 선택한 분량이 12분 이상이라면, spine_question 하나로 그 분량을 견디는가? (못 견디면 spine을 좁히거나 분량을 줄임)
- [ ] 5번 audience_takeaway가 1번 spine_question의 답인가? (서로 다른 질문에 답하면 1번 또는 5번을 다시 받음)
- [ ] 4번 excluded_angles가 3번 hook이나 2번 real_topic을 잡아먹지 않는가?

체크 실패 시 해당 항목을 **다시 질문**한다. 사용자에게 "1번과 5번이 같은 질문을 향하지 않습니다 — 어느 쪽을 살릴까요?"처럼 구체적으로 안내.

#### editorial_brief 작성 (coherence_spine 포함)

체크 통과 후 `editorial_brief.json` + `editorial_brief.v1.json` 양쪽에 동일 내용으로 저장. brief-dna 6레버 스키마 준수:

```python
brief = {
    "core_question": "{1번 답변}",
    "real_topic": "{2번 답변}",
    "hook_angle": "{3번 답변}",
    "supporting_case": "{3번 답변에서 추출한 사례}",
    "excluded_angles": ["{4번 답변}"],
    "audience_takeaway": "{5번 답변}",
    "tone_goal": "{아트스타일에서 자동: quirky_cartoon→충격형, semoji→정보형}",
    "success_criteria": [
        "시청자가 핵심 개념을 직관적으로 이해한다",
        "사례보다 본질 설명이 중심에 남는다"
    ],
    # ⭐ Lever 6 — coherence_spine (척추, 다른 모든 레버보다 먼저 확정)
    "coherence_spine": {
        "spine_question": "{1번 답변과 동일}",
        "spine_answer": "{5번 답변과 정렬된 한 문장 답}",
        "layer_map": {
            "act1_hook": "1막이 spine_question을 어떤 각도로 여는가 (3번 답변 기반)",
            "act2_body": "2막 본문이 어떤 증거/심화를 더하는가 (2번 답변 기반)",
            "act3_landing": "3막이 어떤 답으로 착지하는가 (5번 답변 기반)"
        }
    },
    "_generated_by": "cli_interview",
    "_version": "v1"
}
```

후속 stage 0b의 brief-reviewer가 G1~G5 spine 게이트로 자동 재검증하므로, 여기서는 **명백한 결함만 막는다** (이중 척추, spine_question 비어있음 등).

### 6단계: 설정 확인 (기존 4단계)

선택한 프리셋 JSON에서 자동으로 가져올 값:
- `writing_style`: 프리셋의 channel로 매핑 (이로미즘→iromism, 세모지→semoji, 없으면 직접 질문)
- `voice_id`: 프리셋의 voice.voice_id
- `voice_settings`: 프리셋의 voice.voice_settings
- `art_style`: 프리셋 파일의 상대경로 (예: `artstyle/styles/quirky_cartoon.json`)

설정 요약을 보여주고 확인:
```
설정 확인:
  주제: {topic}
  핵심 질문: {core_question}
  진짜 주제: {real_topic}
  분량: {duration}분
  아트스타일: {preset_name}
  문체: {writing_style}
  음성: {voice_id[:12]}...

  시작할까요? (Y/n)
```

### 7단계: 프로젝트 생성 (기존 5단계)

Bash로 실행:
```bash
.venv/bin/python -c "
from auto_agent.db.project_manager import ProjectManager
pm = ProjectManager()
config = {
    'art_style': '{art_style_path}',
    'writing_style': '{writing_style}',
    'duration_minutes': {duration},
    'voice_id': '{voice_id}',
    'voice_settings': {voice_settings_json},
}
pid = pm.create_project(
    name='{project_name}',
    slug='{slug}',
    topic='{topic}',
    config=config,
    channel='{channel}',
)
p = pm.get_project(pid)
print(f'id={pid} slug={p[\"slug\"]} uuid={p.get(\"uuid\",\"\")}')
"
```

**CLAUDE.md 규칙 준수**: config에 art_style, writing_style, duration_minutes 반드시 포함.

### 8단계: editorial_brief.json 저장 (기존 6단계 전)

프로젝트 생성 후, 4단계에서 받은 brief 답변을 파일로 저장한다:

```bash
.venv/bin/python -c "
import json
from pathlib import Path
output_dir = Path('{output_dir}')
output_dir.mkdir(parents=True, exist_ok=True)
brief = {
    'core_question': '{core_question}',
    'real_topic': '{real_topic}',
    'hook_angle': '{hook_angle}',
    'supporting_case': '{supporting_case}',
    'excluded_angles': {excluded_angles_json},
    'audience_takeaway': '{audience_takeaway}',
    'tone_goal': '{tone_goal}',
    'success_criteria': ['시청자가 핵심 개념을 직관적으로 이해한다', '사례보다 본질 설명이 중심에 남는다'],
    '_generated_by': 'cli_interview'
}
(output_dir / 'editorial_brief.json').write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding='utf-8')
print('editorial_brief.json 저장 완료')
"
```

output_dir은 `pm.get_project(pid)['output_dir']`에서 가져온다.

### 9단계: v4 워크플로 (PD 오케스트레이션)

프로젝트 디렉토리 생성 후, PD가 v4 스킬을 순서대로 진행한다:

각 v4 스킬은 `.claude/skills/v4/<이름>/SKILL.md` 지침을 PD가 순서대로 읽고 수행한다.

1. `strategy-explore` — 각도/훅/구조 옵션
2. `fresh-research`(가벼운 경로) 또는 `deep-research`(깊은 경로) — research_reports/
3. `target-research` — research_targeted/
4. `draft-write` — drafts/v{n}.md
5. `proofread` — 언어 검토
6. `finalize-for-bridge` — final_manuscript_marked.md + final_manuscript.md + outline.json

### 10단계: v3 파이프라인 (씬분할 + 소스 제작)

```bash
auto-agent bg start --project {slug}
```

- step_1_v4bridge(어댑터)가 v4 산출물을 v3 입력으로 변환
- 네이티브 stage 1/2는 legacy_only로 자동 스킵 (ENABLE_LEGACY_V3 미설정 시)
- step_2(씬분할) → Stage 3(조립/렌더)로 진행

### 11단계: 진행 모니터링 + 단계별 보고

사용자에게 즉시 안내:
- 대시보드: `http://localhost:8080`
- 상태: `auto-agent bg status --project {slug}`
- 로그: `auto-agent bg logs --project {slug}`

이후 로그를 주기적으로 확인하며 단계별로 보고한다:
```bash
tail -20 $KAIROS_HOME/output/*_{slug}/logs/pipeline_*.log
```

체크포인트 키워드 → 사용자 보고 메시지:

| 로그 키워드 | 보고 메시지 |
|-----------|-----------|
| `[검증] 리서치:` | "리서치 완료 — N섹션, N소스. Stage 2(원고+연출) 진행 중..." |
| `[검증] 원고+연출:` | "원고+연출 완료 — N씬. 대시보드에서 스토리보드 확인 가능. Stage 3(에셋) 진행 중..." |
| `[팩트체크]` | "팩트체크 완료" |
| `Pipeline Complete` | 최종 보고 (아래) |

전체 완료 시:
```bash
python3 -c "
import json
from pathlib import Path
out = list(Path('$KAIROS_HOME/output').glob('*_{slug}'))[0]
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

- 프로젝트 생성 시 config에 필수값(art_style, writing_style, duration_minutes)이 누락되면 파이프라인이 실패한다
- slug는 영문+숫자+언더스코어만 허용 (한글은 자동 변환)
- voice_id와 voice_settings는 프리셋에서 자동으로 가져온다 — 사용자에게 묻지 않는다
- channel은 프리셋의 channel 값을 사용한다 (null이면 None)
- 이전 버전이 있으면 v2, v3 등 버전 번호를 slug에 추가한다
- 대시보드가 꺼져있으면 시작 전에 재시작한다 (--reload 없이)
