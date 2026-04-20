-- auto_agent_v2 프로젝트 관리 스키마
-- SQLite WAL 모드: NAS 동시 읽기 지원
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ═══════════════════════════════════════════
-- 프로젝트 마스터
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid            TEXT NOT NULL DEFAULT '',            -- "b3cef462" (8자 hex 프로젝트 ID)
    name            TEXT NOT NULL,                       -- "미국 이란 전쟁 2026"
    slug            TEXT NOT NULL UNIQUE,                -- "미국_이란_전쟁_2026"
    status          TEXT NOT NULL DEFAULT 'created'
                    CHECK (status IN ('created','in_progress','completed','archived','failed')),
    topic           TEXT,                                -- scene_specs.json "topic" 필드
    theme           TEXT DEFAULT 'simple',               -- "simple" | "kairos"
    scene_count     INTEGER DEFAULT 0,
    total_duration_sec REAL DEFAULT 0.0,
    channel         TEXT DEFAULT NULL,                   -- "이로미즘" | "세모지" | NULL
    video_id        TEXT DEFAULT NULL,                   -- 게시된 YouTube 영상 ID
    config          TEXT,                                -- JSON: 프로젝트별 설정 오버라이드
    output_dir      TEXT NOT NULL,                       -- "output/미국_이란_전쟁_2026"
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- 파이프라인 실행 기록
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    phase           TEXT NOT NULL,                       -- "phase_0" ~ "phase_5"
    step            TEXT NOT NULL,                       -- "step_1", "step_6" 등
    step_name       TEXT,                                -- "deep_research_and_synthesis" 등
    agent_or_module TEXT,                                -- "visual-composer", "tts-generator" 등
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed','skipped')),
    started_at      TEXT,
    completed_at    TEXT,
    duration_sec    REAL,
    cost_tokens_in  INTEGER DEFAULT 0,
    cost_tokens_out INTEGER DEFAULT 0,
    cost_usd        REAL DEFAULT 0.0,
    error_log       TEXT,
    metadata        TEXT,                                -- JSON: model, retries 등
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- 에셋 파일 레지스트리
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_type      TEXT NOT NULL
                    CHECK (asset_type IN ('audio','image','subtitle','video','json',
                                          'manuscript','character','viz_bg','other')),
    scene_number    INTEGER,                             -- NULL = 프로젝트 레벨 에셋
    file_path       TEXT NOT NULL,                       -- output_dir 기준 상대경로
    file_name       TEXT NOT NULL,
    file_size       INTEGER DEFAULT 0,                   -- bytes
    checksum        TEXT,                                -- SHA-256
    mime_type       TEXT,
    metadata        TEXT,                                -- JSON: duration, dimensions 등
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- 핵심 파일 버전 히스토리
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS file_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_type       TEXT NOT NULL
                    CHECK (file_type IN ('scene_specs','motion_plan','scene_decomposition',
                                         'manuscript','outline','manifest','character_plan',
                                         'art_style','subtitles_json','other')),
    version         INTEGER NOT NULL,
    file_path       TEXT NOT NULL,                       -- versions/ 디렉토리 내 경로
    file_size       INTEGER DEFAULT 0,
    checksum        TEXT,
    description     TEXT,
    created_by      TEXT,                                -- "visual-composer", "manual", "rollback" 등
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, file_type, version)
);

-- ═══════════════════════════════════════════
-- 이미지 라이선스 추적
-- ═══════════════════════════════════════════
CREATE TABLE IF NOT EXISTS asset_licenses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id        INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,                       -- "wikimedia", "serper", "pixabay", "fal-ai"
    source_url      TEXT,
    license_type    TEXT,                                -- "CC BY-SA 4.0", "editorial" 등
    attribution     TEXT,
    title           TEXT,
    metadata        TEXT,                                -- JSON
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════
-- 인덱스
-- ═══════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_project ON pipeline_runs(project_id, phase, step);
CREATE INDEX IF NOT EXISTS idx_assets_project_type ON assets(project_id, asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_project_scene ON assets(project_id, scene_number);
CREATE INDEX IF NOT EXISTS idx_file_versions_project ON file_versions(project_id, file_type);
CREATE INDEX IF NOT EXISTS idx_asset_licenses_asset ON asset_licenses(asset_id);

-- ═══════════════════════════════════════════
-- 트리거: projects.updated_at 자동 갱신
-- ═══════════════════════════════════════════
CREATE TRIGGER IF NOT EXISTS trg_projects_updated_at
    AFTER UPDATE ON projects
    BEGIN
        UPDATE projects SET updated_at = datetime('now') WHERE id = NEW.id;
    END;
