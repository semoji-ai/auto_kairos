"""도감 343개 기법의 AE 이식 1차 분류 — native / partial / render(렌더 대체) / 제외.

    python3 adobe/scripts/dogam_classify.py   → adobe/docs/dogam_ae_classification.md (전체 표) + 요약 출력

분류 기준(컴포넌트 단위 규칙, 사람이 고친 판단을 여기 모읍니다)
  native  : 트랜스폼·불투명·마스크·도형·텍스트·기본 효과(블러·그림자·램프)와 캐스트 PNG 로 키프레임 재현 가능
  partial : 핵심 모션은 키프레임으로 되지만 한 부분이 근사(노이즈·입자·필터·지도 프리렌더·자유 변형)
  render  : WebGL/3D·절차 셰이더·유체처럼 AE 키프레임으로 옮기면 손이 더 가는 것 → Remotion 에서 알파 영상/PNG 시퀀스로 뽑아 레이어로 얹기
  제외    : 도감 status 금지(방사형 광선 계열) · 분석만(구현 없음)
"""
from __future__ import annotations

import collections
import json
import os
from pathlib import Path

ADOBE = Path(__file__).resolve().parents[1]
SM = Path(os.environ.get("SEMOJI_MOTION_DIR") or ADOBE.parent / "motion").expanduser()   # 구 ~/Projects/semoji-motion
REG = ADOBE / "cep/com.autokairos.pd/jsx/dogam/registry.json"
OUT = ADOBE / "docs" / "dogam_ae_classification.md"

RENDER = {
    "GlobeSpinScatter": "3D 지구본 회전(WebGL)", "DiscPie3D": "3D 원반 파이", "SpiralTunnelBg": "나선 터널 셰이더",
    "TwirlLiquid": "소용돌이 액체 변형", "ElectricVortexSpawn": "전기 소용돌이 절차 효과", "SpectralZoomThrough": "스펙트럼 줌 셰이더",
    "SpiralSuck": "나선 흡입 왜곡", "FireBgLoop": "불꽃 배경 루프", "FireTransition": "불꽃 전환", "FlameSprite": "불꽃 스프라이트",
    "PhotoFlameEyes": "사진 눈 불꽃", "ArchiveNewsreel": "뉴스릴 필름 질감 합성", "MapLecturerCountryFill": "지도 국가 채움(벡터 타일)",
    "XraySilhouette": "X선 실루엣 셰이딩", "FloodRise": "물 차오름 유체", "SaucePour": "소스 붓기 유체", "InkBlobReveal": "잉크 번짐 마스크",
    "GlassCrack": "유리 깨짐 파편", "OctopusMonster": "촉수 절차 애니메이션",
}
PARTIAL = {
    "MapRoute": "지도 배경 프리렌더", "MapPin": "지도 배경 프리렌더", "MapSpreadPullback": "지도 프리렌더 + 증식", "MapStatOverlay": "지도 프리렌더",
    "FlagMapStatLink": "지도 프리렌더", "Grain": "필름 그레인 → Noise 효과 근사", "GlitchOverlay": "글리치 → 효과 근사", "CRTSwitch": "CRT 주사선 근사",
    "SlatMosaic": "슬랫 모자이크 → 도형 반복", "PixelateAvatar": "픽셀화 → Mosaic 효과", "FaceBlur": "얼굴 블러(추적 없음)",
    "Confetti": "입자 40개 키 굽기(무거움)", "Steam": "김 루프 → 도형 키 굽기", "SmokeSwap": "연기 퍼프", "Teleport": "연기 퍼프",
    "SnowfallLoop": "입자 루프", "MoneyRain": "입자 루프", "FlowerParticles": "입자 루프", "BokehDrift": "보케 입자", "CrowdBokeh": "보케 입자",
    "MatrixRain": "문자 비 절차", "CodeScroll": "코드 텍스트 스크롤(텍스트 레이어 가능)", "WordWallpaper": "반복 텍스트 벽지", "RepeatObjectWallpaper": "반복 배치",
    "FlagWave": "깃발 물결 → Wave Warp 근사", "TechAura": "글로우 절차", "TechCircuitGlow": "회로 펄스 다수", "GradientLightWash": "그라디언트 빛 → 램프 근사",
    "SkyGradientAscent": "하늘 그라디언트 → 램프", "ColorDrain": "채도 빠짐 → Tint 키", "GrayscaleBeat": "흑백 → Tint 키", "InstantMono": "흑백 → Tint 키",
    "EraPalette": "시대 색보정 → 효과 근사", "ArchivalAdOnPaper": "종이 질감 합성", "BlurFillPhoto": "블러 복제 배경", "RackDefocus": "디포커스 → 블러 키",
    "FocusPull": "초점 이동 → 블러 키", "LightningFlash": "번개 절차 도형", "EnergySlash": "에너지 슬래시 글로우", "OrangeFlare": "플레어 → 그라디언트 근사",
    "IdeaWarmBloom": "블룸 글로우", "ConcentricDarkPulse": "동심원 펄스(도형 다수)", "RippleRings": "파문 링(도형 다수)", "RippleRingsBg": "파문 링 배경",
    "GlowCloudText": "글로우 구름 글자", "NeonTiles": "네온 글로우", "CloudBubbles": "구름 풍선 보일링", "LayeredCover": "까딱·깜빡임 native, 패럴랙스 drift 미이식",
    "FlickerLeak": "빛샘 radial-gradient → 램프·블렌드 근사", "YellowBurst": "번짐 radial-gradient → 램프 근사", "PinkColorWash": "컬러 워시 블렌드",
    "WaveBg": "물결 문양 배경(패턴)", "CloudDrift": "구름 루프", "SpotlightCone": "빛 원뿔 그라디언트", "Spotlight": "딤 + 둥근 구멍(마스크) 근사",
    "LegacyFormat": "구 포맷 합성(여러 기법 묶음)", "Main": "본편 합성(여러 기법 묶음)", "IntroMontage": "몽타주 합성", "OutroRecap": "리캡 합성",
    "SignalWaveDiagram": "파형 절차 패스", "CandlestickGrowth": "캔들 다수(데이터 많음)", "PictogramCrowdMarquee": "픽토그램 다수 마키",
    "Whiteboard": "손글씨 드로잉 → Trim Paths 근사", "BrushHeadline": "붓 마스크 → Trim 근사", "BrushMaskQuote": "붓 마스크 → Trim 근사",
    "HandDrawnCircle": "손그림 원 → Trim 근사(떨림)", "DottedPathDraw": "점선 드로우", "IrisFeather": "페더 아이리스 마스크", "ArcWipeIris": "호 와이프 마스크",
    "TheaterCurtain": "커튼 주름 → 도형 근사", "MagazineFlip": "책장 넘김 3D", "NewspaperPullout": "신문 3D 회전", "Signboard": "간판 Y축 카드 플립(3D 레이어)",
    "FlipTurn": "Y축 뒤집기(3D 레이어)", "CardSwipeMontage": "카드 3D 스와이프", "TcgCardMarquee": "카드 3D 마키", "Marionette": "줄 인형 물리",
    "RopeSwing": "진자 물리 → 키 굽기", "BurdenBallChain": "사슬 물리", "BlobHead": "말랑 변형", "HopArc": "포물선 → 키 굽기", "TreadmillWalk": "걷기 사이클(리그)",
    "WalkPath": "걷기 사이클(리그)", "CrashImpact": "충돌 파편", "ThoughtMaterialize": "생각 구름 물질화", "LogoFaceMask": "얼굴 로고 마스크",
    "HangingIconDrop": "매달린 흔들림 물리", "ClipboardSwingDrop": "진자 흔들림", "BoardingPassDrop": "종이 낙하 흔들림",
}
EXCLUDE_STATUS = {"금지": "금지 기법(방사형 광선 계열)", "분석만": "Remotion 구현 없음(분석만)"}


def main() -> None:
    cat = json.loads((SM / "dogam/techniques.json").read_text(encoding="utf-8"))
    ae = {}
    if REG.exists():
        ae = {t["id"]: t for t in json.loads(REG.read_text(encoding="utf-8"))["techniques"]}
    rows, cnt, by_cat = [], collections.Counter(), collections.defaultdict(collections.Counter)
    for e in cat:
        comp = e.get("component") or ""
        if e["status"] in EXCLUDE_STATUS:
            cls, why = "제외", EXCLUDE_STATUS[e["status"]]
        elif comp in RENDER:
            cls, why = "render", RENDER[comp]
        elif comp in PARTIAL:
            cls, why = "partial", PARTIAL[comp]
        else:
            cls, why = "native", "트랜스폼·마스크·도형·텍스트 키프레임"
        if e["id"] in ae:
            done = f"✅ AE 이식({ae[e['id']].get('support', 'native')})"
            if ae[e["id"]].get("support") == "partial":
                cls = "partial"
        else:
            done = ""
        cnt[cls] += 1
        by_cat[e["category"]][cls] += 1
        rows.append((e["category"], e["id"], e["name"], comp, cls, why, done, e.get("preview") or ""))
    order = ["native", "partial", "render", "제외"]
    lines = ["# 기법 도감 → AE 이식 1차 분류 (전체 343)", "",
             "> `scripts/dogam_classify.py` 가 만든 표입니다. 규칙은 스크립트의 RENDER·PARTIAL 표 — 판단을 고칠 때는 거기를 고치고 다시 돌립니다.", "",
             "## 요약", "", "| 분류 | " + " | ".join(order) + " | 합계 |", "|---|" + "---:|" * (len(order) + 1)]
    for c in sorted(by_cat):
        lines.append(f"| {c} | " + " | ".join(str(by_cat[c][o]) for o in order) + f" | {sum(by_cat[c].values())} |")
    lines.append("| **합계** | " + " | ".join(f"**{cnt[o]}**" for o in order) + f" | **{sum(cnt.values())}** |")
    lines += ["", "## 전체 표", "", "| 분류 | id | 이름 | 컴포넌트 | 1차 분류 | 근거 | 상태 | 미리보기 |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r[0], order.index(r[4]), r[1])):
        lines.append("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("1차 분류:", dict(cnt))
    for c in sorted(by_cat):
        print(f"  {c}: " + ", ".join(f"{o} {by_cat[c][o]}" for o in order if by_cat[c][o]))
    print("→", OUT)


if __name__ == "__main__":
    main()
