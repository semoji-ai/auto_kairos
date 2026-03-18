# 파이프라인 분량별 소요시간 추적

## 진행 상태: 1분 완료! 3분 프로젝트 진행 중

## 1분 프로젝트: 테슬라_테라팹_반도체_혁명
- 상태: step_1~step_11b 성공 (20/22), step_12(렌더링) Remotion 에셋 다운로드 실패
- 실패 원인: Remotion render가 localhost:3000에서 에셋 다운로드 시도 → 서버 미실행
- 해결 필요: Remotion Studio 서버 실행 후 렌더링, 또는 --bundle-cache 옵션 확인
- 총 비용: $3.69
- 파이프라인 22스텝 중 20스텝 성공!

### 성공한 스텝 (20/22)
- step_0 (환경점검): 0.7s
- step_1 (리서치): 796s, $0.03 — Python 병합으로 성공
- step_2 (원고): 242s, $0.16 — 이로미즘 스타일, 1분 분량
- step_3 (중복검사): 0.2s
- step_4 (팩트체크): OK — agent 모드
- step_5 (씬분해): OK — agent 모드
- step_5b (캐릭터): OK
- step_6 (크리에이티브 디렉션): OK
- step_6b (에셋심의): OK
- step_6c (데이터보강): OK
- step_6d (모션설계): OK
- step_7 (TTS전처리): OK
- step_8 (TTS생성): OK
- step_8b (이미지소싱): OK
- step_9 (자막동기화): OK
- step_9b (TTS검증): OK
- step_10 (데이터검증): OK
- step_11 (매니페스트): OK — int→str 수정
- step_11a (스틸캡처): OK
- step_11b (QA사전): OK

### 실패한 스텝 (2/22)
- step_12 (영상조립): Remotion render 에셋 경로/서버 문제
- step_12b (QA사후): step_12 의존

## 3분 프로젝트: 아카데미_한국영화_쾌거
- 상태: 진행 중
- 시작: 2026-03-18 08:30

## 5분 프로젝트: 중동전쟁과_유가폭등
- 상태: 진행 중 (agent 모드 + searchQuery 강화)
- 시작: 2026-03-18 09:10

## 10분 프로젝트: AI반도체_패권전쟁
- 상태: 대기

## 주요 수정 이력 (2026-03-18)
1. iCloud 손상 복구 → ~/Projects/로 이동
2. 대시보드: 로컬 PM 전환, 카톡 스타일 메신저, 에이전트 캐릭터
3. 리서치: Python 병합 (Explorer 산출물 자동 통합)
4. pipeline.json: single_call → agent 모드 전환
5. pipeline.json: 로컬 DATA_DIR 우선 로드 (Supabase 캐시 무시)
6. project_config: 프롬프트에 분량/문체/스타일 주입
7. manifest_building: int→str 수정
8. Remotion: entry point 추가, SlideProcess 생성, 심볼릭 링크 수정
9. BuildingBlocks.tsx 등 5개 iCloud 빈 파일 복구
