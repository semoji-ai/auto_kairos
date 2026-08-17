---
name: reference-list
description: 최종 원고에서 핵심 시각 레퍼런스 목록을 뽑아 references.json 생성(이미지 생성용 프롬프트 포함).
---
# reference-list
final_manuscript.md를 읽고 영상의 핵심 시각 소재 3~6개를 고른다(주요 장면·사물·인물).
## 출력(references.json, 스키마 references.schema.json)
- 각 항목: id("ref_1"…), subject(한 줄 소재), image_prompt(생성용 시각 묘사, 한국어)
- image_prompt에는 아트스타일 키워드(평면/3등신 등) 넣지 말 것 — 스타일은 생성 단계가 따로 입힌다.
## 금지
- 6개 초과. 텍스트가 들어간 이미지 요구.
## 한국어 규칙
- 가타카나/히라가나/한자 금지
