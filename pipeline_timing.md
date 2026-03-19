# 아트스타일별 파이프라인 테스트 결과 (2026-03-19)

## 전체 결과: 3/3 완료

| # | 프로젝트 | 스타일 | 보이스 | 영상 | 씬수 | 비용 |
|---|---------|--------|--------|------|------|------|
| 1 | 세모지_AI에이전트시대_1min | semoji | W7FnAxJNpD5WGjrF5GLp | 10.7MB | 7씬 | $0.87 |
| 2 | 이로미즘_양자컴퓨터_1min | quirky_cartoon | 9Sj8ugvpK1DmcAXyvi3a | 34.1MB | 6씬 | $1.17 |
| 3 | 레고_화성탐사_1min | lego | 4JJwo477JUAx3HV0T7n7 | 20.3MB | 6씬 | $1.05 |

## 공통 성공 항목
- 리서치: Explorer 3개, Python 병합, 사감독 LLM 검증 통과
- 원고: 씬 마커 없음 (챕터만), 분량 400~520자
- 씬 설계: creative direction + asset advisory + data enrichment
- 이미지: 검색(위키미디어) + 생성(FAL.ai) 혼합
- TTS: 스타일별 보이스 자동 적용
- 자막: WhisperX + Gemini
- 렌더링: Remotion SimpleVideo

## 공통 실패/수동 처리
- step_11 (매니페스트 빌드): Supabase 미연결로 실패 → 수동 리빌드
- step_9b (TTS 검증): report.json 미생성 → 실제 검증은 됨
- 렌더링: 매니페스트 리빌드 후 수동 실행

## 향후 개선 필요
- 매니페스트 빌드: Supabase 없이도 작동하도록 수정
- TTS 검증: 에이전트 대신 Python 스크립트로 전환
- Phase 4 병렬화: TTS + 이미지 검색 + 이미지 생성 동시
- 이미지 생성 일괄 처리 (FAL.ai batch)
- 캐릭터 플래닝: 이미지 소싱 안으로 통합
