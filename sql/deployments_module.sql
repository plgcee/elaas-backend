-- Deployments Module Tables
-- This file creates all tables required for the deployments module
-- Compatible with Supabase PostgreSQL
-- Note: Requires auth.users, workshops, and templates tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Deployments table
-- Stores deployment records for workshops
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workshop_id UUID NOT NULL REFERENCES workshops(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'deploying', 'deployed', 'failed')),
    terraform_vars JSONB NOT NULL DEFAULT '{}',
    deployment_logs TEXT[] DEFAULT ARRAY[]::TEXT[],
    terraform_state_key TEXT,
    deployment_output JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_deployments_workshop_id ON deployments(workshop_id);
CREATE INDEX IF NOT EXISTS idx_deployments_template_id ON deployments(template_id);
CREATE INDEX IF NOT EXISTS idx_deployments_user_id ON deployments(user_id);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_deployments_created_at ON deployments(created_at DESC);

-- GIN index for terraform_vars queries
CREATE INDEX IF NOT EXISTS idx_deployments_terraform_vars ON deployments USING GIN (terraform_vars jsonb_path_ops);

-- Add comments for documentation
COMMENT ON TABLE deployments IS 'Stores deployment records for workshops with Terraform infrastructure';
COMMENT ON COLUMN deployments.id IS 'Primary key (UUID)';
COMMENT ON COLUMN deployments.workshop_id IS 'Reference to the workshop being deployed';
COMMENT ON COLUMN deployments.template_id IS 'Reference to the template used for deployment';
COMMENT ON COLUMN deployments.user_id IS 'User who initiated the deployment';
COMMENT ON COLUMN deployments.status IS 'Deployment status: pending, deploying, deployed, failed';
COMMENT ON COLUMN deployments.terraform_vars IS 'Terraform variables used for deployment (AWS keys obfuscated)';
COMMENT ON COLUMN deployments.deployment_logs IS 'Array of deployment log lines';
COMMENT ON COLUMN deployments.terraform_state_key IS 'S3 key path for Terraform state file';
COMMENT ON COLUMN deployments.deployment_output IS 'Terraform output after successful deployment';
COMMENT ON COLUMN deployments.error_message IS 'Error message if deployment failed';
COMMENT ON COLUMN deployments.created_at IS 'Creation timestamp';
COMMENT ON COLUMN deployments.updated_at IS 'Last update timestamp';
COMMENT ON COLUMN deployments.completed_at IS 'Completion timestamp (success or failure)';
