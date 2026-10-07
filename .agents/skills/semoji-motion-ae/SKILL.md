---
name: semoji-motion-ae
description: Use when planning or editing Semoji-style motion (built from various references) in After Effects with an Auto Kairos project, including work continued on another computer. Not for Remotion-only work.
---

# 세모지 모션 도감 → After Effects

세모지 연출 규칙(여러 레퍼런스 참고)에 따른 **편집 판단과 완성 검수**는 `adobe/docs/editorial-motion-playbook.md`가 정본이다. 레퍼런스는 연출의 정보 순서·리듬만 참고하며 현재 프로젝트의 화풍을 바꾸지 않는다. 도감 자동 적용과 수동 AE 구현을 구분한다.

저장소 루트를 기준으로 경로를 찾는다. 개인 컴퓨터의 `~/Projects/semoji-motion`은 선택 사항이다. 도감의 343개 항목 스냅샷은 `adobe/data/semoji-motion/dogam/techniques.json`에 있고, AE에서 바로 적용 가능한 기법은 `adobe/cep/com.autokairos.pd/jsx/dogam/registry.json`의 12개다. 나머지 항목은 **연출 참고 자료**이며 AE 구현이 있다고 가정하지 않는다.

다른 컴퓨터의 Remotion과 같은 프로젝트를 이어받을 때는 먼저 `docs/contracts/semoji-renderer-handoff-v1.md`의 전달 파일·경로·검증 계약을 따른다. Remotion은 각 컴퓨터에 설치된 것을 사용하며 이 스킬은 AE 쪽 작업을 담당한다.

`scenes.json`이 없는 v3 출력 프로젝트는 씬 분해를 다시 시키지 않는다. `python3 adobe/scripts/prepare_ae_project.py output/<project>`로 읽기 전용 점검한 뒤, 기존 AE 편집 파일이 없을 때만 `--write`로 씬 목록을 만든다. 씬 번호·원고·선택 이미지·도감 의도를 유지하고 기존 파일은 덮어쓰지 않는다.

## 연출 선택

1. `auto_agent/data/skills/shared/motion-dogam-semoji.md`를 읽고, 씬의 나레이션·자료·이미지가 요구하는 움직임을 결정한다. 원고·씬 경계를 모션에 맞춰 바꾸지 않는다.
2. 전체 기법의 `id`·실측 정보·상태는 번들 `techniques.json`에서 확인한다. `금지` 항목은 사용하지 않는다. 특히 방사형 줄무늬 광선·선버스트 배경은 사용하지 않는다.
3. 해당 `id`가 AE `registry.json`에 있으면 패널의 **기법 도감** 탭에서 적용할 수 있다. 없으면 그 효과를 새 JSX로 구현하거나 기존 AE 레이어·키프레임으로 재현할지 판단한다. 이때 구현·검증 없이 자동 적용했다고 기록하지 않는다.
4. `scene_specs.json`에 `techniques`가 있다면 연출 의도로 존중한다. 이는 AE 자동 적용 명령이 아니다. Remotion으로도 출력한다면 기존 `motion` 프리셋을 별도로 유지한다.
5. 이로미즘 등 다른 화풍에서는 도감의 **타이밍·등장 순서·시선 이동**만 차용한다. `art_style.json` 및 현재 씬 이미지의 캐릭터·선·색·배경·폰트를 유지한다. 레퍼런스·세모지 원본의 시각 자산이나 장식은 그대로 가져오지 않는다. 씬의 `motionNote`를 확인하고, 효과의 룩 옵션이 화풍과 충돌하면 조정하거나 해당 기법 대신 같은 의미의 수동 레이어 모션으로 구현한다.
6. 설명형 레퍼런스(여러 레퍼런스 중 하나, `ref_b`) 항목은 `techniques.json`의 `sources[].ref == "ref_b"`에서 찾는다. 12개 중 현재 AE 직접 적용은 `wipe-reveal-bubble`, `dim-cutaway-drop-exit` 둘뿐이다. 나머지는 작업 규칙서의 수동 AE 구현 기준을 따른다. 실제 AE 구현을 검수하지 않고 적용 완료로 표시하지 않는다.

## 다른 macOS 컴퓨터에서 처음 실행

After Effects가 설치된 컴퓨터에서 저장소를 받은 뒤 다음을 실행한다.

```bash
bash adobe/scripts/setup_cep_dev.sh
cd adobe && python3 -m backend.app
```

설치 스크립트는 CEP 패널 링크와 함께 **저장소에 포함된 도감 미리보기·지도·기본 에셋**을 패널에 복사한다. 외부 `semoji-motion` 저장소가 있으면 그것을 우선 사용한다. 다른 위치에 있다면 `SEMOJI_MOTION_DIR`로 지정한다. 설치 후 AE를 재시작하고 `Window > Extensions > auto_kairos PD`에서 **기법 도감** 탭을 연다. 프로젝트는 기본적으로 저장소 `output/`을 바라보며, 필요하면 `AK_PROJECTS_ROOT`로 바꾼다.

완성 검수는 씬의 내용과 화면, 자막·상단 텍스트 가림, 챕터 프리컴프, 누락 에셋을 실제 AE 프레임에서 확인한다. 도해는 승인된 완성 화면을 만든 뒤 레이어를 분리해 움직인다. 자세한 판정 순서는 작업 규칙서를 따른다.

패널에서 적용할 때는 대상 컴프·레이어·재생 헤드를 먼저 확인한다. 기법에 따라 레이어 선택이 필요하다. 적용 후 AE 타임라인의 `ak-dogam:<id>` 마커와 실제 프레임을 확인하고, 필요하면 패널의 **다시 적용/제거**를 쓴다. 기존 `.aep`를 덮어쓰기 전에 새 버전으로 저장한다. 씬별 오디오, 말자막, 상단 텍스트 가림을 확인하고 챕터별 프리컴프 구조와 전체 레이어 수를 점검한다.

## 근거와 검증

- `adobe/cep/com.autokairos.pd/jsx/dogam/registry.json`: AE 적용 가능 기법·변수·미리보기.
- `adobe/data/semoji-motion/dogam/techniques.json`: 343개 전체 카탈로그 스냅샷. `구현`은 원본 Remotion 구현 상태일 수 있으며 AE 지원 여부는 registry로만 판단한다.
- `adobe/scripts/sync_dogam.py --check`: 원본 또는 번들 카탈로그와 AE 구현 변수의 정합성 확인(Node 필요).
- `adobe/scripts/dogam_verify.py`: 실제 AE 렌더 비교. 이 스크립트의 전체 검증은 별도 원본 `semoji-motion`의 영상 레이어·미리보기를 필요로 한다. 다른 컴퓨터에서 번들만 있을 때는 도감 패널의 AE 적용·프레임 확인을 수행한다.

자산을 새로 만들거나 레이어를 나눌 때는 저장소 `AGENTS.md`의 이미지 생성·기존 파일 보존 규칙을 따른다.
