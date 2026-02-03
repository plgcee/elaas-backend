# Supabase tables: permissions, roles, role_permissions
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py

"""
Expected Supabase table structure:

permissions:
- id: uuid (primary key)
- name: text (not null, unique) - e.g., "read_templates", "deploy_workshops"
- resource: text (not null) - e.g., "templates", "workshops", "users"
- action: text (not null) - e.g., "read", "write", "delete", "deploy"
- description: text (nullable)
- created_at: timestamp (default: now())

roles:
- id: uuid (primary key)
- name: text (not null, unique) - e.g., "admin", "developer", "viewer"
- description: text (nullable)
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)

role_permissions:
- id: uuid (primary key)
- role_id: uuid (foreign key to roles.id, not null)
- permission_id: uuid (foreign key to permissions.id, not null)
- created_at: timestamp (default: now())
- unique constraint on (role_id, permission_id)
"""
