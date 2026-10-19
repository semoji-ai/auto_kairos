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
