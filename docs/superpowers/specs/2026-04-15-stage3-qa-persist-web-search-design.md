# Stage 3 개선: QA Persist + 재시도 축소 + enable_web_search 판단

**날짜:** 2026-04-15  
**배경:** 팀원 컴퓨터에서 step_3b가 2회 실행되어 이미지가 최대 7버전까지 생성된 문제 발생. 원인은 (1) runner가 assembly-director를 최대 3회 재시도하고 (2) 재시작된 에이전트가 이전 QA 상태를 모른 채 처음부터 재검수+재생성을 반복한 것.

---

## 1. QA Persist

### 문제
에이전트가 재시작되면 Phase B-3 QA 상태를 알 수 없어 이미 검수된 이미지를 다시 검수하고 재생성한다.

### 설계

#### image_assets.json 스키마 변경

각 씬에 `qa` 필드 추가:

```json
{
  "sceneNumber": 3,
  "qa": {
    "passed": false,
    "issues": ["캐릭터 의상 불일치", "프롬프트 미매칭"],
    "checked_at": "2026-04-15T10:23:00"
  },
  "images": [
    { "file": "generated/scene_003_gen_01.png", "type": "generate", "selected": true }
  ]
}
```

- `passed: true` — QA 통과
- `passed: false` — QA 미달, `issues` 배열에 이유 기록
- `qa` 필드 없음 — 아직 검수 안 됨

#### image_assets.py 추가 함수

```python
def set_qa_result(images_dir: Path, scene_num: int, passed: bool, issues: list[str] = None) -> None:
    """QA 결과를 image_assets.json에 기록. Thread-safe."""

def get_qa_result(images_dir: Path, scene_num: int) -> dict | None:
    """qa 필드 반환. 없으면 None."""
```

#### 에이전트 동작 (assembly-director SKILL.md)

**Phase B-3 QA 규칙:**

1. `get_qa_result(scene_num)` 호출
2. 결과가 있으면 (`qa` 필드 존재) → **스킵** (재시작 여부 무관)
3. 결과가 없으면 → Read 도구로 이미지 검수 (1회)
4. 통과 → `set_qa_result(passed=True)`
5. 미달 → `set_qa_result(passed=False, issues=[...])` 기록 후 **재생성 없이 종료**

**재생성 없음.** 미달 씬은 스토리보드에서 사용자가 수동 처리.

---

## 2. 스토리보드 QA 배지

### 설계

QA 미달 씬을 스토리보드 카드에 시각적으로 표시.

#### 스토리보드 라우터

씬 데이터 구성 시 `image_assets.json`의 `qa` 필드를 씬에 병합:

```python
# auto_agent/dashboard/scene_editor.py 또는 storyboard 라우터
qa = image_assets.get_qa_result(images_dir, scene_num)
if qa:
    scene["qa"] = qa
```

#### _storyboard_scene.html

기존 배지 패턴에 QA 배지 추가:

```html
{% if scene.qa and not scene.qa.passed %}
  <span class="qa-badge" title="{{ scene.qa.issues | join(', ') }}">⚠ QA 미달</span>
{% endif %}
```

#### styles.html / CSS

```css
.qa-badge {
  background: #EF4444;
  color: white;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: help;
}
```

---

## 3. step_3b 재시도 횟수 축소

### 문제
`runner.py`에서 `assembly-director`의 `max_attempts`가 3 (최초 1회 + 재시도 2회). 재시도 중 이미지 중복 생성이 발생.

### 설계

`runner.py` `_get_max_attempts()` 변경:

```python
# 변경 전
if agent == "assembly-director" or step_name == "assembly":
    return 3

# 변경 후
if agent == "assembly-director" or step_name == "assembly":
    return 2  # 최초 1회 + 재시도 1회
```

QA persist가 적용되면 재시작 시 이미지 중복 생성이 없으므로, 재시도 자체를 최소화하는 것으로 충분.

---

## 4. enable_web_search LLM 판단

### 배경
FAL banobanana2 API에 `enable_web_search: bool` 옵션이 있음. 이미지 생성 시 웹 최신 정보를 참조하게 함. 실존 인물/사건/장소가 포함된 씬에서 유리함.

### 설계

#### scene_specs.json 필드 추가

`script-director`가 원고 작성 시점에 판단하여 기록:

```json
{
  "imageAsset": {
    "source": "generate",
    "enable_web_search": true,
    "prompt": "2026년 이란 핵시설 공습 현장..."
  }
}
```

- `true` — 실존 인물, 실사 필요 장소/사건
- `false` — 순수 일러스트/만화 씬
- 생략(`null`) — `image_generate.py`가 규칙 기반 fallback

#### image_generate.py — `_build_scene_fal_input()` 수정

```python
def _infer_web_search(scene: dict, is_search_fallback: bool) -> bool:
    """enable_web_search 명시 없을 때 규칙 기반 판단."""
    if is_search_fallback:
        return True  # 원래 실사가 필요했던 씬
    query = scene.get("imageAsset", {}).get("prompt", "")
    current_year = str(datetime.now().year)
    signals = [current_year, str(int(current_year) - 1)]  # 최근 2년 연도
    return any(s in query for s in signals)

# _build_scene_fal_input() 내부
explicit = scene.get("imageAsset", {}).get("enable_web_search")
enable_web_search = explicit if explicit is not None else _infer_web_search(scene, is_search_fallback)
fal_input["enable_web_search"] = enable_web_search
```

#### script-director SKILL.md 추가

`imageAsset` 필드 작성 기준에 `enable_web_search` 판단 규칙 추가:

| 씬 유형 | enable_web_search |
|--------|-------------------|
| 실존 인물 등장 (정치인, 유명인) | `true` |
| 실제 사건/뉴스 장면 (전쟁, 재난, 정상회담) | `true` |
| 실제 장소 (랜드마크, 도시 전경) | `true` |
| 순수 일러스트/만화/아트 씬 | `false` |
| 데이터 시각화, 차트 배경 | `false` |
| 판단 불명확 | 생략 (규칙 기반 fallback) |

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|---------|
| `auto_agent/tools/image_assets.py` | `set_qa_result()`, `get_qa_result()` 추가 |
| `auto_agent/modules/image_batch_module.py` | 해당 없음 (스킵 로직 이미 존재) |
| `auto_agent/data/skills/agents/assembly-director/SKILL.md` | QA 1회 규칙, 재생성 없음, persist 기록 지시 |
| `auto_agent/data/skills/agents/script-director/SKILL.md` | `enable_web_search` 판단 기준 추가 |
| `auto_agent/tools/image_generate.py` | `_infer_web_search()`, `fal_input["enable_web_search"]` 추가 |
| `auto_agent/orchestrator/runner.py` | `assembly-director` max_attempts 3 → 2 |
| `auto_agent/dashboard/templates/partials/_storyboard_scene.html` | QA 배지 추가 |
| `auto_agent/dashboard/templates/styles.html` | `.qa-badge` CSS 추가 |
| `auto_agent/dashboard/` 라우터 (scene_editor.py 등) | 씬 데이터에 qa 필드 병합 |

---

## 데이터 흐름 (변경 후)

```
step_3b 실행 (max 2회)
  │
  ├─ Phase B-2: image_batch_module (기존 씬 스킵)
  │
  ├─ Phase B-3: QA (씬당 1회)
  │   ├─ qa 필드 있음 → 스킵
  │   ├─ 통과 → set_qa_result(passed=True)
  │   └─ 미달 → set_qa_result(passed=False, issues=[...])
  │
  └─ Phase D: 매니페스트 빌드

스토리보드 조회
  └─ qa.passed == false → ⚠ QA 미달 배지 표시
```
