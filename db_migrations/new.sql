UPDATE "user" SET groups = string_to_array(replace(array_to_string(groups, ','), 'user', 'employee'), ',');
UPDATE "user" SET groups = string_to_array(replace(array_to_string(groups, ','), 'scrum', 'scrum master'), ',');
