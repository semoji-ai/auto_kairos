# Jev(TypeSafe) 검토 — 오토 카이로스에 맞는가

> 2026-09-19 조사. **아직 채택하지 않았다.** 실측 없이 쓴 검토 노트이므로
> 이 문서의 수치는 전부 공급사·언론 발표값이다. 우리 쪽 실측은 5절의 파일럿을
> 돌린 뒤에야 생긴다. 래칫 원칙상 그 전에는 현상 유지다.

---

## 0. 한 줄

**판단을 잘하는 모델이 아니라 판단만 하는 모델이다.** 그래서 오토 카이로스의
에이전트를 대체할 수는 없고, **관문(check_*.py)의 1차 선별**에만 들어갈 자리가 있다.
그런데 우리 관문의 절반은 그림을 봐야 하는데 Jev는 그림을 못 본다.

---

## 1. 무엇인가 (확인된 사실)

TypeSafe AI가 2026-09-15 얼리액세스로 연 「System One 모델」이다. 나온 지 나흘째다.

```
state(상태) 한 덩어리 + 타입이 붙은 질문 여러 개  →  구조화된 답 + 보정된 확률
```

글자를 만들지 않는다. 질문 종류가 셋뿐이다.

| 종류 | 무엇 | 돌려주는 것 |
|---|---|---|
| **Noul** | 예/아니오 | 0~1 확률 |
| **Choice** | 보기 중 하나 (최대 255지) | 고른 값 + 확률분포 + confidence |
| **Score** | 2~10단계 등급 | 등급 + 확률분포 + confidence |

질문 여러 개가 **같은 state에 병렬로** 걸린다. state를 한 번만 읽는다.

```python
from typesafe_sdk import Choice, TypeSafeClient      # pip install typesafe-sdk (0.7.0, py>=3.10)

with TypeSafeClient() as client:                     # TYPESAFE_API_KEY
    r = client.system_one(
        state={"narration": "...", "desc": "..."},
        questions={"verdict": Choice(instructions="...",
                                     criteria={"ok": None, "risky": None, "wrong": None})})
    r.choices["verdict"].choice
```

| | |
|---|---|
| 컨텍스트 | 32K (state + 가장 긴 질문) · 전체 예산 64K |
| 값 | 입력 $0.042/M · **출력 $0** |
| 속도 | 70~500ms (발표 기준 LLM 대비 약 193배, 값 444배) |
| 경로 | 자체 API · OpenRouter · Vercel AI Gateway · Cloudflare |

「보정된 확률(calibrated)」이 이 모델의 요지다. confidence 0.9가 실제로 열 번 중
아홉 번 맞는다고 주장한다. RLCD 라는 학습법으로 그걸 맞췄다고 한다.

---

## 2. 못 하는 것 — 우리에게 치명적인 순서대로

### ① 그림을 못 본다

공급사 문서가 명시한다 — 이미지·음성·영상은 **텍스트로 전처리해서 넣으라**고.
그런데 오토 카이로스의 판정 관문은 절반이 그림을 여는 것이다.

```
check_image_says.py        그린 뒤 그림을 열어 「이 말을 하는가」   ← 규칙이 ⑦로 못박은 관문
review_images_gemini.py    3중 교차 검수 (Gemini 멀티모달)
compare_scene_vs_info.py   씬 그림 ↔ 도해를 나란히 열어 고른다
check_infographic.py       겹침·묻힘·군더더기
_imggen/review_sheets.sh   인물 시트 검수
```

`image-direction-rules.md` 가 「⑦이 없으면 나머지가 다 무의미하다」고 적어 둔 그
자리다. Jev로는 못 간다. 그림을 말로 옮겨 넣으면 되지 않느냐 — 그 방식이 왜
실패하는지는 `character-sheet-rules.md` 1절에 세 번의 실패로 적혀 있다.

### ② 근거를 못 낸다

확률만 나오고 자연어 이유가 없다. 우리 판정기는 전부 이유를 함께 받는다.

```
check_asset_relevance   why · instead(대신 찾아야 할 자료)
check_redundancy        why · same_as · drop
ask_removal             lost · gained · why
```

그리고 규칙이 이유를 요구한다.

> **채점 결과를 그대로 믿지 않는다.** 감점 근거는 원본 데이터에서 확인하고,
> 틀렸으면 근거를 들어 반박한다. — `direction-standard.md` 6절 8항
>
> **점수를 깎을 때마다 씬번호를 대게 한다** — 못 대면 깎지 못한다.
> — `content-evaluation-rules.md` 2절

이건 실제로 일했다. EP01 채점에서 「씬 48·49에 mapScene이 없다」며 5점을 깎았는데
둘 다 있었다. 근거가 있었기에 반박할 수 있었다. **확률 0.83만 돌아오면 그 반박이
불가능하다.** 이유를 못 대는 감점은 우리 규칙상 감점할 수 없는 감점이다.

### ③ 연도·수치·간접 지시에 약하다

공급사가 스스로 적어 둔 약점이다(counting·calculation·numeric precision·indirection).
그런데 우리가 잡아야 하는 오류가 정확히 그 모양이다.

```
1931년 개업 이야기에 노년 초상       → 나이와 연도의 간접 대조
1940년대 동업에 2005년 출범식 사진   → 연도 건너뜀
값 4개에 라벨 2개                    → 개수 대조
```

### ④ 한국어 성능이 공개되지 않았다

발표 자료·벤치마크가 전부 영어다. 우리 판정 대상은 전부 한국어 나레이션이고,
`verify_voice` 는 아예 **한국어 종결어미 분포**를 본다. 영어에서 맞춘 calibration이
한국어에서도 유지되는지는 **아무 근거가 없다.** 파일럿의 가장 큰 미지수가 이것이다.

### ⑤ 나온 지 나흘이다

`Jev 1.13 jaggedness` 라는 「알려진 실패 모드」 문서가 따로 있을 만큼 초기다.

---

## 3. 그럼에도 맞는 자리가 있다

Jev를 **에이전트 자리**에 놓으면 전부 틀리지만, **관문의 1차 선별**에 놓으면 맞는다.
우리 관문 중 텍스트만 보고 보기가 닫혀 있는 것들이다.

| 자리 | 지금 | Jev 표현 | 되나 |
|---|---|---|---|
| `check_asset_relevance --judge` | codex exec, 타임아웃 1800초 | Choice(ok/risky/wrong) | **된다** — payload가 이미 텍스트뿐이다 |
| `ask_removal` | claude CLI, 페르소나 4인 | Choice(빼는 게 낫다/두는 게 낫다) | **된다** — 판정에 쓰이는 건 verdict 하나 |
| `check_redundancy` | claude CLI | Choice(keep/풀이/사족) | 된다 (③ 세 예외가 관건) |
| `check_kind_reason` | 정규식 `WEAK` | Noul(「이유가 되는 이유인가」) | 된다 — 정규식보다 나을 여지 |
| `run_visual_mode` | codex exec | Choice(재연/인포/실물/콜라주/지도) | 된다 |
| `verify_voice` **②층** | **비어 있다** | Noul(major만) | 된다 — 아래 참조 |
| `vault_lookup_module` slug 매처 | LLM | Noul/Choice | 된다 |
| `check_image_says` | claude + Read | — | **안 된다** (그림) |
| `compare_scene_vs_info` | claude + Read 2장 | — | **안 된다** (그림 2장) |
| `review_images_gemini` | Gemini 멀티모달 | — | **안 된다** (그림) |
| `manuscript-reviewer` · `script-reviewer` | 자체 3라운드 래칫 | — | **안 된다** — 개정본을 쓰는 게 본체다 |
| `script-director` · `draft-writer` 전부 | opus | — | **안 된다** (생성) |

### `verify_voice` ②층이 가장 깨끗한 자리다

`direction-standard.md` 7절이 이렇게 적어 뒀다.

```
층            adobe   v3    왜
① regex 지표    ✅     ✅    객관적, 싸다
② LLM 이해도    ✅     ✗     ← 비어 있다
③ 자동 재작성    ✅     ✗     붙이면 안 된다
```

> 언젠가 자동화한다면 **②(LLM 심사, major만 탈락)를 먼저** 붙이고 그다음에 ③이다
> — 순서를 뒤집으면 스터핑이 열린다.

Jev가 ②에 들어가면 **③이 구조적으로 불가능해진다.** 재작성을 할 줄 모르는 모델이라
지표 스터핑이 원천 차단된다. 우리가 경계하던 위험이 모델의 한계 덕에 사라진다.

### 두 층 구조가 맞다

Jev 단독이 아니라 앞에 세운다.

```
지금    180건 전부 → codex exec (1800초) → verdict + why + instead
바꾸면  180건 전부 → Jev (수 초, 약 $0.005) → ok 는 통과
                    risky·wrong 만 → LLM → why + instead
```

「근거를 못 낸다」는 이렇게 비켜 간다 — **근거가 필요한 것은 걸린 것뿐**이고,
걸린 것에는 LLM이 붙는다. ok 판정에 이유를 읽은 적은 원래 없다.

---

## 4. 래칫 판정

> 기존보다 **명확히** 우위인 방식만 채택, 아니면 현상 유지.

지금 아는 것으로는 「명확히 우위」가 아니다.

| | |
|---|---|
| 확실한 이득 | 속도(1800초 → 수 초)와 값(사실상 0) |
| 확실한 손실 | 자연어 근거. 두 층 구조로 비켜 갈 수 있으나 공짜는 아니다 |
| **모르는 것** | **한국어에서 맞느냐.** 이게 답이 없으면 나머지는 의미가 없다 |

그래서 **전면 도입은 아니고, 재 보고 정한다.** 다행히 우리에게는 정답지가 있다.

---

## 5. 파일럿 — 정답지가 이미 있는 두 곳

새로 라벨을 만들 필요가 없다. 과거 작업이 정답지를 남겨 뒀다.

### 파일럿 A — `check_asset_relevance --judge`

```
정답지   12편 180건. 그중 relevance 공란 58건(33%)
         EP01 시청자가 지적한 실물 자료가 하나도 빠짐없이 공란 목록 안에 있었고,
         relevance가 적힌 자료는 한 건도 지적받지 않았다
문항     Choice(ok / risky / wrong)
state    {narration(400자), desc, relevance} — 이미 텍스트뿐이다
재는 것  ① 시청자가 지적한 3건(씬 48·57·5)을 risky·wrong 으로 잡는가
         ② 지적 없던 자료를 ok 로 통과시키는가 (오탐률)
         ③ confidence 0.9 구간이 실제로 90% 맞는가 ← 한국어 calibration
값       180건 × 약 600토큰 ≈ 0.11M → 약 $0.005
```

이 자리를 고른 이유는 셋이다. 정답지가 있고, 지금 경로가 가장 느리고(1800초),
**실패해도 비차단**이라 기존 경로를 그대로 두고 나란히 돌릴 수 있다.

> ⚠️ 이 스크립트의 docstring 은 「멀티모달이 직접 이어지는지 본다」고 적혀 있지만
> 실제 payload 는 `narration`·`desc`·`relevance` **텍스트뿐**이다. 주석과 구현이
> 어긋나 있다 — 그래서 Jev 로 옮길 수 있는 것이기도 하다.

### 파일럿 B — `ask_removal`

```
정답지   LG 1편. 11줄을 빼자 5줄이 「빼면 안 된다」로 돌아왔다.
         이어 5줄 → 2줄, 2줄 → 2줄 다 돌아왔다
문항     Choice(빼는 게 낫다 / 두는 게 낫다)
재는 것  되돌아온 5줄을 「두는 게 낫다」로 잡는가
         ← 이게 `manuscript-redundancy-rules.md` 2·3절의 세 예외
            (숫자를 닫는 줄 · 반전을 준비하는 줄 · 뒤 문장의 주어가 되는 줄)
```

B가 A보다 어렵다. 세 예외는 **뒤 문장을 읽어야** 판정되는데, 그게 Jev가 약하다고
적어 둔 「indirection」이다. B에서 통과하면 한국어 서사 판단까지 되는 것이고,
떨어지면 「닫힌 사실 대조에만 쓴다」로 범위가 정해진다. **둘 다 돌려야 선이 그어진다.**

### 통과선

```
파일럿 A   시청자 지적 3건을 전부 잡고, 오탐이 지금(codex)보다 늘지 않을 것
파일럿 B   되돌아온 5줄 중 4줄 이상을 「두는 게 낫다」로 잡을 것
공통       confidence 0.9 구간의 실제 적중이 85% 이상 (한국어 calibration)
```

셋 다 넘으면 A부터 두 층 구조로 넣는다. 하나라도 못 넘으면 **현상 유지**다.

---

## 6. 지금 막힌 것

이 세션에서는 재 볼 수 없었다.

```
TYPESAFE_API_KEY      없다 (.env.example 에도 없다)
api.typesafe.ai       이 환경의 프록시가 막는다 (CONNECT 403)
typesafe.ai · docs    egress 차단 — 1차 문서를 직접 못 읽었다
pypi typesafe-sdk     읽힌다 (0.7.0). 위 API 모양은 이 패키지 README 에서 확인
```

그래서 1절의 수치는 전부 언론·유통 경로를 통한 2차 정보다. 파일럿을 돌리려면
키와 아웃바운드가 먼저 필요하다.

---

## 7. 결론

**「판단을 잘한다」는 말을 우리 맥락으로 옮기면 「판정 라벨을 빠르고 싸게 붙인다」이지
「연출을 판단한다」가 아니다.** 오토 카이로스의 판단은 대부분 그림을 보고, 이유를
적고, 고쳐 쓰는 데까지 간다. 그건 Jev 바깥이다.

남는 자리는 **텍스트 관문의 1차 선별**이고, 거기서는 속도·값의 차이가 두 자릿수다.
`verify_voice` ②층처럼 **비어 있는 칸**도 하나 있다. 작지만 진짜다.

다음 행동은 하나다 — **키를 받아 파일럿 A·B를 돌린다.** 그 전에는 채택하지 않는다.

---

## 함께 볼 것

- `docs/rules/direction-standard.md` 7절 — 게이트는 검출기다, 자동 재작성을 붙이지 않는다
- `docs/rules/image-direction-rules.md` — 그린 뒤 그림을 열어 본다(⑦)
- `docs/rules/content-evaluation-rules.md` — 지표를 먼저 의심한다, 감점에 근거를 단다
- `docs/rules/manuscript-redundancy-rules.md` 2·3절 — 빼면 안 되는 세 가지
- `docs/hybrid-execution.md` — provider 선택 규칙
