# v3 ↔ adobe 통합 — 코드를 합치지 말고 **프로젝트 폴더**를 합친다

> 「기획 → 원고 → 에셋」은 v3가, 「패널 → AE → 렌더」는 adobe가 맡는다.
> 그 둘을 어떻게 이을 것인가.

---

## 결론

**저장소를 합치지 않는다. 산출물 폴더 하나를 두 프로그램이 함께 본다.**

```
                    프로젝트 폴더 (단일 진실)
                    output/{uuid}_{slug}/
                      scene_specs.json
                      scenes.json          ← adobe가 읽는 관문
                      images/  audio/  layers/
                            ▲            ▲
                            │            │
          v3가 쓴다 ────────┘            └──────── adobe가 읽고 덧쓴다
      (기획·원고·자료·에셋)                    (분리·벡터화·매니페스트·AE)
```

adobe에는 이미 그 열쇠가 있다.

```python
# backend/projects.py
def projects_root() -> Path:
    env = os.environ.get("AK_PROJECTS_ROOT")   # ← 이걸 v3 output으로 돌린다
```

`AK_PROJECTS_ROOT=/Volumes/.../auto_kairos_v3/output` 하나면 패널이 v3 프로젝트를
그대로 목록에 띄운다. **에셋을 복사하지 않는다** — 지금 브리지가 이미지 700장을
복사해 넣고 있는데, 그러면 원본이 갱신될 때마다 어긋난다.

---

## 왜 합치지 않는가

합치자는 말이 나오는 이유는 분명하다 — 한 번에 돌리고 싶다. 그런데 합치면
따라오는 것이 있다.

| 합쳤을 때 딸려 오는 것 | 무게 |
|---|---|
| Remotion 렌더러 · 대시보드 · SQLite | 갈라 두면 **자체 렌더 경로로 계속 쓴다** (아래 참조) |
| v3 venv (무거움) vs adobe stdlib 백엔드 | 런타임이 다르다 |
| CEP 패널 설치 경로 | AE 확장 규약을 따라야 한다 |
| 릴리스 주기 | 원고 파이프라인과 패널은 고치는 빈도가 다르다 |

**갈라 두어 잃는 것은 거의 없다.** 두 프로그램이 파일로만 대화하기 때문이다.

---

## 출력 경로가 둘이라는 것 — 약점이 아니라 자산

처음에 「AE가 렌더를 맡으면 Remotion은 죽은 코드」라고 썼는데 틀렸다.
같은 `scene_specs`에서 **두 갈래 출력**이 나오는 것이 v3의 강점이다.

```
                 scene_specs.json
                   ╱          ╲
        Remotion 렌더          adobe → AE
      (자동 · 일괄 · 무인)      (레이어 2.5D · 사람 손)
```

| | Remotion 경로 | AE 경로 |
|---|---|---|
| 사람 손 | 필요 없음 | 편집자가 이어받는다 |
| 속도 | 헤드리스 일괄 — 12편을 밤새 돌린다 | 씬 단위, 손이 든다 |
| 품질 | 레이아웃·자막·차트는 충분 | 2.5D 모션·카메라·리깅까지 |
| 쓰임 | **초벌 · 쇼츠 · 카드뉴스 · 썸네일 · 검수** | **본편 마감** |

**초벌을 무인으로 뽑고 본편만 AE로 마감하는 사다리**가 된다. 12부작처럼 물량이
많을 때 전편을 AE로 끌고 가는 것은 현실적이지 않다.

Remotion에는 대체하기 어려운 쓸모가 하나 더 있다 — **검수용 정지 프레임**이다.
`remotion still`로 씬별 완성 화면을 뽑아 블라인드 시청자 평가를 돌렸더니
`metric_wall`의 값이 전부 `1`로 뜨는 버그가 잡혔다. 이미지 검수로는 보이지 않는
층이었고, AE로 같은 일을 하려면 사람이 붙어야 한다.

**그래서 Remotion을 걷어내지 않는다.** 오히려 이것이 저장소를 합치지 않을 또 하나의
이유다 — 합치면 렌더러가 둘인 구조가 어색해 보이지만, 갈라 두면 각자 제 일을 하는
두 경로다.

---

## 이어지는 지점 세 곳

### ① 프로젝트 목록 — `AK_PROJECTS_ROOT`

adobe 패널이 v3 프로젝트를 그대로 본다. 폴더 이름은 `{uuid}_{slug}`.

`_artifacts()`가 보는 파일 목록에 v3 산출물을 더한다.

```python
ARTIFACT_FILES = ["plan.md", "final_manuscript.md", "scenes.json", "pd_notebook.md",
                  "scene_specs.json"]          # ← v3 원본
```

### ② 관문 파일 — `scenes.json`

v3가 `scene_specs.json`을 `scenes.json`으로 옮겨 **같은 폴더에** 쓴다.
지금 `scripts/export_to_adobe.py`가 하는 일인데, 다른 폴더로 복사하는 대신
제자리에 쓰도록 바꾼다(`--in-place`).

adobe가 쓰는 필드에 맞추고, v3에만 있는 것을 얹는다.

| 필드 | 쓰임 |
|---|---|
| `characters` = cast + people | **레이어 분리에서 인물을 찾는 근거** |
| `layout` · `items` · `values` · `unit` | AE 텍스트 레이어 |
| `badge` · `attribution` · `attributionStatus` | 배지, 출처 자막(협의 미완은 빨강) |
| `visualMode` · `assets` · `composition` | 인포그래픽 씬 — 분리 없이 바로 배치 |
| `camera` | 가이드 널 키프레임 |

강조 마커 `{{1936}}`은 벗겨서 넘긴다 — AE에는 그걸 해석할 렌더러가 없다.

### ③ 되돌아오는 것

adobe가 만든 것도 **같은 폴더에** 쓴다. v3 대시보드가 그걸 보고 진행 상태를
표시할 수 있다.

```
layers/       분리·벡터화 결과 (사이드카 포함)
ae_manifest.json
ae_scripts/
```

---

## 한 번에 돌리고 싶을 때

코드를 합치지 않고도 된다. **프로세스 경계로 부른다.**

```
auto-agent run --project <slug> --to assets     # v3: 기획~에셋
auto-agent handoff --project <slug>             # scenes.json 제자리 생성
curl localhost:<port>/api/layers/split ...      # adobe 백엔드 호출
```

v3에 얇은 `handoff` 명령 하나만 더하면 된다. adobe 백엔드는 이미 FastAPI라
HTTP로 부를 수 있다.

---

## 그래도 합친다면

정말 한 저장소로 가야 한다면 **v3에 adobe를 넣는 쪽**이 맞다. 프로젝트 저장소·
DB·에이전트가 v3에 있고, adobe는 그 위에 얹히는 표현 계층이기 때문이다.
그때도 아래는 지켜야 한다.

- `adobe/` 를 별도 최상위 폴더로 두고 **v3 패키지를 import 하지 않는다**
- adobe 백엔드는 계속 stdlib만 쓴다 (venv 의존 금지)
- CEP 패널은 심링크로 AE 확장 폴더에 건다
- 공유는 여전히 **파일**로 한다 — 함수 호출로 엮으면 되돌리기 어렵다

즉 합쳐도 **결합은 지금과 같아야 한다.** 그렇다면 굳이 합칠 이유가 약하다.

---

## 권고 순서

1. **`AK_PROJECTS_ROOT`를 v3 output으로 돌려 본다** — 패널에 12편이 뜨는지
2. `export_to_adobe.py --in-place` — 복사 대신 제자리에 `scenes.json`
3. `ARTIFACT_FILES`에 `scene_specs.json` 추가 — 상태 표시
4. 카메라·인포그래픽 필드를 매니페스트 빌더가 읽도록 (별도 인수인계 문서 둘 참조)
5. v3에 `handoff` 명령 추가 (선택)

1번만 해도 **에셋 복사 없이** 두 프로그램이 같은 프로젝트를 보게 된다.
거기서부터 하나씩 이으면 된다.

---

## 함께 볼 것

- `2026-08-17-camera-null-handoff.md` — 카메라를 가이드 널로
- `2026-08-17-infographic-scene-handoff.md` — 인포그래픽 씬 만드는 순서
