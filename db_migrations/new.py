--add start/end
ALTER TABLE late ADD COLUMN late_start TIME;
ALTER TABLE late ADD COLUMN late_end TIME;
ALTER TABLE "user" ADD COLUMN notify_blacklist integer ARRAY;
--add start/end
