# motion — 세모지 모션 도감 원본

구 `~/Projects/semoji-motion` 의 코드와 분석 자료를 옮긴 독립 하위 프로젝트입니다.
세모지 스타일 모션그래픽의 Remotion 구현, 기법 도감(343항목) 빌더, 레퍼런스 분석 노트가 들어 있습니다.
AE 패널(`adobe/`)은 여기서 만든 도감을 `adobe/scripts/sync_dogam.py` 로 가져가 씁니다.

## 구성

| 경로 | 내용 |
|---|---|
| `video/` | Remotion 4.0.436 + React 19 npm 프로젝트. `remotion/`(React 18)과 **의존성을 합치지 않습니다** |
| `video/src/lib`, `gallery`, `fx.tsx` | 기법 구현과 갤러리 데모 |
| `video/src/explainer_demo/` | 설명형 편집 레퍼런스 스타일 1분 테스트 영상(컴포지션 `ExplainerDemo`) |
| `video/src/data/` | 공용 지도 데이터(Natural Earth 50m 육지·해안선 등) |
| `dogam/` | 도감 빌더(`build_techniques.py`, `build_viewer.py`, `export_params.sh`, `render_previews.py`)와 산출물(`techniques.json`, `params.json`, `index.html`) — [dogam/README.md](dogam/README.md) |
| `explainer_demo/` | 테스트 영상의 원고·TTS·타임라인·에셋 처리 스크립트 |
| `assets/` | 원화·키트 생성 스크립트와 프롬프트 기록(이미지 원본은 NAS) |
| `ref*/`, `ref_story/` | 레퍼런스 분석 노트·측정 스크립트 — 출처와 원본 위치는 [REFERENCES.md](REFERENCES.md) |
| `*.py`, `script.json` | 짜장면편 파일럿용 원고·TTS·레이어 분리·타임라인 스크립트 |
| `rig-kit/` | 세모지 2D 리깅 캐릭터 엔진(순수 JS Canvas → MP4). 나레이션 문장 → 시간 슬롯 → 캐릭터 연기 장면. 캐릭터 13명·소품 12종·검사 도구 — [rig-kit/README.md](rig-kit/README.md). `semoji-rig-animation` 스킬이 쓰는 키트의 원본 |

## 저장소 밖(NAS)에 있는 것

미디어는 커밋하지 않습니다(`.gitignore`). 원본은 NAS 백업 `/Volumes/jleavens/007_AI_Projects/semoji-motion_backup_20261007` 에 있습니다.

- `video/public` 미디어(폰트·이미지·오디오·키트 PNG, 약 197MB): `bash motion/video/scripts/fetch_public.sh` 로 받아 옵니다. 다른 위치는 `SEMOJI_NAS=…` 로 지정합니다. JSON(리그·소품 목록·VO 정렬·지도)과 출처 메모만 저장소에 있습니다.
- 도감 미리보기(약 92MB): `DOGAM_PREVIEWS_DIR` → `motion/dogam/previews`(로컬 캐시·링크) → NAS 순으로 찾습니다. AE 패널용 12개는 `adobe/data/semoji-motion/` 에 번들돼 있습니다.
- 레퍼런스 원본 영상·프레임·자막, AE 실험 파일, 렌더 결과(`video/out`): [REFERENCES.md](REFERENCES.md)

## 자주 쓰는 명령

```bash
cd motion/video && npm ci && npx tsc --noEmit -p .   # 타입 검사
bash motion/video/scripts/fetch_public.sh             # 렌더·Studio 전에 미디어 받기
cd motion/video && npx remotion studio                # Studio (params 폴더에 기법별 슬라이더)
python3 motion/dogam/build_techniques.py              # 도감 재생성 + 검증("검증 통과")
bash motion/dogam/export_params.sh                    # 기법 변수 스키마 → dogam/params.json
python3 motion/dogam/build_viewer.py                  # dogam/index.html
python3 adobe/scripts/sync_dogam.py --check           # AE registry 정합성
```

도감을 바꾼 뒤에는 `adobe/data/semoji-motion/dogam/techniques.json`·`params.json` 번들도 같은 내용으로 갱신해야 AE 백엔드가 새 카탈로그를 봅니다.
