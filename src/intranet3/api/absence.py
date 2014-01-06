# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from webob.multidict import MultiDict

from intranet3 import memcache
from intranet3 import config
from intranet3 import helpers as h
from intranet3.utils.views import ApiView
from intranet3.utils import google_calendar as cal
from intranet3.utils.task import deferred
from intranet3.utils import mail
from intranet3.models import Absence, Holiday, TimeEntry
from intranet3.api.presence import MEMCACHED_NOTIFY_KEY
from intranet3.forms.employees import AbsentApplicationForm, ABSENCE_TYPES
from intranet3.lib.employee import user_leave


LEAVE_PROJECT_ID = 86
L4_PROJECT_ID = 87


@view_config(route_name='api_absence', renderer='json')
class AbsenceApi(ApiView):
    ABSENCE_TOPIC = u'[intranet] Podanie o urlop'
    ABSENCE_BODY = u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego za rok ${year} urlopu wypoczynkowego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}"""
    L4_TOPIC = u'[intranet] Podanie o urlop chorobowy'
    L4_BODY = u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego urlopu zdrowotnego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}"""
    COMPASSIONATE_TOPIC = u'[intranet] Podanie o urlop okolicznościowy'
    COMPASSIONATE_BODY = u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego urlopu okolicznościowego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}"""
    REQUEST_TOPIC = u'[intranet] Podanie o urlop na żądanie'
    REQUEST_BODY = u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego za rok ${year} urlopu na żadaie (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}"""
    TYPES = {
        'planowany': (ABSENCE_TOPIC, ABSENCE_BODY),
        'l4': (L4_TOPIC, L4_BODY),
        'okolicznosciowy': (COMPASSIONATE_TOPIC, COMPASSIONATE_BODY),
        'zadanie': (REQUEST_TOPIC, REQUEST_BODY),
    }

    def _send_email(self, type, date_start, date_end, days, remarks):
        name = self.request.user.name
        email = self.request.user.email
        today = datetime.date.today()
        topic, body = self.TYPES[type]

        body = self._(
            body,
            today=today.strftime('%Y-%m-%d'),
            date_start=date_start,
            date_end=date_end,
            year=today.year,
            days=days,
            remarks=remarks,
            name=name,
        )
        return deferred.defer(
            mail.send,
            config['ACCOUNTANT_EMAIL'],
            topic,
            body,
            cc=email,
            sender_name=name,
            replay_to=','.join([self.request.user.email]),
        )

    def post(self):
        absence = self.request.json.get('absence')
        form = AbsentApplicationForm(MultiDict(**absence), request=self.request)
        if form.validate():
            response = {
                u'request': False,
                u'hours': False,
                u'calendar_entry': False,
            }

            memcache.clear()

            date_start = form.popup_date_start.data
            date_end = form.popup_date_end.data
            days = 0
            if date_start and date_end:
                days = h.get_working_days(date_start, date_end)
            type = form.popup_type.data
            remarks = form.popup_remarks.data
            absence = Absence(
                user_id=self.request.user.id,
                date_start=date_start,
                date_end=date_end,
                days=days,
                type=type,
                remarks=remarks,
            )

            self.session.add(absence)
            memcache.delete(MEMCACHED_NOTIFY_KEY % date_start)

            if absence.type != 'inne':
                holidays = Holiday.all()
                date = date_start
                oneday = datetime.timedelta(days=1)
                description = self._(
                    u'Auto Leave: ${type} - ${remarks}',
                    type=dict(ABSENCE_TYPES)[type],
                    remarks=remarks
                )
                project_id = L4_PROJECT_ID if type == u'l4' else LEAVE_PROJECT_ID

                while date <= date_end:
                    if not Holiday.is_holiday(date, holidays=holidays):
                        timeentry = TimeEntry(
                            user_id=self.request.user.id,
                            date=date,
                            time=8,
                            description=description,
                            project_id=project_id,
                        )
                        self.session.add(timeentry)
                    date += oneday

                self._send_email(
                    absence.type,
                    date_start.strftime('%Y-%m-%d'),
                    date_end.strftime('%Y-%m-%d'),
                    days,
                    remarks,
                )

                response[u'request'] = True
                response[u'hours'] = True

            calendar = cal.Calendar(self.request.user)
            event = cal.Event(
                date_start,
                date_end + cal.oneday,
                u'NIEOB-[%s]' % self.request.user.name,
                remarks
            )
            event_id = calendar.addEvent(event)

            response[u'calendar_entry'] = bool(event_id)

            return response

        self.request.response.status = 400
        return form.errors


@view_config(route_name='api_absence_days', renderer='json')
class AbsenceDaysApi(ApiView):
    def get(self):
        date_start = self.request.GET.get('date_start')
        date_end = self.request.GET.get('date_end')

        if date_start:
            date_start = datetime.datetime.strptime(date_start, '%d/%m/%Y').date()
            mandated, used, left = user_leave(self.request, date_start.year)
            days = 0

            if date_end:
                type = self.request.GET.get('type')
                date_end = datetime.datetime.strptime(date_end, '%d/%m/%Y').date()

                days = h.get_working_days(date_start, date_end)
                if days is None:
                    days = 0
                if type in ('planowany', 'zadanie'):
                    left -= days

            return dict(
                days=days,
                left=left,
                mandated=mandated
            )

        self.request.response.status = 400
        return dict(
            date_start='This field is required.'
        )
