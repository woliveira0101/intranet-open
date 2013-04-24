ALTER TABLE project ADD COLUMN working_agreement TEXT NOT NULL DEFAULT '';
ALTER TABLE project ADD COLUMN definition_of_done TEXT NOT NULL DEFAULT '';
ALTER TABLE project ADD COLUMN continuous_integration_url CHARACTER VARYING NOT NULL DEFAULT '';
