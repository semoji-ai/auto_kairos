# 이미지 생성 후 업스케일 단계 설계

날짜: 2026-07-21 / 브랜치: v4-bridge / 승인: 사용자 대화

## 목표

generate 이미지(codex·FAL 공통) 성공 직후 Upscayl 로컬 CLI로 업스케일하고, 결과를 새 버전 파일로 등록해 selected 전환한다. auto_kairos_adobe `backend/upscale.py` 패턴 이식.

## 구성

1. **`auto_agent/tools/upscale.py`**
   - `upscayl_available() -> bool` — env `UPSCAYL_BIN` 우선, 기본 `~/.local/share/upscayl/bin/upscayl-bin`, `shutil.which` 폴백.
   - `upscale_image(src_png, out_png=None, *, content="illustration", model=None, scale=2, timeout=600) -> dict` — `{status, path, model, scale}` 또는 `{status:"failed", error}`. 모델 자동 선택: illustration=digital-art-4x, photo=upscayl-standard-4x, photo_detail=remacri-4x, 미설치 시 설치분 폴백. env `UPSCAYL_MODELS` (기본 `~/.local/share/upscayl/models`).
2. **`image_batch_module.py` 통합**
   - 씬/캐릭터 generate 성공 후처리 직후 업스케일. 씬: `<stem>_up.png` 별도 파일 생성 → `image_assets`에 버전 등록 + selected 전환. 캐릭터: `characters/{id}_up.png` 생성 후 참조 갱신 없이 씬과 동일하게 원본 유지(캐릭터는 레퍼런스용이라 업스케일 대상에서 제외해도 무방 — 구현 단순화를 위해 **씬 generate만 업스케일**).
   - 실행 시점: 생성 배치 완료 후 **순차 일괄** (GPU 자원 경합 방지, 생성 병렬과 분리).
   - 실패 시 비차단: warn 로그 + 원본 selected 유지. summary에 `scenes_upscaled` 카운트.
3. **토글**: env `IMAGE_UPSCALE=1|0` 기본 1. upscayl-bin 부재 시 자동 스킵 + warn. `.env.example` 문서화.
4. **불변 규칙**: 파일 삭제 금지(원본 유지), 버전 등록은 기존 `image_assets` 계약 사용.

## 범위 제외

- search 이미지(실사) 업스케일 — 후속 (photo 모델).
- 캐릭터 이미지 업스케일 — 후속.
- 429/병렬 업스케일 — 순차로 충분.

## 테스트

- upscale.py 단위(mock subprocess): 모델 선택, 부재 처리, 실패 반환.
- image_batch 통합(mock upscale_image): 성공 시 버전 등록+selected 전환, 실패 시 비차단, IMAGE_UPSCALE=0 스킵.
- 실전 스모크: 기존 생성 PNG 1장 실제 업스케일 → 해상도 2배 확인.
