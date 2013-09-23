# coding: utf-8
import datetime
from babel.core import Locale
from pyramid.view import view_config

from intranet3.models import User, Late, Absence
from intranet3.utils.views import ApiView
from intranet3 import memcache

locale = Locale('en', 'US')

MEMCACHED_NOTIFY_KEY = 'notify-%s'

@view_config(route_name='api_presence', renderer='json')
class PresenceApi(ApiView):

    def _remove_blacklisted(self, data):
        blacklist = self.request.user.notify_blacklist
        return dict(
            lates=[
                late for late in data['lates']
                if late['id'] not in blacklist
            ],
            absences=[
                absence for absence in data['absences']
                if absence['id'] not in blacklist
            ],
        )

    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        current_data_late = memcache.get(
            MEMCACHED_NOTIFY_KEY % date.strftime('%d.%m.%Y')
        )

        if current_data_late is not None:
            result_dict = self._remove_blacklisted(current_data_late)
            return result_dict

        late_query = self.session.query(
            User.id,
            User.name,
            Late.late_start,
            Late.late_end,
        )
        late_query = late_query.filter(User.id == Late.user_id)\
                               .filter(Late.date == date)\
                               .order_by(User.name)

        absences = self.session.query(User.id, User.name)\
                               .filter(User.id == Absence.user_id)\
                               .filter(Absence.date_start <= date)\
                               .filter(Absence.date_end >= date)\
                               .order_by(User.name)

        current_data_late = dict(
            lates=[
                dict(
                    id=user_id,
                    name=user_name,
                    start=start and start.isoformat()[:5] or None,
                    end=end and end.isoformat()[:5] or None,
                )for user_id, user_name, start, end in late_query
            ],
            absences=[
                dict(
                    id=user_id,
                    name=user_name
                )
                for user_id, user_name in absences
            ],
        )

        memcache.add(
            MEMCACHED_NOTIFY_KEY % date.strftime('%d.%m.%Y'),
            current_data_late,
            60*60*24,
        )
        result_dict = self._remove_blacklisted(current_data_late)
        return result_dict