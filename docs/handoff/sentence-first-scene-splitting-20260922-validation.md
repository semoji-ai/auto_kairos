# 문장 우선 씬분할 — 노트북 적용 검증

2026-09-22. 다운로드 폴더의 동일 날짜 핸드오프 문서와 6파일 패치를 검토하고,
최신 `origin/main`의 `b8fe846bc4b18d6288fdb998d80dc71bc68a40d0`에 적용했다.
브랜치: `feat/sentence-first-scene-splitting-20260922`.
기존 노트북 작업 폴더의 미커밋 마이디어·Jev 작업은 변경하지 않았다.

## 핸드오프의 미검증 항목 처리

- 신규 생성·기존 씬·`--only step_2`가 동일한 문장 목록 경로를 사용한다. 기존 씬이 원고와 일치하면 재개 시 보존한다. 불일치하면 중단하며 명시적 `--force` 재분할 때 이전 JSON과 프로젝트 메타데이터를 보존한다.
- 챕터 제목이 없는 원고도 chapter 0으로 처리한다. `Ch`, `Chapter`, `챕터`, 다단계/들여쓴 Markdown 제목을 검사했다.
- 여러 줄의 한 문장, 닫는 인용부호, 소수점, 강조 표기, 블록 앞뒤 제작 주석을 검사했다. 닫히지 않은 HTML 주석은 실패한다.
- chars/caption/기타 제작 메모를 모델에 전달한다. 블록 caption은 첫 문장의 시작에만 기본 표시하며 분할된 모든 씬에 자동 복제하지 않는다.
- `sourceSentences` 외에 `sourceSpans`로 문장 내부 분할을 지원한다. 유니코드 문자 인덱스 `[start, end)`의 누락·중복·겹침·순서·범위·챕터를 검증한다. narration은 코드가 원문에서 조립한다.
- 모델이 쓴 narration/characters/source mapping이 검증된 원문·캐스팅을 덮어쓰지 못한다. 연출 infoStructure/beat/keyVisual은 보존한다. 하위 cuts는 거부한다.
- 병합 결과를 저장하기 전에 전체 원문을 대조한다. 일부 챕터 실패를 legacy 모드에서도 부분 성공으로 저장하지 않는다.
- 목록이 있는 프로젝트는 후속 씬 소비/수정 단계 및 Stage 3/4 진입 전후에 보존 검사를 한다. 사후 팩트 수정도 다시 검사한다. 훼손은 FATAL로 비차단 리뷰 설정과 관계없이 단계 및 다음 phase를 중단한다.
- 정당한 팩트 수정은 canonical 원고부터 반영하고 목록·씬을 재생성해야 한다. 원문 오류를 무조건 자동 수용하는 동기화는 하지 않는다.
- Remotion은 별도 작업 공간에서 원본 73파일만 있었으며 복사본에만 있는 파일/수정은 없었다. 동기화 후 `--check` 통과. 원래 작업 공간의 Remotion은 수정하지 않았다.

## 자동 테스트

관련 회귀 명령:

```bash
python -m pytest -q tests/test_scene_coverage.py tests/test_agent_runner.py tests/test_chapter_prompt_caching.py tests/test_pipeline_v4bridge_config.py tests/test_execution.py tests/test_codex_provider_routing.py
python -m py_compile auto_agent/orchestrator/runner.py auto_agent/modules/scene_coverage_module.py
git diff --check
python scripts/sync_remotion_src.py --check
```

최종 관련 회귀 테스트: **108 passed**. 컴파일·diff 공백 검사·Remotion 동기화 검사 통과.
전체 suite 최종 실행: **668 passed, 5 failed, 2 skipped**.
아래 5개는 수정 전 기준 커밋을 별도 임시 디렉토리에 풀어 같은 테스트를 실행했을 때도 모두 실패했다(25 passed, 5 failed).

- `tests/dashboard/test_route_v4_context.py::test_research_tab_includes_v4_section_when_files_exist`
- `tests/dashboard/test_route_v4_context.py::test_manuscript_tab_includes_v4_section`
- `tests/dashboard/test_route_v4_context.py::test_research_tab_no_v4_section_when_files_missing`
- `tests/test_video_tracks.py::test_adobe_specs_drift_blocks_track_not_silently_retargets`
- `tests/test_video_tracks.py::test_adobe_aliases_use_same_clock`

앞 3개는 `sqlite3.OperationalError: no such table: projects`, 뒤 2개는 `ModuleNotFoundError: backend`이다. 이 변경에서 무관한 DB/Adobe 코드나 테스트 설정을 고치지 않았다.

## 실제 CLI 검증

프로덕션 `_execute_manuscript_chapter` → `_run_selected_cli` → CLI 어댑터를 사용했다.
각각 독립 임시 프로젝트에 두 문장 원고를 준비하고 현재 chapters 스킬과 배분 프롬프트를 전달했다.
DB/이미지/영상 생성은 실행하지 않았으며 LG·마이디어 원본에서 테스트하지 않았다.

| 제공자/모델 | 파일 출력·파싱 | 결과 | 원문 보존 | CLI 시간 |
|---|---|---|---|---|
| Claude / claude-opus-5 | 통과 | 2문장 → 2씬 | 통과 | 66.35초 |
| Codex / gpt-5.6-sol | 통과 | 2문장 → 2씬 | 통과 | 117.74초 |

두 모델 모두 sourceSentences와 splitReason을 반환하고 지정한 임시 JSON을 썼다.
원본 원고는 그대로였다. 비용 로그는 Claude $1.56094, Codex 금액 미제공(`cost_known=false`)이며 Codex를 무료 비용으로 해석하지 않는다.
실제 출력에서 발견한 caption 반복은 이후 회귀 테스트로 재현·수정했다.
실제 제공자 오류 경로는 CLI를 실패 응답으로 대체한 자동 테스트에서 폴백 없이 실패하는지 검사했다.

## 남은 범위

- 실제 CLI 검증은 작은 두 문장 fixture이다. 장편 전체의 연출 품질, 실제 모델의 문장 내부 offset 선택, 전체 Stage 1→4 제작/렌더링은 검증하지 않았다.
- 문장 파서는 표기 기반이다. 모든 언어의 약어/인용 문법을 이해하는 언어학적 파서는 아니다. 최종 원문 보존 검사가 경계 판단과 별도로 동작한다.
- 제목과 `---` 사이 제작 주석은 블록 범위이다. 범위가 다른 인물·caption은 원고에 경계를 명시해야 한다.
- 기존 프로젝트는 자동 재분할하지 않았다. main 병합 및 기존 작업 폴더 갱신은 별도 통합 작업이다.
