#!/usr/bin/env python3
"""생성된 씬 이미지를 나레이션과 함께 보고 검수한다 (Gemini 멀티모달).

**지금까지의 채점은 메타데이터만 봤다.** 연출 설계가 잘 됐는지는 알 수 있어도
나온 그림이 실제로 좋은지는 모른다. 프롬프트가 훌륭해도 결과물이 엉망일 수 있고,
그 둘은 다른 질문이다.

씬 이미지 + 나레이션 + 화면 텍스트를 함께 보고 판단한다.

    python3 scripts/review_images_gemini.py <review_in.json> -o <out.json>
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

MODEL = "gemini-2.5-pro"
REF = Path("_imggen/review_small/_ref_sheet.jpg")   # 세모지 기준 캐릭터 시트
BATCH = 6

RUBRIC = """당신은 한국 유튜브 다큐멘터리 〈브랜드백과사전 LG편〉의 화면을 검수합니다.

**첫 번째 이미지가 이 채널의 그림체 기준입니다.** 세모지 공식 캐릭터 시트입니다.
그림체를 말로 설명하지 않겠습니다. 그 그림을 직접 보고 기준으로 삼으세요.
인물 등신, 눈·코·입 처리, 외곽선 유무, 그림자 방식, 색면의 채도를 눈으로 대조하세요.

두 번째 이미지부터가 검수 대상 씬입니다. 나레이션과 함께 판단하세요.

씬마다 다음을 봅니다.

1. 내용 일치 — 그림이 나레이션이 말하는 바로 그 장면인가.
   엉뚱한 시대·장소·사물이 그려졌으면 여기서 감점입니다.
2. 화풍 일관 — 위 그림체에서 벗어나지 않았는가. 검은 외곽선, 사실적 묘사,
   8등신 인물, 지나친 질감은 벗어난 것입니다.
3. 인물 — 같은 인물이 다른 씬과 같은 사람으로 보이는가. 얼굴·머리·옷이
   흔들리면 감점. (cast가 비어 있으면 해당 없음)
4. 시대 고증 — 복식·건물·소품이 그 연대에 맞는가.
5. 화면 완성도 — 구도가 안정적인가. 인물이 너무 작아 안 보이거나, 손·얼굴이
   뭉개졌거나, 글자가 이미지에 박혀 있으면 감점.
6. 레이어 분리 — 배경·중경·인물·전경이 층으로 나뉘어 2.5D 모션을 넣을 수 있는가.

각 항목 1~5점(5가 좋음). verdict는 keep(그대로 씀) / fix(재생성 권함) /
reject(반드시 다시) 중 하나.
문제가 있으면 무엇이 어떻게 잘못됐는지 구체적으로 쓰세요. 없으면 짧게.

JSON만 출력하세요. 설명 문장을 앞뒤에 붙이지 마세요.
{"scenes":[{"n":1,"content":5,"style":5,"character":5,"period":5,"quality":5,
"layers":5,"verdict":"keep","issue":""}]}"""


def call(api_key: str, parts: list[dict], retries: int = 3) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={api_key}")
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=body,
                                         headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=300).read())
            return d["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:200]
            if i == retries - 1:
                raise RuntimeError(f"HTTP {e.code} {msg}")
            time.sleep(5 * (i + 1))
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(5 * (i + 1))
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("review_in", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    args = ap.parse_args()

    key = dotenv_values(".env").get("GOOGLE_API_KEY")
    if not key:
        print("GOOGLE_API_KEY 없음")
        return 1

    rows = json.loads(args.review_in.read_text(encoding="utf-8"))["scenes"]
    out: list[dict] = []

    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        # 그림체는 말로 옮기면 매번 재해석된다 — 기준 그림을 직접 붙인다
        parts: list[dict] = [{"text": RUBRIC}]
        if REF.exists():
            parts.append({"inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(REF.read_bytes()).decode()}})
        for r in chunk:
            meta = {k: r.get(k) for k in
                    ("n", "narration", "headline", "items", "layout", "badge", "cast")}
            parts.append({"text": f"\n[씬 {r['n']}]\n"
                                  + json.dumps(meta, ensure_ascii=False)})
            img = Path(r.get("small") or r["image"])
            parts.append({"inline_data": {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(img.read_bytes()).decode(),
            }})
        try:
            txt = call(key, parts)
            parsed = json.loads(txt)
            # 모델이 {"scenes":[...]} 대신 [...] 를 그대로 주기도 한다
            got = parsed.get("scenes", []) if isinstance(parsed, dict) else parsed
            out += got
            print(f"  씬 {chunk[0]['n']}~{chunk[-1]['n']}: {len(got)}건", flush=True)
        except Exception as e:
            print(f"  씬 {chunk[0]['n']}~{chunk[-1]['n']} 실패: {e}", flush=True)

    args.out.write_text(json.dumps({"model": MODEL, "scenes": out},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    if out:
        keys = ("content", "style", "character", "period", "quality", "layers")
        avg = {k: sum(x.get(k, 0) for x in out) / len(out) for k in keys}
        print("\n평균 " + " / ".join(f"{k} {v:.1f}" for k, v in avg.items()))
        for v in ("keep", "fix", "reject"):
            n = sum(1 for x in out if x.get("verdict") == v)
            print(f"  {v}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
