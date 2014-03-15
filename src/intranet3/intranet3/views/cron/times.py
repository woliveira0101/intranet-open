# -*- coding: utf-8 -*-
from operator import itemgetter
import os
import datetime
import xlwt
import copy
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from functools import partial

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

from intranet3 import config
from intranet3 import helpers as h
from intranet3.utils import idate
from intranet3.utils import gdocs
from intranet3.utils.views import CronView
from intranet3.views.report.wrongtime import AnnuallyReportMixin
from intranet3.models import TimeEntry, Tracker, Project, Client, User, ApplicationConfig, Holiday, DBSession
from intranet3.utils import mail
from intranet3.log import WARN_LOG, ERROR_LOG, DEBUG_LOG, INFO_LOG, EXCEPTION_LOG

LOG = INFO_LOG(__name__)
WARN = WARN_LOG(__name__)
ERROR = ERROR_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)


oneday = datetime.timedelta(days=1)

@view_config(route_name='cron_times_report', permission='cron')
class ExcelReport(CronView):

    def _previous_month(self):
        today = datetime.date.today()
        first = datetime.date(today.year, today.month, 1)
        end_date = first - datetime.timedelta(days=1)
        start_date = datetime.date(end_date.year, end_date.month, 1)
        return start_date, end_date

    def _format_row(self, a_row):
        row = list(a_row)
        row[0] = (row[0],)                                         #client
        row[1] = (row[1],)                                         #project
        row[2] = (row[2],)                                         #ticketid
        row[3] = (row[3],)                                         #email
        row[4] = (unicode(row[4]),)                                #desc
        date_xf = xlwt.easyxf(num_format_str='DD/MM/YYYY')
        row[5] = (row[5], date_xf)                                 #date
        row[6] = (round(row[6], 2),)                               #time
        return row

    def action(self):
        today = datetime.date.today()
        query = DBSession.query
        uber_query = query(
            Client.name, Project.name, TimeEntry.ticket_id,
            User.email, TimeEntry.description, TimeEntry.date, TimeEntry.time
        )
        uber_query = uber_query.filter(TimeEntry.user_id==User.id)\
                               .filter(TimeEntry.project_id==Project.id)\
                               .filter(Project.tracker_id==Tracker.id)\
                               .filter(Project.client_id==Client.id)
        start, end = self._previous_month()
        uber_query = uber_query.filter(TimeEntry.date>=start)\
                               .filter(TimeEntry.date<=end)\
                               .filter(TimeEntry.deleted==False)
        uber_query = uber_query.order_by(Client.name, Project.name, TimeEntry.ticket_id, User.name)
        data = uber_query.all()

        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet('%s.xls' % start.strftime('%m-%Y'))

        heading_xf = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
        headings = ('Klient','Projekt', 'Ticket id', 'Pracownik', 'Opis', 'Data', 'Czas')
        headings_width = (x*256 for x in (20, 30, 10, 40, 100, 12, 10))
        for colx, value in enumerate(headings):
            sheet.write(0, colx, value, heading_xf)
        for i, width in enumerate(headings_width):
            sheet.col(i).width = width

        sheet.set_panes_frozen(True)
        sheet.set_horz_split_pos(1)
        sheet.set_remove_splits(True)

        for j, row in enumerate(data):
            row = self._format_row(row)
            for i, cell in enumerate(row):
                sheet.write(j+1,i,*cell)

        file_path = '/tmp/%s.xls' % start.strftime('%m-%Y')
        wbk.save(file_path)
        topic = '[intranet] Excel with projects hours'
        message = 'Excel with projects hours'
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                topic,
                message,
                file_path=file_path,
            )
        return Response('ok')


@view_config(route_name='cron_wrongtime_report', permission='cron')
class WrongTimeReport(AnnuallyReportMixin, CronView):

    def action(self):
        today = datetime.date.today()
        data = self._annually_report(today.year)
        data['config'] = self.settings
        response = render(
            'intranet3:templates/_email_reports/time_annually_report.html',
            data,
            request=self.request,
        )
        response = response.replace('\n', '').replace('\t', '')
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                self._(u'[Intranet2] Wrong time record report'),
                html_message=response,
            )
        return Response('ok')


@view_config(route_name='cron_times_todayhours', permission='cron')
class TodayHours(CronView):
    """ Daily report with hours """

    def action(self):
        date = datetime.date.today() - relativedelta(days=1)
        config_obj = ApplicationConfig.get_current_config()
        self._today_hours(
            date,
            config_obj.reports_project_ids,
            config_obj.reports_omit_user_ids
        )
        return Response('ok')

    def _today_hours(self, date, projects, omit_users):
        time_entries = DBSession.query('uid', 'user', 'description', 'time',
            'project', 'client', 'ticket_id', 'tracker_id',
            'total_time').from_statement("""
                SELECT
                    u.id as "uid", u.name as "user", t.description as "description",
                    t.time as "time", p.name as "project", c.name as "client",
                    t.ticket_id as "ticket_id", p.tracker_id as "tracker_id",
                    (
                        SELECT SUM(te.time)
                        FROM time_entry te
                        WHERE te.ticket_id=t.ticket_id
                    ) as "total_time"
                FROM
                    time_entry as t, project as p, client as c, "user" as u
                WHERE
                    t.deleted = False AND
                    t.date = :date AND
                    u.id = t.user_id AND
                    p.id = t.project_id AND
                    c.id = p.client_id AND
                    p.id IN :projects AND
                    u.id NOT IN :users
                ORDER BY u.name, c.name, p.name
            """).params(date=date, projects=tuple(projects),
                        users=tuple(omit_users)).all()
        if not time_entries:
            s = u"No time entries for report with hours added on %s" % date
            LOG(s)
            return s

        output = []
        total_sum = 0
        user_sum = defaultdict(lambda: 0.0)
        user_entries = defaultdict(lambda: [])
        trackers = {}
        for (uid, user, description, time, project, client, ticket_id, tracker_id,
             total_time) in time_entries:
            # Lazy dict filling
            if not tracker_id in trackers:
                trackers[tracker_id] = Tracker.query.get(tracker_id)
            tracker = trackers[tracker_id]
            ticket_url = tracker.get_bug_url(ticket_id)

            total_sum += time
            user_sum[uid] += time
            user_entries[(uid, user)].append((description, time, project, client,
                                       ticket_id, ticket_url, total_time)
            )
        output.append(self._(u"Daily hours report (${total_sum} h)",
                             total_sum='%.2f' % total_sum)
        )

        user_entries = sorted(
            user_entries.iteritems(),
            key=lambda u: user_sum[u[0][0]],
            reverse=True,
        )
        base_url = self.request.registry.settings['FRONTEND_PREFIX']
        for (user_id, user_name), entries in user_entries:
            entries = sorted(
                entries,
                key=itemgetter(1),
                reverse=True,
            )
            output.append(u"")
            time_link = base_url + self.request.url_for(
                '/times/list_user',
                user_id=user_id,
                date=date.strftime("%d.%m.%Y"),
            )
            output.append(u"\t<a href=\"%s\">%s</a> (%.2f h):" % (time_link, user_name, user_sum[user_id]))

            for (description, time, project, client, ticket_id, bug_url,
                 total_time) in entries:
                if ticket_id:
                    ticket_id = "[<a href=\"%s\">%s</a>] " % (bug_url,
                                                              ticket_id)
                else:
                    ticket_id = ""
                total_time = " (%.2fh)" % total_time if ticket_id else ""
                output.append(u"\t\t- %s / %s / %s%s - %.2fh%s" %
                              (client, project, ticket_id, description, time,
                               total_time)
                )

        message = u'<br />\n'.join(output).replace('\t', '&emsp;&emsp;')

        topic = self._(u"[intranet] Daily hours report")
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                topic,
                html_message=message,
            )
        LOG(u"Report with hours on %s - started" % (date,))
        return message


@view_config(route_name='cron_times_dailyhourswithoutticket', permission='cron')
class DailyHoursWithoutTicket(CronView):
    """ Daily report with hours without tickets"""
    def action(self):
        date = datetime.date.today() - relativedelta(days=1)
        config_obj = ApplicationConfig.get_current_config()
        self._today_hours_without_ticket(
            date,
            config_obj.reports_without_ticket_project_ids,
            config_obj.reports_without_ticket_omit_user_ids,
        )
        return Response('ok')


    def _today_hours_without_ticket(self, date, projects, omit_users):
        if not omit_users:
            # because u.id NOT IN (,) returns error
            omit_users = (987654321,)
        time_entries = DBSession.query('user', 'description', 'time', 'project', 'client').from_statement("""
        SELECT
            u.name as "user", t.description as "description",
            t.time as "time", p.name as "project", c.name as "client"
        FROM
            time_entry as t, project as p, client as c, "user" as u
        WHERE
            t.deleted = False AND
            t.date = :date AND
            t.ticket_id IS NULL AND
            u.id = t.user_id AND
            p.id = t.project_id AND
            c.id = p.client_id AND
            p.id IN :projects AND
            u.id NOT IN :users
        ORDER BY u.name, c.name, p.name
        """).params(date=date, projects=tuple(projects), users=tuple(omit_users)).all()

        if not time_entries:
            LOG(u"No time entries for report with hours without ticket added on %s" % (date,))
            return u"No time entries for report with hours without ticket added on %s" % (date,)

        output = []
        total_sum = 0
        user_sum = defaultdict(lambda: 0.0)
        user_entries = defaultdict(lambda: [])

        for user, description, time, project, client in time_entries:
            total_sum += time
            user_sum[user] += time
            user_entries[user].append((description, time, project, client))

        output.append(self._(u"Daily hours report without bugs (${total_sum} h)", total_sum=u'%.2f' % total_sum))

        for user, entries in user_entries.iteritems():
            output.append(u"")
            output.append(u"\t%s (%.2f h):" % (user, user_sum[user]))

            for description, time, project, client in entries:
                output.append(u"\t\t- %s / %s / %s %.2f h" % (client, project, description, time))

        message = u'\n'.join(output)

        topic = self._(u"[intranet] Daily hours report without bugs")
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                topic,
                message,
            )
        LOG(u"Report with hours without ticket on %s - started" % (date,))
        return message


@view_config(route_name='cron_times_hoursforpreviousmonths', permission='cron')
class HoursForPreviousMonths(CronView):
    """ Daily report with hours added for previous month """
    def action(self):
        date = datetime.date.today() - relativedelta(days=1)
        self._hours_for_previous_months(date)
        return Response('ok')

    def _hours_for_previous_months(self, date):
        current_month_start = datetime.date(date.year, date.month, 1)
        time_entries = DBSession.query(
            'user', 'client', 'project', 'time',
            'description', 'ticket_id', 'entry_date', 'entry_status').from_statement("""
        SELECT
            u.name as "user", c.name as "client", p.name as "project",
            t.time as "time", t.description as "description",
            t.ticket_id as "ticket_id", t.date as "entry_date",
            t.deleted as "entry_status"
        FROM
            time_entry as t,
            "user" as u,
            client as c,
            project as p
        WHERE
            t.user_id = u.id AND
            t.project_id = p.id AND
            p.client_id = c.id AND
            DATE(t.modified_ts) = :date AND
            t.date < :current_month_start
        ORDER BY
            u.name, c.name, p.name
        """).params(current_month_start=current_month_start, date=date).all()

        if not time_entries:
            LOG(u"No time entries for previous months %s" % (date,))
            return u"No time entries for previous months %s" % (date,)

        output = []
        tmp_user = ''
        for user, client, project, time, description, ticket_id, entry_date, entry_status in time_entries:
            if tmp_user != user:
                tmp_user = user
                output.append(u"")
                output.append(u"%s:" % (user,))

            ticket_id = ticket_id and u"[%s] " % ticket_id or u""
            status = entry_status and self._(u"[Deleted]") or u""
            output.append(u"\t- [%s]%s %s / %s / %s%s %.2f h" % (entry_date, status, client, project, ticket_id, description, time))

        message = u'\n'.join(output)

        topic = self._(u"[intranet] Report with hours added for the previous months")
        with mail.EmailSender() as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                topic,
                message,
            )
        LOG(u"Report with hours added for previous months - started")
        return message


@view_config(route_name='cron_times_syncclienthours', permission='cron')
class ClientHours(CronView):

    def action(self):
        self._synchronize_client_hours()
        return Response('ok')

    def _synchronize_client_hours(self):
        LOG(u"Client Hours synchronization starts")
        entries = DBSession.query('month', 'email', 'client', 'time').from_statement("""
            SELECT
                date_trunc('month', t.date) as "month",
                u.email as "email",
                c.name as client,
                COALESCE(SUM(t.time), 0) as "time"
            FROM
                time_entry t,
                project p,
                "user" u,
                client c
            WHERE
                t.deleted = FALSE AND
                t.project_id = p.id AND
                p.client_id = c.id AND
                t.user_id = u.id
            GROUP BY
                u.email,
                c.name,
                date_trunc('month', t.date)
            ORDER BY
                "month",
                "email",
                "client"
        """)
        rows = [
        (month.strftime('%Y-%m-%d'), client, email, (u'%.2f' % time).replace('.', ','))
        for month, email, client, time in entries
        ]
        config_obj = ApplicationConfig.get_current_config()
        h.trier(
            partial(
                gdocs.insert_or_replace_worksheet,
                config_obj.google_user_email,
                config_obj.google_user_password,
                config_obj.hours_employee_project,
                'DB-CLIENT',
                [u'Miesiac', u'Klient', u'Osoba', u'Liczba przepracowanych godzin', u'Miesiac (import)'],
                rows
            ),
            doc=u"Client hours synchronization"
        )
        return u"Synchronized"


@view_config(route_name='cron_times_missed_hours', permission='cron')
class MissedHours(CronView):

    def action(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        self.start, self.end = self._period(date)
        self.months = idate.months_between(self.start, self.end)
        self._send_email()
        return Response('ok')

    @classmethod
    def _period(cls, date):
        first_day_of_month = datetime.date(date.year, date.month, 1)
        # last day of previous month
        end = first_day_of_month - oneday

        if date.month in (1, 4, 7, 10):
            # two last quarters
            start = first_day_of_month - relativedelta(months=6)
        else:
            # current quarter and previous quarter
            start = idate.first_day_of_quarter(
                idate.first_day_of_quarter(date) - oneday
            )

        return start, end

    def _send_email(self):
        data = self._get_data()
        data['not_full_time_users'] = self._get_not_full_time_employees()
        data['quarters'] = 'Q%s' % idate.quarter_number(self.start), 'Q%s' % idate.quarter_number(self.end)
        data['months'] = self.months
        response = render(
            'intranet3:templates/_email_reports/missed_hours.html',
            data,
            request=self.request
        )
        response = response.replace('\n', '').replace('\t', '')
        with mail.EmailSender as email_sender:
            email_sender.send(
                config['MANAGER_EMAIL'],
                self._(u'[Intranet2] Missed hours'),
                html_message=response,
            )
        return data

    def _get_first_day_of_work(self):
        entries = DBSession.query('email', 'date').from_statement("""
            SELECT
                u.email as "email",
                MIN(t.date) as "date"
            FROM
                time_entry t,
                "user" u
            WHERE
                t.deleted = FALSE AND
                NOT ( u.groups @> '{"freelancer"}' ) AND
                t.user_id = u.id AND
                u.is_active = true AND
                (u.start_full_time_work IS NOT NULL AND t.date >= u.start_full_time_work AND t.date >= :date_start)
            GROUP BY
                u.email
        """).params(date_start=self.start)
        return dict(entries.all())

    def _get_expected(self, first_day_of_work):
        def first_day_of_next_month(date):
            next_month = h.next_month(date)
            return datetime.date(next_month.year, next_month.month, 1)

        months = []
        day = first_day_of_work
        while day < self.end:
            month_expected = h.get_working_days(day, idate.last_day_of_month(day))
            months.append(month_expected * 8)
            day = first_day_of_next_month(day)

        empty_months = len(self.months) - len(months)
        months = [0] * empty_months + months

        quarters = sum(months[0:3]), sum(months[3:])

        return quarters, months

    def _get_not_full_time_employees(self):
        users = User.query\
                    .filter(User.is_active==True)\
                    .filter(User.is_not_client())\
                    .filter(User.start_full_time_work==None)\
                    .order_by(User.name)
        users = users.all()
        return users

    def _get_data(self):
        entries = DBSession.query('user_id', 'email', 'month', 'time').from_statement("""
            SELECT
                u.email as "email",
                u.id as "user_id",
                date_trunc('month', t.date) as "month",
                COALESCE(SUM(t.time), 0) as "time"
            FROM
                time_entry t,
                "user" u
            WHERE
                t.user_id = u.id AND
                t.deleted = FALSE AND
                NOT ( u.groups @> '{"freelancer"}' ) AND
                u.is_active = true AND
                (u.start_full_time_work IS NOT NULL AND t.date >= u.start_full_time_work AND t.date >= :date_start) AND
                t.date <= :date_end
            GROUP BY
                u.id,
                u.email,
                date_trunc('month', t.date)
            ORDER BY
                "month",
                "email"
        """).params(date_start=self.start, date_end=self.end)
        # entries:
        # (user_id, user_email) -> [(month, hours_worked), (month, hours_worked), (month, hours), ...]
        entries = h.groupby(
            entries,
            lambda row: (row[0], row[1]),
            lambda row: (row[2], row[3]),
        )

        first_day_of_work = self._get_first_day_of_work()

        undertime_users = {}
        expected_users = {}
        users = []
        for (user_id, user), hours in entries.iteritems():
            months = [ time for month, time in hours ]
            empty_months = len(self.months) - len(months)
            months = [0] * empty_months + months
            quarters = sum(months[0:3]), sum(months[3:])

            expected_q, expected_m = self._get_expected(first_day_of_work[user])
            if expected_q[0] > quarters[0] or expected_q[1] > quarters[1]:
                if user not in (config['MANAGER_EMAIL'],):
                    users.append((user_id, user))
                    undertime_users[user] = quarters, months
                    expected_users[user] = expected_q, expected_m

        users = sorted(users, key=lambda u: u[1])

        return dict(
            users=users,
            data=undertime_users,
            expected=expected_users,
        )



