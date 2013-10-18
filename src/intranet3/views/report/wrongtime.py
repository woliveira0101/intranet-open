# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

from intranet3.utils.views import BaseView, MonthMixin
from intranet3.utils import excuses
from intranet3.helpers import next_month, previous_month
from intranet3.models import ApplicationConfig, User, Holiday
from intranet3.log import INFO_LOG, DEBUG_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


@view_config(route_name='report_wrongtime_current', permission='hr')
class Current(BaseView):
    def get(self):
        today = datetime.date.today()
        return HTTPFound(location=self.request.url_for('/report/wrongtime/annually', year=today.year))


class AnnuallyReportMixin(object):

    def _annually_report(self, year):
        year_start = datetime.date(year, 1, 1)
        year_end = datetime.date(year, 12, 31)
        excuses_error = None
        config_obj = ApplicationConfig.get_current_config()
        entries = self.session.query('user_id', 'date').from_statement("""
        SELECT date_trunc('day', s.date) as date, s.user_id as user_id
        FROM time_entry s
        WHERE DATE(s.modified_ts) > s.date AND
              s.date >= :year_start AND
              s.date <= :year_end
        GROUP BY date_trunc('day', s.date), s.user_id
        """).params(year_start=year_start, year_end=year_end)

        users = User.query.filter(User.is_active==True)\
                          .filter(User.is_not_client())\
                          .order_by(User.freelancer, User.name)

        entries_grouped = {}
        _excuses = excuses.wrongtime()

        for user_id, date in entries:
            month = date.month - 1
            entry = entries_grouped.setdefault(user_id, [0]*12)
            if date.strftime('%Y-%m-%d') not in _excuses.get(user_id, {}).keys():
                entry[month] += 1

        stats = {}

        for user_id, entry in entries_grouped.iteritems():
            stats_entry = stats.setdefault(user_id, [0])
            stats_entry[0] = sum(entry)

        return dict(
            entries=entries_grouped,
            stats=stats,
            users=users,
            year_start=year_start,
            limit=config_obj.monthly_incorrect_time_record_limit,
            excuses_error=excuses_error,
        )


@view_config(route_name='report_wrongtime_annually', permission='hr')
class Annually(AnnuallyReportMixin, BaseView):
    def get(self):
        year = self.request.GET.get('year')
        year = int(year)
        return self._annually_report(year)


@view_config(route_name='report_wrongtime_monthly', permission='hr')
class Monthly(MonthMixin, BaseView):

    def _group_by_user_monthly(self, data, user_id):
        result = {}
        _excuses = excuses.wrongtime()
        for date, incorrect_count in data:
            day_data = result.setdefault(date.day, [0, ''])

            excuse = '-'
            if date.strftime('%Y-%m-%d') in _excuses.get(user_id, {}).keys():
                excuse = _excuses[user_id][date.strftime('%Y-%m-%d')]
            day_data[0] = incorrect_count
            day_data[1] = excuse
        return result

    def get(self):
        user_id = self.request.GET.get('user_id')
        month_start, month_end = self._get_month()
        user = User.query.filter(User.id==user_id).one()

        query = self.session.query('date', 'incorrect_count').from_statement("""
            SELECT  date, COUNT(date) as incorrect_count
            FROM time_entry s
            WHERE DATE(s.modified_ts) > s.date AND
                  s.user_id = :user_id AND
                  s.date >= :month_start AND
                  s.date <= :month_end
            GROUP BY date
        """).params(month_start=month_start, month_end=month_end, user_id=user.id)
        data = query.all()

        data = self._group_by_user_monthly(data, user.id)

        holidays = Holiday.all()

        return dict(
            data=data,
            user=user,
            is_holiday=lambda date: Holiday.is_holiday(date, holidays=holidays),

            month_start=month_start, month_end=month_end,
            next_month=next_month(month_start),
            prev_month=previous_month(month_start),
            datetime=datetime,
        )

