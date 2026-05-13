"""씬별 익명 엑스트라 캐릭터 LLM 추출.

캐스트 없는 씬 대상. narration·title·entities 기반으로 씬을 시각화할 때 자연스러운
익명 캐릭터(시민·기자·학생·발표자 등) 1~2명을 제안한다.

출력: projects/{project}/scene_extras.json
    { "<scene_number>": [ { "label": "...", "description_en": "...", "description_ko": "...", "action_hint": "..." } ] }
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from scene_layer_animate import _load_env, resolve_project_dir

SYSTEM = """너는 이로미즘 스타일 영상 PD다. 한국어 다큐멘터리 씬에 등장할 익명 엑스트라 캐릭터를 한 명만 제안한다.

규칙:
- 실존 인물·트레이드마크 금지. 일반 직업/역할만.
- 이로미즘 톤: 3등신 stubby + UGLY-CUTE + 단순한 옷차림.
- **씬 맥락에 가장 어울리는 역할을 다양하게 선택**. 다음은 예시 풀이며 매번 다르게:
  · 미디어/외신 씬 → 앵커, 신문기자, 라디오DJ
  · 데이터/통계/지표 씬 → 안경 쓴 분석가, 칠판 앞 교수, 도표 들고 있는 학자
  · 사회/세대 씬 → 어르신, 20대 청년, 직장인, 카페 손님, 학생, 노점상
  · 교육 씬 → 책상 앞 학생, 칠판 앞 선생, 교과서 든 학부모
  · 산업/경제 씬 → 공장 작업자, 화이트칼라, 자영업자
  · 외교/안보 씬 → 양복 차림 외교관, 군인
  · 인구/저출산 씬 → 유모차 미는 부모, 빈 의자 보는 어르신
  · 자원/에너지 씬 → 등이 굽은 시민, 손전등 든 사람 — 어색하면 null
- action_hint는 매번 다르게 (가리키기 외에도: 글 쓰기, 책 보기, 박수, 어깨 으쓱, 한숨, 미소, 손짓 등).
- 같은 description을 절대 반복 금지.

출력은 JSON 한 줄:
{"label":"<역할>","description_en":"...","description_ko":"...","action_hint":"<구체 동작>"}
또는 null"""


def extract_for_scene(client: OpenAI, scene: dict) -> dict | None:
    user = f"""씬 {scene['sceneNumber']}: {scene.get('title','')}
section: {scene.get('section','')}
narration: {scene.get('narration','')[:500]}
entities: {scene.get('entities',[])[:5]}"""
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":user}],
        temperature=0.4,
        response_format={"type":"json_object"},
    )
    txt = r.choices[0].message.content.strip()
    try:
        d = json.loads(txt)
        if isinstance(d, dict) and d.get("label"): return d
        if isinstance(d, dict) and d.get("extra"): return d["extra"]  # 모델이 감싸는 경우
    except Exception:
        pass
    return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--scenes", help="쉼표 구분 씬 번호 (생략 시 전체)")
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    _load_env()
    client = OpenAI()
    pdir = resolve_project_dir(args.project)
    specs = json.loads((pdir / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    roster = json.loads((pdir / "characters" / "roster.json").read_text(encoding="utf-8"))
    casts = roster.get("scene_casts", {})

    targets = []
    selected = set(int(x) for x in args.scenes.split(",")) if args.scenes else None
    for s in specs:
        n = s["sceneNumber"]
        if selected and n not in selected: continue
        if casts.get(str(n)) or casts.get(n): continue  # 캐스트 있는 씬 제외
        targets.append(s)
        if args.limit and len(targets) >= args.limit: break

    print(f"대상 씬 {len(targets)}개")
    out_path = pdir / "scene_extras.json"
    existing = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    def _work(s):
        try: return (s["sceneNumber"], extract_for_scene(client, s))
        except Exception as e: return (s["sceneNumber"], {"_error": str(e)[:120]})

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(_work, s): s for s in targets}
        for fut in as_completed(futs):
            n, res = fut.result()
            existing[str(n)] = [res] if res and "_error" not in res else (res or [])
            tag = res.get("label") if isinstance(res, dict) and res.get("label") else ("(없음)" if not res else "err")
            print(f"  씬 {n:>2}: {tag}")

    out_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nscene_extras.json: {out_path}")


if __name__ == "__main__":
    main()
