# 세모지 문체·분량이 원고에 반영되지 않는 문제 — 진단 및 수정 플랜

**작성:** 2026-08-03 (서브머신에서 진단, 메인컴 개발용 인계)
**상태:** 원인 규명 완료 · 수정 미착수 · **차단 결정 1건 있음(§5)**

---

## 1. 증상

`plan.md` 에 `채널: semoji`, `톤: 흥미로운 다큐`, `분량: 5분` 을 지정했으나, 산출된 최종 원고의 문체가 기존 세모지 채널과 다르고 분량도 크게 모자람.

재현 프로젝트: `projects/bd4d47b9` (「메시의 인생」, 2026-08-03 16:47 실행, 파이프라인 자체는 정상 완주)

---

## 2. 근본 원인 (3건, 모두 확인됨)

### 원인 A — 세모지 **텍스트** 문체 정의 파일이 존재하지 않음

저장소 전체 검색 결과, 원고 문체를 규정하는 자료가 없다. 이름이 비슷한 파일들은 전부 다른 용도다.

| 파일 | 실제 용도 | 로드 위치 |
|---|---|---|
| `data/artstyle/semoji.md` | **이미지** 아트스타일 (flat-vector, 눈=검은 점 등) | `backend/imagegen.py:25` `STYLE_FILE` 뿐 |
| `data/artstyle/themes/semoji.json` | 비주얼 테마 | — |
| `data/artstyle/voices.json` | TTS 음성 ID | `backend/tts.py:36` |
| `data/brief-dna.md` | 서사 **구조** 레버 6종(아크·인물·반전·현재연결·증거·척추) | `backend/brief.py:52` |

검증: 파이프라인 5개 스킬의 `SKILL.md` 에서 `문체|톤|voice|style|세모지|말투|어투` 검색 → **전 파일 0건**.

→ `plan.md` 의 `채널: semoji` 와 `톤: 흥미로운 다큐` 는 **정의가 없는 빈 라벨**. 모델이 매 실행마다 자기 기본값으로 쓴다.

### 원인 B — 그 라벨조차 최종 2단계에 전달되지 않음

`skills/*/skill.json` 의 `inputs` 체인 (`backend/skills_cfg.py:build_prompt` 가 이 목록만 프롬프트에 주입):

```
plan-explore          [plan.md]                                  plan.md ✅
deep-research         [plan.md, strategy/options.md]             plan.md ✅
draft-write           [plan.md, options.md, research_reports/deep.md]  plan.md ✅
target-research       [drafts/v1.md, deep.md]                    plan.md ❌
finalize-manuscript   [drafts/v1.md, research_targeted/targeted.md]    plan.md ❌  ← 최종본 집필
review-refine         [final_manuscript.md, deep.md, targeted.md]      plan.md ❌  ← 최종본 수정
```

**최종 원고를 쓰고 다듬는 두 단계가 채널·톤·분량을 전혀 모르는 상태로 실행된다.**

### 원인 C — 분량이 1분으로 하드코딩

`plan.md` 의 `분량: 5분` 이 무시된다. 두 스킬 본문에 고정 문구가 박혀 있다.

```
skills/draft-write/SKILL.md:5         "1분(한국어 약 400자) 원고를 쓴다"
skills/finalize-manuscript/SKILL.md:5 "분량 1분(한국어 약 400자) 유지"
```

실측: `projects/bd4d47b9/final_manuscript.md` 의 나레이션(메타라인 제외) **291자**. 5분 목표(약 1,200~1,500자)의 **1/4 수준**.

---

## 3. 뒷받침 증거 — 기존 프로젝트끼리도 문체가 불일치

문체 앵커가 없다는 직접 증거. 같은 파이프라인 산출물인데 서로 다르다.

| 프로젝트 | 문장 어미 | 숫자 표기 |
|---|---|---|
| `demo01` (트럼프) | **합니다체** — "백악관에 두 번 들어갔습니다" | — |
| `tesla` (테슬라) | 평서체 "~했다/됐다" | **2003년, 3.9초** (아라비아) |
| `bd4d47b9` (메시) | 평서체 "~됐다" | **"이천이십이년", "육백칠십이 골"** (전부 한글) |

메시 원고에는 아라비아 숫자가 **0개**다. 표기 규칙조차 실행마다 달라진다.
(참고: `skills/*/SKILL.md` 의 유일한 한국어 규칙은 "가타카나/히라가나/한자 금지" 뿐 — 숫자 표기 규정 없음.)

---

## 4. 재현 방법

```bash
# 레포 루트에서
./.venv/bin/python -m backend.app          # ← app.py 직접 실행은 실패함(§7)
# AE 패널 [연결] → 새 프로젝트: 채널 semoji / 분량 5분 / 톤 흥미로운 다큐 → 파이프라인 실행
```

산출물 확인:
```bash
python3 - <<'EOF'
import re,pathlib
t=pathlib.Path("projects/<id>/final_manuscript.md").read_text(encoding="utf-8")
nar="\n".join(l for l in t.splitlines() if not re.match(r'^\s*[\[(#]',l))
print("한글", len(re.findall(r'[가-힣]',nar)), "자")
EOF
```

---

## 5. 문체 정본 — 확인 완료 ✅

**정본은 `~/Projects/kairos-vault` (Obsidian 볼트).** 저장소 밖에 이미 존재하며, 전부 `status: validated`.

| 노트 | 내용 | 근거 |
|---|---|---|
| `01-patterns/style-dna/문장-리듬-패턴.md` | 짧은 문장 2~3연타 → 의미부여 / **"그런데" 단독행 반전** / "하지만" 역전 리듬 / 대사 직접인용 / **"~다고 합니다" 전달체** | 5편 |
| `01-patterns/structure/원고-구성-방식.md` | **"~습니다/입니다" 기본 + "~거죠/잖아요/거든요" 구어체 혼용** (팩트="습니다", 공감="거죠") / 챕터 번호+제목(인물 5~7) / `(타이틀)` 마커 / 1문단 2~5문장 / 1문장=나레이션 1호흡 | 5편 |
| `01-patterns/storytelling/인물-서사-분석.md` | 인물 카테고리 서사 구조 — **「메시의 인생」과 동일 카테고리** | **87편 전수** |
| `01-patterns/hooks/도입부-후킹-패턴.md` | 도입 훅 | — |
| `01-patterns/transitions/챕터-전환-패턴.md` | 챕터 전환 | — |
| `channels/세모지/videos/*.md` | 실제 영상별 노트 | 다수 |

### 정본 대비 현재 산출물 측정 (`projects/bd4d47b9`)

| 규칙 | 정본 요구 | 실측 |
|---|---|---|
| 존댓말 `~습니다/입니다` | 기본 | **0회** |
| 구어체 `~거죠/잖아요/거든요` | 혼용 | **0회** |
| `~다고 합니다` 전달체 | 핵심 | **0회** |
| "그런데" 단독행 반전 | 필수 | **0회** |
| "하지만" 역전 | 반복 | 1회 |
| 평서체 `~했다/됐다` | 금지 | **6회** |
| 챕터 번호+제목 | 5~7개 | **0개** |
| `(타이틀)` 마커 | 1회 | **0회** |

→ **8개 규칙 중 7개가 0.** 문체가 "다른" 수준이 아니라 볼트가 파이프라인에 **전혀 연결돼 있지 않다**.

### ⚠️ 남은 차단 요소 — 볼트가 이 머신 로컬에만 있음

- `~/Projects/kairos-vault` 는 **git 저장소가 아니며**, NAS(`/Volumes/jleavens/Projects/`)에도 사본이 없다.
- NAS의 `auto_kairos_codex/codex_project_vault` 는 **화면 레이아웃용 방송 문법** 볼트로 별개다(문체 아님).
- **메인컴에서 착수하려면 볼트 동기화가 선행돼야 한다.** NAS로 옮기거나 git 저장소로 만들 것.

### gn-voice — 팩은 쓰지 말고, **방법론을 이식할 것**

**실험 결과(공냥 팩 그대로 적용):** 정본 규칙 개선 0건, 평서체 6→8회로 **악화**.
judge 리포트 *"해라체 1.000(팩 0.835 방향 일치)"* — 공냥 팩은 **해라체(평서체) 타깃**이라 존댓말 기반 세모지와 정면충돌.
→ **기존 팩(essay 등)을 세모지 원고에 적용하는 것은 금지.**

**단, gn-voice의 파이프라인 자체가 이 문제의 정답이다.** (`~/Projects/gn-voice` = 빌드 저장소, `~/.claude/skills/gn-voice` = 배포본)

```
코퍼스 → fingerprint.py(kiwipiepy 형태소) → --calibrate: 대조군 대비 z-프로필
      → 장르×채널 셀 지문 → 70줄 팩 증류(레지스터·시그니처·리듬·구조관습·대조페어·Do-NOT)
      → 러너(윤문) → 게이트(verify_style.py + gate_fidelity.py) → 심사관(A~D 등급)
```

README 핵심 주장 — **"분석 대상을 한 사람으로 좁히면 다뤄야 할 분포가 확 줄어든다"**.
**"한 사람" → "한 채널(세모지)"** 로 치환하면 그대로 성립한다. 팩 수치는 전부 코퍼스 실측이고 손으로 적은 숫자가 없다는 점, 채점을 LLM이 아니라 파이썬 스크립트가 한다는 점이 §5 표 같은 검증을 자동화해 준다.

**재료 보유 현황:**

| 필요 | 상태 | 위치 |
|---|---|---|
| 세모지 코퍼스 | **원고 60편 .hwp 추출 완료(329KB)** | `002_intra/001_세상의모든지식/기획/원고모음` (NAS) |
| 검증된 패턴 | 인물 87편 전수분석 + validated 노트 5종 | `~/Projects/kairos-vault` |
| 빌드 스크립트 | 그대로 재사용 가능 | `~/Projects/gn-voice/scripts/` |
| 코퍼스 규격 | `manifest.jsonl`(367행), `strip-rules.md`, train/test 15% 봉인 | `~/Projects/gn-voice/corpus/` |
| 3역 에이전트 | monolith / judge / composer | `~/.claude/agents/` |
| **kiwipiepy venv** | ⚠️ **이 머신에 없음** (`~/.venvs/gn` 부재) | README상 "ext4 위" = 리눅스 머신 추정 — **소재 확인 필요** |

> .hwp 본문 추출은 olefile + zlib + HWPTAG_PARA_TEXT(67) 파싱으로 60/60 성공. 추출 스크립트는 재작성 필요(스크래치패드에만 있음).

실험 산출물: `_workspace/2026-08-03-001/` (커밋 대상 아님)

---

## 6. 수정 플랜 (볼트 동기화 후 착수)

**테스트:** `./.venv/bin/python -m pytest`

### Task 0: 볼트 접근 확보 (선행)

- [ ] `~/Projects/kairos-vault` 를 메인컴에서 접근 가능하게 만든다 (NAS 이전 또는 git 저장소화)
- [ ] 결정: 볼트를 **참조**만 할지, 컴파일 결과를 **레포에 복사**할지
      → 볼트는 계속 갱신되므로 **컴파일 스크립트 + 산출물 커밋** 방식 권장 (레포가 볼트 경로에 의존하면 CI·타 머신에서 깨짐)

### Task 1: 세모지 문체 팩 구축 — gn-voice 방법론 이식

**두 갈래 중 택1. (b) 권장.**

**(a) 볼트 수기 컴파일** — 빠르지만 수치가 손으로 적힌 값이라 검증 게이트를 만들 수 없다. 임시방편.

**(b) gn-voice 파이프라인 재사용** ← 권장. 게이트·심사관까지 딸려 온다.

- [ ] 세모지 코퍼스 구축 — 원고 60편 + 볼트 `channels/세모지/videos/`
  - `.hwp` 추출 스크립트 재작성 (olefile+zlib, HWPTAG_PARA_TEXT=67)
  - **주의: 원고모음은 작가 초고라 개조식 메모·취소선·`/` 끊기 마커가 섞여 있다.** `strip-rules.md` 방식으로 정제 필요
  - `manifest.jsonl` 규격 준수, **train/test 15% 봉인** (규칙 만들 때 test 절대 열람 금지)
  - 카테고리 라벨: 인물/브랜드/일반상식/역사 — 볼트 `01-patterns/storytelling/*-서사-분석.md` 분류 재사용
- [ ] `~/.venvs/gn` (kiwipiepy) 소재 확인 또는 재구축
- [ ] `fingerprint.py --corpus semoji` → `--calibrate` (대조군 ref는 gn-voice 기존 것 재사용 가능)
- [ ] z-프로필에서 세모지 팩 증류 → `data/artstyle/packs/semoji-{인물,브랜드,상식}.md`
      최소 항목 (볼트 노트로 교차검증):
  - 어미 체계 — `~습니다/입니다` 기본, `~거죠/잖아요/거든요` 혼용 규칙(팩트/공감 구분), **평서체 금지 명시**
  - `~다고 합니다` 전달체 사용 지점
  - 리듬 — 짧은 문장 2~3연타 → 의미부여, "그런데" 단독행, "하지만" 역전
  - 구조 — 챕터 번호+제목(인물 5~7), `(타이틀)` 마커, 1문단 2~5문장, 1문장=1호흡
  - 숫자 표기 규칙 (**현재 실행마다 아라비아↔한글이 뒤바뀜 — 볼트에 규정 없으면 여기서 확정할 것**)
- [ ] 이미지용 `data/artstyle/semoji.md` 와 **파일명·용도를 명확히 구분** (혼동이 이 버그의 근원)
- [ ] 컴파일 산출물을 커밋해 볼트 없이도 파이프라인이 동작하게 할 것

### Task 2: 문체·기획 정보를 전 집필 단계에 주입

**Files:** `backend/skills_cfg.py`, `skills/draft-write/skill.json`, `skills/finalize-manuscript/skill.json`, `skills/review-refine/skill.json`; Test `tests/test_skills_cfg.py`

- [ ] **실패 테스트 먼저**: `build_prompt("finalize-manuscript", ...)` 결과에 `plan.md` 내용과 문체 가이드 문자열이 포함되는지 검사 → 현재 실패해야 정상
- [ ] `skill.json` 의 `inputs` 에 `plan.md` 추가 (target-research/finalize-manuscript/review-refine)
- [ ] `build_prompt` 가 문체 가이드를 주입하도록 확장. 설계 선택지 2가지:
  - (a) `skill.json` 에 `"style_ref": "data/artstyle/semoji-voice.md"` 필드 추가 — 레포 루트 기준 경로라 `inputs`(프로젝트 상대 경로)와 해석이 다름에 주의
  - (b) `plan.md` 의 `채널:` 값으로 `data/artstyle/{채널}-voice.md` 를 조회해 자동 주입 — 채널 확장에 유리
  - → **(b) 권장.** 채널이 늘어날 때 skill.json 6개를 매번 고칠 필요가 없다.
- [ ] `missing_inputs` 가 문체 파일 부재를 실패로 만들지 않도록 주의 (없으면 경고 후 진행)

### Task 3: 분량 하드코딩 제거

**Files:** `skills/draft-write/SKILL.md`, `skills/finalize-manuscript/SKILL.md`, `backend/skills_cfg.py`; Test `tests/test_skills_cfg.py`

- [ ] SKILL.md 의 "1분(한국어 약 400자)" 고정 문구 삭제 → `{{목표 분량}}` 자리표시자 또는 프롬프트 말미 주입으로 대체
- [ ] `plan.md` 의 `분량:` 파싱 → 목표 글자수 환산 후 주입.
      환산 기준은 `backend/brief.py:parse_plan` 이 이미 `duration` 을 뽑고 있으니 **파서 재사용**(중복 구현 금지)
- [ ] 기준 수치: 한국어 나레이션 **분당 약 250~300자**로 잡을 것. (현행 "1분=400자"는 실제 낭독 속도보다 빠름 — 이 값도 함께 재검토 대상)
- [ ] 테스트: `분량: 5분` 인 `plan.md` 로 build_prompt 시 1,200자 이상 목표가 프롬프트에 포함되는지

### Task 4: 문체 검증 게이트 이식 (Task 1을 (b)로 한 경우)

**Files:** `scripts/verify_semoji_style.py`, `backend/pipeline.py`; Test `tests/test_verify_style.py`

- [ ] `gn-voice/scripts/verify_style.py` 를 세모지 팩 밴드용으로 이식 — 어미 분포·구두점 밀도·개행 리듬을 실측 밴드와 대조
- [ ] **하한선 유지**: 문장 길이가 실측보다 지나치게 고른("너무 매끈한") 원고도 탈락시킬 것 — gn-voice의 핵심 장치
- [ ] `gate_fidelity.py` 이식 — 수치·고유명사 전수 대조로 날조·누락 차단 (리서치 기반 원고라 특히 중요)
- [ ] `review-refine` 단계 뒤에 게이트를 붙이고, 실패 시 위반 항목만 겨냥해 1회 재작성

### Task 5: 회귀 검증

- [ ] 「메시의 인생」 동일 조건 재실행 → §5 측정표 8개 규칙 재측정 (0/8 → 목표 7/8 이상)
- [ ] **봉인해 둔 test 15% 원고로 검증** — 학습에 쓴 원고로 채점하면 외운 건지 구분 안 됨
- [ ] `projects/tesla`, `projects/demo01` 재생성 시 문체가 서로 수렴하는지 확인

---

## 7. 부수 발견 (별건, 같이 처리 권장)

### 7-1. README 의 백엔드 실행 명령이 동작하지 않음

`README.md:35`, `install.sh:101` 의 명령은 그대로 실행하면 실패한다.

```
$ ./.venv/bin/python backend/app.py
ModuleNotFoundError: No module named 'backend'
```

`backend/app.py:10-12` 가 절대 임포트(`from backend import projects`)를 쓰는데 스크립트로 직접 실행하면 `sys.path[0]` 이 레포 루트가 아니라 `backend/` 가 되기 때문.

**수정:** 두 파일의 명령을 `./.venv/bin/python -m backend.app` 로 교체.
(`feat/tylenol-motion-recreation` 브랜치의 자동 스폰 코드도 `python3 -m backend.app` 을 쓴다 — 이쪽이 정본.)

### 7-2. 패널 [연결] 버튼이 백엔드를 띄우지 않음

`cep/com.autokairos.pd/js/main.js:534` → `checkBackend()` 는 `/health` 를 확인만 한다. 백엔드가 죽어 있으면 몇 번을 눌러도 연결되지 않고, 사용자에게는 원인이 보이지 않는다.

**수정:** `feat/tylenol-motion-recreation` 의 `ebdef74` (`feat(panel): health 실패 시 백엔드 자동 스폰(createProcess) + 재시도`) 를 cherry-pick.

---

## 8. 조사에 사용한 명령 (재확인용)

```bash
# 문체 자료가 어디서 로드되는지
grep -rn "semoji.md\|brief-dna\|voices.json" backend/*.py

# 파이프라인 스킬에 문체 지시가 있는지 (→ 0건)
for s in deep-research draft-write target-research review-refine finalize-manuscript; do
  grep -in "문체\|톤\|voice\|style\|세모지\|말투\|어투" skills/$s/SKILL.md skills/$s/skill.json
done

# 스킬 입출력 체인
for s in plan-explore deep-research draft-write target-research finalize-manuscript review-refine; do
  printf "%-22s " "$s"
  python3 -c "import json;d=json.load(open('skills/$s/skill.json'));print(d.get('inputs'),'->',d.get('output'))"
done
```
