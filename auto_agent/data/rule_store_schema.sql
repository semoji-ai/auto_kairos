-- ═══════════════════════════════════════════
-- Rule Store: 중앙 규칙 관리 테이블
-- ═══════════════════════════════════════════

-- rule_store: 규칙 파일 중앙 저장소
CREATE TABLE IF NOT EXISTS rule_store (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    rule_type   TEXT NOT NULL
                CHECK (rule_type IN ('prompt','pipeline','agent_config','skill','artstyle')),
    checksum    TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_rule_store_type ON rule_store(rule_type);

-- rule_versions: 규칙 변경 히스토리
CREATE TABLE IF NOT EXISTS rule_versions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_key    TEXT NOT NULL,
    version     INTEGER NOT NULL,
    content     TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    description TEXT,
    created_by  TEXT DEFAULT 'system',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(rule_key, version)
);

CREATE INDEX IF NOT EXISTS idx_rule_versions_key ON rule_versions(rule_key, version DESC);

-- updated_at 자동 갱신 (update_updated_at 함수는 기존 supabase_schema.sql에서 이미 생성됨)
CREATE TRIGGER trg_rule_store_updated_at
    BEFORE UPDATE ON rule_store
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
