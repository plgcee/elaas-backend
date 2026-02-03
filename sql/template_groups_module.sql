-- Template Groups Module Tables
-- Groups templates together (many-to-many). Org-wide visibility (no user_id).
-- Run after templates_module.sql.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Template groups table (org-wide)
CREATE TABLE IF NOT EXISTS template_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_template_groups_name ON template_groups(name);
CREATE INDEX IF NOT EXISTS idx_template_groups_created_at ON template_groups(created_at DESC);

-- Junction: template <-> template_group (many-to-many)
CREATE TABLE IF NOT EXISTS template_group_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    template_group_id UUID NOT NULL REFERENCES template_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT template_group_assignments_unique UNIQUE (template_id, template_group_id)
);

CREATE INDEX IF NOT EXISTS idx_template_group_assignments_template_id ON template_group_assignments(template_id);
CREATE INDEX IF NOT EXISTS idx_template_group_assignments_template_group_id ON template_group_assignments(template_group_id);

COMMENT ON TABLE template_groups IS 'Template groups for organizing templates; org-wide visibility';
COMMENT ON TABLE template_group_assignments IS 'Junction table linking templates to template groups (many-to-many)';
