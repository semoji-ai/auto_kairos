# PoC — Codex Runner (decision #6/#7 검증)

> 목적: 스펙 v0.2의 전제 "이미지·LLM 모두 Codex 인증 단일 + 백엔드가 codex를 드라이브"가 실제로 되는지 터미널에서 검증.
> 일시: 2026-06-04 · 머신: darwin, codex-cli 0.136.0

## 결론 요약

| 항목 | 결과 |
|------|------|
| 공식 "Codex Python SDK" (pip) | ❌ **없음** — `openai-codex`/`codex-sdk` 미존재, PyPI `codex`는 "comic archive web server"(무관) |
| codex 비대화 실행 (`codex exec`) | ✅ **검증됨** — 구조화 출력 캡처 가능 |
| codex 인증으로 LLM 호출 | ✅ 라이브 왕복 성공 (API 키 불필요) |
| codex imagegen (codex 인증) | ✅ **track record로 실증** (config.toml에 auto-kairos-codex-imagegen 프로젝트 다수) + v4 스크립트 존재 |
| 기본 모델 | `gpt-5.5` (config.toml) |

## 1. 공식 Python SDK 부재 → `codex exec`가 통합 경로

- `pip index versions openai-codex` / `codex-sdk` → 없음
- PyPI `codex 1.12.7` = "A comic archive web server" (AJ Slater, 무관) → **설치 금지**
- 결론: 백엔드 Codex Runner는 **`codex exec` CLI 서브프로세스** 또는 **`codex mcp-server`(stdio)** 로 드라이브. pip SDK 아님.

## 2. `codex exec` 구조화 출력 (Codex Runner에 최적)

```
codex exec [PROMPT|stdin] \
  --skip-git-repo-check \
  -o, --output-last-message <FILE>   # 최종 답변 파일 캡처
  --json                              # 이벤트 JSONL stdout
  --output-schema <FILE>              # 최종 응답 JSON Schema 강제
  -i, --image <FILE>...               # 입력 이미지 첨부
  -m, --model <MODEL>
```

→ 백엔드는 `codex exec ... -o out.txt` (또는 `--output-schema`)로 **결정적 결과 회수** 가능. job 단위 실행/로그/재시도에 적합.

## 3. 라이브 왕복 검증 (실제 실행)

```bash
codex exec --skip-git-repo-check -o last.txt "Reply with exactly one word: PONG"
# exit=0, last.txt = "PONG", model=gpt-5.5, tokens=11,648, OPENAI_API_KEY 불필요
```

→ codex 인증만으로 LLM 호출 + 구조화 출력 캡처 = **Codex Runner 핵심 메커니즘 실증.**

## 4. 이미지 생성 경로 (decision #6)

- `~/.codex/config.toml`에 `auto-kairos-codex-imagegen-*` / `auto-kairos-codex-transparent-asset-*` 프로젝트 항목 다수 → codex 경유 imagegen이 이미 반복 실행된 이력.
- auto_kairos_v4 `scripts/generate_images_codex.py` + `image_gen.py`(스타일/캐릭터 ref 첨부 패턴) 존재.
- 라이브 1장 생성 확인은 크레딧 소비가 커서 **선택 검증**으로 남김(필요 시 1회 스모크).

## 스펙 반영 (decision #7 정정)

> ~~Codex Python SDK 우선~~ → **`codex exec`(구조화 출력) 주력 + `codex mcp-server`/app-server(상주·멀티스텝)**. pip SDK는 존재하지 않음.

## 남은 PoC (AE 환경 필요)

- #3 CEP 익스텐션 ↔ localhost 백엔드 + 백엔드 자동 spawn
- #4 ae_manifest.json → 최소 모션 JSX → AE 컴프 1씬 왕복
  → CEP 익스텐션 스캐폴드 + AE 실행 필요 (다음 단계)
