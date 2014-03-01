ALTER TABLE "user" DROP COLUMN "freelancer" RESTRICT;
ALTER TABLE "user" DROP COLUMN "is_programmer" RESTRICT;
ALTER TABLE "user" DROP COLUMN "is_graphic_designer" RESTRICT;
ALTER TABLE "user" DROP COLUMN "is_frontend_developer" RESTRICT;
ALTER TABLE "user" ADD COLUMN "start_work_experience" DATE DEFAULT NULL;
