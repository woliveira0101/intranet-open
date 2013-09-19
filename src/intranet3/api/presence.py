# coding: utf-8
import datetime
from babel.core import Locale
from pyramid.view import view_config

from intranet3.models import User, Late, Absence
from intranet3.utils.views import ApiView

locale = Locale('en', 'US')


@view_config(route_name='api_presence', renderer='json')
class PresenceApi(ApiView):
    def get(self):
        date = self.request.GET.get('date')
        if date:
            date = datetime.datetime.strptime(date, '%d.%m.%Y')
        else:
            date = datetime.date.today()
        late = self.session.query(User.id, User.name,  Late.late_start, Late.late_end)\
                            .filter(User.id==Late.user_id)\
                            .filter(Late.date == date)\
                            .order_by(User.name)
        absences = self.session.query(User.id, User.name)\
                            .filter(User.id == Absence.user_id)\
                            .filter(Absence.date_start <= date)\
                            .filter(Absence.date_end >= date)\
                            .order_by(User.name)
        return dict(
            lates=[
                dict(
                    id=user_id,
                    name=user_name,
                    late_start=late_start.isoformat()[:5] if late_start else None,
                    late_end=late_end.isoformat()[:5] if late_end else None
                )
                for user_id, user_name, late_start, late_end in late
            ],
            absences=[
                dict(
                    id=user_id,
                    name=user_name
                )
                for user_id, user_name in absences]
        )