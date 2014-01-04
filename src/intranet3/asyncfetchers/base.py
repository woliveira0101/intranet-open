import sys
import traceback
import codecs
import functools
import csv

import gevent
from requests.auth import HTTPBasicAuth

from intranet3.models import User
from intranet3.models.project import SelectorMapping
from intranet3.helpers import decoded_dict
from .request import RPC


class FetcherBaseException(Exception):
    pass


class FetchException(FetcherBaseException):
    pass


class FetcherTimeout(FetcherBaseException):
    pass

class FetcherBadDataError(FetcherBaseException):
    """
    Exception that indicates that is misconfigurated,
    like wrong password or wrong sprint name.
    Exception.message will be shown to user.
    """


class FetcherMeta(type):
    FETCHERS = [
        'fetch_user_tickets',
        'fetch_all_tickets',
        'fetch_bugs_for_query',
        'fetch_scrum',
    ]

    @staticmethod
    def __async(f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            self = args[0]
            # clear fetcher
            self.bugs = {}
            # start greenlet
            self.before_fetch()
            self._greenlet = gevent.Greenlet.spawn(f, *args, **kwargs)
        return func

    def __new__(mcs, name, bases, attrs):
        for attr_name in mcs.FETCHERS:
            if attr_name in attrs:
                attr = attrs[attr_name]
                attrs[attr_name] = mcs.__async(attr)
        return type.__new__(mcs, name, bases, attrs)

class BaseFetcher(object):
    __metaclass__ = FetcherMeta
    bug_class = None
    get_converter = None
    CACHE_TIMEOUT = 3 * 60  # 3 minutes
    SPRINT_REGEX = 's=%s(?!\S)'
    MAX_TIMEOUT = 30 # DON'T WAIT LONGER THAN DEFINED TIMEOUT

    def __init__(self, tracker, credentials, user, login_mapping, timeout=MAX_TIMEOUT):
        self._greenlet = None
        self.tracker = tracker
        self.login = credentials.login
        self.password = credentials.password
        self.user = user
        self.login_mapping = login_mapping
        self.bugs = {}
        self.done = False
        self.error = None
        self.cache_key = None
        self.dependson_and_blocked_status = {}
        self.timeout = timeout

        self.traceback = None
        self.fetch_error = None

        self._auth_data = None

    def get_auth(self):
        """ Perform action to get authentication (like token or cookies) """
        return None

    def set_auth(self, session, data=None):
        """ Perform action to set authentication (like token or cookies) """
        return None

    def add_data(self, session):
        return None

    def before_fetch(self):
        """
        Action before fetching the data
        It is called before fetch_* function.
        It blocks fetch_* function.
        """
        return None

    def apply_auth(self, rpc_or_session):
        if isinstance(rpc_or_session, RPC):
            session = rpc_or_session.s
        else:
            session = rpc_or_session

        if not self._auth_data:
            self._auth_data = self.get_auth()
        self.set_auth(session, self._auth_data)

    def get_rpc(self):
        rpc = RPC()
        self.apply_auth(rpc)
        return rpc

    def consume(self, rpcs):
        if not isinstance(rpcs, list):
            rpcs = [rpcs]

        if not self._auth_data:
            self._auth_data = self.get_auth()

        for rpc in rpcs:
            self.set_auth(rpc.s, self._auth_data)
            self.add_data(rpc.s)
            rpc.start()

        for rpc in rpcs:
            response = rpc.get_result()
            reason = self.check_if_failed(response)
            if reason:
                raise FetchException(reason)
            self.received(response.text)

        self.done = True

    def check_if_failed(self, response):
        code = response.status_code
        if 200 > code > 299:
            return u'Received response %s' % code

    def received(self, data):
        """ Called when server returns whole response body """
        converter = self.get_converter()
        for bug_desc in self.parse(data):
            bug = self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )
            self.bugs[bug.id] = bug

    def resolve_user(self, orig_login):
        login = orig_login.lower()
        if login in self.login_mapping:
            return self.login_mapping[login]
        else:
            return User(name=orig_login, email=orig_login)

    def resolve(self, bug):
        bug.owner = self.resolve_user(bug.owner)
        bug.reporter = self.resolve_user(bug.reporter)
        bug.project_id = SelectorMapping(self.tracker).match(
            bug.id, bug.project_name, bug.component_name, bug.version,
        )

    def get_result(self):
        self._greenlet.join(self.MAX_TIMEOUT)

        if not self._greenlet.ready():
            raise FetcherTimeout()

        if not self._greenlet.successful():
            raise self._greenlet.exception

        results = []
        for bug in self.bugs.itervalues():
            self.resolve(bug)
            results.append(bug)

        return results

    # methods that should be overridden:

    def parse(self, data):
        raise NotImplementedError()

    def fetch_user_tickets(self, resolved=False):
        """ Start fetching tickets for current user """
        raise NotImplementedError()

    def fetch_all_tickets(self, resolved=False):
        """ Start fetching tickets for all users in mapping """
        raise NotImplementedError()

    def fetch_bugs_for_query(self, ticket_ids, project_selector, component_selector, version, resolved=False):
        """ Start fetching all bugs matching given criteria """
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
