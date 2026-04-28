# URL UUID 라우팅 전환 — slug → uuid 정본화

> 날짜: 2026-04-28
> 적용 범위: 대시보드 백엔드 라우트 + 프론트 fetch + Remotion 정적 경로
> 선행 작업: `2026-03-19-project-id-migration-design.md` (uuid 도입은 완료된 상태)

## 배경

대시보드 URL이 한글 slug 기반(`/p/포켓몬스터30주년...`)이라 발생한 문제:

1. **이중 인코딩 버그** — `window.location.pathname`이 인코딩된 상태로 반환되고, 후속 `encodeURIComponent` 호출에서 `%`가 다시 `%25`로 인코딩되어 서버 404. (오늘 1줄 hotfix `decodeURIComponent`로 임시 차단했으나 근본 해결 아님)
2. **취약성의 근원** — slug가 시스템 식별자로 쓰이는 한 같은 부류의 인코딩 버그가 다른 진입점에서 또 터질 수 있음.
3. **변수명 거짓말 누적 위험** — A안(slug 라우트에 uuid를 넘기는 식)은 변수명 부채만 쌓음.

DB에는 이미 `projects.uuid` (8자 hex)가 도입돼 있으므로(2026-03-19), URL/코드 정본만 uuid로 전환하면 한글이 시스템 경로에서 사라진다. **디렉토리명은 사람 인식을 위해 `{uuid}_{slug}` 그대로 유지** — slug는 라벨일 뿐, 시스템은 uuid prefix만 식별자로 사용.

## 핵심 결정

| 항목 | 결정 |
|------|------|
| URL 식별자 | 8자 hex uuid (예: `9f202fb4`) |
| 디렉토리명 | `output/{uuid}_{slug}/` 그대로 유지 — 사람용 라벨 |
| slug의 역할 | DB 컬럼 + 화면 표시(대시보드 카드, 디스코드 알림) 전용. 시스템 식별자 아님. |
| 기존 slug 라우트 | 영구 301 redirect 유지 (외부 북마크/옛 디스코드 링크 호환) |
| 검증 방법 | A(수동 클릭 체크리스트) + C(grep 카운터) 조합 |
| 단계화 | 4-Phase, 단계별 회귀 검수 후 진행 |

## 단계 설계

### Phase 1 — 백엔드 라우트 신설 + slug redirect 전환

**목표**: 모든 라우트가 uuid를 정본으로 받고, slug 라우트는 uuid로 redirect만 하는 thin wrapper로 전환. 프론트는 아직 slug 사용 중이지만 자동 redirect로 흡수됨.

**변경**
- `app.py`의 `/p/{slug}`, `/api/p/{slug}/...` 38개 라우트를 uuid 받는 형태로 시그니처 변경
  - 패턴: `@app.get("/p/{uuid}")` async def `project_by_uuid(uuid: str, ...)`, 내부에서 `pm.get_project(uuid=uuid)`
- 별도 thin redirect 핸들러 추가
  - `@app.get("/p/{slug}")` (priority 낮게) — `pm.get_project(slug=slug)` → 301 to `/p/{project["uuid"]}`
  - 모든 `/api/p/{slug}/...` 동일 패턴
- 라우트 우선순위 충돌 회피: FastAPI는 등록 순서 우선이므로 uuid 라우트를 먼저 등록. uuid는 `^[a-f0-9]{8}$` 정규식 path converter로 제약(slug와 명확히 구분).

**검증 (A)**
- 대시보드 9개 탭 클릭 (브라우저 주소창에 slug URL 입력 → uuid로 redirect 확인)
- 씬에디터 진입 (slug → uuid redirect)
- 이미지 교체 API (slug 그대로 호출 → 301 → uuid → 200 OK)

**검증 (C)**
- `grep "/p/{slug}" app.py` → 0 (slug 라우트는 redirect만 남아야 함)
- `grep -r "pm.get_project(slug=" app.py auto_agent/dashboard/` → redirect 핸들러 외 0

**롤백**: Phase 1 commit revert로 복귀 (프론트 미변경이라 안전)

---

### Phase 2 — 프론트 fetch 영역별 점진 전환

**목표**: 프론트에서 사용하는 식별자를 slug → uuid로 전환. 영역별로 끊어서 회귀 표면 최소화.

**변경 단위 (각각 독립 커밋)**
1. **글로벌 주입** — `_load_tab_data()`에서 `context["uuid"] = project["uuid"]` 추가, `project.html` base에 `window.PROJECT_UUID = '{{ uuid }}'` 정의
2. **storyboard** — `_storyboard.html`, `_storyboard_scene.html`의 fetch 사이트 (~50개) — `slug` → `PROJECT_UUID` 치환, 변수명도 `projectUuid`로 정직화
3. **scene editor** — `scene-editor.js`, `_studio.html` (~30개)
4. **assets/enrichment** — `_assets.html`, `_enrichment.html` (~20개)
5. **upload/multi/research** — `_upload_info.html`, `_multiformat.html`, `_research.html` (~30개)
6. **map editor** — `map-editor.js` (~5개)

**원칙**
- 각 단위 작업 후 즉시 커밋 + Phase별 grep 카운터로 미전환 사이트 추적
- `encodeURIComponent` 호출은 그대로 둬도 무방 (uuid는 ASCII라 no-op이지만 방어 코드로 유지)

**검증 (A) — 영역별**
- storyboard 단위 종료: 스토리보드 탭 진입, 씬 split, 이미지 교체, 에셋 타입 변경
- scene editor 단위 종료: 씬에디터 진입, 저장, manifest 재빌드 트리거
- ... (영역별로 해당 기능 손으로 1회씩)

**검증 (C) — 영역별**
- `grep -rn "'/api/p/' + slug\|'/api/p/' + encodeURIComponent(slug)\|'/p/' + slug" auto_agent/dashboard/templates/ auto_agent/dashboard/static/`
- 각 단위 종료 시 카운터 감소 확인. 전체 종료 시 0.

**롤백**: 단위별 커밋이라 문제 영역만 revert 가능

---

### Phase 3 — Remotion 번들 + 정적 자원 경로

**목표**: Remotion 번들 빌드 시점에 박혀있는 `/p/{slug}/background/...` 같은 정적 경로를 uuid 기반으로 전환.

**변경**
- `build_manifest.py`에서 매니페스트의 base URL 생성 시 slug → uuid
- `app.py:129`의 `/p/{slug}/background/{file_path:path}` 라우트는 redirect 형태로 유지 (이미 빌드된 옛 번들 호환)
- 신규 `/p/{uuid}/background/{file_path:path}` 추가
- 기존 프로젝트 매니페스트 재빌드 (`auto-agent` CLI에 일괄 재빌드 명령 추가 또는 1회성 스크립트)

**검증 (A)**
- 신규 프로젝트 1개 Stage 3 완주 → Remotion 미리보기에서 배경 이미지 정상 로드
- 기존 프로젝트(slug 매니페스트) 1개 → 옛 URL로도 배경 로드 가능 (redirect 동작)
- 매니페스트 재빌드 후 → uuid URL로 배경 로드

**검증 (C)**
- `grep -rn "/p/.*slug.*background\|/p/.*\${slug}/background" auto_agent/` → 0

**롤백**: 매니페스트 재빌드는 멱등적이라 안전. 라우트 변경은 commit revert.

---

### Phase 4 — 정리 + deprecation 표시

**목표**: 잔존 slug 사용처 점검 및 향후 부주의한 재도입 방지.

**변경**
- `docs/rules/path-env-rules.md`에 룰 추가: "URL/fetch에서 식별자는 uuid 사용, slug는 표시 전용"
- slug redirect 핸들러에 `logger.info("[deprecation] slug route used: %s", slug)` 추가 — 어디서 옛 링크가 들어오는지 모니터링용
- CLAUDE.md에 한 줄 추가: "프로젝트 식별자는 uuid (8자 hex), URL 경로는 `/p/{uuid}`. slug는 사람용 라벨."
- 1주일 모니터링 후 redirect 로그 확인. 여전히 호출되면 진입점 파악 후 그 진입점도 uuid로 전환.

**검증 (A)**
- 전체 회귀 1회 (모든 탭 클릭 + 씬에디터 + 이미지 교체 + 디스코드 봇 트리거)

**검증 (C)**
- 전 프로젝트 grep 1회: `grep -rn "PROJECT_SLUG\|var slug = '{{ slug" auto_agent/dashboard/templates/` — 표시용 외 0
- `auto-agent` CLI는 `--project <slug-or-uuid>` 둘 다 허용 유지 (사용자 편의)

**롤백**: 룰 추가만이라 무위험.

---

## 영향 범위 카운트 (현 시점)

- 백엔드 slug 라우트: 38개 → Phase 1
- 프론트 fetch 사이트 (slug 사용): ~136개 → Phase 2
- Remotion/매니페스트 정적 경로: ~5개 → Phase 3

## YAGNI 제외 항목

- **디렉토리 리네임 (uuid-only)**: 사람 인식성 손실. 현 `{uuid}_{slug}` 유지.
- **DB id → uuid 통합**: 이미 별도 컬럼으로 공존. 본 작업과 무관.
- **CLI의 `--project` 인자 변경**: slug/uuid 둘 다 허용 유지. 사람 편의 우선.
- **slug 라우트 영구 제거**: A안 결정대로 redirect 유지. 유지비 0에 가깝고 옛 링크 안전망.

## 회귀 위험 표

| 영역 | 위험도 | 완화 |
|------|--------|------|
| FastAPI 라우트 우선순위 | 中 | uuid path converter 정규식 `^[a-f0-9]{8}$`로 명확 분리 |
| Remotion 번들 캐시 | 中 | redirect 라우트로 옛 번들도 동작 보장 |
| 디스코드 봇 외부 링크 | 低 | slug redirect 영구 유지 |
| 매니페스트 재빌드 누락 | 低 | redirect로 자동 흡수 |
| 프론트 영역 누락 | 中 | 단계별 grep 카운터 0 확인 |

## 완료 정의 (Definition of Done)

- 모든 신규 fetch 호출 식별자가 uuid
- `/p/{slug}` 입력 시 자동 301 → `/p/{uuid}` 동작 확인
- 대시보드 9개 탭 + 씬에디터 + 이미지 교체 + Stage 3 렌더 1회 회귀 통과
- grep 카운터 0 (Phase 2 영역별 + Phase 3 정적 경로 + Phase 4 잔존)
- CLAUDE.md 룰 추가
