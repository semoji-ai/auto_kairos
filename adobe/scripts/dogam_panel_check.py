"""기법 도감 탭 스모크 검사 — 패널(index.html)을 Playwright 로 열고 CEP 다리를 가짜로 끼워
목록·검색·폼·[적용] 호출문까지 확인합니다(AE 없이). 실제 AE 클릭 확인은 사용자와 따로 합니다.

    python3 adobe/scripts/dogam_panel_check.py [스크린샷.png]
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
ext = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
out = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "tmp" / "dogam_panel.png")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--allow-file-access-from-files"])
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.add_init_script("""window.__adobe_cep__ = { getSystemPath: function(){ return "file:///fake/ext"; },
      evalScript: function(s, cb){ window.__LASTJSX = s; setTimeout(function(){ cb('{"ok":true,"msg":"(테스트) 도장 슬램 — 레이어 1개","names":["00 도장 폐업","00 도장 잔상"]}'); }, 10); } };""")
    pg.goto(ext.joinpath("index.html").as_uri())
    pg.wait_for_timeout(800)
    pg.evaluate("openDogamStandalone()")
    pg.wait_for_timeout(500)
    n = pg.evaluate("document.querySelectorAll('.dg-card').length")
    pg.fill("#dgSearch", "도장")
    pg.wait_for_timeout(200)
    n2 = pg.evaluate("document.querySelectorAll('.dg-card').length")
    pg.fill("#dgSearch", "")
    pg.click(".dg-card[data-id=stamp-slam]")
    pg.wait_for_timeout(300)
    pg.fill(".dg-row[data-key=size] input[type=number]", "150")
    pg.dispatch_event(".dg-row[data-key=size] input[type=number]", "input")
    pg.click("#dgApply")
    pg.wait_for_timeout(300)
    call = pg.evaluate("window.__LASTJSX.slice(window.__LASTJSX.lastIndexOf('AKD.assetsRoot'))")
    st = pg.inner_text("#dgStatus")
    rng = pg.evaluate("document.querySelector('.dg-row[data-key=size] input[type=range]').value")
    pg.screenshot(path=out)
    print("cards", n, "search도장", n2, "range-sync", rng)
    print("status", st)
    print("call", call[:400])
    print("errors", errs[:8])
    b.close()
