ALTER TABLE sprint DROP CONSTRAINT "sprint_project_id_fkey";
ALTER TABLE sprint ALTER COLUMN project_id TYPE INTEGER[] USING array[project_id]::INTEGER[];
ALTER TABLE sprint RENAME COLUMN project_id to project_ids;
