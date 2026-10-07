# 세모지 연출 규칙(여러 레퍼런스 참고) — AE 편집 운영 규칙

이 문서는 Auto Kairos 프로젝트를 **다른 macOS 컴퓨터의 After Effects**에서 이어 편집할 때 쓰는 연출 기준이다. 기법의 출처는 `adobe/data/semoji-motion/dogam/techniques.json`, 실제 AE 적용 범위는 `adobe/cep/com.autokairos.pd/jsx/dogam/registry.json`이 정한다. 도감의 343개는 참고 항목이며, 현재 패널에서 바로 적용되는 것은 12개다. `status: 구현`은 AE 구현을 뜻하지 않는다.

## 프로젝트를 여는 순서

1. Git으로 코드를 받고 `output/<project>/` 전체와 참조하는 `output/_series/` 등 공유 에셋을 옮긴다. 이미지·음성은 Git만으로 이동하지 않는다. 옛 컴퓨터의 절대 경로는 연결 기준이 아니다.
2. AE가 설치된 컴퓨터에서 필요한 Python 의존성을 `python3 -m pip install -r adobe/requirements.txt`로 설치하고, 저장소 루트 기준 `bash adobe/scripts/setup_cep_dev.sh`를 실행한 뒤 AE를 재시작한다. `cd adobe && python3 -m backend.app`으로 패널 백엔드를 띄운다. 패널은 기본적으로 저장소 `output/`을 본다. 다른 위치라면 `AK_PROJECTS_ROOT`를 지정한다.
3. `python3 adobe/scripts/prepare_ae_project.py output/<project>`로 씬 번호·이미지·도감 ID를 읽기 전용 점검한다. `scenes.json`이 없고 결과가 `ready_to_create`이면 같은 명령에 `--write`를 붙여 **한 번만** 생성한다. 이 명령은 기존 `scenes.json`·이미지·레이어를 덮어쓰거나 복사하지 않는다. 이미 AE 편집이 있다면 파일을 유지하고 불일치를 수동으로 대조한다.
4. 패널의 `Window > Extensions > auto_kairos PD`에서 같은 프로젝트를 연다. 원고, 선택 이미지, 오디오, 말자막, 레이어를 확인하고 새 버전의 `.aep`로 저장한다. 프로젝트 연결과 전달 파일의 상세 계약은 `docs/contracts/semoji-renderer-handoff-v1.md`를 따른다.

## 씬별 연출 결정

먼저 나레이션이 요구하는 **이해 동작**을 한 줄로 쓴다. 예: “세 공장이 한 회사로 합쳐진다”, “두 수치의 격차가 뒤집힌다”. 이 문장이 없으면 효과부터 고르지 않는다. 다음으로 현재 씬의 장면 이미지·실제 자료·도해 중 무엇이 뜻을 가장 정확하게 보여주는지 결정한다. 같은 공간의 다음 앵글은 새 씬·새 화면으로 다루며, 한 그림을 늘려 크롭하는 것으로 대체하지 않는다.

`scene_specs.json`의 `motion`은 Remotion 근사 프리셋, `techniques`는 도감 ID, `motionNote`는 이 편의 실제 AE 연출 의도다. AE 패널은 `scenes.json`에 값이 없을 때 같은 씬 번호의 의도를 읽기 전용으로 보완한다. **도감 ID를 기록한 것과 AE에 적용한 것은 다르다.** AE registry에 없는 ID는 수동 키프레임·마스크·텍스트·도형으로 구현하거나 씬의 뜻에 맞는 다른 동작을 설계한다. 구현한 방법과 차이를 `motionNote` 또는 작업 기록에 남긴다.

화풍은 프로젝트의 `art_style.json`과 승인된 씬 이미지가 정한다. 레퍼런스의 **등장 순서·속도·시선 이동·정보 계층**을 차용할 수 있지만, 레퍼런스의 캐릭터·색·폰트·장식·자료 이미지를 그대로 복제하지 않는다. 방사형 줄무늬 광선·선버스트·집중선은 사용하지 않는다. 패널 registry에 `starburst-echo`가 있어도 이 금지 규칙이 우선한다.

| 연출 방향 | 주로 쓰는 판단 | AE 구현 예 |
|---|---|---|
| 세모지식 이야기 | 사건·인물·반전에서 컷과 정지 화면을 살리고, 말하는 단어에 맞춰 요소를 하나씩 누적 | 하드컷, 짧은 단어 카드, 자료 사진 팝, 인물의 발끝 기준 까딱임, 연도 태그·도장 |
| 설명형 연출 | 비교·분류·지도·수치의 관계를 먼저 보여주고, 읽는 순서를 모션으로 지정 | 점선 열 비교, 지도 항로와 통계, 단계별 차트, 한 항목씩 올라오는 카드·말풍선 |

세모지의 실측 리듬과 기법별 적합·부적합 조건은 `auto_agent/data/skills/shared/motion-dogam-semoji.md`를 본다. 평균 컷 길이·팝 빈도는 관찰값이지 할당량이 아니다. 연결어 “그런데”를 언제나 별도 카드로 만들거나 모든 장면에 느린 줌을 넣지 않는다. 설명형 레퍼런스(여러 레퍼런스 중 하나) 항목은 카탈로그에서 `sources[].ref == "ref_explainer_editorial"`로 찾는다.

현재 `ref_explainer_editorial` 레퍼런스 12개 중 `wipe-reveal-bubble`, `dim-cutaway-drop-exit` 두 기법만 AE 패널에 직접 이식되어 있다. `globe-spin-scatter`, `dashed-column-compare`, `chat-parody`, `map-stat-overlay`, `rack-defocus-drop-exit`, `bar-end-icon-pop`, `bar-end-icon-pop-h`, `brush-arrow-route`, `random-mouth-talk`, `tilted-stamp-hold`는 **연출 참고**다. 예컨대 비교는 점선·패널·값을 순차 키프레임으로 만들고, 채팅은 텍스트 레이어와 마스크의 푸시업으로, 지도는 승인된 지도 이미지 위 경로 패스로 재현한다. 수동 구현을 자동 적용 결과로 기록하지 않는다.

## AE 타임라인과 화면 검수

- **한 씬의 한 화면**을 기준으로 배경·인물·사물·설명 텍스트를 분리한다. 도해는 먼저 모든 에셋·텍스트·선을 배치한 완성 화면 한 장으로 승인받고, 그 화면을 구성하는 레이어를 분리해 등장 순서와 모션을 준다.
- 팝·강조는 해당 단어의 발화 시점에 맞춘다. 전환은 문장 경계와 뜻의 변화에 맞춘다. 레이어가 늘어나는 씬도 무엇을 먼저 읽어야 하는지 분명해야 한다.
- 장면별 컴프를 챕터별 프리컴프로 묶어 전체 타임라인의 레이어 폭증을 피한다. 전체 타임라인이 1,000레이어에 가까워지면 챕터 분리가 제대로 되었는지 점검한다. 챕터 카드 길이는 원고·프로젝트 지시를 따른다.
- 말자막 영역과 상단 정보 영역을 실제 프레임에서 확인한다. 연도·로고·수치·출처가 자막에 가리거나 프레임 밖으로 밀리면 위치나 레이아웃을 다시 설계한다. 원본 이미지를 확대 크롭해 화질을 희생하지 않는다.
- 패널에서 기법을 적용할 때 대상 컴프·레이어·재생 헤드를 확인하고 `ak-dogam:<id>` 마커와 실제 프레임을 본다. `registry.json`의 `support: partial`은 부분 구현이다. 기존 `.aep`는 덮어쓰지 않고 버전을 올린다.
- 최종 검수는 전체 재생과 함께 각 씬의 시작·발화 포인트·마지막 프레임에서 한다. 나레이션/자료 일치, 가려진 텍스트, 자막 타이밍, 씬·챕터 전환, 반복 이미지, 누락 에셋을 확인한다.

자동 검증은 `python3 adobe/scripts/sync_dogam.py --check`와 `python3 -m pytest -q adobe/tests/test_dogam_portability.py`로 한다. AE 기법 렌더 대조가 필요한 경우 `adobe/scripts/dogam_verify.py`를 사용한다. 이 세 검사는 **영상의 연출 적합성**을 대신 판정하지 않는다.
