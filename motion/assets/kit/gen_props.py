"""세모지 소품 키트 일괄 생성 — audit.json 의 props → codex 이미지젠(초록 배경) → 키잉 → video/public/kit/props/<id>.png

  python3 gen_props.py full     # 1단계: 소품 전체 그림
  python3 gen_props.py parts    # 2단계: 분리가 필요한 소품의 부위(전체 그림을 ref 로 같은 좌표 편집)
  python3 gen_props.py key      # 키잉 + 여백 크롭(부위는 전체 캔버스 유지 → 좌표 정렬) + props.json
  python3 gen_props.py sheet    # 확인용 시트

규칙: 글자·숫자는 그리지 않고 비워 둔다(코드가 올림). 국기·라인 아이콘·만화 장갑은 코드 유지(제외).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parent
OUT = KIT / "props"
PUB = KIT.parent.parent / "video/public/kit/props"
RUNNER = Path.home() / "Projects/codex-fleet/runners/codex_imagegen_runner.py"
KEY = Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"
STYLE = [str(KIT / "walk/out/base.png"), str(KIT.parent.parent / "video/public/img/s05_bowl.png"), str(KIT.parent.parent / "video/public/img/s03_restaurant.jpg")]
SKIP = {"flag_kr", "flag_cn", "flag_star_red", "union_flag", "line_icon_calendar", "line_icon_stopwatch", "cartoon_glove_hand", "lantern_red", "hand_kit",
        "crowd_silhouette_front", "crowd_back_silhouette", "old_phone", "iso_port_kit", "boarding_pass", "card_terminal", "ufo_and_moon", "octopus_monster",
        "clapping_palm", "spray_can", "sauce_jar_hand", "boxing_glove_robot_arm", "iron_ball_chain", "logo_mascot"}
STYLE_TXT = ("Flat 2D vector illustration in exactly the same style as the attached images (Korean history explainer YouTube style): no outlines, simple clean shapes, "
             "soft slightly muted colors, subtle paper grain texture, at most one soft shade tone per color. ")
BG = (" Single object only, centered, filling about 80% of the image. Background flat solid chroma green #00B140 everywhere else (do not use green in the object unless stated),"
      " no ground, no cast shadow, no text, no letters, no numbers (leave any label areas blank).")
TINT = " Draw it in plain light gray #D9D9D9 with a slightly darker gray #BDBDBD for inner details, so it can be recolored in code."

# 여러 변형·세트로 나눠 그리는 항목(원래 audit 항목 → 개별 id)
EXTRA = {
    "hand_open": ("세모지 플랫 손(오른손), 손바닥을 편 채 손가락 위로, 흰 셔츠 커프와 남색 정장 소매가 손목 아래로 조금 보임, 피부 #F2C7A5", "2:3"),
    "hand_grip": ("세모지 플랫 오른손이 무언가를 쥐는 모양(주먹을 느슨하게 쥐어 가운데가 빈 원통 구멍), 흰 커프 + 남색 소매", "1:1"),
    "hand_pinch_back": ("세모지 플랫 오른손, 엄지와 검지로 얇은 카드를 집는 포즈의 손 뒤쪽 부분(엄지는 그리지 않음), 흰 커프 + 남색 소매", "1:1"),
    "hand_thumb_front": ("세모지 플랫 엄지손가락 하나(카드 앞에 겹쳐 올라갈 엄지만, 옆으로 누운 모양), 피부 #F2C7A5", "1:1"),
    "hand_hold_bottom": ("세모지 플랫 오른손이 종이 아래 가장자리를 받쳐 든 모양(손가락 끝이 위로, 엄지 앞), 흰 커프 + 남색 소매", "1:1"),
    "hand_pen": ("세모지 플랫 오른손이 검은 펜을 쥐고 쓰는 모양(측면), 흰 커프 + 남색 소매", "1:1"),
    "hand_point_big": ("세모지 플랫 큰 손이 아래에서 위로 뻗어 검지로 가리킴(다른 손가락은 접음), 긴 남색 정장 소매 + 흰 커프 포함, 세로로 긴 구도", "2:3"),
    "hand_press_nozzle": ("세모지 플랫 오른손이 위에서 스프레이 캔 노즐을 검지로 누르는 모양(캔은 그리지 않음), 흰 커프 + 남색 소매", "1:1"),
    "hand_clap": ("세모지 플랫 손 측면(손가락을 모아 편 손바닥을 옆에서 본 모양, 엄지 위), 흰 커프, 박수 치는 손 한쪽", "1:1"),
    "crowd_v": ("얼굴 없는 단순 사람 실루엣(원형 머리 + 종 모양 몸), 양팔을 V자로 들어 환호" + TINT, "2:3"),
    "crowd_one": ("얼굴 없는 단순 사람 실루엣(원형 머리 + 종 모양 몸), 한 팔만 들어 흔듦" + TINT, "2:3"),
    "crowd_down": ("얼굴 없는 단순 사람 실루엣(원형 머리 + 종 모양 몸), 팔을 내리고 서 있음" + TINT, "2:3"),
    "crowd_back_a": ("관객 뒷모습 — 검은 머리(짧은 머리)와 어깨 흉상, 뒤에서 본 모습, 짙은 회색 옷", "1:1"),
    "crowd_back_b": ("관객 뒷모습 — 검은 긴 머리 묶은 머리와 어깨 흉상, 뒤에서 본 모습, 짙은 회색 옷", "1:1"),
    "crowd_back_phone": ("관객 뒷모습 — 검은 머리와 어깨, 한 팔을 들어 스마트폰을 머리 위로 든 모습(폰 화면 밝음)", "1:1"),
    "phone_bar_light": ("바형 옛날 휴대폰 정면 — 연회색 둥근 몸체, 작은 녹회색 화면, 3×4 키패드(버튼만, 숫자 없음)", "2:3"),
    "phone_bar_dark": ("바형 옛날 휴대폰 정면 — 짙은 회색 각진 몸체, 작은 녹회색 화면, 3×4 키패드(버튼만, 숫자 없음)", "2:3"),
    "iso_container": ("아이소메트릭(2:1) 화물 컨테이너 한 개, 골판 줄무늬" + TINT, "1:1"),
    "iso_crane": ("아이소메트릭(2:1) 빨간 항만 갠트리 크레인", "1:1"),
    "iso_warehouse": ("아이소메트릭(2:1) 크림색 벽 + 파란 지붕 창고", "1:1"),
    "iso_ship": ("아이소메트릭(2:1) 화물선(갑판 위 컨테이너 몇 개)", "3:2"),
    "boarding_pass_front": ("흰 항공 탑승권 — 위쪽 주황 헤더 띠, 오른쪽 점선 절취선 뒤 주황 스텁, 바코드 블록, 글자 자리는 빈 회색 줄", "3:2"),
    "boarding_pass_back": ("짙은 회색(#4A4A4A) 항공 탑승권 — 절취선 점선과 스텁, 글자 없음", "3:2"),
    "card_terminal": ("둥근 모서리 회색 카드 결제 단말기 정면 — 청록 테두리의 어두운 빈 화면, 초록·빨강 LED 두 개, 2×4 키패드(숫자 없음)", "2:3"),
    "receipt_strip": ("흰 영수증 종이 띠(아래 끝 지그재그), 회색 줄 몇 개", "2:3"),
    "ufo": ("회색 비행접시(UFO) 측면 — 투명 돔, 테두리 불빛 점", "3:2"),
    "moon": ("크레이터 있는 회색 달", "1:1"),
    "octopus_body": ("보라색 문어 괴물 몸통(머리) — 하이라이트, 노란 큰 눈 한 개와 눈꺼풀, 촉수 없이 몸통만", "1:1"),
    "octopus_tentacle": ("보라색 문어 촉수 하나(아래쪽에 분홍 빨판 줄), 살짝 S자로 휜 모양, 뿌리가 위쪽", "2:3"),
    "clapping_palm": ("살구색 손바닥 측면(손가락 모아 폄) + 엄지 + 흰 소매 커프, 박수 치는 손", "1:1"),
    "spray_can": ("하늘색 스프레이 캔 + 회색 노즐 캡", "2:3"),
    "sauce_jar": ("빨간 소스 병(둥근 어깨, 주황 원형 라벨 자리 비움) + 뚜껑", "2:3"),
    "boxing_glove_blue": ("큰 파란 복싱 글러브 측면(흰 커프, 로고 자리 비움)", "1:1"),
    "boxing_glove_red": ("큰 빨간 복싱 글러브 측면(흰 커프, 로고 자리 비움)", "1:1"),
    "robot_arm_segment": ("회색 금속 로봇팔 한 마디(원통형, 양끝 관절 원판)", "3:2"),
    "iron_ball": ("짙은 남청 쇳구슬(하이라이트) + 위쪽 고리", "1:1"),
    "chain_link": ("짙은 회색 쇠사슬 고리 한 개", "1:1"),
    "shuttle_flame": ("로켓 분사 불꽃 — 위가 좁고 아래로 퍼지는 노랑·주황 불꽃 기둥(세로), 부드러운 2~3톤", "2:3"),
    "mascot_disc": ("흰 원판(가장자리 흰 링), 눈 두 개(흰자 + 검은 눈동자), 아래에 작은 검은 발 두 개", "1:1"),
}
# 전체 그림 → 부위(같은 캔버스 편집). (부위 id, 부모 id, 남길 부분 설명)
PARTS = [
    ("royal_cape_back", "royal_cape", "only the crimson cape body (the part that goes behind the person), without the white fur collar"),
    ("royal_cape_collar", "royal_cape", "only the white ermine fur collar with black tail dots"),
    ("cloche_lid", "cloche_platter", "only the silver dome lid with its handle"),
    ("cloche_plate", "cloche_platter", "only the white plate and the small black plaque in front"),
    ("gavel_hammer", "gavel_set", "only the wooden gavel (head and long handle)"),
    ("gavel_block", "gavel_set", "only the round wooden sound block (base)"),
    ("throne_back", "throne", "only the tall back rest and the side arm rests of the throne (the part behind a seated person)"),
    ("throne_front", "throne", "only the front edge of the seat cushion and the front legs of the throne (the part in front of a seated person's legs)"),
    ("creation_forearm", "creation_arm", "only the arm without the hand"),
    ("creation_hand", "creation_arm", "only the hand with the extended index finger"),
    ("pot_leaves", "flower_pot", "only the green leaves (behind the pot)"),
    ("pot_body", "flower_pot", "only the terracotta pot with its rim and soil surface"),
    ("inkblob_head", "ink_blob_figure", "only the black ink-blob head with its face"),
    ("inkblob_body", "ink_blob_figure", "only the gray trapezoid body"),
    ("sedan_body", "car_sedan_side", "only the car body without the two wheels (wheel wells left empty)"),
    ("sedan_wheel", "car_sedan_side", "only the front wheel (tire and hub), nothing else"),
    ("car_body", "car_side", "only the car body without the two wheels (wheel wells left empty)"),
    ("car_wheel", "car_side", "only the front wheel (tire and hub), nothing else"),
    ("carfront_body", "car_front_driver", "only the car body below the windshield (hood, headlights, grille, bumper) and the empty interior behind it; remove the windshield glass and roof frame"),
    ("carfront_glass", "car_front_driver", "only the windshield glass with its surrounding roof frame and pillars"),
    ("shuttle_body", "space_shuttle", "only the shuttle, rocket and boosters, without any flames"),
    ("isochip_base", "iso_chip", "only the lavender base and middle layers, without the glowing core"),
    ("isochip_core", "iso_chip", "only the glowing cyan core layer"),
    ("zipper_body", "zipper_slider", "only the slider body without the pull tab"),
    ("zipper_tab", "zipper_slider", "only the pull tab"),
]


def ar_of(size_txt):
    import re
    m = re.findall(r"(\d+)\s*[×x]\s*(\d+)", size_txt or "")
    if m:
        w_, h_ = map(int, m[-1])
        r = w_ / h_
        return "3:2" if r > 1.35 else "2:3" if r < 0.74 else "1:1"
    return "1:1"


MAGENTA = {"globe", "money_pile", "tunnel_portal", "flower_pot", "pot_leaves", "pot_body", "apple_icon", "banknote_won", "banknote_500", "tree_round", "watering_can"}


SIZE = {"1:1": "1024x1024", "3:2": "1536x1024", "2:3": "1024x1536"}


def items():
    a = json.load(open(KIT / "audit.json"))
    out = []
    for p in a["props"]:
        if p["id"] in SKIP:
            continue
        tint = TINT if p["id"].startswith("icon_") or p["id"] in {"pictogram_person", "person_avatar_icon", "question_silhouette", "pc_icon", "bottle_silhouette_q"} else ""
        desc = f"{p['name']} — {p['desc']}"
        if p["id"].startswith("icon_"):
            what = p["id"][5:].replace("_", " ")   # 영문 id 로 지정('배'=과일 배 오해 방지)
            what = {"ship": "a cargo ship (boat) seen from the side", "bowl": "a food bowl"}.get(what, what)
            desc = f"icon of {what} — simple bold flat glyph icon (solid filled shapes, no outline), clear silhouette"
        out.append((p["id"], desc + tint, ar_of(p.get("size_px"))))
    for k, (d, ar) in EXTRA.items():
        out.append((k, d, ar))
    return out


def run(jobdir, lines):
    jobdir.mkdir(parents=True, exist_ok=True)
    with open(jobdir / "prompts.jsonl", "w") as f:
        for l in lines:
            f.write(json.dumps(l) + "\n")
    r = subprocess.run(["python3", str(RUNNER)], cwd=jobdir, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip().splitlines()[-1])


def full():
    lines = []
    for i, d, ar in items():
        if (OUT / "raw" / f"{i}.png").exists():
            continue
        bg = BG.replace("chroma green #00B140", "chroma magenta #FF00FF").replace("do not use green in the object unless stated", "do not use magenta or pink in the object") if i in MAGENTA else BG
        lines.append({"id": i, "ar": ar, "size": SIZE[ar], "prompt": STYLE_TXT + "Draw: " + d + bg, "output_path": str(OUT / "raw" / f"{i}.png"), "ref_images": STYLE})
    print(len(lines), "개 생성")
    run(OUT / "job_full", lines)


def parts():
    lines = []
    for pid, parent, keep in PARTS:
        src = OUT / "raw" / f"{parent}.png"
        if not src.exists() or (OUT / "raw" / f"{pid}.png").exists():
            continue
        im = Image.open(src)
        ar = "3:2" if im.width > im.height * 1.2 else "2:3" if im.height > im.width * 1.2 else "1:1"
        lines.append({"id": pid, "ar": ar, "size": SIZE[ar], "prompt": f"Edit the attached image: keep ONLY {keep}. Keep EXACTLY the same style, colors, position and scale as in the attached image; everything removed becomes flat solid chroma {'magenta #FF00FF' if pid in MAGENTA else 'green #00B140'}. Complete any hidden edges of the kept part naturally. No new objects.",
                      "output_path": str(OUT / "raw" / f"{pid}.png"), "ref_images": [str(src)]})
    print(len(lines), "개 부위")
    run(OUT / "job_parts", lines)


def key():
    PUB.mkdir(parents=True, exist_ok=True)
    part_ids = {p[0]: p[1] for p in PARTS}
    meta = {}
    for f in sorted((OUT / "raw").glob("*.png")):
        k = OUT / "keyed" / f.name
        k.parent.mkdir(exist_ok=True)
        subprocess.run(["python3", str(KEY), "--input", str(f), "--out", str(k), "--key-color", "#FF00FF" if f.stem in MAGENTA else "#00B140", "--soft-matte", "--despill", "--force"], capture_output=True)
        im = Image.open(k).convert("RGBA")
        bb = im.getbbox()
        if not bb:
            continue
        fam = part_ids.get(f.stem)
        if fam or f.stem in part_ids.values():
            # 부위 세트: 부모 캔버스 그대로(좌표 정렬), 대신 세트 공통 bbox 로 크롭
            pass
        meta[f.stem] = {"bbox": bb, "canvas": im.size, "family": fam or (f.stem if f.stem in part_ids.values() else None)}
    # 세트 공통 크롭
    fams = {}
    for i, m in meta.items():
        if m["family"]:
            fams.setdefault(m["family"], []).append(i)
    done = set()
    for fam, ids in fams.items():
        bbs = [meta[i]["bbox"] for i in ids]
        u = (min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs))
        for i in ids:
            im = Image.open(OUT / "keyed" / f"{i}.png").convert("RGBA")
            if im.size != Image.open(OUT / "keyed" / f"{fam}.png").size:
                im = im.resize(Image.open(OUT / "keyed" / f"{fam}.png").size, Image.LANCZOS)
            im.crop(u).save(PUB / f"{i}.png", optimize=True)
            meta[i]["crop"] = u
            meta[i]["size"] = [u[2] - u[0], u[3] - u[1]]
            done.add(i)
    for i, m in meta.items():
        if i in done:
            continue
        im = Image.open(OUT / "keyed" / f"{i}.png").convert("RGBA").crop(m["bbox"])
        im.save(PUB / f"{i}.png", optimize=True)
        m["size"] = list(im.size)
    json.dump(meta, open(PUB / "props.json", "w"), indent=1, ensure_ascii=False)
    print(len(meta), "개 → ", PUB)


def sheet():
    fs = sorted(PUB.glob("*.png"))
    n = len(fs); cols = 12; rows = (n + cols - 1) // cols
    s = Image.new("RGB", (cols * 160, rows * 180), (200, 210, 200))
    from PIL import ImageDraw
    d = ImageDraw.Draw(s)
    for k, f in enumerate(fs):
        im = Image.open(f).convert("RGBA"); im.thumbnail((150, 150))
        x, y = (k % cols) * 160, (k // cols) * 180
        bg = Image.new("RGBA", im.size, (200, 210, 200, 255)); bg.alpha_composite(im)
        s.paste(bg.convert("RGB"), (x + (160 - im.width) // 2, y + 5))
        d.text((x + 4, y + 160), f.stem[:24], fill=(0, 0, 0))
    s.save(OUT / "sheet.png")
    print(OUT / "sheet.png")


if __name__ == "__main__":
    {"full": full, "parts": parts, "key": key, "sheet": sheet}[sys.argv[1]]()
