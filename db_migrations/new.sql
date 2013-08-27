-- add bugs_project_ids
ALTER TABLE sprint DROP COLUMN IF EXISTS bugs_project_ids;
ALTER TABLE sprint ADD COLUMN bugs_project_ids INTEGER;

UPDATE sprint s1
SET bugs_project_ids = s2.project_id
FROM sprint s2;

ALTER TABLE sprint ALTER COLUMN bugs_project_ids TYPE INTEGER[] USING array[project_id]::INTEGER[];
-- add bugs_project_ids
-- add github to tracker.type
BEGIN;
ALTER type tracker_type_enum RENAME to old__tracker_type_enum;
CREATE type tracker_type_enum as enum ('bugzilla', 'trac', 'cookie_trac', 'igozilla', 'bitbucket', 'rockzilla', 'pivotaltracker', 'harvest', 'unfuddle', 'github');
ALTER TABLE tracker ALTER COLUMN type TYPE tracker_type_enum USING type::text::tracker_type_enum;
DROP type old__tracker_type_enum;
COMMIT;
-- add github to tracker.type