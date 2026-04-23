# Config Inspector — 프로젝트 설정 검증 및 자동 수정

파이프라인 시작 전 프로젝트 설정을 교차 검증하고, 자동 수정 가능한 항목은 직접 고친다.

## 역할

세 가지 소스를 비교해서 불일치·누락을 찾고 수정한다:

1. **DB project config** — `ProjectManager.get_config(project_id)`
2. **artstyle JSON** — `auto_agent/data/artstyle/styles/{art_style}.json`
3. **환경변수** — `.env` + 현재 환경

## 실행 절차

### Step 1 — DB config 읽기

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from auto_agent.db.project_manager import ProjectManager
import json, os
pm = ProjectManager()
slug = os.environ.get('PROJECT_NAME', '')
p = pm.resolve_project(slug)
cfg = pm.get_config(p['id']) if p else {}
print(json.dumps({'project': p, 'config': cfg}, ensure_ascii=False, indent=2))
"
```

### Step 2 — artstyle JSON 읽기

art_style 값에서 스타일 ID 추출 (`artstyle/styles/semoji_3D.json` → `semoji_3D`).
`auto_agent/data/artstyle/styles/{style_id}.json`을 Read로 읽는다.

### Step 3 — 환경변수 확인

```bash
echo "ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:+SET}" 
echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:+SET}"
echo "FAL_API_KEY=${FAL_API_KEY:+SET}"
echo "SERPER_API_KEY=${SERPER_API_KEY:+SET}"
echo "GOOGLE_API_KEY=${GOOGLE_API_KEY:+SET}"
echo "KAIROS_VAULT_DIR=${KAIROS_VAULT_DIR}"
echo "RESEARCH_AGENT_DIR=${RESEARCH_AGENT_DIR}"
```

### Step 4 — 교차 검증 및 자동 수정

아래 항목을 순서대로 확인하고, 수정이 필요하면 즉시 실행한다.

#### 4-1. voice_id 검증 (최우선)

| 상태 | 처리 |
|------|------|
| DB `voice_id`가 없고 artstyle JSON에 `voice.voice_id` 있음 | DB에 artstyle 값으로 업데이트 |
| DB `voice_id`가 artstyle JSON `voice.voice_id`와 다름 | artstyle JSON 값으로 덮어씀 (단일 소스는 artstyle) |
| artstyle JSON에 `voice.voice_id` 없음 | FAIL — 파이프라인 중단 |
| DB와 artstyle 일치 | OK |

DB 업데이트 방법:
```bash
python3 -c "
from auto_agent.db.project_manager import ProjectManager
import os, json
pm = ProjectManager()
slug = os.environ.get('PROJECT_NAME', '')
p = pm.resolve_project(slug)
pm.update_config(p['id'], voice_id='{voice_id}', voice_settings={voice_settings})
print('voice_id 업데이트 완료')
"
```

#### 4-2. art_style 경로 정규화

- DB에 `artstyle/styles/semoji_3D.json` 형태로 저장된 경우 → `semoji_3D`로 정규화
- artstyle JSON 파일 실제 존재 여부 확인

정규화 방법:
```bash
python3 -c "
from pathlib import Path
from auto_agent.db.project_manager import ProjectManager
import os
pm = ProjectManager()
slug = os.environ.get('PROJECT_NAME', '')
p = pm.resolve_project(slug)
cfg = pm.get_config(p['id'])
art = cfg.get('art_style', '')
if '/' in art or art.endswith('.json'):
    normalized = Path(art).stem
    pm.update_config(p['id'], art_style=normalized)
    print(f'art_style 정규화: {art} → {normalized}')
"
```

#### 4-3. ELEVENLABS_API_KEY

- 없으면 FAIL — `config_check.json`에 기록 후 `sys.exit(1)` 메시지 출력
- 있으면 OK

#### 4-4. KAIROS_VAULT_DIR / RESEARCH_AGENT_DIR

- 경로가 실제 존재하는지 확인
- 없으면 WARN (stage_1 리서치에 영향)

#### 4-5. writing_style 정합성

- DB `writing_style`이 artstyle JSON의 `id`나 `name`과 일치하는지 확인
- 불일치 시 WARN

### Step 5 — config_check.json 저장

```json
{
  "status": "ok" | "warn" | "fail",
  "resolved": {
    "art_style": "semoji_3D",
    "voice_id": "W7FnAxJNpD5WGjrF5GLp",
    "voice_settings": {...},
    "writing_style": "semoji"
  },
  "fixes_applied": ["voice_id DB 업데이트", "art_style 경로 정규화"],
  "warnings": ["KAIROS_VAULT_DIR 없음"],
  "errors": []
}
```

Write 도구로 `{PROJECT_DIR}/config_check.json`에 저장.

## 판정 기준

- `errors` 있음 → `sys.exit(1)` 출력 후 종료 (파이프라인 중단)
- `warnings`만 있음 → 계속 진행, 경고 내용 출력
- 모두 OK → 계속 진행

## 주의사항

- artstyle JSON이 단일 소스 — DB config의 voice_id보다 artstyle JSON이 우선
- 수정 사항은 반드시 `fixes_applied`에 기록
- 환경변수는 수정하지 않음 (읽기 전용) — 없으면 경고/에러로만 처리
