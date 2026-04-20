# Stage 3 이미지 중복 생성 버그 조사 보고서

**조사 일자**: 2026-04-15  
**조사 범위**: `auto_agent/modules/image_batch_module.py`, `auto_agent/tools/image_assets.py`, `auto_agent/tools/image_search.py`, `auto_agent/tools/fal_queue.py`

---

## 증상

`images/search/` 디렉토리 안에 `scene_NNN_search_01.jpg` 형식의 정상 파일 외에 해시 이름 파일(`0ab0652f4c0d.jpg` 등)이 다수 생성됨.

실제 확인 (프로젝트 `68405937_자동차의_역사`):
```
search/ 전체 파일: 41개
  scene_* (선택된 파일): 14개
  해시명 고아 파일:       27개  ← 버그
```

---

## 재현 방법

```bash
# 검색 씬이 포함된 프로젝트에서 Stage 3 실행 후 확인
ls output/{project}/images/search/ | grep -v "scene_"
# → URL 해시명 파일들이 다수 존재하면 버그 발생 확인
```

---

## 실제 중복이 발생하는 정확한 지점

### Bug 1 (주요 버그): 검색 후보 파일 미정리

**파일**: `auto_agent/modules/image_batch_module.py`  
**함수**: `_run_search()`, 약 234~253번째 줄

`search_waterfall(query, limit=3)`은 최대 3개의 후보 이미지를 **모두 다운로드**하지만, `_run_search`는 `results[0]`만 사용하고 `results[1]`, `results[2]`는 정리하지 않는다.

```python
# image_batch_module.py _run_search()
results = searcher.search_waterfall(query, limit=3, preferred_aspect="16:9")
if results and results[0].local_path and Path(results[0].local_path).exists():
    best = results[0]  # ← 1번만 사용
    # results[1], results[2]는 search/ 디렉토리에 해시 파일로 남음
    dest = search_dl_dir / fname
    _sh.copy2(best.local_path, dest)
    try:
        Path(best.local_path).unlink(missing_ok=True)  # ← best만 삭제
    except Exception:
        pass
    # results[1].local_path, results[2].local_path → 삭제 안 함 ✗
```

**결과**: 씬 N당 최대 3개 파일 다운로드 → 1개 사용 → 2개 고아 파일 잔존  
14개 search 씬 × 평균 2개 고아 = ~28개 고아 파일 (실측 27개와 일치)

---

### Bug 2 (잠재적 레이스): `next_filename`이 락 없이 파일시스템 읽기

**파일**: `auto_agent/tools/image_assets.py`  
**함수**: `next_filename()`, 259번째 줄

```python
def next_filename(images_dir, scene_num, version_type, ext=".png"):
    # _file_lock 없이 glob 실행 ← 레이스 가능
    existing = list(sub_dir.glob(f"{prefix}*"))
    num = len(existing) + 1
    return f"{prefix}{num:02d}{ext}"
```

반면 `add_version()`은 `_file_lock`을 보유하며 쓰기.

현재 아키텍처에서는 `_run_generate`(source=generate)와 `_run_search` fallback(source=search)이 서로 다른 씬 번호를 처리하므로 실제 충돌은 발생하지 않는다. 그러나 향후 코드 변경이나 `scene_specs.json`에 중복 sceneNumber가 있을 경우 동일 파일명을 두 스레드가 동시에 계산할 수 있다.

---

### Bug 3 (설계 중복): SKILL.md가 `image_batch_module`을 B-1과 B-2에서 중복 호출

**파일**: `auto_agent/data/skills/agents/assembly-director/SKILL.md`

```
B-1 step 4: python3 -m auto_agent.modules.image_batch_module
            (주석: "캐릭터/씬 모두 image_batch_module이 일괄 처리")

B-2 step 1: python3 -m auto_agent.modules.image_batch_module
            (모든 씬 배치 생성)
```

`image_batch_module`은 캐릭터와 씬 이미지를 **한 번에 처리**한다. B-1에서 이미 전체 처리가 완료되므로 B-2는 `has_generated_version` 체크에 의해 전부 스킵된다.

**결과**: 불필요한 두 번째 모듈 실행. 실제 중복 생성은 없지만 혼란을 유발하고, 간혹 타이밍 이슈 시 FAL API 이중 호출 가능성 존재.

---

### Bug 4 (잠재적): runner의 step_3b 재시도 시 이미지 재생성

**파일**: `auto_agent/orchestrator/runner.py`, 2822번째 줄

`_is_retryable_error()`가 True를 반환하면 assembly-director가 **새 세션**으로 재시작된다. 새 세션은 SKILL.md B-1부터 다시 시작하므로 `image_batch_module`을 다시 호출한다.

두 번째 호출에서 `has_generated_version`이 True를 반환하면 스킵되어 정상이다. 단, 재시도 전에 `image_assets.json`이 손상됐거나 `generated/` 파일이 불완전하면 FAL API 재호출 가능성이 있다.

---

## Root Cause Hypothesis

**주요 원인**: `search_waterfall`이 N개 후보를 다운로드하는 것을 `_run_search`가 인지하지 못하고, 첫 번째 결과만 처리한 뒤 나머지 임시 파일을 정리하지 않음.

**부차 원인**: `next_filename`과 `add_version` 사이에 원자성이 없어 멀티스레드 환경에서 잠재적 레이스 존재.

---

## 관련 파일/함수/라인

| 파일 | 함수 | 라인 | 역할 |
|------|------|------|------|
| `image_batch_module.py` | `_run_search()` | ~234~256 | search 후보 미정리 ← 주요 버그 |
| `image_search.py` | `search_waterfall()` | 589~642 | 3개 후보 다운로드 |
| `image_search.py` | `download_image()` | 492~538 | 해시명으로 저장 |
| `image_assets.py` | `next_filename()` | 259~269 | 파일명 생성 (락 없음) |
| `image_assets.py` | `add_version()` | 175~202 | 파일 등록 (락 있음) |
| `SKILL.md` (assembly-director) | B-1 / B-2 단계 | ~ | 중복 모듈 호출 설계 |

---

## 수정 제안

### Fix 1 (즉시): `_run_search`에서 미사용 후보 파일 정리

```python
# image_batch_module.py _run_search()
results = searcher.search_waterfall(query, limit=3, preferred_aspect="16:9")
if results and results[0].local_path and ...:
    best = results[0]
    # 나머지 후보 파일 정리 ← 추가
    for unused in results[1:]:
        if unused.local_path:
            try:
                Path(unused.local_path).unlink(missing_ok=True)
            except Exception:
                pass
    # ... 기존 로직
```

또는 `search_waterfall(limit=1)`로 줄이고, 품질 검수는 `limit=1`이어도 충분한 경우.

### Fix 2 (권고): `next_filename`에 락 추가

```python
def next_filename(images_dir, scene_num, version_type, ext=".png"):
    with _file_lock:  # ← 추가
        prefix = f"scene_{scene_num:03d}_{version_type}_"
        sub_dir = images_dir / ("generated" if version_type == "gen" else "search")
        existing = list(sub_dir.glob(f"{prefix}*")) if sub_dir.exists() else []
        num = len(existing) + 1
        return f"{prefix}{num:02d}{ext}"
```

### Fix 3 (SKILL.md 개선): B-1에서 캐릭터 전용 설명 명확화

B-1에서 `image_batch_module`이 씬도 함께 처리한다는 것을 명시하거나, B-2 호출을 제거하여 혼란 방지.

---

## 비고

- `image_assets.json`의 `scenes` 배열에는 중복 없음 확인 (정상)  
- FAL API 이중 호출(비용 낭비)은 단일 실행 시에는 발생하지 않음. runner 재시도 시에만 가능
- 고아 해시 파일은 `image_assets.json`에 등록되지 않으므로 렌더링에 영향 없음. 디스크 낭비만 발생
