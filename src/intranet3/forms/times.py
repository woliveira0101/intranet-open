#-*- coding: utf-8 -*-
import datetime
import calendar
import re

import wtforms as wtf
from wtforms import validators
from wtforms.widgets import HTMLString, html_params
from pyramid.i18n import TranslationStringFactory

import utils
from intranet3.models import DBSession, Client, User
from intranet3.forms.project import ProjectChoices
from intranet3 import helpers as h
from intranet3.forms.utils import DataValidator

today = datetime.date.today
_ = TranslationStringFactory('intranet3')

class TicketIdValidator(object):
    """
    NonRequired, Integer or ^[mM]\d+$ for meetings (setted by javascript)
    """

    def validate(self, data):
        if not data:
            return
        if data.isdigit() and int(data) > 0:
            return
        if re.search('^[M]\d$', data):
            return
        raise validators.ValidationError(_(u'Ticket id must be integer number'))

    def __call__(self, form, field):
        self.validate(field.data)


class TicketIdListValidator(TicketIdValidator):
    """
        Validator class for tickets ids
    """

    def __call__(self, form, field):
        data = field.data
        if isinstance(data, list):
            for id in data:
                self.validate(id)


class NonRequiredStringListField(wtf.StringField):

    _raw_data = ''
    
    def process_formdata(self, valuelist):
        if valuelist:
            self._raw_data = valuelist[0]
            ids = [id.strip() for id in valuelist[0].split(',') if id.strip()]
            self.data = ids or ''

    def _value(self):
        return self._raw_data or self.data


class NonRequiredIntegerField(wtf.IntegerField):
    
    def process_formdata(self, valuelist):
        if valuelist and not valuelist[0]:
            self.data = None
        else:
            super(NonRequiredIntegerField, self).process_formdata(valuelist)


def time_filter(data):
    if data:
        if not isinstance(data, float) and data.count(':'):
            try:
                h, min = [int(i) for i in data.split(':')]
            except ValueError:
                raise validators.ValidationError(_(u"Time must be a number in format hh:mm"))
            else:
                if h < 0 or min < 0:
                    raise validators.ValidationError(_(u"Hours and minutes must be a positive number"))
                
                if h >= 24:
                    raise validators.ValidationError(_(u"Hours can not be greater or equal than 24"))
                
                if min >= 60:
                    raise validators.ValidationError(_(u"Minutes can not be greater or equal than 60"))
    
                data = h + (float(min) / 60.0)
    
        if not isinstance(data, float):
            data = data.replace(',', '.')
            try:
                data = float(data)
            except ValueError:
                raise validators.ValidationError(_(u"Time must be a float or hh:mm"))
    return data


class TimerValidation(validators.Required):
    
    def __call__(self, form, field):
        if not form.timer.data:
            super(TimerValidation, self).__call__(form, field)


class TimerNumberRangeValidation(validators.NumberRange):
    
    def __call__(self, form, field):
        if not form.timer.data or (form.timer.data and form.time.data != 0.0):
            super(TimerNumberRangeValidation, self).__call__(form, field)


class TimeInput(wtf.widgets.TextInput):
    
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs.setdefault('type', self.input_type)

        if 'value' not in kwargs:
            value = field._value()
            if value:
                try:
                    time = float(value)
                    kwargs['value'] = h.format_time(time)
                except ValueError:
                    kwargs['value'] = value

        return HTMLString(u'<input %s />' % html_params(name=field.name, **kwargs))


class TimeEntryForm(wtf.Form):

    PREDEFINED_TICKET_IDS = [
        {'value': 'M1', 'desc': _(u'Daily Standup')},
        {'value': 'M2', 'desc': _(u'Planning meeting')},
        {'value': 'M3', 'desc': _(u'Review meeting')},
        {'value': 'M4', 'desc': _(u'Retrospective meeting')},
    ]

    project_id = wtf.SelectField(_(u'Project'), validators=[validators.Required()],
                              choices=ProjectChoices(skip_inactive=True, empty=True))
    add_to_harvest = wtf.BooleanField(_(u'Add to Harvest'))
    time = wtf.TextField(_(u'Time'), validators=[TimerValidation(), TimerNumberRangeValidation(min=0.0, max=24.0)], filters=(time_filter,), widget=TimeInput())
    description = wtf.TextAreaField(u'Description', validators=[validators.Required()])
    ticket_id = wtf.StringField(_(u'Ticket #'), validators=[TicketIdValidator()])
    timer = wtf.HiddenField(_(u'Timer'))


class AddTimeEntryForm(TimeEntryForm):
    ticket_id = NonRequiredStringListField(_(u'Ticket #'), validators=[TicketIdListValidator()])


def end_month():
    year = today().year
    month = today().month
    day_of_week, days_in_month = calendar.monthrange(year, month)
    end_date = datetime.date(year, month, days_in_month)
    return end_date


class EmployeeChoices(object):
    def __init__(self, inactive=False, first_empty=False):
        self.inactive = inactive
        self.first_empty = first_empty

    def __iter__(self):
        if self.first_empty:
            yield '', ''*8
        query = DBSession.query(User.id, User.name)\
                              .filter(User.is_not_client())\
                              .filter(User.is_active==True)\
                              .order_by(User.name)
        for client_id, client_name in query:
            yield str(client_id), client_name

        if self.inactive:
            yield '', ' '*8
            query = DBSession.query(User.id, User.name)\
                                  .filter(User.is_not_client())\
                                  .filter(User.is_active==False)\
                                  .order_by(User.name)
            for id, name in query:
                yield str(id), name

class ProjectTimeForm(wtf.Form):
    date_range = utils.DateRangeField(
        u'Date range', validators=[validators.Required()], format='%d-%m-%Y',
        default=lambda: h.start_end_month(datetime.date.today()),
    )
    projects = wtf.SelectMultipleField(
        _(u'Projects'),
        choices=ProjectChoices(skip_inactive=True),
        validators=[]
    )
    group_by_client = wtf.BooleanField(_(u'Group by client'), default=True)
    group_by_project = wtf.BooleanField(_(u'Group by project'), default=True)
    group_by_bugs = wtf.BooleanField(_(u'Group by bugs'), default=True)
    group_by_user = wtf.BooleanField(_(u'Group by employee'), default=True)
    ticket_choice = wtf.RadioField(_('Tickets'), choices=[
        ('all','All'),
        ('without_bug_only','Without bugs only'),
        ('meetings_only','Meetings only'),
    ], default='all')

    def __init__(self, *args, **kwargs):
        super(ProjectTimeForm, self).__init__(*args, **kwargs)
        client = kwargs.pop('client', None)
        self.projects.choices = ProjectChoices(client=client, skip_inactive=True)

class ProjectsTimeForm(ProjectTimeForm):
    users = wtf.SelectMultipleField(_(u'Employees'), choices=EmployeeChoices())


class ClientChoices(object):

    def __iter__(self):
        query = DBSession().query(Client.id, Client.name).order_by(Client.name)
        for client_id, client_name in query:
            yield str(client_id), client_name


class ClientTimeForm(wtf.Form):
    clients = wtf.SelectMultipleField(_(u'Clients'), choices=ClientChoices(), validators=[validators.Required()])
    date = wtf.DateField(_(u'Month'), validators=[validators.Required()],
                                   format='%d/%m/%Y',
                                   default=datetime.date(today().year, today().month, 1))
    groupby = wtf.RadioField(_(u'Client / Project'), choices=[('client', _(u'By client')),('project', _(u'By Project'))], default='client')


class HoursWorkedReportFormBase(wtf.Form):
    date_range = wtf.SelectField(_(u'Report for'), validators=[],
                                         choices=[('0', u'date range'),
                                                  ('1', u'current quarter'),
                                                  ('2', u'previous quarter'),
                                                  ('3', u'current year'),
                                                  ('4', u'previous year')],
                                         default='0')
    start_date = wtf.DateField(_(u'Start'), validators=[DataValidator(format='%d/%m/%Y')],
                                              format='%d/%m/%Y',
                                              default=datetime.date(today().year, today().month, 1))
    end_date = wtf.DateField(_(u'End'), validators=[DataValidator(format='%d/%m/%Y')],
                                          format='%d/%m/%Y',
                                          default=end_month)
    user_id = wtf.SelectMultipleField(_(u'Employees'), validators=[], choices=EmployeeChoices(inactive=True))
    only_fully_employed = wtf.BooleanField(_(u'Full time employees only'),
                                           default=True)
    only_red = wtf.BooleanField(_(u'Red only'), default=True)
    group_by_month = wtf.BooleanField(_(u'Group by month'), default=True)

