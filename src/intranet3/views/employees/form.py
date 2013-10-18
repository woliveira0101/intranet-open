# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.response import Response

from intranet3 import helpers as h
from intranet3.utils.views import BaseView
from intranet3.forms.employees import (
    LateJustificationForm,
    WrongTimeJustificationForm,
    AbsenceCreateForm
)
from intranet3.lib.employee import user_leave
from intranet3.models import Late, WrongTime, Absence
from intranet3.log import INFO_LOG

LOG = INFO_LOG(__name__)

#if popup was opened on page with justification button we change button to text
CHANGE_STATUS = '<script>$(".justification-info").html(\'<span class="justification-info label">%s</span>\');</script>'
RELOAD_PAGE = '<script>window.location.reload()</script>'

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


@view_config(route_name='employee_form_create_absence', permission='hr')
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


