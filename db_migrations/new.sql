ALTER TABLE sprint
	ADD COLUMN velocity REAL NOT NULL DEFAULT 0.0,
	ADD COLUMN story_velocity REAL NOT NULL DEFAULT 0.0,
	ADD COLUMN velocity_mean REAL NOT NULL DEFAULT 0.0,
	ADD COLUMN story_velocity_mean REAL NOT NULL DEFAULT 0.0;

UPDATE sprint
	SET velocity = CASE
		WHEN worked_hours != 0 THEN
			8 * achieved_points / worked_hours
		ELSE
			0
		END;

UPDATE sprint
	SET story_velocity = CASE
		WHEN bugs_worked_hours != 0 THEN
			8 * achieved_points / bugs_worked_hours
		ELSE
			0
		END;

UPDATE sprint as this_sprint SET velocity_mean = (
    SELECT avg(velocity) from sprint
    WHERE project_id = this_sprint.project_id
);

UPDATE sprint as this_sprint SET story_velocity_mean = (
    SELECT avg(story_velocity) from sprint
    WHERE project_id = this_sprint.project_id
);
