# Supabase table: environments
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py

"""
Expected Supabase table structure:
- id: uuid (primary key)
- name: text (not null)
- description: text (nullable)
- group_id: uuid (foreign key to groups.id, not null)
- user_id: uuid (foreign key to users.id, not null) - creator/owner
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)
- unique constraint on (name, group_id)
"""
