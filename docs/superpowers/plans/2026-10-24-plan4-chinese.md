# 계획 4: 코스트코(B209) 중국어 간체판 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 영어판과 같은 파이프라인으로 B209 중국어 간체판(비리비리·샤오홍수용 16:9 전체판)을 만든다. 지금까지 영어를 전제로 짠 부분(자막 나누기, 그림 문구 번역 규칙, 폰트, 공용 에셋 문구)을 언어 설정으로 일반화해, 일본어 등 다음 언어도 설정 파일만 추가하면 되게 한다.

**Architecture:** 언어별 차이는 `profiles/<lang>.json`(TTS·자막·폰트 역할·에셋 문구)과 `glossary/<lang>.json`(고유명사)에 둔다. 코드는 프로필을 읽는다: 띄어쓰기 없는 언어는 글자 단위 자막 분할, 그림 문구 번역 규칙은 언어별, 래스터 텍스트 폰트는 역할(label/title/hand/brush)로 고른다. 판 PNG·형광펜 검출·타임 워프·오디오 믹서는 언어 무관이라 그대로 쓴다.

**Tech Stack:** 기존과 같음(Python 3, AE 2026 ExtendScript+aerender, ElevenLabs eleven_v4, claude -p, ffmpeg).

**Spec:** `docs/superpowers/specs/2026-10-19-semoji-global-localization-design.md` + 사용자 결정(2026-10-24): 가로 전체판 하나, 채널명 Semoji 그대로(로고 SE/MO/JI 유지, 버튼만 중국어), 성조기·지도 그대로, 중국어 폰트는 상업 무료 안에서 용도별 추천(자막은 思源黑体 Bold 지정).

## Global Constraints
- 폰트(모두 상업 무료, 라이선스 사본 `docs/fonts/zh/`):
  - 자막 `SourceHanSansCN-Bold`(思源黑体, OFL)
  - 라벨·이름표·연도 배지·출처 `SourceHanSansCN-Heavy`
  - 기울어진 강조 띠·챕터 제목 `SmileySans-Oblique`(得意黑, OFL)
  - 말풍선 손글씨 `ZCOOLKuaiLe-Regular`(站酷快乐体, OFL)
  - 흰 외곽선 붓글씨 외침 `ZhiMangXing-Regular`(钟齐志莽行书, OFL)
  - 맥 내장 중국어 폰트(PingFang·HanziPen 등)와 方正·汉仪·字魂 계열은 쓰지 않는다.
- TTS: 세모지 보이스 `W7FnAxJNpD5WGjrF5GLp`, `eleven_v4`, language_code `zh`(시험: 开市客·연도 정확).
- 간체만(번체 금지). 브랜드명은 중국 본토 표기(开市客 Costco, 沃尔玛, 易买得, 乐天玛特 등 — glossary).
- 화면 한글 0자(실제 브랜드 간판 예외), 한국어 원고 규칙(가타카나·한자 금지)은 중국어판 결과물에는 해당 없음.
- 기존 영어판 산출물·테스트를 깨지 않는다(영어 프로필 동작 동일).

## Review Focus
1. 중국어 자막 분할 — 띄어쓰기가 없어 단어 단위 분할이 통째로 한 큐가 되거나 글자 중간에서 끊길 수 있음. 문장부호 우선, 길이 상한, 짧은 큐 병합 테스트.
2. 래스터 텍스트 폰트에 없는 글자 — 손글씨·붓글씨 폰트는 GB2312 밖 글자가 빠짐. 적용 전 글리프 검사가 역할별 폰트 파일로 돌아야 함.
3. 영어 전제 하드코딩(ASCII 규칙, 'ha', 'Subscribe') — 언어 프로필로 옮긴 뒤 영어 동작이 그대로인지.
4. TTS 길이 — 중국어는 글자당 시간이 길어 글자 예산(cps)이 다름. 예산이 틀리면 워프 비율이 극단으로.
5. 형광펜 구절 매칭 — 중국어 줄에서 같은 뜻 구절을 찾아 폭을 재는 경로가 띄어쓰기 없이도 맞는지.

---

### Task 1: 언어 일반화 — 자막 분할(CJK)·번역 규칙·폰트 역할
**Files:** `sg/subs.py`, `sg/translate.py`, `scripts/raster_translate.py`, `scripts/raster_apply.py`, `scripts/subtitles.py`, `scripts/ae/subtitles.jsx`, `scripts/build_global_assets.py`, `profiles/en.json`, tests
- `split_cues(..., cjk=False)`: cjk면 글자 단위 토큰, 끊는 우선순위 `。！？` > `，、；：` > 길이 상한(max_chars), 짧은 큐 병합은 기존 규칙, 결합 시 공백 없음. `retext`도 cjk면 글자 비율로 나눔.
  - 테스트: 문장부호에서 끊김, 상한 넘는 긴 문장이 둘 이상으로, 결합에 공백 없음, 영어 기존 테스트 그대로 통과.
- `build_prompt(kind="raster")`: 언어별 규칙 — en은 기존(ASCII), zh는 "简体中文, 不用繁体, 数字用阿拉伯数字, 不用表情符号"과 `[[ ]]` 강조 규칙 동일. 테스트: zh 프롬프트에 ASCII 규칙이 없고 간체 규칙이 있음.
- 폰트 역할: `profiles/<lang>.json`의 `"raster_fonts": {"label":{ps,file}, "title":…, "hand":…, "brush":…}`. 선택 규칙 `font_role(font, stroke, angle)`: hand+외곽선→brush, hand→hand, gothic+|각도|>3°→title, gothic→label. en 프로필은 label=title=OTSBAggroB, hand=brush=Noteworthy-Bold로 기존과 동일. 테스트: 역할 4가지.
- `raster_apply`·`raster_translate`의 글리프 검사는 역할별 폰트 파일로.
- 자막 폰트: `subs.font`가 있으면 subtitles.jsx가 큐 텍스트 레이어 폰트를 바꿈(없으면 템플릿 그대로 — en 동작 유지).
- 공용 에셋 문구는 프로필 `"assets_text"`(en: ha/Subscribe/Like/Semoji; zh: 哈/关注/点赞/Semoji)와 폰트(`assets_fonts`)에서.
- [ ] 각 테스트 RED→GREEN, 전체 스위트 통과, en 프로필 dry-run(`raster_apply.py --dry`) 결과가 이전과 같음(텍스트 레이어 213). 커밋.

### Task 2: 중국어 프로필·용어집
**Files:** `profiles/zh.json`, `glossary/zh.json`
- cps: 영어판 TTS 실측처럼 중국어 샘플 몇 문장을 v4로 만들어 글자/초 측정 → 그 값(예상 4~5). subs: cjk true, max_chars 18, min_dur 0.8, font SourceHanSansCN-Bold. fonts(AE 문자열용 font_map): 원래 한국어 폰트 → 역할 폰트(제목류는 SmileySans, 그 외 SourceHanSansCN-Heavy/Bold).
- glossary: 코스트코 开市客(Costco), 이마트 易买得(E-Mart), 홈플러스 Homeplus, 롯데마트 乐天玛特, 월마트 沃尔玛, K마트 凯马特(Kmart), 까르푸 家乐福, 페드마트 FedMart, 프라이스클럽 Price Club(普来斯会员店), 짐 시네갈 吉姆·辛内加尔, 솔 프라이스 索尔·普莱斯, 샘 월튼 山姆·沃尔顿, 후고 만 雨果·曼, 제프 브로트만 杰夫·布罗特曼, 커클랜드 科克兰(Kirkland Signature), 양재점 良才店, 신세계 新世界, 트레이더스 Traders, 출처 来源, 챕터 第N章, 억/조 → 亿/万亿 韩元(자연스러우면 美元 병기).
- [ ] cps 측정 기록, 커밋.

### Task 3: 내레이션 번역·TTS·발음 검수
- `translate.py episodes/B209 zh` → `tts.py episodes/B209 zh --rewrite-loop` → `asr_check.py episodes/B209 zh`.
- 숫자·연도 발음 문제는 l10n의 `tts` 필드(한자 숫자)로.
- [ ] Expected: 172구간 번역, TTS 길이 0.75~1.35배 안(재작성 최대 2회), 발음 이상 0(또는 tts 필드로 해결). 커밋(l10n).

### Task 4: 화면 문자열·그림 문구 번역 + 중국어 공용 에셋
- `translate.py`(strings), `raster_translate.py episodes/B209 zh`(판·OCR·manual은 언어 무관이라 재사용; manual의 text 덮어쓰기는 en 전용이므로 언어별 키 `text_<lang>` 지원).
- 공용 에셋: `build_global_assets.py zh emotion|title|outro` → `assets/global/zh/`(킥킥 哈, 타이틀 SE/MO/JI + 关注/点赞, 아웃트로 Semoji), `assets/global/swap_zh.json`.
- [ ] Expected: 번역 누락 0, 글리프 누락 0, 에셋 3개 원본과 크기·길이 같음, 비교 시트 확인. 커밋.

### Task 5: 재빌드 + 검수
- `scripts/rebuild_lang.sh episodes/B209 zh` → `render/zh/B209_ZH_preview.mp4`.
- 검수: 한글 검사(0.5초), 기술 검사(형식·검은 화면·무음·음량), 10초 간격 화면 시트 전부 보기(자막 줄바꿈·폰트·말풍선 넘침), 중국어 음성 인식으로 자막 싱크.
- [ ] Expected: 화면 한글 0(브랜드 예외), 문제 시트 없음, -19±1 LUFS. 런북에 중국어 절차 추가. 최종 리뷰.
