# -*- coding: utf-8 -*-
import datetime
from calendar import monthrange
from collections import defaultdict

from babel.core import Locale
from sqlalchemy import func
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from intranet3.utils.views import BaseView
from intranet3.models import User, PresenceEntry, Holiday, Absence, Late
from intranet3 import helpers as h
from intranet3.utils import excuses, idate

day_start = datetime.time(0, 0, 0)
day_end = datetime.time(23, 59, 59)
hour_9 = datetime.time(9, 0, 0)

locale = Locale('en', 'US')

@view_config(route_name='presence_list')
class List(BaseView):
    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        start_date = datetime.datetime.combine(date, day_start)
        end_date = datetime.datetime.combine(date, day_end)
        entries_p = self.session.query(User.id, User.name, func.min(PresenceEntry.ts), func.max(PresenceEntry.ts))\
                              .filter(User.id==PresenceEntry.user_id)\
                              .filter((User.location=="poznan") | (User.location==None))\
                              .filter(PresenceEntry.ts>=start_date)\
                              .filter(PresenceEntry.ts<=end_date)\
                              .group_by(User.id, User.name)\
                              .order_by(User.name)

        entries_w = self.session.query(User.id, User.name, func.min(PresenceEntry.ts), func.max(PresenceEntry.ts))\
                              .filter(User.id==PresenceEntry.user_id)\
                              .filter(User.location=="wroclaw")\
                              .filter(PresenceEntry.ts>=start_date)\
                              .filter(PresenceEntry.ts<=end_date)\
                              .group_by(User.id, User.name)\
                              .order_by(User.name)

        return dict(
            entries_p=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in entries_p),
            entries_w=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in entries_w),
            date=date,
            prev_date=h.previous_day(date),
            next_date=h.next_day(date),
            excuses=excuses.presence(),
            justification=excuses.presence_status(date, self.request.user.id),
        )

@view_config(route_name='presence_full')
class Full(BaseView):
    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()

        start_date = datetime.datetime.combine(date, day_start)
        end_date = datetime.datetime.combine(date, day_end)
        entries = self.session.query(User, PresenceEntry)\
                              .filter(PresenceEntry.user_id==User.id)\
                              .filter(PresenceEntry.ts>=start_date)\
                              .filter(PresenceEntry.ts<=end_date)\
                              .order_by(PresenceEntry.ts)
        return dict(
            entries=entries,
            date=date,
            prev_date=h.previous_day(date), next_date=h.next_day(date)
        )

@view_config(route_name='presence_absences')
class Absences(BaseView):
    WEEKDAYS = locale.days['stand-alone']['narrow']

    def weekday(self, date):
        weekday = date.weekday()
        return self.WEEKDAYS[weekday]

    def get_range(self):
        sunday = idate.first_day_of_week() - datetime.timedelta(days=1)
        curr_year = sunday.year
        monday = idate.first_day_of_week(sunday)
        dec31 = datetime.date(curr_year, 12, 31)
        return monday, dec31

    def necessary_data(self, start, end):
        curr_year = start.year
        days = (end - start).days
        date_range = idate.xdate_range(start, end, group_by_month=True)
        month_range = idate.months_between(start, end)
        month_names = locale.months['format']['wide'].items()
        months = [
            (month_names[m-1][1], monthrange(curr_year, m)[1])
            for m in month_range
        ]

        # we have to modify number of days for first month
        this_month = months.pop(0)
        this_month = this_month[0], this_month[1]-(start.day-1)
        months.insert(0, this_month)

        return days, date_range, months

    def get_absences(self, start, end):
        absences = self.session.query(
            Absence.user_id,
            Absence.date_start,
            Absence.date_end,
            Absence.type,
            Absence.remarks,
        )
        absences = absences.filter(Absence.date_start>=start)\
                           .filter(Absence.date_start<=end)

        absences = h.groupby(
            absences,
            lambda x: x[0],
            lambda x: x[1:],
        )

        absences_groupped = defaultdict(lambda: {})
        for user_id, absences in absences.iteritems():
            for start, end, type_, remarks in absences:
                dates = idate.date_range(start, end)
                for date in dates:
                    absences_groupped[user_id][date] = (type_, remarks)

        return absences_groupped

    def get_lates(self, start, end):
        lates = self.session.query(Late.user_id, Late.date, Late.explanation)
        lates = lates.filter(Late.date>=start) \
                     .filter(Late.date<=end)

        lates = h.groupby(
            lates,
            lambda x: x[0],
            lambda x: x[1:],
        )

        lates_groupped = defaultdict(lambda: {})
        for user_id, lates in lates.iteritems():
            for date, explanation in lates:
                lates_groupped[user_id][date] = explanation

        return lates_groupped

    def get(self):
        start, end = self.get_range()
        days, date_range, months = self.necessary_data(start, end)
        holidays = Holiday.all()
        today = datetime.date.today()


        users_p = User.query.filter(User.is_not_client()) \
                            .filter(User.is_active==True) \
                            .filter(User.location=='poznan') \
                            .order_by(User.freelancer, User.name).all()
        users_w = User.query.filter(User.is_not_client()) \
                            .filter(User.is_active==True) \
                            .filter(User.location=='wroclaw') \
                            .order_by(User.freelancer, User.name).all()
        users_p.extend(users_w)
        absences = self.get_absences(start, end)
        lates = self.get_lates(start, end)


        return dict(
            users=users_p,
            days=days,
            date_range=date_range,
            months=months,
            absences=absences,
            lates=lates,
            is_holiday=lambda date: Holiday.is_holiday(date, holidays=holidays),
            is_today=lambda date: date == today,
            v=self,
        )
