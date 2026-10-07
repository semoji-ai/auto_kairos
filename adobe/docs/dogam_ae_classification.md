# 기법 도감 → AE 이식 1차 분류 (전체 343)

> `scripts/dogam_classify.py` 가 만든 표입니다. 규칙은 스크립트의 RENDER·PARTIAL 표 — 판단을 고칠 때는 거기를 고치고 다시 돌립니다.

## 요약

| 분류 | native | partial | render | 제외 | 합계 |
|---|---:|---:|---:|---:|---:|
| HUD·자막·포맷 | 9 | 3 | 0 | 0 | 12 |
| 감정·효과 FX | 12 | 12 | 7 | 5 | 36 |
| 구성·엔딩 | 12 | 2 | 0 | 2 | 16 |
| 배경·루프 | 5 | 14 | 3 | 5 | 27 |
| 사진·자료 처리 | 22 | 7 | 2 | 0 | 31 |
| 전환 | 19 | 19 | 4 | 0 | 42 |
| 차트·인포그래픽 | 38 | 9 | 3 | 0 | 50 |
| 카메라 | 10 | 2 | 0 | 0 | 12 |
| 캐릭터 연기 | 27 | 12 | 1 | 0 | 40 |
| 콜아웃·라벨 | 42 | 9 | 0 | 0 | 51 |
| 텍스트·타이포 | 21 | 5 | 0 | 0 | 26 |
| **합계** | **217** | **94** | **20** | **12** | **343** |

## 전체 표

| 분류 | id | 이름 | 컴포넌트 | 1차 분류 | 근거 | 상태 | 미리보기 |
|---|---|---|---|---|---|---|---|
| HUD·자막·포맷 | channel-logo-intro | 채널 로고 스탬프 인트로(구포맷) | LegacyLogoIntro | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-22 |
| HUD·자막·포맷 | hud-chapter-bar | HUD 로고 + 챕터 진행바(구 포맷) | HUD | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-55 |
| HUD·자막·포맷 | hud-dark-invert | HUD 다크 반전 | HUDDarkInvert | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-19 |
| HUD·자막·포맷 | hud-tabbed-chapter-bar | 탭형 챕터 바 HUD(사각 스케치 로고) | TabbedChapterHUD | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-18 |
| HUD·자막·포맷 | hud2-renewal | 리뉴얼 HUD(원형 로고 + 챕터 워드마크 라벨) | HUD2 | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-09 |
| HUD·자막·포맷 | paper-card-subtitles | 종이 카드 자막 + 하드 그림자 | Subtitles | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-10 |
| HUD·자막·포맷 | source-chip | 출처 칩(우하단) | SourceChip | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-12 |
| HUD·자막·포맷 | source-chip-draw-on | 출처 칩 드로우온(측정값) | SourceChipDrawOn | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-17 |
| HUD·자막·포맷 | subtitle-band-legacy | 반투명 자막 띠(구 포맷) | LegacySubtitleBand | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-16 |
| HUD·자막·포맷 | content-source-credit | '내용출처' 우하단 표기 | Main | partial | 본편 합성(여러 기법 묶음) |  | core-54 |
| HUD·자막·포맷 | era-palette-shift | 시대별 배경 팔레트 전환 | EraPalette | partial | 시대 색보정 → 효과 근사 |  | x_text-21 |
| HUD·자막·포맷 | legacy-format-v1 | 초기 포맷: 탭형 챕터바 + 세이지 연도 인터스티셜 | LegacyFormat | partial | 구 포맷 합성(여러 기법 묶음) |  | x_text-20 |
| 감정·효과 FX | anger-mark | 분노 혈관 마크 | AngerMark | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-04 |
| 감정·효과 FX | clapping-hands-foreground | 전경 박수 손 루프 | ClappingHands | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-28 |
| 감정·효과 FX | dizzy-falling-blocks | 쏟아지는 압박 블록 + 어지럼 소용돌이 | FallingBlocks | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-06 |
| 감정·효과 FX | ecg-chest-glow | 심전도 배경 + 가슴 통증 글로우 | EcgChestGlow | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-39 |
| 감정·효과 FX | eye-beam | 눈빛 대결 빔 | EyeBeam | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-11 |
| 감정·효과 FX | glow-pulse | 원형 글로우 + 링 펄스(방사광 대체) | GlowPulse | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-22 |
| 감정·효과 FX | phone-ring | 전화벨 '따르릉' | PhoneRing | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-12 |
| 감정·효과 FX | rival-beam | 라이벌 전기 빔 · 전기 크랙 | RivalBeam | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-10 |
| 감정·효과 FX | sparkle-twinkle | 4각 별 반짝이 | Sparkles | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-21 |
| 감정·효과 FX | surprise-lines | 놀람 삐침선 | SurpriseLines | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-04 |
| 감정·효과 FX | sweat-drop | 땀방울 루프 | SweatDrop | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-41 |
| 감정·효과 FX | wind-lines | 바람선 스크리블 | WindLines | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-24 |
| 감정·효과 FX | burden-ballchain-slam | 족쇄 쇳덩이 슬램 | BurdenBallChain | partial | 사슬 물리 |  | x_acting-36 |
| 감정·효과 FX | cloud-bubble | 구름 생각 말풍선 | CloudBubbles | partial | 구름 풍선 보일링 |  | characters-05 |
| 감정·효과 FX | color-drain-desaturate | 컬러 드레인(점진 흑백화) | ColorDrain | partial | 채도 빠짐 → Tint 키 |  | x_acting-35 |
| 감정·효과 FX | concentric-dark-pulse | 동심원 암흑 펄스 | ConcentricDarkPulse | partial | 동심원 펄스(도형 다수) |  | x_acting-32 |
| 감정·효과 FX | confetti | 색종이 버스트 | Confetti | partial | 입자 40개 키 굽기(무거움) |  | core-34 |
| 감정·효과 FX | flower-particles | 꽃 파티클 팝 | FlowerParticles | partial | 입자 루프 |  | x_acting-26 |
| 감정·효과 FX | idea-warm-bloom | 깨달음 웜 블룸 | IdeaWarmBloom | partial | 블룸 글로우 |  | x_acting-30 |
| 감정·효과 FX | lightning | 번개(만화 윤곽 · 실사 플래시) | LightningFlash | partial | 번개 절차 도형 |  | backgrounds-15 |
| 감정·효과 FX | steam | 김(steam) 루프 | Steam | partial | 김 루프 → 도형 키 굽기 |  | core-29 |
| 감정·효과 FX | tech-aura | 홀로그램 테크 오라 | TechAura | partial | 글로우 절차 |  | x_acting-27 |
| 감정·효과 FX | tech-circuit-part-glow | 회로 배경 부품 발광 | TechCircuitGlow | partial | 회로 펄스 다수 |  | x_acting-37 |
| 감정·효과 FX | thought-image-blur-materialize | 떠오른 이미지 블러 물질화 | ThoughtMaterialize | partial | 생각 구름 물질화 |  | x_acting-34 |
| 감정·효과 FX | electric-vortex-spawn | 전기 소용돌이 등장 | ElectricVortexSpawn | render | 전기 소용돌이 절차 효과 |  | x_acting-31 |
| 감정·효과 FX | energy-portal-ring | 에너지 포탈 링 | ElectricVortexSpawn | render | 전기 소용돌이 절차 효과 |  | x_acting-31 |
| 감정·효과 FX | flame-sprite-loop | 불꽃 스프라이트 루프 | FlameSprite | render | 불꽃 스프라이트 |  | x_acting-23 |
| 감정·효과 FX | flood-water-rise | 홍수 수위 상승 + 줌아웃 | FloodRise | render | 물 차오름 유체 |  | x_acting-33 |
| 감정·효과 FX | glass-crack-hardcut | 유리 깨짐 크랙 오버레이 | GlassCrack | render | 유리 깨짐 파편 |  | x_acting-29 |
| 감정·효과 FX | photo-flame-eyes | 실사 사진 불꽃 눈 | PhotoFlameEyes | render | 사진 눈 불꽃 |  | x_acting-38 |
| 감정·효과 FX | sauce-pour | 소스 붓기 연출 | SaucePour | render | 소스 붓기 유체 |  | x_acting-25 |
| 감정·효과 FX | light-burst-tiltdown | 방사형 라이트 버스트 + 틸트다운 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 감정·효과 FX | manga-focus-lines | 만화 집중선 배경 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 감정·효과 FX | manga-speedline-rage-bg | 만화 집중선 분노 배경 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 감정·효과 FX | radial-speedline-burst | 보라 집중선 버스트 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 감정·효과 FX | throne-starburst-glow | 왕좌 뒤 금색 스타버스트 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 구성·엔딩 | bookshelf-series-spines | 백과사전 책장 시리즈 리캡 | BookshelfRecap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-21 |
| 구성·엔딩 | chapter-card | 챕터카드 | ChapterCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-51 |
| 구성·엔딩 | credits-crowd-endcard | 등장인물 군상 크레딧 | CrowdCreditCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-22 |
| 구성·엔딩 | end-card | 엔드카드(세이지 그린) | EndCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-53 |
| 구성·엔딩 | filmstrip-recap | 필름스트립 리캡 · 회상 마퀴 | FilmStrip | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-49 |
| 구성·엔딩 | gameshow-door-reveal | 게임쇼 번호문 순차 공개 | GameshowDoors | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-20 |
| 구성·엔딩 | logo-sting | 로고 스팅 | StingCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-52 |
| 구성·엔딩 | narrator-silhouette-interrupt | '잠깐!!' 내레이터 실루엣 끼어들기 | NarratorInterrupt | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-24 |
| 구성·엔딩 | ots-silhouette-foreground | 어깨너머 검정 실루엣 전경 | OTSSilhouette | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-23 |
| 구성·엔딩 | patron-credit-ending | 후원자 크레딧 엔딩(군중 프레임 + 두루마리) | CrowdCreditCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-22 |
| 구성·엔딩 | typewriter-interstitial | 세이지 타자 인터스티셜 | TypeCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-43 |
| 구성·엔딩 | word-card | 단어 카드(짧은 인터스티셜) | WordCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-17 |
| 구성·엔딩 | intro-montage | 실사 클립 몽타주 인트로 | IntroMontage | partial | 몽타주 합성 |  | x_transitions-18 |
| 구성·엔딩 | outro-recap-sequence | 아웃트로 리캡 구성 | OutroRecap | partial | 리캡 합성 |  | x_transitions-19 |
| 구성·엔딩 | layer-accumulation-pacing | 씬 안 레이어 누적 리듬 |  | 제외 | Remotion 구현 없음(분석만) |  |  |
| 구성·엔딩 | voice-sync-pop | 단어 싱크 팝 |  | 제외 | Remotion 구현 없음(분석만) |  |  |
| 배경·루프 | lantern-sway | 등롱 흔들림 | LanternSway | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-19 |
| 배경·루프 | lightning-versus-split | 번개 지그재그 대결 분할 | LightningVersusSplit | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-27 |
| 배경·루프 | pattern-bg | 구름문양·물결 패턴 배경 | CloudBg | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-24 |
| 배경·루프 | sparkle-dots | 반짝이 점 명멸 | SparkleDots | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-20 |
| 배경·루프 | tonal-wordmark | 톤온톤 대형 워드마크 배경 | TonalWordmark | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-18 |
| 배경·루프 | bokeh-drift | 보케 드리프트 | BokehDrift | partial | 보케 입자 |  | backgrounds-05 |
| 배경·루프 | cloud-drift | 구름 흐름 배경 | CloudDrift | partial | 구름 루프 |  | backgrounds-09 |
| 배경·루프 | code-scroll | 대각선 코드 스크롤 | CodeScroll | partial | 코드 텍스트 스크롤(텍스트 레이어 가능) |  | backgrounds-04 |
| 배경·루프 | crowd-bokeh | 공연장 군중 + 무대 보케 | CrowdBokeh | partial | 보케 입자 |  | backgrounds-08 |
| 배경·루프 | flag-wave | 깃발 펄럭임 · 교체 | FlagWave | partial | 깃발 물결 → Wave Warp 근사 |  | backgrounds-16 |
| 배경·루프 | hypnotic-spiral-bg | 최면 나선 배경 | RippleRingsBg | partial | 파문 링 배경 |  | x_media-28 |
| 배경·루프 | hypnotic-swirl-bg | 최면 스윌 배경 | RippleRingsBg | partial | 파문 링 배경 |  | x_media-28 |
| 배경·루프 | matrix-rain | 매트릭스 숫자 비 | MatrixRain | partial | 문자 비 절차 |  | backgrounds-01 |
| 배경·루프 | money-rain | 돈비(지폐·금화 낙하) | MoneyRain | partial | 입자 루프 |  | backgrounds-03 |
| 배경·루프 | repeat-object-wallpaper | 반복 오브젝트 벽지 배경 | RepeatObjectWallpaper | partial | 반복 배치 |  | x_media-21 |
| 배경·루프 | sky-gradient-ascent | 하늘 그라디언트 고도 상승 | SkyGradientAscent | partial | 하늘 그라디언트 → 램프 |  | x_media-25 |
| 배경·루프 | snowfall-loop | 눈 내림 파티클 루프 | SnowfallLoop | partial | 입자 루프 |  | x_media-26 |
| 배경·루프 | spotlight-cone-fog | 스포트라이트 원뿔 + 안개 무대 | SpotlightCone | partial | 빛 원뿔 그라디언트 |  | backgrounds-06 |
| 배경·루프 | static-grain-paper | 정적 그레인 · 종이 질감 | Grain | partial | 필름 그레인 → Noise 효과 근사 |  | core-26 |
| 배경·루프 | fire-background-loop | 분노 불꽃 배경 루프 | FireBgLoop | render | 불꽃 배경 루프 |  | x_media-23 |
| 배경·루프 | hypno-spiral-bg | 최면 소용돌이 배경 | SpiralTunnelBg | render | 나선 터널 셰이더 |  | x_media-22 |
| 배경·루프 | hypno-spiral-suck | 최면 나선 배경 + 소용돌이 흡입 | SpiralSuck | render | 나선 흡입 왜곡 |  | x_media-24 |
| 배경·루프 | pie-badge-rays | 정적 파이 뱃지 + 광선 링 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 배경·루프 | radial-rays-bg | 방사형 광선·집중선 배경 | Rays | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 배경·루프 | radial-sunburst-bg | 방사 선버스트 배경(주황) |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 배경·루프 | radial-sunburst-logo | 방사 광선 로고 배경 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 배경·루프 | winner-rays | 승자 방사광 |  | 제외 | 금지 기법(방사형 광선 계열) |  |  |
| 사진·자료 처리 | archive-photo-title-band | 사료 사진 반투명 띠 제목 | ArchiveTitleBand | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-12 |
| 사진·자료 처리 | browser-graph | 브라우저 목업 + 하이퍼링크 노드 그래프 | BrowserMockup | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-13 |
| 사진·자료 처리 | browser-shop | 브라우저 쇼핑 목업 | BrowserMockup | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-14 |
| 사진·자료 처리 | bw-photo-inset | 흑백 사진 인셋(거친 흰 비네트) | RoughPhotoInset | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-01 |
| 사진·자료 처리 | capture-scroll | 유튜브 채널 캡처 스크롤 | CaptureScroll | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-13 |
| 사진·자료 처리 | card-slide-in | 카드 슬라이드인(회전 겹침) | CardSlideIn | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-07 |
| 사진·자료 처리 | chat-parody | 역사 인물 메신저 대화 패러디 | ChatParody | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-03 |
| 사진·자료 처리 | dark-vignette-portrait | 원형 다크 비네트 인물 사진 | DarkVignettePortrait | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-02 |
| 사진·자료 처리 | doc-zoom-red-underline | 원문 문서 줌인 + 빨간 밑줄 | DocZoomUnderline | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-16 |
| 사진·자료 처리 | face-cover-box | 사진 속 얼굴 가림 박스 | FaceCoverBox | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-05 |
| 사진·자료 처리 | glow-sticker | 흰 글로우 스티커 컷아웃 | Sticker | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-14 |
| 사진·자료 처리 | insta-card | 인스타 게시물 카드 | InstaCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-17 |
| 사진·자료 처리 | logo-wall-tint-flash | 컬러 틴트 플래시(로고 월) | TintFlash | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-06 |
| 사진·자료 처리 | newspaper-slam-stack | 신문 스택 슬램 | NewspaperSlamStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-14 |
| 사진·자료 처리 | photo-frame | 컬러 테두리 사진 프레임 | PhotoFrame | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-13 |
| 사진·자료 처리 | photo-illust-composite | 실사 + 일러스트 합성 | PhotoIllustComposite | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-03 |
| 사진·자료 처리 | photo-panel-slideup | 사진 패널 슬라이드업 | PhotoPanelSlideUp | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-08 |
| 사진·자료 처리 | photo-pop | 원형·사진 팝(줌블러) | CircleImg | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-15 |
| 사진·자료 처리 | pillarbox-archive | 4:3 아카이브 필러박스 | Pillarbox | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-12 |
| 사진·자료 처리 | screenshot-carousel | 스크린샷 컨베이어 캐러셀 | ScreenshotCarousel | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-16 |
| 사진·자료 처리 | screenshot-grid | 스크린샷 카드 그리드 | ScreenshotGrid | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-15 |
| 사진·자료 처리 | white-stroke-archive-cutout | 흰 윤곽선 흑백 인물 컷아웃 + 로고·왕관 | WhiteStrokeCutout | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_media-09 |
| 사진·자료 처리 | archival-ad-on-paper | 실사 광고 클립 종이 배경 삽입 | ArchivalAdOnPaper | partial | 종이 질감 합성 |  | x_media-18 |
| 사진·자료 처리 | blur-fill-photo | 블러 복제 배경 사진 | BlurFillPhoto | partial | 블러 복제 배경 |  | backgrounds-10 |
| 사진·자료 처리 | boarding-pass-drop | 탑승권 소품 드롭 | BoardingPassDrop | partial | 종이 낙하 흔들림 |  | x_media-10 |
| 사진·자료 처리 | brush-mask-portrait-quote | 붓자국 마스크 인물 + 손글씨 타자 인용 | BrushMaskQuote | partial | 붓 마스크 → Trim 근사 |  | x_media-17 |
| 사진·자료 처리 | bw-past-person | 과거 인물 즉시 흑백화 | InstantMono | partial | 흑백 → Tint 키 |  | x_media-04 |
| 사진·자료 처리 | card-swipe-montage | 카드 결제 몽타주 | CardSwipeMontage | partial | 카드 3D 스와이프 |  | x_media-15 |
| 사진·자료 처리 | pixelate-avatar | 픽셀화·글리치 아바타 | PixelateAvatar | partial | 픽셀화 → Mosaic 효과 |  | backgrounds-14 |
| 사진·자료 처리 | archive-newsreel-insert | 방송 아카이브 영상 인서트(원 로고 유지) | ArchiveNewsreel | render | 뉴스릴 필름 질감 합성 |  | x_media-13 |
| 사진·자료 처리 | xray-silhouette-reveal | 엑스레이 실루엣 투시 | XraySilhouette | render | X선 실루엣 셰이딩 |  | x_media-11 |
| 전환 | cover-slide | 커버 슬라이드 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-03 |
| 전환 | cross-dissolve | 크로스 디졸브 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-02 |
| 전환 | cyan-energy-ring-wipe | 시안 에너지 링 와이프 | CyanRingWipe | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-09 |
| 전환 | dim-cutaway-drop-exit | 딤 컷어웨이 낙하 퇴장(옵션) | BlurDimInterrupt | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | x_ref_b-06 |
| 전환 | dip-to-black | 딥 투 블랙 | DipToBlack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-10 |
| 전환 | element-slide-transition | 캐릭터·요소 슬라이드로 씬 전환 | SlideCut | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-03 |
| 전환 | elevator-door-reveal | 엘리베이터 문 열림 리빌 | ElevatorReveal | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-07 |
| 전환 | hard-cut | 하드컷 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-01 |
| 전환 | in-place-swap | 제자리 장면 교체 | InPlaceSwap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-02 |
| 전환 | magic-move | 요소 캐리오버(매직무브) | MagicMove | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-19 |
| 전환 | manga-panels | 망가 패널 플라이인 | MangaPanels | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-12 |
| 전환 | parallax-push | 패럴랙스 푸시 | ParallaxPush | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-15 |
| 전환 | smoke-wipe | 만화 연기 전환 | SmokeWipe | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-33 |
| 전환 | split-panel-wipe | 좌우 분할 패널 와이프 | SplitPanelWipe | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-13 |
| 전환 | vertical-push | 수직 푸시 | VerticalPush | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-14 |
| 전환 | whip-pan | 휩 전환(방향 블러) | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-01 |
| 전환 | white-dip | 화이트 딥(종이색 경유·노출인) | WhiteDip | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | transitions-09 |
| 전환 | zipper-close-transition | 지퍼 잠금/열림 전환(압축 은유) | ZipperTransition | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-04 |
| 전환 | zoom-through | 줌 스루(렌즈 왜곡·색수차) | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-06 |
| 전환 | arc-wipe-iris | 초승달 와이프 + 원형 리빌 | ArcWipeIris | partial | 호 와이프 마스크 |  | transitions-06 |
| 전환 | card-flip-y | Y축 3D 카드 플립 | Signboard | partial | 간판 Y축 카드 플립(3D 레이어) |  | core-50 |
| 전환 | color-flicker-leak | 컬러 플리커 라이트릭 | FlickerLeak | partial | 빛샘 radial-gradient → 램프·블렌드 근사 |  | core-31 |
| 전환 | crash-impact-zoom-crack | 충돌 임팩트 줌 + 유리 균열 | CrashImpact | partial | 충돌 파편 |  | x_transitions-08 |
| 전환 | crt-switch | CRT 전원 OFF/ON | CRTSwitch | partial | CRT 주사선 근사 |  | transitions-02 |
| 전환 | energy-slash | 에너지 슬래시 파열 | EnergySlash | partial | 에너지 슬래시 글로우 |  | transitions-08 |
| 전환 | focus-pull | 포커스 풀 크로스페이드 | FocusPull | partial | 초점 이동 → 블러 키 |  | transitions-18 |
| 전환 | glitch-transition | 글리치·데이터모시 전환 | GlitchOverlay | partial | 글리치 → 효과 근사 |  | core-44 |
| 전환 | gradient-light-wash | 파스텔 그라디언트 광원 워시 | GradientLightWash | partial | 그라디언트 빛 → 램프 근사 |  | x_transitions-06 |
| 전환 | grayscale-beat | 전체 흑백 비트 | GrayscaleBeat | partial | 흑백 → Tint 키 |  | transitions-17 |
| 전환 | iris-feather | 페더 원형 아이리스 리빌 | IrisFeather | partial | 페더 아이리스 마스크 |  | transitions-07 |
| 전환 | magazine-flip | 잡지 표지 3D 넘김 | MagazineFlip | partial | 책장 넘김 3D |  | transitions-05 |
| 전환 | newspaper-pullout | 장면→신문 풀아웃 | NewspaperPullout | partial | 신문 3D 회전 |  | transitions-04 |
| 전환 | orange-flare | 오렌지 플레어(부드러운 라이트릭) | OrangeFlare | partial | 플레어 → 그라디언트 근사 |  | transitions-11 |
| 전환 | pink-color-wash | 핑크 컬러 워시 디졸브 | PinkColorWash | partial | 컬러 워시 블렌드 |  | x_transitions-01 |
| 전환 | rack-defocus-drop-exit | 디포커스 레이어 낙하 퇴장(옵션) | RackDefocus | partial | 디포커스 → 블러 키 |  | x_ref_b-07 |
| 전환 | slat-mosaic | 세로 슬랫 모자이크 리빌 | SlatMosaic | partial | 슬랫 모자이크 → 도형 반복 |  | transitions-03 |
| 전환 | theater-curtain | 극장 커튼 | TheaterCurtain | partial | 커튼 주름 → 도형 근사 |  | transitions-01 |
| 전환 | yellow-burst | 노란 번(라이트릭 번) | YellowBurst | partial | 번짐 radial-gradient → 램프 근사 |  | core-32 |
| 전환 | fire-transition | 불꽃 전환 | FireTransition | render | 불꽃 전환 |  | transitions-16 |
| 전환 | ink-blob-burst-reveal | 먹물 방울 흩어짐 리빌 | InkBlobReveal | render | 잉크 번짐 마스크 |  | x_transitions-11 |
| 전환 | spectral-tilt-zoomthrough | 스펙트럼 틸트 줌스루(날짜카드 탈출) | SpectralZoomThrough | render | 스펙트럼 줌 셰이더 |  | x_transitions-10 |
| 전환 | twirl-liquid-transition | 트월 리퀴드 전환(RGB 분리) | TwirlLiquid | render | 소용돌이 액체 변형 |  | x_transitions-05 |
| 차트·인포그래픽 | agile-rings | 반복 링 + 무지개 화살표 | AgileRings | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-16 |
| 차트·인포그래픽 | alternating-photo-timeline | 교차 사진 타임라인 | AlternatingPhotoTimeline | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-22 |
| 차트·인포그래픽 | avatar-pop | 인원수 증가 아바타 | AvatarPop | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-45 |
| 차트·인포그래픽 | bar-chart-h | 가로 막대그래프 빌드 | BarChartH | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-03 |
| 차트·인포그래픽 | bar-chart-v | 세로 막대그래프 + 리본 헤더 + 마스코트 | BarChartV | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | charts-04 |
| 차트·인포그래픽 | bar-end-icon-pop | 막대 끝 아이콘 팝(옵션) | BarChartV | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-08 |
| 차트·인포그래픽 | bar-end-icon-pop-h | 가로 막대 끝 아이콘 팝(옵션) | BarChartH | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-09 |
| 차트·인포그래픽 | bottom-up-rank-stack | 역순 순위 리스트 적층 | BottomUpRankStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-12 |
| 차트·인포그래픽 | corp-lineage-flow | 기업 계보 플로차트 | CorpLineageFlow | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-19 |
| 차트·인포그래픽 | counter-badge | 알림 배지 카운터 + 원→필 확장 | CounterBadge | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-11 |
| 차트·인포그래픽 | dashed-column-compare | 점선 세로 구분 N열 비교(대상 성장) | DashedColumnCompare | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-02 |
| 차트·인포그래픽 | dday-calendar-equation | D-DAY 달력 → 화살표 → 산출량 공식 | DDayEquation | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-05 |
| 차트·인포그래픽 | device-tessellation-fill | 기기 외곽 타일 채움 | DeviceTessellation | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-06 |
| 차트·인포그래픽 | election-poster-drop-rank | 포스터 드롭 + 순위 필 | ElectionPosterDropRank | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-20 |
| 차트·인포그래픽 | esports-vs-scoreboard | 대진 배너 + 7세그 스코어보드 | EsportsVsScoreboard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-13 |
| 차트·인포그래픽 | fin-table-row-append | 연도 실적표 행 추가 + 적자/흑자 배지 | FinTableRowAppend | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-24 |
| 차트·인포그래픽 | globe-pie-sweep | 지구본 → 파이 스윕 | PieSweep | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-02 |
| 차트·인포그래픽 | hand-held-document-lineup | 손에 든 서류 순차 라인업(견적 비교) | HandHeldDocLineup | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-15 |
| 차트·인포그래픽 | line-chart-draw | L축 드로우 선그래프 | LineChart | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-05 |
| 차트·인포그래픽 | line-chart-fade-crowd | 딤 위 꺾은선 차트 + 군중 실루엣 | LineChart | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-06 |
| 차트·인포그래픽 | mascot-step-bars | 로고 마스코트 + 계단식 막대 + 카메라 트럭 | MascotStepBars | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-01 |
| 차트·인포그래픽 | pie-sweep | 파이차트 웨지 스윕 | PieSweep | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-01 |
| 차트·인포그래픽 | podium | 포디움 랭킹 상승 | Podium | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-07 |
| 차트·인포그래픽 | product-anchor-value-pill | 제품 앵커 수치 필 + 수요/공급 바 | ProductAnchorValuePill | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-10 |
| 차트·인포그래픽 | proportion-ruler-road | 도로 비율 눈금자 채움 | ProportionRulerRoad | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-16 |
| 차트·인포그래픽 | record-milestone-badge | 기록 달성 원형 배지 스텝업 | RecordMilestoneBadge | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-07 |
| 차트·인포그래픽 | road-lane-analogy | 비유 애니메이션(도로 차선 증가) | RoadLaneAnalogy | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-03 |
| 차트·인포그래픽 | segmented-thermometer-drain | 세그먼트 온도계 배출 | SegmentedThermometerDrain | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-14 |
| 차트·인포그래픽 | silhouette-rival-price-compare | 회색 실루엣 경쟁품 + 가격표 비교 | SilhouettePriceCompare | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-04 |
| 차트·인포그래픽 | split-flag-exchange | 분할 국기 교환 화살표 | SplitFlagExchange | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-21 |
| 차트·인포그래픽 | stat-gauge | 게임식 능력치 게이지 | StatGauge | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-12 |
| 차트·인포그래픽 | tictactoe-win-line | 틱택토 승리선 | TicTacToeWin | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-02 |
| 차트·인포그래픽 | timeline-bar | 연도 타임라인 바 | TimelineBar | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-08 |
| 차트·인포그래픽 | tunnel-section-length-compare | 터널 단면 길이 비교(먼지 스폰) | TunnelLengthCompare | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-17 |
| 차트·인포그래픽 | vs-boxing-gloves | VS 로봇팔 복싱 글러브 | VsBoxingGloves | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_charts-23 |
| 차트·인포그래픽 | waterfall-stairs | 폭포수 계단 다이어그램 + 마스코트 호핑 | WaterfallStairs | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-13 |
| 차트·인포그래픽 | zigzag-arrow-down | 하락 화살표 + 번개 섬광 | ZigzagArrow | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-10 |
| 차트·인포그래픽 | zigzag-arrow-up | 지그재그 성장 화살표 | ZigzagArrow | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-09 |
| 차트·인포그래픽 | brush-arrow-route | 붓 화살표 항로(옵션) | MapRoute | partial | 지도 배경 프리렌더 |  | x_ref_b-10 |
| 차트·인포그래픽 | candlestick-growth | 캔들차트 순차 성장 + 떡상 화살표 | CandlestickGrowth | partial | 캔들 다수(데이터 많음) |  | x_charts-26 |
| 차트·인포그래픽 | flag-map-stat-link | 국기 채움 지도 + 점선 연결 통계 | FlagMapStatLink | partial | 지도 프리렌더 |  | x_charts-08 |
| 차트·인포그래픽 | map-route | 지도 항로 드로우 | MapRoute | partial | 지도 배경 프리렌더 | ✅ AE 이식(partial) | core-42 |
| 차트·인포그래픽 | map-spread-pullback | 확산 풀백(아이콘 증식) + 레이더 파문 | MapSpreadPullback | partial | 지도 프리렌더 + 증식 |  | x_charts-11 |
| 차트·인포그래픽 | map-stat-overlay | 지도 전력 통계 오버레이 | MapStatOverlay | partial | 지도 프리렌더 |  | x_ref_b-04 |
| 차트·인포그래픽 | pictogram-crowd-marquee | 픽토그램 군중 행진 채움 | PictogramCrowdMarquee | partial | 픽토그램 다수 마키 |  | x_charts-09 |
| 차트·인포그래픽 | signal-wave-diagram | 신호 파형 드로우 다이어그램 | SignalWaveDiagram | partial | 파형 절차 패스 |  | x_charts-25 |
| 차트·인포그래픽 | walk-path-timeline | 인생 경로 타임라인(걷는 캐릭터) | WalkPath | partial | 걷기 사이클(리그) |  | characters-16 |
| 차트·인포그래픽 | disc-pie-3d | 3D 원판 파이 | DiscPie3D | render | 3D 원반 파이 |  | charts-15 |
| 차트·인포그래픽 | globe-spin-scatter | 회전 지구본 감속 정지 + 히트맵 + 아이콘 산포 | GlobeSpinScatter | render | 3D 지구본 회전(WebGL) |  | x_ref_b-01 |
| 차트·인포그래픽 | map-lecturer-country-fill | 지시봉 강의 + 국가 하이라이트 채움 | MapLecturerCountryFill | render | 지도 국가 채움(벡터 타일) |  | x_charts-18 |
| 카메라 | binocular-mask-pov | 쌍안경 마스크 시점 | BinocularPOV | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-16 |
| 카메라 | camera-static-default | 카메라 기본 고정 · 앞 1/3 이동 후 정지 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-07 |
| 카메라 | camera-tiltup-sign-reveal | 카메라 틸트업 표지판 리빌 | TiltUpSignReveal | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-13 |
| 카메라 | char-entry-reframe | 캐릭터 슬라이드인 + 카메라 리프레이밍 | SlideInReframe | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-18 |
| 카메라 | impact-shake | 임팩트 셰이크 | useShake | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-56 |
| 카메라 | iso-buildup-pullback | 아이소메트릭 빌드업 풀백 | IsoBuildPullback | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-15 |
| 카메라 | pan-reveal | 수평 팬 리빌 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-07 |
| 카메라 | pullback-reveal | 대형 풀백 리빌 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-07 |
| 카메라 | push-in | 푸시인 · 트럭 패닝 | Scene | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-07 |
| 카메라 | truck-pan-push-door | 가로 팬 → 문 안 인물 푸시인 | TruckPushIn | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_transitions-12 |
| 카메라 | photo-slow-zoom | 사진 슬로 줌(켄번스) | BlurFillPhoto | partial | 블러 복제 배경 |  | backgrounds-10 |
| 카메라 | rack-defocus-backdrop | 직전 장면 디포커스 백드롭 | RackDefocus | partial | 디포커스 → 블러 키 |  | x_transitions-14 |
| 캐릭터 연기 | arm-tween | 팔 1축 트윈 + 스윙 | ArmTween | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-06 |
| 캐릭터 연기 | blur-dim-interrupt | 배경 블러·딤 인터럽트 등장 | BlurDimInterrupt | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-13 |
| 캐릭터 연기 | boxing-glove-punch-swap | 권투 글러브 펀치 교체 | GlovePunchSwap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-12 |
| 캐릭터 연기 | boxing-round-rivalry | 복싱 링 라이벌 구도 + ROUND 표기 | BoxingRound | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-10 |
| 캐릭터 연기 | costume-add | 의상·소품 추가 | CostumeAdd | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-07 |
| 캐릭터 연기 | creation-hand-parody | '천지창조' 손 패러디 | CreationHand | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-15 |
| 캐릭터 연기 | crowd-rise | 군중 실루엣 상승 | CrowdRise | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-15 |
| 캐릭터 연기 | crown-knockoff | 왕관 날아감 | CrownKnockoff | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-18 |
| 캐릭터 연기 | expression-swap | 표정 스왑 | ExpressionSwap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-04 |
| 캐릭터 연기 | fade-in-accumulate | 알파 페이드 등장 · 겹쳤다 분리 | FadeAccumulate | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-03 |
| 캐릭터 연기 | finger-from-corner | 구석에서 들어오는 손가락 | FingerFromCorner | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-14 |
| 캐릭터 연기 | giant-blur-entry | 거대 블러 줌아웃 등장 | GiantBlurEntry | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-02 |
| 캐릭터 연기 | growth-pot-metaphor | 화분 성장 은유 | GrowthPot | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-17 |
| 캐릭터 연기 | hidden-silhouette | 숨은 인물 실루엣 | HiddenSilhouette | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-13 |
| 캐릭터 연기 | mallet-strike | 의사봉 내리치기 | MalletStrike | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-08 |
| 캐릭터 연기 | mascot | 제품 마스코트화(장갑 손·다리) | Mascot | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-01 |
| 캐릭터 연기 | mouth-swap | 말하는 입 교체 | MouthSwap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-01 |
| 캐릭터 연기 | pose-swap | 포즈 하드 스왑 + 효과 싱크 | PoseSwap | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-19 |
| 캐릭터 연기 | q-silhouette | 물음표 실루엣 | QSilhouette | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-27 |
| 캐릭터 연기 | random-mouth-talk | 불규칙 입 교체(옵션) | SemojiRig | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-11 |
| 캐릭터 연기 | repeat-arm-gesture | 반복 팔 동작(주먹 흔들기) | RepeatGesture | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-05 |
| 캐릭터 연기 | rise-from-behind | 소품 뒤에서 솟아오름 | Sticker | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-14 |
| 캐릭터 연기 | rival-enter | 라이벌 낙하 + 밀어내기 | RivalEnter | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-02 |
| 캐릭터 연기 | side-slide-in | 캐릭터 측면 슬라이드인 | Sticker | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-14 |
| 캐릭터 연기 | stair-promotion | 승진 계단 메타포 | StairPromotion | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | characters-17 |
| 캐릭터 연기 | sword-duel-flame-clash | 칼싸움 대결 + 스파크 클래시 | SwordDuel | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-14 |
| 캐릭터 연기 | whack-a-mole-hammer | 두더지 게임 뿅망치 개그 | WhackAMole | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_acting-11 |
| 캐릭터 연기 | blob-head-personification | 먹덩이 얼굴 의인화(부실 회사) | BlobHead | partial | 말랑 변형 |  | x_acting-21 |
| 캐릭터 연기 | extras-face-blur | 비핵심 인물 얼굴 블러 | FaceBlur | partial | 얼굴 블러(추적 없음) |  | x_acting-09 |
| 캐릭터 연기 | eye-blink | 눈 깜빡임 | LayeredCover | partial | 까딱·깜빡임 native, 패럴랙스 drift 미이식 |  | core-28 |
| 캐릭터 연기 | flip-turn | 뒷모습→앞모습 뒤집기 턴 | FlipTurn | partial | Y축 뒤집기(3D 레이어) |  | core-35 |
| 캐릭터 연기 | hop-arc | 포물선 점프 + 먼지 링 | HopArc | partial | 포물선 → 키 굽기 |  | characters-09 |
| 캐릭터 연기 | idle-bob | 아이들 까딱(바디 밥) | LayeredCover | partial | 까딱·깜빡임 native, 패럴랙스 drift 미이식 | ✅ AE 이식(partial) | core-28 |
| 캐릭터 연기 | logo-face-mask | 브랜드 로고 얼굴 가면 | LogoFaceMask | partial | 얼굴 로고 마스크 |  | characters-03 |
| 캐릭터 연기 | marionette-puppeteer | 꼭두각시 조종자 | Marionette | partial | 줄 인형 물리 |  | x_acting-20 |
| 캐릭터 연기 | rope-swing-traverse | 밧줄 건너뛰기(카메라 추적) | RopeSwing | partial | 진자 물리 → 키 굽기 |  | x_acting-16 |
| 캐릭터 연기 | smoke-swap | 연기 퍼프 캐릭터 교체 | SmokeSwap | partial | 연기 퍼프 |  | characters-07 |
| 캐릭터 연기 | teleport-smoke | 연기 순간이동 | Teleport | partial | 연기 퍼프 |  | characters-08 |
| 캐릭터 연기 | treadmill-walk-milestones | 제자리 걷기 + 이정표 트랙 | TreadmillWalk | partial | 걷기 사이클(리그) |  | x_acting-22 |
| 캐릭터 연기 | octopus-metaphor-monster | 은유 괴물 + 라벨 | OctopusMonster | render | 촉수 절차 애니메이션 |  | x_acting-19 |
| 콜아웃·라벨 | arrow-name-tag | 이름표 + 곡선 화살표 드로우 | ArrowTag | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-37 |
| 콜아웃·라벨 | big-x-strike | 대형 X 표 스트라이크 | BigXStrike | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-08 |
| 콜아웃·라벨 | calendar-tag-smoke-pop | 탁상달력 연도 태그(연기 등장) | CalendarTagSmoke | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-09 |
| 콜아웃·라벨 | callout-connector | 콜아웃 커넥터(빨간 박스 + 직각선) | CalloutConnector | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-01 |
| 콜아웃·라벨 | checklist-tick-sync | 체크리스트 순차 체크 | ChecklistTick | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-12 |
| 콜아웃·라벨 | circuit-branch | 회로선 분기 | CircuitBranch | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-03 |
| 콜아웃·라벨 | compare-ab | 비교 필 A < B | CompareAB | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-07 |
| 콜아웃·라벨 | dash-circle | 점선 원 하이라이트 | DashCircle | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-40 |
| 콜아웃·라벨 | diagonal-tape-wipe-tags | 대각 테이프 드로우 + 태그 | DiagonalTapeTags | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-14 |
| 콜아웃·라벨 | dim-underlay | 딤 언더레이(이전 장면 어둡게 유지) | DimUnderlay | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-06 |
| 콜아웃·라벨 | elbow-callout | 엘보 리더라인 + 필 라벨 | ElbowCallout | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-47 |
| 콜아웃·라벨 | feathered-smoke-speech-bubble | 연기 가장자리 말풍선(어두운 장면) | FeatheredSmokeBubble | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-11 |
| 콜아웃·라벨 | fighting-game-vs-hud | 격투게임 VS 대결 HUD | FightingVsHud | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-06 |
| 콜아웃·라벨 | game-quest-window-drop | 게임 퀘스트 창 드롭 | QuestWindowDrop | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-13 |
| 콜아웃·라벨 | hand-drawn-loop-arrow | 손글씨 루프 화살표 | LoopArrow | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-01 |
| 콜아웃·라벨 | headline-strip-stack | 기사 헤드라인 종이띠 스택 | HeadlineStripStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-19 |
| 콜아웃·라벨 | icon-pop-suck | 아이콘 순차 팝 → 흡입 퇴장 | IconPop | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-38 |
| 콜아웃·라벨 | icon-row-grid | 아이콘 행 순차 등장(그리드) | IconRowGrid | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-18 |
| 콜아웃·라벨 | label-chip-sparkle | 라벨 칩 + 반짝이 파티클 | LabelChipSparkle | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-02 |
| 콜아웃·라벨 | logo-edge-icons-gather | 로고 주위 사업 아이콘 입장 | LogoEdgeIconsGather | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-15 |
| 콜아웃·라벨 | magnifier-box | 돋보기 콜아웃 박스 | MagnifierBox | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-48 |
| 콜아웃·라벨 | medallion-bracket | 원형 메달리온 + 브래킷 선(계보도) | MedallionTree | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-22 |
| 콜아웃·라벨 | megaphone-cone-text | 확성기 원뿔 텍스트 | MegaphoneCone | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-20 |
| 콜아웃·라벨 | name-tag | 명찰(다크 박스) | NameTag | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-19 |
| 콜아웃·라벨 | numbered-reason-tab | 번호 사유 탭(좌측 도킹) | NumberedReasonTab | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-03 |
| 콜아웃·라벨 | orange-pill-stack-list | 오렌지 pill 세로 스택 목록 | OrangePillStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-05 |
| 콜아웃·라벨 | pill-arrow-pill | 필 → 화살표 → 필(상태 전이) | PillArrowPill | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-04 |
| 콜아웃·라벨 | pill-collision | 필 충돌 → 에너지 링 → 거대 글자 | PillCollision | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-05 |
| 콜아웃·라벨 | probability-pill-label | 확률 수치 pill 라벨 | ProbabilityPill | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-07 |
| 콜아웃·라벨 | product-spec-pin-callouts | 제품 스펙 핀 콜아웃 | ProductSpecPins | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_callouts-17 |
| 콜아웃·라벨 | puzzle-join | 퍼즐 조각 결합 | PuzzleJoin | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-23 |
| 콜아웃·라벨 | red-box-blink | 스크린샷 빨간 박스 깜빡임 | RedBoxBlink | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-11 |
| 콜아웃·라벨 | ribbon-banner | 리본 배너 헤더 | Ribbon | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-03 |
| 콜아웃·라벨 | scroll-label | 가로 두루마리 라벨 | ScrollLabel | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-12 |
| 콜아웃·라벨 | shield-wings | 방패 날개 펼침 엠블럼 | ShieldWings | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-20 |
| 콜아웃·라벨 | stamp-slam | 도장 슬램 + 깜빡임 | Stamp | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-16 |
| 콜아웃·라벨 | starburst-echo | 스타버스트 말풍선 에코 팝 | Starburst | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-17 |
| 콜아웃·라벨 | term-card | 용어 설명 카드 | TermCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-46 |
| 콜아웃·라벨 | tree-droplines | 트리 드롭라인 다이어그램 | TreeDroplines | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-19 |
| 콜아웃·라벨 | version-stack | 로고 버전 히스토리 스택 | VersionStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-17 |
| 콜아웃·라벨 | wipe-reveal-bubble | 와이프 리빌 말풍선(옵션) | SpeechBubble | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | x_ref_b-05 |
| 콜아웃·라벨 | year-tag | 연도 두루마리 태그 | YearTag | native | 트랜스폼·마스크·도형·텍스트 키프레임 | ✅ AE 이식(native) | core-11 |
| 콜아웃·라벨 | clipboard-swing-drop-doc | 클립보드 문서 스윙 드롭 + 줄별 리빌 | ClipboardSwingDrop | partial | 진자 흔들림 |  | x_callouts-04 |
| 콜아웃·라벨 | dotted-path-draw | 점선 직교 경로 드로우 | DottedPathDraw | partial | 점선 드로우 |  | callouts-02 |
| 콜아웃·라벨 | hand-drawn-circle | 빨간 손그림 원 | HandDrawnCircle | partial | 손그림 원 → Trim 근사(떨림) |  | callouts-12 |
| 콜아웃·라벨 | hanging-icon-drop | 매달린 아이콘 드롭(끈+리본) | HangingIconDrop | partial | 매달린 흔들림 물리 |  | x_callouts-10 |
| 콜아웃·라벨 | map-pin-portrait | 지도핀 원형 초상 | MapPin | partial | 지도 배경 프리렌더 |  | callouts-21 |
| 콜아웃·라벨 | ripple-ring-marker | 리플 링 마커(동심원 펄스) | RippleRings | partial | 파문 링(도형 다수) |  | x_callouts-16 |
| 콜아웃·라벨 | signature-ripple-rings | 서명 파문 링 | RippleRings | partial | 파문 링(도형 다수) |  | x_callouts-16 |
| 콜아웃·라벨 | spotlight-dim | 스포트라이트 딤 | Spotlight | partial | 딤 + 둥근 구멍(마스크) 근사 |  | core-36 |
| 콜아웃·라벨 | tcg-profile-card-marquee | TCG 인물 카드 마키 | TcgCardMarquee | partial | 카드 3D 마키 |  | x_callouts-18 |
| 텍스트·타이포 | blur-reveal-quote | 블러→선명 텍스트 리빌 · 인용박스 | QuoteBox | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-20 |
| 텍스트·타이포 | calligraphy-title-slam | 붓글씨 대형 타이틀 슬램 | CalligraphySlam | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-01 |
| 텍스트·타이포 | defocus-hanja-medallion | 배경 디포커스 + 한자 메달리온 | HanjaMedallion | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-14 |
| 텍스트·타이포 | echo-zoom-title | 에코 줌 타이틀 | EchoTitle | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-39 |
| 텍스트·타이포 | four-corner-char-tiles | 네 모서리 빨간 글자 타일 | CornerCharTiles | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-05 |
| 텍스트·타이포 | gradient-band-spec-label | 그라데이션 밴드 스펙 라벨 | SpecBandLabel | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-03 |
| 텍스트·타이포 | handwritten-annot | 손글씨 주석 · 리더선 라벨 | Annot | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-18 |
| 텍스트·타이포 | headline-band-slam | 헤드라인 밴드 슬램 | HeadlineBandSlam | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-12 |
| 텍스트·타이포 | line-blur-rise-definition | 정의문 줄단위 블러 상승 리빌 | DefinitionReveal | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-07 |
| 텍스트·타이포 | money-3d-title | 3D 압출 금액 타이포 + 돈더미 | MoneyTitle | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | charts-14 |
| 텍스트·타이포 | outline-text | 흰 외곽 굵은 텍스트 오버레이 | OutlineText | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | backgrounds-10 |
| 텍스트·타이포 | sage-date-typing-card | 세이지 연월 타이핑 카드 | SageDateCard | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-09 |
| 텍스트·타이포 | scrim-typewriter | 다크 스크림 + 타자기 부제 | ScrimTypewriter | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-09 |
| 텍스트·타이포 | slogan-slash-banner | 사선 구호 배너 | SloganBanner | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-15 |
| 텍스트·타이포 | stacked-fact-pills | 네이비 팩트 필 스택 | FactPillStack | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-11 |
| 텍스트·타이포 | text-behind-character | 인물 뒤 대형 수치 + 불꽃 | TextBehindCharacter | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-13 |
| 텍스트·타이포 | text-pop | 텍스트 팝(크게→작게) · 의성어 | Onoma | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | core-30 |
| 텍스트·타이포 | tilted-stamp-hold | 기울어진 도장 유지(옵션) | Stamp | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_ref_b-12 |
| 텍스트·타이포 | title-box-center-out | 제목 박스 center-out 리빌 | TitleBox | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | callouts-08 |
| 텍스트·타이포 | title-strip-flyoff | 직함 떼어 날리기 | TitleStripFlyoff | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-04 |
| 텍스트·타이포 | year-chip-rapid-roll | 연도 칩 고속 롤 + 라인업 몽타주 | YearChipRoll | native | 트랜스폼·마스크·도형·텍스트 키프레임 |  | x_text-08 |
| 텍스트·타이포 | brush-title-blur-in | 붓글씨 헤드라인 블러 인 | BrushHeadline | partial | 붓 마스크 → Trim 근사 |  | x_text-10 |
| 텍스트·타이포 | glow-cloud-text | 흰 글로우 구름 텍스트 | GlowCloudText | partial | 글로우 구름 글자 |  | x_text-02 |
| 텍스트·타이포 | neon-letter-tiles | 네온 글자 타일 슬램 | NeonTiles | partial | 네온 글로우 |  | callouts-06 |
| 텍스트·타이포 | repeated-word-wallpaper | 반복 단어 월페이퍼 | WordWallpaper | partial | 반복 텍스트 벽지 |  | x_text-06 |
| 텍스트·타이포 | whiteboard | 화이트보드 필기 | Whiteboard | partial | 손글씨 드로잉 → Trim Paths 근사 |  | callouts-10 |
