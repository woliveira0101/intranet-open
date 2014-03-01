# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from webob.multidict import MultiDict

from intranet3 import memcache
from intranet3.utils.views import ApiView
from intranet3.utils import google_calendar as cal
from intranet3.models import Late
from intranet3.api.presence import MEMCACHED_NOTIFY_KEY
from intranet3.forms.employees import LateApplicationForm

hour9 = datetime.time(hour=9)

@view_config(route_name='api_lateness', renderer='json', permission='can_edit_presence')
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
        form = LateApplicationForm(MultiDict(**lateness), user=self.request.user)
        if form.validate():
            date = form.popup_date.data
            explanation = form.popup_explanation.data
            in_future = date > datetime.date.today()
            late = Late(
                user_id=self.request.user.id,
                date=date,
                explanation=explanation,
                justified=in_future or None,
                late_start=form.late_start.data,
                late_end=form.late_end.data,
                work_from_home=form.work_from_home.data,
            )

            self.session.add(late)
            memcache.delete(MEMCACHED_NOTIFY_KEY % date)

            debug = self.request.registry.settings['DEBUG'] == 'True'
            if in_future and not debug:
                event_id = self._add_event(date, explanation)

            return dict(
                entry=True
            )

        self.request.response.status = 400
        return form.errors
