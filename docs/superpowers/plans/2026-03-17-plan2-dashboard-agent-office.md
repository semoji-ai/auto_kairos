# Plan 2: 대시보드 React 재작성 + 에이전트 오피스

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking. **Phase B 태스크들은 병렬 실행 가능** — 각 탭이 독립된 파일에서 작업하므로 충돌 없음.

**Goal:** 기존 FastAPI/Jinja2 대시보드의 11개 탭을 Electron 앱 안의 React 컴포넌트로 재작성하고, 에이전트 오피스(픽셀 캐릭터 시각화)를 추가한다.

**Architecture:** Phase A에서 탭 프레임워크 + API 레이어를 만들고, Phase B에서 각 탭을 병렬로 개발한다. 기존 FastAPI 대시보드의 API 엔드포인트를 Electron IPC로 래핑하여, React 컴포넌트가 동일한 데이터를 사용한다.

**Tech Stack:** React 18, TypeScript, Zustand, CodeMirror 6 (에디터), EventSource (SSE)

**Spec:** `docs/superpowers/specs/2026-03-16-kairos-desktop-app-design.md`
**Depends on:** Plan 1 완료 (`~/Desktop/kairos-app/`)

---

## File Structure (Phase A + B 전체)

```
kairos-app/src/
├── App.tsx                           라우팅 (수정)
├── lib/
│   ├── ipc.ts                        IPC 래퍼 (수정 — API 추가)
│   └── api.ts                        파일시스템 직접 읽기 API
├── stores/
│   ├── project-store.ts              (수정 — 상세 데이터 추가)
│   ├── pipeline-store.ts             (수정 — SSE 연동)
│   └── agent-store.ts                에이전트 메시지 + 오피스 상태
├── components/
│   ├── Layout.tsx                    (수정 — 사이드바 강화)
│   ├── TabBar.tsx                    탭 전환 컴포넌트
│   ├── ProjectCard.tsx               (기존)
│   ├── PipelineProgress.tsx          (수정 — 단계별 상세)
│   ├── PipelineLog.tsx               (기존)
│   └── AgentOffice.tsx               픽셀 에이전트 사무실
├── pages/
│   ├── ProjectList.tsx               (기존)
│   ├── ProjectDetail.tsx             (수정 — 탭 시스템)
│   └── Settings.tsx                  (기존)
└── tabs/                             각 탭 독립 디렉토리
    ├── overview/
    │   └── OverviewTab.tsx
    ├── pipeline/
    │   └── PipelineTab.tsx
    ├── agent/
    │   └── AgentTab.tsx
    ├── manuscript/
    │   └── ManuscriptTab.tsx
    ├── research/
    │   └── ResearchTab.tsx
    ├── storyboard/
    │   └── StoryboardTab.tsx
    ├── assets/
    │   └── AssetsTab.tsx
    ├── costs/
    │   └── CostsTab.tsx
    ├── versions/
    │   └── VersionsTab.tsx
    └── design/
        └── DesignTab.tsx

electron/ipc/
├── project.ipc.ts                    (수정 — 파일 읽기 API 추가)
├── pipeline.ipc.ts                   (기존)
└── cli-manager.ipc.ts                (기존)
```

---

## Phase A: 탭 프레임워크 + API 레이어 (순차)

### Task A1: 파일 읽기 API + IPC 확장

**Files:**
- Create: `kairos-app/src/lib/api.ts`
- Modify: `kairos-app/electron/ipc/project.ipc.ts`
- Modify: `kairos-app/electron/preload.ts`
- Modify: `kairos-app/src/lib/ipc.ts`

각 탭이 프로젝트 파일(scene_specs.json, manifest.json, final_manuscript.md 등)을 읽어야 하므로, 파일 읽기 IPC를 추가한다.

- [ ] **Step 1: project.ipc.ts에 파일 읽기 핸들러 추가**

`electron/ipc/project.ipc.ts`에 추가:

```typescript
import fs from "fs";
import path from "path";

// 기존 registerProjectIPC() 내부에 추가:

ipcMain.handle("project:readFile", (_, slug: string, relativePath: string) => {
  const settings = JSON.parse(
    fs.readFileSync(path.join(os.homedir(), ".kairos", "settings.json"), "utf-8")
  );
  const filePath = path.join(settings.workspaceDir, "output", slug, relativePath);
  if (!fs.existsSync(filePath)) return null;
  const content = fs.readFileSync(filePath, "utf-8");
  // JSON 파일이면 파싱해서 반환
  if (relativePath.endsWith(".json")) {
    try { return JSON.parse(content); } catch { return content; }
  }
  return content;
});

ipcMain.handle("project:readDir", (_, slug: string, relativePath: string) => {
  const settings = JSON.parse(
    fs.readFileSync(path.join(os.homedir(), ".kairos", "settings.json"), "utf-8")
  );
  const dirPath = path.join(settings.workspaceDir, "output", slug, relativePath);
  if (!fs.existsSync(dirPath)) return [];
  return fs.readdirSync(dirPath).map((name) => {
    const stat = fs.statSync(path.join(dirPath, name));
    return { name, size: stat.size, isDir: stat.isDirectory(), mtime: stat.mtime.toISOString() };
  });
});

ipcMain.handle("project:getProjectDir", (_, slug: string) => {
  const settings = JSON.parse(
    fs.readFileSync(path.join(os.homedir(), ".kairos", "settings.json"), "utf-8")
  );
  return path.join(settings.workspaceDir, "output", slug);
});
```

- [ ] **Step 2: preload.ts에 API 노출**

```typescript
// 기존 contextBridge.exposeInMainWorld("kairos", { ... }) 내부에 추가:
readFile: (slug: string, path: string) => ipcRenderer.invoke("project:readFile", slug, path),
readDir: (slug: string, path: string) => ipcRenderer.invoke("project:readDir", slug, path),
getProjectDir: (slug: string) => ipcRenderer.invoke("project:getProjectDir", slug),
```

- [ ] **Step 3: ipc.ts 타입 업데이트**

```typescript
// src/lib/ipc.ts — KairosAPI에 추가:
readFile: (slug: string, path: string) => Promise<any>;
readDir: (slug: string, path: string) => Promise<Array<{ name: string; size: number; isDir: boolean; mtime: string }>>;
getProjectDir: (slug: string) => Promise<string>;
```

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: 파일 읽기 IPC — readFile, readDir, getProjectDir"
```

---

### Task A2: 탭바 + ProjectDetail 탭 시스템

**Files:**
- Create: `kairos-app/src/components/TabBar.tsx`
- Modify: `kairos-app/src/pages/ProjectDetail.tsx`

- [ ] **Step 1: TabBar 컴포넌트 생성**

```tsx
// src/components/TabBar.tsx
import React from "react";

export interface Tab {
  id: string;
  label: string;
  icon?: string;
}

const TABS: Tab[] = [
  { id: "overview", label: "개요" },
  { id: "pipeline", label: "파이프라인" },
  { id: "agent", label: "에이전트" },
  { id: "research", label: "리서치" },
  { id: "manuscript", label: "원고" },
  { id: "storyboard", label: "스토리보드" },
  { id: "assets", label: "에셋" },
  { id: "costs", label: "비용" },
  { id: "versions", label: "버전" },
  { id: "design", label: "디자인" },
];

interface TabBarProps {
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div style={{
      display: "flex", gap: 4, borderBottom: "1px solid #2a2a4a",
      marginBottom: 24, paddingBottom: 0, overflowX: "auto",
    }}>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            padding: "8px 16px",
            background: activeTab === tab.id ? "#16213e" : "transparent",
            color: activeTab === tab.id ? "#fff" : "#888",
            border: "none",
            borderBottom: activeTab === tab.id ? "2px solid #F59E0B" : "2px solid transparent",
            cursor: "pointer",
            fontSize: 14,
            whiteSpace: "nowrap",
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: ProjectDetail 탭 시스템으로 재작성**

```tsx
// src/pages/ProjectDetail.tsx
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { kairos } from "../lib/ipc";
import { TabBar } from "../components/TabBar";

// 각 탭은 lazy import (Phase B에서 구현)
import { OverviewTab } from "../tabs/overview/OverviewTab";
import { PipelineTab } from "../tabs/pipeline/PipelineTab";
import { AgentTab } from "../tabs/agent/AgentTab";
import { ResearchTab } from "../tabs/research/ResearchTab";
import { ManuscriptTab } from "../tabs/manuscript/ManuscriptTab";
import { StoryboardTab } from "../tabs/storyboard/StoryboardTab";
import { AssetsTab } from "../tabs/assets/AssetsTab";
import { CostsTab } from "../tabs/costs/CostsTab";
import { VersionsTab } from "../tabs/versions/VersionsTab";
import { DesignTab } from "../tabs/design/DesignTab";

const TAB_COMPONENTS: Record<string, React.FC<{ slug: string; project: any }>> = {
  overview: OverviewTab,
  pipeline: PipelineTab,
  agent: AgentTab,
  research: ResearchTab,
  manuscript: ManuscriptTab,
  storyboard: StoryboardTab,
  assets: AssetsTab,
  costs: CostsTab,
  versions: VersionsTab,
  design: DesignTab,
};

export function ProjectDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [project, setProject] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    kairos.getProject(decodeURIComponent(slug))
      .then((p) => {
        setProject(p);
        setLoading(false);
        if (!p) setError(`프로젝트를 찾을 수 없습니다: "${slug}"`);
      })
      .catch((e) => { setError(String(e)); setLoading(false); });
  }, [slug]);

  if (loading) return <p>로딩 중...</p>;
  if (error || !project) {
    return (
      <div>
        <p style={{ color: "#e63946" }}>{error ?? "프로젝트 없음"}</p>
        <button onClick={() => navigate("/")}
          style={{ marginTop: 16, padding: "8px 16px", background: "#333", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>
          목록으로
        </button>
      </div>
    );
  }

  const TabComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <button onClick={() => navigate("/")}
          style={{ padding: "4px 12px", background: "transparent", color: "#888", border: "1px solid #333", borderRadius: 4, cursor: "pointer" }}>
          ←
        </button>
        <h1 style={{ margin: 0 }}>{project.name}</h1>
        <span style={{
          fontSize: 12, padding: "2px 8px", borderRadius: 4,
          background: project.status === "completed" ? "#1b4332" : "#2a2a4a",
          color: project.status === "completed" ? "#52b788" : "#aaa",
        }}>
          {project.status}
        </span>
      </div>

      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      {TabComponent ? (
        <TabComponent slug={project.slug} project={project} />
      ) : (
        <p style={{ color: "#666" }}>탭 준비 중...</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 모든 탭에 placeholder 생성**

각 탭 디렉토리에 최소 컴포넌트 생성 (Phase B에서 실제 구현):

```tsx
// src/tabs/overview/OverviewTab.tsx (모든 탭 동일 패턴)
import React from "react";

export function OverviewTab({ slug, project }: { slug: string; project: any }) {
  return <p style={{ color: "#666" }}>개요 탭 — 구현 예정</p>;
}
```

동일 패턴으로 10개 파일 생성:
- `src/tabs/overview/OverviewTab.tsx`
- `src/tabs/pipeline/PipelineTab.tsx`
- `src/tabs/agent/AgentTab.tsx`
- `src/tabs/research/ResearchTab.tsx`
- `src/tabs/manuscript/ManuscriptTab.tsx`
- `src/tabs/storyboard/StoryboardTab.tsx`
- `src/tabs/assets/AssetsTab.tsx`
- `src/tabs/costs/CostsTab.tsx`
- `src/tabs/versions/VersionsTab.tsx`
- `src/tabs/design/DesignTab.tsx`

- [ ] **Step 4: 앱 실행 확인**

탭바가 표시되고, 탭 전환 시 placeholder가 보이는지 확인.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: 탭 시스템 프레임워크 + 10개 placeholder 탭"
```

---

## Phase B: 탭 병렬 개발

> **병렬 실행 규칙:** 각 탭은 `src/tabs/{탭이름}/` 디렉토리에서만 작업한다.
> 공유 파일(stores, lib, components)을 수정해야 할 경우, 해당 탭 내부에 로컬 유틸을 만들고 나중에 통합한다.
> **git worktree로 격리** 실행 가능 — 각 에이전트가 별도 브랜치에서 작업 후 merge.

---

### Task B1: Overview + Pipeline 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/overview/OverviewTab.tsx` (덮어쓰기)
- Create: `src/tabs/pipeline/PipelineTab.tsx` (덮어쓰기)

**Overview 탭 — 프로젝트 요약:**
```tsx
// src/tabs/overview/OverviewTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function OverviewTab({ slug, project }: { slug: string; project: any }) {
  const [sceneSpecs, setSceneSpecs] = useState<any>(null);
  const [assets, setAssets] = useState<any[]>([]);

  useEffect(() => {
    kairos.readFile(slug, "scene_specs.json").then(setSceneSpecs);
    kairos.readDir(slug, "").then(setAssets);
  }, [slug]);

  const config = project.config ?? {};
  const sceneCount = Array.isArray(sceneSpecs) ? sceneSpecs.length : project.scene_count;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16, marginBottom: 24 }}>
        <StatCard label="씬 수" value={sceneCount ?? 0} />
        <StatCard label="상태" value={project.status} />
        <StatCard label="스타일" value={config.style_name ?? config.art_style ?? "-"} />
        <StatCard label="길이" value={project.total_duration_sec ? `${Math.round(project.total_duration_sec / 60)}분` : "-"} />
      </div>

      <h3 style={{ marginBottom: 12 }}>프로젝트 파일</h3>
      <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, fontSize: 13, fontFamily: "monospace" }}>
        {assets.length === 0 ? (
          <p style={{ color: "#555" }}>파일 없음</p>
        ) : (
          assets.map((f) => (
            <div key={f.name} style={{ padding: "4px 0", color: f.isDir ? "#F59E0B" : "#aaa" }}>
              {f.isDir ? "📁" : "📄"} {f.name}
              {!f.isDir && <span style={{ color: "#555", marginLeft: 8 }}>({formatSize(f.size)})</span>}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ background: "#16213e", borderRadius: 8, padding: 16 }}>
      <div style={{ color: "#888", fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: "bold" }}>{value}</div>
    </div>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}
```

**Pipeline 탭 — 파이프라인 진행률 + 단계별 상세:**
```tsx
// src/tabs/pipeline/PipelineTab.tsx
import React, { useEffect, useState, useMemo } from "react";
import { kairos } from "../../lib/ipc";
import { usePipelineStore } from "../../stores/pipeline-store";

const STEP_LABELS: Record<string, string> = {
  step_0: "환경 검증", step_1: "심층 리서치", step_2: "원고 작성",
  step_3: "중복 검사", step_4: "팩트 검증", step_5: "캐릭터 기획",
  step_6: "비주얼 구성", step_7: "TTS 전처리", step_8: "TTS 생성",
  step_8b: "이미지 소싱", step_9: "자막 동기화", step_9b: "TTS 검증",
  step_10: "데이터 검증", step_11: "매니페스트 빌드", step_11b: "사전 QA",
  step_12: "영상 렌더", step_12b: "사후 QA",
};

export function PipelineTab({ slug, project }: { slug: string; project: any }) {
  const [pipelineState, setPipelineState] = useState<any>(null);
  const { running, setRunning } = usePipelineStore();
  const allLogs = usePipelineStore((s) => s.logs);
  const logs = useMemo(() => allLogs.filter((l) => l.slug === slug), [allLogs, slug]);
  const isRunning = running[slug] ?? false;

  useEffect(() => {
    kairos.readFile(slug, "pipeline_state.json").then(setPipelineState);
  }, [slug]);

  const handleRun = async (fromStep?: string) => {
    setRunning(slug, true);
    await kairos.runPipeline(slug, fromStep ? { fromStep } : undefined);
  };

  const handleStop = async () => {
    await kairos.stopPipeline(slug);
    setRunning(slug, false);
  };

  const completed = pipelineState?.completed_steps ?? [];
  const failed = pipelineState?.failed_steps ?? [];

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
        {isRunning ? (
          <button onClick={handleStop} style={{ padding: "8px 16px", background: "#c0392b", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>중단</button>
        ) : (
          <button onClick={() => handleRun()} style={{ padding: "8px 16px", background: "#27ae60", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" }}>전체 실행</button>
        )}
      </div>

      <h3 style={{ marginBottom: 12 }}>단계별 상태</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {Object.entries(STEP_LABELS).map(([stepId, label]) => {
          const status = completed.includes(stepId) ? "completed" : failed.includes(stepId) ? "failed" : "pending";
          const result = pipelineState?.results?.[stepId];
          return (
            <div key={stepId} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "8px 12px", background: "#0a0a1a", borderRadius: 6,
              borderLeft: `3px solid ${status === "completed" ? "#52b788" : status === "failed" ? "#e63946" : "#333"}`,
            }}>
              <span style={{ fontSize: 14 }}>
                {status === "completed" ? "✅" : status === "failed" ? "❌" : "⬜"}
              </span>
              <span style={{ flex: 1, fontSize: 13 }}>{stepId}: {label}</span>
              {result?.duration_sec && (
                <span style={{ color: "#666", fontSize: 12 }}>{result.duration_sec.toFixed(1)}s</span>
              )}
              {result?.cost_info?.cost_usd && (
                <span style={{ color: "#F59E0B", fontSize: 12 }}>${result.cost_info.cost_usd.toFixed(3)}</span>
              )}
              {status === "failed" && !isRunning && (
                <button onClick={() => handleRun(stepId)}
                  style={{ padding: "2px 8px", background: "#333", color: "#aaa", border: "none", borderRadius: 4, cursor: "pointer", fontSize: 11 }}>
                  재시도
                </button>
              )}
            </div>
          );
        })}
      </div>

      {logs.length > 0 && (
        <>
          <h3 style={{ marginTop: 24, marginBottom: 12 }}>실시간 로그</h3>
          <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, maxHeight: 300, overflow: "auto", fontFamily: "monospace", fontSize: 12 }}>
            {logs.slice(-100).map((log, i) => (
              <div key={i} style={{ marginBottom: 2, color: log.level === "error" ? "#e63946" : log.level === "success" ? "#52b788" : "#8899aa" }}>
                [{new Date(log.timestamp * 1000).toLocaleTimeString()}] <b>{log.agent}</b>: {log.text}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Overview + Pipeline 탭`

---

### Task B2: Agent 오피스 + 메신저 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/agent/AgentTab.tsx` (덮어쓰기)
- Create: `src/components/AgentOffice.tsx`
- Create: `src/stores/agent-store.ts`

**에이전트 오피스 — 픽셀 캐릭터 시각화:**
```tsx
// src/components/AgentOffice.tsx
import React from "react";

interface Agent {
  id: string;
  name: string;
  team: "planning" | "production" | "distribution";
  emoji: string;
  status: "idle" | "working" | "done" | "error";
  message?: string;
}

const AGENTS: Agent[] = [
  // 기획팀
  { id: "research", name: "리서치", team: "planning", emoji: "🔍", status: "idle" },
  { id: "writer", name: "작가", team: "planning", emoji: "✍️", status: "idle" },
  { id: "factcheck", name: "팩트체커", team: "planning", emoji: "🛡️", status: "idle" },
  // 제작팀
  { id: "visual", name: "디자이너", team: "production", emoji: "🎨", status: "idle" },
  { id: "character", name: "캐릭터", team: "production", emoji: "👤", status: "idle" },
  { id: "qa", name: "QA", team: "production", emoji: "✅", status: "idle" },
];

const STATUS_STYLES: Record<string, { bg: string; border: string; animation?: string }> = {
  idle: { bg: "#1a1a2e", border: "#2a2a4a" },
  working: { bg: "#1a2e1a", border: "#52b788", animation: "pulse 2s infinite" },
  done: { bg: "#1a1a2e", border: "#52b788" },
  error: { bg: "#2e1a1a", border: "#e63946" },
};

interface AgentOfficeProps {
  agentStatuses?: Record<string, string>;
  agentMessages?: Record<string, string>;
}

export function AgentOffice({ agentStatuses = {}, agentMessages = {} }: AgentOfficeProps) {
  const teams = {
    planning: { label: "🏢 기획팀", agents: AGENTS.filter((a) => a.team === "planning") },
    production: { label: "🎬 제작팀", agents: AGENTS.filter((a) => a.team === "production") },
  };

  return (
    <div>
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }`}</style>
      {Object.entries(teams).map(([teamId, team]) => (
        <div key={teamId} style={{ marginBottom: 20 }}>
          <h4 style={{ margin: "0 0 8px", color: "#888", fontSize: 13 }}>{team.label}</h4>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {team.agents.map((agent) => {
              const status = (agentStatuses[agent.id] as keyof typeof STATUS_STYLES) ?? "idle";
              const style = STATUS_STYLES[status] ?? STATUS_STYLES.idle;
              const msg = agentMessages[agent.id];
              return (
                <div key={agent.id} style={{
                  background: style.bg, border: `1px solid ${style.border}`,
                  borderRadius: 8, padding: "12px 16px", minWidth: 100,
                  textAlign: "center", animation: style.animation,
                }}>
                  <div style={{ fontSize: 28 }}>{agent.emoji}</div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>{agent.name}</div>
                  <div style={{ fontSize: 10, color: "#666", marginTop: 2 }}>
                    {status === "working" ? "작업중" : status === "done" ? "완료" : status === "error" ? "에러" : "대기"}
                  </div>
                  {msg && <div style={{ fontSize: 10, color: "#999", marginTop: 4, maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>💬 {msg}</div>}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**Agent 탭 — 오피스 + 메신저:**
```tsx
// src/tabs/agent/AgentTab.tsx
import React, { useMemo } from "react";
import { AgentOffice } from "../../components/AgentOffice";
import { usePipelineStore } from "../../stores/pipeline-store";

// 에이전트 ID → 오피스 에이전트 매핑
const AGENT_MAP: Record<string, string> = {
  "research-orchestrator": "research",
  "write-manuscript": "writer",
  "fact-verifier": "factcheck",
  "visual-composer": "visual",
  "character-planner": "character",
  "qa-reviewer": "qa",
};

export function AgentTab({ slug, project }: { slug: string; project: any }) {
  const allLogs = usePipelineStore((s) => s.logs);
  const logs = useMemo(() => allLogs.filter((l) => l.slug === slug), [allLogs, slug]);

  // 최신 로그에서 에이전트 상태 추출
  const agentStatuses: Record<string, string> = {};
  const agentMessages: Record<string, string> = {};

  for (const log of logs) {
    const officeId = AGENT_MAP[log.agent];
    if (officeId) {
      agentStatuses[officeId] = log.level === "error" ? "error" : log.level === "success" ? "done" : "working";
      agentMessages[officeId] = log.text;
    }
  }

  return (
    <div>
      <h3 style={{ marginBottom: 16 }}>에이전트 오피스</h3>
      <AgentOffice agentStatuses={agentStatuses} agentMessages={agentMessages} />

      <h3 style={{ marginTop: 32, marginBottom: 12 }}>메신저</h3>
      <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, maxHeight: 400, overflow: "auto", fontFamily: "monospace", fontSize: 12 }}>
        {logs.length === 0 && <p style={{ color: "#555" }}>메시지 없음</p>}
        {logs.map((log, i) => (
          <div key={i} style={{ marginBottom: 6, display: "flex", gap: 8 }}>
            <span style={{ color: "#555", flexShrink: 0 }}>
              [{new Date(log.timestamp * 1000).toLocaleTimeString()}]
            </span>
            <span style={{ color: "#F59E0B", fontWeight: "bold", flexShrink: 0 }}>{log.agent}</span>
            <span style={{ color: log.level === "error" ? "#e63946" : log.level === "success" ? "#52b788" : "#aaa" }}>
              {log.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Agent 오피스 + 메신저 탭`

---

### Task B3: Manuscript 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/manuscript/ManuscriptTab.tsx` (덮어쓰기)

원고 뷰어 + 기본 편집:

```tsx
// src/tabs/manuscript/ManuscriptTab.tsx
import React, { useEffect, useState, useCallback } from "react";
import { kairos } from "../../lib/ipc";

export function ManuscriptTab({ slug, project }: { slug: string; project: any }) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [charCount, setCharCount] = useState(0);

  useEffect(() => {
    kairos.readFile(slug, "final_manuscript.md").then((text) => {
      if (text) {
        setContent(typeof text === "string" ? text : JSON.stringify(text, null, 2));
        setCharCount(typeof text === "string" ? text.length : 0);
      }
      setLoading(false);
    });
  }, [slug]);

  if (loading) return <p>원고 로딩 중...</p>;
  if (!content) return <p style={{ color: "#666" }}>원고 파일이 없습니다.</p>;

  // 간단한 마크다운 하이라이팅
  const highlighted = content
    .split("\n")
    .map((line, i) => {
      if (line.startsWith("# ")) return <div key={i} style={{ fontSize: 20, fontWeight: "bold", color: "#F59E0B", margin: "16px 0 8px" }}>{line.slice(2)}</div>;
      if (line.startsWith("## ")) return <div key={i} style={{ fontSize: 16, fontWeight: "bold", color: "#eee", margin: "12px 0 6px" }}>{line.slice(3)}</div>;
      if (line.startsWith("### ")) return <div key={i} style={{ fontSize: 14, fontWeight: "bold", color: "#ccc", margin: "8px 0 4px" }}>{line.slice(4)}</div>;
      if (line.trim() === "") return <div key={i} style={{ height: 8 }} />;
      return <div key={i} style={{ color: "#bbb", lineHeight: 1.8 }}>{line}</div>;
    });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>원고</h3>
        <span style={{ color: "#666", fontSize: 13 }}>{charCount.toLocaleString()}자</span>
      </div>
      <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 24, maxHeight: 600, overflow: "auto", fontSize: 14, fontFamily: "'Pretendard', sans-serif" }}>
        {highlighted}
      </div>
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Manuscript 탭 — 원고 뷰어`

---

### Task B4: Research 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/research/ResearchTab.tsx` (덮어쓰기)

```tsx
// src/tabs/research/ResearchTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function ResearchTab({ slug, project }: { slug: string; project: any }) {
  const [outline, setOutline] = useState<any>(null);

  useEffect(() => {
    kairos.readFile(slug, "outline.json").then(setOutline);
  }, [slug]);

  if (!outline) return <p style={{ color: "#666" }}>리서치 데이터가 없습니다.</p>;

  return (
    <div>
      <h3 style={{ marginBottom: 16 }}>아웃라인</h3>
      {outline.title && <h4 style={{ color: "#F59E0B" }}>{outline.title}</h4>}
      {outline.chapters?.map((ch: any, i: number) => (
        <div key={i} style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, marginBottom: 12 }}>
          <h4 style={{ margin: "0 0 8px", color: "#eee" }}>
            {ch.chapter_number ?? i + 1}장: {ch.title}
          </h4>
          {ch.summary && <p style={{ color: "#999", fontSize: 13, margin: 0 }}>{ch.summary}</p>}
          {ch.sections?.map((sec: any, j: number) => (
            <div key={j} style={{ marginTop: 8, paddingLeft: 16, borderLeft: "2px solid #2a2a4a" }}>
              <div style={{ color: "#aaa", fontSize: 13 }}>{sec.title}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Research 탭 — 아웃라인 뷰어`

---

### Task B5: Storyboard 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/storyboard/StoryboardTab.tsx` (덮어쓰기)

```tsx
// src/tabs/storyboard/StoryboardTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function StoryboardTab({ slug, project }: { slug: string; project: any }) {
  const [scenes, setScenes] = useState<any[]>([]);
  const [projectDir, setProjectDir] = useState("");

  useEffect(() => {
    kairos.readFile(slug, "scene_specs.json").then((data) => {
      if (Array.isArray(data)) setScenes(data);
    });
    kairos.getProjectDir(slug).then(setProjectDir);
  }, [slug]);

  if (scenes.length === 0) return <p style={{ color: "#666" }}>씬 데이터가 없습니다.</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h3 style={{ margin: 0 }}>스토리보드 ({scenes.length}씬)</h3>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
        {scenes.map((scene, i) => (
          <div key={i} style={{ background: "#0a0a1a", borderRadius: 8, overflow: "hidden", border: "1px solid #2a2a4a" }}>
            <div style={{ height: 160, background: "#111", display: "flex", alignItems: "center", justifyContent: "center", color: "#444" }}>
              S{scene.sceneNumber ?? i + 1}
            </div>
            <div style={{ padding: 12 }}>
              <div style={{ fontSize: 11, color: "#F59E0B", marginBottom: 4 }}>
                {scene.layout ?? "default"} · {scene.visualization?.vizType ?? "text"}
              </div>
              <p style={{ color: "#aaa", fontSize: 12, margin: 0, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                {scene.narration ?? scene.headline ?? "내레이션 없음"}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Storyboard 탭 — 씬 그리드`

---

### Task B6: Assets + Costs + Versions 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/assets/AssetsTab.tsx` (덮어쓰기)
- Create: `src/tabs/costs/CostsTab.tsx` (덮어쓰기)
- Create: `src/tabs/versions/VersionsTab.tsx` (덮어쓰기)

이 3개는 DB 조회 기반으로 단순한 테이블 뷰. 한 에이전트가 처리.

**Assets 탭:**
```tsx
// src/tabs/assets/AssetsTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function AssetsTab({ slug }: { slug: string; project: any }) {
  const [audioFiles, setAudioFiles] = useState<any[]>([]);
  const [imageFiles, setImageFiles] = useState<any[]>([]);

  useEffect(() => {
    kairos.readDir(slug, "audio").then((files) => setAudioFiles(files ?? [])).catch(() => {});
    kairos.readDir(slug, "images").then((files) => setImageFiles(files ?? [])).catch(() => {});
  }, [slug]);

  return (
    <div>
      <h3>에셋</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <AssetSection title={`🔊 오디오 (${audioFiles.length})`} files={audioFiles} />
        <AssetSection title={`🖼️ 이미지 (${imageFiles.length})`} files={imageFiles} />
      </div>
    </div>
  );
}

function AssetSection({ title, files }: { title: string; files: any[] }) {
  return (
    <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16 }}>
      <h4 style={{ margin: "0 0 12px", fontSize: 14 }}>{title}</h4>
      {files.length === 0 ? <p style={{ color: "#555", fontSize: 13 }}>없음</p> : (
        <div style={{ maxHeight: 300, overflow: "auto" }}>
          {files.map((f) => (
            <div key={f.name} style={{ fontSize: 12, padding: "4px 0", color: "#aaa", borderBottom: "1px solid #1a1a2e" }}>
              {f.name} <span style={{ color: "#555" }}>({(f.size / 1024).toFixed(0)}KB)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Costs 탭:**
```tsx
// src/tabs/costs/CostsTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function CostsTab({ slug, project }: { slug: string; project: any }) {
  const [pipelineState, setPipelineState] = useState<any>(null);

  useEffect(() => {
    kairos.readFile(slug, "pipeline_state.json").then(setPipelineState);
  }, [slug]);

  const results = pipelineState?.results ?? {};
  const entries = Object.entries(results);

  let totalCost = 0;
  let totalTokensIn = 0;
  let totalTokensOut = 0;
  entries.forEach(([, r]: [string, any]) => {
    totalCost += r.cost_info?.cost_usd ?? 0;
    totalTokensIn += r.cost_info?.tokens_in ?? 0;
    totalTokensOut += r.cost_info?.tokens_out ?? 0;
  });

  return (
    <div>
      <h3>비용 요약</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 16, marginBottom: 24 }}>
        <div style={{ background: "#16213e", borderRadius: 8, padding: 16 }}>
          <div style={{ color: "#888", fontSize: 12 }}>총 비용</div>
          <div style={{ fontSize: 24, fontWeight: "bold", color: "#F59E0B" }}>${totalCost.toFixed(3)}</div>
        </div>
        <div style={{ background: "#16213e", borderRadius: 8, padding: 16 }}>
          <div style={{ color: "#888", fontSize: 12 }}>입력 토큰</div>
          <div style={{ fontSize: 20 }}>{totalTokensIn.toLocaleString()}</div>
        </div>
        <div style={{ background: "#16213e", borderRadius: 8, padding: 16 }}>
          <div style={{ color: "#888", fontSize: 12 }}>출력 토큰</div>
          <div style={{ fontSize: 20 }}>{totalTokensOut.toLocaleString()}</div>
        </div>
      </div>

      <h3>단계별 비용</h3>
      <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, marginTop: 12 }}>
        {entries.length === 0 ? <p style={{ color: "#555" }}>데이터 없음</p> : (
          entries.map(([stepId, r]: [string, any]) => (
            <div key={stepId} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #1a1a2e", fontSize: 13 }}>
              <span style={{ color: "#aaa" }}>{stepId}</span>
              <span style={{ color: "#F59E0B" }}>${(r.cost_info?.cost_usd ?? 0).toFixed(4)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

**Versions 탭:**
```tsx
// src/tabs/versions/VersionsTab.tsx
import React, { useEffect, useState } from "react";
import { kairos } from "../../lib/ipc";

export function VersionsTab({ slug }: { slug: string; project: any }) {
  const [versions, setVersions] = useState<any[]>([]);

  useEffect(() => {
    kairos.readDir(slug, "versions").then((files) => setVersions(files ?? [])).catch(() => {});
  }, [slug]);

  return (
    <div>
      <h3>버전 히스토리</h3>
      <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16, marginTop: 16 }}>
        {versions.length === 0 ? <p style={{ color: "#555" }}>버전 데이터 없음</p> : (
          versions.map((f) => (
            <div key={f.name} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #1a1a2e", fontSize: 13 }}>
              <span style={{ color: "#aaa" }}>{f.name}</span>
              <span style={{ color: "#666" }}>{new Date(f.mtime).toLocaleString()}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Assets + Costs + Versions 탭`

---

### Task B7: Design 탭 (병렬 가능)

**Files:**
- Create: `src/tabs/design/DesignTab.tsx` (덮어쓰기)

```tsx
// src/tabs/design/DesignTab.tsx
import React from "react";

export function DesignTab({ slug, project }: { slug: string; project: any }) {
  const config = project.config ?? {};

  return (
    <div>
      <h3>디자인 설정</h3>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16 }}>
          <h4 style={{ margin: "0 0 12px", fontSize: 14, color: "#888" }}>현재 설정</h4>
          <ConfigRow label="아트 스타일" value={config.style_name ?? config.art_style ?? "-"} />
          <ConfigRow label="보이스" value={config.voice_id ?? "-"} />
          <ConfigRow label="테마" value={project.theme ?? "simple"} />
        </div>
        <div style={{ background: "#0a0a1a", borderRadius: 8, padding: 16 }}>
          <h4 style={{ margin: "0 0 12px", fontSize: 14, color: "#888" }}>보이스 설정</h4>
          {config.voice_settings ? (
            Object.entries(config.voice_settings).map(([key, val]) => (
              <ConfigRow key={key} label={key} value={String(val)} />
            ))
          ) : <p style={{ color: "#555", fontSize: 13 }}>설정 없음</p>}
        </div>
      </div>
    </div>
  );
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13, borderBottom: "1px solid #1a1a2e" }}>
      <span style={{ color: "#888" }}>{label}</span>
      <span style={{ color: "#eee" }}>{value}</span>
    </div>
  );
}
```

- [ ] 구현 + 테스트 + 커밋: `feat: Design 탭 — 디자인 설정 뷰어`

---

## Phase C: 통합 + 검증 (순차)

### Task C1: 통합 테스트 + 커밋

- [ ] 모든 탭 전환 동작 확인
- [ ] TypeScript 컴파일 에러 없음: `npx tsc --noEmit`
- [ ] 기존 16개 테스트 통과: `npx vitest run`
- [ ] 최종 커밋

---

## 완료 기준

- [ ] 10개 탭 모두 동작 (placeholder 아닌 실제 컴포넌트)
- [ ] 탭 전환 시 흰 화면 없음
- [ ] Pipeline 탭에서 단계별 상태 표시
- [ ] Agent 탭에 에이전트 오피스 픽셀 캐릭터 표시
- [ ] Manuscript 탭에서 원고 읽기 가능
- [ ] Storyboard 탭에서 씬 그리드 표시
- [ ] 기존 테스트 16개 통과

## 병렬 실행 가이드

Phase B의 Task B1~B7은 **모두 독립 실행 가능**:
- 각 태스크는 `src/tabs/{탭이름}/` 내 파일만 생성/수정
- 공유 store나 lib은 읽기만 함 (수정 필요 시 태스크 내 로컬 유틸 생성)
- Git worktree로 격리하면 완전 병렬 가능
- Worktree 없이도, 파일 경로가 겹치지 않으므로 순차 실행 시 충돌 없음
