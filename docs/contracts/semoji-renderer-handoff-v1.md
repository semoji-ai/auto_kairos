# 세모지 프로젝트 렌더러 연결 계약 v1

상태: 2026-09-30 기준 현재 구현의 전달 계약. 적용 대상은 Auto Kairos 프로젝트를 다른 컴퓨터의 **기존 Remotion 설치** 또는 **After Effects + Auto Kairos Adobe 패널**에서 이어 작업하는 경우다. 렌더러 프로그램·`node_modules`·AE 앱을 프로젝트에 복사하지 않는다.

## 1. 전달 단위와 위치

코드는 Git으로 동기화한다. 제작 데이터는 프로젝트 폴더 `output/<project>/` **전체**와 그 편이 참조하는 `output/_series/<series_id>/` 등 공유 에셋을 함께 전달한다. `git pull`만으로 `output/`의 이미지·오디오·레이어가 옮겨진다고 가정하지 않는다. API 키와 `.env`는 전달물에서 제외한다.

받는 컴퓨터에서 코드 저장소의 절대 경로는 달라도 된다. 프로젝트 파일 안의 참조는 가능한 한 **프로젝트 폴더 기준 상대 경로**로 유지하고, 옛 컴퓨터의 `/Users/...`·`/Volumes/...`를 전달 계약으로 사용하지 않는다. 로컬 생성 매니페스트에 절대 경로가 들어간 경우에는 해당 컴퓨터에서 다시 빌드한다.

현재 Remotion 매니페스트 생성기는 `AUTO_AGENT_WORKSPACE/remotion/public/`과 `AUTO_AGENT_WORKSPACE/output/`을 사용한다. AE 백엔드는 기본적으로 이 저장소의 `output/`을 보며, 작업 공간을 분리했다면 `AK_PROJECTS_ROOT=<workspace>/output`으로 맞춘다. **두 렌더러가 동일한 프로젝트 데이터를 읽는 것**이 연결 조건이고, 같은 프로그램 설치 폴더를 공유할 필요는 없다.

## 2. 데이터 소유권

| 데이터 | 정본·전달 파일 | 소비자·주의 |
|---|---|---|
| 씬 순서·내레이션·기본 연출 | `scene_specs.json` | Remotion 매니페스트 입력. flat schema 유지 |
| AE 씬 편집 상태 | `scenes.json` | AE 패널·AE 매니페스트 입력. 같은 프로젝트 폴더에 둔다 |
| 선택된 이미지 | `images/image_assets.json`의 `selected`와 실제 이미지 파일 | Remotion·대시보드가 사용. AE의 `scenes.json.imageRef`와 같은 판본인지 확인 |
| 음성·자막 | `audio/`, `subtitles.json` 및 씬별 자막/타임스탬프 | 파일과 텍스트를 함께 전달. 씬 길이는 실제 오디오 기준으로 확인 |
| 분리 레이어와 의미 | `layers/<sceneId>__*.png`, 선택적 SVG, `layers/<sceneId>__elements.json` | `elements.json`의 `kind`·`bbox`·`z`·`motion`이 레이어 의도의 정본 |
| 모션 연출 의도 | 씬의 `motion`, `techniques`, `motionNote`, 레이어의 `motion` | 기법 ID와 화풍별 적용 메모는 구현이 아니라 의도. 렌더러별 지원 여부를 확인 |

현재 코드에는 `scene_specs.json`과 `scenes.json`이 **둘 다 필요**하다. AE 패널은 주요 텍스트와 이미지 선택을 상대 파일에 되비추지만, 파일 하나만 옮기거나 한쪽만 손으로 수정하면 화면이 갈릴 수 있다. 이동 전후에 씬 번호·순서·내레이션·선택 이미지를 대조한다. **두 파일의 `sceneId`를 같게 만들기 위해 기존 ID를 다시 발급하거나 자산 이름을 바꾸지 않는다.** 현재 프로젝트는 양쪽 ID가 달라도 씬 번호와 각자의 에셋 참조로 연결된다.

## 3. 렌더러별 어댑터

| | Remotion 컴퓨터 | AE 컴퓨터 |
|---|---|---|
| 로컬 프로그램 | 설치된 Remotion 사용. 저장소의 `auto_agent/remotion_template/src/`가 코드 정본 | 설치된 After Effects 사용. `bash adobe/scripts/setup_cep_dev.sh`로 패널·도감 에셋 설치 |
| 입력 변환 | `python3 -m auto_agent.scripts.build_manifest --local output/<project>`로 해당 컴퓨터의 `remotion/public/manifest.json`과 프로젝트 링크 생성 | `adobe.backend.manifest.build_manifest(project_dir)`가 AE용 `output/<project>/manifest.json` 생성. 패널의 빌드 절차를 사용 |
| 레이어 변환 | 필요하면 `scripts/build_remotion_layers.py`가 `elements.json` → `layers/<sid>__remotion.json`으로 변환 | `elements.json`을 읽어 AE 컴프 좌표·키프레임으로 변환 |
| 모션 도감 | 씬의 `motion` 프리셋을 렌더러가 해석. `techniques`만으로 AE 기법을 자동 실행하지 않음 | [세모지 AE 모션 스킬](../../.agents/skills/semoji-motion-ae/SKILL.md)과 패널 도감 사용. 현재 343개 참고 항목 중 12개가 AE 직접 적용 가능 |
| 산출물 | Remotion 매니페스트·props·렌더 | AE 매니페스트·`.aep`·렌더 |

### 이로미즘 등 다른 화풍에서 도감 활용

화풍은 프로젝트 `art_style.json`이 결정하고, 도감은 움직임의 의미·등장 순서·타이밍만 제공한다. 예를 들어 지식해적단 자료가 포함된 `bar-chart-v`를 이로미즘 씬에 선택할 수 있지만, 원본 리본·마스코트·색을 복사하지 않고 이로미즘 손그림 막대와 타이포그래피로 다시 만든다.

```json
{
  "motion": "stagger_wave",
  "techniques": ["bar-chart-v"],
  "motionNote": "막대가 차례로 자라며 수치를 강조한다. 아이콘과 글자는 이로미즘 손그림 화풍으로 제작한다."
}
```

씬 기획에서는 `motion`과 `techniques`를 함께 기록한다. AE 패널은 `scenes.json`에 의도가 없으면 같은 씬 번호의 `scene_specs.json`에서 세 필드를 읽어와 모션 플래너에 전달한다. 기존 AE 편집값이 있으면 그것을 우선한다. 이 읽기 보완은 `scenes.json`을 자동 수정하지 않는다. 도감 ID가 AE registry에 있으면 패널에서 직접 적용하고 화풍에 맞게 룩을 조정한다. registry에 없으면 플래너의 기본 레이어 프리셋으로 가능한 부분만 구현하거나 AE에서 별도 제작한다. Remotion은 기존 `motion` 프리셋을 실행하며, 도감 ID 전체를 자동 재현하지는 않는다.

Remotion의 `remotion/public/project` 링크, `remotion/public/manifest.json`, AE의 `manifest.json`, `.aep`, 렌더 파일은 **로컬 파생물**이다. 다른 컴퓨터의 절대 경로를 포함한 파일을 정본처럼 덮어쓰지 않는다. **현재 Remotion 매니페스트 생성기는 `remotion/public/project`가 실제 디렉터리여도 지우고 링크로 교체하므로, 실행 전에 그 경로가 없거나 기존 링크인지 확인한다. 실제 디렉터리가 있으면 멈추고 내용을 보존한 뒤 연결 위치를 결정한다.** `scripts/setup_remotion.py`는 초기 설치·소스 동기화용이며, 이미 설치된 Remotion의 `src/`를 무심코 덮어쓰는 연결 단계가 아니다. 렌더러 구현은 각각 달라도 된다. 동일하게 유지할 것은 씬 내용, 선택 자산, 타이밍, 레이어 의미와 모션 의도다.

## 4. 인수인계 전 검증 조건

1. `scene_specs.json`과 `scenes.json`의 씬 번호·순서·내레이션이 의도대로 대응한다. 새 씬이나 삽입 씬이 있으면 양쪽에 반영됐는지 확인한다.
2. 선택 이미지, 음성, 레이어 메타가 가리키는 **실제 파일**이 전달 폴더에 있다. `output/_series/` 등 외부 공유 에셋도 빠지지 않았다.
3. `elements.json`의 bbox는 원본 이미지의 `[left, top, right, bottom]`이다. Remotion용 `[x, y, width, height]` 변환은 어댑터가 한 번만 수행한다.
4. `techniques`의 ID는 도감에 존재하는지 확인하고, AE 자동 적용을 기대한다면 AE `registry.json`에도 있는지 확인한다. 없는 기법은 설계 의도로 남기고 수동 구현·대체 연출을 결정한다.
5. 받는 컴퓨터에서 각각 매니페스트를 다시 빌드한 뒤 누락 에셋·씬 길이·말자막 가림·챕터 경계를 확인한다. AE는 컴프/레이어/재생 헤드와 `ak-dogam:<id>` 마커를 확인한다.

계약 위반이 발견되면 자동 복사나 ID 재발급으로 덮지 말고, 어떤 파일과 씬이 갈렸는지 기록한 뒤 정본의 선택 상태를 확인한다. 기존 이미지·세션·프로젝트 파일은 삭제하지 않는다.

관련 구현: [공유/분기 규칙](../rules/shared-vs-branch.md), [Remotion 매니페스트 생성기](../../auto_agent/scripts/build_manifest.py), [AE 매니페스트 생성기](../../adobe/backend/manifest.py), [세모지 AE 모션 스킬](../../.agents/skills/semoji-motion-ae/SKILL.md).
