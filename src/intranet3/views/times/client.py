from __future__ import division
import calendar
import datetime
from operator import itemgetter

import xlwt
from sqlalchemy import func
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPBadRequest, HTTPFound
from pyramid.response import Response

from intranet3 import config
from intranet3.utils.views import BaseView
from intranet3.forms.times import ClientTimeForm
from intranet3.log import INFO_LOG
from intranet3.models import Client, Project, TimeEntry
from intranet3 import helpers as h

LOG = INFO_LOG(__name__)

oneday = datetime.timedelta(days=1)


@view_config(route_name='times_client_report', permission='clients')
class Report(BaseView):
    def _get_start_end_of_month(self, date):
        year = date.year
        month = date.month
        try:
            start_date = datetime.date(year, month, 1)
        except ValueError:
            raise HTTPBadRequest()
        else:
            day_of_week, days_in_month = calendar.monthrange(year, month)
            end_date = datetime.date(year, month, days_in_month)
        return start_date, end_date

    def dispatch(self):
        form = ClientTimeForm(self.request.POST)

        if not (self.request.method == 'POST' and form.validate()):
            return dict(form=form)

        date = form.date.data
        month_start, month_end = self._get_start_end_of_month(date)
        clients = form.clients.data
        groupby = form.groupby.data

        q = self.session.query(Client.name, Project.name, func.sum(TimeEntry.time))\
                            .filter(TimeEntry.project_id==Project.id)\
                            .filter(Project.client_id==Client.id)\
                            .filter(Client.id.in_(clients))\
                            .filter(TimeEntry.date >= month_start)\
                            .filter(TimeEntry.date <= month_end)\
                            .filter(TimeEntry.deleted==False)\
                            .group_by(Client.name, Project.name)
        data = q.all()
        whole_sum = sum([row[2] for row in data])
        whole_sum_without_us = sum([row[2] for row in data if row[0] != config['COMPANY_NAME']])

        q = self.session.query(func.sum(TimeEntry.time))\
                            .filter(TimeEntry.project_id==Project.id)\
                            .filter(Project.client_id==Client.id)\
                            .filter(Client.id != 12)\
                            .filter(TimeEntry.date >= month_start)\
                            .filter(TimeEntry.date <= month_end)\
                            .filter(TimeEntry.deleted==False)
        our_monthly_hours = q.one()[0]

        if groupby == 'client':
            results = {}
            for client, project, time in data:
                results.setdefault(client, 0)
                results[client] += time
            results = results.items()

            data = results
            data.sort(key=itemgetter(0)) # client
        else:
            data.sort(key=itemgetter(0,1)) # client,project


        return dict(
            form=form,
            groupby=groupby,
            data=data,
            whole_sum=whole_sum,
            whole_sum_without_us=whole_sum_without_us,
            our_monthly_hours=our_monthly_hours,
        )


@view_config(route_name='times_client_per_client_per_employee_excel', permission='clients')
class PerClientPerEmployeeExcel(BaseView):
    def _to_excel(self, rows):
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet('Hours')

        heading_xf = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
        headings = ('Client name', 'Employee', 'Client time', 'Month', 'Month time')
        for colx, value in enumerate(headings):
            sheet.write(0, colx, value, heading_xf)
        #headings_width = (x*256 for x in (20, 20, 40, 12, 10))
        #for i, width in enumerate(headings_width):
        #    sheet.col(i).width = width


        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.set_remove_splits(True)

        for j, row in enumerate(rows):
            for i, cell in enumerate(row):
                sheet.write(j+1, i, cell)

        file_path = '/tmp/tmp.xls'
        wbk.save(file_path)

        file_ = open(file_path, 'rb')

        return file_

    def post(self):
        rows = self.session.query('cid', 'cname', 'uid', 'uemail', 'date', 'time').from_statement("""
        SELECT c.id as cid, c.name as cname, u.id as uid, u.email as uemail, date_trunc('month', t.date) as date, SUM(t.time) as time
        FROM time_entry t, project p, client c, "user" u
        WHERE t.project_id = p.id AND
              p.client_id = c.id AND
              t.user_id = u.id AND
              t.deleted = false
        GROUP BY c.id, c.name, u.id, u.email, date_trunc('month', t.date)
        ORDER BY date_trunc('month', t.date)
        """).all()

        monthly = h.groupby(rows, lambda row: (row[2], row[-2]), lambda row: row[5])

        rows = [(
            row[1],
            row[3],
            row[5],
            row[4].strftime('%Y-%m-%d'),
            sum(monthly[row[2], row[-2]]),
        ) for row in rows]


        stream = self._to_excel(rows)

        response = Response(
            content_type='application/vnd.ms-excel',
            app_iter=stream,
        )
        response.headers['Cache-Control'] = 'no-cache'
        response.content_disposition = 'attachment; filename="report-%s.xls"' % datetime.datetime.now().strftime('%d-%m-%Y--%H-%M-%S')

        return response


@view_config(route_name='times_client_current_pivot', permission='clients')
class CurrentPivot(BaseView):
    def get(self):
        today = datetime.date.today()
        return HTTPFound(self.request.url_for('/times/client/pivot', year=today.year))


@view_config(route_name='times_client_pivot', permission='clients')
class Pivot(BaseView):
    @staticmethod
    def _quarters_sum(v):
        return sum(v[0:3]),sum(v[3:6]),sum(v[6:9]),sum(v[9:12]),

    def _get_month_days(self, start, end):
        """
        calculetes worked days (from begining of month to today, from today to end of month)
        """
        today = datetime.date.today()
        days_worked = h.get_working_days(start, h.previous_day(today))
        days_left = h.get_working_days(today, end)
        return days_worked, days_left

    def get(self):
        today = datetime.date.today()
        year = self.request.GET.get('year', today.year)
        year = int(year)
        year_start = datetime.date(year, 1, 1)
        year_end = datetime.date(year, 12, 31)
        if year == today.year:
            # if this is current year we calculate hours only to yesterday
            year_end = today-oneday

        pivot_q = self.session.query('id', 'name', 'color', 'date', 'time').from_statement("""
        SELECT c.id as id, c.name as name, c.color as color, date_trunc('month', t.date) as date, SUM(t.time) as time
        FROM time_entry t, project p, client c
        WHERE t.project_id = p.id AND
              p.client_id = c.id AND
              t.date >= :year_start AND
              t.date <= :year_end AND
              t.deleted = false
        GROUP BY c.id, c.name, c.color, date_trunc('month', t.date)
        """).params(year_start=year_start, year_end=year_end)

        pivot = {}
        for p in pivot_q:
            pivot.setdefault((p.id, p.name, p.color), [0]*12)[p.date.month-1] = int(round(p.time))

        stats_q = self.session.query('date', 'time').from_statement("""
        SELECT date_trunc('month', t.date) as date, SUM(t.time) as time
        FROM time_entry t
        WHERE t.deleted = false
        GROUP BY date_trunc('month', t.date)
        """)

        stats = {}
        for s in stats_q:
            stats.setdefault(s.date.year, [0]*12)[s.date.month-1] = int(round(s.time))

        # estymation of expected worked hours for current month:
        month_approx = None
        if year == today.year and today.day > 1:
            month_start = datetime.date(today.year, today.month, 1)
            day_of_week, days_in_month = calendar.monthrange(today.year, today.month)
            month_end = datetime.date(today.year, today.month, days_in_month)
            days_worked, days_left = self._get_month_days(month_start, month_end)
            if not days_worked:
                days_worked = 1

            month_approx = (days_left + days_worked) / days_worked

        return dict(
            today=today,
            year_start=year_start,
            pivot=pivot,
            stats=stats,
            quarters_sum=self._quarters_sum,
            month_approx=month_approx,
        )
