---
name: vault-absorb
description: 완료된 프로젝트의 큐레이팅된 자료를 kairos-vault로 푸시. 모든 푸시는 vault 운영 매뉴얼(스키마·태그·canonical path)을 준수. wiki compiled 영역은 직접 쓰지 않고 topics 스냅샷/manifests로만 기여.
---

# vault-absorb

프로젝트가 끝난 뒤 vault에 누적 가치 있는 자료만 큐레이팅해 푸시한다. 자동 일괄 푸시 X — PD가 항목별로 선택 후 호출.

## Vault 운영 매뉴얼 (필수 참조)
- `/Volumes/kairos/kairos_vault/kairos-vault/CLAUDE.md`
- 캐노니컬: `02-research/{raw,topics,manifests,wiki}`. `03-research/`는 deprecated, 신규 쓰기 금지
- compiled wiki(`02-research/wiki/`)는 wiki-maintainer 전용. **vault-absorb는 직접 쓰지 않음**(topics/ 스냅샷이나 raw/ 노트로만 기여)
- 모든 .md 파일 frontmatter 필수, 태그는 vault Controlled Vocabulary에서 선택, 빈 태그 금지

## Reads
- `projects/{id}/` 모든 아티팩트
- vault CLAUDE.md (스키마·태그 규칙)
- (선택) brief의 큐레이션 명세

## Writes (vault 안)
허용된 경로만 사용한다.

| v4 자료 | vault 푸시 위치 | 비고 |
|--------|---------------|------|
| `research_reports/{slug}.md` (fresh/deep) | `02-research/topics/{topic_slug}_{video_slug}.md` 스냅샷 | 한 줄 요약 + 사용 영상 위키링크 |
| `research_targeted/{q_slug}.md` | `02-research/raw/{topic_slug}/{run_id}/source_notes/{q_slug}.md` | run_id = 영상 project_id 또는 푸시 시점 stamp |
| `final_manuscript.md` | `channels/{channel}/manuscripts/{video_slug}.md` | 채널 폴더에 보관 |
| (선택) `final_manuscript.units.json` | `channels/{channel}/manuscripts/{video_slug}.units.json` | 다운스트림 재활용용 |
| compiled wiki 제안 | **vault에 직접 쓰지 않음** — `02-research/manifests/_proposals/{date}.md` 에 "wiki-maintainer 검토 요청" 형태로만 기록 |

## Input resolution
1. **Brief 필수**: 다음 중 하나
   - 큐레이션 항목 리스트(어떤 v4 파일을 어디로)
   - 또는 자연어 명세("리서치 보고서랑 최종 원고만 푸시", "타겟 리서치는 빼고")
2. **video_slug 결정**: brief에서 명시 또는 plan.md 제목 기반 slug + project_id 접미
3. **topic_slug 결정**: research_reports/wiki의 slug 따름. 충돌 시 video_slug 접미
4. **실패**: 채널 미상·video_slug 미상이면 종료

## 실행 절차

1. vault 마운트 확인(`vault.is_available()`). 미마운트면 종료
2. brief에서 큐레이션 결정 — 무엇을 어디에
3. 각 항목별로:
   - 원본 파일 읽기
   - vault frontmatter 스키마로 변환(아래 매핑)
   - 태그를 Controlled Vocabulary에서 선택
   - vault 경로에 충돌 검사. 있으면 사용자 결정 필요(decisions에 명시, 자동 덮어쓰기 X)
4. 푸시
5. 푸시 결과 요약 반환

## Frontmatter 매핑

### research_reports → 02-research/topics/
```yaml
---
title: "<topic 한글>"
id: <8자리 hex — project_id 또는 신규>
category: research/topics
tags: [research, <도메인: technology|economy|psychology|culture|brand|people|common-sense>, <채널: 이로미즘|세모지>]
status: researched
summary: "<한 줄 요약>"
date: YYYY-MM-DD
source_video: "[[<video_id 또는 project_id>]]"
---
```

### research_targeted → 02-research/raw/<topic_slug>/<run_id>/source_notes/
```yaml
---
title: "<question 압축>"
category: research/raw
tags: [research, raw-source]
status: collected
source_id: "<unique>"
topic_slug: "<topic_slug>"
run_id: "<project_id 또는 stamp>"
source_type: <web|paper|official|book|report>
url: "<원본 url 있으면>"
retrieved_at: "<ISO datetime>"
---
```

### final_manuscript → channels/{channel}/manuscripts/
```yaml
---
title: "<영상 제목>"
category: <channel>/manuscript
tags: [<채널>, manuscript]
status: completed
project_id: <id>
date: YYYY-MM-DD
duration_estimate: "<분 단위>"
---
```

## 위키링크 / 충돌 처리

- **비디오 stub은 매 푸시 첫 회 자동 생성**: `03-analysis/videos/{project_id}/{project_id}.md` (project_id = UUID 8자 hex). 이미 있으면 skip
- v4 발생 비디오 stub 키는 **project_id 고정**(YouTube ID 아님). vault CLAUDE.md "위키링크 규칙" 참조
- 영상 공개 시 stub frontmatter에 `youtube_id`, `published_at` 채우고 `status: pre-publish → published`. **폴더/파일 rename 절대 X**
- 충돌 시 자동 덮어쓰기 X. PD가 사용자에게 확인 후 명시 덮어쓰기 brief로 재호출

### 스텁 frontmatter 스키마

```yaml
---
project_id: <8자 hex>
youtube_id: null              # 공개 시 채움
title: "<영상 제목>"
channel: <채널>
status: pre-publish           # → published
date_created: YYYY-MM-DD
published_at: null            # → ISO datetime
duration_estimate: "<분>"
category: video-analysis
tags: [<채널>, video-analysis, pre-publish]   # 공개 시 pre-publish 제거 + 도메인 태그 추가
---
```

## 금지

- `03-research/` 신규 쓰기
- `02-research/wiki/` 직접 쓰기 (wiki-maintainer 전용)
- Controlled Vocabulary 외 신규 태그 임의 추가(필요하면 vault CLAUDE.md를 먼저 갱신해야 함 — decisions로 보고)
- `pd_notebook.md`, v4 프로젝트 아티팩트 수정

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지. 외래어 영문 표기 허용

## Return (Skill Contract)
- artifact_paths: 푸시된 vault 절대 경로 리스트
- summary: 200~400단어. 무엇을 어디로 푸시했는지, 충돌·스킵 항목, 위키링크 stub 필요 여부
- decisions: (a) 충돌로 보류된 항목, (b) wiki-maintainer 검토 요청 만든 manifest 경로, (c) 신규 태그 필요로 vault CLAUDE.md 갱신 권장 항목, (d) stub 생성 필요 비디오
