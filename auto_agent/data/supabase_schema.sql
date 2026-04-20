-- ═══════════════════════════════════════════
-- Supabase (PostgreSQL) 스키마
-- UUID 기반 PK, 로컬 SQLite와 매핑
-- ═══════════════════════════════════════════

-- 기존 테이블 제거 (재생성용 — 초기 셋업 시에만 사용)
DROP TABLE IF EXISTS asset_licenses CASCADE;
DROP TABLE IF EXISTS file_versions CASCADE;
DROP TABLE IF EXISTS assets CASCADE;
DROP TABLE IF EXISTS pipeline_runs CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

-- 프로젝트 마스터
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    local_id        INTEGER,                                -- 로컬 SQLite id (매핑용)
    storage_key     TEXT,                                   -- Storage 경로 키 (ASCII-safe)
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    status          TEXT NOT NULL DEFAULT 'created'
                    CHECK (status IN ('created','in_progress','completed','archived','failed')),
    topic           TEXT,
    theme           TEXT DEFAULT 'simple',
    scene_count     INTEGER DEFAULT 0,
    total_duration_sec REAL DEFAULT 0.0,
    config          JSONB,
    output_dir      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- 파이프라인 실행 기록
CREATE TABLE pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    phase           TEXT NOT NULL,
    step            TEXT NOT NULL,
    step_name       TEXT,
    agent_or_module TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','completed','failed','skipped')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_sec    REAL,
    cost_tokens_in  INTEGER DEFAULT 0,
    cost_tokens_out INTEGER DEFAULT 0,
    cost_usd        REAL DEFAULT 0.0,
    error_log       TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 에셋 파일 레지스트리
CREATE TABLE assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_type      TEXT NOT NULL
                    CHECK (asset_type IN ('audio','image','subtitle','video','json',
                                          'manuscript','character','viz_bg','other')),
    scene_number    INTEGER,
    file_path       TEXT NOT NULL,                          -- storage 상대경로
    file_name       TEXT NOT NULL,
    file_size       INTEGER DEFAULT 0,
    checksum        TEXT,
    mime_type       TEXT,
    storage_url     TEXT,                                   -- Supabase Storage public URL
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 핵심 파일 버전 히스토리
CREATE TABLE file_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_type       TEXT NOT NULL
                    CHECK (file_type IN ('scene_specs','motion_plan','scene_decomposition',
                                         'manuscript','outline','manifest','character_plan',
                                         'art_style','subtitles_json','other')),
    version         INTEGER NOT NULL,
    file_path       TEXT NOT NULL,
    file_size       INTEGER DEFAULT 0,
    checksum        TEXT,
    storage_url     TEXT,
    description     TEXT,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(project_id, file_type, version)
);

-- 이미지 라이선스 추적
CREATE TABLE asset_licenses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id        UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,
    source_url      TEXT,
    license_type    TEXT,
    attribution     TEXT,
    title           TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_pipeline_runs_project ON pipeline_runs(project_id, phase, step);
CREATE INDEX idx_assets_project_type ON assets(project_id, asset_type);
CREATE INDEX idx_assets_project_scene ON assets(project_id, scene_number);
CREATE INDEX idx_file_versions_project ON file_versions(project_id, file_type);
CREATE INDEX idx_asset_licenses_asset ON asset_licenses(asset_id);

-- RLS (Row Level Security) — 필요 시 활성화
-- ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
