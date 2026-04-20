# imageAsset 결정 일원화 구현 플랜

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** imageAsset 결정 권한을 Creative Direction에 일원화하고, placement별 이미지 비율을 최적화한다.

**Architecture:** Scene Decomposition에서 imageAsset 초기화를 제거하고, Creative Direction이 layout과 함께 imageAsset을 결정한다. Asset Advisory는 query 보강 + 심볼/차트만 담당하며 source/placement를 변경하지 않는다. 이미지 생성 시 placement에 따라 적합한 aspect_ratio를 적용한다.

**Tech Stack:** Python (runner.py, source_images.py), Markdown 프롬프트

---

## Task 1: Scene Decomposition에서 imageAsset 제거

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:1538-1551`

- [ ] **Step 1: imageAsset 초기화 및 힌트 코드 제거**

`runner.py:1538-1551`에서 `imageAsset: None` 초기화와 decomposition 힌트 세팅을 제거한다.

현재 코드:
```python
                "transition": {"type": "fade", "durationFrames": 15},
                "imageAsset": None,
                "mapScene": None,
            }
            # decomposition에서 이미지/맵 힌트가 있으면 전달
            if s.get("has_image_asset"):
                ia = s.get("image_asset") or {}
                scene["imageAsset"] = {
                    "source": ia.get("source", "search"),
                    "query": ia.get("query", s.get("title", "")),
                    "placement": ia.get("placement", "background"),
                    "opacity": ia.get("opacity", 0.3),
                }
            scenes.append(scene)
```

수정 코드:
```python
                "transition": {"type": "fade", "durationFrames": 15},
                "mapScene": None,
            }
            scenes.append(scene)
```

`imageAsset` 필드 자체를 넣지 않는다. LLM이 "아직 결정 안 됨 → 내가 채워야 함"으로 판단하게 한다.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "refactor: Scene Decomposition에서 imageAsset 초기화 제거 — Asset 결정은 Creative Direction 전담"
```

---

## Task 2: 병합 함수에서 imageAsset 승격 로직 보강

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:1588-1594`

- [ ] **Step 1: 병합 로직 수정**

현재 코드 (방금 수정한 승격 포함):
```python
                # imageAsset 머지 (top-level 우선, visualization에서 승격 fallback)
                if "imageAsset" in llm:
                    result["imageAsset"] = llm["imageAsset"]
                elif llm.get("visualization", {}).get("imageAsset") and not result.get("imageAsset"):
                    result["imageAsset"] = llm["visualization"]["imageAsset"]
```

수정 코드:
```python
                # imageAsset 머지 (top-level 우선, visualization에서 승격 fallback)
                if "imageAsset" in llm and llm["imageAsset"]:
                    result["imageAsset"] = llm["imageAsset"]
                elif llm.get("visualization", {}).get("imageAsset"):
                    result["imageAsset"] = llm["visualization"]["imageAsset"]
```

변경점: `llm["imageAsset"]`이 None이 아닌 경우만 top-level 우선. `result.get("imageAsset")` 체크 제거 — visualization에서 항상 승격 가능하게.

- [ ] **Step 2: 병합 직후 cinematic 검증 추가**

`_merge_llm_response` 함수 끝, `return merged` 직전에 추가:

```python
        # cinematic 씬 검증: placement=fullscreen 강제
        for scene in merged:
            creative = (scene.get("visualization") or {}).get("creative") or {}
            if creative.get("layout") == "cinematic":
                if not scene.get("imageAsset"):
                    scene["imageAsset"] = {"source": "generate", "placement": "fullscreen"}
                else:
                    scene["imageAsset"]["placement"] = "fullscreen"
                    if "opacity" in scene["imageAsset"]:
                        del scene["imageAsset"]["opacity"]
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "fix: 병합 함수에서 imageAsset 승격 보강 + cinematic→fullscreen 강제 검증"
```

---

## Task 3: Asset Advisory 프롬프트 수정 — source/placement 변경 금지

**Files:**
- Modify: `auto_agent/data/prompts/single-call/asset-advisory.md:1-17`

- [ ] **Step 1: 역할 범위 명확화**

프롬프트 상단(라인 1-3)을 수정:

현재:
```markdown
당신은 영상 Asset Advisor입니다. Creative Direction이 완료된 scene_specs를 받아 시각 에셋(차트, 아이콘, 국기, 로고, 이미지)을 추천하고 레이아웃을 확정합니다.

**중요**: creative 필드의 concept/reveal/emphasis/mood/headline은 이미 설계되었습니다. 이를 수정하지 말고, 에셋과 레이아웃만 보강하세요.
```

수정:
```markdown
당신은 영상 Asset Advisor입니다. Creative Direction이 완료된 scene_specs를 받아 **차트, 아이콘, 국기, 로고**를 추천하고, 이미지 query를 보강합니다.

**중요 — 수정 금지 필드:**
- creative 필드 전체 (concept/reveal/emphasis/mood/headline/layout)
- imageAsset.source (generate/search/wikimedia — Creative Direction이 결정 완료)
- imageAsset.placement (fullscreen/background/left/right — Creative Direction이 결정 완료)
- sceneNumber, chapter, narration, durationFrames

**수정 가능 필드:**
- imageAsset.query / searchQuery / fallbackQuery (검색어/프롬프트 품질 보강)
- chartConfig (차트 설정 추가)
- itemIcons / itemFlags (심볼 추가)
- displayMode / logoMap (로고 그리드)
- images 배열 (인물 이미지 슬롯)
```

- [ ] **Step 2: task 섹션 수정 (라인 11-16)**

현재:
```markdown
각 씬에 대해 4개 관점으로 분석하고 에셋을 보강하세요:
1. 📊 차트 관점: 데이터 비교/비중/추세가 있으면 chartConfig 추가
2. 🏷️ 심볼 관점: items에 맞는 itemIcons(Lucide) 또는 itemFlags(국가 ISO) 추가
3. 🖼️ 이미지 관점: 인물/장소/사건 씬에 imageAsset 보강
4. 📐 레이아웃 관점: 데이터 밀도와 의도에 맞는 creative.layout 확정
```

수정:
```markdown
각 씬에 대해 3개 관점으로 분석하고 에셋을 보강하세요:
1. 📊 차트 관점: 데이터 비교/비중/추세가 있으면 chartConfig 추가
2. 🏷️ 심볼 관점: items에 맞는 itemIcons(Lucide) 또는 itemFlags(국가 ISO) 추가
3. 🖼️ 이미지 query 보강: imageAsset이 있는 씬의 query/searchQuery/fallbackQuery 품질 개선 (source와 placement는 변경 금지)

⚠️ layout과 imageAsset.source/placement는 Creative Direction이 결정 완료. 변경하지 마세요.
```

- [ ] **Step 3: cinematic 절대 규칙 추가**

`<image_rules>` 섹션 끝(라인 144 뒤)에 추가:

```markdown
## cinematic 씬 절대 규칙
- layout="cinematic"인 씬의 imageAsset을 절대 변경하지 않는다
- placement는 반드시 "fullscreen" 유지
- source 변경 금지
- cinematic 씬에 items/headline이 있더라도 placement를 left/right로 바꾸지 않는다
```

- [ ] **Step 4: layout 확정 섹션 제거 (라인 147-154)**

`<layout_rules>` 섹션 전체 제거 — layout은 Creative Direction 전담.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/data/prompts/single-call/asset-advisory.md
git commit -m "refactor: Asset Advisory 역할 축소 — query 보강만, source/placement/layout 변경 금지"
```

---

## Task 4: Creative Direction 프롬프트에서 imageAsset 결정 강화

**Files:**
- Modify: `auto_agent/data/prompts/single-call/creative-direction.md:82-93`

- [ ] **Step 1: imageAsset 결정이 Creative Direction의 책임임을 명확화**

라인 82 앞에 주석 추가:

```markdown
- imageAsset: ⚠️ **Creative Direction이 최종 결정자**. Asset Advisory는 query만 보강하고 source/placement를 변경하지 않는다.
```

- [ ] **Step 2: placement-layout 연동 규칙 명확화**

라인 90-92를 수정:

현재:
```markdown
  - placement: "fullscreen" | "background" | "center" | "left" | "right"
    - ⚠️ **layout="cinematic"이면 반드시 placement="fullscreen"** (center, background 등 사용 금지)
  - opacity: 배경 투명도 (0.0~1.0). cinematic이면 생략 (자동 1.0)
```

수정:
```markdown
  - placement: "fullscreen" | "background" | "center" | "left" | "right"
    - ⚠️ **layout="cinematic"이면 반드시 placement="fullscreen"** (변경 금지)
    - left/right: 인물 배치용 (세로 3:4 비율로 생성됨)
    - fullscreen: 전체 화면용 (가로 16:9 비율로 생성됨)
    - background: 배경 보조용 (가로 16:9 비율로 생성됨)
  - opacity: 배경 투명도 (0.0~1.0). cinematic/fullscreen이면 생략 (자동 1.0)
```

- [ ] **Step 3: imageAsset이 없는 씬은 명시적으로 생략하도록 안내**

`<rules>` 섹션에 규칙 추가:

```markdown
11. 이미지가 불필요한 씬(순수 데이터/차트)은 imageAsset 필드를 아예 넣지 않는다. `imageAsset: null` 금지.
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/data/prompts/single-call/creative-direction.md
git commit -m "refactor: Creative Direction을 imageAsset 최종 결정자로 명확화 + placement-ratio 안내"
```

---

## Task 5: placement별 aspect_ratio 적용

**Files:**
- Modify: `auto_agent/scripts/source_images.py:354-360`

- [ ] **Step 1: placement → aspect_ratio 매핑 함수 추가**

`source_images.py`의 `_generate_one` 함수 앞 (라인 311 근처)에 추가:

```python
def _placement_to_ratio(placement: str) -> str:
    """placement에 따른 이미지 생성 aspect_ratio."""
    if placement in ("left", "right"):
        return "3:4"
    if placement == "center":
        return "1:1"
    # fullscreen, background, 기본값
    return "16:9"
```

- [ ] **Step 2: FAL API 호출에서 동적 ratio 적용**

라인 356-360 수정:

현재:
```python
            result = fal_client.subscribe("fal-ai/nano-banana-2/edit", arguments={
                "prompt": full_prompt,
                "image_urls": image_urls,
                "aspect_ratio": "16:9",
            })
```

수정:
```python
            placement = img.get("placement", "fullscreen")
            aspect_ratio = _placement_to_ratio(placement)
            result = fal_client.subscribe("fal-ai/nano-banana-2/edit", arguments={
                "prompt": full_prompt,
                "image_urls": image_urls,
                "aspect_ratio": aspect_ratio,
            })
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/source_images.py
git commit -m "feat: placement별 이미지 생성 비율 최적화 — left/right는 3:4, fullscreen/background는 16:9"
```

---

## Task 6: Creative 검증 fallback 양식 보정

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:1130-1131`

- [ ] **Step 1: cinematic fallback에 query 추가**

현재:
```python
                            if not scene.get("imageAsset"):
                                scene["imageAsset"] = {"source": "generate", "placement": "fullscreen"}
```

수정:
```python
                            if not scene.get("imageAsset"):
                                scene["imageAsset"] = {
                                    "source": "generate",
                                    "placement": "fullscreen",
                                    "query": scene.get("narration", "")[:200],
                                }
```

narration 앞 200자를 fallback query로 사용. 이미지 생성 모듈(`source_images.py:315-317`)이 query 없으면 skip하므로 반드시 채워야 함.

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "fix: cinematic fallback에 narration 기반 query 추가 — 이미지 생성 누락 방지"
```

---

## Task 7: remotion_template 동기화

**Files:**
- Confirm: `auto_agent/remotion_template/src/` — 이번 수정은 Python 파이프라인만 변경하므로 Remotion 코드 변경 없음. 동기화 불필요.

- [ ] **Step 1: 확인**

이번 수정은 runner.py, source_images.py, 프롬프트 파일만 변경. Remotion 소스 변경 없으므로 CLAUDE.md 규칙 1 (양쪽 동기화) 해당 없음을 확인.

---

## 변경 요약

| 파일 | 변경 내용 |
|------|----------|
| `runner.py:1538-1551` | imageAsset 초기화 + decomposition 힌트 제거 |
| `runner.py:1588-1594` | 승격 로직 보강 + cinematic→fullscreen 강제 |
| `runner.py:1130-1131` | fallback에 query 추가 |
| `asset-advisory.md` | 역할 축소: query 보강만, source/placement/layout 변경 금지 |
| `creative-direction.md` | imageAsset 최종 결정자 명확화 + placement-ratio 안내 |
| `source_images.py:354-360` | placement별 aspect_ratio 동적 적용 |
