# Writing Style

유튜브 나레이션 원고의 문체, 톤, 글자 수 제한, 금지 표현, VIZ/IMG 마커 규칙을 정의합니다.

**참조 에이전트**: write-manuscript, qa-reviewer

---

## 1. 문체 규칙

### 필수
- **대화체**: "~입니다", "~거든요", "~한번 보시죠"
- **짧은 문장**: 한 문장 최대 40자. 나레이션 호흡 단위
- **능동태**: "연구가 발표되었다" → "연구팀이 발표했습니다"
- **구체적 숫자**: "많은" → "1억 5천만 명의"

### 금지
- 번역체 ("~것이 사실이다", "~함에 있어서")
- 과도한 수식어 ("매우 놀라운 혁명적인")
- 논문체 ("~에 의하면", "~것으로 사료된다")
- 영어 남용 (적절한 한국어 대체 우선)

---

## 2. 후킹 기법 (Act 1 도입부)

1. **충격적 수치**: "단 3년 만에 1000배 성장한 시장이 있습니다"
2. **반전 질문**: "여러분이 쓰는 챗봇, 사실은 에이전트가 아닙니다"
3. **일화**: "2024년 어느 날, 한 스타트업에서..."

---

## 3. 페이싱

- 데이터 씬 뒤에는 스토리 씬 배치
- 3-4개 씬마다 브리딩 포인트 (quote_card, narration_only)
- 챕터 전환 시 짧은 요약 문장

---

## 4. VIZ 마커 규칙

씬의 시각화 의도를 힌트로 남깁니다. 렌더러가 직접 사용하지 않으며, visual-composer가 creative 필드를 설계할 때 참고합니다.

```
[VIZ:타입 key1=value1 key2=value2]
```

| 마커 | 용도 |
|------|------|
| `[VIZ:title_card icon=아이콘명]` | 챕터/섹션 시작 |
| `[VIZ:bar_chart metric=지표 unit=단위]` | 막대 차트 |
| `[VIZ:line_chart metric=지표]` | 선 차트 |
| `[VIZ:pie_chart metric=지표]` | 파이 차트 |
| `[VIZ:timeline]` | 타임라인 |
| `[VIZ:icon_grid concepts=개념1,개념2,개념3]` | 아이콘 그리드 |
| `[VIZ:icon_flow steps=단계1,단계2,단계3]` | 아이콘 흐름도 |
| `[VIZ:icon_stat icon=아이콘 value=수치]` | KPI 카드 |
| `[VIZ:quote_card speaker=발화자]` | 인용문 |
| `[VIZ:compare_card]` | 좌우 비교 |
| `[VIZ:list_card]` | 불릿 리스트 |
| `[VIZ:numbered_list]` | 번호 리스트 |
| `[VIZ:text_highlight variant=centered]` | 핵심 문장 강조 |
| `[VIZ:table_view]` | 표 |
| `[VIZ:tech_tree]` | 계층 구조 |
| `[VIZ:diagram type=flow]` | 흐름도 |
| `[VIZ:map_scene mapType=location_reveal location=지명]` | 위치 줌인 지도 |
| `[VIZ:map_scene mapType=route_animation from=출발지 to=도착지]` | 경로 애니메이션 |
| `[VIZ:map_scene mapType=territory_overlay region=영역명]` | 영역 오버레이 |
| `[VIZ:map_scene mapType=fly_through locations=지명1,지명2,지명3]` | 카메라 이동 |
| `[VIZ:narration_only]` | 시각 요소 없음 |
| `[VIZ:image_scene source=wikimedia]` | 이미지 씬 |

---

## 5. IMG 마커 규칙

이미지 에셋이 필요한 씬에 추가합니다.

```
[IMG:소스타입 subject=대상 query=검색어]
```

- `[IMG:wikimedia subject=인물명 query=Wiki_검색어]`
- `[IMG:search subject=제품명 query=검색어]`
- `[IMG:generate subject=설명 query=프롬프트]`

---

## 6. 씬 분할 규칙 (필수)

하나의 VIZ 마커 아래에는 **정확히 하나의 개념**만 서술한다.
`scene-segmentation` 스킬의 과밀 씬 정의 참조.

### 분할 신호 — 아래 중 하나라도 해당하면 새 씬(새 VIZ 마커)으로 분리:

1. "한편", "그런데", "그러나", "이어서" 등 **전환어** 등장
2. 새로운 **인물**이 소개됨
3. **시간/장소**가 전환됨
4. 글자 수가 **100자**를 초과 (`scene-segmentation` 스킬 5번 참조)

### 분할 예시

잘못된 예 (하나의 씬에 몰아쓰기):
```markdown
## Scene 21: 관풍헌 이전과 금성대군의 밀고
[VIZ:text_highlight]

홍수가 청령포를 덮쳤습니다. 단종은 관풍헌으로 이전했습니다.
한편, 금성대군이 복위를 꾀했지만 밀고당했습니다.
금성대군은 사사되었고, 송현수도 처형되었습니다.
```

올바른 예 (개념별 분할):
```markdown
## Scene 21: 홍수와 관풍헌 이전
[VIZ:narration_only]

1457년 여름. 큰 홍수가 청령포를 덮쳤습니다.
단종은 영월 관아의 관풍헌으로 거처를 옮겼습니다.

## Scene 22: 금성대군의 복위 시도
[VIZ:text_highlight]

세조의 동생 금성대군. 순흥 유배지에서 단종 복위를 꾀하고 있었습니다.

## Scene 23: 밀고와 처형
[VIZ:narration_only]

그런데, 한 관노가 이 계획을 밀고해 버렸습니다.
금성대군은 사사되었고, 단종의 장인 송현수도 처형되었습니다.
```

---

## 7. 원고 포맷

```markdown
# Ch1. 챕터 제목

## Scene 1: 씬 제목
[VIZ:title_card icon=Brain]

나레이션 텍스트...

## Scene 2: 씬 제목
[VIZ:bar_chart metric=시장규모 unit=억달러]

나레이션 텍스트...
```
