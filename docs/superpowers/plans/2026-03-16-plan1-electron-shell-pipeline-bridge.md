# Plan 1: Electron Shell + Pipeline Bridge 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Electron 데스크톱 앱 기본 셸을 만들고, 기존 Python 파이프라인을 subprocess로 연결하여 프로젝트 생성/목록/파이프라인 실행/진행률 표시가 동작하는 MVP를 완성한다.

**Architecture:** Electron(Vite + React 18 + TypeScript) 메인 프로세스에서 Python CLI(`auto-kairos`)를 subprocess로 호출하고, JSON-lines 기반 progress 파일을 chokidar로 감시하여 렌더러 프로세스에 IPC로 전달한다. SQLite DB는 better-sqlite3로 직접 읽어 프로젝트 목록/상태를 표시한다.

**Tech Stack:** Electron 33+, Vite 6, vite-plugin-electron, React 18, TypeScript 5.5, better-sqlite3, @electron/rebuild, chokidar, Zustand

**Spec:** `docs/superpowers/specs/2026-03-16-kairos-desktop-app-design.md`

---

## File Structure

```
kairos-app/                           (새 프로젝트 — auto_kairos_v3 외부)
├── package.json                      모노레포 루트 (npm workspaces)
├── tsconfig.base.json                공유 TS 설정
├── .gitignore
│
├── electron/                         Electron 메인 프로세스
│   ├── main.ts                       앱 진입점, BrowserWindow 생성
│   ├── preload.ts                    contextBridge IPC 노출
│   └── ipc/
│       ├── project.ipc.ts            프로젝트 CRUD IPC 핸들러
│       ├── pipeline.ipc.ts           파이프라인 실행/모니터 IPC
│       └── cli-manager.ipc.ts        LLM CLI 감지/설정 IPC
│
├── packages/
│   └── core/
│       ├── package.json
│       └── src/
│           ├── db/
│           │   └── project-db.ts     better-sqlite3 프로젝트 CRUD
│           ├── pipeline-bridge/
│           │   ├── runner.ts          Python subprocess 실행
│           │   ├── progress-watcher.ts chokidar JSONL 감시
│           │   └── types.ts          ProgressEvent, PipelineState 타입
│           └── cli-manager/
│               └── detect.ts         LLM CLI 바이너리 감지
│
├── src/                              렌더러 프로세스 (React)
│   ├── main.tsx                      React 진입점
│   ├── App.tsx                       라우팅 + 레이아웃
│   ├── stores/
│   │   ├── project-store.ts          프로젝트 상태 (Zustand)
│   │   └── pipeline-store.ts         파이프라인 실행 상태 (Zustand)
│   ├── pages/
│   │   ├── ProjectList.tsx           프로젝트 목록
│   │   ├── ProjectDetail.tsx         프로젝트 상세 (탭 구조 준비)
│   │   └── Settings.tsx              워크스페이스/LLM 설정
│   ├── components/
│   │   ├── Layout.tsx                사이드바 + 메인 영역
│   │   ├── ProjectCard.tsx           프로젝트 카드
│   │   ├── PipelineProgress.tsx      파이프라인 진행률 표시
│   │   └── PipelineLog.tsx           에이전트 로그 스트리밍
│   └── lib/
│       └── ipc.ts                    타입 안전 IPC 래퍼
│
├── tests/
│   ├── core/
│   │   ├── project-db.test.ts        DB CRUD 테스트
│   │   ├── runner.test.ts            subprocess 실행 테스트
│   │   ├── progress-watcher.test.ts  JSONL 파싱 테스트
│   │   └── detect.test.ts            CLI 감지 테스트
│   └── e2e/
│       └── app-launch.test.ts        Electron 실행 테스트
│
├── vite.config.ts                    Vite 설정 (React + Electron)
└── vitest.config.ts                  테스트용 경로 별칭 설정
```

**주의사항 (리뷰 반영):**
- Electron은 CJS 환경이므로 `vite-plugin-electron`으로 main/preload 빌드 필요
- `better-sqlite3`는 네이티브 모듈이므로 `@electron/rebuild` 필수
- 기존 `auto_agent.db`를 읽기 전용으로 열 것 (자체 스키마 생성 X)
- `@core/*` 경로 별칭은 `vitest.config.ts`에도 설정 필요
- Windows에서 `SIGTERM` 미지원 → 플랫폼별 프로세스 종료 처리
- `titleBarStyle: "hiddenInset"`은 macOS 전용 → 플랫폼 분기

---

## Chunk 1: 프로젝트 스캐폴딩 + Electron 기본 창

### Task 1: 모노레포 초기화

**Files:**
- Create: `kairos-app/package.json`
- Create: `kairos-app/tsconfig.base.json`
- Create: `kairos-app/.gitignore`

- [ ] **Step 1: 프로젝트 디렉토리 생성 + package.json**

```bash
mkdir -p ~/Desktop/kairos-app
cd ~/Desktop/kairos-app
```

```json
{
  "name": "kairos-app",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "workspaces": ["packages/*"],
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "electron:dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "electron:build": "vite build && electron-builder",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "main": "dist-electron/main.js",
  "devDependencies": {
    "electron": "^33.0.0",
    "electron-builder": "^25.0.0",
    "@electron/rebuild": "^3.6.0",
    "vite": "^6.0.0",
    "vite-plugin-electron": "^0.28.0",
    "vite-plugin-electron-renderer": "^0.14.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0",
    "concurrently": "^9.0.0",
    "wait-on": "^8.0.0"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.26.0",
    "zustand": "^5.0.0",
    "better-sqlite3": "^11.0.0",
    "chokidar": "^4.0.0"
  },
  "build": {
    "appId": "com.kairos.studio",
    "productName": "Kairos Studio",
    "mac": {
      "target": "dmg"
    },
    "win": {
      "target": "nsis"
    },
    "files": [
      "dist/**/*",
      "electron/**/*"
    ]
  }
}
```

- [ ] **Step 2: tsconfig.base.json 생성**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "jsx": "react-jsx",
    "outDir": "dist",
    "rootDir": ".",
    "baseUrl": ".",
    "paths": {
      "@core/*": ["packages/core/src/*"],
      "@/*": ["src/*"]
    }
  },
  "include": ["src", "electron", "packages"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 3: .gitignore 생성**

```
node_modules/
dist/
out/
*.db
.env
.DS_Store
```

- [ ] **Step 4: npm install + electron-rebuild**

Run: `cd ~/Desktop/kairos-app && npm install && npx @electron/rebuild`
Expected: node_modules/ 생성, better-sqlite3 네이티브 모듈이 Electron용으로 리빌드

- [ ] **Step 5: git init + 초기 커밋**

```bash
cd ~/Desktop/kairos-app
git init
git add .
git commit -m "chore: monorepo scaffolding with Electron + Vite + React"
```

---

### Task 2: Electron 메인 프로세스 + 기본 창

**Files:**
- Create: `kairos-app/electron/main.ts`
- Create: `kairos-app/electron/preload.ts`
- Create: `kairos-app/vite.config.ts`

- [ ] **Step 1: vite.config.ts 생성 (Electron 플러그인 포함)**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import electron from "vite-plugin-electron";
import renderer from "vite-plugin-electron-renderer";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        entry: "electron/main.ts",
        vite: {
          build: { outDir: "dist-electron" },
        },
      },
      {
        entry: "electron/preload.ts",
        onstart({ startup }) { startup(); },
        vite: {
          build: { outDir: "dist-electron" },
        },
      },
    ]),
    renderer(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@core": path.resolve(__dirname, "packages/core/src"),
    },
  },
  build: {
    outDir: "dist",
  },
});
```

- [ ] **Step 1b: vitest.config.ts 생성 (테스트용 경로 별칭)**

```typescript
import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  test: {
    globals: true,
  },
  resolve: {
    alias: {
      "@core": path.resolve(__dirname, "packages/core/src"),
      "@": path.resolve(__dirname, "src"),
    },
  },
});
```

- [ ] **Step 2: electron/main.ts 생성**

```typescript
import { app, BrowserWindow, ipcMain } from "electron";
import path from "path";

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    webPreferences: {
      preload: path.join(__dirname, "preload.mjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
  });

  if (process.env.NODE_ENV === "development") {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

export { mainWindow };
```

- [ ] **Step 3: electron/preload.ts 생성**

```typescript
import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("kairos", {
  // 프로젝트
  listProjects: () => ipcRenderer.invoke("project:list"),
  getProject: (slug: string) => ipcRenderer.invoke("project:get", slug),
  createProject: (data: { name: string; topic: string }) =>
    ipcRenderer.invoke("project:create", data),

  // 파이프라인
  runPipeline: (slug: string, opts?: { fromStep?: string }) =>
    ipcRenderer.invoke("pipeline:run", slug, opts),
  stopPipeline: (slug: string) => ipcRenderer.invoke("pipeline:stop", slug),
  onPipelineProgress: (callback: (event: unknown) => void) => {
    const listener = (_: unknown, data: unknown) => callback(data);
    ipcRenderer.on("pipeline:progress", listener);
    return () => ipcRenderer.removeListener("pipeline:progress", listener);
  },

  // 설정
  getSettings: () => ipcRenderer.invoke("settings:get"),
  setSettings: (settings: Record<string, unknown>) =>
    ipcRenderer.invoke("settings:set", settings),
  detectCLI: (provider: string) =>
    ipcRenderer.invoke("cli:detect", provider),
});
```

- [ ] **Step 4: index.html 생성**

Create: `kairos-app/index.html`

```html
<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Kairos Studio</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: 최소 React 진입점 생성**

Create: `kairos-app/src/main.tsx`

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

function App() {
  return <h1>Kairos Studio</h1>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 6: Electron 창 열기 확인**

Run: `cd ~/Desktop/kairos-app && npm run electron:dev`
Expected: Electron 창에 "Kairos Studio" 텍스트 표시

- [ ] **Step 7: 커밋**

```bash
git add .
git commit -m "feat: Electron + Vite + React 기본 창"
```

---

## Chunk 2: Core 패키지 — DB + Pipeline Bridge

### Task 3: better-sqlite3 프로젝트 DB 래퍼

**Files:**
- Create: `kairos-app/packages/core/package.json`
- Create: `kairos-app/packages/core/src/db/project-db.ts`
- Test: `kairos-app/tests/core/project-db.test.ts`

- [ ] **Step 1: core 패키지 초기화**

Create: `kairos-app/packages/core/package.json`

```json
{
  "name": "@kairos/core",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "src/index.ts",
  "dependencies": {
    "better-sqlite3": "^11.0.0",
    "chokidar": "^4.0.0"
  },
  "devDependencies": {
    "@types/better-sqlite3": "^7.6.0"
  }
}
```

- [ ] **Step 2: 프로젝트 DB 실패 테스트 작성**

```typescript
// tests/core/project-db.test.ts
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { ProjectDB } from "@core/db/project-db";
import fs from "fs";
import path from "path";
import os from "os";

describe("ProjectDB", () => {
  let db: ProjectDB;
  let dbPath: string;

  beforeEach(() => {
    dbPath = path.join(os.tmpdir(), `kairos-test-${Date.now()}.db`);
    db = new ProjectDB(dbPath);
  });

  afterEach(() => {
    db.close();
    if (fs.existsSync(dbPath)) fs.unlinkSync(dbPath);
  });

  it("should list projects from existing DB", () => {
    const projects = db.listProjects();
    expect(Array.isArray(projects)).toBe(true);
  });

  it("should return null for non-existent project", () => {
    const project = db.getProject("non-existent");
    expect(project).toBeNull();
  });

  it("should return project by slug", () => {
    // Insert a test project directly
    db.createProject({ name: "테스트", slug: "test-project", topic: "테스트 주제" });
    const project = db.getProject("test-project");
    expect(project).not.toBeNull();
    expect(project!.slug).toBe("test-project");
    expect(project!.name).toBe("테스트");
  });

  it("should list all projects", () => {
    db.createProject({ name: "A", slug: "a", topic: "topic-a" });
    db.createProject({ name: "B", slug: "b", topic: "topic-b" });
    const projects = db.listProjects();
    expect(projects.length).toBe(2);
  });

  it("should return pipeline history", () => {
    db.createProject({ name: "Test", slug: "test", topic: "topic" });
    const project = db.getProject("test")!;
    const history = db.getPipelineHistory(project.id);
    expect(Array.isArray(history)).toBe(true);
  });
});
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/project-db.test.ts`
Expected: FAIL — `@core/db/project-db` 모듈 없음

- [ ] **Step 4: project-db.ts 구현**

```typescript
// packages/core/src/db/project-db.ts
import Database from "better-sqlite3";

export interface Project {
  id: number;
  name: string;
  slug: string;
  status: string;
  topic: string | null;
  theme: string;
  scene_count: number;
  total_duration_sec: number;
  config: Record<string, unknown> | null;
  output_dir: string;
  created_at: string;
  updated_at: string;
}

export interface PipelineRun {
  id: number;
  project_id: number;
  phase: string;
  step: string;
  step_name: string | null;
  agent_or_module: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_sec: number | null;
  cost_tokens_in: number;
  cost_tokens_out: number;
  cost_usd: number;
  error_log: string | null;
}

interface CreateProjectInput {
  name: string;
  slug: string;
  topic: string;
  theme?: string;
  config?: Record<string, unknown>;
}

export class ProjectDB {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.initSchemaIfNeeded();
  }

  /**
   * 기존 auto_agent.db를 여는 경우 스키마 생성을 건너뛴다.
   * 새 DB를 만드는 경우(테스트 등)에만 initSchema를 호출한다.
   */
  private initSchemaIfNeeded(): void {
    // 이미 projects 테이블이 존재하면 기존 DB → 스키마 생성 스킵
    const tableExists = this.db
      .prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
      .get();
    if (tableExists) return;

    // 새 DB — 기존 Python schema.sql과 동일한 구조 생성
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        status TEXT DEFAULT 'created'
          CHECK (status IN ('created','in_progress','completed','archived','failed')),
        topic TEXT,
        theme TEXT DEFAULT 'simple',
        scene_count INTEGER DEFAULT 0,
        total_duration_sec REAL DEFAULT 0.0,
        config TEXT,
        output_dir TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE TABLE IF NOT EXISTS pipeline_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        phase TEXT NOT NULL,
        step TEXT NOT NULL,
        step_name TEXT,
        agent_or_module TEXT,
        status TEXT NOT NULL DEFAULT 'pending'
          CHECK (status IN ('pending','running','completed','failed','skipped')),
        started_at TEXT,
        completed_at TEXT,
        duration_sec REAL,
        cost_tokens_in INTEGER DEFAULT 0,
        cost_tokens_out INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0.0,
        error_log TEXT,
        metadata TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX IF NOT EXISTS idx_pipeline_runs_project ON pipeline_runs(project_id, phase, step);
    `);
  }

  listProjects(status?: string): Project[] {
    const query = status
      ? "SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC"
      : "SELECT * FROM projects ORDER BY updated_at DESC";
    const rows = status
      ? this.db.prepare(query).all(status)
      : this.db.prepare(query).all();
    return (rows as Record<string, unknown>[]).map(this.parseProject);
  }

  getProject(slug: string): Project | null {
    const row = this.db
      .prepare("SELECT * FROM projects WHERE slug = ?")
      .get(slug) as Record<string, unknown> | undefined;
    return row ? this.parseProject(row) : null;
  }

  createProject(input: CreateProjectInput): number {
    const stmt = this.db.prepare(`
      INSERT INTO projects (name, slug, topic, theme, config, output_dir)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      input.name,
      input.slug,
      input.topic,
      input.theme ?? "simple",
      input.config ? JSON.stringify(input.config) : null,
      ""
    );
    return Number(result.lastInsertRowid);
  }

  getPipelineHistory(projectId: number): PipelineRun[] {
    return this.db
      .prepare(
        "SELECT * FROM pipeline_runs WHERE project_id = ? ORDER BY created_at DESC"
      )
      .all(projectId) as PipelineRun[];
  }

  getCostSummary(projectId?: number): {
    total_runs: number;
    total_tokens_in: number;
    total_tokens_out: number;
    total_usd: number;
  } {
    const query = projectId
      ? "SELECT COUNT(*) as total_runs, COALESCE(SUM(cost_tokens_in),0) as total_tokens_in, COALESCE(SUM(cost_tokens_out),0) as total_tokens_out, COALESCE(SUM(cost_usd),0) as total_usd FROM pipeline_runs WHERE project_id = ?"
      : "SELECT COUNT(*) as total_runs, COALESCE(SUM(cost_tokens_in),0) as total_tokens_in, COALESCE(SUM(cost_tokens_out),0) as total_tokens_out, COALESCE(SUM(cost_usd),0) as total_usd FROM pipeline_runs";
    const row = projectId
      ? (this.db.prepare(query).get(projectId) as Record<string, number>)
      : (this.db.prepare(query).get() as Record<string, number>);
    return {
      total_runs: row.total_runs,
      total_tokens_in: row.total_tokens_in,
      total_tokens_out: row.total_tokens_out,
      total_usd: row.total_usd,
    };
  }

  close(): void {
    this.db.close();
  }

  private parseProject(row: Record<string, unknown>): Project {
    return {
      ...(row as unknown as Project),
      config: row.config ? JSON.parse(row.config as string) : null,
    };
  }
}
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/project-db.test.ts`
Expected: 5 tests PASS

- [ ] **Step 6: 커밋**

```bash
git add packages/core/ tests/core/project-db.test.ts
git commit -m "feat: ProjectDB — better-sqlite3 프로젝트 CRUD"
```

---

### Task 4: Pipeline Bridge — Python subprocess 실행

**Files:**
- Create: `kairos-app/packages/core/src/pipeline-bridge/types.ts`
- Create: `kairos-app/packages/core/src/pipeline-bridge/runner.ts`
- Test: `kairos-app/tests/core/runner.test.ts`

- [ ] **Step 1: 타입 정의**

```typescript
// packages/core/src/pipeline-bridge/types.ts
export interface ProgressEvent {
  agent: string;
  text: string;
  level: "info" | "success" | "warning" | "error";
  timestamp: number;
  phase?: string;
  data?: Record<string, unknown>;
}

export interface PipelineState {
  project_slug: string;
  started_at: string;
  finished_at?: string;
  config: Record<string, unknown>;
  completed_steps: string[];
  failed_steps: string[];
  skipped_steps: string[];
  results: Record<
    string,
    {
      step_id: string;
      status: "completed" | "failed" | "skipped";
      duration_sec: number;
      error: string;
      output_files: string[];
      cost_info: Record<string, unknown>;
    }
  >;
}

export interface RunPipelineOptions {
  projectSlug: string;
  workspaceDir: string;
  fromStep?: string;
  onlyStep?: string;
  pythonBin?: string;
  onProgress?: (event: ProgressEvent) => void;
  onStdout?: (line: string) => void;
  onStderr?: (line: string) => void;
}
```

- [ ] **Step 2: runner 실패 테스트 작성**

```typescript
// tests/core/runner.test.ts
import { describe, it, expect, vi } from "vitest";
import { PipelineRunner } from "@core/pipeline-bridge/runner";
import os from "os";
import path from "path";

describe("PipelineRunner", () => {
  it("should resolve python binary on current platform", () => {
    const runner = new PipelineRunner();
    const bin = runner.resolvePythonBin();
    // "python3" on macOS/Linux, "python" on Windows
    expect(typeof bin).toBe("string");
    expect(bin.length).toBeGreaterThan(0);
  });

  it("should build correct subprocess args", () => {
    const runner = new PipelineRunner();
    const args = runner.buildArgs({
      projectSlug: "test-project",
      workspaceDir: "/tmp/workspace",
    });
    expect(args).toContain("run");
    expect(args).toContain("--project");
    expect(args).toContain("test-project");
  });

  it("should build args with fromStep", () => {
    const runner = new PipelineRunner();
    const args = runner.buildArgs({
      projectSlug: "test",
      workspaceDir: "/tmp/ws",
      fromStep: "step_3",
    });
    expect(args).toContain("--from");
    expect(args).toContain("step_3");
  });

  it("should build correct env vars", () => {
    const runner = new PipelineRunner();
    const env = runner.buildEnv("/tmp/workspace", "test-slug");
    expect(env.AUTO_AGENT_WORKSPACE).toBe("/tmp/workspace");
    expect(env.PROJECT_NAME).toBe("test-slug");
    expect(env.PROGRESS_FILE).toContain("test-slug");
  });
});
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/runner.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 4: runner.ts 구현**

```typescript
// packages/core/src/pipeline-bridge/runner.ts
import { spawn, ChildProcess } from "child_process";
import path from "path";
import os from "os";
import type { RunPipelineOptions, ProgressEvent } from "./types";

export class PipelineRunner {
  private process: ChildProcess | null = null;

  resolvePythonBin(override?: string): string {
    if (override) return override;
    return os.platform() === "win32" ? "python" : "python3";
  }

  buildArgs(opts: Pick<RunPipelineOptions, "projectSlug" | "fromStep" | "onlyStep">): string[] {
    // auto-kairos CLI 바이너리 호출 (pip install 후 PATH에 존재)
    // 또는 python -m auto_agent.cli 방식 폴백
    const args = ["-m", "auto_agent.cli", "run", "--project", opts.projectSlug,
      "--workspace", opts.workspaceDir ?? ""];
    if (opts.fromStep) {
      args.push("--from", opts.fromStep);
    }
    if (opts.onlyStep) {
      args.push("--only", opts.onlyStep);
    }
    return args;
  }

  buildEnv(workspaceDir: string, projectSlug: string): Record<string, string> {
    const progressFile = path.join(
      workspaceDir,
      "output",
      projectSlug,
      `.progress_${Date.now()}.jsonl`
    );
    return {
      ...process.env as Record<string, string>,
      AUTO_AGENT_WORKSPACE: workspaceDir,
      PROJECT_NAME: projectSlug,
      PROGRESS_FILE: progressFile,
    };
  }

  run(opts: RunPipelineOptions): ChildProcess {
    const pythonBin = this.resolvePythonBin(opts.pythonBin);
    const args = this.buildArgs(opts);
    const env = this.buildEnv(opts.workspaceDir, opts.projectSlug);

    this.process = spawn(pythonBin, args, {
      cwd: opts.workspaceDir,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    if (this.process.stdout) {
      let buffer = "";
      this.process.stdout.on("data", (chunk: Buffer) => {
        buffer += chunk.toString();
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.trim()) opts.onStdout?.(line);
        }
      });
    }

    if (this.process.stderr) {
      let buffer = "";
      this.process.stderr.on("data", (chunk: Buffer) => {
        buffer += chunk.toString();
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (line.trim()) opts.onStderr?.(line);
        }
      });
    }

    return this.process;
  }

  stop(): void {
    if (this.process && !this.process.killed) {
      if (os.platform() === "win32") {
        // Windows: SIGTERM 미지원, taskkill로 프로세스 트리 종료
        spawn("taskkill", ["/pid", String(this.process.pid), "/T", "/F"]);
      } else {
        this.process.kill("SIGTERM");
      }
      this.process = null;
    }
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }
}
```

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/runner.test.ts`
Expected: 4 tests PASS

- [ ] **Step 6: 커밋**

```bash
git add packages/core/src/pipeline-bridge/ tests/core/runner.test.ts
git commit -m "feat: PipelineRunner — Python subprocess 실행"
```

---

### Task 5: Progress Watcher — JSONL 파일 감시

**Files:**
- Create: `kairos-app/packages/core/src/pipeline-bridge/progress-watcher.ts`
- Test: `kairos-app/tests/core/progress-watcher.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

```typescript
// tests/core/progress-watcher.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import { ProgressWatcher } from "@core/pipeline-bridge/progress-watcher";
import fs from "fs";
import path from "path";
import os from "os";

describe("ProgressWatcher", () => {
  let watchDir: string;
  let watcher: ProgressWatcher;

  afterEach(() => {
    watcher?.stop();
  });

  it("should parse valid JSONL line", () => {
    const line = '{"agent":"tts","text":"씬 1 완료","level":"success","timestamp":1710000000}';
    const event = ProgressWatcher.parseLine(line);
    expect(event).not.toBeNull();
    expect(event!.agent).toBe("tts");
    expect(event!.level).toBe("success");
  });

  it("should return null for invalid JSON", () => {
    const event = ProgressWatcher.parseLine("not json");
    expect(event).toBeNull();
  });

  it("should return null for empty line", () => {
    const event = ProgressWatcher.parseLine("");
    expect(event).toBeNull();
  });

  it("should emit events when JSONL file is appended", async () => {
    watchDir = path.join(os.tmpdir(), `kairos-watch-${Date.now()}`);
    fs.mkdirSync(watchDir, { recursive: true });

    const events: unknown[] = [];
    watcher = new ProgressWatcher(watchDir);
    watcher.on("progress", (event) => events.push(event));
    watcher.start();

    // Simulate writing a progress file
    const progressFile = path.join(watchDir, ".progress_test.jsonl");
    fs.writeFileSync(
      progressFile,
      '{"agent":"test","text":"hello","level":"info","timestamp":1}\n'
    );

    // Wait for chokidar to detect
    await new Promise((r) => setTimeout(r, 500));
    expect(events.length).toBeGreaterThanOrEqual(1);

    fs.rmSync(watchDir, { recursive: true });
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/progress-watcher.test.ts`
Expected: FAIL

- [ ] **Step 3: progress-watcher.ts 구현**

```typescript
// packages/core/src/pipeline-bridge/progress-watcher.ts
import { EventEmitter } from "events";
import { watch, FSWatcher } from "chokidar";
import fs from "fs";
import path from "path";
import type { ProgressEvent } from "./types";

export class ProgressWatcher extends EventEmitter {
  private watcher: FSWatcher | null = null;
  private filePositions: Map<string, number> = new Map();
  private watchDir: string;

  constructor(watchDir: string) {
    super();
    this.watchDir = watchDir;
  }

  static parseLine(line: string): ProgressEvent | null {
    const trimmed = line.trim();
    if (!trimmed) return null;
    try {
      const obj = JSON.parse(trimmed);
      if (!obj.agent || !obj.text) return null;
      return {
        agent: obj.agent,
        text: obj.text,
        level: obj.level ?? "info",
        timestamp: obj.timestamp ?? Date.now() / 1000,
        phase: obj.phase,
        data: obj.data,
      };
    } catch {
      return null;
    }
  }

  start(): void {
    const pattern = path.join(this.watchDir, ".progress_*.jsonl");
    this.watcher = watch(pattern, {
      persistent: true,
      ignoreInitial: false,
      awaitWriteFinish: { stabilityThreshold: 100, pollInterval: 50 },
    });

    this.watcher.on("add", (filePath) => this.readNewLines(filePath));
    this.watcher.on("change", (filePath) => this.readNewLines(filePath));
  }

  stop(): void {
    this.watcher?.close();
    this.watcher = null;
    this.filePositions.clear();
  }

  private readNewLines(filePath: string): void {
    const pos = this.filePositions.get(filePath) ?? 0;
    const content = fs.readFileSync(filePath, "utf-8");
    const newContent = content.slice(pos);
    this.filePositions.set(filePath, content.length);

    const lines = newContent.split("\n");
    for (const line of lines) {
      const event = ProgressWatcher.parseLine(line);
      if (event) {
        this.emit("progress", event);
      }
    }
  }
}
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/progress-watcher.test.ts`
Expected: 4 tests PASS

- [ ] **Step 5: 커밋**

```bash
git add packages/core/src/pipeline-bridge/progress-watcher.ts tests/core/progress-watcher.test.ts
git commit -m "feat: ProgressWatcher — chokidar JSONL 파일 감시"
```

---

### Task 6: LLM CLI 감지

**Files:**
- Create: `kairos-app/packages/core/src/cli-manager/detect.ts`
- Test: `kairos-app/tests/core/detect.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

```typescript
// tests/core/detect.test.ts
import { describe, it, expect } from "vitest";
import { detectCLI, type CLIInfo } from "@core/cli-manager/detect";

describe("detectCLI", () => {
  it("should return CLIInfo with found=false for non-existent binary", async () => {
    const result = await detectCLI("nonexistent-binary-xyz-12345");
    expect(result.found).toBe(false);
    expect(result.path).toBeNull();
  });

  it("should detect node binary (known to exist)", async () => {
    const result = await detectCLI("node");
    expect(result.found).toBe(true);
    expect(result.path).not.toBeNull();
    expect(result.version).toBeDefined();
  });

  it("should return provider info for claude", async () => {
    const result = await detectCLI("claude");
    // May or may not be installed, but structure should be correct
    expect(typeof result.found).toBe("boolean");
    expect(result.provider).toBe("claude");
  });
});
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/detect.test.ts`
Expected: FAIL

- [ ] **Step 3: detect.ts 구현**

```typescript
// packages/core/src/cli-manager/detect.ts
import { execFile } from "child_process";
import { promisify } from "util";
import os from "os";

const execFileAsync = promisify(execFile);

export interface CLIInfo {
  provider: string;
  found: boolean;
  path: string | null;
  version: string | null;
}

const PROVIDER_MAP: Record<string, { versionFlag: string }> = {
  claude: { versionFlag: "--version" },
  gemini: { versionFlag: "--version" },
  codex: { versionFlag: "--version" },
  node: { versionFlag: "--version" },
};

export async function detectCLI(binaryName: string): Promise<CLIInfo> {
  const provider = binaryName;
  const whichCmd = os.platform() === "win32" ? "where" : "which";

  try {
    const { stdout: pathOut } = await execFileAsync(whichCmd, [binaryName], {
      timeout: 5000,
    });
    const binPath = pathOut.trim().split("\n")[0];

    let version: string | null = null;
    const config = PROVIDER_MAP[binaryName];
    if (config) {
      try {
        const { stdout: verOut } = await execFileAsync(
          binPath,
          [config.versionFlag],
          { timeout: 5000 }
        );
        version = verOut.trim().split("\n")[0];
      } catch {
        // Version check failed, but binary exists
      }
    }

    return { provider, found: true, path: binPath, version };
  } catch {
    return { provider, found: false, path: null, version: null };
  }
}
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd ~/Desktop/kairos-app && npx vitest run tests/core/detect.test.ts`
Expected: 3 tests PASS

- [ ] **Step 5: core index.ts 작성**

```typescript
// packages/core/src/index.ts
export { ProjectDB } from "./db/project-db";
export type { Project, PipelineRun } from "./db/project-db";
export { PipelineRunner } from "./pipeline-bridge/runner";
export { ProgressWatcher } from "./pipeline-bridge/progress-watcher";
export type { ProgressEvent, PipelineState, RunPipelineOptions } from "./pipeline-bridge/types";
export { detectCLI } from "./cli-manager/detect";
export type { CLIInfo } from "./cli-manager/detect";
```

- [ ] **Step 6: 커밋**

```bash
git add packages/core/ tests/core/detect.test.ts
git commit -m "feat: CLI 감지 + core 패키지 index export"
```

---

## Chunk 3: Electron IPC + React UI

### Task 7: IPC 핸들러 연결

**Files:**
- Create: `kairos-app/electron/ipc/project.ipc.ts`
- Create: `kairos-app/electron/ipc/pipeline.ipc.ts`
- Create: `kairos-app/electron/ipc/cli-manager.ipc.ts`
- Modify: `kairos-app/electron/main.ts`

- [ ] **Step 1: project.ipc.ts 생성**

```typescript
// electron/ipc/project.ipc.ts
import { ipcMain } from "electron";
import { ProjectDB } from "@kairos/core";

let db: ProjectDB | null = null;

export function getDB(): ProjectDB {
  if (!db) throw new Error("DB not initialized. Set workspace first.");
  return db;
}

export function initDB(dbPath: string): void {
  if (db) db.close();
  db = new ProjectDB(dbPath);
}

export function registerProjectIPC(): void {
  ipcMain.handle("project:list", () => {
    return getDB().listProjects();
  });

  ipcMain.handle("project:get", (_, slug: string) => {
    return getDB().getProject(slug);
  });

  ipcMain.handle("project:create", (_, data: { name: string; topic: string }) => {
    const slug = data.name
      .replace(/\s+/g, "_")
      .replace(/[^\w가-힣_-]/g, "")
      .slice(0, 50);
    return getDB().createProject({ ...data, slug });
  });
}
```

- [ ] **Step 2: pipeline.ipc.ts 생성**

```typescript
// electron/ipc/pipeline.ipc.ts
import { ipcMain, BrowserWindow } from "electron";
import { PipelineRunner, ProgressWatcher } from "@kairos/core";
import type { ProgressEvent } from "@kairos/core";
import path from "path";
import { getDB } from "./project.ipc";

const runners: Map<string, PipelineRunner> = new Map();
const watchers: Map<string, ProgressWatcher> = new Map();

export function registerPipelineIPC(getWindow: () => BrowserWindow | null): void {
  ipcMain.handle(
    "pipeline:run",
    async (_, slug: string, opts?: { fromStep?: string; workspaceDir?: string }) => {
      const workspaceDir = opts?.workspaceDir ?? process.env.AUTO_AGENT_WORKSPACE ?? process.cwd();
      const project = getDB().getProject(slug);
      if (!project) throw new Error(`Project not found: ${slug}`);

      const runner = new PipelineRunner();
      runners.set(slug, runner);

      // Start progress watcher
      const projectDir = path.join(workspaceDir, "output", slug);
      const watcher = new ProgressWatcher(projectDir);
      watchers.set(slug, watcher);

      watcher.on("progress", (event: ProgressEvent) => {
        getWindow()?.webContents.send("pipeline:progress", {
          slug,
          ...event,
        });
      });
      watcher.start();

      // Run pipeline
      const child = runner.run({
        projectSlug: slug,
        workspaceDir,
        fromStep: opts?.fromStep,
        onStdout: (line) => {
          getWindow()?.webContents.send("pipeline:progress", {
            slug,
            agent: "system",
            text: line,
            level: "info",
            timestamp: Date.now() / 1000,
          });
        },
        onStderr: (line) => {
          getWindow()?.webContents.send("pipeline:progress", {
            slug,
            agent: "system",
            text: line,
            level: "error",
            timestamp: Date.now() / 1000,
          });
        },
      });

      child.on("exit", (code) => {
        watcher.stop();
        watchers.delete(slug);
        runners.delete(slug);
        getWindow()?.webContents.send("pipeline:progress", {
          slug,
          agent: "system",
          text: code === 0 ? "파이프라인 완료" : `파이프라인 종료 (code: ${code})`,
          level: code === 0 ? "success" : "error",
          timestamp: Date.now() / 1000,
        });
      });

      return { started: true, slug };
    }
  );

  ipcMain.handle("pipeline:stop", (_, slug: string) => {
    const runner = runners.get(slug);
    if (runner) {
      runner.stop();
      runners.delete(slug);
    }
    const watcher = watchers.get(slug);
    if (watcher) {
      watcher.stop();
      watchers.delete(slug);
    }
    return { stopped: true, slug };
  });
}
```

- [ ] **Step 3: cli-manager.ipc.ts 생성**

```typescript
// electron/ipc/cli-manager.ipc.ts
import { ipcMain } from "electron";
import { detectCLI } from "@kairos/core";

import fs from "fs";
import path from "path";
import os from "os";
import { initDB } from "./project.ipc";

const SETTINGS_DIR = path.join(os.homedir(), ".kairos");
const SETTINGS_PATH = path.join(SETTINGS_DIR, "settings.json");

interface AppSettings {
  workspaceDir: string;
  llm: { provider: string; binary: string; verified: boolean };
}

function loadSettings(): AppSettings {
  try {
    if (fs.existsSync(SETTINGS_PATH)) {
      return JSON.parse(fs.readFileSync(SETTINGS_PATH, "utf-8"));
    }
  } catch { /* ignore */ }
  return {
    workspaceDir: process.env.AUTO_AGENT_WORKSPACE ?? "",
    llm: { provider: "claude-code", binary: "", verified: false },
  };
}

function saveSettings(settings: AppSettings): void {
  fs.mkdirSync(SETTINGS_DIR, { recursive: true });
  fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2));
}

export function registerCLIManagerIPC(): void {
  ipcMain.handle("cli:detect", async (_, provider: string) => {
    return detectCLI(provider);
  });

  ipcMain.handle("settings:get", () => {
    return loadSettings();
  });

  ipcMain.handle("settings:set", (_, updates: Partial<AppSettings>) => {
    const current = loadSettings();
    const merged = { ...current, ...updates };
    saveSettings(merged);

    // 워크스페이스 변경 시 DB 재연결
    if (updates.workspaceDir) {
      const dbPath = path.join(updates.workspaceDir, "auto_agent.db");
      if (fs.existsSync(dbPath)) {
        initDB(dbPath);
      }
    }
    return { saved: true };
  });
}

/** 앱 시작 시 저장된 워크스페이스로 DB 초기화 */
export function initSettingsOnStartup(): void {
  const settings = loadSettings();
  if (settings.workspaceDir) {
    const dbPath = path.join(settings.workspaceDir, "auto_agent.db");
    if (fs.existsSync(dbPath)) {
      initDB(dbPath);
    }
  }
}
```

- [ ] **Step 4: main.ts에 IPC 등록**

`electron/main.ts`를 수정하여 IPC 핸들러를 등록:

```typescript
// electron/main.ts 하단에 추가
import { registerProjectIPC } from "./ipc/project.ipc";
import { registerPipelineIPC } from "./ipc/pipeline.ipc";
import { registerCLIManagerIPC, initSettingsOnStartup } from "./ipc/cli-manager.ipc";

app.whenReady().then(() => {
  registerProjectIPC();
  registerPipelineIPC(() => mainWindow);
  registerCLIManagerIPC();
  initSettingsOnStartup(); // 저장된 워크스페이스로 DB 자동 연결
  createWindow();
});
```

- [ ] **Step 5: 커밋**

```bash
git add electron/
git commit -m "feat: IPC 핸들러 — 프로젝트/파이프라인/CLI 관리"
```

---

### Task 8: React UI — 프로젝트 목록 + 파이프라인 실행

**Files:**
- Create: `kairos-app/src/lib/ipc.ts`
- Create: `kairos-app/src/stores/project-store.ts`
- Create: `kairos-app/src/stores/pipeline-store.ts`
- Create: `kairos-app/src/components/Layout.tsx`
- Create: `kairos-app/src/components/ProjectCard.tsx`
- Create: `kairos-app/src/components/PipelineProgress.tsx`
- Create: `kairos-app/src/components/PipelineLog.tsx`
- Create: `kairos-app/src/pages/ProjectList.tsx`
- Create: `kairos-app/src/pages/ProjectDetail.tsx`
- Create: `kairos-app/src/pages/Settings.tsx`
- Modify: `kairos-app/src/App.tsx`
- Modify: `kairos-app/src/main.tsx`

- [ ] **Step 1: IPC 타입 래퍼**

```typescript
// src/lib/ipc.ts
import type { Project, CLIInfo, ProgressEvent } from "@kairos/core";

interface KairosAPI {
  listProjects: () => Promise<Project[]>;
  getProject: (slug: string) => Promise<Project | null>;
  createProject: (data: { name: string; topic: string }) => Promise<number>;
  runPipeline: (slug: string, opts?: { fromStep?: string }) => Promise<{ started: boolean }>;
  stopPipeline: (slug: string) => Promise<{ stopped: boolean }>;
  onPipelineProgress: (callback: (event: ProgressEvent & { slug: string }) => void) => () => void;
  getSettings: () => Promise<{ workspaceDir: string; llm: { provider: string; binary: string; verified: boolean } }>;
  setSettings: (settings: Record<string, unknown>) => Promise<{ saved: boolean }>;
  detectCLI: (provider: string) => Promise<CLIInfo>;
}

export const kairos: KairosAPI = (window as unknown as { kairos: KairosAPI }).kairos;
```

- [ ] **Step 2: Zustand stores**

```typescript
// src/stores/project-store.ts
import { create } from "zustand";
import type { Project } from "@kairos/core";
import { kairos } from "@/lib/ipc";

interface ProjectStore {
  projects: Project[];
  loading: boolean;
  fetchProjects: () => Promise<void>;
  createProject: (name: string, topic: string) => Promise<void>;
}

export const useProjectStore = create<ProjectStore>((set) => ({
  projects: [],
  loading: false,
  fetchProjects: async () => {
    set({ loading: true });
    const projects = await kairos.listProjects();
    set({ projects, loading: false });
  },
  createProject: async (name, topic) => {
    await kairos.createProject({ name, topic });
    const projects = await kairos.listProjects();
    set({ projects });
  },
}));
```

```typescript
// src/stores/pipeline-store.ts
import { create } from "zustand";
import type { ProgressEvent } from "@kairos/core";

interface PipelineLog extends ProgressEvent {
  slug: string;
}

interface PipelineStore {
  running: Record<string, boolean>;
  logs: PipelineLog[];
  addLog: (log: PipelineLog) => void;
  setRunning: (slug: string, isRunning: boolean) => void;
  clearLogs: (slug: string) => void;
}

export const usePipelineStore = create<PipelineStore>((set) => ({
  running: {},
  logs: [],
  addLog: (log) =>
    set((state) => ({ logs: [...state.logs.slice(-500), log] })),
  setRunning: (slug, isRunning) =>
    set((state) => ({ running: { ...state.running, [slug]: isRunning } })),
  clearLogs: (slug) =>
    set((state) => ({ logs: state.logs.filter((l) => l.slug !== slug) })),
}));
```

- [ ] **Step 3: Layout 컴포넌트**

```tsx
// src/components/Layout.tsx
import React from "react";
import { NavLink, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <nav
        style={{
          width: 220,
          background: "#1a1a2e",
          color: "#eee",
          padding: 16,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <h2 style={{ fontSize: 18, marginBottom: 16 }}>Kairos Studio</h2>
        <NavLink to="/" style={{ color: "#ccc", textDecoration: "none" }}>
          프로젝트
        </NavLink>
        <NavLink to="/settings" style={{ color: "#ccc", textDecoration: "none" }}>
          설정
        </NavLink>
      </nav>
      <main style={{ flex: 1, overflow: "auto", background: "#0f0f23", color: "#eee", padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: ProjectCard + ProjectList**

```tsx
// src/components/ProjectCard.tsx
import React from "react";
import type { Project } from "@kairos/core";
import { useNavigate } from "react-router-dom";

const STATUS_LABELS: Record<string, string> = {
  created: "생성됨",
  in_progress: "진행 중",
  completed: "완료",
  failed: "실패",
  archived: "보관됨",
};

export function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate();
  return (
    <div
      onClick={() => navigate(`/project/${project.slug}`)}
      style={{
        background: "#16213e",
        borderRadius: 8,
        padding: 16,
        cursor: "pointer",
        border: "1px solid #2a2a4a",
      }}
    >
      <h3 style={{ margin: "0 0 8px" }}>{project.name}</h3>
      <p style={{ margin: "0 0 4px", color: "#999", fontSize: 14 }}>
        {project.topic ?? "주제 없음"}
      </p>
      <span
        style={{
          fontSize: 12,
          padding: "2px 8px",
          borderRadius: 4,
          background: project.status === "completed" ? "#1b4332" : "#2a2a4a",
          color: project.status === "completed" ? "#52b788" : "#aaa",
        }}
      >
        {STATUS_LABELS[project.status] ?? project.status}
      </span>
    </div>
  );
}
```

```tsx
// src/pages/ProjectList.tsx
import React, { useEffect } from "react";
import { useProjectStore } from "@/stores/project-store";
import { ProjectCard } from "@/components/ProjectCard";

export function ProjectList() {
  const { projects, loading, fetchProjects } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  if (loading) return <p>로딩 중...</p>;

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>프로젝트</h1>
      {projects.length === 0 ? (
        <p style={{ color: "#888" }}>프로젝트가 없습니다. 워크스페이스를 설정해주세요.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: PipelineProgress + PipelineLog**

```tsx
// src/components/PipelineProgress.tsx
import React from "react";
import { usePipelineStore } from "@/stores/pipeline-store";
import { kairos } from "@/lib/ipc";

export function PipelineProgress({ slug }: { slug: string }) {
  const { running, setRunning } = usePipelineStore();
  const isRunning = running[slug] ?? false;

  const handleRun = async () => {
    setRunning(slug, true);
    await kairos.runPipeline(slug);
  };

  const handleStop = async () => {
    await kairos.stopPipeline(slug);
    setRunning(slug, false);
  };

  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
      {isRunning ? (
        <button onClick={handleStop} style={{ padding: "8px 16px", background: "#c0392b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
          중단
        </button>
      ) : (
        <button onClick={handleRun} style={{ padding: "8px 16px", background: "#27ae60", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
          파이프라인 실행
        </button>
      )}
    </div>
  );
}
```

```tsx
// src/components/PipelineLog.tsx
import React, { useRef, useEffect } from "react";
import { usePipelineStore } from "@/stores/pipeline-store";

const LEVEL_COLORS: Record<string, string> = {
  info: "#8899aa",
  success: "#52b788",
  warning: "#f4a261",
  error: "#e63946",
};

export function PipelineLog({ slug }: { slug: string }) {
  const logs = usePipelineStore((s) => s.logs.filter((l) => l.slug === slug));
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  return (
    <div
      style={{
        background: "#0a0a1a",
        borderRadius: 8,
        padding: 16,
        maxHeight: 400,
        overflow: "auto",
        fontFamily: "monospace",
        fontSize: 13,
      }}
    >
      {logs.length === 0 && <p style={{ color: "#555" }}>로그 없음</p>}
      {logs.map((log, i) => (
        <div key={i} style={{ marginBottom: 4, color: LEVEL_COLORS[log.level] ?? "#aaa" }}>
          <span style={{ color: "#555" }}>
            [{new Date(log.timestamp * 1000).toLocaleTimeString()}]
          </span>{" "}
          <span style={{ fontWeight: "bold" }}>{log.agent}</span>: {log.text}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 6: ProjectDetail 페이지**

```tsx
// src/pages/ProjectDetail.tsx
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import type { Project } from "@kairos/core";
import { kairos } from "@/lib/ipc";
import { PipelineProgress } from "@/components/PipelineProgress";
import { PipelineLog } from "@/components/PipelineLog";

export function ProjectDetail() {
  const { slug } = useParams<{ slug: string }>();
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    if (slug) kairos.getProject(slug).then(setProject);
  }, [slug]);

  if (!project) return <p>로딩 중...</p>;

  return (
    <div>
      <h1>{project.name}</h1>
      <p style={{ color: "#999" }}>{project.topic}</p>
      <PipelineProgress slug={project.slug} />
      <h2 style={{ marginTop: 24, marginBottom: 12 }}>파이프라인 로그</h2>
      <PipelineLog slug={project.slug} />
    </div>
  );
}
```

- [ ] **Step 7: Settings 페이지**

```tsx
// src/pages/Settings.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "@/lib/ipc";
import type { CLIInfo } from "@kairos/core";

export function Settings() {
  const [workspaceDir, setWorkspaceDir] = useState("");
  const [cliStatus, setCLIStatus] = useState<CLIInfo | null>(null);

  useEffect(() => {
    kairos.getSettings().then((s) => setWorkspaceDir(s.workspaceDir));
    kairos.detectCLI("claude").then(setCLIStatus);
  }, []);

  return (
    <div>
      <h1>설정</h1>

      <section style={{ marginTop: 24 }}>
        <h2>워크스페이스</h2>
        <input
          value={workspaceDir}
          onChange={(e) => setWorkspaceDir(e.target.value)}
          placeholder="/path/to/workspace"
          style={{ width: 400, padding: 8, background: "#1a1a2e", color: "#eee", border: "1px solid #333", borderRadius: 4 }}
        />
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>LLM CLI</h2>
        {cliStatus ? (
          <div>
            <p>Claude Code: {cliStatus.found ? `✅ ${cliStatus.path}` : "❌ 미설치"}</p>
            {cliStatus.version && <p>버전: {cliStatus.version}</p>}
          </div>
        ) : (
          <p>감지 중...</p>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 8: App.tsx 라우팅 + main.tsx 업데이트**

```tsx
// src/App.tsx
import React, { useEffect } from "react";
import { HashRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { ProjectList } from "@/pages/ProjectList";
import { ProjectDetail } from "@/pages/ProjectDetail";
import { Settings } from "@/pages/Settings";
import { usePipelineStore } from "@/stores/pipeline-store";
import { kairos } from "@/lib/ipc";

export function App() {
  const addLog = usePipelineStore((s) => s.addLog);
  const setRunning = usePipelineStore((s) => s.setRunning);

  useEffect(() => {
    const unsubscribe = kairos.onPipelineProgress((event) => {
      addLog(event);
      if (event.level === "success" && event.text.includes("완료")) {
        setRunning(event.slug, false);
      }
      if (event.level === "error" && event.agent === "system") {
        setRunning(event.slug, false);
      }
    });
    return unsubscribe;
  }, [addLog, setRunning]);

  return (
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<ProjectList />} />
          <Route path="/project/:slug" element={<ProjectDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
```

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: 앱 실행 확인**

Run: `cd ~/Desktop/kairos-app && npm run electron:dev`
Expected:
- Electron 창에 사이드바(프로젝트, 설정) 표시
- 프로젝트 목록 페이지 표시 (워크스페이스 미설정 시 빈 상태)
- 설정 페이지에서 Claude CLI 감지 결과 표시

- [ ] **Step 10: 커밋**

```bash
git add src/ electron/
git commit -m "feat: React UI — 프로젝트 목록, 상세, 파이프라인 실행, 설정"
```

---

## Chunk 4: 통합 테스트 + 마무리

### Task 9: E2E 테스트

**Files:**
- Create: `kairos-app/tests/e2e/app-launch.test.ts`

- [ ] **Step 1: E2E 테스트 작성**

```typescript
// tests/e2e/app-launch.test.ts
import { describe, it, expect } from "vitest";
import { execFileSync } from "child_process";
import os from "os";

describe("App Launch Smoke Test", () => {
  it("should have all dependencies installed", () => {
    const result = execFileSync("npm", ["ls", "--depth=0"], {
      cwd: process.cwd(),
      encoding: "utf-8",
    });
    expect(result).toContain("electron");
    expect(result).toContain("react");
    expect(result).toContain("better-sqlite3");
  });

  it("should compile TypeScript without errors", () => {
    const result = execFileSync("npx", ["tsc", "--noEmit"], {
      cwd: process.cwd(),
      encoding: "utf-8",
      stdio: "pipe",
    });
    // No output = no errors
    expect(result.trim()).toBe("");
  });
});
```

- [ ] **Step 2: 전체 테스트 실행**

Run: `cd ~/Desktop/kairos-app && npm test`
Expected: 모든 단위 테스트 + E2E 스모크 테스트 PASS

- [ ] **Step 3: 커밋**

```bash
git add tests/
git commit -m "test: E2E 스모크 테스트 추가"
```

---

### Task 10: 크로스플랫폼 검증 + 빌드

**Files:**
- Modify: `kairos-app/package.json` (build 스크립트 확인)

- [ ] **Step 1: Mac 빌드 확인**

Run: `cd ~/Desktop/kairos-app && npm run electron:build`
Expected: `dist/` 에 macOS DMG 또는 앱 번들 생성

- [ ] **Step 2: Windows 빌드 설정 확인**

package.json의 build 설정에 win 타겟 포함 확인:
```json
"win": { "target": "nsis" }
```
(실제 Windows 빌드는 Windows 환경 또는 CI에서 실행)

- [ ] **Step 3: 최종 커밋**

```bash
git add .
git commit -m "chore: Plan 1 완료 — Electron shell + Pipeline Bridge MVP"
```

---

## 완료 기준 (Done Criteria)

- [ ] Electron 앱이 Mac에서 실행됨
- [ ] 프로젝트 목록이 SQLite DB에서 로드되어 표시됨
- [ ] 프로젝트 상세에서 파이프라인 실행 버튼 동작
- [ ] 파이프라인 진행률이 JSONL 감시를 통해 실시간 표시됨
- [ ] 파이프라인 중단 버튼 동작
- [ ] 설정에서 Claude Code CLI 감지 결과 표시
- [ ] 전체 테스트 통과
- [ ] 기존 `auto-kairos` CLI와 같은 워크스페이스 공유 가능
