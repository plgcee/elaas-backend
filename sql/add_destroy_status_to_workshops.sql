-- Migration: Add destroying and destroyed statuses to workshops table
-- Run this migration to support infrastructure destruction

-- Drop existing check constraint
ALTER TABLE workshops DROP CONSTRAINT IF EXISTS workshops_status_check;

-- Add new check constraint with destroy statuses
ALTER TABLE workshops 
ADD CONSTRAINT workshops_status_check 
CHECK (status IN ('pending', 'deploying', 'deployed', 'failed', 'destroying', 'destroyed'));

-- Update comment
COMMENT ON COLUMN workshops.status IS 'Workshop status: pending, deploying, deployed, failed, destroying, destroyed';
