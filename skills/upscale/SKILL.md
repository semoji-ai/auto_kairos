---
name: upscale
description: Use when users say "/upscale", "업스케일", "비디오 업스케일", "해상도 올려", or want to upscale a video to 1080p/1440p/2160p with fal SeedVR
---

# Upscale (fal SeedVR)

> fal.ai SeedVR2(`fal-ai/seedvr/upscale/video`)로 비디오를 1080p/1440p/2160p로 업스케일합니다.

## Trigger Conditions

```
- "/upscale <video_path> [1080|1440|2160]"
- "업스케일 <파일> [해상도]"
- "비디오 해상도 올려줘"
```

---

## WHEN TRIGGERED - EXECUTE IMMEDIATELY

1. **입력 확인** — 비디오 경로와 해상도(기본 1080) 추출. 파일이 없으면 사용자에게 경로를 물어보세요.

2. **환경 준비** (FAL_API_KEY는 .env에 있음):
```bash
set -a; source $KAIROS_HOME/.env; set +a
cd $KAIROS_HOME
```

3. **실행**:
```bash
python3 -m auto_agent.cli upscale <video_path> --resolution 1080
```
- `--resolution` : `1080` | `1440` | `2160`
- `--out <path>` : 출력 경로 지정 (기본: 입력 옆 `_up{res}` 접미사)
- `--dry-run` : 과금 호출 없이 페이로드 검증만

4. **결과 보고** — 출력 경로와 해상도를 사용자에게 알립니다.

## 참고

- 업로드 → SeedVR target 모드 처리 → 결과 mp4 다운로드까지 동기 실행 (긴 영상은 수 분 소요).
- 과금 API이므로 대량 배치 전에는 `--dry-run`으로 페이로드를 먼저 확인하세요.
- 구현: `auto_agent/tools/video_upscale.py`
