#!/bin/bash
# usage: run.sh <jsx>
# 잠금으로 한 번에 하나만 실행 → JSX 실행 → AE를 "정상 종료"(project close + app.quit) → Acr*.tmp 삭제 → 잠금 해제.
# pkill로 죽이면 다음 실행 때 Crash Repair 대화상자가 떠서 AE가 멈추므로 강제 종료는 최후 수단(5분 대기 후).
A="/Applications/Adobe After Effects 2026/Adobe After Effects 2026.app"
LOCK=/tmp/brand_cn_ae.lock
TMPD=/private/var/folders/7b/rf80z6797v31y66xgdw2ybvh0000gn/T
until mkdir "$LOCK" 2>/dev/null; do sleep 10; done
cleanup(){
  if pgrep -f "MacOS/After Effects$" >/dev/null; then
    osascript -e "with timeout of 120 seconds
tell application \"$A\" to DoScript \"try{app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);}catch(e){} app.quit();\"
end timeout" >/dev/null 2>&1
    for i in $(seq 1 60); do pgrep -f "MacOS/After Effects$" >/dev/null || break; sleep 5; done
    if pgrep -f "MacOS/After Effects$" >/dev/null; then echo "WARN: AE did not quit; leaving it running (lock released)"; fi
  fi
  pgrep -f "MacOS/After Effects$" >/dev/null || rm -f "$TMPD"/Acr*.tmp
  rmdir "$LOCK" 2>/dev/null
}
trap cleanup EXIT
free=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
if [ "$free" -lt 10 ]; then echo "DISK LOW: ${free}GB free — abort"; exit 3; fi
osascript -e "with timeout of 7200 seconds
tell application \"$A\" to DoScriptFile \"$1\"
end timeout"
