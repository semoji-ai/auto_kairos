# _vendor/

auto_kairos_v3 의 일부 모듈을 v4 안에 **이식(vendor)** 한 것. v4 가 v3 폴더 없이도 동작하도록(L3) 하기 위한 조치.

## 들어 있는 파일

| 파일 | 출처 | 변경 |
|------|------|------|
| `elevenlabs_v3.py` | `auto_kairos_v3/auto_agent/tools/elevenlabs.py` | 내부 import 1건 (KoreanTTSPreprocessor) → 상대 import 로 변경 |
| `korean_tts_preprocessor.py` | `auto_kairos_v3/auto_agent/tools/korean_tts_preprocessor.py` | 그대로 |
| `image_search_v3.py` | `auto_kairos_v3/auto_agent/tools/image_search.py` | 그대로 |
| `video_search_v3.py` | `auto_kairos_v3/auto_agent/tools/video_search.py` | `get_vault_dir` 인라인, 옵션 의존(Gemini 분석·DB 조회)는 try/except + NotImplementedError |

## 사용 규칙

- **본 디렉토리 모듈을 직접 import 하지 말 것**. 항상 wrapper(`shared/lib/elevenlabs.py` 등) 경유
- **L3 원칙**: v4 어떤 코드도 `auto_kairos_v3` 경로를 import 하지 않는다 (옵션 advanced 기능 제외)
- 본 디렉토리 안에서만 vendor 동기화 책임

## v3 가 변경되면

v3 원본 파일이 갱신되면 **수동 동기화** 필요:

1. v3 의 변경 사항 확인
2. 본 디렉토리 해당 파일 갱신 (또는 삭제 후 재복사 + 본 README 의 "변경" 칸 재적용)
3. 회귀 테스트 실행: `python -m unittest tests.test_wrappers`
4. 통합 테스트(트럼프 같은 드라이런)로 동작 확인

## 라이선스

해당 파일들은 v4 와 같은 사용자 소유 코드(같은 프로젝트). vendor 는 단순 복사·재구성. 외부 라이선스 의무 없음.

## L4(미래) 가능성

vendor 도 폐기하고 v4 가 자체 구현으로 가는 단계. 하지만 현재 로직(80+ 한국어 패턴, image search 다중 소스)이 안정적이라 우선순위 낮음. 필요해질 때(예: 외부 라이브러리로 발전) 진행.
