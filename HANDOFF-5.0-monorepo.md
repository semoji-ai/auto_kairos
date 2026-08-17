# ⚠️ 이 저장소는 auto_kairos 5.0으로 옮겨갑니다

> **작업 위치가 바뀝니다.** 지금 이 저장소에서 하던 일을
> `auto_kairos/adobe/` 안에서 하게 됩니다.
> 옮기는 방식은 git subtree이므로 **커밋 이력은 그대로 보존**됩니다.

---

## 왜 옮기나

세 갈래(v3 파이프라인 · v4 실험 · adobe 패널)를 하나로 관리하기로 했습니다.
줄기는 v3입니다 — v4는 v3에서 갈라져 나온 실험 갈래임이 확인됐고(스크립트와
아트스타일이 전부 v3 것), 실제로 도는 코드는 v3에 있습니다.

판단 근거는 `auto_kairos/docs/v5-plan.md`에 있습니다.

**합치되 결합하지 않습니다.** `adobe/backend`는 계속 stdlib만 쓰고 상위 패키지를
import 하지 않습니다. 대화는 지금처럼 파일과 HTTP로만 합니다. 이 경계를 지키는 한
합쳐도 지금과 똑같이 일할 수 있습니다.

---

## 무엇이 바뀌나

| | 지금 | 5.0 이후 |
|---|---|---|
| 저장소 | `semoji-ai/auto_kairos_adobe` | `semoji-ai/auto_kairos` |
| 작업 경로 | `~/LocalProjects/auto_kairos_adobe/` | `~/LocalProjects/auto_kairos/adobe/` |
| 백엔드 | `backend/` | `adobe/backend/` |
| 패널 | `cep/com.autokairos.pd/` | `adobe/cep/com.autokairos.pd/` |
| 이력 | — | **그대로 보존** (subtree) |

---

## 옮긴 뒤 해야 할 것

### ① CEP 확장 심링크 다시 걸기

AE는 정해진 폴더에서만 확장을 읽습니다. 경로가 바뀌었으므로 다시 걸어야 합니다.

```bash
rm -f ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
ln -s ~/LocalProjects/auto_kairos/adobe/cep/com.autokairos.pd \
      ~/Library/Application\ Support/Adobe/CEP/extensions/com.autokairos.pd
```

AE를 껐다 켜서 패널이 뜨는지 확인합니다.

### ② 백엔드 기동 경로

```bash
cd ~/LocalProjects/auto_kairos/adobe
python3 -m uvicorn backend.app:app --port <기존 포트>
```

`AK_PROJECTS_ROOT`는 그대로입니다 — 오히려 이제 같은 저장소 안의
`projects/`(또는 v3 `output/`)를 가리키면 됩니다.

### ③ 진행 중이던 브랜치

`feat/tylenol-motion-recreation`의 내용은 **이미 main에 올라가 있습니다**
(카메라 구현 `9078905`·`c0aa74e` 포함). subtree는 main 기준으로 가져가므로
빠지는 것이 없습니다.

옮긴 뒤 새 작업은 `auto_kairos` 저장소에서 브랜치를 따세요.

---

## 옛 저장소는 어떻게 되나

**지우지 않습니다.** 당분간 읽기 전용으로 남깁니다. 혹시 빠진 것이 있으면
거기서 꺼내 옵니다. 다만 **새 커밋은 하지 마세요** — 두 곳에 갈라지면
합친 의미가 사라집니다.

---

## 지금까지 넘어간 것 (참고)

오늘 v3 ↔ adobe 사이에 오간 것들입니다. 합쳐진 뒤에도 그대로 유효합니다.

| 문서 | 내용 |
|---|---|
| `docs/superpowers/specs/2026-08-17-camera-null-handoff.md` | 가이드 널 카메라 — **구현 완료** |
| `2026-08-17-infographic-scene-handoff.md` | 인포그래픽 씬 만드는 순서 |
| `2026-08-17-v3-adobe-integration.md` | 폴더 공유 방식 |
| `2026-08-17-product-family.md` | AE·Premiere는 한 확장의 두 호스트 |

공유 규격은 잠금으로 묶여 있습니다.

```bash
python3 scripts/spec_check.py        # 사본이 v3 판과 같은지
```

합친 뒤에는 경로만 바뀌고 동작은 같습니다.

---

## 확인할 것이 있으면

이 문서를 읽고 **옮겨도 되는 시점인지** 알려 주세요. 진행 중인 작업이 있으면
그것부터 main에 올린 뒤에 옮기는 것이 안전합니다.
