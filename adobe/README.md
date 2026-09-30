# auto_kairos Adobe PD Assistant

After Effects(1차)/Premiere(2차) 내 영상 제작 보조 패널.
콘텐츠 엔진 = auto_kairos_v4 재사용, 이미지·LLM = Codex 단일 인증.

스펙: docs/spec/SPEC_v0.2.md

환경 키: `OPENAI_API_KEY`(codex 이미지), `ELEVENLABS_API_KEY`(TTS), `FAL_KEY`(레이어 분리 — `FAL_API_KEY` 이름도 인식).

세모지 모션 도감의 343개 항목 스냅샷과 AE 이식 12개 기법의 필수 에셋은 저장소에 포함됩니다. 다른 macOS 컴퓨터에서는 `bash adobe/scripts/setup_cep_dev.sh`로 패널과 도감 에셋을 설치하세요. AE 작업 절차와 지원 범위는 [semoji-motion-ae 스킬](../.agents/skills/semoji-motion-ae/SKILL.md)을 따릅니다.
