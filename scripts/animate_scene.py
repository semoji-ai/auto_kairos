#!/usr/bin/env python3
"""재연 씬을 레이어로 갈라 2.5D로 움직인다 — 5초짜리 시험 영상.

씬 이미지 한 장을 Seedream 5.0 layerize(fal)로 요소별 투명 PNG로 쪼갠 뒤,
인물은 **발을 축으로 까딱**이고 배경은 천천히 밀어(패럴랙스) mp4로 굽는다.

발을 축으로 삼는 이유: 가운데를 축으로 흔들면 발이 땅에서 떠 미끄러진다.
사람은 발이 붙어 있고 몸이 흔들린다.

    python3 scripts/animate_scene.py EP01 23
    python3 scripts/animate_scene.py EP01 23 --skip-split   # 이미 나눈 레이어 재사용
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

FPS = 30
DUR = 5.0

PERSON = ("man", "woman", "boy", "girl", "elder", "person", "people",
          "남성", "여성", "노파", "소년", "인물", "사람")

# 인물 앞을 지나가는 것들. 이것을 함께 떼지 않으면 인물이 까딱일 때 가려져 있던
# 부분이 드러나거나, 소품이 인물에 붙어 같이 흔들린다.
OCCLUDER = ("작업대", "책상", "탁자", "서안", "카운터", "난간", "울타리", "담",
            "수레", "상자", "가마", "궤짝", "화분", "풀숲", "덤불", "바위",
            "table", "desk", "counter", "fence", "railing", "cart", "crate")


def occluders_from_prompt(prompt: str) -> list[str]:
    """인물 앞을 지나갈 수 있는 것을 뽑는다.

    전경만 보면 안 된다. 우리 프롬프트 관례에서 인물은 중경과 전경 사이에 서지만,
    「허리 높이의 작업대가 화면을 가로지르고」처럼 **중경 소품이 인물을 가리는**
    경우가 흔하다. 실제로 EP03 씬 41이 그랬다."""
    import re as _re
    segs = []
    for pat in (r"(Mid ground|중경)\s*[:/]\s*([^.]*)", r"(Foreground|전경)\s*[:/]\s*([^.]*)"):
        m = _re.search(pat, prompt or "")
        if m:
            segs.append(m.group(2))
    seg = " ".join(segs)
    return list(dict.fromkeys(w for w in OCCLUDER if w in seg))


def is_person(name: str) -> bool:
    n = (name or "").lower()
    return any(k in n for k in PERSON)


def bob_params(name: str, idx: int) -> tuple[float, float, float]:
    """인물마다 위상·주기·폭을 흩어 놓는다.

    위상을 일정하게 어긋내면(0.7씩) 파도타기처럼 순서대로 넘실거려 어색하다.
    사람은 각자 다른 박자로 움직인다. 이름을 씨앗으로 삼아 흩되, 같은 씬을
    다시 뽑아도 같은 결과가 나오게 한다.

      위상  0 ~ 2π 무작위
      주기  0.5 ~ 0.85 Hz (약 1.2 ~ 2초)
      폭    0.7% ~ 1.3%
    """
    rnd = random.Random(f"{name}:{idx}")
    return (rnd.uniform(0, 2 * math.pi),
            rnd.uniform(0.5, 0.85),
            rnd.uniform(0.007, 0.013))


def foot_of(im: Image.Image) -> tuple[int, int]:
    """알파가 살아 있는 가장 아래 지점 — 발이 땅에 닿는 자리."""
    a = im.split()[-1]
    bbox = a.getbbox()
    if not bbox:
        return im.width // 2, im.height
    x0, y0, x1, y1 = bbox
    row = y1 - 1
    xs = [x for x in range(x0, x1) if a.getpixel((x, row)) > 12]
    return ((xs[0] + xs[-1]) // 2 if xs else (x0 + x1) // 2), y1


def _claude_vision(image: Path, instructions: str) -> dict | None:
    """클로드에게 그림을 보여 주고 JSON을 받는다 — 코덱스가 막혔을 때의 눈.

    코덱스에는 사용량 한도가 있어 판단이 통째로 멈춘다. 그런데 여기서 코덱스가
    하는 일은 **그림을 보는 것뿐**이고, 그건 클로드도 한다. 헤드리스로 Read
    도구만 열어 주면 그림을 읽는다.

    작업 폴더가 신뢰되지 않았다는 경고가 앞에 붙어 나오므로 JSON만 골라낸다.
    """
    prompt = (f"{image} 을 Read 도구로 열어 보고 아래를 판단하세요.\n"
              "설명 문장 없이 **JSON만** 출력하세요.\n\n" + instructions)
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=600, env=env)
    except Exception as e:
        print(f"  클로드 호출 실패: {e}")
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        print("  클로드가 JSON을 내지 않았습니다")
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError:
        print("  클로드 응답을 읽지 못했습니다")
        return None


def _ask_vision(image: Path, instructions: str, out_file: Path) -> dict | None:
    """그림을 보고 판단한다. 코덱스를 먼저, 막혔으면 클로드로.

    코덱스는 결과를 파일에 쓰고, 클로드는 말로 답한다 — 받는 쪽을 하나로
    맞추려고 클로드 답도 같은 파일에 적어 둔다.
    """
    out_file.parent.mkdir(parents=True, exist_ok=True)
    prompt = ("$imagegen\n\n**먼저 view_image로 아래 그림을 불러오세요.**\n"
              f"{image}\n\n{instructions}\n\n결과를 {out_file} 에 저장하세요.")
    try:
        subprocess.run(["codex", "exec", "--skip-git-repo-check",
                        "--sandbox", "workspace-write", prompt],
                       stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, timeout=900)
    except Exception:
        pass
    if out_file.exists():
        try:
            return json.loads(out_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    print("  코덱스가 답하지 않아 클로드로 봅니다")
    d = _claude_vision(image, instructions)
    if d:
        out_file.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def scene_image_of(project: Path, n: int) -> Path | None:
    """이 씬에서 고른 이미지."""
    db = json.loads((project / "images" / "image_assets.json").read_text(encoding="utf-8"))
    sel = next((i["file"] for e in db["scenes"] if e["sceneNumber"] == n
                for i in e["images"] if i.get("selected")), None)
    return (project / "images" / sel) if sel else None


PLAN_PROMPT = """첨부한 그림은 다큐멘터리 한 장면입니다. 이 장면을 **몇 개의 층으로
가를지** 정합니다. 가른 층은 각각 따로 움직이거나, 카메라가 들어갈 때 앞뒤로
갈라져 깊이를 만듭니다.

## 이 장면의 내레이션

{narration}

## 무엇을 가를 것인가

**움직여야 하는 것**과 **가리는 것**을 가릅니다.

- 사람은 각각 따로 가릅니다 — 사람만 까딱입니다.
- **사람 앞을 지나가는 것**은 반드시 따로 가릅니다. 함께 두면 사람이 움직일 때
  가려져 있던 부분이 드러나거나, 소품이 사람에 붙어 같이 흔들립니다.
- **작업대·책상 위에 놓인 물건**은 상판과 따로 가릅니다. 함께 두면 상판이
  그 물건들을 덮습니다.
- 내레이션이 가리키는 물건이 있으면 따로 가릅니다 — 그것만 나타나거나
  강조될 수 있어야 합니다.
- 배경은 하나로 둡니다.

너무 잘게 가르지 않습니다. 움직일 필요도 없고 아무것도 가리지 않는 것은
배경에 둡니다.

## 순서가 중요합니다

**화면에서 뒤에 있는 것부터 앞에 있는 것 순으로** 적습니다. 이 순서가 그대로
층 순서가 되므로, 여기서 틀리면 나중에 뒤죽박죽이 됩니다.

큰 가구를 조심하세요. **작업대는 사람보다 앞이지만, 그 위에 놓인 물건보다는
뒤입니다.** 상판이 물건을 덮으면 안 됩니다.

## 낼 것

이름은 그림에서 가리키는 그대로 짧은 한국어로 씁니다
(사람은 이름이 있으면 그 이름).

{{"layers":[{{"name":"", "is_person":false, "why":"왜 따로 가르는지 한 마디"}}],
  "note":"앞뒤 순서를 이렇게 정한 근거 한 문장"}}
"""


def plan_layers(scene_image: Path, narration: str, out_dir: Path) -> tuple[list[str], set[str]] | None:
    """그림과 내레이션을 함께 보고 **무엇을 가를지, 어떤 순서로 가를지** 정한다.

    예전에는 키워드 목록(OCCLUDER)으로 정했다. 「작업대」·「상자」가 목록에
    있으면 떼고 없으면 못 뗐다. 장면마다 무엇이 무엇을 가리는지는 그림을 봐야
    아는 것이라, 목록은 매번 조금씩 틀렸다.

    순서도 여기서 정한다. layerize에 넘기는 이름 순서가 곧 층 순서가 되므로,
    뒤에서 앞으로 적어 보내면 나중에 z를 고칠 일이 없다.
    """
    res = out_dir / "layer_plan.json"
    d = _ask_vision(scene_image,
                    PLAN_PROMPT.format(narration=(narration or "").strip()[:400]),
                    res)
    if not d:
        return None
    rows = [L for L in d.get("layers", []) if (L.get("name") or "").strip()]
    if not rows:
        return None
    names = [L["name"].strip() for L in rows]
    people = {L["name"].strip() for L in rows if L.get("is_person")}
    print(f"  층 계획 {len(names)}개 (뒤→앞): {', '.join(names)}")
    print(f"  근거: {d.get('note', '')}")
    return names, people


def split(project: Path, n: int, names: list[str], out: Path,
          people: set[str] | None = None) -> list[dict]:
    # adobe는 5.0에서 저장소 안으로 들어왔다. 홈 아래 옛 폴더를 가리키고 있어
    # 그 폴더를 지우는 순간 조용히 깨진다.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adobe"))
    from backend import fal_api

    db = json.loads((project / "images" / "image_assets.json").read_text(encoding="utf-8"))
    sel = next(i["file"] for e in db["scenes"] if e["sceneNumber"] == n
               for i in e["images"] if i.get("selected"))
    src = project / "images" / sel
    print(f"  분리 요청: {', '.join(names)}")
    layers = fal_api.layerize(src, names)
    out.mkdir(parents=True, exist_ok=True)
    meta = []
    for i, L in enumerate(layers):
        nm = L.get("name") or "bg"
        p = out / f"{i:02d}_{nm.replace(' ', '_')[:24]}.png"
        p.write_bytes(L["data"])
        # 역할은 이름으로 짐작하지 않는다 — 「김해수」·「구인회」는 어떤 키워드에도
        # 안 걸린다. 분리를 요청할 때 무엇이 인물이었는지 우리는 이미 안다.
        role = ("bg" if not L.get("bbox")
                else "person" if (people and nm in people) else "prop")
        meta.append({"name": nm, "role": role, "z": L.get("z", i),
                     "path": str(p), "bbox": L.get("bbox")})
        print(f"    {i:02d} {nm}")
    (out / "layers.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return meta


ORDER_PROMPT = """첨부한 그림은 한 장의 장면입니다. 이 장면을 아래 요소들로 갈랐습니다.

{names}

**그림을 보고 앞뒤 순서를 정하세요.** 화면에서 뒤에 있는 것부터 앞에 있는 것 순으로
나열합니다. 가까이 있어 다른 것을 가리는 것일수록 뒤로 갑니다(목록의 끝).

주의할 것이 하나 있습니다. **책상·작업대처럼 큰 가구는 사람보다 앞이지만,
그 위에 놓인 물건보다는 뒤입니다.** 상판이 물건을 덮으면 안 됩니다.
배경판(bg)은 언제나 맨 처음입니다.

각 요소가 사람인지도 함께 적으세요 — 사람만 움직입니다.

{{"order":["뒤에 있는 것", "...", "앞에 있는 것"],
  "people":["사람인 요소 이름"],
  "note":"판단 근거 한 문장"}}
"""


def order_by_vision(scene_image: Path, meta: list[dict], out_dir: Path) -> list[dict] | None:
    """장면 그림을 직접 보고 앞뒤를 정한다.

    이름 규칙으로 정하면 틀린다. 「가림 소품은 맨 위」로 했더니 작업대가
    **책상 위 부품까지** 덮었다 — 부품은 배경판에 있는데 상판이 그 위로 올라갔다.
    상판은 사람보다 앞이지만 그 위의 물건보다는 뒤다. 그건 그림을 봐야 안다."""
    names = "\n".join(f"- {m['name']}" for m in meta if m.get("bbox"))
    d = _ask_vision(scene_image, ORDER_PROMPT.format(names=names), out_dir / "z_order.json")
    if not d:
        return None
    by = {m["name"]: m for m in meta}
    ordered = [m for m in meta if not m.get("bbox")]          # 배경판 먼저
    for nm in d.get("order", []):
        if nm in by and by[nm].get("bbox"):
            ordered.append(by[nm])
    for m in meta:                                            # 빠진 것 뒤에 붙임
        if m not in ordered:
            ordered.append(m)
    ppl = set(d.get("people") or [])
    for i, m in enumerate(ordered):
        m["z"] = i
        if m.get("bbox"):
            m["role"] = "person" if m["name"] in ppl else "prop"
    print(f"  앞뒤 판정: {' → '.join(m['name'] for m in ordered)}")
    if d.get("note"):
        print(f"    {d['note'][:90]}")
    return ordered


def fix_z(meta: list[dict]) -> list[dict]:
    """가림 소품을 인물 위로 올린다.

    layerize가 매기는 z를 그대로 믿으면 안 된다. EP03 씬 41에서 작업대를 z=2,
    인물을 z=3~6으로 줘서 **사람들이 작업대 위에 서 있는** 화면이 나왔다.
    원본에서는 작업대 뒤에 서서 하반신이 가려져 있었다.

    우리는 어느 것이 가림 소품인지 이미 안다 — 그 이름으로 분리를 요청했다.
    배경판은 맨 아래, 인물은 가운데, 가림 소품은 맨 위로 다시 세운다."""
    def role(m):
        return m.get("role") or ("bg" if not m.get("bbox")
                                 else "person" if is_person(m["name"]) else "prop")
    bg = [m for m in meta if role(m) == "bg"]
    people = [m for m in meta if role(m) == "person"]
    props = [m for m in meta if role(m) == "prop"]
    # 인물끼리는 아래쪽(발이 낮은)일수록 앞이다 — 앞줄이 뒷줄을 가린다
    people.sort(key=lambda m: m["bbox"][3])
    ordered = bg + people + props
    for i, m in enumerate(ordered):
        m["z"] = i
    return ordered


def animate(meta: list[dict], out_mp4: Path, size=(1792, 1024),
            scene_image: Path | None = None) -> None:
    # 층 계획을 세우고 나눴다면 순서는 이미 맞다 — 다시 물을 이유가 없다.
    # 계획 없이 나눈 옛 결과에는 그림을 보고 앞뒤를 고치는 단계가 필요하다.
    planned = (out_mp4.parent / "layer_plan.json").exists()
    ordered = (None if planned
               else order_by_vision(scene_image, meta, out_mp4.parent) if scene_image else None)
    meta = ordered or (meta if planned else fix_z(meta))
    frames = int(FPS * DUR)
    tmp = out_mp4.parent / "_frames"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.png"):
        f.unlink()

    # layerize는 요소를 **바운딩 박스로 잘라** 돌려준다. 전체 화면에 늘이면 안 되고
    # bbox 크기로 줄여 그 자리에 놓아야 원래 구도가 살아난다(배경판만 풀프레임).
    loaded = []
    for m in meta:
        im = Image.open(m["path"]).convert("RGBA")
        bb = m.get("bbox")
        if bb:
            x0, y0, x1, y1 = bb
            im = im.resize((max(x1 - x0, 1), max(y1 - y0, 1)))
            org = (x0, y0)
        else:
            if im.size != size:
                im = im.resize(size)
            org = (0, 0)
        loaded.append((m, im, foot_of(im), (m.get("role") == "person"), org))

    for k in range(frames):
        t = k / FPS
        canvas = Image.new("RGBA", size, (0, 0, 0, 255))
        for idx, (m, im, foot, person, org) in enumerate(loaded):
            layer = im
            dx = dy = 0
            if person:
                # 세로로만 아주 살짝 늘였다 줄인다 — 100% ↔ 101%.
                # 회전을 주면 몸이 기울어 부자연스럽다. 까딱임은 세로 눌림이다.
                # 축은 발이다 — 아래가 고정되고 위로만 늘어난다.
                ph, freq, amp = bob_params(m["name"], idx)
                e = (1 - math.cos(2 * math.pi * (t * freq) + ph)) / 2   # 0↔1 이징
                sy = 1.0 + amp * e
                h2 = max(int(round(im.height * sy)), 1)
                layer = im.resize((im.width, h2), Image.BICUBIC)
                dy = im.height - h2                                      # 발 위치 고정
            # 배경과 소품은 고정한다. 카메라가 안 움직이는데 배경만 흔들면
            # 깊이가 생기는 게 아니라 화면이 미끄러진다.
            canvas.alpha_composite(layer, (org[0] + dx, org[1] + dy))
        canvas.convert("RGB").save(tmp / f"{k:04d}.png")

    subprocess.run(["ffmpeg", "-y", "-framerate", str(FPS), "-i", str(tmp / "%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    str(out_mp4)], capture_output=True)
    print(f"  → {out_mp4}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("scene", type=int)
    ap.add_argument("--skip-split", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    project = Path(next(v["dir"] for k, v in emap.items() if k.startswith(args.ep)))
    out = root / "_imggen" / f"{args.ep.lower()}_anim" / f"s{args.scene:03d}"

    if args.skip_split and (out / "layers.json").exists():
        meta = json.loads((out / "layers.json").read_text(encoding="utf-8"))
    else:
        spec = {s["sceneNumber"]: s for s in json.loads(
            (project / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
        s = spec[args.scene]

        # ① 그림과 내레이션을 함께 보고 무엇을 어떤 순서로 가를지 정한다.
        #    layerize에 넘기는 이름 순서가 그대로 층 순서가 되므로
        #    뒤에서 앞으로 보내야 뒤죽박죽이 되지 않는다.
        img = scene_image_of(project, args.scene)
        # 이미 세워 둔 계획이 있으면 그것을 쓴다. 화면에서 사람이 보고
        # 고친 목록이 있는데 다시 물으면 그 손질이 버려진다.
        saved = out / "layer_plan.json"
        if saved.exists():
            d = json.loads(saved.read_text(encoding="utf-8"))
            rows = [L for L in d.get("layers", []) if (L.get("name") or "").strip()]
            plan = ([L["name"].strip() for L in rows],
                    {L["name"].strip() for L in rows if L.get("is_person")}) if rows else None
            if plan:
                print(f"  세워 둔 계획을 씁니다 ({len(plan[0])}층)")
        else:
            plan = plan_layers(img, s.get("narration") or "", out) if img else None

        if plan:
            names, people = plan
        else:
            # 폴백 — 계획을 못 얻으면 예전 방식(이름 목록 + 키워드)으로 간다
            print("  층 계획 실패 — 이름 목록으로 진행합니다")
            names = [p.split("(")[0].strip() for p in (s.get("people") or [])]
            if not names and s.get("cast"):
                rost = {e["id"]: e["name"] for e in json.loads(
                    (root / "_imggen" / "characters" / "roster.json").read_text(encoding="utf-8"))}
                names = [rost.get(c, c) for c in s["cast"]]
            people = set(names)
            occ = occluders_from_prompt((s.get("imageAsset") or {}).get("prompt", ""))
            if occ:
                print(f"  가림 소품 함께 분리: {', '.join(occ)}")
            names = (names + occ)[:6]

        meta = split(project, args.scene, names[:8], out, people=people)

    animate(meta, out / f"scene_{args.scene:03d}_5s.mp4",
            scene_image=scene_image_of(project, args.scene))
    return 0


if __name__ == "__main__":
    sys.exit(main())
