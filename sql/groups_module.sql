-- Groups Module Tables
-- This file creates all tables required for the groups module
-- Compatible with Supabase PostgreSQL
-- Note: Requires roles table to exist (run roles_module.sql first)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Groups table
CREATE TABLE IF NOT EXISTS groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT groups_name_user_unique UNIQUE (name, user_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_groups_user_id ON groups(user_id);
CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name);
CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups(created_at DESC);

-- Group Members table (user-group associations)
CREATE TABLE IF NOT EXISTS group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT group_members_unique UNIQUE (group_id, user_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id);
CREATE INDEX IF NOT EXISTS idx_group_members_role ON group_members(role);

-- Group Roles table (group-role associations)
-- Links groups to roles from the roles module
CREATE TABLE IF NOT EXISTS group_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT group_roles_unique UNIQUE (group_id, role_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_group_roles_group_id ON group_roles(group_id);
CREATE INDEX IF NOT EXISTS idx_group_roles_role_id ON group_roles(role_id);

-- Add comments for documentation
COMMENT ON TABLE groups IS 'Stores all groups in the system';
COMMENT ON TABLE group_members IS 'Junction table linking users to groups with their membership role';
COMMENT ON TABLE group_roles IS 'Junction table linking groups to roles';

COMMENT ON COLUMN groups.name IS 'Group name';
COMMENT ON COLUMN groups.user_id IS 'Owner/creator of the group (references auth.users)';
COMMENT ON COLUMN group_members.role IS 'Membership role: owner, admin, or member';
COMMENT ON COLUMN group_members.group_id IS 'Reference to the group';
COMMENT ON COLUMN group_members.user_id IS 'Reference to the user (from auth.users)';
COMMENT ON COLUMN group_roles.group_id IS 'Reference to the group';
COMMENT ON COLUMN group_roles.role_id IS 'Reference to the role (from roles table)';
