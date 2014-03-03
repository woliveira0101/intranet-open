import json

from sqlalchemy import orm, Column, ForeignKey
from sqlalchemy.types import Enum, String, Integer
from pyramid.decorator import reify

from intranet3.utils.encryption import encrypt, decrypt
from intranet3.models import (
    Base,
    User,
    Project,
    DBSession,
)

from intranet3.helpers import serialize_url
from intranet3.forms import tracker as tracker_forms
from intranet3.asyncfetchers import FETCHERS

bugzilla_ticket_url = lambda tracker_url, ticket_id: \
    '%s/show_bug.cgi?id=%s' % (tracker_url, ticket_id)

trac_ticket_url = lambda tracker_url, ticket_id: \
    '%s/ticket/%s' % (tracker_url, ticket_id)

bitbucket_ticket_url = lambda tracker_url, ticket_id: \
    '%s/issues/%s' % (tracker_url.replace(
        'https://api.bitbucket.org/1.0/repositories/',
        'https://bitbucket.org/'), ticket_id
    )


def bugzilla_new_ticket_url(tracker_url, project_selector, component_selector):
    params = {}

    if project_selector:
        params['product'] = project_selector
    if component_selector:
        params['component'] = component_selector

    return serialize_url(tracker_url + '/enter_bug.cgi?', **params)


def trac_new_ticket_url(tracker_url, project_selector, component_selector):
    params = {}

    if project_selector:
        params['client_name'] = project_selector
    if component_selector:
        params['component'] = component_selector

    return serialize_url(tracker_url + '/newticket?', **params)


def bitbucket_new_ticket_url(tracker_url, project_selector,
                             component_selector):
    url = tracker_url.replace(
        'https://api.bitbucket.org/1.0/repositories/',
        'https://bitbucket.org/'
    )
    return serialize_url(url + '/issues/new')


def pivotaltracker_ticket_url(tracker_url, ticket_id):
    return tracker_url + '/story/show/%s' % ticket_id


def pivotaltracker_new_ticket_url(tracker_url, project_selector,
                                  component_selector):
    return tracker_url + '/projects'


def unfuddle_ticket_url(tracker_url, ticket_id):
    return tracker_url


def unfuddle_new_ticket_url(tracker_url, project_selector, component_selector):
    return tracker_url


def github_ticket_url(tracker_url, ticket_id):
    return tracker_url


def github_new_ticket_url(tracker_url, project_selector, component_selector):
    return tracker_url


def jira_ticket_url(tracker_url, ticket_id):
    return tracker_url


def jira_new_ticket_url(tracker_url, project_selector, component_selector):
    return tracker_url


class Tracker(Base):
    """ Tracker model """

    class TrackerPermissionError(Exception):
        pass

    __tablename__ = 'tracker'

    URL_CONSTRUCTORS = {
        'trac': trac_ticket_url,
        'cookie_trac': trac_ticket_url,
        'bugzilla': bugzilla_ticket_url,
        'igozilla': bugzilla_ticket_url,
        'rockzilla': bugzilla_ticket_url,
        'bitbucket': bitbucket_ticket_url,
        'pivotaltracker': pivotaltracker_ticket_url,
        'unfuddle': unfuddle_ticket_url,
        'github': github_ticket_url,
        'jira': jira_ticket_url,
    }

    NEW_BUG_URL_CONSTRUCTORS = {
        'trac': trac_new_ticket_url,
        'cookie_trac': trac_new_ticket_url,
        'bugzilla': bugzilla_new_ticket_url,
        'igozilla': bugzilla_new_ticket_url,
        'rockzilla': bugzilla_new_ticket_url,
        'bitbucket': bitbucket_new_ticket_url,
        'pivotaltracker': pivotaltracker_new_ticket_url,
        'unfuddle': unfuddle_new_ticket_url,
        'github': github_new_ticket_url,
        'jira': jira_new_ticket_url,
    }

    LOGIN_FORM = {
        'pivotaltracker': tracker_forms.PivotalTrackerLoginForm,
    }

    id = Column(Integer, primary_key=True, nullable=False, index=True)
    type = Column(Enum("bugzilla", "trac", "cookie_trac", "igozilla",
                  "bitbucket", "rockzilla", "pivotaltracker", "harvest",
                  'unfuddle', 'github', 'jira',
                  name='tracker_type_enum'), nullable=False)
    name = Column(String, nullable=False, unique=True)
    url = Column(String, nullable=False, unique=True)
    mailer = Column(String, nullable=True, unique=True)
    description = Column(String, nullable=True)

    credentials = orm.relationship('TrackerCredentials', backref='tracker',
                                   lazy='dynamic')
    projects = orm.relationship('Project', backref='tracker', lazy='dynamic')

    def get_url(self):
        """ hack for unfuddle
        """
        return ''.join(self.url.split('[MARKER]'))

    def get_bug_url(self, id):
        """ Calculate URL for bug 'id' on this tracker """
        constructor = self.URL_CONSTRUCTORS[self.type]
        return constructor(self.url, id)

    def get_new_bug_url(self, project_selector, component_selector):
        """ Returns url for create new bug in project """
        constructor = self.NEW_BUG_URL_CONSTRUCTORS[self.type]
        return constructor(self.url, project_selector, component_selector)

    @reify
    def logins_mapping(self):
        return TrackerCredentials.get_logins_mapping(self)

    def get_fetcher(self, tracker_credentials, user, full_mapping=False):
        fetcher_class = FETCHERS.get(self.type)

        if full_mapping:
            mapping = self.logins_mapping
        else:
            mapping = tracker_credentials.get_login_mapping(user)

        return fetcher_class(
            self,
            tracker_credentials.credentials,
            user,
            mapping,
        )

    def get_form(self):
        return Tracker.LOGIN_FORM.get(
            self.type,
            tracker_forms.TrackerLoginForm
        )

    def get_credentials(self, user):
        if user.client:
            query = Tracker.query \
                .filter(Project.tracker_id == self.id) \
                .filter(Project.client_id == user.client.id) \
                .filter(Tracker.id == Project.tracker_id)
            result = query.first()
            if not result:
                raise Tracker.TrackerPermissionError(
                    'Client has no permissions to this tracker'
                )

        else:
            return TrackerCredentials.query \
                .filter(TrackerCredentials.user == user) \
                .filter(TrackerCredentials.tracker_id == self.id) \
                .first()

    def create_credentials(self, user):
        return TrackerCredentials(
            tracker_id=self.id,
            user_id=user.id
        )


class TrackerCredentials(Base):
    """ Credentials for given tracker for given user """
    __tablename__ = 'tracker_credentials'

    tracker_id = Column(Integer, ForeignKey(Tracker.id), nullable=False,
                        primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False,
                     primary_key=True, index=True)
    credentials_json = Column(String, nullable=False)

    @property
    def credentials(self):
        credentials = json.loads(self.credentials_json)
        credentials['password'] = decrypt(credentials.get('password', ''))
        return credentials

    @credentials.setter
    def credentials(self, value):
        value = value.copy()
        value['password'] = encrypt(value.get('password', ''))
        self.credentials_json = json.dumps(value)

    def get_login_mapping(self, user):
        return {
            self.credentials.get('login', '').lower(): user
        }

    @classmethod
    def get_logins_mapping(cls, tracker):
        """
        Returns dict user login -> user object for given tracker
        """
        creds_query = DBSession.query(cls, User)\
            .filter(cls.tracker_id == tracker.id)\
            .filter(cls.user_id == User.id)

        return {
            credentials.credentials['login'].lower(): user
            for credentials, user in creds_query
        }
