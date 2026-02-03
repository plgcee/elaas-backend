-- Environments Module Tables
-- This file creates all tables required for the environments module
-- Compatible with Supabase PostgreSQL
-- Note: Requires auth.users and groups tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Environments table
-- Stores logical isolation containers for workshops within groups
CREATE TABLE IF NOT EXISTS environments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT environments_name_group_unique UNIQUE (name, group_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_environments_group_id ON environments(group_id);
CREATE INDEX IF NOT EXISTS idx_environments_user_id ON environments(user_id);
CREATE INDEX IF NOT EXISTS idx_environments_name ON environments(name);
CREATE INDEX IF NOT EXISTS idx_environments_created_at ON environments(created_at DESC);

-- Add comments for documentation
COMMENT ON TABLE environments IS 'Stores logical isolation containers for workshops within groups';
COMMENT ON COLUMN environments.id IS 'Primary key (UUID)';
COMMENT ON COLUMN environments.name IS 'Environment display name (unique within group)';
COMMENT ON COLUMN environments.description IS 'Optional description of the environment';
COMMENT ON COLUMN environments.group_id IS 'Reference to the group this environment belongs to';
COMMENT ON COLUMN environments.user_id IS 'Creator/owner of the environment (references auth.users)';
COMMENT ON COLUMN environments.created_at IS 'Creation timestamp';
COMMENT ON COLUMN environments.updated_at IS 'Last update timestamp';
