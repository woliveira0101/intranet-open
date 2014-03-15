from sqlalchemy import orm, Column, ForeignKey
from sqlalchemy.types import Enum, String, Integer
from pyramid.decorator import reify

from intranet3.utils.encryption import encrypt, decrypt
from intranet3.models import Base, User, DBSession
from intranet3.helpers import serialize_url

bugzilla_ticket_url = lambda tracker_url, ticket_id: '%s/show_bug.cgi?id=%s' % (tracker_url, ticket_id)
trac_ticket_url = lambda tracker_url, ticket_id: '%s/ticket/%s' % (tracker_url, ticket_id)
bitbucket_ticket_url = lambda tracker_url, ticket_id: '%s/issues/%s' % (tracker_url.replace('https://api.bitbucket.org/1.0/repositories/', 'https://bitbucket.org/'), ticket_id)


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


def bitbucket_new_ticket_url(tracker_url, project_selector, component_selector):
    url = tracker_url.replace('https://api.bitbucket.org/1.0/repositories/', 'https://bitbucket.org/')
    return serialize_url(url + '/issues/new')


def pivotaltracker_ticket_url(tracker_url, ticket_id):
    return tracker_url + '/story/show/%s' % ticket_id


def pivotaltracker_new_ticket_url(tracker_url, project_selector, component_selector):
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


    id = Column(Integer, primary_key=True, nullable=False, index=True)

    type = Column(Enum("bugzilla", "trac", "cookie_trac", "igozilla", "bitbucket", "rockzilla", "pivotaltracker", "harvest", 'unfuddle', 'github', name='tracker_type_enum'), nullable=False)
    name = Column(String, nullable=False, unique=True)
    url = Column(String, nullable=False, unique=True)
    mailer = Column(String, nullable=True, unique=True)

    credentials = orm.relationship('TrackerCredentials', backref='tracker', lazy='dynamic')
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


class TrackerCredentials(Base):
    """ Credentials for given tracker for given user """
    __tablename__ = 'tracker_credentials'

    tracker_id = Column(Integer, ForeignKey(Tracker.id), nullable=False, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False, primary_key=True, index=True)
    login = Column(String, nullable=False)
    password = Column(String, nullable=False)

    def __getattribute__(self, name):
        value = super(TrackerCredentials, self).__getattribute__(name)
        if name == 'password' and value:
            value = decrypt(value)
        return value

    def __setattr__(self, name, value):
        if name == 'password' and value:
            value = encrypt(value)
        super(TrackerCredentials, self).__setattr__(name, value)

    @classmethod
    def get_logins_mapping(cls, tracker):
        """
        Returns dict user login -> user object for given tracker
        """
        creds_query = DBSession.query(cls, User)\
                               .filter(cls.tracker_id==tracker.id)\
                               .filter(cls.user_id==User.id)

        return dict(
            (credentials.login.lower(), user) for credentials, user in creds_query
        )


