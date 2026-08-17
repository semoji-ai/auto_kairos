"""타이레놀 영상 → 라이브러리 어휘(프리셋/폰트/컬러/디테일)로 motion.json 생성.
업로드된 파일 재사용(files/tdz4a7uge0w2, 48h 만료 시 재업로드). 결과를 파일로 직접 저장(파이프 잘림 방지)."""
import sys, time, json
from pathlib import Path
from google import genai
from google.genai import errors, types

LIB = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "motion"
presets = list(json.loads((LIB / "motion_presets.json").read_text())["presets"].keys())
fonts = list(json.loads((LIB / "font_map.json").read_text()).keys())
colors = list(json.loads((LIB / "color_tokens.json").read_text()).keys())

client = genai.Client()
f = client.files.get(name="files/tdz4a7uge0w2")
PROMPT = f"""이 70초 광고를 AE 컴프로 생성할 JSON으로만 출력(순수 JSON).
모션은 아래 프리셋명만 사용: {presets}
폰트는 역할명만: {fonts}
컬러는 토큰키 또는 hex: {colors}
디테일(옵션): shadow, glow, depth_blur, motion_blur

컷 스키마:
- searchbar: {{"type":"searchbar","text":..,"redText":..,"start":..,"dur":..,"bg":"토큰키/hex"}}
- button: {{"type":"button","text":..,"start":..,"dur":..,"bg":..}}
- cut: {{"type":"cut","start":..,"dur":..,"bg":..,"grain":true,
    "layers":[{{"type":"text|rrect|line|image|live","text":..,"asset":..,"color":"토큰키/hex","font":"역할명","size":..,"x":..,"y":..,"w":..,"h":..,"align":..,"round":..,"detail":["shadow"],
      "anim":[{{"preset":"프리셋명","t0":..,"dur":..,"params":{{"dir":"left"}}}}]}}]}}
출력: {{"cuts":[...35컷...]}} 순수 JSON만."""
cfg = types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=60000)
for attempt in range(6):
    for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]:
        try:
            resp = client.models.generate_content(model=m, contents=[f, PROMPT], config=cfg)
            data = json.loads(resp.text)
            out = Path(__file__).resolve().parents[1] / "cep/com.autokairos.pd/jsx/tylenol/motion.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"성공 {m}: {len(data['cuts'])}컷 → {out}")
            sys.exit(0)
        except json.JSONDecodeError as e: print(f"{m} JSON실패 {str(e)[:50]}")
        except errors.ServerError as e: print(f"{m} {str(e)[:60]}")
        except Exception as e: print(f"{m} {str(e)[:100]}")
    time.sleep(20 * (attempt + 1))
print("ERROR")
