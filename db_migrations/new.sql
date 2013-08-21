CREATE TABLE teams (
	id SERIAL NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE team_members (
	id SERIAL NOT NULL, 
	team_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT team_members_team_id_user_id_unique UNIQUE (team_id, user_id), 
	FOREIGN KEY(team_id) REFERENCES teams (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);
