# -*- coding: utf-8 -*-
import datetime
import dateutil.parser as dparser

from pyramid.view import view_config

from intranet3 import memcache
from intranet3.utils.views import ApiView
from intranet3.utils import google_calendar as cal
from intranet3.models import Late
from intranet3.api.presence import MEMCACHED_NOTIFY_KEY


hour9 = datetime.time(hour=9)


@view_config(route_name='api_lateness', renderer='json')
class LatenessApi(ApiView):
    def _add_event(self, date, explanation):
        datehour9 = datetime.datetime.combine(date, hour9)
        calendar = cal.Calendar(self.request.user)
        event = cal.Event(
            datehour9,
            datehour9 + cal.onehour,
            self._(u'Late'),
            explanation,
        )
        event_id = calendar.addEvent(event)
        return event_id

    def post(self):
        lateness = self.request.json.get('lateness')
        date = dparser.parse(lateness["date"]).date()
        explanation = lateness["explanation"]
        in_future = date > datetime.date.today()
        late = Late(
            user_id=self.request.user.id,
            date=date,
            explanation=explanation,
            justified=in_future or None,
            late_start=dparser.parse(lateness["start"]),
            late_end=dparser.parse(lateness["end"]),
            work_from_home=lateness["work_from_home"],
        )

        self.session.add(late)
        memcache.delete(MEMCACHED_NOTIFY_KEY % date)

        debug = self.request.registry.settings['DEBUG'] == 'True'
        if in_future and not debug:
            event_id = self._add_event(date, explanation)

        return u'Entry added'
