/**
 * MiniMax → Anthropic API 호환 프록시 (tool_use 실행 루프 포함)
 * Python Anthropic SDK → 이 프록시 → MiniMax API
 *
 * 사용법:
 *   MINIMAX_API_KEY=xxx node server.mjs [--port 8091]
 *
 * Python에서:
 *   client = anthropic.Anthropic(base_url="http://localhost:8091", api_key="dummy")
 */

import { createServer } from "http";

const PORT = parseInt(process.argv.find(a => a.startsWith("--port="))?.split("=")[1] || "8091");
const MINIMAX_KEY = process.env.MINIMAX_API_KEY || "";
const MINIMAX_BASE = "https://api.minimax.io/anthropic/v1";
const MODEL_REMAP = {
  "MiniMax-M2.7": "MiniMax-M2.7",
  "MiniMax-M2.7-highspeed": "MiniMax-M2.7-highspeed",
  "minimax": "MiniMax-M2.7",
};

if (!MINIMAX_KEY) {
  console.error("⚠  MINIMAX_API_KEY 환경변수가 없습니다.");
  process.exit(1);
}

async function readBody(req) {
  return new Promise((res, rej) => {
    let data = "";
    req.on("data", c => data += c);
    req.on("end", () => res(data));
    req.on("error", rej);
  });
}

// MiniMax API 단일 호출
async function callMiniMax(body) {
  const resp = await fetch(`${MINIMAX_BASE}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": MINIMAX_KEY,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });
  const text = await resp.text();
  return { status: resp.status, text };
}

// WebSearch 도구 실행 (search.py 사용)
import { execFile } from "child_process";
import { promisify } from "util";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
const execFileAsync = promisify(execFile);
const __dirname = dirname(fileURLToPath(import.meta.url));

async function executeWebSearch(query) {
  try {
    const scriptPath = join(__dirname, "search.py");
    const { stdout } = await execFileAsync("python3", [scriptPath, query], { timeout: 15000 });
    return stdout.trim() || `"${query}" 검색 결과를 찾지 못했습니다.`;
  } catch (e) {
    return `검색 오류: ${e.message}`;
  }
}

// WebFetch 도구 실행
async function executeWebFetch(url) {
  try {
    const resp = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; KairosBot/1.0)" }
    });
    const html = await resp.text();
    // 태그 제거 후 최대 2000자
    const text = html.replace(/<script[\s\S]*?<\/script>/gi, "")
                     .replace(/<style[\s\S]*?<\/style>/gi, "")
                     .replace(/<[^>]+>/g, " ")
                     .replace(/\s+/g, " ")
                     .trim()
                     .slice(0, 2000);
    return text;
  } catch (e) {
    return `페치 오류: ${e.message}`;
  }
}

// 도구 실행 디스패처
async function executeTool(name, input) {
  console.log(`  🔧 도구 실행: ${name}`, JSON.stringify(input).slice(0, 80));
  if (name === "web_search") {
    return await executeWebSearch(input.query || input.q || "");
  }
  if (name === "web_fetch" || name === "WebFetch") {
    return await executeWebFetch(input.url || "");
  }
  return `알 수 없는 도구: ${name}`;
}

// tool_use 루프로 MiniMax 에이전트 실행
async function runAgentLoop(body) {
  const messages = [...(body.messages || [])];
  let iteration = 0;
  const MAX_ITER = 10;

  while (iteration < MAX_ITER) {
    iteration++;
    const reqBody = { ...body, messages };
    const { status, text } = await callMiniMax(reqBody);
    console.log(`← [iter=${iteration}] status=${status} ${text.slice(0, 100)}`);

    if (status !== 200) {
      return { status, text };
    }

    let parsed;
    try { parsed = JSON.parse(text); } catch { return { status, text }; }

    const hasToolUse = parsed.content?.some(b => b.type === "tool_use");
    if (!hasToolUse) {
      // 도구 호출 없음 — 최종 응답
      return { status, text };
    }

    // assistant 메시지 추가
    messages.push({ role: "assistant", content: parsed.content });

    // 도구 결과 수집
    const toolResults = [];
    for (const block of parsed.content) {
      if (block.type === "tool_use") {
        const result = await executeTool(block.name, block.input || {});
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: result,
        });
      }
    }

    // user 메시지에 tool_result 추가
    messages.push({ role: "user", content: toolResults });
  }

  return { status: 200, text: JSON.stringify({ error: "max iterations reached" }) };
}

const server = createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }

  if (req.url === "/health" || req.url === "/") {
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({ status: "ok", proxy: "minimax", tools: ["web_search", "web_fetch"] }));
  }

  if (req.method === "POST" && req.url?.includes("/messages")) {
    let body;
    try {
      const raw = await readBody(req);
      body = JSON.parse(raw);
    } catch (e) {
      res.writeHead(400, { "Content-Type": "application/json" });
      return res.end(JSON.stringify({ error: "invalid JSON" }));
    }

    const originalModel = body.model || "MiniMax-M2.7";
    body.model = MODEL_REMAP[originalModel] || "MiniMax-M2.7";

    const hasTools = body.tools?.length > 0;
    console.log(`→ [${new Date().toISOString()}] model=${body.model} messages=${body.messages?.length} tools=${hasTools ? body.tools.map(t=>t.name).join(",") : "none"}`);

    try {
      let result;
      if (hasTools) {
        // 도구 루프 실행
        result = await runAgentLoop(body);
      } else {
        result = await callMiniMax(body);
      }

      res.writeHead(result.status, { "Content-Type": "application/json" });
      res.end(result.text);
    } catch (e) {
      console.error("프록시 오류:", e);
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: String(e) }));
    }
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "not found", path: req.url }));
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`✓ MiniMax 프록시 실행 중: http://127.0.0.1:${PORT}`);
  console.log(`  → 업스트림: ${MINIMAX_BASE}`);
  console.log(`  → 도구 지원: web_search, web_fetch (에이전트 루프)`);
});
