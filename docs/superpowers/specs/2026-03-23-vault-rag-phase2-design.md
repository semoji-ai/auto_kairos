# Vault RAG Phase 2 — 벡터 임베딩 기반 시맨틱 검색

**날짜:** 2026-03-23
**상태:** 승인됨
**범위:** auto_kairos_v3 + kairos-vault

---

## 배경

기존 `auto_agent/orchestrator/vault_rag.py`에 Phase 1(키워드 기반 검색)이 구현되어 있다.
파이프라인의 리서치/원고 스텝에서 볼트를 참조하고, 결과를 볼트에 축적하는 구조도 갖춰져 있다.

Phase 2 목표:
- 키워드 매칭 → 시맨틱 임베딩 검색으로 업그레이드
- 대시보드에서 수동 검색 UI 제공
- 심야 일괄 인덱싱 가능한 독립 CLI 명령어 추가
- 볼트 경로 버그 수정

---

## 범위

### 포함
1. 볼트 경로 기본값 버그 수정 (`~/Desktop` → `~/Projects`, 마이그레이션 안전장치 포함)
2. `VaultIndexer` 클래스 신규 추가 (임베딩 + Chroma 저장)
3. `VaultRAG` 시맨틱 검색 업그레이드 (하위 호환 유지)
4. CLI 명령어 `auto-agent vault index/stats/search`
5. 대시보드 검색 API `GET /api/vault/search` (`auto_agent/dashboard/vault_routes.py`)
6. 대시보드 검색 UI (검색창 + 결과 카드)

### 제외
- 파일에 위키링크 자동 삽입 (B안 채택: 추천만)
- 자동 인덱싱 (심야 수동 실행)
- OpenAI 등 외부 API 의존성

---

## 아키텍처

```
kairos-vault/*.md
    ↓ auto-agent vault index (수동/심야)
VaultIndexer
  - frontmatter + [[위키링크]] 제거 후 본문만 청킹
  - 청크 단위: 500자(한국어 기준 문자), 100자 오버랩
  - 청크 ID: {file_relative_path}#{chunk_index} (SHA256 해시 아님 — 경로+인덱스로 결정론적)
  - 파일 재인덱싱 시: 기존 청크 전량 삭제 후 upsert
  - 파일 해시 캐시: ~/.kairos/vault_index_hashes.json
    ↓
Chroma DB (~/.kairos/vault_chroma/, 영구 저장, 컬렉션명: kairos_vault)
  메타데이터 필드: file (상대경로), folder (최상위 폴더), tags (frontmatter), chunk_index
    ↓ 검색
VaultRAG.semantic_search(query, top_k=5, folder_filter=None)
  반환: [{"file": str, "snippet": str, "score": float, "tags": list}]
  - Chroma 없거나 ImportError → 키워드 검색 폴백 (동일 반환 구조로 변환)
    ↓
[A] 파이프라인 search_for_research / search_for_manuscript
[B] GET /api/vault/search (대시보드)
```

---

## 컴포넌트 상세

### 1. 경로 버그 수정 + 마이그레이션 안전장치

**파일:** `auto_agent/orchestrator/vault_rag.py`

```python
def _resolve_vault_dir() -> Path:
    """볼트 경로 결정. 환경변수 → Projects → Desktop 순으로 시도."""
    if env := os.environ.get("KAIROS_VAULT_DIR"):
        return Path(env)
    projects_path = Path.home() / "Projects" / "kairos-vault"
    desktop_path = Path.home() / "Desktop" / "kairos-vault"
    if projects_path.exists():
        return projects_path
    if desktop_path.exists():
        print("[VaultRAG] 경고: ~/Desktop/kairos-vault 사용 중. ~/Projects/로 이전을 권장합니다.")
        return desktop_path
    return projects_path  # 기본값 (미존재 시 비활성)

VAULT_DIR = _resolve_vault_dir()
```

### 2. VaultIndexer

**파일:** `auto_agent/orchestrator/vault_indexer.py` (신규)

```python
class VaultIndexer:
    CHROMA_DIR = Path.home() / ".kairos" / "vault_chroma"
    HASH_CACHE = Path.home() / ".kairos" / "vault_index_hashes.json"
    COLLECTION = "kairos_vault"
    MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    CHUNK_SIZE = 500      # 문자 단위
    CHUNK_OVERLAP = 100

    def index_all(self, vault_dir: Path, force: bool = False) -> dict:
        """
        전체 볼트 인덱싱.
        force=True: 해시 캐시 무시, 전체 재인덱싱.
        반환: {"indexed": int, "skipped": int, "errors": int, "total_chunks": int}
        """

    def index_file(self, path: Path, relative_to: Path) -> int:
        """
        단일 파일 인덱싱.
        1. frontmatter 제거, [[위키링크]] 제거, 마크다운 헤더/#/- 유지
        2. 500자 청킹 (100자 오버랩)
        3. 청크 ID: "{relative_path}#{chunk_index}"
        4. Chroma에 기존 청크 삭제 (prefix 매칭) 후 upsert
        반환: 추가된 청크 수
        """

    def get_stats(self) -> dict:
        """
        반환 구조:
        {
            "file_count": int,       # 인덱싱된 파일 수
            "chunk_count": int,      # 총 청크 수
            "last_indexed_at": str,  # ISO 8601 문자열 or null
            "chroma_dir": str,       # Chroma 저장 경로
            "vault_dir": str         # 볼트 경로
        }
        """
```

**첫 실행 UX (모델 다운로드):**
- `auto-agent vault index` 실행 시 sentence-transformers 미설치면 안내 메시지 출력 후 종료
- 설치 안내: `pip install sentence-transformers chromadb`
- 모델은 HuggingFace 캐시(`~/.cache/huggingface/`)에 자동 저장
- 오프라인 환경: 사전에 다운로드된 캐시가 있으면 정상 동작, 없으면 에러 메시지 출력

**청크 ID 및 재인덱싱:**
```
파일: 01-patterns/hooks/도입부-후킹-패턴.md
청크 0 ID: "01-patterns/hooks/도입부-후킹-패턴.md#0"
청크 1 ID: "01-patterns/hooks/도입부-후킹-패턴.md#1"

재인덱싱 시:
1. Chroma에서 file 메타데이터 == 해당 경로인 모든 ID 조회
2. 전량 delete
3. 새 청크 upsert
```

**Chroma 메타데이터 스키마:**
```python
{
    "file": "01-patterns/hooks/도입부-후킹-패턴.md",  # 볼트 내 상대경로
    "folder": "01-patterns",                          # 최상위 폴더명
    "tags": "hook,opening,style-dna",                 # frontmatter tags (쉼표 구분 문자열)
    "chunk_index": 0
}
```

### 3. VaultRAG 업그레이드

**파일:** `auto_agent/orchestrator/vault_rag.py` (수정)

```python
def semantic_search(
    self,
    query: str,
    top_k: int = 5,
    folder_filter: str = None   # "01-patterns" 등 최상위 폴더명
) -> list[dict]:
    """
    시맨틱 검색. 반환: [{"file": str, "snippet": str, "score": float, "tags": list}]
    - Chroma/sentence-transformers 미설치 → 키워드 폴백 (동일 구조 반환)
    - folder_filter: Chroma where={"folder": folder_filter} 적용
    """
```

`search_for_research` / `search_for_manuscript` 수정:
- `semantic_search` 호출 후 반환값(dict 리스트)을 기존 섹션 조합 로직에 맞게 처리
- 폴백 시 `_search_files` 결과를 `{"file": path.name, "snippet": snippet, "score": 0.0, "tags": []}` 구조로 통일

### 4. CLI 명령어

**파일:** `auto_agent/cli/vault_cmd.py` (신규)
**등록:** `auto_agent/cli.py`의 `COMMANDS` 딕셔너리에 `"vault": cmd_vault` 추가 (기존 패턴과 동일)

```
auto-agent vault index            # 변경된 파일만 재인덱싱
auto-agent vault index --force    # 전체 재인덱싱
auto-agent vault stats            # 인덱스 통계 (file_count, chunk_count, last_indexed_at 출력)
auto-agent vault search "쿼리"    # 터미널 검색 테스트 (결과 5개 출력)
```

### 5. 대시보드 API

**파일:** `auto_agent/dashboard/vault_routes.py` (신규)
**등록:** `app.py`에 `from auto_agent.dashboard.vault_routes import router as vault_router` + `app.include_router(vault_router)` — `memory_routes.py`와 동일한 방식

```
GET /api/vault/search?q=쿼리&top_k=5&folder=01-patterns
응답:
{
  "results": [
    {
      "file": "01-patterns/hooks/도입부-후킹-패턴.md",
      "snippet": "...(200자)...",
      "score": 0.87,
      "tags": ["hook", "opening"]
    }
  ],
  "query": "브랜드 스토리 후킹 방법",
  "total": 5,
  "mode": "semantic"   // "keyword" if fallback
}

GET /api/vault/stats
응답: VaultIndexer.get_stats() 그대로 반환
```

### 6. 대시보드 UI

**파일:** `auto_agent/dashboard/templates/vault_search.html` (신규)
**라우트:** `app.py`에 `GET /vault/search` 페이지 라우트 추가

- 기존 네비게이션(`templates/base.html` 또는 상단 바)에 "볼트 검색" 링크 추가
- 검색창 + 폴더 필터 드롭다운 (전체 / 01-patterns / 02-research / 03-analysis / ...)
- 결과 카드: 파일명, 폴더 배지, 유사도 점수, 스니펫
- 파일 클릭: `obsidian://open?vault=kairos-vault&file={url_encoded_relative_path}` 딥링크

---

## 의존성

```toml
# pyproject.toml [project.optional-dependencies] rag 그룹으로 추가
[project.optional-dependencies]
rag = [
    "sentence-transformers>=2.7",
    "chromadb>=0.5",
]
```

핵심 의존성에 포함하지 않는다. 파이프라인은 Chroma 없이도 키워드 폴백으로 동작한다.
설치: `pip install -e ".[rag]"`

---

## 에러 처리

| 상황 | 동작 |
|------|------|
| sentence-transformers/chromadb 미설치 | `semantic_search`에서 ImportError catch → 키워드 검색 폴백, 로그 출력 |
| Chroma DB 손상 | `VaultIndexer.index_all(force=True)`로 재구축 안내 |
| 해시 캐시 손상 | 해시 캐시만 초기화, Chroma는 유지. 전체 파일 해시 재계산 후 변경분만 재인덱싱 |
| 해시 캐시 ↔ Chroma 불일치 | `--force` 옵션으로 전체 재인덱싱. 불일치 자동 감지는 미구현 (향후) |
| 인덱싱 중 개별 파일 오류 | 해당 파일 skip, 에러 로그 출력, 계속 진행 |
| 모델 다운로드 실패(오프라인) | 에러 메시지 출력, 캐시 존재 시 캐시 사용 |
| 검색 쿼리 빈 문자열 | API 400 반환, `VaultRAG.semantic_search`는 빈 리스트 반환 |

---

## 테스트 기준

1. `auto-agent vault index` 실행 후 `auto-agent vault stats`에서 `chunk_count > 0` 확인
2. `auto-agent vault search "브랜드 스토리 후킹"` 결과에 `01-patterns/hooks/` 파일이 포함되는지 확인
3. Chroma/sentence-transformers 미설치 환경에서 파이프라인 실행 → 에러 없이 키워드 폴백 동작 확인
4. `/api/vault/search?q=AI` 응답에 `mode: "semantic"` 포함, 결과 5개 이하 확인
5. 동일 파일 두 번 인덱싱 후 `chunk_count`가 증가하지 않음을 확인 (중복 방지)
