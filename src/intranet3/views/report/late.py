# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from intranet3.utils.views import BaseView, MonthMixin
from intranet3.utils import excuses
from intranet3.helpers import next_month, previous_month
from intranet3.models import User, ApplicationConfig, Holiday
from intranet3.log import INFO_LOG, DEBUG_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)

am9 = datetime.time(9,0,0)
deltazero = datetime.timedelta(0)

@view_config(route_name='report_late_current', permission='hr')
class Current(BaseView):
    def get(self):
        today = datetime.date.today()
        return HTTPFound(location=self.request.url_for('/report/late/annually', year=today.year))

class AnnuallyReportMixin(object):

    def _prepare_statistics(self, data):
        stats = {}
        for user_id, d in data.iteritems():
            sum_annually = sum(d, datetime.timedelta())
            stats[user_id] = (sum_annually,)
        return stats

    def _group_by_user_monthly(self, data, excuses):
        """
        dictionary: user -> [timedelta * 12]
        We sum only whole minutes
        """
        result = {}
        holidays = Holiday.all()
        for user_id, date, presence in data:
            if presence.strftime('%Y-%m-%d') in excuses.get(user_id, []):
                continue
            user_data = result.setdefault(user_id, [deltazero] * 12)

            late = presence - datetime.datetime.combine(presence.date(), am9)
            late = late if late > datetime.timedelta(minutes=1) and not Holiday.is_holiday(date, holidays=holidays) else deltazero
            user_data[date.month - 1] += datetime.timedelta(days=late.days, minutes=int(late.seconds/60))
        return result

    def _annually_report(self, year):
        year_start = datetime.date(year, 1, 1)
        year_end = datetime.date(year, 12, 31)
        excuses_error = None
        config_obj = ApplicationConfig.get_current_config()
        query = self.session.query('uid', 'date', 'presence').from_statement("""
        SELECT p.user_id as "uid",
               date_trunc('day', p.ts) as "date",
               MIN(p.ts) as "presence"
        FROM presence_entry p
        WHERE p.ts >= :year_start AND
              p.ts <= :year_end
        GROUP BY p.user_id, date_trunc('day', p.ts)
        """).params(year_start=year_start, year_end=year_end)
        data = query.all()
        users = User.query.filter(User.is_active==True)\
                          .filter(User.is_not_client())\
                          .filter(User.freelancer==False)\
                          .order_by(User.name).all()

        _excuses = excuses.presence()


        data = self._group_by_user_monthly(data, _excuses)
        stats = self._prepare_statistics(data)

        return dict(
            data=data,
            users=users,
            stats=stats,

            today=datetime.datetime.today(),
            year_start=year_start,
            deltazero=deltazero,
            late_limit=config_obj.monthly_late_limit,
            excuses_error=excuses_error,
        )


@view_config(route_name='report_late_annually', permission='hr')
class Annually(AnnuallyReportMixin, BaseView):
    def get(self):
        year = self.request.GET.get('year')
        year = int(year)
        return self._annually_report(year)


@view_config(route_name='report_late_monthly', permission='hr')
class Monthly(MonthMixin, BaseView):

    def _group_by_user_monthly(self, data, user_id):
        result = {}
        _excuses = excuses.presence()
        holidays = Holiday.all()
        for date, presence, leave in data:
            day_data = result.setdefault(date.day, [0, 0, deltazero])

            day_data[0] = presence.strftime('%H:%M:%S')
            day_data[1] = leave.strftime('%H:%M:%S')
            late = presence - datetime.datetime.combine(presence.date(), am9)
            late = late if late > datetime.timedelta(minutes=1) and not Holiday.is_holiday(date, holidays=holidays) else deltazero
            excuse = '-'
            if presence.strftime('%Y-%m-%d') in _excuses.get(user_id, {}).keys():
                excuse = _excuses[user_id][presence.strftime('%Y-%m-%d')]
            day_data[2] = late, excuse
        return result

    def get(self):
        user_id = self.request.GET.get('user_id')
        month_start, month_end = self._get_month()
        user = User.query.filter(User.id==user_id).one()

        query = self.session.query('date', 'presence', 'leave').from_statement("""
        SELECT date_trunc('day', p.ts) as "date",
               MIN(p.ts) as "presence",
               MAX(p.ts) as "leave"
        FROM presence_entry p
        WHERE p.ts >= :month_start AND
              date_trunc('day', p.ts) <= :month_end AND
              p.user_id = :user_id
        GROUP BY date_trunc('day', p.ts)
        """).params(month_start=month_start, month_end=month_end, user_id=user_id)
        data = query.all()

        holidays = Holiday.all()

        data = self._group_by_user_monthly(data, user.id)

        return dict(
            data=data,
            user=user,
            is_holiday=lambda date: Holiday.is_holiday(date, holidays=holidays),

            month_start=month_start, month_end=month_end,
            next_month=next_month(month_start),
            prev_month=previous_month(month_start),
            deltazero=deltazero,
            datetime=datetime,
        )

