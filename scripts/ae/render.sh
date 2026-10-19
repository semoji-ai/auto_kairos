#!/bin/bash
# usage: render.sh <aep> <comp name> <in sec> <out sec> <out.mp4> [fps=30] [OM template="H.264 - Match Render Settings - 40 Mbps"]
# fps는 컴프 프레임레이트(29.97 컴프면 29.97을 넘길 것). in/out은 원본 mp4 기준 초 그대로.
# 화면 잠김(원격 화면공유 등)에서도 동작하는 aerender 기반 렌더. run.sh와 같은 잠금 사용.
AER="/Applications/Adobe After Effects 2026/aerender"
LOCK=/tmp/brand_cn_ae.lock
TMPD=/private/var/folders/7b/rf80z6797v31y66xgdw2ybvh0000gn/T
until mkdir "$LOCK" 2>/dev/null; do sleep 10; done
trap 'rm -f "$TMPD"/Acr*.tmp 2>/dev/null; rmdir "$LOCK" 2>/dev/null' EXIT
free=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
[ "$free" -lt 10 ] && { echo "DISK LOW"; exit 3; }
FPS=${6:-30}
S=$(python3 -c "print(round($3*$FPS))"); E=$(python3 -c "print(round($4*$FPS)-1)")
"$AER" -project "$1" -comp "$2" -s $S -e $E -OMtemplate "${7:-H.264 - Match Render Settings - 40 Mbps}" -output "$5" -sound OFF 2>&1 | tail -5
ls -la "$5"
