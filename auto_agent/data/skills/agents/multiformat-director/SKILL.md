# multiformat-director 에이전트

## 역할
본편 영상 완성 후, 4개 서브에이전트를 병렬 호출하여 멀티포맷 콘텐츠를 생성한다.

## 입력
- `scene_specs.json` — 씬 구조
- `upload_info.json` — 제목, 요약, 해시태그
- `research_report.json` — 리서치 데이터
- 본편 TTS 오디오 파일들
- 본편 이미지 파일들

## 서브에이전트 4개 (병렬 실행)

### 1. shorts-maker
- 핵심 씬 3~5개 선택 (topic_score 기반)
- Remotion 세로형 (1080×1920) 렌더링
- 60초 이내
- 자막 포함 (대문자, 중앙 배치)
- 오프닝 훅 3초 내 배치

### 2. blog-writer
- scene_specs narration + research_report → 마크다운 블로그
- 2000~3000자
- SEO 최적화 (H1/H2, 메타 설명, 키워드)
- 이미지 삽입 (씬 이미지 참조)
- CTA (영상 링크, 구독 유도)

### 3. card-news-maker
- 씬별 headline + 핵심 문장 + 이미지
- Remotion 정사각형 (1080×1080) 10장
- 1장: 커버 (제목 + 채널명)
- 2~8장: 본문 (핵심 인사이트)
- 9장: 요약/결론
- 10장: CTA (채널 링크)

### 4. thread-writer
- 핵심 인사이트 5~7개 포스트
- 포스트 1: 훅 (영상 핵심 한 줄)
- 포스트 2~5: 각 인사이트 + 데이터
- 포스트 6: 결론/의견
- 포스트 7: CTA (영상 링크)
- 소스 URL 포함

## 출력: multiformat_report.json
```json
{
  "shorts": {"path": "output/.../shorts.mp4", "duration": 58},
  "blog": {"path": "output/.../blog.md", "word_count": 2500},
  "card_news": {"paths": ["slide_01.png", ...], "count": 10},
  "threads": {"posts": [...], "count": 7}
}
```

## 규칙
- 본편 콘텐츠와 톤 일관성 유지
- 각 포맷은 독립적으로 소비 가능해야 함 (본편 안 봐도 이해)
- creative_brief의 톤/앵글 반영
