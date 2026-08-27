# 인수인계 — LG 1편 씬 연출 보강

> 2026-08-27 세션. 다음 세션은 이 문서만 읽고 이어가면 된다.
> 프로젝트: `output/b5f04c4d_lg_brand_encyclopedia_ep01`
> 브랜치: `rules/scene-splitting` (커밋 `a43b29a` 까지 푸시됨)

---

## 1. 지금 상태

```
씬 165 = 실컷 141 + 카드 24
종류    재연 121 · 도해 14 · 실물 자료 5 · 지도 1

그림 검사(check_image_says)      ok 81 · weak 19 · wrong 6   → 마지막 6컷 손봐 5컷 회복
시청자 평가(viewer_eval)          53 → 56   (그림 고치기 전 측정, 다시 재야 함)

TTS      재녹음 필요 141/141   기존 mp3 207개는 씬 경계가 바뀌기 전 것이라 못 씀
자막     2개 (사실상 없음)
Remotion 정적 폴더 비어 있음
```

---

## 2. 바로 이어서 할 일

```
① 씬61 다시 그리기            아직 wrong. 「거대한 화학단지 같은 건 없었다」
                              대비를 만들었는데도 크기 차가 안 산다
② 전수 재검사                 python3 scripts/check_image_says.py EP01
③ weak 19컷 손보기            python3 scripts/apply_image_fixes.py EP01 --apply
④ 시청자 재평가               python3 scripts/viewer_eval.py EP01
⑤ TTS 141컷 → 자막 → 조립
```

**③에서 표정이 처음으로 반영된다.** 이번 세션 끝에 표정 지시를 넣었는데
그 뒤로 6컷만 그렸다. weak 19컷은 아직 옛 프롬프트(표정 없음)로 그려진 것이다.

---

## 3. 고친 것 — 원인 넷

시청자 평가 53점의 원인을 끝까지 따라간 결과다. **규칙이 없어서가 아니라
검사가 없어서**였다.

### ① 화풍이 이야기를 이겼다

프롬프트의 80%가 화풍 지시였고, 인물 비율 블록이 스스로 이렇게 선언했다.

```
This is the single most important requirement of the image.
```

모델은 시킨 대로 화풍을 지키고 이야기를 흘렸다.

```
씬993   프롬프트 「빈손을 펴 보이며 고개 숙이는 구인회, 빈 나무 칸」
        나온 그림  선반 가득한 가게에서 웃으며 천을 펼치는 주인
```

**화풍을 덜면 그림체가 흩어진다.** 한 글자도 덜지 않고 순위만 바꿨다 —
맨 앞에 `Priority`, 맨 끝에 `Must be visible`. 13컷 재생성에 11컷 회복.

### ② 표정이 잠겨 있었다

캐릭터 시트 아랫줄에 **평온·놀람·근심·낙담·기쁨 다섯 표정**이 그려져 있는데,
`gen_scenes.py` 가 「얼굴과 옷차림만 참고합니다」라고 못 박아 못 쓰게 하고
있었다. 게다가 화풍 문구에 「뺨에 옅은 홍조가 있다」가 박혀 있었다.

그래서 모든 인물이 평온하게 웃었고, 두려움을 말하는 씬이 「사람들이 편안한
평시 장터」로 읽혔다.

```
gen_scenes.py          「생김새·옷차림·표정을 시트에서 가져옵니다」로 바꿈
build_image_prompts.py  얼굴은 그리는 방식만 정하고 표정은 씬이 정하게
replan_direction.py     people 줄 끝에 표정을 적게 — 「… 맨눈 — 근심」
apply_image_fixes.py    같음
check_image_says.py     표정이 말과 어긋나면 잡게
```

**얼굴이 아주 작게 나오는 컷에서는 표정을 따지지 않는다.** 그때는 하늘 색·
자세·향하는 방향·비어 있는 자리가 감정을 진다.

### ③ 실물 자료에 근거가 없었다

판정문과 종류가 정반대로 저장돼 있었다.

```
씬1023  이유 「archive 부재, 재현 필요」  →  종류 search_image
```

다음 단계는 곧이곧대로 자료를 찾으러 갔고, 맞는 자료가 없으니 시대만 맞는
아무 사진을 붙였다 — 「그의 이름은 안희제」에 일본어 간판 거리 사진.

**이유문으로 잡으면 안 된다 — 이유문은 낡는다.** 씬25·52·1039는 「부재」라
적혔지만 그 뒤 좋은 자료를 실제로 찾았다. **관련성 칸이 비었는지**로 가른다.

### ④ 쪼갠 조각이 프롬프트를 물려받았다

```
씬20    「보통 첫 실패 뒤에는 물건을 줄이기 마련인데요」
씬997   「구인회는 반대로 구색을 늘렸습니다」            ← 반전
둘 다   「…두 선택 사이에서 풍성한 쪽을 고르는 구인회…」
```

질문 컷에 답이 이미 그려져 반전이 미리 소진됐다. `scene-splitting-rules`
6절에 있던 검사인데 한 번도 돌지 않았다(16씬).

---

## 4. 남긴 도구

```
check_split_health.py   쪼갠 조각이 프롬프트를 물려받았나
check_kind_reason.py    실물 자료에 근거(관련성)가 있나 · --apply 로 재현 되돌림
check_image_says.py     **그림을 열어 보고 이 말을 하는지 묻는다** ← 빠져 있던 고리
apply_image_fixes.py    검사기의 처방을 프롬프트에 반영 (weak 은 한 가지만 바꿈)
replan_direction.py     제 문장으로 화면을 다시 짠다 (wrong 용)
viewer_eval.py          시청자 셋에게 보인다
viewer_fixes.py         그 셋에게 처방을 받는다
```

### 고리

```
replan_direction  →  build_image_prompts  →  gen_scenes  →  check_image_says
                              ↑                                    │
                              └──────── wrong 이면 되돌아간다 ────────┘
```

`wrong` 은 `replan_direction`(화면을 통째로 다시 짬), `weak` 은
`apply_image_fixes`(한 가지만 바꿈). 성격이 다르니 도구도 다르다.

---

## 5. 파이프라인에 걸어 둔 것

```
step_2_visual_check   visual_gate_module    ①④를 센다
step_3b_image_check   image_says_module     그림을 열어 본다
```

문서만 두면 또 안 돌린다. `runner.py` 모듈 표에도 등록돼 있다.

---

## 6. 절차 (그림 다시 그릴 때)

```bash
# 1. 프롬프트를 손본다
python3 scripts/apply_image_fixes.py EP01 --apply          # weak
python3 scripts/replan_direction.py EP01 --scenes N --apply # wrong

# 2. 프롬프트 파일을 만든다 (반드시 「철칙 위반 0컷」이어야 함)
python3 scripts/build_image_prompts.py output/b5f04c4d_lg_brand_encyclopedia_ep01 -o _imggen/ep01_vN

# 3. 그릴 씬만 남긴다 — 안 그러면 124컷을 통째로 다시 그린다
python3 - <<'EOF'
import json, pathlib
d = pathlib.Path('_imggen/ep01_vN'); want = {61}
j = json.loads((d/'jobs.json').read_text(encoding='utf-8'))
(d/'jobs.json').write_text(json.dumps([x for x in j if x['sceneNumber'] in want],
                                      ensure_ascii=False, indent=2), encoding='utf-8')
EOF

# 4. 그린다
python3 scripts/gen_scenes.py output/b5f04c4d_lg_brand_encyclopedia_ep01 _imggen/ep01_vN -o _imggen/ep01_vN/out

# 5. 붙인다 — publish_images 는 `current/` 를 본다. out 을 복사해야 한다
mkdir -p _imggen/ep01_vN/current && cp _imggen/ep01_vN/out/scene_*.png _imggen/ep01_vN/current/
python3 scripts/publish_images.py _imggen/ep01_vN output/b5f04c4d_lg_brand_encyclopedia_ep01

# 6. 확인한다
python3 scripts/check_image_says.py EP01 --scenes 61
```

---

## 7. 걸릴 만한 것

- **파이썬은 `/opt/homebrew/bin/python3.12`** 를 쓴다. `python3` 는 시스템 3.9라
  `app.py:617` 의 `Path | None` 에서 죽는다. 대시보드도 같다
- **`scripts/*` 가 `.gitignore` 로 통째로 무시된다.** 새 스크립트는 허용 목록에
  `!/scripts/이름.py` 를 넣어야 커밋된다
- **`compose_infographics.py` 는 `--scenes` 없이 돌리지 말 것.** 한 장 고치려고
  전편을 다시 조립하면 잘 만든 도해가 레이아웃 파일 상태로 되돌아간다
- **도해 렌더 PNG는 검수용 미리보기다.** Remotion 이 `infographic` 명세로 직접
  그리므로 프로젝트 `images/` 에 발행하지 않는다
- **codex 는 NAS 심링크에 못 쓴다.** `_imggen/` 에 만들고 복사한다
- **검사기도 틀린다.** 씬1004를 「맑고 넓은 하늘」이라 읽었는데 실제로는 흐린
  회색이었다. wrong 이 뜨면 그림을 직접 열어 보고 판단할 것

---

## 8. 열린 결정

- 허만정 도해 요소에 갓이 씌워져 있다. 실사진에는 갓이 없고 둥근 검은
  뿔테 안경에 콧수염이다 — 감독님이 「우선 두자」고 하셨다
- 캐릭터 시트 PNG 를 git 에 넣을지
- EP02 는 도해 24씬·TTS 179컷이 손도 안 댄 상태
- EP03~12 보강 미착수

---

## 함께 볼 것

- `docs/rules/image-direction-rules.md` — 오늘 세운 규칙 전문
- `docs/rules/dont-discard-good-work.md` — 잘 만든 것을 덮어쓰지 않는 법
- `docs/EP01-fix-list.md` — 시청자 118건 처방 (씬 단위)
- `_imggen/EP01_image_says.json` — 마지막 그림 검사 결과
- `_imggen/EP01_viewer.json` — 마지막 시청자 평가
