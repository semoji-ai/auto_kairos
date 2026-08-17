# auto_kairos_adobe 확장·하드닝 감사 보고서 (2026-06-12)

> 백그라운드 감사 에이전트 산출물. 코드 근거 기반.

## 1. 구조 감사

### backend/
- **router.py 단일 dispatch (517줄)** — 심각도 중. 라우트 테이블(dict) + 프로젝트 검증 데코레이터로 전환 권장(`proj_dir.is_dir()` 20곳 복붙 제거).
- **jobs 동기 실행** — 심각도 상(체감 1순위). 모든 핸들러가 요청 스레드에서 끝까지 동기 실행 → codex 수십 초~수 분 작업에 패널 fetch 블로킹. `GET /api/jobs/{id}` 폴링이 이미 있으나 사장됨. **threading.Thread로 비동기화 + 즉시 {job_id} 반환 + 기존 폴링 활용.**
- **scenes.json 동시 쓰기** — 심각도 상. read→modify→write 전체 재기록, 비동기화 시 경합. **프로젝트별 threading.Lock 필수**(비동기화와 같은 PR).
- **에러 처리** — handle_request 최상위 try/except 없음 → 500 + {"error"} 한 겹 추가. `_run_codex_image` 실패 사유가 "rate_limit_or_no_file" 하나로 뭉개짐 → 분류 필요.
- **경로 하드코딩** — main.js `BACKEND`/`MANIFEST`/`renderScenes()` 절대경로 머신 의존. `/health`에 root 포함시켜 해소.

### cep/js
- **문자열 HTML 조립** — 심각도 상(이중+ NaN 사고 이력). `_esc`가 main.js에 없음 → 제목/이름에 따옴표 들어가면 속성 깨짐. `_esc` 공용화 + renderRow는 createElement 헬퍼 전환 권장. `loadSheet()` 전체 재렌더 → 행 단위 `refreshRow(n)`으로 포커스 손실/스크롤 점프 해소.
- **전역 var 공유** — `window.AK` 네임스페이스로 정리(ES 모듈 전환은 비용 대비 이득 낮음 — 래칫).

### jsx
- **eval 파싱** — subtitle(나레이션 원문)에 특수 문자열 시 깨질 수 있음 → json2.js 폴리필 + JSON.parse.
- **자막 좌표 실버그** — subtitle 위치가 [W/2, H*0.88](1920/1080 기준)인데 컴프는 cw×ch → **이미지 크기 다르면 자막 빗나감. cw/ch로 수정 필요.**
- evalScript(jsx+call) 매번 전체 주입 → 모션 단계 전 $.evalFile/함수 라이브러리 방식 검토.

## 2. 레이어 파이프라인 개선점
- **(a) 크기 정합** — ✅ 2026-06-12 normalize_layer_size로 해결(c4ec227). 종횡비 자체가 다르면 failed_geometry 처리(추가 여지).
- **(b) 크로마 품질** — 이진 알파 → 마젠타 거리 기반 소프트 알파 + erode/feather. 보라/분홍 요소 뚫림 주의. `transparent_ratio` 반환값을 아무도 안 봄 = 무료 QC 신호.
- **(c) QC 루프** — 1) 정량 게이트: transparent_ratio <0.05(지시 무시) 또는 >0.98(요소 없음) → 자동 재시도. 2) LLM 시각 검수(옵션 플래그): 합성 vs 원본 비교 → 실패 레이어만 재생성. 배경의 "제거 대상 잔존 → 이중 등장"은 2)로만 잡힘.
- **(d) 재시도 정책** — 실패 분류(rate_limit/no_file/bad_geometry/bad_chroma) + geometry/chroma는 피드백 한 줄 추가해 1회 재생성.
- **(e)** 구 generate_layer(bg/char 2분할)와 신 split_scene_to_elements 공존 — `/api/layers/generate`는 구버전. deprecated 표시.

## 3. 모션 단계 설계 스케치
- `backend/motion.py` + `schemas/motion_plan.schema.json` — **프리셋 enum만 허용**(slide_in/fade_in/pop/drift/bob/shake/zoom_emphasis/exit_fade + camera: slow_zoom_in/out/pan). LLM이 임의 키프레임 좌표를 내지 않게 — 수치는 jsx가 결정적으로 계산(assistant 바운디드 카탈로그와 동일 안전 모델).
- 입력: narration + duration(TTS) + 레이어 목록. 출력: 씬별 `motion_{sid}.json`(versioned).
- manifest에 moves/camera 병합(하위호환) → jsx `applyMoves(il, moves, dur, cw, ch)` — 기존 fade 키프레임 패턴의 연장. camera는 Final 컴프의 씬 레이어 Scale/Position 키프레임.
- 라우터 `/api/scenes/motion` + assistant 카탈로그 `plan_motion` + 시트 버튼.
- **전제: 레이어 크기 정합 보장 후 착수.** start/duration 초 단위(v3는 frame — 변환 주의).

## 4. 렌더큐 + v3 연결
- **렌더**: 1차 jsx RenderQueue API(`akQueueRender(compName, outPath, omTemplate)` — OM 템플릿 이름 manifest에 기재, render()는 AE UI 블로킹 안내). 무인 배치 단계에서 aerender(.aep 저장 후 subprocess, 잡 폴링과 자연 결합). 택일 아닌 단계.
- **v3 임포트**: `backend/v3_import.py` + `POST /api/projects/import-v3 {output_dir}`(전체 경로 — uuid 접두사라 slug 조합 금지).
  - 매핑: sceneNumber/title/narration 동일, narration_tts 보존(tts.py 우선 사용 1줄), imageAsset.prompt→image_prompt(search면 query+`_source` 보존), durationFrames→duration_estimate_sec(/30), visualization 요약→visual_summary, sceneId 신규 발급, final_manuscript.md 복사, 기존 images/scene_XXX → storyboard/ 복사+imageRef.
  - 구(visualization.creative 중첩)/신(플랫) 스키마 양쪽 허용.

## 5. 우선순위 로드맵
| 순서 | 항목 | 근거 |
|---|---|---|
| 1 | 하드닝 A: 잡 비동기화 + scenes.json 락 + 최상위 예외 | 모든 장시간 작업의 토대, /api/jobs 폴링 기존재 |
| 2 | 레이어: 소프트 크로마 → 실패 분류·재시도 → 정량 QC 게이트 (크기 정합은 완료) | 모션의 전제. LLM 시각 검수는 옵션 후순위 |
| 3 | 하드닝 B: main.js _esc + 행 단위 재렌더 + jsx JSON.parse + 자막 좌표 버그 + 경로 하드코딩 | 사고 이력 계열 재발 방지, 2와 병렬 |
| 4 | 모션 단계 | 2 완료 후. 프리셋 enum이라 리스크 바운디드 |
| 5 | 렌더큐 jsx | 작아서 4와 병렬 가능 |
| 6 | v3 임포트 | 독립적이나 대형 프로젝트 실사용엔 1·2 선행 필요 |
| 이후 | aerender 무인 배치, LLM 시각 QC, 라우트 테이블 | 규모 커진 뒤 |

**핵심: "비동기 잡 + 레이어 크기 정합"이 모든 확장의 병목.** 이 둘 해결 후 모션·렌더·v3 연결은 기존 패턴(스키마 JSON → 결정적 적용)의 반복으로 안전하게 적층.
