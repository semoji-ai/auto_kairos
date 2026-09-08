# auto_kairos 정본 통합 — adobe 저장소 봉인과 보안 회귀 복구

날짜: 2026-09-08 / 브랜치: main / 승인: 사용자 대화

## 왜 하는가

`auto_kairos_adobe`가 원격에 살아 있고 로컬 폴더 이름이 `auto_kairos_v3`인 탓에,
"어느 쪽이 정본인가"를 매번 다시 판별해야 했다. 그 판별을 한 번 하고 구조로
못박는다.

판별 근거는 내용 대조다.

- `adobe/`는 2026-08-17 subtree로 흡수됐다 (`179adba`, squashed from `1f6b46d`).
- 흡수 이후 `adobe/`를 고친 커밋이 **115개**.
- 흡수 시점 트리 vs 표준 저장소 `main` 트리를 파일 단위로 비교하면 **표준
  저장소에만 있는 파일이 0개**다. 오히려 v3 쪽이 `camera_plan.py`·spec 문서를
  더 갖고 있었다.

표준 저장소는 흡수 시점에 이미 뒤처져 있었고, 그 뒤로 한 번도 앞선 적이 없다.

분기처럼 보이던 `feat/layerkit-adapter`·`origin/feat/tylenol-motion-recreation`은
`main`과 **같은 커밋**(`8391293`)을 가리키는 포인터였다. 진짜 분기는
`backup/layerkit-adapter-20260817`(`aa385ad`) 한 줄기뿐이고, 그마저 대부분은
v3에서 이름만 바뀐 것이었다(`upscale.py`→`upscale_layers.py`,
`korean_tts_preprocessor.py`→`auto_agent/tools/`, `install.sh`→루트).

**살릴 것은 하나다 — 유실된 CSRF 방어.**

## 정본 선언

| 대상 | 지위 |
|---|---|
| `semoji-ai/auto_kairos` `main` | **정본.** `adobe/`는 subtree로 흡수된 하위 디렉토리 |
| `semoji-ai/auto_kairos_adobe` | 이력 보존용 아카이브. 쓰기 금지 |
| `semoji-ai/auto_kairos_v4` | 이미 archived. 손대지 않음 |

## 구성

### 1. 보안 회귀 복구 — `adobe/backend/app.py`

패널 백엔드는 `127.0.0.1:8765`에 뜨는 웹서버이고 라우트가 73개다. 그중에는
`/api/projects/file/save`(파일 덮어쓰기)·`/api/scenes/delete`·`/api/skills/run`
(codex/claude 프로세스 기동)이 있다.

현재 `app.py`는 `Access-Control-Allow-Origin: *`만 내보내고 Origin 검사가 없다.
`do_OPTIONS`도 `*`를 돌려주므로 JSON POST의 preflight까지 통과한다. 브라우저가
쳐 줄 same-origin 방어를 서버가 명시적으로 해제한 상태다. AE 패널이 떠 있는
동안 사용자가 방문한 아무 웹페이지나 위 라우트를 호출하고 응답을 읽을 수 있다.

**`origin_allowed(origin: str | None) -> bool`** — 헤더 문자열만 받는 순수 함수로
둔다. 서버를 띄우지 않고 테스트할 수 있어야 하기 때문이다.

```python
def origin_allowed(origin) -> bool:
    """CEP 패널은 file:// 출신이라 Origin 헤더가 없거나 null.
    Origin이 존재하고 null/file:// 이 아니면(=브라우저 웹페이지 출처) 차단."""
    if origin is None:
        return True
    return origin == "null" or origin.startswith("file://")
```

`Origin` 헤더는 브라우저가 직접 붙이며 웹페이지가 위조할 수 없다. 그래서
"Origin이 붙어 있고 `file://`도 아니면 = 웹페이지"가 깔끔하게 갈린다.

검사를 거는 지점은 **두 곳**이다.

| 지점 | 이유 |
|---|---|
| `_route()` | GET/POST 전부가 지나감 |
| `_sse()` | `/api/events`는 `do_GET`에서 `_route`를 **우회**함 |

폐기 브랜치의 원본 수정은 `_route`만 막았다. 그 브랜치에도 `do_GET`의
`/api/events` 분기가 있었으므로(`backend/app.py:62-64`) SSE는 무방비였다.
**그대로 베끼면 구멍이 남는다.** 이식하면서 `_sse()`에도 같은 검사를 넣는다.

거부 응답은 403 + `{"error": "forbidden origin"}`.

`Access-Control-Allow-Origin: *`는 유지한다. CEP 패널이 `file://` 출신이라
화이트리스트에 올릴 출처가 없다. 문을 지키는 역할은 `origin_allowed`가 전담한다.

### 2. 표준 저장소 봉인 — `semoji-ai/auto_kairos_adobe`

1. 로컬 미커밋 항목 확인 — `_workspace/`(8K)·`projects/bd4d47b9/`(40K)·
   `.gitignore` 수정. 내용을 보고 보존 여부를 사용자에게 확인한다.
2. 태그로 이력 고정
   - `archive/layerkit-20260813` → `aa385ad` (분기 36커밋의 머리)
   - `archive/main-20260816` → `8391293`
3. README 상단에 이전 안내를 커밋하고 push
4. `gh repo archive semoji-ai/auto_kairos_adobe` — 읽기전용 전환
5. 로컬 폴더를 `~/Projects/_archive/auto_kairos_adobe`로 **이동**(삭제 아님)

### 3. 문자열·죽은 브랜치 정리 — 정본 저장소

```bash
git remote set-url origin git@github.com:semoji-ai/auto_kairos.git
```

로컬 remote가 `jleavens01/auto_kairos`로 남아 있다. GitHub 리다이렉트로 동작은
하지만 보는 사람을 계속 헷갈리게 한다. README 설치 안내 2곳도 같은 주소로 고친다.

죽은 브랜치는 **삭제 전에 기계로 검증한다.**

```
rev-list --count main..<branch> == 0  이어야만 삭제 대상
0 이 아니면 그대로 두고 목록으로 보고한다
```

이 관문이 판단 착오로 인한 유실을 막는다. 삭제 직전 각 브랜치에
`archive/<이름>` 태그를 찍는다.

확인된 삭제 후보(둘 다 `main..` 카운트 0):

- `v4-bridge` (로컬·원격) — `origin/v4-bridge`의 미병합 2커밋은 내용이 이미
  main에 있다. `pv-zoom` 확대보기는 `storyboard.js`에, `--drop-missing`은
  `scripts/apply_rewrite.py:42`에 들어가 있다. SHA만 다른 재적용본이다.
- `claude/fix-windows-art-style-oZLv0` (로컬·원격) — 로컬이 원격보다 4커밋
  앞서 있으나 `main`에 부족한 커밋은 0개다.

나머지 브랜치는 검증 스크립트 결과에 따른다.

### 4. 폴더 개명

```
mv ~/Projects/auto_kairos_v3  ~/Projects/auto_kairos
```

`_v3`라는 이름이 이번 혼란의 근원이다. `docs/v5-plan.md`에도 예정된 작업이다.

의존처 5곳을 이어서 고친다.

| # | 대상 | 내용 |
|---|---|---|
| 1 | `~/Library/Application Support/Adobe/CEP/extensions/com.autokairos.pd` | 심링크 재생성 |
| 2 | `~/.claude/settings.json` | 경로 참조 |
| 3 | `~/.codex/config.toml` | 경로 참조 |
| 4 | `~/Projects/brand-tycoon/tools/gen_portraits.py` | 다른 프로젝트가 참조 |
| 5 | 저장소 내부 `.claude/settings.json`·`.env.example` | 경로 참조 |

개명은 `mv`이므로 미커밋 변경분이 그대로 따라온다.

## 범위 제외

- **패널 UI 3탭 이식 안 함** — `settings.js`(12K)·`pipeline.js`(10K)·
  `video.js`(10K)는 폐기 브랜치에만 있으나, v3 패널은 `planning`/`storyboard`
  두 탭으로 재설계됐다. 백엔드 라우트(`/api/video/models`·`/api/pipeline/run`·
  `/api/tts/settings`·`/api/llm/settings`)는 이미 정본에 있으므로, 필요해지면
  현행 탭 구조에 맞춰 새로 짜는 편이 낫다.
- **`cues.py` 이식 안 함** — TTS 글자별 타임스탬프→연출 큐 변환(3.3K).
  정본 `tts.py`에 타임스탬프는 있으나 큐 변환은 없다. 실제 공백일 수 있으므로
  후속으로 남긴다.
- **미커밋 작업물 손대지 않음** — `adobe/backend/video.py`(+25)·
  `docs/rules/scene-video-rules.md`(+43)·`semoji-engine` 서브모듈은 진행 중인
  작업이다(첨부 이미지 경로 오류를 조용히 넘기던 버그). 이 통합 작업이
  커밋하지 않는다.
- **`ACAO: *`를 화이트리스트로 바꾸지 않음** — 위 1항 참조.
- **`auto_kairos_v4` 저장소 손대지 않음** — 이미 archived.

## 테스트

- `test_app_origin.py` 단위 5케이스 — `None` 허용 / `"null"` 허용 /
  `file://…` 허용 / `http://evil.example` 차단 / `https://attacker.test` 차단.
  순수 함수라 서버 기동 불필요.
- SSE 가드 — `/api/events`가 교차 출처 요청에 403을 돌려주는지. `_sse`가
  `_route`를 우회하므로 별도 케이스가 필요하다.
- `adobe/` 기존 테스트 전체 통과(회귀 없음).
- 실전 스모크
  - `curl -H "Origin: https://evil.test" http://127.0.0.1:8765/api/projects/files` → **403**
  - Origin 헤더 없이 같은 요청 → **200** (패널 정상 동작 확인)
- 개명 후 — AE에서 패널 로드 + `/api/events` 스트림 연결.

## 완료 판정

- 위 테스트 전부 통과
- `gh repo view semoji-ai/auto_kairos_adobe --json isArchived` → `true`
- `git remote -v`가 `semoji-ai/auto_kairos`를 가리킴
- `~/Projects/auto_kairos` 경로에서 패널이 정상 기동
- 남은 브랜치 목록에 `main..` 카운트 0인 브랜치가 없음

## 순서와 그 이유

```
1. 보안 이식      되돌리기 가장 쉬움. 먼저 안전해진다
2. 저장소 봉인    분기 재발 경로를 닫는다
3. 문자열 정리    remote URL · README · 죽은 브랜치
4. 폴더 개명      외부 의존처 5곳 — 가장 위험하므로 마지막
```

각 단계는 독립적으로 커밋하고 되돌릴 수 있다. 4단계에서 막혀도 1~3단계의
성과는 남는다.
