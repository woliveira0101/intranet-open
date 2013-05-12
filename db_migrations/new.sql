ALTER TABLE project ADD COLUMN backlog_url VARCHAR NOT NULL default '';
ALTER TABLE project ADD COLUMN definition_of_ready TEXT NOT NULL DEFAULT '';
ALTER TABLE sprint ADD COLUMN retrospective_note TEXT NOT NULL DEFAULT '';
