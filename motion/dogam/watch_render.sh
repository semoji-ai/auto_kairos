#!/bin/bash
# 새 데모가 생기는 대로 미리보기 렌더 → 변수 내보내기 → 도감 재빌드. dogam/.stop_watch 가 생기면 종료
cd "$(dirname "$0")/.."
for pass in $(seq 1 60); do
  [ -f dogam/.stop_watch ] && { echo "stop"; break; }
  miss=$(python3 -c "
import importlib.util as u,os; s=u.spec_from_file_location('rp','dogam/render_previews.py'); m=u.module_from_spec(s); s.loader.exec_module(m)
print(' '.join(i for i in m.demo_ids() if not (m.OUT / f'{i}.mp4').exists()))")
  if [ -n "$miss" ]; then
    echo "[$(date +%H:%M)] pass $pass: $(echo $miss | wc -w)편 렌더"
    python3 dogam/render_previews.py $miss 2>&1 | grep -E " ok| FAIL" | sed 's/FAIL.*/FAIL(재시도 예정)/'
    dogam/export_params.sh 2>&1 | tail -1
    python3 dogam/build_techniques.py > /dev/null 2>&1 && python3 dogam/build_viewer.py
  fi
  sleep 180
done
