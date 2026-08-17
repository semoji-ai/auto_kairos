# M2 — v4 참고 자료 + 자체 구현 계약

> v4는 **참고 전용**. 아래 v4 구조를 참고해 우리 레포에 **자체 구현**할 M2 계약을 확정한다.
> 작성일: 2026-06-04 · 근거: auto_kairos_v4 (읽기 참고), SPEC_v0.2/PRD/ROADMAP

---

## 1. v4 파이프라인 형태 (참고)

```
final_manuscript.md
  → [manuscript-tag]   → final_manuscript.units.json  (문장 단위 + 메타)
  → [scene-decompose]  → scene_specs.json             (units 그룹핑 → 씬)
  → [asset-decide / motion-plan / image-generate ...] → manifest
```

### v4 units 스키마 (참고 — 문장 단위)
`{id, section, text, canonical_subject, characters[], entities[], events[], canonical_date, canonical_place, visual_anchors[], asset_kind_recommended[], unit_role, quote_attribution}`

### v4 scene 스키마 (참고 — 그룹핑된 씬)
`{sceneNumber, chapter, section, title(2~6자), narration, narration_tts(null), unit_ids[], durationFrames(null), characters[], entities[], events[], canonical_date/place, imageAsset{kind,source,query_or_prompt,placement,opacity}, overlays{narration_caption, content[]}, transition{type}}`

### v4 그룹핑 원칙 (참고)
section/chapter 경계 · unit_role 전환점 · 길이 예산(~250자/씬, 상한 ~40초) · primary asset 일관성 · canonical_subject 변화.

---

## 2. M2 자체 구현 계약 (우리 버전)

### 2.1 범위 결정
- **M2 = `manuscript → scenes` 단일 codex 스킬.** v4의 2단계(units→scenes)를 합쳐, 첫 마일스톤은 씬 목록 산출까지 직행.
- units 중간층 / asset_plan 머지 / overlays content 풍부화는 **후속 마일스톤**(M3+)에서 추가.
- 이유: "작동 우선" + 패널 씬 목록 데모 + codex `--output-schema` 단일 호출로 단순.

### 2.2 자체 프로젝트 스토어 (v4 참고, 단순화)
```
projects/{project_id}/
  plan.md              # 기획 (제목/톤/챕터) — 선택
  final_manuscript.md  # 원고 (입력)
  scenes.json          # ← M2 산출물 (씬 목록)
  pd_notebook.md       # PD 대화/결정 로그 — 선택
  logs/                # job 로그
```
project_id = 짧은 해시(예: 8자). `_index.md`로 목록 관리(v4 참고).

### 2.3 scenes.json 스키마 (M2 — 단순화)
```json
{
  "version": "adobe-0.1",
  "project_id": "<id>",
  "topic": "<plan title 또는 추론>",
  "total_scenes": 0,
  "scenes": [
    {
      "sceneNumber": 1,
      "section": "<섹션/챕터명 또는 null>",
      "title": "<2~6자 씬 제목>",
      "narration": "<해당 씬 원고 텍스트(원문 substring)>",
      "characters": ["<등장 인물>"],
      "visual_summary": "<한 줄 화면 설명>",
      "image_prompt": "<생성/검색용 시각 단서, 한국어>",
      "duration_estimate_sec": 0
    }
  ]
}
```
- **narration 불변**: 원고 substring(재작성 금지) — v3/v4 공통 규칙 계승.
- title/visual_summary/image_prompt/characters는 codex가 판단.
- duration_estimate_sec = 한국어 글자수 기반 추정(예: 글자/6).
- M3에서 imageAsset/overlays, M4에서 motion/transition 확장.

### 2.4 scene-decompose 스킬 (자체, codex 구동)
- 위치: `skills/scene-decompose/SKILL.md` (우리 레포)
- 입력: `final_manuscript.md` (+ 선택 `plan.md`)
- 출력: `scenes.json`
- 구동: 백엔드가 `codex exec --output-schema <scenes.schema.json> -o <scenes.json> "<스킬 프롬프트 + 원고>"`
- 그룹핑 기준(v4 참고): 의미 전환 · 길이 예산(~250자/씬) · 인물(canonical_subject) 변화 · 섹션 경계.

### 2.5 백엔드 API (M2 신규)
| Endpoint | 용도 |
|----------|------|
| `GET /api/projects` | projects/ 스캔 → {project_id, title, status, updated_at, artifacts} |
| `POST /api/projects/load` | 프로젝트 상세(보유 아티팩트, 다음 작업) |
| `POST /api/skills/run` | skill_name=scene-decompose 등 → codex exec 래퍼, job_id 반환 |
| `GET /api/jobs/{id}` | 상태/로그/스트리밍 이벤트/artifact_paths |

### 2.6 Codex Runner 계약 (대화형)
- 프로젝트별 **session id 유지**: 첫 호출 후 session id 저장 → 후속은 `codex exec resume <session_id> "<후속>"`.
- **스트리밍**: `codex exec --json` JSONL 이벤트를 job 로그로 적재 → `/api/jobs/{id}`가 패널에 전달.
- **구조화 산출**: 스킬이 파일 산출(scenes.json) 시 `--output-schema`로 형식 강제 + `-o`로 최종 메시지 캡처.

### 2.7 패널 (M2)
- Project 탭: 목록 / 선택 / 아티팩트 상태
- PD Chat: 다회차 + 스트리밍, "씬 분해" 실행 → scenes.json → **씬 목록 렌더**

### 2.8 M2 exit 기준
실제 프로젝트(final_manuscript.md 보유) 선택 → PD Chat "씬 분해" → `scenes.json` 생성 + 패널에 씬 목록(번호/제목/narration) 표시. 후속 지시("3번 씬 더 잘게")가 같은 세션 맥락에서 동작.

---

## 3. 비범위 (M2)
units 중간층, asset_plan, overlays content 풍부화, motion/transition, 이미지 생성(M3), 승인 게이트(M4).
