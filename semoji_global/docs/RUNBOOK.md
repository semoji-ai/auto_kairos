# 세모지 글로벌화 런북 (계획 1 범위)

## 0. 준비
- `caffeinate -d -u -t 21600 &` (AE 작업 중 화면보호기 방지 — 켜지면 AE 대화상자를 못 닫음)
- 디스크 여유 10GB 이상 (`df -h /System/Volumes/Data`). render.sh/run.sh가 끝날 때 AE 디스크 캐시를 비운다.
- 테스트: `python3 -m pytest -q`

## 1. 편 가져오기 (B209 기준, 완료)
1. 기준본: `yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 -o episodes/<EP>/yt_master.mp4 <url>`
2. NAS aep 그래프·인벤토리: `scripts/ae/graph.jsx`(graph_job.json {aep: NAS 경로, out}) → `graph_nas.json`, `scripts/ae/inventory_full.jsx` → `inventory_nas.json` (실행은 `scripts/ae/run.sh <jsx 절대경로>`)
3. 실제 쓰이는 파일만 복사: `python3 -I scripts/reach.py graph_nas.json <파트 컴프 id> 0 <길이>` → 목록의 파일을 `episodes/<EP>/src/`로(NFC, 편 폴더 기준 상대경로 유지)
4. `prep_main.jsx`(파트 컴프 고유 이름 MAIN_*) → `fontmap.jsx`(SBAggroM→OTSBAggroM 등) → `src/<EP>_main_ko.aep`
5. 프리미어: `python3 scripts/parse_prproj.py <prproj> > episodes/<EP>/pr_timeline.json`
6. 재구성 검증: 파트 렌더(render.sh) → `scripts/assemble_pr.py` → `scripts/compare_video.py`(유튜브·NAS 최종본). 연속 차이가 있으면 컷·패치·누락을 찾아 config에 반영.

## 2. 마스터
- `episodes/<EP>/master_config.json` 작성(파트·원래 컴프 id·로컬 컴프 이름·내레이션 파일명·프리미어 시퀀스 uid·유튜브 컷 `cuts_pr`)
- `python3 scripts/master.py episodes/<EP>` → `master/edl.json`, `master/source.json`
  - 내레이션 wav(프리컴프 안이어도 찾음)를 무음 기준으로 나누고(15초 넘는 구간은 구간 중앙값 −12dB 쉼에서 재분할) 자막 레이어 텍스트를 붙인다. 컷·건너뛴 소스에 걸친 말은 바깥 조각만 남긴다.
  - 텍스트 없는 조각은 로컬 whisper(small)로 판정: 말이면 0.5초 이내로 이어지는 이웃 문장에 합치고, 환각/무음이면 `nonverbal`(번역 안 함, 원래 소리 유지). 양쪽이 막힌 말은 `nonverbal`+`review` → 사람이 확인.
  - 출력 확인: 구간 수, `nonverbal` 목록(heard 필드), `no-text 0`, `build_warp(segments, {}, [], length)`가 겹침 오류 없이 통과.

## 3. 타임 워프
- 변환표: `python3 scripts/timewarp.py episodes/<EP> <tag> --durs <{구간id: 새 길이초}>` (검증용 `--test-pattern`, 자막을 남기려면 `--keep-subs`)
  → `build/<tag>/warp.json`, `scripts/ae/localize_job.json`
- 적용: `scripts/ae/run.sh $PWD/scripts/ae/localize.jsx` → `build/<tag>/<EP>_<tag>.aep`, `localize_log.json`(errors·warnings 0이어야 함)
- 파트 렌더: `scripts/ae/render.sh <aep> <MAIN_*> 0 <warp.json parts[pid].dur_new> <out.mp4> 29.97 "H.264 - Match Render Settings - 15 Mbps"` (파트 컴프 자체 길이는 1230초라 렌더 범위는 dur_new를 쓸 것)
- 대조: `python3 scripts/compare_warped.py <원본 파트 렌더> <변환 렌더> build/<tag>/warp.json <part> <out_dir> --t0 <> --t1 <>` → mean_sim ≥ 0.90, 연속 bad 없음

## 검증 기록 (B209, 2026-10-19, 최종 리뷰 수정 후)
- 마스터: 177구간(최대 14.8초), 화면 문자열 42, nonverbal 5(review 1), 길이 979.354
- 항등 변환: 미나 0~120초 mean 0.99998, bad 0
- 테스트 패턴(×0.9/×1.15): 미나 0~120 mean 0.989 bad 0
- 균일 ×1.3: 미나 0~120 mean 0.986 bad 0 / 가을 140~185(유튜브 컷 포함, 앵커 13개) mean 0.986 bad 0
- localize 로그: 오류·경고 0 (로컬에 없는 미사용 footage 레이어는 missing_footage_layers로 집계)

## 4. 영어판 (계획 2)
1. 번역: `python3 scripts/translate.py episodes/<EP> en` → `l10n/en.json`, `en_review.md` (헤드리스 `claude -p`, 구간별 글자 예산 = 길이 × profiles cps)
2. TTS: `python3 scripts/tts.py episodes/<EP> en --rewrite-loop` → `tts/en/*.mp3`, `durs.json`, `fit.json` (eleven_v4, 세모지 보이스, 0.75~1.35배 밖이면 재번역 최대 2회)
3. 발음 검수: `python3 scripts/asr_check.py episodes/<EP> en` → `asr.json` (유사도 0.85 미만은 표기 차이인지 들어서 확인, 발음 문제면 l10n에 "tts" 필드)
4. 화면 문자열: `python3 scripts/patch_text.py episodes/<EP> en` → `scripts/ae/run.sh $PWD/scripts/ae/patch_text.jsx` → `build/en/<EP>_en_text.aep` (넓으면 글자 축소, 최소 70%)
5. 워프: `python3 scripts/timewarp.py episodes/<EP> en --durs episodes/<EP>/tts/en/durs.json --keep-subs --aep episodes/<EP>/build/en/<EP>_en_text.aep` → `run.sh localize.jsx` → `build/en/<EP>_en.aep`
6. 자막: `python3 scripts/subtitles.py episodes/<EP> en` → `run.sh subtitles.jsx` → `build/en/<EP>_en_subs.aep`, `render/en/en.srt`
7. 파트 렌더: 파트마다 `render.sh build/en/<EP>_en_subs.aep <MAIN_*> 0 <warp.json parts[pid].dur_new> render/en/part_<pid>.mp4 29.97 "H.264 - Match Render Settings - 15 Mbps"`
8. 미리보기: `python3 scripts/preview.py episodes/<EP> en --narration-only` → `audio_mix.py` → `preview.py` (mix.wav가 파트 렌더·워프보다 오래되면 preview가 멈춤; 보통은 7절 `rebuild_lang.sh`가 이 순서로 함)

검증 기록(B209, 2026-10-19): 번역 172구간·문자열 42, TTS 172 전부 범위 안(1차 재작성 10), 829s/922s, 문자열 42/42 교체, 워프 979.35→886.15s, 자막 417큐, 미리보기 886.19s. 남은 한글: .ai 일러스트 속 글자(계획 3).

## 5. 화면 속 글자(계획 3a) — 일러스트·이미지
1. 내보내기·OCR: `python3 scripts/raster_scan.py episodes/<EP>` (벡터 k=4, 긴 변 1200px 이상; TIFF는 언프리멀티플라이; OCR은 투명·흰·검은 배경 3번) → `raster/items.json`. 이미 번역한 편에서 놓친 작은 벡터만 다시: `--upscale-small`(기존 항목 번호 유지)
2. 번역: `python3 scripts/raster_translate.py episodes/<EP> <lang>` → `l10n/<lang>.json` raster
3. 판: `python3 scripts/raster_plates.py episodes/<EP>` → `raster/plate/*.png`, `styles.json`, 검수 시트 `raster/plate_review_NN.png`(눈으로 확인)
4. 사람 보정: `raster/manual.json` — `"<id>#<n>": {"skip"|"text"|"font"}`, `"_hand_footage": [...]`(손글씨 폰트)
5. AE 적용은 아래 7의 `rebuild_lang.sh`가 함(`raster_apply.py` — 적용 전 검사 실패·AE 오류면 멈춤)

## 6. 오디오(계획 3b) — 프리미어 층
1. 재료: `python3 scripts/audio_fetch.py episodes/<EP>` → `src/audio/`(효과음 wav·BGM·아웃트로 BGM, NAS에서 NFC 비교로 찾아 복사). `master_config.json`의 `audio` 설정 필요(main_seq_uid, sfx_track, bgm_tracks, outro_bgm).
2. 믹서 검증(편마다 한 번): `python3 scripts/audio_mix.py episodes/<EP> ko-identity` — 유튜브 원본과 상관 ≥ 0.95, 30초 최솟값 ≥ 0.85. 재료가 없는 구간은 `audio.identity_exclude`에 사유와 함께.
3. 언어 믹스는 7에서 자동(`audio_mix.py <EP> <lang>` → `render/<lang>/mix.wav`; 내레이션은 한국어 녹음 LUFS에 맞춤, 피크 0.97 보호)

## 7. 공용 에셋 + 전체 재빌드
- 공용 에셋(언어마다 한 번, 모든 편 공유): `python3 scripts/build_global_assets.py <lang> emotion|title|outro <원본 파일>` → `assets/global/<lang>/`, 비교 시트 `review_*.png`. 대체 표 `assets/global/swap_<lang>.json`(키 = 원본 파일명).
- 재빌드: `scripts/rebuild_lang.sh episodes/<EP> <lang>` = 래스터 적용 → 에셋 교체 → 워프 → 자막 → 파트 렌더 → 내레이션 → 믹스 → 미리보기 → 한글 검사(0.5초)

검증 기록(B209 영어, 2026-10-20): 래스터 텍스트 213·소스 교체 309, 에셋 교체 7(타이틀 4·킥킥 3), 미리보기 886.19s, -18.9 LUFS(한국어 원본 -18.3)·피크 -0.5dBFS·클리핑 0, 항등 믹스 상관 0.970. 한글 검사 남은 것 = 실제 브랜드(롯데마트 간판·트레이더스 사진)와 OCR 오독뿐.

## AE 애니메이션 규칙
- **도장·팝 등 스케일로 등장하는 효과**: 실제로 그려지는 레이어(글자·셰이프·이미지)마다 첫 스케일 키 시각에 불투명도 0→100 키를 넣는다. null·부모 레이어의 불투명도는 자식에 전달되지 않으므로, 묶음(null)에만 넣으면 등장 전부터 화면에 떠 있다. `scripts/ae/build_inserts.jsx`의 `checkReveal`이 장면마다 검사해 어기면 오류로 멈춘다(`fadeChildren`으로 자식에 키를 넣음).
