# Video Asset Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 씬에 실제 YouTube 자료영상을 배경으로 재생하는 `videoAsset` 필드를 scene_specs → 매니페스트 → Remotion 렌더러 전 과정에 추가하고, Gemini Video API로 각 영상의 타임스탬프별 장면 데이터를 추출하여 적절한 구간을 자동으로 씬에 매핑한다.

**Architecture:** (1) `video_analyzer.py` — Gemini Video API로 mp4 업로드 → 타임스탬프별 장면 JSON 생성. (2) `build_manifest.py` 확장 — video_assets.json 룩업 → 매니페스트 씬에 `videoPath` + `videoAsset` 주입. (3) `SceneRenderer.tsx` 확장 — `videoAsset` 필드 감지 시 `ImageBg` 대신 `VideoBg` 컴포넌트로 배경 렌더링. 양쪽 remotion 폴더(`remotion/src/` ↔ `auto_agent/remotion_template/src/`) 동기화 필수.

**Tech Stack:** Python 3.9+, `google-genai`, Remotion `OffthreadVideo`, TypeScript, pathlib

---

## 파일 구조

| 파일 | 역할 |
|------|------|
| `auto_agent/tools/video_analyzer.py` | **신규** — Gemini Video API 래퍼. mp4 업로드 → 타임스탬프 JSON 반환 |
| `auto_agent/scripts/analyze_video_sources.py` | **신규** — video_sources/ 전체 분석 스크립트. video_scenes.json 생성 |
| `output/{id}/video_sources/video_scenes.json` | **신규** — 영상별 타임스탬프 장면 데이터 |
| `output/{id}/video_assets.json` | **신규** — 씬별 videoAsset 할당 (image_assets.json 패턴) |
| `auto_agent/scripts/build_manifest.py` | **수정** — video_assets.json 룩업 → 매니페스트 videoPath/videoAsset 주입 |
| `remotion/src/components/SceneRenderer.tsx` | **수정** — VideoBg 컴포넌트 + videoAsset 분기 추가 |
| `auto_agent/remotion_template/src/components/SceneRenderer.tsx` | **수정** — 위와 동일 (동기화) |

---

## Task 1: Gemini Video 분석 도구 구현

**Files:**
- Create: `auto_agent/tools/video_analyzer.py`

- [ ] **Step 1: 테스트 파일 작성**

```python
# tests/tools/test_video_analyzer.py
import json, pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

def test_analyze_returns_scenes_list():
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "duration_sec": 61.0,
        "scenes": [
            {"start": 0.0, "end": 3.0, "description": "타이틀 카드 — 포켓몬 로고 등장", "tags": ["title", "logo"]},
            {"start": 3.0, "end": 8.0, "description": "피카츄 달리기 장면", "tags": ["pikachu", "action"]},
        ]
    })
    with patch("auto_agent.tools.video_analyzer._gemini_generate", return_value=mock_response):
        from auto_agent.tools.video_analyzer import analyze_video
        result = analyze_video(Path("dummy.mp4"))
    assert isinstance(result["scenes"], list)
    assert result["scenes"][0]["start"] == 0.0
    assert "description" in result["scenes"][0]

def test_analyze_handles_json_fenced():
    mock_response = MagicMock()
    mock_response.text = '```json\n{"duration_sec": 30.0, "scenes": []}\n```'
    with patch("auto_agent.tools.video_analyzer._gemini_generate", return_value=mock_response):
        from auto_agent.tools.video_analyzer import analyze_video
        result = analyze_video(Path("dummy.mp4"))
    assert result["duration_sec"] == 30.0
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
python3 -m pytest tests/tools/test_video_analyzer.py -v 2>&1 | tail -10
```
Expected: `ImportError` 또는 `ModuleNotFoundError` (파일 없으므로)

- [ ] **Step 3: video_analyzer.py 구현**

```python
# auto_agent/tools/video_analyzer.py
"""
Gemini Video API로 mp4 분석 → 타임스탬프별 장면 JSON 반환

사용법:
    from auto_agent.tools.video_analyzer import analyze_video
    result = analyze_video(Path("video.mp4"))
    # result = {"duration_sec": 61.0, "scenes": [{"start": 0.0, "end": 3.0, "description": "...", "tags": [...]}]}
"""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    from google.genai import types as gtypes
except ImportError as e:
    raise ImportError("google-genai 패키지 필요: pip install google-genai") from e

_client: "genai.Client | None" = None

def _get_client() -> "genai.Client":
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


ANALYZE_PROMPT = """이 영상을 분석해서 장면별 타임스탬프 데이터를 JSON으로 반환하세요.

규칙:
- 의미 있는 장면 전환마다 새 항목 생성 (최소 1초 단위)
- description은 한국어로 영상 내용을 구체적으로 묘사
- tags는 영상에 등장하는 핵심 요소 (캐릭터명, 행동, 장소 등 영어 소문자)

아래 JSON 형식으로만 응답 (다른 텍스트 없이):
{
  "duration_sec": 영상_총_길이_초,
  "language": "ja 또는 en 또는 ko",
  "scenes": [
    {
      "start": 시작_초,
      "end": 종료_초,
      "description": "장면 한국어 설명",
      "tags": ["tag1", "tag2"]
    }
  ]
}"""


def _gemini_generate(video_bytes: bytes, mime_type: str) -> "gtypes.GenerateContentResponse":
    """내부 헬퍼 — 테스트에서 mock 대상."""
    client = _get_client()
    return client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            gtypes.Part.from_bytes(data=video_bytes, mime_type=mime_type),
            ANALYZE_PROMPT,
        ],
    )


def _gemini_generate_large(video_path: Path, mime_type: str) -> "gtypes.GenerateContentResponse":
    """20MB 초과 영상용 — File API 업로드 후 분석."""
    client = _get_client()
    uploaded = client.files.upload(
        file=str(video_path),
        config=gtypes.UploadFileConfig(mime_type=mime_type),
    )
    # 업로드 완료 대기
    for _ in range(30):
        if uploaded.state != "PROCESSING":
            break
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
    if uploaded.state == "FAILED":
        raise RuntimeError(f"Gemini 파일 업로드 실패: {uploaded.name}")
    try:
        return client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                gtypes.Part.from_uri(file_uri=uploaded.uri, mime_type=mime_type),
                ANALYZE_PROMPT,
            ],
        )
    finally:
        client.files.delete(name=uploaded.name)


def analyze_video(video_path: Path) -> dict:
    """mp4/webm 영상을 Gemini로 분석하여 장면 타임스탬프 dict 반환.

    Returns:
        {
            "duration_sec": float,
            "language": str,
            "scenes": [{"start": float, "end": float, "description": str, "tags": list[str]}]
        }
    """
    suffix = video_path.suffix.lower()
    mime_map = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}
    mime_type = mime_map.get(suffix, "video/mp4")

    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    if file_size_mb <= 19:
        video_bytes = video_path.read_bytes()
        response = _gemini_generate(video_bytes, mime_type)
    else:
        response = _gemini_generate_large(video_path, mime_type)

    raw = response.text.strip()
    # ```json ... ``` 펜스 제거
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    return json.loads(raw)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python3 -m pytest tests/tools/test_video_analyzer.py -v 2>&1 | tail -10
```
Expected: `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/video_analyzer.py tests/tools/test_video_analyzer.py
git commit -m "feat: add Gemini video analyzer tool"
```

---

## Task 2: 영상 소스 일괄 분석 스크립트

**Files:**
- Create: `auto_agent/scripts/analyze_video_sources.py`

- [ ] **Step 1: 스크립트 구현**

```python
#!/usr/bin/env python3
"""
video_sources/ 폴더의 모든 mp4를 Gemini로 분석하여 video_scenes.json 생성.

사용법:
    python3 -m auto_agent.scripts.analyze_video_sources \
        --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편

출력:
    output/{project}/video_sources/video_scenes.json
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from auto_agent.utils.workspace import get_workspace_dir
from auto_agent.tools.video_analyzer import analyze_video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="output/ 하위 프로젝트 폴더명")
    parser.add_argument("--force", action="store_true", help="이미 분석된 파일도 재분석")
    args = parser.parse_args()

    ws = get_workspace_dir()
    video_dir = ws / "output" / args.project / "video_sources"
    if not video_dir.exists():
        print(f"[error] video_sources 폴더 없음: {video_dir}")
        sys.exit(1)

    out_path = video_dir / "video_scenes.json"
    # 기존 결과 로드 (증분 실행 지원)
    existing: dict = {}
    if out_path.exists() and not args.force:
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    mp4_files = sorted(video_dir.glob("*.mp4"))
    if not mp4_files:
        print("[warn] mp4 파일 없음")
        sys.exit(0)

    results: dict = dict(existing)

    for mp4 in mp4_files:
        key = mp4.name
        if key in results and not args.force:
            print(f"[skip] {key} (already analyzed)")
            continue
        print(f"[analyze] {key} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)...")
        try:
            data = analyze_video(mp4)
            data["file"] = key
            results[key] = data
            print(f"  → {len(data.get('scenes', []))}개 장면, {data.get('duration_sec', 0):.1f}초")
        except Exception as e:
            print(f"  [error] {key}: {e}")
            results[key] = {"file": key, "error": str(e), "scenes": []}

        # 중간 저장 (중단 대비)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n완료: {out_path}")
    print(f"분석된 영상: {len(results)}개")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 실제 영상 분석 실행**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
python3 -m auto_agent.scripts.analyze_video_sources \
    --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

Expected: 6개 파일 분석, `video_sources/video_scenes.json` 생성.
각 영상마다 장면 목록(start/end/description/tags)이 출력됨.

- [ ] **Step 3: 결과 확인**

```bash
python3 -c "
import json
data = json.load(open('output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/video_sources/video_scenes.json'))
for k, v in data.items():
    scenes = v.get('scenes', [])
    print(f'{k}: {len(scenes)}장면, {v.get(\"duration_sec\",0):.1f}초')
    for s in scenes[:3]:
        print(f'  {s[\"start\"]:.1f}-{s[\"end\"]:.1f}s: {s[\"description\"][:60]}')
"
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/scripts/analyze_video_sources.py \
        output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/video_sources/video_scenes.json
git commit -m "feat: add video source analyzer script + analysis results"
```

---

## Task 3: video_assets.json 생성 (씬 → 타임코드 매핑)

video_scenes.json 결과를 보고 각 씬에 어떤 영상의 어느 구간을 쓸지 결정하는 JSON을 만든다.

**Files:**
- Create: `output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/video_assets.json`

- [ ] **Step 1: video_assets.json 스키마 정의 및 초기 파일 작성**

video_scenes.json 분석 결과를 참고하여 다음 구조로 작성:

```json
{
  "scenes": [
    {
      "sceneNumber": 25,
      "videoFile": "mjCK2D88bCs_ポケットモンスター　初代ＣＭ.mp4",
      "startSec": 0.0,
      "endSec": 30.0,
      "placement": "background",
      "opacity": 0.7,
      "volume": 0.0,
      "note": "1996년 출시 CM 전체 — 씬 배경으로 음소거 재생"
    },
    {
      "sceneNumber": 32,
      "videoFile": "R4GIyJxvk94_Pokémon： Indigo League 📺 ｜ Opening Theme.mp4",
      "startSec": 0.0,
      "endSec": 15.0,
      "placement": "background",
      "opacity": 0.65,
      "volume": 0.0,
      "note": "오프닝 타이틀 첫 15초 — 애니 방영 씬 배경"
    },
    {
      "sceneNumber": 41,
      "videoFile": "4QBsSTajfP0_BBC News Report On The Banned Pokémon Ep.mp4",
      "startSec": 0.0,
      "endSec": 30.0,
      "placement": "background",
      "opacity": 0.6,
      "volume": 0.0,
      "note": "BBC 뉴스 리포트 앞부분 — 포켓몬 쇼크 보도 장면"
    },
    {
      "sceneNumber": 43,
      "videoFile": "4QBsSTajfP0_BBC News Report On The Banned Pokémon Ep.mp4",
      "startSec": 30.0,
      "endSec": 60.0,
      "placement": "background",
      "opacity": 0.6,
      "volume": 0.0,
      "note": "BBC 뉴스 이어지는 부분 — 685명 구급이송 씬"
    },
    {
      "sceneNumber": 64,
      "videoFile": "5T7aObdI2do_【予告編】劇場版ポケットモンスター ミュウツーの逆襲.mp4",
      "startSec": 0.0,
      "endSec": 30.0,
      "placement": "background",
      "opacity": 0.75,
      "volume": 0.0,
      "note": "뮤츠의 역습 예고편 앞부분 — 극장판 개봉 씬"
    }
  ]
}
```

> **주의:** `startSec`/`endSec`는 Task 2의 video_scenes.json 결과를 보고 실제 원하는 장면 타임코드로 업데이트할 것. 위 값은 초기 추정치.

- [ ] **Step 2: video_assets.json 저장**

```bash
# 위 JSON을 파일로 저장
python3 -c "
import json
# (위 JSON 내용을 파일로 쓰는 코드)
data = { ... }  # 위 JSON
json.dump(data, open('output/9f202fb4_.../video_assets.json', 'w'), ensure_ascii=False, indent=2)
"
```

실제로는 직접 파일 편집기로 작성해도 무방.

- [ ] **Step 3: 커밋**

```bash
git add output/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편/video_assets.json
git commit -m "feat: add video_assets.json with scene timecode mapping"
```

---

## Task 4: build_manifest.py — videoAsset 주입

**Files:**
- Modify: `auto_agent/scripts/build_manifest.py`

- [ ] **Step 1: video_assets.json 룩업 코드 추가**

`build_manifest.py`에서 `image_assets_lookup` 빌드 직후 (약 line 232 이후)에 추가:

```python
# video_assets.json → {sceneNumber: videoAsset} 룩업
video_assets_lookup: dict = {}
video_assets_path = out_dir / "video_assets.json"
if video_assets_path.exists():
    try:
        va_data = json.loads(video_assets_path.read_text(encoding="utf-8"))
        for va_entry in va_data.get("scenes", []):
            sn = va_entry.get("sceneNumber")
            if sn is not None:
                video_assets_lookup[sn] = va_entry
    except Exception:
        pass
```

- [ ] **Step 2: 매니페스트 엔트리에 videoPath/videoAsset 주입**

씬 루프 안에서 `image_path` 빌드 직후 (약 line 265 이후)에 추가:

```python
# Video — video_assets.json에 있으면 videoPath + videoAsset 주입
video_path = ""
video_asset_cfg: dict = {}
va_entry = video_assets_lookup.get(num)
if va_entry:
    video_file = va_entry.get("videoFile", "")
    video_src = out_dir / "video_sources" / video_file
    if video_src.exists():
        # video_sources/ → project/video_sources/ symlink 경로
        video_path = link_asset(video_src, "video_sources", video_file)
    video_asset_cfg = {
        "placement": va_entry.get("placement", "background"),
        "startSec": va_entry.get("startSec", 0.0),
        "endSec": va_entry.get("endSec", None),
        "opacity": va_entry.get("opacity", 0.7),
        "volume": va_entry.get("volume", 0.0),
    }
```

- [ ] **Step 3: entry 딕셔너리에 videoPath/videoAsset 추가**

entry 딕셔너리 빌드 부분 (`entry["imagePath"]` 근처)에 추가:

```python
entry["videoPath"] = video_path
if video_asset_cfg:
    entry["videoAsset"] = video_asset_cfg
```

- [ ] **Step 4: video_sources 심링크 설정**

`link_asset`은 `project/video_sources/` 경로를 반환하는데, `project/` 심링크가 output 폴더를 가리키므로 `video_sources/` 하위 폴더도 자동으로 접근 가능. 단, Remotion `staticFile()` 사용 시 `public/project/video_sources/` 경로임을 확인:

```python
# build_manifest.py 상단 project 심링크 설정 부분 (약 line 130-140) — 이미 처리됨
# project_link → out_dir.resolve() 심링크이므로 video_sources도 자동 포함됨
# 추가 작업 불필요
```

- [ ] **Step 5: 매니페스트 재빌드 테스트**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
python3 -m auto_agent.scripts.build_manifest \
    --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편

# 결과 확인 — 씬25에 videoPath/videoAsset이 있어야 함
python3 -c "
import json
m = json.load(open('remotion/public/manifests/9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편.json'))
scenes = m.get('scenes', m.get('data', []))
for s in scenes:
    if s.get('videoPath'):
        print(f'씬{s.get(\"sceneNumber\")}: {s[\"videoPath\"]} | {s.get(\"videoAsset\")}')
"
```
Expected: 씬 25, 32, 41, 43, 64에 `videoPath`와 `videoAsset` 출력.

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/scripts/build_manifest.py
git commit -m "feat: build_manifest — inject videoPath/videoAsset from video_assets.json"
```

---

## Task 5: SceneRenderer.tsx — VideoBg 컴포넌트 + videoAsset 분기

**Files:**
- Modify: `remotion/src/components/SceneRenderer.tsx`
- Modify: `auto_agent/remotion_template/src/components/SceneRenderer.tsx`

- [ ] **Step 1: remotion import에 OffthreadVideo 추가**

`SceneRenderer.tsx` line 9 수정:

```typescript
// 변경 전
import { AbsoluteFill, Img, staticFile } from "remotion";

// 변경 후
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useVideoConfig } from "remotion";
```

- [ ] **Step 2: VideoBg 컴포넌트 추가 (ImageBg 바로 다음)**

`ImageBg` 컴포넌트 (line 52–65) 다음에 삽입:

```typescript
/* ── 비디오 배경 ── */
export const VideoBg: React.FC<{
  src: string;
  opacity: number;
  startSec?: number;
  endSec?: number;
  volume?: number;
}> = ({ src, opacity, startSec = 0, volume = 0 }) => {
  const { fps } = useVideoConfig();
  const startFrom = Math.round(startSec * fps);
  return (
    <AbsoluteFill style={{ zIndex: 0, overflow: "hidden" }}>
      <OffthreadVideo
        src={resolveUrl(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity,
        }}
        startFrom={startFrom}
        volume={volume}
        muted={volume === 0}
        playbackRate={1}
        pauseWhenBuffering
      />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: SceneRendererInner에서 videoAsset 분기 처리**

`SceneRendererInner` 내부 (line 171–)에서 `sceneImage` 선언 바로 다음에 videoAsset 읽기 추가:

```typescript
// 기존 (line 179)
const sceneImage = scene.imagePath || scene.vizBackgroundPath || "";
const hasSceneImage = !!sceneImage;

// 추가 — videoAsset 읽기
const videoPath = scene.videoPath || "";
const videoAssetCfg = scene.videoAsset as {
  placement?: string;
  startSec?: number;
  endSec?: number;
  opacity?: number;
  volume?: number;
} | undefined;
const hasVideo = !!videoPath && !!videoAssetCfg;
const videoPlacement = videoAssetCfg?.placement ?? "background";
const videoOpacity = videoAssetCfg?.opacity ?? 0.7;
const videoStartSec = videoAssetCfg?.startSec ?? 0;
const videoEndSec = videoAssetCfg?.endSec;
const videoVolume = videoAssetCfg?.volume ?? 0;
```

- [ ] **Step 4: background 분기에 VideoBg 삽입**

`SceneRendererInner` 내 `// ── background (기본) ──` 분기 (line 257–270) 수정:

```typescript
// ── background (기본) ──
return (
  <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
    {/* 비디오 배경: videoAsset 있으면 VideoBg, 아니면 기존 ImageBg */}
    {hasVideo && videoPlacement === "background" ? (
      <VideoBg
        src={videoPath}
        opacity={videoOpacity}
        startSec={videoStartSec}
        endSec={videoEndSec}
        volume={videoVolume}
      />
    ) : (
      hasAnyImage && <ImageBg src={imgSrc} opacity={imgOpacity} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale} fit={imgFit} />
    )}
    <CreativeScene
      data={vizData}
      subtitles={scene.subtitles}
      fps={fps}
      hasImageBackground={hasAnyImage || hasVideo}
      imageAssetPlacement={placement}
    />
    {textureCfg && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
  </AbsoluteFill>
);
```

- [ ] **Step 5: fullscreen 분기에도 VideoBg 지원 추가**

`// ── fullscreen ──` 분기 (line 202–216) 수정:

```typescript
if ((hasAnyImage || hasVideo) && (placement === "fullscreen" || (hasVideo && videoPlacement === "fullscreen"))) {
  return (
    <AbsoluteFill style={{ backgroundColor: preset.colors.bg, fontFamily }}>
      {hasVideo && videoPlacement === "fullscreen" ? (
        <VideoBg src={videoPath} opacity={videoOpacity} startSec={videoStartSec} endSec={videoEndSec} volume={videoVolume} />
      ) : (
        <ImageBg src={imgSrc} opacity={imgOpacity >= 0.8 ? imgOpacity : 0.9} offsetX={imgOffsetX} offsetY={imgOffsetY} scale={imgScale} fit={imgFit} />
      )}
      <CreativeScene data={vizData} subtitles={scene.subtitles} fps={fps} hasImageBackground={true} imageAssetPlacement="fullscreen" />
      {textureCfg && <TextureOverlay src={textureCfg.src} blendMode={textureCfg.blendMode} opacity={textureCfg.opacity} />}
    </AbsoluteFill>
  );
}
```

- [ ] **Step 6: TypeScript 타입 에러 없는지 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3/remotion
npx tsc --noEmit 2>&1 | head -20
```
Expected: 에러 없음

- [ ] **Step 7: remotion_template 동기화**

```bash
cp remotion/src/components/SceneRenderer.tsx \
   auto_agent/remotion_template/src/components/SceneRenderer.tsx
```

- [ ] **Step 8: 커밋**

```bash
git add remotion/src/components/SceneRenderer.tsx \
        auto_agent/remotion_template/src/components/SceneRenderer.tsx
git commit -m "feat: SceneRenderer — add VideoBg component + videoAsset background support"
```

---

## Task 6: Vite 번들 재빌드 + 스토리보드 확인

**Files:**
- 빌드 산출물 (tracked 아님)

- [ ] **Step 1: Vite 빌드 (Node 22 직접 호출)**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3/remotion
/opt/homebrew/opt/node@22/bin/node node_modules/vite/bin/vite.js build --config vite.thumb.config.ts
/opt/homebrew/opt/node@22/bin/node node_modules/vite/bin/vite.js build --config vite.editor.config.ts
```
Expected: `✓ built in` 메시지 (에러 없음)

- [ ] **Step 2: 대시보드 재시작 및 스토리보드 확인**

```bash
# 대시보드가 실행 중이라면 재시작
# python -m uvicorn app:app --host 0.0.0.0 --port 8080

# 씬 25, 32, 64가 비디오 배경으로 렌더링되는지 스토리보드에서 확인
open http://localhost:8080
```

- [ ] **Step 3: 매니페스트 재빌드**

```bash
python3 -m auto_agent.scripts.build_manifest \
    --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편
```

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "build: rebuild vite bundles for videoAsset support"
git push
```

---

## Self-Review

**1. Spec coverage 체크:**
- ✅ Gemini Video API로 타임스탬프 추출 → Task 1, 2
- ✅ video_assets.json으로 씬↔타임코드 매핑 → Task 3
- ✅ build_manifest.py videoPath/videoAsset 주입 → Task 4
- ✅ Remotion VideoBg 컴포넌트 + 분기 → Task 5
- ✅ 빌드 및 확인 → Task 6

**2. Placeholder 없음 확인:**
- 모든 스텝에 실제 코드/명령어 포함 ✅
- Task 3 Step 2에 "..." 주석이 있으나 앞 Step에서 JSON 전체 제시했으므로 허용 ✅

**3. 타입 일관성:**
- `videoAsset.startSec/endSec` — build_manifest ↔ SceneRenderer ↔ video_assets.json 동일 ✅
- `VideoBg` 컴포넌트 props — `startSec`, `endSec`, `opacity`, `volume` 일관 ✅
- `link_asset` 반환값 → `videoPath` → `resolveUrl()` 처리 — 기존 `imagePath` 패턴과 동일 ✅
