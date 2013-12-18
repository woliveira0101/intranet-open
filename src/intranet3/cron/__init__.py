# -*- coding: utf-8 -*-


from task import URLCronTask
from intranet3.log import INFO_LOG, EXCEPTION_LOG, WARN_LOG
from intranet3.utils.mail_fetcher import MailCheckerTask
from failsafe import Repeater, RequiredAction

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
WARN= WARN_LOG(__name__)


sync_holidays = URLCronTask(
    u'Holidays synchronization ',
    '/cron/holidays/sync'
)
clean = URLCronTask(
    u'Cleaning delay entries',
    '/cron/presence/clean',
)
resolved_notification = URLCronTask(
    u'Resolved bugs notification',
    '/cron/remind/resolved_bugs',
)
missing_hours_notification = URLCronTask(
    u'Missing hours notification',
    '/cron/remind/missing_hours',
)
mailer = MailCheckerTask()

## Reports
report_with_today_hours = URLCronTask(
    u'Report with hours added today',
    '/cron/times/today_hours',
)
report_with_today_hours_without_ticket = URLCronTask(
    u'Report with hours without ticket added today',
    '/cron/times/daily_hours_without_ticket',
)
report_with_hours_added_for_prev_months = URLCronTask(
    u'Report with entries added for previous months',
    '/cron/times/hours_for_previous_months',
)
annually_time_report_email = URLCronTask(
    u'Report with incorrect time records',
    '/cron/times/wrong_time_report',
)
old_bugs_report_email = URLCronTask(
    u'Report with old bugs',
    '/cron/bugs/old_bugs_report',
)
tickets_report_with_excel = URLCronTask(
    u'Report with ticket times in excel',
    '/cron/times/excel_report',
)
missed_hours = URLCronTask(
    u'Missed hours report',
    '/cron/times/missed_hours',
)

repeater = Repeater(
    RequiredAction('sync_client_hours', lambda date: '/cron/time/client_hours'),
)

cron_tasks = (
    #func, cron_line
    (clean, (-1, -1, -1, -1, -1)),
#    (sync_holidays, '1 0 * * *'),
#    (resolved_notification, '0 7 * * *'),
#    (missing_hours_notification, '0 19 * * *'),
#    (repeater, '1 0 1,2,3,4,5 * *'), # at 00:01 every first 5 days of month
#    (report_with_today_hours, '1 0 * * *'), # at 00:01 every day
#    (report_with_today_hours_without_ticket, '1 0 * * *'), # at 00:01 every day
#    (report_with_hours_added_for_prev_months, '1 0 * * *'), # at 00:01 every day

#    (tickets_report_with_excel, '1 1 2 * *'),
#    (annually_time_report_email, '1 0 28 * *'),
#    (old_bugs_report_email, '1 0 1 * * '),
#    (missed_hours, '1 0 1,2 * *'), # at 00:01 every first 2 days of month
)

timer_tasks = (
    (mailer, 60), # every 60 second
)

def run_cron_tasks():
    from uwsgidecorators import cron, timer
    for task in cron_tasks:
        f, cron_line = task

        cron_job = cron(*cron_line)
        cron_job(f)

    for task in timer_tasks:
        f, sec = task
        timer_job = timer(sec)
        timer_job(f)


