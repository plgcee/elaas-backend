-- Add template_group_id to workshops for template-group deployments.
-- When template_group_id is set, workshop deploys all templates in that group (one deployment per template).
-- template_id becomes nullable for group workshops.

-- Add column (requires template_groups table to exist)
ALTER TABLE workshops
ADD COLUMN IF NOT EXISTS template_group_id UUID REFERENCES template_groups(id) ON DELETE SET NULL;

-- Make template_id nullable (for group workshops)
ALTER TABLE workshops
ALTER COLUMN template_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workshops_template_group_id ON workshops(template_group_id);
