# coding: utf-8
import datetime
from pyramid.view import view_config

from intranet3.models import User, Late, Absence
from intranet3.utils.views import ApiView
from intranet3 import memcache

MEMCACHED_NOTIFY_KEY = 'notify-%s'


@view_config(route_name='api_presence', renderer='json')
class PresenceApi(ApiView):

    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        current_data_late = memcache.get(
            MEMCACHED_NOTIFY_KEY % date
        )
        blacklist = self.request.user.notify_blacklist
        if current_data_late is not None:
            current_data_late['blacklist'] = blacklist
            return current_data_late

        late_query = self.session.query(
            User.id,
            User.name,
            Late.id,
            Late.late_start,
            Late.late_end,
            Late.explanation,
        )
        late_query = late_query.filter(User.id == Late.user_id)\
                               .filter(Late.date == date)\
                               .filter(Late.deleted == False)\
                               .order_by(User.name)

        absences = self.session.query(
            User.id,
            User.name,
            Absence.id,
            Absence.date_start,
            Absence.date_end,
            Absence.remarks
        )
        absences = absences.filter(User.id == Absence.user_id)\
                            .filter(Absence.deleted == False)\
                           .filter(Absence.date_start <= date)\
                           .filter(Absence.date_end >= date)\
                           .order_by(User.name)

        current_data_late = dict(
            lates=[
                dict(
                    id=user_id,
                    name=user_name,
                    late_id=late_id,
                    start=start and start.isoformat()[:5] or None,
                    end=end and end.isoformat()[:5] or None,
                    explanation=explanation,
                )for user_id, user_name, late_id, start, end, explanation in late_query
            ],
            absences=[
                dict(
                    id=user_id,
                    name=user_name,
                    absence_id=absence_id,
                    start=date_start and date_start.strftime('%d/%m') or None,
                    end=date_end and date_end.strftime('%d/%m') or None,
                    remarks=remarks
                )
                for user_id, user_name, absence_id, date_start, date_end, remarks in absences
            ]
        )
        memcache.add(
            MEMCACHED_NOTIFY_KEY % date,
            current_data_late,
            60 * 60 * 24,
        )
        current_data_late['blacklist'] = blacklist
        return current_data_late
