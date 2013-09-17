# coding: utf-8
import datetime
from babel.core import Locale
from pyramid.view import view_config

from intranet3.models import User, Late
from intranet3.utils import excuses
from intranet3.utils.views import ApiView


day_start = datetime.time(0, 0, 0)
day_end = datetime.time(23, 59, 59)
hour_9 = datetime.time(9, 0, 0)

locale = Locale('en', 'US')


@view_config(route_name='api_presence', renderer='json')
class PresenceApi(ApiView):
    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        date = datetime.date(2013, 9, 10) # USUNĄĆ PO TESTACH NA SZTYWNO USTAWIONĄ DATĘ
        start_date = datetime.datetime.combine(date, day_start)
        end_date = datetime.datetime.combine(date, day_end)

        late = self.session.query(User.id, User.name, Late.added_ts)\
                            .filter(User.id==Late.user_id)\
                            .filter(Late.added_ts>=start_date)\
                            .filter(Late.added_ts<=end_date)\
                            .group_by(User.id, User.name, Late.added_ts)\
                            .order_by(User.name)

        return dict(
            justification=excuses.presence_status(date, self.request.user.id),
            late=[
                dict(id=user_id, name=user_name)
                for user_id, user_name, late_from in late
            ],
            user_id=self.request.user.id,
        )

        #
        # late = self.session.query(User.id, User.name, Late.added_ts)\
        #                     .filter(User.id==Late.user_id)\
        #                     .filter(Late.added_ts>=start_date)\
        #                     .filter(Late.added_ts<=end_date)\
        #                     .group_by(User.id, User.name, Late.added_ts)\
        #                     .order_by(User.name)
        #
        # return dict(
        #     date=date,
        #     justification=excuses.presence_status(date, self.request.user.id),
        #     late=[(user_id, user_name, late_from) for (user_id, user_name, late_from) in late],
        # )
