--add sprint tabs
ALTER TABLE "project" ADD COLUMN "sprint_tabs" TEXT DEFAULT '';
--/add sprint tabs
ALTER TABLE "user" ADD COLUMN date_of_birth DATE DEFAULT NULL;
