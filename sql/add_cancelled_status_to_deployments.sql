-- Add 'cancelled' to deployments.status allowed values
-- Run after deployments_module.sql

ALTER TABLE deployments DROP CONSTRAINT IF EXISTS deployments_status_check;
ALTER TABLE deployments ADD CONSTRAINT deployments_status_check
    CHECK (status IN ('pending', 'deploying', 'deployed', 'failed', 'cancelled'));

COMMENT ON COLUMN deployments.status IS 'Deployment status: pending, deploying, deployed, failed, cancelled';
