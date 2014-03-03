ALTER TABLE "tracker_credentials" ADD COLUMN "credentials_json" TEXT
NOT NULL DEFAULT '';

UPDATE tracker_credentials
SET credentials_json =
    --split login and email by semicolon if pivotal tracker
    CASE WHEN tracker_id IN (SELECT id FROM tracker WHERE type = 'pivotaltracker')
         THEN
             '{"login": "' || split_part(login, ';', 2) || '", ' ||
             '"password": "' || password || '", ' ||
             '"email": "' || split_part(login, ';', 1) || '"}'
	 ELSE '{"login": "' || login || '","password": "' || password || '"}'
    END;

ALTER TABLE "tracker_credentials" DROP COLUMN "login";
ALTER TABLE "tracker_credentials" DROP COLUMN "password";
ALTER TABLE "tracker" ADD COLUMN "description" TEXT DEFAULT '';
