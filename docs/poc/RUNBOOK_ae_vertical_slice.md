# RUNBOOK — AE 수직 슬라이스 PoC (#3 백엔드 연결 + #4 컴프 생성)

목표: 패널 ↔ 백엔드 통신(#3)과 manifest → JSX → AE 컴프 생성(#4)을 한 번에 검증.
환경: macOS, After Effects 2026.

## 순서 (AE 열기 전에 1~2 먼저!)

### 1. CEP 개발 환경 설정 (1회)
```bash
bash /Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/scripts/setup_cep_dev.sh
```
→ 디버그 모드 ON + 익스텐션 링크. **AE가 이미 켜져 있었다면 종료 후 다시 켜야 적용됨.**

### 2. 백엔드 실행 (별도 터미널, 켜둔 채로)
```bash
python3 /Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/backend/app.py
# → [auto_kairos backend] http://127.0.0.1:8765/health  (codex=ready)
```

### 3. After Effects 2026 실행
- 메뉴: **Window > Extensions > auto_kairos PD (PoC)** → 패널이 뜸

### 4. 검증
- **[버튼] 백엔드 확인** → `backend: connected / codex: ready / version: 0.1.0-poc`
  → ✅ #3 통과 (패널 ↔ localhost 백엔드 통신 OK)
- **[버튼] 샘플 manifest → AE 컴프 생성** → `OK: 씬 컴프 3개 + Final(9s)`
  → ✅ #4 통과 (프로젝트에 Scene_001/002/003 + Final 컴프 생성, Final이 뷰어에 열림)

## 성공 기준 (스펙 §6.2)
프로젝트 패널에 **씬 컴프 3개 + Final 컴프**가 생기고, Final에 씬이 순서대로 배치되면 PoC 성공.

## ✅ 검증 결과 (2026-06-04): 전체 통과
- #3 백엔드 연결: 패널 「백엔드 확인」 → connected / codex ready 확인
- #4 컴프 생성: 「샘플 manifest → AE 컴프 생성」 → Scene_001~003 + Final 자동 생성 확인
- AE 2026 + CEP(미서명, 디버그모드) + 표준라이브러리 백엔드 조합 동작 검증

## 안 될 때
| 증상 | 점검 |
|------|------|
| 패널이 메뉴에 없음 | setup 스크립트 실행 여부, AE 재시작, CSXS 버전(11/12) 디버그 모드 |
| "연결 실패" | 백엔드(app.py) 실행 중인지, 포트 8765 |
| "jsx 로드 실패" | 익스텐션 링크 경로, manifest.xml의 file-access 파라미터 |
| 컴프 생성 ERROR | 반환 메시지 확인 — manifest 경로/JSON 형식 |
| codex: not_authenticated | `codex login` 1회 |

## 다음 단계 (PoC 통과 후)
- ae_manifest 스키마를 v4 산출물(units/motion_plan/selected images)과 연결
- 백엔드에 `/api/ae/build-jsx` + `/api/skills/run`(codex exec) 추가
- 이미지 레이어/오디오 싱크 실제 에셋으로 확장 → PRD/로드맵
