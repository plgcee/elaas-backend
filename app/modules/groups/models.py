# Supabase tables: groups, group_members, group_roles
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py

"""
Expected Supabase table structure:

groups:
- id: uuid (primary key)
- name: text (not null)
- description: text (nullable)
- user_id: uuid (foreign key to users.id, not null) - owner/creator
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)

group_members:
- id: uuid (primary key)
- group_id: uuid (foreign key to groups.id, not null)
- user_id: uuid (foreign key to users.id, not null)
- role: text (not null, default: 'member') - values: owner, admin, member
- created_at: timestamp (default: now())

group_roles:
- id: uuid (primary key)
- group_id: uuid (foreign key to groups.id, not null)
- role_id: uuid (foreign key to roles.id, not null)
- created_at: timestamp (default: now())
- unique constraint on (group_id, role_id)
"""
