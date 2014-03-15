# -*- coding: utf-8 -*-
import wtforms as wtf
from wtforms import validators
from ordereddict import OrderedDict
from pyramid.i18n import TranslationStringFactory

from .utils import StarredPasswordField

_ = TranslationStringFactory('intranet3')

TRACKER_TYPES = OrderedDict()
TRACKER_TYPES["bugzilla"] = u"Bugzilla"
TRACKER_TYPES["trac"] = u"Trac"
TRACKER_TYPES["igozilla"] = u"Igozilla"
TRACKER_TYPES["rockzilla"] = u"SteepRockZilla"
TRACKER_TYPES["pivotaltracker"] = u"PivotalTracker"
TRACKER_TYPES["harvest"] = u"Harvest"
TRACKER_TYPES["unfuddle"] = u"Unfuddle"
TRACKER_TYPES["github"] = u"Github"
TRACKER_TYPES["jira"] = u"Jira"
# TODO: if you need those fetchers, take them from 8a57e8ae3cc83f3d14b173351ee2d615aaaad402
# and convert to use greenlet
#TRACKER_TYPES["cookie_trac"] = u"Cookie-Login Trac"
#TRACKER_TYPES["bitbucket"] = u"Bitbucket"

trackers_login_validators = {
    'all': {
        'login': validators.Required(),
        'password': validators.Required(),
    },
}


class TrackerForm(wtf.Form):
    """ Tracker form """
    type = wtf.SelectField(
        _(u'Tracker type'),
        choices=TRACKER_TYPES.items(),
        validators=[validators.Required()])
    name = wtf.TextField(_(u'Tracker friendly name'), validators=[validators.Required()])
    url = wtf.TextField(_(u'Tracker URL'), validators=[validators.Required(), validators.URL()])
    mailer = wtf.TextField(_(u'Mailer email'), validators=[validators.Optional(), validators.Email()])

class TrackerLoginForm(wtf.Form):
    """ Tracker login form """
    login = wtf.TextField(_(u'Login'), validators=[validators.Required()])
    password = StarredPasswordField(_(u'Password'), validators=[validators.Required()])
