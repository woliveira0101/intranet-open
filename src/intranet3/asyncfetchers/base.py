import codecs
import functools
import csv

import gevent
from requests.auth import HTTPBasicAuth

from intranet3 import memcache
from intranet3.helpers import decoded_dict
from intranet3.log import DEBUG_LOG, ERROR_LOG
from .request import RPC

DEBUG = DEBUG_LOG(__name__)
ERROR = ERROR_LOG(__name__)

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
    """
    Metaclass for Fetcher classes.
    It does three things:
    1. Spawns greenlets when one of mcs.FETCHERS method is called
    2. Generates self._memcache_key
    3. Decides if use cached data from memcached.
    """

    MEMCACHED_KEY = '{tracker_id}-{login}-{method_name}-{args}-{kwargs}'
    FETCHERS = [
        'fetch_user_tickets',
        'fetch_all_tickets',
        'fetch_bugs_for_query',
        'fetch_scrum',
    ]

    @classmethod
    def _gen_memcached_key(mcs, tracker_id, login, method_name, args, kwargs):
        """
        Fancy key generator (c)
        """
        args = str(args)
        kwargs = str(kwargs)
        return mcs.MEMCACHED_KEY.format(**locals()).replace(' ', '')

    @classmethod
    def __async(mcs, f):
        @functools.wraps(f)
        def func(*args, **kwargs):
            self = args[0]
            self._memcached_key = mcs._gen_memcached_key(
                self.tracker.id,
                self.login,
                f.func_name,
                args[1:],
                kwargs,
            )
            # clear fetcher
            self._parsed_data = []
            cached = memcache.get(self._memcached_key)

            if cached is not None:
                DEBUG(u"Bugs found in cache for key %s" % self._memcached_key )
                self._parsed_data = cached
            else:
                # start greenlet
                DEBUG(u"Bugs not in cache for key %s" % self._memcached_key)
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
    BUG_PRODUCER_CLASS = None
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
        self.error = None
        self.cache_key = None
        self.dependson_and_blocked_status = {}
        self.timeout = timeout

        # _parsed_data is set by metaclass if it is present in memached
        self._parsed_data = []
        # _memcached_data is set by metaclass
        self._memcached_key = None

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
            self.check_if_failed(response)
            self._parsed_data.extend(self.parse(response.text))

        self._parsed_data = self.after_parsing(self._parsed_data)
        memcache.set(self._memcached_key, self._parsed_data, self.CACHE_TIMEOUT)

    def check_if_failed(self, response):
        code = response.status_code
        if 200 > code > 299:
            reason = u'Received response %s' % code
            raise FetchException(reason)

    def get_result(self):
        if self._greenlet:
            self._greenlet.join(self.MAX_TIMEOUT)

            if not self._greenlet.ready():
                raise FetcherTimeout()

            if not self._greenlet.successful():
                raise self._greenlet.exception

        bug_producer = self.BUG_PRODUCER_CLASS(self.tracker, self.login_mapping)
        bugs = {}
        for bug_desc in self._parsed_data:
            bug = bug_producer(
                bug_desc,
            )
            bugs[bug.id] = bug

        return bugs.values()

    # methods that should/could be overridden:

    def after_parsing(self, parsed_data):
        return parsed_data

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
        result = []
        for bug_desc in reader:
            bug_desc = decoded_dict(bug_desc, encoding=self.encoding)
            result.append(bug_desc)
        return result
