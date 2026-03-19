# 프로젝트 ID 마이그레이션 — slug → uuid_{slug}

> 날짜: 2026-03-19
> 적용 범위: 글로벌 (전체 파이프라인 + 대시보드 + CLI)

## 배경

kairos-app에서 프로젝트 ID(8자 hex)를 도입했으나, auto_kairos_v3 파이프라인은 여전히 slug 기반. 앱-파이프라인 통일 + slug 중복 방지를 위해 uuid 기반으로 마이그레이션.

## 핵심 결정

- **폴더 구조**: `output/{uuid}_{slug}/` (예: `b3cef462_이로미즘_양자컴퓨터_1min`)
- **식별자**: 8자 hex uuid가 primary, slug는 가독성용으로 병존
- **CLI 호환**: `--project b3cef462` (uuid) 또는 `--project 이로미즘_양자컴퓨터_1min` (slug) 둘 다 허용
- **uuid 생성**: kairos-app과 auto_kairos_v3 양쪽에서 생성 가능
- **기존 프로젝트**: 마이그레이션 스크립트로 10개 전부 전환

## 변경 1: DB 스키마 + uuid 생성

### schema.sql
projects 테이블에 uuid 컬럼 추가:
```sql
uuid TEXT NOT NULL DEFAULT '',
```

### project_manager.py

uuid 자동 생성:
```python
import uuid as _uuid

def _generate_project_uuid() -> str:
    """8자 hex 프로젝트 ID 생성."""
    return _uuid.uuid4().hex[:8]
```

create_project() 변경:
- uuid 인자 추가 (optional, 없으면 자동 생성)
- output_dir을 `output/{uuid}_{slug}` 형태로 생성

get_project() 확장:
- uuid로도 조회 가능: `get_project(uuid="b3cef462")`

resolve_project() 신규:
```python
def resolve_project(self, identifier: str) -> dict:
    """uuid(8자 hex) 또는 slug로 프로젝트 조회."""
    if len(identifier) == 8 and all(c in '0123456789abcdef' for c in identifier):
        return self.get_project(uuid=identifier) or self.get_project(slug=identifier)
    return self.get_project(slug=identifier)
```

## 변경 2: 경로 중앙화 — resolve_project_dir

### 문제
각 모듈이 `output/{slug}/` 를 직접 조합 → uuid 전환 시 모든 모듈을 수정해야 함.

### 해결
ProjectManager에 경로 메서드를 집중하고, 각 모듈은 DB의 output_dir를 사용:

```python
def get_project_dir(self, project_id=None, uuid=None, slug=None) -> Path:
    """프로젝트 output 디렉토리. DB의 output_dir 반환."""
    project = self._resolve(project_id, uuid, slug)
    return Path(project["output_dir"])

def get_manifest_path(self, project_id=None, uuid=None, slug=None) -> Path:
    """매니페스트 경로: manifests/{uuid}_{slug}.json"""
    project = self._resolve(project_id, uuid, slug)
    return get_workspace_dir() / "remotion" / "public" / "manifests" / f"{project['uuid']}_{project['slug']}.json"
```

### 수정 대상

| 파일 | 현재 | 변경 |
|------|------|------|
| runner.py | `output / slug` 직접 조합 | `pm.get_project_dir(project_id)` |
| cli.py | `--project slug` → 경로 직접 조합 | `pm.resolve_project(identifier)` |
| session_manager.py | `output / project_slug / logs` | `pm.get_project_dir() / "logs"` |
| remotion_bridge.py | `manifests / f"{slug}.json"` | `pm.get_manifest_path()` |
| build_manifest.py | `manifests / f"{storage_key}.json"` | `pm.get_manifest_path()` |
| app.py | `/output/{slug}/images/...` | `pm.get_project_dir()` 기반 URL |
| project_paths.py | slug 기반 경로 결정 | `pm.resolve_project()` 활용 |
| vault_rag.py | `07-projects/{slug}/` | uuid 기반 경로 |

## 변경 3: 마이그레이션 스크립트

### migrate_to_uuid.py (신규)

```
1. DB 백업 (auto_agent.db → auto_agent.db.bak)
2. uuid가 비어있는 프로젝트에 uuid 생성
3. 폴더 rename: output/{slug} → output/{uuid}_{slug}
4. DB output_dir 업데이트
5. 매니페스트 rename: manifests/{slug}.json → manifests/{uuid}_{slug}.json
6. 검증: 모든 output_dir이 실제 존재하는지
```

### 안전장치
- `--dry-run`: 실제 변경 없이 미리보기
- rename 전 폴더 존재 확인 (없으면 스킵)
- rollback 정보 JSON 기록
- DB 업데이트는 단일 트랜잭션

## 변경 4: CLI 호환

cli.py의 `--project` 인자 처리:
```python
# 8자 hex면 uuid, 아니면 slug
project = pm.resolve_project(identifier)
```

## 수정 대상 파일 전체

| # | 파일 | 변경 내용 |
|---|------|-----------|
| 1 | `auto_agent/db/schema.sql` | uuid 컬럼 추가 |
| 2 | `auto_agent/db/project_manager.py` | uuid 생성, resolve_project(), 경로 메서드 |
| 3 | `auto_agent/db/migrate_to_uuid.py` | 신규 — 마이그레이션 스크립트 |
| 4 | `auto_agent/orchestrator/runner.py` | slug 직접 조합 → pm 경로 메서드 |
| 5 | `auto_agent/cli.py` | --project uuid/slug 양쪽 허용 |
| 6 | `auto_agent/session_manager.py` | 세션 파일명 변경 |
| 7 | `auto_agent/tools/remotion_bridge.py` | manifest 경로 중앙화 |
| 8 | `auto_agent/scripts/build_manifest.py` | manifest 경로 중앙화 |
| 9 | `auto_agent/scripts/project_paths.py` | resolve_project() 활용 |
| 10 | `app.py` | URL 경로 uuid_{slug} 반영 |
| 11 | `auto_agent/orchestrator/vault_rag.py` | 볼트 경로 uuid 반영 |
| 12 | `auto_agent/data/CLAUDE.md.template` | 경로 안내 업데이트 |
