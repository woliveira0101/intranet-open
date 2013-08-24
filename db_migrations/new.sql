ALTER TABLE "user" DROP COLUMN freelancer;
-- add bugs_project_ids
ALTER TABLE sprint DROP COLUMN IF EXISTS bugs_project_ids;
ALTER TABLE sprint ADD COLUMN bugs_project_ids INTEGER;

UPDATE sprint s1
SET bugs_project_ids = s2.project_id
FROM sprint s2;

ALTER TABLE sprint ALTER COLUMN bugs_project_ids TYPE INTEGER[] USING array[project_id]::INTEGER[];
-- add bugs_project_ids
