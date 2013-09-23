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
        if not blacklist:
            return data
        return dict(
            lates=[
                late for late in data['lates']
                if (late and late.get('id') not in blacklist)
            ] if data['lates'] else [],
            absences=[
                absence for absence in data['absences']
                if (absence and absence.get('id') not in blacklist)
            ] if data['absences'] else [],
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

        late = self.session.query(
            User.id,
            User.name,
            Late.late_start,
            Late.late_end,
        )\
            .filter(User.id == Late.user_id)\
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
                    late_start=late_start.isoformat()[:5]
                    if late_start else None,
                    late_end=late_end.isoformat()[:5]
                    if late_end else None
                )
                for user_id, user_name, late_start, late_end in late
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