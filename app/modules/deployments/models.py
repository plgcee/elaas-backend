# Supabase table: deployments
# This file documents the expected database schema
# Actual operations are handled via Supabase SDK in service.py

"""
Expected Supabase table structure:
- id: uuid (primary key)
- workshop_id: uuid (foreign key to workshops.id, not null)
- template_id: uuid (foreign key to templates.id, not null)
- user_id: uuid (foreign key to users.id, not null)
- status: text (not null, default: 'pending') - values: pending, deploying, deployed, failed
- terraform_vars: jsonb (not null, default: {})
- deployment_logs: text[] (default: [])
- terraform_state_key: text (nullable)
- deployment_output: jsonb (nullable)
- error_message: text (nullable)
- created_at: timestamp (default: now())
- updated_at: timestamp (nullable)
- completed_at: timestamp (nullable)
"""
