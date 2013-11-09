
import gevent
import gevent.monkey
gevent.monkey.patch_all()

import sys
import traceback
import codecs
import functools
import csv

from requests.auth import HTTPBasicAuth

from intranet3.models import User
from intranet3.helpers import decoded_dict

from .request import RPC



class FetchException(Exception):
    pass

class Scrum(object):
    def __init__(self, bug):
        self.__bug = bug

    @property
    def points(self):
        return None

    @property
    def velocity(self):
        return 0.0


class Bug(object):
    Scrum = Scrum

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
            self.get_reporter(self.data),
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


class FetcherMeta(type):
    FETCHERS = [
        'fetch_user_tickets',
        'fetch_all_tickets',
        'fetch_bugs_for_query',
        'fetch_scrum',

        'fetch_bug_titles_and_depends_on',
        'fetch_dependons_for_ticket_ids',
    ]

    @staticmethod
    def __async(f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            self = args[0]
            self._run = f
            self.args = args
            self.kwargs = kwargs
            self.start()
            return
        return func

    def __new__(mcs, name, bases, dct):
        for name, prop in dct.iteritems():
            if name in mcs.FETCHERS:
                dct[name] = mcs.__async(prop)
        return type.__new__(mcs, name, bases, dct)

class BaseFetcher(gevent.Greenlet):
    __metaclass__ = FetcherMeta
    CACHE_TIMEOUT = 3 * 60  # 3 minutes
    SPRINT_REGEX = 's=%s(?!\S)'
    BUG_CLASS = Bug
    MAX_TIMEOUT = 50 # DON'T WAIT LONGER THAN DEFINED TIMEOUT

    def __repr__(self):
        return ''


    def __init__(self, tracker, credentials, login_mapping, timeout=MAX_TIMEOUT):
        gevent.Greenlet.__init__(self)
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

        self.traceback = None
        self.fetch_error = None

    def get_auth(self):
        """ Perform action to get authentication (like token or cookies) """
        return None

    def set_auth(self, session, data=None):
        """ Perform action to set authentication (like token or cookies) """
        return None

    def add_data(self, session):
        return None

    def before_processing(self, rpc):
        """
        Store some data before doing processing,
        i.e. fetch some data necessary for processing
        """
        return None

    def consume(self, rpcs):
        if not isinstance(rpcs, list):
            rpcs = [rpcs]

        auth_data = self.get_auth()

        for rpc in rpcs:
            self.set_auth(rpc.s, auth_data)
            self.add_data(rpc.s)
            rpc.start()

        rpc = RPC()
        self.set_auth(rpc.s, auth_data)
        self.before_processing(rpc)

        for rpc in rpcs:
            response = rpc.get_result()
            reason = self.check_if_failed(response)
            if reason:
                self.fail(FetchException(reason))
                return
            self.received(response.text)

    def check_if_failed(self, response):
        code = response.status_code
        if 200 > code > 299:
            return u'Received response %s' % code

    def received(self, data):
        """ Called when server returns whole response body """
        try:
            self.bugs = [bug for bug in self.parse(data)]
        except Exception as e:
            self.fail(*sys.exc_info())

    def parse(self, data):
        for bug_data in data:
            yield bug_data

    def result(self):
        """ iterate over fetched tickets """
        self.join()
        if self.fetch_error:
            e, v, t = self.fetch_error
            raise e, v, t

        return [
            self.BUG_CLASS(self.tracker, self.login_mapping, bug_data)
            for bug_data in self.bugs
        ]

    def fail(self, type_, value=None, traceb=None):
        self.fetch_error = type_, value, traceb

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


class BasicAuthMixin(object):

    def set_auth(self, session, data=None):
        session.auth = HTTPBasicAuth(self.login, self.password)

class CSVParserMixin(object):
    # bug object class
    bug_class = None

    # CSV encoding
    encoding = 'utf-8'

    # CSV delimited
    delimiter=','

    def parse(self, data):
        if codecs.BOM_UTF8 == data[:3]:
            data = data.decode('utf-8-sig')
        else:
            data = data.encode('utf-8')

        if '\r\n' in data:
            data = data.split('\r\n')
        else:
            data = data.split('\n')

        reader = csv.DictReader(data,  delimiter=self.delimiter)
        for bug_desc in reader:
            bug_desc = decoded_dict(bug_desc, encoding=self.encoding)
            yield bug_desc
