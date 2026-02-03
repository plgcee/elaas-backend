-- Add ui_variables_json to templates (variables to show/edit in UI)
ALTER TABLE templates
ADD COLUMN IF NOT EXISTS ui_variables_json JSONB;

COMMENT ON COLUMN templates.ui_variables_json IS 'JSON defining which variables to show and allow editing in the UI (e.g. from ui-variables.json in template ZIP)';
