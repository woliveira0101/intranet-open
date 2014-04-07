# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from intranet3 import config
from intranet3.models import ApplicationConfig, DBSession
from intranet3.utils.views import CronView
from intranet3.log import INFO_LOG, EXCEPTION_LOG
from intranet3.utils import mail
from intranet3.views.report.late import AnnuallyReportMixin

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

day_end = datetime.time(23, 59, 59)

@view_config(route_name='cron_presence_report', permission='cron')
class Report(AnnuallyReportMixin, CronView):
    """
    DISALBED
    """

    def action(self):
        today = datetime.date.today()
        data = self._annually_report(today.year)
        data['config'] = self.request.registry.settings
        response = render('intranet3:templates/_email_reports/presence_annually_report.html', data, self.request)
        response = response.replace('\n', '').replace('\t', '')
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                self._(u'[Intranet2] Late report'),
                html_message=response,
            )
        return Response('ok')


@view_config(route_name='cron_presence_clean', permission='cron')
class Clean(AnnuallyReportMixin, CronView):
    def action(self):
        config_obj = ApplicationConfig.get_current_config()
        cleaning_time_presence = int(config_obj.cleaning_time_presence)

        today = datetime.datetime.now().date()
        date = today - datetime.timedelta(days=cleaning_time_presence)
        end_date = datetime.datetime.combine(date, day_end)
        start_date = end_date - datetime.timedelta(
            days=cleaning_time_presence*3,
        )
        cleaned = DBSession.execute("""
            WITH minq as
            (
                SELECT MIN(p1.id) FROM presence_entry as p1
                WHERE p1.ts >= :start_date AND p1.ts <= :end_date
                GROUP BY p1.user_id, date_trunc('day', p1.ts)
            ),
            maxq as
            (
                SELECT MAX(p2.id) FROM presence_entry as p2
                WHERE p2.ts >= :start_date AND p2.ts <= :end_date
                GROUP BY p2.user_id, date_trunc('day', p2.ts)
            )
            DELETE FROM presence_entry as p
            WHERE p.ts >= :start_date AND p.ts <= :end_date
            AND p.id NOT IN (SELECT * FROM minq) AND p.id NOT IN (SELECT * FROM maxq);
        """, params= {'start_date': start_date, 'end_date': end_date}).rowcount
        LOG(u"Cleaned %s entries" % (cleaned, ))
        return Response(self._(u"Cleaned ${num} entries", num=cleaned))
