// 도감용 변수 목록 내보내기: 각 미리보기 id → 스키마 설명
import { ENTRIES } from "../src/dogam/registry";
import { describeSchema } from "../src/params/p";
const out: Record<string, unknown> = {};
for (const e of ENTRIES) if (e.schema) out[e.id] = { name: e.name, params: describeSchema(e.schema) };
process.stdout.write(JSON.stringify(out, null, 1));
