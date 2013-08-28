# -*- coding: utf-8 -*-
import csv
import codecs
from base64 import b64encode
from twisted.internet import reactor
from twisted.web.client import Agent, WebClientContextFactory
from twisted.web.http_headers import Headers
from twisted.web._newclient import ResponseDone
from twisted.internet.protocol import Protocol
from twisted.web.iweb import IBodyProducer
from twisted.internet.defer import succeed
from zope.interface.declarations import implements

from intranet3 import memcache
from intranet3.log import EXCEPTION_LOG, INFO_LOG, DEBUG_LOG
from intranet3.models.project import SelectorMapping
from intranet3.models import User
from intranet3.helpers import decoded_dict
from intranet3.lib.scrum import parse_whiteboard
from intranet3.priorities import PRIORITIES

EXCEPTION = EXCEPTION_LOG(__name__)
LOG = INFO_LOG(__name__)
DEBUG = DEBUG_LOG(__name__)

_marker = object()

class Bug(object):
    
    def __init__(self,
                 tracker, id, desc, reporter, owner, priority, severity,
                 status, resolution, project_name, component_name, deadline,
                 opendate, changeddate,
                 dependson=_marker, blocked=_marker, whiteboard='', version='',
                 number=None):
        self.time = 0.0
        self.tracker = tracker
        self.number = number  # Unique number for github
        self.id = str(id)
        self.desc = desc
        self.reporter = reporter
        self.owner = owner
        self.priority = priority
        self.severity = severity
        self.status = status
        self.resolution = resolution
        self.project_name = project_name
        self.component_name = component_name
        self.project = None
        self.deadline = deadline
        self.opendate = opendate
        self.changeddate = changeddate
        self.dependson = {} if dependson is _marker else dependson
        self.blocked = {} if blocked is _marker else blocked

        if isinstance(whiteboard, basestring):
            self.whiteboard = parse_whiteboard(whiteboard)
        else:
            self.whiteboard = whiteboard
        self.version = version

    def get_url(self):
        raise NotImplementedError()

    def is_unassigned(self):
        raise NotImplementedError()

    @property
    def is_blocked(self):
        return False

    def get_status(self):
        """
        Convert tracker specific status to one of these:
        'NEW', 'ASSIGNED', 'REOPENED', 'UNCONFIRMED', 'CONFIRMED', 'WAITING', 'RESOLVED', 'VERIFIED'
        """
        raise NotImplementedError()

    @property
    def priority_number(self):
        priority = getattr(self, 'priority', 'unknown')
        return PRIORITIES.get(priority.lower(), 5)

    @property
    def severity_number(self):
        severity = getattr(self, 'severity', 'unknown')
        return PRIORITIES.get(severity.lower(), 5)

class FetchException(Exception):
    pass

class SimpleProtocol(Protocol):
    
    def __init__(self, on_success, on_error):
        self.buffer = []
        self.on_success = on_success
        self.on_error = on_error
        
    def dataReceived(self, bytes):
        self.buffer.append(bytes)

    def connectionLost(self, reason):
        DEBUG(u'SimpleProtocol lost connection due to %s' % (reason.getErrorMessage(), ))
        if isinstance(reason.value, ResponseDone):
            self.on_success(''.join(self.buffer))
        else:
            self.on_error(reason.value)
            
class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class cached_bug_fetcher(object):
    """ makes function fetch bugs from cache first """
    def __init__(self, key_generator):
        assert callable(key_generator)
        self.key_generator = key_generator
    
    def __call__(self, func):
        def fetcher(this, *args, **kwargs):
            query = self.key_generator(*args, **kwargs)
            key = u"BUGS_LOGIN-%s_TRACKERID-%s_QUERY-%s" % (this.login, this.tracker.id, query)
            bugs = memcache.get(key)
            if bugs is None: # fetch as usual
                DEBUG(u"Bugs not in cache for key %s" % (key, ))
                this.cache_key = key.replace(' ', '') # mark where to cache results
                func(this, *args, **kwargs)
            else:  # bugs got from cache
                DEBUG(u"Bugs found in cache for key %s" % (key, ))
                this.bugs = bugs
                this.success()
        return fetcher

class BaseFetcher(object):
    
    USER_AGENT = 'Intranet Bug Fetcher'
    contextFactory = WebClientContextFactory()
    client = Agent(reactor, contextFactory)
    SLEEP_PERIOD = 0.1
    CACHE_TIMEOUT = 3 * 60  # 3 minutes
    redirect_support = False
    
    def __init__(self, tracker, credentials, login_mapping):
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
        
    def run(self):
        """ start fetching tickets """
        try:
            # start asynchronous ticket fetching
            self.fetch()
        except:
            # failed to start ticket fetching
            self.done = True
            raise
        
    def request(self, url, headers, on_success, on_failure=None, method='GET', body=None):
        LOG(u'Will request URL %s' % (url, ))
        if on_failure is None:
            on_failure = self.failed
        deferred = self.client.request(
            method,
            url,
            Headers(headers),
            None if body is None else StringProducer(body)
        )
        def redirecting_on_success(resp):
            if resp.code == 302:
                LOG(u"Redirect (302) found in response")
                location = resp.headers.getRawHeaders('location')[0]
                if method == 'POST':
                    new_url, body = location.split('?')
                    self.request(new_url, headers, on_success, on_failure,
                                 method, body)
                else:
                    self.request(location, headers, on_success, on_failure,
                                 'GET', None)
            else:
                on_success(resp)
        deferred.addCallbacks(redirecting_on_success if self.redirect_support else on_success, on_failure)

    def failed(self, err):
        self.fail(err)
        EXCEPTION(u"Fetcher for tracker %s failed: %s" % (self.tracker.name, err))
        
    def success(self):
        self.done = True
        
    def get_headers(self):
        """ Generate request headers (as a dictionary) """
        return {
            'User-Agent': [self.USER_AGENT]
        }
    
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

    def fetch_scrum(self, sprint_name, project_id):
        raise NotImplementedError()

    def isReady(self):
        """ Check if this fetcher is done """
        return self.done
    
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

    def __iter__(self):
        """ iterate over fetched tickets """
        if self.cache_key and self.error is None: # cache bugs if key was designeated and no error occured
            memcache.set(self.cache_key, self.bugs, timeout=self.CACHE_TIMEOUT)
            DEBUG(u"Cached %s bugs for key %s" % (len(self.bugs), self.cache_key))
        for bug in self.bugs.itervalues():
            self.resolve(bug)
            yield bug
            
    def responded(self, resp, on_success=None):
        """ Called when server returns response headers """
        if resp.code == 200:
            on_success = on_success or self.received
            resp.deliverBody(SimpleProtocol(on_success, self.failed))
        else:
            self.fail(FetchException(u'Received response %s' % (resp.code, )))

    def received(self, data):
        """ Called when server returns whole response body """
        try:
            for bug in self.parse(data):
                self.bugs[bug.id] = bug  
        except BaseException, e:
            EXCEPTION(u"Could not parse tracker response")
            self.fail(e)
        else:
            self.success()
            
    def parse(self, data):
        raise NotImplementedError()
    
    def fail(self, error):
        self.done = True
        self.error = error
    
    def update_depensons_and_blocked_status(self):
        for bug in self.bugs.itervalues():
            for key in bug.dependson:
                bug.dependson[key] = self.dependson_and_blocked_status.get(key, {})
                
            for key in bug.blocked:
                bug.blocked[key] = self.dependson_and_blocked_status.get(key, {})
        
    fetch_user_resolved_tickets = success
        
    fetch_all_resolved_tickets = success


class CSVParserMixin(object):
    
    # function that converts CSV entries into bug class keyword params
    get_converter = lambda self: None
    
    # bug object class
    bug_class = None
    
    # CSV encoding
    encoding = 'utf-8'
    
    # CSV delimited
    delimiter=','
    
    def parse(self, data):
        converter = self.get_converter()

        if codecs.BOM_UTF8 == data[:3]:
            data = data.decode('utf-8-sig')

        if '\r\n' in data:
            data = data.split('\r\n')
        else:
            data = data.split('\n')

        reader = csv.DictReader(data,  delimiter=self.delimiter)
        for bug_desc in reader:
            bug_desc = decoded_dict(bug_desc, encoding=self.encoding)
            yield self.bug_class(
                tracker=self.tracker,
                **converter(bug_desc)
            )


class BasicAuthMixin(object):

    def get_headers(self):
        headers = super(BasicAuthMixin, self).get_headers()
        headers.update(Authorization=['Basic %s' % b64encode('%s:%s' % (self.login, self.password))])
        return headers

class AuthCookiesMixin(object):

    def get_headers(self):
        """ We need to do an additional HTTP request to get a login token from cookie """
        headers = super(AuthCookiesMixin, self).get_headers()
        if self.cookie:
            headers['Cookie'] = self.cookie
        return headers

    def __call__(self, *args, **kwargs):
        self.cookie = None
        try:
            self.cookie = self.get_auth_cookie()

        except BaseException, e:
            EXCEPTION(u'Cookie auth token fetch failed')
            self.failed = FetchException(e)
        else:
            self.failed = None
            return super(AuthCookiesMixin, self).__call__(*args, **kwargs)

    def __iter__(self):
        if self.failed:
            raise self.failed
        else:
            for bug in super(AuthCookiesMixin, self).__iter__():
                yield bug
