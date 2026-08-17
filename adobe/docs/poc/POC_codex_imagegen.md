# PoC — codex 빌트인 image_gen (M3b/M3c 전제)

일시: 2026-06-05

## 결론: ✅ codex 단일 인증으로 이미지 생성·저장 가능

| 항목 | 결과 |
|------|------|
| codex exec가 image_gen 도구 호출 | ✅ (OPENAI_API_KEY 불필요, codex 인증) |
| 실제 PNG 생성 | ✅ (1254×1254 / 1024×1024 RGB) |
| 프로젝트 폴더 직접 저장 | ✅ `-s workspace-write` 필요 |
| rate limit | ⚠️ 간헐적 — 재시도/백오프 필요 |

## 핵심 메커니즘 (M3b imagegen 모듈)
```bash
codex exec --skip-git-repo-check -s workspace-write -o <log> - <<'PROMPT'
image_gen 도구로 이미지 생성해 <상대경로>.png 로 저장. 내용: <프롬프트>. 저장되면 OK만 답.
PROMPT
# cwd = projects/{id} → 이미지가 cwd에 저장됨
```
- **read-only 샌드박스(기본)면 저장 실패** → 반드시 `-s workspace-write`.
- 폴백: 저장 실패 시 `~/.codex/generated_images/<session>/ig_*.png`에 원본 존재 → 백엔드가 복사.
- rate limit 대비: 재시도/백오프 + 동시 생성 수 제한(1~2).

## M3b 설계 반영
- imagegen 백엔드 모듈: `codex exec -s workspace-write` (cwd=proj_dir), 출력 `images/ref_{n}.png`.
- run_skill에 sandbox 옵션 파라미터 추가 필요(현재 read-only 고정).
