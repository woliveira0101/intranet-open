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


@view_config(route_name='presence_list', permission='hr')
class List(BaseView):
    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        start_date = datetime.datetime.combine(date, day_start)
        end_date = datetime.datetime.combine(date, day_end)

        def get_entries(city):
            if city in ['wroclaw', 'poznan']:
                return self.session.query(User.id, User.name, func.min(PresenceEntry.ts), func.max(PresenceEntry.ts))\
                              .filter(User.id == PresenceEntry.user_id)\
                              .filter((User.location == city) | (User.location == None))\
                              .filter(PresenceEntry.ts >= start_date)\
                              .filter(PresenceEntry.ts <= end_date)\
                              .group_by(User.id, User.name)\
                              .order_by(User.name)

        def get_lates(city):
            if city in ['wroclaw', 'poznan']:
                return self.session.query(User.id, User.name, Late.late_start, Late.late_end)\
                            .filter(User.id == Late.user_id)\
                            .filter(User.location == city)\
                            .filter(Late.date == date)\
                            .order_by(User.name)

        def get_absence(city):
            if city in ['wroclaw', 'poznan']:
                return self.session.query(User.id, User.name)\
                            .filter(User.id == Absence.user_id)\
                            .filter(User.location == city)\
                            .filter(Absence.date_start <= date)\
                            .filter(Absence.date_end >= date)\
                            .order_by(User.name)

        return dict(
            date=date,
            prev_date=h.previous_day(date),
            next_date=h.next_day(date),
            excuses=excuses.presence(),
            justification=excuses.presence_status(date, self.request.user.id),
            city=[
                dict(
                    name=u'Poznań',
                    entries=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in get_entries('poznan')),
                    late=get_lates('poznan'),
                    absence=get_absence('poznan'),
                ),
                dict(
                    name=u'Wrocław',
                    entries=((user_id, user_name, start, stop, start.time() > hour_9) for (user_id, user_name, start, stop) in get_entries('wroclaw')),
                    late=get_lates('wroclaw'),
                    absence=get_absence('wroclaw'),
                 ),
            ],
        )



@view_config(route_name='presence_full', permission='hr')
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
