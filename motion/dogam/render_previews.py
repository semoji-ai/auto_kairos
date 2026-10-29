"""기법 도감 미리보기 렌더러 — 갤러리 데모마다 짧은 mp4 + 포스터 jpg 를 만든다.

Dogam 컴포지션(video/src/dogam)에 --props id 를 넘겨 한 편씩 렌더한다. 이미 있는 파일은 건너뛴다(--force 로 재렌더).
    python3 motion/dogam/render_previews.py            # 전부
    python3 motion/dogam/render_previews.py charts-03  # 특정 id
출력 폴더: 환경변수 DOGAM_PREVIEWS_DIR, 없으면 로컬 캐시 motion/dogam/previews (NAS 에 직접 쓰지 않는다).
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO = ROOT / "video"
sys.path.insert(0, str(ROOT / "dogam"))
from previews_dir import LOCAL  # noqa: E402

OUT = Path(os.environ.get("DOGAM_PREVIEWS_DIR") or LOCAL).expanduser()
GROUPS = ["core", "charts", "transitions", "callouts", "characters", "backgrounds", "x_transitions", "x_text", "x_callouts", "x_charts", "x_media", "x_acting", "kit", "x_explainer"]


def demo_ids():
    """레지스트리와 같은 규칙(id 직접 지정, 없으면 group-NN). 이름 추출은 build_techniques.gallery_names 와 동일한 정규식."""
    ids = []
    for g in GROUPS:
        txt = (VIDEO / f"src/gallery/{g}.tsx").read_text()
        body = txt.split("export const DEMOS", 1)[1].split("export const GALLERY_DUR", 1)[0]
        for i, m in enumerate(re.finditer(r'(?:^\s*(?:\{\s*name:|AB\(\{\s*name:|D\()\s*)"([^"]+)"(.*)$', body, re.M), 1):
            x = re.search(r'\bid:\s*"([^"]+)"', m.group(2))   # 데모 id 직접 지정(demo-<기법 id>)
            ids.append(x.group(1) if x else f"{g}-{i:02d}")
    return ids


def render(i, force=False):
    mp4, jpg = OUT / f"{i}.mp4", OUT / f"{i}.jpg"
    if mp4.exists() and jpg.exists() and not force:
        return i, "skip"
    props = json.dumps({"id": i})
    try:
      r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Dogam", str(mp4), f"--props={props}",
                        "--scale=0.5", "--crf=26", "--concurrency=2", "--timeout=120000", "--gl=angle", "--log=error"],
                       cwd=VIDEO, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:   # 멈춘 렌더(타일·폰트 대기 등)는 15분에 끊고 다음 편으로
        return i, "FAIL timeout"
    if r.returncode != 0:
        return i, "FAIL " + (r.stderr or r.stdout)[-300:]
    # 포스터: 효과가 자리 잡은 뒤(70% 지점) 한 장
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)]))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * (0.45 if i.startswith('transitions') else 0.7):.2f}", "-i", str(mp4), "-frames:v", "1", "-q:v", "4", str(jpg)])
    return i, "ok"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    ids = args or demo_ids()
    print(f"{len(ids)}편 렌더")
    with ThreadPoolExecutor(max_workers=3) as ex:
        for i, st in ex.map(lambda x: render(x, force), ids):
            print(i, st, flush=True)


if __name__ == "__main__":
    main()
