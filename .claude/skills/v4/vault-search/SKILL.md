---
name: vault-search
description: Kairos Vault에서 주제·키워드 관련 기존 자료를 검색해 후보 경로와 스니펫을 반환. 새 리서치 시작 전 재사용 가능 자료 확인용.
---

# vault-search

NAS 마운트된 Obsidian 볼트(`/Volumes/kairos/kairos_vault/kairos-vault/`)에서 기존 리서치·분석 자료를 검색한다. **읽기 전용**. 흡수(쓰기)는 별도 vault-absorb 스킬 책임(MVP 후).

## Reads
- Vault의 캐노니컬 리서치 영역만:
  - `02-research/wiki`, `02-research/topics`, `02-research/raw`
  - `01-patterns`
  - `03-analysis/videos`, `03-analysis/channels`
- Vault 매뉴얼: `/Volumes/kairos/kairos_vault/kairos-vault/CLAUDE.md` (스키마·태그 참조용)

## Writes
- 없음. 결과는 반환값으로만 전달.

## Input resolution
1. **Brief 필수**: 검색 키워드(주제·인물·기관·이벤트). 추가 키워드 리스트 선택
2. **영역 한정**: brief에 `areas:` 가 있으면 그 영역만 검색
3. **Vault 미마운트**: 마운트 안 되어 있으면 빈 결과 + decisions에 사유 명시(에러 아님)

## 실행 절차

1. `skills.shared.lib.vault.is_available()` 확인. False면 빈 결과 반환, decisions에 "vault unavailable" 기록
2. `vault.search(query, extra_terms=..., areas=..., limit=20)` 호출
3. 상위 후보를 메인이 판단 가능한 형태로 정리:
   - 경로(절대)
   - 영역(02-research/wiki 등)
   - 제목, 태그
   - 짧은 스니펫(최대 200자)
   - 점수(상대 비교용)
4. summary에 "찾은 후보 N건, 상위 K건의 성격" 기술
5. decisions에 (a) 재사용 권장 후보, (b) 직접 normalize 권장(원문 가져오기), (c) 이번 주제는 vault에 부족하므로 새 리서치 권장 같은 결정 항목

## 반환

Skill Contract 준수. **artifact_paths는 비어 있을 수 있음**(읽기 전용). 후보 목록은 summary에 압축 표기, 자세한 경로/스니펫은 메인이 다음 행동 결정에 쓸 수 있도록 decisions에 인라인 포함.

원본 본문은 메인 컨텍스트로 올리지 않는다. 메인이 재사용 결정한 항목만 다음 단계에서 (각 리서치 스킬의 외부 경로 normalize 어댑터로) 가져온다.

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
