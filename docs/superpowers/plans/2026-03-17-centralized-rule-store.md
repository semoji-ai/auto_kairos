# Centralized Rule Store Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프롬프트/스킬/파이프라인 설정을 Supabase에 중앙 관리하여 소스코드 배포 없이 규칙을 업데이트하고, 팀 전원이 동일 규칙으로 작업할 수 있게 한다.

**Architecture:** Supabase `rule_store` 테이블에 규칙 파일을 텍스트로 저장. Runner는 파이프라인 시작 시 1회 fetch → `.rules_cache/`에 저장 → 실행 중 캐시에서 로드. `file_versions` 테이블을 확장하여 규칙 버전 히스토리 관리. 모든 파일 I/O는 UTF-8 + LF 강제로 윈도우/맥 호환.

**Tech Stack:** Python 3.9+, Supabase (PostgreSQL + Python SDK), pathlib

---

## File Structure

| 파일 | 역할 |
|------|------|
| **Create:** `auto_agent/rule_manager.py` | RuleManager 클래스 — fetch/load/push/rollback 핵심 로직 |
| **Create:** `auto_agent/data/rule_store_schema.sql` | rule_store 테이블 + rule_versions 테이블 DDL |
| **Create:** `auto_agent/scripts/rules_cli.py` | CLI 진입점 — `python -m auto_agent.scripts.rules_cli push/pull/rollback/list` |
| **Modify:** `auto_agent/orchestrator/runner.py` | RuleManager 통합 — _load_pipeline, _load_agents_config, _build_from_prompt_file 교체 |
| **Modify:** `auto_agent/supabase_client.py` | supabase_enabled() 재사용 (변경 없을 수 있음) |

---

## Chunk 1: Supabase 스키마 + RuleManager 코어

### Task 1: rule_store 테이블 DDL 작성

**Files:**
- Create: `auto_agent/data/rule_store_schema.sql`

- [ ] **Step 1: DDL 파일 작성**

```sql
-- rule_store: 규칙 파일 중앙 저장소
CREATE TABLE IF NOT EXISTS rule_store (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    rule_type   TEXT NOT NULL
                CHECK (rule_type IN ('prompt','pipeline','agent_config','skill','artstyle')),
    checksum    TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  TEXT DEFAULT 'system'
);

CREATE INDEX idx_rule_store_type ON rule_store(rule_type);

-- rule_versions: 규칙 변경 히스토리
CREATE TABLE IF NOT EXISTS rule_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key    TEXT NOT NULL,
    version     INTEGER NOT NULL,
    content     TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    description TEXT,
    created_by  TEXT DEFAULT 'system',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(rule_key, version)
);

CREATE INDEX idx_rule_versions_key ON rule_versions(rule_key, version DESC);

-- updated_at 자동 갱신
CREATE TRIGGER trg_rule_store_updated_at
    BEFORE UPDATE ON rule_store
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

- [ ] **Step 2: Supabase 대시보드에서 SQL 실행하여 테이블 생성**

Run: Supabase Dashboard → SQL Editor → 위 DDL 실행

- [ ] **Step 3: Commit**

```bash
git add auto_agent/data/rule_store_schema.sql
git commit -m "feat: rule_store + rule_versions 테이블 DDL 추가"
```

---

### Task 2: RuleManager 코어 클래스 구현

**Files:**
- Create: `auto_agent/rule_manager.py`

- [ ] **Step 1: RuleManager 클래스 작성**

```python
"""
중앙 규칙 관리자.

규칙 파일(프롬프트, 스킬, 파이프라인 설정)을 Supabase에 저장/조회하고
로컬 캐시(.rules_cache/)를 통해 오프라인 실행을 지원한다.

크로스플랫폼 안전 규칙:
- 모든 파일 I/O는 encoding="utf-8"
- rule_store key는 항상 / 구분자 (POSIX)
- content는 항상 LF 줄바꿈
- checksum은 UTF-8 바이트 기준 SHA-256
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Optional

from auto_agent.supabase_client import get_supabase, supabase_enabled

# 로컬 data/ 디렉토리 (fallback)
DATA_DIR = Path(__file__).parent / "data"

# 규칙 파일 → (rule_store key, rule_type) 매핑
RULE_MANIFEST = {
    # 1턴 프롬프트
    "prompts/single-call/creative-direction.md": "prompt",
    "prompts/single-call/asset-advisory.md": "prompt",
    "prompts/single-call/data-enrichment.md": "prompt",
    # 파이프라인 설정
    "pipeline.json": "pipeline",
    "agents.json": "agent_config",
    # 에이전트 스킬
    "skills/agents/character-planner/SKILL.md": "skill",
    "skills/agents/fact-verifier/SKILL.md": "skill",
    "skills/agents/qa-reviewer/SKILL.md": "skill",
    "skills/agents/research-orchestrator/SKILL.md": "skill",
    "skills/agents/visual-composer/SKILL.md": "skill",
    "skills/agents/write-manuscript/SKILL.md": "skill",
    # 공유 스킬 (플랫 파일)
    "skills/shared/chart-mapping.md": "skill",
    "skills/shared/data-mapping.md": "skill",
    "skills/shared/image-generation.md": "skill",
    "skills/shared/korean-tts-rules.md": "skill",
    "skills/shared/motion-rhythm.md": "skill",
    "skills/shared/outline-template.md": "skill",
    "skills/shared/remotion-design-system.md": "skill",
    "skills/shared/research-format.md": "skill",
    "skills/shared/scene-segmentation.md": "skill",
    "skills/shared/tts-verification.md": "skill",
    "skills/shared/writing-style.md": "skill",
    "skills/shared/writing-style-iromism.md": "skill",
    "skills/shared/writing-style-semoji.md": "skill",
    "skills/shared/research-requirements-semoji.md": "skill",
    # 공유 스킬 (디렉토리 — SKILL.md + references/)
    "skills/shared/asset-advisory/SKILL.md": "skill",
    "skills/shared/asset-advisory/references/examples.md": "skill",
    "skills/shared/asset-advisory/references/perspectives.md": "skill",
    "skills/shared/asset-advisory/references/cross-review.md": "skill",
    "skills/shared/creative-direction/SKILL.md": "skill",
    "skills/shared/creative-direction/references/process.md": "skill",
    "skills/shared/creative-direction/references/patterns.md": "skill",
    "skills/shared/creative-direction/references/examples-palette.md": "skill",
}


def _checksum(content: str) -> str:
    """UTF-8 바이트 기준 SHA-256."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _normalize(content: str) -> str:
    """CRLF → LF 통일."""
    return content.replace("\r\n", "\n")


class RuleManager:
    """중앙 규칙 저장소 관리자."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or (DATA_DIR.parent / ".rules_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._enabled = supabase_enabled()

    # ── Fetch (중앙 → 로컬 캐시) ──

    def fetch_all(self) -> int:
        """중앙에서 전체 규칙 fetch → 로컬 캐시 저장. 변경된 파일 수 리턴."""
        if not self._enabled:
            return 0

        sb = get_supabase()
        resp = sb.table("rule_store").select("key, content, checksum").execute()
        rows = resp.data or []

        changed = 0
        for row in rows:
            key = row["key"]
            content = row["content"]
            remote_checksum = row["checksum"]

            cache_path = self._cache_path(key)

            # 로컬 캐시와 checksum 비교
            if cache_path.exists():
                local_content = cache_path.read_text(encoding="utf-8")
                if _checksum(local_content) == remote_checksum:
                    continue

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(content, encoding="utf-8")
            changed += 1

        return changed

    # ── Load (캐시 → fallback 로컬) ──

    def load(self, key: str) -> str:
        """규칙 로드. 캐시 → 로컬 data/ 순서."""
        # 1순위: 캐시
        cache_path = self._cache_path(key)
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        # 2순위: 로컬 data/
        local_path = DATA_DIR / PurePosixPath(key)
        if local_path.exists():
            return local_path.read_text(encoding="utf-8")

        raise FileNotFoundError(f"규칙을 찾을 수 없습니다: {key}")

    def load_json(self, key: str) -> dict:
        """JSON 규칙 로드."""
        return json.loads(self.load(key))

    # ── Push (로컬 → 중앙) ──

    def push(self, key: str, content: str, updated_by: str = "system",
             description: str = "") -> dict:
        """규칙을 중앙에 push + 버전 기록."""
        if not self._enabled:
            raise RuntimeError("Supabase 미연결 — push 불가")

        content = _normalize(content)
        cs = _checksum(content)
        rule_type = RULE_MANIFEST.get(key, "skill")

        sb = get_supabase()

        # 기존 버전 조회 (버전 번호 결정)
        existing = sb.table("rule_store").select("checksum").eq("key", key).execute()
        if existing.data:
            old_checksum = existing.data[0]["checksum"]
            if old_checksum == cs:
                return {"status": "unchanged", "key": key}

            # 이전 content를 버전 히스토리에 저장
            old_content_resp = sb.table("rule_store").select("content").eq("key", key).execute()
            if old_content_resp.data:
                # 최신 버전 번호 조회
                ver_resp = (sb.table("rule_versions")
                            .select("version")
                            .eq("rule_key", key)
                            .order("version", desc=True)
                            .limit(1)
                            .execute())
                next_ver = (ver_resp.data[0]["version"] + 1) if ver_resp.data else 1

                sb.table("rule_versions").insert({
                    "rule_key": key,
                    "version": next_ver,
                    "content": old_content_resp.data[0]["content"],
                    "checksum": old_checksum,
                    "description": description or f"v{next_ver} before update",
                    "created_by": updated_by,
                }).execute()

        # upsert
        sb.table("rule_store").upsert({
            "key": key,
            "content": content,
            "rule_type": rule_type,
            "checksum": cs,
            "updated_by": updated_by,
        }, on_conflict="key").execute()

        # 로컬 캐시도 갱신
        cache_path = self._cache_path(key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")

        return {"status": "pushed", "key": key, "checksum": cs}

    def push_all(self, updated_by: str = "system") -> dict:
        """RULE_MANIFEST의 모든 로컬 파일을 중앙에 push."""
        results = {"pushed": 0, "unchanged": 0, "missing": 0}
        for key in RULE_MANIFEST:
            local_path = DATA_DIR / PurePosixPath(key)
            if not local_path.exists():
                results["missing"] += 1
                continue
            content = local_path.read_text(encoding="utf-8")
            r = self.push(key, content, updated_by=updated_by)
            if r["status"] == "pushed":
                results["pushed"] += 1
            else:
                results["unchanged"] += 1
        return results

    # ── Rollback ──

    def rollback(self, key: str, version: int) -> dict:
        """특정 버전으로 롤백."""
        if not self._enabled:
            raise RuntimeError("Supabase 미연결 — rollback 불가")

        sb = get_supabase()
        ver_resp = (sb.table("rule_versions")
                    .select("content, checksum")
                    .eq("rule_key", key)
                    .eq("version", version)
                    .execute())
        if not ver_resp.data:
            raise ValueError(f"버전 {version}을 찾을 수 없습니다: {key}")

        old = ver_resp.data[0]
        # 현재를 버전 히스토리에 저장 후 롤백
        return self.push(key, old["content"],
                         updated_by="rollback",
                         description=f"rollback to v{version}")

    # ── List Versions ──

    def list_versions(self, key: str) -> list:
        """버전 히스토리 조회."""
        if not self._enabled:
            return []
        sb = get_supabase()
        resp = (sb.table("rule_versions")
                .select("version, checksum, description, created_by, created_at")
                .eq("rule_key", key)
                .order("version", desc=True)
                .execute())
        return resp.data or []

    # ── 아트스타일 (공유/개인) ──

    def push_artstyle(self, style_name: str, content: str,
                      updated_by: str = "system") -> dict:
        """아트스타일 프리셋을 중앙에 push."""
        key = f"artstyle/styles/{style_name}.json"
        return self.push(key, content, updated_by=updated_by)

    def list_artstyles(self) -> list:
        """중앙에 등록된 아트스타일 목록."""
        if not self._enabled:
            return []
        sb = get_supabase()
        resp = (sb.table("rule_store")
                .select("key, updated_at, updated_by")
                .eq("rule_type", "artstyle")
                .execute())
        return resp.data or []

    # ── Internal ──

    def _cache_path(self, key: str) -> Path:
        """key → 로컬 캐시 경로 변환."""
        return self.cache_dir / PurePosixPath(key)
```

- [ ] **Step 2: 임포트 테스트**

Run: `python3 -c "from auto_agent.rule_manager import RuleManager; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add auto_agent/rule_manager.py
git commit -m "feat: RuleManager — 중앙 규칙 fetch/load/push/rollback"
```

---

## Chunk 2: CLI 도구 + Runner 통합

### Task 3: rules CLI 스크립트 작성

**Files:**
- Create: `auto_agent/scripts/rules_cli.py`

- [ ] **Step 1: CLI 스크립트 작성**

```python
"""
규칙 중앙 관리 CLI.

사용법:
    python -m auto_agent.scripts.rules_cli push_all          # 로컬 전체 → 중앙
    python -m auto_agent.scripts.rules_cli push <key>        # 단일 파일 push
    python -m auto_agent.scripts.rules_cli fetch             # 중앙 → 로컬 캐시
    python -m auto_agent.scripts.rules_cli list <key>        # 버전 히스토리
    python -m auto_agent.scripts.rules_cli rollback <key> <version>
    python -m auto_agent.scripts.rules_cli diff <key>        # 로컬 vs 중앙 비교
"""
import argparse
import sys
from pathlib import Path, PurePosixPath

from auto_agent.rule_manager import RuleManager, DATA_DIR, _checksum, _normalize


def main():
    parser = argparse.ArgumentParser(description="Kairos Rule Store CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("push_all", help="로컬 규칙 전체를 중앙에 push")
    sub.add_parser("fetch", help="중앙 규칙을 로컬 캐시로 fetch")

    p_push = sub.add_parser("push", help="단일 규칙 파일 push")
    p_push.add_argument("key", help="규칙 key (예: prompts/single-call/creative-direction.md)")

    p_list = sub.add_parser("list", help="버전 히스토리 조회")
    p_list.add_argument("key", help="규칙 key")

    p_rb = sub.add_parser("rollback", help="특정 버전으로 롤백")
    p_rb.add_argument("key")
    p_rb.add_argument("version", type=int)

    p_diff = sub.add_parser("diff", help="로컬 vs 중앙 비교")
    p_diff.add_argument("key")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    rm = RuleManager()

    if args.command == "push_all":
        result = rm.push_all(updated_by="cli")
        print(f"Push 완료: {result['pushed']}개 업데이트, "
              f"{result['unchanged']}개 변경 없음, "
              f"{result['missing']}개 파일 없음")

    elif args.command == "fetch":
        changed = rm.fetch_all()
        print(f"Fetch 완료: {changed}개 파일 갱신")

    elif args.command == "push":
        local_path = DATA_DIR / PurePosixPath(args.key)
        if not local_path.exists():
            print(f"ERROR: 파일 없음 — {local_path}")
            sys.exit(1)
        content = local_path.read_text(encoding="utf-8")
        result = rm.push(args.key, content, updated_by="cli")
        print(f"{result['status']}: {args.key}")

    elif args.command == "list":
        versions = rm.list_versions(args.key)
        if not versions:
            print("버전 히스토리 없음")
            return
        for v in versions:
            print(f"  v{v['version']}  {v['created_at'][:19]}  "
                  f"{v['created_by']:<10}  {v.get('description', '')}")

    elif args.command == "rollback":
        result = rm.rollback(args.key, args.version)
        print(f"롤백 완료: {args.key} → v{args.version}")

    elif args.command == "diff":
        local_path = DATA_DIR / PurePosixPath(args.key)
        if not local_path.exists():
            print(f"로컬 파일 없음: {local_path}")
            sys.exit(1)
        local_content = _normalize(local_path.read_text(encoding="utf-8"))
        try:
            remote_content = rm.load(args.key)
            # 캐시에서 로드된 것이 중앙 버전
        except FileNotFoundError:
            print("중앙에 등록되지 않은 규칙")
            sys.exit(1)
        if _checksum(local_content) == _checksum(remote_content):
            print("동일 (변경 없음)")
        else:
            # 간단한 라인 수 비교
            local_lines = local_content.splitlines()
            remote_lines = remote_content.splitlines()
            print(f"차이 있음: 로컬 {len(local_lines)}줄 vs 중앙 {len(remote_lines)}줄")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CLI 실행 테스트**

Run: `python3 -m auto_agent.scripts.rules_cli --help`
Expected: 도움말 출력

- [ ] **Step 3: Commit**

```bash
git add auto_agent/scripts/rules_cli.py
git commit -m "feat: rules CLI — push/fetch/rollback/diff 명령어"
```

---

### Task 4: Runner에 RuleManager 통합

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:217` (\_\_init\_\_에 RuleManager 추가)
- Modify: `auto_agent/orchestrator/runner.py:247-250` (_load_pipeline 교체)
- Modify: `auto_agent/orchestrator/runner.py:2177-2183` (_load_agents_config 교체)
- Modify: `auto_agent/orchestrator/runner.py` (_build_from_prompt_file 교체)
- Modify: `auto_agent/orchestrator/runner.py` (_build_agent_prompt 스킬 로드 교체)

- [ ] **Step 1: __init__에 RuleManager 초기화 + fetch 추가**

runner.py `__init__` 메서드에서 `self.pipeline = self._load_pipeline()` 직전에:

```python
from auto_agent.rule_manager import RuleManager
self.rule_manager = RuleManager()
if supabase_enabled():
    changed = self.rule_manager.fetch_all()
    if changed:
        print(f"[Rules] 중앙 규칙 {changed}개 갱신됨")
```

- [ ] **Step 2: _load_pipeline 교체**

```python
def _load_pipeline(self) -> dict:
    try:
        return self.rule_manager.load_json("pipeline.json")
    except FileNotFoundError:
        path = DATA_DIR / "pipeline.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
```

- [ ] **Step 3: _load_agents_config 교체**

```python
def _load_agents_config(self) -> dict:
    if not hasattr(self, "_agents_cache"):
        try:
            self._agents_cache = self.rule_manager.load_json("agents.json")
        except FileNotFoundError:
            path = DATA_DIR / "agents.json"
            with open(path, "r", encoding="utf-8") as f:
                self._agents_cache = json.load(f)
    return self._agents_cache
```

- [ ] **Step 4: _build_from_prompt_file에서 RuleManager 사용**

```python
def _build_from_prompt_file(self, step, chapter_specs, prompt_file):
    # 기존: prompt_path = DATA_DIR / "prompts" / "single-call" / prompt_file
    #       template = prompt_path.read_text(encoding="utf-8")
    # 변경:
    template = self.rule_manager.load(f"prompts/single-call/{prompt_file}")
    # ... 나머지 동일
```

- [ ] **Step 5: _build_agent_prompt / _build_chapter_prompt_generic에서 스킬 로드 교체**

기존 `skill_path.read_text(encoding="utf-8")` 호출을 `rule_manager.load()` 로 교체:

```python
# 에이전트 스킬
skill_key = f"skills/agents/{agent_name}/SKILL.md"
try:
    agent_skill = self.rule_manager.load(skill_key)
except FileNotFoundError:
    agent_skill = ""

# 공유 스킬 (디렉토리 or 플랫 파일)
# 기존 로직의 read_text 호출을 rule_manager.load로 교체
```

- [ ] **Step 6: 임포트 테스트**

Run: `python3 -c "from auto_agent.orchestrator.runner import PipelineRunner; print('OK')"`
Expected: OK

- [ ] **Step 7: Commit**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "feat: Runner에 RuleManager 통합 — 중앙 규칙 fetch/load"
```

---

## Chunk 3: 초기 데이터 업로드 + 검증

### Task 5: 초기 규칙 push + 검증

- [ ] **Step 1: Supabase에 rule_store, rule_versions 테이블 생성**

Run: Supabase Dashboard → SQL Editor → `auto_agent/data/rule_store_schema.sql` 실행

- [ ] **Step 2: 로컬 규칙 전체 push**

Run: `set -a && source .env && set +a && python3 -m auto_agent.scripts.rules_cli push_all`
Expected: `Push 완료: NN개 업데이트, 0개 변경 없음, 0개 파일 없음`

- [ ] **Step 3: fetch 테스트 (캐시 삭제 후 재다운로드)**

```bash
rm -rf auto_agent/.rules_cache
python3 -m auto_agent.scripts.rules_cli fetch
```
Expected: `Fetch 완료: NN개 파일 갱신`

- [ ] **Step 4: 파이프라인 실행 테스트 (step_6만)**

```bash
python3 -m auto_agent.orchestrator.runner --project 이란_위기와_글로벌_경제 --only step_6 --dry-run
```
Expected: 규칙 fetch 메시지 출력 + dry-run 정상 동작

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: 초기 규칙 push 완료 + .rules_cache gitignore"
```

---

### Task 6: .gitignore에 캐시 디렉토리 추가

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: .gitignore에 추가**

```
# Rule cache (fetched from Supabase)
auto_agent/.rules_cache/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: .rules_cache를 gitignore에 추가"
```
