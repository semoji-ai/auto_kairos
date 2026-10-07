# auto_kairos Adobe PD Assistant

After Effects(1차)/Premiere(2차) 내 영상 제작 보조 패널.
콘텐츠 엔진 = auto_kairos_v4 재사용, 이미지·LLM = Codex 단일 인증.

스펙: docs/spec/SPEC_v0.2.md

환경 키: `ELEVENLABS_API_KEY`(TTS), `FAL_KEY`(레이어 분리 — `FAL_API_KEY` 이름도 인식). 이미지 생성 경로는 저장소 `AGENTS.md`의 codex 내장 imagegen 규칙을 따릅니다.

세모지 모션 도감의 343개 항목 스냅샷과 AE 이식 12개 기법의 필수 에셋은 저장소에 포함됩니다. 도감 원본 코드(Remotion·빌더)는 저장소 [`motion/`](../motion/README.md)에 있습니다. 다른 macOS 컴퓨터에서는 `bash adobe/scripts/setup_cep_dev.sh`로 패널과 도감 에셋을 설치하세요. AE 작업 절차와 지원 범위는 [semoji-motion-ae 스킬](../.agents/skills/semoji-motion-ae/SKILL.md)을 따릅니다.

세모지 연출 규칙(여러 레퍼런스 참고)에 따른 연출 선택과 AE 검수 기준은 [편집 운영 규칙](docs/editorial-motion-playbook.md)에 있습니다. 프로젝트를 옮긴 뒤 `python3 adobe/scripts/prepare_ae_project.py output/<project>`로 점검하고, `scenes.json`이 없는 경우에만 `--write`로 생성하세요. 기존 AE 편집 파일과 이미지에는 손대지 않습니다.

컴퓨터 간 프로젝트 전달과 각자의 Remotion·AE 연결 기준은 [렌더러 연결 계약](../docs/contracts/semoji-renderer-handoff-v1.md)에 정의했습니다.
