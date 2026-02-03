-- Migration: Add environment field to templates table
-- Run this migration to add environment support for multi-cloud deployments

ALTER TABLE templates 
ADD COLUMN IF NOT EXISTS environment TEXT;

-- Create index for environment lookups
CREATE INDEX IF NOT EXISTS idx_templates_environment ON templates(environment);

-- Add comment
COMMENT ON COLUMN templates.environment IS 'Target environment for deployment (AWS, GCP, Azure, MongoDB, Snowflake, etc.)';
