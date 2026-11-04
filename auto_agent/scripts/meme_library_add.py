"""밈 라이브러리에 장면 추가.  usage: meme_library_add.py <entries.json>
entries.json: [{"id": "nv1_youdontsay", "video": "<영상 경로>", "t": 215, "episode": "B145 엔비디아 1편",
                "type": "유명 밈 패러디", "meme": "니콜라스 케이지 You don't say", "narration": "…",
                "use": "펀치라인", "emotion": ["황당"], "tags": ["컴퓨터", "초창기"], "note": "…"}]
- 프레임을 1280px jpg로 auto_agent/data/artstyle/meme_library/img/<id>.jpg 에 저장
- index.json 에 항목 추가(같은 id면 갱신), README.md 표 다시 생성
밈 종류(type): 유명 밈 패러디 / 실사 캐리커처 반응 / 의인화 / 텍스트 폭발 / 인터넷 짤 패러디"""
import json, os, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LIB = os.path.join(ROOT, "auto_agent", "data", "artstyle", "meme_library")
FIELDS = ["id", "episode", "t", "type", "meme", "narration", "use", "emotion", "tags", "note"]


def grab(video, t, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video, "-frames:v", "1",
                    "-vf", "scale=1280:-2", "-q:v", "3", out], check=True)


def readme(items):
    head = open(os.path.join(LIB, "README.head.md")).read() if os.path.exists(os.path.join(LIB, "README.head.md")) else ""
    rows = ["| 그림 | id | 편·시각 | 종류 | 밈 | 쓰는 자리 | 감정 | 내레이션 |", "|---|---|---|---|---|---|---|---|"]
    for e in items:
        rows.append(f"| ![](img/{e['id']}.jpg) | `{e['id']}` | {e['episode']} {e['t']}초 | {e['type']} | {e.get('meme','')} | "
                    f"{e.get('use','')} | {', '.join(e.get('emotion', []))} | {e.get('narration','')} |")
    open(os.path.join(LIB, "README.md"), "w").write(head + "\n## 목록\n\n" + "\n".join(rows) + "\n")


if __name__ == "__main__":
    new = json.load(open(sys.argv[1]))
    ip = os.path.join(LIB, "index.json")
    items = json.load(open(ip)) if os.path.exists(ip) else []
    by = {e["id"]: e for e in items}
    for e in new:
        grab(e["video"], e["t"], os.path.join(LIB, "img", e["id"] + ".jpg"))
        by[e["id"]] = {k: e[k] for k in FIELDS if k in e}
        print("added", e["id"])
    items = sorted(by.values(), key=lambda e: (e["episode"], e["t"]))
    json.dump(items, open(ip, "w"), ensure_ascii=False, indent=1)
    readme(items)
    print(len(items), "items")
