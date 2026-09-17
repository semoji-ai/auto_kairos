# 인수인계 — LG 브랜드백과 12부작

> 2026-08-28~29 세션. 다음 세션은 이 문서만 읽고 이어가면 된다.
> 브랜치 `rules/scene-splitting`

---

## 1. 지금 어디까지 왔나

```
편     점수    씬     그림없음   TTS    상태
EP01   86     156      0       151컷   씬4 홍보영상 · 자막 · 조립 남음
EP02   91     177      1       64컷    ← 목표 90점 넘음
EP03   86      72      6        -      손대지 않은 기준 상태
EP04~12  미측정
EP04b·EP06  그림 0 — 원고 단계에서 멈춘 편
```

**1·2편은 마무리 단계, 3~12편은 본격 작업 전이다.**

---

## 2. 평가 — 이것부터 읽을 것

전문은 `docs/rules/content-evaluation-rules.md`. 요지만 적는다.

```bash
python3 scripts/youtube_eval.py EP03            # 편 전체 100점
python3 scripts/ask_removal.py EP03             # 뺀 자리를 그 자리에서 되묻기
```

**재미 30 · 유용 30 · 확산 25 · 신뢰 15.** 감점마다 씬번호와 `cause`(원고|화면|구성)가
붙어 나오므로, 무엇을 고쳐야 오르는지 매번 자동으로 보인다.

### 눈금이 두 번 고장 났다 — 또 그러지 않게

```
① 「천만 뷰 편 = 80점」 앵커        → 천장이 생겨 69점에 묶였다
② 「이탈 위험 — 짚을 수 있는가」    → 만점이 뭔지 없어 일곱 번 내내 2/5
③ 재미를 제작 품질로 재기          → 화풍·중복이 재미 감점 근거로 쓰였다
④ 「화면 신뢰 셋 넘으면 0」        → 길이에 상관없는 절대 개수라 항상 0~2
```

**증상은 하나다 — 어떤 항목이 회차를 거듭해도 같은 값이면 그 항목은 죽은 것이다.**
작업이 안 먹히면 작업을 더 하기 전에 **항목별 점수를 회차별로 늘어놓아 본다.**

```bash
python3 - <<'EOF'
import json,pathlib
for f in sorted(pathlib.Path('_imggen').glob('EP0*_youtube*.json')):
    d=json.loads(f.read_text(encoding='utf-8'))
    print(f.stem, d.get('scores'), d.get('total'))
EOF
```

**총점은 ±3 흔들린다.** 같은 방향으로 두 번 나오거나 항목 근거가 바뀌어야 신호다.

---

## 3. 무엇이 실제로 점수를 올렸나 (실측)

```
EP02  72 → 91
  되풀이 4줄 삭제            +2
  visual_kind 오분류 교정     +6    ← 도해 24개가 빈 판이었다
  화면신뢰 눈금 교정          +1
  빈 판 7곳을 도해로 그리기   +10   ← 가장 큰 지렛대

EP01  69 → 86
  채점표 교정               +11
  화면 4자리 수리            +3
  되풀이 3줄 삭제            +3
  그림 100여 컷 재생성        0     ← 밴드 안에서만 움직였다
```

**빈 화면·빈 판을 채우는 것이 가장 크다.** 그림을 더 잘 그리는 것은 거의 안 움직인다.

---

## 4. 편마다 도는 순서

```bash
# ① 배관 검사 — 분류가 틀려 화면이 안 뜨는 씬
python3 scripts/fix_visual_kind.py <project_dir> --dry-run
python3 scripts/fix_visual_kind.py <project_dir>

# ② 그림 없는 씬 세기 (아래 5절 스니펫)
#    후보가 있으면 고르고, 없으면 화면을 쓴 뒤 생성
python3 scripts/pick_unselected.py EP03 --apply

# ③ 명세 없는 빈 판을 세모지 화풍 도해로
python3 scripts/gen_infographic_scenes.py EP03 --scenes 6,1027 --apply --use-check
python3 scripts/render_infographic.py EP03 --scenes 6,1027

# ④ 되풀이 걷어내기 — 반드시 되묻기로 검증
python3 scripts/check_redundancy.py EP03
python3 scripts/ask_removal.py EP03      # 절반쯤 「빼면 안 된다」로 돌아온다

# ⑤ 측정
python3 scripts/youtube_eval.py EP03 --tag _r1
```

---

## 5. 자주 쓰는 확인 스니펫

```python
import json,pathlib,sys,collections
sys.path.insert(0,'.')
from auto_agent.tools.image_assets import get_selected
from auto_agent.paths import resolve_project
proj,ep=resolve_project('EP03')
ss=json.loads((proj/'scene_specs.json').read_text(encoding='utf-8'))['scenes']

# 그림 없는 씬
miss=[s['sceneNumber'] for s in ss
      if (s.get('narration') or '').strip()
      and not s.get('isChapterCard') and not s.get('isTurnCard')
      and s.get('visual_kind')!='infographic'
      and not get_selected(proj/'images',s['sceneNumber'])]

# 명세 없는 빈 판
empty=[s['sceneNumber'] for s in ss if s.get('visual_kind')=='infographic'
       and not (s.get('infographic') or {}).get('items')]

# 같은 그림을 두 씬 이상이 쓰는가
use=collections.defaultdict(list)
for s in ss:
    f=get_selected(proj/'images',s['sceneNumber'])
    if f: use[f].append(s['sceneNumber'])
dup={f:n for f,n in use.items() if len(n)>1}
```

---

## 6. EP03~12에 남은 일 (감독 지시)

```
① LG 역사관 · 뉴스룸 자료 보강
② 세모지 문체로 원고 보정
③ 씬 분할
④ 각 조각에 화면 배정 → 생성
⑤ 측정
```

**③만 하고 ④를 건너뛰면 점수가 떨어진다.** EP03에서 실제로 그랬다 —
나레이션을 5씬→18씬으로 갈랐는데 원래 씬의 25초짜리 붙박이 화면이 그대로 남아
**86 → 79**가 됐다. `split_scenes_by_sentence`는 말만 가른다.

EP03은 그 변경을 되돌려 72씬(86점) 상태로 두었다. 새로 그린 11장은 후보로 남아 있다.

---

## 7. 오늘 고친 도구 결함 (다시 생기지 않게)

```
gen_scenes           낡은 `_up` 시트가 새 시트를 이겨 일곱 컷이 옛 얼굴로 나왔다
                     → 기본 시트가 더 새것이면 그쪽을 쓴다
build_image_prompts  「모든 면을 빈 색면으로」가 간판·현판 글자를 막고 있었다
                     → gpt-image-2 는 한글을 정확히 쓴다. 뜻이 곧 글자인 자리에만 넣는다
                     → 씬에 `text_in_image` 를 적으면 그 글자만 들어간다
check_image_says     부분 검사가 전수 결과를 덮어써 weak 목록이 사라졌다 → 병합
publish_images       `current/` 만 봐서 out→current 복사가 필요했고 그 복사가 사본을
                     한 벌씩 더 만들었다 → 이제 `out/` 을 바로 본다. **복사하지 말 것**
build_manifest       켄번 기본 해제 (감독 지시 — 정지 그림을 미는 것은 의미 없다)
image_assets.json    「고른 것」을 적는 칸이 둘이었다. 씬 단위 `selected` 는 낡아서
                     72건이 다른 씬 그림을 가리켰다 → `selected_legacy_do_not_use` 로
                     비켜 뒀다. **정본은 `images[].selected` 하나뿐이다**
```

---

## 8. 걸릴 만한 것

- **파이썬은 `/opt/homebrew/bin/python3.12`.** `python3` 는 시스템 3.9라 `Path | None` 에서 죽는다
- **`scripts/*` 가 `.gitignore` 로 무시된다.** 새 스크립트는 `!/scripts/이름.py` 를 넣어야 커밋된다
- **`compose_infographics.py` 는 `--scenes` 없이 돌리지 말 것** — 전편이 레이아웃 상태로 되돌아간다
- **코덱스는 `/Volumes`(NAS)에 못 쓴다.** 「operation not permitted」. 그래서 `_imggen` 은
  로컬에 있어야 하고, `output` 은 NAS 심링크다 (발행=복사라 괜찮다)
- **`output` 은 이미 NAS다** — `/Volumes/jleavens/Projects/auto_kairos_v3/output`
- **씬4(EP01)·씬8(EP02) 는 브랜드 홍보영상 자리다.** `videoAsset.status: to_source`.
  가장 최근 브랜드 필름의 **맨 끝 로고 지점**을 컷 길이(약 6.6초)에 맞춰 넣는다

---

## 9. 함께 볼 것

- `docs/rules/content-evaluation-rules.md` — 평가 기준 전문. **눈금 사고 두 건의 전말**
- `docs/rules/manuscript-redundancy-rules.md` — 되풀이는 요점 횟수다. 병합·압축은 실패했다
- `docs/HANDOFF-ep01-direction.md` — 1편 연출 보강 기록
- `_imggen/EP0*_youtube_*.json` — 회차별 채점 원본 (항목 점수 추이 확인용)
