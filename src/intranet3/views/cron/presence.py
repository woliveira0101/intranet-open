# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from intranet3 import config
from intranet3.models import ApplicationConfig
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
        date = datetime.datetime.combine(date, day_end)
        cleaned = self.session.execute("""
            DELETE FROM presence_entry as p
            WHERE p.ts <= :date
            AND p.ts > (
                SELECT MIN(a.ts) FROM presence_entry a
                WHERE date_trunc('day', a.ts) = date_trunc('day', p.ts)
                AND a.user_id = p.user_id
            ) AND p.ts < (
                SELECT MAX(b.ts) FROM presence_entry b
                WHERE date_trunc('day', b.ts) = date_trunc('day', p.ts)
                AND b.user_id = p.user_id
            );
        """, params= {'date': date}).rowcount
        LOG(u"Cleaned %s entries" % (cleaned, ))
        return Response(self._(u"Cleaned ${num} entries", num=cleaned))
