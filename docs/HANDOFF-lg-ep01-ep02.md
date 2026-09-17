# LG 브랜드백과 1·2편 — 이어서 할 일

> 세션이 길어져 넘긴다. 이 문서만 읽으면 이어서 할 수 있다.
> 마지막 커밋 `16caeec` (브랜치 `rules/scene-splitting`, PR #2)

---

## 지금 어디까지 왔나

| | EP01 | EP02 |
|---|---|---|
| 프로젝트 | `output/b5f04c4d_lg_brand_encyclopedia_ep01` | `output/b7f6721d_lg_brand_encyclopedia_ep02` |
| 씬 | 179 | 184 |
| 원고 | 감독 목소리로 다시 씀 · 자료 보강 완료 | 〃 |
| 그림 | 그릴 컷 **27** 남음 | 그릴 컷 **27** 남음 |
| 도해 | 17씬 (설계·검수 전) | 27씬 (손도 안 댐) |
| TTS | **174씬 다시 만들어야 함** | **179씬** |
| 자막 | TTS 뒤 | 〃 |

두 편 모두 **원고는 끝났고 에셋이 남았다.**

---

## 바로 이어서 할 일 — 순서대로

### ① 남은 그림 (EP01 27컷 · EP02 27컷)

```bash
D=output/b7f6721d_lg_brand_encyclopedia_ep02     # EP01이면 b5f04c4d…

python3 - <<'PY'
import json,sys; sys.path.insert(0,'.')
from auto_agent.paths import resolve_project
proj,_=resolve_project("EP02")
S=json.loads((proj/"scene_specs.json").read_text(encoding="utf-8"))["scenes"]
need=[s for s in S if s.get("needs_image") and s.get("visual_kind")=="generate_image"]
new=[s["sceneNumber"] for s in need if (s.get("imageAsset") or {}).get("continuity")!="continuous"]
cont=[s["sceneNumber"] for s in need if (s.get("imageAsset") or {}).get("continuity")=="continuous"]
open("_imggen/ep02_new/new.txt","w").write(",".join(map(str,new)))
open("_imggen/ep02_new/cont.txt","w").write(",".join(map(str,cont)))
print(len(new),"새 장면 ·",len(cont),"이어짐")
PY

python3 scripts/build_image_prompts.py $D -o _imggen/ep02_p8
python3 scripts/gen_scenes.py $D _imggen/ep02_p8 -o _imggen/ep02_cuts8 \
        --only "$(cat _imggen/ep02_new/new.txt)" -j 4          # 새 장면은 병렬
python3 scripts/gen_scenes.py $D _imggen/ep02_p8 -o _imggen/ep02_cuts8 \
        --only "$(cat _imggen/ep02_new/cont.txt)" -j 1         # 이어짐은 순차
```

**이어짐은 반드시 `-j 1`.** 앞 컷을 레퍼런스로 붙이므로 앞 컷이 먼저 나와야 한다.

### ② 그린 것을 검사한다 — 빼먹지 말 것

그림마다 **두 가지**를 묻는다. 이걸 안 하면 「사람이 빠진 컷」·「말이 화면에
없는 컷」이 그대로 영상에 들어간다. EP01 은 39컷 중 24컷이 실패했었다.

```
① 사람 수가 맞는가            people 항목 수와 화면의 사람 수
② 말이 화면에 보이는가         시대·분위기만 맞으면 실패
                              글자에 기대도 실패 (이미지에 글자를 굽지 않는다)
```

검사 코드는 이 세션에서 매번 즉석으로 짰다. `_imggen/ep02_check1.txt`~`2.txt`
에 결과 형식이 남아 있으니 그대로 쓰면 된다. **`--allowedTools Read` 로
헤드리스 클로드를 부르고 그림을 실제로 열게 해야 한다.**

### ③ 통과분 붙이기 — 중복을 반드시 확인

```python
# 뒤 판이 이긴다. 붙인 뒤 중복을 센다.
# 재매칭으로 물려준 그림과 새로 그린 그림이 겹치는 일이 잦다 (EP02에서 7건).
# 제 번호를 가진 씬이 임자다 — scene_022 는 씬23(원래 22)의 것.
```

### ④ 도해 (EP01 17 · EP02 27)

```bash
python3 scripts/plan_infographic_layout.py EP02 --force
python3 scripts/gen_info_assets.py EP02 --scenes <번호들>
python3 scripts/compose_infographics.py EP02 --apply
python3 scripts/render_infographic.py EP02
python3 scripts/check_infographic.py EP02 --force      # 고친 뒤엔 반드시 --force
python3 scripts/sanitize_layout.py EP02                # 겹침·화면밖은 계산으로
```

**도해는 걸러지는 것이 정상이다.** EP01 은 22 → 7씬이 됐다.
설계에서 「요소가 하나뿐」으로 빠지고, 검수에서 「뜻이 어긋남」으로 또 빠진다.

### ⑤ TTS + 자막

```bash
.venv/bin/python -m auto_agent.scripts.generate_tts $D    # 시스템 python 3.9 로는 실패
python3 scripts/build_srt.py EP02 --split 45
```

---

## 이 세션에서 잡은 결함 — 다시 겪지 말 것

전부 코드/규칙에 박아 두었다. 다음 편은 처음부터 통과한다.

### 한 프롬프트 안에서 말이 엇갈리면 모델은 적게 그린다

세 갈래가 같은 병이었고 셋 다 `gen_scenes.py` 에서 막았다.

```
사람 없음 모순   프롬프트가 사람을 말하는데 「사람 없음」이 붙음
사물만인데 시트   people=[] 인데 cast 가 남아 시트가 붙음
한 줄에 여럿      「인부 둘」 — 세는 수 1, 그리는 수 2  → 자리를 갈라 자동 분리
```

### 옛 파일을 정본으로 삼지 않는다

`_imggen/<EP>_mode.json`(재분석 결과)은 **옛 씬 경계**를 가리킨다.
설계기·조립기·요소생성기·검수기·수정기 모두 `scene_specs.json` 을 본다.

### 글자에 기대는 설계는 몇 번을 그려도 실패한다

이미지에 글자를 굽지 않는다. 현판·간판·현수막의 **글씨 내용**이 화면의
유일한 근거이면 그 설계는 무효다. **말을 물건으로 옮긴다.**

```
구교리댁 현판  → 교지 두루마리의 붉은 인장과 학이 수놓인 흉배
우리의 목표는 콜게이트 → 별무늬 미제 치약 한 통과 그것을 바라보는 반장
```

### 답은 다음 컷이 준다

「이런 말이 있습니다」·「회사부터 세웁니다」 같은 자리는 **답이 나오기 직전의
화면**으로 둔다. 이 컷 안에서 답까지 주려 하면 어색해진다 (씬983 을 네 번
다시 그리고 알았다).

### 반전 카드에는 문장을 붙이지 않는다

혼자 설 수 없는 문장을 뒤 문장과 묶을 때, 뒤가 반전 카드(「그런데,」)면
카드가 세 문장짜리가 된다. 카드는 한 마디로 홀로 서야 하고, 붙일 문장은
**카드 앞**에 제 씬으로 둔다 — 뒤집을 내용이 앞에 있어야 뜻이 산다.

### 검사할 때 최신 판을 볼 것

기존 파일을 지우지 않으므로 재생성본은 `_v2` 로 쌓인다. 이름만 보고 열면
**고치기 전 그림을 검사하게 된다** — 실제로 7컷을 그렇게 잘못 판정했다.

---

## 규칙 문서 (PR #2 에 들어 있음)

```
docs/rules/scene-splitting-rules.md    씬 나누기 — 두 물음의 순서
docs/rules/scene-visual-decision.md    무엇으로 보여줄까 (도해는 예외)
docs/rules/direction-recipes.md        통한 연출 — 도장·계단·여럿·환산
docs/rules/image-review-rules.md       그림 검수
```

**씬 배분의 두 물음** — 순서가 중요하다.

```
첫째   이 문장 혼자서 한 장면이 되는가     ← 화면이 서는가
둘째   앞뒤와 한 호흡인가, 너무 길지 않은가  ← 리듬과 길이
```

첫째가 먼저다. 「확실한 것은 이겁니다」 같은 문장은 뒤 문장과 묶는다 —
**60자를 넘어도 묶는다.**

---

## 자료 — 계속 캐 볼 곳

이번에 크게 건졌다. 나머지 편에도 쓸 것이 많다.

```
한국경제인협회 디지털 기업인 박물관   30점 정리돼 있음 (가장 좋음)
  https://www.fki-emuseum.or.kr/main/businessman/KooInhoe.do
LG화학 역사관 (연혁·도전과 혁신)
  https://www.lgchem.com/kr/lg-chem-history/timeline
LG 창업회장 소개
  https://www.lg.co.kr/chairman/1/1
경남일보 연재 「일취월장 진주경제」
```

### 이번에 찾은 실물 자료 (권리 협의 전제, `attributionStatus: pending`)

```
EP01 씬25    물에 잠긴 구인회포목상점 (간판 글씨 읽힘)   한국경제인협회
EP01 씬1021  주식회사 구인회상회 주권 실물              한국경제인협회
EP02 씬15    럭키크림 실물 용기 (배우 얼굴 라벨)        경남일보
```

**아직 안 쓴 것** — 포목상점 광고물, 락희화학 서대신동 공장(1947),
사출성형기, 럭키치약, 오리엔탈 플라스틱 빗.

### 주의 — 자료가 갈리는 곳

```
구인회상회 vs 구인상회   주권 실물은 「具仁會商會」. 2차 자료 다수는 「구인상회」.
                        → 실물을 따라 EP01 을 「구인회상회」로 고쳤다
법인 전환 연도          LG 공식 1938.6 / 다수 자료 1940.6 / 나무위키 1941
                        → 다수를 따라 1940 유지
홍수 사진의 연도        박물관 캡션 1935 · 경남일보 1931년 설립 상점
                        → 원고는 연도를 특정하지 않는 문장 아래 두었다
80% 점유율             1957년이 아니라 1962년 불소 첨가 후 1971년까지의 최고치
                        → 이 편에 쓰면 안 된다
```

---

## 남은 판단 (감독님께 물어볼 것)

1. **인물 캐릭터 시트 15장을 깃에 넣을지** — 지금 `_imggen/characters/final_v2_up/*.png`
   가 추적되지 않아, 다른 컴퓨터에서 깃풀하면 얼굴 고정이 안 된다
2. **김준환**(럭키크림 기술자) 시트를 만들지 — 시리즈에서 EP02 한 씬만 나온다
3. **업스케일** — `IMAGE_UPSCALE` 은 파이프라인(`image_batch_module`)에서만 돈다.
   `gen_scenes.py` 로 그린 것은 1792×1024 원본 그대로다. 검사 통과 후 한 번에
   돌리는 편이 낫다 (컷당 몇 초, 로컬 GPU)
4. **EP03~12** — 같은 방식으로 보강할지. 자료 캐기 → 다시 쓰기 → 팩트체크 →
   씬 나누기 → 화면 → 그림 순서

---

## 진행 기록 (EP02 그림)

```
1판 42컷 → 18 통과      2판 36 → 24      3판 12 → 6
4판  7 → 3             5판  4 → 2       6판  2 → 2
7판 21 → 12            8판  9 → 7       9판  2 → 2
```

붙인 컷은 `images/generated/scene_*_gen*.png`. 아직 안 붙인 판은
`_imggen/ep02_cuts7` `_cuts9` `_cuts10` 에 있다 — **붙이면서 중복을 반드시
확인할 것**(제 번호를 가진 씬이 임자).

씬 수는 181. 배분을 다시 하며 줄었다(194 → 181).

---

## 자주 쓴 명령

```bash
# 프로젝트 경로
python3 -c "import sys;sys.path.insert(0,'.');from auto_agent.paths import resolve_project;print(resolve_project('EP02')[0])"

# 원고 뽑기
python3 - <<'PY'
import json,sys,pathlib; sys.path.insert(0,'.')
from auto_agent.paths import resolve_project
proj,_=resolve_project("EP02")
S=json.loads((proj/"scene_specs.json").read_text(encoding="utf-8"))["scenes"]
out=[]; ch=object()
for s in S:
    c=s.get("chapter")
    if c!=ch: ch=c; out.append(f"\n## 챕터 {c}\n")
    t=(s.get("narration") or "").strip()
    if t: out.append(f"{s['sceneNumber']:>5} ({len(t)}자) {t}")
pathlib.Path("_imggen/EP02_원고.md").write_text("\n".join(out),encoding="utf-8")
PY

# 검산
python3 - <<'PY'
import json,sys,re,collections; sys.path.insert(0,'.')
from auto_agent.paths import resolve_project
from auto_agent.tools.image_assets import get_selected
proj,_=resolve_project("EP02")
S=json.loads((proj/"scene_specs.json").read_text(encoding="utf-8"))["scenes"]
said=[s for s in S if (s.get("narration") or "").strip()]
L=[len(s["narration"].strip()) for s in said]
print(f"씬 {len(S)} · 평균 {sum(L)//len(L)}자 · 60자 초과 {sum(1 for l in L if l>60)}")
print("화면:",dict(collections.Counter(s.get("visual_kind") for s in S)))
img=proj/"images"
print("그림 없는 씬:",[s["sceneNumber"] for s in S
      if s.get("visual_kind")=="generate_image" and not get_selected(img,s["sceneNumber"])])
PY
```

**코덱스는 NAS 에 못 쓴다.** `gen_scenes.py -o` 는 반드시 로컬(`_imggen/…`)로
주고 나중에 프로젝트로 옮긴다. 생성은 되고 저장만 조용히 실패한다.
