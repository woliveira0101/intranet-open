# -*- coding: utf-8 -*-
"""
Forms for user edit
"""
import wtforms as wtf
from wtforms import validators
from pyramid.i18n import TranslationStringFactory

from intranet3.models.user import User
from intranet3.forms.utils import MinYearValidator

_ = TranslationStringFactory('intranet3')


class UserEditForm(wtf.Form):
    """ Admin edits freelancer's profile """

    start_work_experience_tooltip = u"""
    Rok rozpoczęcia pracy zawodowej, dzięki czemu będziemy mogli
    policzyć automatycznie doświadczenie. Jeżeli ktoś pracował przez
    4 lata na pół etatu, to należy to potraktować jako 2 lata, czyli
    dodać dwa do roku rozpoczęcia pracy zawodowej. Bierzemy pod uwagę
    tylko pracę w branży wynikającej ze stanowiska, czyli jak
    programista pracował jako kelner to tego mu nie wliczamy.
    """

    employment_contract = wtf.BooleanField(
        _(u"Employment contract"),
        validators=[],
    )
    is_active = wtf.BooleanField(_(u"Is active"), validators=[])
    avatar = wtf.HiddenField()
    roles = wtf.SelectMultipleField(
        _(u'Role'),
        validators=[],
        choices=User.ROLES,
    )
    start_work = wtf.DateField(
        _(u"Start work"),
        format='%d/%m/%Y',
        validators=[MinYearValidator()],
    )
    start_full_time_work = wtf.DateField(
        _(u"Start full time work"),
        format='%d/%m/%Y',
        validators=[validators.Optional(), MinYearValidator()],
    )
    stop_work = wtf.DateField(
        _(u"Stop work"),
        format='%d/%m/%Y',
        validators=[validators.Optional(), MinYearValidator()],
    )
    description = wtf.TextField(
        _(u"Description"),
        validators=[validators.Optional()],
    )
    date_of_birth = wtf.DateField(
        _(u"Date of birth"),
        format='%d/%m/%Y',
        validators=[validators.Optional(), MinYearValidator()],
    )
    location = wtf.SelectField(
        _(u"Office location"),
        choices=[('', u'--None--')] + [(k, v[0]) for k, v in User.LOCATIONS.items()]
    )
    start_work_experience = wtf.DateField(
        _(u"Start work experience"),
        validators=[validators.Optional(), MinYearValidator()],
        description=start_work_experience_tooltip,
        format="%Y",
    )
    availability_link = wtf.TextField(
        _(u"Availability calendar link"),
        validators=[validators.Optional(), validators.URL()],
    )
    tasks_link = wtf.TextField(
        _(u"Tasks calendar link"),
        validators=[validators.Optional(), validators.URL()],
    )
    skype = wtf.TextField(_(u"Skype"), validators=[validators.Optional()])
    phone = wtf.TextField(_(u"Phone"), validators=[validators.Optional()])
    phone_on_desk = wtf.TextField(
        _(u"Deskphone"),
        validators=[validators.Optional()],
    )
    irc = wtf.TextField(_(u"IRC"), validators=[validators.Optional()])

    groups = wtf.SelectMultipleField(_(u'Groups'), validators=[], choices=((
        ('freelancer', 'freelancer'),
        ('employee', 'employee'),
        ('admin', 'admin'),
        ('scrum master', 'scrum master'),
        ('hr', 'hr'),
        ('business', 'business'),
        ('client', 'client'),
    )))

