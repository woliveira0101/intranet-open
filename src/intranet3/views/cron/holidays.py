# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response

from intranet3.utils.views import CronView
from intranet3.log import INFO_LOG, EXCEPTION_LOG
from intranet3.helpers import SpreadsheetConnector
from intranet3.models import ApplicationConfig, Holiday, DBSession

INFO = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


@view_config(route_name='cron_holidays_sync', permission='cron')
class Sync(CronView):
    def action(self):
        config_obj = ApplicationConfig.get_current_config()
        client = SpreadsheetConnector(config_obj.google_user_email, config_obj.google_user_password)
        worksheet = client.get_worksheet(config_obj.holidays_spreadsheet, 6)
        data = worksheet.FindRecords('')
        dates_new = set([ datetime.datetime.strptime(d.content['data'], '%Y-%m-%d').date() for d in data ])
        dates_old = set(Holiday.all(cache=False))
        dates_diff = dates_new.difference(dates_old)

        if dates_diff:
            holidays = [ Holiday(date=date) for date in dates_diff ]
            DBSession.add_all(holidays)

        INFO(u'%s Holidays added: %s' % (len(dates_diff), dates_diff))
        return Response('ok')

