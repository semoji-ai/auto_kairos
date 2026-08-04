# 컨텍스트 주입 낭비 감사 (2026-08-04, LG편 실행 실측 기반)

> 배경: EP04~06 3편 생산에 5시간 리밋 70% 소모. codex에 리서치를 위임했음에도 과다 → Claude CLI 호출의 프롬프트 구성을 감사함.

## 결론 요약

가장 큰 낭비는 **script-director SKILL.md(69KB)를 챕터 병렬 호출마다 통째로 재주입**하는 것. 편당 약 9~10회 재주입되어 **편당 약 60만 자(≈27만 토큰)가 중복 투입**된다. 이것 하나가 전체 소모의 지배적 비중.

---

## 1. [치명] 챕터 병렬 처리 시 SKILL.md 전문 재주입

**위치**: `runner.py` `_run_chapter_*` (약 2890~3000행)

씬 분할 스텝(`step_2`)은 챕터 수만큼(LG편 기준 6~8개) 병렬 호출하는데, **각 호출 프롬프트에 `<agent_skill>` 태그로 69KB SKILL.md 전문을 매번 삽입**한다.

```
편당 script-director 호출 = 챕터 7회(step_2) + manuscript 1회 + consistency 1회 ≈ 9회
9 × 69KB = 621KB ≈ 27만 토큰 / 편 (중복분만)
```

**게다가 이 경로는 캐시를 안 탄다.** 코드에는 prompt caching 경로(`static_system` + `cache_control`, 3580~3600행)가 이미 구현돼 있으나, 챕터 병렬 경로는 그것을 쓰지 않고 CLI(`--print`)에 프롬프트를 평문 문자열로 넘긴다.

### 개선안 (효과 순)

**A. 모드별 SKILL 슬라이싱 (최우선, 80% 절감)**
챕터 분할 모드에 실제로 필요한 섹션은 전체의 약 1/5뿐이다.

| 섹션 | 크기 | chapters 모드 필요? |
|---|---|---|
| 다단계 실행 모드 | 12k | ❌ (이미 모드가 결정된 뒤) |
| 작업 흐름 | 14k | ❌ (manuscript 작성용) |
| 씬 스키마 | 7k | ✅ |
| 씬 분할 규칙 / headline / 모션 / 에셋 결정 | ~5k | ✅ |
| 나머지 규칙 | ~2k | ✅ |

→ SKILL.md를 `SKILL.md`(공통) + `mode-manuscript.md` + `mode-chapters.md`로 분할하고 모드에 맞는 것만 주입. 챕터 호출당 69KB → 약 14KB.

**B. 챕터 병렬 경로를 캐싱 SDK 경로로 전환**
`static_system`(SKILL+shared) / `dynamic`(챕터 원고) 분리 후 `cache_control` 적용. 단, 병렬 동시 발사는 캐시 write 레이스가 나므로 **첫 호출로 캐시를 데운 뒤 나머지를 병렬 발사**하는 순서 조정 필요.

A와 B를 함께 적용하면 챕터 호출 비용이 1/10 수준까지 내려간다.

---

## 2. [중] 시리즈 모드에서 preflight 3스텝 중복

편당 `step_0c`(config_inspect) + `step_0b`(editorial_interview) + `step_0d`(brief_ratchet) = **약 $3, 편당 총비용의 30%**.

시리즈물은 `series_plan.json`에 기획이 이미 확정돼 있고 `episode_brief.json`이 자동 생성되는데도, 편마다 기획 인터뷰와 브리프 래칫 리뷰를 새로 돌린다. `step_0d`는 편당 3~7분씩 소모($1.5~2.9).

→ **개선**: 시리즈 실행 시 `_series` 키가 있으면 `step_0b`/`step_0d`를 스킵하고 series_plan의 브리프를 상속. (검증된 브리프를 편마다 재심사할 이유 없음)

---

## 3. [소] 브리프 전 스텝 무차별 주입

`editorial_brief` + `creative_brief`(약 2,000자)가 `data-mapper`/`fact-verifier`/`assembly-director`를 제외한 **모든** 에이전트에 주입된다. `config-inspector` 같은 환경 점검 에이전트에도 들어간다.

→ 영향은 작지만(스텝당 ~3KB), skip 목록에 preflight 계열 추가 권장.

---

## 4. 참고: 낭비가 아닌 것

- **codex 위임 구간**(사전 리서치 5트랙, step_2_target 타겟 리서치)은 Claude 리밋과 무관 — 이미 잘 분리돼 있음.
- **opus 원고(step_2_manuscript)** 자체 비용($2.6~3.5)은 품질의 핵심이라 유지 권장. 단 여기서도 69KB SKILL 주입은 A안으로 줄일 수 있음.

---

## 적용 결과 (2026-08-04 구현 완료)

1·2·4 적용, 3(캐싱 경로)은 병렬 캐시 write 레이스 처리가 필요해 보류.

| 항목 | 구현 | 실측 효과 |
|---|---|---|
| 1 모드별 SKILL 슬라이싱 | `auto_agent/orchestrator/skill_slicer.py` + `runner._load_agent_skill()` | 편당 400,464자 → 258,583자 (**35% 절감**) |
| 2 시리즈 preflight 상속 | `runner._has_series_brief()` + step_0b/0d 스킵 | 편당 **$2.1~3.5 절감** |
| 4 브리프 주입 제외 | `_skip_brief_agents`에 config-inspector, brief-interviewer-auto 추가 | 스텝당 ~3KB |

모드별 슬라이싱 실측: chapters 72%(7회 호출), manuscript 22%, consistency 53% 크기로 축소.
manuscript는 SKILL.md 모드 1.5가 "layout/motion/imageAsset은 이 모드 책임이 아니다"라고
명시하므로 연출 섹션을 안전하게 제거.

검증: `tests/test_skill_mode_slice.py`(7) + `tests/test_series_preflight_skip.py`(6) 통과,
전체 스위트 484 passed / 2 skipped 회귀 없음.

> 주의: 초기 감사에서 "69KB"로 적은 것은 **바이트**였고 실제는 44,496**자**다(한글 3바이트).
> 절감 추정도 80% → 35%로 정정. 그래도 편당 14만 자 중복 제거.

## 5. [신규·치명] wiki_compile — 비용 미기록 + resume 미적용 (2026-08-04 EP08에서 발견)

`step_1d_wiki_compile`은 **`cost_usd`를 기록하지 않는데 실제로는 claude CLI를 장시간 돌린다.**
EP08 재개 시 이 스텝이 **70분 넘게** 실행되며 claude 프로세스가 CPU 17분+를 소모했다
(이전 편들은 9~19분). 비용 집계표에 아예 안 잡히므로 지금까지의 편당 $9~10 추정은
**과소평가**다.

추가 문제: 이전 실행에서 이미 wiki를 만들었는데도 **resume이 스킵하지 않고 재컴파일**했다.
`step_1_fresh`도 마찬가지로 재실행됨(이쪽은 비 LLM이라 토큰 부담은 없음).
원인 추정 — `pipeline_state.json`에 중간 진행이 저장되지 않아(강제 종료 시 유실),
출력 파일 기반 resume 판정이 wiki_compile에는 적용되지 않는 구조.

### 개선안
- `wiki_compile`에 cost 기록 추가 → 실소모 가시화 (선행 조건)
- 출력 파일(`research/wiki/<topic>/index.md`) 기반 resume 스킵 적용
- 흡수 토픽 수에 비례해 폭증하므로 토픽 상한/증분 컴파일 검토
  (EP08은 삼성전자·갤럭시노트7·한국스마트폰보급률 등 다수 흡수)

## 적용 우선순위

1. **1-A 모드별 SKILL 슬라이싱** — 가장 큰 절감, 리스크 낮음
2. **2 시리즈 preflight 상속** — 편당 30% 절감, 구현 간단
3. **1-B 캐싱 경로 전환** — 절감 크지만 레이스 처리 필요
4. **3 브리프 skip 목록 정리** — 마무리

EP07~12 재개 전에 1-A와 2를 적용하면 남은 6편의 리밋 소모를 절반 이하로 낮출 수 있을 것으로 추정.
