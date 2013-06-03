# -*- coding: utf-8 -*-
import datetime

from sqlalchemy import func
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from intranet3.utils.views import BaseView
from intranet3.models import User, PresenceEntry
from intranet3.helpers import previous_day, next_day
from intranet3.utils import excuses

day_start = datetime.time(0, 0, 0)
day_end = datetime.time(23, 59, 59)
hour_9 = datetime.time(9, 0, 0)


@view_config(route_name='presence_today')
class Today(BaseView):
    def get(self):
        today = datetime.datetime.now().date()
        url = self.request.url_for('/presence/list', date=today.strftime('%d.%m.%Y'))
        return HTTPFound(location=url)


@view_config(route_name='presence_list')
class List(BaseView):
    def get(self):
        date = datetime.datetime.strptime(self.request.GET.get('date'), '%d.%m.%Y')
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
            prev_date=previous_day(date),
            next_date=next_day(date),
            excuses=excuses.presence(),
            justification=excuses.presence_status(date, self.request.user.id),
        )

@view_config(route_name='presence_full')
class Full(BaseView):
    def get(self):
        date = datetime.datetime.strptime(self.request.GET.get('date'), '%d.%m.%Y')

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
            prev_date=previous_day(date), next_date=next_day(date)
        )

@view_config(route_name='presence_absences')
class Absences(BaseView):
    def get(self):
        users_p = User.query.filter(User.is_not_client()) \
                          .filter(User.is_active==True) \
                          .filter(User.location=='poznan') \
                          .order_by(User.freelancer, User.name).all()
        users_w = User.query.filter(User.is_not_client()) \
                          .filter(User.is_active==True) \
                          .filter(User.location=='wroclaw') \
                          .order_by(User.freelancer, User.name).all()
        users_p.extend(users_w)
        days = [u'Ś', u'C', u'P', u'S', u'N', u'P', u'W'] * 20

        return dict(
            users=users_p,
            days=days,
            may_weekdays = days[0:31],
            june_weekdays = days[31:61],
            july_weekdays = days[61:92],
        )
