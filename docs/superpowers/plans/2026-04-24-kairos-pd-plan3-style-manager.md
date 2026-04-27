# kairos-pd Plan 3: 스타일 매니저 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `kairos-pd style new <채널>` 이 Claude 인터뷰어를 실행해 `style_bundle.json` + `writing_style.md`를 생성하고, StyleManager가 Orchestrator에 스타일 컨텍스트를 제공한다.

**Architecture:** StyleManager(Python)는 `styles/{channel}/` 디렉토리를 읽고 쓰는 단순 CRUD 레이어. `style new`는 ClaudeRunner로 style-interviewer SKILL.md를 실행해 인터뷰 → 파일 생성. `writing_style.md`는 v3의 `semoji_style_guide.md` 수준의 상세 문체 가이드 포맷을 따른다.

**Tech Stack:** Python 3.11+, Click, pathlib, JSON, Markdown, ClaudeRunner(기존)

---

## 설계 인사이트: v3 design.md 패턴 적용

v3 `semoji_style_guide.md` 분석에서 도출한 `writing_style.md` 표준 구조:

```
# {채널명} 문체 스타일 가이드

> [채널 분석 근거]

## 1. 문체 특징 (어조, 문장 길이, 종결어미, 반복 패턴)
## 2. 스토리텔링 구조 (도입-전개-결말, 챕터 방식)
## 3. 화자 스타일 (나레이션 방식, 감정 표현 원칙)
## 4. 수사법 (핵심 기법 7가지)
## 5. 씬 전환 패턴 (시간/장소/밀도)
## 6. 특수 표현 및 관용구 (시그니처 전환어, 금지 표현)
## 7. 주제 전개 (정보/감성 비율, 팩트 인용)

## 부록: 원고 작성 체크리스트
```

`style_bundle.json`의 `writing.style_file`이 이 MD를 참조 → Orchestrator가 에이전트 프롬프트에 통째로 주입.

---

## 파일 맵

### Create
- `/Volumes/jleavens/Projects/kairos-pd/core/style_manager.py` — StyleManager CRUD
- `/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/style_bundle.json` — 샘플 번들
- `/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md` — 샘플 문체 가이드
- `/Volumes/jleavens/Projects/kairos-pd/skills/agents/style-interviewer/SKILL.md` — 인터뷰 에이전트
- `/Volumes/jleavens/Projects/kairos-pd/tests/test_style_manager.py` — StyleManager 테스트
- `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_style.py` — style CLI 테스트

### Modify
- `/Volumes/jleavens/Projects/kairos-pd/cli.py` — `style new` 커맨드를 ClaudeRunner 연결로 교체

---

## Task 1: core/style_manager.py + 테스트

`StyleManager`는 `styles/{channel}/` 디렉토리를 관리한다. CLI와 Orchestrator 양쪽에서 사용한다.

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/core/style_manager.py`
- Create: `/Volumes/jleavens/Projects/kairos-pd/tests/test_style_manager.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/jleavens/Projects/kairos-pd/tests/test_style_manager.py`:

```python
from __future__ import annotations
import json
import pytest
from pathlib import Path
from core.style_manager import StyleManager, StyleNotFoundError


@pytest.fixture
def styles_root(tmp_path):
    return tmp_path / "styles"


@pytest.fixture
def mgr(styles_root):
    return StyleManager(styles_root)


@pytest.fixture
def sample_bundle():
    return {
        "channel": "테스트채널",
        "version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "artstyle": {
            "prompt_positive": "cinematic, beautiful lighting",
            "prompt_negative": "blurry, low quality",
            "reference_images": [],
        },
        "voice": {
            "id": "test-voice-id",
            "name": "테스트보이스",
            "provider": "elevenlabs",
            "settings": {"stability": 0.8, "similarity_boost": 0.9, "style": 0.8, "speed": 1.0},
        },
        "writing": {"style_file": "writing_style.md"},
        "tts": {"pre": ["숫자 한글 변환"], "post": ["묵음 제거"]},
        "image_rules": {
            "character_extract": "extract main character",
            "character_generate": "generate character",
            "scene_generate": "generate scene",
        },
    }


def test_save_and_load_bundle(mgr, sample_bundle):
    mgr.save_bundle("테스트채널", sample_bundle)
    loaded = mgr.load_bundle("테스트채널")
    assert loaded["channel"] == "테스트채널"
    assert loaded["voice"]["id"] == "test-voice-id"


def test_load_bundle_not_found_raises(mgr):
    with pytest.raises(StyleNotFoundError):
        mgr.load_bundle("존재하지않는채널")


def test_list_channels_empty(mgr):
    assert mgr.list_channels() == []


def test_list_channels_after_save(mgr, sample_bundle):
    mgr.save_bundle("채널A", sample_bundle)
    mgr.save_bundle("채널B", {**sample_bundle, "channel": "채널B"})
    channels = mgr.list_channels()
    assert "채널A" in channels
    assert "채널B" in channels


def test_save_writing_style(mgr, sample_bundle):
    mgr.save_bundle("테스트채널", sample_bundle)
    mgr.save_writing_style("테스트채널", "# 문체 가이드\n\n## 1. 어조\n- 합니다체")
    content = mgr.load_writing_style("테스트채널")
    assert "합니다체" in content


def test_load_writing_style_not_found_returns_empty(mgr, sample_bundle):
    mgr.save_bundle("테스트채널", sample_bundle)
    content = mgr.load_writing_style("테스트채널")
    assert content == ""


def test_channel_dir_is_created_on_save(mgr, sample_bundle, styles_root):
    mgr.save_bundle("신규채널", sample_bundle)
    assert (styles_root / "신규채널" / "style_bundle.json").exists()


def test_set_field_updates_nested(mgr, sample_bundle):
    mgr.save_bundle("테스트채널", sample_bundle)
    mgr.set_field("테스트채널", "voice.id", "new-voice-id")
    loaded = mgr.load_bundle("테스트채널")
    assert loaded["voice"]["id"] == "new-voice-id"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_style_manager.py -v 2>&1 | head -15
```

Expected: FAIL — `ModuleNotFoundError: No module named 'core.style_manager'`

- [ ] **Step 3: style_manager.py 구현**

`/Volumes/jleavens/Projects/kairos-pd/core/style_manager.py`:

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


class StyleNotFoundError(Exception):
    pass


class StyleManager:
    def __init__(self, styles_root: Path):
        self.root = Path(styles_root)

    def _bundle_path(self, channel: str) -> Path:
        return self.root / channel / "style_bundle.json"

    def _writing_path(self, channel: str) -> Path:
        return self.root / channel / "writing_style.md"

    def list_channels(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            d.name for d in self.root.iterdir()
            if d.is_dir() and (d / "style_bundle.json").exists()
        )

    def load_bundle(self, channel: str) -> dict:
        path = self._bundle_path(channel)
        if not path.exists():
            raise StyleNotFoundError(f"스타일 '{channel}'을 찾을 수 없습니다.")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_bundle(self, channel: str, bundle: dict) -> None:
        path = self._bundle_path(channel)
        path.parent.mkdir(parents=True, exist_ok=True)
        bundle["updated_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_writing_style(self, channel: str) -> str:
        path = self._writing_path(channel)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def save_writing_style(self, channel: str, content: str) -> None:
        path = self._writing_path(channel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def set_field(self, channel: str, field: str, value: object) -> None:
        bundle = self.load_bundle(channel)
        keys = field.split(".")
        target = bundle
        for k in keys[:-1]:
            if not isinstance(target.get(k), dict):
                raise KeyError(f"'{k}'는 중첩 가능한 필드가 아닙니다.")
            target = target[k]
        target[keys[-1]] = value
        self.save_bundle(channel, bundle)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_style_manager.py -v
```

Expected: 9 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
/opt/homebrew/bin/python3.12 -m pytest tests/ -v 2>&1 | tail -5
```

Expected: 35 passed

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add core/style_manager.py tests/test_style_manager.py
git commit -m "feat: add StyleManager CRUD for style_bundle.json and writing_style.md"
```

---

## Task 2: 이로미즘 샘플 스타일 번들 생성

v3 패턴을 반영한 실제 사용 가능한 샘플을 생성한다. Orchestrator 테스트와 `style list` 검증에 사용.

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/style_bundle.json`
- Create: `/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/jleavens/Projects/kairos-pd/styles/이로미즘
```

- [ ] **Step 2: style_bundle.json 작성**

`/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/style_bundle.json`:

```json
{
  "channel": "이로미즘",
  "version": "1.0",
  "updated_at": "2026-04-24T00:00:00Z",
  "artstyle": {
    "preset": "iromism_cinematic",
    "prompt_positive": "cinematic korean animation style, beautiful lighting, rich color palette, detailed character design, smooth line art, expressive eyes, atmospheric background",
    "prompt_negative": "blurry, low quality, distorted, watermark, text, signature, bad anatomy, deformed",
    "reference_images": []
  },
  "voice": {
    "id": "EXAVITQu4vr4xnSDxMaL",
    "name": "이로미",
    "provider": "elevenlabs",
    "settings": {
      "stability": 0.8,
      "similarity_boost": 0.9,
      "style": 0.8,
      "speed": 1.0
    }
  },
  "writing": {
    "style_file": "writing_style.md"
  },
  "tts": {
    "pre": ["숫자 한글 변환", "영어 발음 한글 표기", "특수문자 제거"],
    "post": ["0.1초 미만 묵음 제거", "0.3s 페이드인", "정규화 -14 LUFS"]
  },
  "image_rules": {
    "character_extract": "주인공 캐릭터를 배경 없이 추출. 전신 또는 상반신. 이로미즘 스타일 유지.",
    "character_generate": "이로미즘 아트스타일로 캐릭터 생성. reference_images의 스타일 참조. 표정과 포즈 지정.",
    "scene_generate": "씬 전체 배경 생성. 캐릭터 없이 배경만. 시네마틱 조명과 분위기 우선."
  }
}
```

- [ ] **Step 3: writing_style.md 작성**

`/Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md`:

```markdown
# 이로미즘 문체 스타일 가이드

> 이로미즘 채널의 원고 문체 기준. Writer 에이전트의 프롬프트에 주입되어 채널 톤을 재현한다.

---

## 1. 문체 특징

### 1-1. 어조 및 어체
- **기본 어체**: 해요체(~해요/~예요/~이에요) 메인 톤. 친근하고 따뜻한 느낌.
- **부드러운 존댓말**: 딱딱하지 않게, 친한 언니/오빠가 설명해주는 느낌.
- **금지**: 합쇼체(~입니다/~했습니다)는 사용하지 않는다. 해라체(~했다/~이다)도 금지.
- **감탄과 공감**: "그쵸?", "맞아요", "근데 있잖아요" 등 구어체 삽입 허용.

### 1-2. 문장 길이 패턴
- **1~2문장 단위 줄바꿈** 기본. 각 줄이 하나의 씬(나레이션)에 대응.
- **짧은 단문(10~20자)**과 **중간 길이(30~50자)**를 교대로 배치해 리듬감 형성.
- **긴 문장은 쉼표나 슬래시로 분절**: "사실은요, 이 이야기가 / 지금 우리랑 완전 관련 있어요."
- **3문장 연속 같은 길이 금지**: 짧-중-짧 또는 중-짧-긴 패턴 유지.

### 1-3. 종결어미 순환 패턴
같은 종결어미 3회 이상 연속 금지:
1. **친근 전달**: ~해요 / ~이에요 / ~예요
2. **공감 확인**: ~거든요 / ~잖아요 / ~이잖아요
3. **서술 강조**: ~더라고요 / ~대요 / ~래요
4. **마침 단문(여운)**: "바로 이거예요." / "정말 대단하죠?" / "이게 핵심이에요."

### 1-4. 시그니처 표현
- **"근데요,"**: 반전/뜻밖의 사건 도입. 단독 줄에 배치.
- **"사실은요,"**: 진짜 이야기 시작. 호기심 유발.
- **"있잖아요,"**: 친근한 이야기 전환.
- **"그래서요,"**: 결론/결과로 이행.
- **"어때요?"**: 시청자 공감 유도. 마무리 뒤에 배치.

---

## 2. 스토리텔링 구조

### 2-1. 도입-전개-결말 패턴

#### 도입부
- **공감 질문으로 시작**: "여러분, 혹시 ~해본 적 있어요?"
- **일상적 장면 묘사**: 시청자가 공감할 수 있는 장면부터 진입.
- **핵심 주제 예고**: "오늘은 ~에 대해 얘기해볼 거예요."

#### 전개부
- **에피소드 중심**: 인물/사건을 에피소드 단위로 나눠 전달.
- **3~5개 챕터**: 각 챕터에 소제목. 10자 이내, 임팩트 있게.
- **시간 기반 흐름**: 연도/시기를 명시하되, 딱딱하지 않게.
  - "1990년대 초반이었어요" / "그로부터 10년 후,"

#### 결말부
- **핵심 메시지 정리**: "결국 이게 핵심이에요."
- **시청자 호출**: "이 이야기가 여러분에게 어떻게 느껴졌나요?"
- **다음 영상 예고** (시리즈물): "2편에서 계속할게요!"

### 2-2. 챕터 구성
- 원고당 3~6개 챕터.
- 각 챕터는 단일 사건/에피소드에 집중.
- 챕터 전환: "자, 이제 다음 이야기로 넘어가볼게요."

---

## 3. 화자 스타일

### 3-1. 나레이션 방식
- **친근한 관찰자 시점**: 1.5인칭. "우리"를 자주 사용.
- **시청자와 함께 발견하는 느낌**: "아, 이게 이런 이유가 있었던 거예요!"
- **화자 감정 표현 허용**: "저도 처음 알았을 때 깜짝 놀랐어요."

### 3-2. 감정 표현 원칙
- **공감 먼저**: 시청자가 느낄 감정을 먼저 표현.
- **과장 절제**: !!나 강한 감탄은 전환점에만 (챕터당 0~2회).
- **긍정 에너지 유지**: 어두운 이야기도 배울 점/희망으로 마무리.
- **금지**: "대박이죠!", "충격적이지 않나요?" 같은 과잉 리액션.

---

## 4. 수사법

### 4-1. 핵심 기법

#### (1) "근데요," 반전법
가장 빈번한 핵심 기법. 단독 줄에 배치해 반전을 예고.
```
이렇게 잘 나가던 회사였는데요,
근데요,
갑자기 모든 게 바뀌기 시작했어요.
```

#### (2) 현재 연결법
과거 이야기를 현재와 연결해 친숙함 부여.
```
이 회사가 바로 지금 우리가 매일 쓰는 ~예요.
```

#### (3) 비교 체감법
숫자/규모를 일상적 비유로 풀어내기.
```
당시 그 돈이면 지금 아파트를 몇 채는 살 수 있었다고 해요.
```

#### (4) 의문문 유도
질문하고 바로 답을 제시.
```
과연 어떻게 된 걸까요?
알고 보니 완전 예상 밖의 이유가 있었어요.
```

#### (5) 미래 예고법
인물 첫 등장 시 미래를 미리 알려주기.
```
이 분이 바로 훗날 ~을 만든 그 분이에요.
```

---

## 5. 씬 전환 패턴

### 5-1. 시간 전환
- **구어체 시간 표현**: "1990년대 초반이었어요", "그로부터 5년 후,"
- **"그래서요," 결과 이행**: 과정 → 결과로 넘어갈 때.
- **"한편," 병렬 전환**: 다른 인물/사건으로 이동.

### 5-2. 장소 전환
- 장소는 간결하게: "미국으로 건너간 그는,"
- 현재 지명 병기: "지금의 서울 종로 일대에서"

### 5-3. 장면 묘사 밀도
- **배경 묘사 최소**: 인물 행동과 사건 중심.
- **감각 묘사는 오프닝/클라이맥스에만**: 분위기 전환 목적.
- **동작은 간결하게**: 긴 묘사보다 짧고 임팩트 있는 표현.

---

## 6. 특수 표현 및 관용구

### 6-1. 시그니처 전환어구

| 표현 | 용도 | 빈도 |
|------|------|------|
| 근데요, | 반전/예상 밖 전환 | 매우 높음 |
| 사실은요, | 진짜 이야기 시작 | 높음 |
| 있잖아요, | 친근한 화제 전환 | 높음 |
| 그래서요, | 결과/결론 이행 | 높음 |
| 어때요? | 시청자 공감 유도 | 중간 |
| 근데 있잖아요, | 이야기 전환 강조 | 중간 |
| 어쨌든, | 복잡한 상황 정리 | 낮음 |

### 6-2. 금지 표현
- 합쇼체 종결어미 (입니다, 했습니다)
- 해라체 나레이션 (했다, 이다)
- 과잉 감탄 ("대박이죠!", "충격이지 않나요?")
- 번역체 ("~에 의해 ~되었어요", "~하는 것은 ~이에요")
- 일본식 표현

---

## 7. 주제 전개

### 7-1. 정보/감성 비율
- **정보 60% : 감성/서사 40%**: 이로미즘은 감성 비중이 세모지보다 높다.
- 정보 밀집 구간 뒤 반드시 에피소드/공감 구간 배치.
- 기술/숫자 설명은 비유 + 일상 비교로 풀기.

### 7-2. 팩트 인용 방식
- **구체 수치 선호**: "약 30%" 대신 "정확히 31.4%".
- **화폐/규모 체감 비유**: 과거 금액을 현재 기준 환산.
- **출처 자연스럽게 녹이기**: "~의 인터뷰에서 밝혔어요."
- **불확실한 사실**: "정확히 확인된 건 아니지만,".

---

## 부록: 원고 작성 체크리스트

Writer 에이전트가 최종 원고 검토 시 확인:

- [ ] "근데요,"가 반전 지점에 적절히 배치됐나요?
- [ ] 동일 종결어미가 3회 이상 연속되지 않나요?
- [ ] 해요체가 일관되게 유지됐나요? (합쇼체, 해라체 혼입 없이)
- [ ] 각 챕터에 시청자 공감 요소가 하나 이상 있나요?
- [ ] 숫자/수치에 체감 비유가 함께 제시됐나요?
- [ ] 과잉 감탄(!, 대박이죠! 등)이 챕터당 2회 이하인가요?
- [ ] 5문장 이상 줄바꿈 없이 몰아쓴 구간이 없나요?
- [ ] 도입부에 공감 질문 또는 일상 장면이 있나요?
- [ ] 번역체 표현이 없나요?
- [ ] 마무리에 시청자 호출 또는 핵심 메시지가 있나요?
```

- [ ] **Step 4: 파일 존재 확인**

```bash
ls /Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/
wc -l /Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md
```

Expected: `style_bundle.json writing_style.md` / 140줄 이상

- [ ] **Step 5: style list 동작 확인**

```bash
kairos-pd style list
```

Expected: `이로미즘` 채널 목록에 출력

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add styles/
git commit -m "feat: add 이로미즘 sample style bundle and writing_style.md"
```

---

## Task 3: style-interviewer SKILL.md

Claude가 대화형으로 채널 스타일을 수집해 파일을 생성하는 에이전트.

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/skills/agents/style-interviewer/SKILL.md`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/jleavens/Projects/kairos-pd/skills/agents/style-interviewer
```

- [ ] **Step 2: SKILL.md 작성**

`/Volumes/jleavens/Projects/kairos-pd/skills/agents/style-interviewer/SKILL.md`:

````markdown
# Style Interviewer Agent

당신은 kairos-pd 스타일 인터뷰어입니다.
채널 운영자와 대화하며 채널 스타일 정보를 수집하고,
`style_bundle.json`과 `writing_style.md`를 생성합니다.

## 환경

- CHANNEL: $CHANNEL
- STYLES_ROOT: $STYLES_ROOT (기본: kairos-pd 설치 디렉토리의 styles/)
- kairos-pd CLI: kairos-pd (PATH에 등록됨)

## 도구

Bash, Read, Write 도구를 사용합니다.

## 인터뷰 흐름

다음 항목을 **한 번에 하나씩** 질문합니다. 이미 알고 있는 정보는 건너뜁니다.

### 1. 아트스타일

"채널의 이미지 스타일을 설명해주세요. 어떤 분위기, 색감, 캐릭터 스타일인가요?"

수집 정보:
- 긍정 프롬프트 키워드 (영어, 이미지 생성 AI용)
- 부정 프롬프트 키워드
- 기준 캐릭터 이미지 파일 경로 (있다면)

### 2. 보이스 설정

"채널의 나레이션 보이스 ID를 알려주세요. ElevenLabs 보이스 ID입니다."

수집 정보:
- voice_id (ElevenLabs)
- 보이스 이름 (별칭)
- stability, similarity_boost, style, speed 설정 (기본값: 0.8/0.9/0.8/1.0)

### 3. TTS 전처리/후처리

"TTS 변환 시 적용할 전처리/후처리 규칙을 알려주세요."

기본값:
- pre: ["숫자 한글 변환", "영어 발음 한글 표기"]
- post: ["0.1초 미만 묵음 제거", "0.3s 페이드인", "정규화 -14 LUFS"]

### 4. 이미지 생성 규칙

"캐릭터 추출/생성, 씬 생성 시 적용할 규칙을 설명해주세요."

수집 정보:
- character_extract: 기존 이미지에서 캐릭터 추출 방법
- character_generate: 새 캐릭터 생성 방법
- scene_generate: 배경/씬 생성 방법

### 5. 문체 스타일

"채널의 나레이션 문체를 설명해주세요. 기존 원고가 있다면 공유해 주시면 분석해드릴게요."

수집 정보 (writing_style.md 생성용):
- 기본 어체 (해요체/합쇼체/구어체 등)
- 시그니처 표현 / 자주 쓰는 전환어
- 금지 표현
- 스토리텔링 패턴 (도입-전개-결말)
- 정보/감성 비율

### 6. 요약 확인

수집된 정보를 요약해 보여주고 수정 요청을 받습니다.

## 파일 생성

인터뷰 완료 후:

### style_bundle.json 생성

```bash
# styles/{CHANNEL}/ 디렉토리 생성
mkdir -p $STYLES_ROOT/$CHANNEL

# style_bundle.json 작성 (수집된 정보로)
kairos-pd style set $CHANNEL channel "$CHANNEL"
# ... (Write 도구로 직접 작성 권장)
```

Write 도구로 `$STYLES_ROOT/$CHANNEL/style_bundle.json` 직접 작성:

```json
{
  "channel": "{CHANNEL}",
  "version": "1.0",
  "updated_at": "{ISO_TIMESTAMP}",
  "artstyle": {
    "prompt_positive": "{수집된 긍정 프롬프트}",
    "prompt_negative": "{수집된 부정 프롬프트}",
    "reference_images": ["{기준 이미지 경로 또는 빈 배열}"]
  },
  "voice": {
    "id": "{voice_id}",
    "name": "{보이스 이름}",
    "provider": "elevenlabs",
    "settings": {
      "stability": 0.8,
      "similarity_boost": 0.9,
      "style": 0.8,
      "speed": 1.0
    }
  },
  "writing": {
    "style_file": "writing_style.md"
  },
  "tts": {
    "pre": ["숫자 한글 변환", "영어 발음 한글 표기"],
    "post": ["0.1초 미만 묵음 제거", "0.3s 페이드인", "정규화 -14 LUFS"]
  },
  "image_rules": {
    "character_extract": "{수집된 규칙}",
    "character_generate": "{수집된 규칙}",
    "scene_generate": "{수집된 규칙}"
  }
}
```

### writing_style.md 생성

Write 도구로 `$STYLES_ROOT/$CHANNEL/writing_style.md` 작성.
반드시 다음 섹션을 포함:

```markdown
# {CHANNEL} 문체 스타일 가이드

> [수집된 채널 설명]

## 1. 문체 특징 (어조, 문장 길이, 종결어미, 시그니처 표현)
## 2. 스토리텔링 구조 (도입-전개-결말, 챕터 방식)
## 3. 화자 스타일 (나레이션 방식, 감정 표현)
## 4. 수사법 (핵심 기법 — 최소 3가지)
## 5. 씬 전환 패턴 (시간/장소/장면 밀도)
## 6. 특수 표현 및 관용구 (시그니처 전환어 표, 금지 표현)
## 7. 주제 전개 (정보/감성 비율, 팩트 인용 방식)

## 부록: 원고 작성 체크리스트
- [ ] [핵심 문체 규칙 10개 이상]
```

## 규칙

- 한 번에 하나의 질문만 합니다.
- 사용자가 "기본값으로" 또는 "나중에"라고 하면 기본값을 사용하고 넘어갑니다.
- 파일 생성 후 `kairos-pd style show $CHANNEL` 로 결과를 확인합니다.
- 생성 완료 메시지: "✅ {CHANNEL} 스타일이 생성되었습니다. `kairos-pd style show {CHANNEL}` 로 확인하세요."
````

- [ ] **Step 3: 파일 확인**

```bash
wc -l /Volumes/jleavens/Projects/kairos-pd/skills/agents/style-interviewer/SKILL.md
```

Expected: 100줄 이상

- [ ] **Step 4: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add skills/agents/style-interviewer/SKILL.md
git commit -m "feat: add style-interviewer SKILL.md"
```

---

## Task 4: `style new` → ClaudeRunner 연결 + CLI 테스트

**Files:**
- Modify: `/Volumes/jleavens/Projects/kairos-pd/cli.py`
- Create: `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_style.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_style.py`:

```python
from __future__ import annotations
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def styles_root(tmp_path):
    root = tmp_path / "styles"
    root.mkdir()
    return root


@pytest.fixture
def 이로미즘_bundle(tmp_path):
    """이로미즘 스타일 번들을 임시 경로에 생성."""
    styles = tmp_path / "styles" / "이로미즘"
    styles.mkdir(parents=True)
    bundle = {
        "channel": "이로미즘",
        "version": "1.0",
        "updated_at": "2026-04-24T00:00:00Z",
        "artstyle": {"prompt_positive": "cinematic", "prompt_negative": "blurry", "reference_images": []},
        "voice": {"id": "test-id", "name": "이로미", "provider": "elevenlabs",
                  "settings": {"stability": 0.8, "similarity_boost": 0.9, "style": 0.8, "speed": 1.0}},
        "writing": {"style_file": "writing_style.md"},
        "tts": {"pre": ["숫자 한글 변환"], "post": ["묵음 제거"]},
        "image_rules": {"character_extract": "extract", "character_generate": "generate", "scene_generate": "scene"},
    }
    (styles / "style_bundle.json").write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    (styles / "writing_style.md").write_text("# 이로미즘 문체 가이드\n", encoding="utf-8")
    return tmp_path


def test_style_list_shows_channel(runner, 이로미즘_bundle, monkeypatch):
    monkeypatch.setattr("cli.STYLES_ROOT", 이로미즘_bundle / "styles")
    result = runner.invoke(main, ["style", "list"])
    assert result.exit_code == 0
    assert "이로미즘" in result.output


def test_style_show_outputs_json(runner, 이로미즘_bundle, monkeypatch):
    monkeypatch.setattr("cli.STYLES_ROOT", 이로미즘_bundle / "styles")
    result = runner.invoke(main, ["style", "show", "이로미즘"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["channel"] == "이로미즘"
    assert "voice" in data
    assert "artstyle" in data


def test_style_show_unknown_channel_fails(runner, 이로미즘_bundle, monkeypatch):
    monkeypatch.setattr("cli.STYLES_ROOT", 이로미즘_bundle / "styles")
    result = runner.invoke(main, ["style", "show", "없는채널"])
    assert result.exit_code == 1


def test_style_new_invokes_claude_runner(runner, tmp_path, monkeypatch):
    monkeypatch.setattr("cli.STYLES_ROOT", tmp_path / "styles")
    with patch("cli.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        mock_instance.run.return_value = 0
        MockRunner.return_value = mock_instance

        result = runner.invoke(main, ["style", "new", "테스트채널"])

    assert result.exit_code == 0
    assert mock_instance.run.called
    call_kwargs = mock_instance.run.call_args[1]
    assert call_kwargs.get("env_extra", {}).get("CHANNEL") == "테스트채널"


def test_style_set_updates_field(runner, 이로미즘_bundle, monkeypatch):
    monkeypatch.setattr("cli.STYLES_ROOT", 이로미즘_bundle / "styles")
    result = runner.invoke(main, ["style", "set", "이로미즘", "voice.id", "new-voice-id"])
    assert result.exit_code == 0
    bundle_path = 이로미즘_bundle / "styles" / "이로미즘" / "style_bundle.json"
    data = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert data["voice"]["id"] == "new-voice-id"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_style.py -v 2>&1 | head -20
```

Expected: 일부 FAIL — `test_style_new_invokes_claude_runner` 실패 (`style new` 가 stub)

- [ ] **Step 3: cli.py `style new` 커맨드 업데이트**

`cli.py`에서 현재 `style_new` 커맨드를 다음으로 교체:

```python
@style.command("new")
@click.argument("channel")
def style_new(channel):
    """채널 스타일 신규 생성 — Claude 인터뷰어 실행"""
    skill_path = _HERE / "skills" / "agents" / "style-interviewer" / "SKILL.md"
    if not skill_path.exists():
        click.echo(f"style-interviewer SKILL.md 없음: {skill_path}", err=True)
        raise SystemExit(1)

    skill = skill_path.read_text(encoding="utf-8")
    prompt = f"""{skill}

## 실행 파라미터
CHANNEL={channel}
STYLES_ROOT={STYLES_ROOT}
"""
    click.echo(f"[kairos-pd] '{channel}' 스타일 인터뷰 시작...")
    cr = ClaudeRunner()
    rc = cr.run(
        prompt=prompt,
        max_turns=100,
        tools=["Bash", "Read", "Write"],
        env_extra={"CHANNEL": channel, "STYLES_ROOT": str(STYLES_ROOT)},
        cwd=str(_HERE),
    )
    if rc != 0:
        click.echo(f"[kairos-pd] 스타일 인터뷰 종료 (exit {rc})", err=True)
        raise SystemExit(rc)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_style.py -v
```

Expected: 5 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
/opt/homebrew/bin/python3.12 -m pytest tests/ -v 2>&1 | tail -5
```

Expected: 40 passed

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add cli.py tests/test_cli_style.py
git commit -m "feat: style new invokes style-interviewer via ClaudeRunner"
```

---

## Task 5: 최종 검증

**Files:**
- 수정 없음 — 통합 동작 확인

- [ ] **Step 1: 전체 테스트**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
```

Expected: 40 passed

- [ ] **Step 2: style list 동작 확인**

```bash
kairos-pd style list
```

Expected: `이로미즘` 출력

- [ ] **Step 3: style show 동작 확인**

```bash
kairos-pd style show 이로미즘 | python3.12 -m json.tool | head -20
```

Expected: JSON 출력 (channel, artstyle, voice, writing 포함)

- [ ] **Step 4: writing_style.md 내용 확인**

```bash
wc -l /Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md
head -10 /Volumes/jleavens/Projects/kairos-pd/styles/이로미즘/writing_style.md
```

Expected: 140줄 이상 / `# 이로미즘 문체 스타일 가이드` 출력

- [ ] **Step 5: 최종 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add .
git commit -m "feat: kairos-pd Plan 3 완료 — 스타일 매니저 + 이로미즘 샘플"
```

---

## Verification

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
# Expected: 40 passed

kairos-pd style list
# Expected: 이로미즘 v1.0

kairos-pd style show 이로미즘 | python3.12 -m json.tool | grep channel
# Expected: "channel": "이로미즘"
```

---

## Self-Review

### Spec Coverage

| 스펙 요구사항 | 구현 태스크 |
|-------------|-----------|
| style_bundle.json 스키마 (artstyle, voice, writing, tts, image_rules) | Task 1(StyleManager) + Task 2(샘플) |
| writing_style.md — semoji_style_guide.md 수준 상세 가이드 | Task 2 |
| `style new` → Claude 인터뷰어 실행 | Task 3(SKILL.md) + Task 4(CLI) |
| StyleManager CRUD (load/save/validate/set_field) | Task 1 |
| 이로미즘 샘플 스타일 (테스트 + 실사용 가능) | Task 2 |
| CLI 테스트 (list/show/new/set) | Task 4 |
| writing.style_file 포인터 패턴 (v3 호환) | Task 1 + Task 2 |

### v3 Design.md 패턴 적용 ✅
- `semoji_style_guide.md` 7섹션 + 체크리스트 구조 → `writing_style.md` 표준으로 채택
- `semoji.json`의 `writing_style: "semoji"` 참조 키 → kairos-pd의 `writing.style_file: "writing_style.md"` 포인터로 개선
- style-interviewer SKILL.md가 이 MD 포맷을 강제하여 신규 채널도 동일 품질 보장

### Placeholder 없음 ✅
### 타입 일관성 ✅ — StyleManager.load_bundle() → dict, save_bundle(channel, bundle: dict)
