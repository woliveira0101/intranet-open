# -*- coding: utf-8 -*-
"""
Forms for user edit
"""
import wtforms as wtf
from wtforms import validators
from pyramid.i18n import TranslationStringFactory

from intranet3.models.user import User

_ = TranslationStringFactory('intranet3')

class UserEditForm(wtf.Form):
    """ Admin edits freelancer's profile """

    employment_contract = wtf.BooleanField(_(u"Employment contract"), validators=[])
    is_active = wtf.BooleanField(_(u"Is active"), validators=[])

    avatar = wtf.HiddenField()
    roles = wtf.SelectMultipleField(_(u'Role'), validators=[], choices=User.LEVELS)
    
    start_work  = wtf.DateField(_(u"Start work"), format='%d/%m/%Y', validators=[])
    start_full_time_work  = wtf.DateField(_(u"Start full time work"), format='%d/%m/%Y', validators=[validators.Optional()])
    stop_work = wtf.DateField(_(u"Stop work"), format='%d/%m/%Y', validators=[validators.Optional()])
    description = wtf.TextField(_(u"Description"), validators=[validators.Optional()])
    location = wtf.SelectField(
        _(u"Office location"),
        choices=[('', u'--None--')] + [(k, v[0]) for k, v in User.LOCATIONS.items()]
    )

    availability_link = wtf.TextField(_(u"Availability calendar link"), validators=[validators.Optional(), validators.URL()])
    tasks_link = wtf.TextField(_(u"Tasks calendar link"), validators=[validators.Optional(), validators.URL()])
    skype = wtf.TextField(_(u"Skype"), validators=[validators.Optional()])
    phone = wtf.TextField(_(u"Phone"), validators=[validators.Optional()])
    phone_on_desk = wtf.TextField(_(u"Deskphone"), validators=[validators.Optional()])
    irc = wtf.TextField(_(u"IRC"), validators=[validators.Optional()])

    groups = wtf.SelectMultipleField(_(u'Groups'), validators=[], choices=(('freelancer','freelancer'),('user','user'),('admin','admin'), ('scrum', 'scrum')))

