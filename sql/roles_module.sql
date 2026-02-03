-- Roles Module Tables
-- This file creates all tables required for the roles and permissions module
-- Compatible with Supabase PostgreSQL

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT permissions_name_unique UNIQUE (name)
);

-- Create index on resource for faster filtering
CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);

-- Create index on action for faster filtering
CREATE INDEX IF NOT EXISTS idx_permissions_action ON permissions(action);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT roles_name_unique UNIQUE (name)
);

-- Create index on name for faster lookups
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- Role-Permissions junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS role_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT role_permissions_unique UNIQUE (role_id, permission_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);

-- Add comments for documentation
COMMENT ON TABLE permissions IS 'Stores all available permissions in the system';
COMMENT ON TABLE roles IS 'Stores all roles that can be assigned to users or groups';
COMMENT ON TABLE role_permissions IS 'Junction table linking roles to their associated permissions';

COMMENT ON COLUMN permissions.name IS 'Unique permission name (e.g., read_templates, deploy_workshops)';
COMMENT ON COLUMN permissions.resource IS 'Resource type (e.g., templates, workshops, users)';
COMMENT ON COLUMN permissions.action IS 'Action type (e.g., read, write, delete, deploy)';
COMMENT ON COLUMN roles.name IS 'Unique role name (e.g., admin, developer, viewer)';
