from __future__ import with_statement
import wtforms as wtf
from wtforms import validators
from pyramid.i18n import TranslationStringFactory

from .utils import StarredPasswordField, EntityChoices, ListValidator
from .project import ProjectChoices
from intranet3.models import DBSession, User

_ = TranslationStringFactory('intranet3')

class UserChoices(EntityChoices):
    
    def __init__(self, empty=False, empty_title=u'-- None --'):
        super(UserChoices, self).__init__(entity_class=User, title_getter=None, empty=empty, empty_title=empty_title)
    
    def __iter__(self):
        if self.empty:
            yield '', self.empty_title
        query = DBSession.query(User.id, User.name).order_by(User.name)
        for user_id, user_name in query:
            yield str(user_id), u'%s' % (user_name)


class GeneralForm(wtf.Form):
    office_ip = wtf.TextField(_(u"Office IP prefixes"), validators=[validators.Required()])
    google_user_email = wtf.TextField(
        _(u'Google User Email'),
        validators=[
            validators.Email(),
            validators.Required(),
            validators.Length(min=6, max=64)
        ]
    )
    google_user_password = StarredPasswordField(
        _(u'Google User Password'),
        validators=[
            validators.Required(),
            validators.Length(min=6, max=64)
        ]
    )
    cleaning_time_presence = wtf.IntegerField(
        _(u'Cleaning time presence'),
        validators=[
            validators.Required(),
        ]
    )
    absence_project_id = wtf.SelectField(_(u'Absence project'), validators=[], choices=ProjectChoices(skip_inactive=True, empty=True))
    monthly_late_limit = wtf.IntegerField(
        _(u'Monthly late limit'),
        validators=[
            validators.Required(),
            ]
    )
    monthly_incorrect_time_record_limit = wtf.IntegerField(
        _(u'Monthly incorrect time record limit'),
        validators=[
            validators.Required(),
            ]
    )

class ReportsForm(wtf.Form):
    reports_project_ids = wtf.SelectMultipleField(_(u'Daily report - include projects'), validators=[], choices=ProjectChoices())
    reports_omit_user_ids = wtf.SelectMultipleField(_(u'Daily report - omit user'), validators=[], choices=UserChoices())
    reports_without_ticket_project_ids = wtf.SelectMultipleField(_(u'Daily report without ticket - include projects'), validators=[], choices=ProjectChoices())
    reports_without_ticket_omit_user_ids = wtf.SelectMultipleField(_(u'Daily report without ticket - omit user'), validators=[], choices=UserChoices())


class SpreadsheetsForm(wtf.Form):
    holidays_spreadsheet = wtf.TextField(_(u"Holidays Spreadsheet"), validators=[validators.Required()])
    hours_employee_project = wtf.TextField(_(u"Hours employee - project Spreadsheet"), validators=[validators.Required()])
    hours_ticket_user_id = wtf.SelectField(_(u'Hours per ticket synchronization user credentials'), validators=[], choices=UserChoices(empty=False))


class AccessForm(wtf.Form):
    freelancers = wtf.TextAreaField(_(u"Freelancers"), validators=[ListValidator(validators=[validators.Email()])])
