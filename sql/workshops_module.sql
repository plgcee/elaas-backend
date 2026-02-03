-- Workshops Module Tables
-- This file creates all tables required for the workshops module
-- Compatible with Supabase PostgreSQL
-- Note: Requires auth.users and templates tables

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Workshops table
-- Stores workshop instances that use Terraform templates for deployment
CREATE TABLE IF NOT EXISTS workshops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    terraform_vars JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'deploying', 'deployed', 'failed', 'destroying', 'destroyed')),
    fargate_task_arn TEXT,
    deployment_output JSONB,
    ttl_hours INTEGER DEFAULT 48,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_workshops_user_id ON workshops(user_id);
CREATE INDEX IF NOT EXISTS idx_workshops_template_id ON workshops(template_id);
CREATE INDEX IF NOT EXISTS idx_workshops_name ON workshops(name);
CREATE INDEX IF NOT EXISTS idx_workshops_status ON workshops(status);
CREATE INDEX IF NOT EXISTS idx_workshops_created_at ON workshops(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workshops_expires_at ON workshops(expires_at);

-- GIN index for terraform_vars queries
CREATE INDEX IF NOT EXISTS idx_workshops_terraform_vars ON workshops USING GIN (terraform_vars jsonb_path_ops);

-- GIN index for deployment_output queries
CREATE INDEX IF NOT EXISTS idx_workshops_deployment_output ON workshops USING GIN (deployment_output jsonb_path_ops);

-- Add comments for documentation
COMMENT ON TABLE workshops IS 'Stores workshop instances that use Terraform templates for infrastructure deployment';
COMMENT ON COLUMN workshops.id IS 'Primary key (UUID)';
COMMENT ON COLUMN workshops.name IS 'Workshop display name';
COMMENT ON COLUMN workshops.description IS 'Optional description of the workshop';
COMMENT ON COLUMN workshops.template_id IS 'Reference to the Terraform template used for this workshop';
COMMENT ON COLUMN workshops.user_id IS 'Owner/creator (references auth.users)';
COMMENT ON COLUMN workshops.terraform_vars IS 'Terraform variables for deployment (AWS keys obfuscated)';
COMMENT ON COLUMN workshops.status IS 'Workshop status: pending, deploying, deployed, failed, destroying, destroyed';
COMMENT ON COLUMN workshops.fargate_task_arn IS 'AWS Fargate task ARN if applicable';
COMMENT ON COLUMN workshops.deployment_output IS 'Terraform output after successful deployment';
COMMENT ON COLUMN workshops.ttl_hours IS 'Time to live in hours (default: 48). Workshop will be automatically destroyed after this time.';
COMMENT ON COLUMN workshops.expires_at IS 'Timestamp when workshop expires and should be automatically destroyed';
COMMENT ON COLUMN workshops.created_at IS 'Creation timestamp';
COMMENT ON COLUMN workshops.updated_at IS 'Last update timestamp';
