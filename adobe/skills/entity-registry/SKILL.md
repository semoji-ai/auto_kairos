---
name: entity-registry
description: 씬별 free-text 엔티티 태그를 비디오 전체 정규화 레지스트리로 통합 — 표기 변형 dedupe + 풍부 시각 명세 합성.
---
# entity-registry

씬에서 추출된 캐릭터/장소/소품 출현 목록을 받아 **비디오 전체에서 정규화된 엔티티 레지스트리**를 만든다. 이후 시트 생성·씬 렌더가 이 레지스트리를 단일 소스로 쓴다.

## 입력
- 엔티티 출현 목록: `- [type] raw (씬N)` 형태. type은 character|location|prop.
- editorial brief, 원고 — 각 엔티티의 시각 묘사 출처.

## 해야 할 일
1. **표기 변형 통합** — 같은 대상의 다른 표기(예 "할머니" / "할머니 캐릭터" / "노인")를 하나의 엔티티로 묶고, 본 표기들을 모두 `aliases`에 넣는다.
2. **canonical 부여** — 안정적 `id`(kebab-case, 타입 접두: `char-`, `loc-`, `prop-`), 대표 `name`(한국어), `type`.
3. **시각 명세 합성** — 원고·브리프 근거로 `visual` 작성:
   - character → `{appearance, hair, outfit, expressions[]}`
   - location → `{space, mood, lighting}`
   - prop → `{form, material, color}`
4. `first_scene`(최초 등장 씬 번호), `scenes`(등장 씬 번호 배열).

## 출력
entities JSON만 출력:
```
{ "entities": [ { "id", "type", "name", "aliases": [...], "visual": {...}, "first_scene", "scenes": [...] } ] }
```
- 모든 출현이 어떤 엔티티의 `name` 또는 `aliases`에 정확히 포함되어야 한다(역링크가 정확 일치로 매칭함).
- 근거 없는 엔티티를 새로 만들지 말 것. 출현에 있는 대상만.

## 한국어 규칙
- 가타카나/히라가나/한자 금지.
