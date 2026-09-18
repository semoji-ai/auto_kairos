# 다중 씬 비디오 트랙 — 앱·웹·Remotion 통합

기존 Adobe 트랙 커밋 a4fbb62의 계약을 공유 Python 모듈로 옮겼습니다.
Claude/Codex 어느 실행 제공자에도 의존하지 않습니다. MP4를 씬별로
잘라 복제하지 않고, 프로젝트 video_tracks.json이 배치를 소유합니다.

## 사용

1. 프로젝트 video_sources/에 원본 MP4를 보관합니다.
2. 앱/웹 스토리보드의 **통합 비디오 트랙**을 엽니다.
3. 영상, 연속된 첫/마지막 씬, 원본 시작/종료 초를 지정합니다.
4. 원본 구간과 각 씬 시작 위치를 확인하고 추가·활성화합니다.
5. 스토리보드에 통합 영상 배지가 표시됩니다. 씬 미리보기를 다시 열면
   해당 원본 위치부터 재생합니다. 전체 렌더 전 **렌더 매니페스트 갱신** 후
   스튜디오를 새로고침합니다.
6. 비활성화하면 기존 시각 자료가 복원됩니다. 이미지·원고·TTS는 수정하지 않습니다.

구간 수정·재검토는 기존 clipId를 유지합니다. TTS/원고/씬 순서가 바뀌면
기존 클립 활성화를 차단합니다. 현재 원고와 내부 컷 타이밍을 검토한 후
명시적으로 다시 저장해야 합니다. 자동 속도 변경이나 루프는 하지 않습니다.

대량 생성 결과는 다음 명령으로 **비활성 초안**을 만들 수 있습니다.
stdout JSON을 파일로 저장한 뒤 UI에서 가져옵니다. 프로젝트 루트에 바로
video_tracks.json으로 덮어쓰지 마세요. 가져오기는 항상 비활성으로 등록하며
중복 ID는 거절합니다.

```sh
python3 -m auto_agent.scripts.prepare_video_tracks \
  --project /path/to/project \
  --cutlist /path/to/execution_cutlist.json \
  --downloads /path/to/download_log.json
```

입력은 units[].shots[].sceneId와 다운로드 원장의 id/path입니다.
생성 프롬프트의 컷 시간은 실제 영상 전환 검수의 대체물이 아닙니다.

## 계약과 안전

- 앱/웹 API: GET/POST /api/p/{project_ref}/video-tracks.
- 저장: 기존 revision 필수, 프로세스 간 파일 잠금과 원자적 교체.
- 씬 ID, 범위 순서/연속성, 실제 파일, 경로 탈출(심볼릭 링크 포함),
  원본 길이, 숫자, 겹침을 검사합니다. ffprobe가 필요합니다.
- MVP: 불투명 전체 화면, 원본 비율 contain, 무음, 1배속, 비중첩.
- 원본이 길면 범위 끝에서 자르고, 짧으면 기존 씬 화면으로 돌아갑니다.
  둘 다 경고에 남깁니다. 부분적으로 덮인 씬의 기존 비디오는 삭제하지 않습니다.
- 트랙이 있는 프로젝트의 기준은 scene_specs와 실제 오디오 길이의
  30fps 프레임 올림입니다. 정수 프레임 누적값을 manifest에 전달합니다.
- 전체 재생은 프로젝트 수준 Sequence 하나, 단독 미리보기만 scene-local
  sourceIn을 사용합니다. TTS와 자막은 기존 씬 단위로 유지합니다.
- 활성 영상 위에 출처/권리 협의 표시와 자막을 보존합니다.
- 트랙 파일이 없는 프로젝트의 manifest/timing 경로는 그대로입니다.
- Adobe와 specs의 번호 순서가 다르면 트랙은 오류로 차단합니다.
  둘의 ID가 달라도 번호 순서가 일치하면 covered ID를 대응시킵니다.
- 렌더 manifest는 캐시입니다. CLI 렌더 전 반드시 재빌드합니다.

## 검증 (2026-09-18)

- 공유 계약/API + 기존 Adobe manifest/timeline/Premiere 회귀: **92 tests passed**.
- 원본 24fps → 타임라인 30fps 실제 4초/120프레임 렌더:
  프레임 0–59 빨강, 60–119 초록. 두 번째 씬에서 재시작/검은 프레임 없음.
- 전체 프레임 75와 두 번째 씬 단독 프레임 15의 중심 픽셀 동일:
  RGB (0, 127, 0).
- 스토리보드/에디터 Vite 번들 빌드 성공, 생성 번들 포함.
- remotion/src 미러 일치, git diff --check, JS 구문 검사 통과.
- 메인의 InfographicScene JSX 주석 위치 오류는 빌드 선행 조건으로 국소 수정.
- 전체 tsc는 기존 타입 오류/누락 에셋 등으로 실패합니다. 전역 타입 검사
  통과를 주장하지 않습니다. 새 기능의 실제 번들/렌더와 별개입니다.
- 앱/Tauri 수동 클릭 검증, 실제 Premiere/AE 호스트 조립은 미실행입니다.

재현:

```sh
PYTHONPATH=.:adobe python3 -m pytest -q tests/test_video_tracks.py \
  adobe/tests/test_video_tracks.py adobe/tests/test_timeline.py \
  adobe/tests/test_manifest.py adobe/tests/test_premiere.py
python3 scripts/sync_remotion_src.py --check
cd auto_agent/remotion_template
npm ci
npx vite build --config vite.thumb.config.ts --outDir ../dashboard/static
npx vite build --config vite.editor.config.ts --outDir ../dashboard/static
# 아래 테스트 원본이 이미 있다면 덮어쓰지 않고 재사용합니다.
ffmpeg -v error -f lavfi -i color=red:s=320x180:r=24:d=2 \
  -f lavfi -i color=green:s=320x180:r=24:d=2 \
  -filter_complex '[0:v][1:v]concat=n=2:v=1:a=0' \
  -c:v libx264 -pix_fmt yuv420p public/track-smoke.mp4
npx remotion render test/video-track-render.tsx FullTrackSmoke /tmp/full-track-smoke.mp4
npx remotion still test/video-track-render.tsx FullTrackSmoke /tmp/full75.png --frame=75
npx remotion still test/video-track-render.tsx SliceTrackSmoke /tmp/slice15.png --frame=15
```

## LG 1·2편 적용 상태

실제 프로젝트 원본에 대한 읽기 전용 검사:

- 1편 55개: 파일·씬 ID·연속 범위 검증. 기존 시험 001/038은 별도 기록으로 매칭.
- 2편 24개: 같은 검증. 수정 이미지로 새로 제출했던 8건은 확보 원장에 없으므로 제외.
- 1편 LG01-H3-017은 원본이 씬 범위보다 짧다는 경고. 내용/타이밍 검토 필요.
- 두 프로젝트 planning/video_track_integration_20260918/video_tracks.draft.json에
  비활성 초안 저장. PR에는 개인 프로젝트 원고/영상/초안을 포함하지 않음.
- Adobe scenes.json은 1편 68 vs specs 121, 2편 65 vs specs 138로 불일치.
  기존 Adobe 수정분을 보존하는 별도 씬 동기화 전에는 Adobe 트랙 활성화 불가.
- **운영 앱 재시작·브랜치 전환·프로젝트 최종 영상 선택은 아직 하지 않았습니다.**
  이 PR 병합/배포 후 시청 검수된 클립부터 활성화합니다.
