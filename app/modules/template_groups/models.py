# Supabase tables: template_groups, template_group_assignments
# This file documents the expected database schema

"""
Expected Supabase table structure:

template_groups:
- id: uuid (primary key)
- name: text (not null)
- description: text (nullable)
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)

template_group_assignments:
- id: uuid (primary key)
- template_id: uuid (foreign key to templates.id, not null)
- template_group_id: uuid (foreign key to template_groups.id, not null)
- created_at: timestamp (default: now())
- unique constraint on (template_id, template_group_id)
"""
