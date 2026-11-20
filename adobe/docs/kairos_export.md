# 카이로스로 내보내기

애프터이펙트용으로 만든 편(`output/<편>/manifest.json`)을 카이로스 편집기(cut.semoji.dev)의
타임라인으로 옮기는 절차다. 계산은 `adobe/scripts/kairos_export.py` 가 하고, 카이로스 MCP
호출(파일 올리기·타임라인 저장)은 클로드 세션이 한다.

## 옮겨지는 것

| 매니페스트 | 카이로스 타임라인 |
|---|---|
| 레이어(위치·배율) | 영상 트랙의 그림 클립(레이어 순서대로 V1, V2, …) |
| 카메라 줌 | 레이어마다 위치·배율 키프레임으로 구워 넣음(애펙 70:30) |
| 강조(zoom_emphasis) | 배율 키 3개(이지 이즈) |
| 까딱임(bob) | 발을 기준점으로 한 회전 키 2개 + 왕복 반복 |
| 흔들기(wiggle) | 그 구간의 회전 키(이지 이즈) |
| 사진 한 장 씬 | 그림 클립 하나 |
| 음성 · 말자막 · 제목 | 오디오 트랙 · 자막 트랙 · 제목 트랙 |

효과 키프레임은 모두 이지 이즈를 건다. 레이어가 없는 도해 레이아웃(리모션 템플릿)은 옮기지 않는다.

## 절차

```bash
# 1) 올릴 파일과 타임라인 초안
python3 adobe/scripts/kairos_export.py plan output/<편> --scenes 1-6 --out <작업 폴더>
#    → <작업 폴더>/files/*  +  <작업 폴더>/plan.json   (에셋 자리는 "@file:<파일 이름>")
```

2) 클로드 세션에서 카이로스 MCP 로:

- `create_project` (또는 기존 프로젝트)
- `plan.json` 의 `files` 마다 `create_upload`(kind·content_type·bytes) → 받은 주소로 PUT → `complete_upload`
  - PUT 헤더: `content-type: <content_type>`, `cache-control: max-age=31536000`
  - 음성은 `complete_upload` 에 `duration_seconds` 를 함께 보낸다
- 결과의 `timeline_asset` 을 `<작업 폴더>/map.txt` 에 한 줄씩 적는다: `<파일 이름> <timeline_asset>`

```bash
# 3) 에셋 자리를 채운 최종 타임라인
python3 adobe/scripts/kairos_export.py finalize <작업 폴더>
#    → <작업 폴더>/timeline.json
```

4) `get_timeline` 으로 `rev` 를 받고 `save_timeline(base_rev, timeline)` 으로 저장한다.

## 알아 둘 것

- 한 편 전체는 무겁다. 대한항공 편(136씬)은 파일 717개 · 약 700MB · 타임라인 JSON 약 400KB 다.
  몇 씬씩 나눠 올리거나 범위를 정해 쓴다.
- 매니페스트의 경로가 다른 기기(NAS) 기준이어도, 편 폴더 이름을 기준으로 이 기기의 파일을 찾는다.
- 2560px 를 넘는 JPG 는 줄여서 올린다(편집기 디코드 부담).
- 카메라 줌은 지금 레이어마다 구워 넣는다. 카이로스에 널·페어런츠가 배포되면 널 하나로 바꿀 수 있다.
