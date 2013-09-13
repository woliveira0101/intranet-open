# -*- coding: utf-8 -*-
import datetime

from babel.core import Locale
from sqlalchemy import func
from pyramid.view import view_config

from intranet3.utils.views import BaseView
from intranet3.models import User, PresenceEntry, Late, Absence
from intranet3 import helpers as h
from intranet3.utils import excuses


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
        # start_date = datetime.datetime.combine(date, day_start)
        start_date = datetime.datetime(2013, 8, 19, 0, 0, 0, 476596)
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
        late_p = self.session.query(User.id, User.name, Late.added_ts, Late.added_ts)\
                        .filter(User.id==Late.user_id)\
                        .filter(User.location=="poznan")\
                        .filter(Late.added_ts>=start_date)\
                        .filter(Late.added_ts<=end_date)\
                        .order_by(User.name)

        late_w = self.session.query(User.id, User.name, Late.date, Late.added_ts)\
                        .filter(User.id==Late.user_id)\
                        .filter(User.location=="wroclaw")\
                        .filter(Late.added_ts>=start_date)\
                        .filter(Late.added_ts<=end_date)\
                        .order_by(User.name)

        absence_p = self.session.query(User.id, User.name)\
                        .filter(User.id==Absence.user_id)\
                        .filter(User.location=="poznan")\
                        .filter(Absence.date_start<=start_date)\
                        .filter(Absence.date_end>=start_date)\
                        .order_by(User.name)
        absence_w = self.session.query(User.id, User.name)\
                        .filter(User.id==Absence.user_id)\
                        .filter(User.location=="wroclaw")\
                        .filter(Absence.date_start<=start_date)\
                        .filter(Absence.date_end>=start_date)\
                        .order_by(User.name)

        return dict(
            entries_p=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in entries_p),
            entries_w=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in entries_w),
            date=date,
            prev_date=h.previous_day(date),
            next_date=h.next_day(date),
            excuses=excuses.presence(),
            justification=excuses.presence_status(date, self.request.user.id),
            late_p=late_p,
            late_w=late_w,
            absence_p=absence_p,
            absence_w=absence_w
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
