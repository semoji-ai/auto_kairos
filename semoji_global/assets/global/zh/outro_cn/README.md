# 중국어판 아웃트로 (2026-10-26)

원래 아웃트로(세모지 아웃트로_최종.mov)의 한복·태극기 인물 → 중국 시청자용으로 다시 그림(사용자 결정).
- 생성: codex `$imagegen`(--enable image_generation), 원래 아웃트로 5초 프레임(ref_outro.png)을 그림체·구도 참조로 첨부, 프롬프트 `prompt.txt`(check_prompt ok)
- 후보 2장 중 cand_1 채택(치파오+등롱, 장삼+부채, 당장 아이, 한푸+찻잔이 카드 옆 가운데 높이). 국기 없음
- `preview_1.png` = 1920×1080 + 카드에 "Semoji"(站酷快乐体 84px, #608064)
- outro.mov = preview_1.png 정지 화면 19.986633초, 29.97fps, h264 yuv420p (원래 규격과 같음). 이전 판은 outro_v1.mov(로컬)
```
ffmpeg -loop 1 -framerate 30000/1001 -i preview_1.png -t 19.986633 -c:v libx264 -pix_fmt yuv420p -crf 16 -r 30000/1001 ../outro.mov
```

## 아웃트로가 없는 편용 완성 클립 (2026-10-27)
KFC(B019·B020)처럼 원래 아웃트로가 없는 편은 코카콜라 1편 중국어판 끝 10.277초(아웃트로 정지 화면 + 종이 텍스처 + Sand_Castle BGM)를 그대로 붙인다(사용자 결정).
`assets/global/zh/build/outro_cn_cocacola.mp4`(gitignore) 다시 만들기:
```
ffmpeg -ss 775.908 -i episodes/B052/render/zh/B052_ZH_preview.mp4 -t 10.277 -c:v libx264 -crf 18 -pix_fmt yuv420p -r 30000/1001 -c:a aac -b:a 192k -ar 48000 assets/global/zh/build/outro_cn_cocacola.mp4
```
편 설정 `master_config.json` → `"append_outro": {"zh": "assets/global/zh/build/outro_cn_cocacola.mp4"}`, `scripts/append_outro.py`가 rebuild 끝에 붙임.
