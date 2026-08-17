# P9 — 레이어 품질: 소프트 크로마 + 실패 분류·재시도 + 정량 QC 게이트 Implementation Plan

**Goal:** 레이어 분리 품질 3종 개선 — ① 크로마 이진 알파 → 마젠타 거리 기반 **소프트 알파 + 가장자리 정리**, ② `_run_codex_image` 실패 사유 **분류**(rate_limit/no_file 구분), ③ split 요소 레이어 **정량 QC 게이트**(transparent_ratio 기준 자동 재시도 1회).

**Architecture:** `chroma_key_magenta`를 소프트 알파로 재작성(거리 기반 + erode + feather, numpy/PIL만). `_run_codex_image` 반환에 `error` 분류. `split_scene_to_elements._element`에서 chroma 결과의 `transparent_ratio`로 QC: `<0.05`(마젠타 지시 무시 — 전체를 그림) 또는 `>0.98`(요소 안 그림)이면 **피드백 한 줄 추가해 1회 재생성**, 그래도 실패면 status="completed_lowq"로 표시(레이어는 보존 — 무삭제).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`.

**현재 사실(확인됨):**
- `chroma_key_magenta(src_png, out_png)` — 임계값 마스크(r>150 & g<110 & b>150) → alpha 0/255 이진, 디스필(g<min(r,b)-40 픽셀의 r/b 감쇠), `{"transparent_ratio": float}` 반환. **반환값을 아무도 안 씀.**
- `split._element`: `_run_codex_image(..., post=lambda o: chroma_key_magenta(o, o))` — post 반환값 버려짐.
- `_run_codex_image`: rate limit 문자열일 때만 백오프 재시도, 실패 시 `{"status":"failed","error":"rate_limit_or_no_file","log_tail":...}`.
- `normalize_layer_size` 가드는 P8 직전에 추가됨(완료) — 요소·배경 생성 직후 호출.
- 테스트들이 `chroma_key_magenta`를 `lambda a, b: {"transparent_ratio": 0.5}` 로 monkeypatch — 시그니처/반환 유지 필수.

---

## Task 1: 소프트 크로마

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트**:

```python
def _mk_magenta_test_img(tmp_path):
    """중앙 빨강 사각형 + 마젠타 배경 + 경계 혼합색 1px 띠."""
    from PIL import Image
    im = Image.new("RGB", (100, 100), (255, 0, 255))          # 순수 마젠타
    for y in range(30, 70):
        for x in range(30, 70):
            im.putpixel((x, y), (200, 30, 40))                # 요소(빨강)
    for x in range(29, 71):                                    # 경계 혼합(반쯤 마젠타)
        im.putpixel((x, 29), (228, 15, 148)); im.putpixel((x, 70), (228, 15, 148))
    p = tmp_path / "m.png"; im.save(p)
    return p


def test_soft_chroma_core_kept_bg_removed(tmp_path):
    from PIL import Image
    from backend import imagegen as ig
    p = _mk_magenta_test_img(tmp_path)
    r = ig.chroma_key_magenta(p, p)
    out = Image.open(p).convert("RGBA")
    assert out.getpixel((50, 50))[3] == 255                   # 요소 중심 불투명
    assert out.getpixel((5, 5))[3] == 0                       # 마젠타 배경 완전 투명
    assert 0.5 < r["transparent_ratio"] < 0.95                # 비율 신호 유지


def test_soft_chroma_edge_soft_alpha(tmp_path):
    from PIL import Image
    from backend import imagegen as ig
    p = _mk_magenta_test_img(tmp_path)
    ig.chroma_key_magenta(p, p)
    out = Image.open(p).convert("RGBA")
    a = out.getpixel((50, 29))[3]                              # 혼합 경계 픽셀
    assert a < 255                                             # 이진(255)이 아니라 소프트
```

- [ ] **Step 2: 구현** — `chroma_key_magenta` 재작성(시그니처·반환 키 유지):

```python
def chroma_key_magenta(src_png: Path, out_png: Path) -> dict:
    """마젠타(#FF00FF) 거리 기반 소프트 알파 + 가장자리 수축·페더.
    반환 {"transparent_ratio": float} — QC 게이트 신호로 사용."""
    im = Image.open(src_png).convert("RGBA")
    a = np.array(im).astype(float)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    # 마젠타 유사도: r·b 높고 g 낮을수록 마젠타. dist 0=순수 마젠타.
    dist = np.sqrt((255 - r) ** 2 + g ** 2 + (255 - b) ** 2) / 441.673
    alpha = np.clip((dist - 0.18) / 0.22, 0.0, 1.0)           # 0.18 이하=투명, 0.40 이상=불투명
    # 가장자리 수축(erode 1px) — 마젠타 프린지 제거
    core = alpha >= 0.999
    er = core.copy()
    er[1:, :] &= core[:-1, :]; er[:-1, :] &= core[1:, :]
    er[:, 1:] &= core[:, :-1]; er[:, :-1] &= core[:, 1:]
    edge = core & ~er
    alpha[edge] *= 0.8                                        # 경계 페더
    # 디스필: 남은 픽셀의 마젠타 성분 감쇠(기존 로직 유지)
    keep = alpha > 0
    over = keep & (g < np.minimum(r, b) - 40)
    a[over, 0] = np.minimum(a[over, 0], a[over, 1] + 40)
    a[over, 2] = np.minimum(a[over, 2], a[over, 1] + 40)
    a[:, :, 3] = alpha * 255
    Image.fromarray(a.astype("uint8"), "RGBA").save(out_png)
    return {"transparent_ratio": float((alpha < 0.5).sum()) / alpha.size}
```

(임계 0.18/0.22는 테스트 통과 기준으로 조정 가능 — 순수 마젠타 dist=0, 빨강(200,30,40) dist≈0.49, 혼합(228,15,148) dist≈0.26. 구현 후 실측해 미세조정하되 테스트 의미는 유지.)

- [ ] **Step 3: 통과 + 기존 chroma 테스트 정합 확인 + 커밋** — `git commit -m "feat(chroma): 마젠타 거리 기반 소프트 알파 + erode·feather — 프린지 제거"`

---

## Task 2: 실패 분류

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트**:

```python
def test_run_codex_image_classifies_rate_limit(tmp_path, monkeypatch):
    from backend import imagegen as ig
    def fake_run(prompt, cwd, **kw):
        kw.get("on_line", lambda x: None)("image_gen rate limit exceeded")
        return {"returncode": 1, "output_last": None}
    monkeypatch.setattr(ig, "run_skill", fake_run)
    monkeypatch.setattr(ig.time, "sleep", lambda s: None)
    res = ig._run_codex_image(tmp_path, tmp_path / "x.png", "p", retries=1)
    assert res["status"] == "failed" and res["error"] == "rate_limit"


def test_run_codex_image_classifies_no_file(tmp_path, monkeypatch):
    from backend import imagegen as ig
    monkeypatch.setattr(ig, "run_skill", lambda *a, **k: {"returncode": 0, "output_last": None})
    res = ig._run_codex_image(tmp_path, tmp_path / "x.png", "p", retries=0)
    assert res["status"] == "failed" and res["error"] == "no_file"
```

- [ ] **Step 2: 구현** — `_run_codex_image` 마지막 반환을:

```python
    reason = "rate_limit" if is_rate_limited(last) else "no_file"
    return {"status": "failed", "error": reason, "log_tail": last[-200:]}
```

(기존 테스트가 `"rate_limit_or_no_file"` 문자열을 검사하면 갱신.)

- [ ] **Step 3: 통과 + 커밋** — `git commit -m "feat(imagegen): 실패 사유 분류(rate_limit/no_file)"`

---

## Task 3: split 정량 QC 게이트 + 1회 재시도

**Files:** Modify `backend/imagegen.py`; Test `tests/test_imagegen.py`

- [ ] **Step 1: 실패 테스트**:

```python
def test_split_qc_retries_on_bad_ratio(tmp_path, monkeypatch):
    from PIL import Image
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir()
    scene = proj / "storyboard" / "s.png"; Image.new("RGB", (100, 100)).save(scene)
    calls = {"n": 0}

    def fake_run_codex(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        calls["n"] += 1
        Image.new("RGBA", (100, 100)).save(out)
        if post: post(out)
        return {"status": "completed", "path": str(out)}

    # 1차: ratio 0.01(불량 — 전체를 그림), 2차: 0.6(정상)
    ratios = iter([0.01, 0.6])
    monkeypatch.setattr(ig, "_run_codex_image", fake_run_codex)
    monkeypatch.setattr(ig, "chroma_key_magenta", lambda a, b: {"transparent_ratio": next(ratios)})
    res = ig.split_scene_to_elements(proj, str(scene), "qc1",
                                     [{"name": "차", "location": "왼쪽"}], concurrency=1)
    el = res["layers"][0]
    assert calls["n"] >= 3                       # 요소 1차+재시도 + 배경 1
    assert el["status"] == "completed" and el.get("qc") == "retried_ok"


def test_split_qc_marks_lowq_after_retry(tmp_path, monkeypatch):
    from PIL import Image
    from backend import imagegen as ig
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "storyboard").mkdir()
    scene = proj / "storyboard" / "s.png"; Image.new("RGB", (100, 100)).save(scene)

    def fake_run_codex(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        Image.new("RGBA", (100, 100)).save(out)
        if post: post(out)
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(ig, "_run_codex_image", fake_run_codex)
    monkeypatch.setattr(ig, "chroma_key_magenta", lambda a, b: {"transparent_ratio": 0.005})  # 항상 불량
    res = ig.split_scene_to_elements(proj, str(scene), "qc2",
                                     [{"name": "차", "location": "왼쪽"}], concurrency=1)
    el = res["layers"][0]
    assert el["status"] == "completed_lowq"      # 보존하되 저품질 표시(무삭제)
```

- [ ] **Step 2: 구현** — `_element`를 QC 루프로 재구성:

```python
    QC_MIN, QC_MAX = 0.05, 0.98

    def _gen_element_once(out, prompt):
        ratio_box = {}
        def _post(o):
            ratio_box.update(chroma_key_magenta(o, o))
        res = _run_codex_image(proj_dir, out, prompt, images=[scene_image], post=_post)
        if res.get("status") == "completed" and scene_size:
            normalize_layer_size(out, scene_size)
        return res, ratio_box.get("transparent_ratio")

    def _element(i_el):
        i, el = i_el
        name, loc = el.get("name", f"el{i}"), el.get("location", "")
        out = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(name)}.png")
        rel = out.relative_to(proj_dir).as_posix()
        others = [nm for j, nm in enumerate(all_names) if j != i]
        prompt = build_element_layer_prompt(name, loc, style, rel, others=others)
        res, ratio = _gen_element_once(out, prompt)
        qc = None
        if res.get("status") == "completed" and ratio is not None and not (QC_MIN <= ratio <= QC_MAX):
            fb = ("이전 시도에서 마젠타 채움이 거의 없었다(전체를 그렸다). 요소 외 전 영역을 반드시 마젠타로."
                  if ratio < QC_MIN else
                  "이전 시도에서 요소가 거의 그려지지 않았다(전부 마젠타). 요소를 분명히 그려라.")
            out2 = versioned_path(out_base, f"{sid}__{i}_{_layer_slug(name)}.png")
            res2, ratio2 = _gen_element_once(out2, prompt + "\n[재시도 피드백] " + fb)
            if res2.get("status") == "completed" and ratio2 is not None and QC_MIN <= ratio2 <= QC_MAX:
                out, rel, res, qc = out2, out2.relative_to(proj_dir).as_posix(), res2, "retried_ok"
            else:
                res = {"status": "completed_lowq", "path": str(out)}   # 1차본 유지, 저품질 표시
        r = {"name": name, "rel": rel, "status": res.get("status"), "qc": qc}
        if on_event:
            on_event(r)
        return r
```

(주의: 기존 split 테스트들의 chroma monkeypatch가 `{"transparent_ratio": 0.5}` 반환 → QC 통과라 무영향. `test_split_normalizes_to_scene_size` 등도 0.5라 통과 확인.)

- [ ] **Step 3: 통과(전체 멱등 2회) + 커밋** — `git commit -m "feat(split): 정량 QC 게이트(transparent_ratio) + 피드백 1회 재시도, 저품질 표시(무삭제)"`

---

## Task 4: 통합 검증

- [ ] 전체 테스트 멱등 2회 + git 클린.
- [ ] 실제 chroma 화질 확인: tesla 기존 마젠타 원본이 없으므로, 테스트 픽스처 수준 검증으로 충분(다음 실분리에서 체감). 백엔드 재시작(8765 유지).

---

## Self-Review

- **시그니처 보존**: chroma_key_magenta(src,out)→{"transparent_ratio"} 유지 — 기존 monkeypatch 테스트 호환.
- **QC는 요소만**: 배경은 마젠타 방식이 아니라 ratio 무의미 — 게이트 제외.
- **무삭제**: 재시도는 versioned_path 새 파일, 저품질도 보존+표시.
- **재시도 1회 한정**: 비용 통제. 피드백 문구로 동일 실패 반복 확률 감소.
- **한계(정직)**: 정량 게이트는 "이중 등장"(배경에 제거 대상 잔존)을 못 잡음 — LLM 시각 QC(옵션)는 후속. 소프트 알파 임계값은 세모지 팔레트 기준 — 보라/분홍 위주 스타일에선 조정 필요.
