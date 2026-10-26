# 중국어판 아웃트로 (2026-10-26)

원래 아웃트로(세모지 아웃트로_최종.mov)의 한복·태극기 인물 → 중국 시청자용으로 다시 그림(사용자 결정).
- 생성: codex `$imagegen`(--enable image_generation), 원래 아웃트로 5초 프레임(ref_outro.png)을 그림체·구도 참조로 첨부, 프롬프트 `prompt.txt`(check_prompt ok)
- 후보 2장 중 cand_1 채택(치파오+등롱, 장삼+부채, 당장 아이, 한푸+찻잔이 카드 옆 가운데 높이). 국기 없음
- `preview_1.png` = 1920×1080 + 카드에 "Semoji"(站酷快乐体 84px, #608064)
- outro.mov = preview_1.png 정지 화면 19.986633초, 29.97fps, h264 yuv420p (원래 규격과 같음). 이전 판은 outro_v1.mov(로컬)
```
ffmpeg -loop 1 -framerate 30000/1001 -i preview_1.png -t 19.986633 -c:v libx264 -pix_fmt yuv420p -crf 16 -r 30000/1001 ../outro.mov
```
