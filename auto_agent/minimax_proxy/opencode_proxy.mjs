/**
 * OpenCode HTTP → Anthropic API 호환 프록시
 * Python Anthropic SDK → 이 프록시 → opencode serve REST API → MiniMax
 *
 * 사용법:
 *   # 터미널 1: opencode serve 시작
 *   opencode serve --port=8093 --pure
 *   # 터미널 2: 프록시 시작
 *   node opencode_proxy.mjs [--port=8092] [--serve-url=http://127.0.0.1:8093]
 *
 * Python에서:
 *   client = anthropic.Anthropic(base_url="http://localhost:8092", api_key="dummy")
 *
 * 특징:
 *   - subprocess 없이 opencode serve REST API 직접 호출
 *   - DB 잠금 없음, 빠른 응답
 *   - OpenCode의 모든 내장 도구 (webfetch, bash 등)
 *   - 각 요청마다 새 세션 생성 (상태 격리)
 */

import { createServer } from "http";
import { spawn } from "child_process";

const PORT = parseInt(process.argv.find(a => a.startsWith("--port="))?.split("=")[1] || "8092");
const SERVE_PORT = parseInt(process.argv.find(a => a.startsWith("--serve-port="))?.split("=")[1] || "8093");
const OPENCODE_BIN = process.env.OPENCODE_BIN || "/opt/homebrew/bin/opencode";
const DEFAULT_MODEL = process.env.OPENCODE_MODEL || "minimax/MiniMax-M2.7";
const SERVE_URL = process.env.OPENCODE_SERVE_URL ||
  process.argv.find(a => a.startsWith("--serve-url="))?.split("=").slice(1).join("=") ||
  `http://127.0.0.1:${SERVE_PORT}`;

let serveProcess = null;

async function readBody(req) {
  return new Promise((res, rej) => {
    let data = "";
    req.on("data", c => (data += c));
    req.on("end", () => res(data));
    req.on("error", rej);
  });
}

/** opencode serve 준비 확인 */
async function isServeReady() {
  try {
    const r = await fetch(`${SERVE_URL}/`);
    return r.status < 500;
  } catch {
    return false;
  }
}

/** opencode serve 자동 시작 */
async function ensureServe() {
  if (await isServeReady()) return;

  console.log(`  → opencode serve 시작 중 (포트: ${SERVE_PORT})...`);
  serveProcess = spawn(OPENCODE_BIN, ["serve", `--port=${SERVE_PORT}`, "--pure"], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env },
  });
  serveProcess.stderr?.on("data", d => {
    const msg = d.toString().trim();
    if (msg && !msg.includes("Warning")) console.log(`  [serve] ${msg}`);
  });

  for (let i = 0; i < 30; i++) {
    await new Promise(r => setTimeout(r, 500));
    if (await isServeReady()) {
      console.log(`  ✓ opencode serve 준비 완료: ${SERVE_URL}`);
      return;
    }
  }
  throw new Error(`opencode serve 시작 실패 (${SERVE_URL})`);
}

/** 새 세션 생성 */
async function createSession() {
  const r = await fetch(`${SERVE_URL}/session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!r.ok) throw new Error(`세션 생성 실패: ${r.status}`);
  return (await r.json()).id;
}

/** 모델 설정 (세션 생성 후) */
async function setSessionModel(sessionId, model) {
  try {
    // opencode는 기본 설정 모델을 사용하므로 별도 설정 불필요
    // 필요 시 여기에 model override 로직 추가
  } catch {}
}

/** 메시지 전송 및 응답 수신 */
async function sendMessage(sessionId, prompt) {
  const parts = [{ type: "text", text: prompt }];
  const r = await fetch(`${SERVE_URL}/session/${sessionId}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parts }),
    signal: AbortSignal.timeout(300_000),
  });
  if (!r.ok) {
    const err = await r.text();
    throw new Error(`메시지 전송 실패: ${r.status} ${err.slice(0, 200)}`);
  }
  return r.json();
}

/** Anthropic messages → 단일 프롬프트 */
function messagesToPrompt(messages, system) {
  const parts = [];
  if (system) parts.push(`[System]: ${system}`);
  for (const msg of messages) {
    const role = msg.role === "assistant" ? "Assistant" : "User";
    const content =
      typeof msg.content === "string"
        ? msg.content
        : msg.content.filter(b => b.type === "text").map(b => b.text).join(" ");
    if (content.trim()) parts.push(`[${role}]: ${content.trim()}`);
  }
  return parts.join("\n");
}

/** Anthropic API 호환 응답 */
function makeResponse(text, inputTokens, outputTokens) {
  return {
    id: `msg_oc_${Date.now()}`,
    type: "message",
    role: "assistant",
    content: [{ type: "text", text }],
    model: DEFAULT_MODEL,
    stop_reason: "end_turn",
    stop_sequence: null,
    usage: { input_tokens: inputTokens, output_tokens: outputTokens },
  };
}

const server = createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");

  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }

  if (req.url === "/health" || req.url === "/") {
    const ready = await isServeReady();
    res.writeHead(200, { "Content-Type": "application/json" });
    return res.end(JSON.stringify({
      status: ready ? "ok" : "serve_not_ready",
      proxy: "opencode-http",
      serve: SERVE_URL,
      serve_ready: ready,
      model: DEFAULT_MODEL,
    }));
  }

  if (req.method === "POST" && req.url?.includes("/messages")) {
    let body;
    try {
      body = JSON.parse(await readBody(req));
    } catch {
      res.writeHead(400, { "Content-Type": "application/json" });
      return res.end(JSON.stringify({ error: "invalid JSON" }));
    }

    const prompt = messagesToPrompt(body.messages || [], body.system || "");
    console.log(`→ [${new Date().toISOString()}] messages=${body.messages?.length} prompt=${prompt.slice(0,60).replace(/\n/g," ")}...`);

    try {
      await ensureServe();

      const sessionId = await createSession();
      console.log(`  session: ${sessionId}`);

      const start = Date.now();
      const msgData = await sendMessage(sessionId, prompt);
      const elapsed = ((Date.now() - start) / 1000).toFixed(1);

      // 응답 텍스트 추출
      let text = "";
      for (const part of msgData.parts || []) {
        if (part.type === "text") text += part.text || "";
      }

      const tokens = msgData.info?.tokens || {};
      console.log(`← 완료 (${elapsed}s) tokens=${tokens.output || "?"}`);

      if (!text.trim()) {
        res.writeHead(502, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ error: "empty response from opencode" }));
      }

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(makeResponse(text.trim(), tokens.input || 0, tokens.output || 0)));
    } catch (e) {
      console.error("오류:", e.message);
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "not found" }));
});

process.on("exit", () => serveProcess?.kill());
process.on("SIGINT", () => { serveProcess?.kill(); process.exit(0); });
process.on("SIGTERM", () => { serveProcess?.kill(); process.exit(0); });

server.listen(PORT, "127.0.0.1", async () => {
  console.log(`✓ OpenCode HTTP 프록시: http://127.0.0.1:${PORT}`);
  console.log(`  → 백엔드: ${SERVE_URL} (model: ${DEFAULT_MODEL})`);
  try {
    await ensureServe();
  } catch (e) {
    console.error(`  ⚠ ${e.message}`);
    console.error(`  → 수동 시작: opencode serve --port=${SERVE_PORT} --pure`);
  }
});
