# 브랜드백과사전 엔비디아 4편 — 사실 원장 (2023-06 ~ 2026-11)

- 작성일: 2026-11-04 (조사 기준일)
- 용도: 한국판 4편 원고 → 중국 본토용 중국어판(英伟达 4) 번역의 사실 기준
- 원칙: 수치는 출처 표기 그대로(달러, 엔비디아 회계연도 기준). 추측 수치 없음. 확인 못 한 것은 「미확인」.

## 0. 표기 규칙

**회계연도 주의**: 엔비디아 회계연도(FY)는 1월 말에 끝난다. FY2024 = 2023-02 ~ 2024-01, FY2025 = 2024-02 ~ 2025-01, FY2026 = 2025-02 ~ 2026-01, FY2027 = 2026-02 ~ 2027-01. 원고에서 "2분기"라고 쓰면 달력과 헷갈리니 "2026년 5~7월 분기"처럼 쓰는 것을 권장.

**주가 주의**: 2024-06-10부터 10대1 분할 가격으로 거래. 1~3편과 2024-06 이전 기사의 주가(예: 446.64달러, 목표주가 750달러, 1,224.40달러)는 분할 전 가격이라 지금 가격과 바로 비교하면 안 된다(10으로 나누면 분할 후 기준).

**확인 수준**
- `확인` — 엔비디아 IR·보도자료·SEC 공시, 또는 서로 다른 주요 매체 2곳 이상이 같은 내용을 보도
- `단일출처` — 매체 한 곳의 보도, 또는 익명 소식통 보도 → 원고에서는 "~라고 보도됐다"(중국어판 `据报道`)로 쓴다
- `미확인` — 출처를 찾지 못했거나 서로 엇갈림 → 원고에 쓰지 말 것

**판 표시**
- `공용` — 한국판·중국판 모두 사용
- `한국판만` — 한국판에만 사용(중국판에서 빼도 흐름이 끊기지 않음)
- `중국판만` — 중국판에 넣을 중국 시장 소재
- `중국판 피할 것` — 중국 본토 심의·정서상 위험. 이유와 대체 서술을 비고에 적음

**중국어 고유명사**: 엔비디아=英伟达(NVIDIA), 젠슨 황=黄仁勋, 쿠다=CUDA, 블랙웰=Blackwell, 루빈=Rubin(베라 루빈 플랫폼은 중국 매체에서도 `Vera Rubin` 영문 그대로 쓰는 경우가 많음), 딥시크=深度求索(DeepSeek), 화웨이 어센드=华为昇腾, 바이트댄스=字节跳动, 알리바바=阿里巴巴, 텐센트=腾讯, 중국 국가시장감독관리총국=国家市场监督管理总局, 중국 국가인터넷정보판공실=国家互联网信息办公室(网信办).

---

## 1. 1~3편이 다룬 범위 (요약)

| 편 | 다룬 내용 | 끝맺음 |
|---|---|---|
| 1편 (B145) | 젠슨 황 출생(1963, 대만 타이난)·미국 이민·AMD/LSI Logic 경력, PC 그래픽 역사(애플·IBM·VGA·윈도 3.1), 1993-04-05 창업(4만 달러, invidia), 인텔 NSP 계획과 경쟁 의식 | 올인원 멀티미디어 칩 개발 착수 |
| 2편 (B146) | NV1 실패·NV2 중단·파산 위기, RIVA 128·TNT·TNT2, 3dfx 파산(2000), 1999 지포스 256 "세계 최초 GPU", 지포스 2~30 시리즈 연표(쿠다 2006 첫 등장 언급) | "어떻게 미국 반도체 1위가 됐는지 다음 편에서" |
| 3편 (B147) | ATI 라데온 9700 경쟁·실적 부진, 2008 노트북 칩 결함·금융위기·연봉 1달러, 암호화폐 붐과 "숙취", 딥러닝(알렉스넷 2012, 테슬라 K40 2013, V100·텐서 코어 2017, 래피즈 2018), 챗GPT 열풍 | 2023-05-30 장중 시총 1조 달러 → 6/13 종가 1조, "AI 반도체 97%", "2023년 주가 200% 상승" |

**4편의 출발점**: 2023년 중반, 챗GPT 이후 H100 품귀와 데이터센터 매출 폭증부터. 3편 뒤쪽 메모에 남아 있는 GH200(2023-08 시그래프 발표) 소재는 원고 본문에는 들어가지 않았으므로 4편 도입에서 쓸 수 있다.

---

## 2. 분기 실적 추이 (엔비디아 공식 발표 기준)

> 모두 엔비디아 보도자료(nvidianews.nvidia.com) 원문 수치. 데이터센터 비중(%)은 표 아래 계산식으로 원고 작성자가 직접 낸 값(반올림)이며, 엔비디아가 발표한 값이 아님(단, FY27 2분기 92.5%는 보도 수치).

| 발표일 | 분기(끝난 날) | 전체 매출 | 데이터센터 매출 | 전년 대비 | DC 비중(계산) | 출처 |
|---|---|---|---|---|---|---|
| 2023-08-23 | FY24 2Q (2023-07-30) | 135.1억 달러($13.51B) | 103.2억($10.32B) | 매출 +101%, DC +171% | 약 76% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2024) |
| 2023-11-21 | FY24 3Q (2023-10-29) | 181.2억($18.12B) | 145.1억($14.51B) | +206%, DC +279% | 약 80% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2024) |
| 2024-02-21 | FY24 4Q (2024-01-28) | 221억($22.1B) | 184억($18.4B) | +265%, DC +409% | 약 83% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2024) |
| 〃 | **FY2024 연간** | **609억($60.9B)** | 475억($47.5B) | +126%, DC +217% | 약 78% | 〃 |
| 2024-05-22 | FY25 1Q (2024-04-28) | 260억($26.0B) | 226억($22.6B) | +262%, DC +427% | 약 87% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025) |
| 2024-08-28 | FY25 2Q (2024-07-28) | 300억($30.0B) | 263억($26.3B) | +122%, DC +154% | 약 88% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2025) |
| 2024-11-20 | FY25 3Q (2024-10-27) | 351억($35.1B) | 308억($30.8B) | +94%, DC +112% | 약 88% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2025) |
| 2025-02-26 | FY25 4Q (2025-01-26) | 393억($39.3B) | 356억($35.6B) | — | 약 91% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2025) |
| 〃 | **FY2025 연간** | **1,305억($130.5B)** | 1,152억($115.2B) | — | 약 88% | 〃 |
| 2025-05-28 | FY26 1Q (2025-04-27) | 441억($44.1B) | 391억($39.1B) | +69%, DC +73% | 약 89% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2026) |
| 2025-08-27 | FY26 2Q (2025-07-27) | 467억($46.7B) | 411억($41.1B) | +56%, DC +56% | 약 88% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2026) |
| 2025-11-19 | FY26 3Q (2025-10-26) | 570억($57.0B) | 512억($51.2B) | +62%, DC +66% | 약 90% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2026) |
| 2026-02-25 | FY26 4Q (2026-01-25) | 681억($68.1B) | 623억($62.3B) | +73%, DC +75% | 약 91% | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2026), [SEC 8-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000019/q4fy26pr.htm) |
| 〃 | **FY2026 연간** | **2,159억($215.9B)** | 1,937억($193.7B) | +65%, DC +68% | 약 90% | 〃 |
| 2026-05-20 | FY27 1Q (2026-04-26) | 816억($81.6B) | 752억($75.2B) | +85%, DC +92% | 약 92% | [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000051/q1fy27pr.htm) |
| 2026-08-26 | FY27 2Q (2026-07-26) | **962억($96.2B)** | **890억($89.0B)** | +106%, DC +117% | 92.5%(보도) | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027), [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000073/q2fy27pr.htm) |
| 예정 2026-11-17 | FY27 3Q (2026-10-25) | 전망 1,080억($108.0B) ±2% | — | — | — | [Investing.com](https://www.investing.com/news/company-news/nvidia-schedules-q3-fiscal-2027-earnings-call-for-nov-17-93CH-4980909) |

메모
- 원고용 한 줄 비교(확인): **분기 매출 135억 달러(2023년 7월 분기) → 962억 달러(2026년 7월 분기), 3년 만에 약 7배**. 연매출 609억(FY24) → 1,305억(FY25) → 2,159억(FY26).
- FY27부터 사업 부문 표기가 바뀜: 「데이터센터」+「엣지 컴퓨팅(Edge Computing, 게임 등 포함)」 두 축. 데이터센터는 하이퍼스케일 / ACIE(AI 클라우드·산업·기업)로 나눔. 또 FY27부터 비GAAP 수치에서 주식보상비를 빼지 않도록 바뀌어 과거와 이익 비교 시 주의([FY27 1Q 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000051/q1fy27pr.htm)).
- FY27 2Q 순이익(GAAP) 596.88억 달러, 총이익률 75.0%(보도자료). CNBC는 539.5억 달러로 보도(비GAAP으로 추정) — 원고에는 GAAP 보도자료 값 사용.

---

## 3. 시간순 사실 원장

열: 번호 | 날짜 | 사실 | 출처 | 확인 수준 | 판 | 비고(중국판 민감 사유·대체 서술)

### 3-1. 2023년 하반기 — H100 품귀와 첫 번째 폭증

| # | 날짜 | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|---|
| 1 | 2023-05 하순 | 일론 머스크가 WSJ 행사에서 "지금 GPU는 마약보다 구하기 어렵다(considerably harder to get than drugs)"고 발언 | [GPU Utils 정리](https://gpus.llm-utils.org/nvidia-h100-gpus-supply-and-demand/), [El Financiero](https://www.elfinanciero.com.mx/opinion/jonathan-ruiz/2024/02/08/las-gpu-son-mas-dificiles-de-conseguir-que-las-drogas/) | 단일출처(원 영상 미확인, 2차 인용 다수) | 한국판만 | 중국판: "마약" 비유는 심의상 부적절. 대신 "一卡难求(카드 한 장 구하기 어렵다)" 같은 관용 표현으로 품귀 묘사 |
| 2 | 2023-08 | H100 품귀: "애저·GCP는 수백~수천 장 단위 H100 물량이 사실상 바닥, AWS도 거의 바닥"(업계 취재 정리). 샘 올트먼은 GPU 부족으로 오픈AI 단기 계획이 늦어진다고 언급 | [GPU Utils](https://gpus.llm-utils.org/nvidia-h100-gpus-supply-and-demand/) | 단일출처 | 공용 | 대기 기간 "6~12개월" 같은 구체 수치는 미확인 → 쓰지 말 것 |
| 3 | 2023-08-08 | 시그래프에서 GH200 그레이스 호퍼 슈퍼칩(HBM3e 141GB) 발표. 당시 H100 가격은 약 4만 달러로 보도 | 3편 원고 메모(국내 기사 전재), 원 기사 URL 미기록 | 단일출처 | 공용 | H100 가격은 "약 2.5만~4만 달러로 보도" 정도로 범위 표기 권장. 정가는 비공개 |
| 4 | 2023-08-21 / 08-23 | 자사주 매입 250억 달러 추가 승인. 2023년 5~7월 분기 매출 135.1억 달러(전년 대비 +101%), 데이터센터 103.2억 달러(+171%) — 한 분기 만에 매출이 88% 늘어남 | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2024) | 확인 | 공용 | |
| 5 | 2023-10-17 | 미국 상무부, 수출 규제 개정 발표. A100·A800·H100·H800·L40·L40S·RTX 4090 등을 중국 등에 수출 시 허가 필요. 10-23 엔비디아는 해당 데이터센터 제품 규제가 즉시 발효된다고 통보받음(원래 30일 유예). 직전 몇 분기 동안 이 지역 대상 매출은 데이터센터 매출의 약 20~25% | [엔비디아 8-K 10/17](https://www.sec.gov/Archives/edgar/data/1045810/000104581023000217/nvda-20231017.htm), [8-K 10/24](https://www.sec.gov/Archives/edgar/data/1045810/000104581023000221/nvda-20231023.htm), [CNBC](https://www.cnbc.com/2023/10/17/us-bans-export-of-more-ai-chips-including-nvidia-h800-to-china.html) | 확인 | 공용(서술 주의) | 중국판: "美国更新出口管制规则，部分高端芯片对华出口需许可证" 처럼 정책 사실만 중립 서술. "중국 봉쇄·압박", "기술 포위" 구도 금지. A800/H800은 원래 2022년 규제 이후 중국 시장용으로 만든 제품이라는 점은 공용 |
| 6 | 2023-11-21 | 2023년 8~10월 분기 매출 181.2억 달러(+206%), 데이터센터 145.1억 달러(+279%) | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2024) | 확인 | 공용 | |
| 7 | 2023-12-28 | 중국 전용 게임용 그래픽카드 지포스 RTX 4090 D 발표(2024-01 출시). 코어 11% 적고 "게임·창작 성능 약 5% 낮음", 가격 12,999위안. 엔비디아 "미국 수출 규제를 완전히 준수하도록 설계" | [CNBC](https://www.cnbc.com/2023/12/29/nvidia-brings-slower-gaming-chip-version-to-china-to-bypass-us-rules.html), [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/nvidia-launches-china-specific-rtx-4090d-dragon-gpu-sanctions-compliant-model-has-fewer-cores-and-lower-power-draw) | 확인 | 공용 | 중국판 소재로 좋음: 중국 게이머에게 친숙한 "4090D". 'D'가 용(Dragon)의 해 뜻이라는 설은 보도상 추정 → `据说` 처리 |
| 8 | 2023-12 | 중국용 데이터센터 칩 HGX H20 출시가 2024년 1분기로 미뤄졌다고 보도 | [Tom's Hardware 기사 내 언급](https://www.tomshardware.com/pc-components/gpus/nvidia-launches-china-specific-rtx-4090d-dragon-gpu-sanctions-compliant-model-has-fewer-cores-and-lower-power-draw) | 단일출처 | 공용 | 출시 정확한 날짜는 미확인 |

### 3-2. 2024년 — 2조·3조 달러, 세계 1위, 주식분할, 블랙웰

| # | 날짜 | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|---|
| 9 | 2024-02-12 | 젠슨 황, 두바이 세계정부정상회의에서 "모든 나라는 자국 지능의 생산을 소유해야 한다… 그래서 '소버린 AI'라는 개념이 있다" | [Reuters 전재(The Star)](https://www.thestar.com.my/tech/tech-news/2024/02/12/nvidia-ceo-huang-says-countries-must-build-sovereign-ai-infrastructure), [엔비디아 블로그](https://blogs.nvidia.com/?p=69708) | 확인 | 공용 | 중국판: "主权AI" 개념은 중국에서도 쓰는 말이라 사용 가능. 발표 장소(UAE)도 무난 |
| 10 | 2024-02-21 | FY2024 연매출 609억 달러(+126%). 황 "가속 컴퓨팅과 생성형 AI가 티핑 포인트에 도달했다" | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2024) | 확인 | 공용 | |
| 11 | 2024-02-22 | 하루에 시가총액 2,730억 달러 증가 — 당시 한 기업 하루 최대 증가 기록 | [Forbes](https://www.forbes.com/sites/dereksaul/2024/02/23/nvidia-tops-2-trillion-market-value-for-first-time-ever/) | 단일출처 | 공용 | |
| 12 | 2024-02-23 / 03-01 | 2/23 장중 시총 2조 달러 첫 돌파(종가 1.94조). 3/1 종가 기준 첫 2조 달러(약 2.06조, 주가 822.79달러·분할 전) | [Reuters 전재(Yahoo)](https://finance.yahoo.com/news/nvidia-set-close-2-trillion-192859845.html), [Forbes](https://www.forbes.com/sites/dereksaul/2024/02/23/nvidia-tops-2-trillion-market-value-for-first-time-ever/) | 확인 | 공용 | 1조(2023-06) → 2조까지 약 9개월 |
| 13 | 2024-03-18 | GTC 2024에서 블랙웰 발표: B200은 2,080억 트랜지스터(1,040억×2개 다이를 하나로 연결), GB200 NVL72 랙은 그레이스 CPU 36개+블랙웰 GPU 72개. 엔비디아는 H100 대비 조 단위 파라미터 추론 성능 최대 30배라고 주장 | [Forbes](https://www.forbes.com/sites/marcochiappetta/2024/03/18/nvidia-fortifies-ai-dominance-with-monster-blackwell-gpu-and-plethora-of-new-tech-at-gtc/), [TechRepublic](https://www.techrepublic.com/article/nvidia-gtc-2024-keynote/) | 확인 | 공용 | "30배"는 엔비디아 주장임을 밝힐 것 |
| 14 | 2024-05-22 | 2024년 2~4월 분기 매출 260억 달러(+262%), 데이터센터 226억 달러(+427%). **10대1 주식분할 발표**(6/7 기준, 6/10부터 분할 가격 거래) | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025) | 확인 | 공용 | |
| 15 | 2024-05-29 ~ 06-08 | 컴퓨텍스 방문 중 대만 방송 인터뷰에서 대만을 "가장 중요한 나라(country) 중 하나"라고 표현 → 중국 본토에서 반발·불매 주장. 6/8 황은 "지정학적 의견이 아니라 협력사들에 대한 감사 표현"이라고 해명 | [SCMP](https://www.scmp.com/news/china/politics/article/3265776/backlash-mainland-china-calls-nvidias-jensen-huang-clarify-taiwan-comment), [Taipei Times](https://www.taipeitimes.com/News/taiwan/archives/2024/06/09/2003819096), [CNN](https://www.cnn.com/2024/06/07/tech/nvidia-jenson-huang-taiwan-computex-hnk-intl) | 확인 | **중국판 피할 것** | 대만 지위 관련 발언. 한국판도 굳이 넣을 필요는 낮음(한국판만, 선택). 중국판에서는 컴퓨텍스 자체도 "台北电脑展"이라 부르지만 장면을 만들지 않는 편이 안전 |
| 16 | 2024-06-02 | 컴퓨텍스 직전 국립대만대 기조연설에서 차세대 **루빈(Rubin)** 플랫폼(GPU+베라 CPU+NVLink 6 등) 첫 공개, "1년 주기(one-year rhythm)"로 신제품 내겠다고 발표. 이전에는 약 2년 주기였음 | [엔비디아 블로그](https://blogs.nvidia.com/blog/computex-2024-jensen-huang/), [CNBC](https://www.cnbc.com/2024/06/02/nvidia-next-generation-ai-chips-rubin-blackwell.html) | 확인 | 공용 | 중국판: 장소는 "在一场主题演讲中" 정도로 흐리게 |
| 17 | 2024-06-05 | 시총 3조 달러 첫 돌파(종가 약 3.019조, 주가 1,224.40달러·분할 전), 애플을 넘어 세계 2위 | [CNBC](https://www.cnbc.com/2024/06/05/nvidia-briefly-passes-3-trillion-market-cap-on-back-of-ai-boom.html), [NBC](https://www.nbcnews.com/business/business-news/nvidia-passes-apple-market-cap-second-valuable-public-us-company-rcna155724) | 확인 | 공용 | 2조 → 3조 약 3개월 |
| 18 | 2024-06-10 | 10대1 분할 가격으로 거래 시작 | [보도자료(14번)](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2025) | 확인 | 공용 | 원고에서 "주식을 10조각으로 쪼개 1주 가격이 1/10이 됐다"로 쉽게 설명 |
| 19 | 2024-06-18 | 종가 시총 약 3.34조 달러로 마이크로소프트(3.32조)를 넘어 **처음으로 세계 시총 1위**(주가 135.58달러) | [CNN](https://edition.cnn.com/2024/06/18/markets/nvidia-largest-public-company/index.html), [Al Jazeera](https://www.aljazeera.com/economy/2024/6/19/nvidia-becomes-worlds-most-valuable-company-dethroning-microsoft) | 확인 | 공용 | 이후 1위 자리를 애플·MS와 여러 번 주고받음 |
| 20 | 2024-08 초 ~ 10-23 | 블랙웰 출시 지연: 8월 초 "설계 결함으로 약 3개월 지연" 보도(The Information) 후 주가 약 8% 하락. 8월 실적 발표에서 "수율 개선을 위해 GPU 마스크 변경, 기능 변경 없음". 10/23 황 "블랙웰에 설계 결함이 있었다… 100% 엔비디아 잘못", TSMC 갈등설은 "가짜 뉴스" | [Quartz](https://qz.com/nvidia-jensen-huang-design-flaw-blackwell-fault-ai-chip-1851679078), [DigiTimes](https://www.digitimes.com/news/a20241024VL201/nvidia-tsmc-blackwell-supplier-production.html), [heise](https://www.heise.de/en/news/Blackwell-Nvidia-s-AI-accelerator-design-flaw-fixed-thanks-to-TSMC-9992474.html) | 확인 | 공용 | "100% 엔비디아 잘못" 인용은 좋은 장면. 결함 내용은 공식 설명 없음 |
| 21 | 2024-08-28 | 2024년 5~7월 분기 매출 300억 달러(+122%), 자사주 500억 달러 추가 승인, "블랙웰 샘플 출하 중" | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2025) | 확인 | 공용 | |
| 22 | 2024-09-03 | 하루 9% 하락, 시총 약 2,790억 달러 증발(당시 미국 증시 하루 최대 감소 기록) | [Forbes(딥시크 기사 내 언급)](https://www.forbes.com/sites/dereksaul/2025/01/27/biggest-market-loss-in-history-nvidia-stock-sheds-nearly-600-billion-as-deepseek-shakes-ai-darling/) | 확인 | 공용 | 딥시크 때 기록과 비교용 |
| 23 | 2024-11-08 | 다우존스 산업평균지수에 편입, **인텔을 대체**. 발표 당시 엔비디아 연초 대비 +173%, 인텔 −54%, 인텔 시총은 엔비디아의 약 1/34 | [S&P 다우존스 발표](https://press.spglobal.com/2024-11-01-NVIDIA-and-Sherwin-Williams-Set-to-Join-Dow-Jones-Industrial-Average-Vistra-to-Join-Dow-Jones-Utility-Average), [NBC](https://www.nbcnews.com/business/nvidia-replaces-intel-dow-jones-rcna178524) | 확인 | 공용 | 1편의 "인텔은 골리앗, 엔비디아는 다윗" 구도를 되받는 장면으로 좋음 |
| 24 | 2024-12-09 | 중국 국가시장감독관리총국, 2020년 멜라녹스 인수 승인 조건 위반 혐의로 반독점 조사 착수 | [CNBC(2025-09 기사 배경)](https://www.cnbc.com/2025/09/15/china-nvidia-violated-anti-monopoly-law-will-continue-investigation.html), [JURIST](https://www.jurist.org/news/2025/09/china-finds-nvidia-violated-antimonopoly-law-in-preliminary-probe/) | 확인 | 중국판 피할 것(권장) | 중국 정부 조치라 사실 자체는 중국 매체도 보도하지만, 미중 갈등의 맞대응 구도로 읽히기 쉬움. 중국판에서 꼭 넣는다면 "国家市场监督管理总局依法对英伟达开展调查" 수준의 관영 표현만 |

### 3-3. 2025년 — 딥시크 충격, H20 롤러코스터, 4조·5조 달러

| # | 날짜 | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|---|
| 25 | 2025-01-13 경 | 바이든 정부 「AI 확산 규칙(AI Diffusion Framework)」 발표 — 국가별 등급으로 AI 칩 수출 제한. 엔비디아 부사장 "미국의 기술 우위를 낭비할 위험" 비판. 2025-05-12~13 트럼프 정부 상무부가 철회 발표 | [Wiley](https://www.wiley.law/alert-BIS-Rescinds-AI-Diffusion-Rule), [Kirkland](https://www.kirkland.com/publications/kirkland-alert/2025/05/bis-rescission-of-the-biden-administration), [US Studies Centre](https://www.ussc.edu.au/the-us-ai-diffusion-rule) | 확인(발표일 1/13·1/15 엇갈림) | 한국판만 | 정권별 정책 비교라 중국판 불필요 |
| 26 | 2025-01-27 | **딥시크 충격**: 딥시크 R1이 저비용으로 고성능을 냈다는 소식에 엔비디아 하루 −17%, 시총 **5,890억 달러** 증발 — 미국 증시 역사상 한 기업 하루 최대 감소. 엔비디아는 R1을 "훌륭한 AI 발전"이라 논평. 다음 날 약 2,600억 달러 회복 | [Bloomberg 전재(Yahoo)](https://finance.yahoo.com/news/nvidia-589-billion-deepseek-rout-211407539.html), [Forbes](https://www.forbes.com/sites/dereksaul/2025/01/27/biggest-market-loss-in-history-nvidia-stock-sheds-nearly-600-billion-as-deepseek-shakes-ai-darling/) | 확인 | 공용(서술 주의) | 중국판: 딥시크는 중국에서 자부심의 대상. "중국 AI가 엔비디아를 무너뜨렸다" 식의 승패 구도·조롱은 피하고 "一家中国团队发布的开源模型引发全球市场对算力需求的重新讨论"처럼. 이후 엔비디아가 사상 최고치를 다시 경신했다는 사실(4조·5조)과 이어서 "효율이 오르면 수요가 더 커진다"는 흐름으로 쓰면 양국 모두 무난. "훈련비 560만 달러"는 딥시크 주장 수치 → `据称` |
| 27 | 2025-02-26 | FY2025 연매출 1,305억 달러, 데이터센터 1,152억 달러. 블랙웰 첫 분기 "수십억 달러" 매출. 황 "추론 AI가 또 하나의 스케일링 법칙을 더하면서 블랙웰 수요가 놀랍다" | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2025) | 확인 | 공용 | |
| 28 | 2025-03-18 | GTC 2025: 블랙웰 울트라(GB300, 2025 하반기), 베라 루빈(2026 하반기), 루빈 울트라(2027 하반기), 그다음 세대 이름 **파인만(Feynman, 2028 예정)** 공개 | [CNBC](https://www.cnbc.com/2025/03/18/nvidia-announces-blackwell-ultra-and-vera-rubin-ai-chips-.html), [엔비디아 블로그](https://blogs.nvidia.com/blog/nvidia-keynote-at-gtc-2025-ai-news-live-updates/), [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/nvidia-announces-rubin-gpus-in-2026-rubin-ultra-in-2027-feynam-after) | 확인 | 공용 | 이름 이야기(그레이스 호퍼·블랙웰·루빈·파인만 = 과학자 이름)는 공용 소재 |
| 29 | 2025-04-09 / 04-15 | 미국 정부, H20의 중국 수출에 허가가 필요하다고 통보(사실상 판매 중단). 2025년 2~4월 분기에 H20 재고·구매약정 관련 **45억 달러** 비용 처리, 출하 못 한 H20 매출 25억 달러. 다음 분기 전망에 "H20 매출 손실 약 80억 달러" 반영 | [보도자료 FY26 1Q](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-first-quarter-fiscal-2026) | 확인 | 공용(서술 주의) | 처음 공시는 55억 달러 비용 예상이었으나 실제 처리액은 45억 달러(보도자료 기준) |
| 30 | 2025-04-14 | 향후 4년간 미국에서 최대 5,000억 달러 규모 AI 인프라 생산 계획 발표. TSMC 애리조나에서 블랙웰 생산 시작, 텍사스(폭스콘 휴스턴·위스트론 댈러스)에서 AI 슈퍼컴퓨터 조립 | [CNBC](https://www.cnbc.com/2025/04/14/nvidia-to-mass-produce-ai-supercomputers-in-texas.html), [The Hill](https://thehill.com/policy/technology/5247815-nvidia-ai-chip-manufacturing/) | 확인 | 한국판만 | 미국 제조 회귀 정치 맥락. 중국판에는 불필요 |
| 31 | 2025-05-19 | 컴퓨텍스 2025에서 대만 신사옥 「컨스텔레이션(Constellation)」 부지(타이베이 베이터우·스린 과학단지) 발표 | [TaiwanPlus](https://www.taiwanplus.com/news/taiwan-news/technology-and-science/250519012/nvidia-unveils-new-constellation-taiwan-hq-at-computex-taipei), [DigiTimes](https://www.digitimes.com/news/a20250519PD231/nvidia-jensen-huang-taipei-taiwan-2025.html) | 확인 | 중국판 피할 것 | 대만 관련 장면 최소화 원칙. 착공 여부(2026)는 미확인 |
| 32 | 2025-07-09 / 07-10 | 7/9 장중 시총 **4조 달러** 첫 돌파(세계 최초, 주가 164.42달러), 7/10 종가 4.004조 달러. 3조 → 4조 약 13개월 | [CNBC](https://www.cnbc.com/2025/07/09/nvidia-4-trillion.html), [CBS](https://www.cbsnews.com/news/chipmaker-nvidia-becomes-most-valuable-company-in-the-world-at-4-trillion/), [Bloomberg](https://www.bloomberg.com/news/articles/2025-07-09/nvidia-hits-4-trillion-value-as-rally-notches-another-milestone) | 확인 | 공용 | |
| 33 | 2025-07-14~16 | 엔비디아, 미국 정부가 H20 판매 허가를 내줄 것이라는 보장을 받았다며 중국 판매 재개 발표. 7/16 베이징 「제3회 중국국제공급망촉진박람회(链博会)」 개막식에서 황이 일부 중국어로 연설: "중국 공급망은 기적", "딥시크·알리바바·텐센트·미니맥스·바이두 어니 같은 모델은 세계적 수준", "중국 개발자 150만 명 이상이 엔비디아 위에서 개발" | [CNBC](https://www.cnbc.com/2025/07/16/as-nvidia-gets-a-lifeline-in-china-jensen-huang-goes-on-the-charm-offensive-in-beijing.html), [Global Times](https://www.globaltimes.cn/page/202507/1338497.shtml), [신화](https://english.news.cn/20250718/973d3cd8e00a4747beaefb1daf409721/c.html) | 확인 | **중국판만**(핵심 소재), 한국판은 요약 | 중국판 하이라이트 후보: 첫 중국어 연설, 중국 AI 칭찬, 150만 개발자. 7/20 CCTV 「面对面」 인터뷰도 있음([Geopolitechs](https://www.geopolitechs.org/p/jensen-huangs-interview-on-cctvs)). 희토류 교환 언급은 중국판 피할 것 |
| 34 | 2025-07-31 | 중국 국가인터넷정보판공실(网信办)이 H20의 "백도어 보안 위험"을 이유로 엔비디아를 불러 설명 요구. 8/5 엔비디아 최고보안책임자 블로그 "GPU에 킬 스위치·백도어는 없고 있어서도 안 된다" | [신화](https://english.news.cn/20250731/934beba4e31949ed92cfcaa6ecb86678/c.html), [AP(US News)](https://www.usnews.com/news/business/articles/2025-07-31/china-summons-nvidia-over-backdoor-safety-risks-in-h20-chips), [Bloomberg](https://www.bloomberg.com/news/articles/2025-07-31/china-summons-nvidia-representatives-over-h20-chip-security-risk) | 확인 | 중국판 피할 것 | 중국 규제기관과 엔비디아 대립 장면. 중국판에서는 생략하거나 "围绕芯片安全问题，监管部门约谈了英伟达" 한 줄 이하 |
| 35 | 2025-08-10~11 | 엔비디아·AMD가 중국향 H20·MI308 판매액의 15%를 미국 정부에 내는 조건으로 수출 허가를 받는다는 보도(FT) → 트럼프가 기자회견에서 확인, "처음엔 20%를 원했는데 젠슨이 15%로 깎았다" | [NPR](https://www.npr.org/2025/08/11/nx-s1-5498689/trump-nvidia-h20-chip-sales-china), [CBS](https://www.cbsnews.com/news/nvidia-amd-chip-sales-china-15-percent-h20-mi308/), [PBS](https://www.pbs.org/newshour/politics/under-new-unusual-agreement-u-s-will-get-a-15-cut-of-nvidia-and-amd-chip-sales-to-china) | 확인 | 한국판만 | 정치 인물 발언 + 대중국 거래 조건. 중국판 피할 것에 준함 |
| 36 | 2025-08-27 | 2025년 5~7월 분기 매출 467억 달러. "이 분기 중국 고객에 대한 H20 매출 없음", 다음 분기 전망에도 중국향 H20 출하 미반영. 자사주 600억 달러 추가 승인 | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2026) | 확인 | 공용 | 중국판: "受多重因素影响，H20对华出货暂停" 중립 서술 |
| 37 | 2025-09-15 | 중국 국가시장감독관리총국, 예비조사 결과 엔비디아가 반독점법을 위반했다고 발표하고 추가 조사 예고. 엔비디아 10-Q: 규제당국은 "미국 수출 규제 준수로 중국에 성능을 낮춘 제품을 제공한 것이 중국 고객을 부당 차별한 것"으로 봤다고 기재. 엔비디아 "모든 면에서 법을 준수한다" | [CNBC](https://www.cnbc.com/2025/09/15/china-nvidia-violated-anti-monopoly-law-will-continue-investigation.html), [엔비디아 10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000230/nvda-20251026.htm) | 확인 | 중국판 피할 것(권장) | 24번과 같은 이유. 최종 처분은 2026-11 현재까지 확인 안 됨(미확인) |
| 38 | 2025-09-17 | FT 보도: 网信办이 바이트댄스·알리바바 등에 블랙웰 기반 중국용 칩 RTX Pro 6000D 시험·주문 중단 지시. 보도에 따르면 규제당국은 화웨이·캄브리콘 등 중국 칩이 엔비디아의 중국용 제품과 비슷하거나 낫다고 판단. 황 "실망스럽다" | [Bloomberg(FT 인용)](https://www.bloomberg.com/news/articles/2025-09-17/china-agency-orders-firms-to-stop-buying-nvidia-ai-chip-ft-says), [Engadget](https://www.engadget.com/ai/china-reportedly-bans-tech-companies-from-buying-nvidias-ai-chips-120143740.html) | 단일출처(FT, 익명 소식통) | 중국판 피할 것 | 중국 기업과의 성능 우열 비교 + 정부 지시. 중국판에선 생략 |
| 39 | 2025-09-18 | 화웨이 쉬즈쥔 순환회장, 어센드(昇腾) 로드맵 발표: 950PR(2026 1분기)·950DT(2026 4분기)·960(2027)·970(2028), 자체 HBM | [Tom's Hardware](https://www.tomshardware.com/tech-industry/semiconductors/huawei-unveils-ascend-roadmap-backed-by-in-house-hbm), [RCR Wireless](https://rcrwireless.com/20250922/ai-infrastructure/huawei-ai-chips) | 확인 | 한국판만(경쟁사 소개) | 중국판: 화웨이를 "엔비디아보다 낫다/못하다"로 비교하지 말 것. 넣는다면 "中国本土算力生态也在快速发展" 같은 우열 없는 서술 |
| 40 | 2025-09-18 | 엔비디아, 인텔에 50억 달러 투자 발표(주당 23.28달러, 약 4% 지분). 데이터센터 CPU·PC 칩 공동 개발. 2025-12-26 거래 완료 | [CNBC](https://www.cnbc.com/2025/12/29/nvidia-takes-5-billion-stake-in-intel-under-september-agreement.html), [CBC](https://www.cbc.ca/lite/story/1.7636948) | 확인 | 공용 | 1편 "다윗과 골리앗"의 역전 장면으로 매우 좋음 |
| 41 | 2025-09-22 | 오픈AI와 전략적 제휴: 최소 10GW 엔비디아 시스템 구축, 엔비디아는 단계적으로 **최대 1,000억 달러** 투자 의향서(LOI). 첫 1GW는 2026 하반기 베라 루빈 플랫폼 | [엔비디아 보도자료](https://nvidianews.nvidia.com/news/openai-and-nvidia-announce-strategic-partnership-to-deploy-10gw-of-nvidia-systems) | 확인 | 공용 | 이후 실제로는 축소(53번) — 둘을 반드시 같이 쓸 것 |
| 42 | 2025-10-06 | AMD–오픈AI 6GW 계약(2026 하반기 MI450 1GW부터), AMD는 오픈AI에 주식 최대 1억6천만 주 워런트 | [Yahoo](https://finance.yahoo.com/news/openai-selects-amd-gpus-6gw-103137328.html), AMD IR(ir.amd.com, 원문 미열람) | 확인 | 공용 | 경쟁사 장면. AMD는 1편에 나온 젠슨 황의 첫 직장 → 연결 고리 |
| 43 | 2025-10-06(공개 10/16 경) | 황, 시타델 행사에서 "중국 시장 점유율이 95%에서 0%가 됐다", "우리 전망에서 중국은 0으로 가정" | [SCMP](https://www.scmp.com/tech/article/3329292/nvidia-chief-holds-hope-policy-change-china-market-share-drops-0-95), [Caixin](https://www.caixinglobal.com/2025-10-18/us-export-ban-wipes-out-nvidias-china-market-ceo-says-102372899.html), [Global Times](https://www.globaltimes.cn/page/202510/1345958.shtml) | 확인 | 공용(서술 주의) | 중국 매체도 크게 다룬 발언이라 중국판 사용 가능. 단 미국 정책 비판 대목("중국을 해치는 것이 미국을 더 해칠 수 있다")은 정치 논평이 되므로 인용 최소화. "95%→0%"는 고급 AI 칩 시장 기준 황의 표현임을 명시 |
| 44 | 2025-10-28 | 워싱턴 GTC: 블랙웰+루빈 2026년 말까지 누적 주문(예약) **5,000억 달러** 공개, 미 에너지부 슈퍼컴퓨터 7대, 노키아에 10억 달러 투자. 당일 종가 시총 4.89조 달러 | [Reuters 전재(Al Jazeera)](https://www.aljazeera.com/economy/2025/10/29/chipmaker-nvidia-hits-5-trillion-valuation), [TrendForce](https://www.trendforce.com/news/2025/10/29/news-nvidia-dismisses-ai-bubble-concerns-reportedly-projects-500b-in-gpu-sales-from-blackwell-and-rubin/) | 확인 | 한국판만(장소·정부 계약) / 수치는 공용 | 중국판은 "5000亿美元订单" 수치만 |
| 45 | 2025-10-29 | **세계 최초 시총 5조 달러** 기업(장중 주가 최고 212.19달러). 4조 달러 돌파 후 약 3개월 | [CNBC](https://www.cnbc.com/2025/10/29/nvidia-on-track-to-hit-historic-5-trillion-valuation-amid-ai-rally.html), [TechCrunch](https://techcrunch.com/2025/10/29/nvidia-becomes-first-public-company-worth-5-trillion/), [CNN](https://www.cnn.com/2025/10/29/tech/nvidia-5-trillion-valuation-ai) | 확인 | 공용 | 4편 클라이맥스 후보. 1조(2023-06) → 5조(2025-10) 약 2년 4개월 |
| 46 | 2025-11-18 | 마이크로소프트·엔비디아·앤트로픽 3자 제휴: 엔비디아가 앤트로픽에 최대 100억 달러 투자(조건부), 앤트로픽은 그레이스 블랙웰·베라 루빈 기반 최대 1GW 사용 약정 | [CNBC](https://www.cnbc.com/2025/11/18/anthropic-ai-azure-microsoft-nvidia.html), [엔비디아 10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000230/nvda-20251026.htm) | 확인 | 공용 | "고객에게 투자하고 그 돈이 다시 칩 구매로 돌아온다"는 순환 투자 논란과 함께 다루면 균형 |
| 47 | 2025-11-19 | 2025년 8~10월 분기 매출 570억 달러(+62%), 데이터센터 512억 달러. 황 "블랙웰 판매는 차트를 뚫었고, 클라우드 GPU는 매진" | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-third-quarter-fiscal-2026) | 확인 | 공용 | |
| 48 | 2025-11-24~25 | 메타가 구글 TPU 도입을 협의 중이라는 보도(The Information) → 엔비디아 장중 최대 −7%, 종가 −2.6%. 엔비디아 공식 X 계정 "구글의 성공을 기쁘게 생각한다… 엔비디아는 업계보다 한 세대 앞서 있고 모든 AI 모델을 돌리는 유일한 플랫폼" | [CNBC](https://www.cnbc.com/2025/11/25/nvidia-says-its-gpus-are-a-generation-ahead-of-googles-ai-chips.html), [SiliconANGLE](https://siliconangle.com/2025/11/25/nvidia-shares-drop-report-meta-may-buy-tpus-google/) | 확인(협의 자체는 단일출처) | 공용 | 자체 칩(TPU·트레이니엄) 경쟁 장면 |
| 49 | 2025-12-08 | 트럼프, H200을 "승인된 중국 고객"에게 판매 허용, 대신 미국이 25%를 가져간다고 발표. 블랙웰·루빈은 제외 | [CNBC](https://www.cnbc.com/2025/12/08/trump-nvidia-h200-sales-china.html), [Axios](https://www.axios.com/2025/12/08/trump-nvidia-200-chips) | 확인 | 한국판만 | 정치 인물 발언. 중국판에선 "H200获准在一定条件下对华销售" 정도로만 |
| 50 | 2025-12-24 | 추론 칩 스타트업 그록(Groq)과 기술 비독점 라이선스 + 핵심 인력 영입 계약, 약 200억 달러(현금, 투자사 대표가 CNBC에 밝힌 금액) — 엔비디아 사상 최대 거래. 황 "그록을 회사째 인수하는 것은 아니다" | [CNBC](https://www.cnbc.com/2025/12/24/nvidia-buying-ai-chip-startup-groq-for-about-20-billion-biggest-deal.html), [SiliconANGLE](https://siliconangle.com/2025/12/24/nvidia-license-technology-inference-chip-startup-groq-reported-20b-deal/) | 확인(금액은 단일출처 성격) | 공용 | 2026 GTC에서 「그록 3 LPX」 제품으로 이어짐(55번) |

### 3-4. 2026년 — 루빈, 6조 문턱, 다시 흔들리는 왕좌

| # | 날짜 | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|---|
| 51 | 2026-01-05 | CES 2026 기조연설: 베라 루빈 플랫폼 "본격 생산(full production)" 발표. 6종 칩(베라 CPU·루빈 GPU·NVLink 6 스위치·ConnectX-9·BlueField-4·Spectrum-6). 엔비디아는 블랙웰 대비 추론 5배·학습 3.5배 성능 주장, 2026 하반기 고객 배치 | [Tom's Hardware](https://www.tomshardware.com/tech-industry/artificial-intelligence/nvidia-ceo-confirms-vera-rubin-nvl72-is-now-in-production-jensen-huang-uses-ces-keynote-to-announce-the-milestone), [DCD](https://www.datacenterdynamics.com/en/news/nvidia-ceo-announces-vera-rubin-chips-are-in-full-production-during-ces-keynote/) | 확인 | 공용 | "full production" 표현은 1월(첫 이정표)과 5월(대량 양산 보도자료)에 두 번 쓰였음 → 원고는 "1월 생산 착수, 5월 본격 양산"으로 |
| 52 | 2026-01-23~28 | 황, 2026년 첫 중국 방문: 상하이(장장 신사무소, 루자쭈이 시장에서 과일 사고 상인에게 600위안 홍바오) → 베이징 → 선전. 춘절 전 직원 행사. 보도에 따르면 중국 직원 약 4,000명, 그중 2,000명 이상 상하이 연구개발센터 | [CNBC](https://www.cnbc.com/2026/01/23/nvidia-ceo-jensen-huang-china-visit-chip-sales-restrictions.html), [Global Times](https://www.globaltimes.cn/page/202601/1354183.shtml), [DigiTimes](https://www.digitimes.com/news/a20260126PD231/nvidia-shanghai-ceo-jensen-huang-sales.html) | 확인(직원 수는 단일출처) | **중국판만**(핵심 소재) | 중국 시청자 친화 장면: 시장에서 과일 사기·홍바오·중국 직원. 한국판은 한 줄 |
| 53 | 2026-01-28 / 03-18 | 로이터: 중국이 H200 첫 수입 물량(수십만 개) 승인, 바이트댄스·알리바바·텐센트 대상이라고 보도. 3월 로이터·WSJ 추가 승인 보도. 그러나 엔비디아 10-Q(2026-04-26 분기)는 "H200 허가 프로그램으로 아직 매출 없음, 중국 반입 허용 여부도 모름" | [CNBC(Reuters)](https://www.cnbc.com/2026/01/28/china-gives-green-light-importing-first-batch-nvidias-h200-ai-chips-sources-say.html), [Semafor](https://www.semafor.com/article/01/28/2026/china-approves-the-first-batch-of-nvidia-h200-chip-imports), [엔비디아 10-Q](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000052/nvda-20260426.htm) | 단일출처(익명 소식통) + 공시는 확인 | 공용(서술 주의) | 중국판: "据报道，字节跳动、阿里巴巴、腾讯等中国企业获批采购" — 중국 고객사 소재로 활용 가능. 승인 규모 숫자는 쓰지 말 것 |
| 54 | 2026-02-02 / 02-27 | 황 "오픈AI 1,000억 달러는 약속(commitment)이 아니었다". 2/27 오픈AI 1,100억 달러 투자 라운드에 엔비디아 300억 달러 참여(아마존 500억·소프트뱅크 300억) | [Fortune](https://fortune.com/2026/02/02/jensen-huang-nvidia-ceo-on-openai-investment-never-a-commitment/), [Yahoo](https://finance.yahoo.com/news/nvidia-says-100-billion-openai-183732361.html) | 확인(라운드 최종 규모 1,220억·기업가치 8,520억은 단일출처) | 공용 | 41번과 짝 |
| 55 | 2026-03-16 | GTC 2026 기조연설: 블랙웰+베라 루빈 주문이 2027년까지 **1조 달러**에 이를 것(1년 전 5,000억의 두 배). 루빈 울트라(2027, 「카이버」 랙), 파인만(2028), 그록 3 LPX 추론 가속기, 우주 데이터센터 「베라 루빈 스페이스-1」, BYD·현대·닛산·지리(吉利) 자율주행 협력 | [Tom's Hardware](https://www.tomshardware.com/news/live/nvidia-gtc-2026-keynote-live-blog-jensen-huang), [TweakTown](https://www.tweaktown.com/news/110521/nvidia-updates-roadmap-with-new-details-on-its-next-gen-gpu-feynman-coming-in-2028/index.html), [Jon Peddie](https://www.jonpeddie.com/news/nvidia-gtc-2026-keynote/) | 확인(세부 사양은 매체마다 엇갈림 → 사양 수치는 쓰지 말 것) | 공용 | 중국판: BYD(比亚迪)·지리(吉利) 협력은 좋은 중국 소재. 3/18 황 "중국 많은 고객에게서 H200 주문" 발언 보도 |
| 56 | 2026-03-19 | 슈퍼마이크로 공동창업자 등 3명, 엔비디아 AI 칩 탑재 서버 25억 달러어치를 중국으로 불법 우회 수출한 혐의로 기소 | [CNN](https://www.cnn.com/2026/03/19/politics/super-micro-computer-founder-charged-ai-chips-china), [Fortune](https://fortune.com/2026/05/05/supermicro-nvidia-china-smuggling-investigation/) | 확인 | 중국판 피할 것 | 밀수·형사 사건. 한국판도 엔비디아 자체 사건이 아니므로 선택 |
| 57 | 2026-05-13~15 | 트럼프 방중(베이징 미중 정상회담)에 황이 막판 합류(5/13 에어포스원 탑승). 5/13 시총 5.5조 달러 첫 돌파, 5/14 종가 235.74달러·시총 약 5.71조 달러 사상 최고(7거래일 연속 상승). 로이터는 미 상무부가 중국 기업 약 10곳의 H200 구매를 허가했다고 보도 | [CNBC](https://www.cnbc.com/2026/05/13/nvidia-says-ceo-jensen-huang-is-joining-trumps-china-trip.html), [Bloomberg](https://www.bloomberg.com/news/articles/2026-05-14/nvidia-gains-20-in-seven-days-nearing-6-trillion-market-value), [GuruFocus](https://www.gurufocus.com/news/8861002/nvidia-hits-record-high-as-market-cap-soars-to-571-trillion-nvda) | 확인(10곳 허가는 단일출처) | 공용(서술 주의) | 중국판: 정상 이름·정치 맥락은 빼고 "随美国企业家代表团访华" 정도. 시총 기록은 공용 |
| 58 | 2026-05-18 / 05-20 | 자사주 800억 달러 추가 승인, 분기 배당 0.01달러 → 0.25달러로 인상. 2026년 2~4월 분기 매출 816억 달러(+85%), 데이터센터 752억 달러(그중 네트워킹 148억, +199%). 사업 부문을 데이터센터/엣지 컴퓨팅으로 개편 | [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000051/q1fy27pr.htm) | 확인 | 공용 | |
| 59 | 2026-05-14 ~ 07 초 | 5/14 고점 이후 약 두 달간 주가 약 16% 하락, 시총 약 1조 달러 증발. 블룸버그는 AI 투자금이 메모리 등 다른 반도체로 이동한 영향으로 분석. 7/8 기준 예상이익 대비 주가배수(약 18배)가 생성형 AI 붐 이전 수준으로 내려감 | [Bloomberg](https://www.bloomberg.com/news/articles/2026-07-08/nvidia-s-1-trillion-slide-sends-valuation-to-pre-ai-boom-levels), [Yahoo](https://finance.yahoo.com/markets/stocks/articles/nvidia-stock-valuation-falls-pre-132505643.html) | 확인 | 공용 | "회사 실적이 나빠서가 아니라 기대가 옮겨간 것"이라는 해석이 다수. 일부 기사의 "2019년 이후 최저 시총"은 배수(밸류에이션)를 잘못 옮긴 것으로 보임 → 쓰지 말 것 |
| 60 | 2026-08-26 | 2026년 5~7월 분기 매출 **962억 달러**(+106%), 데이터센터 **890억 달러**(+117%, 매출의 92.5%), GAAP 순이익 596.88억 달러. 다음 분기 전망 1,080억 달러, 전망에 중국 데이터센터 연산 매출 0 가정. 황 "AI가 변곡점에 도달했다… 이제 컴퓨트가 곧 매출", 베라 루빈 "본격 생산 중". CFO는 다음 회계연도(FY28) 매출 70% 성장 전망. 중국으로 간 구형 칩 출하는 데이터센터 매출의 "1% 미만" | [보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-second-quarter-fiscal-2027), [CNBC](https://www.cnbc.com/2026/08/26/nvidia-nvda-earnings-report-q2-2027-live-updates.html) | 확인(70%·1% 미만은 CNBC 보도) | 공용 | 4편의 "현재" 숫자. 아마존 AWS가 GPU 200만 개 구매(황 발언, CNBC) — 단일출처 |
| 61 | 2026-08 | SB에너지 오하이오 파이크 카운티 캠퍼스(약 4.25GW) 임대 보증, 엔비디아 부담 최대 1,050억 달러, 오픈AI에 20년 임대 | [엔비디아 10-Q(2026-07-26 분기)](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000075/nvda-20260726.htm) | 단일출처(공시 원문 직접 미열람, 검색 요약 경유) | 한국판만 | 원고에 쓰려면 10-Q 원문 재확인 필요 |
| 62 | 2026-09-02~03 | 허깅페이스 인수 확정 계약, 약 129.3억 달러(매수 대금 약 119억 + 직원 유지 보상 최대 약 10억). 2027 상반기 완료 예정(규제 승인 조건). 엔비디아 "허깅페이스는 모든 AI 생태계에 열린 플랫폼으로 남고 엔비디아 칩을 강요하지 않는다" — 그록에 이어 두 번째 큰 거래 | [엔비디아 블로그](https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face/), [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000078/nvda-20260902.htm), [CNN](https://www.cnn.com/2026/09/03/tech/nvidia-hugging-face-ai-acquisition) | 확인 | 공용 | 중국판: 허깅페이스는 중국 개발자도 많이 쓰는 플랫폼(접속 사정은 별개) → "全球最大的开源模型社区" 정도로 소개 |
| 63 | 2026-09-28 | 자사주 매입 1,500억 달러 추가 승인 — 엔비디아 발표 기준 "역사상 최대 자사주 매입 승인 증액", 잔여 한도 2,350억 달러(FY2028까지) | [엔비디아 IR](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-a-150-Billion-Share-Repurchase-Authorization-Increase/default.aspx), [CNBC](https://www.cnbc.com/2026/09/28/nvidia-share-buyback-plan-gets-150-billion-boost.html) | 확인 | 공용 | |
| 64 | 2026-10-02 / 10-06 | 10/2 5월 이후 첫 종가 최고치(시총 약 5.7조). 10/6 장중 사상 최고 243.37달러, 시총 5.8조 달러 넘어 **"세계 첫 6조 달러" 문턱**(약 249달러 필요)까지 접근 — 6조 돌파는 확인되지 않음 | [Bloomberg](https://www.bloomberg.com/news/articles/2026-10-06/nvidia-heads-for-6-trillion-value-with-chipmaker-back-at-record), [Yahoo](https://finance.yahoo.com/markets/stocks/articles/nvidia-stock-hits-record-high-175422059.html) | 확인 | 공용 | 원고에서 "6조 돌파"라고 쓰면 오류. "6조 문턱"까지만 |
| 65 | 2026-10-29 | 뉴욕타임스 보도: 미국 정보당국이 황과 가까운 싱가포르 데이터센터 업체(Megaspeed) 임원을 중국 측 정보원으로 의심했다는 내용. 엔비디아 "고객 임원과의 만남은 CEO 업무의 일부", 칩 우회 의혹은 "작년에 조사해 사실무근으로 결론". 중국 외교부 "중국을 먹칠하려는 시도" | [CNBC](https://www.cnbc.com/2026/10/29/nvidia-jensen-huang-chinese-intelligence-asset.html), [Bloomberg](https://www.bloomberg.com/news/articles/2026-10-29/nvidia-ceo-says-ties-to-company-under-spying-probe-were-normal), [Euronews](https://www.euronews.com/2026/10/30/china-rejects-report-of-spy-plot-targeting-nvidias-jensen-huang) | 확인(보도 사실) / 의혹 내용은 미확인 | **중국판 피할 것**, 한국판도 사용 비권장 | 확인되지 않은 정보기관 의혹 + 개인 명예 문제. 브랜드 다큐 성격과 맞지 않음 |
| 66 | 2026-10-23 / 10-30 | 10/23 장중 애플이 잠시 시총 1위. 10/30 종가 애플 5.03조 vs 엔비디아 4.93조 달러로 **애플이 세계 1위 탈환**(블룸버그: 7월 말 잠깐 이후 처음). 엔비디아 10월 한 달 약 −10%(AI 투자 회수 우려) | [Bloomberg](https://www.bloomberg.com/news/articles/2026-10-30/apple-overtakes-nvidia-to-become-world-s-most-valuable-company), [Business Standard](https://www.business-standard.com/world-news/apple-overtakes-nvidia-to-become-world-s-most-valuable-company-at-5-03-trn-126103100103_1.html), [9to5Mac](https://9to5mac.com/2026/10/23/apple-overtakes-nvidia-as-most-valuable-company-in-the-world-on-iphone-duo-launch-day/) | 확인 | 공용 | 4편 엔딩 "왕좌는 영원하지 않다 / 11/17 실적이 다음 장" 구도에 적합. 월간 하락률 −10.39%는 단일출처 |
| 67 | 2026-11-03 | FT 보도: 엔비디아가 클라우드 협력사에 앞으로의 계약에서 서비스 매출 51% 이상을 중국 밖 기업에서 내도록(중국 기업 49% 상한) 구두 요구. 엔비디아는 확인도 부인도 안 함. 중국 외교부 "보도 내용을 모른다" | [France24(AFP)](https://www.france24.com/en/live-news/20261103-nvidia-orders-data-center-clients-to-reduce-china-exposure-ft), [Bloomberg(FT 인용)](https://www.bloomberg.com/news/articles/2026-11-03/nvidia-tells-data-center-clients-to-trim-china-business-ft-says), [Taipei Times](https://www.taipeitimes.com/News/biz/archives/2026/11/04/2003867097) | 단일출처(FT, 익명 소식통) | 중국판 피할 것 | 중국 기업 배제 조치 보도. 한국판도 "보도" 수준으로만 |
| 68 | 2026-11-03 | 종가 206.69달러(+2.29%) | [Gotrade](https://www.heygotrade.com/en/news/nvidia-nvda-stock-news-november-4-2026/) | 단일출처 | 한국판만 | 이 시점 시총은 출처 확인 못 함 → "약 5조 달러 안팎"도 미확인. 원고에는 10/30 블룸버그 종가 4.93조를 쓰는 것을 권장 |
| 69 | 2026-11-17(예정) | FY27 3분기(2026-10-25 끝) 실적 발표 예정, 오후 2시 PT 컨퍼런스콜 | [Investing.com](https://www.investing.com/news/company-news/nvidia-schedules-q3-fiscal-2027-earnings-call-for-nov-17-93CH-4980909), [StockTitan](https://www.stocktitan.net/news/NVDA/nvidia-sets-conference-call-for-third-quarter-financial-rgdf7hquxgar.html) | 확인 | 공용 | 4편 제작 일정이 11/17 이후면 실적 수치 반영 여부 결정 필요 |

### 3-5. 날짜를 특정하지 않는 배경 사실(장 구성용)

| # | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|
| 70 | 중국(홍콩 포함) 매출: FY2024 103.06억 달러(약 17%, 청구지 기준), FY2025 171.08억(13.1%, 청구지 기준). FY2026 10-K부터 "고객 본사 소재지 기준"으로 바꿔 FY2025를 250.48억으로 재작성, FY2026은 196.77억 달러(총매출의 약 9.1%) | [FY2024 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm), [FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm), 비율 계산은 [FourWeekMBA](https://fourweekmba.com/ai-nvidias-china-revenue-19-under-its-new-count-not-13/) | 확인(10-K 수치) / 비율은 계산값 | 공용 | 기준이 바뀐 것을 꼭 밝힐 것. "중국 비중 약 1/5 → 1/10 이하"로 요약 가능. FY27 2Q 중국 본사 고객 매출 79억 달러(8%)는 단일출처 |
| 71 | 쿠다(CUDA) 생태계: 중국 개발자 150만 명 이상(황 2025-07 연설). 글로벌 개발자 수의 최신 공식 수치는 이번 조사에서 확인 못 함 | 33번 출처 | 중국 수치는 확인 / 글로벌은 미확인 | 공용 | 쿠다 해자 설명은 2편(2006 쿠다 첫 등장)과 연결. 글로벌 "수백만 명" 같은 숫자는 쓰지 말 것 |
| 72 | 데이터센터 GPU 점유율: "서버 GPU 시장 약 97%(2025년 말)"(블룸버그 기사 내 인용), "AI 칩 시장 90% 이상"(애널리스트 추정, CNBC) | [Yahoo(Bloomberg)](https://finance.yahoo.com/markets/stocks/articles/nvidia-stock-valuation-falls-pre-132505643.html), [CNBC](https://www.cnbc.com/2025/11/25/nvidia-says-its-gpus-are-a-generation-ahead-of-googles-ai-chips.html) | 단일출처(조사기관·기준 제각각) | 공용 | 점유율은 "~로 추정된다"로만. 3편 "딜로이트 97%"는 출처 확인 불가(정정표 참고) |
| 73 | 중국 내 호칭: 英伟达, 黄仁勋, 별명 「黄教主」·「皮衣刀客」(가죽 재킷과 "칼질(제품 성능 자르기)"을 빗댄 인터넷 별명) | 출처 미기록(중국 인터넷 관용) | 미확인 | 중국판만(선택) | 중국 현지 검수자 확인 후 사용. "刀客"는 성능 깎은 중국판 제품을 비꼬는 뉘앙스가 있어 쓰지 않는 편이 무난 |

---

## 4. 확인 수준·판 집계

- 원장 항목: **73건**(3-1~3-4 시간순 69건 + 배경 4건). 분기 실적표는 별도 17행.
- 확인 수준(항목별 주 판정 기준)
  - 확인: **60건** — 이 중 50·54·57·60처럼 일부 세부 수치만 단일출처인 항목은 비고에 따로 표시
  - 단일출처(据报道): **11건** — 1, 2, 3, 8, 11, 38, 53, 61, 67, 68, 72
  - 미확인: **2건** — 65(의혹 내용 자체), 73(중국 별명). 이 밖에 개별 수치 단위의 미확인(H100 대기 개월 수, 글로벌 쿠다 개발자 수, 11/3 시총, 6조 돌파 여부, 중국 반독점 최종 처분)은 비고에 표시
- 판 표시
  - 공용: **52건**(그중 "서술 주의" 6건: 5, 26, 29, 43, 53, 57)
  - 한국판만: **9건**(1, 25, 30, 35, 39, 44, 49, 61, 68) — 35·49(트럼프 발언·몫 배분)는 사실상 중국판 금지
  - 중국판만: **3건**(33, 52, 73)
  - 중국판 피할 것: **9건**(15, 24, 31, 34, 37, 38, 56, 65, 67)

---

## 5. 중국판 민감 항목 요약과 대체 서술

| 분류 | 해당 항목 | 왜 위험한가 | 중국판 대체 |
|---|---|---|---|
| 대만 지위 | 15(대만 "나라" 발언), 31(대만 신사옥), 1편 출생지 | 대만 관련 표현은 최우선 심의 대상. 2024년 실제로 중국 본토 반발 발생 | 출생지는 "出生于中国台湾台南"(관용 표기). 컴퓨텍스·대만 사옥 장면은 만들지 않음. 루빈 첫 공개(16)는 장소 없이 "2024年6月的一场演讲中" |
| 미중 수출 규제 구도 | 5, 25, 29, 35, 36, 49 | "미국이 중국을 압박·봉쇄" 또는 반대로 "중국이 굴복" 구도 모두 위험. 정치 인물(트럼프·바이든) 발언·거래 조건(15%·25% 몫)은 정치 논평이 됨 | "受美国出口管制政策变化影响，英伟达多次调整面向中国市场的产品"으로 사실만. 제품 흐름(A800/H800 → H20 → RTX 4090D → H200)을 "中国特供版"이라는 업계 일반 표현으로 정리 |
| 중국 규제기관과의 대립 | 24, 34, 37, 38 | 중국 정부 조치를 영상에서 평가하는 순간 어느 쪽으로든 문제 소지 | 생략 권장. 꼭 필요하면 관영 표현 한 줄("监管部门依法开展调查") |
| 중국 기업 우열 비교 | 38, 39, 72 | 화웨이·캄브리콘을 "엔비디아보다 못하다/낫다"로 비교하면 위험 | "中国本土算力产业快速发展，市场选择更加多元" 같은 우열 없는 서술 |
| 딥시크 | 26 | 중국에서는 자부심 소재. 조롱·승패 구도·"중국발 폭락" 표현은 반감 | "深度求索的开源模型以高效率引发全球关注，市场一度重新评估算力需求" → 이후 엔비디아도 R1을 "훌륭한 진전"이라 평가했다는 공식 반응과 함께 |
| 밀수·정보기관 의혹 | 56, 65, 67 | 형사·안보 사안, 중국 외교부가 반박한 사안 | 전부 생략 |
| 정상외교 | 57 | 정치 인물 등장 | "2026年5月，黄仁勋随美国企业家代表团访华" 한 줄. 시총 5.5조·5.71조 기록은 그대로 사용 가능 |

**중국판에 넣으면 좋은 중국 시장 소재**
1. 2025-07 베이징 링보후이(链博会) 첫 참석·일부 중국어 연설, "중국 공급망은 기적", 중국 AI 모델 칭찬, 중국 개발자 150만 명(33)
2. 2025-07 CCTV 「面对面」 인터뷰(33 비고)
3. 2026-01 춘절 전 상하이·베이징·선전 방문, 시장에서 과일 사고 홍바오(52)
4. 중국 전용 제품의 연대기 — RTX 4090D(12,999위안), H20, H200 승인 보도와 字节跳动·阿里巴巴·腾讯(7, 53)
5. 중국 자동차 기업과 협력 — BYD·지리(55)
6. 중국 매출 비중 변화(70): 숫자로 담담하게
7. 황의 "95%→0%" 발언(43): 중국 매체(Global Times·Caixin)도 크게 다룬 소재. 정책 비판 대목은 빼고 "중국은 세계 2위 컴퓨터 시장"이라는 황의 평가 위주

---

## 6. 1~3편 정정·보강 표 (중국어판 1~3편 번역 시 반영)

| 편 | 원고 표현 | 문제 | 정정·권장 | 근거 | 확인 |
|---|---|---|---|---|---|
| 1편 | "올해만 주가가 230%가량 폭등", "창업 30년 만에 1조 클럽" | 2023년 기준 표현. 지금 보면 "올해"가 2023년임이 불분명 | "2023년 한 해에만" 으로 연도 명시 | — | 표현 정정 |
| 1편 | "스탠포드대학원 박사 과정까지 밟는" | 젠슨 황은 스탠퍼드 **전기공학 석사**(1992). 박사 과정 아님 | "스탠퍼드대 대학원 석사" | 엔비디아 공식 프로필(nvidia.com 이사회 소개, 이번 조사에서 원문 미열람) / 다수 전기 | 확인 필요(공식 프로필 재확인 권장) |
| 1편 | "대만 타이난시에서 태어납니다" | 중국판 표기 문제 | 중국판: "出生于中国台湾台南" | 심의 관행 | 표기 정정 |
| 1편 | "미국 반도체 1위 기업" | 낡음 | 지금은 "세계 시가총액 1위를 다투는 기업"(2026-10-30 애플에 1위 내줌, 66) | 66번 | 확인 |
| 2편 | "세가 새턴의 투자를 받을", "세가 새턴을 설득하여", "세가 새턴이 먼저 포기" | 회사(세가)와 게임기(새턴)를 섞어 씀 | "세가(Sega)", 게임기는 "새턴" | 일반 사실 | 확인 |
| 2편 | "NV1은 가속 컴퓨팅의 최초의 사례로 기록" | 근거 불명, 과장 | 삭제 또는 "엔비디아는 NV1을 가속 컴퓨팅의 출발점으로 소개한다" | 미확인 | 미확인 |
| 2편 | "그래픽 카드는 GPU 시장을 독점해 가기 시작" | 2000년대 ATI와 경쟁 중이었음(3편 본인 서술과 충돌) | "선두를 다투기 시작" | 3편 내용 | 표현 정정 |
| 3편 | "2023년 세상을 놀라게 하는 AI가 등장… 챗GPT" | 챗GPT 공개는 **2022-11-30** | "2022년 11월 말 공개된 챗GPT가 2023년 세상을 흔들었다" | OpenAI 발표(2022-11-30) | 확인 |
| 3편 | "챗GPT를 훈련시켰던 것이 엔비디아의 V100" | 마이크로소프트가 오픈AI용으로 만든 애저 슈퍼컴퓨터는 **A100** 수만 개(2023-03 블룸버그·MS 블로그). V100은 그 이전 GPT-3 계열 | "엔비디아 A100 수만 개로 만든 마이크로소프트 슈퍼컴퓨터에서 훈련" | [TechSpot(Bloomberg)](https://www.techspot.com/news/97919-chatgpt-possible-due-tens-thousands-nvidia-gpus-which.html), [Digital Trends](https://www.digitaltrends.com/computing/microsoft-explains-thousands-nvidia-gpus-built-chatgpt/) | 확인 |
| 3편 | "시장조사업체 딜로이트에 따르면 AI 반도체 시장의 97%" | 딜로이트 원 자료 확인 불가. 당시 흔히 인용된 수치는 80~95% | 중국판에서는 삭제하거나 "업계 추정 80% 이상" | 3편 메모에도 "80% 이상" 국내 기사 존재 | 미확인 |
| 3편 | "2023년 6월 13일 종가 1조… 미국 기업 중 7번째로 1조 클럽" | 6/13 종가 1조 날짜·"7번째" 순번 모두 이번 조사에서 1차 출처 확인 못 함(첫 종가 1조가 2023-06이라는 것은 로이터 확인) | "2023년 6월 처음으로 종가 기준 시총 1조 달러" 로 완화. 순번은 빼기 | [Reuters 전재(Investing)](https://www.investing.com/news/stock-market-news/nvidia-becomes-first-company-to-clinch-4-trillion-in-market-value-4128409), [Fortune 5/30](https://fortune.com/2023/05/30/nvidia-hits-trillion-dollar-mark) | 부분 확인 |
| 3편 | "2023년 8월 월가 목표주가 750달러 이상" | 분할 전 가격. 지금 주가(200달러대)와 비교하면 오해 | 중국판: "按拆股前价格计算 750 美元(相当于拆股后 75 美元)" | 14·18번(10대1 분할) | 확인 |
| 3편 | "2023년 한해동안 200프로가 넘게" | 8월 시점 표현. 2023년 연간 상승률은 이번 조사에서 1차 출처 확인 못 함 | "2023년 들어 8월까지 200% 넘게" 또는 연간 수치 재확인 후 사용 | — | 미확인(연간값) |
| 3편 | "2017년 암호화폐 붐… 엔비디아는 이때를 기회로 채굴용 제품(CMP)을 출시" → "2018년 1월 규제… 과잉 재고" | 순서 오류. 2018년 과잉 재고는 일반 게임 GPU 재고. **CMP는 2021년 2월** 발표 | "2018년 채굴 붐이 꺼지며 재고가 쌓였고(숙취), 2021년 다시 붐이 오자 채굴 전용 CMP를 따로 내놓았다" | 엔비디아 블로그 2021-02-18 CMP 발표(이번 조사에서 원문 미열람) | 확인 필요 |
| 3편 | "2018년 1월 규제가 발표되면서 암호화폐 시장 빙하기" | 어느 나라 규제인지 불명확(한국·중국 규제가 섞여 있음) | 중국판에서는 "2018年加密货币市场降温" 으로 원인 생략 | — | 표현 정정 |
| 3편 | "엔비디아의 위기… 2000년대 이후 닷컴버블로 주가 90% 폭락" | 시점 대략적(2000~2002). 큰 틀은 맞음 | "2002년 전후 고점 대비 약 90% 하락"으로 시점 명시 | 3편 메모 차트 출처(블로그) | 부분 확인 |
| 3편 | "세계 시장에서 GPU 공급의 90%" (메모 부분) | 본문 미사용 메모. 사용 시 출처 필요 | 사용하지 말 것 | — | 미확인 |
| 3편 | "잰슨" | 표기 흔들림(1편 "젠슨") | "젠슨"으로 통일 | — | 표현 정정 |

---

## 7. 4편 구성안 초안 (10~12분, 6장)

**가제**: 한국판 「엔비디아 4편 — 5조 달러의 왕좌」 / 중국판 「英伟达（四）：从1万亿到5万亿美元」

| 장 | 길이 | 한국판 내용 | 중국판 처리 | 핵심 원장 번호 |
|---|---|---|---|---|
| 오프닝 | 0:40 | 3편 마지막(2023-06 시총 1조) 회상 → "그 뒤 2년 4개월 만에 5조 달러". 분기 매출 135억 → 962억 달러 그래프 예고 | 공용 | 4, 45, 60 |
| 1장. 없어서 못 파는 칩 | 1:40 | H100 품귀("마약보다 구하기 어렵다"), 매출이 한 분기 만에 88% 증가, 데이터센터가 매출의 대부분이 됨. 쿠다 생태계가 왜 해자인지(2편 쿠다 2006 연결) | 공용(머스크 "마약" 비유 → "一卡难求"로 교체) | 1~4, 6, 10, 71 |
| 2장. 2조·3조, 그리고 세계 1위 | 1:50 | 2024년 2조(3월)·3조(6월)·세계 1위(6/18), 10대1 주식분할, 다우지수에서 인텔을 밀어냄(1편 다윗·골리앗 회수), 소버린 AI | 공용(대만 "나라" 발언·컴퓨텍스 장면은 넣지 않음) | 9, 12, 14, 17~19, 23 |
| 3장. 블랙웰과 1년 주기 | 1:50 | 블랙웰 발표(2,080억 트랜지스터), 설계 결함과 "100% 우리 잘못", 1년 주기 로드맵(블랙웰 울트라→루빈→루빈 울트라→파인만, 과학자 이름 이야기), CES 2026 루빈 생산 | 공용 | 13, 16, 20, 28, 51, 55 |
| 4장-K. 규제의 벽과 롤러코스터 **(한국판 전용)** | 2:00 | 수출 규제 연대기(A800/H800 → H20 → H20 중단 45억 달러 비용 → 15% 조건 재개 → H200 25%), 중국 매출 비중 17%→9%, 황 "95%→0%", 화웨이 어센드 로드맵, 중국 규제기관 조사·RTX Pro 6000D 중단 보도 | — | 5, 7, 25, 29, 35~39, 43, 49, 53, 70 |
| 4장-C. 英伟达与中国市场 **(중국판 교체 장)** | 2:00 | — | 중국 전용 제품 연대기를 담담하게(4090D 12,999위안, H20, H200 승인 보도와 字节·阿里·腾讯), 2025-07 링보후이 첫 중국어 연설·"中国供应链是奇迹"·중국 개발자 150만 명, CCTV 인터뷰, 2026-01 춘절 방문(시장·홍바오·중국 직원 약 4,000명), BYD·지리 협력, 중국 매출 비중 변화는 숫자만 | 7, 33, 43(일부), 52, 53, 55, 70 |
| 5장. 딥시크 쇼크와 5조 달러 | 1:40 | 하루 5,890억 달러 증발(역대 최대) → 반년 만에 4조(7월), 5조(10/29) — "효율이 오르면 수요가 더 커진다". 5,000억 달러 주문 | 공용(딥시크는 "중국 오픈소스 모델이 세계를 놀라게 했다"는 긍정 프레임, 승패 구도 금지. 워싱턴 GTC 장소는 생략) | 22, 26, 32, 44, 45 |
| 6장. 칩 회사에서 AI 제국으로 / 흔들리는 왕좌 | 2:00 | 투자·인수: 인텔 50억 달러(경쟁사의 주주가 됨), 오픈AI 1,000억 LOI → 300억으로 축소, 앤트로픽 최대 100억, 그록 200억, 허깅페이스 129억. 경쟁: AMD–오픈AI 6GW, 구글 TPU. 2026: 5.71조 최고치 → 두 달 1조 증발 → 6조 문턱(10/6) → 10/30 애플에 1위 내줌. 최근 분기 962억 달러, 11/17 다음 실적 | 공용(트럼프 방중 동행은 중국판에서 "随美国企业家代表团访华" 한 줄 또는 생략, 51% 규칙·밀수·스파이 보도는 양판 모두 제외 권장) | 40~42, 46, 48, 50, 54, 57~60, 62~64, 66, 69 |
| 엔딩 | 0:30 | "게임 그래픽카드에서 세계 AI의 엔진으로. 다음 장은 11월 17일 실적과 루빈이 쓴다" | 공용 | 69 |

합계 약 11분 50초(장당 내레이션 기준, 편집 여유 포함 10~12분).

**제작 메모**
- 4편 공개 시점이 2026-11-17 이후라면 FY27 3분기 실적(전망 1,080억 달러)을 엔딩에 반영하고 원장 69번을 갱신할 것.
- 중국판은 한국판 4장을 통째로 4장-C로 바꾸고, 나머지 장에서는 비고의 대체 서술만 반영하면 흐름이 이어지도록 설계함.
- 주가·시총은 반드시 날짜와 함께 쓰고, 분할 전 가격은 "분할 전"이라고 표시.
- 단일출처 항목(1, 2, 38, 53, 67 등)은 내레이션에 "~라고 보도됐다"를 붙일 것.

---

## 8. 추가 확인이 필요한 것 (원고 확정 전)

1. 젠슨 황 학력(스탠퍼드 석사) — 엔비디아 공식 프로필 원문 확인
2. CMP 발표일(2021-02-18) — 엔비디아 블로그 원문 확인
3. 2023-06-13 종가 1조 달러·"7번째" 순번 — 로이터 원문
4. 2023년 연간 주가 상승률 — 연말 종가 기준 1차 자료
5. 원장 61번(SB에너지 보증 1,050억 달러) — 10-Q 원문
6. 중국 반독점 조사(24·37) 최종 처분 여부
7. 2026-11-03 기준 시가총액
8. 2026-11-17 FY27 3분기 실적

---

## 추가 사실 (2026-11-04 원고 보강 때 덧붙임)

> 4편 원고 2·4장 보강용. 원장 번호와 겹치지 않게 A번호를 쓴다. 원고 주석은 〔A1〕 식.

| # | 사실 | 출처 | 확인 | 판 | 비고 |
|---|---|---|---|---|---|
| A1 | 엔비디아는 1998년 「Fahrenheit」부터 아키텍처에 과학자 이름을 붙여 왔다. 작명 이유를 공식 설명한 적은 없고, 블랙웰에 대해 황은 "완벽한 이름이라고 생각했다"고만 말함. 루빈 플랫폼은 CPU 「베라」+GPU 「루빈」으로 한 사람의 이름을 나눠 씀 | [CNBC 2025-03-13](https://www.cnbc.com/2025/03/13/nvidia-to-detail-vera-rubin-chips-at-gtc-conference.html) | 확인(단일 매체지만 사실 정리 기사) | 공용 | "왜 그 이름인지"는 회사 설명이 없으므로 원고에서 이유를 단정하지 말 것 |
| A2 | 그레이스 호퍼(1906~1992): 미국 컴퓨터 과학자·미 해군 소장. 2차대전 중 하버드 마크 I 프로그래밍, 초기 컴파일러 개발, 코볼(COBOL)의 토대 마련. 1986년 79세로 퇴역할 때 미군 최고령 현역 장교. 엔비디아 그레이스 CPU·호퍼 GPU 모두 그의 이름 | [Wikipedia](https://en.wikipedia.org/wiki/Grace_Hopper), [Wikipedia(Hopper)](https://en.wikipedia.org/wiki/Hopper_(microarchitecture)), [Georgia Tech](https://news.gatech.edu/news/2024/04/17/researchers-blazing-new-trails-superchip-named-after-computing-pioneer) | 확인 | 공용 | "최초의 컴파일러"는 출처마다 표현이 다름 → "초기 컴파일러" |
| A3 | 데이비드 블랙웰(1919~2010): 미국 수학자·통계학자. 게임이론·확률론·정보이론·통계에 기여. 1965년 흑인 학자로는 처음 미국 국립과학원 회원. UC버클리 첫 흑인 종신교수 | [Wikipedia(Blackwell 아키텍처)](https://en.wikipedia.org/wiki/Blackwell_(microarchitecture)), [CNBC(A1)](https://www.cnbc.com/2025/03/13/nvidia-to-detail-vera-rubin-chips-at-gtc-conference.html), [Quartz](https://qz.com/nvidia-ai-chips-women-scientists-rubin-hopper-ada-gpu-1851770154) | 확인 | 공용 | |
| A4 | 베라 루빈(1928~2016): 미국 천문학자. 1968년부터 안드로메다 은하 관측 등으로 은하 바깥쪽 별이 예상보다 빨리 도는 것을 보여, 눈에 보이지 않는 질량(암흑물질)의 핵심 관측 증거를 제시. 1993년 미국 국가과학훈장. 칠레의 베라 C. 루빈 천문대가 그의 이름 | [CNBC(A1)](https://www.cnbc.com/2025/03/13/nvidia-to-detail-vera-rubin-chips-at-gtc-conference.html), [Wikipedia](https://en.wikipedia.org/wiki/Vera_Rubin), [Britannica](https://www.britannica.com/biography/Vera-Rubin) | 확인 | 공용 | "암흑물질 발견자"보다 "암흑물질의 결정적 관측 증거"가 정확 |
| A5 | 리처드 파인만(1918~1988): 미국 이론물리학자. 양자전기역학 연구로 1965년 노벨 물리학상(슈윙거·도모나가와 공동) | [Wikipedia](https://en.wikipedia.org/wiki/Richard_Feynman), [Wikipedia(Feynman 아키텍처)](https://en.wikipedia.org/wiki/Feynman_(microarchitecture)) | 확인 | 공용 | 도모나가는 일본 학자 — 원고에서 공동 수상자 이름은 생략 권장 |
| A6 | 2024-10-23 덴마크 코펜하겐 행사에서 황: "블랙웰에 설계 결함이 있었다. 작동은 했지만 결함 때문에 수율이 낮았다. 100% 엔비디아 잘못이다", "TSMC가 수율 문제를 극복하고 블랙웰 생산을 놀라운 속도로 재개하도록 도왔다" (원장 #20 보강) | [heise](https://www.heise.de/en/news/Blackwell-Nvidia-s-AI-accelerator-design-flaw-fixed-thanks-to-TSMC-9992474.html) | 확인(#20 출처와 같은 보도) | 공용 | 중국판: 장소(덴마크) 무난 |
| A7 | 2025-01-27 딥시크 충격 당일 엔비디아 대변인 성명: "딥시크는 훌륭한 AI 발전이자 테스트 타임 스케일링의 완벽한 예… 추론에는 상당한 수의 엔비디아 GPU와 고성능 네트워킹이 필요하다. 이제 스케일링 법칙은 셋 — 계속되는 사전 학습·사후 학습, 그리고 새로운 테스트 타임 스케일링" (원장 #26 보강) | [CNBC](https://www.nbcnewyork.com/news/business/money-report/nvidia-calls-chinas-deepseek-r1-model-an-excellent-ai-advancement/6123436/), [TechCrunch](https://techcrunch.com/2025/01/27/nvidia-drops-600bn-off-its-market-cap-amid-the-rise-of-deepseek/), [Yahoo](https://finance.yahoo.com/news/nvidia-calls-deepseek-excellent-ai-172622804.html) | 확인 | 공용 | 같은 성명의 "수출 규제를 완전히 준수한 연산" 대목은 중국판 피할 것 |
| A8 | 블랙웰 첫 판매 분기(FY25 4분기, 2024-11~2025-01) 블랙웰 매출 **110억 달러** — CFO 해설 "회사 역사상 가장 빠른 제품 증가". 보도자료의 황 발언은 "첫 분기에 수십억 달러 판매"(원장 #27 보강) | [SEC 8-K CFO 해설](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000021/q4fy25cfocommentary.htm), [보도자료](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000021/q4fy25pr.htm) | 확인 | 공용 | |
| A9 | (재확인) 허깅페이스 인수: 2026-09-02 확정 계약 서명, 9/3 발표. 총 129.3억 달러(현금 약 119억+직원 유지 최대 약 10억). 엔비디아 "허깅페이스는 전체 AI 생태계에 열린 플랫폼으로 남고, 엔비디아 컴퓨트가 필요하지 않다". 완료(클로징) 보도는 확인 못 함 → 원고는 "인수 계약"으로(원장 #62 재확인) | [엔비디아 블로그](https://blogs.nvidia.com/blog/nvidia-to-acquire-hugging-face/), [TechCrunch](https://techcrunch.com/2026/09/03/nvidia-confirms-it-will-buy-hugging-face-for-12-9-billion/), [CNBC](https://www.cnbc.com/2026/09/03/nvidia-agrees-to-buy-hugging-face-for-almost-13-billion-ai-expansion.html) | 확인 | 공용 | |
| A10 | (재확인) 배당 0.01→0.25달러: 2026-05-18 이사회 승인, 5/20 실적 보도자료로 공개, 같은 날 자사주 800억 달러 추가(원장 #58 재확인) | [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001045810/000104581026000051/q1fy27pr.htm), [Yahoo](https://finance.yahoo.com/markets/stocks/articles/nvidia-raises-dividend-adds-80-123618331.html) | 확인 | 공용 | |
| A11 | (재확인) 2026-05-14 종가 235.74달러·시총 약 5.7조 달러 사상 최고 — 확인. 원장 #57의 "7거래일 연속 상승"은 블룸버그 제목 "7일간 20% 상승"을 옮긴 것으로, 연속 상승 일수는 확인 못 함 → 쓰지 말 것. 황의 트럼프 방중 막판 합류(트럼프가 직접 전화, 알래스카에서 에어포스원 탑승)는 확인 | [Decrypt](https://decrypt.co/379959/nvidia-hits-record-high-market-value-5-7-trillion), [CNBC 5/15](https://www.cnbc.com/2026/05/15/nvidias-trillion-dollar-run-puts-pressure-on-the-bulls.html), [CNBC 5/13](https://www.cnbc.com/2026/05/13/nvidia-says-ceo-jensen-huang-is-joining-trumps-china-trip.html) | 확인(연속 일수만 미확인) | 공용 | |
| A12 | 「순환 거래」 우려: 엔비디아–오픈AI 최대 1,000억 달러 의향서 발표 뒤, 번스타인 애널리스트 스테이시 래스곤이 투자자 메모에 "이번 일은 분명 '순환' 우려를 키울 것"이라고 씀(포춘 2025-09-28). 악시오스도 "엔비디아의 1,000억 달러 오픈AI 투자가 AI 버블 우려를 키운다"고 보도 | [Fortune 전재(Yahoo)](https://finance.yahoo.com/news/nvidia-100-billion-openai-investment-110000256.html), [Axios](https://www.axios.com/2025/09/25/nvidia-openai-investment-ai) | 확인(포춘 원문 인용 직접 확인, 악시오스는 제목만) | 공용 | 원고 귀속은 "~라는 지적이 나왔습니다" 한 번. 엔비디아가 번스타인에 "투자금은 직접 구매에 쓰이지 않는다"고 했다는 내용은 2차 요약에서만 봄 → 쓰지 말 것 |
| A13 | (#26 정정) 딥시크가 밝힌 "약 560만 달러"는 2024-12 공개한 **V3 모델 기술 보고서**의 최종 학습 1회 비용(H800 278.8만 GPU시간×시간당 2달러 가정)이며, 이전 연구·실험 비용은 빠짐. R1은 V3를 바탕으로 추가 학습한 추론 모델로, 560만 달러는 R1 학습비가 아님 | [CNBC 2025-01-30](https://www.cnbc.com/2025/01/30/chinas-deepseek-has-some-big-ai-claims-not-all-experts-are-convinced-.html), [V3 정리(ainchina)](https://www.ainchina.com/blog/deepseek-v3-deep-dive/) | 확인 | 공용 | 원장 #26 비고의 "훈련비 560만 달러(딥시크 주장)"는 V3 기준으로 읽을 것 |
| A14 | 2026-02-02 엔비디아–오픈AI 1,000억 달러 투자가 멈춰 섰다는 보도(WSJ 등)에 엔비디아 주가 하락. 같은 날 황 "1,000억 달러는 약속이 아니었다"(원장 #54 보강) | [CNBC 2026-02-02](https://www.cnbc.com/2026/02/02/nvidia-stock-price-openai-funding.html), [Fortune(#54)](https://fortune.com/2026/02/02/jensen-huang-nvidia-ceo-on-openai-investment-never-a-commitment/) | 확인(하락률은 쓰지 말 것) | 공용 | |
| A15 | 2026-10-23 애플이 장중 시총 1위에 오른 날은 아이폰 두 신모델 출시일(9to5Mac 제목 "on iPhone duo launch day")(원장 #66 보강) | [9to5Mac](https://9to5mac.com/2026/10/23/apple-overtakes-nvidia-as-most-valuable-company-in-the-world-on-iphone-duo-launch-day/) | 단일출처 | 공용 | |
| A16 | (도입 정정) 2023-06 시총 1조 달러 시점의 최근 발표 분기는 FY24 1분기(2023-02~04): 매출 71.9억 달러(전 분기 대비 +19%), 2023-05-24 발표. 135억 달러는 2023-08-23 발표된 5~7월 분기 | [SEC 8-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581023000087/q1fy24pr.htm) | 확인 | 공용 | 원고 "약 72억 달러" |
| A17 | (#11 정정) 2024-02-22 하루 시총 증가는 **약 2,770억 달러**(주가 +16%), 당시 미국 증시 한 기업 하루 최대 증가(메타 1,960억 기록 경신). 2024-07-31에 엔비디아 스스로 약 3,300억으로 다시 경신 | [Reuters 전재(Investing)](https://www.investing.com/news/stock-market-news/ai-leader-nvidia-rises-as-forecast-tops-wall-streets-lofty-goals-3310840), [Bloomberg](https://www.bloomberg.com/news/articles/2024-02-22/nvidia-to-top-meta-record-with-nearly-250-billion-value-jump) | 확인 | 공용 | #11의 2,730억(포브스)은 쓰지 말 것 |
| A18 | (#20 보강) 블랙웰 결함 보도(디인포메이션, 8/2 금요일 밤) 뒤 첫 거래일 2024-08-05: 장중 한때 약 8%·개장 전 약 13% 하락, 미국 증시 전반 급락일과 겹침. 종가 하락률(약 6.4%)은 확인 못 함 | [Quartz](https://qz.com/nvidia-stock-blackwell-ai-chip-design-flaws-production-1851613133), [SiliconANGLE](https://siliconangle.com/2024/08/04/report-design-flaw-discovery-set-delay-launch-nvidias-new-blackwell-gpus/) | 확인(종가만 미확인) | 공용 | 원고 "장중 한때 8% 가까이" |
| A19 | (#55 확인) 2026-03-16 GTC 기조연설에서 「베라 루빈 스페이스-1 모듈」(궤도 데이터센터용) 발표. 출시일은 미정 | [CNBC](https://www.cnbc.com/2026/03/16/nvidia-chips-orbital-data-centers-space-ai.html), [SiliconANGLE](https://siliconangle.com/2026/03/16/nvidia-previews-vera-rubin-space-1-module-orbital-data-centers/) | 확인 | 공용 | |
| A20 | (#54 정정) 황의 발언은 2026-02-01(일) 기자들에게 "It was never a commitment(처음부터 약속이 아니었다)", 투자는 "한 걸음씩" — WSJ의 투자 정체 보도 뒤. 주가 하락은 다음 날 2/2 | [Fortune](https://fortune.com/2026/02/02/jensen-huang-nvidia-ceo-on-openai-investment-never-a-commitment/), [CNBC 2/2](https://www.cnbc.com/2026/02/02/nvidia-stock-price-openai-funding.html) | 확인 | 공용 | 발언 장소(타이베이)는 원고에 쓰지 않음 |
| A21 | (#60 확인) FY27 2분기 GAAP 순이익 596.88억 달러(매출 962.21억). 기타 수익(보유 주식 평가이익 등) 77.73억 달러 포함 | [엔비디아 IR 보도자료](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/default.aspx) | 확인 | 공용 | |
| A22 | (#69 확인) 엔비디아 2026-10-28 공지: 11/17(화) 오후 2시(태평양시간) FY27 3분기(10/25 끝) 실적 컨퍼런스콜 | [NVIDIA Newsroom](https://nvidianews.nvidia.com/news/nvidia-sets-conference-call-for-third-quarter-financial-results-6928873) | 확인 | 공용 | |
| A23 | (원고 처리 메모) #59 "두 달 약 16%·시총 1조 달러"는 5.7조×16%≈9,100억으로 서로 맞지 않음(블룸버그 제목 "1조 달러 하락"은 고점 대비 장중 저점 기준으로 보임) → 원고에서 수치 삭제. #66 "10월 한 달 약 10%"·A15(아이폰 출시일, 단일출처)도 원고에서 삭제 | — | — | — | |
| A24 | (A18 재확인) 2024-08-05 장중 낙폭은 매체마다 엇갈림(개장 전 약 13%, 장중 약 8% 보도). 종가 약 6.4% 하락(100.45달러)은 벤진가 한 곳(날짜 표기 오류 포함) → 원고는 퍼센트 없이 "크게 떨어졌다 + 증시 전반 급락일"로 | [Quartz](https://qz.com/nvidia-stock-blackwell-ai-chip-design-flaws-production-1851613133), [Benzinga](https://benzinga.com/trading-ideas/24/08/40191855/nvidias-unexpected-35-stock-plunge-amid-chip-delay-could-set-the-stage-for-a-surprising-turn-in-sto) | 단일출처(종가) | 공용 | |
| A25 | (#1 보강) 머스크 "GPU는 마약보다 구하기 어렵다" — 2023년 5월 하순 월스트리트저널 CEO 협의회 행사 발언으로 2차 인용됨(원 영상 미확인) | #1 출처 | 단일출처 | 한국판만 | 원고 "그해 5월, 월스트리트저널이 연 행사에서 … 말했다고 합니다" |
| A26 | HBM 공급: SK하이닉스가 엔비디아의 주 HBM 공급사(카운터포인트 2025년 3분기 HBM 점유율 SK하이닉스 57%·삼성 22%). 삼성의 HBM3E 12단은 2024년 2월 첫 샘플 뒤 2025년 9월 말에야 엔비디아 품질 시험을 통과했다고 한국 매체·트렌드포스가 보도(삼성은 고객 관련 확인 불가 입장) | [TrendForce 2025-09-22](https://www.trendforce.com/news/2025/09/22/news-samsung-12h-hbm3e-reportedly-clears-nvidia-tests-after-18-month-setback-hbm4-reaches-final-phase/), [Korea JoongAng Daily](https://www.koreajoongangdaily.com/business/samsung-electronics-passes-nvidias-quality-test-for-hbm3e-chip-supply/11989896) | 확인(삼성 통과 시점은 보도 기준) | **한국판만** | 중국판에서 뺄 것 |
| A27 | 점유율 기준: IoT 애널리틱스 집계 2024년(달력 연도) 데이터센터 GPU 시장 **매출 점유율 92%**(2023년과 비슷). 출하 기준 98%(2023년, HPCwire 인용)와 구분 | [IoT Analytics](https://iot-analytics.com/leading-generative-ai-companies/), [Tom's Hardware](https://www.tomshardware.com/tech-industry/nvidia-shipped-376m-data-center-gpus-in-2023-dominates-business-with-98-revenue-share) | 단일출처(조사기관 집계) | 공용 | 원장 #72 "90% 이상"을 이것으로 대체 |
| A28 | 지포스: 블랙웰 기반 게임용 지포스 RTX 50 시리즈 2025년 초 출시. FY2026(2025-02~2026-01) 게임 매출 **160억 달러, +41%, 사상 최고** | [엔비디아 FY26 4분기 보도자료](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2026) | 확인 | 공용 | |
| A29 | H20 성능: 반도체 조사기관 트렌드포스는 H20의 연산 성능을 H100의 약 15% 수준으로 평가(FP16 148 TFLOPS 대 H100 밀집 기준 약 989) | [TrendForce 2024-01-04](https://www.trendforce.com/news/2024/01/04/news-nvidias-china-exclusive-chip-h20-to-begin-production-in-q2-by-wistron/), [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/the-tale-of-nvidias-hgx-h20-how-an-ai-gpu-became-a-political-lightning-rod) | 확인(유출 사양 기반 추정) | 한국판만(3장) | |
| A30 | 규제 명분: 2023-10-17 지나 러몬도 상무장관 "목표는 언제나 같다, 중국의 군사적 활용을 제한하는 것" | [Axios](https://www.axios.com/2023/10/17/biden-export-restrictions-ai-chips-china), [SCMP](https://www.scmp.com/news/world/united-states-canada/article/3238289/us-restricts-china-nvidias-ai-chips-hinder-beijings-military-development-expands-curbs-russia-iran) | 확인 | 한국판만(3장) | |
| A31 | 생산: 엔비디아는 칩을 설계하고 웨이퍼 생산은 TSMC 등 파운드리에 맡김(10-K "We utilize foundries, such as TSMC and Samsung") | [FY2024 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm) | 확인 | 공용 | 중국판: "台积电" 회사명만 |
| A32 | 15% 조건 평가: 미국기업연구소(AEI) 데릭 시저스 "전례가 없다… 수수료라 부르지만 매출의 15%는 전형적인 세금" — 수출세는 헌법상 금지라는 지적 | [The Hill](https://thehill.com/policy/technology/5446890-nvidia-amd-china-chip-deal/), [Fortune](https://fortune.com/2025/08/11/nvidia-amd-china-chip-sales-15-percent-unconstitutional-trump-china) | 확인 | 한국판만(3장) | |
| A33 | 딥시크 V3 학습 칩: V3 기술 보고서 "엔비디아 H800 GPU 2,048개 클러스터에서 학습"(H800은 2022년 규제 뒤 중국 시장용으로 만든 칩, 원장 #5) | [arXiv 2412.19437](https://arxiv.org/pdf/2412.19437) | 확인 | 공용 | |
| A34 | 10기가와트 규모: 황, CNBC 인터뷰(2025-09-22) "10기가와트, 대략 GPU 400만~500만 개 — 올해 한 해 동안 출하한 양과 비슷" | [CNBC](https://www.cnbc.com/2025/09/22/nvidia-openai-data-center.html), [CNBC 대담 전문](https://www.cnbc.com/2025/09/22/cnbc-transcript-nvidia-ceo-jensen-huang-openai-ceo-sam-altman-and-openai-president-greg-brockman-speak-with-cnbcs-jon-fortt-on-halftime-report-today-.html) | 확인 | 공용 | |
| A35 | 순환 금융 반박: 2025-11 말 엔비디아가 애널리스트들에게 보낸 7쪽 메모(배런스 첫 보도, CNBC 등) — 마이클 버리 등의 "순환 금융" 주장 반박. 3분기 전략 투자 약 37억 달러로 매출의 작은 부분, 투자 대상 회사들은 대부분 제3자에게서 돈을 조달, "루슨트와 달리 공급업체 금융에 기대 매출을 늘리지 않는다", 고객은 구매 후 평균 53일 안에 대금 지급 | [CNBC 2025-11-25](https://www.cnbc.com/2025/11/25/nvidia-pushes-back-on-charges-that-ai-investment-is-a-bubble.html), [Investing.com](https://uk.investing.com/news/stock-market-news/nvidia-rebuts-burrylinked-fraud-allegations-in-detailed-analyst-memo-4387091) | 확인 | 공용 | |
| A36 | 쿠다 전환 비용: 세미애널리시스(2024-12-22) AMD MI300X 대 H100 학습 벤치마크 "쿠다 해자는 여전히 살아 있다" — 공개 안정판 소프트웨어로는 MI300X의 비용 대비 학습 성능이 H100보다 낮았고, AMD 엔지니어들의 버그 수정이 있어야 격차를 좁힘. AMD의 GPU 소프트웨어는 ROCm | [SemiAnalysis](https://semianalysis.com/2024/12/22/mi300x-vs-h100-vs-h200-benchmark-part-1-training/) | 단일출처(독립 조사기관) | 공용 | |
| A37 | 매출총이익률: FY27 2분기 GAAP·비GAAP 매출총이익률 75.0% | [엔비디아 IR 보도자료](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/default.aspx) | 확인 | 공용 | |
| A38 | (A29 보강) H20의 메모리는 96GB로 H100(80GB)보다 많고, 메모리 대역폭 4.0TB/s — 연산(FP16)은 크게 낮췄지만 메모리는 넉넉해 거대 언어 모델의 답 내기(추론)에 쓰기 알맞다는 평가 | [TrendForce 2024-01-04](https://www.trendforce.com/news/2024/01/04/news-nvidias-china-exclusive-chip-h20-to-begin-production-in-q2-by-wistron/), [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/the-tale-of-nvidias-hgx-h20-how-an-ai-gpu-became-a-political-lightning-rod) | 확인(유출 사양 기반) | 한국판만(3장) | |
| A39 | (#59 재확인) 2026년 7월 초 블룸버그 분석: 엔비디아 **선행 PER 약 18배**(S&P500 20배 넘음·나스닥100 약 23배보다 낮음). 원인은 메모리·스토리지 반도체로의 투자 이동. 「생성형 AI 붐 이전」 표현은 PER이 아니라 **시가총액** 비교에 쓰인 것으로, PER 비교 기준은 원문에 없음 → 원고에서 「붐 이전 수준」 삭제, 「약 18배」만 | [Yahoo(블룸버그 인용)](https://finance.yahoo.com/markets/stocks/articles/nvidia-stock-valuation-falls-pre-132505643.html) | 확인 | 공용 | 원장 #59 비고의 "시총 2019년 이후 최저" 표현은 계속 쓰지 말 것 |
| A40 | (#55 재확인) 2026-03-16 GTC 황 원문: "right here where I stand, I see through 2027, at least $1 trillion"(블랙웰·베라 루빈). CNBC는 "구매 주문(purchase orders)", WSJ는 "판매" 기대로 전함. 1년 전 5,000억 달러는 2026년까지의 수요 | [TechCrunch](https://techcrunch.com/?p=3103020), [CNBC](https://www.cnbc.com/2026/03/16/nvidia-gtc-2026-ceo-jensen-huang-keynote-blackwell-vera-rubin.html) | 확인 | 공용 | 원고 "2027년까지 적어도 1조 달러가 보인다" |
| A41 | (A37 재확인) 매출총이익률 75.0%는 FY27 2분기(2026년 5~7월) **GAAP·비GAAP 모두** | [엔비디아 IR](https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-Second-Quarter-Fiscal-2027/default.aspx) | 확인 | 공용 | |
| A42 | (A20 재확인) 황 원문 "It was never a commitment" — 원고 "그건 처음부터 약속이 아니었습니다"는 원문 그대로의 번역 | [Fortune](https://fortune.com/2026/02/02/jensen-huang-nvidia-ceo-on-openai-investment-never-a-commitment/) | 확인 | 공용 | |
