# -*- coding: utf-8 -*-
import datetime

from pyramid.view import view_config
from pyramid.response import Response

from intranet3 import config
from intranet3 import helpers as h
from intranet3.utils.views import BaseView
from intranet3.utils import google_calendar as cal
from intranet3.utils.mail import EmailSender
from intranet3.forms.employees import (LateJustificationForm,
                                       LateApplicationForm,
                                       WrongTimeJustificationForm,
                                       AbsentApplicationForm,
                                       AbsenceCreateForm,
                                       ABSENCE_TYPES)
from intranet3.lib.employee import user_leave
from intranet3.models import Late, WrongTime, Absence, Holiday, TimeEntry
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

LEAVE_PROJECT_ID = 86
L4_PROJECT_ID = 87

#if popup was opened on page with justification button we change button to text
CHANGE_STATUS = '<script>$(".justification-info").html(\'<span class="justification-info label">%s</span>\');</script>'
RELOAD_PAGE = '<script>window.location.reload()</script>'

hour9 = datetime.time(hour=9)

@view_config(route_name='employee_form_late_justification')
class LateJustification(BaseView):
    def get(self):
        form = LateJustificationForm(self.request.GET, user=self.request.user)
        return dict(form=form)

    def post(self):
        form = LateJustificationForm(self.request.POST, user=self.request.user)

        if form.validate():
            late = Late(
                user_id=self.request.user.id,
                date=form.popup_date.data,
                explanation=form.popup_explanation.data,
            )
            self.session.add(late)
            LOG(u"Late added")
            return Response(self._(u'Explanation added') + CHANGE_STATUS % self._('Waits for verification'))

        return dict(form=form)

@view_config(route_name='employee_form_late_application')
class LateApplication(BaseView):
    def get(self):
        form = LateApplicationForm(user=self.request.user)
        return dict(form=form)

    def post(self):
        form = LateApplicationForm(self.request.POST, user=self.request.user)
        if form.validate():
            date = form.popup_date.data
            explanation = form.popup_explanation.data
            late = Late(
                user_id=self.request.user.id,
                date=date,
                explanation=explanation,
                justified=True,
            )
            self.session.add(late)
            topic = self._(u'${email} - Late ${date}',
                email=self.request.user.email,
                date=date.strftime('%d.%m.%Y')
            )
            deferred = EmailSender.send(
                config['COMPANY_MAILING_LIST'],
                topic,
                form.popup_explanation.data,
                sender_name=self.request.user.name,
                replay_to=self.request.user.email,
            )
            datehour9 = datetime.datetime.combine(date, hour9)

            calendar = cal.Calendar(self.request.user)
            event = cal.Event(
                datehour9,
                datehour9+cal.onehour,
                self._(u'Late'),
                explanation,
            )
            event_id = calendar.addEvent(event)

            if deferred:
                LOG(u"Late added")
                if event_id:
                    return Response(self._(u'Request added. Calendar entry added'))
                else:
                    return Response(self._(u'Request added. Calendar entry has <b class="red">NOT</b> beed added'))

            else:
                return Response(self._(u'There was problem with sending email - request has not been added, please conntact administrator'))

        return dict(form=form)

@view_config(route_name='employee_form_wrong_time_justification')
class WrongTimeJustification(BaseView):
    def get(self):
        form = WrongTimeJustificationForm(self.request.GET, user=self.request.user)
        return dict(form=form)

    def post(self):
        form = WrongTimeJustificationForm(self.request.POST, user=self.request.user)
        if form.validate():
            wrongtime = WrongTime(
                user_id=self.request.user.id,
                date=form.popup_date.data,
                explanation=form.popup_explanation.data,
            )
            self.session.add(wrongtime)
            LOG(u"WrongTime added")
            response = '%s %s' % (self._(u'Explanation added'), CHANGE_STATUS % self._('Waits for verification'))
            return Response(response)
        return dict(form=form)


@view_config(route_name='employee_form_absence_application')
class AbsenceApplication(BaseView):
    def ABSENCE_TOPIC(self):
        return self._(u'[intranet] Podanie o urlop')

    def ABSENCE_BODY(self, **kwargs):
        return self._(u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego za rok ${year} urlopu wypoczynkowego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}""", **kwargs)

    def L4_TOPIC(self):
        return self._(u'[intranet] Podanie o urlop chorobowy')

    def L4_BODY(self, **kwargs):
        return self._(u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego urlopu zdrowotnego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}""", **kwargs)

    def COMPASSIONATE_TOPIC(self):
        return self._(u'[intranet] Podanie o urlop okolicznościowy')

    def COMPASSIONATE_BODY(self, **kwargs):
        return self._(u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego urlopu okolicznościowego (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}""", **kwargs)

    def REQUEST_TOPIC(self):
        return self._(u'[intranet] Podanie o urlop na żądanie')

    def REQUEST_BODY(self, **kwargs):
        return self._(u"""Poznań, ${today}

Niniejszym składam wniosek o udzielenie w dniach ${date_start} do ${date_end} przysługującego za rok ${year} urlopu na żadaie (ogółem ${days} dni).

Termin proponowanego urlopu jest zgodny z wcześniejszym uzgodnieniem.

Uwagi:

${remarks}

${name}""", **kwargs)

    def _resolve_type(self, type):
        if type == 'planowany':
            return self.ABSENCE_TOPIC(), self.ABSENCE_BODY
        elif type == 'l4':
            return self.L4_TOPIC(), self.L4_BODY
        elif type == 'okolicznosciowy':
            return self.COMPASSIONATE_TOPIC(), self.COMPASSIONATE_BODY
        elif type == 'zadanie':
            return self.REQUEST_TOPIC(), self.REQUEST_BODY

    def _send_mail(self, type, date_start, date_end, days, remarks):
        today = datetime.date.today().strftime('%Y-%m-%d')
        year = datetime.date.today().year
        name = self.request.user.name
        topic, body = self._resolve_type(type)
        kwargs = locals()
        kwargs.pop('self')
        body = body(**kwargs)
        return EmailSender.send(
            config['ACCOUNTANT_EMAIL'],
            topic,
            body,
            cc=self.request.user.email,
            sender_name=self.request.user.name,
            replay_to=','.join([self.request.user.email]),
        )

    def dispatch(self):
        form = AbsentApplicationForm(self.request.POST, request=self.request)
        days, mandated, used, left = 0, 0, 0, 0
        if form.popup_date_start.data:
            mandated, used, left = user_leave(self.request, form.popup_date_start.data.year)
            if form.popup_date_end.data:
                days = h.get_working_days(form.popup_date_start.data, form.popup_date_end.data)
                left -= days
        if self.request.method == 'POST' and form.validate():
            response = u''
            date_start = form.popup_date_start.data
            date_end = form.popup_date_end.data
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

            if absence.type != 'inne':
                # let's add timeentries for this leave
                holidays = Holiday.all()
                date = date_start
                oneday = datetime.timedelta(days=1)
                description = self._(u'Auto Leave: ${type} - ${remarks}',
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

                ## let's send email
                deferred = self._send_mail(
                    absence.type,
                    date_start.strftime('%Y-%m-%d'),
                    date_end.strftime('%Y-%m-%d'),
                    days,
                    remarks,
                )
                response += self._(u'Request added<br>Hours added<br>')

            ## and add event to calendar:
            calendar = cal.Calendar(self.request.user)
            event = cal.Event(
                date_start,
                date_end+cal.oneday,
                u'NIEOB-[%s]' % self.request.user.name,
                remarks,
            )
            event_id = calendar.addEvent(event)

            if event_id:
                response += self._(u'Calendar entry has been added')
            else:
                response += u'Calendar entry has <b class="red">NOT</b> beed added'

            return Response(response)

        return dict(
            form=form,
            days=days,
            mandated=mandated,
            used=used,
            left=left
        )

@view_config(route_name='employee_form_create_absence', permission='admin')
class CreateAbsence(BaseView):
    def dispatch(self):
        form = AbsenceCreateForm(self.request.POST, request=self.request)
        days, mandated, used, left = 0, 0, 0, 0
        if form.popup_date_start.data:
            mandated, used, left = user_leave(self.request, form.popup_date_start.data.year)
            if form.popup_date_end.data:
                days = h.get_working_days(form.popup_date_start.data, form.popup_date_end.data)
                left -= days
        if self.request.method == 'POST' and form.validate():
            date_start = form.popup_date_start.data
            date_end = form.popup_date_end.data
            type = form.popup_type.data
            remarks = form.popup_remarks.data
            user_id = form.popup_user_id.data
            absence = Absence(
                user_id=user_id,
                date_start=date_start,
                date_end=date_end,
                days=days,
                type=type,
                remarks=remarks,
            )
            self.session.add(absence)
            return Response(self._('Done') + RELOAD_PAGE)

        return dict(
            form=form,
            days=days,
            mandated=mandated,
            used=used,
            left=left
        )


@view_config(route_name='employee_form_absence_days', renderer='json')
class AbsenceDays(BaseView):
    def get(self):
        date_start = self.request.GET.get('date_start')
        date_end = self.request.GET.get('date_end')
        type = self.request.GET.get('type')
        days = 0
        if date_start:
            date_start = datetime.datetime.strptime(date_start, '%d/%m/%Y').date()
            mandated, used, left = user_leave(self.request, date_start.year)
            if date_end:
                date_end = datetime.datetime.strptime(date_end, '%d/%m/%Y').date()
                days = h.get_working_days(date_start, date_end)
                if days is None:
                    days = 0
                if type in ('planowany', 'zadanie'):
                    left -= days

            return dict(
                status='ok',
                days=days,
                left=left,
                mandated=mandated,
            )
        return dict(
            status='nok',
        )


