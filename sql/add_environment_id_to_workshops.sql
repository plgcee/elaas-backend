-- Add environment_id column to workshops table
-- This migration adds support for logical isolation of workshops into environments

-- Add environment_id column (nullable to support existing workshops)
ALTER TABLE workshops 
ADD COLUMN IF NOT EXISTS environment_id UUID REFERENCES environments(id) ON DELETE SET NULL;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_workshops_environment_id ON workshops(environment_id);

-- Add comment
COMMENT ON COLUMN workshops.environment_id IS 'Reference to the environment this workshop belongs to (nullable)';
