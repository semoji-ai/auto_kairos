#!/bin/bash
# 기법 변수(스키마) → dogam/params.json   (Remotion 코드에서 직접 추출)
set -e
cd "$(dirname "$0")/../video"
node_modules/.bin/esbuild scripts/export-params.tsx --bundle --platform=node --format=cjs --jsx=automatic --loader:.json=json --log-level=error --outfile=/tmp/semoji_export_params.cjs
node /tmp/semoji_export_params.cjs > ../dogam/params.json
python3 -c "import json;d=json.load(open('../dogam/params.json'));print('변수 스키마', len(d), '개 기법,', sum(len(v['params']) for v in d.values()), '개 변수')"
