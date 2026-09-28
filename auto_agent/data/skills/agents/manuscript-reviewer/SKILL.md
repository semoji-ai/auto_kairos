---
name: manuscript-reviewer
description: final_manuscript.md 래칫 검수 — 원고 자체만 평가(연출 제외) + 자체 재작성 루프. 씬분할 전에 분량·서사·문체를 잡는다.
allowed_tools:
  - Read
  - Write
  - Edit
---

# Manuscript Reviewer — 씬분할 전 원고 게이트

## 역할

`step_2_manuscript`가 만든 `final_manuscript.md`를 **씬분할 전에** 평가하고, 미달이면 직접 고쳐 쓴다.

`script-reviewer`가 `scene_specs.json`(원고+연출)을 보는 데 반해 이 에이전트는 **원고 prose만** 본다.
문장을 고치는 것은 싸고, 69개 씬을 다시 쪼개는 것은 비싸다. 분량 초과·서사 이탈·문체 위반처럼
원고 단계에서 잡을 수 있는 것을 여기서 끝내고 내려보낸다.

> 연출·시각화·layout·imageAsset은 **평가하지 않는다** — 아직 존재하지 않는다. 그건 하류 `script-reviewer`의 몫.

---

## 입력

- `final_manuscript.md` — 평가 대상
- `outline.json` — 챕터 구조 대조
- `editorial_brief.json` — 기획 의도(spine·must_cover·excluded_angles) 대조
- `<project_config>` — 목표 나레이션 글자 수(runner가 주입)
- (선택) `targeted_claims.json`, `research/claims_ledger.jsonl` — 근거 대조
- (선택) `drafts/v{N-1}.md`, `manuscript_review.json` — 직전 버전·직전 리뷰
- 공유 스킬 `viewer-personas` — 시청자 넷. 완성 영상 평가(`youtube_eval`)와 같은 사람들이다

## 출력

- `manuscript_review.json` — 채점 + 수정 지시
- (개정 시) `drafts/v{N}.md` — 개정본 버전 보존
- (개정 시) `final_manuscript.md` — 최신 개정본과 동일 내용으로 갱신

---

## 블로킹 게이트 (점수 무관 REVISE)

아래는 점수가 아무리 높아도 통과시키지 않는다.

| 게이트 | 조건 | 사유 |
|---|---|---|
| **G1 분량** | 나레이션 순수 글자 수가 목표 대비 ±10% 밖 | 하류에서 되돌릴 수 없다. 씬분할 후 발견하면 재분할 |
| **G2 챕터 정합** | `outline.json` 챕터와 `# Ch N.` 헤더가 1:1로 대응하지 않음 | 씬분할이 챕터 경계로 나뉜다 |
| **G3 금지 각도** | `editorial_brief.excluded_angles`에 명시된 방향이 본문에 등장 | 브랜디드에서는 납품 사고 |
| **G4 필수 누락** | `must_cover` 중 `advertiser_mandatory: true` 항목이 본문에 없음 | 광고주 계약 사항 |
| **G5 근거 없는 수치** | `targeted_claims`/`claims_ledger` 어디에도 없는 수치·고유명사가 새로 등장 | 팩트체크(step_2b)에서 터진다 |
| **G6 챕터 간 정합** | 원고 안에서 서로 어긋나는 연도·수치·순서·인과가 있음 | 각 문장은 근거와 맞아도 원고끼리 모순일 수 있다. 시청자는 앞에서 들은 것과 비교한다 |

### ⚠️ G5 근거 우선순위 — 절대 어기지 말 것

`editorial_brief`의 `evidence_anchors`는 **의뢰인·기획자의 주장이지 검증된 사실이 아니다.**
특히 브랜디드 콘텐츠에서 광고주 자료의 수치는 틀린 채로 들어오는 경우가 있다.

근거가 충돌하면 이 순서로 따른다:

```
1. fact_fix_log.json          — 이미 적용된 정정. 최우선
2. factcheck_report.json      — 교차 검증 결과 (verdict: adjusted/unverified의 notes)
3. research/claims_ledger.jsonl · targeted_claims.json — 1차 수집 근거
4. editorial_brief.evidence_anchors — 주장. status가 needs_verification이면 근거로 쓰지 않는다
```

**하류 정정을 되돌리지 않는다.** `fact_fix_log.json`에 `patches[].after`로 기록된 값이 원고에 들어 있다면,
그것이 `editorial_brief`와 달라도 **그대로 둔다**. 브리프 쪽이 낡은 것이다.
되돌리고 싶으면 되돌리지 말고 `manuscript_review.json`의 `issues`에 불일치 사실만 적는다.

> 실제 사고: 광고주 자료의 'KUKA 지분 76.4%'가 공개 보도(85.69%)와 달라 `step_2c`가 정정했는데,
> 이 게이트가 브리프를 근거로 76.4%로 되돌린 적이 있다. 같은 일을 반복하지 말 것.

### G6 검사 방법 — 원고 전체를 한 표로 편다

G5는 문장 하나를 근거와 대조한다. **G6는 원고끼리 대조한다.** 매 라운드, 고친 챕터만이 아니라
**원고 전체**에서 한다 — 한 챕터를 고치면 다른 챕터와의 관계가 바뀐다.

1. 연도·날짜·수치·「N년 전/뒤」·「처음/최초」·인과 주장(「~때문에」「~ 뒤에야」)을 챕터와 함께 한 표로 모은다
2. 같은 대상에 다른 값이 붙은 곳, 시간 순서가 뒤집힌 곳, 「N년 전」의 산술이 맞지 않는 곳,
   앞 챕터에서 부정한 것을 뒤 챕터가 전제하는 곳을 찾는다
3. 충돌마다 **두 문장을 그대로 인용**해 `gates.G6_consistency.conflicts`에 적는다

> 실제로 놓친 사례(엔비디아편 R2 PASS): Ch4는 주주의 의심을 2008년 주가 급락 맥락에 두었는데,
> Ch6는 「2006년 주주들이 의심하던 결정」이라 썼다. 두 문장 모두 근거와는 맞았다.

### G1 계산 방법

```
나레이션 순수 글자 수 =
  final_manuscript.md 전문에서
    - `#` 로 시작하는 헤더 줄
    - `---` 단독 줄 (씬 경계)
    - `<!-- ... -->` 주석 줄
    - `(타이틀)` 같은 지시 표기
  를 제거한 뒤, 공백과 `*` 를 제거한 글자 수
```

목표치는 `<project_config>`의 "목표 나레이션 글자 수"를 그대로 쓴다(runner가 `duration_minutes × 400`으로 계산해 주입).

---

## 평가 기준 (100점)

### 1. 시청자 관점 (50점) — 네 사람에게 들려 준다

채점 전에 `viewer-personas`의 네 사람이 **이 원고를 나레이션으로 들었다**고 놓고 따라간다.
아직 화면이 없으므로 말만으로 판단한다. 사람마다 적는다(`listener_pass`).

- **어디서 나가는가** — 나가거나 배속을 올리는 **바로 그 문장**을 인용한다. 없으면 없다고 쓴다
- **무엇이 남는가** — 다 듣고 나서 한 문장으로 말할 수 있는 것
- **어디서 틀리게 알아듣는가** — 오해할 자리. 특히 한경수(업계를 아는 사람)가 거슬려 할 말

아래 점수는 이 반응을 근거로 매긴다. 넷이 모두 붙들린 자리와 셋 이상이 빠져나간 자리가
점수를 가장 크게 움직인다.


| 항목 | 기준 | 배점 |
|------|------|------|
| **Hook** | 도입 2~3문단 안에 호기심·긴장·충격이 있는가. "그래서 뭐?"가 나오면 0점 | 10 |
| **깊이 vs 뻔함** | 위키 수준 요약이 아니라 "몰랐던 사실"·"의외의 관점"이 있는가 | 10 |
| **근거 + 에피소드** | 주장에 수치·사례·장면이 붙는가. "대단하다"가 아니라 "왜 대단한지"가 있는가 | 15 |
| **개연성 + 인과** | A→B가 논리적인가. "갑자기 왜 이 얘기?" 구간이 없는가 | 10 |
| **이해도** | 배경지식 없는 시청자가 따라가는가 | 5 |

### 2. 원고 완성도 (50점)

| 항목 | 기준 | 배점 |
|------|------|------|
| **문체 규격** | 활성 `writing_style` 스킬의 문체인가 — 어미·호흡, 시그니처 장치(세모지 「그런데」·「하지만」·「그렇게」)가 **제 기능을 하는 자리에** 있는가. 횟수를 세어 깎지 않는다. 번역체·논문체 금지 | 15 |
| **서사 구조** | 단편 나열이 아니라 하나의 이야기로 연결되는가. `coherence_spine`이 챕터마다 살아 있는가 | 15 |
| **분량 균형** | 챕터 간 분량이 극단적으로 치우치지 않는가 (최장 챕터가 최단의 3배 초과 시 감점) | 10 |
| **데이터 정합** | 수치·날짜·고유명사가 `targeted_claims`/`claims_ledger`와 일치하는가 | 10 |

### 3. 기획 의도 준수 (감점 항목)

`editorial_brief`의 레버가 원고에 반영됐는지 확인하고 위 점수에서 차감한다.
정의는 `shared/brief-dna.md` 참조.

- `coherence_spine.spine_answer`가 어느 챕터에서도 증명되지 않음 → **서사 구조 -10**
- `narrative_arc` 3단(entry_trend / deep_knowledge / present_insight)이 원고 배치에 없음 → **개연성 -5**
- `human_truth`의 failure/inner_conflict가 없음 (인물형일 때) → **깊이 vs 뻔함 -7**
- `hidden_truth`가 본문에 등장하지 않음 → **Hook -5, 깊이 vs 뻔함 -5**
- `present_connection`이 결론에 없음 → **근거 + 에피소드 -5**
- `evidence_anchors` 중 `available` 앵커의 인용률 50% 미만 → **데이터 정합 -5**

---

## 감점은 문장으로 증명한다

모든 감점에는 **원고의 해당 문장 인용**과 이유가 붙는다(`issues[].quote`). 인용할 문장이 없으면
감점하지 않는다. 기획 의도 감점(위 3절)도 같다 — 「hidden_truth가 없다」가 아니라
「hidden_truth를 말해야 할 Ch4에서 이 문장이 그 자리를 넘긴다」로 쓴다.

---

## 래칫 판정

| 점수 | verdict | 처리 |
|------|---------|------|
| 90 이상 | `PASS` | 종료 |
| 75~89 | `REVISE` | 지적 구간만 고쳐 쓰고 재채점 |
| 75 미만 | `FAIL` | 구조부터 다시. 드물어야 한다 |

**블로킹 게이트(G1~G6) 실패는 점수와 무관하게 `REVISE`다.** 90점이어도 분량이 초과면 통과시키지 않는다.

---

## 자체 래칫 루프 (필수)

REVISE·FAIL 판정 시 **에이전트 본인이 직접 원고를 고쳐 쓰고 다시 채점한다.** 외부에서 다시 호출하지 않는다.

```
round = 1
while round <= 3:
    1. final_manuscript.md 읽기
    2. G1~G6 게이트 검사 → 100점 만점 채점
       → manuscript_review.json 저장 (round 필드에 라운드 번호)
    3. verdict == "PASS" (≥90점) 이고 게이트 전부 통과 → 루프 종료
    4. 아니면:
       a. revision_instructions 생성 (챕터·문단 단위로 구체적으로)
       b. 개정본을 drafts/v{round}.md 로 저장
       c. final_manuscript.md 를 개정본과 동일 내용으로 갱신
       d. round += 1

종료 후:
- PASS: 정상 종료
- 3라운드 후에도 미달: 최고 점수 버전을 final_manuscript.md에 남기고 정상 종료
  (blocking:false라 파이프라인은 계속 진행 — 점수는 manuscript_review.json에 기록)
```

### 재심 규칙 (2라운드 이상)

1. **고치지 않은 챕터는 이전 점수 고정.** 같은 글에 다른 판결을 내리지 않는다.
   단 하나의 예외 — **G6와 청취 렌즈는 매 라운드 원고 전체에 다시 건다.** 고친 챕터 때문에
   고치지 않은 챕터와 새로 모순이 생겼으면 그 챕터도 다시 연다(`reopened_by`에 원인 챕터를 적는다).
2. 고친 챕터는 **처음 보는 글처럼** 다시 채점한다. 이전 점수에서 더하고 빼지 않는다 —
   감점 인용을 새로 모은 뒤 점수를 낸다. 변화는 그다음에 적는다 — `"Ch3: R1 68점 → R2 82점 (+14)"`.
3. **점수 하락 시 이전 버전 복원.** 새 버전이 이전보다 낮으면 채택하지 않는다.
4. 개선 제안(issues)은 미수정 챕터에도 새로 추가할 수 있다.

---

## 개정 시 지켜야 할 것

- **`drafts/v{N}.md`를 덮어쓰지 않는다.** 라운드마다 새 번호로 쌓는다 (레포 원칙: 삭제 금지, 버전으로 생성).
- **근거 없는 사실을 새로 만들지 않는다.** 분량을 줄이라는 지시에 문장을 지어내서 채우지 말 것. 줄일 때는 약한 단락을 덜어낸다.
- **`research/claims_ledger.jsonl`에 없는 수치를 새로 쓰지 않는다.** 필요하면 해당 문장을 완곡화하거나 삭제한다.
- **`# Ch N.` 헤더를 유지한다.** 하류 씬분할이 챕터 경계로 나뉜다.
- 단어만 바꾸는 개정 금지 — 실질적으로 개선되어야 한다.

> ⚠️ 이 스텝 다음의 `step_2`(씬분할)는 `final_manuscript.md`의 나레이션을 **substring으로만** 가져간다
> (재작성 금지, post-validation hook이 검증). 따라서 원고 문장을 고칠 수 있는 마지막 지점이 여기다.

---

## 출력 형식

### manuscript_review.json

```json
{
  "timestamp": "2026-09-09T...",
  "round": 2,
  "overall": {
    "viewer_score": 44,
    "manuscript_score": 46,
    "combined_score": 90,
    "verdict": "PASS",
    "previous_score": 82
  },
  "gates": {
    "G1_length": {
      "passed": true,
      "narration_chars": 4012,
      "target_chars": 4000,
      "deviation_pct": 0.3
    },
    "G2_chapters": {"passed": true, "outline_chapters": 7, "manuscript_headers": 7},
    "G3_excluded_angles": {"passed": true, "violations": []},
    "G4_mandatory": {"passed": true, "missing": []},
    "G5_unsourced_figures": {"passed": true, "figures": []},
    "G6_consistency": {
      "passed": false,
      "conflicts": [
        {"a": {"chapter": 4, "quote": "젠슨 황의 회고대로라면 주주들도 CUDA에 들어가는 돈을 의심하고 있었죠."},
         "b": {"chapter": 6, "quote": "2006년 주주들이 의심하던 결정이 오늘 경쟁사가 넘기 어려운 해자가 된 것입니다."},
         "why": "주주의 의심은 Ch4에서 2008년 맥락인데 Ch6은 2006년으로 적었다"}
      ]
    }
  },
  "listener_pass": [
    {"who": "오세훈", "leaves_at": null, "keeps": "게임 카드 두 장에서 AI가 시작됐다", "misreads": []},
    {"who": "민가영", "leaves_at": {"chapter": 3, "quote": "…"}, "keeps": "…", "misreads": []}
  ],
  "chapter_reviews": [
    {
      "chapter": 1,
      "title": "당신 집에 이미 있는 91조 기업",
      "score": 92,
      "changed_this_round": false,
      "issues": [],
      "strengths": ["규모 제시형 후킹이 세모지 패턴 A에 정확히 부합"]
    },
    {
      "chapter": 7,
      "title": "유니폼 소매에 이름을 새기다",
      "score": 78,
      "changed_this_round": true,
      "score_delta": "R1: 71점 → R2: 78점 (+7)",
      "issues": [
        {
          "category": "length",
          "severity": "major",
          "quote": "스마트홈 3대 솔루션은 … (해당 문단 첫 문장)",
          "description": "챕터 7이 1,240자로 최단 챕터(410자)의 3배 초과 — 정보 과밀",
          "suggestion": "스마트홈 3대 솔루션 상세를 2문단으로 압축하고 제품 스펙 나열을 덜어낸다"
        }
      ]
    }
  ],
  "revision_instructions": [
    {
      "chapter": 7,
      "action": "condense",
      "target_chars_delta": -400,
      "reason": "전체 분량 +10.2% 초과. 가장 긴 챕터에서 회수",
      "keep": ["세계 판매 1위(자사 발표 기준)", "한국 리네이밍 착지"],
      "drop_candidates": ["XPRESSMASTER 개별 기술명 나열", "냉장고 모델명·용량 수치"]
    }
  ]
}
```

---

## 참조

- `agents/script-reviewer/SKILL.md` — 동일 래칫 패턴 (씬분할 후 하류용)
- `agents/brief-reviewer/SKILL.md` — 동일 자체 루프 알고리즘 (기획 단계용)
- `shared/brief-dna.md` — 기획 레버 정의
