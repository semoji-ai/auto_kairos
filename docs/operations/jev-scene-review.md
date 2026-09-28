# 선택적 Jev 씬 분석·자료 적합성 검사

2026-09-20. 기존 scene_enricher_module(step_2d)에 연결했습니다. 이미지 생성이나 픽셀 관찰을 Jev로 대체하지 않습니다. 기존 flat scene schema를 유지하며 분석 결과는 별도 파일에 둡니다.

## 적용 범위

- 모든 씬의 나레이션·concept·배경·캐릭터·기존 자료 요구를 입력으로, 단일 씬으로 전달 가능한지와 사진/도해/지도/비교 화면 중 적절한 표현 유형을 판정합니다. 분석은 제안이며 씬 분할·visual_kind 변경을 자동 실행하지 않습니다.
- 검색 이미지·영상 후보 중 정확한 URL에 연결된 관찰 기록이 있는 후보만 실제 적합성 판정을 합니다. 후보별 pass/partial/fail/unknown 및 선택/없음을 반환합니다.
- 적합 후보라도 기존 해상도·라이선스/영상 점수 게이트를 통과해야 자동 선택합니다. 기존 점수는 휴리스틱이지 법적 사용권 검증이 아닙니다.
- 관찰된 후보가 부적합/일부만 충족/판단 불가이면 기존 임시 자동선택을 복원하고 검토 큐에 보냅니다. 재검색/씬 분리/관찰 보강 등의 다음 조치가 기록됩니다. 추가 검색이나 장면 재작성 자체를 이 기능이 실행하지는 않습니다.
- 관찰이 전혀 없으면 기존 선택 동작을 유지하고 needs_observation 및 관찰 요청을 남깁니다. 이것은 Jev가 적합 판정을 했다는 뜻이 아닙니다.
- API 오류/예산 부족은 기존 선택 동작을 유지하고 error를 기록합니다. 원본 이미지·영상 파일은 삭제하지 않습니다.

## 활성화

TYPESAFE_API_KEY가 로드되어 있으면 활성화됩니다. JEV_SCENE_REVIEW=0으로 끌 수 있습니다. 키가 없으면 기존 경로와 동일합니다. 타겟 리서치 스위치 JEV_TARGETED_RESEARCH와 독립입니다. 이 판단 기능에는 Serper 키가 필수는 아니며 실제 검색은 기존 검색 공급자 설정을 사용합니다.

실행당 Jev 예산 $0.03, 최대64 API 시도, 씬당 최대5개 후보를 검사합니다. 같은 입력의 영구 판단 캐시는 아직 없어서 재실행 시 재판정합니다. dry_run도 검색/판정 API는 호출하고 파일 저장만 생략합니다.

## 관찰 기록 제공

프로젝트 출력 폴더에 asset_observations.json을 둡니다. 관찰 대상은 실제 픽셀/영상이어야 하며 제목이나 검색 설명만을 관찰로 등록하지 않습니다. 이 파일은 이제 구독 인증된 Codex/Claude CLI 관찰로도 생성됩니다. 기존 수동 관찰은 우선 보존합니다. 자세한 설정·한도는 아래 자동 관찰 절을 참조하세요.

```json
{
  "observations": {
    "https://example.org/exact-candidate-image.jpg": {
      "kind": "image",
      "scope": "thumbnail",
      "observation": "실사. 사람이 마트에서 식품 포장을 들고 있음. 날짜 숫자는 해상도가 낮아 읽히지 않음."
    },
    "https://example.org/exact-video-url": {
      "kind": "video",
      "scope": "00:12–00:18 직접 확인",
      "observation": "손이 포장을 뒤집는 모습. 날짜가 화면 밖에 있어 보이지 않음."
    }
  }
}
```

키는 후보의 image_url 또는 video url과 정확히 일치해야 합니다. 이미지 관찰을 영상 관찰로 쓰지 않습니다. URL 내용이 바뀌었거나 관찰 해상도가 다르면 관찰 기록을 새로 갱신해야 합니다. 조건은 기존 narration/concept/imageAsset/videoAsset에 기술하고, 필요하면 visual_requirements에 명시적으로 기술할 수 있습니다. Jev가 자유문으로 새 요구사항을 작성하는 구조는 아닙니다.

## 결과 파일

- scene_judgements.json: 씬 요구/분석, 후보 판정, 다음 조치, 사용량·비용·API 원시 판정.
- asset_observation_requests.json: 관찰이 필요한 후보 URL과 관찰 작업.
- enrichment_queue.json: 기존 검토 큐에 jev 필드가 추가됩니다. 대시보드의 기존 후보 선택 기능은 유지됩니다. Jev 상세 판정을 위한 별도 UI는 추가하지 않았습니다.
- 자동 채택된 경우 imageAsset/videoAsset의 selection_status는 jev_auto입니다.

## 검증 결과

tests/test_jev_scene.py에서 선택 교체, 부적합 자료 차단, 부분 관찰, 기존 해상도/라이선스 기준, API 실패 시 기존 동작, 키 없음/비활성화, 생성 씬 분석, 영상/이미지 관찰 혼용 방지, 파이프라인 검토 큐 저장을 검증합니다.

실제 저장 관찰 기록과 Jev API로 2개 씬을 시험했습니다. 초기 질문에서 후보 ID를 명시하지 않아 모든 후보를 같은 기준으로 혼동하는 오류를 발견했습니다. 선택지 설명마다 평가할 후보 ID를 명시하고 회귀 테스트를 추가했습니다. 초기 실패 기록을 보존했습니다.

수정 후 해안+증류소 요구는 I01 통과, 해안이 없는 I02/I06 탈락. 실제 손+마트+식품+읽히는 날짜 요구는 완전 충족 후보 없음으로 판정했습니다. 사용권 불명 후보는 자동 채택하지 않았습니다. 수정 후2호출/5,415입력토큰/Jev $0.00022743. 전체 이미지 직접 인식이나 품질 우월성 시험은 아닙니다.

기록: experiments/jev_scene_integration_20260920/. 프로덕션의 기존 scene_specs나 이미지에는 실험 결과를 적용하지 않았습니다. 다음 실제 step_2d 실행부터 옵션/관찰 기록에 따라 적용됩니다.


## 자동 이미지 관찰 — 구독 CLI 경로 (2026-09-20 수정)

사용자 요청에 따라 Gemini API 관찰 경로를 제거했습니다. 현재는 Serper 등 기존 검색기의 후보 → 이미지 다운로드 → 구독 인증된 Codex/Claude 관찰 → Jev 적합성 판단입니다. 이미지 생성 API는 호출하지 않습니다.

기본 설정:

```bash
JEV_OBSERVER_PROVIDER=codex
# 기본 모델: gpt-5.6-sol
```

Claude Opus로 관찰하려면:

```bash
JEV_OBSERVER_PROVIDER=claude
# 기본 모델: opus
```

JEV_OBSERVER_MODEL로 CLI 모델을 명시할 수도 있습니다. 모델 변경 시 기존 자동 관찰 캐시를 재사용하지 않습니다. 기본 Codex Sol 또는 선택한 Claude Opus 하나만 호출하며, 실패할 때 다른 API나 모델로 자동 과금 전환하지 않습니다.

- 활성 조건: TYPESAFE_API_KEY와 선택한 CLI 설치·구독 로그인. GOOGLE_API_KEY/GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY는 필요하지 않습니다.
- Serper 검색에는 별도로 SERPER_API_KEY가 필요합니다. Jev·Serper 비용은 기존과 동일하게 별도이며 관찰은 구독 사용량을 소비합니다. 월 구독료 절감을 뜻하지 않습니다.
- 각 관찰 전에 Codex의 ChatGPT 로그인 또는 Claude의 claude.ai/firstParty 로그인을 확인합니다. API 인증이면 관찰을 거절하고 기존 경로로 복귀합니다. 자식 프로세스에서 API 키·API 공급자 경로 환경변수를 제거합니다. 인증정보 자체를 로그에 기록하지 않습니다.
- Codex는 이미지 파일을 -i로 직접 전달하고 JSON 결과만 요청합니다. Claude는 inline base64 이미지로 전달하며 도구를 비활성화합니다. CLI stdout의 사용량을 기록하고 CLI 비용표시는 실제 별도 API 청구액으로 해석하지 않습니다.
- JEV_SCENE_REVIEW=0: 씬 Jev와 자동 관찰 모두 비활성화.
- JEV_AUTO_OBSERVE=0: 자동 관찰만 비활성화. 기존 수동 관찰 기록으로 Jev 판단은 가능.
- 씬당 최대5후보, 실행당 관찰 최대10회·다운로드20회.180초 이후 새 관찰을 시작하지 않으며 진행 중 CLI의 제한시간은120초입니다.
- 관찰은 원본보다 썸네일을 우선합니다. 보이지 않는 날짜·정체를 추측하지 않도록 요청합니다. 영상 썸네일을 영상 관찰로 쓰지 않습니다.
- 캐시는 후보/이미지 URL·provider·model·관찰 버전이 같으면24시간 재사용합니다. 실행 중 같은 이미지 바이트는 해시로 중복 호출을 막습니다. 만료/버전 변경된 자동 관찰의 갱신이 실패하면 현재 실행에서는 오래된 관찰을 사용하지 않습니다. 기존 Gemini 자동 관찰도 새 버전으로 다시 관찰하며 수동 기록은 보존합니다.
- 원본 이미지 입력은 research/observer_inputs/에 해시 이름으로 보존하고 삭제하지 않습니다. 임시 CLI 결과·스키마 텍스트만 정리합니다.
- asset_observation_usage.json에 provider·model·호출 횟수·CLI 사용량·오류 유형을 기록합니다.
- dry_run도 네트워크/CLI 호출을 실행하지만 관찰 결과 JSON 저장은 생략합니다. CLI에 전달한 이미지 입력은 보존됩니다.

테스트: tests/test_subscription_vision.py, tests/test_asset_observer.py 및 기존 Jev/runner 테스트. 실제 구독 호출 기록은 experiments/jev_subscription_observe_20260920/에 보존합니다. 이전 experiments/jev_auto_observe_20260920/는 폐기된 Gemini 경로의 역사적 시험 기록이며 현재 구현이 아닙니다.
