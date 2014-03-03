# -*- coding: utf-8 -*-
import wtforms as wtf
from wtforms import validators
from ordereddict import OrderedDict
from pyramid.i18n import TranslationStringFactory

from .utils import StarredPasswordField
from intranet3.log import INFO_LOG
from intranet3.models import DBSession

LOG = INFO_LOG(__name__)

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
# TODO: if you need those fetchers, take them from
# 8a57e8ae3cc83f3d14b173351ee2d615aaaad402
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

    name = wtf.TextField(
        _(u'Tracker friendly name'),
        validators=[validators.Required()]
    )
    url = wtf.TextField(
        _(u'Tracker URL'),
        validators=[validators.Required(), validators.URL()]
    )
    mailer = wtf.TextField(
        _(u'Mailer email'),
        validators=[validators.Optional(), validators.Email()]
    )
    description = wtf.TextAreaField(
        _(u'Tracker description'),
        validators=[validators.Optional()]
    )


class TrackerLoginForm(wtf.Form):
    """ Tracker login form """

    def __init__(self, tracker, user, post=None, *args, **kwargs):

        self.tracker = tracker
        self.user = user

        self._tracker_credentials = self.tracker.get_credentials(self.user)

        if self._tracker_credentials:
            credentials = self._tracker_credentials.credentials
            kwargs.update(credentials)

        super(TrackerLoginForm, self).__init__(post, *args, **kwargs)

    login = wtf.TextField(
        label=_(u'Login'),
        description='Login for given tracker',
        validators=[validators.Required()]
    )
    password = StarredPasswordField(
        label=_(u'Password'),
        description='Password for given tracker',
        validators=[validators.Required()]
    )

    @property
    def credentials(self):
        return {field.name: field.data for field in self}

    def save_credentials(self):
        if self._tracker_credentials is None:
            self._tracker_credentials = \
                self.tracker.create_credentials(self.user)
        self._tracker_credentials.credentials = self.credentials
        DBSession.add(self._tracker_credentials)
        LOG(u"Credentials saved")
        return self._tracker_credentials


class PivotalTrackerLoginForm(TrackerLoginForm):
    """ Pivotal tracker login form """
    email = wtf.TextField(
        label=_(u'Email'),
        description=_(u'Your Pivotal account email'),
        validators=[validators.Required(), validators.Email()]
    )
