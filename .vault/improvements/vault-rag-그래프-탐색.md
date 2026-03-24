---
tags: [improvement, vault-rag, knowledge-graph]
date: 2026-03-24
priority: medium
status: planned
---

# VaultRAG를 위키링크 그래프 탐색으로 개선

## 현재
키워드 기반 파일명/내용 문자열 매칭 (단순 grep 수준).
옵시디언 위키링크(`[[노트명]]`)를 완전히 무시.

## 목표
1. 위키링크 파싱 → 인접 리스트(그래프) 구성
2. 주제 노트에서 1~2홉 이내 연결 노트 수집
3. 역링크 탐색 — "이 주제를 참조하는 노트"도 수집
4. 태그 기반 클러스터링 — 같은 tag를 가진 노트군 자동 포함

## 볼트 현황
위키링크가 이미 존재:
- `videos/*.md` → `[[question]]`, `[[visual-heavy]]` 등 패턴 링크
- `patterns/*.md` → `[[videoId]]` 역링크
- 채널 → 비디오 → 패턴 양방향 연결
