# Supabase tables: user_profiles, auth.users
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py
# Authentication is handled by Supabase Auth (auth.users table)

"""
Expected Supabase table structure:

user_profiles:
- id: uuid (primary key, references auth.users.id)
- email: text (unique, not null) - synced from auth.users
- full_name: text (nullable)
- avatar_url: text (nullable)
- phone: text (nullable)
- bio: text (nullable)
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)

Note: Authentication data (password, tokens) is stored in auth.users table
managed by Supabase Auth. This table only stores profile information.
"""
