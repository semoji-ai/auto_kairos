# 레퍼런스 색인

`motion/` 의 분석 노트가 가리키는 레퍼런스 영상과, 저장소에 넣지 않은 원본 미디어(영상·프레임·시트·자막 원문)의 위치입니다.
제3자 채널은 이름 대신 중립 id 로 부릅니다. 원본 영상 URL 은 출처 기록으로 남깁니다.

원본 미디어 루트: `$SEMOJI_NAS` = `/Volumes/jleavens/007_AI_Projects/semoji-motion_backup_20261007`
(2026-10-07 전체 백업, node_modules 제외 6,570개·7.22GB). NAS 쪽 폴더 이름은 백업 당시 그대로라 아래 표의 "NAS 폴더" 열로 찾습니다.
분석 노트·프롬프트 기록 속 `$SEMOJI_NAS/...` 경로도 이 루트 기준입니다.

## 중립 id ↔ NAS 폴더

| 저장소 id (motion/) | 성격 | NAS 폴더 | NAS에만 있는 것 |
|---|---|---|---|
| `ref` (도감 ref1) | 자체 채널(세모지) 중식편 | `ref/` | `ref.webm`, `frames/`, `sheets/`, `motion/`, 캡처 png, `ref.ko.vtt`, 원본 info.json |
| `ref2` | 자체 채널 마이크로소프트편 | `ref2/` | `ref.webm`(2.3GB), 원본 info.json |
| `ref3` | 자체 채널 리뉴얼 포맷(디아지오편) | `ref3/` | `ref.f616.mp4`, 캡처 png·jpg, 원본 info.json |
| `ref4` (ref4-apple·cocacola·hyundai·samsung) | 자체 채널 통합편 4종 | `ref4/` | `QMQ5HasZrxA.mp4`, 다운로드 로그 |
| `ref_explainer_editorial` | 제3자 설명형 편집 채널(동판화·지도·마스코트) | `ref_pirates/` | mp4 3편, `frames/`, `scenes/`(컷 감지 원자료 262MB), 원본 info.json |
| `ref_explainer_cartoon` | 제3자 카툰 설명 채널(고정 마스코트 캐스트) | `ref_mandoo/` | mp4 4개, `frames/`, `scenes/*.npy`, 원본 info.json |
| `ref_story/explainer_editorial` | 위 편집 채널 원고 분석 | `ref_story/pirates/` | 오디오, 자막(vtt), 전사(txt·words.json), 프레임 |
| `ref_story/explainer_cartoon` | 위 카툰 채널 원고 분석 | `ref_story/mandoo/` | 오디오 wav, srt, 자막, 전사, 프레임 |
| `ref_story/booktalk` | 제3자 북토크 채널 원고 분석 | `ref_story/njt/` | 자막 원문, 전사, 영상 조각, 프레임 |
| `ref_story/semoji` | 자체 채널 원고 분석 | `ref_story/semoji/` | 자막 원문·info.json, 프레임 (전사 txt 는 저장소에 있음) |
| `explainer_demo` | 편집 레퍼런스 스타일 1분 테스트 영상 프로젝트 | `pirates/` (코드는 `video/src/pirates/`, 미디어는 `video/public/pirates/`) | 생성 이미지 원본·키잉본, 지도 원자료(`countries-50m.json`, `land-*.json`), 로그 |
| `video/public` | Remotion 정적 에셋 | `video/public/` | 폰트·이미지·오디오·키트 PNG·레이어 SVG 전체(197MB) — `bash motion/video/scripts/fetch_public.sh` 로 받음 |
| `dogam` 미리보기 | 기법 도감 미리보기 mp4·jpg | `dogam/previews/` | 652개(92MB) — `motion/dogam/README.md` "미리보기 파일 위치" |
| (AE 실험) | AE 파일럿 생성기·aep | `ae/` | `adobe/` 로 대체된 실험. 지도 배경 `ae/assets/map_bg.png` 는 `adobe/data/semoji-motion/` 에 번들 |
| (원화 에셋) | 생성 원본·마스크·키트 원본 | `assets/` | PNG 원본 677개(563MB). 생성 코드·프롬프트 기록만 `motion/assets/` 에 있음 |

## 도감(techniques.json) sources 의 ref 값

| ref | 영상 |
|---|---|
| ref1 | https://youtu.be/NZsB8vnv1FU — 중식 4대문파편 |
| ref2 | https://youtu.be/kAFIom5Xrrw — 마이크로소프트 통합편 |
| ref3 | https://youtu.be/Lh0drBozqck — 디아지오 증류소편(리뉴얼 포맷) |
| ref4-apple | https://youtu.be/-KlzkB3b46c — 애플의 역사 통합편 |
| ref4-cocacola | https://youtu.be/QMQ5HasZrxA — 코카콜라의 역사 통합편 |
| ref4-hyundai | https://youtu.be/iB5cA-rKGRA — 현대의 역사 통합편 |
| ref4-samsung | https://youtu.be/0s6A0hkg11U — 삼성의 역사 통합편 |
| ref_explainer_editorial | https://youtu.be/y7OMrkjkFPg · https://youtu.be/5JTEU99XKb0 · https://youtu.be/J-PrL3eM33U |

## 영상 목록

### `ref_explainer_editorial` — NAS `$SEMOJI_NAS/ref_pirates/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| 5JTEU99XKb0 | 💀 2차세계대전 🇺🇸미국편 9화 / 💀 인류 역사상 최대의 해전… 레이테만 해전!! | 17:23 | 2026-08-14 | https://youtu.be/5JTEU99XKb0 |
| J-PrL3eM33U | 💀 호칭 인플레이션?? 왜 일어나는 걸까 / 💀 한국어 화자들이 피곤한 이유 | 16:37 | 2026-09-01 | https://youtu.be/J-PrL3eM33U |
| y7OMrkjkFPg | 💀 쓰레기 땅에서도 재배 가능한 개사기 작물 ㄷㄷ  / 💀 감자가 치트키인 이유 | 15:14 | 2026-01-11 | https://youtu.be/y7OMrkjkFPg |

### `ref_explainer_cartoon` — NAS `$SEMOJI_NAS/ref_mandoo/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| OR-55EGPOLY | 미국 급식은 어쩌다 이 지경이 됐을까?｜"김치 먹어라" 권고한 트럼프 정부 | 7:38 | 2026-09-18 | https://youtu.be/OR-55EGPOLY |
| jb0NxoZHuu8 | 조선시대 사또는 월급의 노예였다?｜사또의 피곤한 하루 | 6:49 | 2025-03-06 | https://youtu.be/jb0NxoZHuu8 |
| mBhCwJK1xR4 | 역대급 기괴하게 진화한 생물들｜곤충처럼 짝짓기하는 괴상한 포유류 | 6:20 | 2026-09-10 | https://youtu.be/mBhCwJK1xR4 |

### `ref_story/explainer_editorial` — NAS `$SEMOJI_NAS/ref_story/pirates/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| 3rjhFUvZRas | 💀 산지 70%의 나라… 여기서 어떻게 살아남았을까? / 💀 한반도 지형 눈물의 리뷰 | 15:09 | 2025-06-26 | https://youtu.be/3rjhFUvZRas |
| 40ssEFbJrVU | 💀 서양인들은 왜 집에서 신발을 신을까? / 💀 입식vs좌식 서로 달라진 이유 | 12:45 | 2025-11-21 | https://youtu.be/40ssEFbJrVU |
| 5JTEU99XKb0 | 💀 2차세계대전 🇺🇸미국편 9화 / 💀 인류 역사상 최대의 해전… 레이테만 해전!! | 17:23 | 2026-08-14 | https://youtu.be/5JTEU99XKb0 |
| J-PrL3eM33U | 💀 호칭 인플레이션?? 왜 일어나는 걸까 / 💀 한국어 화자들이 피곤한 이유 | 16:37 | 2026-09-01 | https://youtu.be/J-PrL3eM33U |
| y7OMrkjkFPg | 💀 쓰레기 땅에서도 재배 가능한 개사기 작물 ㄷㄷ  / 💀 감자가 치트키인 이유 | 15:14 | 2026-01-11 | https://youtu.be/y7OMrkjkFPg |

### `ref_story/explainer_cartoon` — NAS `$SEMOJI_NAS/ref_story/mandoo/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| -tksjDqRp0k | 사형수들은 감옥에서 어떻게 살고 있을까?｜무기징역vs사형수, 교도소 생활 비교 | 8:06 | 2025-08-14 | https://youtu.be/-tksjDqRp0k |
| NBcqXNuQt6E | 왜 몸에 좋은 음식은 유독 맛없을까?｜우리가 몸에 안 좋은 것만 찾는 과학적인 이유 | 7:33 | 2026-02-19 | https://youtu.be/NBcqXNuQt6E |
| OR-55EGPOLY | 미국 급식은 어쩌다 이 지경이 됐을까?｜"김치 먹어라" 권고한 트럼프 정부 | 7:38 | 2026-09-18 | https://youtu.be/OR-55EGPOLY |
| jb0NxoZHuu8 | 조선시대 사또는 월급의 노예였다?｜사또의 피곤한 하루 | 6:49 | 2025-03-06 | https://youtu.be/jb0NxoZHuu8 |
| mBhCwJK1xR4 | 역대급 기괴하게 진화한 생물들｜곤충처럼 짝짓기하는 괴상한 포유류 | 6:20 | 2026-09-10 | https://youtu.be/mBhCwJK1xR4 |

### `ref_story/booktalk` — NAS `$SEMOJI_NAS/ref_story/njt/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| 0utk3wm8cJU | 뇌 빼고 봐도 되는 [구운몽] ｜ 국문학 끝판왕 | 37:28 | 2026-08-01 | https://youtu.be/0utk3wm8cJU |
| 34g2xZ0DpIE | 21세기에 노예 만드는 법 (실용 100%) | 13:28 | 2026-06-13 | https://youtu.be/34g2xZ0DpIE |
| IQ7UH43tDH0 | 영화 [오디세이] 에 오디세우스는 없습니다. | 15:35 | 2026-08-13 | https://youtu.be/IQ7UH43tDH0 |
| RZBnwqjK_CY | 한국사에 감춰진 부처님 : 파계승 원효 | 25:54 | 2026-02-14 | https://youtu.be/RZBnwqjK_CY |
| TmJGenL0z-o | 어린왕자에 숨겨진 충격적인 진실 | 28:15 | 2025-04-05 | https://youtu.be/TmJGenL0z-o |
| a4D5wX01vV0 | 우울 극복하는 치트키 (+뇌 과학) | 7:24 | 2026-06-19 | https://youtu.be/a4D5wX01vV0 |

### `ref_story/semoji` — NAS `$SEMOJI_NAS/ref_story/semoji/`

| 영상 id | 제목 | 길이 | 업로드 | URL |
|---|---|---|---|---|
| 0s6A0hkg11U | 당신이 몰랐던 삼성(Samsung)의 역사 통합편[브랜드 스토리] | 95:36 | 2020-09-29 | https://youtu.be/0s6A0hkg11U |
| Lh0drBozqck | 당신이 몰랐던 디아지오 네개의 증류소, 클라이넬리쉬, 더프타운, 탈리스커, 라가불린의 역사 #싱글톤 #클라이넬리쉬 #라가불린 #탈리스커 #위스키 #위스키추천 #싱글몰트 | 17:04 | 2026-08-31 | https://youtu.be/Lh0drBozqck |
| NZsB8vnv1FU | 아서원(유방녕), 홍보석(여경래, 박은영), 호화대반점(이연복, 왕육성, 정지선, 황진선), 팔선(후덕죽) 출신 우리나라 대표 중식 요리사들 [브랜드 스토리] | 14:28 | 2024-10-11 | https://youtu.be/NZsB8vnv1FU |
| QMQ5HasZrxA | 당신이 몰랐던 코카콜라(CocaCola)의 역사 통합편 [브랜드 스토리] | 32:38 | 2021-09-20 | https://youtu.be/QMQ5HasZrxA |
| TwN-w76uzzo | 면비디아로 불리는 그 라면! 당신이 몰랐던 불닭볶음면의 역사  [브랜드 스토리] | 8:00 | 2025-09-17 | https://youtu.be/TwN-w76uzzo |
| dJntbYXPgbU | 왕과 사는 남자, 최강 빌런, 당신이 몰랐던 한명회의 인생 [인물백과사전] | 12:21 | 2026-02-21 | https://youtu.be/dJntbYXPgbU |
| jsK4Ez9eky0 | 위기의 신세계, 이명희 복귀의 의미는? 신세계 1편 [브랜드 스토리] | 14:26 | 2025-01-24 | https://youtu.be/jsK4Ez9eky0 |
| mkXBgbcehXM | 롯데리아가 초심을 잃을 줄이야... 당신이 몰랐던 롯데리아(LOTTERIA)의 역사 [브랜드 스토리] | 14:09 | 2025-03-20 | https://youtu.be/mkXBgbcehXM |
