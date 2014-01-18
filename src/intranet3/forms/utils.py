import json
import datetime
import dateutil.parser as dparser

import wtforms as wtf
from wtforms import widgets
from wtforms.validators import ValidationError
from pyramid.i18n import TranslationStringFactory
from sqlalchemy import not_

from intranet3.models import DBSession, User

_ = TranslationStringFactory('intranet3')

class TimeField(wtf.TextField):
    """
    TimeField, which stores a `datetime.time`.
    """
    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                self.data = dparser.parse(date_str).time() #konwersja 12h -> 24h
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid time value'))

class StarredPasswordField(wtf.PasswordField):

    widget = widgets.PasswordInput(hide_value=False)


class EntityChoices(object):

    def __init__(self, entity_class, title_getter, empty=False, empty_title=u'-- None --', order_by=None):
        self.entity_class = entity_class
        self.title_getter = title_getter
        self.empty = empty
        self.empty_title = empty_title
        self.order_by = order_by

    def __iter__(self):
        if self.empty:
            yield '', self.empty_title
        query = self.entity_class.query
        if self.order_by is not None:
            query = query.order_by(self.order_by)
        else:
            query = query.all()
        for entity in query:
            yield str(entity.id), self.title_getter(entity)


class FieldDataProxy(object):

    def __init__(self, obj, data):
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, 'data', data)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def __setattr__(self, name, value):
        setattr(self._obj, name, value)


class ListValidator(object):

    def __init__(self, separator='\n', validators=[]):
        self.separator = separator
        self.validators = validators

    def __call__(self, form, field):
        if field.data and isinstance(field.data, basestring):
            text = field.data.strip()
            for value in text.split(self.separator):
                value = value.strip()
                proxy = FieldDataProxy(field, value)
                for validator in self.validators:
                    validator(form, proxy)


class JSONValidator(object):

    def __call__(self, form, field):
        try:
            json.loads(field.data)
        except:
            raise ValidationError(_('Not json'))

class DataValidator(object):
    def __init__(self, message=None, format='%Y-%m-%d'):
        self.format = format
        self.message = message

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext(_('This field is required.'))
        if not field.data or not isinstance(field.data, datetime.date):
            raise ValidationError(self.message)


class UserChoices(object):
    def __init__(self, empty=False, inactive=False):
        self.empty = empty
        self.inactive = inactive
        self.session = DBSession()

    def __iter__(self):
        if self.empty:
            yield '', u'-- None --'
        query = self.session.query(User.id, User.name)\
                            .filter(not_(User.is_client()))\
                            .filter(User.is_active==True)\
                            .order_by(User.name)
        for id, name in query:
            yield str(id), name

        if self.inactive:
            yield '', ' '*8
            query = self.session.query(User.id, User.name)\
                                .filter(User.is_client())\
                                .filter(User.is_active==False)\
                                .order_by(User.name)
            for id, name in query:
                yield str(id), name


class DateRangeField(wtf.Field):
    """
    A text field which stores two `datetime.date` matching a format.
    """
    widget = widgets.TextInput()

    def __init__(self, label=None, validators=None, format='%Y-%m-%d', separator=' - ', **kwargs):
        super(DateRangeField, self).__init__(label, validators, **kwargs)
        self.format = format
        self.separator = separator

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            if self.data:
                start, end = self.data
                return '%s%s%s' % (start.strftime(self.format), self.separator, end.strftime(self.format))
            else:
                return ''

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            try:
                start, end = date_str.split(self.separator)
            except (ValueError, TypeError):
                self.data = None, None
                raise ValueError(self.gettext('Dates have to splitted by \'%s\'' % self.separator))

            try:
                start = datetime.datetime.strptime(start, self.format).date()
                end = datetime.datetime.strptime(end, self.format).date()
            except ValueError:
                self.data = None, None
                raise ValueError(self.gettext('Not a valid date value'))
            else:
                self.data = [start, end]
