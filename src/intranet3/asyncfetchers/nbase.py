from intranet3 import memcache
from intranet3.models import User


MAX_TIMEOUT = 50 # DON'T WAIT LONGER THAN DEFINED TIMEOUT


class Bug(object):
    class Scrum(object):
        def __init__(self, bug):
            self.__bug = bug

        @property
        def points(self):
            return None

        @property
        def velocity(self):
            return 0.0

    def __init__(self, tracker, login_mapping, raw_data):
        # we shouldn't keep login_mapping inside Bug object
        # we do not need it to be pickled during memcached set
        self.tracker = tracker
        self.data = self.parse(raw_data)
        self.owner = self.__resolve_user(
            self.get_owner(self.data),
            login_mapping,
        )
        self.reporter = self.__resolve_user(
            self.get_owner(self.data),
            login_mapping,
        )
        self.scrum = self.Scrum(self)

    def __resolve_user(self, orig_login, login_mapping):
        return login_mapping.get(
            orig_login.lower(),
            User(name=orig_login, email=orig_login),
        )

    def parse(self, raw_data):
        return raw_data

    def get_owner(self, data):
        """ Get tracker owner username """
        return None

    def get_reporter(self, data):
        """ Get tracker reporter username """
        return None

    @property
    def id(self):
        return None

    @property
    def desc(self):
        return None

    @property
    def priority(self):
        return None

    @property
    def severity(self):
        return None

    @property
    def status(self):
        return None

    @property
    def resolution(self):
        return None

    @property
    def url(self):
        return None

    @property
    def project(self):
        return None

    @property
    def opendate(self):
        return None

    @property
    def changeddate(self):
        return None

    @property
    def dependson(self):
        return {}

    @property
    def blocked(self):
        return {}



class BaseFetcher(object):
    CACHE_TIMEOUT = 3 * 60  # 3 minutes
    BUG_CLASS = Bug

    def __init__(self, tracker, credentials, login_mapping, timeout=MAX_TIMEOUT):
        self.tracker = tracker
        self.login = credentials.login
        self.password = credentials.password
        self.user = credentials.user
        self.login_mapping = login_mapping
        self.bugs = {}
        self.done = False
        self.error = None
        self.cache_key = None
        self.dependson_and_blocked_status = {}
        self.timeout = timeout

    def request(self, url, headers, method='GET', body=None):
        future = None
        return future

    def parse(self, data):
        for bug_data in data:
            yield bug_data

    def result(self):
        """ iterate over fetched tickets """
        if self.cache_key and self.error is None: # cache bugs if key was designeated and no error occured
            memcache.set(self.cache_key, self.bugs, timeout=self.CACHE_TIMEOUT)
        for bug_data in self.bugs.itervalues():
            yield self.BUG_CLASS(self.tracker, self.login_mapping, bug_data)

    # methods that should be overridden:

    def fetch_user_tickets(self):
        """ Start fetching tickets for current user """
        raise NotImplementedError()

    def fetch_all_tickets(self):
        """ Start fetching tickets for all users in mapping """
        raise NotImplementedError()

    def fetch_user_resolved_bugs(self):
        """ Start fetching fixable tickets for current user """
        raise NotImplementedError()

    def fetch_all_resolved_bugs(self):
        """ Start fetching fixable tickets for all users """
        raise NotImplementedError()

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version):
        """ Start fetching all bugs matching given criteria """
        raise NotImplementedError()

    def fetch_resolved_bugs_for_query(self, ticket_id, project_selector, component_selector, version):
        """ Start fetching resolved bugs matching given criteria """
        raise NotImplementedError()

    def fetch_bug_titles_and_depends_on(self, ticket_ids):
        """ Start fetching bug titles and bug depends_on for bugs with given ids """
        # TODO other implementations
        self.success()

    def fetch_dependons_for_ticket_ids(self, ticket_ids):
        """ Start recursively fetching dependons for ticket ids """
        raise NotImplementedError()

    def fetch_scrum(self, sprint_name, project_id, component_id=None):
        raise NotImplementedError()
