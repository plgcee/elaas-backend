# Supabase table: templates
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py

"""
Expected Supabase table structure:
- id: uuid (primary key)
- name: text (not null)
- description: text (nullable)
- version: text (not null, default: '1.0.0')
- user_id: uuid (foreign key to users.id, not null)
- zip_file_path: text (nullable) - S3 path or Supabase Storage path
- variables_json: jsonb (nullable) - Parsed Terraform variables for form generation
- ui_variables_json: jsonb (nullable) - Which variables to show/edit in UI (from ui-variables.json in ZIP)
- validation_issues: text[] (nullable) - List of validation warnings/errors
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)
"""
