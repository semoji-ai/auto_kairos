# auto_kairos_v3 Research Session Directive

이 문서는 `auto_kairos_v3` 세션이 Stage 1 리서치를 다룰 때 따라야 할 저장 규칙입니다.

## Canonical Root

- 장기 리서치 저장소의 기준 경로는 `KAIROS_VAULT_DIR/02-research` 입니다.
- 현재 NAS 기준 절대경로는 `/Volumes/kairos/kairos_vault/kairos-vault/02-research` 입니다.
- `03-research/` 는 신규 쓰기 경로로 사용하지 않습니다.

## Read First

세션은 아래 문서를 먼저 읽고 시작합니다.

1. `/Volumes/kairos/kairos_vault/kairos-vault/CLAUDE.md`
2. `/Volumes/kairos/kairos_vault/kairos-vault/02-research/llm-wiki-research-policy.md`
3. `/Volumes/kairos/kairos_vault/kairos-vault/02-research/research-vault-lint-checklist.md`
4. `/Volumes/kairos/kairos_vault/kairos-vault/03-research/_deprecated.md`

## Why

- 기존 `topics/*.md` 단일 노트 방식은 Explorer 출력은 남기지만, claim, source, image, timeline이 분리되지 않아 재사용성이 낮았습니다.
- 앞으로는 `llm-wiki` 방식으로 raw source와 compiled wiki를 분리하여, 이후 원고/콘텐츠/검증 에이전트가 동일한 축적 지식을 공유하도록 합니다.

## Required Behavior

Stage 1 리서치 세션은 아래를 모두 수행해야 합니다.

1. 프로젝트 로컬 산출물은 기존대로 유지합니다.
   - `research_report.json`
   - 필요 시 `research_digest.json`
2. 장기 저장은 반드시 `02-research/` 아래에 별도로 남깁니다.
3. `02-research/topics/*.md` 는 더 이상 유일한 저장본이 아닙니다.
   - 역할: 호환성용 compiled topic snapshot
   - canonical memory: `raw/`, `wiki/`, `manifests/`

## Required Layout

```text
02-research/
├── raw/
│   └── <topic_slug>/<run_id>/
│       ├── source_notes/
│       │   └── <source_id>.md
│       ├── image_notes/
│       │   └── <image_id>.md
│       ├── source_manifest.jsonl
│       ├── image_manifest.jsonl
│       └── run_summary.md
├── manifests/
│   └── <topic_slug>/
│       ├── latest_run.txt
│       ├── claims.jsonl
│       └── open_questions.jsonl
├── wiki/
│   └── <topic_slug>/
│       ├── overview.md
│       ├── claims.md
│       ├── entities.md
│       ├── timeline.md
│       ├── images.md
│       └── log.md
└── topics/
    └── <topic_slug>.md
```

## Agent Contract

- `planner`: 조사축, 검색식, 병렬 서브태스크 정의
- `web/paper/literature explorer`: raw source만 수집하고 `source_notes/*.md` 작성
- `image-curator`: 이미지 수집, 라이선스/캡션/연결 claim 기록
- `wiki-maintainer`: raw를 읽고 `wiki/<topic_slug>/` 갱신
- `linter`: 약한 출처, 상충 claim, 빈 구멍, stale note를 기록

중요:

- Explorer는 wiki 페이지를 직접 덮어쓰지 않습니다.
- `wiki-maintainer`만 compiled wiki를 갱신합니다.
- `topics/<topic_slug>.md` 는 wiki의 요약 스냅샷으로 생성합니다.

## Minimum Save Rules

- 각 source는 최소 1개의 정규화 `.md` 노트를 남깁니다.
- 각 source manifest row는 `source_id`, `title`, `url`, `publisher`, `published_at`, `retrieved_at`, `source_type`, `quality`, `run_id`를 포함해야 합니다.
- 각 image manifest row는 `image_id`, `source_url`, `license`, `caption`, `relevance`, `linked_claims`, `run_id`를 포함해야 합니다.
- `claims.jsonl` 의 각 row는 `claim_id`, `statement`, `supporting_sources`, `confidence`, `updated_at`를 포함해야 합니다.

## Compatibility Notes

- 현재 downstream은 여전히 `research_report.json` 을 소비합니다.
- 따라서 `auto_kairos_v3` 는 로컬 workspace artifact를 계속 생성하되, 장기 기억은 반드시 `02-research`에 축적합니다.
- 기존 `02-research/topics/*.md` 노트는 읽기 대상으로 유지하되, 신규 세션은 `raw/ + wiki/ + manifests/`를 우선 구조로 사용합니다.

## Session Start Checklist

- `KAIROS_VAULT_DIR` 가 실제 NAS 볼트를 가리키는지 확인
- 장기 리서치 쓰기 경로를 `02-research/` 로 고정
- `03-research/` 에 새 파일을 쓰지 않도록 주의
- run마다 `raw/<topic_slug>/<run_id>/` 를 새로 생성
- 종료 전 `research-vault-lint-checklist.md` 기준으로 점검

## Copy-Paste Handoff

아래 블록을 새 세션에 그대로 전달하면 됩니다.

```text
Read these first:
1. /Volumes/kairos/kairos_vault/kairos-vault/CLAUDE.md
2. /Volumes/kairos/kairos_vault/kairos-vault/02-research/llm-wiki-research-policy.md
3. /Volumes/kairos/kairos_vault/kairos-vault/02-research/research-vault-lint-checklist.md
4. /Volumes/kairos/kairos_vault/kairos-vault/03-research/_deprecated.md

For Stage 1 research, treat KAIROS_VAULT_DIR/02-research as the canonical long-term research store.
Do not write new long-term research into 03-research.
Keep workspace research_report.json and research_digest.json for pipeline compatibility.
Persist raw source notes, manifests, compiled wiki pages, and topic snapshots under 02-research.
Explorer agents may write raw notes and manifests, but compiled wiki updates must be done by the wiki-maintainer layer.
Before finishing, check /Volumes/kairos/kairos_vault/kairos-vault/02-research/research-vault-lint-checklist.md.
```

## Session Prompt

새 세션에 아래를 전달하면 됩니다.

```text
Read docs/llm-wiki-research-session-directive.md first.
Treat KAIROS_VAULT_DIR/02-research as the canonical long-term research store.
Do not write new long-term research into 03-research.
Keep workspace research_report.json for pipeline compatibility, but persist raw sources, manifests, and compiled wiki pages under 02-research.
```
