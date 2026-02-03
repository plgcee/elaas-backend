-- Migration: Add TTL (Time To Live) field to workshops table
-- Run this migration to add TTL support for automatic workshop destruction

ALTER TABLE workshops 
ADD COLUMN IF NOT EXISTS ttl_hours INTEGER DEFAULT 48;

ALTER TABLE workshops 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Create index for expiration lookups
CREATE INDEX IF NOT EXISTS idx_workshops_expires_at ON workshops(expires_at);

-- Add comments
COMMENT ON COLUMN workshops.ttl_hours IS 'Time to live in hours (default: 48). Workshop will be automatically destroyed after this time.';
COMMENT ON COLUMN workshops.expires_at IS 'Timestamp when workshop expires and should be automatically destroyed';
