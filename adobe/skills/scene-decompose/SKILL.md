---
name: scene-decompose
description: final_manuscript.md를 의미·길이·인물 기준으로 씬으로 분해해 scenes.json 생성. narration은 원문 substring 불변.
---

# scene-decompose

원고를 씬 단위로 분해한다. narration은 원고에서 **그대로** 가져온다(재작성·요약 금지).

## Reads
- `final_manuscript.md` (필수)
- `plan.md` (선택 — 제목/톤/섹션)

## Writes
- `scenes.json` (스키마: `scenes.schema.json`)

## 그룹핑 기준 (우선순위)
1. 섹션/문단 경계
2. 의미 전환(도입/전개/전환/마무리)
3. 길이 예산: 씬당 한국어 약 100~250자(상한 ~40초 분량)
4. 핵심 인물(주어) 변화 시 씬 경계

## 씬 필드
- title: 2~6글자 핵심 키워드
- narration: 해당 씬 원고 텍스트(원문 substring, 공백 1칸 join)
- characters: 등장 인물(없으면 빈 배열)
- visual_summary: 한 줄 화면 설명
- image_prompt: 생성/검색용 시각 단서(한국어, 아트스타일 키워드 제외)
- duration_estimate_sec: 한국어 글자수 ÷ 6 추정

## 출력
- `scenes.json` 만 출력. JSON 외 텍스트 금지(--output-schema 강제).
- 모든 씬은 8개 필드(sceneNumber, section, title, narration, characters, visual_summary, image_prompt, duration_estimate_sec)를 빠짐없이 채운다. 없으면 section은 null, characters는 빈 배열.

## 레이아웃 선택(씬마다)
- 모든 씬을 이미지(cinematic)로 만들지 마라. 내용에 맞는 레이아웃을 고른다:
  - cinematic: 장면 묘사가 필요한 스토리텔링 씬(이미지 생성) — image_prompt 필수
  - headline_only: 한 문장 선언/전환(헤드라인 타이포) — headline 필수, sub 선택
  - items_list: 나열(3~5개) — headline+items 필수
  - metric_spotlight: 핵심 수치 강조 — value+label 필수
  - bar: 수치 비교(3~6개) — headline+chart{labels,values,unit} 필수
  - quote: 인용 — quote_text+quote_who 필수
  - map: 지리적 위치/이동 경로가 핵심인 씬 — map_center[위도,경도]+map_zoom(국가~4, 도시~10)+map_markers[{name,coord:[위도,경도]}] 필수. 좌표는 [위도, 경도] 순서.
    이동 경로가 있으면 map_route(순서대로 [위도,경도] 점 목록, 2~8개)도 채운다.
- 비율 감각: 이미지 씬 40~60%, 나머지를 내용에 맞게 섞어라. 연속 2씬 같은 비-이미지 레이아웃 지양.
- cinematic이 아닌 씬은 image_prompt를 빈 문자열로.
- headline은 내레이션 요지의 단순 반복이 아니라 다른 표현으로 쓴다(자막과 중복 방지).
- 사용하지 않는 레이아웃 데이터 필드는 null로 채운다.

## 금지
- narration 변경(요약/오탈자 수정 포함)
- 연출/레이아웃/이미지 생성 결정(후속 단계)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
