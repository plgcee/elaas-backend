-- Seed Permissions and Roles Script
-- This script populates the permissions and roles tables with the standard permission matrix
-- Run this script to initialize or update permissions and roles in the database

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Insert Permissions
-- Note: This uses INSERT ... ON CONFLICT to allow re-running the script safely

-- Users module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('users:create', 'users', 'create', 'Create user profiles'),
    ('users:read', 'users', 'read', 'Read user profiles'),
    ('users:update', 'users', 'update', 'Update user profiles'),
    ('users:delete', 'users', 'delete', 'Delete user profiles')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Templates module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('templates:create', 'templates', 'create', 'Create Terraform templates'),
    ('templates:read', 'templates', 'read', 'Read Terraform templates'),
    ('templates:update', 'templates', 'update', 'Update Terraform templates'),
    ('templates:delete', 'templates', 'delete', 'Delete Terraform templates'),
    ('templates:upload', 'templates', 'upload', 'Upload template files')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Workshops module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('workshops:create', 'workshops', 'create', 'Create workshops'),
    ('workshops:read', 'workshops', 'read', 'Read workshops'),
    ('workshops:update', 'workshops', 'update', 'Update workshops'),
    ('workshops:delete', 'workshops', 'delete', 'Delete workshops'),
    ('workshops:deploy', 'workshops', 'deploy', 'Deploy workshops')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Deployments module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('deployments:create', 'deployments', 'create', 'Create deployments'),
    ('deployments:read', 'deployments', 'read', 'Read deployments'),
    ('deployments:update', 'deployments', 'update', 'Update deployments'),
    ('deployments:delete', 'deployments', 'delete', 'Delete deployments'),
    ('deployments:cancel', 'deployments', 'cancel', 'Cancel in-progress deployment')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Groups module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('groups:create', 'groups', 'create', 'Create groups'),
    ('groups:read', 'groups', 'read', 'Read groups'),
    ('groups:update', 'groups', 'update', 'Update groups'),
    ('groups:delete', 'groups', 'delete', 'Delete groups'),
    ('groups:manage_members', 'groups', 'manage_members', 'Manage group members')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Roles module permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('roles:create', 'roles', 'create', 'Create roles'),
    ('roles:read', 'roles', 'read', 'Read roles'),
    ('roles:update', 'roles', 'update', 'Update roles'),
    ('roles:delete', 'roles', 'delete', 'Delete roles'),
    ('roles:assign', 'roles', 'assign', 'Assign roles to users/groups')
ON CONFLICT (name) DO UPDATE SET
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    description = EXCLUDED.description;

-- Insert Roles
-- Users module roles
INSERT INTO roles (name, description) VALUES
    ('users_admin', 'Full administrative access to user profile management'),
    ('users_viewer', 'Read-only access to user profile management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Templates module roles
INSERT INTO roles (name, description) VALUES
    ('templates_admin', 'Full administrative access to Terraform template management'),
    ('templates_viewer', 'Read-only access to Terraform template management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Workshops module roles
INSERT INTO roles (name, description) VALUES
    ('workshops_admin', 'Full administrative access to workshop deployment management'),
    ('workshops_viewer', 'Read-only access to workshop deployment management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Deployments module roles
INSERT INTO roles (name, description) VALUES
    ('deployments_admin', 'Full administrative access to deployment management'),
    ('deployments_viewer', 'Read-only access to deployment management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Groups module roles
INSERT INTO roles (name, description) VALUES
    ('groups_admin', 'Full administrative access to group management'),
    ('groups_viewer', 'Read-only access to group management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Roles module roles
INSERT INTO roles (name, description) VALUES
    ('roles_admin', 'Full administrative access to role and permission management'),
    ('roles_viewer', 'Read-only access to role and permission management')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    updated_at = NOW();

-- Assign Permissions to Roles
-- This uses a CTE to get permission and role IDs, then inserts the relationships

-- Users Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'users_admin'
  AND p.name IN ('users:create', 'users:read', 'users:update', 'users:delete')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Users Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'users_viewer'
  AND p.name = 'users:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Templates Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'templates_admin'
  AND p.name IN ('templates:create', 'templates:read', 'templates:update', 'templates:delete', 'templates:upload')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Templates Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'templates_viewer'
  AND p.name = 'templates:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Workshops Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'workshops_admin'
  AND p.name IN ('workshops:create', 'workshops:read', 'workshops:update', 'workshops:delete', 'workshops:deploy')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Workshops Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'workshops_viewer'
  AND p.name = 'workshops:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Deployments Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'deployments_admin'
  AND p.name IN ('deployments:create', 'deployments:read', 'deployments:update', 'deployments:delete', 'deployments:cancel')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Deployments Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'deployments_viewer'
  AND p.name = 'deployments:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Groups Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'groups_admin'
  AND p.name IN ('groups:create', 'groups:read', 'groups:update', 'groups:delete', 'groups:manage_members')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Groups Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'groups_viewer'
  AND p.name = 'groups:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Roles Admin role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'roles_admin'
  AND p.name IN ('roles:create', 'roles:read', 'roles:update', 'roles:delete', 'roles:assign')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Roles Viewer role permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'roles_viewer'
  AND p.name = 'roles:read'
ON CONFLICT (role_id, permission_id) DO NOTHING;
