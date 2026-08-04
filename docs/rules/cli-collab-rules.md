# Codex / Gemini CLI 협업 규칙 (LG 브랜드백과 프로젝트에서 축적)

> 되풀이 방지용. 새 문제/해결이 나올 때마다 이 문서에 추가할 것.

## Codex CLI (codex-cli 0.144.x)

- **`--search` 플래그는 반드시 `exec` 앞에**: `codex --search exec "프롬프트"` — `codex exec --search`는 exit 2 (unexpected argument). (2026-08-03, 4개 리서치 잡 전부 실패 후 재실행으로 확인)
- 장문 프롬프트는 `"$(cat <<'EOF' ... EOF)"` 히어독으로 전달 — 쉘 이스케이프 사고 방지.
- **백그라운드(비TTY) 실행 시 반드시 `</dev/null` 붙일 것** — 안 하면 "Reading additional input from stdin..."으로 무한 대기 후 killed. (2026-08-03, 4개 잡 전부 행 걸림)
- 리서치 위임 시 프롬프트 끝에 **"최종 응답으로 보고서 전문을 출력하세요"** 를 명시 — 안 하면 요약만 출력하고 파일에 본문이 안 남는 경우가 있음. stdout 리다이렉트(`> file.md 2> file.err`)로 수집.
- codex stdout에는 세션 헤더/도구 로그가 섞여 나올 수 있음 — 수집 후 보고서 본문만 남기는 후처리 필요 여부를 항상 확인.
- codex 샌드박스는 NAS 심링크에 쓰기 불가 (기존 확인) — 산출물은 로컬 경로로만.

## Gemini CLI (0.52.x)

- 비대화 실행: `gemini -p "프롬프트"` (stdin도 가능).
- **무료 OAuth 티어 인증 폐기됨** (IneligibleTierError, Antigravity 이전 요구). `--auth-type` 플래그는 0.52에 존재하지 않음. 해결: `~/.gemini/settings.json`의 `security.auth.selectedType`을 `"gemini-api-key"`로 변경 + `.env`의 `GEMINI_API_KEY` export 후 실행. GEMINI_API_KEY만 export해도 settings가 oauth-personal이면 무시됨. (2026-08-03 확인)
- 영상 이해 강점 — 유튜브 영상 분석/벤치마크는 gemini에 위임.
- **API 키는 `.env`의 `GOOGLE_API_KEY`를 `GEMINI_API_KEY`로 export해서 사용** — `GEMINI_API_KEY`라는 이름의 키는 `.env.example`에만 있음(.env에는 없음). `.env.example`에 실제 키가 노출돼 있는 것도 발견 — 정리 필요 (개선사항 참조).
- gemini 웹 검색 결과의 수치·URL은 환각 가능성 있음 — 조회수/URL 등 원고에 인용할 값은 반드시 교차 검증.

## 공통 위임 원칙

- 위임 잡은 **background로 병렬 실행**, stdout/stderr를 프로젝트 research 디렉토리에 파일로 남김.
- 실패 시 err 파일 먼저 확인 — 플래그 오류 vs 인증 오류 vs 타임아웃 구분.
- 품질 검수는 Claude가 담당: 수치·실명·출처 URL이 실제 포함됐는지, 날조 징후(출처 없는 구체 수치) 스팟체크.

## auto_kairos_v3 개선 필요 사항 (발견 시 추가)

- **v4-bridge 브랜치에서 v3 리서치→원고 체인을 돌리려면 `ENABLE_LEGACY_V3=1` 필수** — 없으면 step_1/step_2 전부 legacy_only 스킵 후 step_2에서 실패하는데, series_runner는 이를 "EP 완료"처럼 넘겨버림. 프리플라이트 비용(~$2/편)만 태우고 원고는 안 나옴. (2026-08-04, 10편 헛돈 후 발견 — 메모리에 이미 있던 규칙을 세션에서 미적용한 사례. 개선: runner가 스텝 전부 스킵되면 시작 전에 명시적 에러를 내야 함) — 시스템 `python3`은 3.9라 `type | None` 문법에서 전부 실패. series_runner가 에피소드 실패를 삼키고 exit 0으로 끝나는 것도 문제(실패 시 non-zero로 나가거나 fail-fast 옵션 필요).

- **`.env.example`에 실제 API 키가 커밋돼 있음** (`GEMINI_API_KEY=AIzaSy...`) — 플레이스홀더로 교체하고 키 로테이션 검토 필요.
- 환경변수 명명 불일치: 코드/문서는 `GOOGLE_API_KEY`, gemini CLI는 `GEMINI_API_KEY` 요구 — `.env`에 두 이름 모두 정의해 두는 것이 안전.
- **fresh_collector의 image_manifest.jsonl이 항상 0줄** — 이미지 링크 수집이 구현만 있고 실제로 채워지지 않음 (반도체 파일럿·LG편 모두 확인). 이미지/영상 자료 수집은 scene_specs 이후 `scripts/scene_video_scan.py` + 수동 패스에 의존 중 → Stage 1에서 자료 후보 링크를 함께 쌓는 레인 필요.
- **컨텍스트 낭비 감사 결과 → `docs/token-waste-audit.md`** (2026-08-04). 최대 낭비: script-director SKILL.md 69KB를 챕터 병렬 호출마다 전문 재주입(편당 ~27만 토큰 중복), 캐싱 경로 미사용. 차순위: 시리즈 모드에서 편별 preflight 중복(편당 ~$3).
- **토큰 비용 구조 (LG편 실측, 2026-08-04)**: 완성 편당 ~$9-10(Claude CLI 부분). 최종원고 $2.6-3.5 > 브리프래칫(step_0d) $1.5-2.9 > 팩트체크 ~$1. **preflight가 편당 ~$3(30%)** — 시리즈물은 기획이 series_plan에 이미 있으므로 편별 인터뷰→래칫 중복. 개선: 시리즈 모드 preflight 경량화(브리프 상속). 또한 step_2 씬분할·wiki_compile은 cost_usd 미기록이라 실소모는 로그의 1.5-2배로 추정(codex 토큰 별도).
- 장편 시리즈(멀티 에피소드) 워크플로가 1급 개념이 아님 — `output/series/`에 수동 JSON으로만 존재. 시리즈 기획 → 에피소드별 프로젝트 생성 → 공유 리서치 풀 재사용 구조가 필요 (LG편에서 프로토타입 후 일반화)
