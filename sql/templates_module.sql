-- Templates Module Tables
-- This file creates all tables required for the templates module
-- Compatible with Supabase PostgreSQL
-- Note: Requires auth.users (Supabase Auth). Run after users/roles if you use user_profiles.

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Templates table
-- Stores Terraform template metadata, ZIP path, and parsed variables JSON for form generation
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL DEFAULT '1.0.0',
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    zip_file_path TEXT,
    variables_json JSONB,
    validation_issues TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_templates_user_id ON templates(user_id);
CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name);
CREATE INDEX IF NOT EXISTS idx_templates_created_at ON templates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_templates_version ON templates(version);

-- GIN index for variables_json queries (e.g. jsonb_path_ops)
CREATE INDEX IF NOT EXISTS idx_templates_variables_json ON templates USING GIN (variables_json jsonb_path_ops);

-- Add comments for documentation
COMMENT ON TABLE templates IS 'Stores Terraform template metadata, ZIP file path (S3/Supabase Storage), and parsed variables JSON for frontend form generation';
COMMENT ON COLUMN templates.id IS 'Primary key (UUID)';
COMMENT ON COLUMN templates.name IS 'Template display name';
COMMENT ON COLUMN templates.description IS 'Optional description of the template';
COMMENT ON COLUMN templates.version IS 'Template version (e.g. 1.0.0)';
COMMENT ON COLUMN templates.user_id IS 'Owner/creator (references auth.users)';
COMMENT ON COLUMN templates.zip_file_path IS 'Path to Terraform ZIP in S3 or Supabase Storage';
COMMENT ON COLUMN templates.variables_json IS 'Parsed Terraform variables (variables + variable_count) for form generation';
COMMENT ON COLUMN templates.validation_issues IS 'List of validation warnings/errors from Terraform best-practices check';
COMMENT ON COLUMN templates.created_at IS 'Creation timestamp';
COMMENT ON COLUMN templates.updated_at IS 'Last update timestamp';
